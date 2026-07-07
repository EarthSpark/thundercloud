# -*- coding: utf-8 -*-
# Copyright © 2013-2025 SparkMeter, Inc.
# All Rights Reserved.
"""Views for the historical data file browser interface."""

import http.client
import logging

from flask import redirect
from flask.json import jsonify
from flask.templating import render_template
from flask_security import roles_accepted

from sparkmeter.config.configdict import config
from sparkmeter.web.blueprint import AuthBlueprint

logger = logging.getLogger(__name__)
historyview = AuthBlueprint('history', __name__)


@historyview.route("/history")
@roles_accepted('operator')
def index():
    """Historical data file browser page.

    Displays a list of historical data files available in S3 for the
    current site. Operator users can browse and download their archived
    meter readings.
    """
    site_serial = config.get('S3_SITE')
    return render_template('history-index.html', site_serial=site_serial)


@historyview.route("/history/list.json")
@roles_accepted('operator')
def list_history_json():
    """List historical data files as JSON for web UI.

    This endpoint uses session authentication and delegates to the API logic.
    """
    from sparkmeter.api.historyviews0 import list_history_files_logic

    try:
        result = list_history_files_logic()
        return jsonify(
            error=None,
            status='success',
            files=result['files'],
            count=result['count'],
            site_serial=result['site_serial']
        )
    except Exception as e:
        logger.exception("Error listing historical data files: %s" % (e,))
        return jsonify(
            error=str(e),
            status='failure'
        ), http.client.INTERNAL_SERVER_ERROR


@historyview.route("/history/download/<path:filename>")
@roles_accepted('operator')
def download_history_redirect(filename):
    """Download a historical data file from S3.

    Redirects the user directly to a presigned S3 URL to download the file.
    This endpoint uses session authentication and delegates to the API logic.
    """
    from sparkmeter.api.historyviews0 import get_history_file_url_logic

    try:
        result = get_history_file_url_logic(filename)
        return redirect(result['url'])
    except Exception as e:
        logger.exception("Error generating presigned URL: %s" % (e,))
        return jsonify(
            error=str(e),
            status='failure'
        ), http.client.INTERNAL_SERVER_ERROR
