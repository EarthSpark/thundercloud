# -*- coding: utf-8 -*-
# Copyright (C) 2013-${create_date.year} SparkMeter, Inc.
# All Rights Reserved.
"""${message}.

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}

"""

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}


def upgrade():
    """Upgrade the database schema from ${down_revision} to ${up_revision}."""
    ${upgrades if upgrades else "pass"}


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from ${up_revision} to ${down_revision}."""
    ${downgrades if downgrades else "pass"}
    raise SystemExit("Downgrading from ${up_revision} to ${down_revision} not supported")
