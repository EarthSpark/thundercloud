# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Utilities for interacting with uWSGI."""

import contextlib
import logging
import time

import uwsgi

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def uwsgi_worker_lock(locknum):
    """
    Acquire a uWSGI worker lock.

    This prevents other workers from executing this block of code at the
    same time.

    :note: Remember that locks needs to be set in uwsgi.ini for these locks to work.

    :param locknum: number of the lock to fetch.
    :return: ``True`` if it's the first worker executing the code, ``False`` otherwise
    """
    if uwsgi.is_locked(locknum):
        logger.info("UWSGI Lock #{} found, waiting for it to be released".format(locknum))
        while uwsgi.is_locked(locknum):
            time.sleep(1)
        logger.info("UWSGI Lock #{} released, starting up normally".format(locknum))
        yield False
    else:
        uwsgi.lock(locknum)
        yield True
        uwsgi.unlock(locknum)
