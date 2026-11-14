#!/bin/sh
# Disposable: answer every pending Codex question form with one fixed dialogues.json line.
# Usage: answer.sh brief|any_question|validate
set -eu
T=$(cd "$(dirname "$0")" && pwd)
A=$(python3 -c "import json,sys;print(json.load(open('$T/dialogues.json'))[sys.argv[1]])" "$1")
id=$(cat "$T/runs/_pane/current")
tmux capture-pane -pt qtrial | grep -q "Type your answer\|[0-9]\. Other" || { tmux send-keys -t qtrial S-Left; sleep 2; }
for i in 1 2 3 4 5 6; do
  p=$(tmux capture-pane -pt qtrial)
  if echo "$p" | grep -q "Type your answer"; then
    tmux send-keys -t qtrial -l "$A"
  elif n=$(echo "$p" | grep -oE '^ +(›)? *[0-9]+\. Other' | grep -oE '[0-9]+' | tail -1) && [ -n "$n" ]; then
    tmux send-keys -t qtrial "$n"; sleep 1; tmux send-keys -t qtrial -l "$A"
  else
    break
  fi
  sleep 1; tmux send-keys -t qtrial Enter
  printf '%s\t<form answer> %s\n' "$(date -u +%FT%TZ)" "$A" >> "$T/runs/_pane/$id.inputs"
  sleep 3
done
tmux capture-pane -pt qtrial | grep -v '^\s*$' | tail -8
