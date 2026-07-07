# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Database manage commands.py."""
import logging

import click
from flask.cli import with_appcontext
from sqlalchemy import text
from zope.component import getUtility

from sparkmeter.alembic.migrationhelper import get_latest_patch
from sparkmeter.config.configdict import config
from sparkmeter.database.database import database_has_constraint
from sparkmeter.interface import IApplication

logger = logging.getLogger(__name__)

database = click.Group('database', help='Database management commands.')


@database.command('reset')
@click.option('--empty', is_flag=True, help='Empty the database')
@click.option('--force', is_flag=True, help='Force reset')
@click.option('--keep-schema', is_flag=True, help='Keep the schema')
@with_appcontext
def reset(empty=False, force=False, keep_schema=False):
    """Reset all databases."""
    from sparkmeter.controller import resetdb
    app = getUtility(IApplication)
    app.setup_databases()
    resetdb(empty=empty, force=force, resetschema=not keep_schema)


@database.command('reset-demo')
@click.option('--force', is_flag=True, help='Force reset')
@click.option('--name', default=None, help='Ground name')
@click.option('--serial', default=None, help='Ground serial')
@click.option('--sparkcloud-api-key', default=None, help='SparkCloud API key')
@with_appcontext
def reset_demo(force=False, name=None, serial=None, sparkcloud_api_key=None):
    """Reset the demo system."""
    from sparkmeter.controller import resetdb
    from sparkmeter.database.alchemy import sql
    from sparkmeter.database.demodata import DemoExamples

    if not force and not config.get('ENABLE_DEMO_RESET', False):
        return "ENABLE_DEMO_RESET = False, set to True (venv/var/sparkmeter.app-instance/settings_custom.py)"
    app = getUtility(IApplication)
    app.setup_databases()
    resetdb(force=True, resetschema=True)
    data = DemoExamples(sql.session)
    data.create_ground(
        name=name,
        serial=serial,
        secret_key=sparkcloud_api_key)
    data.create_all()
    sql.session.commit()


@database.command('init-sync')
@click.option('--external-id', default=None, help='External node ID')
@with_appcontext
def init_sync(external_id=None):
    """Initialize a cloud node for syncing."""
    if external_id is None:
        external_id = config['SERIAL']
    app = getUtility(IApplication)
    app.setup_databases()

    from sparkmeter.database.sync import create_default_policy
    create_default_policy(app.sql.session, external_id=external_id)


def force_table_reload(table_name, sym_channel, dest_node_id):
    """Force SymmetricDS to reload data from a table on this database to the other."""
    from sparkmeter.database.alchemy import sql
    from sparkmeter.database.sync import force_table_reload
    app = getUtility(IApplication)
    app.setup_databases()
    force_table_reload(table_name, dest_node_id, sym_channel, sql.session)
    sql.session.commit()
    logger.info("Forced resync of table '%s' to node '%s'.", table_name, dest_node_id)


def clean_tables(force=False, keep_ground=None, keep_user=None):
    """Remove data from database tables."""
    if not force:
        logger.warning("This is a dangerous command to run, pass in --force "
                       "if you know what you are doing")
        return 1

    from sparkmeter.database.alchemy import sql
    from sparkmeter.event.eventdomain import Event, SMSMessage
    from sparkmeter.ground.grounddomain import Ground
    from sparkmeter.meter.meterdomain import Meter
    from sparkmeter.user.userdomain import User

    app = getUtility(IApplication)
    app.setup_databases()

    for user in User.query.all():
        if user.email != keep_user:
            user.remove()
    for meter in Meter.query.all():
        meter.remove()
    for message in SMSMessage.query.all():
        sql.session.delete(message)
    for event in Event.query.all():
        sql.session.delete(event)

    for ground in Ground.query.all():
        if ground.serial != keep_ground:
            ground.remove()

    sql.session.commit()
    logger.info('Cleaned up database tables')


def cloud_start_merge():
    """
    Start a multigrid merge.

    This will disable triggers, conflicts and cyclic foreign key references.

    cloud-start-merge should run when you start the process of
    merging a single grid cloud into a multigrid cloud.
    """
    from sparkmeter.database.alchemy import sql
    from sparkmeter.database.symmetricdsdomain import Trigger

    app = getUtility(IApplication)
    app.setup_databases()

    # Disable sync on incoming
    cloud_triggers = Trigger.query.filter(Trigger.trigger_id.like('cloud%'))
    cloud_triggers.update(
        dict(sync_on_incoming_batch=False),
        synchronize_session='fetch')

    # Cyclic/Self-referencing tables.
    # Since we are importing the whole transactions table in an unspecified order, we need
    # to disable the self-referencing/cycling reference_id foreign key, we'll add it back
    # after merging
    sql.session.execute(text(
        "ALTER TABLE transactions "
        "DROP CONSTRAINT IF EXISTS transactions_reference_id_fkey;"))
    sql.session.execute(text(
        "ALTER TABLE sms_message "
        "DROP CONSTRAINT IF EXISTS sms_message_in_reply_to_id_fkey;"))

    # Disable conflicts, which prevents merging of similar data
    sql.session.execute(text("DELETE FROM sym_conflict;"))
    sql.session.commit()


def cloud_finish_merge():
    """
    Finish a multigrid merge.

    cloud-finish-merge should run when you start the process of
    merging a single grid cloud into a multigrid cloud.
    """
    from sparkmeter.database.alchemy import sql
    from sparkmeter.database.symmetricdsdomain import Trigger
    from sparkmeter.database.sync import create_default_policy
    from sparkmeter.ground.grounddomain import Ground
    from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
    from sparkmeter.user.userdomain import User

    app = getUtility(IApplication)
    app.setup_databases()

    # Recreate sym conflicts
    create_default_policy(app.sql.session, external_id='cloud')

    # Re-enable sync on incoming
    cloud_triggers = Trigger.query.filter(Trigger.trigger_id.like('cloud%'))
    cloud_triggers.update(
        dict(sync_on_incoming_batch=True),
        synchronize_session='fetch')

    # Add back cycling references
    engine = sql.engine
    if not database_has_constraint(engine, 'transactions_reference_id_fkey'):
        sql.session.execute(text(
            "ALTER TABLE transactions "
            "ADD CONSTRAINT transactions_reference_id_fkey "
            "FOREIGN KEY (reference_id) "
            "REFERENCES transactions (id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION;"))

    if not database_has_constraint(engine, 'sms_message_in_reply_to_id_fkey'):
        sql.session.execute(text(
            "ALTER TABLE sms_message "
            "ADD CONSTRAINT sms_message_in_reply_to_id_fkey "
            "FOREIGN KEY (in_reply_to_id) "
            "REFERENCES sms_message (id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION;"))

    # Fix up users with access to all sales accounts and grounds
    all_accounts = SalesAccount.get_all()
    for user in User.get_with_all_account_access():
        user.accounts = all_accounts
    all_grounds = Ground.get_all()
    for user in User.get_with_all_ground_access():
        user.grounds = all_grounds

    sql.session.commit()


@database.command('upgrade')
@click.argument('revision')
@with_appcontext
def upgrade(revision):
    """Upgrade the alembic schema."""
    from sparkmeter.alembic.migrationhelper import upgrade_database

    app = getUtility(IApplication)
    app.setup_databases()

    upgrade_database(app.sql.engine, revision)
    logger.info('Finished upgrading to %s', revision)


@database.command('downgrade')
@click.argument('revision')
@with_appcontext
def downgrade(revision):
    """Downgrade the alembic schema."""
    from sparkmeter.alembic.migrationhelper import downgrade_database

    app = getUtility(IApplication)
    app.setup_databases()

    downgrade_database(app.sql.engine, revision)
    logger.info('Finished downgrading to %s', revision)


@database.command('new-revision')
@click.argument('message')
@with_appcontext
def new_revision(message):
    """Create a new alembic revision."""
    from sparkmeter.alembic.migrationhelper import create_migration

    app = getUtility(IApplication)
    app.setup_databases()

    patch = get_latest_patch()
    sql_file = 'sparkmeter/database/schemas/{}.sql'.format(patch)
    create_migration(
        app.sql.engine,
        message, sql_file,
        version_num=patch)


# Backwards-compatible top-level aliases for old Flask-Script commands
initdb = click.Command('initdb', callback=reset.callback,
                       help='Alias for "database reset".',
                       params=reset.params,
                       deprecated=True)
resetdb = click.Command('resetdb', callback=reset.callback,
                        help='Alias for "database reset".',
                        params=reset.params,
                        deprecated=True)
demo = click.Command('demo', callback=reset_demo.callback,
                     help='Alias for "database reset-demo".',
                     params=reset_demo.params,
                     deprecated=True)
