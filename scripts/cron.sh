#!/usr/bin/env bash
# Cron entry point for Relay recurring tasks.
#
# Set up in your crontab, e.g.:
#   0 * * * * cd /path/to/relay && scripts/cron.sh
#
# Acquires a pidfile lock so at most one instance runs at a time. If
# another instance is already running, exits silently with status 0.
# If the machine is off when the cron fires, nothing runs; the next
# run picks up any tasks that were due but missed.

set -euo pipefail

PIDFILE="/tmp/relay-cron.pid"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Pidfile lock. If the file exists and the PID inside is still alive,
# another cron run is in progress — exit.
if [[ -f "$PIDFILE" ]]; then
  existing_pid=$(cat "$PIDFILE" 2>/dev/null || echo "")
  if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
    echo "[relay cron] another instance is running (pid $existing_pid), exiting" >&2
    exit 0
  fi
  # Stale pidfile — process is gone. Fall through and reclaim.
fi

echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT

cd "$REPO_ROOT"

# Put relay on PATH if it isn't already.
if ! command -v relay >/dev/null 2>&1; then
  export PATH="$REPO_ROOT/cli:$PATH"
fi

# Check for due recurring tasks. Scheduling detection itself is a stub
# in v1 (spec flags this as an open question) — the command will print
# the templates it found and exit cleanly until scheduling logic lands.
relay create --check-recurring

# Future: auto-launch any newly created `mode: auto` tasks here.
