# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Module for all model orm definitions for SQLAlchemy."""

import logging
import uuid
from contextlib import contextmanager

from sqlalchemy import func
from sqlalchemy.schema import Column

from sparkmeter.database.alchemy import sql
from sparkmeter.database.ormobject import ORMObject
from sparkmeter.database.sync import SYNC_DIRECTION_BOTH
from sparkmeter.database.tables import get_class_by_tablename
from sparkmeter.database.types import UUIDType

logger = logging.getLogger(__name__)


@contextmanager
def session_scope():
    """Provide a commit/rollback scope around a series of operations."""
    try:
        yield sql.session
        sql.session.commit()
    except Exception:
        sql.session.rollback()
        logger.exception("Rolling back an sql commit")
        raise


class BaseDomain(ORMObject):

    """Abstract domain class for all tables with a UUID column."""

    __abstract__ = True

    sync_direction = SYNC_DIRECTION_BOTH

    # Mapping tables needs a deterministic UUID so that it
    # is consistent across different databases, eg allowing
    # cloud and ground to create these mapping entries independently
    # of each other without ending up creating conflicts.
    def default_id(context):
        """Helper for fetching the default id in a table/class specific way."""
        table = context.prefetch_cols[0].table
        cls = get_class_by_tablename(table.name)
        return cls.get_default_id(context)

    id = Column(UUIDType(binary=False), default=default_id, primary_key=True,
                server_default=func.uuid_generate_v4())

    @classmethod
    def sync_init(cls, group):
        """Initialize sync configuration for the this table."""

    @classmethod
    def get_default_id(cls, context):
        """BaseDomain default uuid value."""
        return uuid.uuid4()

    @property
    def _data(self):
        """Get the stored data as a dict."""
        self.id
        return {
            i: j
            for i, j in list(self.__dict__.items())
            if i != '_sa_instance_state'
        }


class BaseView(BaseDomain):

    """Abstract domain class for a view."""

    __abstract__ = True
    __table_args__ = dict(
        info=dict(is_view=True),
    )
