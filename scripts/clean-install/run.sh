#!/usr/bin/env bash
# Install Coga into a fresh Linux container and walk the documented path.
#
#   scripts/clean-install/run.sh pypi   the current PyPI release
#   scripts/clean-install/run.sh main   a wheel built with `uv build` from fetched origin/main
#
# The container is kept running for inspection and the attended steps; the
# runbook is the "Clean-install harness" section of the coga/testing topic.
set -euo pipefail

mode=${1:-}
case "$mode" in
    pypi | main) ;;
    *)
        echo "usage: $0 pypi|main" >&2
        exit 2
        ;;
esac

engine=${COGA_CLEAN_INSTALL_ENGINE:-docker}
image=${COGA_CLEAN_INSTALL_IMAGE:-coga-clean-install:py3.11}
remote=${COGA_CLEAN_INSTALL_REMOTE:-origin}
# Set to `host` when the engine's bridge network drops large downloads.
network=()
if [ -n "${COGA_CLEAN_INSTALL_NETWORK:-}" ]; then
    network=(--network "$COGA_CLEAN_INSTALL_NETWORK")
fi
stamp=$(date -u +%Y%m%dT%H%M%SZ)
container=coga-clean-install-$mode-$stamp
evidence=${COGA_CLEAN_INSTALL_EVIDENCE:-${TMPDIR:-/tmp}/coga-clean-install/$mode-$stamp}
script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
repo_root=$(git -C "$script_dir" rev-parse --show-toplevel)

mkdir -p "$evidence"
provenance=$evidence/provenance.txt
{
    printf 'mode=%s\n' "$mode"
    printf 'container=%s\n' "$container"
    printf 'image=%s\n' "$image"
    printf 'harness_commit=%s\n' "$(git -C "$repo_root" rev-parse HEAD)"
} > "$provenance"

"$engine" build --pull "${network[@]}" -t "$image" "$script_dir"
printf 'image_id=%s\n' "$("$engine" image inspect --format '{{.Id}}' "$image")" >> "$provenance"

walk=(coga-walk pypi)
if [ "$mode" = main ]; then
    build_dir=$(mktemp -d "${TMPDIR:-/tmp}/coga-clean-install-build.XXXXXX")
    trap 'rm -rf "$build_dir"' EXIT
    git -C "$repo_root" fetch "$remote" main
    main_sha=$(git -C "$repo_root" rev-parse FETCH_HEAD)
    # Build from the fetched commit, never the working tree, so local edits
    # and untracked files cannot leak into the artifact under test.
    mkdir "$build_dir/src"
    git -C "$repo_root" archive "$main_sha" | tar -x -C "$build_dir/src"
    uv build --wheel --out-dir "$build_dir/dist" "$build_dir/src"
    wheel=$(ls "$build_dir"/dist/coga-*.whl)
    {
        printf 'main_commit=%s\n' "$main_sha"
        printf 'wheel=%s\n' "$(basename "$wheel")"
        printf 'wheel_sha256=%s\n' "$(sha256sum "$wheel" | cut -d' ' -f1)"
    } >> "$provenance"
    cp "$wheel" "$evidence/"
    walk=(coga-walk wheel "/tmp/$(basename "$wheel")")
fi

"$engine" run -d "${network[@]}" --name "$container" "$image" sleep infinity > /dev/null
if [ "$mode" = main ]; then
    "$engine" cp "$wheel" "$container:/tmp/"
fi

status=0
"$engine" exec "$container" "${walk[@]}" || status=$?

printf 'installed=%s\n' "$("$engine" exec "$container" coga --version 2>&1 || true)" >> "$provenance"
printf 'walk_exit=%s\n' "$status" >> "$provenance"
"$engine" cp "$container:/home/tester/evidence/." "$evidence/"

cat <<EOF

Walk exited $status. Evidence: $evidence
Steps: $evidence/steps.tsv (the last line is where the walk stopped)
Container kept: $container
  Drop in:  $engine exec -it $container bash
  Remove:   $engine rm -f $container
EOF
exit "$status"
