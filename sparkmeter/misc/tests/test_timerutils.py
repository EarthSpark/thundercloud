# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Unittests for timer utilities."""

import logging
from unittest import mock

import pytest
from testfixtures import LogCapture

from sparkmeter.misc.timerutils import timer


@pytest.fixture()
def logger():
    with LogCapture("timer", level=logging.DEBUG) as logger:
        yield logger


def test_timer(logger, mocker):
    func = mocker.Mock()
    time = mocker.patch("sparkmeter.misc.timerutils.time")
    time.time.side_effect = [
        3.010,
        3.567,
    ]
    with timer("message"):
        func()

    assert time.mock_calls == [
        mock.call.time(),
        mock.call.time(),
    ]
    assert func.mock_calls == [
        mock.call(),
    ]

    logger.check(("timer", "DEBUG", "message: took 557.00ms"))
