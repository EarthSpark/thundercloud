# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Password utility module."""

import random
import string
from builtins import range


def generate_password(length):
    """Generate a password.

    :params length: length of the password
    :returns: the generated password
    """
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"

    r = random.SystemRandom()
    return "".join([r.choice(chars) for i in range(length)])
