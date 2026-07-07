# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""User Microgrids.

Revision ID: 0.41
Revises: 0.40
Create Date: 2016-06-16 21:45:01.783495

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from sparkmeter.misc.uuidutils import as_uuid

revision = '0.41'
down_revision = '0.40'
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.40 to 0.41."""
    op.create_table(
        'users_microgrids',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('microgrid_id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['microgrid_id'], ['public.microgrid.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['public.user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.add_column(
        'user',
        sa.Column(
            'microgrid_all_access',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        )
    )
    conn = op.get_bind()
    for role in ['operator', 'api']:
        res = conn.execute('UPDATE "user" SET microgrid_all_access = true;')
        logger.info('Updated microgrid_all_access for %d %s users' % (
            res.rowcount, role))

    microgrid_id = conn.execute('SELECT id FROM microgrid;').fetchone()[0]

    # For each user that has a wallet
    for result in conn.execute(
            'SELECT "user".id AS id, "user".username AS username FROM "user"'):
        conn.execute(
            sa.sql.text("INSERT INTO users_microgrids (id, user_id, microgrid_id)"
                        " VALUES (:id, :user_id, :microgrid_id)"),
            id=as_uuid(result.id, microgrid_id),
            user_id=result.id,
            microgrid_id=microgrid_id)
        logger.info('Added %d microgrids_user mappings for user %s' % (
            res.rowcount, result.username))


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.41 to 0.40."""
    raise SystemExit("Downgrading from 0.41 to 0.40 is not supported")
