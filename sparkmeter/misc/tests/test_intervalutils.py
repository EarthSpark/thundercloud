# -*- coding: utf-8 -*-
# Copyright © 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Unittests for sparkmeter.intervalsutils"""

from sparkmeter.misc.intervalutils import Overlap, check_interval_overlaps, check_intervals_overlap
from sparkmeter.tests.base import SparkMeterTestCaseBase


class IntervalTests(SparkMeterTestCaseBase):

    def test_check_intervals_overlaps(self):
        assert not check_intervals_overlap([(0, 30), (30, 100), (100, 220), (220, 4800)])

        overlap = check_intervals_overlap([(0, 1000), (900, 2000)])
        assert overlap == Overlap(0, 1000, 900, 2000)

        # Make sure it's ordered nicely for good exception message
        overlap = check_intervals_overlap([(0, 100), (50, 200)])
        assert overlap == Overlap(0, 100, 50, 200)
        overlap = check_intervals_overlap([(50, 200), (0, 100)])
        assert overlap == Overlap(0, 100, 50, 200)

    def test_check_interval_overlap(self):
        assert check_interval_overlaps(0, 30, 29, 100)
        assert check_interval_overlaps(29, 100, 0, 30)
        assert not check_interval_overlaps(0, 30, 30, 100)
