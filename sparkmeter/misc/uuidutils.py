# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""UUID utilities."""

import hashlib
import uuid
from builtins import str


# Be very careful about changing this, since it is used by database migration
# scripts. If changes are absolutely required, version this so that old patches
# still work.
def as_uuid(*args):
    """Create a new uuid based on hashes for a set of existing parameters."""
    # For mapping tables, this is usually the hash of the mapped references, see
    # microgrid_addresses in patch 0.27
    # For newly created singletons, just use a string, see sms_config in patch 0.32
    # If the table has a foreign key, use that, see meter_billing in patch 0.22
    md5 = hashlib.md5("-".join(str(arg) for arg in args).encode())
    return uuid.UUID(md5.hexdigest())
