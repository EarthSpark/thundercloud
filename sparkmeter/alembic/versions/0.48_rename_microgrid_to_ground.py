# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""rename microgrid to ground

Revision ID: 0.48
Revises: 0.47
Create Date: 2016-08-29 18:01:31.091926

"""

from alembic import op

revision = '0.48'
down_revision = '0.47'


def upgrade():
    """Upgrade the database schema from 0.48 to 0.47."""
    op.rename_table('microgrid', 'ground')
    op.rename_table('microgrid_private', 'ground_private')
    op.rename_table('microgrids_addresses', 'grounds_addresses')
    op.rename_table('users_microgrids', 'users_grounds')

    op.alter_column('address', 'microgrid_id', new_column_name='ground_id')
    op.alter_column('dashboard_daily_tariff_summary', 'microgrid_id', new_column_name='ground_id')
    op.alter_column('event', 'microgrid_id', new_column_name='ground_id')
    op.alter_column('meter', 'microgrid_id', new_column_name='ground_id')
    op.alter_column('grounds_addresses', 'microgrid_id', new_column_name='ground_id')
    op.alter_column('ground_private', 'microgrid_id', new_column_name='ground_id')
    op.alter_column('sales_account', 'microgrid_id', new_column_name='ground_id')
    op.alter_column('sms_message', 'microgrid_id', new_column_name='ground_id')
    op.alter_column('transactions', 'microgrid_id', new_column_name='ground_id')
    op.alter_column('users_grounds', 'microgrid_id', new_column_name='ground_id')
    op.alter_column('user', 'microgrid_all_access', new_column_name='ground_all_access')


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.48 to 0.47."""
    raise SystemExit("Downgrading from 0.48 to 0.47 is not supported")
