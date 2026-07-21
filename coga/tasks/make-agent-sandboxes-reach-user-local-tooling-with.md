---
slug: make-agent-sandboxes-reach-user-local-tooling-with
title: Make agent sandboxes reach user-local tooling without per-path config
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (design)
---

## Description

A sandboxed agent (Codex under `bwrap`) can only read what its permission
profile grants. Coga's workspace is granted; the tooling an agent needs to *do*
its job largely is not, because it lives under `~/.local`. Every failure
surfaces as something else — a missing file, a stale path, a missing command —
so it gets misdiagnosed, and the fix so far has been to add one more path to
`~/.codex/config.toml` per symptom.

Observed in a single session, all the same root cause:

1. `bwrap: execvp .../bin/codex` — `codex` on PATH symlinks into
   `~/.codex/packages/standalone/releases/<version>/bin/codex`. The agent
   concluded the binary was missing; it was present and executable.
2. `code/open-pr/SKILL.md` "not found" — `coga/.agent-skills/**` symlinks to the
   packaged `resources/templates/**` (`agent_skills.py:49`). The links sit
   inside the workspace, the targets don't. The agent concluded the installed
   path was stale; it had been regenerated minutes earlier.
3. `coga` not on PATH — `~/.local/bin` was never granted.
4. `gh` would have failed next, at `gh pr create`, for the same reason.

The pattern: **an agent can see a symlink and not follow it**, so the error
never names the real cause. Two of the four were confidently misdiagnosed by the
agent that hit them.

Enumerating paths does not converge. `~/.local/bin` entries resolve on into
`~/.local/share/{uv,pipx,claude}/...`, which change on every reinstall, version
bump, or installer switch. The current stopgap is a single read-only
`/home/n/.local` grant — it works, but it is hand-maintained, host-specific,
lives outside the repo, and is invisible to `coga validate`.

Worth noting what already works, because it bounds the problem: a project-local
`.venv` under a workspace root (e.g. `demo-hackathon/coga/.coga/.venv`) is
self-contained and needs no rule at all.

**Design question.** Where should this belong? Candidates, none yet chosen:

- **Coga emits the profile.** `coga init` / `coga launch` generate the sandbox
  permission set from what Coga actually knows it needs (its own install root,
  the agent CLIs it is configured to spawn, `gh`). Makes it declarative and
  reviewable; couples Coga to each agent CLI's permission schema.
- **Keep the view inside the workspace.** Materialize packaged skills in
  `.agent-skills` as real files instead of symlinks out of the install; keep
  symlinks for local skills under `coga/skills` so live editing survives. The
  view is wiped and rebuilt on every launch (`_remove_existing`,
  `agent_skills.py:31`; `launch.py:1177`) and is gitignored, so copies cannot go
  stale and never enter git. Fixes (2) only — not the CLI or `gh` cases.
- **Prefer project-local installs.** Lean on the `.coga/.venv` pattern that
  already works, and treat a global install as the unsupported path.
- **Document + validate.** Leave the profile hand-written but have
  `coga validate` check the paths an agent will need are reachable, so this
  fails loudly at setup instead of mid-task.

Not urgent — the `/home/n/.local` grant unblocks the current work. The point of
the ticket is to pick a direction rather than keep adding paths per symptom.

Design step should land on one approach and say plainly what it does *not*
cover; a fix for skills alone would have left `gh` broken.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
