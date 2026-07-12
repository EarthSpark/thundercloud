# -*- coding: utf-8 -*-
# Copyright © 2026 SparkMeter, Inc.
# All Rights Reserved.
"""Tests for the `server dev` CLI command defaults."""

from sparkmeter.tests.base import SparkMeterTestCaseBase


class ServerDevCommandTest(SparkMeterTestCaseBase):
    """The dev server defaults to debug-on and demo-login-on; flags toggle off."""

    def _run_dev(self, app, cli, mocker, *args):
        # Mock the blocking run() and the (re-)bootstrap so the command returns;
        # patch.dict restores config mutations so the shared app is untouched.
        mocker.patch.object(app, "run")
        mocker.patch.object(app, "bootstrap")
        mocker.patch.dict(app.config)
        result = cli("server", "dev", *args)
        assert result.exit_code == 0, result.output
        return result

    def test_dev_debug_on_and_demo_login_on_by_default(self, app, cli, mocker):
        self._run_dev(app, cli, mocker)
        assert app.run.call_args.kwargs["debug"] is True
        # subscript (not .get): the command must have set the key to exactly True;
        # if the assignment were dropped the key would be absent and this errors.
        assert app.config["ENABLE_DEMO_LOGIN"] is True

    def test_dev_demo_login_disabled_by_explicit_flag(self, app, cli, mocker):
        self._run_dev(app, cli, mocker, "--no-demo-login")
        assert app.config["ENABLE_DEMO_LOGIN"] is False

    def test_dev_demo_login_default_overrides_preset_config(self, app, cli, mocker):
        # An ambient ENABLE_DEMO_LOGIN=False must NOT keep demo login off when the
        # operator runs `server dev` without a flag (pins the authoritative
        # assignment of the default, not a setdefault no-op).
        mocker.patch.object(app, "run")
        mocker.patch.object(app, "bootstrap")
        mocker.patch.dict(app.config, {"ENABLE_DEMO_LOGIN": False})
        result = cli("server", "dev")
        assert result.exit_code == 0, result.output
        assert app.config["ENABLE_DEMO_LOGIN"] is True

    def test_dev_debug_disabled_by_explicit_flag(self, app, cli, mocker):
        self._run_dev(app, cli, mocker, "--no-debug")
        assert app.run.call_args.kwargs["debug"] is False
