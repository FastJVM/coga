#!/bin/sh
set -eu

if [ "$#" -lt 1 ]; then
    echo "usage: COGA_GATE_AGENT_INSTALL='...' $0 VERSION [-- CONTAINER-ARG ...]" >&2
    exit 2
fi

version=$1
shift
if [ "${1:-}" = "--" ]; then
    shift
fi

engine=${COGA_GATE_CONTAINER_ENGINE:-docker}
agent=${COGA_GATE_AGENT:-codex}
image=${COGA_GATE_IMAGE:-python:3.11-slim}
evidence_dir=${COGA_GATE_EVIDENCE_DIR:-"$PWD/coga-install-gate-evidence"}

if [ -z "${COGA_GATE_AGENT_INSTALL:-}" ]; then
    echo "COGA_GATE_AGENT_INSTALL must install the authenticated '$agent' CLI in the container" >&2
    exit 2
fi
if ! command -v "$engine" >/dev/null 2>&1; then
    echo "container engine not found: $engine" >&2
    exit 2
fi

mkdir -p "$evidence_dir"
evidence_dir=$(cd "$evidence_dir" && pwd)
script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)

exec "$engine" run --rm -it \
    -e "COGA_GATE_VERSION=$version" \
    -e "COGA_GATE_AGENT=$agent" \
    -e "COGA_GATE_AGENT_INSTALL=$COGA_GATE_AGENT_INSTALL" \
    -e "COGA_GATE_IMAGE=$image" \
    -v "$evidence_dir:/evidence" \
    -v "$script_dir/verify-clean-install-container.sh:/verify-clean-install:ro" \
    "$@" \
    "$image" \
    bash /verify-clean-install
