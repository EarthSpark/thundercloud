# -*- coding: utf-8 -*-
# Copyright © 2013-2019 SparkMeter, Inc.
# All Rights Reserved.
from sparkmeter.tests.base import SparkMeterTestCaseBase


class SystemCommandTest(SparkMeterTestCaseBase):
    def test_system_methods(self, config):
        config["HEROKU"] = False
        assert config.local_system == config.GROUND
        assert config.is_ground() is True
        assert config.is_cloud() is False

        config["HEROKU"] = True
        assert config.local_system == config.CLOUD
        assert config.is_ground() is False
        assert config.is_cloud() is True

    def test_is_offline(self, config):
        # OFFLINE unset defaults to online; the flag reads the OFFLINE config
        # value, which config normalizes from SM_OFFLINE at load time.
        config.pop("OFFLINE", None)
        assert config.is_offline() is False
        config["OFFLINE"] = False
        assert config.is_offline() is False
        config["OFFLINE"] = True
        assert config.is_offline() is True
