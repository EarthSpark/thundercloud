# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Sparkmeter configuration."""

import errno
import json
import logging
import os
import sys
from importlib import reload

from past.builtins import execfile

logging.captureWarnings(True)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-7s %(asctime)s   %(message)s",
)
logger = logging.getLogger(__name__)


class ConfigDict(dict):
    """Dict subclass which provides our global configuration."""

    #: The ground system
    GROUND = "ground"

    #: The cloud system
    CLOUD = "cloud"

    def load_dict(self, ns):
        """Load values from a dictionary."""
        for key, value in list(ns.items()):
            self[key] = value

    def load_object(self, object_name):
        """Import an object and load values from its attributes."""
        if object_name in sys.modules:
            reload(sys.modules[object_name])
        obj = __import__(object_name, globals(), locals(), [" "])
        for attr in dir(obj):
            self[attr] = getattr(obj, attr)

    def load_pyfile(self, filename, warn=True):
        """Parse a python file and load values from its attributes."""
        g = dict()
        try:
            execfile(filename, g)
            if warn:
                logger.warn("Using %s file, use env variables instead" % filename)
        except IOError as e:  # pragma: nocover
            if e.errno != errno.ENOENT:
                raise
        g.pop("__builtins__", None)
        self.load_dict(g)

    def load(self, app=None):
        """
        Load the config settings for the sparkmeter application.

        Configs are loaded in the following order:
            1. Flask default config
            2. sparkmeter/settings.py defaults
            3. SPARKMETER_SETTINGS (settings_custom.py) overrides
            4. env overrides
            5. heroku env settings
        """
        # 1. load the flask config first as defaults
        if app is not None:
            self.update(app.config)

        # 2. load the default settings
        self.load_object("sparkmeter.settings")

        # 3. load the SPARKMETER_SETTINGS (settings_custom.py) overrides
        if not os.environ.get("HEROKU"):
            # load instance settings only if not running in heroku.
            settings_filename = os.environ.get("SPARKMETER_SETTINGS")
            if settings_filename:
                filename = os.path.join(os.path.dirname(__file__), "..", "..", settings_filename)
                self.load_pyfile(filename)
            elif app is not None:  # pragma nocover
                # custom server level configs stored in instance dir
                settings_custom_file = os.path.join(app.instance_path, "settings_custom.py")
                self.load_pyfile(settings_custom_file)

                # custom user defined configs stored in instance dir
                settings_user_file = os.path.join(app.instance_path, "settings_custom_user.py")
                self.load_pyfile(settings_user_file)

        # 4. load the env overrides, unless we are running the unittests
        if "SPARKMETER_TESTING" not in os.environ:  # pragma: nocoverage
            envoverrides = {k[3:]: v for k, v in list(os.environ.items()) if k.startswith("SM_")}
            for key, value in list(envoverrides.items()):
                # Always keep these as strings
                string_keys = [
                    "SERIAL",
                    "SPARKCLOUD_API_KEY",
                    "GROUND_NAME",
                    "SECURITY_PASSWORD_SALT",
                    "SECRET_KEY",
                ]
                if key in string_keys:
                    self[key] = value
                else:
                    try:
                        self[key] = json.loads(value)
                    except ValueError:
                        self[key] = value

        # 5. load the heroku specific env overrides
        heroku_configs = {
            "SENTRY_DSN": "SENTRY_DSN",
            "DATABASE_URL": "SQLALCHEMY_DATABASE_URI",
        }
        for env_name, config_name in list(heroku_configs.items()):  # pragma nocover
            value = os.environ.get(env_name, None)
            if value is not None:
                self[config_name] = value

        for old_var in ["HEROKU"]:
            if old_var in os.environ:  # pragma nocover
                logger.warn("Using old style env variables, please update %s to SM_%s" % (old_var, old_var))
                self[old_var] = os.environ[old_var]

        # remove any keys that are not upper case. This removes the imports like logging, and builtins
        for key, value in list(self.items()):
            if not key.isupper():
                self.pop(key)

    def get_current_locale(self):
        """Fetch the currently configured locale as a string.

        :returns: the locale string or 'en_US' if not configured.
        """
        return self.get("LOCALES", ["en_US"])[0]

    @property
    def local_system(self):
        """Get if this is a ground or cloud system."""
        if self.get("HEROKU"):
            return self.CLOUD
        return self.GROUND

    def is_ground(self):
        """Get if this a ground system."""
        return self.local_system == self.GROUND

    def is_cloud(self):
        """Get if this a cloud system."""
        return self.local_system == self.CLOUD


config = ConfigDict()
