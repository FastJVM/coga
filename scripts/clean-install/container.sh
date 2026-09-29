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

run id
run python --version
run git --version
run uv --version
if [[ $mode == pypi ]]; then
    run uv tool install coga
else
    run sha256sum "$3"
    run uv tool install "$3"
fi
run coga --version
run uv tool list
cd "$repo"
run git init -b main
run git config --local user.name "Coga install harness"
run git config --local user.email "install-harness@example.invalid"
run coga init --user "$operator"
printf 'coga init passed; attended coga ticket has not run\n' | tee "$evidence/init-passed.txt"
echo 'Install and authenticate an agent in this container, then run:'
echo '  coga-clean-install ticket "Write a hello-world script" --agent claude'
