# -*- coding: utf-8 -*-
# Copyright © 2013-2019 SparkMeter, Inc.
# All Rights Reserved.
from sparkmeter.tests.base import SparkMeterTestCaseBase


class SystemCommandTest(SparkMeterTestCaseBase):

    def test_system_methods(self, config):
        config['HEROKU'] = False
        assert config.local_system == config.GROUND
        assert config.is_ground() is True
        assert config.is_cloud() is False

        config['HEROKU'] = True
        assert config.local_system == config.CLOUD
        assert config.is_ground() is False
        assert config.is_cloud() is True
