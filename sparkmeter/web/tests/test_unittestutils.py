# -*- coding: utf-8 -*-
# Copyright © 2026 SparkMeter, Inc.
# All Rights Reserved.
"""Unittests for the snapshot comparison in ContentTester.verify()."""

import os
import warnings

import pytest

from sparkmeter.web import unittestutils
from sparkmeter.web.unittestutils import ContentTester, SnapshotRegenerated

# An mtime far enough in the past that any rewrite moves it.
OLD_MTIME = 1000000000


class SnapshotTester(ContentTester):
    """A ContentTester whose snapshot lives at an explicit path.

    ContentTester derives expected_filename from the caller's stack frame and
    the test-data tree; these tests need a throwaway file under tmp_path
    instead. The frame is still the test method that built this object, so
    ``name`` -- which is what the regeneration warning reports -- keeps its
    normal shape.
    """

    def __init__(self, path):
        """Create a tester reading and writing the snapshot at ``path``."""
        super(SnapshotTester, self).__init__(frame=2)
        self.path = str(path)

    @property
    def expected_filename(self):
        """Get the snapshot path this tester was pointed at."""
        return self.path


def write_snapshot(path, content):
    """Write a snapshot file and backdate it so a rewrite is detectable."""
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(content)
    os.utime(path, (OLD_MTIME, OLD_MTIME))


def read_snapshot(path):
    """Read a snapshot file back."""
    with open(path, encoding="utf-8") as fp:
        return fp.read()


def regeneration_warnings(caught):
    """Pick the snapshot regeneration warnings out of recorded warnings.

    Unrelated warnings from application imports surface in the same recorder,
    so select the dedicated category rather than every warning raised.
    """
    return [w for w in caught if issubclass(w.category, SnapshotRegenerated)]


class ContentTesterVerifyTest(object):
    @pytest.fixture(autouse=True)
    def flag_off(self, monkeypatch):
        """Keep the module level flag off unless a test turns it on.

        It is process global, so leaking it would change how later tests in
        the same worker compare their snapshots.
        """
        monkeypatch.setattr(unittestutils, "regenerate_snapshots", False)

    @pytest.fixture()
    def regenerating(self, monkeypatch):
        """Turn on snapshot regeneration for the duration of a test."""
        monkeypatch.setattr(unittestutils, "regenerate_snapshots", True)

    @pytest.fixture()
    def snapshot(self, tmp_path):
        """Path of the snapshot file under test."""
        return tmp_path / "example.page"

    def test_matching_content_passes_without_touching_the_file(self, snapshot):
        """Flag off, content matches: test passes and the file is untouched."""
        write_snapshot(snapshot, "hello\n")
        tester = SnapshotTester(snapshot)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            tester.verify("hello")

        assert regeneration_warnings(caught) == []
        assert read_snapshot(snapshot) == "hello\n"
        assert os.stat(snapshot).st_mtime == OLD_MTIME

    def test_differing_content_fails_and_leaves_the_file_alone(self, snapshot):
        """Flag off, content differs: the existing failure path runs."""
        write_snapshot(snapshot, "hello\n")
        tester = SnapshotTester(snapshot)

        with pytest.raises(pytest.fail.Exception):
            tester.verify("goodbye")

        assert read_snapshot(snapshot) == "hello\n"
        assert os.stat(snapshot).st_mtime == OLD_MTIME

    def test_differing_content_is_rewritten_when_regenerating(self, snapshot, regenerating):
        """Flag on, content differs: the file is rewritten and a warning names its path."""
        write_snapshot(snapshot, "hello\n")
        tester = SnapshotTester(snapshot)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            tester.verify("goodbye")

        assert read_snapshot(snapshot) == "goodbye\n"
        assert os.stat(snapshot).st_mtime != OLD_MTIME
        regenerated = regeneration_warnings(caught)
        assert [str(w.message) for w in regenerated] == ["Regenerated snapshot: %s" % (snapshot,)]

    def test_rewriting_leaves_no_temporary_file_behind(self, snapshot, regenerating):
        """The rewrite goes through a temporary file, which must not survive it.

        The whole test-data tree is copied out of the container after a
        regeneration run, so a leftover temporary would be committed too.
        """
        write_snapshot(snapshot, "hello\n")
        tester = SnapshotTester(snapshot)

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            tester.verify("goodbye")

        assert sorted(os.listdir(os.path.dirname(str(snapshot)))) == ["example.page"]

    def test_matching_content_is_not_rewritten_when_regenerating(self, snapshot, regenerating):
        """Flag on, content matches: no rewrite, no warning, no mtime churn."""
        write_snapshot(snapshot, "hello\n")
        tester = SnapshotTester(snapshot)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            tester.verify("hello")

        assert regeneration_warnings(caught) == []
        assert read_snapshot(snapshot) == "hello\n"
        assert os.stat(snapshot).st_mtime == OLD_MTIME

    @pytest.mark.parametrize("regenerate", [False, True])
    def test_absent_file_is_written_without_warning(self, snapshot, monkeypatch, regenerate):
        """Either flag state, no file: it is written and no warning is emitted."""
        monkeypatch.setattr(unittestutils, "regenerate_snapshots", regenerate)
        tester = SnapshotTester(snapshot)
        assert not os.path.exists(snapshot)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            tester.verify("hello")

        assert regeneration_warnings(caught) == []
        assert read_snapshot(snapshot) == "hello\n"

    def test_snapshot_differing_only_in_leading_whitespace_stays_stale(self, snapshot, regenerating):
        """Leading whitespace is stripped from both sides before comparing.

        Nothing on disk is normalized as a result: a snapshot whose only
        difference from the rendered content is leading whitespace compares
        equal, so it is not rewritten and its stored form survives verbatim.
        """
        write_snapshot(snapshot, "\n\n  hello\n")
        tester = SnapshotTester(snapshot)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            tester.verify("   hello")

        assert regeneration_warnings(caught) == []
        assert read_snapshot(snapshot) == "\n\n  hello\n"
        assert os.stat(snapshot).st_mtime == OLD_MTIME


# ---------------------------------------------------------------------------
# The conftest wiring, exercised by running pytest on a throwaway test
# ---------------------------------------------------------------------------

# The top level conftest.py, i.e. the one actually shipped. The runs below use
# its real source rather than a restatement of it, so they cover the option's
# registration, its default, and pytest_configure handing it to unittestutils.
ROOT_CONFTEST = os.path.join(os.path.abspath(unittestutils.rootdir), "conftest.py")

# A test rendering content that differs from its snapshot -- the one case whose
# outcome --regenerate-snapshots changes.
DIFFERING_SNAPSHOT_TEST = '''
from sparkmeter.web.unittestutils import ContentTester


class SnapshotTester(ContentTester):
    """A ContentTester whose snapshot lives at an explicit path."""

    def __init__(self, path):
        """Create a tester reading and writing the snapshot at ``path``."""
        super(SnapshotTester, self).__init__(frame=2)
        self.path = path

    @property
    def expected_filename(self):
        """Get the snapshot path this tester was pointed at."""
        return self.path


def test_content_differs_from_its_snapshot():
    """Render content that does not match the snapshot on disk."""
    SnapshotTester(%r).verify("goodbye")
'''


@pytest.fixture()
def stale_snapshot(pytester, monkeypatch):
    """Build a pytest run of one test whose snapshot on disk is out of date.

    Returns the path of that snapshot. The inner runs set the module level
    flag exactly as a real run does -- that is the point of them -- so it is
    pinned through monkeypatch here and restored when the test ends.
    """
    monkeypatch.setattr(unittestutils, "regenerate_snapshots", False)

    with open(ROOT_CONFTEST, encoding="utf-8") as fp:
        pytester.makeconftest(fp.read())

    snapshot = pytester.path / "example.page"
    write_snapshot(snapshot, "hello\n")
    pytester.makepyfile(test_snapshot=DIFFERING_SNAPSHOT_TEST % (str(snapshot),))
    return snapshot


def test_run_without_the_flag_fails_and_keeps_the_snapshot(pytester, stale_snapshot):
    """The shipped default is off: a differing snapshot fails and is not touched."""
    result = pytester.runpytest()

    result.assert_outcomes(failed=1)
    assert read_snapshot(stale_snapshot) == "hello\n"
    assert os.stat(stale_snapshot).st_mtime == OLD_MTIME


def test_run_with_the_flag_rewrites_the_snapshot_and_warns(pytester, stale_snapshot):
    """With --regenerate-snapshots the same run passes, rewriting the snapshot."""
    result = pytester.runpytest("--regenerate-snapshots")

    result.assert_outcomes(passed=1)
    assert read_snapshot(stale_snapshot) == "goodbye\n"
    result.stdout.fnmatch_lines(["*SnapshotRegenerated: Regenerated snapshot: %s*" % (stale_snapshot,)])
