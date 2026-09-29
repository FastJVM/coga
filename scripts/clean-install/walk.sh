#!/usr/bin/env bash
# Walk the documented install path inside the clean-install container.
#
#   coga-walk pypi                 install the current PyPI release, then init
#   coga-walk wheel PATH           install a built wheel, then init
#   coga-walk ticket "FIRST TASK"  attended: run `coga ticket` in the scratch repo
#
# Every step's command and exit code is appended to ~/evidence/steps.tsv and
# its output to ~/evidence/transcript.txt. The walk stops at the first failing
# step, so the last line of steps.tsv is exactly where it failed.
set -uo pipefail

evidence=$HOME/evidence
repo=$HOME/scratch
user_name=${COGA_WALK_USER:-tester}
mkdir -p "$evidence"
exec > >(tee -a "$evidence/transcript.txt") 2>&1

step() {
    local name=$1
    shift
    printf '\n== %s: %s\n' "$name" "$*"
    "$@"
    local status=$?
    printf '%s\t%s\t%s\n' "$name" "$status" "$*" >> "$evidence/steps.tsv"
    if [ "$status" -ne 0 ]; then
        printf '\n!! %s failed with exit %s; stopping the walk\n' "$name" "$status"
        exit "$status"
    fi
}

install_and_init() {
    local source=$1
    step install uv tool install "$source"
    step version coga --version
    step git-init git init "$repo"
    # A fresh user has no Git identity, and `coga init` requires one to
    # commit. Setting it is ordinary Git setup, not a Coga step.
    step git-identity git config --global user.name "Clean Install Tester"
    step git-email git config --global user.email "tester@example.invalid"
    cd "$repo" || exit 1
    step coga-init coga init --user "$user_name"
    step validate coga validate --json
    printf '\nReached coga init. Next is attended: log in to an agent CLI, then\n'
    printf '  coga-walk ticket "<first task>"\n'
}

case "${1:-}" in
    pypi)
        install_and_init coga
        ;;
    wheel)
        if [ -z "${2:-}" ]; then
            echo "usage: coga-walk wheel PATH" >&2
            exit 2
        fi
        install_and_init "$2"
        ;;
    ticket)
        if [ -z "${2:-}" ]; then
            echo 'usage: coga-walk ticket "FIRST TASK"' >&2
            exit 2
        fi
        cd "$repo" || exit 1
        step ticket coga ticket "$2"
        ;;
    *)
        echo 'usage: coga-walk pypi | wheel PATH | ticket "FIRST TASK"' >&2
        exit 2
        ;;
esac
