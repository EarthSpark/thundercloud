#!/usr/bin/env bash
# Build the test image and run the suite with the coverage gate. The report and
# validatecoverage both run inside the container, so this works in any docker
# context (local or CI) with nothing bind-mounted or copied out.
set -euo pipefail

# A git worktree's .git is a file, not a directory, and is unreadable inside the
# build context, so hatch-vcs cannot derive the version. Supply a placeholder in
# that case; a normal checkout leaves it empty and reads .git as usual.
version=""
if [ -f .git ]; then
    version="0.0.0"
fi

docker compose --profile test build \
    --build-arg SETUPTOOLS_SCM_PRETEND_VERSION="$version" \
    test
docker compose --profile test run --rm test \
    sh -c 'uv run pytest -n auto && python3 scripts/validatecoverage --python .coverage.xml'
