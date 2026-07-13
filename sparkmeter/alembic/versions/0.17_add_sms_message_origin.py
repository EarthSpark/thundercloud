# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Add sms message origin.

Revision ID: 0.17
Revises: 0.16
Create Date: 2016-03-03 10:17:07.543296

"""

import sqlalchemy as sa
from alembic import op

from sparkmeter.database.types import UUIDType

revision = "0.17"
down_revision = "0.16"


def upgrade():
    """Upgrade the database schema from 0.16 to 0.17."""
    op.add_column("sms_message", sa.Column("origin", sa.String(), nullable=False, server_default="unknown"))
    op.add_column(
        "sms_message",
        sa.Column(
            "config_alert_id", UUIDType(binary=True), sa.ForeignKey("sms_config_alert.id"), nullable=True
        ),
    )
    op.add_column(
        "sms_message",
        sa.Column(
            "config_command_id", UUIDType(binary=True), sa.ForeignKey("sms_config_command.id"), nullable=True
        ),
    )
    op.add_column(
        "sms_message",
        sa.Column(
            "config_message_id", UUIDType(binary=True), sa.ForeignKey("sms_config_message.id"), nullable=True
        ),
    )


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.17 to 0.16."""
    op.drop_column("sms_message", "origin")
    op.drop_column("sms_message", "config_message_id")
    op.drop_column("sms_message", "config_alert_id")
    op.drop_column("sms_message", "config_command_id")
