# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.

from unittest import mock

from sparkmeter.database.alchemy import format_sql_stack, get_app_name, sqlalchemy_query_tagger
from sparkmeter.tests.base import SparkMeterTestCaseBase


class AlchemyTest(SparkMeterTestCaseBase):
    def test_app_name(self):
        with mock.patch("os.getpid") as getpid:
            getpid.return_value = 12345
            assert get_app_name(["hypercorn"]) == "sm-hypercorn-12345"
            assert get_app_name(["gunicorn"]) == "sm-gunicorn-12345"
            assert get_app_name(["uwsgi"]) == "sm-uwsgi-12345"
            assert get_app_name(["main.py"]) == "sm-dev-12345"
            assert get_app_name(["asgi.py"]) == "sm-dev-12345"
            assert get_app_name(["sliff"]) == "sm-sliff-12345"

    def test_format_sql_stack(self):
        stack = [
            ("sparkmeter/filename.py", 13, "funcname", "this is an app line"),
            ("sparkmeter/filename.py", 42, "foo", "this is an app line"),
            ("venv/flask/app.py", 13, "werkzeug", "this is Flask handling a request"),
        ]
        formatted = format_sql_stack(stack)
        assert formatted == "filename.py:13:funcname->filename.py:42:foo"

    def test_sqlalchemy_query_tagger_with_request(self, app, config):
        config["QUERY_TAGGING_FORMAT"] = "app={app_name} endpoint={endpoint} stack={stack}"
        with app.test_request_context("/"):
            with mock.patch("traceback.extract_stack") as extract_stack:
                extract_stack.return_value = []
                query, params = sqlalchemy_query_tagger(None, None, "foo", None, None, None)
                # endpoint depends on whether '/' is mapped
                assert query.startswith("foo /* app=sparkmeter.app endpoint=")
                assert params is None

    def test_sqlalchemy_query_tagger_without_request(self, config):
        config["QUERY_TAGGING_FORMAT"] = "app={app_name} endpoint={endpoint} stack={stack}"
        with mock.patch("traceback.extract_stack") as extract_stack:
            extract_stack.return_value = []
            # Outside request context, endpoint should be None
            query, params = sqlalchemy_query_tagger(None, None, "foo", None, None, None)
            assert query == "foo /* app=sparkmeter.app endpoint=None stack= */"
            assert params is None

    def test_sqlalchemy_query_tagger_disabled(self, config):
        config["QUERY_TAGGING_FORMAT"] = None
        query, params = sqlalchemy_query_tagger(None, None, "foo", None, None, None)
        assert query == "foo"
        assert params is None
