# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Remove meter wallet references.

Revision ID: 0.19
Revises: 0.18
Create Date: 2016-03-29 11:56:41.783598

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0.19"
down_revision = "0.18"
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.18 to 0.19."""
    op.drop_constraint("meter_debt_wallet_id_fkey", "meter", type_="foreignkey")
    op.drop_constraint("meter_plan_wallet_id_fkey", "meter", type_="foreignkey")
    op.drop_constraint("meter_credit_wallet_id_fkey", "meter", type_="foreignkey")
    op.drop_column("meter", "debt_wallet_id")
    op.drop_column("meter", "plan_wallet_id")
    op.drop_column("meter", "credit_wallet_id")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.19 to 0.18."""
    op.add_column(
        "meter", sa.Column("credit_wallet_id", postgresql.UUID(), autoincrement=False, nullable=True)
    )
    op.add_column("meter", sa.Column("plan_wallet_id", postgresql.UUID(), autoincrement=False, nullable=True))
    op.add_column("meter", sa.Column("debt_wallet_id", postgresql.UUID(), autoincrement=False, nullable=True))
    conn = op.get_bind()
    for wallet_type in ["credit", "debt", "plan"]:
        res = conn.execute(
            """
        UPDATE meter SET %(wallet_type)s_wallet_id = wallet.id
        FROM wallet
        WHERE wallet.meter_id = meter.id AND wallet_type = '%(wallet_type)s'"""
            % (dict(wallet_type=wallet_type))
        )
        logger.info(
            "Set %s wallet of %r meters"
            % (
                wallet_type,
                res.rowcount,
            )
        )
        op.alter_column("meter", "%s_wallet_id" % (wallet_type,), nullable=False)

    op.create_foreign_key("meter_credit_wallet_id_fkey", "meter", "wallet", ["credit_wallet_id"], ["id"])
    op.create_foreign_key("meter_plan_wallet_id_fkey", "meter", "wallet", ["plan_wallet_id"], ["id"])
    op.create_foreign_key("meter_debt_wallet_id_fkey", "meter", "wallet", ["debt_wallet_id"], ["id"])
