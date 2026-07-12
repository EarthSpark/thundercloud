# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Demo example data creation."""

import logging
from builtins import object

from flask_security.utils import hash_password

from sparkmeter.config.configdict import config
from sparkmeter.database.types import Choice
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.meter.meterdomain import Meter, MeterConfig, MeterView
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.transaction.transactiondomain import Transaction, TransactionSource
from sparkmeter.user.userdomain import Role, SalesAccountsUsers, User

logger = logging.getLogger(__name__)


class DemoExamples(object):
    """Helper for creating demo example data."""

    def __init__(self, session):
        """Create a new instance."""
        self.session = session
        self.ground = None

    def create_all(self):
        """Create all example data."""
        self._create_users()
        self._create_tariffs()
        self._create_sales_accounts()
        self._create_meters()

    def create_ground(self, name=None, serial=None, secret_key=None):
        """Create an example ground."""
        self.ground = Ground.create_empty(
            self.session,
            serial=serial,
            name=name,
            secret_key=secret_key,
        )

    def _get_password(self):
        password = config["DEMO_PASSWORD"]

        # Pre encrypted password with default salt, since it's slow to generate.
        if password == "password":
            password = "$2a$12$NoGOmNrA3o1OpWHcBZNwO.CLxxYmZyMi6tmxcCJ40VP/6BM6/DqeK"
        else:
            password = hash_password(password)
        return password

    def _create_users(self):
        self.supervisor = self._create_user(
            "operator",
            "Supervisor",
            "supervisor@sparkmeter.io",
            account_all_access=True,
            ground_all_access=True,
        )
        self._create_user("vendor", "Employee", "employee@sparkmeter.io")
        self._create_user("vendor", "Third-party vendor", "vendor@thirdparty.io")
        self.apiuser = self._create_user("api", "api")
        self.session.add(self.apiuser)

    def _create_tariffs(self):
        self._create_tariff(name="ET1", flat_price=80, flat_load_limit=12)
        self._create_tariff(name="ET2", flat_price=60, flat_load_limit=30)
        self._create_tariff(name="ET3", flat_price=40, flat_load_limit=120)
        self._create_tariff(name="ET4", flat_price=30, flat_load_limit=360)
        self.session.flush()

    def _create_meters(self):
        for meter_data in config.get("DEMO_METERS", []):
            self._create_meter(**meter_data)

    def _create_sales_accounts(self):
        sau = SalesAccountsUsers(user=self.supervisor, sales_account=SalesAccount.get_system())
        self.session.add(sau)

        (self._create_sales_account("Internal sales", 0, True, 0, ["Supervisor", "Employee"]),)
        (self._create_sales_account("Mobile money", 0, True, 0, ["Supervisor", "api"]),)
        self._create_sales_account(
            "Third-party sales", 0.05, False, 100, ["Supervisor", "Third-party vendor"]
        )

    def _create_user(self, role, username, email=None, account_all_access=False, ground_all_access=False):
        created, user = User.get_one_or_create(session=self.session, username=username)
        user.roles = [self.session.query(Role).filter_by(name=role).one()]
        user.grounds = [self.ground]

        user.password = self._get_password()
        user.email = email
        user.account_all_access = account_all_access
        user.ground_all_access = ground_all_access
        if created:
            logger.info(
                "Created %s %r"
                % (
                    role,
                    user.username,
                )
            )

        self.session.commit()
        return user

    def _create_tariff(self, name, flat_price, flat_load_limit):
        created, tariff = Tariff.get_one_or_create(session=self.session, name=name)
        tariff.flat_price = flat_price
        tariff.flat_load_limit = flat_load_limit
        tariff.tariff_type = Tariff.TYPE_FLAT
        if created:
            logger.info("Created tariff %r" % (name,))

    def _create_meter(
        self,
        serial=None,
        code=None,
        customer_code=None,
        tariff_name="ET1",
        address=None,
        phone_number=None,
        verified=True,
        name=None,
        hidden=False,
        amount=1,
        meter_state=MeterConfig.STATE_AUTO,
    ):
        if serial is None:
            if code is None:
                raise TypeError("Must provide a serial or code")

            # make a serial for these old style DEMO_METER values
            product_code = "SM15R"
            if code > 1508:
                product_code = "SM20R"
            serial = "%s-01-%08X" % (product_code, code)

        meter_type = Meter.TYPE_TOTALIZER if name is None else Meter.TYPE_CUSTOMER

        meter_view = MeterView.create_meter(meter_type=meter_type, ground=self.ground, serial=serial)
        meter_view.active = not hidden
        meter_view.state = meter_state

        # the address collection is: [street1, street2, city, state, country, postalcode, coords]
        if address is not None:
            meter_view.address_street1 = address[0]
            meter_view.address_street2 = address[1]
            meter_view.address_city = address[2]
            meter_view.address_state = address[3]
            meter_view.address_country = address[4]
            meter_view.address_postalcode = address[5]
            meter_view.address_coords = address[6]

        if meter_type == Meter.TYPE_CUSTOMER:
            meter_view.customer_name = name
            meter_view.customer_code = customer_code
            meter_view.customer_phone_number = phone_number
            meter_view.customer_phone_number_verified = verified
            meter_view.tariff = Tariff.get_by_name(name=config.get("NEW_METER_TARIFF", tariff_name))

        self.session.add(meter_view)
        self.session.commit()
        self.session.flush()

        if meter_type == Meter.TYPE_CUSTOMER:
            Transaction.create_transactions(
                from_object=SalesAccount.query.filter_by(name="Internal sales").one(),
                to_object=meter_view.meter,
                amount=amount,
                user=self.supervisor,
                wallet_type=Transaction(acct_type="credit").acct_type,
                source=TransactionSource.get_by_name("cash"),
                ground=self.ground,
                markup=0,
                session=self.session,
            )

    def _create_sales_account(self, name, markup, global_account, credit, users):
        sa = SalesAccount.create_empty(ground=self.ground, global_account=global_account)
        sa.name = name
        if not global_account:
            sa.markup = markup

        for user in users:
            if user == "api":
                self.apiuser.api_sales_account = sa
                self.session.add(self.apiuser)
            else:
                sau = SalesAccountsUsers(
                    user=User.get_by_name(user),
                    sales_account=sa,
                )
                self.session.add(sau)
        self.session.flush()
        if credit:
            Transaction.create_transactions(
                from_object=SalesAccount.get_system(),
                to_object=sa,
                amount=credit,
                user=self.supervisor,
                wallet_type=Choice(code="credit", value="Credit"),
                source=TransactionSource.get_by_name("cash"),
                ground=self.ground,
                markup=0.05,
                session=self.session,
            )
            for t in Transaction.get_all():
                t.process()
