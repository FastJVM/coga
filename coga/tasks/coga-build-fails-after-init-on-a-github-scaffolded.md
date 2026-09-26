---
title: coga build fails after init on a GitHub-scaffolded repo
status: in_progress
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
step: 2 (peer-review)
agent: claude
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

## Dev

branch: init-hosting-scaffold-empty

## Plan (agreed with owner)

- README* is scaffold when <=3 non-blank lines and <1 KB; LICENSE*/COPYING*/.gitattributes are scaffold by name. Tradeoff: a real project whose only content is a tiny README gets the (deletable) onboarding ticket — preferred over the reverse miss this ticket reports.
- `coga launch coga-build` miss prints an onboarding-specific explanation (filled repo -> not seeded; use `coga ticket`). Init's skip line says `coga build` is unavailable. Share the slug via one constant.

## Implement handoff

Pushed `init-hosting-scaffold-empty` (commit "Treat hosting scaffold as empty on init; explain a missing coga-build"), rebased on origin/main.

- `src/coga/commands/init.py` `_is_hosting_scaffold` + `_repo_is_empty`: LICENSE*/LICENCE*/COPYING*, `.gitattributes` always scaffold; README* scaffold when <=3 non-blank lines and <1 KB (`_SCAFFOLD_README_MAX_*`). The init skip line now says `coga build` is unavailable.
- `src/coga/aliases.py` `ONBOARDING_TASK` + `onboarding_missing_message`: one slug constant shared by the `build` default alias, init's prune/log, and launch.
- `src/coga/commands/launch.py` (the `resolve_target` miss in `launch`): when the target is `coga-build` and no task matches it as a prefix, bail (exit 2) with the resolver message plus the onboarding explanation. Other misses are unchanged.
- Docs: `coga/init` step 3 (canonical + packaged twin). The `coga/cli` index has no `## coga build`/`## coga init` sections; it delegates both rows to `coga/init`, so it was left unchanged (one owner per fact).
- Tests: `test_init_hosting_scaffold_repo_seeds_onboarding`, `test_repo_is_empty_true_for_hosting_scaffold`, `test_repo_is_empty_false_for_real_readme` (parametrized), `test_launch_missing_onboarding_ticket_explains_filled_init`, `test_launch_missing_ordinary_task_keeps_bare_miss`. Existing "filled" tests used a `README.md` containing "hi" (now scaffold) and were switched to `main.py`.
- Verification: `.venv/bin/python -m pytest -q` passes, 2951 tests.
- Process note: the first pre-branch sync ran under the wrong interpreter (the global `python` lacks coga), and a chained `git switch` briefly carried the dirty ticket onto the branch. I switched back, published with `.venv/bin/python`, and reset the branch to the synced main before any work.
