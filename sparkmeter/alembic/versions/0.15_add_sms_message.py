# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Add SMS Message.

Revision ID: 0.15
Revises: 0.14
Create Date: 2016-02-12 11:07:07.100957

"""
import datetime

import sqlalchemy as sa
from alembic import op

from sparkmeter.database.types import UUIDType
from sparkmeter.misc.uuidutils import as_uuid

revision = '0.15'
down_revision = '0.14'


def upgrade():
    """Upgrade the database schema from 0.14 to 0.15."""
    op.create_table(
        'sms_message',
        sa.Column('id', UUIDType(binary=True), nullable=False),
        sa.Column('last_update', sa.DateTime(), nullable=True),
        sa.Column('needs_sync', sa.Boolean(), nullable=True),
        sa.Column('last_sync', sa.DateTime(), nullable=True),
        sa.Column('external_id', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('phone_number', sa.String(), nullable=False),
        sa.Column('text', sa.String(), nullable=False),
        sa.Column('direction', sa.String(), nullable=False),
        sa.Column('event_id', UUIDType(binary=True), sa.ForeignKey('event.id'), nullable=True),
        sa.Column('in_reply_to_id', UUIDType(binary=True), sa.ForeignKey('sms_message.id'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.add_column('event', sa.Column('processed', sa.Boolean(), nullable=False,
                                     server_default=sa.false()))
    op.create_unique_constraint('sms_message_external_id_unique', 'sms_message', ['external_id'])
    op.add_column('sms_message', sa.Column('processed', sa.Boolean(), nullable=False,
                                           server_default=sa.false()))


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.15 to 0.14."""
    op.drop_constraint(u'sms_message_external_id_unique', 'sms_message')
    op.drop_table('sms_message')
    op.drop_column('event', 'processed')


def test_defaults():
    conn = op.get_bind()
    incoming_id = as_uuid('incoming-sms-message')
    conn.execute(
        sa.sql.text("""INSERT INTO "sms_message" VALUES (
            :id, :last_update, :needs_sync, :last_sync, :external_id, :timestamp,
            :phone_number, :text, :direction, :event_id, :in_reply_to_id)"""),
        id=incoming_id,
        last_update=None, needs_sync=True, last_sync=None,
        external_id='external-id',
        timestamp=datetime.datetime(2016, 1, 1),
        phone_number='+15555550101',
        text='Hello!',
        direction='in',
        event_id=None,
        in_reply_to_id=None,
    )
