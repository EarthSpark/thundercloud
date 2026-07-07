# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
import uuid

from sparkmeter.tests.base import WebViewTestCaseBase


class HomepageViewTest(WebViewTestCaseBase):
    path = "/"

    def test_homepage(self, client):
        response = client.get(self.path)
        assert response.status_code == 200

    def test_cloud_portal_link_present(self, client):
        self.user.portal_id = uuid.uuid4()
        self.session.commit()

        response = client.get(self.path)
        assert 'data-name="koios"' in response.text
        self.verify_response(response)

    def test_cloud_portal_link_absent(self, client):
        response = client.get(self.path)
        assert 'data-name="koios"' not in response.text
        self.verify_response(response)

    def test_cloud_portal_link_absent_ground(self, client, config):
        self.user.portal_id = uuid.uuid4()
        self.session.commit()
        config['HEROKU'] = False

        response = client.get(self.path)
        assert 'data-name="koios"' not in response.text
        self.verify_response(response)
