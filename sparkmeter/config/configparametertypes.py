# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Configuration parameter types."""

import logging

from sparkmeter.misc.pythonutils import ClassInittable

logger = logging.getLogger(__name__)


class ParameterType(ClassInittable):
    """Abstract parameter type.

    Contains a type name and functions to convert to/from python
    and database.
    """

    type_name = ""
    types = {}
    python_type = None

    @classmethod
    def __class_init__(cls):
        """Initialize the class."""
        if cls.__name__ != "ParameterType":
            cls.types[cls.type_name] = cls

    def to_python(self, value):
        """
        Convert a database value to python.

        :param value: the database value to convert.
        :return: the converted python value
        """
        raise NotImplementedError(type(self).__name__)

    def from_python(self, value):
        """
        Convert a python value to database.

        :param value: the python value to convert.
        :return: the converted database value
        """
        raise NotImplementedError(type(self).__name__)


class Bool(ParameterType):
    """
    A boolean parameter.

    This is represented as true/false in the database and
    the True/False boolean values in Python.
    """

    type_name = "bool"
    python_type = bool

    def to_python(self, value):
        """
        Convert a database value to python.

        :param value: the database value to convert.
        :return: the converted python value
        """
        if value == "true":
            python_value = True
        elif value == "false":
            python_value = False
        else:
            msg = "Could not convert {!r} to a boolean value".format(value)
            logger.warning(msg)
            python_value = False
        return python_value

    def from_python(self, value):
        """
        Convert a python value to database.

        :param value: the python value to convert.
        :return: the converted database value
        """
        if value is True:
            return "true"
        elif value is False:
            return "false"
        else:
            msg = "boolean parameters must be True or False, not {!r}.".format(value)
            raise TypeError(msg)


class Float(ParameterType):
    """
    A float parameter.

    This is represented as float in the database and python.
    """

    type_name = "float"
    python_type = float

    def __init__(self, min_value=None, max_value=None):
        """
        Create a new float type with optional minimum and maximum values.

        :param min_value: minimum allowed value or None
        :param max_value: maximum allowed value or None
        """
        self.min_value = min_value
        self.max_value = max_value

    def to_python(self, value):
        """
        Convert a database value to python.

        :param value: the database value to convert.
        :return: the converted python value
        """
        try:
            python_value = float(value)
        except (ValueError, TypeError):
            logger.warning("Could not convert database value {!r} to a python float".format(value))
            python_value = 0.0
        return self._validate_value(python_value)

    def _validate_value(self, value):
        retval = float(value)
        if self.min_value is not None and value < self.min_value:
            retval = self.min_value
            msg = "value cannot be less than {}, defaulting to {}."
            logger.warning(msg.format(self.min_value, retval))
        if self.max_value is not None and value > self.max_value:
            retval = self.max_value
            msg = "value cannot be more than {}, defaulting to {}."
            logger.warning(msg.format(self.max_value, retval))
        return retval

    def from_python(self, value):
        """
        Convert a python value to database.

        :param value: the python value to convert.
        :return: the converted database value
        """
        if type(value) not in [float, int]:
            msg = "value must be a number, not {}."
            raise TypeError(msg.format(type(value).__name__))
        value = self._validate_value(value)
        return str(value)


class Percent(Float):
    """
    A percentage parameter.

    This is subtype of float with a minimum allowed value of 0 and
    a maxmimum allowed value of 100.
    """

    type_name = "percent"

    def __init__(self):
        """Create a new percent type."""
        super(Percent, self).__init__(min_value=0.0, max_value=100.0)


class Voltage(Float):
    """
    A voltage parameter.

    This is subtype of float with a minimum allowed value of 100 and
    a maxmimum allowed value of 240
    """

    type_name = "voltage"
    allowed = [110.0, 120.0, 220.0, 230.0, 240.0]

    def __init__(self):
        """Create a new voltage type."""
        super(Voltage, self).__init__(min_value=min(self.allowed), max_value=max(self.allowed))

    def _validate_value(self, value):
        retval = float(value)
        if retval not in self.allowed:
            raise TypeError("value must be one of: {}".format(", ".join(str(val) for val in self.allowed)))
        return retval


class String(ParameterType):
    """A string parameter."""

    type_name = "string"
    python_type = str

    def to_python(self, value):
        """Convert a database value to python."""
        if value is None:
            return ""
        return str(value)

    def from_python(self, value):
        """Convert a python value to database."""
        if value is None:
            return ""
        if not isinstance(value, str):
            msg = "string parameters must be strings, not {!r}."
            raise TypeError(msg.format(type(value).__name__))
        return value
