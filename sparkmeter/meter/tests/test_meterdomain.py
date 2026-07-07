# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
import datetime
from builtins import str
from unittest import mock

import pytest
from freezegun import freeze_time
from testfixtures import LogCapture, log_capture

from sparkmeter.config.configparameter import ParameterObject, parameters
from sparkmeter.exceptions import MeterError, TransactionError
from sparkmeter.meter.meterdomain import (Address, Customer, Meter, MeterBilling, MeterConfig,
                                          MeterModels, MeterScalars, MeterSystemInfo, MeterTag,
                                          MeterView, SparkmacNode)
from sparkmeter.meter.meterstate import MeterState
from sparkmeter.misc.jsonutils import json_dumps
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import (EventFactory, GroundFactory, MeterFactory,
                                                MeterModelsFactory, OperatorFactory, ReadingFactory,
                                                TariffFactory, TotalizerMeterFactory,
                                                TransactionFactory, UserFactory)
from sparkmeter.transaction.transactiondomain import Transaction, Wallet


class MeterTest(SparkMeterTestCaseBase):

    def test_get_all_customer_meters(self):
        tariff = TariffFactory(flat_load_limit=50)
        meter = MeterFactory(code=1,
                             config__state=MeterState.STATE_ON.id,
                             tariff=tariff)
        TotalizerMeterFactory(config__subnet=255)
        self.session.commit()
        meters = Meter.get_all_customer_meters()
        assert len(meters) == 1
        assert meters[0].id == meter.id

    def test_get_all_totalizer_meters(self):
        tariff = TariffFactory(flat_load_limit=50)
        MeterFactory(code=1,
                     config__state=MeterState.STATE_ON.id,
                     tariff=tariff)
        totalizer = TotalizerMeterFactory(config__subnet=255)
        self.session.commit()
        meters = Meter.get_all_totalizer_meters()
        assert len(meters) == 1
        assert meters[0].id == totalizer.id

    @log_capture('sparkmeter.meter.meterdomain')
    def test_needs_update(self, logger):
        tariff = TariffFactory(flat_load_limit=50)
        meter = MeterFactory(code=1,
                             config__state=MeterState.STATE_ON.id,
                             tariff=tariff)
        self.session.commit()

        # no update needed
        assert not meter._needs_update(
            current_state=1,
            current_load_limit=50,
            override_meter_state=False)

        # updates needed
        assert meter._needs_update(
            current_state=None,
            current_load_limit=None,
            override_meter_state=False)
        assert meter._needs_update(
            current_state=MeterState.STATE_OFF.id,
            current_load_limit=50,
            override_meter_state=False)
        assert meter._needs_update(
            current_state=MeterState.STATE_ON.id,
            current_load_limit=60,
            override_meter_state=False)

        logger.check(
            ('sparkmeter.meter.meterdomain',
             'INFO',
             u'Meter SM15R-01-00000001 has state and load limit are up to date, '
             u'skipping update.'),
            ('sparkmeter.meter.meterdomain',
             'INFO',
             'Meter SM15R-01-00000001 has unknown current load_limit/state, '
             'requesting update (load_limit=None, state=None).'),
            ('sparkmeter.meter.meterdomain',
             'INFO',
             u'Meter SM15R-01-00000001 has a current state of Off, '
             u'but it should be On, requesting update.'),
            ('sparkmeter.meter.meterdomain',
             'INFO',
             u'Meter SM15R-01-00000001 has a load limit of 60, '
             u'but it should be 50, requesting update.'),
        )

        logger.clear()
        assert meter._needs_update(
            current_state=None,
            current_load_limit=None,
            override_meter_state=True)
        assert meter._needs_update(
            current_state=MeterState.STATE_ON.id,
            current_load_limit=60,
            override_meter_state=True)

        logger.check(
            ('sparkmeter.meter.meterdomain',
             'INFO',
             'Meter SM15R-01-00000001 has unknown current load_limit/state, '
             'requesting update (load_limit=None, state=None).'),
            ('sparkmeter.meter.meterdomain',
             'INFO',
             u'Meter SM15R-01-00000001 has a current state of On, '
             u'but it should be Off (override enabled), requesting update.')
        )

        # Power limits changes are ignored when override is enabled
        assert not meter._needs_update(
            current_state=MeterState.STATE_OFF.id,
            current_load_limit=50,
            override_meter_state=True)

    def test_needs_update_totalizers(self):
        meter = TotalizerMeterFactory(config__subnet=255)
        self.session.commit()
        assert meter._needs_update()
        # Some meters in prod have load limits and states. Ensure we are able
        # to handle this without error
        assert not meter._needs_update(MeterState.STATE_ON.id, current_load_limit=200)

    @log_capture('sparkmeter.meter.meterdomain')
    def test_needs_update_force(self, logger):
        meter = MeterFactory(code=1)
        self.session.commit()
        assert meter._needs_update()

        logger.check(
            ('sparkmeter.meter.meterdomain',
             'INFO',
             'Meter SM15R-01-00000001 is requesting update '
             'by force (load_limit=unset, state=unset).'),
        )

    def test_get_transaction_view(self):
        meter = MeterFactory()
        tr = TransactionFactory(to_wallet=meter.credit_wallet)
        self.session.commit()

        views = meter.get_transaction_view()
        assert views.count() == 1
        assert views.first().TransactionView.id == tr.id
        assert views.first().total == 1

    def test_remove(self):
        meter = MeterFactory()
        TransactionFactory(_to_wallet_meter=meter)
        self.session.commit()

        assert 2 == Address.query.count()
        assert 1 == Customer.query.count()
        assert 1 == Meter.query.count()
        assert 1 == MeterBilling.query.count()
        assert 1 == MeterConfig.query.count()
        assert 1 == MeterSystemInfo.query.count()
        assert 1 == SparkmacNode.query.count()
        assert 1 == Tariff.query.count()
        assert 1 == Transaction.query.count()
        assert 7 == Wallet.query.count()

        meter.remove()
        self.session.commit()

        # transaction creates a ground which has an address
        assert 1 == Address.query.count()
        assert 0 == Customer.query.count()
        assert 0 == Meter.query.count()
        assert 0 == MeterBilling.query.count()
        assert 0 == MeterConfig.query.count()
        assert 0 == MeterSystemInfo.query.count()
        assert 0 == SparkmacNode.query.count()
        # Tariff should not be deleted
        assert 1 == Tariff.query.count()
        assert 0 == Transaction.query.count()
        # meter/transaction factory creates a ground and a vendor, each has two wallets
        assert 4 == Wallet.query.count()

    def test_current_state_text(self):
        meter = MeterFactory()
        assert meter.current_state_text == u'On'

        meter.system_info.current_state = MeterState.STATE_THROTTLE.id
        assert meter.current_state_text == u'Throttle'

        meter.system_info.current_state = 99
        assert meter.current_state_text == u'Unknown'

    def test_send_set_config_unconditionally(self, config, send_set_config):
        config['HEROKU'] = False
        meter = MeterFactory(config__subnet=255)
        meter.send_set_config_unconditionally()
        self.session.commit()
        send_set_config.assert_called_once_with(
            load_limit=50.0,
            subnet=255,
            current_limit=10000.0,
            command='disable',
            mac='1',
            balance=0,
            low_balance=False,
            firmware_version='abc1234')

    def test_send_set_config_unconditionally_same_state(self, send_set_config):
        meter = MeterFactory(system_info__current_state=0, config__state=0)
        self.session.commit()
        meter.send_set_config_based_on_system_info()
        assert send_set_config.mock_calls == []

    def test_send_set_config_based_on_system_info(self, config, send_set_config):
        config['HEROKU'] = False
        meter = MeterFactory(config__subnet=255)
        meter.send_set_config_based_on_system_info()
        send_set_config.assert_called_once_with(
            load_limit=50.0,
            subnet=255,
            current_limit=10000.0,
            command='disable',
            mac='1',
            balance=0,
            low_balance=False,
            firmware_version='abc1234')

    def test_send_set_config_based_on_system_info_totalizer(self, config, send_set_config):
        config['HEROKU'] = False
        meter = TotalizerMeterFactory(config__subnet=255)
        meter.send_set_config_based_on_system_info()
        send_set_config.assert_called_once_with(
            load_limit=65535,
            subnet=255,
            current_limit=10000.0,
            command='disable',
            mac='1',
            balance=0,
            low_balance=False,
            firmware_version='abc1234')

    def test_send_set_config_based_on_system_info_unknown_model(self, config, send_set_config):
        config['HEROKU'] = False
        meter = MeterFactory(serial='SM21R-01-00000000', config__subnet=255, model=None)
        with LogCapture('sparkmeter.meter.meterdomain') as log:
            with pytest.raises(MeterError) as exc_info:
                meter.send_set_config_based_on_system_info()
            assert 'Cannot retrieve attributes' in exc_info.value.message
        log.check(
            ('sparkmeter.meter.meterdomain', 'INFO',
             'Meter SM21R-01-00000000 has unknown current load_limit/state, requesting update '
             '(load_limit=None, state=1).'),)

    def test_send_set_config_load_limit_cap(self, config, session, send_set_config):
        config['HEROKU'] = False
        parameters.NOMINAL_VOLTAGE = 120.0
        tariff = TariffFactory(flat_load_limit=10000)
        meter = MeterFactory(config__subnet=255, tariff=tariff)
        meter.send_set_config_based_on_system_info()
        self.session.commit()
        send_set_config.assert_called_once_with(
            # nominal_voltage * continuous_current * phase_count / power_scalar
            load_limit=120.0 * 20.0 * 1 / 2.0,
            subnet=255,
            current_limit=10000.0,
            command='disable',
            mac='1',
            balance=0,
            low_balance=False,
            firmware_version='abc1234')

    def test_send_set_config_load_phase_consideration(self, config, session, send_set_config):
        config['HEROKU'] = False
        parameters.NOMINAL_VOLTAGE = 120.0
        tariff = TariffFactory(flat_load_limit=10000)
        meter = MeterFactory(config__subnet=255, model__phase_count=3, tariff=tariff)
        meter.send_set_config_based_on_system_info()
        self.session.commit()
        send_set_config.assert_called_once_with(
            # nominal_voltage * continuous_current * phase_count / power_scalar
            load_limit=120.0 * 20.0 * 3 / 2.0,
            subnet=255,
            current_limit=10000.0,
            command='disable',
            mac='1',
            balance=0,
            low_balance=False,
            firmware_version='abc1234')

    def test_send_set_config_based_on_system_info_same_state(self, send_set_config):
        meter = MeterFactory(system_info__current_state=0, config__state=0)
        self.session.commit()
        meter.send_set_config_based_on_system_info()
        assert send_set_config.mock_calls == []

    def test_is_customer_meter(self):
        meter = MeterFactory(meter_type=Meter.TYPE_CUSTOMER)
        assert meter.is_customer_meter()
        meter.meter_type = Meter.TYPE_TOTALIZER
        assert not meter.is_customer_meter()

    def test_is_totalizer_meter(self):
        meter = MeterFactory(meter_type=Meter.TYPE_CUSTOMER)
        assert not meter.is_totalizer_meter()
        meter.meter_type = Meter.TYPE_TOTALIZER
        assert meter.is_totalizer_meter()

    def test_check_can_sell_from_api(self, api_role):
        # make sure api can't sell from meters
        meter = MeterFactory()  # type: Meter
        user = UserFactory(roles=[api_role])
        with pytest.raises(TransactionError) as exc_info:
            meter.check_can_sell_from(user)
        assert str(exc_info.value) == (
            u"user 'testüser-001' cannot repay debt for meter 'SM15R-01-00000001': "
            u"api users cannot repay debt.")

    def test_check_can_sell_from_on_cloud(self, config):
        config.update(HEROKU=True, SERIAL='')
        m2 = GroundFactory()
        self.session.commit()
        meter = MeterFactory()
        meter2 = MeterFactory(ground=m2)
        self.session.commit()
        user = OperatorFactory(grounds=[meter.ground, m2])
        self.session.commit()
        # make sure cloud can sell from all grounds
        meter.check_can_sell_from(user)
        meter2.check_can_sell_from(user)

    def test_check_can_sell_from_ground(self, config):
        meter = MeterFactory()
        user = OperatorFactory(grounds=[meter.ground])
        self.session.commit()
        # make sure ground can't sell from another ground
        config.update(HEROKU=False, SERIAL=meter.serial)
        with pytest.raises(TransactionError) as exc_info:
            meter.check_can_sell_from(user)
        assert str(exc_info.value) == (
            u"user 'testüser-001' cannot repay debt for meter 'SM15R-01-00000001': "
            u"transactions for this meter can only be placed on ground 'test micrøgrid 1'."
        )

        # make sure ground can sell from proper ground
        config.update(HEROKU=False, SERIAL=self.ground.serial)
        meter.check_can_sell_from(user)

    def test_check_can_sell_from_user_permission(self):
        # make sure user without access can't sell from
        meter = MeterFactory()
        user = OperatorFactory()
        self.session.commit()
        with pytest.raises(TransactionError) as exc_info:
            meter.check_can_sell_from(user)
        assert str(exc_info.value) == (
            u"user 'testüser-001' cannot repay debt for meter 'SM15R-01-00000001': "
            u"user is not associated with ground 'test micrøgrid 1'."
        )
        # make sure user with access access can sell from
        user.grounds.append(meter.ground)
        self.session.commit()
        meter.check_can_sell_from(user)

    def test_check_can_sell_to_api(self, api_role):
        meter = MeterFactory()  # type: Meter
        user = UserFactory(roles=[api_role])
        meter.check_can_sell_to(user)

    def test_check_can_sell_to_on_cloud(self, config):
        config.update(HEROKU=True, SERIAL='')
        # make sure cloud can sell to all grounds
        m2 = GroundFactory()
        self.session.commit()
        meter = MeterFactory()
        meter2 = MeterFactory(ground=m2)
        self.session.commit()
        user = OperatorFactory(grounds=[meter.ground, m2])
        self.session.commit()
        # make sure cloud can sell from all grounds
        meter.check_can_sell_to(user)
        meter2.check_can_sell_to(user)

    def test_check_can_sell_to_user_permission(self):
        # make sure user without access can't sell to a meter
        meter = MeterFactory()
        user = OperatorFactory()
        self.session.commit()
        with pytest.raises(TransactionError) as exc_info:
            meter.check_can_sell_to(user)
        assert str(exc_info.value) == (
            u"user 'testüser-001' cannot buy credit for meter 'SM15R-01-00000001': "
            u"user is not associated with ground 'test micrøgrid 1'."
        )

        # make sure user with access access can sell to a meter
        user.grounds.append(meter.ground)
        self.session.commit()
        meter.check_can_sell_to(user)

    def test_override_state_kept(self, config, mocker, send_set_config):
        event_create = mocker.patch('sparkmeter.event.eventdomain.Event.create')
        event_create.return_value = EventFactory()
        parameters.SEND_BROADCAST_SIGNAL = True
        event_create.reset_mock()
        disable_all_meters = mocker.patch('sparkmeter.ground.grounddomain.disable_all_meters')
        tariff = TariffFactory(flat_load_limit=100.0)

        # Change state meter
        m1 = MeterFactory(ground=self.ground,
                          billing__tariff=tariff,
                          system_info__current_user_power_limit=100.0,
                          config__state=MeterConfig.STATE_ON)
        m2 = MeterFactory(ground=self.ground,
                          billing__tariff=tariff,
                          system_info__current_user_power_limit=100.0,
                          config__state=MeterConfig.STATE_OFF)
        m3 = MeterFactory(ground=self.ground,
                          billing__tariff=tariff,
                          system_info__current_user_power_limit=100.0,
                          config__state=MeterConfig.STATE_AUTO,
                          credit_wallet__value=10)  # On
        m4 = MeterFactory(ground=self.ground,
                          billing__tariff=tariff,
                          config__state=MeterConfig.STATE_AUTO,
                          credit_wallet__value=0,
                          system_info__current_user_power_limit=100.0)  # Off
        m5 = MeterFactory(ground=self.ground,
                          billing__tariff=tariff,
                          config__state=MeterConfig.STATE_OFF,
                          credit_wallet__value=10,
                          system_info__current_user_power_limit=100.0)
        # Reset meters
        m6 = MeterFactory(ground=self.ground,
                          billing__tariff=tariff,
                          config__state=MeterConfig.STATE_ON,
                          system_info__current_user_power_limit=100.0)
        m7 = MeterFactory(ground=self.ground,
                          config__state=MeterConfig.STATE_OFF,
                          system_info__current_user_power_limit=100.0)
        m8 = MeterFactory(ground=self.ground,
                          config__state=MeterConfig.STATE_AUTO,
                          credit_wallet__value=10,
                          system_info__current_user_power_limit=100.0)  # On
        m9 = MeterFactory(ground=self.ground,
                          config__state=MeterConfig.STATE_AUTO,
                          credit_wallet__value=0,
                          system_info__current_user_power_limit=100.0)  # Off
        m10 = MeterFactory(ground=self.ground,
                           config__state=MeterConfig.STATE_OFF,
                           credit_wallet__value=10,
                           system_info__current_user_power_limit=100.0)
        # Totalizer, should be ignored
        TotalizerMeterFactory()
        self.session.commit()

        config['HEROKU'] = False
        self.ground.private.set_override_meter_state(True)
        send_set_config.reset_mock()

        # verify meters stays off, indepentent on requested state changes
        m1.config.state = MeterConfig.STATE_OFF  # On -> Off
        m1.send_set_config_based_on_system_info()
        m2.config.state = MeterConfig.STATE_ON   # Off -> On
        m2.send_set_config_based_on_system_info()
        m3.config.state = MeterConfig.STATE_OFF  # Auto On -> Off
        m3.send_set_config_based_on_system_info()
        m4.config.state = MeterConfig.STATE_ON  # Auto Off -> On
        m4.send_set_config_based_on_system_info()
        m5.config.state = MeterConfig.STATE_AUTO  # Off -> Auto On
        m5.send_set_config_based_on_system_info()

        # Reset after override has been enabled
        m6.send_set_config_based_on_system_info()
        m7.send_set_config_based_on_system_info()
        m8.send_set_config_based_on_system_info()
        m9.send_set_config_based_on_system_info()
        m10.send_set_config_based_on_system_info()

        assert send_set_config.mock_calls == [
            mock.call(
                load_limit=50.0,
                subnet=255,
                current_limit=10000.0,
                firmware_version=u'abc1234',
                command='disable',
                balance=balance,
                low_balance=(balance == 0),
                mac=mac)
            for mac, balance in [
                (1, 0.0),
                (2, 0.0),
                (3, 10.0),
                (4, 0.0),
                (5, 10.0),
                (6, 0.0),
                (7, 0.0),
                (8, 10.0),
                (9, 0.0),
                (10, 10.0)
            ]
        ]
        assert disable_all_meters.mock_calls == [mock.call()]

        # Disabling override should take into account changes made while override was enabled
        send_set_config.reset_mock()
        disable_all_meters.reset_mock()
        config['HEROKU'] = False
        self.ground.private.set_override_meter_state(False)

        assert send_set_config.mock_calls == [
            mock.call(
                load_limit=50.0,
                subnet=255,
                current_limit=10000.0,
                firmware_version='abc1234',
                command=cmd,
                balance=balance,
                low_balance=(balance == 0),
                mac=mac)
            for mac, balance, cmd in [
                (1, 0.0, 'disable'),
                (3, 10.0, 'disable'),
                (7, 0.0, 'disable'),
                (9, 0.0, 'disable'),
                (10, 10.0, 'disable'),
                (2, 0.0, 'enable'),
                (4, 0.0, 'enable'),
                (5, 10.0, 'enable'),
                (6, 0.0, 'enable'),
                (8, 10.0, 'enable'),
            ]
        ]
        assert disable_all_meters.mock_calls == []
        assert event_create.mock_calls == []

    def test_apply_scalars(self):
        m = MeterFactory(serial='SM15R-01-00000001')
        m.model = MeterModels.get_by_serial(m.serial)
        self.session.commit()
        data = m.apply_scalars(dict(frequency=1,
                                    energy=1,
                                    power_factor_avg=1,
                                    voltage_min=1,
                                    current_min=1,
                                    user_power_limit=1))
        assert data['frequency'] == 0.01
        assert data['energy'] == 0.00003125
        assert data['power_factor_avg'] == 0.001
        assert data['voltage_min'] == 0.01
        assert data['current_min'] == 0.002
        assert data['user_power_limit'] == 2.0

        m = MeterFactory(serial='SM200E-01-00000001')
        m.model = MeterModels.get_by_serial(m.serial)
        self.session.commit()
        data = m.apply_scalars(dict(frequency=1,
                                    energy=1,
                                    power_factor_avg=1,
                                    voltage_min=1,
                                    current_min=1,
                                    user_power_limit=1))
        assert data['frequency'] == 0.01
        assert data['energy'] == 0.00003125
        assert data['power_factor_avg'] == 0.001
        assert data['voltage_min'] == 0.01
        assert data['current_min'] == 0.004
        assert data['user_power_limit'] == 4.0

    def test_product_code(self):
        m = MeterFactory(serial='SM15R-01-00000001')
        m.model = MeterModels.get_by_serial(m.serial)
        self.session.commit()
        product_code = m.product_code
        assert product_code == 'SM15R'

    def test_maybe_convert_negative_balance_to_debt(self, mocker):
        event_create = mocker.patch('sparkmeter.event.eventdomain.Event.create')
        event_create.return_value = EventFactory()

        meter = MeterFactory(
            config__state=MeterConfig.STATE_AUTO,
            credit_wallet__value=-10,
            debt_wallet__value=5,
        )
        parameters.ALLOW_NEGATIVE_BALANCE = False
        self.session.commit()

        with LogCapture('sparkmeter.meter.meterdomain') as log:
            assert meter.maybe_convert_negative_balance_to_debt()
            assert meter.credit_wallet.value == 0
            assert meter.debt_wallet.value == 15
            log.check(
                ('sparkmeter.meter.meterdomain',
                 'INFO',
                 'Converting -10.0 credit balance for meter SM15R-01-00000001 into debt')
            )
            log.clear()
        meter.credit_wallet.value = -10
        meter.debt_wallet.value = 5

        # State must be auto
        meter.config.state = MeterConfig.STATE_ON
        assert not meter.maybe_convert_negative_balance_to_debt()
        assert meter.credit_wallet.value == -10
        assert meter.debt_wallet.value == 5
        log.check()

        meter.config.state = MeterConfig.STATE_OFF
        assert not meter.maybe_convert_negative_balance_to_debt()
        assert meter.credit_wallet.value == -10
        assert meter.debt_wallet.value == 5
        meter.config.state = MeterConfig.STATE_AUTO
        log.check()

        # Negative balance must be False
        parameters.ALLOW_NEGATIVE_BALANCE = True
        assert not meter.maybe_convert_negative_balance_to_debt()
        assert meter.credit_wallet.value == -10
        assert meter.debt_wallet.value == 5
        parameters.ALLOW_NEGATIVE_BALANCE = False
        log.check()

        # Must have a negative credit
        meter.credit_wallet.value = 0
        assert not meter.maybe_convert_negative_balance_to_debt()
        assert meter.debt_wallet.value == 5
        log.check()

        meter.credit_wallet.value = 100
        assert not meter.maybe_convert_negative_balance_to_debt()
        assert meter.debt_wallet.value == 5
        log.check()

        assert event_create.mock_calls == [
            mock.call('config-parameter-changed',
                      obj=ParameterObject.ALLOW_NEGATIVE_BALANCE.parameter),
            mock.call('config-parameter-changed',
                      obj=ParameterObject.ALLOW_NEGATIVE_BALANCE.parameter),
            mock.call('config-parameter-changed',
                      obj=ParameterObject.ALLOW_NEGATIVE_BALANCE.parameter),
        ]

    def test_get_latest_reading(self):
        meter = MeterFactory()
        reading_instance = ReadingFactory(_meter=meter)
        self.session.commit()

        reading = meter.get_latest_reading()
        assert reading_instance.id == reading.id

    def test_meter_daily_energy_limit_auto_state_values(self):
        with LogCapture('sparkmeter.meter.meterdomain') as logger:

            with freeze_time("2017-01-02 12:34:56"):
                tariff = TariffFactory(
                    flat_load_limit=50,
                    plan_enabled=False,
                    daily_energy_limit_enabled=False,
                    daily_energy_limit_value=100,
                    daily_energy_limit_reset_hour=2,
                )
                meter = MeterFactory(
                    config__state=MeterConfig.STATE_AUTO,
                    credit_wallet__value=10,
                    debt_wallet__value=5,
                    tariff=tariff,
                    billing__last_daily_energy_limit_reset_value=None,
                    billing__last_daily_energy_limit_reset_datetime=None,
                    system_info__last_energy=0,
                )
                meter.billing.last_daily_energy_limit_reset_value = None
                self.session.add(meter.billing)
                self.session.commit()
                assert meter.state_value == MeterConfig.STATE_ON

                # add a daily energy limit to the tariff
                tariff.daily_energy_limit_enabled = True
                self.session.commit()

                # still shows as on because no readings have come in yet so the daily energy limit is not
                # yet take into account with the state_value
                assert meter.state_value == MeterConfig.STATE_ON

                assert meter.current_daily_energy is None

                # verify that both last_daily fields are still None because no reading has come in yet
                assert meter.billing.last_daily_energy_limit_reset_value is None
                assert meter.billing.last_daily_energy_limit_reset_datetime is None

                # First reading on an updated tariff that now has a daily limit
                # this will set the values for the meter billing object
                meter.update_from_reading(ReadingFactory(energy=50))
                self.session.commit()

                # make sure the last_daily values were updated with the info from the reading
                assert meter.billing.last_daily_energy_limit_reset_value == 50
                reset_time = datetime.datetime(2017, 1, 2, 2, 0)
                assert meter.billing.last_daily_energy_limit_reset_datetime == reset_time

                assert meter.state_value == MeterConfig.STATE_ON
                logger.check((
                    'sparkmeter.meter.meterdomain',
                    'INFO',
                    (
                        'Meter SM15R-01-00000001 has crossed the daily energy limit reset time. '
                        'Resetting saved energy value'
                    )
                ))
                logger.clear()

                # use up the rest of the daily energy limit
                meter.update_from_reading(ReadingFactory(energy=1000))
                self.session.commit()
                assert meter.state_value == MeterConfig.STATE_OFF

            # next day the limit should be reset and the meter turned back on
            with freeze_time("2017-01-03 12:34:56"):
                meter.update_from_reading(ReadingFactory(energy=1001))
                self.session.commit()
                assert meter.state_value == MeterConfig.STATE_ON
                logger.check((
                    'sparkmeter.meter.meterdomain',
                    'INFO',
                    (
                        'Meter SM15R-01-00000001 has crossed the daily energy limit reset time. '
                        'Resetting saved energy value'
                    )
                ))
                logger.clear()


class CustomerTest(SparkMeterTestCaseBase):
    def test_phone_number(self):
        c = Customer()
        assert c.national_number is None
        assert c.country_code is None
        assert c.phone_number is None

        c.national_number = '8008000001'
        assert c.national_number == '8008000001'
        assert c.country_code is None
        assert c.phone_number is None

        c.country_code = '1'
        assert c.national_number == '8008000001'
        assert c.country_code == '1'
        assert c.phone_number == '+18008000001'

        c.country_code = '55'
        assert c.national_number == '8008000001'
        assert c.country_code == '55'
        assert c.phone_number == '+558008000001'

        c.national_number = '16991234567'
        assert c.national_number == '16991234567'
        assert c.country_code == '55'
        assert c.phone_number == '+5516991234567'

        c.national_number = None
        assert c.national_number is None
        assert c.country_code == '55'
        assert c.phone_number is None

        c.country_code = None
        assert c.national_number is None
        assert c.country_code is None
        assert c.phone_number is None


class MeterViewTest(SparkMeterTestCaseBase):

    @freeze_time("2017-01-01 12:34:56")
    def test_select(self):
        MeterFactory()
        TotalizerMeterFactory()
        MeterFactory()
        tag = MeterTag(name='existing-tag')
        self.session.add(tag)
        self.session.commit()
        self.verify_meter_views()

    def test_insert_customer_meter(self):
        m = MeterView()
        m.active = True
        m.address_city = 'City'
        m.address_coords = '1,2'
        m.address_country = 'Country'
        m.address_postalcode = '12345'
        m.address_state = 'State'
        m.address_street1 = 'Street1'
        m.address_street2 = 'Street2'
        m.code = 2
        m.current_state = MeterState.STATE_ON.id
        m.customer_code = 'code 123'
        m.customer_name = 'Customer name'
        m.customer_phone_number = '+551633710123'
        m.customer_phone_number_verified = True
        m.credit_value = 123
        m.debt_value = 456
        m.ground = self.ground
        m.meter_type = Meter.TYPE_CUSTOMER
        m.plan_value = 789
        m.is_running_plan = True
        m.last_cycle_start = datetime.datetime(2017, 1, 1, 12, 00, 00)
        m.last_energy = 1138
        m.last_energy_datetime = datetime.datetime(2017, 1, 1, 12, 34, 56)
        m.last_plan_payment_date = datetime.datetime(2017, 1, 1, 12, 00, 00)
        m.serial = 'SM15R-01-10000002'
        m.model = MeterModelsFactory()
        m.state = MeterConfig.STATE_AUTO
        m.subnet = 127
        m.tags = ['existing-tag']
        m.tariff = TariffFactory()
        m.total_cycle_energy = 10
        assert m.is_customer_meter()
        self.session.add(m)
        self.session.commit()
        self.verify_meter_views()

    def test_insert_totalizer_meter(self):
        m = MeterView()
        m.active = True
        m.address_city = 'City'
        m.address_coords = '1,2'
        m.address_country = 'Country'
        m.address_postalcode = '12345'
        m.address_state = 'State'
        m.address_street1 = 'Street1'
        m.address_street2 = 'Street2'
        m.code = 2
        m.current_state = MeterState.STATE_ON.id
        m.ground = self.ground
        m.meter_type = Meter.TYPE_TOTALIZER
        m.last_energy = 1138
        m.last_energy_datetime = datetime.datetime(2017, 1, 1, 12, 34, 56)
        m.serial = 'SM15R-01-10000002'
        m.model = MeterModelsFactory()
        m.state = MeterConfig.STATE_AUTO
        m.subnet = 127
        m.tags = ['existing-tag']
        assert m.is_totalizer_meter()
        self.session.add(m)
        self.session.commit()
        self.verify_meter_views()

    def test_update_customer_meter(self):
        MeterFactory()
        self.session.commit()
        m = MeterView.get_view()[0]
        m.active = True
        m.address_city = 'City'
        m.address_coords = '1,2'
        m.address_country = 'Country'
        m.address_postalcode = '12345'
        m.address_state = 'State'
        m.address_street1 = 'Street1'
        m.address_street2 = 'Street2'
        m.code = 2
        m.credit_value = 123
        m.current_state = MeterState.STATE_ON.id
        m.customer_code = 'code 123'
        m.customer_name = 'Customer name'
        m.customer_phone_number = '+551633710123'
        m.customer_phone_number_verified = True
        m.debt_value = 456
        m.ground = self.ground
        m.is_running_plan = True
        m.last_cycle_start = datetime.datetime(2017, 1, 1, 12, 00, 00)
        m.last_energy = 1138
        m.last_energy_datetime = datetime.datetime(2017, 1, 1, 12, 34, 56)
        m.last_plan_payment_date = datetime.datetime(2017, 1, 1, 00, 00, 00)
        m.meter_type = Meter.TYPE_CUSTOMER
        m.plan_value = 789
        m.serial = 'SM15R-01-10000002'
        m.state = MeterConfig.STATE_AUTO
        m.subnet = 127
        m.tags = ['existing-tag']
        m.tariff = TariffFactory()
        m.total_cycle_energy = 10
        self.session.add(m)
        self.session.commit()
        self.verify_meter_views()

    def test_reset_customer_meter(self):
        MeterFactory()
        self.session.commit()
        m = MeterView.get_view()[0]
        m.address_city = None
        m.address_coords = None
        m.address_country = None
        m.address_postalcode = None
        m.address_state = None
        m.address_street1 = None
        m.address_street2 = None
        m.customer_code = None
        m.customer_name = None
        m.customer_phone_number = None
        m.customer_phone_number_verified = None
        m.ground = self.ground
        m.is_running_plan = True
        m.last_cycle_start = None
        m.last_energy = None
        m.last_energy_datetime = None
        m.last_plan_payment_date = None
        m.tags = None
        m.total_cycle_energy = None
        self.session.add(m)
        self.session.commit()
        self.verify_meter_views()

    def test_update_totalizer_meter(self):
        TotalizerMeterFactory()
        self.session.commit()
        m = MeterView.get_view()[0]
        m.active = True
        m.address_city = 'City'
        m.address_coords = '1,2'
        m.address_country = 'Country'
        m.address_postalcode = '12345'
        m.address_state = 'State'
        m.address_street1 = 'Street1'
        m.address_street2 = 'Street2'
        m.code = 2
        m.current_state = MeterState.STATE_ON.id
        m.ground = self.ground
        m.meter_type = Meter.TYPE_TOTALIZER
        m.last_energy_datetime = datetime.datetime(2017, 1, 1, 12, 34, 56)
        m.serial = 'SM15R-01-10000002'
        m.state = MeterConfig.STATE_AUTO
        m.subnet = 127
        m.tags = ['existing-tag']
        m.tariff = None
        self.session.add(m)
        self.session.commit()
        self.verify_meter_views()

    def serialize_meter_view(self, meter_view):
        d = dict(meter_view._data)
        d['id'] = '%% METER ID %%'
        if d['customer_id'] is not None:
            d['customer_id'] = '%% CUSTOMER ID %%'
        return d

    def verify_meter_views(self):
        body = []
        for meter_view in MeterView.get_view():
            body.append(self.serialize_meter_view(meter_view))
        self.verify_json_content(json_dumps(body), frame=2)


class MeterSystemInfoTest(SparkMeterTestCaseBase):
    def test_update_from_set_config(self):
        m = MeterFactory()
        self.session.commit()
        system_info = m.system_info
        system_info.update_from_set_config(
            command='enable',
            application_version='app-ver',
            bootloader_version='boot-ver',
            power_limit=100)
        assert system_info.current_state == MeterConfig.STATE_ON
        assert system_info.firmware == 'app-ver'
        assert system_info.bootloader == 'boot-ver'
        assert system_info.current_user_power_limit == 200

        system_info.update_from_set_config(
            command='disable',
            application_version='app-ver-2',
            bootloader_version='boot-ver-2',
            power_limit=200)
        assert system_info.current_state == MeterConfig.STATE_OFF
        assert system_info.firmware == 'app-ver-2'
        assert system_info.bootloader == 'boot-ver-2'
        assert system_info.current_user_power_limit == 400

    def test_update_from_set_config_missing_scalars(self):
        m = MeterFactory(model=None)
        self.session.commit()
        with pytest.raises(MeterError) as exc_info:
            m.system_info.update_from_set_config(
                command='enable',
                application_version='app-ver',
                bootloader_version='boot-ver',
                power_limit=100)
        assert exc_info.value.code == MeterError.UNKNOWN_MODEL


class MeterModelsTest(SparkMeterTestCaseBase):
    def test_get_scalars_by_name(self):
        scalars = MeterScalars.get_by_name('2x')
        assert scalars.name == '2x'

    def test_get_model_by_name(self):
        model = MeterModels.get_by_name('SM5R')
        assert model.name == 'SM5R'

    def test_get_model_by_name_unknown(self):
        model = MeterModels.get_by_name('SM7R')
        assert model is None

    def test_get_model_by_name_disabled(self):
        model = MeterModels.get_by_name('SM20XR')
        assert model is None
        model = MeterModels.get_by_name('SM20XR', include_disabled=True)
        assert model.name == 'SM20XR'

    def test_get_model_by_serial(self):
        model = MeterModels.get_by_serial('SM15R-01-10000002')
        assert model.name == 'SM15R'

    def test_get_model_by_serial_malformed(self):
        with pytest.raises(MeterError) as merr:
            MeterModels.get_by_serial('SM15R-01-1000002')
        assert merr.value.code == MeterError.INVALID_SERIAL

    def test_get_model_by_serial_unknown(self):
        model = MeterModels.get_by_serial('SM2R-01-10000002')
        assert model is None

    def test_get_model_by_serial_disabled(self):
        model = MeterModels.get_by_serial('SM20XR-01-10000002')
        assert model is None
        model = MeterModels.get_by_serial('SM20XR-01-10000002', include_disabled=True)
        assert model.name == 'SM20XR'

    def test_get_lowest_inrush_current(self):
        lowest = MeterModels.get_lowest_inrush_current()
        assert lowest == 12.0
