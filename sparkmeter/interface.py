# -*- coding: utf-8 -*-
# Copyright © 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Sparkmeter Interfaces."""

from zope.interface import Interface


class IApplication(Interface):

    """Global application singleton."""


class ICurrentUser(Interface):

    """Currently logged in user."""
