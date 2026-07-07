# Copyright (C) 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""adding serial to meter.

Revision ID: 0.07
Revises: 0.06
Create Date: 2015-11-30 13:12:09.399953

"""

import sqlalchemy as sa
from alembic import op

revision = '0.07'
down_revision = '0.06'


def upgrade():
    """Upgrade the database schema from 0.06 to 0.07."""
    # add the field, but keep it nullable until we generate data for this field
    op.add_column('meter', sa.Column('serial', sa.String(), nullable=True))

    # generate serials for existing meters using their code. below 1508 are SM15R, above are SM20R
    conn = op.get_bind()
    conn.execute(
        """UPDATE meter SET "serial" = 'SM15R-01-'||upper(lpad(to_hex(code), 8, '0')) WHERE code <= 1508;"""
    )
    conn.execute(
        """UPDATE meter SET "serial" = 'SM20R-01-'||upper(lpad(to_hex(code), 8, '0')) WHERE code > 1508;"""
    )

    # make field not nullable
    op.alter_column('meter', 'serial', existing_type=sa.String(), nullable=False)

    # make the field unique
    op.create_unique_constraint('meter_serial_unique', 'meter', ['serial'])

    # make the check constraint on the formatting
    op.create_check_constraint("ck_meter_serial_format", "meter", r"serial ~* '^[\dA-Z]+-\d{2}-[\dA-F]{8}$'")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.07 to 0.06."""
    op.drop_column('meter', 'serial')
