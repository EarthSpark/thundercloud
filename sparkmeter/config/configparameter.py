# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Configuration parameter."""

from sparkmeter.config.configdict import config
from sparkmeter.config.configparametertypes import Bool, Percent, String, Voltage
from sparkmeter.database.alchemy import sql
from sparkmeter.misc.pythonutils import ClassInittable, unset


class ParameterAttribute(object):
    """
    Parameter attribute.

    This represents a single configuration parameter, eg a row in the
    config_parameter table. It is responsible for delegating de/serialization
    requests to the corresponding parameter type class.
    """

    #: Class attribute that is used to keep the attributes sorted in
    #: the order they are defined in ParameterObject.
    cls_order = 0

    def __init__(self, param_type, default=unset, label=None, tooltip=None):
        # type: (Type[ParameterType], Any) -> None
        """
        Create a new parameter attribute.

        :param param_type: a ParameterType for this attribute
        :param default: default value
        :param label: label
        :param tooltip: tooltip
        """
        self.param_type = param_type()
        self.default = default
        self.attribute = None
        self.label = label
        self.tooltip = tooltip

        self.order = ParameterAttribute.cls_order
        ParameterAttribute.cls_order += 1

    @property
    def name(self):
        # type: () -> str
        """
        Get the name of the parameter.

        This is the same as the attribute but in lower case and
        using dashes instead of underscores.
        """
        return self.attribute.lower().replace("_", "-")

    @property
    def parameter(self):
        # type: () -> ConfigParameter
        """
        Get the config parameter for this attribute.

        :returns: a configuration parameter.
        """
        from sparkmeter.config.configdomain import ConfigParameter

        parameter = ConfigParameter.get_by_name(self.name)
        return parameter

    def __get__(self, instance, owner=None):
        """
        Get a parameter attribute value.

        :param instance: instance or None if class access
        :param owner: owner
        :returns the value for the attribute
        """
        if instance is None:
            return self
        param = self.parameter
        if param is None:
            return self.get_default()
        return param.value

    def get_default(self):
        """Resolve this attribute's default value.

        ``default`` may be a plain value or a zero-argument callable. A
        callable is evaluated lazily here -- at seed/access time, after the
        application config has been loaded -- rather than being frozen when
        this module is first imported. This keeps a config-driven default
        such as ``NOMINAL_VOLTAGE`` deterministic regardless of import order.
        """
        return self.default() if callable(self.default) else self.default

    def __set__(self, instance, value):
        """Update a parameter attribute."""
        parameter = self.parameter
        parameter.value = value
        sql.session.add(parameter)

    def __lt__(self, other):
        """Compare a parameter attribute with another.

        Used for sorting.
        :param other: other attribute
        :returns: True if self.order < other.order
        """
        return self.order < other.order

    def __eq__(self, other):
        """Check equality based on order."""
        return self.order == other.order


class ParameterObject(ClassInittable):
    """
    ParameterObject.

    Containers a high-level api to read and write database configuration
    parameters.
    """

    #: Class variable, unsorted list of attributes
    attributes = []

    #: Negative balance, if True allow, if False, convert negative balance
    #: into debt automatically
    ALLOW_NEGATIVE_BALANCE = ParameterAttribute(
        Bool,
        default=True,
        label="Allow Negative Balance",
        tooltip="When convert to debt is selected, meters in Auto mode are "
        "not allowed to have a negative credits balance. Instead, "
        "charges that would result in negative balance are automatically "
        "converted to debt.",
    )

    #: How much of debt should be paid back in each billing cycle,
    #: is a percentage of the consumption cost.
    DEBT_PAYBACK_PERCENT = ParameterAttribute(
        Percent,
        default=0.0,
        label="On-bill debt repayment",
        tooltip="Percent of reading cost that will be automatically transferred "
        "to repay debt, every time a reading is received from the meter.",
    )

    #: Broadcast signal, If True, with load shedding enabled, send out broadcast
    #: signal to disable meters, if False, do not send out broadcast signal.
    SEND_BROADCAST_SIGNAL = ParameterAttribute(
        Bool,
        default=False,
        label="Send broadcast signal",
        tooltip="When in load shedding is enabled, send out a broadcast signal "
        "so that all meters are turned off as soon as possible.",
    )

    #: Send set-config packets for all active meters during startup
    #: when loading shedding is enabled.
    SEND_SET_CONFIG_AT_STARTUP = ParameterAttribute(
        Bool,
        default=True,
        label="Send set-config packets during startup",
        tooltip="This parameter drives whether all active meters would be updated with "
        "their desired state as soon as the application starts, in order to "
        "accelerate the propagation of load shedding.",
    )

    #: Voltage traveling through power meters. Used to calculate the power limit for meters, capping the
    #: tariff.
    NOMINAL_VOLTAGE = ParameterAttribute(
        Voltage,
        # Lazily read the default from config so a deployment (chef) can set
        # NOMINAL_VOLTAGE before the parameter is seeded. The callable is
        # evaluated at seed/access time (see ParameterAttribute.get_default),
        # not frozen at import, so the value is deterministic regardless of
        # the order in which this module is imported relative to config load.
        default=lambda: config.get("NOMINAL_VOLTAGE", 120.0),
        label="Nominal voltage of system",
        tooltip="Nominal voltage of current flowing through meters.",
    )

    METERING_PROVIDERS = ParameterAttribute(
        String, default="[]", label="Meter drivers", tooltip="JSON-encoded list of configured meter drivers."
    )

    @classmethod
    def __class_init__(cls):
        """Update all attributes with their names."""
        for attr, value in cls.type_attributes():
            # attribute needs to know its own name
            value.attribute = attr

            # for safe keeping
            cls.attributes.append(value)

    @classmethod
    def type_attributes(cls):
        """Get a sequence of ParameterAttribute names and values.

        :returns: sequence of tuple (attr, name) for all parameter attributes.
        """
        for attr, value in cls.__dict__.items():
            if type(value) is ParameterAttribute:
                yield (attr, value)


parameters = ParameterObject()
