#!/bin/sh
# Disposable controller helpers (tmux). Usage:
#   ctl.sh start <case> <arm> <rep>   | ctl.sh send "<line>" | ctl.sh key <tmux-key>
#   ctl.sh peek [lines]               | ctl.sh tokens        | ctl.sh stop
set -eu
T=$(cd "$(dirname "$0")" && pwd)
PY=${TRIAL_PY:-/tmp/claude-1000/-home-n-Code-coga/ca74c63f-79b7-4898-85c1-336b1613e156/scratchpad/pin/venv/bin/python}
LOGS=$T/runs/_pane
mkdir -p "$LOGS"
case "$1" in
  start)
    id="$2__$3__r$4"; : > "$LOGS/$id.log"; echo "$id" > "$LOGS/current"
    date -u +%FT%TZ > "$LOGS/$id.start"
    tmux kill-session -t trial 2>/dev/null || true
    tmux new-session -d -s trial -x 200 -y 50 "cd /tmp && $PY $T/adapter.py run $2 $3 $4; echo ADAPTER-EXIT=\$?; sleep 3600"
    tmux pipe-pane -t trial -o "cat >> $LOGS/$id.log" ;;
  send)
    id=$(cat "$LOGS/current"); printf '%s\t%s\n' "$(date -u +%FT%TZ)" "$2" >> "$LOGS/$id.inputs"
    tmux send-keys -t trial -l "$2"; sleep 1; tmux send-keys -t trial Enter ;;
  key)
    id=$(cat "$LOGS/current"); printf '%s\t<key %s>\n' "$(date -u +%FT%TZ)" "$2" >> "$LOGS/$id.inputs"
    tmux send-keys -t trial "$2" ;;
  peek) tmux capture-pane -pt trial -S -"${2:-40}" | grep -v '^\s*$' | tail -"${2:-40}" ;;
  tokens)
    f=$(grep -l "\"cwd\":\"/tmp/coga-prompt-trial-667707cc" $(find ~/.codex/sessions -name "*.jsonl" -newer "$LOGS/$(cat "$LOGS/current").start") /dev/null | head -1)
    [ -n "$f" ] && grep '"token_count"' "$f" | tail -1 | grep -o '"total_token_usage":{[^}]*}' || echo none ;;
  stop) tmux kill-session -t trial ;;
esac
