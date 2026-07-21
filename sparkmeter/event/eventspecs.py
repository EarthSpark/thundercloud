# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Event specs."""

import datetime
import logging
import uuid
from builtins import object, str

from flask_babel import lazy_gettext as _

from sparkmeter.config.configdict import config
from sparkmeter.database.types import Choice
from sparkmeter.event.eventkeywords import (
    BooleanKeyword,
    CurrencyKeyword,
    DateTimeKeyword,
    EnergyKeyword,
    StringKeyword,
)

logger = logging.getLogger()
KEYWORD_CUSTOMER_NAME = StringKeyword("customer_name", _("Name of the customer."), _("John Doe"))

KEYWORD_CUSTOMER_CODE = StringKeyword("customer_code", _("Code of the customer."), _("CC1618"))

KEYWORD_CREDITS_BALANCE = CurrencyKeyword("credits_balance", _("Credit balance for the customer."), 10.34)

KEYWORD_DEBT_BALANCE = CurrencyKeyword("debt_balance", _("Debt balance for the customer."), 42.91)

KEYWORD_CURRENT_TARIFF_NAME = StringKeyword(
    "current_tariff_name", _("Name of Tariff used by the meter."), _("ET60")
)


KEYWORD_SERIAL = StringKeyword("serial", _("Meter serial number."), _("SM15R-01-00DDBA11"))


KEYWORD_IS_RUNNING_PLAN = BooleanKeyword(
    "is_running_plan", _("If the tariff used includes a plan, has it been paid? (yes/no)"), True
)

KEYWORD_PLAN_BALANCE = CurrencyKeyword("plan_balance", _("For tariffs with plans, the Plan balance."), 17.26)

KEYWORD_LAST_ENERGY = EnergyKeyword("last_energy", _("Last energy value read for the meter, in kWh."), 8.663)

KEYWORD_OPERATING_MODE = StringKeyword(
    "operating_mode", _("Operating mode of the meter (On/Off/Auto)."), _("Auto")
)

KEYWORD_TOTAL_CYCLE_ENERGY = EnergyKeyword(
    "total_cycle_energy", _("Total amount of energy used since the beginning of the month, in kWh."), 2.804
)

KEYWORD_TRANSACTION_AMOUNT = CurrencyKeyword("amount", _("Amount of the placed transaction."), 25)

KEYWORD_TRANSACTION_VENDOR = StringKeyword(
    "vendor", _("Name of vendor used for the placed transaction."), _("Jane Doe")
)

KEYWORD_TRANSACTION_CREATION_DATETIME = DateTimeKeyword(
    "creation_datetime", _("Time when the transaction was placed."), datetime.datetime(2016, 3, 31, 16, 1, 0)
)

KEYWORD_TRANSACTION_SOURCE = StringKeyword(
    "source", _("Source of the placed transaction (cash/bonus)."), _("cash")
)

KEYWORD_TRANSACTION_STATUS = StringKeyword(
    "status", _("Status of placed transaction (not processed/processed/error)."), _("processed")
)

KEYWORD_LAST_TRANSACTION_AMOUNT = CurrencyKeyword(
    "last_transaction_amount", _("Amount of the last transaction placed for this customer."), 25.00
)

KEYWORD_LAST_TRANSACTION_VENDOR = StringKeyword(
    "last_transaction_vendor",
    _("Name of vendor used for the last transaction placed for this customer."),
    _("Jane Doe"),
)

KEYWORD_LAST_TRANSACTION_CREATION_DATETIME = DateTimeKeyword(
    "last_transaction_creation_datetime",
    _("Time when the last transaction for this customer was placed."),
    datetime.datetime(2016, 3, 31, 16, 1, 0),
)

KEYWORD_LAST_TRANSACTION_SOURCE = StringKeyword(
    "last_transaction_source",
    _("Source of the last transaction placed for this customer (cash/bonus)."),
    _("cash"),
)

KEYWORD_LAST_TRANSACTION_STATUS = StringKeyword(
    "last_transaction_status",
    _("Status of the last transaction placed for this customer (not processed/processed/error)."),
    _("processed"),
)

KEYWORD_GROUND_SERIAL = StringKeyword(
    "ground_serial",
    _("Serial of the ground."),
    _("2Mlp4sbMGQVGIvhIri8K"),
)

KEYWORD_GROUND_NAME = StringKeyword(
    "ground_name",
    _("Name of the ground."),
    _("My Microgrid"),
)

KEYWORD_WALLET_TYPE = StringKeyword(
    "wallet_type",
    _("Name of the wallet."),
    "debt",
)

KEYWORD_WALLET_BALANCE = CurrencyKeyword(
    "wallet_balance",
    _("Total value for the wallet."),
    25.02,
)


class EventSpec(object):
    """Event specification."""

    #: Event type for this specification
    event_type = None

    _event_specs = {}

    def get_event_object(self, event):
        """Get the object from an event."""
        if event.event_type != self.event_type:  # pragma nocoverage
            raise ValueError("Wrong event type")
        return event.object

    @classmethod
    def register(cls, event_spec):
        """Register a new event spec."""
        if event_spec.event_type in cls._event_specs:  # pragma nocoverage
            raise TypeError("EventSpec %r has already been registered" % (event_spec.event_type))
        cls._event_specs[event_spec.event_type] = event_spec()

    @classmethod
    def get_all(cls):
        """Get all event specs."""
        return list(cls._event_specs.values())

    @classmethod
    def get_by_event_type(cls, event_type):
        """Get an event specs given an event type."""
        return cls._event_specs.get(event_type)

    def render(self, obj, template):
        """
        Render a message given an object and a template.

        Rendering means that a message is created by starting with
        a template and substituting all the keywords markers with
        values fetched from the database.
        :param obj: the object to fetch keywords from.
        :param template: the template to render
        :returns: the rendered message.
        """
        locale = config.get_current_locale()

        # 1) Collect the values from the system environment
        env = self.collect_environment(obj)

        # 2) Format values according to current locale
        for keyword in self.keywords:
            if keyword.name in env:
                value = env[keyword.name]
                output = ""
                if value is not None:
                    output = keyword.format(value, locale)
                env[keyword.name] = output

        # 3) Replace placeholders in the template with the formatted values
        text = str(template)
        for key, value in list(env.items()):
            text = text.replace("{" + str(key) + "}", str(value))
        return text

    def maybe_create_alert(self, event):
        """Try to create an SMS alert message for this event, if possible."""
        from sparkmeter.event.eventdomain import SMSMessage

        message = SMSMessage.maybe_create_alert(event)
        if message is not None:
            event.session.add(message)

    def process(self, event):
        """EventSpec hook for meter events."""

    def collect_environment(self, transaction):
        """EventSpec hook for collecting alert keywords."""
        return {}

    def get_customer_for_object(self, obj):
        """Get the customer for an object.

        This is used for events that are tied to a customer, eg, one
        which we can send an SMS message to.
        """

    def to_json(self, event):
        return {
            "id": event.id,
            "created": event.timestamp,
            "status": "processed" if event.processed else "pending",
        }


class MeterEventSpec(EventSpec):
    event_type = None
    object_table = "meter"
    keywords = [
        KEYWORD_CUSTOMER_NAME,
        KEYWORD_CUSTOMER_CODE,
        KEYWORD_CREDITS_BALANCE,
        KEYWORD_DEBT_BALANCE,
        KEYWORD_CURRENT_TARIFF_NAME,
        KEYWORD_SERIAL,
        KEYWORD_IS_RUNNING_PLAN,
        KEYWORD_PLAN_BALANCE,
        KEYWORD_LAST_ENERGY,
        KEYWORD_OPERATING_MODE,
        KEYWORD_TOTAL_CYCLE_ENERGY,
        KEYWORD_LAST_TRANSACTION_AMOUNT,
        KEYWORD_LAST_TRANSACTION_VENDOR,
        KEYWORD_LAST_TRANSACTION_CREATION_DATETIME,
        KEYWORD_LAST_TRANSACTION_SOURCE,
        KEYWORD_LAST_TRANSACTION_STATUS,
    ]

    def collect_environment(self, meter):
        """Collect keyword variables."""
        customer = self.get_customer_for_object(meter)
        env = dict(
            customer_name=customer.name,
            customer_code=customer.code,
            credits_balance=meter.credit_wallet.value,
            debt_balance=meter.debt_wallet.value,
            meter=meter.id,
            current_tariff_name=meter.tariff.name,
            serial=meter.serial,
            is_running_plan=meter.billing.is_running_plan,
            plan_balance=meter.plan_wallet.value,
            last_energy=meter.system_info.last_energy,
            operating_mode=meter.state_text,
            total_cycle_energy=meter.billing.total_cycle_energy,
        )
        transaction = meter.get_last_placed_transaction()
        if transaction is not None:
            env.update(
                dict(
                    last_transaction_amount=transaction.amount,
                    last_transaction_vendor=transaction.user.username,
                    last_transaction_creation_datetime=transaction.created,
                    last_transaction_source=transaction.source.name,
                    last_transaction_status=transaction.status_text,
                )
            )
        return env

    def get_customer_for_object(self, meter):
        """Get a customer for this event."""
        return meter.customer

    def process(self, event):
        """EventSpec hook for transaction events."""
        EventSpec.process(self, event)
        self.maybe_create_alert(event)


class TransactionEventSpec(EventSpec):
    event_type = None
    object_table = "transactions"
    keywords = [
        KEYWORD_CUSTOMER_NAME,
        KEYWORD_CUSTOMER_CODE,
        KEYWORD_CREDITS_BALANCE,
        KEYWORD_DEBT_BALANCE,
        KEYWORD_CURRENT_TARIFF_NAME,
        KEYWORD_SERIAL,
        KEYWORD_IS_RUNNING_PLAN,
        KEYWORD_PLAN_BALANCE,
        KEYWORD_LAST_ENERGY,
        KEYWORD_OPERATING_MODE,
        KEYWORD_TOTAL_CYCLE_ENERGY,
        KEYWORD_TRANSACTION_AMOUNT,
        KEYWORD_TRANSACTION_VENDOR,
        KEYWORD_TRANSACTION_CREATION_DATETIME,
        KEYWORD_TRANSACTION_SOURCE,
        KEYWORD_TRANSACTION_STATUS,
    ]

    def collect_environment(self, transaction):
        """Collect keyword variables."""
        customer = self.get_customer_for_object(transaction)
        meter = customer.meter
        return dict(
            customer_name=customer.name,
            customer_code=customer.code,
            credits_balance=meter.credit_wallet.value,
            debt_balance=meter.debt_wallet.value,
            meter=meter.id,
            current_tariff_name=meter.tariff.name,
            serial=meter.serial,
            is_running_plan=meter.billing.is_running_plan,
            plan_balance=meter.plan_wallet.value,
            last_energy=meter.system_info.last_energy,
            operating_mode=meter.state_text,
            total_cycle_energy=meter.billing.total_cycle_energy,
            amount=transaction.amount,
            vendor=transaction.user.username,
            creation_datetime=transaction.created,
            source=transaction.source.name,
            status=transaction.status_text,
        )

    def get_customer_for_object(self, transaction):
        """Get a customer for this event."""
        meter = transaction.to_wallet.meter
        return meter.customer

    def process(self, event):
        """EventSpec hook for transaction events."""
        EventSpec.process(self, event)
        self.maybe_create_alert(event)


class GroundEventSpec(EventSpec):
    """A base class for events tied to a Ground."""

    event_type = None
    object_table = "ground"


class ConfigParameterSpec(EventSpec):
    """A base class for events tied to a Config Parameter."""

    event_type = None
    object_table = "config_parameter"


class CustomerWalletEventSpec(EventSpec):
    event_type = None
    object_table = "wallet"
    keywords = [
        KEYWORD_CUSTOMER_NAME,
        KEYWORD_CUSTOMER_CODE,
        KEYWORD_CREDITS_BALANCE,
        KEYWORD_DEBT_BALANCE,
        KEYWORD_CURRENT_TARIFF_NAME,
        KEYWORD_SERIAL,
        KEYWORD_IS_RUNNING_PLAN,
        KEYWORD_PLAN_BALANCE,
        KEYWORD_LAST_ENERGY,
        KEYWORD_OPERATING_MODE,
        KEYWORD_TOTAL_CYCLE_ENERGY,
        KEYWORD_WALLET_BALANCE,
        KEYWORD_WALLET_TYPE,
    ]

    def collect_environment(self, wallet):
        """Collect keyword variables."""
        customer = self.get_customer_for_object(wallet)
        meter = customer.meter
        return dict(
            customer_name=customer.name,
            customer_code=customer.code,
            credits_balance=meter.credit_wallet.value,
            debt_balance=meter.debt_wallet.value,
            meter=meter.id,
            current_tariff_name=meter.tariff.name,
            serial=meter.serial,
            is_running_plan=meter.billing.is_running_plan,
            plan_balance=meter.plan_wallet.value,
            last_energy=meter.system_info.last_energy,
            operating_mode=meter.state_text,
            total_cycle_energy=meter.billing.total_cycle_energy,
            wallet_type=wallet.wallet_type,
            wallet_balance=wallet.value,
        )

    def get_customer_for_object(self, wallet):
        """Get a customer for this event."""
        meter = wallet.meter
        return meter.customer

    def process(self, event):
        """EventSpec hook for transaction events."""
        EventSpec.process(self, event)
        self.maybe_create_alert(event)

    def to_json(self, event):
        wallet = event.object
        customer = self.get_customer_for_object(wallet)
        base_json = EventSpec.to_json(self, event)
        base_json["customer"] = customer.id
        base_json["wallet"] = wallet.wallet_type
        return base_json


@EventSpec.register
class CustomerCreditTransactionProcessedEvent(TransactionEventSpec):
    """A transaction has been placed from a customer."""

    #: Event.TYPE_CUSTOMER_CREDIT_TRANSACTION
    event_type = "customer-credit-transaction-processed"


@EventSpec.register
class CustomerCreditBonusTransactionProcessedEvent(TransactionEventSpec):
    """A bonus transaction has been placed from a customer."""

    #: Event.TYPE_CUSTOMER_CREDIT_BONUS_TRANSACTION
    event_type = "customer-credit-bonus-transaction-processed"


@EventSpec.register
class ReversalTransactionProcessedEvent(TransactionEventSpec):
    """A reversal transaction has been placed."""

    #: Event.TYPE_REVERSAL_TRANSACTION
    event_type = "reversal-transaction-processed"


@EventSpec.register
class MeterCreatedEvent(MeterEventSpec):
    """A has been created."""

    #: Event.TYPE_METER_CREATED
    event_type = "meter-created"

    def process(self, event):
        MeterEventSpec.process(self, event)
        meter = event.object
        from sparkmeter.metering.api import register_meter

        register_meter(
            node_id=int(meter.code),
            node_type=str(meter.product_code),
            mac=int(meter.code),
        )
        meter.send_set_config_unconditionally()


@EventSpec.register
class CustomerLowBalanceEvent(MeterEventSpec):
    """A customer is almost running out of energy."""

    #: Event.TYPE_CUSTOMER_LOW_BALANCE
    event_type = "customer-low-balance"


@EventSpec.register
class MeterStateChangedEvent(MeterEventSpec):
    """The operational state of a meter changed.

    This is being created when:
    - set-operating-mode API is called
    - Power button is toggled in the UI
    - Reset meter button is pushed in the UI
    """

    #: Event.TYPE_METER_STATE_CHANGED
    event_type = "meter-state-changed"

    def process(self, event):
        MeterEventSpec.process(self, event)
        meter = event.object
        if meter.is_customer_meter():
            meter.send_set_config_unconditionally()


@EventSpec.register
class MeterTariffChangedEvent(MeterEventSpec):
    """The tariff of a meter changed."""

    #: Event.TYPE_METER_TARIFF_CHANGED
    event_type = "meter-tariff-changed"

    def process(self, event):
        MeterEventSpec.process(self, event)
        meter = event.object
        if meter.is_customer_meter():
            # FIXME: Should base this on meter_system_info
            meter.send_set_config_unconditionally()


@EventSpec.register
class TariffPowerLimitChangedEvent(EventSpec):
    """The power limit of a tariff has changed."""

    #: Event.TYPE_TARIFF_POWER_LIMIT_CHANGED
    event_type = "tariff-power-limit-changed"
    object_table = "tariff"

    def process(self, event):
        EventSpec.process(self, event)
        tariff = event.object
        tariff.update_meters()


@EventSpec.register
class GroundOverrideMeterStateEnabledEvent(GroundEventSpec):
    """Ground override meter state has been enabled."""

    #: Event.TYPE_GROUND_OVERRIDE_METER_STATE_ENABLED
    event_type = "ground-override-meter-state-enabled"

    def process(self, event):
        EventSpec.process(self, event)
        ground = event.object
        ground.private.set_override_meter_state(True)


@EventSpec.register
class GroundOverrideMeterStateDisabledEvent(GroundEventSpec):
    """Ground override meter state has been disabled."""

    #: Event.TYPE_GROUND_OVERRIDE_METER_STATE_DISABLED
    event_type = "ground-override-meter-state-disabled"

    def process(self, event):
        EventSpec.process(self, event)
        ground = event.object
        ground.private.set_override_meter_state(False)


@EventSpec.register
class ConfigParameterChanged(ConfigParameterSpec):
    """The value of a configuration parameter has changed."""

    #: Event.TYPE_CONFIG_PARAMETER_CHANGED
    event_type = "config-parameter-changed"

    def update_meters(self):
        """Instruct all customer meters to update if necessary"""
        from sparkmeter.meter.meterdomain import Meter

        for meter in Meter.get_all_customer_meters():
            meter.send_set_config_based_on_system_info()

    def process(self, event):
        EventSpec.process(self, event)
        config = event.object
        if config.name == "nominal-voltage":
            self.update_meters()


@EventSpec.register
class CustomerWalletZeroRequestedEvent(CustomerWalletEventSpec):
    """A request to zero a customer wallet has been submitted."""

    #: Event.TYPE_CUSTOMER_WALLET_ZERO_REQUESTED
    event_type = "customer-wallet-zero-requested"

    def zero_balance(self, wallet, user, session):
        """Zero the balance of the wallet.

        :param wallet: The wallet to zero.
        :param user: The user that initiated the zeroing request.
        :param session: The database session to use.
        :returns: None
        """
        from sparkmeter.controller import process_transaction
        from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
        from sparkmeter.transaction.transactiondomain import Transaction, TransactionSource

        sales_account = SalesAccount.get_system()
        sales_account.check_can_sell_from(user)
        from_wallet = sales_account.get_wallet(wallet.wallet_type) or sales_account.credit_wallet
        now = datetime.datetime.utcnow()
        transaction = Transaction(
            id=uuid.uuid4(),
            amount=-wallet.value,
            ground=wallet.grid,
            user=user,
            acct_type=Choice(code=from_wallet.wallet_type, value=from_wallet.wallet_type),
            source=TransactionSource.get_by_name(TransactionSource.BONUS),
            from_wallet=from_wallet,
            to_wallet=wallet,
            origin=Transaction.ORIGIN_ZEROING,
            state=Transaction.STATE_PENDING,
            created=now,
        )
        session.add(transaction)
        session.commit()
        process_transaction(transaction.id)

    def process(self, event):
        """Process the wallet zeroing event."""
        CustomerWalletEventSpec.process(self, event)
        wallet = event.object
        self.zero_balance(wallet, event.created_by, event.session)
