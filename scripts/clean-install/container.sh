#!/usr/bin/env bash
set -euo pipefail

work_root="$HOME/clean-install"
evidence="$work_root/evidence"
repo="$work_root/repo"

if [[ ${1:-} == ticket && $# -ge 2 ]]; then
    shift
    if [[ ! -f $evidence/init-passed.txt ]]; then
        echo "Run the install/init phase successfully before the attended ticket step" >&2
        exit 2
    fi
    cd "$repo"
    # Keep both descriptors on the terminal: coga ticket requires a real TTY.
    # Login and agent conversation are deliberately outside the install transcript.
    printf '+ coga ticket' | tee -a "$evidence/ticket.txt"
    printf ' %q' "$@" | tee -a "$evidence/ticket.txt"
    printf '\n' | tee -a "$evidence/ticket.txt"
    status=0
    coga ticket "$@" || status=$?
    printf 'ticket_exit_code=%s\n' "$status" | tee -a "$evidence/ticket.txt"
    exit "$status"
fi

if [[ $# -lt 2 || $# -gt 3 || ! $1 =~ ^(pypi|wheel)$ ]]; then
    echo "usage: coga-clean-install pypi USER | wheel USER WHEEL | ticket TITLE [--agent NAME]" >&2
    exit 2
fi
mode=$1
operator=$2
if [[ ($mode == wheel && ($# -ne 3 || ! -f $3)) || ($mode == pypi && $# -ne 2) ]]; then
    echo "Supply one existing wheel for wheel mode; no wheel for PyPI mode" >&2
    exit 2
fi
if [[ $(id -u) -eq 0 ]]; then
    echo "Run as the image's fresh non-root coga user" >&2
    exit 2
fi
if [[ -e $work_root ]] || command -v coga >/dev/null 2>&1; then
    echo "This is not a clean install; start a new container" >&2
    exit 2
fi
# Both harnesses test the declared Python floor: the Linux image and the macOS
# walk pin uv to 3.11. Refuse any other interpreter rather than record a walk
# that silently ran on it.
required_python=3.11
if [[ -z ${UV_PYTHON:-} || ${UV_PYTHON_DOWNLOADS:-} != never ]]; then
    echo "Pin uv to Python $required_python: set UV_PYTHON and UV_PYTHON_DOWNLOADS=never" >&2
    exit 2
fi
mkdir -p "$evidence" "$repo"

run() {
    local command status
    printf -v command '%q ' "$@"
    printf '\n+ %s\n' "$command" | tee -a "$evidence/transcript.txt"
    if "$@" 2>&1 | tee -a "$evidence/transcript.txt"; then
        printf 'PASS\t%s\n' "$command" >> "$evidence/steps.txt"
    else
        status=$?
        printf 'FAIL (exit %s)\t%s\n' "$status" "$command" | tee -a "$evidence/steps.txt"
        exit "$status"
    fi
}

checksum() {
    # GNU coreutils on Linux; macOS ships shasum.
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1"; else shasum -a 256 "$1"; fi
}

check_python() {
    local version
    version=$("$1" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')
    echo "Python $version at $1"
    if [[ $version != "$required_python".* ]]; then
        echo "Python $version is not the required $required_python" >&2
        return 2
    fi
}

run id
# On a fresh Mac, this first git call is where the Command Line Tools prompt appears.
run git --version
run uv --version
run uv python find "$UV_PYTHON"
run check_python "$(uv python find "$UV_PYTHON")"
if [[ $mode == pypi ]]; then
    run uv tool install --python "$UV_PYTHON" coga
else
    run checksum "$3"
    run uv tool install --python "$UV_PYTHON" "$3"
fi
run coga --version
run uv tool list
cd "$repo"
run git init -b main
run git config --local user.name "Coga install harness"
run git config --local user.email "install-harness@example.invalid"
run coga init --user "$operator"
run coga validate --json
printf 'coga init passed; attended coga ticket has not run\n' | tee "$evidence/init-passed.txt"
echo 'Install and authenticate an agent in this container, then run:'
echo '  coga-clean-install ticket "Write a hello-world script" --agent claude'
