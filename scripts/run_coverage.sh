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
docker compose -f docker-compose.test.yml run --rm test \
    sh -c 'uv run pytest -n auto --junitxml=/app/junit.xml 2>&1 | tee /app/pytest-coverage.txt 1>&2; tar -c -C /app .coverage.xml junit.xml pytest-coverage.txt' \
    | tar -x

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
set +e
uvx "diff-cover==10.3.0" .coverage.xml \
    --compare-branch "$compare_branch" \
    --fail-under "$fail_under" \
    --format "$formats"
diff_cover_rc=$?
set -e

if [ -n "${GITHUB_STEP_SUMMARY:-}" ] && [ -f "$report_md" ]; then
    cat "$report_md" >> "$GITHUB_STEP_SUMMARY"
fi

exit "$diff_cover_rc"
