# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
import datetime
from builtins import range, str
from unittest import mock

import pytest
from freezegun import freeze_time
from testfixtures import log_capture

from sparkmeter.config.configparameter import parameters
from sparkmeter.controller import process_reading, process_transaction
from sparkmeter.event.eventdomain import Event, SMSConfigCommand, SMSConfigMessage, SMSMessage
from sparkmeter.event.eventkeywords import CurrencyKeyword
from sparkmeter.meter.meterdomain import Customer, Meter, MeterConfig
from sparkmeter.misc.jsonutils import json_dumps
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import (MeterFactory, OperatorFactory, ReadingFactory,
                                                SalesAccountFactory, SMSConfigAlertFactory,
                                                SMSConfigCommandFactory, SMSMessageFactory,
                                                TariffFactory, TotalizerMeterFactory,
                                                TransactionSourceFactory, UserFactory)
from sparkmeter.transaction.transactiondomain import Transaction, TransactionSource, Wallet
from sparkmeter.user.userutils import set_current_user


class EventTest(SparkMeterTestCaseBase):
    def collect_events(self):
        events = []
        for event in Event.get_all():
            data = event._data
            data['environment'] = event.spec.collect_environment(event.object)
            events.append(data)
        return events

    def check_events(self, events, ignore_values=None, variant=None):
        if ignore_values is None:
            ignore_values = []
        data = json_dumps(events)
        for event in events:
            ignore_values.append(event['timestamp'].isoformat())
            ignore_values.append(str(event['id']))
            ignore_values.append(str(event['object_id']))

        self.verify_json_content(data, variant=variant, ignore_values=ignore_values, frame=2)

    def test_create_error(self):
        with pytest.raises(ValueError):
            Event.create('foo', None)

    def process_events(self):
        for event in Event.get_unprocessed():
            event.process()

    def test_create(self, operator_role):
        user = OperatorFactory(roles=[operator_role])
        self.session.commit()
        set_current_user(user)
        meter = MeterFactory()
        self.session.commit()
        e = Event.create(Event.TYPE_CUSTOMER_LOW_BALANCE, meter)
        self.session.commit()
        assert not e.processed
        assert e.created_by == user

    @freeze_time("2017-06-02")
    def test_processed_timestamp(self):
        meter = MeterFactory()
        self.session.commit()
        e = Event.create(Event.TYPE_CUSTOMER_LOW_BALANCE, meter)
        self.session.commit()
        assert not e.processed
        assert e.processed_timestamp is None
        e.process()
        assert e.processed is True
        assert e.processed_timestamp == datetime.datetime(2017, 6, 2, 0, 0, 0)

    @freeze_time("2017-06-02")
    def test_customer_credit_transaction_cash(self, config, operator_role, send_set_config):
        account = SalesAccountFactory(credit_wallet__value=1000,
                                      debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(accounts=[account],
                               roles=[operator_role],
                               grounds=[account.ground])
        meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100,
                             system_info__last_energy=2972.3873,
                             billing__total_cycle_energy=28045.12345)
        source = TransactionSource.get_by_name(TransactionSource.CASH)
        self.session.commit()

        transaction = Transaction.create_transactions(
            from_object=account,
            to_object=meter,
            amount=40,
            wallet_type=Wallet.TYPE_CREDIT,
            user=user,
            source=source,
            ground=meter.ground,
            session=self.session,
        )
        self.session.commit()

        assert Event.query.count() == 0
        config['HEROKU'] = False
        process_transaction(transaction.id)

        events = self.collect_events()
        self.check_events(events, ignore_values=[transaction.created.isoformat()])
        assert send_set_config.mock_calls == [
            mock.call(
                subnet=255,
                current_limit=10000.0,
                load_limit=50.0,
                mac=1,
                command='enable',
                balance=240.0,
                low_balance=False,
                firmware_version=u'abc1234'),
        ]

    @freeze_time("2017-06-02")
    def test_customer_credit_transaction_bonus(self, config, mocker, operator_role, send_set_config):
        account = SalesAccountFactory(credit_wallet__value=1000,
                                      debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(roles=[operator_role],
                               accounts=[account],
                               grounds=[account.ground])
        meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100,
                             system_info__last_energy=2972.3873,
                             billing__total_cycle_energy=28045.12345)
        source = TransactionSource.get_by_name(TransactionSource.BONUS)
        self.session.commit()

        transaction = Transaction.create_transactions(
            from_object=account,
            to_object=meter,
            amount=40,
            wallet_type=Wallet.TYPE_CREDIT,
            user=user,
            source=source,
            ground=meter.ground,
            session=self.session,
        )
        self.session.commit()

        assert Event.query.count() == 0
        config['HEROKU'] = False
        process_transaction(transaction.id)

        events = self.collect_events()
        self.check_events(events, ignore_values=[transaction.created.isoformat()])
        assert send_set_config.mock_calls == [
            mock.call(
                subnet=255,
                current_limit=10000.0,
                load_limit=50.0,
                mac=1,
                command='enable',
                balance=240.0,
                low_balance=False,
                firmware_version=u'abc1234'),
        ]

    @freeze_time("2017-06-02")
    def test_customer_credit_transaction_reversal(self, config, operator_role, send_set_config):
        account = SalesAccountFactory(credit_wallet__value=1000,
                                      debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(roles=[operator_role],
                               accounts=[account],
                               grounds=[account.ground])
        meter = MeterFactory(credit_wallet__value=200,
                             debt_wallet__value=100,
                             system_info__last_energy=2972.3873,
                             billing__total_cycle_energy=28045.12345)
        source = TransactionSource.get_by_name(TransactionSource.CASH)
        self.session.commit()

        transaction = Transaction.create_transactions(
            from_object=account,
            to_object=meter,
            amount=40,
            wallet_type=Wallet.TYPE_CREDIT,
            user=user,
            source=source,
            ground=meter.ground,
            session=self.session,
        )
        self.session.commit()

        assert Event.query.count() == 0
        config['HEROKU'] = False
        process_transaction(transaction.id)

        events = self.collect_events()
        reversed_transaction = transaction.reverse(user)
        self.session.add(reversed_transaction)
        self.session.commit()
        config['HEROKU'] = False
        process_transaction(reversed_transaction.id)

        events.append(self.collect_events()[-1])
        self.check_events(events, ignore_values=[transaction.created.isoformat()])
        assert send_set_config.mock_calls == [
            mock.call(
                subnet=255,
                current_limit=10000.0,
                load_limit=50.0,
                mac=1,
                command='enable',
                balance=240.0,
                low_balance=False,
                firmware_version=u'abc1234'),
            mock.call(
                subnet=255,
                current_limit=10000.0,
                load_limit=50.0,
                mac=1,
                command='enable',
                balance=200.0,
                low_balance=False,
                firmware_version=u'abc1234'),
        ]

    @freeze_time("2017-06-02")
    def test_customer_low_balance(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        user = OperatorFactory(roles=[operator_role],
                               accounts=[account],
                               grounds=[account.ground])
        source = TransactionSourceFactory()
        m = MeterFactory(
            config__state=MeterConfig.STATE_AUTO,
            billing__tariff__low_balance_threshold=5,
            billing__tariff__flat_price=10,
            system_info__last_energy=39
        )
        self.session.commit()

        transaction = Transaction.create_transactions(
            from_object=account,
            to_object=m,
            amount=40,
            wallet_type=Wallet.TYPE_CREDIT,
            user=user,
            source=source,
            ground=m.ground,
            session=self.session,
        )
        transaction.state = Transaction.STATE_PROCESSED
        self.session.commit()

        sr = ReadingFactory(
            meter=str(m.code),
            energy=40,
            heartbeat_start=datetime.datetime(2013, 1, 1, 0, 30, 0),
            heartbeat_end=datetime.datetime(2013, 1, 1, 0, 45, 0),
        )
        self.session.commit()

        process_reading(sr, m, self.session)
        self.session.commit()

        events = self.collect_events()
        self.check_events(events, ignore_values=[transaction.created.isoformat()])

    @freeze_time("2017-06-02")
    def test_customer_low_balance_ps_487(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        user = OperatorFactory(roles=[operator_role],
                               accounts=[account],
                               grounds=[account.ground])
        source = TransactionSourceFactory()
        m = MeterFactory(
            config__state=MeterConfig.STATE_AUTO,
            billing__tariff__low_balance_threshold=0,
            system_info__last_energy=40,
        )
        self.session.commit()

        transaction = Transaction.create_transactions(
            from_object=account,
            to_object=m,
            amount=40,
            wallet_type=Wallet.TYPE_CREDIT,
            user=user,
            source=source,
            ground=m.ground,
            session=self.session,
        )
        transaction.state = Transaction.STATE_PROCESSED
        self.session.commit()

        for i in range(5):
            sr = ReadingFactory(
                meter=str(m.code),
                kilowatt_hours=1,
                energy=41 + i)
            self.session.commit()

            process_reading(sr, m, self.session)
            self.session.commit()

        events = self.collect_events()
        self.check_events(events, ignore_values=[transaction.created.isoformat()])

    def test_customer_credit_transaction_error(self):
        with pytest.raises(TypeError, match="obj must be a Transaction, not str"):
            Event.create(Event.TYPE_CUSTOMER_CREDIT_TRANSACTION, 'invalid-type')

    def test_get_unprocessed(self):
        meter = MeterFactory()
        self.session.commit()
        e1 = Event.create(Event.TYPE_CUSTOMER_LOW_BALANCE, meter)
        e1.processed = True
        self.session.add(e1)
        e2 = Event.create(Event.TYPE_CUSTOMER_LOW_BALANCE, meter)
        self.session.add(e2)
        self.session.commit()
        assert [e.id for e in Event.get_unprocessed()] == [e2.id]

    def test_get_last_event_by(self):
        event_type = Event.TYPE_CUSTOMER_LOW_BALANCE
        m1 = MeterFactory()
        m2 = MeterFactory()
        self.session.commit()
        e1 = Event.create(event_type, m1)
        self.session.add(e1)
        e2 = Event.create(event_type, m1)
        self.session.add(e2)
        e3 = Event.create(event_type, m2)
        self.session.add(e3)
        self.session.commit()
        assert Event.get_last_event_by(event_type, m1) == e2

    def test_event_currency_keyword(self):
        keyword = CurrencyKeyword('name', 'description', 'example')
        assert keyword.format(0, 'en_US') == '0.00'
        assert keyword.format(1.23, 'en_US') == '1.23'
        assert keyword.format(123456.789, 'en_US') == '123,456.79'

        assert keyword.format(0, 'fr_FR') == '0,00'
        assert keyword.format(1.23, 'fr_FR') == '1,23'
        # Babel 2.14+ uses narrow no-break space (\u202f)
        assert keyword.format(123456.789, 'fr_FR') == '123\u202f456,79'

    @freeze_time("2017-06-02")
    def test_meter_set_state(self, config):
        m = MeterFactory(config__state=MeterConfig.STATE_ON)
        self.session.commit()
        m.set_state(MeterConfig.STATE_OFF)
        self.session.commit()

        config['HEROKU'] = False
        events = self.collect_events()
        self.check_events(events)

    @freeze_time("2017-06-02")
    def test_ground_override_state_on(self, config, mocker, send_set_config):
        parameters.SEND_BROADCAST_SIGNAL = True
        disable_all_meters = mocker.patch('sparkmeter.ground.grounddomain.disable_all_meters')

        self.ground.private.queue_override_meter_state(True)
        MeterFactory(ground=self.ground, config__state=MeterConfig.STATE_ON,
                     system_info__current_user_power_limit=100.0)
        MeterFactory(ground=self.ground, config__state=MeterConfig.STATE_OFF,
                     system_info__current_user_power_limit=100.0)
        self.session.commit()

        config['HEROKU'] = False
        events = self.collect_events()
        self.check_events(events)
        self.process_events()

        assert self.ground.private.override_meter_state is True
        assert self.ground.private.override_meter_state_modified == datetime.datetime(2017, 6, 2)
        assert send_set_config.mock_calls == [
            mock.call(
                load_limit=50.0,
                subnet=255,
                current_limit=10000.0,
                command='disable',
                mac=1,
                balance=0,
                low_balance=True,
                firmware_version=u'abc1234'),
            mock.call(
                load_limit=50.0,
                subnet=255,
                current_limit=10000.0,
                command='disable',
                mac=2,
                balance=0,
                low_balance=True,
                firmware_version=u'abc1234'),
        ]

        # verify old state is restored when override is disabled
        send_set_config.reset_mock()
        config['HEROKU'] = False
        self.ground.private.set_override_meter_state(False)

        assert send_set_config.mock_calls == [
            mock.call(
                load_limit=50.0,
                subnet=255,
                current_limit=10000.0,
                command='disable',
                mac=2,
                balance=0,
                low_balance=True,
                firmware_version=u'abc1234'),
            mock.call(
                load_limit=50.0,
                subnet=255,
                current_limit=10000.0,
                command='enable',
                mac=1,
                balance=0,
                low_balance=True,
                firmware_version=u'abc1234'),
        ]
        assert disable_all_meters.mock_calls == [mock.call()]

    @freeze_time("2017-06-02")
    def test_ground_override_state_off(self, config, send_set_config):
        self.ground.private.override_meter_state = True
        MeterFactory(ground=self.ground, config__state=MeterConfig.STATE_ON)
        MeterFactory(ground=self.ground, config__state=MeterConfig.STATE_ON)
        self.session.commit()

        self.ground.private.queue_override_meter_state(False)
        self.session.commit()

        config['HEROKU'] = False
        events = self.collect_events()
        self.check_events(events)
        self.process_events()

        assert self.ground.private.override_meter_state is False
        assert self.ground.private.override_meter_state_modified == datetime.datetime(2017, 6, 2)
        assert send_set_config.mock_calls == [
            mock.call(
                load_limit=50.0,
                subnet=255,
                current_limit=10000.0,
                command='enable',
                mac=1,
                balance=0,
                low_balance=True,
                firmware_version='abc1234'),
            mock.call(
                load_limit=50.0,
                subnet=255,
                current_limit=10000.0,
                command='enable',
                mac=2,
                balance=0,
                low_balance=True,
                firmware_version='abc1234'),
        ]

    def test_nominal_voltage_update(self, config, send_set_config):
        parameters.NOMINAL_VOLTAGE = 110.0
        tariff = TariffFactory(flat_load_limit=10000)
        meter = MeterFactory(config__subnet=255, tariff=tariff)
        meter.send_set_config_based_on_system_info()
        self.session.commit()

        config['HEROKU'] = False
        events = self.collect_events()
        self.check_events(events)
        self.process_events()
        assert send_set_config.mock_calls == [
            mock.call(
                load_limit=1100.0,
                subnet=255,
                current_limit=10000.0,
                command='disable',
                mac=1,
                balance=0,
                low_balance=True,
                firmware_version='abc1234'),
        ]

    def test_nominal_voltage_update_only_customer_meters(self, config, send_set_config):
        parameters.NOMINAL_VOLTAGE = 110.0
        tariff = TariffFactory(flat_load_limit=10000)
        meter = MeterFactory(config__subnet=255, tariff=tariff)
        TotalizerMeterFactory(config__subnet=255)
        meter.send_set_config_based_on_system_info()
        self.session.commit()

        config['HEROKU'] = False
        events = self.collect_events()
        self.check_events(events)
        assert len(Meter.get_all()) == 2
        with mock.patch.object(Meter, 'send_set_config_based_on_system_info') as send_system_info:
            self.process_events()
            send_system_info.assert_called_once()

    def test_customer_wallet_zero_requested(self, config):
        meter = MeterFactory()
        meter.credit_wallet.value = 10.0
        self.session.commit()
        meter.credit_wallet.request_zero()
        self.session.commit()

        config['HEROKU'] = False
        events = self.collect_events()
        assert len(events) == 1
        self.check_events(events)

    @pytest.mark.parametrize('balance', [10.0, -10.0])
    def test_customer_wallet_zero_processing(self, balance, config, send_set_config):
        with mock.patch('sparkmeter.event.eventdomain.get_current_user') as gcu:
            meter = MeterFactory()
            gcu.return_value = UserFactory()
            meter.credit_wallet.value = balance
            self.session.commit()
            meter.credit_wallet.request_zero()
            self.session.commit()

        sales_acct_value = SalesAccount.get_system().get_wallet('credit').value
        config['HEROKU'] = False
        events = self.collect_events()
        self.check_events(events, variant='balance_{}'.format(balance))
        self.process_events()
        self.session.commit()
        assert len(events) == 1
        self.session.refresh(meter)
        assert meter.credit_wallet.value == 0
        transactions = Transaction.get_all()
        assert len(transactions) == 1
        transaction = transactions[0]
        assert transaction.amount == -balance
        assert transaction.state == Transaction.STATE_PROCESSED
        assert transaction.user.id == events[0]['created_by_id']
        assert sales_acct_value - transaction.amount == transaction.from_wallet.value


class SMSMessageTest(SparkMeterTestCaseBase):
    def test_get_outgoing(self):
        meter = MeterFactory()
        alert = SMSConfigAlertFactory(event_type=Event.TYPE_CUSTOMER_LOW_BALANCE,
                                      template=u'Low on alert {credits_balance}')
        self.session.add(alert.save())
        self.session.commit()

        event1 = Event.create(Event.TYPE_CUSTOMER_LOW_BALANCE, meter)
        self.session.add(event1)
        self.session.commit()
        message1 = SMSMessage.maybe_create_alert(event1)
        message1.processed = False
        self.session.add(message1)

        event2 = Event.create(Event.TYPE_CUSTOMER_LOW_BALANCE, meter)
        self.session.add(event2)
        self.session.commit()
        message2 = SMSMessage.maybe_create_alert(event2)
        message2.processed = True
        self.session.add(message1)
        self.session.add(event2)

        # Two-Way, with reply,
        message3 = SMSMessageFactory(text='CMD',
                                     direction=SMSMessage.DIRECTION_OUT)
        SMSMessage.create_outgoing(message3.phone_number, 'some reply',
                                   in_reply_to=message3)
        self.session.commit()
        assert [m.id for m in SMSMessage.get_outgoing()] == [message1.id]

    def test_maybe_create_alert(self):
        meter = MeterFactory(customer__phone_number=None)
        self.session.commit()
        event_type = Event.TYPE_CUSTOMER_LOW_BALANCE
        event = Event.create(event_type, meter)
        self.session.add(event)
        self.session.commit()

        # no alert configured
        message = SMSMessage.maybe_create_alert(event)
        assert not message

        alert = SMSConfigAlertFactory(event_type=event_type,
                                      template=u'Low on alert {credits_balance}')
        self.session.add(alert.save())
        self.session.commit()

        # no customer phone number
        message = SMSMessage.maybe_create_alert(event)
        assert not message

        meter.customer.phone_number = '+123456'
        self.session.commit()

        message = SMSMessage.maybe_create_alert(event)
        self.session.add(message)
        self.session.commit()

        assert message.direction == SMSMessage.DIRECTION_OUT
        assert message.phone_number == '+123456'
        assert message.timestamp
        assert not message.processed
        assert not message.external_id
        assert not message.in_reply_to_id
        assert message.event_id == event.id
        assert message.text == u'Low on alert 0.00'

    def test_set_origin(self):
        message = SMSMessageFactory(text='CMD', origin=None)
        message.set_origin(SMSMessage.ORIGIN_ALERT)
        assert message.origin == SMSMessage.ORIGIN_ALERT
        msg = "origin is already set"
        with pytest.raises(TypeError, match=msg):
            message.set_origin(SMSMessage.ORIGIN_ALERT)

    @log_capture('sparkmeter.event.eventdomain')
    def test_multiple_customer_with_same_phone_number(self, logger):
        MeterFactory(customer__name='Customer 1',
                     customer__phone_number='+123456',
                     customer__phone_number_verified=False)
        MeterFactory(customer__name='Customer 2',
                     customer__phone_number='+123456',
                     customer__phone_number_verified=False)
        command = SMSConfigCommandFactory(code='CMD', template=u'{customer_name}')
        self.session.add(command.save())
        self.session.commit()
        with freeze_time("2010-01-01 12:01"):
            message = SMSMessageFactory(text='CMD', phone_number='+123456',
                                        direction=SMSMessage.DIRECTION_IN,
                                        timestamp=datetime.datetime.utcnow(),
                                        origin=None)
            reply = message.handle_incoming()
            assert reply.text == u'Customer 1'
        logger.check(('sparkmeter.event.eventdomain',
                      'ERROR',
                      'Multiple customers for phone number +123456'))
        c1 = Customer.query.filter_by(name=u'Customer 1').one()
        assert c1.phone_number_verified

        c2 = Customer.query.filter_by(name=u'Customer 2').one()
        assert not c2.phone_number_verified

    def test_sms_config_command_default_id(self):
        command = SMSConfigMessage()
        assert command.id is not None

    def test_matches_escapes_regex_metacharacters(self):
        # Admin command codes are matched literally; regex metacharacters must
        # not be interpreted (prevents ReDoS / over-broad matching). matches()
        # is start-anchored (re.match) with a trailing end/whitespace delimiter.
        dot = SMSConfigCommand(code='a.c')
        assert dot.matches('a.c') is True       # literal match
        assert dot.matches('a.c now') is True   # code + args, still a token
        assert dot.matches('abc') is False      # '.' must not act as a wildcard
        plus = SMSConfigCommand(code='a+')
        assert plus.matches('a+') is True        # literal match
        assert plus.matches('aaa') is False      # '+' must not act as a quantifier
