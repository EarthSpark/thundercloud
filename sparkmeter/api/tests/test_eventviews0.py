# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import uuid

from sparkmeter.api.tests.test_apiviews0 import APIView0TestCaseBase
from sparkmeter.event.eventdomain import Event
from sparkmeter.tests.test_data_factory import EventFactory, MeterFactory


class EventViewTest(APIView0TestCaseBase):
    path = "v0/event/{id}"

    def test_get(self):
        event = EventFactory()
        self.session.commit()
        path = self.path.format(id=event.id)
        response = self.get(path)
        self.verify_response(response, ignore_values=[str(event.id)])

    def test_get_nonexistent(self):
        event_id = uuid.uuid4()
        path = self.path.format(id=event_id)
        response = self.get(path)
        self.verify_response(response, ignore_values=[str(event_id)])

    def test_get_customer_wallet_zero_event(self):
        meter = MeterFactory()
        self.session.commit()
        event = EventFactory(
            event_type=Event.TYPE_CUSTOMER_WALLET_ZERO_REQUESTED,
            object_table="wallet",
            object_id=meter.credit_wallet.id,
        )
        self.session.commit()
        path = self.path.format(id=event.id)
        response = self.get(path)
        self.verify_response(response, ignore_values=[str(event.id)])
