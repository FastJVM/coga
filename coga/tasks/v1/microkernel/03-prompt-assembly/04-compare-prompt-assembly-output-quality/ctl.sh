#!/bin/sh
# Disposable controller helpers for ticket 04 (tmux). Usage:
#   ctl.sh start <case> <arm> <rep>   | ctl.sh send "<line>" | ctl.sh key <tmux-key>
#   ctl.sh peek [lines]               | ctl.sh done          | ctl.sh stop
set -eu
T=$(cd "$(dirname "$0")" && pwd)
PY=${TRIAL_PY:-/tmp/claude-1000/-home-n-Code-coga/c40b5e78-888b-487d-b738-a313661983c0/scratchpad/pin/venv/bin/python}
LOGS=$T/runs/_pane
mkdir -p "$LOGS"
case "$1" in
  start)
    id="$2__$3__r$4"; : > "$LOGS/$id.log"; echo "$id" > "$LOGS/current"
    date -u +%FT%TZ > "$LOGS/$id.start"
    tmux kill-session -t qtrial 2>/dev/null || true
    tmux new-session -d -s qtrial -x 200 -y 50 "cd /tmp && $PY $T/adapter.py run $2 $3 $4; echo ADAPTER-EXIT=\$?; sleep 3600"
    tmux pipe-pane -t qtrial -o "cat >> $LOGS/$id.log" ;;
  send)
    id=$(cat "$LOGS/current"); printf '%s\t%s\n' "$(date -u +%FT%TZ)" "$2" >> "$LOGS/$id.inputs"
    tmux send-keys -t qtrial -l "$2"; sleep 1; tmux send-keys -t qtrial Enter ;;
  key)
    id=$(cat "$LOGS/current"); printf '%s\t<key %s>\n' "$(date -u +%FT%TZ)" "$2" >> "$LOGS/$id.inputs"
    tmux send-keys -t qtrial "$2" ;;
  peek) tmux capture-pane -pt qtrial -S -"${2:-40}" | grep -v '^\s*$' | tail -"${2:-40}" ;;
  done) grep -q "ADAPTER-EXIT=" "$LOGS/$(cat "$LOGS/current").log" && echo yes || echo no ;;
  stop) tmux kill-session -t qtrial ;;
esac
