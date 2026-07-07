#!/usr/bin/env python
"""CLI entry point for Flask CLI system."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sparkmeter.app import SparkmeterApplication  # noqa isort:skip
from sparkmeter.cli import register_cli_commands  # noqa isort:skip


# Create app instance for CLI usage
app = SparkmeterApplication(mode=SparkmeterApplication.MODE_MANAGE)

# Provide the IApplication utility for CLI commands
app.provide()

# Register CLI commands
register_cli_commands(app)

# This is needed for Flask CLI to find the app
# Usage: export FLASK_APP=sparkmeter.cli_app:app && flask <command>
