# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Move meter references.

Revision ID: 0.26
Revises: 0.25
Create Date: 2016-04-22 17:26:47.434502

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0.26'
down_revision = '0.25'
logger = logging.getLogger()
TABLES = [
    ('meter_config', 'config_id'),
    ('meter_system_info', 'system_info_id'),
    ('sparkmac_node', 'sparkmac_id'),
]


def upgrade():
    """Upgrade the database schema from 0.25 to 0.26."""
    for table, column in TABLES:
        op.add_column(table, sa.Column('meter_id', postgresql.UUID(), nullable=True))

        conn = op.get_bind()
        res = conn.execute("""
          UPDATE %(table)s SET meter_id = meter.id
            FROM meter
           WHERE meter.%(column)s = %(table)s.id""" % dict(table=table, column=column))
        logger.info('Set meter of %r %ss' % (res.rowcount, table))
        op.alter_column(table, 'meter_id', nullable=False)

        op.create_foreign_key(None, table, 'meter', ['meter_id'], ['id'])
        op.drop_constraint(u'meter_%s_fkey' % (column, ), 'meter', type_='foreignkey')
        op.drop_column('meter', column)


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.26 to 0.25."""
    for table, column in TABLES:
        op.add_column('meter', sa.Column(column, postgresql.UUID(),
                                         autoincrement=False, nullable=True))
        conn = op.get_bind()
        res = conn.execute("""
          UPDATE meter SET %(column)s = %(table)s.id
            FROM %(table)s
           WHERE %(table)s.meter_id = meter.id""" % (dict(table=table, column=column)))
        logger.info('Set customer of %r %ss' % (res.rowcount, table))
        op.alter_column('meter', column, nullable=False)

        op.create_foreign_key(u'meter_%s_fkey' % (column, ),
                              'meter', table, [column], ['id'])
        op.drop_column(table, 'meter_id')
