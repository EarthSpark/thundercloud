# -*- coding: utf-8 -*-
# Copyright © 2026 SparkMeter, Inc.
# All Rights Reserved.
"""Tests for safe_redirect_target (open-redirect guard)."""

import pytest

from sparkmeter.web.redirects import safe_redirect_target


class SafeRedirectTargetTest:
    """Only safe local / same-host targets are honored; else fallback."""

    @pytest.mark.parametrize(
        "target, expected",
        [
            # honored: rooted local paths
            ("/dashboard", "/dashboard"),
            ("/user/foo/?x=1", "/user/foo/?x=1"),
            # rejected: external / protocol-relative / non-local scheme
            ("https://evil.example.com/", "FALLBACK"),
            ("http://evil.example.com", "FALLBACK"),
            ("//evil.example.com", "FALLBACK"),
            ("///evil.example.com", "FALLBACK"),
            ("javascript:alert(1)", "FALLBACK"),
            # rejected: missing-slash scheme fold (browsers normalize to cross-origin)
            ("https:/evil.example.com", "FALLBACK"),
            ("https:evil.example.com", "FALLBACK"),
            # rejected: malformed URL (unbalanced IPv6 bracket -> urlparse ValueError)
            ("https://[::1", "FALLBACK"),
            ("//[::1", "FALLBACK"),
            # rejected: bare host (no leading slash)
            ("evil.example.com/path", "FALLBACK"),
            # rejected: backslash folds to // in browsers
            ("/\\evil.example.com", "FALLBACK"),
            ("\\\\evil.example.com", "FALLBACK"),
            ("\\/evil.example.com", "FALLBACK"),
            # rejected: leading / embedded whitespace and control chars
            ("  https://evil.example.com", "FALLBACK"),
            ("\thttps://evil.example.com", "FALLBACK"),
            ("/foo\n//evil.example.com", "FALLBACK"),
            # rejected: empty / missing
            (None, "FALLBACK"),
            ("", "FALLBACK"),
        ],
    )
    def test_path_only(self, target, expected):
        assert safe_redirect_target(target, "FALLBACK") == expected

    @pytest.mark.parametrize(
        "target, expected",
        [
            # same-host absolute URL (e.g. a same-site Referer) is honored
            ("http://myhost/back", "http://myhost/back"),
            ("https://myhost/back?x=1", "https://myhost/back?x=1"),
            # other host is rejected
            ("http://evil.example.com/back", "FALLBACK"),
            # a local path still works with a host given
            ("/local", "/local"),
            # backslash bypass still rejected with a host
            ("/\\evil.example.com", "FALLBACK"),
        ],
    )
    def test_same_host(self, target, expected):
        assert safe_redirect_target(target, "FALLBACK", "myhost") == expected
