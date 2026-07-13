# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Remove old sync.

Revision ID: 0.38
Revises: 0.37
Create Date: 2016-08-19 14:08:40.916632

"""

from alembic import op

from sparkmeter.database.database import load_schema

revision = "0.38"
down_revision = "0.37"


def upgrade():
    """Upgrade the database schema from 0.37 to 0.38."""
    op.drop_table("sync_conflict")
    op.drop_table("sync_operation")
    op.drop_table("sync_collection")

    op.drop_index("reading_needs_sync_true", table_name="reading")
    op.drop_index("transaction_needs_sync_true", table_name="transactions")

    op.drop_column("address", "last_update")
    op.drop_column("address", "needs_sync")
    op.drop_column("address", "last_sync")
    op.drop_column("customer", "last_update")
    op.drop_column("customer", "needs_sync")
    op.drop_column("customer", "last_sync")
    op.drop_column("dashboard_daily_tariff_summary", "last_update")
    op.drop_column("dashboard_daily_tariff_summary", "needs_sync")
    op.drop_column("dashboard_daily_tariff_summary", "last_sync")
    op.drop_column("event", "last_update")
    op.drop_column("event", "needs_sync")
    op.drop_column("event", "last_sync")
    op.drop_column("meter", "last_update")
    op.drop_column("meter", "needs_sync")
    op.drop_column("meter", "last_sync")
    op.drop_column("meter_billing", "last_update")
    op.drop_column("meter_billing", "needs_sync")
    op.drop_column("meter_billing", "last_sync")
    op.drop_column("meter_config", "last_update")
    op.drop_column("meter_config", "needs_sync")
    op.drop_column("meter_config", "last_sync")
    op.drop_column("meter_system_info", "last_update")
    op.drop_column("meter_system_info", "needs_sync")
    op.drop_column("meter_system_info", "last_sync")
    op.drop_column("meter_tag", "last_sync")
    op.drop_column("meter_tag", "needs_sync")
    op.drop_column("meter_tag", "last_update")
    op.drop_column("meters_tags", "last_sync")
    op.drop_column("meters_tags", "needs_sync")
    op.drop_column("meters_tags", "last_update")
    op.drop_column("microgrid", "last_update")
    op.drop_column("microgrid", "needs_sync")
    op.drop_column("microgrid", "last_sync")
    op.drop_column("microgrids_addresses", "last_sync")
    op.drop_column("microgrids_addresses", "needs_sync")
    op.drop_column("microgrids_addresses", "last_update")
    op.drop_column("reading", "last_update")
    op.drop_column("reading", "needs_sync")
    op.drop_column("reading", "last_sync")
    op.drop_column("role", "last_sync")
    op.drop_column("role", "needs_sync")
    op.drop_column("role", "last_update")
    op.drop_column("roles_users", "last_update")
    op.drop_column("roles_users", "needs_sync")
    op.drop_column("roles_users", "last_sync")
    op.drop_column("sales_account", "last_update")
    op.drop_column("sales_account", "needs_sync")
    op.drop_column("sales_account", "last_sync")
    op.drop_column("sales_accounts_users", "last_sync")
    op.drop_column("sales_accounts_users", "needs_sync")
    op.drop_column("sales_accounts_users", "last_update")
    op.drop_column("sms_config", "last_sync")
    op.drop_column("sms_config", "needs_sync")
    op.drop_column("sms_config", "last_update")
    op.drop_column("sms_message", "last_sync")
    op.drop_column("sms_message", "needs_sync")
    op.drop_column("sms_message", "last_update")
    op.drop_column("sparkmac_node", "last_update")
    op.drop_column("sparkmac_node", "needs_sync")
    op.drop_column("sparkmac_node", "last_sync")
    op.drop_column("tariff", "last_update")
    op.drop_column("tariff", "needs_sync")
    op.drop_column("tariff", "last_sync")
    op.drop_column("transaction_sources", "last_sync")
    op.drop_column("transaction_sources", "needs_sync")
    op.drop_column("transaction_sources", "last_update")
    op.drop_column("transactions", "last_sync")
    op.drop_column("transactions", "needs_sync")
    op.drop_column("transactions", "last_update")
    op.drop_column("user", "last_sync")
    op.drop_column("user", "needs_sync")
    op.drop_column("user", "last_update")
    op.drop_column("wallet", "last_sync")
    op.drop_column("wallet", "needs_sync")
    op.drop_column("wallet", "last_update")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.38 to 0.37."""
    raise SystemExit("Downgrading from 0.38 to 0.37 not supported")


def test_defaults():
    conn = op.get_bind()
    load_schema(conn, "symmetricds.sql")
    conn.execute("""
INSERT INTO sym_node_group VALUES ('cloud-group', 'A ThunderCloud node',
'2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_node_group VALUES ('ground-group', 'A Groundbolt node',
'2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');

INSERT INTO sym_node_group_link VALUES ('ground-group', 'cloud-group', 'P',
1, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_node_group_link VALUES ('cloud-group', 'ground-group', 'W',
1, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');

INSERT INTO sym_conflict VALUES ('ground-event-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'event', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-sms_message-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'sms_message', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-event-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'event', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-sms_message-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'sms_message', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-reading-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'reading', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-wallet-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'wallet', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-wallet-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'wallet', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-transaction_sources-conflict',
'ground-group', 'cloud-group', NULL, NULL, NULL, 'transaction_sources', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-transactions-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'transactions', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-transaction_sources-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'transaction_sources', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-transactions-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'transactions', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-sparkmac_node-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'sparkmac_node', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-customer-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'customer', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-meter_billing-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'meter_billing', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-meter_system_info-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'meter_system_info', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-meter_config-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'meter_config', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-meters_tags-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'meters_tags', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-meter-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'meter', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-sparkmac_node-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'sparkmac_node', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-customer-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'customer', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-meter_billing-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'meter_billing', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-meter_system_info-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'meter_system_info', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-meter_config-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'meter_config', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-meters_tags-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'meters_tags', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-meter-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'meter', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-address-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'address', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-grounds_addresses-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'grounds_addresses', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-address-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'address', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-grounds_addresses-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'grounds_addresses', 'USE_CHANGED_DATA', NULL,
 'FALLBACK','REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-tariff-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'tariff', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-tariff-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'tariff', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-ground_private-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'ground_private', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-ground-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'ground', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-ground_private-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'ground_private', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-ground-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'ground', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-dashboard_daily_tariff_summary-conflict',
'ground-group', 'cloud-group', NULL, NULL, NULL, 'dashboard_daily_tariff_summary',
'USE_CHANGED_DATA', NULL, 'FALLBACK','REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488',
NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-dashboard_daily_tariff_summary-conflict',
'cloud-group', 'ground-group', NULL, NULL, NULL, 'dashboard_daily_tariff_summary',
'USE_CHANGED_DATA', NULL, 'IGNORE','REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488',
NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-sales_account-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'sales_account', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-sales_account-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'sales_account', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-roles_users-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'roles_users', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-role-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'role', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-sales_accounts_users-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'sales_accounts_users', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-users_grounds-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'users_grounds', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('ground-user-conflict', 'ground-group',
'cloud-group', NULL, NULL, NULL, 'user', 'USE_CHANGED_DATA', NULL, 'IGNORE',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-roles_users-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'roles_users', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-role-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'role', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-sales_accounts_users-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'sales_accounts_users', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-users_grounds-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'users_grounds', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
INSERT INTO sym_conflict VALUES ('cloud-user-conflict', 'cloud-group',
'ground-group', NULL, NULL, NULL, 'user', 'USE_CHANGED_DATA', NULL, 'FALLBACK',
'REMAINING_ROWS', 1, 0, '2018-01-25 22:30:18.0488', NULL, '2018-01-25 22:30:18.0488');
""")
