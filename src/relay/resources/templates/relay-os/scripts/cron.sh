#!/bin/sh
# scripts/cron.sh — entry point for system cron.
#
# Usage: set up a user crontab entry like:
#   0 * * * * cd /path/to/relay-repo && relay-os/scripts/cron.sh
#
# Acquires a pidfile lock so only one instance runs at a time.
# Runs `relay create --check-recurring` which scans templates and
# creates any due tasks. Exits non-zero if relay returns non-zero.

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

exec relay create --check-recurring
