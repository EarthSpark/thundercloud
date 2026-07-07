# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import calendar
import datetime
import http.client
import urllib.parse
from builtins import range, str
from unittest import mock

import pytest
from dateutil.tz import tzutc
from freezegun import freeze_time

from sparkmeter.event.eventdomain import Event, SMSMessage
from sparkmeter.exceptions import MeterError
from sparkmeter.meter.meterdomain import Meter, MeterConfig, MetersTags, MeterTag
from sparkmeter.tests.base import WebViewTestCaseBase
from sparkmeter.tests.test_data_factory import (EventFactory, GroundFactory, MeterFactory,
                                                OperatorFactory, ReadingFactory, SMSMessageFactory,
                                                TariffFactory, TotalizerMeterFactory,
                                                TransactionFactory, VendorFactory)
from sparkmeter.transaction.transactiondomain import Transaction


@pytest.fixture(scope="module", autouse=True)
def _setup(app):
    with mock.patch.dict(app.config, dict(HEROKU=False)):
        yield


@pytest.fixture(scope="function")
def MeterView(mocker):
    yield mocker.patch('sparkmeter.meter.meterform.MeterView')


@pytest.fixture()
def current_user(mocker):
    yield mocker.patch('sparkmeter.web.permission.current_user')


class MeterViewTest(WebViewTestCaseBase):

    def test_add(self, client, send_set_config):
        path = "/meter/add-meter"
        response = client.get(path)
        self.verify_response(response)

        tariff = TariffFactory()
        self.session.commit()

        data = {
            'customer_code': '1',
            'customer_national_number': '8008374966',
            'serial': 'SM15R-01-0000007B',
            'state': '0',
            'subnet': '1',
            'tariff': tariff.id,
        }
        response = client.post(path, data=data, follow_redirects=True)
        meters = list(self.ground.get_meters())
        assert len(meters) == 1
        meter = meters[0]
        self.verify_response(response, variant='post',
                             ignore_values=[
                                 str(meter.id),
                                 str(meter.system_info.last_energy_datetime),
                             ])
        assert meter.meter_type == Meter.TYPE_CUSTOMER
        assert meter.code == 123
        assert meter.serial == 'SM15R-01-0000007B'
        assert meter.config.state == 0
        assert meter.config.subnet == 1
        assert meter.tariff.id == tariff.id
        assert meter.credit_wallet
        assert meter.debt_wallet
        assert meter.plan_wallet
        assert meter.sparkmac.forwarding == 'flooding'

        assert send_set_config.mock_calls == [
            mock.call(
                load_limit=50.0,
                subnet=1,
                current_limit=10000.0,
                command='disable',
                mac=123,
                balance=0,
                low_balance=True,
                firmware_version=None),
        ]

    def test_add_from_cloud(self, client, config):
        config.update(HEROKU=True)
        path = "/meter/add-meter"
        response = client.get(path)
        self.verify_response(response)

        tariff = TariffFactory()
        self.session.commit()

        data = {
            'customer_code': '1',
            'customer_national_number': '8008374966',
            'serial': 'SM15R-01-0000007B',
            'state': '0',
            'subnet': '1',
            'tariff': tariff.id,
        }
        response = client.post(path, data=data, follow_redirects=True)
        meters = list(self.ground.get_meters())
        assert len(meters) == 1
        meter = meters[0]
        self.verify_response(response, variant='post',
                             ignore_values=[
                                 str(meter.id),
                                 str(meter.system_info.last_energy_datetime),
                             ])
        assert meter.meter_type == Meter.TYPE_CUSTOMER
        assert meter.code == 123
        assert meter.serial == 'SM15R-01-0000007B'
        assert meter.config.state == 0
        assert meter.config.subnet == 1
        assert meter.tariff.id == tariff.id
        assert meter.credit_wallet
        assert meter.debt_wallet
        assert meter.plan_wallet
        assert meter.sparkmac.forwarding == 'flooding'

    def test_add_totalizer(self, client, config, send_set_config):
        path = "/meter/add-meter/totalizer"
        self.verify_response(client.get(path))

        data = {
            'subnet': 1,
            'serial': 'sm15r-01-0000007B',
        }
        response = client.post(path, data=data, follow_redirects=True)
        config['HEROKU'] = False
        meters = list(self.ground.get_meters())
        assert len(meters) == 1
        meter = meters[0]
        self.verify_response(response, variant='post',
                             ignore_values=[
                                 str(meter.id),
                                 str(meter.system_info.last_energy_datetime),
                             ])
        assert ' created.' in response.text
        assert meter.meter_type == Meter.TYPE_TOTALIZER
        assert meter.code == 123
        assert meter.serial == 'SM15R-01-0000007B'
        assert meter.config.state == 0
        assert meter.config.subnet == 1
        assert meter.billing is None
        assert meter.customer is None
        assert meter.credit_wallet is None
        assert meter.debt_wallet is None
        assert meter.plan_wallet is None
        assert meter.sparkmac.forwarding == 'flooding'

        assert send_set_config.mock_calls == [
            mock.call(
                load_limit=65535,
                subnet=1,
                current_limit=10000.0,
                command='disable',
                mac=123,
                balance=0,
                low_balance=False,
                firmware_version=None),
        ]

    def test_add_totalizer_from_cloud(self, client, config, send_set_config):
        path = "/meter/add-meter/totalizer"
        config.update(HEROKU=True)
        self.verify_response(client.get(path))

        data = {
            'subnet': 1,
            'serial': 'sm15r-01-0000007B',
        }
        response = client.post(path, data=data, follow_redirects=True)
        # config['HEROKU'] = False
        meters = list(self.ground.get_meters())
        assert len(meters) == 1
        meter = meters[0]
        self.verify_response(response, variant='post',
                             ignore_values=[
                                 str(meter.id),
                                 str(meter.system_info.last_energy_datetime),
                             ])
        assert ' created.' in response.text
        assert meter.meter_type == Meter.TYPE_TOTALIZER
        assert meter.code == 123
        assert meter.serial == 'SM15R-01-0000007B'
        assert meter.config.state == 0
        assert meter.config.subnet == 1
        assert meter.billing is None
        assert meter.customer is None
        assert meter.credit_wallet is None
        assert meter.debt_wallet is None
        assert meter.plan_wallet is None
        assert meter.sparkmac.forwarding == 'flooding'

    def test_add_invalid(self, client):
        path = "/meter/add-meter/invalid"
        response = client.post(path)
        self.verify_response(response)

    def test_add_duplicated_serial(self, client):
        tariff = TariffFactory()
        self.session.commit()

        data = {
            'tariff': tariff.id,
            'serial': 'SM15R-01-0000007B',
            'state': 0,
        }
        MeterFactory(serial='SM15R-01-0000007B')
        self.session.commit()

        path = "/meter/add-meter"
        response = client.post(path, data=data)
        assert 'Meter serial SM15R-01-0000007B already exists.' in response.text
        self.verify_response(response)

    def test_add_unknown_model(self, client):
        tariff = TariffFactory()
        self.session.commit()

        data = {
            'tariff': tariff.id,
            'serial': 'SM2R-01-0000007B',
            'state': 0,
        }

        path = "/meter/add-meter"
        response = client.post(path, data=data)
        assert 'The serial is not associated with a known model' in response.text
        self.verify_response(response)

    def test_add_invalid_serial(self, client):
        tariff = TariffFactory()
        self.session.commit()

        data = {
            'tariff': tariff.id,
            'serial': 'invalid-serial',
            'state': 0,
        }
        path = "/meter/add-meter"
        response = client.post(path, data=data)
        self.verify_response(response, variant='invalid-serial')
        assert 'Invalid meter serial, must look like "SMXXX-XX-XXXXXXXX".' in response.text

        response = client.post(path, data=dict(serial='SM15R-01-000000000'))
        assert 'Invalid meter serial, must look like "SMXXX-XX-XXXXXXXX".' in response.text
        self.verify_response(response)

    def test_add_32_bit_serial(self, config, client, send_set_config):
        config['HEROKU'] = False
        path = "/meter/add-meter"
        response = client.get(path)
        self.verify_response(response)

        tariff = TariffFactory()
        self.session.commit()

        data = {
            'customer_code': '1',
            'customer_national_number': '8008374966',
            'serial': 'SM15R-01-0001007B',
            'state': '0',
            'subnet': '1',
            'tariff': tariff.id,
        }
        response = client.post(path, data=data, follow_redirects=True)
        meters = list(self.ground.get_meters())
        assert len(meters) == 1
        meter = meters[0]
        self.verify_response(response, variant='post',
                             ignore_values=[
                                 str(meter.id),
                                 str(meter.system_info.last_energy_datetime),
                             ])
        assert meter.meter_type == Meter.TYPE_CUSTOMER
        assert meter.serial == 'SM15R-01-0001007B'
        assert meter.code == 123
        assert meter.config.state == 0
        assert meter.config.subnet == 1
        assert meter.tariff.id == tariff.id
        assert meter.credit_wallet
        assert meter.debt_wallet
        assert meter.plan_wallet
        assert meter.sparkmac.forwarding == 'flooding'

        assert send_set_config.mock_calls == [
            mock.call(
                load_limit=50.0,
                subnet=1,
                current_limit=10000.0,
                command='disable',
                mac=123,
                balance=0,
                low_balance=True,
                firmware_version=None),
        ]

    def test_unknown_server_error(self, client, MeterView):
        MeterView.validate_serial.side_effect = MeterError(
            'unknown', 'Unknown message')
        path = "/meter/add-meter/totalizer"
        data = {
            'subnet': 1,
            'serial': 'SM15R-01-0000007B',
        }
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)

    def test_add_empty_phone_number(self, client):
        data = {
            'customer_country_code': '55',
            'customer_national_number': '',
            'serial': 'SM15R-01-0000007B',
        }
        path = "/meter/add-meter"
        response = client.post(path, data=data)
        self.verify_response(response)

    def test_add_empty_country_code(self, client):
        data = {
            'customer_national_number': '8008374966',
            'serial': 'SM15R-01-0000007B',
        }
        path = "/meter/add-meter"
        response = client.post(path, data=data)
        self.verify_response(response)

    def test_add_invalid_phone_number(self, client):
        data = {
            'customer_country_code': '55',
            'customer_national_number': '1',
            'serial': 'SM15R-01-0000007B',
        }
        path = "/meter/add-meter"
        response = client.post(path, data=data)
        assert '1 is not a valid national phone number for Brazil' in response.text
        self.verify_response(response)

    def test_add_unauthorized_user(self, client, vendor_role, send_set_config):
        path = "/meter/add-meter"

        tariff = TariffFactory()
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()

        client.login_as(vendor)

        data = {
            'customer_code': '1',
            'customer_national_number': '8008374966',
            'serial': 'SM15R-01-0000007B',
            'state': '0',
            'subnet': '1',
            'tariff': tariff.id,
        }

        response = client.post(path, data=data, follow_redirects=True)
        assert response.status_code in (http.client.OK, http.client.FORBIDDEN)

    @freeze_time("2013-01-01T01:01:01")
    def test_view_ground(self, client, config):
        meter = MeterFactory()
        trans = TransactionFactory(state=Transaction.STATE_PROCESSED, error=None)
        trans.to_wallet = meter.credit_wallet
        trans = TransactionFactory(state=Transaction.STATE_PENDING, error=None)
        trans.to_wallet = meter.credit_wallet
        trans = TransactionFactory(state=Transaction.STATE_ERROR, error='an error')
        trans.to_wallet = meter.credit_wallet
        self.session.commit()

        path = "/meter/" + meter.serial + '/'
        config['HEROKU'] = False
        response = client.get(path)
        self.verify_response(response)

    def test_view_ground_error_state(self, client, config):
        meter = MeterFactory(system_info__current_state=3)
        self.session.commit()

        path = "/meter/" + meter.serial + '/'
        config['HEROKU'] = False
        response = client.get(path)
        self.verify_response(response)

    def test_view_cloud(self, client, config):
        meter = MeterFactory(
            system_info__last_config_datetime=datetime.datetime(2010, 1, 1))
        self.session.commit()

        path = "/meter/" + meter.serial + '/'
        config['HEROKU'] = True
        response = client.get(path)
        self.verify_response(response)

    def test_view_totalizer(self, client, config):
        meter = TotalizerMeterFactory()
        self.session.commit()

        path = "/meter/" + meter.serial + '/'
        config['HEROKU'] = False
        response = client.get(path)
        self.verify_response(response)

    @freeze_time("2013-01-01T01:01:01")
    def test_view_phone_number_verified(self, client, config):
        meter = MeterFactory(customer__phone_number_verified=False)
        self.session.commit()

        assert not meter.customer.verification_message_sent()

        path = "/meter/" + meter.serial + '/'
        config['HEROKU'] = False
        response = client.get(path)
        self.verify_response(response, variant='phone-number-not-verified')

        message = meter.customer.send_phone_number_verification()
        self.session.add(message)
        self.session.commit()
        assert meter.customer.verification_message_sent()

        response = client.get(path)
        self.verify_response(response, variant='phone-number-verified')

    def test_view_not_found(self, client):
        path = "/meter/invalid-serial/"
        response = client.get(path)
        self.verify_response(response)

    def test_view_forbidden(self, client, vendor_role):
        vendor = VendorFactory(roles=[vendor_role])
        meter = TotalizerMeterFactory()
        self.session.commit()
        client.login_as(vendor)

        path = "/meter/" + meter.serial + "/"
        response = client.get(path)
        self.verify_response(response)

    @freeze_time("2015-03-11")
    def test_chart_customer(self, client):
        meter = MeterFactory()
        self.session.commit()

        path = "/meter/" + meter.serial + '/chart'
        response = client.get(path)
        self.verify_response(response, variant='customer')

    @freeze_time("2015-03-11")
    def test_chart_totalizer(self, client):
        meter = TotalizerMeterFactory()
        self.session.commit()

        path = "/meter/" + meter.serial + '/chart'
        response = client.get(path)
        self.verify_response(response, variant='totalizer')

    def test_chart_not_found(self, client):
        path = "/meter/invalid-serial/chart"
        response = client.get(path)
        self.verify_response(response)

    def test_chart_forbidden(self, client, vendor_role):
        vendor = VendorFactory(roles=[vendor_role])
        meter = TotalizerMeterFactory()
        self.session.commit()
        client.login_as(vendor)

        path = "/meter/" + meter.serial + "/chart"
        response = client.get(path)
        self.verify_response(response)

    @freeze_time("2015-03-11")
    @mock.patch('sparkmeter.meter.meterview.tzlocal', tzutc)
    @mock.patch('vincent.data.time.mktime', calendar.timegm)
    def test_chart_data(self, client):
        # JSON format
        meter = MeterFactory()
        dt = datetime.datetime(2015, 3, 10)
        for reading in range(3):
            start = dt
            dt += datetime.timedelta(minutes=15)
            end = dt
            ReadingFactory(heartbeat_start=start, heartbeat_end=end,
                           _meter=None, meter=str(meter.code))
        self.session.commit()

        data = {
            'group_by': 'none',
            'group_by_function': 'sum',
            'fields': 'true_power_inst',
            'start': "2015-03-9",
            'end': "2015-03-11",
        }
        path = "/meter/" + meter.serial + '/chart/data.json'
        path_with_data = "%s?%s" % (path, urllib.parse.urlencode(data))
        response = client.get(path_with_data)
        self.verify_response(response, variant='json')

        # CSV format
        path = "/meter/" + meter.serial + '/chart/data.csv'
        path_with_data = "%s?%s" % (path, urllib.parse.urlencode(data))
        response = client.get(path_with_data)
        self.verify_response(response, variant='csv')

        # Unsupported/invalid data format
        path = "/meter/" + meter.serial + '/chart/data.invalid'
        path_with_data = "%s?%s" % (path, urllib.parse.urlencode(data))
        response = client.get(path_with_data)
        self.verify_response(response, variant='invalid')

    def test_chart_data_not_found(self, client):
        path = "/meter/invalid-serial/chart/data.json"
        response = client.get(path)
        assert response.status_code == http.client.NOT_FOUND

    def test_chart_data_forbidden(self, client, vendor_role):
        vendor = VendorFactory(roles=[vendor_role])
        meter = TotalizerMeterFactory()
        self.session.commit()
        client.login_as(vendor)

        path = "/meter/" + meter.serial + "/chart/data.json"
        response = client.get(path)
        self.verify_response(response)

    @freeze_time("2015-03-11")
    @mock.patch('sparkmeter.meter.meterview.tzlocal', tzutc)
    @mock.patch('vincent.data.time.mktime', calendar.timegm)
    def test_chart_data_group_by(self, client):
        meter = MeterFactory()
        dt = datetime.datetime(2015, 3, 10)
        for reading in range(3):
            start = dt
            dt += datetime.timedelta(minutes=15)
            end = dt
            ReadingFactory(heartbeat_start=start,
                           heartbeat_end=end,
                           energy=reading * 10,
                           meter=str(meter.code))
        self.session.commit()

        data = {
            'group_by': 'D',
            'group_by_function': 'sum',
            'fields': 'energy',
            'start': "2015-03-9",
            'end': "2015-03-11",
        }
        path = "/meter/%s/chart/data.json"
        response = client.get(path % (meter.serial, ) + "?" + urllib.parse.urlencode(data))
        self.verify_response(response, variant='group_by')

    @freeze_time("2015-03-11")
    def test_chart_data_group_by_bad_function(self, client):
        meter = MeterFactory()
        self.session.commit()

        data = {
            'group_by': 'D',
            'group_by_function': 'invalid',
            'fields': 'energy',
            'start': "2015-03-9",
            'end': "2015-03-11",
        }
        path = "/meter/" + meter.serial + '/chart/data.json'
        response = client.get(path + "?" + urllib.parse.urlencode(data))
        self.verify_response(response)

    def test_edit_customer(self, client, config):
        tariff = TariffFactory()
        meter = MeterFactory(customer__phone_number=None, billing__tariff=tariff)
        self.session.commit()

        path = "/meter/" + meter.serial + "/edit"
        data = {
            'tariff': tariff.id,
            'state': meter.config.state,
            'customer_code': '1234',
            'customer_country_code': '55',
            'customer_national_number': '1633710001',
        }
        config['HEROKU'] = True
        response = client.post(path, data=data)
        self.verify_response(response)
        meter = Meter.get_by_serial(meter.serial)
        assert meter.customer is not None
        assert meter.customer.code == '1234'
        assert meter.customer.phone_number == '+551633710001'

    def test_edit_customer_state_cloud(self, client, config):
        tariff = TariffFactory()
        meter = MeterFactory(config__state=MeterConfig.STATE_ON, billing__tariff=tariff)
        self.session.commit()

        path = "/meter/" + meter.serial + "/edit"
        response = client.get(path)
        self.verify_response(response, variant='customer-state-cloud')

        data = {
            'tariff': tariff.id,
            'state': str(MeterConfig.STATE_OFF),
        }
        config['HEROKU'] = True
        response = client.post(path, data=data)
        self.verify_response(response)
        assert meter.config.state == MeterConfig.STATE_OFF
        events = Event.query.all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == Event.TYPE_METER_STATE_CHANGED
        assert event.object.id == meter.id
        assert not event.processed

    def test_edit_customer_state_ground(self, client, config, send_set_config):
        tariff = TariffFactory()
        meter = MeterFactory(config__state=MeterConfig.STATE_ON, billing__tariff=tariff)
        self.session.commit()

        path = "/meter/" + meter.serial + "/edit"
        response = client.get(path)
        self.verify_response(response, variant='customer-state-ground')

        data = {
            'state': str(MeterConfig.STATE_OFF),
            'tariff': tariff.id,
        }
        config['HEROKU'] = False
        response = client.post(path, data=data)
        self.verify_response(response)
        assert meter.config.state == MeterConfig.STATE_OFF
        events = Event.query.all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == Event.TYPE_METER_STATE_CHANGED
        assert event.object.id == meter.id
        assert event.processed

        assert send_set_config.mock_calls == [
            mock.call(
                subnet=255,
                current_limit=10000.0,
                load_limit=50.0,
                mac=1,
                command='enable',
                balance=0,
                low_balance=True,
                firmware_version=u'abc1234'),
        ]

    def test_edit_customer_tariff_cloud(self, client, config):
        tariff1 = TariffFactory()
        tariff2 = TariffFactory()
        meter = MeterFactory(tariff=tariff1)
        self.session.commit()

        path = "/meter/" + meter.serial + "/edit"
        response = client.get(path)
        self.verify_response(response, variant='customer-tariff-cloud')

        data = {
            'state': str(MeterConfig.STATE_OFF),
            'tariff': str(tariff2.id),
        }
        config['HEROKU'] = True
        response = client.post(path, data=data)
        self.verify_response(response)
        assert meter.tariff.id == tariff2.id
        events = Event.query.all()
        assert len(events) == 2
        event = events[0]
        assert event.event_type == Event.TYPE_METER_STATE_CHANGED
        assert event.object.id == meter.id
        assert not event.processed
        event = events[1]
        assert event.event_type == Event.TYPE_METER_TARIFF_CHANGED
        assert event.object.id == meter.id
        assert not event.processed

    def test_edit_customer_tariff_ground(self, client, config, send_set_config):
        tariff1 = TariffFactory()
        tariff2 = TariffFactory()
        meter = MeterFactory(tariff=tariff1)
        self.session.commit()

        path = "/meter/" + meter.serial + "/edit"

        data = {
            'state': str(MeterConfig.STATE_OFF),
            'tariff': str(tariff2.id),
        }
        config['HEROKU'] = False
        response = client.post(path, data=data)
        self.verify_response(response)
        assert meter.tariff.id == tariff2.id
        events = Event.query.all()
        assert len(events) == 2
        event = events[0]
        assert event.event_type == Event.TYPE_METER_STATE_CHANGED
        assert event.object.id == meter.id
        assert event.processed
        event = events[1]
        assert event.event_type == Event.TYPE_METER_TARIFF_CHANGED
        assert event.object.id == meter.id
        assert event.processed
        assert send_set_config.mock_calls == [
            mock.call(
                subnet=255,
                current_limit=10000.0,
                load_limit=50.0,
                mac=1,
                command='disable',
                balance=0,
                low_balance=True,
                firmware_version=u'abc1234'),
            mock.call(
                subnet=255,
                current_limit=10000.0,
                load_limit=50.0,
                mac=1,
                command='disable',
                balance=0,
                low_balance=True,
                firmware_version=u'abc1234'),
        ]

    def test_edit_customer_active(self, client):
        meter = MeterFactory(config__hidden=False)
        self.session.commit()

        assert meter.config.active
        assert not meter.config.hidden

        path = "/meter/" + meter.serial + "/edit"

        data = {
            'tariff': meter.billing.tariff.id,
            'serial': meter.serial,
            'state': meter.config.state,
        }
        response = client.post(path, data=data)
        self.verify_response(response, variant='archived')
        assert not meter.config.active
        assert meter.config.hidden

        data = {
            'active': 'y',
            'customer_country_code': '55',
            'customer_national_number': '1633710001',
            'tariff': meter.billing.tariff.id,
            'serial': meter.serial,
            'state': meter.config.state,
        }
        response = client.post(path, data=data)
        self.verify_response(response, variant='active')
        assert meter.config.active
        assert not meter.config.hidden

    def test_edit_totalizer(self, client, config):
        meter = TotalizerMeterFactory()
        self.session.commit()

        path = "/meter/" + meter.serial + "/edit"
        response = client.get(path)
        self.verify_response(response)

        data = {}
        config['HEROKU'] = True
        response = client.post(path, data=data)
        self.verify_response(response, variant='post')

    def test_edit_with_tags(self, client, config):
        tariff = TariffFactory()
        meter = MeterFactory(
            billing__tariff=tariff)
        tag = MeterTag(name='existing-tag')
        self.session.add(tag)
        self.session.commit()

        path = "/meter/" + meter.serial + "/edit"
        response = client.get(path)
        self.verify_response(response)

        # Add an existing tag
        data = {
            'customer_country_code': '55',
            'customer_national_number': '1633710001',
            'tariff': tariff.id,
            'state': str(MeterConfig.STATE_OFF),
            'tags': ['existing-tag'],
        }
        config['HEROKU'] = True
        response = client.post(path, data=data)
        self.verify_response(response, variant='add-existing')
        assert [u'existing-tag'] == [t.name for t in meter.tags]
        assert MetersTags.query.count() == 1
        assert MeterTag.query.count() == 1

        # Add a new tag
        data['tags'] = ['existing-tag', 'new-tag']
        config['HEROKU'] = True
        response = client.post(path, data=data)
        self.verify_response(response, variant='add-new')

        assert sorted([u'existing-tag', u'new-tag']) == sorted([t.name for t in meter.tags])
        assert MetersTags.query.count() == 2
        assert MeterTag.query.count() == 2

        # Remove a tag
        data['tags'] = ['new-tag']
        config['HEROKU'] = True
        response = client.post(path, data=data)
        self.verify_response(response, variant='remove')

        assert sorted([u'new-tag']) == sorted([t.name for t in meter.tags])
        assert MetersTags.query.count() == 2
        assert MeterTag.query.count() == 2

        response = client.post(path, data=data)
        assert response.status_code == http.client.FOUND

        # Re-Add a tag
        data['tags'] = ['existing-tag', 'new-tag']
        config['HEROKU'] = True
        response = client.post(path, data=data)
        self.verify_response(response, variant='readd')

        assert sorted([u'existing-tag', u'new-tag']) == sorted([t.name for t in meter.tags])
        assert MetersTags.query.count() == 2
        assert MeterTag.query.count() == 2

        # Prepopulate tags
        response = client.get(path)
        self.verify_response(response, variant='prepopulate')

    def test_edit_not_found(self, client):
        path = "/meter/invalid-serial/edit"
        response = client.get(path)
        self.verify_response(response)

    def test_edit_forbidden(self, client, vendor_role):
        vendor = VendorFactory(roles=[vendor_role])
        meter = TotalizerMeterFactory()
        self.session.commit()
        client.login_as(vendor)

        path = "/meter/" + meter.serial + "/edit"
        response = client.get(path)
        self.verify_response(response)

    def test_set_state_on(self, client):
        meter = MeterFactory(config__state=0)
        self.session.commit()

        path = "/meter/" + meter.serial + "/set-state"
        response = client.post(path, json=dict(state='on'))
        self.verify_response(response)
        meter.reload(self.session)
        assert meter.config.state == 1

    def test_set_state_off(self, client):
        meter = MeterFactory(config__state=1)
        self.session.commit()

        path = "/meter/" + meter.serial + "/set-state"
        response = client.post(path, json=dict(state='off'))
        self.verify_response(response)

        meter.reload(self.session)
        assert meter.config.state == 0

    def test_set_state_auto(self, client):
        meter = MeterFactory(config__state=0)
        self.session.commit()

        path = "/meter/" + meter.serial + "/set-state"
        response = client.post(path, json=dict(state='auto'))
        self.verify_response(response)

        meter2 = Meter.get_by_code(self.ground, 1)
        assert meter2.config.state == 2

    def test_set_state_bad_value(self, client):
        meter = MeterFactory()
        self.session.commit()

        path = "/meter/" + meter.serial + "/set-state"
        response = client.post(path, json=dict(state='bad-state'))
        self.verify_response(response)

    def test_set_state_not_found(self, client):
        path = "/meter/invalid-serial/set-state"
        response = client.post(path, json=dict(state='auto'))
        self.verify_response(response)

    def test_set_state_meter_forbidden(self, client, vendor_role):
        vendor = VendorFactory(roles=[vendor_role])
        meter = TotalizerMeterFactory()
        self.session.commit()
        client.login_as(vendor)

        path = "/meter/" + meter.serial + "/set-state"
        response = client.post(path, json=dict(state='auto'))
        self.verify_response(response)

    def test_reset_meter(self, client):
        meter = MeterFactory(config__state=1)
        self.session.commit()

        events = Event.query.filter_by(object_id=str(meter.id))
        assert events.count() == 0

        path = "/meter/" + meter.serial + "/reset-meter"
        response = client.get(path)
        self.verify_response(response)

        # make sure this doesnt change the saved meter state
        meter.reload(self.session)
        assert meter.config.state == 1

        events = Event.query.filter_by(object_id=str(meter.id))
        assert events.count() == 1
        event = events.first()
        assert event.event_type == Event.TYPE_METER_STATE_CHANGED

    def test_reset_meter_not_found(self, client):
        path = "/meter/invalid-serial/reset-meter"
        response = client.get(path)
        self.verify_response(response)

    def test_reset_meter_forbidden(self, client, vendor_role):
        vendor = VendorFactory(roles=[vendor_role])
        meter = TotalizerMeterFactory()
        self.session.commit()
        client.login_as(vendor)

        path = "/meter/" + meter.serial + "/reset-meter"
        response = client.get(path)
        self.verify_response(response)

    def test_code_redirect(self, client):
        meter = MeterFactory()
        self.session.commit()

        path = "/microgrid/groundserial1/" + str(meter.code) + "/"
        response = client.get(path)
        self.verify_response(response)

        path = "/microgrid/groundserial1/" + str(meter.code) + "/some/url"
        response = client.get(path)
        self.verify_response(response, 'subpage')

        path = "/microgrid/groundserial1/1234/some/url"
        response = client.get(path)
        self.verify_response(response, 'subpage2')

    def test_serial_redirect(self, client):
        meter = MeterFactory()
        self.session.commit()

        path = "/microgrid/groundserial1/" + str(meter.serial) + "/"
        response = client.get(path)
        self.verify_response(response)

        path = "/microgrid/groundserial1/" + str(meter.serial) + "/some/url"
        response = client.get(path)
        self.verify_response(response, 'subpage')

        path = "/microgrid/groundserial1/SM15R-01-1234678/some/url"
        response = client.get(path)
        self.verify_response(response, 'subpage2')

    def test_messages_json(self, client, mocker):
        event_create = mocker.patch('sparkmeter.event.eventdomain.Event.create')
        event_create.return_value = EventFactory()
        meter = MeterFactory()
        self.session.commit()

        event_type = Event.TYPE_CUSTOMER_LOW_BALANCE
        event = Event.create(event_type, meter)
        SMSMessageFactory(phone_number=meter.customer.phone_number,
                          direction=SMSMessage.DIRECTION_IN)
        SMSMessageFactory(phone_number=meter.customer.phone_number,
                          event=event,
                          direction=SMSMessage.DIRECTION_OUT)
        self.session.commit()

        path = "/meter/" + meter.serial + "/messages.json"
        response = client.get(path)
        self.verify_response(response)
        assert event_create.mock_calls == [
            mock.call('customer-low-balance', meter),
        ]

    def test_messages_json_not_found(self, client):
        path = "/meter/invalid-serial/messages.json"
        response = client.get(path)
        self.verify_response(response)

    def test_messages_export(self, client, mocker):
        event_create = mocker.patch('sparkmeter.event.eventdomain.Event.create')
        event_create.return_value = EventFactory()
        meter = MeterFactory()
        self.session.commit()

        event_type = Event.TYPE_CUSTOMER_LOW_BALANCE
        event = Event.create(event_type, meter)
        SMSMessageFactory(phone_number=meter.customer.phone_number,
                          direction=SMSMessage.DIRECTION_IN)
        SMSMessageFactory(phone_number=meter.customer.phone_number,
                          event=event,
                          direction=SMSMessage.DIRECTION_OUT)
        self.session.commit()

        path = "/meter/" + meter.serial + "/messages.csv"
        response = client.get(path)
        self.verify_response(response)
        assert event_create.mock_calls == [
            mock.call('customer-low-balance', meter),
        ]

    def test_messages_export_not_found(self, client, mocker):
        event_create = mocker.patch('sparkmeter.event.eventdomain.Event.create')
        event_create.return_value = EventFactory()
        meter = MeterFactory()
        self.session.commit()
        event_type = Event.TYPE_CUSTOMER_LOW_BALANCE
        event = Event.create(event_type, meter)
        SMSMessageFactory(phone_number=meter.customer.phone_number,
                          direction=SMSMessage.DIRECTION_IN)
        SMSMessageFactory(phone_number=meter.customer.phone_number,
                          event=event,
                          direction=SMSMessage.DIRECTION_OUT)
        self.session.commit()

        path = "/meter/1234/messages.csv"
        response = client.get(path)
        self.verify_response(response)

    def test_verify_phone_number(self, client):
        meter = MeterFactory(customer__phone_number_verified=False)
        self.session.commit()

        path = "/meter/" + meter.serial + "/verify-phone-number"
        response = client.put(path, json={})
        self.verify_response(response)

        assert not meter.customer.phone_number_verified
        messages = list(SMSMessage.get_all())
        assert len(messages) == 1
        assert messages[0].direction == SMSMessage.DIRECTION_OUT
        assert messages[0].phone_number == '+18008000001'
        msg = (u'Send back CHECK to validate this phone number. '
               u'This will allow you to receive alerts from SparkMeter.')
        assert messages[0].text == msg

    def test_verify_phone_number_not_found(self, client):
        path = "/meter/invalid-serial/verify-phone-number"
        response = client.put(path)
        assert response.status_code == http.client.NOT_FOUND

    def test_edit_phone_number(self, client, config):
        tariff = TariffFactory()
        MeterFactory(customer__phone_number='+551633710001')
        meter = MeterFactory(customer__phone_number=None, billing__tariff=tariff)
        self.session.commit()

        path = "/meter/" + meter.serial + "/edit"
        data = {
            'tariff': tariff.id,
            'state': meter.config.state,
            'customer_country_code': '55',
            'customer_national_number': '1633710001',
        }
        data['customer_national_number'] = '1633710002'
        config['HEROKU'] = True
        response = client.post(path, data=data)
        self.verify_response(response)
        assert meter.customer.phone_number == '+551633710002'

        config['HEROKU'] = True
        response = client.post(path, data=data)
        self.verify_response(response, variant='skip-self')
        assert meter.customer.phone_number == '+551633710002'

    def test_transaction_json(self, client):
        meter = MeterFactory()
        TransactionFactory(_to_wallet_meter=meter)
        self.session.commit()

        path = "/meter/" + meter.serial + "/transactions.json"
        response = client.get(path)
        self.verify_response(response)

    def test_transactions_json_not_found(self, client):
        path = "/meter/invalid/transactions.json"
        response = client.get(path)
        self.verify_response(response)

    def test_transaction_csv(self, client):
        meter = MeterFactory()
        TransactionFactory(_to_wallet_meter=meter)
        self.session.commit()

        path = "/meter/" + meter.serial + "/transactions.csv"
        response = client.get(path)
        self.verify_response(response)

    def test_transactions_csv_not_found(self, client):
        path = "/meter/invalid/transactions.csv"
        response = client.get(path)
        self.verify_response(response)

    def test_meters_json(self, client):
        path = "/meter/meters.json"
        MeterFactory(
            code=1,
            config__hidden=True,
            customer__name="hiddencustomer",
        )
        MeterFactory(
            code=2,
            config__hidden=False,
            customer__name="visiblecustomer",
        )
        MeterFactory(
            code=3,
            config__hidden=False,
            customer__name="visiblecustomer2",
        )
        self.session.commit()

        response = client.get(path)
        self.verify_response(response)

    def test_meters_json_customer_meter(self, client):
        path = "/meter/meters.json"
        MeterFactory(code=1, meter_type=Meter.TYPE_TOTALIZER)
        TotalizerMeterFactory(code=2)
        self.session.commit()
        response = client.get(path + '?meter_type=customer')
        self.verify_response(response)

    def test_meters_json_totalizer(self, client):
        path = "/meter/meters.json"
        MeterFactory(code=1, meter_type=Meter.TYPE_TOTALIZER)
        TotalizerMeterFactory(code=2)
        self.session.commit()
        response = client.get(path + '?meter_type=totalizer')
        self.verify_response(response)

    def test_meters_json_tags(self, client):
        path = "/meter/meters.json"
        m = MeterFactory()
        MeterTag(name='active-tag')
        MeterTag(name='inactive-tag')
        self.session.commit()
        MeterTag.add('active-tag', m)
        MeterTag.add('inactive-tag', m)
        self.session.commit()
        MeterTag.remove('inactive-tag', m)
        self.session.commit()
        response = client.get(path + '?meter_type=customer')
        self.verify_response(response)

    def test_meters_json_invalid_meter_type(self, client):
        path = "/meter/meters.json"
        response = client.get(path + '?meter_type=invalid')
        self.verify_response(response)

    def test_meters_filtering(self, client, config, operator_role, vendor_role):
        path = "/meter/meters.json"
        other = GroundFactory()
        self.session.commit()
        MeterFactory(serial='SM15R-01-00000001',
                     ground=self.ground)
        MeterFactory(serial='SM15R-01-00000002',
                     ground=other)
        o1 = OperatorFactory(roles=[operator_role],
                             username='operator-only-1',
                             grounds=[self.ground])
        o2 = OperatorFactory(roles=[operator_role],
                             username='operator-only-2',
                             grounds=[other])
        o3 = OperatorFactory(roles=[operator_role],
                             username='operator-all',
                             grounds=[self.ground, other])
        v1 = VendorFactory(roles=[vendor_role],
                           username='vendor-only-1',
                           grounds=[self.ground])
        v2 = VendorFactory(roles=[vendor_role],
                           username='vendor-only-2',
                           grounds=[other])
        v3 = VendorFactory(roles=[vendor_role],
                           username='vendor-all',
                           grounds=[self.ground, other])
        self.session.commit()

        for params in [dict(HEROKU=True, SERIAL=self.ground.serial),
                       dict(HEROKU=False, SERIAL=self.ground.serial),
                       dict(HEROKU=False, SERIAL=other.serial)]:
            where = 'cloud' if params.get('HEROKU') else 'ground'
            if params['HEROKU']:
                where = 'cloud'
                del params['SERIAL']
            elif params['SERIAL'] == self.ground.serial:
                where = 'ground1'
            elif params['SERIAL'] == other.serial:
                where = 'ground2'
            for user in [o1, o2, o3, v1, v2, v3]:
                config.update(**params)
                client.login_as(user)
                response = client.get(path)
                variant = '%s-%s' % (where, user.username)
                self.verify_response(response, variant=variant)
