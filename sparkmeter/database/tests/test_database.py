# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import os
from unittest import mock

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from testfixtures import LogCapture

from sparkmeter.database.alchemy import sql
from sparkmeter.database.database import (
    bootstrap_production,
    database_exists,
    wait_for_ground_host,
    wait_for_postgres,
    wait_for_table,
    wait_for_table_count,
    wait_for_triggers,
)
from sparkmeter.tests.base import SparkMeterTestCaseBase


@pytest.fixture()
def logger():
    with LogCapture("sparkmeter.database.database") as logger:
        yield logger


@pytest.fixture()
def create_engine(mocker):
    yield mocker.patch("sparkmeter.database.database.create_engine")


@pytest.fixture()
def resetdb(mocker):
    yield mocker.patch("sparkmeter.controller.resetdb", return_value=False)


@pytest.fixture(name="table_is_empty")
def mock_table_is_empty(mocker):
    yield mocker.patch("sparkmeter.database.database.table_is_empty", return_value=True)


@pytest.fixture()
def sleep(mocker):
    yield mocker.patch("time.sleep")


@pytest.fixture(name="create_default_policy")
def mock_create_default_policy(mocker):
    yield mocker.patch("sparkmeter.database.sync.create_default_policy")


@pytest.fixture(name="database_has_table")
def mock_database_has_table(mocker):
    yield mocker.patch("sparkmeter.database.database.database_has_table")


@pytest.fixture(name="wait_for_table")
def mock_wait_for_table(mocker):
    yield mocker.patch("sparkmeter.database.database.wait_for_table")


@pytest.fixture(name="wait_for_ground_host")
def mock_wait_for_ground_host(mocker):
    yield mocker.patch("sparkmeter.database.database.wait_for_ground_host")


@pytest.fixture(name="wait_for_triggers")
def mock_wait_for_triggers(mocker):
    yield mocker.patch("sparkmeter.database.database.wait_for_triggers")


@pytest.fixture(name="wait_for_postgres")
def mock_wait_for_postgres(mocker):
    yield mocker.patch("sparkmeter.database.database.wait_for_postgres")


@pytest.fixture(name="wait_for_table_count")
def mock_wait_for_table_count(mocker):
    yield mocker.patch("sparkmeter.database.database.wait_for_table_count")


@pytest.fixture()
def DemoExamples(mocker):
    yield mocker.patch("sparkmeter.database.demodata.DemoExamples")


class DatabaseTest(SparkMeterTestCaseBase):
    @property
    def engine(self):
        return sql.engine

    def test_database_exists(self):
        engine = mock.MagicMock()
        # Setup: connect() as context manager returns a connection mock
        conn = engine.connect().__enter__()
        conn.execute().first.return_value = [1]
        engine.reset_mock()

        assert database_exists(engine, "database")
        # Verify: used context manager, called execute with text + params, called first()
        engine.connect.assert_called_once()
        conn = engine.connect().__enter__()
        conn.execute.assert_called_once_with(mock.ANY, {"datname": "database"})
        conn.execute().first.assert_called_once()

        # Reset for negative test
        conn = engine.connect().__enter__()
        conn.execute().first.return_value = [0]
        engine.reset_mock()

        assert not database_exists(engine, "invalid-database-name")
        engine.connect.assert_called_once()
        conn = engine.connect().__enter__()
        conn.execute.assert_called_once_with(mock.ANY, {"datname": "invalid-database-name"})
        conn.execute().first.assert_called_once()

    def test_wait_for_table(self, sleep, logger):
        engine = mock.MagicMock()
        engine.connect().execute().fetchone().__getitem__.side_effect = [0, 1]
        engine.reset_mock()
        wait_for_table(engine, "table_name")

        # Should connect twice (first iteration finds 0, sleeps, second finds 1)
        assert engine.connect.call_count == 2
        # Each iteration: connect, execute(text, params), fetchone, close
        conn = engine.connect()
        assert conn.execute.call_count == 2
        # Verify params passed correctly
        for call in conn.execute.call_args_list:
            args = call[0]
            assert len(args) >= 1  # text object
            if len(args) > 1:
                assert args[1] == {"table": "table_name"}
        assert conn.close.call_count == 2
        assert sleep.mock_calls == [
            mock.call(2),
        ]
        logger.check(
            ("sparkmeter.database.database", "INFO", "Waiting for table table_name to be present in schema"),
            ("sparkmeter.database.database", "INFO", "Table table_name found"),
        )

    def test_wait_for_table_count(self, wait_for_table, sleep, logger):
        engine = mock.MagicMock()
        engine.connect().execute().fetchone().__getitem__.side_effect = [0, 5]
        engine.reset_mock()
        wait_for_table_count(engine, "table_name", 3)

        # Should connect twice (first iteration finds 0, sleeps, second finds 5)
        assert engine.connect.call_count == 2
        conn = engine.connect()
        assert conn.execute.call_count == 2
        assert conn.close.call_count == 2
        assert wait_for_table.mock_calls == [mock.call(engine, "table_name")]
        assert sleep.mock_calls == [
            mock.call(2),
        ]

        logger.check(
            (
                "sparkmeter.database.database",
                "INFO",
                "Waiting for table table_name to contain at least 3 row(s) ]",
            ),
            ("sparkmeter.database.database", "INFO", "Table table_name contains 5 items, continuing"),
        )

    def test_wait_for_postgres(self, sleep, create_engine, logger):
        create_engine().connect.side_effect = [OperationalError("a", "b", "c"), None]
        create_engine.reset_mock()
        wait_for_postgres("postgresql://host/db")

        assert create_engine.mock_calls == [
            mock.call("postgresql://host/db"),
            mock.call().connect(),
            mock.call("postgresql://host/db"),
            mock.call().connect(),
        ]
        assert sleep.mock_calls == [
            mock.call(2),
        ]
        logger.check(
            ("sparkmeter.database.database", "INFO", "Waiting for PostgreSQL"),
        )

    def test_wait_for_ground_host(self):
        engine = mock.MagicMock()
        engine.connect().execute().fetchone().__getitem__.side_effect = [0, 1]
        engine.reset_mock()
        wait_for_ground_host(engine)
        # Should connect twice (first attempt finds 0, second finds 1)
        assert engine.connect.call_count == 2
        conn = engine.connect()
        # Each iteration: execute(text), fetchone, close
        assert conn.execute.call_count == 2
        assert conn.close.call_count == 2

    def test_wait_for_triggers(self):
        engine = mock.MagicMock()
        engine.connect().execute().fetchone().__getitem__.side_effect = [0, 1, 2, 2]
        engine.reset_mock()
        wait_for_triggers(engine, wait_seconds=0)
        # Connects once, executes 4 queries, then closes
        engine.connect.assert_called_once()
        conn = engine.connect()
        assert conn.execute.call_count == 4
        conn.close.assert_called_once()

    def test_bootstrap_production_ground(
        self, app, config, logger, resetdb, database_has_table, wait_for_postgres, table_is_empty
    ):
        config.update(HEROKU=False, SQLALCHEMY_DATABASE_URI="db://url")
        database_has_table.return_value = False
        wait_for_postgres.return_value = "my-engine"

        bootstrap_production(app)
        assert database_has_table.mock_calls == [mock.call("my-engine", "alembic_version")]
        assert wait_for_postgres.mock_calls[0] == mock.call("db://url")
        assert resetdb.mock_calls == [
            mock.call(force=True, empty=True, resetschema=False, engine="my-engine")
        ]

        logger.check(
            ("sparkmeter.database.database", "INFO", "Creating an empty schema"),
            ("sparkmeter.database.database", "INFO", "No ground found in this database"),
            (
                "sparkmeter.database.database",
                "WARNING",
                (
                    "Skipping creation of ground because required "
                    "fields are missing ['INIT_GROUND_NAME', 'INIT_GROUND_SERIAL']"
                ),
            ),
        )

    def test_bootstrap_production_ground_demo(
        self, app, config, logger, resetdb, database_has_table, wait_for_postgres, DemoExamples
    ):
        config.update(HEROKU=False, SQLALCHEMY_DATABASE_URI="db://url")
        database_has_table.return_value = True
        environ = mock.patch.dict(os.environ, {"INIT_DEMO_ON_STARTUP": "true"})
        wait_for_postgres.return_value = self.engine
        try:
            environ.start()
            bootstrap_production(app)
            assert database_has_table.mock_calls == [mock.call(self.engine, "alembic_version")]
            assert wait_for_postgres.mock_calls[0] == mock.call("db://url")
            assert resetdb.mock_calls == [mock.call(resetschema=False, force=True)]
            assert DemoExamples.mock_calls == [
                mock.call(self.session),
                mock.call().create_ground(),
                mock.call().create_all(),
            ]
            logger.check(("sparkmeter.database.database", "INFO", "Resetting demo"))
        finally:
            environ.stop()

    def test_bootstrap_production_ground_demo_two_grounds(
        self, app, config, database_has_table, logger, resetdb, wait_for_postgres, DemoExamples
    ):
        config.update(HEROKU=False, SQLALCHEMY_DATABASE_URI="db://url")
        database_has_table.return_value = True
        wait_for_postgres.return_value = self.engine

        environ = mock.patch.dict(
            os.environ,
            {
                "INIT_DEMO_ON_STARTUP": "true",
                "SM_SERIAL_GROUND1": "ground1-serial",
                "SM_MICROGRID_NAME_GROUND1": "ground1-name",
                "SM_SERIAL_GROUND2": "ground2-serial",
                "SM_MICROGRID_NAME_GROUND2": "ground2-name",
            },
        )
        try:
            environ.start()
            bootstrap_production(app)
            assert database_has_table.mock_calls == [mock.call(self.engine, "alembic_version")]
            assert wait_for_postgres.mock_calls[0] == mock.call("db://url")
            assert resetdb.mock_calls == [mock.call(resetschema=False, force=True)]
            assert DemoExamples.mock_calls == [
                mock.call(self.session),
                mock.call().create_ground("ground1-name", "ground1-serial"),
                mock.call().create_ground("ground2-name", "ground2-serial"),
                mock.call().create_all(),
            ]

            logger.check(("sparkmeter.database.database", "INFO", "Resetting demo"))
        finally:
            environ.stop()

    def test_bootstrap_production_cloud(
        self,
        mocker,
        create_default_policy,
        wait_for_ground_host,
        wait_for_triggers,
        wait_for_table_count,
        database_has_table,
        wait_for_postgres,
        logger,
        resetdb,
    ):
        # Mock alembic.command since env.py creates its own DB connection
        # that we can't direct to the per-test database
        mocker.patch("alembic.command")
        database_has_table.return_value = True
        app = mock.Mock()
        app.app_context = mock.MagicMock()
        app.config = dict(
            EXTERNAL_ID="external-id",
            HEROKU=True,
            SQLALCHEMY_DATABASE_URI="db://url",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        environ = mock.patch.dict(
            os.environ,
            dict(
                EXTERNAL_ID="external-id",
            ),
        )

        wait_for_postgres.return_value = engine = mock.MagicMock(spec=Engine)
        engine.connect().execute().fetchone().__getitem__.return_value = 0
        engine.reset_mock()
        try:
            environ.start()
            bootstrap_production(app)
            assert database_has_table.mock_calls == [mock.call(engine, "alembic_version")]
            assert resetdb.mock_calls == []
            # Verify wait_for_postgres was called with the right URL
            assert mock.call("db://url") in wait_for_postgres.mock_calls
            assert wait_for_table_count.mock_calls == [
                mock.call(engine, "sym_sequence", 4),
                mock.call(engine, "sym_trigger_hist", 1),
            ]
            assert create_default_policy.mock_calls == [
                mock.call(
                    app.sql.session,
                    external_id="external-id",
                )
            ]
            assert wait_for_ground_host.mock_calls == []
            logger.check(
                ("sparkmeter.database.database", "INFO", "Attempting schema upgrade"),
                ("sparkmeter.database.database", "INFO", "Finished upgrading schema"),
                ("sparkmeter.database.database", "INFO", "No ground found in this database"),
                (
                    "sparkmeter.database.database",
                    "WARNING",
                    (
                        "Skipping creation of ground because required "
                        "fields are missing ['INIT_GROUND_NAME', 'INIT_GROUND_SERIAL']"
                    ),
                ),
                ("sparkmeter.database.database", "INFO", "Running init-sync"),
            )
        finally:
            environ.stop()

    def test_bootstrap_production_cloud_init(
        self,
        mocker,
        create_default_policy,
        wait_for_ground_host,
        wait_for_triggers,
        wait_for_table_count,
        resetdb,
        database_has_table,
        wait_for_postgres,
        logger,
    ):
        mocker.patch("alembic.command")
        # the database has no tables yet, so this should be a clean install
        database_has_table.return_value = False
        app = mock.Mock()
        app.app_context = mock.MagicMock()
        app.config = dict(
            EXTERNAL_ID="external-id",
            HEROKU=True,
            SQLALCHEMY_DATABASE_URI="db://url",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            INIT_ADMIN_USERNAME="admin",
            INIT_ADMIN_PASSWORD="passw0rd",
            INIT_ADMIN_EMAIL="admin@sparkmeter.io",
        )
        wait_for_postgres.return_value = engine = mock.MagicMock(spec=Engine)
        engine.connect().execute().fetchone().__getitem__.return_value = 0
        engine.reset_mock()

        environ = mock.patch.dict(
            os.environ,
            dict(
                EXTERNAL_ID="external-id",
                INIT_CREATE_DEFAULTS="true",
                INIT_ADMIN_USERNAME="admin",
                INIT_ADMIN_PASSWORD="passw0rd",
                INIT_ADMIN_EMAIL="admin@sparkmeter.io",
                INIT_GROUND_NAME="ground",
                INIT_GROUND_SERIAL="serial",
            ),
        )
        try:
            environ.start()
            bootstrap_production(app)
            assert database_has_table.mock_calls == [mock.call(engine, "alembic_version")]
            assert resetdb.mock_calls == [
                mock.call(force=True, empty=False, resetschema=False, engine=engine)
            ]
            # Verify wait_for_postgres was called with the right URL
            assert mock.call("db://url") in wait_for_postgres.mock_calls
            assert wait_for_table_count.mock_calls == [
                mock.call(engine, "sym_sequence", 4),
                mock.call(engine, "sym_trigger_hist", 1),
            ]
            assert create_default_policy.mock_calls == [
                mock.call(
                    app.sql.session,
                    external_id="external-id",
                )
            ]
            # wait_for_ground_host is only called in init_demo path
            assert wait_for_ground_host.mock_calls == []
            assert wait_for_triggers.mock_calls == [mock.call(engine)]
            logger.check(
                ("sparkmeter.database.database", "INFO", "Creating an empty schema"),
                ("sparkmeter.database.database", "INFO", "No ground found in this database"),
                ("sparkmeter.database.database", "INFO", "Creating the initial ground"),
                ("sparkmeter.database.database", "INFO", "ground created"),
                ("sparkmeter.database.database", "INFO", "Running init-sync"),
                ("sparkmeter.database.database", "INFO", "No admin user found in this database"),
                ("sparkmeter.database.database", "INFO", "Creating the initial admin user"),
                ("sparkmeter.database.database", "INFO", "admin user created"),
            )

        finally:
            environ.stop()

    def test_bootstrap_production_cloud_init_no_ground_or_user(
        self,
        mocker,
        create_default_policy,
        wait_for_ground_host,
        wait_for_triggers,
        wait_for_table_count,
        resetdb,
        database_has_table,
        wait_for_postgres,
        logger,
    ):
        mocker.patch("alembic.command")
        # the database has no tables yet, so this should be a clean install
        database_has_table.return_value = False
        app = mock.Mock()
        app.app_context = mock.MagicMock()
        app.config = dict(
            EXTERNAL_ID="external-id",
            HEROKU=True,
            SQLALCHEMY_DATABASE_URI="db://url",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        wait_for_postgres.return_value = engine = mock.MagicMock(spec=Engine)
        engine.connect().execute().fetchone().__getitem__.return_value = 0
        engine.reset_mock()

        environ = mock.patch.dict(
            os.environ,
            dict(
                EXTERNAL_ID="external-id",
                INIT_CREATE_DEFAULTS="true",
            ),
        )
        try:
            environ.start()
            bootstrap_production(app)
            assert database_has_table.mock_calls == [mock.call(engine, "alembic_version")]
            assert resetdb.mock_calls == [
                mock.call(force=True, empty=False, resetschema=False, engine=engine)
            ]
            # Verify wait_for_postgres was called with the right URL
            assert mock.call("db://url") in wait_for_postgres.mock_calls
            assert wait_for_table_count.mock_calls == [
                mock.call(engine, "sym_sequence", 4),
                mock.call(engine, "sym_trigger_hist", 1),
            ]
            assert create_default_policy.mock_calls == [
                mock.call(
                    app.sql.session,
                    external_id="external-id",
                )
            ]
            # wait_for_ground_host is only called in init_demo path
            assert wait_for_ground_host.mock_calls == []
            logger.check(
                ("sparkmeter.database.database", "INFO", "Creating an empty schema"),
                ("sparkmeter.database.database", "INFO", "No ground found in this database"),
                (
                    "sparkmeter.database.database",
                    "WARNING",
                    (
                        "Skipping creation of ground because required "
                        "fields are missing ['INIT_GROUND_NAME', 'INIT_GROUND_SERIAL']"
                    ),
                ),
                ("sparkmeter.database.database", "INFO", "Running init-sync"),
            )

        finally:
            environ.stop()
