# -*- coding: utf-8 -*-
# Copyright © 2026 SparkMeter, Inc.
# All Rights Reserved.
"""Tests for Flask CLI commands."""

from sparkmeter.tests.base import SparkMeterTestCaseBase


class CliCommandTest(SparkMeterTestCaseBase):
    def test_status(self, cli):
        result = cli("status")
        assert result.exit_code == 0
        assert "Sparkmeter Application Status" in result.output
