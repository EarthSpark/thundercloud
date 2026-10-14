# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Logging utilities.

Every log record, from this package, from libraries and from Hypercorn, goes
through one handler on the root logger, writing to stderr (stdout is left to
CLI command output). The handler renders each record in one of three
formats, chosen with the LOG_FORMAT setting (`SM_LOG_FORMAT`):

- `text` (default): a human-oriented line, with tracebacks on the following lines;
- `logfmt`: one `key=value` line per record, tracebacks included, for Loki
  and similar;
- `json`: one JSON object per line, for Elasticsearch and similar.

logfmt and JSON carry the same keys: `time` (ISO 8601, UTC), `level`,
`logger`, `msg`, then any context bound with `structlog.contextvars` (the
access log's `request_id`, a periodic `task`), any `extra=` fields, and
`exception` when there is a traceback.

Existing `logging.getLogger(__name__)` loggers need no changes. New code can
also log key/value pairs with `structlog.stdlib.get_logger(__name__)`; both
render the same way.
"""

import logging
import sys
import warnings

import structlog

LOG_FORMATS = ("text", "logfmt", "json")

# Keys that open every logfmt and JSON line, in this order.
_LEADING_KEYS = ("time", "level", "logger", "msg")

# The root handler this module manages; created on the first setup_logging call.
_handler = None


def setup_logging(level=logging.INFO, fmt="text"):
    """Route all logging through one stderr handler rendering `fmt` at `level`.

    Safe to call again: later calls change the format and level of the same
    handler. An unrecognized level or format falls back to INFO or text, with
    a warning.
    """
    global _handler
    level_value, bad_level = _coerce_level(level)
    fmt_value = str(fmt).strip().lower()
    bad_fmt = fmt_value not in LOG_FORMATS
    if bad_fmt:
        fmt_value = "text"

    root = logging.getLogger()
    if _handler is None:
        _handler = logging.StreamHandler(sys.stderr)
        root.addHandler(_handler)
        _configure_once()
    _handler.setFormatter(_formatter(fmt_value, _handler.stream))
    root.setLevel(level_value)

    if bad_level:
        logging.getLogger(__name__).warning("unrecognized LOG_LEVEL %r; using INFO", level)
    if bad_fmt:
        logging.getLogger(__name__).warning(
            "unrecognized LOG_FORMAT %r; using text (choose from %s)", fmt, ", ".join(LOG_FORMATS)
        )


def _coerce_level(level):
    """Return `(level number, was_invalid)` for an int, a number string or a level name."""
    if isinstance(level, int) and not isinstance(level, bool):
        return level, False
    name = str(level).strip().upper()
    if name.isdigit():
        return int(name), False
    value = logging.getLevelNamesMapping().get(name)
    if value is None:
        return logging.INFO, True
    return value, False


def _shared_processors():
    """Processors every record passes through, whether it came from logging or structlog."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="time"),
    ]


def _lead_with_standard_keys(logger, method_name, event_dict):
    lead = {key: event_dict.pop(key) for key in _LEADING_KEYS if key in event_dict}
    return {**lead, **event_dict}


def _formatter(fmt, stream):
    if fmt == "text":
        renderers = [
            structlog.dev.ConsoleRenderer(colors=_isatty(stream), timestamp_key="time"),
        ]
    else:
        renderers = [
            structlog.processors.format_exc_info,
            structlog.processors.EventRenamer("msg"),
            _lead_with_standard_keys,
            structlog.processors.JSONRenderer()
            if fmt == "json"
            else structlog.processors.LogfmtRenderer(bool_as_flag=False),
        ]
    return structlog.stdlib.ProcessorFormatter(
        # Records from logging: add the shared keys plus any `extra=` fields.
        foreign_pre_chain=[*_shared_processors(), structlog.stdlib.ExtraAdder()],
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, *renderers],
    )


def _isatty(stream):
    try:
        return stream.isatty()
    except (AttributeError, ValueError):
        return False


def _configure_once():
    """Process-wide setup that doesn't depend on the format or level."""
    logging.captureWarnings(True)

    # structlog loggers hand their event dicts to the root handler's formatter.
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            *_shared_processors(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
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
