# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
from sparkmeter.misc.pythonutils import unset


def test_repr():
    assert repr(unset) == 'unset'


def test_is():
    assert unset is unset
    assert unset is not None
    assert unset != 0
    assert unset != 0.0
    assert unset != ""
