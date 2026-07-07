# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Config views unittest."""
from sparkmeter.tests.base import WebViewTestCaseBase


class ConfigTest(WebViewTestCaseBase):
    def test_billing(self, client, config):
        client.login_as(self.user)
        path = '/config/billing'
        config['HEROKU'] = True
        response = client.get(path)
        self.verify_response(response)

    def test_sms(self, client, config):
        path = '/config/sms'
        config['HEROKU'] = True
        response = client.get(path)
        self.verify_response(response)

    def test_sms_template_help(self, client):
        path = '/config/sms-template-help'
        response = client.get(path + '?event_type=customer-low-balance')
        self.verify_response(response)

    def test_meters(self, client, config):
        client.login_as(self.user)
        config['HEROKU'] = True
        path = '/config/meters'
        response = client.get(path)
        self.verify_response(response)
