# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Module containing all of the sample data factories."""

import datetime
import uuid
from builtins import object

from dateutil.relativedelta import relativedelta
from factory.alchemy import SQLAlchemyModelFactory
from factory.base import Factory
from factory.declarations import Iterator, LazyAttribute, SelfAttribute, Sequence, SubFactory, logger

from sparkmeter.config.configdict import config
from sparkmeter.dashboard.dashboarddomain import DashboardDailyTariffSummary
from sparkmeter.database.types import Choice
from sparkmeter.event.eventdomain import Event, SMSConfigAlert, SMSConfigCommand, SMSConfigMessage, SMSMessage
from sparkmeter.ground.grounddomain import Ground, GroundPrivate
from sparkmeter.meter.meterdomain import (
    Address,
    Customer,
    Meter,
    MeterBilling,
    MeterConfig,
    MeterModels,
    MeterScalars,
    MeterSystemInfo,
    SparkmacNode,
)
from sparkmeter.reading.readingdomain import Reading
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.system.systemdomain import SystemState
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.transaction.transactiondomain import Transaction, TransactionSource, Wallet
from sparkmeter.user.userdomain import User


def make_id_sequence(category, cat2="0"):
    """Create an id sequence from a template."""
    template = "{:0>8}-{:0>4}-{:0>4}-{:0>4}-{{:0>12}}".format(category, cat2, 0, 0)
    return Sequence(lambda n: uuid.UUID(template.format(n)))


def make_sequence(template):
    """Create a sequence from a template."""
    return Sequence(template.format)


def _reset_iterators(factory_cls):
    """Reset any ``Iterator`` declarations on a factory.

    ``reset_sequence`` resets a factory's sequence counter but not its
    ``Iterator`` cursors. An Iterator's position is global state that otherwise
    leaks across tests, making iterator-derived fields (such as the alert
    factory's cycling ``event_type``) non-deterministic under randomized test
    ordering. Resetting them per test pins a deterministic starting position.
    """
    for declaration in factory_cls._meta.declarations.values():
        if isinstance(declaration, Iterator):
            declaration.reset()


class DefaultSubFactory(SubFactory):
    """SubFactory that will first check if a default value exists for this model."""

    def evaluate(self, instance, step, extra):
        """Evaluate the subfactory, reusing the default if it exists."""
        factory = self.get_factory()
        if factory._default_model is None:
            factory._default_model = super(DefaultSubFactory, self).evaluate(instance, step, extra)
        else:
            logger.debug("SubFactory: Reusing default for %s: %s", factory.__name__, factory._default_model)
        return factory._default_model


class BaseFactory(Factory):
    @classmethod
    def setup(cls, session):
        """
        Setup all subclassed factories.

        This reset the sequency numbers,
        """
        for c in cls.__subclasses__():
            c.reset_sequence(1, force=True)
            _reset_iterators(c)
            c.setup(session)


class DomainFactory(SQLAlchemyModelFactory):
    """Abstract Base Factory."""

    _default_model = None

    @classmethod
    def setup(cls, session):
        """
        Setup all subclassed factories.

        This will set the session for the factories,
        reset the sequency numbers,
        and reset the default model.
        """
        for c in cls.__subclasses__():
            c._meta.sqlalchemy_session = session
            c.reset_sequence(1, force=True)
            _reset_iterators(c)
            c._default_model = None
            c.setup(session)

    @classmethod
    def get_default(cls, *args, **kwargs):
        """Get or create the default model for this factory."""
        if cls._default_model is None:
            cls._default_model = cls(*args, **kwargs)
        return cls._default_model


class AddressFactory(DomainFactory):
    """Address Factory."""

    class Meta(object):
        model = Address

    id = make_id_sequence("b")
    street1 = "strëet"
    street2 = "street2"
    city = "city"
    state = "state"
    postalcode = "12345"
    country = "usa"
    coords = "42.5646975,-71.2708356"

    @classmethod
    def _generate(cls, create, attrs):
        create_ground = "ground_id" not in attrs
        address = super(AddressFactory, cls)._generate(create, attrs)
        if create_ground:
            address.ground_id = GroundFactory(address=address).id
        return address


class WalletFactory(DomainFactory):
    """Wallet Factory."""

    class Meta(object):
        model = Wallet

    id = make_id_sequence("a")
    meter_id = None
    wallet_type = Wallet.TYPE_CREDIT
    value = 0
    grid = None


class GroundPrivateFactory(DomainFactory):
    """Ground Private Factory."""

    class Meta(object):
        model = GroundPrivate

    max_capacity = 1000
    secret_key = "aside"


class GroundFactory(DomainFactory):
    """Ground Factory."""

    class Meta(object):
        model = Ground

    id = make_id_sequence("2")
    name = make_sequence("test micrøgrid {0}")
    serial = make_sequence("groundserial{0}")
    address = SubFactory(AddressFactory, ground_id=SelfAttribute("..id"))
    private = SubFactory(GroundPrivateFactory, ground_id=SelfAttribute("..id"))


class SalesAccountFactory(DomainFactory):
    """Sales Account Factory."""

    class Meta(object):
        model = SalesAccount

    id = make_id_sequence("a")
    name = make_sequence("sales åccöünt {0}")
    markup = 0.05
    active = True
    system = False
    ground = DefaultSubFactory(GroundFactory)
    credit_wallet = SubFactory(
        WalletFactory,
        wallet_type=Wallet.TYPE_CREDIT,
        value=0,
        negative_permitted=False,
        sales_account_id=SelfAttribute("..id"),
        grid=SelfAttribute("..ground"),
    )
    debt_wallet = SubFactory(
        WalletFactory,
        wallet_type=Wallet.TYPE_DEBT,
        value=0,
        negative_permitted=False,
        sales_account_id=SelfAttribute("..id"),
        grid=SelfAttribute("..ground"),
    )
    global_account = False


class GlobalSalesAccountFactory(DomainFactory):
    class Meta(object):
        model = SalesAccount

    id = make_id_sequence("a", "1")
    ground = None
    credit_wallet = None
    debt_wallet = None
    global_account = True
    credit_wallet = SubFactory(
        WalletFactory,
        wallet_type=Wallet.TYPE_CREDIT,
        value=0,
        negative_permitted=True,
        sales_account_id=SelfAttribute("..id"),
        grid=None,
    )
    debt_wallet = SubFactory(
        WalletFactory,
        wallet_type=Wallet.TYPE_DEBT,
        value=0,
        negative_permitted=True,
        sales_account_id=SelfAttribute("..id"),
        grid=None,
    )


class CustomerFactory(DomainFactory):
    """Customer Factory."""

    class Meta(object):
        model = Customer

    id = make_id_sequence("c")
    name = "strëet"
    code = make_sequence("customer code {:d}")
    phone_number = make_sequence("+18008{:06d}")
    phone_number_verified = True
    meter_id = None


class TariffFactory(DomainFactory):
    """Tariff Factory."""

    class Meta(object):
        model = Tariff

    id = make_id_sequence("4")
    name = make_sequence("tarïff{:0>2}")
    flat_load_limit = 100
    load_limit_type = Tariff.LOAD_LIMIT_TYPE_FLAT
    flat_price = 10.0
    plan_price = 0.0
    plan_fixed_fee = 0.0
    tariff_type = Tariff.TYPE_FLAT
    tou_enabled = False
    plan_enabled = False
    plan_duration_span = 1
    plan_duration_unit = "m"
    cycle_start_day_of_month = 1
    blockrates = []
    tous = []
    load_limits = []
    daily_energy_limit_enabled = False
    daily_energy_limit_reset_hour = 0
    daily_energy_limit_value = 0


class DashboardSummaryFactory(DomainFactory):
    """DashboardSummary Factory."""

    class Meta(object):
        model = DashboardDailyTariffSummary

    id = make_id_sequence("6")
    tariff = DefaultSubFactory(TariffFactory)
    ground = DefaultSubFactory(GroundFactory)
    date = datetime.datetime(2013, 1, 1, 1, 1, 1)
    transaction_amount = 100
    transaction_count = 100
    kwh_consumed = 100.00
    customer_count = 100


class SparkmacNodeFactory(DomainFactory):
    """SparkmacNode Factory."""

    class Meta(object):
        model = SparkmacNode

    id = make_id_sequence("d")
    static_routes = "[]"
    forwarding = "off"
    routing_enabled = ["custom", "static", "dynamic"]
    flooding_subnets = 0x0
    flooding_macs = []
    ttl = 5
    meter_id = None


class MeterSystemInfoFactory(DomainFactory):
    """MeterSystemInfo Factory."""

    class Meta(object):
        model = MeterSystemInfo

    id = make_id_sequence("e")
    last_config_datetime = datetime.datetime(2013, 1, 1, 1, 1, 1)
    last_energy = 0.0
    last_energy_datetime = datetime.datetime(2013, 1, 1, 1, 1, 1)
    current_state = 1
    firmware = "abc1234"
    bootloader = "def456"
    reading_id = None
    meter_id = None
    current_user_power_limit = None


class MeterBillingFactory(DomainFactory):
    """MeterBilling Factory."""

    class Meta(object):
        model = MeterBilling

    id = make_id_sequence("0", "5")
    last_plan_payment_date = None
    last_plan_expiration_date = None
    last_cycle_start = None
    total_cycle_energy = 0
    is_running_plan = False
    meter_id = None
    tariff = DefaultSubFactory(TariffFactory)
    last_daily_energy_limit_reset_datetime = None
    last_daily_energy_limit_reset_value = None


class MeterConfigFactory(DomainFactory):
    """MeterConfig Factory."""

    class Meta(object):
        model = MeterConfig

    id = make_id_sequence("f")
    hidden = False
    state = 2
    meter_id = None


class MeterScalarsFactory(DomainFactory):
    """Meter Scalars"""

    class Meta(object):
        model = MeterScalars

    id = make_id_sequence("1")
    name = "normal"
    frequency_scalar = 0.01
    voltage_scalar = 0.01
    current_scalar = 0.002
    energy_scalar = 0.00003125
    power_scalar = 2.0
    power_factor_scalar = 0.001


class MeterModelsFactory(DomainFactory):
    """MeterModels Factory."""

    class Meta(object):
        model = MeterModels

    id = make_id_sequence("1")
    enabled = True
    name = "SMXR"
    inrush_limit = 0.0
    continuous_limit = 0.0
    phase_count = 1
    scalars = DefaultSubFactory(MeterScalarsFactory)


class MeterFactory(DomainFactory):
    """Meter Factory."""

    class Meta(object):
        model = Meter

    id = make_id_sequence("1")
    code = make_sequence("{0}")
    serial = make_sequence("SM15R-01-{:0>8X}")
    meter_type = Meter.TYPE_CUSTOMER
    ground = DefaultSubFactory(GroundFactory)
    address = SubFactory(AddressFactory, ground_id=SelfAttribute("..ground.id"))
    customer = SubFactory(CustomerFactory, meter_id=SelfAttribute("..id"))
    sparkmac = SubFactory(SparkmacNodeFactory, meter_id=SelfAttribute("..id"))
    config = SubFactory(MeterConfigFactory, meter_id=SelfAttribute("..id"))
    system_info = SubFactory(MeterSystemInfoFactory, meter_id=SelfAttribute("..id"))
    billing = SubFactory(MeterBillingFactory, meter_id=SelfAttribute("..id"))
    credit_wallet = SubFactory(
        WalletFactory,
        wallet_type=Wallet.TYPE_CREDIT,
        value=0,
        negative_permitted=False,
        meter_id=SelfAttribute("..id"),
        grid=SelfAttribute("..ground"),
    )
    debt_wallet = SubFactory(
        WalletFactory,
        wallet_type=Wallet.TYPE_DEBT,
        value=0,
        negative_permitted=False,
        meter_id=SelfAttribute("..id"),
        grid=SelfAttribute("..ground"),
    )
    plan_wallet = SubFactory(
        WalletFactory,
        wallet_type=Wallet.TYPE_PLAN,
        value=0,
        negative_permitted=False,
        meter_id=SelfAttribute("..id"),
        grid=SelfAttribute("..ground"),
    )
    model = DefaultSubFactory(
        MeterModelsFactory,
        name="SM25R",
        inrush_limit=20.0,
        continuous_limit=20.0,
        phase_count=1,
    )


class TotalizerMeterFactory(MeterFactory):
    """Totalizer Meter Factory."""

    id = make_id_sequence("0", "6")
    code = make_sequence("{0}")
    serial = make_sequence("SM15R-01-1{:0>7X}")
    meter_type = Meter.TYPE_TOTALIZER
    address = SubFactory(AddressFactory, ground_id=SelfAttribute("..ground.id"))
    ground = DefaultSubFactory(GroundFactory)
    customer = None
    sparkmac = SubFactory(SparkmacNodeFactory, meter_id=SelfAttribute("..id"))
    config = SubFactory(MeterConfigFactory)
    system_info = SubFactory(MeterSystemInfoFactory)
    billing = None

    credit_wallet = None
    debt_wallet = None
    plan_wallet = None


class UserFactory(DomainFactory):
    """User Factory."""

    class Meta(object):
        model = User

    id = make_id_sequence("9")
    fs_uniquifier = LazyAttribute(lambda obj: str(obj.id).replace("-", ""))
    email = LazyAttribute(lambda obj: "%s@earthsparkinternational.org" % obj.username)
    password = "pass"
    active = True
    accounts = []  # list[SalesAccount]
    roles = []
    username = make_sequence("testüser-{:0>3}")
    locale = "en_US"
    api_sales_account = None
    account_all_access = False
    ground_all_access = False
    grounds = []  # list[Ground]


class OperatorFactory(UserFactory):
    """Operator User Factory."""


class VendorFactory(UserFactory):
    """Vendor User Factory."""


class ReadingFactory(DomainFactory):
    """Reading Factory."""

    class Meta(object):
        model = Reading
        exclude = ("_meter",)

    id = make_id_sequence("3")
    kilowatt_hours = 1.1
    kilowatt_hours_period = 300
    cost = 1.0
    acct_credit = 2.0
    acct_debt = 0
    meter = SelfAttribute("_meter.code")
    # NOTE: if defining a custom 'meter' value, set _meter=None to disable it from creating another meter.
    _meter = DefaultSubFactory(MeterFactory)
    heartbeat_start = Sequence(
        lambda n: datetime.datetime(2013, 1, 1, 0, 0, 0) + relativedelta(minutes=15 * n)
    )
    heartbeat_end = Sequence(
        lambda n: datetime.datetime(2013, 1, 1, 0, 15, 0) + relativedelta(minutes=15 * n)
    )
    frequency = 60.0
    voltage_min = 120.0
    voltage_max = 120.0
    voltage_avg = 120.0
    current_min = 1.0
    current_max = 1.0
    current_avg = 1.0
    true_power_inst = 1.0
    true_power_avg = 1.0
    apparent_power_avg = 1.0
    power_factor_avg = 1.0
    energy = 1.0
    uptime = 100
    state = 1
    user_power_limit = 12000


class TransactionSourceFactory(DomainFactory):
    """TransactionSource Factory."""

    class Meta(object):
        model = TransactionSource

    id = make_id_sequence("8")
    name = make_sequence("transaction sòurce name {:0>2}")
    monetary = True
    transaction_metadata = None


class TransactionFactory(DomainFactory):
    """Transaction Factory."""

    class Meta(object):
        model = Transaction
        exclude = ("_to_wallet_meter", "_from_wallet_account")

    id = make_id_sequence("7")
    created = datetime.datetime(2013, 1, 1, 1, 1, 1)
    amount = 100.0
    state = Transaction.STATE_PENDING
    acct_type = Choice(code="credit", value="Credit")
    ground = DefaultSubFactory(GroundFactory)  # type: Ground
    user = DefaultSubFactory(OperatorFactory)  # type: User
    source = DefaultSubFactory(TransactionSourceFactory)
    error = None
    origin = Transaction.ORIGIN_USER

    _to_wallet_meter = DefaultSubFactory(MeterFactory)
    to_wallet = SelfAttribute("_to_wallet_meter.credit_wallet")  # type: Wallet

    _from_wallet_account = DefaultSubFactory(SalesAccountFactory)
    from_wallet = SelfAttribute("_from_wallet_account.credit_wallet")  # type: Wallet


class SMSConfigAlertFactory(BaseFactory):
    """SMSConfigAlert Factory."""

    class Meta(object):
        model = SMSConfigAlert

    id = make_id_sequence("0", "1")
    event_type = Iterator(sorted(Event.events), cycle=True)
    template = make_sequence("alert témplate {0}")


class SMSConfigCommandFactory(BaseFactory):
    """SMSConfigCommand Factory."""

    class Meta(object):
        model = SMSConfigCommand

    id = make_id_sequence("0", "2")
    code = make_sequence("CODE{0}")
    template = make_sequence("command témplate {0}")


class SMSConfigMessageFactory(BaseFactory):
    """SMSConfigMessage Factory."""

    class Meta(object):
        model = SMSConfigMessage

    id = make_id_sequence("0", "3")
    message_type = make_sequence("invalid-méssage-type-{0}")
    template = make_sequence("message témplate {0}")


class SMSMessageFactory(DomainFactory):
    """SMSMessage Factory."""

    class Meta(object):
        model = SMSMessage

    id = make_id_sequence("0", "4")
    direction = Iterator([SMSMessage.DIRECTION_IN, SMSMessage.DIRECTION_OUT], cycle=True)
    text = make_sequence("sms méśśáge text {:0>2}")
    timestamp = datetime.datetime(2013, 1, 1, 1, 1, 1)
    phone_number = make_sequence("+123456789")
    processed = False
    event = None
    origin = SMSMessage.ORIGIN_COMMAND
    ground = None


class EventFactory(DomainFactory):
    """Event Factory."""

    class Meta(object):
        model = Event

    id = make_id_sequence("0", "5")
    ground = DefaultSubFactory(GroundFactory)
    timestamp = datetime.datetime(2013, 1, 1, 1, 1, 1)
    event_type = Event.TYPE_METER_CREATED
    object_id = None
    object_table = "meter"
    processed = False
    created_by = DefaultSubFactory(OperatorFactory)  # type: User
    processed_timestamp = None


class SystemStateFactory(DomainFactory):
    """SystemState Factory."""

    class Meta(object):
        model = SystemState

    id = make_id_sequence("1", "0")
    timestamp = Sequence(lambda n: datetime.datetime(2018, 1, 1, 0, 0, 0) + relativedelta(minutes=15 * n))
    action = LazyAttribute(lambda obj: "Changing state to %s" % obj.state)
    system = config.GROUND
    state = SystemState.STATE_RUN
    version = "1.2.3"
