# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
import datetime

import pytest
from freezegun import freeze_time
from testfixtures import LogCapture

from sparkmeter.system.systemdomain import SystemState, SystemVersion
from sparkmeter.tests.base import SparkMeterTestCaseBase


@pytest.fixture()
def logger():
    with LogCapture(("sparkmeter.system.systemcommand", "sparkmeter.system.systemdomain")) as logger:
        yield logger


@pytest.fixture()
def pinned_current_version(monkeypatch):
    """Pin the package's reported version to a value the test data was
    designed around. The actual `sparkmeter.__version__.version` is
    resolved by `hatch-vcs` from git tags at build time and can be
    `0.1.dev1+g<hash>` in an untagged checkout, which breaks
    old-vs-new comparisons against the registered versions below.
    """
    monkeypatch.setattr("sparkmeter.system.systemdomain.current_version", "1.5.0")


class SystemCommandTest(SparkMeterTestCaseBase):
    def test_register(self, cli, config, logger, pinned_current_version):
        config["HEROKU"] = False
        cli("system", "register", "--version", "1.2.3")
        version = SystemVersion.query.one()
        assert version.version == "1.2.3"
        logger.check(("sparkmeter.system.systemcommand", "INFO", "Added version 1.2.3 to database."))

    def test_register_from_cloud(self, cli, config, logger):
        config["HEROKU"] = True
        cli("system", "register", "--version", "1.2.3")
        assert SystemVersion.query.count() == 0
        logger.check(
            ("sparkmeter.system.systemcommand", "ERROR", "This command can only be run on the ground")
        )

    def test_register_duplicate(self, cli, config, logger):
        config["HEROKU"] = False
        logger.uninstall()
        cli("system", "register", "--version", "1.2.3")
        logger.install()

        cli("system", "register", "--version", "1.2.3")
        logger.check(
            ("sparkmeter.system.systemcommand", "WARNING", "version 1.2.3 is already in the database.")
        )

    def test_register_newer_version(self, cli, config, logger):
        config["HEROKU"] = False
        cli("system", "register", "--version", "999.2.3")
        state = SystemState.query.one()

        assert state.system == config.GROUND
        assert state.action == "version 999.2.3 prereleased on ground"
        assert state.state == SystemState.STATE_UPGRADABLE
        assert state.version == "999.2.3"

        logger.check(
            ("sparkmeter.system.systemcommand", "INFO", "Added version 999.2.3 to database."),
            ("sparkmeter.system.systemcommand", "INFO", "System state transitioned to upgradable."),
        )

    def test_versions(self, cli, config, pinned_current_version):
        """
        Verify that the versions command returns the right information.

        This should list all the versions registered, listed in the correct order
        by version number and not date. They should also include a status based on
        what the current version of the app is.
        """
        config["HEROKU"] = False

        dt = datetime.datetime(2017, 8, 15)

        # versions start out of order, to keep the dates out of order.
        app_versions = [
            "1.2.4",
            "1.2.3.rc0",
            "1.2.3",
            "1.20.0",
            "2.0.10000",
            "1.2.1",
        ]

        for v in app_versions:
            dt += datetime.timedelta(days=1)
            with freeze_time(dt):
                cli("system", "register", "--version", v)

        result = cli("system", "versions")
        expected = """{
    "1.2.1": {
        "status": "old",
        "installed": "2017-08-21T00:00:00"
    },
    "1.2.3.rc0": {
        "status": "old",
        "installed": "2017-08-17T00:00:00"
    },
    "1.2.3": {
        "status": "old",
        "installed": "2017-08-18T00:00:00"
    },
    "1.2.4": {
        "status": "old",
        "installed": "2017-08-16T00:00:00"
    },
    "1.20.0": {
        "status": "new",
        "installed": "2017-08-19T00:00:00"
    },
    "2.0.10000": {
        "status": "new",
        "installed": "2017-08-20T00:00:00"
    }
}"""
        assert result.output.strip() == expected
