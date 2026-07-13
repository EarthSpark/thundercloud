# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Base SQLAlchemy ORMObject."""

import collections

from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.session import Session

from sparkmeter.database.alchemy import sql
from sparkmeter.misc.pythonutils import classproperty

GetOneOrCreateResult = collections.namedtuple("result", ["created", "object"])


class ORMObject(sql.Model):
    """Mixin for some common sql model methods."""

    __abstract__ = True

    @property
    def session(self):
        """Fetch the current session of this object."""
        return Session.object_session(self)

    def save(self, session=None):
        """Helper for saving the sql objects the same way as mongo objects."""
        if session is None:
            session = sql.session

        session.add(self)
        session.commit()

    def reload(self, session):
        """Helper for reloading the sql objects the same way as mongo objects."""
        session.expire(self)
        session.refresh(self)

    @classproperty
    def table(cls):
        """Get the SQLAlchemy table associated with this class."""
        # FIXME: Use get_table_by_name, but requires an Abstract ORMObject or so.
        return cls.metadata.tables[cls.__tablename__]

    @classmethod
    def column_labels(cls, exclude):
        """Get the column name and translated labels."""
        exclude.append("id")
        include = [col.key for col in cls.table.columns]

        # FIXME: handle someref_id fields some how
        return [
            (field, getattr(cls, field).info.get("label", field)) for field in include if field not in exclude
        ]

    def __repr__(self):
        """Short and safe SQL object display name."""
        state = inspect(self)
        if state.has_identity:
            return "<%s id=%s>" % (self.__class__.__name__, state.identity[0])
        # use the python id instead if we can't get the sql object id
        return "<%s %s>" % (self.__class__.__name__, id(self))

    @classmethod
    def get_all(cls):
        """Get all objects."""
        return cls.query.all()

    @classmethod
    def get_by_id(cls, object_id):
        """Get the object by the given object_id.

        :rtype: Type[ORMObject]
        """
        return cls.query.get(object_id)

    @classmethod
    def get_one_or_create(cls, session=None, flush=False, **kwargs):
        """Fetch an object or create it if missing.

        This is similar to what exists in Django, but implemented on
        top of SQLAlchemy. Just pass in the keyword arguments and this
        function will first try to fetch the object and if it doesn't exist,
        it will create and add it to a session.

        This returns a tuple of (created, object).
        created is a bool of if the object found in the query, or created.

        :param session: The session to be used for creation
        :param flush: `True` if the returned object should be flushed from the session
        """
        if session is None:
            session = sql.session

        # modified from http://stackoverflow.com/posts/21146492/revisions
        created = False
        try:
            model = session.query(cls).filter_by(**kwargs).one()
        except NoResultFound:
            model = cls(**kwargs)
            try:
                session.add(model)
                created = True
            except IntegrityError:  # pragma: nocoverage
                session.rollback()
                model = session.query(cls).filter_by(**kwargs).one()
            if flush:
                session.flush()
        return GetOneOrCreateResult(created, model)
