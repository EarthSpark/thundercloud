# Copyright (C) 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""adding acct_plan to readings.

Revision ID: 0.02
Revises: 0.01
Create Date: 2015-08-21 16:07:36.271851

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0.02"
down_revision = "0.01"


def upgrade():  # pragma: nocoverage
    """Upgrade the database schema from 0.01 to 0.02."""
    op.add_column("reading", sa.Column("acct_plan", sa.Float(), nullable=True))


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.02 to 0.01."""
    op.drop_column("reading", "acct_plan")
