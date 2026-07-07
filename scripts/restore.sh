#!/bin/bash

echo "Loading data from backup"

BACKUP_FILE="$1"

echo "Warning, this will erase everything in the current database and replace it with the backup"

while true; do
    read -p "Do you wish to continue?" yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) echo "Exiting. No restore performed"; exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

TMPDIR=`mktemp -d -t sparkmeter_db_backup.XXXXXXXXXXXXXXX`

echo "Extracting backup"
tar -xvvf $BACKUP_FILE -C $TMPDIR

# load the settings defined from the backup site and restore to there
# FIXME: add ability to either specify custom databases, or to use my local config instead
echo "Loading remote database settings for restore"
source $TMPDIR/backup/config.sh

echo "Restoring postgres database $POSTGRES_SETTINGS_DB"
# FIXME: check if a db already exists in this location, warn if it does
# wipe and restore the postgres db
sudo -u postgres dropdb $POSTGRES_SETTINGS_DB
sudo -u postgres createdb $POSTGRES_SETTINGS_DB
sudo -u postgres psql $POSTGRES_SETTINGS_DB < $TMPDIR/backup/sql

echo "Ignoring the remote instance settings"
# FIXME: what should we do with the instance settings, maybe add a param to optionally use them

echo "Cleaning up temporary files"
rm -rf $TMPDIR

echo "Restore complete"
