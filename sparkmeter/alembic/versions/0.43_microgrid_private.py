# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""microgrid: Add private table.

Revision ID: 0.43
Revises: 0.42
Create Date: 2016-05-31 11:06:29.239818

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from sparkmeter.database.columns import JSONString
from sparkmeter.misc.uuidutils import as_uuid

revision = '0.43'
down_revision = '0.42'
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.42 to 0.43."""
    op.create_table(
        'microgrid_private',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('microgrid_id', postgresql.UUID(), nullable=False),
        sa.Column('status', JSONString(), nullable=True),
        sa.Column('max_capacity', sa.Integer(), nullable=True),
        sa.Column('secret_key', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )

    conn = op.get_bind()
    for result in conn.execute('SELECT * FROM microgrid;'):
        logger.info("Migrating columns from microgrid %s to private" % (result.serial, ))
        stmt = sa.sql.text(
            "INSERT INTO microgrid_private (id, microgrid_id, status, secret_key, max_capacity)"
            " VALUES (:id, :microgrid_id, :status, :secret_key, :max_capacity)")
        conn.execute(
            stmt,
            id=as_uuid(result.id, 'private'),
            microgrid_id=result.id,
            status=result.status,
            secret_key=result.secret_key,
            max_capacity=result.max_capacity,
        )
    op.drop_column(u'microgrid', 'secret_key')
    op.drop_column(u'microgrid', 'status')
    op.drop_column(u'microgrid', 'max_capacity')


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.43 to 0.42."""
    raise SystemExit("Downgrading from 0.43 to 0.42 is not supported")
