# -*- coding: utf-8 -*-
# Copyright © 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Table/ORM utilities."""

from sparkmeter.database.alchemy import sql


def get_table_by_name(tablename):
    """Get a table given a name."""
    return sql.metadata.tables[tablename]


def get_class_by_tablename(tablename):
    """Get an ORM class model given a table name."""
    # for c in list(ORMObject._decl_class_registry.values()):
    #     if hasattr(c, '__tablename__') and c.__tablename__ == tablename:
    #         return c

    # Use a simpler approach that works with modern SQLAlchemy
    # Import all the domain models to ensure they're registered
    from sparkmeter.config.configdomain import ConfigParameter
    from sparkmeter.dashboard.dashboarddomain import DashboardDailyTariffSummary
    from sparkmeter.event.eventdomain import Event, SMSConfig, SMSMessage
    from sparkmeter.ground.grounddomain import Ground, GroundPrivate, GroundsAddresses
    from sparkmeter.meter.meterdomain import (
        Address,
        Customer,
        Meter,
        MeterBilling,
        MeterConfig,
        MeterModels,
        MeterScalars,
        MetersTags,
        MeterSystemInfo,
        MeterTag,
        MeterView,
        SparkmacNode,
    )
    from sparkmeter.reading.readingdomain import Reading
    from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
    from sparkmeter.snapshot.snapshotdomain import Snapshot
    from sparkmeter.system.systemdomain import SystemState, SystemVersion
    from sparkmeter.tariff.tariffdomain import Tariff
    from sparkmeter.transaction.transactiondomain import (
        Transaction,
        TransactionSource,
        TransactionView,
        Wallet,
    )
    from sparkmeter.user.userdomain import Role, RolesUsers, SalesAccountsUsers, User, UsersGrounds

    # Create a mapping of table names to classes
    table_class_map = {
        "ground": Ground,
        "ground_private": GroundPrivate,
        "grounds_addresses": GroundsAddresses,
        "meter": Meter,
        "meter_config": MeterConfig,
        "meter_system_info": MeterSystemInfo,
        "customer": Customer,
        "meter_billing": MeterBilling,
        "meters_tags": MetersTags,
        "address": Address,
        "sparkmac_node": SparkmacNode,
        "meter_tag": MeterTag,
        "meter_scalars": MeterScalars,
        "meter_models": MeterModels,
        "user": User,
        "role": Role,
        "roles_users": RolesUsers,
        "sales_accounts_users": SalesAccountsUsers,
        "users_grounds": UsersGrounds,
        "sales_account": SalesAccount,
        "transactions": Transaction,
        "transaction_sources": TransactionSource,
        "transaction_view": TransactionView,
        "wallet": Wallet,
        "tariff": Tariff,
        "meter_view": MeterView,
        "event": Event,
        "sms_config": SMSConfig,
        "sms_message": SMSMessage,
        "snapshot": Snapshot,
        "config_parameter": ConfigParameter,
        "reading": Reading,
        "dashboard_daily_tariff_summary": DashboardDailyTariffSummary,
        "system_version": SystemVersion,
        "system_state": SystemState,
    }

    return table_class_map.get(tablename)
