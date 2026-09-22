---
title: coga build fails after init on a GitHub-scaffolded repo
status: draft
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
---

## Description

`coga init` on a repo whose only prior content is GitHub's stock scaffold (`README.md` + `LICENSE` from "Initialize this repository with...") classifies the repo as *filled*, prunes the delivered `coga-build` onboarding ticket, but still registers the `build` alias. The advertised first-run command then fails with a bare resolver miss:

```
$ coga build
→ coga launch coga-build
No tasks found (looked for 'coga-build')
```

Observed 2026-09-22 in a fresh `thinkpick` repo (coga 0.3.2): first commit was README.md + LICENSE only; the init commit contains no `coga/tasks/coga-build.md` and log.md has no `created` line for it.

Root cause, in `src/coga/commands/init.py`:

- `_repo_is_empty` / `_INIT_IGNORE` treat any entry outside `.git`, `.DS_Store`, `coga`, `CLAUDE.md`, `AGENTS.md`, `.claude`, `.codex`, `.gitignore` as real project content, so hosting-provider scaffold files flip the repo to "filled".
- `_prune_onboarding_tickets` then removes `coga-build`, while `aliases.DEFAULT_ALIASES` and the scaffolded `coga.toml` still advertise `build = "launch coga-build"`.

Fix both halves:

1. Treat stock hosting scaffold as empty: at minimum a top-level `README*` and `LICENSE*`/`COPYING*` (and `.gitattributes`). Decide whether README content should be size/shape-gated (a one-line `# <name>` README is scaffold; a real project README is not) and record the tradeoff.
2. Make `coga build` fail loud and actionable when the onboarding ticket is absent — name why (repo was initialized as filled, so onboarding was not seeded) and how to proceed — instead of the generic "No tasks found". Also consider whether init should print that it skipped onboarding and that `coga build` is therefore unavailable.

Update `coga/cli` (`## coga build`, `## coga init`) and any matching docs in the same PR, and add tests for the README+LICENSE-only init path and the missing-ticket `build` message.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
