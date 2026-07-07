# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.

import gzip
import io
from types import SimpleNamespace
from unittest import mock

import pytest
from flask.blueprints import Blueprint
from flask.globals import request
from flask.helpers import url_for
from flask.wrappers import Response
from testfixtures import LogCapture
from zope.component import getUtility

from sparkmeter.app import SparkmeterApplication
from sparkmeter.config.configparameter import parameters
from sparkmeter.interface import IApplication
from sparkmeter.tests.base import WebViewTestCaseBase


@pytest.fixture()
def logger():
    with LogCapture('sparkmeter.app') as logger:
        yield logger


@pytest.fixture(scope="module", autouse=True)
def _setup_module(app):
    blueprint = Blueprint("unittest", __name__)

    @blueprint.route("/gzip/", methods=['GET'])
    def gzip_test():
        data = request.args.get('data')
        mime = request.args.get('mime')
        r = Response(data, mimetype=mime)
        r.direct_passthrough = request.args.get('direct', False)
        return r

    if 'unittest' not in app.blueprints:
        app._got_first_request = False
        app.register_blueprint(blueprint)
        app._got_first_request = True


class RequireProductionSecretsTest:
    """Directly exercise the production fail-fast guard.

    ``_require_production_secrets`` only reads ``mode`` and the configured
    secret values, so it can be invoked on a bare namespace without booting
    the full application. ``_call`` supplies a valid value for every required
    secret by default, so each test isolates a single missing secret.
    """

    def _call(self, mode, salt='a-configured-salt', secret_key='a-configured-secret-key'):
        stub = SimpleNamespace(MODE_PRODUCTION=SparkmeterApplication.MODE_PRODUCTION)
        config = {'SECURITY_PASSWORD_SALT': salt, 'SECRET_KEY': secret_key}
        SparkmeterApplication._require_production_secrets(stub, config, mode)

    def test_production_missing_salt_raises(self):
        with pytest.raises(SystemExit) as excinfo:
            self._call(SparkmeterApplication.MODE_PRODUCTION, None)
        assert 'SM_SECURITY_PASSWORD_SALT' in str(excinfo.value)

    def test_production_empty_salt_raises(self):
        with pytest.raises(SystemExit) as excinfo:
            self._call(SparkmeterApplication.MODE_PRODUCTION, '')
        assert 'SM_SECURITY_PASSWORD_SALT' in str(excinfo.value)

    def test_production_whitespace_salt_raises(self):
        with pytest.raises(SystemExit) as excinfo:
            self._call(SparkmeterApplication.MODE_PRODUCTION, '   ')
        assert 'SM_SECURITY_PASSWORD_SALT' in str(excinfo.value)

    def test_production_with_salt_does_not_raise(self):
        self._call(SparkmeterApplication.MODE_PRODUCTION, 'a-configured-salt')

    @pytest.mark.parametrize('mode', [
        SparkmeterApplication.MODE_UNITTEST,
        SparkmeterApplication.MODE_MANAGE,
        SparkmeterApplication.MODE_ALEMBIC,
        SparkmeterApplication.MODE_UNKNOWN,
    ])
    def test_non_production_missing_salt_does_not_raise(self, mode):
        self._call(mode, None)

    def test_load_configuration_invokes_guard(self):
        """Wire-check that _load_configuration actually calls the guard.

        Deleting the guard call from _load_configuration must not pass
        silently. A unique sentinel as ``mode`` (asserted by identity) also
        catches a regression that forwards a hardcoded mode instead of
        ``self.mode``.
        """
        sentinel_mode = object()
        stub = SimpleNamespace(
            mode=sentinel_mode,
            _require_production_secrets=mock.Mock(),
        )
        with mock.patch('sparkmeter.config.configdict.config'):
            SparkmeterApplication._load_configuration(stub)
        stub._require_production_secrets.assert_called_once()
        assert stub._require_production_secrets.call_args.args[-1] is sentinel_mode

    def test_production_missing_secret_key_raises(self):
        with pytest.raises(SystemExit) as excinfo:
            self._call(SparkmeterApplication.MODE_PRODUCTION, secret_key=None)
        assert 'SM_SECRET_KEY' in str(excinfo.value)

    def test_production_empty_secret_key_raises(self):
        with pytest.raises(SystemExit) as excinfo:
            self._call(SparkmeterApplication.MODE_PRODUCTION, secret_key='')
        assert 'SM_SECRET_KEY' in str(excinfo.value)

    def test_production_whitespace_secret_key_raises(self):
        with pytest.raises(SystemExit) as excinfo:
            self._call(SparkmeterApplication.MODE_PRODUCTION, secret_key='   ')
        assert 'SM_SECRET_KEY' in str(excinfo.value)

    def test_production_with_both_secrets_does_not_raise(self):
        self._call(SparkmeterApplication.MODE_PRODUCTION)

    @pytest.mark.parametrize('mode', [
        SparkmeterApplication.MODE_UNITTEST,
        SparkmeterApplication.MODE_MANAGE,
        SparkmeterApplication.MODE_ALEMBIC,
        SparkmeterApplication.MODE_UNKNOWN,
    ])
    def test_non_production_missing_secret_key_does_not_raise(self, mode):
        self._call(mode, secret_key=None)


class PasswordSaltConfiguredTest:
    """Truth table for the password_salt_configured helper."""

    @pytest.mark.parametrize('salt, expected', [
        (None, False),
        ('', False),
        ('   ', False),
        ('\t\n', False),
        ('a-real-salt', True),
        ('  padded-but-real  ', True),
    ])
    def test_truth_table(self, salt, expected):
        from sparkmeter.app import password_salt_configured
        assert password_salt_configured({'SECURITY_PASSWORD_SALT': salt}) is expected


class SecretConfiguredTest:
    """Truth table for the generic secret_configured helper."""

    @pytest.mark.parametrize('value, expected', [
        (None, False),
        ('', False),
        ('   ', False),
        ('\t\n', False),
        (12345, False),
        ('a-real-secret', True),
        ('  padded-but-real  ', True),
    ])
    def test_truth_table(self, value, expected):
        from sparkmeter.app import secret_configured
        assert secret_configured({'SECRET_KEY': value}, 'SECRET_KEY') is expected


class HardenSessionCookieTest:
    """The session-cookie Secure flag tracks whether HTTPS is in effect."""

    def test_secure_off_without_https(self):
        stub = SimpleNamespace(config={}, _should_use_https=lambda: False)
        SparkmeterApplication._harden_session_cookie(stub)
        assert stub.config['SESSION_COOKIE_SECURE'] is False

    def test_secure_on_with_https(self):
        stub = SimpleNamespace(config={}, _should_use_https=lambda: True)
        SparkmeterApplication._harden_session_cookie(stub)
        assert stub.config['SESSION_COOKIE_SECURE'] is True

    def test_secure_preset_true_preserved(self):
        # An HTTPS-terminating gateway sets SESSION_COOKIE_SECURE=True; the
        # promote-only logic must not downgrade it even when _should_use_https
        # is False (the app cannot detect TLS terminated upstream by nginx).
        stub = SimpleNamespace(config={'SESSION_COOKIE_SECURE': True},
                               _should_use_https=lambda: False)
        SparkmeterApplication._harden_session_cookie(stub)
        assert stub.config['SESSION_COOKIE_SECURE'] is True

    def test_setup_flask_and_extensions_invokes_hardening(self):
        """_setup_flask_and_extensions must actually call _harden_session_cookie.

        Deleting the call would silently drop session-cookie hardening in
        production while every other test still passed.
        """
        stub = SimpleNamespace(
            config={},
            _harden_session_cookie=mock.Mock(),
            _setup_flask_security=mock.Mock(),
            _setup_bootstrap=mock.Mock(),
            _setup_babel=mock.Mock(),
            _setup_jinja=mock.Mock(),
            _setup_permissions=mock.Mock(),
            _setup_filters=mock.Mock(),
            _register_blueprints=mock.Mock(),
        )
        SparkmeterApplication._setup_flask_and_extensions(stub)
        stub._harden_session_cookie.assert_called_once()


class AppTest(WebViewTestCaseBase):
    def test_session_cookie_hardened(self, client):
        # `client` boots the shared app via the fixture before we read its config.
        app = getUtility(IApplication)
        assert app.config['SESSION_COOKIE_HTTPONLY'] is True
        assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
        # MODE_UNITTEST is not HTTPS, so Secure stays off for the test client.
        assert app.config['SESSION_COOKIE_SECURE'] is False

    def test_gzip(self, client):
        data = "x" * 1024
        response = client.get(
            url_for("unittest.gzip_test", data=data, mime="application/json"),
            headers={'Accept-Encoding': 'gzip'})
        assert response.headers['Content-Encoding'] == 'gzip'
        buf = io.BytesIO(response.data)
        assert gzip.GzipFile(mode='r', fileobj=buf).read() == data.encode()

    def test_gzip_wrong_status(self, client):
        response = client.get("/404")
        assert 'Content-Encoding' not in response.headers

    def test_gzip_passthrough(self, client):
        data = "x" * 1024
        response = client.get(
            url_for("unittest.gzip_test", data=data, mime="application/json",
                    direct='1'),
            headers={'Accept-Encoding': 'gzip'})
        assert 'Content-Encoding' not in response.headers
        assert response.data == data.encode()

    def test_gzip_too_small(self, client):
        data = "small"
        response = client.get(
            url_for("unittest.gzip_test", data=data, mime="application/json"))
        assert 'Content-Encoding' not in response.headers
        assert response.data == data.encode()

    def test_gzip_no_user_agent_support(self, client):
        data = "x" * 1024
        response = client.get(
            url_for("unittest.gzip_test", data=data, mime="application/json"),
            headers={'Accept-Encoding': ''})
        assert 'Content-Encoding' not in response.headers
        assert response.data == data.encode()

    def test_gzip_wrong_mime(self, client):
        data = "x" * 1024
        response = client.get(
            url_for("unittest.gzip_test", data=data, mime="unsupported/mime-type"),
            headers={'Accept-Encoding': 'gzip'})
        assert 'Content-Encoding' not in response.headers
        assert response.data == data.encode()

    def test_maybe_send_broadcast(self, config, logger, mocker):
        update_all_active_customer_meters = mocker.patch(
            'sparkmeter.ground.grounddomain.Ground.update_all_active_customer_meters')
        config['HEROKU'] = True
        del config['SERIAL']
        self.ground.private.override_meter_state = False
        parameters.SEND_SET_CONFIG_AT_STARTUP = False

        app = getUtility(IApplication)
        assert not app._maybe_send_broadcast()
        logger.check()
        logger.clear()
        assert update_all_active_customer_meters.mock_calls == []

        config['HEROKU'] = False
        assert not app._maybe_send_broadcast()
        logger.check(
            ('sparkmeter.app', 'INFO',
             'No ground found, not sending set-config to active meters.')
        )
        logger.clear()
        assert update_all_active_customer_meters.mock_calls == []

        config['SERIAL'] = self.ground.serial
        assert not app._maybe_send_broadcast()
        logger.check(
            ('sparkmeter.app', 'INFO',
             'Override meter state disable, not sending set-config to active meters.')
        )
        logger.clear()
        assert update_all_active_customer_meters.mock_calls == []

        self.ground.private.override_meter_state = True
        assert not app._maybe_send_broadcast()
        logger.check(
            ('sparkmeter.app', 'INFO',
             'Configuration parameter disabled, not sending set-config to active meters.')
        )
        logger.clear()
        assert update_all_active_customer_meters.mock_calls == []

        parameters.SEND_SET_CONFIG_AT_STARTUP = True
        assert app._maybe_send_broadcast()
        logger.check(
            ('sparkmeter.app', 'INFO',
             'Sending set-config to active meters, with override enabled.')
        )
        logger.clear()
        assert update_all_active_customer_meters.mock_calls == [
            mock.call(),
        ]
