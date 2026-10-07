# Shared host-side helpers for the macOS clean-install drivers (aws-mac.sh,
# owned-mac.sh); sourced, not run. Each driver sets script_dir, repo_root and
# evidence, and its ssh_args sets ssh_opts and target, before calling these.

remote_dir=/tmp/coga-clean-install

run() {
    # Trace to stderr so a command's own stdout can be captured cleanly.
    {
        printf '\n+'
        printf ' %q' "$@"
        printf '\n'
    } >&2
    "$@"
}

record() {
    # Every resource ID is written the moment it exists, so teardown can find
    # everything a failed setup left behind.
    printf '%s=%q\n' "$1" "$2" >> "$evidence/resources.env"
    printf -v "$1" '%s' "$2"
    printf 'recorded %s=%s\n' "$1" "$2"
}

record_output() {
    # Capture separately: record KEY "$(cmd ...)" would hide the exit code.
    local key=$1 value
    shift
    value=$("$@")
    record "$key" "$value"
}

checksum() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1"; else shasum -a 256 "$1"; fi
}

mac() {
    # ssh joins remote words with spaces for the remote shell; quote each one.
    ssh "${ssh_opts[@]}" "$target" "$(printf '%q ' "$@")"
}

copy_walk_scripts() {
    run mac mkdir -m 755 -p "$remote_dir"
    run scp "${ssh_opts[@]}" "$script_dir/macos-walk.sh" "$script_dir/container.sh" \
        "$target:$remote_dir/"
    run mac chmod 755 "$remote_dir/macos-walk.sh" "$remote_dir/container.sh"
}

mac_walk() {
    # mac_walk NAME pypi|main MAC_USER OPERATOR: one fresh-user install walk.
    local name=$1 artifact=$2 user=$3 operator=$4
    [[ $user =~ ^[a-z][a-z0-9]*$ ]] || { echo "MAC_USER must be a short lowercase name" >&2; exit 2; }
    local out="$evidence/walks/$user"
    [[ ! -e $out ]] || { echo "Walk evidence exists: $out; choose a new MAC_USER" >&2; exit 2; }
    mkdir -p "$out"
    local password
    password=$(openssl rand -hex 12)
    (umask 077 && printf '%s\n' "$password" > "$out/password.txt")

    local mode=pypi remote_wheel=
    if [[ $artifact == main ]]; then
        # Export the fetched commit, never the caller's working tree.
        run git -C "$repo_root" fetch origin main
        local sha tmp wheels
        sha=$(git -C "$repo_root" rev-parse FETCH_HEAD)
        printf 'origin/main=%s\n' "$sha" | tee "$out/source.txt"
        tmp=$(mktemp -d)
        mkdir "$tmp/source"
        git -C "$repo_root" archive "$sha" | tar -x -C "$tmp/source"
        run uv build --wheel --no-sources --out-dir "$out/wheels" "$tmp/source"
        rm -rf -- "$tmp"
        wheels=("$out"/wheels/*.whl)
        [[ ${#wheels[@]} -eq 1 && -f ${wheels[0]} ]]
        run checksum "${wheels[0]}"
        remote_wheel="$remote_dir/$(basename -- "${wheels[0]}")"
        run scp "${ssh_opts[@]}" "${wheels[0]}" "$target:$remote_wheel"
        # The build and SCP inherit the private evidence umask. The fresh walk
        # user must be able to read this non-secret artifact owned by the admin.
        run mac chmod 644 "$remote_wheel"
        mode=wheel
    fi
    local status=0
    local walk_command=(bash "$remote_dir/macos-walk.sh" walk
        "$mode" "$operator" "$user" "$password" ${remote_wheel:+"$remote_wheel"})
    if [[ ${KIND:-} == host ]]; then
        walk_command=(env "COGA_MAC_WALK_OWNER=$WALK_OWNER" "${walk_command[@]}")
    fi
    # Passwords stay out of the terminal and host.txt command trace.
    mac "${walk_command[@]}" || status=$?
    fetch_evidence "$user" "$out"
    printf 'artifact=%s\nmac_user=%s\nexit_code=%s\n' "$artifact" "$user" "$status" | tee "$out/result.txt"
    echo "Continue attended: $0 ssh $name sudo -iu $user"
    return "$status"
}

fetch_evidence() {
    mkdir -p "$2/mac"
    mac sudo tar -C "/Users/$1/clean-install" -cf - evidence | tar -x -C "$2/mac" ||
        echo "Could not copy walk evidence for $1; inspect over ssh"
}

mac_vnc() {
    # Screen Sharing on a disposable Mac, reached only through an SSH tunnel.
    local password
    password=$(openssl rand -hex 12)
    (umask 077 && printf '%s\n' "$password" > "$evidence/vnc-password.txt")
    # Do not trace the password argument.
    mac bash "$remote_dir/macos-walk.sh" vnc "$password"
    printf 'Tunnel:  ssh'
    printf ' %q' "${ssh_opts[@]}" -N -L 5900:localhost:5900 "$target"
    printf '\nThen open vnc://localhost:5900 as %s; password in %s\n' \
        "${target%@*}" "$evidence/vnc-password.txt"
}
