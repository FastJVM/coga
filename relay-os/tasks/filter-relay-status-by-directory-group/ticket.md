---
title: Filter relay status by directory/group
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/cli
- relay/architecture
- relay/codebase
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 4 (review)
---

## Description

Add directory/group filtering to `relay status`. Today `relay status`
lists every task in the repo with no way to slice by where the task lives.
Tasks live under `relay-os/tasks/` either as direct children
(`tasks/<slug>/`) or one level deeper inside an organizational group
(`tasks/<group>/<slug>/`). Users want to see only the tasks in one group
(e.g. `marketing`) or only the top-level/root tasks.

Add a filter so the operator can narrow `relay status` to a single
directory/group:

- `relay status <group>` (or a `--group <name>` flag — pick the more
  idiomatic shape for the existing CLI and note the choice in the
  blackboard) shows only tasks under `tasks/<group>/`.
- A way to show only root (un-grouped) tasks — e.g. `relay status root`
  or `relay status --root`. Decide the sentinel and document it.
- Unknown group → fail loud with a clear message listing available
  groups, not a silent empty list.

Keep `relay status` read-only (principle 6 — no network, no state
mutation as a side effect of rendering). Add tests under
`tests/test_status.py` covering: a group filter, the root filter, and the
unknown-group error. Update the `relay/cli` context's `relay status`
section to document the new filtering.

## Context

The `relay status` command lives in `src/relay/commands/`. The
group-qualified slug convention (`<group>/<leaf>`) and the
`tasks/<group>/<slug>/` vs `tasks/<slug>/` layout are described in the
`relay/architecture` context already in this prompt. Keep the change
markdown-first and legible; no new dependencies.
