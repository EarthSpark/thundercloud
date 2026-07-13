# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
from sparkmeter.event.eventdomain import Event, SMSMessage
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import MeterFactory


class EventCommandTest(SparkMeterTestCaseBase):
    def test_create_sms_message_in(self, cli):
        MeterFactory(customer__phone_number="12345")
        self.session.commit()
        cli("event", "create-sms", "--text", "text", "--phone-number", "12345", "--direction", "in")
        message = SMSMessage.query.filter_by(direction=SMSMessage.DIRECTION_IN).one()
        assert message.text == "text"
        assert message.phone_number == "12345"
        assert message.processed

        message = SMSMessage.query.filter_by(direction=SMSMessage.DIRECTION_OUT).one()
        assert message.text == "This SMS code is not recognized by SparkMeter."
        assert message.phone_number == "12345"
        assert not message.processed

    def test_create_sms_message_out(self, cli):
        cli("event", "create-sms", "--text", "text", "--phone-number", "12345", "--direction", "out")
        message = SMSMessage.query.one()
        assert message.text == "text"
        assert message.phone_number == "12345"
        assert message.direction == SMSMessage.DIRECTION_OUT
        assert message.processed

    def test_process_events(self, cli):
        meter = MeterFactory()
        self.session.commit()
        event = Event.create(Event.TYPE_CUSTOMER_LOW_BALANCE, meter)
        self.session.add(event)
        self.session.commit()

        event_id = event.id
        assert not event.processed
        cli("event", "process")
        event = Event.get_by_id(event_id)
        assert event.processed
