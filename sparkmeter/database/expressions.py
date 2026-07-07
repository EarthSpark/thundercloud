# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Module containing custom SQLAlchemy DDL element expressions."""

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import ColumnElement


class JSONAgg(ColumnElement):

    """DDLElement wrapper for the function json_agg."""

    def __init__(self, items, order_by=None):
        """Create a new json_agg."""
        self.items = items
        self.order_by = order_by


@compiles(JSONAgg)
def compile_json_agg(element, compiler, **kw):
    """Compile json_agg into a SQL statement."""
    s = 'json_agg(row_to_json((SELECT r FROM (SELECT '
    s += ', '.join([compiler.process(item) for item in element.items])
    s += ') r) )'
    if element.order_by is not None:
        s += ' ORDER BY ' + ','.join([compiler.process(item) for item in element.order_by])
    s += ')'
    return s
