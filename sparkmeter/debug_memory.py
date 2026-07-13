# -*- coding: utf-8 -*-
# Copyright © 2025 SparkMeter, Inc.
# All Rights Reserved.
"""Debug endpoint for memory profiling."""

import os
import resource
import sys

from flask import Blueprint, jsonify

debug_memory = Blueprint("debug_memory", __name__)


@debug_memory.route("/debug/memory")
def memory_profile():
    """Return detailed memory profile of the current process."""
    # Get process memory info
    rusage = resource.getrusage(resource.RUSAGE_SELF)
    rss_mb = rusage.ru_maxrss / 1024.0  # Convert to MB (on Linux it's in KB)

    # Get loaded modules
    loaded_modules = list(sys.modules.keys())

    # Check for specific heavy libraries
    heavy_libs = {
        "pandas": "pandas" in sys.modules,
        "numpy": "numpy" in sys.modules,
        "celery": "celery" in sys.modules,
        "kombu": "kombu" in sys.modules,
        "amqp": "amqp" in sys.modules,
        "billiard": "billiard" in sys.modules,
        "vincent": "vincent" in sys.modules,
    }

    # Get module counts by package
    package_counts = {}
    for module in loaded_modules:
        package = module.split(".")[0]
        package_counts[package] = package_counts.get(package, 0) + 1

    # Sort by count
    top_packages = sorted(package_counts.items(), key=lambda x: x[1], reverse=True)[:20]

    # Get memory maps for shared libraries (Linux only)
    shared_libs = []
    try:
        pid = os.getpid()
        with open("/proc/%d/maps" % pid, "r") as f:
            for line in f:
                if ".so" in line and "r-xp" in line:
                    parts = line.strip().split()
                    if len(parts) >= 6:
                        lib_path = parts[5]
                        # Only include interesting libraries
                        interesting = ["pandas", "numpy", "celery", "kombu", "amqp", "vincent"]
                        if any(name in lib_path.lower() for name in interesting):
                            if lib_path not in shared_libs:
                                shared_libs.append(lib_path)
    except (IOError, OSError):
        pass

    return jsonify(
        {
            "pid": os.getpid(),
            "rss_mb": rss_mb,
            "total_modules": len(loaded_modules),
            "heavy_libraries": heavy_libs,
            "top_packages": [{"package": pkg, "module_count": count} for pkg, count in top_packages],
            "shared_libraries": shared_libs,
            "sample_modules": loaded_modules[:50],  # First 50 modules as sample
        }
    )
