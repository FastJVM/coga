---
slug: v2/exclude-dev-tree-agent-skill-symlink-views-from-th
title: Exclude dev-tree agent-skill symlink views from the wheel build
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Surfaced by the Dream run on 2026-06-09 as a `gap` finding, and explicitly left
as a follow-up by the merged `fix-wheel-build-failing-on-a-clean-checkout-duplic`
ticket (PR #319).

A wheel built from a **dev tree** — one where `relay init` has materialized the
gitignored agent-skill symlink views (`.agent-skills/`, `.claude/skills/`,
`.codex/skills/`) under the templates tree — leaks ~51 `.agent-skills/...` view
entries into the wheel archive. Real releases build from a clean checkout (no
symlinks), so shipped wheels are unaffected and this never broke a release —
which is exactly why it is a latent trap rather than an urgent bug.

Proposed fix: exclude the symlink-view paths from the hatchling wheel walk —
`**/.agent-skills/**`, `**/.claude/**`, `**/.codex/**` — in
`[tool.hatch.build.targets.wheel].exclude` in `pyproject.toml`, so a dev-tree
build produces the same archive as a clean-tree build.

Acceptance:
- A wheel built from a dev tree (symlink views present) contains no
  `.agent-skills/`, `.claude/`, or `.codex/` entries.
- A clean-tree build is unchanged and still ships every
  `EXPECTED_BOOTSTRAP_RESOURCES` battery (verify both tree shapes, as the
  parent ticket did — hatchling's dedup is symlink-sensitive).

See `relay/codebase` → "Wheel packaging: force-include vs the package walk" for
the build model this builds on.

## Context

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
