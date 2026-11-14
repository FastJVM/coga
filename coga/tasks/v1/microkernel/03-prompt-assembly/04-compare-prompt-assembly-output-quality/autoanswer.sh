#!/bin/sh
# Disposable controller loop for authoring runs: answers Codex question forms per dialogues.json rules.
T=$(cd "$(dirname "$0")" && pwd)
first=${FIRST:-1}; prev=""; n=0
while true; do
  p=$(tmux capture-pane -pt qtrial -S -60 2>/dev/null)
  echo "$p" | grep -q "ADAPTER-EXIT=" && { echo EXITED; break; }
  if echo "$p" | grep -q "shift+← to answer\|Type your answer\|[0-9]\. Other"; then
    echo "$p" | grep -q "Type your answer\|[0-9]\. Other" || { tmux send-keys -t qtrial S-Left; sleep 2; p=$(tmux capture-pane -pt qtrial); }
    if [ $first = 1 ]; then k=brief; first=0
    elif echo "$p" | tail -12 | grep -qi "look right\|anything to change\|finish the draft\|before you launch"; then k=validate
    else k=any_question; fi
    echo "FORM -> $k"; "$T/answer.sh" $k >/dev/null; prev=FORM; sleep 5; continue
  fi
  if echo "$p" | grep -q "Working ("; then n=0; s=WORKING; else n=$((n+1)); [ $n -ge 3 ] && s=IDLE || s=$prev; fi
  [ "$s" != "$prev" ] && [ "$s" = IDLE ] && echo IDLE
  prev=$s; sleep 5
done
