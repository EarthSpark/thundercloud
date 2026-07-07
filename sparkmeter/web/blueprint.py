# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Blueprint for sparkmeter views."""
import http.client

from flask.blueprints import Blueprint
from flask.globals import current_app, request
from flask_security import current_user
from flask_security.utils import login_user
from werkzeug.exceptions import abort

from sparkmeter.config.configdict import config
from sparkmeter.exceptions import APIError
from sparkmeter.user.userutils import set_current_user


class APIBlueprint(Blueprint):

    """API specific blueprint with token authentication."""

    def __init__(self, import_name, version):
        """Create a new API blueprint.

        :param import_name, set this to __name__
        :param version: version of the api
        """
        name = 'apiv%d' % (version, )
        url_prefix = '/api/v%d' % (version, )
        super(APIBlueprint, self).__init__(name, import_name, url_prefix=url_prefix)
        self.before_request(self._before_request)
        self.after_request(self._after_request)

    def _before_request(self):
        # Validate the auth token and set current_user
        security = current_app.extensions['security']
        user = security.login_manager.request_callback(request)
        if user is None or not user.is_authenticated:
            raise APIError("unauthorized", status_code=http.client.UNAUTHORIZED)

        login_user(user)
        set_current_user(user)

    def _after_request(self, response):
        # Disable caching completely.
        # - This will ensure that each request is not cached by a client or proxy,
        #   which should be fine as long as the API is not being requested
        #   many times per second.
        # - It allows us to safely modify content on all http requests
        # Reference: http://stackoverflow.com/q/49547/14337

        # For HTTP 1.1 clients and proxies
        #  - no-store: do not store the request
        #  - no-cache: revalidate every time
        #  - must-revalidate: must revalidate on subsequent requests
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'

        # For HTTP/1.0 clients
        response.headers['Pragma'] = 'no-cache'

        # For HTTP 1.0 proxies
        response.headers['Expires'] = '0'
        return response


class AuthBlueprint(Blueprint):

    """Blueprint that does user authentication."""

    def __init__(self, name, import_name):
        """See Blueprint.__init__."""
        self.local_only_enpoints = []
        super(AuthBlueprint, self).__init__(name, import_name)
        self.before_request(self.lookup_user)

    def local_only(self, fn):
        """Decorator to disable heroku access."""
        endpoint = ".".join([self.name, fn.__name__])
        self.local_only_enpoints.append(endpoint)
        return fn

    def lookup_user(self):  # pragma nocover
        """Enforce user authentication."""
        # disable authentication when testing
        if config.get('LOGIN_DISABLED', False):
            return

        insecure_views = ['web.favicon']

        if config.get('ENABLE_DEMO_LOGIN', False):
            insecure_views.append('web.demo_login')

        if request.endpoint not in insecure_views:
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()

        if request.endpoint in self.local_only_enpoints:
            return abort(http.client.NOT_FOUND)

        if current_user.is_authenticated:
            user = current_user._get_current_object()
            set_current_user(user)
