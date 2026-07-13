# Copyright (C) 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Add sms tables.

Revision ID: 0.13
Revises: 0.12
Create Date: 2016-01-25 10:51:40.787861

"""

from builtins import str

import sqlalchemy as sa
from alembic import op

from sparkmeter.database.types import UUIDType
from sparkmeter.misc.uuidutils import as_uuid

revision = "0.13"
down_revision = "0.12"


def upgrade():
    """Upgrade the database schema from 0.12 to 0.13."""
    op.create_table(
        "sms_config_message",
        sa.Column("id", UUIDType(binary=True), nullable=False),
        sa.Column("last_update", sa.DateTime(), nullable=True),
        sa.Column("needs_sync", sa.Boolean(), nullable=True),
        sa.Column("last_sync", sa.DateTime(), nullable=True),
        sa.Column("message_type", sa.String(), nullable=False),
        sa.Column("template", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_type", name="sms_config_message_message_type_unique"),
    )
    op.create_table(
        "sms_config_alert",
        sa.Column("id", UUIDType(binary=True), nullable=False),
        sa.Column("last_update", sa.DateTime(), nullable=True),
        sa.Column("needs_sync", sa.Boolean(), nullable=True),
        sa.Column("last_sync", sa.DateTime(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("template", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_type", name="sms_config_alert_event_type_unique"),
    )
    op.create_table(
        "sms_config_command",
        sa.Column("id", UUIDType(binary=True), nullable=False),
        sa.Column("last_update", sa.DateTime(), nullable=True),
        sa.Column("needs_sync", sa.Boolean(), nullable=True),
        sa.Column("last_sync", sa.DateTime(), nullable=True),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("template", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("code = upper(code)", name="sms_config_command_code_upper"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="sms_config_command_code_unique"),
    )

    conn = op.get_bind()

    from sparkmeter.event.eventdomain import SMSConfigCommand

    for code, template in list(SMSConfigCommand.DEFAULT_COMMANDS.items()):
        query = sa.sql.text(
            "INSERT INTO sms_config_command "
            "(id, code, template, active) "
            "VALUES (:id, :code, :template, :active);"
        )
        conn.execute(
            query,
            id=as_uuid("migrated-sms-config-command-" + code),
            code=code,
            template=str(template),
            active=True,
        )

    from sparkmeter.event.eventdomain import SMSConfigMessage

    for message_type, mti in list(SMSConfigMessage.messages.items()):
        query = sa.sql.text(
            "INSERT INTO sms_config_message "
            "(id, message_type, template, active) "
            "VALUES (:id, :message_type, :template, :active);"
        )
        conn.execute(
            query,
            id=as_uuid("migrated-sms-config-message-" + message_type),
            message_type=message_type,
            template=str(mti.default),
            active=True,
        )


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.13 to 0.12."""
    op.drop_table("sms_config_command")
    op.drop_table("sms_config_alert")
    op.drop_table("sms_config_message")
