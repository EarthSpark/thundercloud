# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""ORM Database utilities."""
import contextlib
import logging
import os
import time

import psycopg2.errors
# AsIs removed - no longer needed with SQLAlchemy 2.0
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql.expression import text

logger = logging.getLogger(__name__)


def create_database_if_not_exists(default_url, dbname):
    """Create a new postgresql database.

    :param default_url: the default database url
    :param dbname: name of the new database.
    :returns: ``True`` if the database was created, ``False`` otherwise.
    """
    engine = create_engine_for_database(default_url, "postgres",
                                        isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        results = conn.execute(text("SELECT 1 FROM pg_database WHERE datname=:dbname;"), {"dbname": dbname})
        if results.first() != (1,):  # pragma nocoverage
            logger.info("Creating a new database: %s", dbname)
            conn.execute(text("CREATE DATABASE %s" % (dbname,)))
            return True
    return False


def drop_database_if_exists(default_url, dbname):
    """
    Drop a postgresql database.

    :param default_url: the default database url
    :param dbname: name of the new database.
    """
    engine = create_engine_for_database(default_url, "postgres",
                                        isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS %s" % (dbname,)))


def create_engine_for_database(default_url, dbname, **options):
    """
    Create an engine for a different dbname.

    :returns: a database engine
    :rtype: sqlalchemy.engine.base.Engine
    """
    sql_url = make_url(default_url)
    sql_url = sql_url.set(database=dbname)
    if dbname != 'postgres':  # pragma: nocoverage
        logger.info("Connected to %s" % (sql_url,))
    return create_engine(sql_url, **options)


def reset_database_schema(engine):
    """
    Reset the database schema.

    :param engine: a database engine
    :type engine: sqlalchemy.engine.base.Engine
    """
    logger.info("Resetting database schema")
    with engine.connect() as conn:
        # Drop extensions first so they get fully recreated (not skipped)
        # when base.sql runs CREATE EXTENSION IF NOT EXISTS.
        # Without this, DROP SCHEMA CASCADE destroys extension functions
        # but leaves the extension registered, so IF NOT EXISTS skips it.
        conn.execute(text('DROP EXTENSION IF EXISTS "uuid-ossp" CASCADE;'))
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.execute(text("GRANT CREATE, USAGE ON SCHEMA public TO public;"))
        conn.commit()


def database_exists(engine, database):
    """
    Check if a database exists.

    :param engine: a database engine
    :type engine: sqlalchemy.engine.base.Engine
    :param database:
    :return: ``True`` if the database exists, otherwise ``False``
    :rtype: bool
    """
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM pg_database WHERE datname = :datname;"),
            {"datname": database})
        return result.first()[0] > 0


def database_has_tables(engine):  # pragma: nocoverage
    """
    Check if a database has any tables.

    :param engine: a database engine
    :type engine: sqlalchemy.engine.base.Engine
    :return: ``True`` if any tables exist, otherwise ``False``
    :rtype: bool
    """
    logger.info("Checking for tables")

    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';"))
        return result.first()[0] > 0


def database_has_table(engine, table):  # pragma: nocoverage
    """
    Check if a database table exists.

    :param engine: a database engine
    :type engine: sqlalchemy.engine.base.Engine
    :param table: table name
    :type table: str
    :return: ``True`` if the table exists, otherwise ``False``
    :rtype: bool
    """
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM pg_tables WHERE tablename = :table"), {"table": table})
        return result.first()[0] == 1


def database_has_constraint(engine, constraint_name):
    """
    Check if a constraint exists in a database.

    :param engine: a database engine
    :type engine: sqlalchemy.engine.base.Engine
    :param constraint_name: the constraint to check
    :return: True if it exists, False otherwise
    """
    with engine.connect() as conn:
        result = conn.execute(
            text('SELECT COUNT(*) '
                 'FROM information_schema.constraint_table_usage '
                 'WHERE constraint_name = :constraint_name;'),
            {"constraint_name": constraint_name},
        )
        return result.fetchone() != (0,)


@contextlib.contextmanager
def sync_triggers_disabled(conn):
    """
    Disable all sync triggers.

    This prevents SymmetricDS created triggers from attempting to understand
    and outdated schema.
    This is required when a schema is changed and must be accompanied by a
    corresponding sync of triggers via symadmin sync-triggers

    :param conn: the database connection
    :type conn: sqlalchemy.engine.base.Connection
    :return:
    """
    result = conn.execute(
        text('SELECT DISTINCT event_object_table '
             'FROM information_schema.triggers '
             'WHERE event_object_table NOT LIKE \'sym_%%\' AND'
             '      event_object_table NOT LIKE \'%%_view\';')
    )
    tables = sorted([row[0] for row in result])
    logger.info("Disabling triggers for tables: %s", tables)
    for table in tables:  # pragma: nocoverage
        # Table names cannot be parameterized, so use string formatting
        # This is safe because table names come from information_schema
        conn.execute(
            text(f'ALTER TABLE IF EXISTS "{table}" DISABLE TRIGGER USER;')
        )
    yield
    logger.info("Re-enabling triggers for tables %s", tables)
    for table in tables:  # pragma: nocoverage
        # Table names cannot be parameterized, so use string formatting
        # This is safe because table names come from information_schema
        conn.execute(
            text(f'ALTER TABLE IF EXISTS "{table}" ENABLE TRIGGER USER;')
        )


def wait_for_table(engine, tablename, wait_seconds=2):
    """
    Wait for a database table to exist.

    :param engine: a database engine
    :type engine: sqlalchemy.engine.base.Engine
    :param tablename: a table
    :type tablename: str
    :param wait_seconds: how long to wait between retries
    :type wait_seconds: int
    """
    i = 0
    while True:
        if i == 1:
            logger.info("Waiting for table %s to be present in schema", tablename)
        i += 1
        conn = engine.connect()
        res = conn.execute(
            text("SELECT COUNT(*) FROM pg_tables WHERE tablename = :table;"),
            {"table": tablename},
        )
        count = res.fetchone()[0]
        conn.close()
        if count == 1:
            if i > 1:
                logger.info("Table %s found", tablename)
            break

        time.sleep(wait_seconds)


def wait_for_triggers(engine, wait_seconds=10):
    """
    Wait for a cloud database to have all its triggers created.

    This will check to make sure that the number of triggers in
    the database has settled for 10 seconds.
    The settle time is configurable via the wait_seconds param.

    :param engine: a database engine
    :type engine: sqlalchemy.engine.base.Engine
    :param wait_seconds: how long to wait between retries
    :type wait_seconds: int
    """
    logger.info(
        "Waiting the number of triggers in the database to settle for %s seconds",
        wait_seconds,
    )

    previous_count = None

    conn = engine.connect()

    while True:

        res = conn.execute(
            text("SELECT count(*) FROM information_schema.triggers;")
        )
        current_count = res.fetchone()[0]

        if current_count == 0:
            logger.info("still waiting for triggers to appear in the database")
        elif current_count != previous_count:
            logger.info("Trigger count still rising. Currently at {} triggers".format(current_count))
        else:
            logger.info("Trigger count appears to have settled at {} triggers".format(current_count))
            break

        previous_count = current_count
        time.sleep(wait_seconds)

    conn.close()


def get_table_count(connection, tablename):
    """
    Check the count of rows in a table.

    :param connection: a database connection
    :type connection: sqlalchemy.engine.base.Connection
    :param tablename:
    :type tablename: str
    """
    res = connection.execute(
        text(f'SELECT COUNT(*) FROM public.{tablename};')
    )
    return res.fetchone()[0]


def wait_for_table_count(engine, tablename, count, wait_seconds=2):
    """
    Wait for a table to contain a certain number of rows.

    :param engine: a database engine
    :type engine: sqlalchemy.engine.base.Engine
    :param tablename:
    :type tablename: str
    :param count: count that the table should have before we return
    :type count: int
    :param wait_seconds: how long to wait between retries
    :type wait_seconds: int
    """
    wait_for_table(engine, tablename)
    i = 0
    while True:
        if i == 1:
            logger.info("Waiting for table %s to contain at least %s row(s) ]", tablename, count)
        i += 1
        conn = engine.connect()
        table_count = get_table_count(conn, tablename)
        conn.close()
        if table_count >= count:
            if i > 1:
                logger.info("Table %s contains %s items, continuing", tablename, table_count)
            break

        time.sleep(wait_seconds)


def wait_for_postgres(url, wait_seconds=2):
    """
    Wait for a database instance of PostgreSQL to startup.

    :param url: database url to connect to
    :type url: str
    :param wait_seconds: how long to wait between retries
    :type wait_seconds: int
    """
    i = 0
    while True:
        if i == 1:
            logger.info("Waiting for PostgreSQL")
        i += 1
        try:
            engine = create_engine(url)
            engine.connect()
            return engine
        except OperationalError:
            pass

        time.sleep(wait_seconds)


def wait_for_ground_host(engine, wait_seconds=2):
    """Wait for a ground node to come up."""
    # The last thing SymmetricDS does on ground after setting up a schema,
    # is to request an insert on the sym_node_host table on _cloud_, so when
    # it comes in there, everything will be ready to start creating examples.
    while True:
        conn = engine.connect()
        res = conn.execute(
            text("SELECT COUNT(*) FROM sym_node_host, sym_node "
                 "WHERE sym_node_host.node_id = sym_node.node_id "
                 "AND sym_node.node_group_id = 'ground-group';"))
        count = res.fetchone()[0]
        conn.close()
        if count >= 1:
            break
        time.sleep(wait_seconds)


def table_is_empty(engine, table):
    """Check if a table has no records in it."""
    conn = engine.connect()
    n_records = get_table_count(conn, table)
    conn.close()
    return n_records == 0


def bootstrap_production(app):
    """
    Bootstrap a production instance.

    This is a little bit more involved than bootstrapping a development
    environment, this will create a database if one doesn't exist,
    it will also try to initialize sync and create demo data if
    requested to

    :param app: an application
    :type app: sparkmeter.app.SparkmeterApplication
    """
    from flask_security.utils import hash_password

    from sparkmeter.controller import resetdb
    from sparkmeter.database.alchemy import sql
    from sparkmeter.database.demodata import DemoExamples
    from sparkmeter.ground.grounddomain import Ground
    from sparkmeter.misc.uuidutils import as_uuid
    from sparkmeter.models import session_scope
    from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
    from sparkmeter.user.userdomain import Role, User

    engine = wait_for_postgres(app.config['SQLALCHEMY_DATABASE_URI'])

    init_demo = os.environ.get('INIT_DEMO_ON_STARTUP') == "true"

    # is this a brand new database with nothing in it
    if not database_has_table(engine, 'alembic_version'):
        logger.info("Creating an empty schema")
        with app.app_context():
            app.setup_databases()
            # if INIT_CREATE_DEFAULTS = true then reset the db with defaults
            empty = os.environ.get('INIT_CREATE_DEFAULTS') != 'true'
            resetdb(force=True, empty=empty, resetschema=False, engine=engine)
    else:
        # this is not a new database.
        # if we are in the cloud lets check if we need to
        # run an alembic upgrade before starting the app
        # this allows the app to take care of itself and
        # allow the infrastructure to not need to interfere
        # with the application in a difficult way.
        if app.config['HEROKU']:
            logger.info("Attempting schema upgrade")
            with app.app_context():
                from alembic import command

                from sparkmeter.alembic.migrationhelper import get_alembic_config
                app.setup_databases()
                alembic_cfg = get_alembic_config()
                command.upgrade(alembic_cfg, 'head')
                sql.session.commit()
                logger.info('Finished upgrading schema')

    # create the initial ground if the system has no ground
    if table_is_empty(engine, "ground") and not init_demo:
        logger.info("No ground found in this database")
        with app.app_context():
            app.setup_databases()

            # make sure the required fields are set if we are going to try
            # to create a ground and cloud otherwise we will fall back to
            # the original behavior of not creating them in the cloud on boot
            required_ground_fields = {
                'INIT_GROUND_NAME',
                'INIT_GROUND_SERIAL',
            }
            missing_ground_fields = required_ground_fields - set(os.environ.keys())

            if missing_ground_fields:
                # FIXME: if this system has no ground, then the app should not start up.
                # This is hiding a configuration error.
                # It is only here because it is how deploy uses the app currently.
                # Once that is gone this should be come a failure.
                logger.warning(
                    'Skipping creation of ground because required fields are missing %s',
                    sorted(missing_ground_fields)
                )
            else:
                with session_scope() as session:
                    logger.info('Creating the initial ground')
                    Ground.create_empty(
                        session,
                        serial=os.environ['INIT_GROUND_SERIAL'],
                        name=os.environ['INIT_GROUND_NAME'],
                        secret_key='unused',
                    )
                    logger.info('ground created')

    # init sync (create symmetricds tables and register triggers)
    if app.config['HEROKU'] and not app.config.get('STANDALONE_SPARKAPP', 0):
        # The last thing symadmin create-sym-tables does is to
        # insert 4 entries into the sym_sequence table
        wait_for_table_count(engine, 'sym_sequence', 4)

        if table_is_empty(engine, "sym_trigger_hist"):
            logger.info("Running init-sync")
            app.setup_databases()

            from sparkmeter.database.sync import create_default_policy
            with app.app_context():
                create_default_policy(
                    app.sql.session,
                    external_id=os.environ.get('EXTERNAL_ID', 'cloud'),
                )

            # wait until symmetricds has created at least one sym trigger
            wait_for_table_count(engine, 'sym_trigger_hist', 1)

            # wait for symmetricds to place all triggers on sparkmeter tables
            # this means it is safe to insert data after this point
            wait_for_triggers(engine)

    # Create the initial admin user if this database has no users in it and this is the cloud.
    # this is after sync has been started so that this user is synced to the ground.
    if table_is_empty(engine, "user") and app.config.get('INIT_ADMIN_USERNAME') and not init_demo:
        logger.info("No admin user found in this database")
        with app.app_context():
            app.setup_databases()

            # make sure the required fields are set if we are going to try
            # to create a ground and cloud otherwise we will fall back to
            # the original behavior of not creating them in the cloud on boot
            required_admin_fields = {
                'INIT_ADMIN_USERNAME',
                'INIT_ADMIN_PASSWORD',
                'INIT_ADMIN_EMAIL',
            }
            missing_admin_fields = required_admin_fields - set(os.environ.keys())

            if missing_admin_fields:
                # FIXME: if this system has no users, then the app should not start up.
                # This is hiding a configuration error.
                # It is only here because it is how deploy uses the app currently.
                # Once that is gone this should be come a failure.
                logger.warning(
                    'Skipping creation of the admin because required fields are missing %s',
                    list(missing_admin_fields),
                )
            else:
                with session_scope() as session:
                    logger.info('Creating the initial admin user')
                    created, user = User.get_one_or_create(
                        session=session,
                        id=as_uuid(os.environ['INIT_ADMIN_USERNAME']),
                        username=os.environ['INIT_ADMIN_USERNAME'],
                    )
                    user.roles = [Role.get_by_name('operator')]
                    user.password = hash_password(os.environ['INIT_ADMIN_PASSWORD'])
                    user.email = os.environ['INIT_ADMIN_EMAIL']
                    user.grounds = Ground.get_all()
                    user.accounts = SalesAccount.get_all()
                    user.account_all_access = True
                    user.ground_all_access = True
                    logger.info('admin user created')

    # TODO: we should also have a param to init the ground on the ground on startup using the same
    # env params as we do in the cloud to remove one more responsibility from chef.

    # TODO: we should get rid of all this demo code, it doesn't belong here.
    # Or at least update it to use the standard process for creating a ground and admin user.
    if init_demo:
        if app.config['HEROKU'] and not app.config.get('STANDALONE_SPARKAPP', 0):  # pragma: nocoverage
            wait_for_ground_host(engine)
        else:
            # FIXME: Remove when we move over integration testing with sync
            wait_for_table(engine, "ground")
        conn = engine.connect()
        n_grounds = get_table_count(conn, "ground")
        conn.close()
        if n_grounds == 0:
            logger.info("Resetting demo")
            app.setup_databases()
            with app.app_context():
                resetdb(force=True, resetschema=False)
                data = DemoExamples(sql.session)
                if os.environ.get('SM_SERIAL_GROUND1'):
                    data.create_ground(os.environ['SM_MICROGRID_NAME_GROUND1'],
                                       os.environ['SM_SERIAL_GROUND1'])
                    data.create_ground(os.environ['SM_MICROGRID_NAME_GROUND2'],
                                       os.environ['SM_SERIAL_GROUND2'])
                else:
                    data.create_ground()
                data.create_all()
                sql.session.commit()


def load_database_schemas(engine):
    """Import all our database schemas.

    :param engine: database engine to import on
    """
    filenames = [
        'meterschema.sql',
        'transactionschema.sql'
    ]
    for filename in filenames:
        load_schema(engine, filename)


def load_schema(engine, filename):
    """Import a schema file into a database engine.

    :param engine: database engine to import on
    :param filename: sql file to import
    """
    logger.info("Loading schema %s", filename)
    filename = os.path.join(os.path.dirname(__file__), 'schemas', filename)
    with open(filename) as f:
        data = f.read()
        # Get raw psycopg2 connection to avoid SQLAlchemy parameter escaping
        # In test sessions, engine may be a Connection bound to the test transaction
        actual_engine = engine.engine if hasattr(engine, 'engine') else engine
        raw_conn = actual_engine.raw_connection()
        try:
            cursor = raw_conn.cursor()
            cursor.execute(data)
            raw_conn.commit()
        except psycopg2.errors.DuplicateTable:
            raw_conn.rollback()
        finally:
            raw_conn.close()


def get_schema_tables():
    """Get a list of all database tables.

    This excludes views and symmetricds tables.
    """
    from sparkmeter.database.alchemy import sql
    for table in sql.metadata.tables.values():
        if table.name.endswith('_view'):
            continue
        yield table
