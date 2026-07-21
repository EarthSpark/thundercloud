#!/usr/bin/env bash
# Build the test image, run the suite, and gate the changed lines with
# diff-cover. Coverage is produced inside the container and streamed out to the
# host, where git history is available to diff against the compare branch.
set -euo pipefail

compare_branch="${DIFF_COVER_COMPARE_BRANCH:-origin/main}"
fail_under="${DIFF_COVER_FAIL_UNDER:-90}"

# A git worktree's .git is a file, not a directory, and is unreadable inside the
# build context, so hatch-vcs cannot derive the version. Supply a placeholder in
# that case; a normal checkout leaves it empty and reads .git as usual.
version=""
if [ -f .git ]; then
    version="0.0.0"
fi

docker compose -f docker-compose.test.yml build \
    --build-arg SETUPTOOLS_SCM_PRETEND_VERSION="$version" \
    test

# pytest writes .coverage.xml (see setup.cfg addopts) and, via --junitxml, a
# junit report; its terminal output (the term-missing coverage table) is teed to
# pytest-coverage.txt for the PR report comment. All three are produced in the
# container, tarred to stdout, and unpacked on the host. pytest's output is teed
# to stderr, not stdout, so stdout carries only the tar stream.
#
# pytest's exit status has to be carried out by hand. `pipefail` makes the
# pipeline report pytest's status rather than tee's, it is captured before tar
# runs, and the container exits with it. Otherwise the container's status is
# tar's: an ordinary red suite still failed the job, but only because
# --no-cov-on-fail suppresses .coverage.xml and tar then errors on the missing
# file. A run that writes the reports and still exits non-zero -- pytest's
# exit 5, "no tests collected", from a -k that matches nothing -- left tar
# succeeding and the job green. On the host the status is captured rather than
# allowed to abort, so the script runs to the end and reports it there instead
# of dying mid-script; when coverage did reach the host, the diff-cover report
# below is still produced.
#
# The artifacts are cleared first so that a run which fails before writing them
# cannot leave the previous run's files behind to be read as current -- the gate
# below reads .coverage.xml, and the CI report steps read the other two.
rm -f .coverage.xml junit.xml pytest-coverage.txt

set +e
docker compose -f docker-compose.test.yml run --rm test \
    sh -c 'set -o pipefail; uv run pytest -n auto --junitxml=/app/junit.xml 2>&1 | tee /app/pytest-coverage.txt 1>&2; status=$?; tar -c -C /app .coverage.xml junit.xml pytest-coverage.txt; exit $status' \
    | tar -x
tests_rc=${PIPESTATUS[0]}
set -e

# diff-cover gates the changed lines and always prints a terminal report. It
# also writes a markdown report, which is appended to the GitHub Actions job
# summary below. Under Actions it additionally emits GitHub annotations on
# stdout, so each uncovered changed line is flagged inline on the PR diff.
report_md="diff-cover-report.md"
formats="markdown:$report_md"
if [ -n "${GITHUB_ACTIONS:-}" ]; then
    formats="$formats,github-annotations:error"
fi

# --fail-under exits non-zero when changed-line coverage is below the threshold.
# Capture that instead of aborting so the report still reaches the job summary.
#
# A suite that fails writes no coverage at all (--no-cov-on-fail in setup.cfg),
# so there is nothing to gate. Skip it and say so, rather than letting
# diff-cover fail on the missing file with a traceback that reads like a broken
# tool instead of a failing test. The suite's own status is reported below.
diff_cover_rc=0
if [ -f .coverage.xml ]; then
    set +e
    uvx "diff-cover==10.3.0" .coverage.xml \
        --compare-branch "$compare_branch" \
        --fail-under "$fail_under" \
        --format "$formats"
    diff_cover_rc=$?
    set -e
else
    # Drop any report from a previous run so the summary below cannot append a
    # stale one for a gate that did not run.
    rm -f "$report_md"
    echo "No coverage was produced, so the coverage gate is skipped." >&2
fi

if [ -n "${GITHUB_STEP_SUMMARY:-}" ] && [ -f "$report_md" ]; then
    cat "$report_md" >> "$GITHUB_STEP_SUMMARY"
fi

# A failing suite fails the job. It is reported ahead of the coverage gate
# because a red run makes the coverage number meaningless.
if [ "$tests_rc" -ne 0 ]; then
    exit "$tests_rc"
fi

exit "$diff_cover_rc"
