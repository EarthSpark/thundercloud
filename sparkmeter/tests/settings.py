# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Settings to override normal settings when running tests."""

import os

# Flask
TESTING = True
SERVER_NAME = "localhost"

# Flask-Security
LOGIN_DISABLED = True
CSRF_ENABLED = False
SECURITY_PASSWORD_SALT = "test-salt-not-secret"

# WTForms
WTF_CSRF_ENABLED = False

# SQLAlchemy
SQL_DATABASE_NAME = "test"
SQLALCHEMY_DATABASE_URI = "postgresql://localhost:%s/%s" % (os.environ.get("PGPORT", 5432), SQL_DATABASE_NAME)
# SQLALCHEMY_ECHO = True

# Sentry
SENTRY_DSN = None

# Uncomment and set a real DSN to log errors to a Sentry project.
# SENTRY_DSN = 'https://<public_key>:<secret_key>@sentry.io/<project_id>'

# App defaults
API_ENDPOINT = "https://testsite.sparkmeter.cloud/api/v0"
DEFAULT_PHONE_COUNTRY_CODE = "1"
HEROKU = True
SERIAL = "groundserial1"
SECRET_KEY = "secretkey"

# S3 History
S3_HISTORY_BUCKET = "test-history-bucket"
S3_SITE = "groundserial1"

# default nominal voltage
NOMINAL_VOLTAGE = 240.0
# QUERY_TAGGING_FORMAT = "app={app_name} endpoint={endpoint} stack={stack}"
