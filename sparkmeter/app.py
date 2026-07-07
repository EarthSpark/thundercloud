# -*- coding: utf-8 -*-
# Copyright © 2013-2025 SparkMeter, Inc.
# All Rights Reserved.
"""Package for the sparkmeter flask application."""

import gzip
import io
import logging
import os
import sys

# Fix bcrypt compatibility issue with newer versions
try:
    import bcrypt
    if not hasattr(bcrypt, '__about__'):
        # Create a dummy __about__ attribute to prevent passlib warnings
        bcrypt.__about__ = type('About', (), {'__version__': '4.0.0'})()
except ImportError:
    pass

# Fix pandas 2.x compatibility for vincent library (iteritems removed)
# TODO: Replace vincent with a maintained library (e.g. plotly or altair)
import pandas

if not hasattr(pandas.Series, 'iteritems'):
    pandas.Series.iteritems = pandas.Series.items

from flask import Flask

logger = logging.getLogger(__name__)
# Smallest request we can compress, no point in compressing data that
# can fit in one packet anyway;
# Akamai uses 860 as a limit for their CDN, just copy that.
# http://calendar.perfplanet.com/2012/is-your-cdn-intentionally-hurting-your-performance/
# http://webmasters.stackexchange.com/questions/31750
_GZIP_MIN_SIZE = 860
_GZIP_LEVEL = 6
_GZIP_MIMETYPES = [
    'application/javascript',
    'application/json',
    'text/css',
    'text/html',
]


# Secrets that must be configured before a request-serving process boots.
# Each entry maps the config key to the SM_* env override operators set.
REQUIRED_PRODUCTION_SECRETS = (
    ('SECRET_KEY', 'SM_SECRET_KEY'),
    ('SECURITY_PASSWORD_SALT', 'SM_SECURITY_PASSWORD_SALT'),
)


def secret_configured(config, key):
    """Return True when ``config[key]`` holds a usable secret value.

    ``None``, the empty string, whitespace-only strings, and non-string
    values all count as *not configured*, so the fail-fast guards treat them
    identically.
    """
    value = config.get(key)
    return bool(isinstance(value, str) and value.strip())


def password_salt_configured(config):
    """Return True when SECURITY_PASSWORD_SALT holds a usable value."""
    return secret_configured(config, 'SECURITY_PASSWORD_SALT')


class SparkmeterApplication(Flask):

    """Flask application subclass."""

    MODE_ALEMBIC = 'alembic'
    MODE_MANAGE = 'manage'
    MODE_PRODUCTION = 'production'
    MODE_UNITTEST = 'unittest'
    MODE_UNKNOWN = 'unknown'

    STATIC_FOLDER_CANDIDATES = [
        os.path.join(os.path.dirname(__file__), '..', 'static'),
        os.path.join(sys.prefix, 'share', 'sparkmeter', 'static'),
    ]

    def __init__(self, mode=MODE_UNKNOWN):
        """Flask app factory."""
        super(SparkmeterApplication, self).__init__(
            __name__,
            static_folder=self._get_static_folder())
        self.mode = mode
        self.developer_mode = os.path.exists(
            os.path.join(os.path.dirname(__file__), '..', '.git'))
        self._setup_logging()
        self._load_configuration()
        self._load_domain_modules()

    def _get_static_folder(self):
        for candidate in self.STATIC_FOLDER_CANDIDATES:
            if os.path.exists(candidate):
                return os.path.abspath(candidate)
        raise SystemExit("Couldn't find static_folder")  # pragma: nocoverage

    def provide(self):
        """Provide the IApplication utility for this application instance."""
        self._provide_utility()

    def bootstrap(self):
        """Bootstrap the application environment."""
        self.provide()

        try:
            import uwsgi  # noqa: F401
            under_uwsgi = True
        except ImportError:
            under_uwsgi = False

        if self.mode in (self.MODE_PRODUCTION, self.MODE_MANAGE):  # pragma: nocoverage
            from sparkmeter.database.database import bootstrap_production
            if self.mode == self.MODE_MANAGE or not under_uwsgi:
                # Single-process init paths (manage CLI, ASGI server) — no inter-worker
                # contention to serialize, just bootstrap directly.
                bootstrap_production(self)
            else:
                # MODE_PRODUCTION under uwsgi: serialize bootstrap across workers.
                from sparkmeter.web.uwsgiutils import uwsgi_worker_lock
                with uwsgi_worker_lock(1) as first:
                    if first:
                        bootstrap_production(self)

        self._setup_sqlalchemy()
        self._setup_flask_and_extensions()
        self._setup_sentry()

        # Register CLI commands
        from sparkmeter.cli import register_cli_commands
        register_cli_commands(self)

        if self.mode == self.MODE_UNITTEST:
            self._setup_unittest()
        elif self.mode in (self.MODE_PRODUCTION, self.MODE_MANAGE):  # pragma: nocoverage
            if self.mode == self.MODE_MANAGE or not under_uwsgi:
                with self.app_context():
                    self._maybe_send_broadcast()
            else:
                from sparkmeter.web.uwsgiutils import uwsgi_worker_lock
                with uwsgi_worker_lock(2) as first:
                    if first:
                        with self.app_context():
                            self._maybe_send_broadcast()

    def _maybe_send_broadcast(self):
        from sparkmeter.ground.grounddomain import Ground
        if self.config['HEROKU']:
            return False
        ground = Ground.get_current()
        if ground is None:
            logger.info("No ground found, "
                        "not sending set-config to active meters.")
            return False
        if not ground.private.override_meter_state:
            logger.info("Override meter state disable, "
                        "not sending set-config to active meters.")
            return False
        from sparkmeter.config.configparameter import parameters
        if not parameters.SEND_SET_CONFIG_AT_STARTUP:
            logger.info("Configuration parameter disabled, "
                        "not sending set-config to active meters.")
            return False
        logger.info("Sending set-config to active meters, "
                    "with override enabled.")
        ground.update_all_active_customer_meters()
        return True

    def setup_databases(self):
        """Connect to a database."""
        self._setup_sqlalchemy()
        # These two are used by (the reset command)
        self._setup_flask_security()
        self._setup_babel()

    def _setup_flask_and_extensions(self):
        self._harden_session_cookie()
        self._setup_flask_security()
        self._setup_bootstrap()
        self._setup_babel()
        self._setup_jinja()
        self._setup_permissions()
        self._setup_filters()
        self._register_blueprints()

        from sparkmeter.misc.jsonutils import JsonEncoder
        self.json_encoder = JsonEncoder
        self.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

    def _harden_session_cookie(self):
        """Mark the session cookie Secure when the deployment serves HTTPS.

        ``SESSION_COOKIE_HTTPONLY`` and ``SESSION_COOKIE_SAMESITE`` are set
        statically in settings. ``Secure`` is enabled when it is explicitly
        configured -- HTTPS-terminating deployments (e.g. gateways behind a
        TLS-terminating nginx) set ``SM_SESSION_COOKIE_SECURE=true`` -- OR when
        the app itself serves HTTPS (``_should_use_https()``, e.g. Heroku). It
        stays False in dev and tests over plain HTTP. This is promote-only: an
        explicitly configured ``True`` is never downgraded.
        """
        self.config['SESSION_COOKIE_SECURE'] = (
            self.config.get('SESSION_COOKIE_SECURE', False) or self._should_use_https())

    def _provide_utility(self):
        from zope.component import getUtility, provideUtility
        from zope.interface.interfaces import ComponentLookupError

        from sparkmeter.interface import IApplication

        # Only provide an IApplication if there is no other one before,
        # We create a global one in testrunner.py and this allows us
        # To test this code that creates new SparkmeterApplication's without
        # messing with the other tests
        try:
            getUtility(IApplication)
        except ComponentLookupError:
            provideUtility(self, IApplication)

    def _load_domain_modules(self):
        """Load all domains so that we can use things like BaseDomain.__subclasses__() safely."""
        import sparkmeter.config.configdomain  # noqa
        import sparkmeter.dashboard.dashboarddomain  # noqa
        import sparkmeter.database.symmetricdsdomain  # noqa
        import sparkmeter.event.eventdomain  # noqa
        import sparkmeter.ground.grounddomain  # noqa
        import sparkmeter.meter.meterdomain  # noqa
        import sparkmeter.reading.readingdomain  # noqa
        import sparkmeter.salesaccount.salesaccountdomain  # noqa
        import sparkmeter.snapshot.snapshotdomain  # noqa
        import sparkmeter.system.systemdomain  # noqa
        import sparkmeter.tariff.tariffdomain  # noqa
        import sparkmeter.transaction.transactiondomain  # noqa
        import sparkmeter.user.userdomain  # noqa

    def _load_configuration(self):
        from sparkmeter.config.configdict import config
        config.load(self)
        self.config = config
        self.debug = config.get('DEBUG')
        self._require_production_secrets(config, self.mode)

    def _require_production_secrets(self, config, mode):
        """Fail fast in production when required secrets are unset.

        Only enforced when ``mode == MODE_PRODUCTION``. Of the other modes,
        only ``MODE_UNITTEST`` supplies its own secrets (via
        ``tests/settings.py``); ``MODE_MANAGE``, ``MODE_ALEMBIC`` and
        ``MODE_UNKNOWN`` rely on the ``SM_*`` env overrides and are simply not
        gated here.
        """
        if mode != self.MODE_PRODUCTION:
            return
        for key, env_var in REQUIRED_PRODUCTION_SECRETS:
            if not secret_configured(config, key):
                raise SystemExit(
                    '%s must be set in production; refusing to boot '
                    'without a configured %s.' % (env_var, key))

    def _setup_logging(self):
        from sparkmeter.misc.logutils import setup_logging
        setup_logging(level=self.config.get('LOG_LEVEL', logging.INFO))

    def _setup_bootstrap(self):
        from flask_bootstrap import Bootstrap
        bootstrap = Bootstrap()
        bootstrap.init_app(self)

    def _setup_babel(self):
        from flask.globals import request
        from flask_babel import Babel

        from sparkmeter.user.userutils import get_current_user

        def babel_localeselector():
            """Get the locale of the current user."""
            if self.mode == self.MODE_PRODUCTION:  # pragma: nocoverage
                user = get_current_user()
                if user is not None:
                    # if a user is logged in, use the locale from the user settings
                    if user.is_authenticated:
                        return user.locale
                    # otherwise try to guess the language from the user accept
                    # header the browser transmits.  We support de/fr/en in this
                    # example.  The best match wins.
                    return request.accept_languages.best_match(['fr', 'en'])
            return None

        babel = Babel()
        babel.init_app(self, locale_selector=babel_localeselector)

    def _setup_sentry(self):  # pragma: nocoverage
        from sparkmeter.sentry_proxy import _SENTRY_SDK, SentryProxy

        # Only enable sentry when it's enabled in the configuration
        if self.mode == self.MODE_UNITTEST or self.config.get('SENTRY_DSN') is None:
            self.sentry = SentryProxy()
            return

        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(
            dsn=self.config['SENTRY_DSN'],
            integrations=[FlaskIntegration(), FastApiIntegration()],
        )
        self.sentry = SentryProxy(_SENTRY_SDK)

    def _setup_sqlalchemy(self):
        if 'sqlalchemy' in self.extensions:
            return

        from sparkmeter.database.alchemy import sql
        sql.init_app(self)
        logger.info(" * Connected to %s" % (
            self.config['SQLALCHEMY_DATABASE_URI'], ))
        self.sql = sql

    def _demo_login_enabled(self):
        return self.config.get('ENABLE_DEMO_LOGIN', False)

    def _setup_flask_security(self):
        # This is called twice to be able to test database commands
        if 'security' in self.extensions:
            return
        from flask_security import Security

        from sparkmeter.user.userdomain import user_datastore

        # Setup Flask-Security
        security = Security()
        security.init_app(self, user_datastore)

        # there is a bug/feature in flask security where you cant actually use
        # security.login_context_processor instead we have to use
        # app.extensions['security'] so that the state is correctly referenced
        # https://github.com/mattupstate/flask-security/issues/211
        # https://github.com/mattupstate/flask-security/issues/141
        security_ctx = self.extensions['security']

        def set_users():
            """Inject the systems users into the security tempalates if using the demo system."""
            if self._demo_login_enabled():
                from sparkmeter.user.userdomain import User

                # FIXME: Only include active users
                return {'demo_users': User.get_login_users()}
            return {}
        security_ctx.login_context_processor(set_users)

    def _cache_buster(self, filename):
        import hashlib

        # If CDN_URL is configured, use it instead of serving locally
        cdn_url = self.config.get('CDN_URL')
        if cdn_url:
            from sparkmeter import __version__

            # Assume CDN has files with same structure, add cache
            # busting via file modification time or version
            # TODO: include file hashes in the file names and for each
            # TC version record which hashes go with the release.
            cdn_url = cdn_url.rstrip('/')
            return '%s/%s/static/%s' % (cdn_url,
                                        __version__.version,
                                        filename)

        # Fall back to local serving with cache busting
        full = os.path.join(self.static_folder, filename)
        if (self.developer_mode and not os.path.exists(full)):  # pragma: nocoverage
            relativename = full[len(self.static_folder) + 1:]
            import subprocess
            subprocess.check_call(['make', 'static/' + relativename])

        with open(full, 'rb') as f:
            file_hash = hashlib.sha1(f.read()).hexdigest()
        filename = '/static/%s?%s' % (full[len(self.static_folder) + 1:], file_hash)
        return filename

    def _setup_jinja(self):
        # FIXME: Write a custom Loader which does
        # {% include "meter/meter-list.html" %} ->
        # sparkmeter/meter/templates/meter-list.html
        from jinja2 import ChoiceLoader, FileSystemLoader
        from markupsafe import Markup

        from sparkmeter import __version__
        base = os.path.dirname(__file__)
        my_loader = ChoiceLoader([
            FileSystemLoader([base + '/dashboard/templates',
                              base + '/config/templates',
                              base + '/event/templates',
                              base + '/history/templates',
                              base + '/meter/templates',
                              base + '/ground/templates',
                              base + '/reading/templates',
                              base + '/salesaccount/templates',
                              base + '/tariff/templates',
                              base + '/transaction/templates',
                              base + '/user/templates',
                              base + '/homepage/templates',
                              base + '/templates']),
        ])
        self.jinja_loader = my_loader
        self.jinja_env.add_extension('jinja2.ext.do')
        self.jinja_env.trim_blocks = True
        self.jinja_env.lstrip_blocks = True
        self.jinja_env.globals.update(dict(
            APPLICATION_CSS=self._cache_buster('stylesheets/application.css'),
            APPLICATION_JS=self._cache_buster('javascripts/application.js'),
            VENDOR_JS=self._cache_buster('javascripts/vendor.js'),
            APP_VERSION=__version__.version,
            GIT_VERSION=__version__.git_version,
            Markup=Markup,
        ))

    def _setup_permissions(self):
        from sparkmeter.web.permission import register_functions
        register_functions(self)

    def _setup_filters(self):
        with self.app_context():
            from sparkmeter.web.filters import register_filters
            register_filters(self)

    def _app_error_handler(self, exc):
        """Transform 404 errors into a prettier error pages."""
        import http.client

        from flask import render_template, request

        from sparkmeter.misc.jsonutils import jsonify
        if request.path.startswith('/api/'):
            r = jsonify(dict(error='no such api', status='failure'))
            r.status_code = http.client.NOT_FOUND
        else:
            r = render_template('404.html'), http.client.NOT_FOUND
        return r

    def _app_readonly_handler(self, exc):
        """Transform 503 readonly errors into a prettier error pages."""
        # This is using an error handler so that later we can raise this
        # error more granularly if we want to enable some functionality in RO mode.
        from flask import make_response, render_template, request

        from sparkmeter.misc.jsonutils import jsonify
        error_info = {
            'error': exc.description,
            'status': 'failure',
        }
        if request.path.startswith('/api/'):
            r = jsonify(error_info)
        else:
            r = render_template('503.html', **error_info)
        return make_response(r, exc.code)

    def _register_blueprints(self):
        """Register the blueprints for the application."""
        import http.client

        from sparkmeter.exceptions import ReadOnlyError

        with self.app_context():
            self.errorhandler(http.client.NOT_FOUND)(self._app_error_handler)
            self.register_error_handler(ReadOnlyError, self._app_readonly_handler)

            from sparkmeter.event.alertviews import alert
            self.register_blueprint(alert)

            from sparkmeter.event.eventviews import event
            self.register_blueprint(event)

            from sparkmeter.api.apiviews0 import register_api_blueprint
            register_api_blueprint(self)

            from sparkmeter.config.configviews import config
            self.register_blueprint(config)

            from sparkmeter.dashboard.dashboardview import dashboard
            self.register_blueprint(dashboard)

            from sparkmeter.meter.meterview import meter
            self.register_blueprint(meter)

            from sparkmeter.ground.groundview import ground
            self.register_blueprint(ground)

            from sparkmeter.reading.readingview import reading
            self.register_blueprint(reading)

            from sparkmeter.tariff.tariffview import tariff
            self.register_blueprint(tariff)

            from sparkmeter.salesaccount.salesaccountviews import sales_account
            self.register_blueprint(sales_account)

            from sparkmeter.transaction.transactionview import transaction
            self.register_blueprint(transaction)

            from sparkmeter.user.userview import user
            self.register_blueprint(user)

            from sparkmeter.web.views import web
            self.register_blueprint(web)

            from sparkmeter.homepage.homepageview import homepage
            self.register_blueprint(homepage)

            if self.config.get('S3_HISTORY_BUCKET') and self.config.get('S3_SITE'):
                from sparkmeter.history.historyview import historyview
                self.register_blueprint(historyview)

            if self.config.get('MEMORY_DEBUG', False):
                from sparkmeter.debug_memory import debug_memory
                self.register_blueprint(debug_memory)

        # Enable http->https direct for Heroku
        if self._should_use_https():  # pragma: nocoverage
            self.before_request(self._add_ssl_headers_and_redirect_http)
            self.after_request(self._add_htsh_header)

        # setup the readonly mode check
        self.before_request(self._check_readonly_mode)

        self.after_request(self._gzip_maybe_compress_response)

    def _check_readonly_mode(self):
        if self.readonly_mode:
            from sparkmeter.exceptions import ReadOnlyError
            raise ReadOnlyError()

    @property
    def readonly_mode(self):
        """Check to see if the app is in readonly mode."""
        # for now just check to see if the config is defined as RO, later this
        # will probably check a few sources to determine the right state.
        return self.config.get('READONLY', False)

    def _add_ssl_headers_and_redirect_http(self):  # pragma nocoverage
        import http.client

        from flask.globals import request
        from werkzeug.utils import redirect

        if request.is_secure:
            return

        if request.headers.get('X-Forwarded-Proto', 'http') == 'https':
            return

        if request.url.startswith('http://'):
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=http.client.MOVED_PERMANENTLY)

    def _add_htsh_header(self, response):  # pragma nocoverage
        from flask.globals import request
        if request.is_secure:
            # Number of seconds per day; 365 * 24 * 3600 = 31536000
            response.headers.setdefault('Strict-Transport-Security',
                                        'max-age={0}'.format(31536000))
        return response

    def _should_use_https(self):
        if self.debug:  # pragma: nocoverage
            return False

        if self.mode == self.MODE_UNITTEST:
            return False

        # FIXME: Enable this for gateways once we figured out the certificate
        if not self.config.get('HEROKU', False):  # pragma: nocoverage
            return False

        return self.config.get('USE_HTTPS', True)  # pragma: nocoverage

    def _gzip_can_compress(self, response):
        # We can only compress pages with successful status codes
        if response.status_code < 200 or response.status_code >= 300:
            return False

        # Response should be returned unmodified
        if response.direct_passthrough:
            return False

        # Do not compress small requests
        if len(response.data) < _GZIP_MIN_SIZE:
            return False

        # We can only compress to user agents that supports compression and
        # we will not compress already compressed responses
        from flask.globals import request
        accept_encoding = request.headers.get('Accept-Encoding', '')
        if ('gzip' not in accept_encoding.lower()
           or 'Content-Encoding' in response.headers):
            return False

        # Only compress mimetypes that aren't already compressed like
        # images and fonts
        if response.mimetype not in _GZIP_MIMETYPES:
            return False

        return True

    def _gzip_compress_response_data(self, response):
        gzip_buffer = io.BytesIO()
        with gzip.GzipFile(mode='wb',
                           compresslevel=_GZIP_LEVEL,
                           fileobj=gzip_buffer) as f:
            f.write(response.get_data())
        response.set_data(gzip_buffer.getvalue())
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = response.content_length

    def _gzip_maybe_compress_response(self, response):
        if self._gzip_can_compress(response):
            self._gzip_compress_response_data(response)

        return response

    def _setup_unittest(self):
        logger.info('Setting up unittests')
        from sparkmeter.web.unittestutils import TestFlaskClient, TestResponse
        self.response_class = TestResponse
        self.test_client_class = TestFlaskClient

        # Use a session interface that ignores cookie max_age.
        # This prevents @freeze_time from invalidating session cookies
        # (cookies signed at real time appear "from the future" when
        # time is frozen to the past, and itsdangerous rejects them).
        from flask.sessions import SecureCookieSessionInterface

        class TestSessionInterface(SecureCookieSessionInterface):
            def open_session(self, app, request):
                s = self.get_signing_serializer(app)
                if s is None:
                    return None
                val = request.cookies.get(self.get_cookie_name(app))
                if not val:
                    return self.session_class()
                try:
                    data = s.loads(val)
                    return self.session_class(data)
                except Exception:
                    return self.session_class()
        self.session_interface = TestSessionInterface()

        # Push an app context (not request context) for test setup
        ctx = self.app_context()
        ctx.push()
        # Close the internal SQLAlchemy transaction, we will replace it with our own
        from sparkmeter.database.alchemy import sql
        sql.session.remove()
