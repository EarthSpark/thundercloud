# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Timing utilities."""
import contextlib
import logging
import time

logger = logging.getLogger('timer')


@contextlib.contextmanager
def timer(message):
    """Use this to measure how long time it takes to run some code.

    Usage:

       with timer('hello'):
          hello()

    """
    start = time.time()
    yield
    end = time.time()
    logger.debug('{}: took {:.2f}ms'.format(message, (end - start) * 1000.0))
