# -*- coding: utf-8 -*-
# Copyright © 2026 SparkMeter, Inc.
# All Rights Reserved.
"""Top level pytest configuration.

This file exists at the top of the checkout, rather than alongside the tests
in sparkmeter/conftest.py, because pytest only calls pytest_addoption for
*initial* conftests -- the ones found by walking down to the invocation's
anchor directory before the command line is parsed. With no path argument the
anchor is the rootdir, so a conftest.py one directory further down is loaded
too late for its options to exist: `pytest --regenerate-snapshots` would be
rejected as an unrecognized argument.
"""

# pytest's own `pytester` fixture, used by the tests that run pytest on a
# throwaway test to check this file's wiring end to end. `pytest_plugins` is
# only honored in the top level conftest, which is here.
pytest_plugins = ["pytester"]


def pytest_addoption(parser):
    """Register our own command line options."""
    parser.addoption(
        "--regenerate-snapshots",
        action="store_true",
        default=False,
        help=(
            "Rewrite the .page snapshot of any content test whose rendered "
            "output differs, instead of failing the test."
        ),
    )


def pytest_configure(config):
    """Propagate command line options to the code that needs them.

    ContentTester is a plain class with no fixture access, so the option is
    handed to it as a module level flag. This runs once per process, which
    covers each xdist worker as well as a plain single-process run.
    """
    from sparkmeter.web import unittestutils

    unittestutils.regenerate_snapshots = config.getoption("--regenerate-snapshots")
