# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Custom SQLAlchemy columns used in Sparkmeter."""

from builtins import str

from sqlalchemy import VARCHAR
from sqlalchemy.ext.mutable import MutableDict

# SQLAlchemy 2.x removed processors module, implementing inline


def boolean_to_int(value):
    """Convert boolean to int."""
    return 1 if value else 0


def int_to_boolean(value):
    """Convert int to boolean."""
    return bool(value)


from sqlalchemy.sql.type_api import UserDefinedType  # noqa: E402

from sparkmeter.misc.jsonutils import json_dumps, json_loads  # noqa: E402


class JSONString(UserDefinedType):
    """A JSON object which is stored as a string and (de)serialized when used."""

    def compare_against_backend(self, dialect, conn_type):  # pragma: nocoverage
        """Check if the database column is the same as this.

        This is currently only used when generate a new database revision.
        """
        return isinstance(conn_type, VARCHAR)

    def get_col_spec(self):
        """How this column is stored in the database."""
        return "VARCHAR"

    def bind_processor(self, dialect):
        """Serialize to database."""
        return lambda value: json_dumps(value)

    def result_processor(self, dialect, coltype):
        """Serialize from database."""
        return lambda value: json_loads(value)


class MutableJSONDict(JSONString):
    """A JSON object which mutable state is tracked."""


MutableDict.associate_with(MutableJSONDict)


class IntBoolean(UserDefinedType):
    """A Boolean that is stored as an SMALLINT in the database."""

    def get_col_spec(self):
        """How this column is stored in the database."""
        return "SMALLINT"

    def literal_processor(self, dialect):
        """Interpret a literal without using a bind."""

        def wrapper(value):
            r = str(1 if value else 0)
            return r

        return wrapper

    def bind_processor(self, dialect):
        """Serialize to database."""

        def wrapper(value):
            r = boolean_to_int(value)
            return r

        return wrapper

    def result_processor(self, dialect, coltype):
        """Serialize from database."""

        def wrapper(value):
            if value == -1:
                return None
            r = int_to_boolean(value)
            return r

        return wrapper
