# Copyright (C) 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Add transaction state change date columns.

Revision ID: 0.66
Revises: 0.65
Create Date: 2018-09-27 11:58:32.123505

"""

import sqlalchemy as sa
from alembic import op

revision = '0.66'
down_revision = '0.65'


def upgrade():
    """Upgrade the database schema from 0.65 to 0.66."""
    op.add_column('transactions', sa.Column('processed_timestamp', sa.DateTime(), nullable=True))
    op.add_column('transactions', sa.Column('reversed_timestamp', sa.DateTime(), nullable=True))
    op.add_column('transactions', sa.Column('errored_timestamp', sa.DateTime(), nullable=True))
    conn = op.get_bind()

    # Load processed times from the Event table
    conn.execute(
        """UPDATE transactions
        SET processed_timestamp = event.timestamp
        FROM event
        WHERE transactions.id = event.object_id
        AND state = 'processed'
        AND transactions.processed_timestamp IS NULL
        AND event.object_table = 'transactions'
        AND event.event_type LIKE 'customer-%%-transaction-processed'
        """
    )

    # Populate remaining processed time fields with the created timestamp
    conn.execute(
        """UPDATE transactions
        SET processed_timestamp = created
        WHERE state = 'processed'
        AND processed_timestamp IS NULL
        """
    )

    # Load reversed times from the Event table
    conn.execute(
        """UPDATE transactions
        SET reversed_timestamp = event.timestamp
        FROM event
        WHERE transactions.id = event.object_id
        AND state = 'reversed'
        AND reversed_timestamp IS NULL
        AND event.object_table = 'transactions'
        AND event.event_type = 'reversal-transaction-processed'
        """
    )

    # Populate remaining reversed time fields with the created timestamp
    conn.execute(
        """UPDATE transactions
        SET reversed_timestamp = created
        WHERE state = 'reversed'
        AND reversed_timestamp IS NULL
        """
    )

    # Populate errored time fields with the created timestamp
    conn.execute(
        """UPDATE transactions
        SET errored_timestamp = created
        WHERE state = 'error'
        AND errored_timestamp IS NULL
        """
    )


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.66 to 0.65."""
    op.drop_column('transactions', 'processed_timestamp')
    op.drop_column('transactions', 'reversed_timestamp')
    op.drop_column('transactions', 'errored_timestamp')
