# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Utility functions for unittests."""
import codecs
import difflib
import os
import re
import sys
import urllib.parse
from builtins import str

import html5lib
import pytest
from flask import Response
from flask.helpers import request
from flask.testing import FlaskClient
from zope.component import getUtility

from sparkmeter.interface import IApplication
from sparkmeter.misc.jsonutils import json_dumps, json_loads
from sparkmeter.user.userutils import set_current_user

rootdir = os.path.join(os.path.dirname(__file__), '..', '..')


def validate_html(data, ignores=None):
    """Validate the html in the request's response."""
    if ignores is None:
        ignores = {}
    tree = html5lib.treebuilders.getTreeBuilder("etree")
    parser = html5lib.HTMLParser(tree=tree)

    # FIXME: Use our own redirect() instead of werkzeugs that can be validated
    data = data.replace('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">',
                        '<!DOCTYPE html>')
    parser.parse(data)
    lines = data.split('\n')
    if parser.errors:  # pragma: nocoverage
        err = []
        for pos, errorcode, vars in parser.errors:
            tagname = vars.get('name')
            if errorcode in ignores and tagname in ignores[errorcode]:
                continue

            line, col = pos
            error = html5lib.constants.E.get(errorcode, 'Unknown error: %r' % (errorcode,))
            err.append("%s: %s" % (lines[line - 1].strip(), error % vars))

        if err:
            raise Exception('\n'.join(err))


class ContentTester(object):

    """Helper for testing content compared to last output."""

    def __init__(self, frame, ext='page', variant=None):
        """
        Create a new content tester.

        :param frame: frame where we get the filename and module from
        :param ext: filename extension, defaults to page
        :param variant: variant, if not None will be appended to test
        """
        self.frame = sys._getframe(frame)
        self.ext = ext
        self.variant = variant
        self.components = []
        self.ignores = []
        self.regex_ignores = []

        self._add_caller_filename()
        self._add_caller_funcname()

    def _add_caller_filename(self):
        filename = os.path.basename(self.frame.f_code.co_filename)
        filename = filename.replace('.py', '')
        self.components.append(filename)

    def _add_caller_funcname(self):
        func_name = self.frame.f_code.co_name
        if 'self' in self.frame.f_locals:
            test_name = type(self.frame.f_locals['self']).__name__
            func_name = '{}.{}'.format(test_name, func_name)
        self.components.append(func_name)

    def add_ignores(self, ignores):
        """Add a new list of ignored items."""
        if ignores is not None:
            self.ignores.extend(ignores)

    def add_regex_ignores(self, ignores):
        """Add a new list of ignored regexes."""
        if ignores is not None:
            self.regex_ignores.extend(ignores)

    @property
    def expected_filename(self):
        """Get an expeceted test name."""
        fname = self.frame.f_globals['__file__']
        testdirname = os.path.basename(os.path.dirname(
            os.path.dirname(fname)))
        testdir = os.path.join(rootdir, 'test-data', testdirname)
        if not os.path.exists(testdir):  # pragma: nocoverage
            os.makedirs(testdir)
        return os.path.abspath(os.path.join(testdir, self.name))

    @property
    def name(self):
        """Create a page name."""
        name = '-'.join(self.components)
        name = name.replace('/', '-')
        if self.variant:
            name += '-' + self.variant
        name += '.' + self.ext

        # Windows do not like ? in the path
        name = name.replace('?', '-')
        name = name.replace('--', '-')
        name = name.strip('-')
        return name

    def verify(self, content):
        """Verify a file on disk."""
        content = content.lstrip()

        for ignore in self.ignores:
            if ignore.startswith('0000000'):
                continue
            content = content.replace(ignore, '%% FILTERED BY UNITTEST %%')
        content += '\n'

        for ignore in self.regex_ignores:
            content = re.sub(ignore, '%% FILTERED BY UNITTEST %%', content)

        expected_filename = self.expected_filename
        if not os.path.exists(expected_filename):  # pragma: nocoverage
            open(expected_filename, 'w', encoding='utf-8').write(content)
            return

        expected_content = open(expected_filename, encoding='utf-8').read()
        expected_content = expected_content.lstrip()
        self._diff_lines(
            expected_content.split('\n'),
            content.split('\n'),
            short=self.name,
            expected_filename=expected_filename,
            test_filename=self.name,
        )

    def _diff_lines(self, expected_lines, test_lines, expected_filename,
                    test_filename, short):  # pragma: nocoverage
        """Compare the lines of saved files."""
        lines = difflib.unified_diff(
            expected_lines,
            test_lines,
            expected_filename,
            test_filename)
        if not lines:
            return

        diff = False
        try:
            next(lines)
            diff = True
        except StopIteration:
            pass
        else:
            print('\nerror: %s:1:' % (expected_filename,))
            for line in lines:
                print('%s: %r' % (short, line))

        if diff:
            pytest.fail("Expected test content differ")


class PageTester(ContentTester):

    """Helper class for testing contents of Flask requests."""

    def _format_request_response_as_curl(self, request, response):
        """Format a flask request and response as a curl output.

        This is similar to running curl -v and is basically the request
        data prefixed by > and the response prefixed by <, eg:

        > GET / HTTP/1.1
        > Location: localhost
        > Header: Value

        < 200 Found
        < Content-Length: 25
        < Content-Type: application/json
        <
        < { status: "success", error: null }

        Main use case for this is saving test requests as a .page test
        :returns: the formatted response.
        :rtype: str
        """
        request_headers = "\n".join("> %s: %s" % i for i in list(sorted(request.headers.items())))
        response_headers = "\n".join("< %s: %s" % i for i in list(sorted(response.headers.items()))
                                     if i[0] not in ['Content-Length', 'ETag', 'Last-Modified'])

        if request.form:
            items = list(request.form.items())
            request_data = '> ' + urllib.parse.urlencode(items) + '\n'
        elif request.data:
            data = request.data
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            request_data = '> ' + data + '\n'
        else:
            request_data = ''

        url = request.path
        if request.query_string:
            url += '?' + request.query_string.decode('utf-8')

        content_type = response.headers.get('Content-Type')
        if content_type in ['image/vnd.microsoft.icon']:
            body = codecs.encode(response.data, 'base64')
        else:
            body = str(response.data, 'utf-8')

        data = u"""> {request.method} {url} {proto}
{request_headers}
>
{request_data}
< {proto} {response.status}
{response_headers}
<
{body}""".format(
            proto=request.environ['SERVER_PROTOCOL'],
            request=request,
            request_data=request_data,
            request_headers=request_headers,
            response=response,
            response_headers=response_headers,
            url=url,
            body=body,
        )
        return data

    def verify_response(self, response):
        """"Verify a response.

        This verifies that the headers and content of the response and its requests
        matches the content of a serialized pair on disk.
        :param response: the response to verify.
        """
        data = self._format_request_response_as_curl(request, response)

        # Expires will contain a date when the request expires, just replace this
        # with a static string, since we don't care in the page tests.
        data = re.sub(r'(Expires=)([\w ,:\-]+)', '\\1%% EXPIRES %%', data)

        # Replace auth & session cookies and tokens
        data = re.sub(r'(remember_token=)([\w\.\-_|]+)', '\\1%% AUTH TOKEN %%', data)
        data = re.sub(r'(session=)([\w\.\-_]+)', '\\1%% SESSION %%', data)
        data = re.sub(r'(Authentication-Token:\s)([\w\.\-_]+)', '\\1%% API AUTH TOKEN %%', data)
        # Replace auth tokens in JSON bodies (itsdangerous signed tokens change per-request)
        data = re.sub(r'("token":\s*")(\.[\w\.\-_]+)"', '\\1%% AUTH TOKEN %%"', data)
        # Replace Set-Cookie headers (session cookie values change between runs)
        data = re.sub(r'(Set-Cookie:\s)(.+)', '\\1%% COOKIE %%', data)
        app = getUtility(IApplication)
        for env in ['APPLICATION_CSS', 'VENDOR_JS', 'APPLICATION_JS',
                    'APP_VERSION', 'GIT_VERSION']:
            data = data.replace(app.jinja_env.globals[env],
                                '%% {env} %%'.format(env=env))
        self.verify(data)
        if response.headers['Content-Type'] == 'text/html':
            validate_html(response.text)


class TestResponse(Response):

    """Custom Flask Response used for testing."""

    @property
    def text(self):
        """Response body as decoded text."""
        return super().data.decode('utf-8')

    def json(self):
        """JSON as dict."""
        return json_loads(self.text)


class TestFlaskClient(FlaskClient):

    """Custom FlaskClient for testing."""

    def __init__(self, *args, **kwargs):
        """Create a new testing client."""
        super(TestFlaskClient, self).__init__(*args, **kwargs)
        self.environ_base = {'HTTP_USER_AGENT': 'Unittest/1.0'}

    def post(self, path, data=None, json=None, headers=None, follow_redirects=False, query_string=None):
        """Issue a POST request to the server.

        :param path:
        :param data:
        :param json:
        :param headers:
        """
        if headers is None:
            headers = {}
        if data is not None:
            headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
        if json is not None:
            assert data is None
            data = json_dumps(json)
            headers.setdefault('Content-Type', 'application/json')
        return super(TestFlaskClient, self).post(
            path=path,
            data=data,
            headers=headers,
            follow_redirects=follow_redirects,
            query_string=query_string)

    def put(self, path, data=None, json=None, headers=None):
        """Issue a PUT request to the server.

        :param path:
        :param data:
        :param json:
        :param headers:
        """
        if headers is None:
            headers = {}
        if data is not None:
            headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
        if json is not None:
            assert data is None
            data = json_dumps(json)
            headers.setdefault('Content-Type', 'application/json')
        return super(TestFlaskClient, self).put(path=path,
                                                data=data,
                                                headers=headers)

    def patch(self, path, data=None, json=None, headers=None):
        """Issue a PATCH request to the server.

        :param path:
        :param data:
        :param json:
        :param headers:
        """
        if headers is None:
            headers = {}
        if data is not None:
            headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
        if json is not None:
            assert data is None
            data = json_dumps(json)
            headers.setdefault('Content-Type', 'application/json')
        return super(TestFlaskClient, self).patch(path=path,
                                                  data=data,
                                                  headers=headers)

    def login_as(self, user):
        """Login as a user in the client session."""
        if self._cookies is not None:
            self._cookies.clear()
        with self.session_transaction() as sess:
            sess['_user_id'] = user.get_id()
            sess['_fresh'] = True
            sess['_remember'] = 'set'
        # Update Flask-Login's cached user on g to prevent DetachedInstanceError
        from flask import g
        if hasattr(g, '_login_user'):
            g._login_user = user
        set_current_user(user)

    def logout(self):
        """Logout from the client session."""
        with self.session_transaction() as sess:
            sess.pop('_user_id', None)
            sess.pop('_fresh', None)
            sess.pop('_remember', None)
        set_current_user(None)
