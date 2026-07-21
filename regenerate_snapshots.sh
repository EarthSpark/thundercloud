#!/usr/bin/env bash
#
# Regenerate the .page snapshots under test-data/ from the current sources.
#
# Run from the top level of the checkout to regenerate -- the main checkout or
# any worktree:
#
#     ./regenerate_snapshots.sh
#
# The suite runs with --regenerate-snapshots, which makes a content test whose
# rendered output differs rewrite its .page file instead of failing; see
# ContentTester.verify in sparkmeter/web/unittestutils.py. Matching snapshots
# are not touched, so the diff is the set of pages the source change affected.
# Orphans are not pruned: the .page file of a renamed or deleted test is left
# in place and is not reported, so finding those is a manual step.
#
set -euo pipefail

# The image build derives the version from .git via hatch-vcs. In a worktree
# .git is a file pointing elsewhere rather than a directory, so that fails and
# SETUPTOOLS_SCM_PRETEND_VERSION supplies the version instead. Built as its own
# step because `docker compose run --build` cannot forward --build-arg.
docker compose -f docker-compose.test.yml build \
    --build-arg SETUPTOOLS_SCM_PRETEND_VERSION="0.0.0+g$(git rev-parse --short HEAD)" \
    test

# Compose namespaces its own containers by project, but this one is created
# with an explicit --name, so it needs the checkout in its name too. Otherwise
# the pre-run `docker rm -f` below would remove a container another checkout is
# using: docker-compose.test.yml is written so two checkouts can run their
# suites concurrently.
container="$(basename "$PWD")-snapshot-regen"

docker rm -f "$container" >/dev/null 2>&1 || true

# The run's status is captured rather than allowed to abort the script: a test
# failing for a reason unrelated to snapshots would otherwise end the run
# before the copy back, discarding every snapshot it had already rewritten.
status=0
docker compose -f docker-compose.test.yml run --name "$container" test \
    uv run pytest -n auto --regenerate-snapshots || status=$?

# The test image COPYs the source in rather than bind-mounting the working
# tree, so the rewritten files exist only inside the container -- hence the
# name instead of --rm, and this copy back.
if ! docker cp "$container:/app/test-data/." ./test-data/; then
    echo "Failed to copy the regenerated snapshots out of the container." >&2
    echo "Leaving the container in place so the run can still be retrieved:" >&2
    echo "  docker cp $container:/app/test-data/. ./test-data/" >&2
    exit 1
fi

docker rm -f "$container" >/dev/null || true

exit "$status"
