# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
import datetime
from builtins import str
from unittest import mock

import pytest
from dateutil.tz import tzlocal, tzoffset, tzutc
from freezegun import freeze_time
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from sparkmeter.tariff.tariffdomain import Tariff, TariffBlockrate, TariffTOU
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import TariffFactory


class TariffTest(SparkMeterTestCaseBase):
    def test_validate_blockrates(self):
        t = Tariff()
        t.blockrates = []
        with pytest.raises(ValueError) as ctx:
            t.validate_blockrates()
        assert 'Please add some block rates.' == str(ctx.value)

        t.blockrates.append(dict(lower=0, upper=0, value=0))

        # lower
        t.blockrates[0]['lower'] = -1
        with pytest.raises(ValueError) as ctx:
            t.validate_blockrates()
        msg = 'The lower value of a block rate must be a positive number.'
        assert msg == str(ctx.value)

        t.blockrates[0]['lower'] = 0

        # upper
        t.blockrates[0]['upper'] = '-1'
        with pytest.raises(ValueError) as ctx:
            t.validate_blockrates()
        msg = 'The upper value of a block rate must be a positive number.'
        assert msg == str(ctx.value)

        # upper == lower == 0 is a special case, no error
        t.blockrates[0]['value'] = 0
        t.blockrates[0]['lower'] = 0
        t.blockrates[0]['upper'] = 0
        t.validate_blockrates()

        t.blockrates[0]['lower'] = 5
        t.blockrates[0]['upper'] = 5

        # upper == lower
        with pytest.raises(ValueError) as ctx:
            t.validate_blockrates()
        msg = 'Block rate lower (5) must be different from upper (5)'
        assert msg == str(ctx.value)

        # upper > lower
        t.blockrates[0]['lower'] = 10
        with pytest.raises(ValueError) as ctx:
            t.validate_blockrates()
        msg = 'Block rate upper (5) must be higher than lower (10)'
        assert msg == str(ctx.value)

        # overlap
        t.blockrates[0]['lower'] = 0
        t.blockrates[0]['upper'] = 10

        br2 = dict(lower=5, upper=20, value=0)
        t.blockrates.append(br2)

        with pytest.raises(ValueError) as ctx:
            t.validate_blockrates()
        msg = 'Block rate 0 to 10 overlaps with Block rate 5 to 20'
        assert msg == str(ctx.value)
        t.blockrates[1]['lower'] = 10

        # gaps
        with pytest.raises(ValueError) as ctx:
            t.validate_blockrates()
        msg = 'Block rates contain at least one gap, between 20 and 65535'
        assert msg == str(ctx.value)

        # value
        t.blockrates[0]['value'] = -1
        with pytest.raises(ValueError) as ctx:
            t.validate_blockrates()
        msg = 'The block rate value must be a positive number.'
        assert msg == str(ctx.value)

    def test_validate_tous(self):
        t = Tariff(name='Tou Tariff')
        t.tous = []
        with pytest.raises(ValueError) as ctx:
            t.validate_tous()
        assert 'Please add some TOU periods.' == str(ctx.value)

        t.tous.append(dict(start='00:00', end='00:00', value=0))

        # start valid time
        t.tous[0]['start'] = 'FOOBARZ'
        with pytest.raises(ValueError) as ctx:
            t.validate_tous()
        msg = 'The start value of a TOU period must be a valid time, not FOOBARZ.'
        assert msg == str(ctx.value)
        t.tous[0]['start'] = '01:00'

        # end valid
        t.tous[0]['end'] = 'FOOBARZ'
        with pytest.raises(ValueError) as ctx:
            t.validate_tous()
        msg = 'The end value of a TOU period must be a valid time, not FOOBARZ.'
        assert msg == str(ctx.value)

        # start == end, special case 24h
        t.tous[0] = dict(start='00:00', end='00:00', value=100)
        t.get_tous()[0].validate()

        t.tous[0]['start'] = '01:00'
        t.tous[0]['end'] = '01:00'
        with pytest.raises(ValueError) as ctx:
            t.validate_tous()
        msg = 'TOU period start (01:00) must be different from end (01:00)'
        assert msg == str(ctx.value)

        # overlap
        t.tous[0]['start'] = '00:00'
        t.tous[0]['end'] = '10:00'

        t.tous.append(dict(start='05:00', end='20:00', value=100))

        with pytest.raises(ValueError) as ctx:
            t.validate_tous()
        msg = 'TOU period 00:00 to 10:00 overlaps with TOU period 05:00 to 20:00'
        assert msg == str(ctx.value)

        # value
        t.tous[0]['value'] = ''
        assert len(t.get_tous()) == 1

        t.tous[0]['value'] = -1
        with pytest.raises(ValueError) as ctx:
            t.validate_tous()
        msg = 'The TOU period modifier must be a positive number.'
        assert msg == str(ctx.value)

    def test_validate_load_limits(self):
        t = Tariff(name='Load Limit Tariff')
        t.load_limits = []
        with pytest.raises(ValueError) as ctx:
            t.validate_load_limits()
        assert 'Please add some Load limit periods.' == str(ctx.value)

        t.load_limits.append(dict(start='00:00', end='00:00', value=0))

        # start valid time
        t.load_limits[0]['start'] = 'FOOBARZ'
        with pytest.raises(ValueError) as ctx:
            t.validate_load_limits()
        msg = 'The start value of a Load limit period must be a valid time, not FOOBARZ.'
        assert msg == str(ctx.value)
        t.load_limits[0]['start'] = '01:00'

        # end valid
        t.load_limits[0]['end'] = 'FOOBARZ'
        with pytest.raises(ValueError) as ctx:
            t.validate_load_limits()
        msg = 'The end value of a Load limit period must be a valid time, not FOOBARZ.'
        assert msg == str(ctx.value)

        # start == end, special case 24h
        t.load_limits[0] = dict(start='00:00', end='00:00', value=100)
        t.get_load_limits()[0].validate()

        t.load_limits[0]['start'] = '01:00'
        t.load_limits[0]['end'] = '01:00'
        with pytest.raises(ValueError) as ctx:
            t.validate_load_limits()
        msg = 'Load limit period start (01:00) must be different from end (01:00)'
        assert msg == str(ctx.value)

        # overlap
        t.load_limits[0]['start'] = '00:00'
        t.load_limits[0]['end'] = '10:00'

        t.load_limits.append(dict(start='05:00', end='20:00', value=100))

        with pytest.raises(ValueError) as ctx:
            t.validate_load_limits()
        msg = 'Load limit period 00:00 to 10:00 overlaps with load limit period 05:00 to 20:00'
        assert msg == str(ctx.value)

        # value
        t.load_limits[0]['value'] = ''
        assert len(t.get_load_limits()) == 1

        t.load_limits[0]['value'] = -1
        with pytest.raises(ValueError) as ctx:
            t.validate_load_limits()
        msg = 'The Load limit period modifier must be a positive number.'
        assert msg == str(ctx.value)

    def test_validate_load_limits_overlap(self):
        t = Tariff()
        t.load_limits = [
            dict(start='09:00', end='15:00', value=100),
            dict(start='16:00', end='10:00', value=50),
        ]
        msg = 'Load limit period 00:00 to 10:00 overlaps with load limit period 09:00 to 15:00'
        with pytest.raises(ValueError, match=msg):
            t.validate_load_limits()

    def test_validate_load_limits_not_covered(self):
        t = Tariff()
        t.load_limits = [
            dict(start='02:00', end='12:00', value=100),
            dict(start='14:00', end='02:00', value=50),
        ]
        msg = 'Load limit periods needs to cover 12:00, 13:00'
        with pytest.raises(ValueError, match=msg):
            t.validate_load_limits()

    def test_validate_tous_ps_548(self):
        t = Tariff()
        t.tous = [
            dict(start='09:00', end='15:00', value=100),
            dict(start='16:00', end='10:00', value=50),
        ]
        msg = 'TOU period 00:00 to 10:00 overlaps with TOU period 09:00 to 15:00'
        with pytest.raises(ValueError, match=msg):
            t.validate_tous()

    def test_get_average_block_rate_errors(self):
        t = TariffFactory()
        msg = 'lower must be a number, not \'str\''
        with pytest.raises(TypeError, match=msg):
            t.get_average_block_rate('', '')
        msg = 'upper must be a number, not \'str\''
        with pytest.raises(TypeError, match=msg):
            t.get_average_block_rate(1, '')
        msg = 'upper and lower must be positive'
        with pytest.raises(ValueError, match=msg):
            t.get_average_block_rate(-1, -1)
        msg = 'upper must be higher than lower'
        with pytest.raises(ValueError, match=msg):
            t.get_average_block_rate(10, 1)

    def test_get_average_block_rate(self):
        t1 = TariffFactory()
        assert t1.get_average_block_rate(0, 10) == 0

        t1.blockrates = [dict(lower=0, upper=10, value=1),
                         dict(lower=10, upper=30, value=2),
                         dict(lower=30, upper=100, value=3),
                         dict(lower=100, upper=0, value=4)]

        assert t1.get_average_block_rate(0, 10) == 1
        assert t1.get_average_block_rate(5, 5) == 1
        assert t1.get_average_block_rate(10, 30) == 2
        assert t1.get_average_block_rate(30, 100) == 3
        assert t1.get_average_block_rate(5, 15) == 1.5
        assert t1.get_average_block_rate(25, 35) == 2.5
        assert t1.get_average_block_rate(8, 33) == 2.04
        assert t1.get_average_block_rate(100, 200) == 4
        assert t1.get_average_block_rate(100, 200000) == 4
        assert t1.get_average_block_rate(200, 200000) == 4

        assert t1.get_average_block_rate(0, 0) == 0
        assert t1.get_average_block_rate(9, 9) == 1
        assert t1.get_average_block_rate(10, 10) == 1
        assert t1.get_average_block_rate(11, 11) == 2
        assert t1.get_average_block_rate(30, 30) == 2
        assert t1.get_average_block_rate(31, 31) == 3
        assert t1.get_average_block_rate(100, 100) == 3
        assert t1.get_average_block_rate(101, 101) == 4
        assert t1.get_average_block_rate(200, 200) == 4
        assert t1.get_average_block_rate(9999, 99990) == 4

    def test_tariff_get_by_name(self):
        m1t1 = TariffFactory(name='m1t1')
        m1t2 = TariffFactory(name='m1t2')
        m2t1 = TariffFactory(name='m2t1')
        m2t2 = TariffFactory(name='m2t2')
        m2t31 = TariffFactory(name='m2t3')
        m2t32 = TariffFactory(name='m2t3')
        self.session.commit()

        t1 = Tariff.get_by_name('m1t1')
        assert m1t1._data == t1._data
        assert m1t2._data != t1._data
        assert m2t1._data != t1._data
        assert m2t2._data != t1._data

        with pytest.raises(NoResultFound):
            Tariff.get_by_name('no-tariff-name')

        t3 = Tariff.get_by_name('m2t3')
        assert t3._data == m2t31._data
        assert t3._data != m2t32._data

        with pytest.raises(MultipleResultsFound):
            Tariff.get_by_name('m2t3', fail_on_multiple=True)

    def test_get_current_load_limits_flat(self):
        tariff = TariffFactory(flat_load_limit=30)
        self.session.commit()
        assert tariff.get_current_load_limit() == 30

    def test_get_current_load_limits_scheduled(self):
        tariff = TariffFactory()
        tariff.load_limits = [
            dict(start="00:00", end="18:00", value=80),
            dict(start="18:00", end="00:00", value=100),
        ]
        tariff.load_limit_type = Tariff.LOAD_LIMIT_TYPE_SCHEDULED
        self.session.commit()

        for when, load_limit in [
            (datetime.datetime(2010, 1, 1, 0, 0), 80),
            (datetime.datetime(2010, 1, 1, 2, 0), 80),
            (datetime.datetime(2010, 1, 1, 10, 0), 80),
            (datetime.datetime(2010, 1, 1, 17, 59), 80),
            (datetime.datetime(2010, 1, 1, 18, 0), 100),
            (datetime.datetime(2010, 1, 1, 20, 0), 100),
            (datetime.datetime(2010, 1, 1, 23, 59), 100),
        ]:
            assert tariff.get_current_load_limit(when=when) == load_limit

        with freeze_time("2010-01-01 00:00"):
            assert tariff.get_current_load_limit() == 80

    def test_get_current_load_limits_scheduled_crossing_midnight(self):
        tariff = TariffFactory()
        tariff.load_limits = [
            dict(start="03:00", end="18:00", value=45),
            dict(start="18:00", end="03:00", value=30),
        ]
        tariff.load_limit_type = Tariff.LOAD_LIMIT_TYPE_SCHEDULED
        self.session.commit()

        for when, load_limit in [
            (datetime.datetime(2010, 1, 1, 0, 0), 30),
            (datetime.datetime(2010, 1, 1, 2, 59), 30),
            (datetime.datetime(2010, 1, 1, 3, 0), 45),
            (datetime.datetime(2010, 1, 1, 17, 59), 45),
            (datetime.datetime(2010, 1, 1, 18, 0), 30),
            (datetime.datetime(2010, 1, 1, 20, 0), 30),
            (datetime.datetime(2010, 1, 1, 23, 59), 30),
        ]:
            assert tariff.get_current_load_limit(when=when) == load_limit

        with freeze_time("2010-01-01 00:00"):
            assert tariff.get_current_load_limit() == 30

    def test_get_last_cycle_start_monthly(self):
        tariff = TariffFactory()
        self.session.commit()

        tariff.cycle_start_day_of_month = 10
        # First month of the year
        # Reference date is exactly the start day datetime: last cycle start is in this month
        assert tariff.get_last_cycle_start(
            datetime.datetime(2010, 1, 10, 0, 0)) == datetime.datetime(2010, 1, 10, 0, 0)
        # Reference date is the same day but later than 00:00: last cycle start is in this month
        assert tariff.get_last_cycle_start(
            datetime.datetime(2010, 1, 10, 12, 43)) == datetime.datetime(2010, 1, 10, 0, 0)
        # Reference date is later in the month: last cycle start is in this month
        assert tariff.get_last_cycle_start(
            datetime.datetime(2010, 1, 17, 8, 23)) == datetime.datetime(2010, 1, 10, 0, 0)
        # Reference date is earlier in the month: last cycle start is in previous month
        assert tariff.get_last_cycle_start(
            datetime.datetime(2010, 1, 7, 8, 23)) == datetime.datetime(2009, 12, 10, 0, 0)

        # Not first month of the year
        # Reference date is exactly the start day datetime: last cycle start is in this month
        assert tariff.get_last_cycle_start(
            datetime.datetime(2010, 3, 10, 0, 0)) == datetime.datetime(2010, 3, 10, 0, 0)
        # Reference date is the same day but later than 00:00: last cycle start is in this month
        assert tariff.get_last_cycle_start(
            datetime.datetime(2010, 3, 10, 12, 43)) == datetime.datetime(2010, 3, 10, 0, 0)
        # Reference date is later in the month: last cycle start is in this month
        assert tariff.get_last_cycle_start(
            datetime.datetime(2010, 3, 17, 8, 23)) == datetime.datetime(2010, 3, 10, 0, 0)
        # Reference date is earlier in the month: last cycle is in previous month
        assert tariff.get_last_cycle_start(
            datetime.datetime(2010, 3, 7, 8, 23)) == datetime.datetime(2010, 2, 10, 0, 0)

    def test_get_last_cycle_start_daily(self):
        tariff = TariffFactory(plan_duration_unit='d')
        self.session.commit()
        # Exactly at the start of the cycle
        assert tariff.get_last_cycle_start(
            datetime.datetime(2010, 1, 1, 0, 0)) == datetime.datetime(2010, 1, 1, 0, 0)
        # After the cycle
        assert tariff.get_last_cycle_start(
            datetime.datetime(2010, 1, 1, 0, 1)) == datetime.datetime(2010, 1, 1, 0, 0)
        # Just before the next cycle
        assert tariff.get_last_cycle_start(
            datetime.datetime(2010, 1, 31, 23, 59)) == datetime.datetime(2010, 1, 1, 0, 0)

    def test_get_next_cycle_start_monthly(self):
        tariff = TariffFactory()
        self.session.commit()

        tariff.cycle_start_day_of_month = 10
        # Last month of the year
        # Reference date is exactly the start day datetime: next cycle start is in next month
        assert tariff.get_next_cycle_start(
            datetime.datetime(2010, 12, 10, 0, 0)) == datetime.datetime(2011, 1, 10, 0, 0)
        # Reference date is later in the month: next cycle start is in next month
        assert tariff.get_next_cycle_start(
            datetime.datetime(2010, 12, 17, 8, 23)) == datetime.datetime(2011, 1, 10, 0, 0)
        # Reference date is earlier in the month: next cycle start is in this month
        assert tariff.get_next_cycle_start(
            datetime.datetime(2010, 12, 7, 8, 23)) == datetime.datetime(2010, 12, 10, 0, 0)

        # Not last month of the year
        # Reference date is exactly the change datetime: next cycle start is in next month
        assert tariff.get_next_cycle_start(
            datetime.datetime(2010, 3, 10, 0, 0)) == datetime.datetime(2010, 4, 10, 0, 0)
        # Reference date is later in the month: next cycle start is in next month
        assert tariff.get_next_cycle_start(
            datetime.datetime(2010, 3, 17, 8, 23)) == datetime.datetime(2010, 4, 10, 0, 0)
        # Reference date is earlier in the month: next cycle start is in same month
        assert tariff.get_next_cycle_start(
            datetime.datetime(2010, 3, 7, 8, 23)) == datetime.datetime(2010, 3, 10, 0, 0)

    def test_get_next_cycle_start_daily(self):
        tariff = TariffFactory(plan_duration_unit='d')
        self.session.commit()

        # Reference date is exactly at the turn of a date
        assert tariff.get_next_cycle_start(
            datetime.datetime(2010, 12, 10, 0, 0)) == datetime.datetime(2010, 12, 11, 0, 0)
        # Reference date is on the last day of a year
        assert tariff.get_next_cycle_start(
            datetime.datetime(2010, 12, 31, 0, 0)) == datetime.datetime(2011, 1, 1, 0, 0)
        # Reference date is at an arbitrary point in the middle of the day
        assert tariff.get_next_cycle_start(
            datetime.datetime(2010, 12, 24, 14, 00)) == datetime.datetime(2010, 12, 25, 14, 00)
        # Reference date is the minute before the next day
        assert tariff.get_next_cycle_start(
            datetime.datetime(2010, 12, 30, 23, 59)) == datetime.datetime(2010, 12, 31, 23, 59)
        # Reference day is Feb 28 on a leap year
        assert tariff.get_next_cycle_start(
            datetime.datetime(2020, 2, 28, 0, 0)) == datetime.datetime(2020, 2, 29, 0, 0)
        # Reference day is Feb 29 on a leap year
        assert tariff.get_next_cycle_start(
            datetime.datetime(2020, 2, 29, 0, 0)) == datetime.datetime(2020, 3, 1, 0, 0)

    def test_last_daily_energy_limit_reset_hour(self):
        tariff = TariffFactory()
        self.session.commit()

        # the localtime hour the limit resets
        tariff.daily_energy_limit_reset_hour = 10

        yesterdays_reset = datetime.datetime(2010, 1, 1, 10, 0)
        todays_reset = datetime.datetime(2010, 1, 2, 10, 0)

        # the last reset time was the previous day because it is not yet 10am localtime
        with freeze_time("2010-01-02 9:00"):
            assert tariff.last_daily_energy_limit_reset_datetime() == yesterdays_reset

        # the last reset time was the previous day because it is not yet 10am localtime
        with freeze_time("2010-01-02 9:59"):
            assert tariff.last_daily_energy_limit_reset_datetime() == yesterdays_reset

        # the last reset time is now because it is 10am localtime
        with freeze_time("2010-01-02 10:00"):
            assert tariff.last_daily_energy_limit_reset_datetime() == todays_reset

        # the last reset time is today because it is past 10am localtime
        with freeze_time("2010-01-02 10:01"):
            assert tariff.last_daily_energy_limit_reset_datetime() == todays_reset

        # the last reset time is today because it is past 10am localtime
        with freeze_time("2010-01-02 11:00"):
            assert tariff.last_daily_energy_limit_reset_datetime() == todays_reset


class TariffBlockrateTest(SparkMeterTestCaseBase):
    def test_repr(self):
        tou = TariffBlockrate(lower=0, upper=10, value=3.5)
        assert repr(tou) == '<TariffBlockrate lower=0 upper=10 value=3.5>'

    def test_eq(self):
        t1 = TariffBlockrate(lower=0, upper=10, value=3.5)
        t2 = TariffBlockrate(lower=1, upper=10, value=3.5)
        assert t1 != t2
        t3 = TariffBlockrate(lower=0, upper=10, value=3.5)
        t4 = TariffBlockrate(lower=0, upper=11, value=3.5)
        assert t3 != t4
        t5 = TariffBlockrate(lower=0, upper=10, value=3.5)
        t6 = TariffBlockrate(lower=0, upper=10, value=8.4)
        assert t5 != t6
        assert t1 == t1

    def test_bad_lower_type(self):
        for value in [None, 'invalid', 2.5, [], {}]:
            with pytest.raises(TypeError):
                TariffBlockrate(lower=value, upper=10, value=0)

    def test_bad_upper_type(self):
        for value in [None, 'invalid', 2.5, [], {}]:
            with pytest.raises(TypeError):
                TariffBlockrate(lower=0, upper=value, value=0)

    def test_bad_value_type(self):
        for value in [None, 'invalid', u'invalid', True, False, [], {}]:
            with pytest.raises(TypeError):
                TariffBlockrate(lower=0, upper=10, value=value)

    def test_from_dict_empty(self):
        assert not list(TariffBlockrate.from_database('t', [{}]))

    def test_from_dict_invalid_lower_type(self):
        for value in [None, 'invalid', u'invalid', [], {}]:
            assert not list(TariffBlockrate.from_database('t', [dict(lower=value, upper=0, value=0)]))

    def test_from_dict_invalid_upper_type(self):
        for value in [None, 'invalid', u'invalid', [], {}]:
            assert not list(TariffBlockrate.from_database('t', [dict(lower=0, upper=value, value=0)]))

    def test_from_dict_invalid_value_type(self):
        for value in [None, 'invalid', u'invalid', [], {}]:
            assert not list(TariffBlockrate.from_database('t', [dict(lower=0, upper=0, value=value)]))

    def test_from_dict_all_zero(self):
        brs = list(TariffBlockrate.from_database('t', [dict(lower=0, upper=0, value=0)]))
        assert brs == [TariffBlockrate(lower=0, upper=0, value=0)]

    def test_from_dict_all_numbers(self):
        brs = list(TariffBlockrate.from_database('t', [dict(lower=10, upper=20, value=30)]))
        assert brs == [TariffBlockrate(lower=10, upper=20, value=30)]

    def test_from_dict_all_strings(self):
        brs = list(TariffBlockrate.from_database('t', [dict(lower='10', upper='20', value='30')]))
        assert brs == [TariffBlockrate(lower=10, upper=20, value=30)]


class TariffTOUTest(SparkMeterTestCaseBase):
    def test_repr(self):
        tou = TariffTOU(start='8:00', end='18:00', value=3.5)
        assert repr(tou) == '<TariffTOU start=8:00 end=18:00 value=3.5>'

    def test_eq(self):
        t1 = TariffTOU(start='8:00', end='18:00', value=3.5)
        t2 = TariffTOU(start='9:00', end='18:00', value=3.5)
        assert t1 != t2
        t3 = TariffTOU(start='8:00', end='18:00', value=3.5)
        t4 = TariffTOU(start='8:00', end='19:00', value=3.5)
        assert t3 != t4
        t5 = TariffTOU(start='8:00', end='18:00', value=3.5)
        t6 = TariffTOU(start='8:00', end='18:00', value=8.4)
        assert t5 != t6
        assert t1 == t1

    def test_bad_start_type(self):
        for value in [None, 10, 10.5, True, False, [], {}]:
            with pytest.raises(TypeError):
                TariffTOU(start=value, end='18:00', value=None)

    def test_bad_end_type(self):
        for value in [None, 10, 10.5, True, False, [], {}]:
            with pytest.raises(TypeError):
                TariffTOU(start='8:00', end=value, value=0)

    def test_bad_value_type(self):
        for value in [None, 'invalid', True, False, [], {}]:
            with pytest.raises(TypeError):
                TariffTOU(start='8:00', end='18:00', value=value)

    def test_from_dict_invalid_start_type(self):
        for value in [None]:
            assert not list(TariffTOU.from_database('t', [dict(start=value, end='18:00', value=0)]))

    def test_from_dict_invalid_end_type(self):
        for value in [None]:
            assert not list(TariffTOU.from_database('t', [dict(start='8:00', end=value, value=0)]))

    def test_from_dict_invalid_value_type(self):
        for value in [None, {}, [], 'foobar']:
            assert not list(TariffTOU.from_database('t', [dict(start='8:00', end='18:00', value=value)]))

    def test_from_dict(self):
        brs = list(TariffTOU.from_database('t', [dict(start='8:00', end='18:00', value=30)]))
        assert brs == [TariffTOU(start='8:00', end='18:00', value=30)]

    def test_superset_of(self):
        tou = TariffTOU(start='8:00', end='18:00', value=0)
        rv = tou.superset_of(datetime.datetime(2015, 1, 1, 9, tzinfo=tzlocal()),
                             datetime.datetime(2015, 1, 1, 10, tzinfo=tzlocal()))
        assert rv

        rv = tou.superset_of(datetime.datetime(2015, 1, 1, 7, tzinfo=tzlocal()),
                             datetime.datetime(2015, 1, 1, 8, tzinfo=tzlocal()))
        assert not rv

        rv = tou.superset_of(datetime.datetime(2015, 1, 1, 7, tzinfo=tzlocal()),
                             datetime.datetime(2015, 1, 1, 8, tzinfo=tzlocal()))
        assert not rv

    def test_superset_of_midnight_crossing(self):
        tou = TariffTOU(start='22:00', end='2:00', value=0)

        rv = tou.superset_of(datetime.datetime(2015, 1, 1, 23, tzinfo=tzlocal()),
                             datetime.datetime(2015, 1, 2, 1, tzinfo=tzlocal()))
        assert rv

    def test_end_to_min_after_midnight(self):
        tou = TariffTOU(start='0:00', end='0:00', value=0)
        assert tou.end_to_min_after_midnight() == 24 * 60

    @mock.patch('sparkmeter.billing.tzlocal', tzutc)
    @mock.patch('sparkmeter.tariff.tariffdomain.tzlocal', tzutc)
    def test_superset_of_errors(self):
        tou = TariffTOU(start='0:00', end='0:00', value=0)
        start = datetime.datetime(2015, 1, 1, tzinfo=tzutc())
        msg = 'heartbeat_start must be a datetime.datetime, not a \'str\''
        with pytest.raises(TypeError, match=msg):
            tou.superset_of('', '')
        msg = 'heartbeat_end must be a datetime.datetime, not a \'str\''
        with pytest.raises(TypeError, match=msg):
            tou.superset_of(start, '')
        msg = (r'heartbeat_start \(2015-01-01 00:00:00\+00:00\) and '
               r'heartbeat_end \(2015-01-01 00:00:00\+00:00\) must be different')
        with pytest.raises(ValueError, match=msg):
            tou.superset_of(start, start)
        # Create a crazy non-existent timezone that will never be the same
        # as the current local timezone where the tests are run
        non_local = tzoffset('non-local-timezone', -123 * 60)
        msg = r'heartbeat_start must be in tzlocal\(\) timezone'
        with pytest.raises(ValueError, match=msg):
            start = datetime.datetime(2015, 1, 1, tzinfo=non_local)
            end = datetime.datetime(2015, 1, 1, tzinfo=tzutc())
            tou.superset_of(start, end)
        msg = r'heartbeat_end must be in tzlocal\(\) timezone'
        with pytest.raises(ValueError, match=msg):
            start = datetime.datetime(2015, 1, 1, tzinfo=tzutc())
            end = datetime.datetime(2015, 1, 1, tzinfo=non_local)
            tou.superset_of(start, end)

    def test_display_rate(self):
        t = TariffFactory()
        t.tariff_type = 'blockrate'
        t.blockrates = [dict(lower=0, upper=10, value=1),
                        dict(lower=10, upper=30, value=2),
                        dict(lower=30, upper=100, value=3),
                        dict(lower=100, upper=0, value=4)]
        assert t.display_rate() == '1.0 to 4.0'

        t = TariffFactory()
        t.flat_price = 20
        assert t.display_rate() == '20'

    def test_display_tou(self):
        t = Tariff()
        assert t.display_tou() == ''
        t.tous = [
            dict(start='09:00', end='15:00', value=100),
            dict(start='16:00', end='10:00', value=50),
        ]
        t.tou_enabled = True
        assert t.display_tou() == '50% to 100%'

    def test_display_load_limits(self):
        t = Tariff(load_limit_type=Tariff.LOAD_LIMIT_TYPE_FLAT, flat_load_limit=10)
        assert t.display_load_limit() == '10'
        t.load_limits = [
            dict(start='09:00', end='15:00', value=100),
            dict(start='16:00', end='10:00', value=50),
        ]
        t.load_limit_type = Tariff.LOAD_LIMIT_TYPE_SCHEDULED
        assert t.display_load_limit() == '50 to 100'

    def test_display_plan(self):
        t = Tariff(plan_enabled=False)
        assert t.display_plan() == 'Off'
        t.plan_enabled = True
        t.plan_duration_and_start_day = '1m1'
        t.plan_price = 1.0
        t.plan_fixed_fee = 2.0
        assert t.display_plan() == '1 month for 3.0 USD'
        t.plan_duration_and_start_day = '1d1'
        assert t.display_plan() == '1 day for 3.0 USD'

    def test_get_last_cycle_start(self):
        t = TariffFactory()
        dt = datetime.datetime(2018, 1, 1)
        start = t.get_last_cycle_start(dt)
        assert start == dt

    def test_set_empty_tariff_plan_duration(self):
        t = TariffFactory()
        with pytest.raises(ValueError) as valerr:
            t.plan_duration_and_start_day = None
        assert "Cannot set the plan to None" in str(valerr)

    def test_set_zero_tariff_plan_duration_integers(self):
        t = TariffFactory()
        with pytest.raises(ValueError) as valerr:
            t.plan_duration_and_start_day = '0d1'
        assert "Span must be greater than 0" in str(valerr)

        with pytest.raises(ValueError) as valerr:
            t.plan_duration_and_start_day = '1d0'
        assert "Start day must be greater than 0" in str(valerr)

    def test_set_invalid_tariff_plan_duration_unit(self):
        t = TariffFactory()
        with pytest.raises(ValueError) as valerr:
            t.plan_duration_and_start_day = '1w1'
        assert "Invalid plan duration string" in str(valerr)

    def test_empty_tariff_plan_attributes(self):
        t = TariffFactory(plan_duration_span=None)
        assert t.plan_duration_and_start_day is None

        t = TariffFactory(plan_duration_unit=None)
        assert t.plan_duration_and_start_day is None

        t = TariffFactory(cycle_start_day_of_month=None)
        assert t.plan_duration_and_start_day is None

    def test_set_monthly_tariff_plan(self):
        t = TariffFactory()
        t.plan_duration_and_start_day = '1m2'
        assert t.plan_is_monthly
        assert t.plan_duration_span == 1
        assert t.cycle_start_day_of_month == 2

    def test_set_daily_tariff_plan(self):
        t = TariffFactory()
        t.plan_duration_and_start_day = '1d1'
        assert t.plan_is_daily
        assert t.plan_duration_span == 1
