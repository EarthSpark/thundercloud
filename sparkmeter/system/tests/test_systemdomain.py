# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
import uuid

import pytest

from sparkmeter.__version__ import version as current_version
from sparkmeter.system.systemdomain import SystemState, SystemVersion
from sparkmeter.tests.test_data_factory import SystemStateFactory


def test_system_version_get_status(session):
    s = SystemVersion()

    s.version = "0.0.0"
    assert s.status == SystemVersion.STATUS_OLD

    s.version = current_version
    assert s.status == SystemVersion.STATUS_ACTIVE

    s.version = "100.0.0"
    assert s.status == SystemVersion.STATUS_NEW


def test_system_version_get_parsed_version(session):
    s = SystemVersion()
    s.version = "1.2.3"
    assert s.parsed_version == SystemVersion.parse_version("1.2.3")


def test_system_version_eq(session):
    s1 = SystemVersion()
    s1.version = "1.2.3"

    s2 = SystemVersion()
    s2.version = "1.2.3"

    assert s1 == s2


def test_system_version_gt(session):
    s1 = SystemVersion()
    s1.version = "1.20.0"

    s2 = SystemVersion()
    s2.version = "1.2.4"

    assert s1 > s2


def test_system_version_default_id(session):
    s = SystemVersion()
    s.version = "1.2.3"

    session.add(s)
    session.commit()

    assert s.id == uuid.UUID("b0e8daa2-58ac-bb6f-c4c8-6f89e0c9183e")


def test_get_state(session, config):

    versions = [
        "1.2.5",
        "1.11.1",
    ]

    states = [
        SystemState.STATE_UPGRADABLE,
        SystemState.STATE_PREPARE,
        SystemState.STATE_TERMINATE,
        SystemState.STATE_START,
        SystemState.STATE_UPGRADE,
        SystemState.STATE_RUN,
    ]

    systems = [config.GROUND, config.CLOUD]

    for version in versions:
        for state in states:
            for system in systems:
                SystemStateFactory(system=system, state=state, version=version)

    # add one new version beyond the currently running version
    SystemStateFactory(system=config.GROUND, state=SystemState.STATE_UPGRADABLE, version="2.0.0")

    session.commit()

    # test the local state (cloud)
    config["HEROKU"] = True
    assert SystemState.get_state() == "run"

    # test the local state (ground)
    config["HEROKU"] = False
    assert SystemState.get_state() == "upgradable"

    # specify we want the ground state
    assert SystemState.get_state(config.GROUND) == "upgradable"

    # specify the cloud state
    assert SystemState.get_state(config.CLOUD) == "run"


def test_set_state_default_version(session, config):
    config["HEROKU"] = True
    # add a current version
    SystemState.set_state(state=SystemState.STATE_RUN, action="running", version="2.0.0")
    session.commit()

    # change the state without changing the version
    SystemState.set_state(state=SystemState.STATE_TERMINATE, action="terminating")
    session.commit()

    # test that the current version is 2.0.0 and the state is terminate
    assert SystemState.get_state() == SystemState.STATE_TERMINATE
    assert SystemState.get_version() == "2.0.0"


def test_set_state_no_default_version(session, config):
    config["HEROKU"] = True

    # change the state without specifying a version
    with pytest.raises(ValueError) as exc:
        SystemState.set_state(state=SystemState.STATE_TERMINATE, action="terminating")
    assert str(exc.value) == "No version provided and unable to determine current version"
