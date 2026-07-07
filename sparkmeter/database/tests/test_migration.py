# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Database migration unittests."""
import pytest
from freezegun import freeze_time
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.sql import select
from sqlalchemy.sql.ddl import CreateTable

from sparkmeter.config.configdomain import ConfigParameter
from sparkmeter.database.database import get_schema_tables
from sparkmeter.database.tests.databasetestbase import (MIGRATION_TEST_URI,
                                                        bootstrap_migration_database)
from sparkmeter.misc.jsonutils import json_dumps
from sparkmeter.tests.base import SparkMeterTestCaseBase


@pytest.fixture(scope="module")
def migration_session():
    """Run test fixture for this module."""
    with freeze_time("2010-01-01"):
        bootstrap_migration_database()
        engine = create_engine(MIGRATION_TEST_URI)
        connection = engine.connect()
        yield Session(bind=connection)
        connection.close()


class MigrationTest(SparkMeterTestCaseBase):

    """This test verifies that the state system in the current/latest
    schema is similar to what it was from the beginning.

    Since this is the latest version, we will be able to use our domain classes
    to query the system. This has to be updated to check for any state that is present
    in the old migration dump.
    """

    def test_tables(self, migration_session):
        ignore_values = [str(c.id) for c in migration_session.query(ConfigParameter)]
        for table in get_schema_tables():
            # Order by primary key columns to ensure deterministic results
            query = select(table)
            if table.primary_key:
                query = query.order_by(*table.primary_key.columns)
            res = migration_session.execute(query)
            objs = []
            for row in res:
                objs.append(dict(row._mapping))
            content = json_dumps(objs)
            table_ignore = []
            if table.name in ('sym_channel', 'sym_trigger', 'sym_router', 'sym_trigger_router'):
                # SymmetricDS-generated timestamps: filter only the value
                # (fixed-width lookbehind on the key) so the key/structure stay
                # asserted -> "create_time": "%% FILTERED BY UNITTEST %%".
                table_ignore = [
                    r'(?<="create_time": ")\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+',
                    r'(?<="last_update_time": ")\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+',
                ]
            if table.name == 'user':
                # fs_uniquifier is generated randomly by the migration. Match
                # only the value (fixed-width lookbehind on the key) so the
                # snapshot keeps the key and structure and filters just the
                # random hex: "fs_uniquifier": "%% FILTERED BY UNITTEST %%".
                table_ignore.append(r'(?<="fs_uniquifier": ")[a-f0-9]+')
            self.verify_json_content(content, variant=table.name,
                                     ignore_values=ignore_values, ignore_regexes=table_ignore)

            schema = str(CreateTable(table))
            schema = schema.replace('\n\n', '\n')
            schema = schema.replace('\t', ' ' * 4)
            schema = schema.replace(' \n', '\n')
            self.verify_file_content('sql', schema, variant=table.name)
