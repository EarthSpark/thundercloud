# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""sms: merge tables.

Revision ID: 0.32
Revises: 0.31
Create Date: 2016-05-25 16:22:58.981848

"""

from builtins import str

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from sparkmeter.database.columns import JSONString
from sparkmeter.misc.jsonutils import json_dumps
from sparkmeter.misc.uuidutils import as_uuid

revision = "0.32"
down_revision = "0.31"


def upgrade():
    """Upgrade the database schema from 0.31 to 0.32."""
    op.create_table(
        "sms_config",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("last_update", sa.DateTime(), nullable=True),
        sa.Column("needs_sync", sa.Boolean(), nullable=True),
        sa.Column("last_sync", sa.DateTime(), nullable=True),
        sa.Column("alerts", JSONString(), nullable=True),
        sa.Column("commands", JSONString(), nullable=True),
        sa.Column("messages", JSONString(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("sms_message", sa.Column("config_event_type", sa.String(), nullable=True))
    op.add_column("sms_message", sa.Column("config_command_code", sa.String(), nullable=True))
    op.add_column("sms_message", sa.Column("config_message_type", sa.String(), nullable=True))

    alerts = {}
    commands = {}
    messages = {}

    conn = op.get_bind()
    for result in conn.execute("SELECT id, code, active, template FROM sms_config_command;"):
        commands[result.code] = dict(
            code=result.code, id=str(result.id), active=result.active, template=result.template
        )
        stmt = sa.sql.text(
            "UPDATE sms_message SET config_command_code = :code WHERE sms_message.config_command_id = :id;"
        )
        conn.execute(
            stmt,
            code=result.code,
            id=str(result.id),
        )

    for result in conn.execute("SELECT id, event_type, active, template FROM sms_config_alert;"):
        alerts[result.event_type] = dict(
            event_type=result.event_type, id=str(result.id), active=result.active, template=result.template
        )
        stmt = sa.sql.text(
            "UPDATE sms_message SET config_event_type = :event_type WHERE sms_message.config_alert_id = :id;"
        )
        conn.execute(
            stmt,
            event_type=result.event_type,
            id=str(result.id),
        )

    for result in conn.execute("SELECT id, message_type, active, template FROM sms_config_message;"):
        messages[result.message_type] = dict(
            message_type=result.message_type,
            id=str(result.id),
            active=result.active,
            template=result.template,
        )
        stmt = sa.sql.text(
            "UPDATE sms_message "
            "SET config_message_type = :message_type "
            "WHERE sms_message.config_message_id = :id;"
        )
        conn.execute(
            stmt,
            message_type=result.message_type,
            id=str(result.id),
        )

    query = sa.sql.text("""
    INSERT INTO sms_config VALUES (
    :id, :last_update, :needs_sync, :last_sync,
    :alerts, :commands, :messages)
    """)
    values = dict()
    values["id"] = as_uuid("migrated-sms-config-entries")
    values["last_update"] = None
    values["needs_sync"] = True
    values["last_sync"] = None
    values["alerts"] = json_dumps(alerts)
    values["commands"] = json_dumps(commands)
    values["messages"] = json_dumps(messages)
    conn.execute(query, **values)

    op.drop_column("sms_message", "config_alert_id")
    op.drop_column("sms_message", "config_command_id")
    op.drop_column("sms_message", "config_message_id")
    op.drop_table("sms_config_alert")
    op.drop_table("sms_config_command")
    op.drop_table("sms_config_message")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.32 to 0.31."""
