# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import pytest
from testfixtures import LogCapture

from sparkmeter.config.configparametertypes import Bool, Float, ParameterType, Percent, String, Voltage


def test_abstract():
    class TestType(ParameterType):
        pass

    tt = TestType()
    with pytest.raises(NotImplementedError) as exc:
        tt.to_python(None)
    assert str(exc.value) == "TestType"
    with pytest.raises(NotImplementedError) as exc:
        tt.from_python(None)
    assert str(exc.value) == "TestType"


def test_bool_from_python():
    b = Bool()
    assert b.from_python(True) == "true"
    assert b.from_python(False) == "false"
    with pytest.raises(TypeError) as exc:
        assert b.from_python(None)
    assert str(exc.value) == "boolean parameters must be True or False, not None."


def test_bool_to_python():
    b = Bool()
    assert b.to_python("true") is True
    assert b.to_python("false") is False
    with LogCapture("sparkmeter.config.configparametertypes") as log:
        assert b.to_python(None) is False
    log.check(
        ("sparkmeter.config.configparametertypes", "WARNING", "Could not convert None to a boolean value")
    )


def test_float_from_python():
    f = Float()
    assert f.from_python(0) == "0.0"
    assert f.from_python(0.0) == "0.0"
    assert f.from_python(0) == "0.0"
    assert f.from_python(-123) == "-123.0"
    assert f.from_python(345.678) == "345.678"
    with pytest.raises(TypeError) as exc:
        assert f.from_python("xxx")
    assert str(exc.value) == "value must be a number, not str."


def test_float_to_python():
    f = Float()
    assert f.to_python("0.0") == 0.0
    assert f.to_python("-123.0") == -123.0
    assert f.to_python("345.678") == 345.678
    for v in [None, "xxx", (), []]:
        with LogCapture("sparkmeter.config.configparametertypes") as log:
            assert f.to_python(v) == 0.0
        log.check(
            (
                "sparkmeter.config.configparametertypes",
                "WARNING",
                "Could not convert database value {!r} to a python float".format(v),
            )
        )
        log.clear()


def test_percent():
    p = Percent()
    # Below the minimum clamps up to 0; above the maximum clamps down to 100.
    for v, expected, msg in [
        (-1, "0.0", "value cannot be less than 0.0, defaulting to 0.0."),
        (101, "100.0", "value cannot be more than 100.0, defaulting to 100.0."),
    ]:
        with LogCapture("sparkmeter.config.configparametertypes") as log:
            assert p.from_python(v) == expected
        log.check(("sparkmeter.config.configparametertypes", "WARNING", msg))
        log.clear()


def test_voltage():
    v = Voltage()
    assert v.from_python(110) == "110.0"
    assert v.from_python(120) == "120.0"
    with pytest.raises(TypeError):
        v.to_python("113")
    with pytest.raises(TypeError):
        v.from_python("113")


def test_string():
    s = String()
    assert s.to_python(None) == ""
    assert s.to_python(123) == "123"
    assert s.from_python(None) == ""
    assert s.from_python("hello") == "hello"
    with pytest.raises(TypeError) as exc:
        s.from_python(123)
    assert str(exc.value) == "string parameters must be strings, not 'int'."
    # bool is an int subclass but still not a str, so it is rejected too.
    with pytest.raises(TypeError) as exc:
        s.from_python(True)
    assert str(exc.value) == "string parameters must be strings, not 'bool'."
