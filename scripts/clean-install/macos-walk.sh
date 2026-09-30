#!/bin/bash
# Mac-side half of the macOS clean-install harness. aws-mac.sh copies this
# file and container.sh to /tmp/coga-clean-install/ on the EC2 Mac and runs it
# as ec2-user. Keep it to macOS's stock Bash 3.2.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)

fail() {
    echo "$*" >&2
    exit 1
}

case ${1:-} in
baseline)
    # What the AMI ships, recorded before reset. Never call git here: without
    # Command Line Tools that would start the install prompt early.
    sw_vers
    uname -m
    id
    printf 'xcode-select -p: '
    xcode-select -p 2>&1 || true
    pkgutil --pkgs | grep -i CLTools || echo 'no CLTools receipts'
    ls -d /opt/homebrew/bin/brew /usr/local/bin/brew 2>/dev/null || echo 'no brew'
    printf '/etc/paths:\n'
    cat /etc/paths
    ls /etc/paths.d
    ;;
reset)
    # EC2 Mac AMIs ship Command Line Tools for their Homebrew. Remove them
    # (Apple's uninstall, plus receipts) so the first git call on this machine
    # behaves as it does on a new Mac: the /usr/bin shim asks to install them.
    sudo rm -rf /Library/Developer/CommandLineTools
    for pkg in $(pkgutil --pkgs | grep -i CLTools || true); do
        sudo pkgutil --forget "$pkg" >/dev/null
    done
    sudo xcode-select --reset
    if xcode-select -p >/dev/null 2>&1; then
        fail "A developer directory is still selected: $(xcode-select -p)"
    fi
    # A new user's login shell must reach only the shim, not a Homebrew git.
    resolved=$(env -i HOME=/var/empty /bin/zsh -lc 'command -v git' || true)
    [ "$resolved" = /usr/bin/git ] || fail "A fresh login shell resolves git to '$resolved', not /usr/bin/git"
    echo 'Command Line Tools removed; git is the /usr/bin shim for new users'
    ;;
walk)
    if [ $# -lt 5 ] || [ $# -gt 6 ]; then
        fail "usage: $0 walk pypi|wheel OPERATOR MAC_USER PASSWORD [WHEEL]"
    fi
    mode=$2 operator=$3 user=$4 password=$5 wheel=${6:-}
    if id "$user" >/dev/null 2>&1; then
        fail "macOS user $user already exists; choose a new name for a fresh home"
    fi
    sudo sysadminctl -addUser "$user" -fullName "Coga clean install" \
        -password "$password" -home "/Users/$user"
    sudo createhomedir -c -u "$user" >/dev/null
    # Fresh login shell as the new user: install uv as its docs say, then run
    # the same install/init walk the Linux container runs.
    set -- "$here/container.sh" "$mode" "$operator" ${wheel:+"$wheel"}
    sudo -H -u "$user" /bin/zsh -lc '
        cd "$HOME"
        printf "\n+ curl -LsSf https://astral.sh/uv/install.sh | sh\n"
        curl -LsSf https://astral.sh/uv/install.sh | sh || exit
        export PATH="$HOME/.local/bin:$PATH"
        exec bash "$0" "$@"
    ' "$@"
    ;;
ticket)
    # Attended continuation, run by the walk user after agent login.
    shift
    export PATH="$HOME/.local/bin:$PATH"
    exec bash "$here/container.sh" ticket "$@"
    ;;
vnc)
    [ $# -eq 2 ] || fail "usage: $0 vnc PASSWORD"
    sudo dscl . -passwd /Users/ec2-user "$2"
    sudo launchctl enable system/com.apple.screensharing
    sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.screensharing.plist 2>/dev/null || true
    echo 'Screen Sharing enabled on localhost:5900 (reach it through the SSH tunnel)'
    ;;
*)
    fail "usage: $0 baseline | reset | walk ... | ticket TITLE [--agent NAME] | vnc PASSWORD"
    ;;
esac
