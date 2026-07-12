# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
import contextlib
from importlib import reload

from sparkmeter.config import configdomain, configparameter
from sparkmeter.config.configparametertypes import Bool
from sparkmeter.tests.test_data_factory import EventFactory


def test_get_class():
    assert isinstance(
        configparameter.ParameterObject.ALLOW_NEGATIVE_BALANCE, configparameter.ParameterAttribute
    )
    assert configparameter.ParameterObject.ALLOW_NEGATIVE_BALANCE.name == "allow-negative-balance"
    assert configparameter.ParameterObject.ALLOW_NEGATIVE_BALANCE.default
    assert isinstance(configparameter.ParameterObject.ALLOW_NEGATIVE_BALANCE.param_type, Bool)


def test_attribute_parameter(session):
    parameter = configdomain.ConfigParameter(name="foo-bar-baz", value_type="bool")
    session.add(parameter)
    session.commit()

    attribute = configparameter.ParameterAttribute(Bool)
    attribute.attribute = "foo_bar_baz"
    parameter = attribute.parameter
    assert parameter is not None
    assert isinstance(parameter, configdomain.ConfigParameter)
    assert parameter.name == "foo-bar-baz"


def test_get(session):
    parameter = configdomain.ConfigParameter(name="foo-bar-baz", value_type="bool", raw_value="true")
    session.add(parameter)
    session.commit()

    class FakeObject(object):
        foo_bar_baz = configparameter.ParameterAttribute(Bool)

    FakeObject.foo_bar_baz.attribute = "foo_bar_baz"

    x = FakeObject()
    assert x.foo_bar_baz is True


def test_set(session, mocker):
    create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
    create.return_value = EventFactory()

    parameter = configdomain.ConfigParameter(name="foo-bar-baz", value_type="bool")
    session.add(parameter)
    session.commit()

    class FakeObject(object):
        foo_bar_baz = configparameter.ParameterAttribute(Bool)

    FakeObject.foo_bar_baz.attribute = "foo_bar_baz"

    x = FakeObject()
    x.foo_bar_baz = True
    assert FakeObject.foo_bar_baz.parameter.raw_value == "true"

    x.foo_bar_baz = False
    assert FakeObject.foo_bar_baz.parameter.raw_value == "false"


def test_nominal_voltage(session, config):
    def reset_param(name):
        # Reset the nominal-voltage config parameter
        # Since config is a global variable and the default value in
        # ParameterObject is retrieved statically on module load, we must change
        # reload the module to take the applied changes to config into account
        reload(configparameter)
        cp = configdomain.ConfigParameter.get_by_name(name)
        session.delete(cp)
        session.commit()
        configdomain.ConfigParameter.add_defaults(session)
        session.commit()

    @contextlib.contextmanager
    def ctx(param_name, key, val):
        # Since resetting parameters will have a global impact beyond this
        # method, we need to reset to the default value after this context has
        # finished
        old_val = config.get(key)
        config[key] = val
        reset_param(param_name)
        yield
        config[key] = old_val
        reset_param(param_name)

    with ctx("nominal-voltage", "NOMINAL_VOLTAGE", 220.0):
        po = configparameter.ParameterObject()
        assert po.NOMINAL_VOLTAGE == 220.0
        cp = configdomain.ConfigParameter.get_by_name("nominal-voltage")
        assert cp.value == 220.0
