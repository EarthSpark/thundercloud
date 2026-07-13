# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.

import datetime
import http.client
import uuid
from unittest import mock

import pytest
from freezegun import freeze_time

from sparkmeter.config.configparameter import ParameterObject, parameters
from sparkmeter.tests.base import WebViewTestCaseBase
from sparkmeter.tests.test_data_factory import EventFactory


@pytest.fixture(scope="function")
def open_instance_resource(mocker):
    yield mocker.patch("sparkmeter.web.views.current_app.open_instance_resource", create=True)


class WebViewTest(WebViewTestCaseBase):
    def test_reset_demo_data(self, client, config):
        path = "/reset-demo"

        config.update(HEROKU=False, ENABLE_DEMO_RESET=True)
        response = client.get(path)

        self.verify_response(response)

    def test_reset_demo_data_post(self, client, config, mocker):
        reset_demo = mocker.patch("sparkmeter.web.views.reset_demo")
        path = "/reset-demo"

        config.update(HEROKU=False, ENABLE_DEMO_RESET=True)
        response = client.post(path)
        self.verify_response(response, variant="post")

        response = client.post(path, data=dict(confirm="YES"))
        assert response.data == b"System reset"
        reset_demo.assert_called_once()

    def test_reset_demo_data_disabled(self, client, config):
        path = "/reset-demo"

        config.update(HEROKU=False, ENABLE_DEMO_RESET=False)
        response = client.get(path)
        self.verify_response(response)

    def test_demo_login_user_not_found(self, client, config):
        path = "/demo-login/%s" % "44769678-0003-4a63-94d8-1be7a417216a"
        config["HEROKU"] = False
        response = client.get(path)
        assert response.status_code == http.client.NOT_FOUND

    def test_login_cloud(self, client, config):
        path = "/login"
        client.logout()

        config.update(HEROKU=True, ENABLE_DEMO_LOGIN=True)
        response = client.get(path)
        self.verify_response(response)

        self.ground.remove()
        self.session.commit()

        response = client.get(path)
        self.verify_response(response, variant="empty")

    def test_login_ground(self, client, config):
        path = "/login"
        client.logout()

        config.update(HEROKU=False, ENABLE_DEMO_LOGIN=True)
        response = client.get(path)
        self.verify_response(response)

        self.ground.remove()
        self.session.commit()

        response = client.get(path)
        self.verify_response(response, variant="empty")

    def test_demo_login_enabled(self, client, config):
        path = "/login"
        client.logout()
        config.update(HEROKU=False, ENABLE_DEMO_LOGIN=True)
        response = client.get(path)
        self.verify_response(response, variant="demo_login_enabled")

        demo_login_path = "/demo-login/%s" % self.user.id
        demo_login_response = client.get(demo_login_path)
        self.verify_response(demo_login_response)

    def test_demo_login_rejects_external_next(self, client, config):
        client.logout()
        config.update(HEROKU=False, ENABLE_DEMO_LOGIN=True)
        response = client.get("/demo-login/%s?next=https://evil.example.com/" % self.user.id)
        assert response.status_code == 302
        assert "evil.example.com" not in response.headers["Location"]

    def test_demo_login_rejects_backslash_next(self, client, config):
        # Browsers fold backslashes to '/', so /\evil becomes //evil
        # (protocol-relative cross-origin); the guard must reject it.
        client.logout()
        config.update(HEROKU=False, ENABLE_DEMO_LOGIN=True)
        response = client.get("/demo-login/%s?next=/\\evil.example.com" % self.user.id)
        assert response.status_code == 302
        assert "evil.example.com" not in response.headers["Location"]

    def test_demo_login_allows_local_next(self, client, config):
        client.logout()
        config.update(HEROKU=False, ENABLE_DEMO_LOGIN=True)
        response = client.get("/demo-login/%s?next=/dashboard" % self.user.id)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/dashboard")

    def test_flashed_message_is_html_escaped(self, app):
        # base.html renders flashes with {{ message }} (no |safe), so a plain
        # string flash with markup is escaped -- not executed (XSS guard).
        from flask import flash, render_template_string

        with app.test_request_context():
            flash('<script>alert(1)</script> "x"')
            rendered = render_template_string("{% for m in get_flashed_messages() %}{{ m }}{% endfor %}")
        assert "<script>" not in rendered
        assert "&lt;script&gt;" in rendered

    def test_flashed_markup_renders_as_html(self, app):
        # A Markup-wrapped flash (e.g. a build_link anchor) still renders as HTML.
        # This covers the Jinja layer; the cross-request session round-trip
        # (Flask's TaggedJSONSerializer preserving Markup across POST->redirect->
        # GET) is covered by the link-flash view snapshots, e.g.
        # tariff/user/meter "created" tests, which render a raw anchor.
        from flask import flash, render_template_string
        from markupsafe import Markup

        with app.test_request_context():
            flash(Markup('<a href="/u">user</a>'))
            rendered = render_template_string("{% for m in get_flashed_messages() %}{{ m }}{% endfor %}")
        assert '<a href="/u">user</a>' in rendered

    def test_demo_login_disabled(self, client, config):
        path = "/login"
        client.logout()
        config.update(HEROKU=False, ENABLE_DEMO_LOGIN=False)
        response = client.get(path)
        self.verify_response(response, variant="demo_login_disabled")

        demo_login_path = "/demo-login/%s" % self.user.id
        demo_login_response = client.get(demo_login_path)
        self.verify_response(demo_login_response)

    def test_change_password_view(self, client, config):
        path = "/change"

        config["HEROKU"] = False
        response = client.get(path)
        self.verify_response(response)

    def test_change_password_view_portal(self, client, config):
        path = "/change"
        self.user.portal_id = uuid.uuid4()
        self.session.commit()

        response = client.get(path)
        assert "managed by the SparkMeter Cloud Portal" in response.text
        self.verify_response(response)

    def test_change_password_update(self, client):
        path = "/change"

        data = {
            "password": "pass",
            "new_password": "new-password",
            "new_password_confirm": "new-password",
            "submit": "Change Password",
        }
        with mock.patch("flask_security.changeable.hash_password") as hash_password:
            hash_password.return_value = "encrypted-password"
            response = client.post(path, data=data)
        self.verify_response(response)
        assert self.user.password == "encrypted-password"

    @freeze_time("2017-06-05 12:23:01")
    def test_override_banner_on_ground(self, client, config, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()

        disable_all_meters = mocker.patch("sparkmeter.ground.grounddomain.disable_all_meters")
        config.update(HEROKU=False)

        with freeze_time(datetime.datetime(2017, 6, 2, 15, 29, 43, 79060)):
            self.ground.private.set_override_meter_state(True)
            self.session.commit()
        assert disable_all_meters.mock_calls == []
        disable_all_meters.reset_mock()

        parameters.SEND_BROADCAST_SIGNAL = True
        try:
            with freeze_time(datetime.datetime(2017, 6, 2, 15, 29, 43, 79060)):
                self.ground.private.set_override_meter_state(True)
                self.session.commit()
            assert disable_all_meters.mock_calls == [mock.call()]

            path = "/"
            response = client.get(path)
            self.verify_response(response)
        finally:
            parameters.SEND_BROADCAST_SIGNAL = False
        assert event_create.mock_calls == [
            mock.call("config-parameter-changed", obj=ParameterObject.SEND_BROADCAST_SIGNAL.parameter),
            mock.call("config-parameter-changed", obj=ParameterObject.SEND_BROADCAST_SIGNAL.parameter),
        ]

    @freeze_time("2017-06-05 12:23:01")
    def test_override_banner_on_cloud(self, client, config):
        config.update(HEROKU=True)
        with freeze_time(datetime.datetime(2017, 6, 2, 15, 29, 43, 79060)):
            self.ground.private.set_override_meter_state(True)
            self.session.commit()

        path = "/"
        response = client.get(path)
        self.verify_response(response)

    @freeze_time("2017-11-27 12:24:36")
    def test_favicon(self, client):
        response = client.get("/favicon.ico")
        self.verify_response(response)

    def test_readonly_app(self, client, config):
        config.update(READONLY=True)
        path = "/"
        response = client.get(path)
        self.verify_response(response)

    def test_readonly_app_json(self, client, config):
        config.update(READONLY=True)
        path = "/api/test"
        response = client.get(path)
        self.verify_response(response)
