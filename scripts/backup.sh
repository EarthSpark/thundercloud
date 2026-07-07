#!/bin/bash

echo "Backing up sparkmeter databases and settings"

# setup temp dir for the backups
TMPDIR=`mktemp -d -t sparkmeter_db_backup.XXXXXXXXXXXXXXX`
mkdir $TMPDIR/backup/

echo "Loading python config"
python manage.py bash_config > $TMPDIR/backup/config.sh

source $TMPDIR/backup/config.sh

echo "Backing up postgres database $POSTGRES_SETTINGS_DB"
#FIXME: include authentication, host, and port
pg_dump $POSTGRES_SETTINGS_DB > $TMPDIR/backup/sql

echo "Backing up custom app configs"
cp -rv instance $TMPDIR/backup/

echo "Compressing the backup"
BACKUP_FILE="sparkmeter_backup_`date +"%Y%m%d%H%M%S"`.tar.gz"
tar cv -C $TMPDIR/ backup | bzip2 -kv9 > $BACKUP_FILE

echo "Cleaning up temporary files"
rm -rf $TMPDIR

echo "Backed up system to $BACKUP_FILE"
