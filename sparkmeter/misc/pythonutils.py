# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Misc. Python utilities."""

from builtins import object


class classproperty(object):
    """A property for class attributes."""

    def __init__(self, func):
        """Create a new class property."""
        self.func = func

    def __get__(self, obj, owner):
        """Property class descriptor."""
        return self.func(owner)


class ClassInitMeta(type):
    """Metaclass that calls __class_init__ after class creation."""

    def __init__(cls, name, bases, namespace):
        # type: (ClassInittable, str, Tuple[str], Dict[str, Any]) -> None
        type.__init__(cls, name, bases, namespace)
        cls.__class_init__()


class ClassInittable(object, metaclass=ClassInitMeta):
    """Class with a __class_init__ method."""

    @classmethod
    def __class_init__(cls):
        """Override this in a subclass."""
        # type: () -> None


class Unset(object):
    """Used as a singleton to indicate unset value.

    This is distinct for None which is used to indicate an
    empty value.
    """

    def __repr__(self):
        # type: () -> str
        """ "Textual representation of unset."""
        return "unset"


unset = Unset()
