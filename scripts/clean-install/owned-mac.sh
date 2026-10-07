#!/usr/bin/env bash
# Host-side driver for the macOS clean-install harness on owner-provided Macs
# reached over SSH: a disposable Tart VM on Apple silicon, or an ordinary Mac
# attached as-is. See the coga/testing/clean-install/macos-owned topic.
set -Eeuo pipefail
umask 077

usage() {
    cat >&2 <<'EOF'
usage (SSH_HOST is an ssh destination, e.g. tester@mac-mini.local):
  owned-mac.sh preflight SSH_HOST
  owned-mac.sh vm NAME SSH_HOST [IMAGE]      Apple silicon: fresh disposable VM
  owned-mac.sh attach NAME SSH_HOST          any Mac as-is: compatibility only
  owned-mac.sh walk NAME pypi|main MAC_USER [OPERATOR]
  owned-mac.sh ssh NAME [REMOTE-COMMAND ...]
  owned-mac.sh vnc NAME                      VM only
  owned-mac.sh status NAME
  owned-mac.sh cleanup NAME
EOF
    exit 2
}

[[ $# -ge 2 ]] || usage
command=$1
shift

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(git -C "$script_dir" rev-parse --show-toplevel)
# shellcheck source=mac-common.sh
source "$script_dir/mac-common.sh"

default_image=ghcr.io/cirruslabs/macos-tahoe-vanilla:latest

hostc() {
    # A login shell on the physical Mac, so Homebrew's tart is on PATH.
    ssh -o ConnectTimeout=15 "$HOST" "$(printf '%q ' /bin/zsh -lc "$(printf '%q ' "$@")")"
}

load() {
    run_name=$1
    if [[ ! $run_name =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
        echo "NAME must be lowercase letters, digits and dashes" >&2
        exit 2
    fi
    evidence="$repo_root/.coga/clean-install/$run_name"
    if [[ $command == vm || $command == attach ]]; then
        if [[ -e $evidence ]]; then
            echo "Evidence already exists: $evidence; choose a new NAME" >&2
            exit 2
        fi
        mkdir -p "$evidence"
        exec > >(tee -a "$evidence/host.txt") 2>&1
        trap 'status=$?; printf "FAILED (exit %s): %s\nState so far is in %s; run: %q cleanup %q\n" "$status" "$BASH_COMMAND" "$evidence/resources.env" "$0" "$run_name" >&2; exit "$status"' ERR
        return
    fi
    if [[ ! -f $evidence/resources.env ]]; then
        echo "No run named $run_name ($evidence/resources.env)" >&2
        exit 2
    fi
    # shellcheck disable=SC1091
    source "$evidence/resources.env"
    remote_dir=${REMOTE_DIR:-/tmp/coga-clean-install}
    # An interactive ssh session keeps its terminal; everything else is logged.
    [[ $command == ssh ]] && return
    exec > >(tee -a "$evidence/host.txt") 2>&1
    printf '\n=== %s %s %s\n' "$(date -u +%FT%TZ)" "$command" "$run_name"
}

ssh_args() {
    if [[ $KIND == vm ]]; then
        # The VM sits on the physical Mac's private NAT; jump through the Mac.
        ssh_opts=(-i "$evidence/key.pem" -o IdentitiesOnly=yes
            -o StrictHostKeyChecking=accept-new
            -o UserKnownHostsFile="$evidence/known_hosts" -o ConnectTimeout=15
            -o ProxyJump="$HOST")
        target="$VM_USER@$VM_IP"
    else
        ssh_opts=(-o ConnectTimeout=15)
        target=$HOST
    fi
}

preflight() {
    [[ $# -eq 1 ]] || usage
    HOST=$1
    # Read-only: what the Mac is, and whether it can host a disposable VM.
    hostc sh -c '
        sw_vers; uname -m
        printf "cpus=%s memory_bytes=%s\n" "$(sysctl -n hw.ncpu)" "$(sysctl -n hw.memsize)"
        df -h "$HOME" | tail -1
        if command -v tart >/dev/null; then tart --version; tart list; else echo "tart: not installed"; fi
        sudo -n true 2>/dev/null && echo "sudo: passwordless" || echo "sudo: needs a password"
    '
}

install_vm_key() {
    # Cirrus Labs vanilla images accept admin/admin over SSH. Use it once, via
    # SSH_ASKPASS, to install this run's key; every later call uses the key.
    ssh-keygen -q -t ed25519 -N '' -C "$VM" -f "$evidence/key.pem"
    printf '#!/bin/sh\nprintf "%%s\\n" "${COGA_MAC_VM_PASSWORD:-admin}"\n' > "$evidence/askpass.sh"
    chmod 700 "$evidence/askpass.sh"
    echo "Waiting for SSH in $VM ($VM_USER@$VM_IP via $HOST)"
    local tries=0
    until SSH_ASKPASS="$evidence/askpass.sh" SSH_ASKPASS_REQUIRE=force \
        ssh -o ProxyJump="$HOST" -o PubkeyAuthentication=no \
            -o StrictHostKeyChecking=accept-new \
            -o UserKnownHostsFile="$evidence/known_hosts" -o ConnectTimeout=15 \
            "$VM_USER@$VM_IP" 'umask 077; mkdir -p .ssh; cat >> .ssh/authorized_keys' \
            < "$evidence/key.pem.pub"; do
        (( ++tries < ${COGA_MAC_SSH_TRIES:-30} )) || { echo 'VM SSH never came up' >&2; false; }
        sleep "${COGA_MAC_SSH_WAIT:-10}"
    done
}

vm() {
    [[ $# -ge 2 && $# -le 3 ]] || usage
    load "$1"
    record KIND vm
    record HOST "$2"
    record IMAGE "${3:-${COGA_MAC_VM_IMAGE:-$default_image}}"
    local arch
    arch=$(hostc uname -m)
    if [[ $arch != arm64 ]]; then
        echo "$HOST is $arch: macOS VMs need Apple silicon. Use: $0 attach $1 $HOST" >&2
        false
    fi
    record_output TART_VERSION hostc tart --version
    record VM "coga-clean-install-$1"
    # A clone is copy-on-write from Tart's local image cache; the first pull
    # downloads the whole image.
    run hostc tart clone "$IMAGE" "$VM"
    record VM_CREATED "$(date -u +%FT%TZ)"
    run hostc sh -c 'nohup tart run --no-graphics "$1" > "/tmp/$1.log" 2>&1 < /dev/null &' sh "$VM"
    record_output VM_IP hostc tart ip --wait 300 "$VM"
    record VM_USER "${COGA_MAC_VM_USER:-admin}"
    install_vm_key
    ssh_args
    copy_walk_scripts
    run mac bash "$remote_dir/macos-walk.sh" baseline | tee "$evidence/baseline.txt"
    # This VM exists only for this run; reset verifies it reaches the git shim.
    run mac bash "$remote_dir/macos-walk.sh" designate-disposable "$VM"
    run mac bash "$remote_dir/macos-walk.sh" reset
    echo "VM ready. Next: $0 walk $1 pypi|main MAC_USER"
}

attach() {
    [[ $# -eq 2 ]] || usage
    load "$1"
    record KIND host
    record HOST "$2"
    ssh_args
    record_output ARCH mac uname -m
    if ! mac sudo -n true; then
        echo "The SSH account on $HOST needs passwordless sudo to create walk users" >&2
        false
    fi
    record_output WALK_OWNER openssl rand -hex 16
    record REMOTE_DIR "/tmp/coga-clean-install-$1"
    remote_dir=$REMOTE_DIR
    # Refuse a pre-existing directory; never overwrite another run's scripts.
    run mac mkdir -m 755 "$remote_dir"
    record SCRIPTS_CREATED yes
    copy_walk_scripts
    run mac bash "$remote_dir/macos-walk.sh" baseline | tee "$evidence/baseline.txt"
    cat <<EOF
Attached $HOST as an ordinary Mac. Nothing machine-wide was changed or reset:
walks there test compatibility with this Mac's existing Command Line Tools,
Homebrew and /etc/paths (see baseline.txt), not a fresh install.
Next: $0 walk $1 pypi|main MAC_USER
EOF
}

walk() {
    [[ $# -ge 3 && $# -le 4 && $2 =~ ^(pypi|main)$ ]] || usage
    load "$1"
    ssh_args
    mac_walk "$1" "$2" "$3" "${4:-installer}"
}

vnc() {
    [[ $# -eq 1 ]] || usage
    load "$1"
    if [[ $KIND != vm ]]; then
        echo "vnc replaces the admin password; use the Mac's own Screen Sharing on an attached host" >&2
        exit 2
    fi
    ssh_args
    mac_vnc
}

status() {
    [[ $# -eq 1 ]] || usage
    load "$1"
    if [[ $KIND == vm ]]; then
        hostc tart list
    else
        ssh_args
        mac dscl . -list /Users
    fi
}

cleanup() {
    [[ $# -eq 1 ]] || usage
    load "$1"
    if [[ $KIND == vm ]]; then
        if [[ -n ${VM_CREATED:-} && -z ${VM_DELETED:-} ]]; then
            run hostc tart stop "$VM" || true
            run hostc tart delete "$VM"
            record VM_DELETED "$(date -u +%FT%TZ)"
        fi
        return
    fi
    # An attached Mac keeps everything machine-wide; remove only what walks made.
    ssh_args
    local dir user key
    for dir in "$evidence"/walks/*/; do
        [[ -d $dir ]] || continue
        user=$(basename -- "$dir")
        key="DELETED_USER_$user"
        [[ -z ${!key:-} ]] || continue
        [[ -n ${WALK_OWNER:-} ]] || { echo 'No account ownership token; manual inspection required' >&2; exit 1; }
        run mac bash "$remote_dir/macos-walk.sh" delete-owned-user "$user" "$WALK_OWNER"
        record "$key" "$(date -u +%FT%TZ)"
    done
    if [[ -n ${SCRIPTS_CREATED:-} && -z ${SCRIPTS_REMOVED:-} ]]; then
        run mac rm -rf "$remote_dir"
        record SCRIPTS_REMOVED "$(date -u +%FT%TZ)"
    fi
}

case $command in
preflight | vm | attach | walk | vnc | status | cleanup) "$command" "$@" ;;
ssh)
    load "$1"
    shift
    ssh_args
    exec ssh -t "${ssh_opts[@]}" "$target" "$@"
    ;;
*) usage ;;
esac
