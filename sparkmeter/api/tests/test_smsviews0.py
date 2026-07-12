# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import datetime
import http.client

from dateutil.tz import tzutc
from freezegun import freeze_time

from sparkmeter.api.tests.test_apiviews0 import APIView0TestCaseBase
from sparkmeter.event.eventdomain import Event, SMSMessage
from sparkmeter.misc.jsonutils import json_dumps
from sparkmeter.tests.test_data_factory import (
    EventFactory,
    MeterFactory,
    SMSConfigAlertFactory,
    SMSConfigCommandFactory,
    SMSMessageFactory,
)


class SMSListOutgoingTest(APIView0TestCaseBase):
    path = "v0/sms/outgoing"

    @freeze_time("2016-01-01")
    def test_get(self):
        meter = MeterFactory()
        alert = SMSConfigAlertFactory(
            event_type=Event.TYPE_CUSTOMER_LOW_BALANCE, template="Low on alert {credits_balance}"
        )
        self.session.add(alert.save())
        self.session.commit()
        event1 = EventFactory(event_type=Event.TYPE_CUSTOMER_LOW_BALANCE, object_id=str(meter.id))
        self.session.add(event1)
        self.session.commit()
        message1 = SMSMessage.maybe_create_alert(event1)
        self.session.add(message1)
        self.session.commit()

        data = dict(mark_delivered=False)
        response = self.get(self.path, data=json_dumps(data), headers={"Content-Type": "application/json"})
        # intentionally using the same return template as GET
        self.verify_response(response, ignore_values=[str(message1.id)])
        assert not message1.processed

        data = dict(mark_delivered=False)
        response = self.get(
            self.path, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        # intentionally using the same return template as GET
        self.verify_response(response, ignore_values=[str(message1.id)], variant="form-encoded")
        assert not message1.processed

        data = dict(mark_delivered=True)
        response = self.get(self.path, data=json_dumps(data), headers={"Content-Type": "application/json"})
        self.verify_response(response, variant="mark-delivered", ignore_values=[str(message1.id)])

        assert message1.processed

    def test_empty_queue(self):
        response = self.get(self.path, headers={"Content-Type": "application/json"})
        self.verify_response(response)

    @freeze_time("2016-01-01")
    def test_get_mark_delivered(self):
        meter = MeterFactory()
        alert = SMSConfigAlertFactory(
            event_type=Event.TYPE_CUSTOMER_LOW_BALANCE, template="Low on alert {credits_balance}"
        )
        self.session.add(alert.save())
        self.session.commit()
        event1 = EventFactory(event_type=Event.TYPE_CUSTOMER_LOW_BALANCE, object_id=str(meter.id))
        self.session.add(event1)
        self.session.commit()
        message1 = SMSMessage.maybe_create_alert(event1)
        self.session.add(message1)
        self.session.commit()

        data = dict(mark_delivered="false")
        response = self.get(self.path, data=json_dumps(data), headers={"Content-Type": "application/json"})
        self.verify_response(response, variant="false", ignore_values=[str(message1.id)])
        assert not message1.processed

        data = dict(mark_delivered="true")
        response = self.get(self.path, data=json_dumps(data), headers={"Content-Type": "application/json"})
        self.verify_response(response, variant="true", ignore_values=[str(message1.id)])
        assert message1.processed

    def test_invalid_mark_delivered(self):
        data = dict(mark_delivered="foobar")
        response = self.get(self.path, data=json_dumps(data), headers={"Content-Type": "application/json"})
        self.verify_response(response, variant="foobar")


class SMSMarkDeliveredTest(APIView0TestCaseBase):
    path = "v0/sms/mark-delivered"

    def test_mark_delivered(self):
        meter = MeterFactory()
        alert = SMSConfigAlertFactory(
            event_type=Event.TYPE_CUSTOMER_LOW_BALANCE, template="Low on alert {credits_balance}"
        )
        self.session.add(alert.save())
        self.session.commit()
        event1 = EventFactory(event_type=Event.TYPE_CUSTOMER_LOW_BALANCE, object_id=str(meter.id))
        self.session.add(event1)
        self.session.commit()
        message1 = SMSMessage.maybe_create_alert(event1)
        self.session.add(message1)
        self.session.commit()

        data = {
            "messages": [str(message1.id), "cafebabe0-0000-0000-0001-00000000000"],
        }
        response = self.put(self.path, json=data)
        self.verify_response(response, ignore_values=[str(message1.id)])

    def test_no_messages(self):
        data = {
            "messages": [],
        }
        response = self.put(self.path, json=data)
        self.verify_response(response)


class SMSAddIncomingTest(APIView0TestCaseBase):
    path = "v0/sms/incoming"

    @freeze_time("2016-01-01")
    def test_add(self):
        meter = MeterFactory()
        command = SMSConfigCommandFactory(code="CMD", template="Reply!")
        self.session.add(command.save())
        self.session.commit()

        data = {
            "id": "31337 gw s0ftwáre!-876786",
            "phone_number": str(meter.customer.phone_number),
            "text": "CMD message",
            "timestamp": datetime.datetime(2010, 1, 1, 12, 30, 4, tzinfo=tzutc()).isoformat(),
        }
        response = self.post(self.path, data=data)
        message = SMSMessage.query.filter_by(direction=SMSMessage.DIRECTION_IN).one()
        assert list(message.customers) == [meter.customer]
        assert message.phone_number == "+18008000001"
        assert message.text == "CMD message"
        # FIXME: Figure out why this is offset by localtime when running in 'make check', but
        #        not via testrunner.
        assert message.timestamp.date() == datetime.date(2010, 1, 1)
        assert message.external_id == "31337 gw s0ftwáre!-876786"
        assert message.direction == SMSMessage.DIRECTION_IN
        assert message.ground == meter.ground

        reply = message.reply
        assert reply
        assert reply.phone_number == "+18008000001"
        assert reply.text == "Reply!"
        assert reply.direction == SMSMessage.DIRECTION_OUT
        assert reply.processed
        assert reply.ground == meter.ground
        self.verify_response(response, ignore_values=[str(reply.id)])

    @freeze_time("2016-01-01")
    def test_empty_id(self):
        meter = MeterFactory()
        command = SMSConfigCommandFactory(code="CMD", template="Reply!")
        self.session.add(command.save())
        self.session.commit()

        data = {
            "phone_number": str(meter.customer.phone_number),
            "text": "CMD message",
            "timestamp": datetime.datetime(2010, 1, 1, 0, 30, 4).isoformat(),
        }
        response = self.post(self.path, data=data)
        message = SMSMessage.query.filter_by(direction=SMSMessage.DIRECTION_IN).one()
        assert message.ground == meter.ground
        reply = message.reply
        assert reply.processed
        assert reply.ground == meter.ground

        self.verify_response(response, ignore_values=[str(reply.id)])

    @freeze_time("2016-01-01")
    def test_empty_timestamp(self):
        meter = MeterFactory()
        command = SMSConfigCommandFactory(code="CMD", template="Reply!")
        self.session.add(command.save())
        self.session.commit()

        data = {
            "id": "31337 gw s0ftwáre!-876786",
            "phone_number": str(meter.customer.phone_number),
            "text": "CMD message",
        }
        response = self.post(self.path, data=data)
        message = SMSMessage.query.filter_by(direction=SMSMessage.DIRECTION_IN).one()
        assert message.ground == meter.ground
        reply = message.reply
        assert reply.processed
        assert reply.ground == meter.ground

        self.verify_response(response, ignore_values=[str(reply.id)])

    def test_timestamp_formats(self):
        meter = MeterFactory()
        command = SMSConfigCommandFactory(code="CMD", template="Reply!")
        self.session.add(command.save())
        self.session.commit()

        number = str(meter.customer.phone_number)
        for i, (fmt, timestamp) in enumerate(
            [
                # Timezone aware (UTC)
                ("2016-01-01T12:34:56.123456789T-0000", datetime.datetime(2016, 1, 1, 12, 34, 56, 123456)),
                # Timezone aware (IST)
                ("2016-01-01T12:34:56.123456789T-0545", datetime.datetime(2016, 1, 1, 6, 49, 56, 123456)),
                # Timezone unaware
                ("2016-01-01T12:34:56.123456789T", datetime.datetime(2016, 1, 1, 12, 34, 56, 123456)),
                # Timezone unaware, microsecond unaware
                ("2016-01-01T12:34:56", datetime.datetime(2016, 1, 1, 12, 34, 56, 0)),
                # Timezone unaware, time unaware
                ("2016-01-01", datetime.datetime(2016, 1, 1, 0, 0, 0, 0)),
            ]
        ):
            data = {
                "id": str(i),
                "phone_number": number,
                "text": "CMD message",
                "timestamp": fmt,
            }
            response = self.post(self.path, data=data)
            if response.status_code != http.client.CREATED:
                raise AssertionError(response.data)
            message = SMSMessage.query.filter_by(direction=SMSMessage.DIRECTION_IN, external_id=str(i)).one()
            assert message.timestamp == timestamp
            assert message.ground == meter.ground

    @freeze_time("2016-01-01")
    def test_verify_customer(self):
        meter = MeterFactory(customer__phone_number_verified=False)
        command = SMSConfigCommandFactory(code="CMD", template="Reply!")
        self.session.add(command.save())
        self.session.commit()

        data = {
            "id": "31337 gw s0ftwáre!-876786",
            "phone_number": str(meter.customer.phone_number),
            "text": "CHECK",
            "timestamp": datetime.datetime(2010, 1, 1, 0, 30, 4).isoformat(),
        }
        response = self.post(self.path, data=data)
        reply = SMSMessage.query.filter_by(direction=SMSMessage.DIRECTION_OUT).one()
        assert reply
        assert reply.phone_number == "+18008000001"
        msg = "Thank you! This phone number has been added to str\xebet in SparkMeter."
        assert reply.text == msg
        assert reply.processed
        assert meter.customer.phone_number_verified
        assert reply.ground == meter.ground

        self.verify_response(response, ignore_values=[str(reply.id)])

    @freeze_time("2016-01-01")
    def test_wrong_code(self):
        meter = MeterFactory()
        command = SMSConfigCommandFactory(code="CMD", template="Reply!")
        self.session.add(command.save())
        self.session.commit()

        data = {
            "id": "31337 gw s0ftwáre!-876786",
            "phone_number": str(meter.customer.phone_number),
            "text": "SLIFF message",
            "timestamp": datetime.datetime(2010, 1, 1, 0, 30, 4).isoformat(),
        }
        response = self.post(self.path, data=data)
        reply = SMSMessage.query.filter_by(direction=SMSMessage.DIRECTION_OUT).one()
        assert reply
        assert reply.phone_number == "+18008000001"
        assert reply.text == "This SMS code is not recognized by SparkMeter."
        assert reply.processed
        assert reply.ground is None

        self.verify_response(response, ignore_values=[str(reply.id)])

    @freeze_time("2016-01-01")
    def test_number_not_recognized(self):
        command = SMSConfigCommandFactory(code="CMD", template="Reply!")
        self.session.add(command.save())
        self.session.commit()

        data = {
            "id": "31337 gw s0ftwáre!-876786",
            "phone_number": "+18008000002",
            "text": "CMD message",
            "timestamp": datetime.datetime(2010, 1, 1, 0, 30, 4).isoformat(),
        }
        response = self.post(self.path, data=data)
        reply = SMSMessage.query.filter_by(direction=SMSMessage.DIRECTION_OUT).one()
        assert reply
        assert reply.phone_number == "+18008000002"
        assert reply.text == "This phone number is not recognized by SparkMeter."
        assert reply.processed
        assert reply.ground is None

        self.verify_response(response, ignore_values=[str(reply.id)])

    def test_missing_phone_number(self):
        data = {
            "id": "31337 gw s0ftwáre!-876786",
            "text": "prétty méssage",
            "timestamp": datetime.datetime(2010, 1, 1, 0, 30, 4).isoformat(),
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)

    def test_invalid_phone_number(self):
        data = {
            "id": "31337 gw s0ftwáre!-876786",
            "phone_number": "+11",
            "text": "prétty méssage",
            "timestamp": datetime.datetime(2010, 1, 1, 0, 30, 4).isoformat(),
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)

    def test_missing_text(self):
        data = {
            "id": "31337 gw s0ftwáre!-876786",
            "phone_number": "+18008374966",
            "timestamp": datetime.datetime(2010, 1, 1, 0, 30, 4).isoformat(),
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)

    def test_invalid_timestamp(self):
        data = {
            "id": "31337 gw s0ftwáre!-876786",
            "phone_number": "+18008374966",
            "text": "prétty méssage",
            "timestamp": "foobarz",
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)

    def test_message_already_exists(self):
        SMSMessageFactory(external_id="external-id")
        self.session.commit()
        data = {
            "id": "external-id",
            "phone_number": "+18008374966",
            "text": "prétty méssage",
            "timestamp": datetime.datetime(2010, 1, 1, 0, 30, 4).isoformat(),
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)
        assert SMSMessage.query.count() == 1
