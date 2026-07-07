# -*- coding: utf-8 -*-
# Copyright © 2013-2026 EarthSpark International Corp.
# All Rights Reserved.
"""Version information.

The actual version string is generated at build time by `hatch-vcs` from
the latest git tag (e.g., `v2.0.0` → `"2.0.0"`; untagged commits get a
PEP 440 dev marker like `"2.0.1.dev3+ga1b2c3d"`). The generated file is
`sparkmeter/_version.py` and is gitignored.

This module is a thin shim so existing callers can keep using
`sparkmeter.__version__.version` and `.git_version`.
"""
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    version = _pkg_version("sparkmeter")
except PackageNotFoundError:
    # Source checkout without `pip install -e .` run yet — fall back to
    # the file hatch-vcs writes on build.
    try:
        from sparkmeter._version import __version__ as version
    except ImportError:  # pragma: nocoverage
        version = "0.0.0+unknown"


def _git_hash_from_version(v: str) -> str:
    """Extract the short git hash from a PEP 440 local-version segment."""
    if "+" not in v:
        return ""
    local = v.split("+", 1)[1]
    # local part shaped like "ga1b2c3d" or "ga1b2c3d.d20260430"
    for token in local.split("."):
        if token.startswith("g") and len(token) > 1:
            return token[1:]
    return ""


git_version = _git_hash_from_version(version)
