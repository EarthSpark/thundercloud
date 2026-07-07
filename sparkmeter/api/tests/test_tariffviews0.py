# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
import http.client
import operator
from unittest import mock

from sparkmeter.api.tests.test_apiviews0 import APIView0TestCaseBase
from sparkmeter.constants import MAX_SIGNED_INT
from sparkmeter.event.eventdomain import Event
from sparkmeter.meter.meterdomain import MeterConfig
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.tests.test_data_factory import MeterFactory, TariffFactory


class TariffViewTest(APIView0TestCaseBase):

    path = 'v0/tariff/{id}'

    def test_get(self):
        t = TariffFactory()
        self.session.commit()
        response = self.get(self.path.format(id=t.id))
        self.verify_response(response,
                             ignore_values=[str(t.id)])

    def test_bad_transaction_id(self):
        response = self.get(self.path.format(id='bad-id-dot-com'))
        self.verify_response(response)

    def test_no_such_transaction(self):
        response = self.get(self.path.format(id='7390109f-7103-4777-84f0-89e7deff382a'))
        self.verify_response(response)


class TariffListTest(APIView0TestCaseBase):

    path = 'v0/tariffs'

    def test_get(self):
        t = TariffFactory()
        self.session.commit()
        response = self.get(self.path)
        self.verify_response(response, ignore_values=[str(t.id)])

    def test_get_empty(self):
        response = self.get(self.path)
        self.verify_response(response)


class TariffAddTest(APIView0TestCaseBase):

    path = 'v0/tariffs'

    def test_add(self, config):
        config['HEROKU'] = False
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'tous': [],
        }
        response = self.post(self.path, json=data)
        t = Tariff.query.one()
        assert t.name == data['name']
        assert t.flat_load_limit == data['flat_load_limit']
        assert t.tariff_type == data['tariff_type']
        assert t.flat_price == data['flat_price']
        assert not t.tou_enabled
        assert len(t.blockrates) == 0
        assert len(t.tous) == 0
        assert t.cycle_start_day_of_month == 1
        self.verify_response(response, ignore_values=[str(t.id)])

    def test_add_int_outrange(self):
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': MAX_SIGNED_INT + 1,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': 'flat',
            'flat_price': 4,
            'tous': [],
        }

        response = self.post(self.path, json=data)
        assert not Tariff.query.scalar()
        self.verify_response(response)

    def test_add_int_max_allowed(self):
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': MAX_SIGNED_INT,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': 'flat',
            'flat_price': 4,
            'tous': [],
        }
        response = self.post(self.path, json=data)
        t = Tariff.query.one()
        self.verify_response(response, ignore_values=[str(t.id)])

    def test_add_tous(self):
        data = {
            'name': 'TARIFF TOU',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': 'flat',
            'flat_price': 4,
            'tou_enabled': True,
            'tous': [{
                'end': '24:00',
                'id': '612aaccf-a86f-486e-82b4-3abd136f34ef',
                'start': '00:00',
                'value': 100
            }],
        }
        response = self.post(self.path, json=data)
        t = Tariff.query.one()
        assert t.name == data['name']
        assert t.flat_load_limit == data['flat_load_limit']
        assert t.tariff_type == data['tariff_type']
        assert t.flat_price == data['flat_price']
        assert t.tou_enabled
        assert len(t.blockrates) == 0
        assert len(t.tous) == 1
        tous = t.get_tous()
        assert tous[0].start == '00:00'
        assert tous[0].end == '00:00'
        assert tous[0].value == 100
        self.verify_response(response, ignore_values=[str(t.id)])

    def test_add_tous_disabled(self):
        data = {
            'name': 'TARIFF TOU',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': 'flat',
            'flat_price': 4,
            'tou_enabled': False,
            'tous': [{
                'end': '24:00',
                'id': '612aaccf-a86f-486e-82b4-3abd136f34ef',
                'start': '00:00',
                'value': 100
            }],
        }
        response = self.post(self.path, json=data)
        t = Tariff.query.one()
        assert t.name == data['name']
        assert t.flat_load_limit == data['flat_load_limit']
        assert t.tariff_type == data['tariff_type']
        assert t.flat_price == data['flat_price']
        assert not t.tou_enabled
        assert len(t.blockrates) == 0
        assert len(t.tous) == 1
        tous = t.get_tous()
        assert tous[0].start == '00:00'
        assert tous[0].end == '00:00'
        assert tous[0].value == 100
        self.verify_response(response, ignore_values=[str(t.id)])

    def test_add_with_blockrates(self):
        data = {
            'blockrates': [
                {'lower': 0, 'upper': 20, 'value': 1},
                {'lower': 20, 'upper': 40, 'value': 2},
                {'lower': 40, 'upper': 0, 'value': 3.5},
            ],
            'name': 'TARIFF BLOCKRATES',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_BLOCKRATE,
            'flat_price': 4,
        }
        response = self.post(self.path, json=data)

        t = Tariff.query.one()
        assert t.name == data['name']
        assert t.flat_load_limit == data['flat_load_limit']
        assert t.tariff_type == data['tariff_type']
        assert t.flat_price == data['flat_price']
        assert not t.tou_enabled
        assert len(t.tous) == 0
        assert len(t.blockrates) == 3
        blockrates = list(sorted(t.get_blockrates(), key=operator.attrgetter('value')))
        assert blockrates[0].lower == 0
        assert blockrates[0].upper == 20
        assert blockrates[0].value == 1
        assert blockrates[1].lower == 20
        assert blockrates[1].upper == 40
        assert blockrates[1].value == 2
        assert blockrates[2].lower == 40
        assert blockrates[2].upper == 0
        assert blockrates[2].value == 3.5

        self.verify_response(response, ignore_values=[str(t.id)])

    def test_add_with_load_limits(self):
        data = {
            'load_limits': [
                {'start': '00:00', 'end': '18:00', 'value': 1},
                {'start': '18:00', 'end': '22:00', 'value': 2},
                {'start': '22:00', 'end': '00:00', 'value': 3.5},
            ],
            'name': 'TARIFF LOAD LIMITS',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_SCHEDULED,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
        }
        response = self.post(self.path, json=data)

        t = Tariff.query.one()
        assert t.name == data['name']
        assert t.flat_load_limit == data['flat_load_limit']
        assert t.tariff_type == data['tariff_type']
        assert t.flat_price == data['flat_price']
        assert not t.tou_enabled
        assert len(t.tous) == 0
        assert len(t.blockrates) == 0
        assert len(t.load_limits) == 3
        limits = list(sorted(t.get_load_limits(), key=operator.attrgetter('value')))
        assert limits[0].start == '00:00'
        assert limits[0].end == '18:00'
        assert limits[0].value == 1
        assert limits[1].start == '18:00'
        assert limits[1].end == '22:00'
        assert limits[1].value == 2
        assert limits[2].start == '22:00'
        assert limits[2].end == '00:00'
        assert limits[2].value == 3.5

        self.verify_response(response, ignore_values=[str(t.id)])

    def test_add_with_invalid_blockrates(self):
        data = {
            'blockrates': [{'lower': '1', 'upper': '20', 'value': '1'}],
            'name': 'Tariff',
            'load_limit_type': 'flat',
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_BLOCKRATE
        }
        response = self.post(self.path, json=data)
        msg = 'Block rates contain at least one gap, between 0 and 65535'
        assert msg in response.text
        self.verify_response(response)

    def test_add_with_invalid_tous(self):
        data = {
            'tous': [{
                'end': '24:00',
                'id': '612aaccf-a86f-486e-82b4-3abd136f34ef',
                'start': '00:00',
                'value': -100
            }],
            'name': 'TARIFF TOU',
            'load_limit_type': 'flat',
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': 'flat',
            'flat_price': 4,
            'tou_enabled': True,
        }
        response = self.post(self.path, json=data)
        msg = 'The TOU period modifier must be a positive number.'
        assert msg in response.text
        self.verify_response(response)

    def test_add_error_empty_name(self):
        data = {'name': '', 'flat_load_limit': 150, 'flat_price': 4}
        response = self.post(self.path, json=data)
        assert 'bad parameter: name, cannot be empty' in response.text
        self.verify_response(response)

    def test_add_error_duplicate_name(self):
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': 'flat',
            'flat_price': 4,
            'tous': [],
        }
        self.post(self.path, json=data)
        t = Tariff.query.one()
        response = self.post(self.path, json=data)
        Tariff.query.one()
        assert 'A tariff with the name \\"TARIFF\\" already exists' in response.text
        self.verify_response(response, ignore_values=[str(t.id)])

    def test_add_error_missing_load_limit(self):
        data = {
            'name': 'Tariff',
            'cycle_start_day_of_month': 1,
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_price': 4,
            'tariff_type': Tariff.TYPE_FLAT,
        }
        response = self.post(self.path, json=data)
        assert 'missing parameter: flat_load_limit' in response.text
        self.verify_response(response)

    def test_add_error_no_scheduled_load_limits(self):
        data = {
            'name': 'Tariff',
            'cycle_start_day_of_month': 1,
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_SCHEDULED,
            'load_limits': [],
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 3.0
        }
        response = self.post(self.path, json=data)
        assert 'Please add some Load limit periods' in response.text
        self.verify_response(response)

    def test_add_invalid_tariff_type(self):
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': 'flatr',
            'flat_price': 4,
            'tous': [],
        }
        response = self.post(self.path, json=data)
        assert 'Must be one of' in response.text
        self.verify_response(response)

    def test_add_tariff_type_missing_dependent(self):
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
        }
        response = self.post(self.path, json=data)
        assert 'missing parameter: flat_price' in response.text
        self.verify_response(response, variant='flat')

        data['tariff_type'] = Tariff.TYPE_BLOCKRATE
        response = self.post(self.path, json=data)
        assert 'missing parameter: blockrates' in response.text
        self.verify_response(response, variant='blockrate')

    def test_add_tariff_no_blockrates(self):
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_BLOCKRATE,
            'blockrates': []
        }
        response = self.post(self.path, json=data)
        assert 'Please add some block rates' in response.text
        self.verify_response(response)

    def test_add_invalid_load_limit_type(self):
        data = {
            'name': 'TARIFF',
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'load_limits': [
                {'start': '00:00', 'end': '18:00', 'value': 1},
                {'start': '18:00', 'end': '22:00', 'value': 2},
                {'start': '22:00', 'end': '00:00', 'value': 3.5},
            ],
            'load_limit_type': 'skeduled',
            'tous': [],
        }
        response = self.post(self.path, json=data)
        assert 'Must be one of' in response.text
        self.verify_response(response)

    def test_add_invalid_tou_start_minute(self):
        data = {
            'name': 'TARIFF TOU',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'tou_enabled': True,
            'tous': [{
                'end': '24:00',
                'id': '612aaccf-a86f-486e-82b4-3abd136f34ef',
                'start': '00:02',
                'value': 100
            }],
        }
        response = self.post(self.path, json=data)
        assert 'must start on the hour' in response.text
        self.verify_response(response)

    def test_add_invalid_tou_end_minute(self):
        data = {
            'name': 'TARIFF TOU',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'tou_enabled': True,
            'tous': [{
                'end': '23:01',
                'id': '612aaccf-a86f-486e-82b4-3abd136f34ef',
                'start': '00:00',
                'value': 100
            }],
        }
        response = self.post(self.path, json=data)
        assert 'must end on the hour' in response.text
        self.verify_response(response)

    def test_add_tou_missing_dependent(self):
        data = {
            'name': 'TARIFF TOU',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'tou_enabled': True,
            'tous': [],
        }
        response = self.post(self.path, json=data)
        assert 'Please add some TOU periods' in response.text
        self.verify_response(response)

    def test_add_invalid_flat_load_limit(self):
        data = {
            'name': 'TARIFF LOAD LIMITS',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 0,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
        }
        response = self.post(self.path, json=data)
        assert 'Please enter a Load Limit for this tariff' in response.text
        self.verify_response(response)

    def test_add_missing_required_load_limit(self):
        data = {
            'name': 'TARIFF LOAD LIMITS',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
        }
        response = self.post(self.path, json=data)
        assert 'missing parameter: flat_load_limit' in response.text
        self.verify_response(response)

    def test_add_invalid_load_limit_start_minute(self):
        data = {
            'load_limits': [
                {'start': '00:01', 'end': '18:00', 'value': 1},
            ],
            'name': 'TARIFF LOAD LIMITS',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_SCHEDULED,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
        }
        response = self.post(self.path, json=data)
        assert 'must start on the hour' in response.text
        self.verify_response(response)

    def test_add_invalid_load_limit_end_minute(self):
        data = {
            'load_limits': [
                {'start': '00:00', 'end': '18:01', 'value': 1},
            ],
            'name': 'TARIFF LOAD LIMITS',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_SCHEDULED,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
        }
        response = self.post(self.path, json=data)
        assert 'must end on the hour' in response.text
        self.verify_response(response)

    def test_add_missing_load_limits(self):
        data = {
            'name': 'TARIFF LOAD LIMITS',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_SCHEDULED,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
        }
        response = self.post(self.path, json=data)
        assert 'missing parameter: load_limits' in response.text
        self.verify_response(response)

    def test_add_plan_enabled_required_fields(self):
        data = {
            'name': 'TARIFF LOAD LIMITS',
            'cycle_start_day_of_month': 1,
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'plan_enabled': True,
            'plan_fixed_fee': 2,
        }
        response = self.post(self.path, json=data)
        assert 'missing parameter: plan_price' in response.text
        self.verify_response(response, variant='missing-plan-price')

        data = {
            'name': 'TARIFF LOAD LIMITS',
            'cycle_start_day_of_month': 1,
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'plan_enabled': True,
            'plan_price': 2,
        }
        response = self.post(self.path, json=data)
        assert 'missing parameter: plan_fixed_fee' in response.text
        self.verify_response(response, variant='missing-plan-fixed-fee')

    def test_add_daily_energy_limit_enabled(self, config):
        config['HEROKU'] = False
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'tous': [],
            'daily_energy_limit_enabled': True,
            'daily_energy_limit_reset_hour': 4,
            'daily_energy_limit_value': 100,
        }
        response = self.post(self.path, json=data)
        t = Tariff.query.one()
        assert t.name == data['name']
        assert t.flat_load_limit == data['flat_load_limit']
        assert t.tariff_type == data['tariff_type']
        assert t.flat_price == data['flat_price']
        assert not t.tou_enabled
        assert len(t.blockrates) == 0
        assert len(t.tous) == 0
        assert t.cycle_start_day_of_month == 1
        assert t.daily_energy_limit_enabled
        assert t.daily_energy_limit_reset_hour == 4
        assert t.daily_energy_limit_value == 100
        self.verify_response(response, ignore_values=[str(t.id)])

    def test_add_daily_energy_limit_enabled_required_fields(self, config):
        config['HEROKU'] = False
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'tous': [],
            'daily_energy_limit_enabled': True,
        }
        response = self.post(self.path, json=data)
        assert 'missing parameter: daily_energy_limit_reset_hour' in response.text
        self.verify_response(response, variant='missing-daily_energy_limit_reset_hour')

        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'tous': [],
            'daily_energy_limit_enabled': True,
            'daily_energy_limit_reset_hour': 4,
        }
        response = self.post(self.path, json=data)
        assert 'missing parameter: daily_energy_limit_value' in response.text
        self.verify_response(response, variant='missing-daily_energy_limit_value')

    def test_add_daily_energy_limit_disabled(self, config):
        config['HEROKU'] = False
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'tous': [],
            'daily_energy_limit_enabled': False,
            'daily_energy_limit_reset_hour': 4,
            'daily_energy_limit_value': 100,
        }
        response = self.post(self.path, json=data)
        t = Tariff.query.one()
        assert t.name == data['name']
        assert t.flat_load_limit == data['flat_load_limit']
        assert t.tariff_type == data['tariff_type']
        assert t.flat_price == data['flat_price']
        assert not t.tou_enabled
        assert len(t.blockrates) == 0
        assert len(t.tous) == 0
        assert t.cycle_start_day_of_month == 1
        assert not t.daily_energy_limit_enabled
        assert t.daily_energy_limit_reset_hour == 4
        assert t.daily_energy_limit_value == 100
        self.verify_response(response, ignore_values=[str(t.id)])

    def test_add_daily_energy_limit_hour_float(self, config):
        config['HEROKU'] = False
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'tous': [],
            'daily_energy_limit_enabled': True,
            'daily_energy_limit_reset_hour': 1.5,
            'daily_energy_limit_value': 100,
        }
        response = self.post(self.path, json=data)
        assert 'bad parameter: daily_energy_limit_reset_hour, expected int type, got float' in response.text
        self.verify_response(response, variant='bad-daily_energy_limit_reset_hour')

    def test_add_daily_energy_limit_value_string(self, config):
        config['HEROKU'] = False
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_price': 0,
            'cycle_start_day_of_month': 1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'tous': [],
            'daily_energy_limit_enabled': True,
            'daily_energy_limit_reset_hour': 1,
            'daily_energy_limit_value': 'asdf',
        }
        response = self.post(self.path, json=data)
        assert 'bad parameter: daily_energy_limit_value, must be a float' in response.text
        self.verify_response(response)

    def test_add_daily_plan(self):
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_enabled': True,
            'plan_price': 1,
            'cycle_start_day_of_month': 1,
            'plan_fixed_fee': 3.0,
            'plan_duration': '1d',
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'tous': [],
        }
        response = self.post(self.path, json=data)
        assert response.status_code == 201, response.json()
        t = Tariff.query.one()
        self.verify_response(response, ignore_values=[str(t.id)])
        assert t.plan_duration_and_start_day == '1d1'
        assert t.cycle_start_day_of_month == 1
        assert t.plan_is_daily

    def test_add_daily_plan_start_day_invalid_cycle(self):
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_enabled': True,
            'plan_price': 1,
            'cycle_start_day_of_month': 3,
            'plan_fixed_fee': 3.0,
            'plan_duration': '1d',
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'tous': [],
        }
        response = self.post(self.path, json=data)
        assert response.status_code == 400, response.json()
        assert Tariff.query.count() == 0
        self.verify_response(response)

    def test_add_monthly_plan(self):
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_enabled': True,
            'plan_price': 1,
            'cycle_start_day_of_month': 4,
            'plan_fixed_fee': 3.0,
            'plan_duration': '1m',
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'tous': [],
        }
        response = self.post(self.path, json=data)
        assert response.status_code == 201, response.json()
        t = Tariff.query.one()
        self.verify_response(response, ignore_values=[str(t.id)])
        assert t.plan_duration_and_start_day == '1m4'
        assert t.cycle_start_day_of_month == 4
        assert t.plan_is_monthly

    def test_add_daily_plan_start_day_invalid_plan_duration(self):
        data = {
            'name': 'TARIFF',
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 150,
            'plan_enabled': True,
            'plan_price': 1,
            'cycle_start_day_of_month': 3,
            'plan_fixed_fee': 3.0,
            'plan_duration': '1dog',
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 4,
            'tous': [],
        }
        response = self.post(self.path, json=data)
        assert response.status_code == 400, response.json()
        assert Tariff.query.count() == 0
        self.verify_response(response)


class TariffEditTest(APIView0TestCaseBase):

    path = 'v0/tariff/{id}'

    def test_edit(self, config):
        config['HEROKU'] = True
        tariff = TariffFactory(name='Tariff', flat_load_limit=30)
        MeterFactory(code=1, config__state=MeterConfig.STATE_AUTO, tariff=tariff)
        MeterFactory(code=2, config__state=MeterConfig.STATE_AUTO, tariff=tariff)
        MeterFactory(code=3, config__state=MeterConfig.STATE_AUTO)
        self.session.commit()
        assert Tariff.get_by_id(tariff.id)

        data = {
            'name': 'Tariff',
            'cycle_start_day_of_month': 1,
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_price': 0,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_load_limit': 60
        }
        response = self.put(self.path.format(id=tariff.id), json=data)
        assert 'Please set a Flat Rate' in response.text
        self.verify_response(response, variant='edit-post-error-no-rate')

        data = {
            'name': 'Tariff',
            'cycle_start_day_of_month': 1,
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_price': -1,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_load_limit': 60
        }
        response = self.put(self.path.format(id=tariff.id), json=data)
        assert 'Flat Rate cannot be negative' in response.text
        self.verify_response(response, variant='edit-post-error-negative-rate')

        data = {
            'name': 'new tariff',
            'cycle_start_day_of_month': 1,
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_price': 4,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_load_limit': 150
        }
        response = self.put(self.path.format(id=tariff.id), json=data)
        self.verify_response(response, variant='tariff-updated')

    def test_edit_flat_load_limit_ground(self, config, send_set_config):
        config['HEROKU'] = False
        tariff = TariffFactory(flat_load_limit=10)
        MeterFactory(tariff=tariff)
        self.session.commit()

        data = {
            'name': 'Tariff',
            'cycle_start_day_of_month': 1,
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT,
            'flat_load_limit': 20,
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 3,
        }
        response = self.put(self.path.format(id=tariff.id), json=data)
        self.verify_response(response)
        assert response.status_code == http.client.OK
        events = Event.query.all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == Event.TYPE_TARIFF_POWER_LIMIT_CHANGED
        assert event.object.id == tariff.id
        assert event.processed

        assert send_set_config.mock_calls == [
            mock.call(
                subnet=255,
                current_limit=10000.0,
                load_limit=10.0,
                mac=1,
                command='disable',
                balance=0,
                low_balance=True,
                firmware_version=u'abc1234'),
        ]

    def test_partial_edit_top_level(self):
        tariff = TariffFactory(name='Tariff', flat_load_limit=30)
        self.session.commit()

        data = {
            'name': 'Tariff 2',
            'cycle_start_day_of_month': 2,
            'flat_load_limit': 40,
            'low_balance_threshold': 2,
            'flat_price': 3,
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response)

    def test_partial_edit_change_load_limit_scheduled(self):
        tariff = TariffFactory(name='Tariff', flat_load_limit=30)
        self.session.commit()

        data = {
            'flat_load_limit': 40,
            'load_limits': [
                {'start': '00:00', 'end': '18:00', 'value': 1},
                {'start': '18:00', 'end': '22:00', 'value': 2},
                {'start': '22:00', 'end': '00:00', 'value': 3.5},
            ],
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_SCHEDULED,
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response)

    def test_partial_edit_change_load_limit_flat(self):
        tariff = TariffFactory(
            name='Tariff',
            load_limit_type=Tariff.LOAD_LIMIT_TYPE_SCHEDULED,
            load_limits=[
                {'start': '00:00', 'end': '18:00', 'value': 1},
                {'start': '18:00', 'end': '22:00', 'value': 2},
                {'start': '22:00', 'end': '00:00', 'value': 3.5},
            ])
        self.session.commit()

        data = {
            'flat_load_limit': 40,
            'load_limit_type': Tariff.LOAD_LIMIT_TYPE_FLAT
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response)

    def test_partial_edit_change_plan_enabled(self):
        tariff = TariffFactory(name='Tariff')
        self.session.commit()

        data = {
            'plan_enabled': True,
            'plan_fixed_fee': 3.0,
            'plan_price': 1.0,
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response)

    def test_partial_edit_change_plan_disabled(self):
        tariff = TariffFactory(name='Tariff', plan_enabled=True, plan_fixed_fee=3.0, plan_price=1.0)
        self.session.commit()

        data = {
            'plan_enabled': False,
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response)

    def test_partial_edit_change_tariff_type_blockrate(self):
        tariff = TariffFactory(name='Tariff')
        self.session.commit()

        data = {
            'tariff_type': Tariff.TYPE_BLOCKRATE,
            'blockrates': [
                {'lower': 0, 'upper': 20, 'value': 1},
                {'lower': 20, 'upper': 40, 'value': 2},
                {'lower': 40, 'upper': 0, 'value': 3.5},
            ]
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response)

    def test_partial_edit_change_tariff_type_flat(self):
        tariff = TariffFactory(
            name='Tariff',
            tariff_type=Tariff.TYPE_BLOCKRATE,
            blockrates=[
                {'lower': 0, 'upper': 20, 'value': 1},
                {'lower': 20, 'upper': 40, 'value': 2},
                {'lower': 40, 'upper': 0, 'value': 3.5},
            ])
        self.session.commit()

        data = {
            'tariff_type': Tariff.TYPE_FLAT,
            'flat_price': 13.0,
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response)

    def test_partial_edit_change_tou_enabled(self):
        tariff = TariffFactory(name='Tariff')
        self.session.commit()

        data = {
            'tou_enabled': True,
            'tous': [{
                'end': '24:00',
                'id': '612aaccf-a86f-486e-82b4-3abd136f34ef',
                'start': '00:00',
                'value': 100
            }]
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response)

    def test_partial_edit_change_tou_disabled(self):
        tariff = TariffFactory(
            name='Tariff',
            tou_enabled=True,
            tous=[{
                'end': '24:00',
                'id': '612aaccf-a86f-486e-82b4-3abd136f34ef',
                'start': '00:00',
                'value': 100
            }])
        self.session.commit()

        data = {
            'tou_enabled': False
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response)

    def test_edit_daily_energy_limit(self, config):
        tariff = TariffFactory(name='Tariff')
        self.session.commit()

        data = {
            'daily_energy_limit_enabled': True,
            'daily_energy_limit_reset_hour': 4,
            'daily_energy_limit_value': 100,
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response, variant='enable')

        data = {
            'daily_energy_limit_enabled': False,
            'daily_energy_limit_reset_hour': 4,
            'daily_energy_limit_value': 100,
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response, variant='disable')

    def test_edit_daily_plan_cycle_start_day(self, config):
        tariff = TariffFactory(plan_duration_span=1, plan_duration_unit='d', cycle_start_day_of_month=1)
        self.session.commit()
        data = {
            'cycle_start_day_of_month': 2,
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        body = response.json()
        assert body['tariff']['cycle_start_day_of_month'] == 1
        self.verify_response(response)

    def test_edit_daily_plan_duration(self, config):
        tariff = TariffFactory(plan_duration_span=1, plan_duration_unit='d', cycle_start_day_of_month=1)
        self.session.commit()
        data = {
            'plan_duration': '1m',
            'cycle_start_day_of_month': 2
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response, variant='daily-to-monthly')

        data = {
            'plan_duration': '1d',
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response, variant='monthly-to-daily')

    def test_edit_existing_invalid_daily_plan(self, config):
        tariff = TariffFactory(plan_duration_unit='z')
        self.session.commit()
        data = {
            'cycle_start_day_of_month': 2,
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response)

    def test_edit_invalid_duration(self):
        tariff = TariffFactory()
        self.session.commit()
        data = {
            'plan_duration': '1z'
        }
        response = self.patch(self.path.format(id=tariff.id), json=data)
        self.verify_response(response)
