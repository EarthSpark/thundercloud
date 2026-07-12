# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
from sparkmeter.config.configdomain import ConfigParameter
from sparkmeter.config.configparametertypes import Bool
from sparkmeter.event.eventdomain import Event
from sparkmeter.tests.test_data_factory import OperatorFactory
from sparkmeter.user.userutils import set_current_user


def test_get_by_name(session):
    assert ConfigParameter.get_by_name("name") is None
    p = ConfigParameter(value_type="bool", name="name")
    session.add(p)
    session.commit()
    got = ConfigParameter.get_by_name("name")
    assert got.name == "name"


def test_parameter_type():
    parameter = ConfigParameter(value_type="bool")
    assert isinstance(parameter.parameter_type, Bool)
    assert parameter.parameter_type.type_name == "bool"


def test_value_getter():
    parameter = ConfigParameter(value_type="bool")

    parameter.raw_value = "false"
    assert parameter.value is False

    parameter.raw_value = "true"
    assert parameter.value is True


def test_value_setter(operator_role, session):
    user = OperatorFactory(roles=[operator_role])
    set_current_user(user)

    parameter = ConfigParameter(value_type="bool", name="bool")
    assert parameter.last_modified is None
    assert parameter.updated_by is None
    session.add(parameter)
    session.flush()
    assert Event.query.count() == 0

    # Setting the value should create a new event
    parameter.value = False
    assert parameter.raw_value == "false"
    session.commit()
    assert parameter.last_modified is not None
    assert parameter.updated_by == user
    prev_modified = parameter.last_modified

    assert Event.query.count() == 1
    event1 = Event.query.one()
    assert event1.object_table == "config_parameter"
    assert event1.object_id == parameter.id

    # Change the value should create a new event
    parameter.value = True
    assert parameter.raw_value == "true"
    session.commit()
    assert parameter.last_modified > prev_modified
    assert parameter.updated_by == user

    assert Event.query.count() == 2
    event2 = Event.get_last_event_by(Event.TYPE_CONFIG_PARAMETER_CHANGED, parameter)
    assert event2 is not None
    assert event1.id != event2.id

    # Update without changing the value should not create a new event
    parameter.value = True
    assert parameter.raw_value == "true"
    session.commit()
    assert Event.query.count() == 2
