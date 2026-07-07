# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
import sys
from unittest import mock

from testfixtures import log_capture

from sparkmeter.tests.base import WebViewTestCaseBase


class UWSGITest(WebViewTestCaseBase):
    @log_capture('sparkmeter.web.uwsgiutils')
    @mock.patch('time.sleep')
    def test_uwsgi_worker_lock(self, sleep, logger):
        sys.modules['uwsgi'] = uwsgi = mock.Mock()
        from sparkmeter.web.uwsgiutils import uwsgi_worker_lock

        uwsgi.is_locked.return_value = False
        uwsgi.reset_mock()
        with uwsgi_worker_lock(1) as value:
            assert value is True
        assert uwsgi.mock_calls == [
            mock.call.is_locked(1),
            mock.call.lock(1),
            mock.call.unlock(1),
        ]
        logger.check()

        uwsgi.is_locked.side_effect = [True, True, False]
        uwsgi.reset_mock()
        with uwsgi_worker_lock(1) as value:
            assert value is False
        assert uwsgi.mock_calls == [
            mock.call.is_locked(1),
            mock.call.is_locked(1),
            mock.call.is_locked(1),
        ]
        assert sleep.mock_calls == [
            mock.call(1),
        ]
        logger.check(
            ('sparkmeter.web.uwsgiutils',
             'INFO',
             'UWSGI Lock #1 found, waiting for it to be released'),
            ('sparkmeter.web.uwsgiutils',
             'INFO',
             'UWSGI Lock #1 released, starting up normally'),
        )
