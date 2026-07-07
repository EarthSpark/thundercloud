# -*- coding: utf-8 -*-
# Copyright © 2013-2025 SparkMeter, Inc.
# All Rights Reserved.
"""Settings module for configuring the application."""

import logging

# the api endpoint to be used for api calls
# EX: API_ENDPOINT = 'https://[testsite].sparkmeter.cloud/api/v0'
API_ENDPOINT = None

# if debugging is enabled, makes things verbose
DEBUG = False

SERIAL = "overwrite_me_in_settings_custom"

HEROKU = False
USE_HTTPS = False  # Use nginx for SSL termination in production

BOOTSTRAP_USE_MINIFIED = False
BOOTSTRAP_USE_CDN = False
BOOTSTRAP_JQUERY_VERSION = None  # including a local copy in the base template
SECRET_KEY = None

# Session cookie hardening. HttpOnly and SameSite are safe over plain HTTP.
# Secure defaults to False so dev/test over plain HTTP still round-trip the
# cookie; HTTPS-terminating production sets it True -- gateways behind a
# TLS-terminating nginx set SM_SESSION_COOKIE_SECURE=true, and Heroku is
# promoted automatically (see SparkmeterApplication._harden_session_cookie).
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = False

READING_RETENTION_MINUTES = 60 * 24  # how long to keep summarized readings for

LOG_LEVEL = logging.INFO

LOCALES = [
    'en_US',
    'fr_FR',
    # 'ht_HT',
]
# Default country code for phone numbers
DEFAULT_PHONE_COUNTRY_CODE = u'1'

# generic sentry settings (disabled for local development)
SENTRY_DSN = None

SECURITY_PASSWORD_HASH = 'bcrypt'
SECURITY_PASSWORD_SALT = None
SECURITY_CHANGEABLE = True
SECURITY_CHANGE_PASSWORD_TEMPLATE = 'security/change_password.html'
SECURITY_SEND_PASSWORD_CHANGE_EMAIL = False
SECURITY_SEND_PASSWORD_RESET_NOTICE_EMAIL = False

# settings for creating new meters
NEW_METER_TARIFF = 'ET1'
NEW_METER_ACCT_CREDIT = 1000
NEW_METER_STATE = 0  # 0=off, 1=on, 2=auto
NEW_METER_HIDDEN = True
NEW_METER_SUBNET = 255
NEW_METER_SPARKMAC_TTL = 15
NEW_METER_SPARKMAC_FORWARDING = 'flooding'
NEW_METER_SPARKMAC_FLOODING_SUBNETS = 255

# configure postgres url on heroku
SQLALCHEMY_DATABASE_URI = 'postgresql:///mydb'
SQLALCHEMY_TRACK_MODIFICATIONS = True

# HEARTBEAT_PERIOD must be in [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20, 30, 60]
HEARTBEAT_PERIOD = 15  # minutes
# CLEAR_PERIOD must be less than the HEARTBEAT_PERIOD
CLEAR_PERIOD = 2  # minutes

PRIORITIZED_READ_QUEUE = True

# NEIGHBORLIST_PERIOD = 5  # minutes

CURRENCY = "USD"

DEMO_PASSWORD = "password"

# maximum number of objects to include in a sync
SYNC_LIMIT = 1000

# current limit in Amps for each product
CURRENT_LIMIT = {
    'SM5R': 6.0,
    'SM15R': 20.0,
    'SM20R': 20.0,
    'SM60R': 61.0,
    'SM60RP': 61.0,
}

# this is the nominal voltage default for the ParameterObject configs
# it is set here to allow chef to modify this value before it gets
# written to the db using the custom settings file or env vars
NOMINAL_VOLTAGE = 120.0
# Tag outgoing queries with comments indicating their point of origin. Available format params:
#  * app_name - The name of the app
#  * endpoint - The Flask endpoint being called (if applicable)
#  * stack - The callstack for the query
QUERY_TAGGING_FORMAT = None
# QUERY_TAGGING_FORMAT = "app={app_name} endpoint={endpoint} stack={stack}"

# True if wallets should be locked for update when processing a reading or a transaction.
LOCK_WALLETS_ON_PROCESS = True
# How long to hold a wallet lock (in seconds).
LOCK_WALLETS_ON_PROCESS_TIMEOUT = 5

CLOUD_PORTAL_URL = 'https://sparkmeter.cloud'

# S3 Historical Data File Access Settings
# boto3 uses standard AWS credential chain (IAM role, then environment variables)
# Standard AWS environment variables (optional):
#   AWS_ACCESS_KEY_ID - AWS access key ID
#   AWS_SECRET_ACCESS_KEY - AWS secret access key
#   AWS_REGION or AWS_DEFAULT_REGION - AWS region
# S3_HISTORY_BUCKET - S3 bucket name for historical data files (set locally / via env var)
S3_HISTORY_BUCKET = None
# site value used when accessing historical data in s3
S3_SITE = None
