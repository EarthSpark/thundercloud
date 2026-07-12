# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Logging utilities."""

import logging
import warnings

_logging_configured = False


def setup_logging(level=logging.INFO):
    """Setup logging configuration."""
    global _logging_configured
    if _logging_configured:
        return
    logging.captureWarnings(True)

    logging.basicConfig(
        level=level,
        format="%(levelname)-7s %(asctime)s [%(name)-24s] %(message)s",
    )
    logging.getLogger("factory.generate").setLevel(logging.INFO)
    logging.getLogger("factory.containers").setLevel(logging.INFO)

    message = (
        "On Wallet.%s, 'passive_deletes' is "
        "normally configured on one-to-many, one-to-one, many-to-many "
        "relationships only."
    )
    for attr in ["meter", "sales_account", "grid"]:
        warnings.filterwarnings("ignore", message % attr)

    # FIXME: Remove this once we upgraded flask_security
    from flask_wtf._compat import FlaskWTFDeprecationWarning

    warnings.filterwarnings("ignore", category=FlaskWTFDeprecationWarning)

    _logging_configured = True
