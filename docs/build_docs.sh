#!/bin/bash

export SPARKMETER_TESTING=1

OUTPUT_PATH=/tmp/sparkmeter-test
POSTGRES_DB_PATH=$OUTPUT_PATH/postgres_db

POSTGRES_PORT=`grep SQLALCHEMY_DATABASE_PORT\ = ../sparkmeter/tests/settings.py| awk '{print $3}'`


rm -rf $OUTPUT_PATH
mkdir -p $OUTPUT_PATH

function log() {
    echo "$@" | tee -a $OUTPUT_PATH/test.log
}

function exists() {
    EXISTS=$(command -v $1)
    if [ -z "$EXISTS" ]; then
        log "$1 not found in \$PATH"
        exit 1
    fi
}

exists initdb
exists createdb
exists postgres
exists pg_ctl

if [ "z" = "z$POSTGRES_PORT" ]; then
    log "POSTGRES_PORT must be set"
    exit 1
fi


if [ ! -d "$POSTGRES_DB_PATH" ]; then
    # create test db path
    log "creating db at $POSTGRES_DB_PATH"
    initdb -D $POSTGRES_DB_PATH
fi

# run postgres on test port
[[ $(postgres --version) =~ ([0-9][.][0-9.]*) ]] && version="${BASH_REMATCH[1]}"
if ! awk -v ver="$version" 'BEGIN { if (ver < 9.3) exit 1; }'; then
    # below version 9.3
    postgres -D $POSTGRES_DB_PATH -p $POSTGRES_PORT --unix_socket_directory=/tmp  2>&1 &
else
    # version 9.3 and above
    postgres -D $POSTGRES_DB_PATH -p $POSTGRES_PORT --unix_socket_directories=/tmp  2>&1 &
fi

POSTGRES_PID=$!
log "postgres pid is $POSTGRES_PID (waiting on localhost:$POSTGRES_PORT)"


function checkport {
    nc -z -w1 localhost $1 &>/dev/null
    # If failure, sleep 1s. This turns our checkport() loop below into
    # a roughly 30s timeout.
    ret=$?
    if [ $ret ]; then
        sleep 1
    fi

    return $ret
}

function checkpostgres {
    pg_ctl status -D $1 &>/dev/null
    # If failure, sleep 1s. This turns our checkpostgres() loop below into
    # a roughly 30s timeout.
    ret=$?
    if [ $ret ]; then
        sleep 1
    fi

    return $ret
}

tries=10
while ! checkpostgres $POSTGRES_DB_PATH; do
    tries=$(($tries-1))
    if [ $tries -lt 0 ]; then
        echo "Timed out waiting for postgres"
        exit 1
    fi
done

# create the db once postgres is started
createdb -h localhost -p $POSTGRES_PORT test

function shutdown() {
    log "Killing postgres"
    kill $POSTGRES_PID 2> /dev/null
}

# trap C-c etc and kill dependent processes

trap shutdown SIGHUP SIGINT SIGTERM

make html;
ret=$?

shutdown

log "Exiting with return code $ret"
exit $ret
