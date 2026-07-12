# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""SQLAlchemy custom types."""

from __future__ import absolute_import

import uuid

from sqlalchemy import types
from sqlalchemy.dialects import postgresql


class UUIDType(types.TypeDecorator):
    """
    UUID type.

    Stores a UUID in the database natively when it can and falls back to
    a BINARY(16) or a CHAR(32) when it can't.

    ::

        from sparkmeter.database.types import UUIDType
        import uuid

        class User(Base):
            __tablename__ = 'user'

            # Pass `binary=False` to fallback to CHAR instead of BINARY
            id = sa.Column(UUIDType(binary=False), primary_key=True)
    """

    impl = types.BINARY(16)
    python_type = uuid.UUID
    cache_ok = True

    def __init__(self, binary=True, native=True):
        """
        Create a new UUID type.

        :param binary: Whether to use a BINARY(16) or CHAR(32) fallback.
        :param native:
        """
        types.TypeDecorator.__init__(self)
        self.binary = binary
        self.native = native

    def load_dialect_impl(self, dialect):
        """Load dialect."""
        if dialect.name == "postgresql" and self.native:
            # Use the native UUID type.
            return dialect.type_descriptor(postgresql.UUID())
        else:
            # Fallback to either a BINARY or a CHAR.
            kind = self.impl if self.binary else types.CHAR(32)
            return dialect.type_descriptor(kind)

    def coercion_listener(self, target, value, oldvalue, initiator):  # pragma: nocoverage
        """Coercion listener."""
        if value and not isinstance(value, uuid.UUID):
            try:
                value = uuid.UUID(value)

            except (TypeError, ValueError):
                value = uuid.UUID(bytes=value)

        return value

    def process_bind_param(self, value, dialect):
        """Process bind param."""
        if value is None:
            return value

        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)

        if self.native and dialect.name == "postgresql":
            return str(value)

        return value.bytes if self.binary else value.hex  # pragma: nocoverage

    def process_result_value(self, value, dialect):
        """Process result value."""
        if value is None:
            return value

        # If value is already a UUID object, return it as-is
        if isinstance(value, uuid.UUID):
            return value

        if self.native and dialect.name == "postgresql":
            return uuid.UUID(value)

        return uuid.UUID(bytes=value) if self.binary else uuid.UUID(value)  # pragma: nocoverage


class Choice(object):
    """
    Choice.

    Used by Choice type.
    """

    def __init__(self, code, value):
        """Create a new choice."""
        self.code = code
        self.value = value

    def __eq__(self, other):
        """Comparision."""
        if isinstance(other, Choice):
            return self.code == other.code
        return other == self.code

    def __ne__(self, other):  # pragma: nocoverage
        """Negative comparision."""
        return not (self == other)

    def __str__(self):  # pragma: nocoverage
        """Serialize to a string."""
        return str(self.value)

    def __repr__(self):
        """String representation."""
        return "Choice(code={code}, value={value})".format(code=self.code, value=self.value)


class ChoiceType(types.TypeDecorator):
    """
    Choice type.

    ChoiceType offers way of having fixed set of choices for given column.
    Columns with ChoiceTypes are automatically coerced to Choice objects.

    ::


        class User(self.Base):
            TYPES = [
                (u'admin', u'Admin'),
                (u'regular-user', u'Regular user')
            ]

            __tablename__ = 'user'
            id = sa.Column(sa.Integer, primary_key=True)
            name = sa.Column(sa.Unicode(255))
            type = sa.Column(ChoiceType(TYPES))


        user = User(type=u'admin')
        user.type  # Choice(type='admin', value=u'Admin')



    ChoiceType is very useful when the rendered values change based on user's
    locale:

    ::

        from babel import lazy_gettext as _


        class User(self.Base):
            TYPES = [
                (u'admin', _(u'Admin')),
                (u'regular-user', _(u'Regular user'))
            ]

            __tablename__ = 'user'
            id = sa.Column(sa.Integer, primary_key=True)
            name = sa.Column(sa.Unicode(255))
            type = sa.Column(ChoiceType(TYPES))


        user = User(type=u'admin')
        user.type  # Choice(type='admin', value=u'Admin')

        print user.type  # u'Admin'
    """

    impl = types.Unicode(255)

    def __init__(self, choices, impl=None):
        """Create a new choice type."""
        types.TypeDecorator.__init__(self)
        if not choices:  # pragma: nocoverage
            raise Exception("ChoiceType needs list of choices defined.")
        self.choices = choices
        self.choices_dict = dict(choices)
        if impl:  # pragma: nocoverage
            self.impl = impl

    @property
    def python_type(self):  # pragma: nocoverage
        """Python type."""
        return self.impl.python_type

    def coercion_listener(self, target, value, oldvalue, initiator):  # pragma: nocoverage
        """Coercion listener."""
        if value is None:
            return value
        if isinstance(value, Choice):
            return value
        return Choice(value, self.choices_dict[value])

    def process_bind_param(self, value, dialect):
        """Process bind param."""
        if value and isinstance(value, Choice):
            return value.code
        return value

    def process_result_value(self, value, dialect):
        """Process result value."""
        if value:
            return Choice(value, self.choices_dict[value])
        return value  # pragma: nocoverage
