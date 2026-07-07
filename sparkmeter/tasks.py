# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Periodic DB-processing jobs."""

import logging

from flask.globals import current_app

logger = logging.getLogger(__name__)


def process_events():
    """Process events from database and handle them accordingly.

    Most common actions:
    - Send SET_CONFIG message to meters in case of meter state changes
    - Create SMS alerts from events
    """
    from sparkmeter.event.eventdomain import Event
    from sparkmeter.models import session_scope
    with current_app.app_context(), session_scope() as session:
        for event in Event.get_unprocessed():
            # FIXME: Investigate splitting this into subtasks, need to do some profiling
            #        to figure out how much overhead it is
            event.process()
            session.add(event)
