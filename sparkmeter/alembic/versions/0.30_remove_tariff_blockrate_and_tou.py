# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Remove Tariff blockrate and TOU.

Revision ID: 0.30
Revises: 0.29
Create Date: 2016-04-22 18:15:50.259696

"""

import logging
from builtins import str

import sqlalchemy as sa
from alembic import op

from sparkmeter.misc.jsonutils import json_dumps

revision = "0.30"
down_revision = "0.29"
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.29 to 0.30."""
    op.add_column("tariff", sa.Column("blockrates", sa.String(), nullable=True))
    op.add_column("tariff", sa.Column("tous", sa.String(), nullable=True))

    conn = op.get_bind()
    for (tariff_id,) in conn.execute("SELECT id FROM tariff"):
        blockrates = []
        for blockrate in conn.execute(
            sa.sql.text("SELECT upper, lower, value FROM tariff_block_rate WHERE tariff_id = :tariff_id"),
            tariff_id=str(tariff_id),
        ):
            blockrates.append(dict(lower=blockrate.lower, upper=blockrate.upper, value=blockrate.value))
        tous = []
        for tou in conn.execute(
            sa.sql.text('SELECT "start", "end", value FROM tariff_tou WHERE tariff_id = :tariff_id'),
            tariff_id=str(tariff_id),
        ):
            tous.append(
                dict(start=tou.start.strftime("%H:%M"), end=tou.end.strftime("%H:%M"), value=tou.value)
            )

        conn.execute(
            sa.sql.text("""UPDATE tariff
            SET blockrates = :blockrates, tous = :tous WHERE id = :tariff_id;"""),
            blockrates=json_dumps(blockrates),
            tous=json_dumps(tous),
            tariff_id=str(tariff_id),
        )
        logger.info(
            "Converted %d blockrates and %d tous for tariff %s " % (len(blockrates), len(tous), tariff_id)
        )

    op.drop_table("tariff_block_rate")
    op.drop_table("tariff_tou")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.30 to 0.29."""
    raise NotImplementedError("Downgrades are not supported")
