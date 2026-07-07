#!/usr/bin/env bash
#
# Regenerate the metering-provider client at
# sparkmeter/metering/_generated/ from the metering provider's OpenAPI
# spec.
#
# Set OPENAPI_PATH (or OPENAPI_URL) to point at the spec source.
#
# Run from the webapp repo root:
#
#     OPENAPI_PATH=/path/to/openapi.json ./scripts/regen-metering-wire.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ -z "${OPENAPI_PATH:-}" ]; then
    echo "OPENAPI_PATH must be set to the path of the metering-provider openapi.json" >&2
    exit 1
fi

if [ ! -f "${OPENAPI_PATH}" ]; then
    echo "openapi.json not found at ${OPENAPI_PATH}" >&2
    exit 1
fi

uv run --project "${REPO_ROOT}" pyopenapi-gen \
    --project-root "${REPO_ROOT}" \
    --output-package sparkmeter.metering._generated \
    --force \
    --no-postprocess \
    "${OPENAPI_PATH}"

echo "regenerated sparkmeter/metering/_generated/"
