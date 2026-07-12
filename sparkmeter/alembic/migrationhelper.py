# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Helper for running alembic upgrades.."""

from __future__ import with_statement

import glob
import logging
import os
from builtins import object

from alembic import command, context
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import Session

from sparkmeter.app import SparkmeterApplication
from sparkmeter.config.configdict import config
from sparkmeter.database.database import load_database_schemas, sync_triggers_disabled

logger = logging.getLogger(__name__)


class MigrationHelper(object):
    """Helper to initialize and configure alembic."""

    def __init__(self):
        """Load configuration and application."""
        self._app = SparkmeterApplication(mode="alembic")
        self._app.provide()
        self._app.setup_databases()

    def _get_database_url(self):  # pragma: nocoverage
        url = context.config.get_main_option("sqlalchemy.url")
        if url:
            return url
        return self._app.config.get("SQLALCHEMY_DATABASE_URI")

    def include_object(self, object, name, type_, reflected, compare_to):  # pragma: nocoverage
        """Check which objects should be included when reflecting domain objects.

        This is used when generating a new patch version.
        """
        if object.info.get("is_view", False):
            return False
        if type_ == "table" and name.startswith("sym_"):
            return False
        return True

    def run(self):
        """Run the main migration."""
        url = self._get_database_url()
        engine = create_engine(url)
        connection = engine.connect()
        context.configure(
            include_schemas=True,
            include_object=self.include_object,
            connection=connection,
            target_metadata=self._app.sql.metadata,
            compare_type=True,
        )

        try:
            with sync_triggers_disabled(connection):
                with context.begin_transaction():
                    context.run_migrations()
            # This is currently all replacable/recreatable schemas like functions and views,
            # It has to be done after all patches has been loaded and only if we
            # are currently at the latest schema version, which is the only valid
            # version.
            latest = get_latest_patch(context.config)
            script = ScriptDirectory.from_config(context.config)
            if ".".join(map(str, latest)) == script.get_revisions("head")[-1].revision:
                load_database_schemas(engine)
            session = Session(engine)
            from sparkmeter.config.configdomain import ConfigParameter

            has_config_params = session.query(ConfigParameter).count() > 0
            # Assume that, if there are no config parameters, this is a new system and sync isn't initialized.
            if not config["HEROKU"] or not has_config_params:
                ConfigParameter.add_defaults(session)
                session.commit()
        finally:
            connection.close()


def get_alembic_config():
    """Get the alembic configuration
    :returns: the configuration
    :rtype: Config
    """
    cfg = Config()
    script_dir = os.path.join(os.path.dirname(__file__))
    cfg.set_main_option("script_location", script_dir)
    cfg.set_main_option("version_locations", os.path.join(script_dir, "versions"))
    return cfg


def upgrade_database(engine, revision):
    """Upgrade the database to the given alembic revision.

    :param engine: a database engine
    :param revision: the revision to upgrade to
    """
    alembic_cfg = get_alembic_config()

    with engine.connect() as connection:
        with sync_triggers_disabled(connection):
            command.upgrade(alembic_cfg, revision)
    load_database_schemas(engine)


def downgrade_database(engine, revision):
    """Downgrade the database to the given alembic revision.

    :param engine: a database engine
    :param revision: the revision to downgrade to
    """
    alembic_cfg = get_alembic_config()

    with engine.connect() as connection:
        with sync_triggers_disabled(connection):
            command.downgrade(alembic_cfg, revision)
    load_database_schemas(engine)


def create_migration(engine, message, sql_file, version_num=None):
    """Create a new alembic revision.

    :param engine: a database engine
    :param message: the revision message
    :param sql_file: the sql file path for the schema
    :param version_num: the version number for the revision id
    """
    alembic_cfg = get_alembic_config()

    command.revision(alembic_cfg, message=message, autogenerate=True, rev_id=version_num)


def get_latest_patch(alembic_cfg=None):
    """Get the latest alembic version
    :param alembic_cfg:
    :return: Tuple (patch_ver, minor)
    """
    if alembic_cfg is None:
        alembic_cfg = get_alembic_config()
    script_dir = alembic_cfg.get_main_option("version_locations")
    items = sorted(glob.glob(script_dir + "/*.py"))
    last_patch_filename = items[-2]  # -1 is __init__.py
    last_patch = os.path.basename(last_patch_filename).split("_", 1)[0]
    return map(int, last_patch.split("."))
