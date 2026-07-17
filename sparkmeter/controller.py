# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Controller module for the ground web interface."""

from __future__ import absolute_import

import logging
import uuid
from builtins import str

from flask.globals import current_app
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from sparkmeter.billing import CalculateBilling
from sparkmeter.config.configdict import config
from sparkmeter.database.alchemy import sql
from sparkmeter.database.database import get_schema_tables, load_schema
from sparkmeter.exceptions import DatabaseLockTimeoutException, DuplicateReadingException, TransactionError
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.meter.meterdomain import Meter
from sparkmeter.meter.meterstate import MeterState
from sparkmeter.misc.uuidutils import as_uuid
from sparkmeter.models import session_scope
from sparkmeter.reading.readingdomain import Reading
from sparkmeter.snapshot.snapshotdomain import Snapshot
from sparkmeter.transaction.transactiondomain import Transaction, TransactionSource, Wallet
from sparkmeter.user.userdomain import Role

logger = logging.getLogger(__name__)


def add_reading(data, update_meter_state=True):
    """
    Save a raw reading to the database and process it.

    :param data: raw reading data
    :type data: dict
    :param update_meter_state: enable sending of config packets
    :type update_meter_state: bool
    :return: reading id
    """
    with session_scope() as session:
        reading, meter = save_raw_reading(data, session)
    with session_scope() as session:
        reading_id = process_reading(reading, meter, session, update_meter_state)
    return reading_id


def save_raw_reading(data, session):
    """
    Save a raw reading to the database.

    This method is exposed to make existing unit testing possible and should
    otherwise not be used directly.

    `data` is a dict of reading field values. This method commits the data to
    the database.

    :param data: reading field values
    :type data: dict
    :param session: The database session to use
    :type Session:
    :return: (reading, meter)
    """
    # First check if there are any existing readings with the same heartbeat
    if (
        session.query(Reading)
        .filter_by(meter=str(data["meter"]), heartbeat_end=data["heartbeat_end"])
        .count()
    ):
        raise DuplicateReadingException(
            "Meter {} already has a reading with heartbeat_end={}".format(
                data["meter"], data["heartbeat_end"]
            )
        )

    meter = session.query(Meter).filter_by(code=data["meter"]).one()
    snapshot = Snapshot.get_or_create_meter_snapshot(code=str(data["meter"]), session=session)
    session.add(snapshot)
    reading = Reading(
        meter=str(data["meter"]),
        heartbeat_start=data["heartbeat_start"],
        heartbeat_end=data["heartbeat_end"],
        frequency=data["frequency"],
        state=MeterState.get_state_id_from_name(data["state"]),  # int
        uptime=data["uptime"],
        voltage_min=data["voltage_min"],
        voltage_max=data["voltage_max"],
        voltage_avg=data["voltage_avg"],
        current_min=data["current_min"],
        current_max=data["current_max"],
        current_avg=data["current_avg"],
        energy=data["energy"],
        true_power_inst=data["true_power_inst"],
        true_power_avg=data["true_power_avg"],
        apparent_power_avg=data["apparent_power_avg"],
        power_factor_avg=data["power_factor_avg"],
        user_power_limit=data["user_power_limit"],
        snapshot_id=str(snapshot.id),
    )
    session.add(reading)
    return reading, meter


def process_reading(reading, meter, session, update_meter_state=True):
    """
    Process a reading by calculating billing and updating stats.

    This method is exposed to make existing unit testing possible and should
    otherwise not be accessed from outside this module.

    :param reading: reading to process
    :type reading: Reading
    :param meter: associated with the reading
    :type meter: Meter
    :param session: The database session to use
    :type Session:
    :param update_meter_state: if we should send updates to the meter
    :type update_meter_state: bool
    :return: reading_id
    """
    if meter.is_customer_meter():
        try:
            if config["LOCK_WALLETS_ON_PROCESS"]:
                session.execute(
                    text("SET LOCAL lock_timeout = '{}s';".format(config["LOCK_WALLETS_ON_PROCESS_TIMEOUT"]))
                )
                session.query(Wallet).with_for_update(of=Wallet).filter(
                    (Wallet.id == meter.credit_wallet.id)
                    | (Wallet.id == meter.debt_wallet.id)
                    | (Wallet.id == meter.plan_wallet.id)
                ).all()
                session.flush()
                logger.info(
                    "Billing wallet lock acquired for: %s, %s and %s",
                    meter.credit_wallet.id,
                    meter.debt_wallet.id,
                    meter.plan_wallet.id,
                )
            session.expire_all()
            reading.update_kilowatt_hours(
                meter.system_info.last_energy, meter.system_info.last_energy_datetime
            )

            # The meter object is tied to the previous session and will not
            # update the wallets that get loaded in
            meter = session.query(Meter).get(meter.id)
            billing = CalculateBilling(reading, meter, session)
            billing.calculate()
            session.commit()
            if config["LOCK_WALLETS_ON_PROCESS"]:
                logger.info("Billing wallet lock released")

        except OperationalError as e:
            if "canceling statement due to lock timeout" in str(e):
                raise DatabaseLockTimeoutException from e
            else:  # pragma: nocoverage
                raise
    else:
        reading.update_kilowatt_hours(meter.system_info.last_energy, meter.system_info.last_energy_datetime)

    meter.update_from_reading(reading)

    # this has to occur after the meter has been updated so that we can
    # take the daily limit into account when determining if we need to
    # send out a set config packet.
    if meter.is_customer_meter() and update_meter_state:
        # maybe turn off the meter for lack of funds
        # or for the daily energy limit
        meter.send_set_config_based_on_reading(reading)

    return reading.id


def get_ground():
    """Get the current ground object."""
    return Ground.get_by_serial(config["SERIAL"])


def resetdb(empty=False, force=False, resetschema=True, engine=None):
    """Drop all and tables in postgres.

    :param empty: `True` if the database should not be initialized with default data. `False` otherwise.
    :param force: `True` if the database should be reset if it already has tables. `False` otherwise.
    :param resetschema: `True` if the schema should be reset in the event the db exists. `False` otherwise.
    :param engine: The database engine to use.
    """
    # type: (bool, bool, bool, Engine)
    from sparkmeter.database.database import (
        create_database_if_not_exists,
        database_has_tables,
        reset_database_schema,
    )

    # First, create the PostgreSQL database if it doesn't exist
    if engine is None:
        engine = current_app.sql.engine

    assert isinstance(engine, Engine)
    if not force and database_has_tables(engine):
        logger.error("Not resetting database, there are tables present, add --force to continue")
        return

    if not create_database_if_not_exists(engine.url, engine.url.database):
        if resetschema:
            # If a database did exist, just reset the schema
            reset_database_schema(engine)

    # We have a database and an empty schema, just create all tables in the main
    # application schema and skip symmetrics tables which are created by symadmin
    logger.info("Creating database tables")
    load_schema(engine, "base.sql")
    sql.metadata.create_all(bind=engine, tables=get_schema_tables())

    # Add the current alembic revision as well, so migration upgrades work
    logger.info("Set alembic revision")
    from alembic import command

    from sparkmeter.alembic.migrationhelper import get_alembic_config

    alembic_cfg = get_alembic_config()
    command.stamp(alembic_cfg, "head")
    session = Session(engine)
    session._model_changes = {}
    session.commit()

    # Load database schemas (views, functions, etc.)
    logger.info("Loading database schemas")
    from sparkmeter.database.database import load_database_schemas

    load_database_schemas(engine)

    if not empty:
        logger.info("Creating default records in new database")
        create_default_config_params()
        create_default_roles()
        create_default_transaction_sources()
        create_default_sms_objects()
        create_system_sales_account()
        create_default_meter_models()


def create_default_config_params():
    """Creating default configuration parameters."""
    with session_scope() as session:
        from sparkmeter.config.configdomain import ConfigParameter

        ConfigParameter.add_defaults(session)
        session.commit()
    logger.info("Created default config params")


def create_default_roles():
    """Creating default roles."""
    roles = [
        {"id": uuid.UUID("000000000-0000-0000-0001-00000000001"), "name": "vendor"},
        {"id": uuid.UUID("000000000-0000-0000-0001-00000000002"), "name": "operator"},
        {"id": uuid.UUID("000000000-0000-0000-0001-00000000004"), "name": "api"},
    ]

    created_roles = {}

    count = 0
    with session_scope() as session:
        for role in roles:
            result = Role.get_one_or_create(session=session, id=role["id"], name=role["name"])
            count += int(result.created)
            created_roles[role["name"]] = result.object

    if count:
        logger.info("Created default roles")

    return created_roles


def create_default_transaction_sources(session=None):
    """Create objects for the default cash and bonus transaction sources."""
    logger.info("Creating default transaction sources")
    if session is None:
        session = sql.session
    with current_app.app_context():
        TransactionSource.get_one_or_create(
            id=as_uuid(TransactionSource.BONUS),
            session=session,
            name=TransactionSource.BONUS,
            monetary=False,
        )
        TransactionSource.get_one_or_create(
            id=as_uuid(TransactionSource.CASH),
            session=session,
            name=TransactionSource.CASH,
            monetary=True,
        )
        session.commit()


def create_default_sms_objects(session=None):
    """Create default commands and messages objects in the database."""
    from sparkmeter.event.eventdomain import SMSConfig, SMSConfigCommand, SMSConfigMessage

    if session is None:
        session = sql.session

    SMSConfig.get_one_or_create(
        id=as_uuid("SMSConfig"),
        session=session,
        flush=True,
    )

    for code, template in list(SMSConfigCommand.DEFAULT_COMMANDS.items()):
        command = SMSConfigCommand.get_one_or_create(
            id=as_uuid(code), session=session, active=True, code=code, template=str(template)
        )
        session.add(command.save())

    for message_type, mti in list(SMSConfigMessage.messages.items()):
        message = SMSConfigMessage.get_one_or_create(
            id=as_uuid(message_type),
            session=session,
            active=True,
            message_type=message_type,
            template=str(mti.default),
        )
        session.add(message.save())
    session.commit()


def create_system_sales_account(session=None):
    """Create the default System Sales Account."""
    from sparkmeter.salesaccount.salesaccountdomain import SalesAccount

    if session is None:
        session = sql.session

    has_account = session.query(SalesAccount).filter_by(system=True).count() > 0
    if not has_account:
        account = SalesAccount.create_empty(global_account=True, id=as_uuid("System"))
        account.system = True
        account.name = "System"
        session.add(account)
        session.commit()


def create_default_meter_models(session=None):
    """Initialize the meter model and scalars tables."""
    from sparkmeter.meter.meterdomain import MeterModels, MeterScalars

    if session is None:
        session = sql.session

    has_scalars = session.query(MeterScalars).count() > 0
    if not has_scalars:
        scalars2x = MeterScalars(
            id=as_uuid("2x"),
            name="2x",
            frequency_scalar=0.01,
            voltage_scalar=0.01,
            current_scalar=0.002,
            energy_scalar=0.00003125,
            power_scalar=2.0,
            power_factor_scalar=0.001,
        )
        scalars4x = MeterScalars(
            id=as_uuid("4x"),
            name="4x",
            frequency_scalar=0.01,
            voltage_scalar=0.01,
            current_scalar=0.004,
            energy_scalar=0.00003125,
            power_scalar=4.0,
            power_factor_scalar=0.001,
        )
        session.add(scalars2x)
        session.add(scalars4x)
        session.commit()
        logger.info("Created default meter scalars")

    has_meter_models = session.query(MeterModels).count() > 0
    if not has_meter_models:
        session.add(
            MeterModels(
                id=as_uuid("SM5R"),
                name="SM5R",
                inrush_limit=12.0,
                continuous_limit=6.0,
                phase_count=1,
                scalars_id=scalars2x.id,
                enabled=True,
            )
        )
        session.add(
            MeterModels(
                id=as_uuid("SM5XR"),
                name="SM5XR",
                inrush_limit=12.0,
                continuous_limit=6.0,
                phase_count=1,
                scalars_id=scalars2x.id,
                enabled=False,
            )
        )
        session.add(
            MeterModels(
                id=as_uuid("SM15R"),
                name="SM15R",
                inrush_limit=20.0,
                continuous_limit=20.0,
                phase_count=1,
                scalars_id=scalars2x.id,
                enabled=True,
            )
        )
        session.add(
            MeterModels(
                id=as_uuid("SM16R"),
                name="SM16R",
                inrush_limit=19.0,
                continuous_limit=16.0,
                phase_count=1,
                scalars_id=scalars2x.id,
                enabled=True,
            )
        )
        session.add(
            MeterModels(
                id=as_uuid("SM20R"),
                name="SM20R",
                inrush_limit=20.0,
                continuous_limit=20.0,
                phase_count=1,
                scalars_id=scalars2x.id,
                enabled=True,
            )
        )
        session.add(
            MeterModels(
                id=as_uuid("SM20XR"),
                name="SM20XR",
                inrush_limit=50.0,
                continuous_limit=20.0,
                phase_count=1,
                scalars_id=scalars2x.id,
                enabled=False,
            )
        )
        session.add(
            MeterModels(
                id=as_uuid("SM60R"),
                name="SM60R",
                inrush_limit=61.0,
                continuous_limit=61.0,
                phase_count=1,
                scalars_id=scalars2x.id,
                enabled=True,
            )
        )
        session.add(
            MeterModels(
                id=as_uuid("SM60RP"),
                name="SM60RP",
                inrush_limit=61.0,
                continuous_limit=61.0,
                phase_count=3,
                scalars_id=scalars2x.id,
                enabled=True,
            )
        )
        session.add(
            MeterModels(
                id=as_uuid("SM100E"),
                name="SM100E",
                inrush_limit=100.0,
                continuous_limit=100.0,
                phase_count=1,
                scalars_id=scalars2x.id,
                enabled=True,
            )
        )
        session.add(
            MeterModels(
                id=as_uuid("SM200E"),
                name="SM200E",
                inrush_limit=200.0,
                continuous_limit=200.0,
                phase_count=1,
                scalars_id=scalars4x.id,
                enabled=True,
            )
        )
        for smrsd in ("SMRSD", "SMRSDRF", "SMRSDPLC"):
            session.add(
                MeterModels(
                    id=as_uuid(smrsd),
                    name=smrsd,
                    inrush_limit=81.0,
                    continuous_limit=61.0,
                    phase_count=1,
                    scalars_id=scalars2x.id,
                    enabled=True,
                )
            )
        for smrpi in ("SMRPI", "SMRPIRF", "SMRPIPLC"):
            session.add(
                MeterModels(
                    id=as_uuid(smrpi),
                    name=smrpi,
                    inrush_limit=101.0,
                    continuous_limit=61.0,
                    phase_count=3,
                    scalars_id=scalars2x.id,
                    enabled=True,
                )
            )
        session.commit()
        logger.info("Created default meter models")


def process_transaction(transaction_id):
    """
    Handle the balance updates associated with an unprocessed transaction.

    This should only be executed on the nuc.
    """
    if config["HEROKU"]:
        raise Exception("transactions can not be processed in heroku")

    with session_scope() as session:
        #
        # This lock protects the transaction table against concurrent data changes, and is
        # self-exclusive so that only one session can hold it at a time.
        # The lock is released at transaction end
        #
        # Locking the whole table is not the most efficient way of dealing with
        # this, ideally it should only lock the current transaction row that it
        # will issue an UPDATE for and the parent transaction, but such a code
        # is harder to write and test, so let's keep it simple. Besides,
        # transactions processing speed on a single ground is probably not going to
        # be a significant bottleneck for a long time.
        #
        session.execute(text("LOCK TABLE transactions IN SHARE ROW EXCLUSIVE MODE;"))
        transaction = Transaction.get_by_id(transaction_id)
        transaction = session.merge(transaction)

        try:
            if config["LOCK_WALLETS_ON_PROCESS"]:
                session.execute(
                    text("SET LOCAL lock_timeout = '{}s';".format(config["LOCK_WALLETS_ON_PROCESS_TIMEOUT"]))
                )
                session.query(Wallet).with_for_update().filter(
                    (Wallet.id == transaction.to_wallet_id) | (Wallet.id == transaction.from_wallet_id)
                ).all()
                session.flush()
                logger.info(
                    "Transaction wallet lock acquired for: %s and %s",
                    transaction.from_wallet_id,
                    transaction.to_wallet_id,
                )
            session.expire_all()
            transaction.process()
            session.commit()
            if config["LOCK_WALLETS_ON_PROCESS"]:
                logger.info("Transaction wallet lock released")
        except TransactionError as e:
            if e.code in [TransactionError.ERROR_ALREADY_REVERSED, TransactionError.ERROR_NOT_ENOUGH_FUNDS]:
                transaction.set_error(str(e))
                # commit here because the scoped session will not commit if an exception is raised
                session.commit()
            raise
        except OperationalError as e:
            if "canceling statement due to lock timeout" in str(e):
                raise DatabaseLockTimeoutException() from e
            else:  # pragma: nocoverage
                raise
        return transaction


def create_admin():
    """Create an admin/operator user interactively."""
    import click
    from flask_security.utils import hash_password
    from zope.component import getUtility

    from sparkmeter.ground.grounddomain import Ground
    from sparkmeter.interface import IApplication
    from sparkmeter.misc.uuidutils import as_uuid
    from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
    from sparkmeter.user.userdomain import Role, User

    # Setup databases
    app = getUtility(IApplication)
    app.setup_databases()

    click.echo("Creating admin user (operator role)...")

    # Get user input
    username = click.prompt("Username")
    email = click.prompt("Email")
    password = click.prompt("Password", hide_input=True, confirmation_prompt=True)

    try:
        with session_scope() as session:
            # Check if user already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                click.echo(f"Error: User '{username}' already exists", err=True)
                return 1

            # Create user
            user = User(
                id=as_uuid(username), username=username, email=email, password=hash_password(password)
            )

            # Get operator role
            operator_role = Role.query.filter_by(name="operator").first()
            if not operator_role:
                click.echo("Error: Operator role not found. Database may not be initialized.", err=True)
                return 1

            user.roles = [operator_role]

            # Grant full access
            user.grounds = Ground.get_all()
            user.accounts = SalesAccount.get_all()
            user.account_all_access = True
            user.ground_all_access = True

            session.add(user)
            session.commit()

            click.echo(f"Admin user '{username}' created successfully!")
            return 0

    except Exception as e:
        click.echo(f"Error creating user: {e}", err=True)
        logger.exception("Failed to create admin user")
        return 1
