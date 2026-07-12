# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
import contextlib
import datetime
import random
from builtins import map, range, str
from unittest import mock

import pytest
from freezegun import freeze_time

from sparkmeter.meter.meterstate import MeterState
from sparkmeter.reading.readingcommand import ReadingGenerator
from sparkmeter.reading.readingdomain import Reading
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import EventFactory, MeterFactory


@contextlib.contextmanager
def deterministic_random(seed=0):
    state = random.getstate()
    random.seed(seed)
    yield
    random.setstate(state)


class ReadingCommandTest(SparkMeterTestCaseBase):
    @freeze_time("2013-01-01T01:01:01")
    def test_create_fake(self, cli, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()
        meter = MeterFactory()
        self.session.commit()

        cli("reading", "create-fake", "-s", meter.serial)

        reading = Reading.query.one()
        assert reading.meter == str(meter.code)
        assert reading.heartbeat_start == datetime.datetime(2013, 1, 1, 1, 0, 0)
        assert reading.heartbeat_end == datetime.datetime(2013, 1, 1, 1, 15, 0)
        assert reading.state == MeterState.STATE_ON.id
        assert reading.energy == 0.015

        cli("reading", "create-fake", "-s", meter.serial)

        reading = (
            Reading.query.filter_by(meter=str(meter.code))
            .order_by(Reading.heartbeat_end.desc())
            .limit(1)
            .scalar()
        )
        assert reading.meter == str(meter.code)
        assert reading.heartbeat_start == datetime.datetime(2013, 1, 1, 1, 15, 0)
        assert reading.heartbeat_end == datetime.datetime(2013, 1, 1, 1, 30, 0)
        assert reading.state == MeterState.STATE_ON.id
        assert reading.energy == 0.03
        assert event_create.mock_calls == [
            mock.call("customer-low-balance", obj=mock.ANY),
            mock.call("customer-low-balance", obj=mock.ANY),
        ]

    def test_create_fake_error(self, cli):
        result = cli("reading", "create-fake", "-s", "abracadabra")
        assert result.exit_code == 1

    def test_create_fake_cycle(self, cli):
        with mock.patch.object(ReadingGenerator, "run_cycle_loop") as run_cycle_loop:
            cli("reading", "create-fake", "-c", "15")
            run_cycle_loop.assert_called_once()


class ReadingGeneratorTest(SparkMeterTestCaseBase):
    def test_get_meters(self):
        gen = ReadingGenerator(60, 15)
        with deterministic_random():
            all_meters = list(range(500))
            parts = gen.get_meters(all_meters)
            assert list(map(len, parts)), [376, 90, 21, 7 == 6]

        with deterministic_random():
            all_meters = list(range(70000))
            parts = gen.get_meters(all_meters)
            assert len(parts) == 10

    @mock.patch("time.sleep")
    @freeze_time("2013-01-01T01:01:01")
    def test_run_cycle_loop(self, sleep):
        gen = ReadingGenerator(60, 15)
        gen.heartbeat = mock.Mock()
        MyException = type("MyException", (Exception,), {})
        gen.heartbeat.side_effect = [None, MyException]
        with pytest.raises(MyException):
            gen.run_cycle_loop()

        assert gen.heartbeat.mock_calls == [
            mock.call(
                [], start=datetime.datetime(2013, 1, 1, 1, 0), end=datetime.datetime(2013, 1, 1, 1, 15)
            ),
            mock.call(
                [], start=datetime.datetime(2013, 1, 1, 1, 15), end=datetime.datetime(2013, 1, 1, 1, 30)
            ),
        ]

    def test_heartbeat(self, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()
        sleep = mocker.patch("time.sleep")
        m1 = MeterFactory()
        self.session.commit()

        heartbeat_start = datetime.datetime(2013, 1, 1, 1, 15, 0)
        heartbeat_end = datetime.datetime(2013, 1, 1, 1, 30, 0)
        gen = ReadingGenerator(60, 15)
        gen.heartbeat([[m1]], heartbeat_start, heartbeat_end)

        readings = Reading.get_all()
        assert len(readings) == 1
        reading = readings[0]
        assert reading.meter == str(m1.code)
        assert reading.heartbeat_start == heartbeat_start
        assert reading.heartbeat_end == heartbeat_end

        # Ensure that no duplicates are inserted
        gen.heartbeat([[m1]], heartbeat_start, heartbeat_end)
        readings = Reading.get_all()
        assert len(readings) == 1

        assert event_create.mock_calls == [
            mock.call("customer-low-balance", obj=mock.ANY),
        ]
        assert sleep.mock_calls == [mock.call(60)] * 30
