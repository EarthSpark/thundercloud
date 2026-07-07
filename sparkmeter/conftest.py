# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Pytest unittest configuration.

Uses per-test database isolation via CREATE DATABASE ... TEMPLATE.
A template database is populated once per session with the full schema
and default data. Each test gets its own clone, so there is zero
cross-test pollution and tests can run in parallel with pytest-xdist.
"""
import os
import uuid
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from testfixtures import LogCapture
from zope.component import getUtility

from sparkmeter.interface import IApplication
from sparkmeter.misc.logutils import setup_logging

setup_logging()

TEMPLATE_DB_NAME = 'test_template'


# ---------------------------------------------------------------------------
# Session-scoped: bootstrap the app and create the template database
# ---------------------------------------------------------------------------

def _create_template_db(sql):
    """Create the template database from the current app database.

    Only runs once — subsequent calls (from xdist workers) skip if the
    template already exists.
    """
    source_db = sql.engine.url.database
    _base_url = sql.engine.url.render_as_string(hide_password=False)
    maintenance_engine = create_engine(
        make_url(_base_url).set(database='postgres'),
        isolation_level='AUTOCOMMIT',
    )
    with maintenance_engine.connect() as conn:
        # Check if template already exists (another worker may have created it)
        result = conn.execute(text(
            "SELECT 1 FROM pg_database WHERE datname = :t"
        ), {"t": TEMPLATE_DB_NAME})
        if result.first():
            maintenance_engine.dispose()
            return

        # Disconnect all other sessions from the source db first
        conn.execute(text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = :db AND pid != pg_backend_pid()"
        ), {"db": source_db})
        # Clone source -> template
        conn.execute(text(
            "CREATE DATABASE %s TEMPLATE %s" % (TEMPLATE_DB_NAME, source_db)
        ))
        conn.execute(text(
            "UPDATE pg_database SET datistemplate = true WHERE datname = :t"
        ), {"t": TEMPLATE_DB_NAME})
    maintenance_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def bootstrap_testsuite():
    """Bootstrap the Flask app and create a template database with schema + defaults."""
    from sparkmeter.app import SparkmeterApplication
    os.environ['SPARKMETER_SETTINGS'] = "sparkmeter/tests/settings.py"
    os.environ['SPARKMETER_TESTING'] = '1'
    app = SparkmeterApplication(mode=SparkmeterApplication.MODE_UNITTEST)
    app.bootstrap()
    # Preload pandas/numpy in the parent process so the lazy imports added
    # in dashboard/meter modules don't pay the C-extension load cost from
    # an xdist worker for the first user that hits a chart endpoint.
    try:
        import numpy  # noqa: F401
        import pandas  # noqa: F401
    except ImportError:
        pass

    import filelock

    from sparkmeter.database.alchemy import sql

    # The template is reused across runs to keep tests fast. Set
    # SM_REBUILD_TEST_TEMPLATE to drop and rebuild it (once per run; the marker
    # is in the container-local /tmp, fresh for each `docker compose run`).
    lock = filelock.FileLock('/tmp/sparkmeter_test_template.lock')
    built_marker = '/tmp/sparkmeter_template_built'
    with lock:
        _base_url = sql.engine.url.render_as_string(hide_password=False)
        maint = create_engine(
            make_url(_base_url).set(database='postgres'),
            isolation_level='AUTOCOMMIT',
        )
        with maint.connect() as conn:
            exists = conn.execute(text(
                "SELECT 1 FROM pg_database WHERE datname = :t"
            ), {"t": TEMPLATE_DB_NAME}).first()
            if (exists and os.environ.get('SM_REBUILD_TEST_TEMPLATE')
                    and not os.path.exists(built_marker)):
                conn.execute(text(
                    "UPDATE pg_database SET datistemplate = false "
                    "WHERE datname = :t"), {"t": TEMPLATE_DB_NAME})
                conn.execute(text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :t AND pid != pg_backend_pid()"),
                    {"t": TEMPLATE_DB_NAME})
                conn.execute(text("DROP DATABASE %s" % TEMPLATE_DB_NAME))
                exists = False
        maint.dispose()

        if not exists:
            from sparkmeter.controller import resetdb
            resetdb(force=True)
            sql.session.remove()
            sql.engine.dispose()
            _create_template_db(sql)
            open(built_marker, 'w').close()

    # Close the app's connection — each test gets its own cloned database.
    sql.session.remove()
    sql.engine.dispose()

    yield app


@pytest.fixture(scope="session")
def app(bootstrap_testsuite):
    """Flask app fixture."""
    yield getUtility(IApplication)


# ---------------------------------------------------------------------------
# Function-scoped: clone template → per-test database, reconfigure engine
# ---------------------------------------------------------------------------

@pytest.fixture()
def session(app):
    """Per-test database session.

    Clones the template database into a unique per-test database,
    reconfigures the Flask-SQLAlchemy engine to point at it, and
    tears it all down after the test.
    """
    from sparkmeter.database.alchemy import sql
    from sparkmeter.user.userutils import set_current_user

    base_url = sql.engine.url.render_as_string(hide_password=False)

    # Unique database name for this test
    test_db = 'test_' + uuid.uuid4().hex[:12]

    # Create the per-test database from template
    maint_url = make_url(base_url).set(database='postgres').render_as_string(hide_password=False)
    maintenance_engine = create_engine(maint_url, isolation_level='AUTOCOMMIT')
    with maintenance_engine.connect() as conn:
        conn.execute(text(
            "CREATE DATABASE %s TEMPLATE %s" % (test_db, TEMPLATE_DB_NAME)
        ))
    maintenance_engine.dispose()

    # Create a new engine for the test database
    test_url = make_url(base_url).set(database=test_db).render_as_string(hide_password=False)
    new_engine = create_engine(test_url)

    # Replace the engine on the Flask-SQLAlchemy extension
    sql.session.remove()
    sql.engine.dispose()
    from flask import current_app
    flask_app = current_app._get_current_object()
    sql._app_engines[flask_app][None] = new_engine

    # Replace the scoped_session with one scoped to thread ID instead of
    # app context ID. This ensures the fixture, test code, and Flask
    # request handlers all share the same session — objects created in
    # the fixture won't be "detached" when accessed during a request.
    import threading

    from sqlalchemy.orm import scoped_session as sa_scoped_session
    original_session = sql.session
    test_scoped = sa_scoped_session(
        sql.session.session_factory,
        scopefunc=threading.get_ident,
    )
    # Prevent Flask-SQLAlchemy's _teardown_session from destroying our
    # session between requests. It calls self.session.remove() after each
    # request, which would detach all objects.
    _real_remove = test_scoped.remove
    test_scoped.remove = lambda: None
    sql.session = test_scoped
    session = sql.session

    # Flask-SQLAlchemy track_modifications needs this
    raw = session()
    if not hasattr(raw, '_model_changes'):
        raw._model_changes = {}

    # Clear stale user references from previous tests
    set_current_user(None)

    # Setup factory_boy
    from sparkmeter.tests.test_data_factory import BaseFactory, DomainFactory
    BaseFactory.setup(session)
    DomainFactory.setup(session)

    yield session

    # Clear Flask-Login/Security state from g (which lives on the app
    # context in Flask 3.x and persists between tests)
    from flask import g
    g.pop('_login_user', None)
    g.pop('fs_authn_via', None)
    g.pop('fs_paa', None)
    g.pop('identity', None)

    # Properly remove the scoped session (not the no-op lambda)
    # to clear the identity map and detach all objects
    _real_remove()
    sql.session = original_session
    new_engine.dispose()

    drop_engine = create_engine(maint_url, isolation_level='AUTOCOMMIT')
    with drop_engine.connect() as conn:
        conn.execute(text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = :db AND pid != pg_backend_pid()"
        ), {"db": test_db})
        conn.execute(text("DROP DATABASE IF EXISTS %s" % test_db))
    drop_engine.dispose()


@pytest.fixture()
def cli(app):
    """CLI test runner fixture. Usage: cli('meter', 'create', '-s', 'serial')"""
    runner = app.test_cli_runner()
    return lambda *args: runner.invoke(args=list(args))


@pytest.fixture()
def client(app):
    """Flask test client fixture."""
    client = app.test_client()
    with client:
        yield client
    # Clear Flask-Login/Security state from g (which lives on the app
    # context in Flask 3.x and persists between tests on the same
    # xdist worker). Must happen after the client context exits so any
    # teardown requests don't re-populate it.
    from flask import g
    g.pop('_login_user', None)
    g.pop('fs_authn_via', None)
    g.pop('fs_paa', None)
    g.pop('identity', None)


@pytest.fixture()
def config():
    """Test fixture for app config."""
    from sparkmeter.config.configdict import config
    old_config = config.copy()
    yield config
    config.clear()
    config.update(old_config)


@pytest.fixture()
def session_manager(session):
    """Allow for the marshalling of multiple DB transactions.

    With per-test database isolation, each 'session' in the manager
    is just a new SQLAlchemy session on the same per-test database.
    """
    from sqlalchemy.orm import Session as SASession

    from sparkmeter.database.alchemy import sql

    # Capture engine ref now — child threads can't access sql.engine
    # because it requires a Flask app context
    engine = sql.engine

    class SessionManager:
        def __init__(self):
            self.sessions = {}
            self._sessions_to_close = []

        def get(self, name):  # pragma: nocoverage
            return self.sessions[name]

        def create(self, name):
            if name in self.sessions:  # pragma: nocoverage
                raise KeyError('Duplicate name')
            new_session = SASession(bind=engine)
            self.sessions[name] = new_session
            self._sessions_to_close.append(new_session)
            return new_session

    manager = SessionManager()
    yield manager

    for s in manager._sessions_to_close:
        s.rollback()
        s.close()


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Convenience fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def Role():
    """Test fixture for Role class."""
    from sparkmeter.user.userdomain import Role
    yield Role


@pytest.fixture()
def api_role(session, Role):
    """Test fixture for API role."""
    return session.query(Role).filter_by(name='api').one()


@pytest.fixture()
def vendor_role(session, Role):
    """Test fixture for Vendor role."""
    return session.query(Role).filter_by(name='vendor').one()


@pytest.fixture()
def operator_role(session, Role):
    """Test fixture for Operator role."""
    return session.query(Role).filter_by(name='operator').one()


@pytest.fixture(scope="function")
def send_set_config(mocker):
    """Test fixture for sending a set config packet."""
    yield mocker.patch('sparkmeter.meter.meterdomain.send_set_config')


@contextmanager
def scoped_session_context():
    """Provide a commit/rollback scope around a series of operations."""
    from sparkmeter.database.alchemy import sql
    try:
        yield sql.session
        sql.session.commit()
    except Exception:  # pragma: nocoverage
        sql.session.rollback()
        raise


@pytest.fixture()
def scoped_session():
    """A test fixture for session scopes."""
    yield scoped_session_context


@pytest.fixture()
def sentry_logger():
    """Sentry proxy log context fixture."""
    with LogCapture('sparkmeter.sentry') as logger:
        yield logger
