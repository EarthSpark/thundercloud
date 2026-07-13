# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Event views unittest."""

import datetime

import pytest
from freezegun import freeze_time

from sparkmeter.event.eventdomain import Event, SMSConfigMessage, SMSMessage
from sparkmeter.event.eventviews import format_messages
from sparkmeter.misc.jsonutils import json_dumps
from sparkmeter.tests.base import WebViewTestCaseBase
from sparkmeter.tests.test_data_factory import (
    GroundFactory,
    MeterFactory,
    OperatorFactory,
    SMSConfigAlertFactory,
    SMSConfigCommandFactory,
    SMSMessageFactory,
    VendorFactory,
)
from sparkmeter.user.userutils import set_current_user


@pytest.fixture(scope="function", autouse=True)
def login_user(mocker, operator_role, session):
    user = OperatorFactory(roles=[operator_role])
    session.commit()
    set_current_user(user)
    yield


class EventTest(WebViewTestCaseBase):
    def test_event_types(self, client):
        response = client.get("/event/event-types")
        self.verify_response(response)

    def test_message_types(self, client):
        response = client.get("/event/message-types")
        self.verify_response(response)

    def test_format_message(self):
        meter = MeterFactory(customer__phone_number="+12345")
        command = SMSConfigCommandFactory(code="CMD", template="Reply!")
        self.session.add(command.save())
        self.session.commit()

        # Two-way SMS received and the code (e.g. BAL) has been recognized
        with freeze_time("2010-01-01 12:01"):
            message = SMSMessageFactory(
                text="CMD",
                phone_number="+12345",
                direction=SMSMessage.DIRECTION_IN,
                timestamp=datetime.datetime.utcnow(),
                origin=None,
            )
            self.session.add(message)

        # Response to a valid Two-way SMS code (e.g. BAL) from a valid number
        with freeze_time("2010-01-01 12:02"):
            message2 = message.handle_incoming()
            message2.processed = True
            self.session.add(message2)

        # Any system message (verify number, error message, etc)
        with freeze_time("2010-01-01 12:03"):
            config_message = SMSConfigMessage.get_by_message_type(SMSConfigMessage.TYPE_VERIFY_NUMBER)
            message3 = config_message.create(meter.customer.phone_number)
            self.session.add(message3)

        # Message sent as the result of an alert (e.g. Low balance)
        with freeze_time("2010-01-01 12:04"):
            alert = SMSConfigAlertFactory(
                event_type=Event.TYPE_CUSTOMER_LOW_BALANCE, template="Low on alert {credits_balance}"
            )
            self.session.add(alert.save())
            self.session.commit()
            event1 = Event.create(Event.TYPE_CUSTOMER_LOW_BALANCE, meter)
            self.session.add(event1)
            self.session.commit()
            message4 = SMSMessage.maybe_create_alert(event1)
            self.session.add(message4)

        # Two-way SMS received but not recognized (unrecognized code)
        with freeze_time("2010-01-01 12:05"):
            message5 = SMSMessage(
                direction=SMSMessage.DIRECTION_IN,
                processed=True,
                phone_number=meter.customer.phone_number,
                text="Not recognized message",
                timestamp=datetime.datetime.now(),
            )
            self.session.add(message5)

        self.session.commit()

        query = SMSMessage.get_messages_view()
        results = self.session.execute(query)
        messages = format_messages(results, 1)
        json = json_dumps(dict(messages=messages))

        self.verify_json_content(json)

    def test_messages_json(self, client, config, operator_role, vendor_role):
        other = GroundFactory()
        meter = MeterFactory()
        self.session.commit()

        with freeze_time("2011-01-01 12:01"):
            SMSMessageFactory(
                phone_number=meter.customer.phone_number,
                direction=SMSMessage.DIRECTION_IN,
                timestamp=datetime.datetime.utcnow(),
                ground=self.ground,
                text="Incoming Message to Meter on Ground#1",
            )
        with freeze_time("2011-01-01 12:02"):
            event = Event.create(Event.TYPE_CUSTOMER_LOW_BALANCE, meter)
            SMSMessageFactory(
                phone_number=meter.customer.phone_number,
                event=event,
                direction=SMSMessage.DIRECTION_OUT,
                timestamp=datetime.datetime.utcnow(),
                ground=self.ground,
                text="Outgoing Message to Meter on Ground#1",
            )
        meter2 = MeterFactory()
        self.session.commit()
        with freeze_time("2012-02-02 12:01"):
            SMSMessageFactory(
                phone_number=meter2.customer.phone_number,
                direction=SMSMessage.DIRECTION_IN,
                timestamp=datetime.datetime.utcnow(),
                ground=other,
                text="Incoming Message to Meter on Ground#2",
            )
        with freeze_time("2012-02-02 12:02"):
            event2 = Event.create(Event.TYPE_CUSTOMER_LOW_BALANCE, meter2)
            SMSMessageFactory(
                phone_number=meter2.customer.phone_number,
                event=event2,
                direction=SMSMessage.DIRECTION_OUT,
                timestamp=datetime.datetime.utcnow(),
                ground=other,
                text="Outgoing Message to Meter on Ground#2",
            )
        with freeze_time("2012-02-03 12:01"):
            SMSMessageFactory(
                phone_number="+123",
                direction=SMSMessage.DIRECTION_IN,
                timestamp=datetime.datetime.utcnow(),
                ground=None,
                text="Incoming Message that is groundless",
            )
        with freeze_time("2012-02-03 12:02"):
            event2 = Event.create(Event.TYPE_CUSTOMER_LOW_BALANCE, meter2)
            SMSMessageFactory(
                phone_number="+123",
                event=event2,
                direction=SMSMessage.DIRECTION_OUT,
                timestamp=datetime.datetime.utcnow(),
                ground=None,
                text="Outgoing Message that is groundless",
            )
        users = [
            OperatorFactory(roles=[operator_role], username="operator-none", grounds=[]),
            OperatorFactory(roles=[operator_role], username="operator-only-1", grounds=[self.ground]),
            OperatorFactory(roles=[operator_role], username="operator-only-2", grounds=[other]),
            OperatorFactory(roles=[operator_role], username="operator-all", grounds=[self.ground, other]),
            VendorFactory(roles=[vendor_role], username="vendor-none", grounds=[]),
            VendorFactory(roles=[vendor_role], username="vendor-only-1", grounds=[self.ground]),
            VendorFactory(roles=[vendor_role], username="vendor-only-2", grounds=[other]),
            VendorFactory(roles=[vendor_role], username="vendor-all", grounds=[self.ground, other]),
        ]

        self.session.commit()

        for params in [
            dict(HEROKU=True, SERIAL=self.ground.serial),
            dict(HEROKU=False, SERIAL=self.ground.serial),
            dict(HEROKU=False, SERIAL=other.serial),
        ]:
            where = "cloud" if params.get("HEROKU") else "ground"
            if params["HEROKU"]:
                where = "cloud"
                del params["SERIAL"]
            elif params["SERIAL"] == self.ground.serial:
                where = "ground1"
            elif params["SERIAL"] == other.serial:
                where = "ground2"
            for user in users:
                config.update(**params)
                client.login_as(user)
                path = "/event/messages.json"
                response = client.get(path)
                variant = "%s-%s" % (where, user.username)
                self.verify_response(response, variant=variant)

    def test_messages_json_datatables_querystring(self, client, config, operator_role, vendor_role):
        meter = MeterFactory()
        with freeze_time("2011-01-01 12:01"):
            SMSMessageFactory(
                phone_number=meter.customer.phone_number,
                direction=SMSMessage.DIRECTION_IN,
                timestamp=datetime.datetime.utcnow(),
                ground=self.ground,
                text="Incoming Message to Meter on Ground#1",
            )
        self.session.commit()
        response = client.get("/event/messages.json?search[value]=motley&search[regex]=true")
        self.verify_response(response)

    def test_messages(self, client, config):
        path = "/event/messages"

        config["HEROKU"] = False
        response = client.get(path)

        self.verify_response(response)

    def test_messages_csv(self, client, config, operator_role, vendor_role):
        meter = MeterFactory()
        with freeze_time("2011-01-01 12:01"):
            SMSMessageFactory(
                phone_number=meter.customer.phone_number,
                direction=SMSMessage.DIRECTION_IN,
                timestamp=datetime.datetime.utcnow(),
                ground=self.ground,
                text="Incoming Message to Meter on Ground#1",
            )
        self.session.commit()
        response = client.get("/event/messages.csv")
        self.verify_response(response)
