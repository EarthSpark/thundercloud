# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""address: Add a microgrid reference.

Revision ID: 0.27
Revises: 0.26
Create Date: 2016-04-22 17:40:22.751466

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from sparkmeter.misc.uuidutils import as_uuid

revision = "0.27"
down_revision = "0.26"
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.26 to 0.27."""
    op.create_table(
        "microgrids_addresses",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("last_update", sa.DateTime(), nullable=True),
        sa.Column("needs_sync", sa.Boolean(), nullable=True),
        sa.Column("last_sync", sa.DateTime(), nullable=True),
        sa.Column("microgrid_id", postgresql.UUID(), nullable=True),
        sa.Column("address_id", postgresql.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["microgrid_id"],
            ["microgrid.id"],
        ),
        sa.ForeignKeyConstraint(
            ["address_id"],
            ["address.id"],
        ),
        sa.UniqueConstraint(
            "microgrid_id", "address_id", name="microgrids_addresses_microgrid_address_unique"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("address", sa.Column("microgrid_id", postgresql.UUID(), nullable=True))

    # Microgrid addresses
    conn = op.get_bind()
    results = conn.execute("""
    SELECT microgrid.id AS microgrid_id, address.id AS address_id
      FROM microgrid, address
    WHERE  microgrid.address_id = address.id;""")
    for result in results:
        query = sa.sql.text("""
        INSERT INTO microgrids_addresses VALUES (
        :id, :last_update, :needs_sync, :last_sync,
        :microgrid_id, :address_id)
        """)
        values = dict(result._mapping)
        values["id"] = as_uuid(values["microgrid_id"], values["address_id"])
        values["last_update"] = None
        values["needs_sync"] = True
        values["last_sync"] = None
        conn.execute(query, **values)
    logger.info("Inserted %r microgrids_addresses" % (results.rowcount,))
    results = conn.execute("""
    UPDATE address
       SET microgrid_id = microgrids_addresses.microgrid_id
      FROM microgrids_addresses
    WHERE  microgrids_addresses.address_id = address.id;""")
    logger.info("Updated %r addresses (microgrid)" % (results.rowcount,))
    op.drop_constraint("microgrid_address_id_fkey", "microgrid", type_="foreignkey")
    op.drop_column("microgrid", "address_id")
    op.alter_column("microgrids_addresses", "address_id", nullable=False)
    op.alter_column("microgrids_addresses", "microgrid_id", nullable=False)

    # Meter addresses
    results = conn.execute("""
    UPDATE address SET microgrid_id = meter.microgrid_id
      FROM meter
    WHERE  meter.address_id = address.id;""")
    logger.info("Updated %r addresses (meter)" % (results.rowcount,))

    op.alter_column("address", "microgrid_id", nullable=False)
    op.create_foreign_key("address_microgrid_id_fkey", "address", "microgrid", ["microgrid_id"], ["id"])


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.27 to 0.26."""
    # add address_id column to microgrid
    op.add_column("microgrid", sa.Column("address_id", postgresql.UUID(), nullable=True))

    # update all microgrid address_id via microgrids_addresses
    conn = op.get_bind()
    results = conn.execute("""
    UPDATE microgrid SET address_id = microgrids_addresses.address_id
      FROM address, microgrids_addresses
    WHERE  microgrids_addresses.address_id = address.id;""")
    logger.info("Updated %r microgrid addresses" % (results.rowcount,))

    # add foreign key and change nullable=False
    op.alter_column("microgrid", "address_id", nullable=False)
    op.create_foreign_key("microgrid_address_id_fkey", "microgrid", "address", ["address_id"], ["id"])

    # remove microgrids_addresses table and foreign keys
    op.drop_table("microgrids_addresses")

    # remove address microgrid_id reference
    op.drop_constraint("address_microgrid_id_fkey", "address", type_="foreignkey")
    op.drop_column("address", "microgrid_id")
