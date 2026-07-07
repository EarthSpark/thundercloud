# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Views for the ground web interface."""

import logging

from flask.templating import render_template

from sparkmeter.config.configdict import config
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.web.blueprint import AuthBlueprint

logger = logging.getLogger(__name__)
homepage = AuthBlueprint('homepage', __name__)


@homepage.route("/")
def index():
    """Root page, redirect to ground list."""
    if not config['HEROKU']:
        ground = Ground.get_current()
    else:
        ground = None
    return render_template('homepage-view.html', ground=ground)
