# Copyright © 2026 SparkMeter, Inc.
# All Rights Reserved.
"""Interactive CLI prompt utilities."""


def prompt(field, default=None):
    """Prompt user for input."""
    if default:
        result = input('%s [%s]: ' % (field, default))
    else:
        result = input('%s: ' % field)
    return result or default


def prompt_bool(msg, default=True):
    """Prompt user for yes/no confirmation."""
    suffix = ' [Y/n] ' if default else ' [y/N] '
    result = input(msg + suffix)
    if not result:
        return default
    return result.lower() in ('y', 'yes')


def prompt_choices(field, choices, default=None):
    """Prompt user to select from choices."""
    choices_str = ', '.join(name for name, _ in choices)
    result = input('%s (%s) [%s]: ' % (field, choices_str, default or ''))
    return result or default
