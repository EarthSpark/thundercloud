# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Database migration base functions."""

import os
from unittest import mock

from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url

import sparkmeter.config.configdict
from sparkmeter.alembic.migrationhelper import get_alembic_config
from sparkmeter.database.database import (create_database_if_not_exists, drop_database_if_exists,
                                          load_schema)
from sparkmeter.tests.settings import SQLALCHEMY_DATABASE_URI

url = make_url(os.environ.get('DATABASE_URL', SQLALCHEMY_DATABASE_URI))
url = url.set(database='test_migration')
MIGRATION_TEST_URI = url.render_as_string(hide_password=False)


def bootstrap_migration_database():

    def create_database():
        url = make_url(MIGRATION_TEST_URI)
        drop_database_if_exists(MIGRATION_TEST_URI, url.database)
        create_database_if_not_exists(MIGRATION_TEST_URI, url.database)

    def migrate_to_latest(engine):
        config = get_alembic_config()
        config.set_main_option("sqlalchemy.url", MIGRATION_TEST_URI)
        script = ScriptDirectory.from_config(config)
        revision = 'head'

        # FIXME: Insert data when running these older migrations, like
        #        - reversed transactions
        #        - events
        #        - sms messages

        def monkey_patch_revision_step(step):
            # Override step.migration_fn for all Steps and call into
            # a test_defaults function inside each patch so we can provide
            # reasonable default unittest values for added tables
            orig_migration_fn = step.migration_fn

            def migration_fn():
                # Call upgrade() first
                orig_migration_fn()

                # Call test_defaults() in the same module, if one exists
                module = step.revision.module
                defaults_fn = getattr(module, 'test_defaults', None)
                if defaults_fn is not None:
                    defaults_fn()

            step.migration_fn = migration_fn

        def upgrade(rev, context):
            for step in script._upgrade_revs(revision, rev):
                monkey_patch_revision_step(step)
                old = sparkmeter.config.configdict.config['HEROKU']
                with mock.patch.dict(sparkmeter.config.configdict.config, {'HEROKU': False}):
                    yield step
                sparkmeter.config.configdict.config['HEROKU'] = old

        connection = engine.connect()

        # Patch Connection.execute at the class level to handle old
        # migration patterns: raw SQL strings and keyword params.
        # SQLAlchemy 2.x requires text() wrappers and dict params.
        # Also patch Row to support dict(row) which SA 2.x removed.
        from sqlalchemy.engine.base import Connection
        _orig_execute = Connection.execute

        def _patched_execute(self, stmt, *args, **kwargs):
            if isinstance(stmt, str):
                stmt = text(stmt)
            if kwargs and not args:
                args = (kwargs,)
                kwargs = {}
            return _orig_execute(self, stmt, *args, **kwargs)
        Connection.execute = _patched_execute

        with EnvironmentContext(
                config,
                script,
                connection=connection,
                fn=upgrade,
                as_sql=False,
                starting_rev=None,
                destination_rev=revision,
                tag=None):
            script.run_env()
        Connection.execute = _orig_execute
        connection.close()

    create_database()
    engine = create_engine(MIGRATION_TEST_URI)
    load_schema(engine, "base.sql")
    load_schema(engine, 'migration-0.03.sql')
    migrate_to_latest(engine)
