# -*- coding: utf-8 -*-
# Copyright © 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Utilities for working with intervals."""

import collections
import itertools
from builtins import range

Overlap = collections.namedtuple("Overlap", "start1 end1 start2 end2")


# http://nedbatchelder.com/blog/201310/range_overlap_in_two_compares.html
# http://stackoverflow.com/questions/325933
def check_interval_overlaps(start1, end1, start2, end2):
    """Check if two intervals overlap.

    :param start1: startpoint of first interval
    :param end1: endpoint of the first interval
    :param start2: startpoint of the second interval
    :param end2: endpoint of the second interval
    :returns: `True` if the intervals overlap, `False` otherwise.
    """
    return end1 > start2 and end2 > start1


def check_intervals_overlap(intervals):
    """Check if a list of interval overlap with each other.

    :param intervals: a list of two sized tuple with integers.
    :returns: an four sized tuple with integers (start1, end1, start2, end2)
    """
    for (s1, e1), (s2, e2) in itertools.combinations(intervals, 2):
        if check_interval_overlaps(s1, e1, s2, e2):
            # Make sure the result is in correct order
            res = sorted([(s1, e1), (s2, e2)])
            return Overlap(res[0][0], res[0][1], res[1][0], res[1][1])


def check_intervals_gap(intervals, imin, imax):
    """Check if there are gaps in a list of intervals.

    :param intervals: a list of two sized tuple with integers.
    :param imin: minimum value for these intervals
    :param imax: maximum value for these intervals.
    :returns: a list of numbers that represents all the numbers that gap
    """
    # This is not super-efficient, but as long as maximum (currently 65535) is
    # not in the millions this should be fast enough.
    gaps = set(range(imin, imax))
    for interval in intervals:
        gaps = gaps.difference(set(range(interval[0], interval[1])))

    return list(gaps)
