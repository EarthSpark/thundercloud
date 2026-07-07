# -*- coding: utf-8 -*-
# Copyright © 2026 SparkMeter, Inc.
# All Rights Reserved.
"""Tests for CLI command registration."""

from sparkmeter.tests.base import SparkMeterTestCaseBase


class CliRegistrationTest(SparkMeterTestCaseBase):

    def test_cli_commands_registered(self, app):
        """Verify all command groups are registered with the Flask CLI."""
        commands = app.cli.list_commands(None)
        expected = [
            'create-ground',
            'dashboard',
            'database',
            'demo',
            'event',
            'initdb',
            'meter',
            'metering',
            'reading',
            'resetdb',
            'salesaccount',
            'server',
            'shell',
            'status',
            'system',
            'tariff',
            'transaction',
            'user',
        ]
        for cmd in expected:
            assert cmd in commands, f"CLI command '{cmd}' not registered"
