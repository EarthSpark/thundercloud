# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.

from sparkmeter.event.eventdomain import Event, SMSMessage
from sparkmeter.meter.meterdomain import Meter
from sparkmeter.tasks import process_events
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import MeterFactory, SMSConfigAlertFactory, TransactionFactory
from sparkmeter.transaction.transactiondomain import Transaction, TransactionSource


class TaskTest(SparkMeterTestCaseBase):
    def test_process_event_low_balance(self):
        meter = MeterFactory()
        self.session.commit()
        event_type = Event.TYPE_CUSTOMER_LOW_BALANCE
        event = Event.create(event_type, meter)
        self.session.add(event)
        self.session.commit()
        meter_id = meter.id

        process_events()
        assert SMSMessage.query.count() == 0

        alert = SMSConfigAlertFactory(event_type=event_type)
        self.session.add(alert.save())
        self.session.commit()

        meter = self.session.query(Meter).get(meter_id)
        event = Event.create(event_type, meter)
        self.session.add(event)
        self.session.commit()

        assert SMSMessage.query.count() == 0

        process_events()
        assert SMSMessage.query.count() == 1

        process_events()
        assert SMSMessage.query.count() == 1

    def test_process_event_transaction(self, config, send_set_config):
        alert = SMSConfigAlertFactory(event_type=Event.TYPE_CUSTOMER_CREDIT_TRANSACTION)
        self.session.add(alert.save())
        self.session.commit()

        t = TransactionFactory(
            source=TransactionSource.get_by_name(TransactionSource.CASH), state=Transaction.STATE_PENDING
        )
        t.from_wallet.value = 100
        self.session.commit()
        t_id = t.id
        user_id = t.user_id
        t.process()
        assert send_set_config.mock_calls == []
        self.session.commit()

        events = Event.get_all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == Event.TYPE_CUSTOMER_CREDIT_TRANSACTION
        assert event.object_id == t_id
        assert not event.processed

        assert SMSMessage.query.count() == 0

        config["HEROKU"] = False
        process_events()
        self.session.commit()

        assert SMSMessage.query.count() == 1
        event = Event.get_all()[0]
        assert event.processed
        assert event.created_by_id == user_id
