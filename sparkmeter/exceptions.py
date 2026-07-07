# -*- coding: utf-8 -*-
# Copyright © 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""SparkMeter exceptions Module."""
import http.client

from werkzeug.exceptions import ServiceUnavailable


class DuplicateReadingException(Exception):

    """Duplicate reading for a meter and heartbeat end time."""


class DatabaseLockTimeoutException(Exception):

    """Emitted when a database lock acquisition request times out."""


class InvalidCommandCode(Exception):

    """An Two-way SMS command code is invalid."""


class IncomingMessageReplyError(Exception):

    """An incoming SMS contained an error."""

    def __init__(self, reply, message_type):
        """Create a new exception based on reply and a config message type."""
        self.reply = reply
        self.message_type = message_type


class TransactionError(Exception):

    """A transaction error."""

    #: An action on a transaction without the necessary permissions
    ERROR_PERMISSION_DENIED = 'permission-denied'

    #: A transaction has already been reversed
    ERROR_ALREADY_REVERSED = 'already-reversed'

    #: A transaction has already been processed
    ERROR_ALREADY_PROCESSED = 'already-processed'

    #: A transaction has not been processed yet
    ERROR_NOT_PROCESSED = 'not-processed'

    #: A transaction has been cancelled
    ERROR_CANCELLED = 'cancelled'

    #: A transaction already exists with this external_id
    ERROR_DUPLICATED = 'duplicated'

    #: Not enough funds to place a transaction
    ERROR_NOT_ENOUGH_FUNDS = 'not-enough-funds'

    #: Wrong transaction type
    ERROR_WRONG_TYPE = 'wrong-type'

    def __init__(self, code, message):
        """Create a new Transaction error.

        :param code: the transaction code.
        :param message: an error message
        """
        super().__init__(message)
        self.code = code
        self.message = message

    def __str__(self):
        """Format this exception."""
        return str(self.message)


class MeterError(Exception):

    """A meter error."""

    #: Invalid serial format
    INVALID_SERIAL = 'invalid-serial'

    #: A meter with this serial already exists
    DUPLICATE_SERIAL = 'duplicate-serial'

    #: This meter is using an unknown model
    UNKNOWN_MODEL = 'unknown-model'

    def __init__(self, code, message):
        """Create a new Meter error.

        :param code: the meter code.
        :param message: an error message
        """
        super().__init__(message)
        self.code = code
        self.message = message

    def __str__(self):
        """Format this exception."""
        return str(self.message)


class APIError(Exception):

    """An error occurred during the API call."""

    def __init__(self, error, status_code=http.client.BAD_REQUEST, payload=None):
        """Create a new API Error.

        :param error: error message
        :param status_code: http status code, defaults to httplib.BAD_REQUEST
        :param payload: optionally, an error payload
        """
        Exception.__init__(self)
        self.error = error
        self.payload = payload
        self.status_code = status_code

    def to_dict(self):
        """Convert this exception state to a dictionary."""
        rv = dict(self.payload or ())
        rv['error'] = self.error
        rv['status'] = 'failure'
        return rv


class InvalidData(Exception):

    """An error raised by JSON to form deserialization."""


class ReadOnlyError(ServiceUnavailable):

    """A request can not be processed because the app is read-only."""

    description = "This application is temporarily read-only. Please try again later."
