# -*- coding: utf-8 -*-
# Copyright © 2026 SparkMeter, Inc.
# All Rights Reserved.
"""Helpers for open-redirect-resistant redirects."""
from urllib.parse import urlparse


def safe_redirect_target(target, fallback, current_host=None):
    """Return ``target`` only when it is a safe redirect, else ``fallback``.

    Accepts a local path rooted at a single ``/`` (e.g. a ``next`` query
    parameter) or, when ``current_host`` is supplied, an absolute http(s) URL
    whose host equals ``current_host`` (e.g. a legitimate same-site ``Referer``,
    which is always an absolute URL).

    Rejects external hosts (``https://evil``), protocol-relative hosts
    (``//evil``), non-local schemes (``javascript:``), bare hosts (``evil.com``),
    and the browser-normalization evasions: backslashes (browsers fold ``\\`` to
    ``/``, so ``/\\evil`` becomes ``//evil``) and leading/embedded whitespace or
    control characters.
    """
    if not target:
        return fallback
    if (target != target.strip()
            or '\\' in target
            or '\t' in target or '\n' in target or '\r' in target):
        return fallback
    try:
        parsed = urlparse(target)
    except ValueError:
        # Malformed URL (e.g. an unbalanced IPv6 bracket) -- never trust it.
        return fallback
    if parsed.scheme not in ('', 'http', 'https'):
        return fallback
    if not parsed.netloc:
        # Rooted local path only -- checked against the original target string,
        # which is security-load-bearing: ``startswith('/')`` rejects
        # missing-slash scheme folds like ``https:/evil``, and not
        # ``startswith('//')`` rejects protocol-relative ``//evil`` (browsers
        # resolve both cross-origin).
        if target.startswith('/') and not target.startswith('//'):
            return target
        return fallback
    # Absolute URL: honor only when it points at our own host (same-site Referer).
    if current_host and parsed.netloc == current_host:
        return target
    return fallback
