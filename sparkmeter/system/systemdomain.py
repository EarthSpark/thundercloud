# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""SystemVersion domain objects."""
import datetime
import logging
from functools import total_ordering

from packaging.version import parse as parse_version
from sqlalchemy import Column, DateTime, String

from sparkmeter.__version__ import version as current_version
from sparkmeter.config.configdict import config
from sparkmeter.database.alchemy import sql
from sparkmeter.database.sync import SYNC_CHANNEL_SYSTEM, syncchannel
from sparkmeter.misc.uuidutils import as_uuid
from sparkmeter.models import BaseDomain

logger = logging.getLogger(__name__)


@total_ordering
@syncchannel(SYNC_CHANNEL_SYSTEM)
class SystemVersion(BaseDomain):

    """Domain class for storing application versions.

    This contains the information about which versions of the application are
    installed. It tells you when it was installed and the version number.
    """

    __tablename__ = 'system_version'

    #: When this version was added to the system, in UTC
    timestamp = Column(DateTime, default=lambda: datetime.datetime.utcnow(), nullable=False)

    #: The version of the app
    version = Column(String, unique=True, nullable=False)

    #: Old versions of the app
    STATUS_OLD = 'old'

    #: The current version of the app
    STATUS_ACTIVE = 'active'

    #: New versions of the app
    STATUS_NEW = 'new'

    @classmethod
    def get_default_id(cls, context):
        """Get the default id for a SystemVersion object."""
        return as_uuid(context.current_parameters['version'])

    @property
    def status(self):
        """Get the status of this version (old, active, or new)"""
        this_parsed = self.parsed_version
        current_parsed = self.parse_version(current_version)
        if this_parsed < current_parsed:
            return self.STATUS_OLD
        elif this_parsed > current_parsed:
            return self.STATUS_NEW
        return self.STATUS_ACTIVE

    def __eq__(self, other):
        return self.parsed_version == other.parsed_version

    def __gt__(self, other):
        return self.parsed_version > other.parsed_version

    @property
    def parsed_version(self):
        """Get the parsed version number of this version using our static parse_version method."""
        # FIXME: make this a cached property
        return self.parse_version(self.version)

    @staticmethod
    def parse_version(version):
        """Parse a version number using packaging.version.parse."""
        # this is here to consolodate how versions are parsed to one location
        return parse_version(version)


@syncchannel(SYNC_CHANNEL_SYSTEM)
class SystemState(BaseDomain):

    """Domain class for storing system state changes.

    This contains the information about which versions of the application is active.
    It tells you where in the upgrade process the system is.
    """

    __tablename__ = 'system_state'

    #: When did this state change occur, in UTC
    timestamp = Column(DateTime, default=lambda: datetime.datetime.utcnow(), nullable=False)

    #: The action being taken causing an application state change
    action = Column(String, nullable=False)

    #: The system who's state is changing (ground vs cloud)
    system = Column(String, nullable=False)

    #: The state when the application is starting up and needs to check some parameters
    STATE_START = 'start'

    #: The state when the application is upgrading itself (alembic upgrade)
    STATE_UPGRADE = 'upgrade'

    #: The state when the application is running normally and has no upgrades available
    STATE_RUN = 'run'

    #: The state when the application has an upgrade available
    STATE_UPGRADABLE = 'upgradable'

    #: The state when the application is waiting for sync to complete before kicking off the upgrade
    STATE_PREPARE = 'prepare'

    #: The state when the application has completed sync and needs to terminate itself to begin the upgrade
    STATE_TERMINATE = 'terminate'

    _valid_states = [
        STATE_START,
        STATE_UPGRADE,
        STATE_RUN,
        STATE_UPGRADABLE,
        STATE_PREPARE,
        STATE_TERMINATE,
    ]

    #: The application state
    state = Column(String, nullable=False)

    #: The version of the app
    version = Column(String, nullable=False)

    @classmethod
    def get_version(cls, system=None):
        """Get the version of this system."""

        # if no system is provided, use the local system
        if not system:
            system = config.local_system

        q = cls.query.with_entities(cls.version)
        q = q.filter_by(state=cls.STATE_RUN)
        q = q.filter_by(system=system)
        q = q.order_by(cls.timestamp.desc())
        q = q.limit(1)
        return q.scalar()

    @classmethod
    def get_state(cls, system=None):
        """Get the state of this system."""

        # if no system is provided, use the local system
        if not system:
            system = config.local_system

        q = cls.query.with_entities(cls.state)
        q = q.filter_by(system=system)
        q = q.order_by(cls.timestamp.desc())
        q = q.limit(1)
        return q.scalar()

    @classmethod
    def set_state(cls, state, action, version=None):

        # make sure the new state is a valid state
        assert state in cls._valid_states

        if cls.get_state() == state:
            # Don't duplicate the current state
            return

        # create a new system state
        ss = SystemState()

        # set if this is the ground or cloud
        ss.system = config.local_system

        # message about why the system is changing states
        ss.action = action

        # set the new state
        ss.state = state

        # use the current version if no version was provided
        if version is None:
            version = cls.get_version()

        if version is None:
            raise ValueError("No version provided and unable to determine current version")

        # set the version
        ss.version = version

        sql.session.add(ss)

        return ss
