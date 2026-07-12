# -*- coding: utf-8 -*-
# Copyright © 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""HTML related utilitites."""

from werkzeug.utils import escape


def build_link(url, label):
    """Construct a link, given an url and a label."""
    return '<a href="{url}">{label}</a>'.format(url=url, label=escape(label))
