# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Configuration parameter domain objects."""

import datetime
import logging

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

import sparkmeter.config.configparameter as configparameter
from sparkmeter.config.configparametertypes import ParameterType
from sparkmeter.database.sync import SYNC_CHANNEL_CONFIG, SYNC_GROUP_CLOUD, syncchannel
from sparkmeter.event.eventdomain import Event
from sparkmeter.misc.uuidutils import as_uuid
from sparkmeter.models import BaseDomain
from sparkmeter.user.userutils import get_current_user

logger = logging.getLogger(__name__)


@syncchannel(SYNC_CHANNEL_CONFIG)
class ConfigParameter(BaseDomain):
    """Domain class for storing a configuration parameter.

    This contains the information about a specific parameter which
    has a name, value, type, ground/user reference and a timestmap.
    """

    __tablename__ = "config_parameter"

    #: Name of the config parameter, for example: negative-balance-type
    name = Column(String, nullable=False)

    #: Raw/Database value of the config parameter, serialization depends on
    #: the ParameterType subclass. Use the .value property to read/write.
    raw_value = Column(String, nullable=True, name="value")

    #: Type of config parameter, this is mapped to a ParameterType
    value_type = Column(String, nullable=False)

    #: Ground which this parameter applies to
    ground_id = Column(ForeignKey("ground.id"), nullable=True)

    #: User which has most recently updated the parameter
    updated_by_id = Column(ForeignKey("user.id"), nullable=True)

    #: Last the the config parameter was modified, in UTC
    last_modified = Column(DateTime, default=lambda: datetime.datetime.utcnow(), nullable=False)

    #: Reference to the ground, if set
    ground = relationship("Ground")

    #: Reference to the user that updated the parameter
    updated_by = relationship("User")

    #: Method API: Configuration page

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_CLOUD)

    @classmethod
    def get_default_id(cls, context):
        """Get the default id for a ConfigParameter object."""
        return as_uuid(context.current_parameters["name"])

    @classmethod
    def get_by_name(cls, name):
        """
        Get a configuration parameter.

        :param name: name of the parameter to fetch
        :return:
        """
        return cls.query.filter_by(name=name).scalar()

    @classmethod
    def create_with_default(cls, param_attr):
        # type: (ParameterAttribute) -> ConfigParameter
        """
        Create parameter with default value.

        Create a new parameter with default values based on a parameter
        attribute.

        :param attr: the parameter attribute
        :return: the newly created configuration parameter.
        """
        self = cls(
            name=param_attr.name,
            raw_value=param_attr.get_default(),
            value_type=param_attr.param_type.type_name,
        )
        return self

    @classmethod
    def add_defaults(cls, session):
        # type: (Session) -> session
        """
        Add defaults for missing parameters.

        :param session: a database session
        """
        logger.info("Creating default parameters")
        config_params = list(p.name for p in session.query(cls).all())
        for param_attr in sorted(configparameter.ParameterObject.attributes):
            if param_attr.name not in config_params:
                param = ConfigParameter.create_with_default(param_attr)
                session.add(param)

    @property
    def parameter_type(self):
        # type: () -> ParameterType
        """Get the ParameterType for this parameter.

        :returns: a parameter type.
        """
        return ParameterType.types.get(self.value_type)()

    @hybrid_property
    def value(self):
        """Value getter."""
        return self.parameter_type.to_python(self.raw_value)

    @value.setter
    def value(self, value):
        """Value setter."""
        new_value = self.parameter_type.from_python(value)
        if new_value == self.raw_value:
            return

        self.raw_value = new_value
        self.last_modified = datetime.datetime.utcnow()
        self.updated_by = get_current_user()

        event = Event.create(Event.TYPE_CONFIG_PARAMETER_CHANGED, obj=self)
        self.session.add(event)
