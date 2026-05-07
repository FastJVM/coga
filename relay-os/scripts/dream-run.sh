#!/usr/bin/env bash
# relay-os/scripts/dream-run.sh — manually scaffold and launch a Dream pass.
#
# Bypasses the recurring scheduler. We're not auto-firing recurring tasks
# yet (see `relay/current-direction`), so this is the hand-driven entry
# point for a Dream run. Drops a fresh `dream-run-<timestamp>` task into
# `relay-os/tasks/`, wires it to the `bootstrap/dream-run` workflow with
# the dispatch contract from `dream-body.md` as its description, then
# hands off to `relay launch`.
#
# Run from the repo root:
#   relay-os/scripts/dream-run.sh
#
# Override owner/assignee per invocation if needed:
#   RELAY_DREAM_OWNER=marc RELAY_DREAM_ASSIGNEE=claude1 relay-os/scripts/dream-run.sh

set -euo pipefail

if [[ ! -d relay-os ]]; then
    echo "Run from a relay repo root (the directory containing relay-os/)." >&2
    exit 2
fi

owner="${RELAY_DREAM_OWNER:-nick}"
assignee="${RELAY_DREAM_ASSIGNEE:-claude1}"

slug="dream-run-$(date +%Y-%m-%d-%H%M%S)"
task_dir="relay-os/tasks/$slug"
body_file="relay-os/scripts/dream-body.md"

if [[ -e "$task_dir" ]]; then
    echo "$task_dir already exists" >&2
    exit 1
fi
if [[ ! -f "$body_file" ]]; then
    echo "Missing $body_file — vendor it before running." >&2
    exit 1
fi

mkdir -p "$task_dir"

# Frontmatter mirrors what scaffold_task() produces for a workflow-bound
# ticket: workflow frozen as {name, steps:[...]} and step pre-set to
# "1 (scan)". status: active because the task is being launched immediately;
# no separate draft → active gesture is needed.
{
    cat <<EOF
---
title: Dream run $(date +'%Y-%m-%d %H:%M')
status: active
mode: auto
owner: $owner
human: $owner
agent: $assignee
assignee: $assignee
workflow:
  name: bootstrap/dream-run
  steps:
    - name: scan
step: 1 (scan)
---

## Description

EOF
    cat "$body_file"
    printf '\n## Context\n\n'
} > "$task_dir/ticket.md"

printf '# %s\n\nBlackboard for this Dream run.\n' "$slug" > "$task_dir/blackboard.md"
: > "$task_dir/log.md"

echo "Scaffolded $slug — launching."
exec relay launch "$slug"
