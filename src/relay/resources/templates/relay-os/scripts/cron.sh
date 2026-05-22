#!/bin/sh
# scripts/cron.sh — entry point for system cron.
#
# Usage: set up a user crontab entry like:
#   0 * * * * cd /path/to/relay-repo && relay-os/scripts/cron.sh
#
# Acquires a pidfile lock so only one instance runs at a time.
# Runs `relay recurring`, which scans templates and scaffolds + launches
# any due tasks. Exits non-zero if relay returns non-zero.
#
# Cron has no TTY: templates meant to run unattended this way should be
# `mode: auto` or `mode: script`. An interactive template will scaffold
# but fail to launch without a terminal.

set -eu

PIDFILE="${RELAY_CRON_PIDFILE:-/tmp/relay-cron.pid}"

# Acquire lock via pidfile + kill -0 probe.
if [ -e "$PIDFILE" ]; then
    if kill -0 "$(cat "$PIDFILE" 2>/dev/null)" 2>/dev/null; then
        echo "relay cron already running (pid $(cat "$PIDFILE"))" >&2
        exit 0
    fi
    rm -f "$PIDFILE"
fi
echo "$$" > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT INT TERM

exec relay recurring
