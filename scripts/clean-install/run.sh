#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -lt 2 || $# -gt 3 || ! $1 =~ ^(pypi|main)$ ]]; then
    echo "usage: $0 pypi|main CONTAINER [USER]" >&2
    exit 2
fi
artifact=$1
container=$2
operator=${3:-installer}
if [[ ! $container =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]*$ ]]; then
    echo "CONTAINER must be a Docker name, not a path" >&2
    exit 2
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(git -C "$script_dir" rev-parse --show-toplevel)
image=${COGA_CLEAN_INSTALL_IMAGE:-coga-clean-install:py311}
network=${COGA_CLEAN_INSTALL_NETWORK:-bridge}
evidence="$repo_root/.coga/clean-install/$container"
# Refuse to overwrite evidence or reuse a user's existing container.
if [[ -e $evidence ]]; then
    echo "Evidence already exists: $evidence; choose a new container name" >&2
    exit 2
fi
if docker container inspect "$container" >/dev/null 2>&1; then
    echo "Container already exists: $container; choose a new name" >&2
    exit 2
fi
mkdir -p "$evidence"
exec > >(tee "$evidence/host.txt") 2>&1
temporary_dir=
created=false

finish() {
    local status=$?
    trap - EXIT
    if [[ $created == true ]]; then
        if ! docker cp "$container:/home/coga/clean-install/evidence" "$evidence/container"; then
            echo "Could not copy container evidence; inspect the retained container."
            [[ $status -ne 0 ]] || status=1
        fi
        printf 'Inspect or continue: docker exec -it %q bash\n' "$container"
    fi
    [[ -z $temporary_dir ]] || rm -rf -- "$temporary_dir"
    printf 'artifact=%s\nnetwork=%s\nexit_code=%s\n' "$artifact" "$network" "$status" > "$evidence/result.txt"
    printf 'Evidence: %s\n' "$evidence"
    exit "$status"
}
trap finish EXIT
trap 'status=$?; printf "FAILED (exit %s): %s\n" "$status" "$BASH_COMMAND" >&2; exit "$status"' ERR

run() {
    printf '\n+'
    printf ' %q' "$@"
    printf '\n'
    "$@"
}

if [[ -z ${COGA_CLEAN_INSTALL_IMAGE:-} ]]; then
    # BuildKit accepts only default|host|none, so pass only a non-default network.
    build_network=()
    [[ $network == bridge ]] || build_network=(--network "$network")
    run docker build --pull "${build_network[@]}" -t "$image" "$script_dir"
fi
run docker image inspect --format '{{.Id}}' "$image"
docker image inspect --format '{{.Id}}' "$image" > "$evidence/image.txt"
if [[ $artifact == main ]]; then
    # Export the fetched commit, never the caller's working tree or editable install.
    run git -C "$repo_root" fetch origin main
    source_sha=$(git -C "$repo_root" rev-parse FETCH_HEAD)
    printf 'origin/main=%s\n' "$source_sha" | tee "$evidence/source.txt"
    temporary_dir=$(mktemp -d)
    mkdir "$temporary_dir/source"
    git -C "$repo_root" archive "$source_sha" | tar -x -C "$temporary_dir/source"
    run uv build --wheel --no-sources --out-dir "$evidence/wheels" "$temporary_dir/source"
    wheels=("$evidence"/wheels/*.whl)
    [[ ${#wheels[@]} -eq 1 && -f ${wheels[0]} ]]
    wheel=${wheels[0]}
    run sha256sum "$wheel"
fi

run docker create --network "$network" --name "$container" "$image"
created=true
if [[ $artifact == main ]]; then
    container_wheel="/tmp/$(basename -- "$wheel")"
    run docker cp "$wheel" "$container:$container_wheel"
fi
run docker start "$container"
if [[ $artifact == pypi ]]; then
    run docker exec "$container" coga-clean-install pypi "$operator"
else
    run docker exec "$container" coga-clean-install wheel "$operator" "$container_wheel"
fi
