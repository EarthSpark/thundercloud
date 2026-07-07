# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Change JSON columns into VARCHAR.

Revision ID: 0.23
Revises: 0.22
Create Date: 2016-04-14 12:07:56.496648

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

from sparkmeter.misc.jsonutils import json_dumps

revision = '0.23'
down_revision = '0.22'

JSON_COLUMNS = [
    ('microgrid', 'graph'),
    ('microgrid', 'status'),
    ('sparkmac_node', 'flooding_macs'),
    ('sparkmac_node', 'routing_enabled'),
    ('sparkmac_node', 'static_routes'),
    ('sync_collection', 'state'),
    ('sync_collection', 'statistics'),
    ('sync_conflict', 'loser'),
    ('sync_conflict', 'winner'),
    ('transaction_sources', 'transaction_metadata'),
]


def upgrade():
    """Upgrade the database schema from 0.22 to 0.23."""
    # Convert all JSON columns into VARCHAR
    # PostgreSQL supports migration of JSON into VARCHAR by itself, so we don't have to do
    # it manually in this migration patch.
    for table, column in JSON_COLUMNS:
        op.alter_column(table, column, existing_type=sa.VARCHAR(), existing_nullable=True)


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.23 to 0.22."""
    conn = op.get_bind()
    # Convert all the VARCHAR columns into JSON
    for table, column in JSON_COLUMNS:
        # Add a new temporary column for the JSON values
        op.add_column(table, sa.Column(column + '_json', JSON(), nullable=True))

        # Select all JSON values, as strings
        for (id_, value, ) in conn.execute('SELECT id, %s FROM %s' % (column, table)):
            # Convert string into JSON
            conn.execute("UPDATE %s SET %s = '%s' WHERE id = '%s'" % (
                table, column + '_json', json_dumps(value), id_))

        # Drop column old column which already has been migrated to the _json column
        op.drop_column(table, column)

        # Rename the _json column into the right one
        op.alter_column(table, column + '_json', new_column_name=column)
