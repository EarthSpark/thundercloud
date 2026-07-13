# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Event domain."""

import collections
import datetime
import logging
import operator
import re
import uuid
from builtins import object, str

from flask_babel import lazy_gettext as _
from sqlalchemy import and_, case, literal_column, or_, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from sqlalchemy.sql.expression import func, null
from sqlalchemy.sql.schema import Column, ForeignKey
from sqlalchemy.sql.sqltypes import Boolean, DateTime, String

from sparkmeter.database.columns import MutableJSONDict
from sparkmeter.database.sync import SYNC_CHANNEL_EVENT, SYNC_GROUP_GROUND, syncchannel
from sparkmeter.database.tables import get_class_by_tablename, get_table_by_name
from sparkmeter.database.types import UUIDType
from sparkmeter.event.eventspecs import EventSpec
from sparkmeter.exceptions import IncomingMessageReplyError, InvalidCommandCode
from sparkmeter.models import BaseDomain
from sparkmeter.snapshot.snapshotdomain import Snapshot
from sparkmeter.user.userutils import get_current_user

logger = logging.getLogger(__name__)

EventTypeInfo = collections.namedtuple("EventTypeInfo", "label object_type")
MessageTypeInfo = collections.namedtuple("MessageTypeInfo", "label default description")


@syncchannel(SYNC_CHANNEL_EVENT)
class Event(BaseDomain):
    """Event.

    Collection of something that happened, such as an error,
    a meter balance out, meter went off etc.
    """

    __tablename__ = "event"

    #: A customer credit cash transaction has been processed
    TYPE_CUSTOMER_CREDIT_TRANSACTION = "customer-credit-transaction-processed"

    #: A customer credit bonus transaction has been processed
    TYPE_CUSTOMER_CREDIT_BONUS_TRANSACTION = "customer-credit-bonus-transaction-processed"

    #: A transaction has been reversed
    TYPE_REVERSAL_TRANSACTION = "reversal-transaction-processed"

    #: A customer is low on balance
    TYPE_CUSTOMER_LOW_BALANCE = "customer-low-balance"

    #: A new meter has been created
    TYPE_METER_CREATED = "meter-created"

    #: The state of a meter changed
    TYPE_METER_STATE_CHANGED = "meter-state-changed"

    #: The tariff of a meter changed
    TYPE_METER_TARIFF_CHANGED = "meter-tariff-changed"

    #: The power limit of a tariff changed
    TYPE_TARIFF_POWER_LIMIT_CHANGED = "tariff-power-limit-changed"

    #: Ground override meter state has been enabled
    TYPE_GROUND_OVERRIDE_METER_STATE_ENABLED = "ground-override-meter-state-enabled"

    #: Ground override meter state has been disabled
    TYPE_GROUND_OVERRIDE_METER_STATE_DISABLED = "ground-override-meter-state-disabled"

    #: Configuration parameter changed
    TYPE_CONFIG_PARAMETER_CHANGED = "config-parameter-changed"

    #: A customer wallet zero request has been emitted
    TYPE_CUSTOMER_WALLET_ZERO_REQUESTED = "customer-wallet-zero-requested"

    #: ID of ground this address belongs to, NULL for global events like tariff changes
    ground_id = Column(UUIDType(binary=False), ForeignKey("ground.id"), nullable=True)

    #: Event timestamp
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    #: Event type/category
    event_type = Column(String, nullable=False)

    #: Event object triggering the event (id)
    object_id = Column(UUIDType(binary=False))

    #: Event object type (table)
    object_table = Column(String)

    #: If this event has been processed, e.g. an SMS alert has been sent
    processed = Column(Boolean, default=False)

    #: User which has most recently updated the parameter
    created_by_id = Column(ForeignKey("user.id"), nullable=True)

    #: Snapshot for the object data
    snapshot_id = Column(ForeignKey("snapshot.id"), nullable=True)

    #: When the event was processed, in UTC
    processed_timestamp = Column(DateTime, nullable=True)

    #: Reference to the user that created the event
    created_by = relationship("User")

    #: Reference to the ground
    ground = relationship("Ground")  # type: Ground

    #: Reference to the snapshot
    snapshot = relationship("Snapshot")  # type: Snapshot

    #: List of events and description and argument type
    events = {
        TYPE_CUSTOMER_CREDIT_TRANSACTION: EventTypeInfo(_("Successful cash payment"), "transactions"),
        TYPE_CUSTOMER_CREDIT_BONUS_TRANSACTION: EventTypeInfo(_("Successful bonus payment"), "transactions"),
        TYPE_REVERSAL_TRANSACTION: EventTypeInfo(_("Payment reversed"), "transactions"),
        TYPE_CUSTOMER_LOW_BALANCE: EventTypeInfo(_("Low balance"), "meter"),
        TYPE_METER_CREATED: EventTypeInfo(_("Meter created"), "meter"),
        TYPE_METER_STATE_CHANGED: EventTypeInfo(_("Meter state changed"), "meter"),
        TYPE_METER_TARIFF_CHANGED: EventTypeInfo(_("Meter tariff changed"), "meter"),
        TYPE_TARIFF_POWER_LIMIT_CHANGED: EventTypeInfo(_("Tariff power limit changed"), "tariff"),
        TYPE_GROUND_OVERRIDE_METER_STATE_ENABLED: EventTypeInfo(
            ("Ground meter state override enabled"), "ground"
        ),
        TYPE_GROUND_OVERRIDE_METER_STATE_DISABLED: EventTypeInfo(
            _("Ground meter state override disabled"), "ground"
        ),
        TYPE_CONFIG_PARAMETER_CHANGED: EventTypeInfo(_("Config parameter changed"), "config_parameter"),
        TYPE_CUSTOMER_WALLET_ZERO_REQUESTED: EventTypeInfo(
            _("Customer wallet zero request received"), "wallet"
        ),
    }

    @classmethod
    def sync_init(cls, group):
        """Initialize sync configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_GROUND)

        if group.is_cloud():
            # FIXME: Use SQLAlchemy syntax
            group.set_subselect_router(
                "(c.external_id IN ("
                "SELECT serial FROM ground WHERE id = cast(:GROUND_ID as uuid)) OR "
                "cast(:GROUND_ID as uuid) IS NULL)"
            )

    @classmethod
    def create(cls, event_type, obj):
        """Create a new event."""
        event_info = cls.events.get(event_type)
        if event_info is None:
            raise ValueError("Invalid event_type: %s" % (event_type,))

        object_type = get_class_by_tablename(event_info.object_type)
        if not isinstance(obj, object_type):
            raise TypeError("obj must be a %s, not %s" % (object_type.__name__, type(obj).__name__))

        if event_info.object_type in ["meter", "transactions"]:
            ground = obj.ground
        elif event_info.object_type == "ground":
            ground = obj
        else:
            ground = None
        event = cls(event_type=event_type, ground=ground)
        event.created_by = get_current_user()
        event.object = obj
        if event_info.object_type == "meter":
            snapshot = Snapshot.get_or_create_meter_snapshot(meter_id=obj.id)
        elif event_info.object_type == "ground":
            snapshot = Snapshot.get_or_create_ground_snapshot(obj)
        elif event_info.object_type == "tariff":
            snapshot = Snapshot.get_or_create_tariff_snapshot(obj)
        elif event_info.object_type == "wallet":
            if obj.meter_id:
                snapshot = Snapshot.get_or_create_meter_snapshot(meter_id=obj.meter_id)
            else:  # pragma: nocover
                # This is `nocover` because we don't yet have a wallet event that's not attached to a meter
                snapshot = Snapshot.get_or_create_empty_snapshot()
        else:
            snapshot = Snapshot.get_or_create_empty_snapshot()
        event.snapshot = snapshot
        logger.info("Created a %s event", event_type)
        return event

    @classmethod
    def get_unprocessed(cls):
        """Get a list of unprocessed events.

        Get a list of events that have not yet been processed.
        """
        return cls.query.filter_by(processed=False)

    @property
    def object(self):
        """Get an event object."""
        object_type = get_class_by_tablename(self.object_table)
        return object_type.query.get(self.object_id)

    @object.setter
    def object(self, value):
        """Update an event object."""
        self.object_id = value.id
        self.object_table = value.__tablename__

    @property
    def spec(self):
        """Get the spec associated with this event."""
        return EventSpec.get_by_event_type(self.event_type)

    def process(self):
        """Process an event.

        Delegate to the EventSpec for this even to run event-type specific
        hooks, like processing an sms or sending state to a meter.
        """
        self.spec.process(self)
        self.processed = True
        self.processed_timestamp = datetime.datetime.utcnow()

    def render(self, template):
        """
        Render a message given a template.

        Rendering means that a message is created by starting with
        a template and substituting all the keywords markers with
        values fetched from the database.
        :param template: the template to render
        :returns: the rendered message.
        """
        obj = self.spec.get_event_object(self)
        return self.spec.render(obj, template)

    def get_customer_phone_number(self):
        """
        Get customer phone number for this event.
        :returns: the phone number or None
        """
        customer = self.spec.get_customer_for_object(self.object)
        if customer is not None and customer.phone_number is not None:
            return customer.phone_number

    @classmethod
    def get_last_event_by(cls, event_type, obj):
        """
        Get the last triggered event given an event_type and an object.
        :param event_type: the event type
        :param obj: an ORM object instance
        :returns: the last event for the event_type and obj
        """
        return (
            cls.query.filter(cls.object_id == obj.id)
            .filter(cls.object_table == obj.__tablename__)
            .filter_by(event_type=event_type)
            .order_by(cls.timestamp.desc())
            .limit(1)
            .scalar()
        )

    def get_info(self):
        """
        Get the type information for this event.
        :returns: The EventTypeInfo tuple
        """
        return Event.events[self.event_type]

    def to_json(self):
        """
        Get a user-friendly JSON-serializable dict of the event.
        :returns: The evnet dict.
        """
        return self.spec.to_json(self)


@syncchannel(SYNC_CHANNEL_EVENT)
class SMSConfig(BaseDomain):
    """
    SMS Configuration.
    """

    __tablename__ = "sms_config"

    #: Dictionary of SMS config commands, indexed using code
    commands = Column(MutableJSONDict, default={})

    #: Dictionary of SMS config alerts, indexed using event_type
    alerts = Column(MutableJSONDict, default={})

    #: Dictionary of SMS config messages, indexed using message_type
    messages = Column(MutableJSONDict, default={})

    def update(self, name, key, values):
        """Update a configuration value
        :param name: name to update, commands/alerts or messages
        :param key: index
        :param values: values to set
        """
        # This is a little bit more complicated than it should be since
        # objects are indexed by command/alert/message name and not ID.
        # FIXME: Evaluate if we should indexed by ID instead in the future,
        #        that will require a database migration script though.
        objects = getattr(self, name) or {}
        object_id = values.get("id")

        # Delete old object(s) that has the same id, make a copy of
        # the dictionary items (which is required by python 3) to
        # avoid corrupting it as we iterate over it.
        for name, object_ in list(objects.items()):
            if object_.get("id") == object_id:
                del objects[name]

        # Insert the new values by the new key
        objects.setdefault(key, {}).update(values)
        setattr(self, name, objects)


class SMSJSONObject(object):
    """Helper class for JSON SMS config object."""

    config_attribute = None
    config_key = None

    @classmethod
    def get_config(cls):
        """Get the config singleton."""
        return SMSConfig.query.one()

    @classmethod
    def get_objects(cls):
        """Get all raw JSON objects."""
        config = cls.get_config()
        return getattr(config, cls.config_attribute)

    @classmethod
    def get_one_or_create(cls, session=None, **kwargs):
        """Compat wrapper to get or create an object."""
        objects = cls.get_objects()
        key = kwargs.get(cls.config_key)
        values = objects.get(key, kwargs)
        return cls(**values)

    @classmethod
    def get_all(cls):
        """Get all objects, in a sorted order."""
        for key, values in sorted(cls.get_objects().items()):
            yield cls(**values)

    @classmethod
    def get_by_id(cls, object_id):
        """Get an object by id."""
        for obj in cls.get_all():
            if obj.id == str(object_id):
                return obj

    @classmethod
    def get_active(cls):
        """Get all active objects."""
        return sorted([obj for obj in cls.get_all() if obj.active], key=operator.attrgetter(cls.config_key))

    def save(self):
        """Save the object.
        :note: you need to add the sms config to the session for this to be saved.
        :returns: the sms config.
        """
        config = self.get_config()
        d = self.as_dict()
        key = d[self.config_key]
        config.update(self.config_attribute, key, d)
        return config


class SMSConfigCommand(SMSJSONObject):
    """A two-way SMS command like BAL to retrive balance."""

    DEFAULT_COMMANDS = {
        "CHECK": _("Thank you! This phone number has been added to {customer_name} in SparkMeter."),
    }

    config_attribute = "commands"
    config_key = "code"

    #: Regexp used to match messages, strips all leading and trailing white space
    #: around the command code
    MATCH_RE = r"(^|\s+)%s($|\s+)"

    def __init__(self, id=None, active=True, code=None, template=None):
        if id is None:
            id = uuid.uuid4()
        self.id = id
        self.active = active
        self.code = code
        self.template = template

    def as_dict(self):
        """Serialize as dictionary."""
        return dict(id=self.id, active=self.active, code=self.code, template=self.template)

    @classmethod
    def parse_message(cls, message):
        """Parse a message and return the command for it.
        :raises InvalidCommandCode: if no command could be found in the message
        :returns: a command message.
        """
        for command in cls.get_active():
            if command.matches(message.text):
                return command

        raise InvalidCommandCode()

    def matches(self, text):
        """Checks if a command is used in a text.

        :returns: True if a command code was found, otherwise False.
        """
        code_regexp = self.MATCH_RE % (re.escape(self.code.lower()),)
        return bool(re.match(code_regexp, text.lower()))

    def render_text(self, customer):
        """Render the text for this config message.

        :param customer: customer we're rendering for.
        :returns: the rendered text message.
        """
        # FIXME: We are currently reusing the low-balance event keywords
        #        for command templates, this will change in the future.
        spec = EventSpec.get_by_event_type(Event.TYPE_CUSTOMER_LOW_BALANCE)
        return spec.render(customer.meter, self.template)


class SMSConfigAlert(SMSJSONObject):
    """An alert, tied to an event that will be sent to an end-user."""

    config_attribute = "alerts"
    config_key = "event_type"

    def __init__(self, id=None, active=True, event_type=None, template=None):
        if id is None:
            id = uuid.uuid4()
        self.id = id
        self.active = active
        self.event_type = event_type
        self.template = template

    def as_dict(self):
        """Serialize as dictionary."""
        return dict(id=self.id, active=self.active, event_type=self.event_type, template=self.template)

    @classmethod
    def get_by_event_type(cls, event_type):
        """
        Get an alert given an event type
        :param event_type: the event type.
        :returns: an alert or None if not configured
        """
        d = cls.get_objects().get(event_type)
        if d is not None and d["active"]:
            return cls(**d)


class SMSConfigMessage(SMSJSONObject):
    """An system message, like no such number."""

    #: Phone number if not recognized, sent when the phone number is not in the system.
    TYPE_NO_SUCH_NUMBER = "no-such-number"

    #: Sent if the code of an inbound message is invalid
    TYPE_WRONG_CODE = "wrong-code"

    #: If this number has not yet been verified with a CHECK command
    TYPE_VERIFY_NUMBER = "verify-number"

    #: List of command and description
    messages = {
        TYPE_NO_SUCH_NUMBER: MessageTypeInfo(
            _("No such number"),
            _("This phone number is not recognized by SparkMeter."),
            _(
                "This message is sent back if the phone number of an "
                "inbound message is not recognized.\n"
                "The message will appear to the recipient exactly as "
                "typed (no keywords used)."
            ),
        ),
        TYPE_WRONG_CODE: MessageTypeInfo(
            _("Wrong code"),
            _("This SMS code is not recognized by SparkMeter."),
            _(
                "This message is sent back if the code in an inbound message "
                "is not recognized.\n"
                "The message will appear to the recipient exactly as "
                "typed (no keywords used)."
            ),
        ),
        TYPE_VERIFY_NUMBER: MessageTypeInfo(
            _("Verify number"),
            _(
                "Send back CHECK to validate this phone number. "
                "This will allow you to receive alerts from SparkMeter."
            ),
            _(
                "This message is sent when a phone number is added to the system. "
                "Customers must reply to this message with code CHECK and "
                "should be instructed to do so in this message is not recognized.\n"
                "The message will appear to the recipient exactly as "
                "typed (no keywords used)."
            ),
        ),
    }
    config_attribute = "messages"
    config_key = "message_type"

    def __init__(self, id=None, active=True, message_type=None, template=None):
        if id is None:
            id = uuid.uuid4()
        self.id = id
        self.active = active
        self.message_type = message_type
        self.template = template

    def as_dict(self):
        """Serialize as dictionary."""
        return dict(id=self.id, active=self.active, message_type=self.message_type, template=self.template)

    @classmethod
    def get_by_message_type(cls, message_type):
        """Get a config message by a type

        :param message_type: the message_type
        :returns: the config message for the type
        """
        d = cls.get_objects().get(message_type)
        if d is not None:
            return cls(**d)

    def create(self, phone_number, in_reply_to=None):
        """Create a new config reply

        :param phone_number: the phone number to reply to
        :param in_reply_to: the message we're replying to
        :returns: the newly created message.
        """
        message = SMSMessage.create_outgoing(
            in_reply_to=in_reply_to,
            phone_number=phone_number,
            text=self.template,
        )
        message.set_config_message(self)
        return message


@syncchannel(SYNC_CHANNEL_EVENT)
class SMSMessage(BaseDomain):
    """An incoming or outgoing SMS message."""

    __tablename__ = "sms_message"

    #: An incoming SMS messages
    DIRECTION_IN = "in"

    #: An outgoing SMS message
    DIRECTION_OUT = "out"

    #: The origin is unrecognized, (unrecognized phone number or core)
    ORIGIN_UNKNOWN = "unknown"

    #: This is message originates from a command, it's either a customer sending a
    #: reply or a the system replying to one.
    ORIGIN_COMMAND = "command"

    #: This message originates from an alert, e.g. 'low balance'
    ORIGIN_ALERT = "alert"

    #: This message originates from the system, e.g. verify a phone number
    ORIGIN_SYSTEM = "system"

    #: For outgoing SMS messages, the receiver
    #: For incoming SMS messages, the sender
    phone_number = Column(String, nullable=False)

    #: Content of the SMS message, usually 160 characters ASCII, 140 latin-1 and 80 Unicode
    text = Column(String, nullable=False)

    #: For outgoing SMS messages, when the message was sent
    #: For incoming SMS messages, when the message was received
    timestamp = Column(DateTime)

    #: Direction, either DIRECTION_IN or DIRECTION_OUT
    direction = Column(String, nullable=False)

    #: Origin of the message, e.g, what entity created this message
    origin = Column(String, nullable=False, default=ORIGIN_UNKNOWN)

    #: For outgoing SMS messages, if it has been processed/delivered to the SMS gateway
    processed = Column(Boolean, default=False)

    #: An optional link to the event that generated this SMS message
    event_id = Column(UUIDType(binary=False), ForeignKey("event.id"))

    #: A reference to an ID in another system
    external_id = Column(String)

    #: For replies, a reference to the message that is being replied to
    in_reply_to_id = Column(UUIDType(binary=False), ForeignKey("sms_message.id"))

    #: The event type, if this message originates from an alert
    config_event_type = Column(String)

    #: The command code, if this message originates from a command
    config_command_code = Column(String)

    #: The message type, if this message originates from a system message
    config_message_type = Column(String)

    #: The ground this message belongs to
    ground_id = Column(UUIDType(binary=False), ForeignKey("ground.id"), nullable=True)

    #: a reference to the event for this message
    event = relationship("Event", foreign_keys=[event_id])

    #: a reference to the message we're replying to
    in_reply_to = relationship("SMSMessage", uselist=False, remote_side=[in_reply_to_id])

    #: The customers with the phone number of this message, if any
    customers = relationship(
        "Customer",
        load_on_pending=True,
        primaryjoin="foreign(Customer.phone_number) == SMSMessage.phone_number",
    )

    #: The ground this event is created on
    ground = relationship("Ground")  # type: Ground

    @classmethod
    def sync_init(cls, group):
        """Initialize sync configuration for the this table."""
        group.set_conflict_winner(SYNC_GROUP_GROUND)
        if group.is_cloud():
            # FIXME: Use SQLAlchemy syntax
            group.set_subselect_router(
                "(c.external_id IN ("
                "SELECT serial FROM ground WHERE id = cast(:GROUND_ID as uuid)) OR "
                "cast(:GROUND_ID as uuid) IS NULL)"
            )

    @classmethod
    def create_outgoing(cls, phone_number, text, event=None, ground=None, in_reply_to=None):
        """Create an outgoing SMS message.

        :param phone_number: phone number to send the message to
        :type phone_number: str
        :param text: text of the message
        :type text: str
        :param event: event or None
        :type event: Event | None
        :param ground: ground or None
        :type ground: Ground | None
        :param in_reply_to: the message this replies to, or None
        :type in_reply_to: SMSMessage | None
        :returns: the newly created message.
        :rtype: SMSMessage
        """
        return cls(
            direction=cls.DIRECTION_OUT,
            event=event,
            ground=ground,
            in_reply_to=in_reply_to,
            phone_number=phone_number,
            timestamp=datetime.datetime.utcnow(),
            text=text,
        )

    @classmethod
    def get_outgoing(cls, message_ids=None):
        """
        Get a list of unprocessed outgoing messages.

        If message_ids is provided, filter by a them.
        :param message_ids: sequence of message ids (UUID)
        :returns: sequence of messages
        """
        query = cls.query.filter_by(direction=cls.DIRECTION_OUT, processed=False).filter(
            cls.event_id != null()
        )
        if message_ids is not None:
            query = query.filter(cls.id.in_(message_ids))
        return query

    @classmethod
    def get_by_external_id(cls, external_id):
        """Get a message given an external_id."""
        return cls.query.filter_by(external_id=external_id).scalar()

    @classmethod
    def get_messages_view(
        cls,
        meter=None,
        ground=None,
        user=None,
        query_string="",
        order="timestamp",
        ascending=False,
        offset=None,
        limit=None,
    ):
        """Get a set of messages.

        This will be used to display the list of messages for a whole system or for a
        specific meter. It will return a list of dictionaries instead of SMSMessage object
        due to performance reasons. It's suitable for putting into jsonify() and display in
        the interface.

        By default the results will be orded by message timestamp descending.

        :param meter: restrict the messages to a meter or ``None``
        :type meter: sparkmeter.meter.meterdomain.Meter
        :param ground: restrict the sales accounts to a ground or ``None``
        :type ground: sparkmeter.ground.grounddomain.Ground
        :param user: restrict the sales accounts to a user or ``None``
        :type user: sparkmeter.user.userdomain.User
        :returns: messages query
        :rtype: sqlalchemy.query.Query
        """
        customer_t = get_table_by_name("customer")
        meter_t = get_table_by_name("meter")
        ground_t = get_table_by_name("ground")

        # Create a temporary "SMS Type" field that corresponds to the "Type" field in the messages view
        # Build the whens list and unpack as positional args (SQLAlchemy 2.0 syntax)
        sms_type_whens = [
            (cls.config_command_code != null(), cls.config_command_code),
            (cls.config_message_type != null(), "System"),
        ] + [
            (cls.config_event_type == event_type, str(event_type_info.label))
            for event_type, event_type_info in Event.events.items()
        ]
        sms_type = case(*sms_type_whens, else_="N/A")

        # Create a temporary "Processed Fmt" field that corresponds to the formatted processed state
        processed_fmt = case(
            (cls.processed.is_(True), "Yes"),
            (cls.processed.is_(False), "No"),
        )

        columns = [
            cls.timestamp.label("timestamp"),
            cls.direction.label("direction"),
            customer_t.c.name.label("customer_name"),
            cls.phone_number.label("phone_number"),
            cls.text.label("text"),
            cls.processed.label("processed"),
            cls.origin.label("origin"),
            cls.config_event_type.label("event_type"),
            cls.config_command_code.label("code"),
            cls.config_message_type.label("message_type"),
            ground_t.c.name.label("ground_name"),
            ground_t.c.serial.label("ground_serial"),
            func.count(cls.id).over().label("total"),
            sms_type.label("sms_type"),
            processed_fmt.label("processed_fmt"),
        ]
        joins = (
            cls.__table__.outerjoin(ground_t, ground_t.c.id == cls.ground_id)
            .outerjoin(Event, Event.id == cls.event_id)
            .outerjoin(customer_t, customer_t.c.phone_number == cls.phone_number)
            .outerjoin(meter_t, meter_t.c.id == customer_t.c.meter_id)
        )
        wheres = []
        if meter is not None:
            wheres.append(meter_t.c.id == meter.id)

        if ground is not None:
            wheres.append(ground_t.c.id == ground.id)

        if user is not None:
            users_ground_t = get_table_by_name("users_grounds")
            subquery = select(users_ground_t.c.ground_id).where(users_ground_t.c.user_id == user.id)
            # Doing a simple OR here, even on ground is fine, since we have a filter
            # above that restricts messages appropriately.
            wheres.append(or_(ground_t.c.id.in_(subquery), ground_t.c.id == null()))

        # Build the query (SQLAlchemy 2.0: unpack columns as positional args)
        query = (
            select(*columns)
            .select_from(joins)
            .where(and_(*wheres))
            .order_by(getattr(literal_column(order), "asc" if ascending else "desc")())
        )

        # Since we're doing complex mappings, the query needs to be converted to a subquery if string matching
        if query_string:
            query_format = "{}::text ~* :query_string"
            query = (
                # Name the subquery "base_query" and map the column labels back to the unprefixed versions
                select(*[text("base_query.{} as {}".format(col._label, col._label)) for col in columns])
                .select_from(query.alias("base_query"))
                .where(
                    or_(
                        text(query_format.format(col._label)).params(query_string=query_string)
                        for col in columns
                        if col._label not in (None, "total", "processed")
                    )
                )
            )

        # Paginate
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        return query

    @classmethod
    def maybe_create_alert(cls, event):
        """
        Examine event and create an alert if appropriate.

        Look at the event and see if it's possible to create
        an alert message for it.
        :param event: the event triggering the alert
        """
        if not isinstance(event, Event):  # pragma: nocoverage
            raise TypeError("event must be an event, not %r" % (type(event).__name__))

        alert_config = SMSConfigAlert.get_by_event_type(event.event_type)
        if alert_config is None:
            logger.info(
                "Not creating {!r} alert, missing alert config".format(
                    event.event_type,
                )
            )
            return

        phone_number = event.get_customer_phone_number()
        if phone_number is None:
            msg = "Not creating {!r} alert, customer {!r} lacks a verified phone number"
            logger.info(
                msg.format(
                    event.event_type,
                    event.spec.get_customer_for_object(event.object),
                )
            )
            return

        text = event.render(alert_config.template)
        logger.info("Creating alert {!r} for {!r}: {!r}".format(event.event_type, phone_number, text))
        message = cls.create_outgoing(phone_number=phone_number, text=text, event=event, ground=event.ground)
        message.set_config_alert(alert_config)
        return message

    def _raise_reply_error(self, message_type):
        config = SMSConfigMessage.get_by_message_type(message_type)
        reply = config.create(self.phone_number, in_reply_to=self)
        raise IncomingMessageReplyError(message_type=message_type, reply=reply)

    def _parse_incoming_command(self):
        # Parse the incoming message and see if it contains any
        # command messages like CHECK to validate a customer or
        # another user-defined message
        try:
            command = SMSConfigCommand.parse_message(self)
        except InvalidCommandCode:
            # We parsed the incoming message and we couldn't identify
            # a command code, create a reply to the command indicating to
            # the customer that the code is wrong
            self._raise_reply_error(SMSConfigMessage.TYPE_WRONG_CODE)

        return command

    def _verify_customer(self):
        # If a customer couldn't be found, reply with a message to the
        # sender saying that the phone number isn't recognized by the system
        if len(self.customers) == 0:
            self._raise_reply_error(SMSConfigMessage.TYPE_NO_SUCH_NUMBER)

        if len(self.customers) != 1:
            logger.exception("Multiple customers for phone number {number}".format(number=self.phone_number))

        # This will pick the first customer by insertion order, eg the customer that
        # was created first.
        customer = self.customers[0]
        if not customer.phone_number_verified:
            customer.phone_number_verified = True

        return customer

    def handle_incoming(self):
        """Parse an incoming message.

        Parse a message, fetch & verify customer and create a reply to it.

        :raises IncomingMessageReplyError: if message could not be parsed
        :raises IncomingMessageReplyError: if customer could not be identified
        :raises IncomingMessageReplyError: if customer isn't verified
        :returns: the reply
        """
        config_command = self._parse_incoming_command()
        customer = self._verify_customer()
        text = config_command.render_text(customer)
        message = SMSMessage.create_outgoing(self.phone_number, text, in_reply_to=self)
        message.ground = customer.meter.ground
        message.set_config_command(config_command)
        self.set_config_command(config_command)
        return message

    @property
    def reply(self):
        """The reply of this message, if any."""
        if self.in_reply_to_id is not None:
            return SMSMessage.query.get(self.in_reply_to_id)

    def set_origin(self, origin):
        """Set the origin of this message.

        :param origin: the origin
        :raises TypeError: if this message already has a origin set
        """
        if self.origin and self.origin != SMSMessage.ORIGIN_UNKNOWN:
            raise TypeError("origin is already set")

        self.origin = origin

    def set_config_command(self, config_command):
        """Set a config_command and origin of this message.

        :param config_command: the config command
        """
        self.set_origin(SMSMessage.ORIGIN_COMMAND)
        self.config_command_code = config_command.code

    def set_config_message(self, config_message):
        """Set a config_message and origin of this message.

        :param config_message: the config message
        """
        self.set_origin(SMSMessage.ORIGIN_SYSTEM)
        self.config_message_type = config_message.message_type

    def set_config_alert(self, config_alert):
        """Set a config_alert and origin of this message.

        :param config_alert: the config message
        """
        self.set_origin(SMSMessage.ORIGIN_ALERT)
        self.config_event_type = config_alert.event_type
