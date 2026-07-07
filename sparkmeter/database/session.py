# Copyright © 2026 SparkMeter, Inc.
# All Rights Reserved.
"""SQLAlchemy test session utilities.

Implements the SQLAlchemy 2.x "Joining a Session into an External Transaction"
pattern for test isolation.

Reference:
https://docs.sqlalchemy.org/en/20/orm/session_transaction.html
"""
from sqlalchemy.orm import scoped_session, sessionmaker


def create_test_session(db):
    """Create a test session bound to an external transaction.

    All database access (views, CLI, tests, factory_boy) goes through the
    same connection and transaction. At cleanup, the transaction is rolled
    back so no test data persists.
    """
    connection = db.engine.connect()
    transaction = connection.begin()

    # Create a sessionmaker bound to this connection. join_transaction_mode
    # makes session.commit() use SAVEPOINTs instead of real commits.
    factory = sessionmaker(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
    )

    # Wrap in scoped_session for compatibility with Flask-SQLAlchemy
    session = scoped_session(factory)

    # Flask-SQLAlchemy's track_modifications listener expects _model_changes
    # on the session. Initialize it on first access.
    raw = session()
    if not hasattr(raw, '_model_changes'):
        raw._model_changes = {}

    # Store the real remove for cleanup, then override to prevent
    # Flask-SQLAlchemy's _teardown_session from destroying our session
    _real_remove = session.remove
    session.remove = lambda: None

    # Store original session for restoration
    original_session = db.session

    def cleanup():
        session.remove = _real_remove
        session.remove()
        transaction.rollback()
        connection.close()
        db.session = original_session

    # Expose connection for concurrent tests that need to commit
    # to the outer transaction
    session._test_connection = connection
    session._test_transaction = transaction

    return session, cleanup
