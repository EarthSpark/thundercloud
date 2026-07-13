# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import datetime
import socket
from builtins import str
from unittest import mock

import pytest

from sparkmeter.dashboard.dashboarddomain import DashboardDailyTariffSummary
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.meter.meterdomain import Meter
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import GroundFactory, MeterFactory, SalesAccountFactory, TariffFactory


class GroundTest(SparkMeterTestCaseBase):
    def test_create_empty(self):
        m = Ground.create_empty(self.session, "serial", "name", "secret-key")
        self.session.commit()
        assert m.serial == "serial"
        assert m.name == "name"
        assert m.private.secret_key == "secret-key"
        assert m.address

    def test_create_empty_config_defaults(self, config):
        config.update(SERIAL="env-serial", GROUND_NAME="env-name", SPARKCLOUD_API_KEY="env-key")
        m = Ground.create_empty(self.session)
        self.session.commit()
        assert m.serial == "env-serial"
        assert m.name == "env-name"
        assert m.private.secret_key == "env-key"
        assert m.address

    def test_create_empty_defaults(self, config):
        config.update(SERIAL="", GROUND_NAME="", SPARKCLOUD_API_KEY="")
        m = Ground.create_empty(self.session)
        self.session.commit()
        hostname = socket.gethostname()
        assert m.name == hostname
        assert m.serial == hostname + "-serial"
        assert m.private.secret_key == hostname + "-secret-key"

    def test_create_duplicate(self):
        with pytest.raises(ValueError) as ctx:
            Ground.create_empty(self.session, name=self.ground.name)
        assert str(ctx.value) == "A ground with name test micr\xf8grid 1 already exists"
        with pytest.raises(ValueError) as ctx:
            Ground.create_empty(self.session, serial=self.ground.serial)
        assert str(ctx.value) == "A ground with serial groundserial1 already exists"

    def test_get_used_capacity(self):
        ground = self.ground

        tariff1 = TariffFactory(flat_load_limit=1)
        tariff2 = TariffFactory(flat_load_limit=10)

        MeterFactory(code="1", ground=ground, tariff=tariff1)
        MeterFactory(code="2", ground=ground, tariff=tariff2)
        MeterFactory(code="3", ground=ground, tariff=tariff2)
        self.session.commit()

        assert ground.get_used_capacity() == 21

    def test_get_default(self, config):
        # what is this doing?
        # ground = Ground.get_default()
        # assert not ground

        m1 = GroundFactory(name="abc", serial="SERIAL1")
        m2 = GroundFactory(name="def", serial="SERIAL2")
        self.session.commit()

        config["SERIAL"] = "SERIAL1"
        assert Ground.get_default().id == m1.id

        config["SERIAL"] = "SERIAL2"
        assert Ground.get_default().id == m2.id

        config["SERIAL"] = None
        assert Ground.get_default().id == m1.id

    def test_get_last_sync_date(self, config, mocker):
        get_heartbeat_time = mocker.patch("sparkmeter.database.symmetricdsdomain.NodeHost.get_heartbeat_time")

        config["HEROKU"] = True
        self.ground.get_last_sync_date()
        get_heartbeat_time.assert_called_once_with(mock.ANY, self.ground.serial)

        get_heartbeat_time.reset_mock()
        config["HEROKU"] = False
        self.ground.get_last_sync_date()
        get_heartbeat_time.assert_called_once_with(mock.ANY, "cloud")

    def test_remove(self):
        ground = GroundFactory()
        self.session.commit()
        MeterFactory(ground=ground)
        tariff = TariffFactory()
        summary = DashboardDailyTariffSummary(
            ground=ground,
            tariff=tariff,
            transaction_amount=0,
            transaction_count=0,
            kwh_consumed=0,
            date=datetime.date(2010, 1, 1),
        )
        self.session.add(summary)
        self.session.commit()
        SalesAccountFactory(ground=ground)
        self.session.commit()
        assert DashboardDailyTariffSummary.query.count() == 1
        assert SalesAccount.query.filter_by(ground=ground).count() == 1

        ground.remove()
        self.session.commit()

        assert DashboardDailyTariffSummary.query.count() == 0
        assert SalesAccount.query.filter_by(ground=ground).count() == 0
        assert Meter.query.filter_by(ground=ground).count() == 0
