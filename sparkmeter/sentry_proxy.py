# -*- coding: utf-8 -*-
# Copyright © 2019 SparkMeter, Inc.
# All Rights Reserved.
"""Sentry proxying logic."""

import logging

logger = logging.getLogger('sparkmeter.sentry')

# Sentinel signalling "use sentry_sdk", set by app._setup_sentry. Kept as a
# module-level flag rather than imported eagerly so test environments without
# sentry_sdk installed still load this module.
_SENTRY_SDK = object()


class SentryProxy(object):

    """A proxy for sentry (to allow for no-op cases).

    Public API: `captureException(message=..., tags={...})` and
    `captureMessage(message=..., tags={...})`. Both accept an optional
    `message` string and `tags` dict.

    Two modes, selected by what is passed to ``__init__``:
    - ``_SENTRY_SDK`` sentinel: forwards to ``sentry_sdk``, translating
      ``tags`` to scope tags and ``message`` to a scope extra (for
      captureException) or to the message body (for captureMessage).
    - default (no client): every call is a no-op that logs to
      ``sparkmeter.sentry``. The unit tests rely on those log records.
    """

    def __init__(self, client=None):
        """Delegate messages to Sentry or the application log based on app context."""
        self._client = client

    def captureException(self, *args, **kwargs):
        """Capture an exception."""
        if self._client is _SENTRY_SDK:
            self._capture_exception_sdk(*args, **kwargs)
        else:
            logger.exception('sentry.captureException: %s, %s', str(args), str(kwargs))

    def captureMessage(self, *args, **kwargs):
        """Capture a message."""
        if self._client is _SENTRY_SDK:
            self._capture_message_sdk(*args, **kwargs)
        else:
            logger.info('sentry.captureMessage: %s, %s', str(args), str(kwargs))

    def _capture_exception_sdk(self, *args, **kwargs):
        """Forward to ``sentry_sdk.capture_exception``.

        Reads ``message=`` and ``tags=`` from kwargs. ``tags`` are set on
        the active scope; ``message`` is attached as a scope extra so it
        appears alongside the exception in the issue view.
        """
        import sentry_sdk
        message = kwargs.pop('message', None)
        tags = kwargs.pop('tags', None) or {}
        with sentry_sdk.push_scope() as scope:
            for k, v in tags.items():
                scope.set_tag(k, v)
            if message is not None:
                scope.set_extra('message', message)
            sentry_sdk.capture_exception()

    def _capture_message_sdk(self, *args, **kwargs):
        """Forward to ``sentry_sdk.capture_message``.

        Accepts the message either positionally (first arg) or as a
        ``message=`` kwarg. ``tags=`` are applied to the active scope.
        """
        import sentry_sdk
        message = kwargs.pop('message', None)
        if message is None and args:
            message = args[0]
        tags = kwargs.pop('tags', None) or {}
        with sentry_sdk.push_scope() as scope:
            for k, v in tags.items():
                scope.set_tag(k, v)
            sentry_sdk.capture_message(message or '')
