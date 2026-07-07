# -*- coding: utf-8 -*-
# Copyright © 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Environment for running alembic upgrades.."""


import os
import sys

# allows alembic to run from root
path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..'))  # noqa
sys.path.insert(0, path)  # noqa

# Workaround for isort not allowing imports after a normal statement.
migrationhelper = __import__("sparkmeter.alembic.migrationhelper",
                             globals(), locals(), fromlist=[' '])

helper = migrationhelper.MigrationHelper()
helper.run()
