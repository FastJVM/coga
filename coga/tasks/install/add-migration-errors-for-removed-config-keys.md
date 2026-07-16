---
slug: install/add-migration-errors-for-removed-config-keys
title: Add migration errors for removed config keys
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- dev/code
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
secrets: null
script: null
step: 3 (open-pr)
---

## Description

Current main rejects the `coga.toml` that released 0.2.0 itself scaffolds:
`[agents.claude] auto = "-p"` (and `[agents.codex] auto = "exec"`) hit the
generic `unknown key(s) ['auto']` error on every command including `--help`,
with no hint that the key was removed or what to do. Upgrading the CLI thus
bricks every existing repo until a hand-edit. Removed/renamed config keys need
tailored migration errors that run before the generic unknown-key check —
exactly the treatment `skip_permissions` / `[assignees]` already get — saying
the key is gone and to delete the line.

## Context

Found in the 2026-07-08 fresh-container retest (HEAD CLI against a
0.2.0-initialized repo). Touchpoint: `src/coga/config.py` (`load_config`
fixed-schema validation and its existing deprecated-key carve-outs — see the
"Config loading fails loud on unknown keys" section of the `coga/architecture`
context). Sibling: `install/cut-release-to-realign-pypi-with-main` (the skew
only bites because main is unreleased).

<!-- coga:blackboard -->

## Dev
branch: removed-agent-key-migration
worktree: /home/n/Code/claude/coga-removed-agent-key-migration

## Findings (implement step)

- Removed `[agents.<name>]` keys are `auto`, `skip_permissions`, and
  `skip_permissions_argv` — all dropped in PR #503 ("Restore mode and remove
  autonomy", commit 83c2dacf). All three currently fall through to the generic
  `_reject_unknown_keys` error in `_parse_agents` (src/coga/config.py).
- The 0.2.0 scaffold (`git show v0.2.0:src/coga/resources/templates/coga/coga.toml`)
  carries `auto = "-p"` / `auto = "exec"`; `skip_permissions*` were documented
  as coga.local.toml-only. Only `auto` bricks a 0.2.0-initialized repo, but all
  three get the tailored error since users may carry any of them.
- Ticket says skip_permissions "already gets" the tailored treatment — that was
  true pre-#503 (the machine-local-policy raise); #503 removed it. This change
  restores tailored messaging for all three as *removed-key* migration errors.
- Existing pattern to follow: `[assignees]` (shared) and `[secrets]` (local)
  raises in `load_config` fire before the generic unknown-key check.

## Implemented (commits c4efeeb1 + 795e57f3, rebased onto origin/main 5c68a5cc)

1. `src/coga/config.py`: new `_REMOVED_AGENT_KEYS` tuple (`auto`,
   `skip_permissions`, `skip_permissions_argv`); `_parse_agents` raises a
   tailored ConfigError for any of them *before* `_reject_unknown_keys`.
   Message says launches are interactive-only now, the keys are gone with no
   replacement, delete the lines, and notes the 0.2.0 scaffold wrote `auto`.
2. `tests/test_config.py`: the three existing removed-key tests now match the
   tailored "has removed key(s)" message (auto's also asserts the "Delete"
   guidance); added `test_agent_unknown_key_error_survives_removed_keys` to
   pin that a genuinely unknown key (`clii`) still gets the generic error.
3. Docs: autonomy-removal line updated in BOTH architecture context copies
   (live coga/contexts + packaged bootstrap); the live copy's "dedicated
   migration errors run first" carve-out bullet now lists all three carve-outs;
   packaged src/coga/resources/templates/coga/coga.toml comment updated.
   The packaged bootstrap context has no "fails loud on unknown keys" section
   (intentionally trimmed copy), so only its autonomy line changed.
4. NOT touched: coga/coga.toml (this repo's own config) — its lines 9-10 carry
   the same now-stale "rejected as unknown config" comment, but agents must not
   edit coga.toml. Human/reviewer: sync that comment by hand if desired.

## Peer review

- Native `codex review --base main` found one P1: the migration check only
  inspected shared `coga.toml`, so the formerly documented machine-local
  `skip_permissions*` keys still produced misleading advice to move them into
  shared config. Fixed in 795e57f3 by detecting removed keys in local agent
  tables first, naming `coga.local.toml`, and adding coverage for both keys.
- Fresh rebase onto `origin/main` 5c68a5cc surfaced one `src/coga/config.py`
  conflict. Resolution kept main's current config/schema code and reapplied
  only this ticket's removed-key migration constant and checks.

## Verification

- Full suite after peer-review fix and fresh rebase: 1222 passed, 1 skipped
  (`/tmp/coga-removed-agent-review-venv/bin/python -m pytest`, with the venv
  pointed at the feature worktree source so script subprocesses import Coga).
- Focused config suite after rebase: 79 passed.
- End-to-end: scratch repo with 0.2.0-style coga.toml (`auto = "-p"` +
  `auto = "exec"`) → `coga --help` prints the migration error; deleting the
  two `auto` lines makes the CLI work again.
- Task-scoped validation: `ok_count: 1`, no issues or fixes.

## PR

### Summary

- Give removed `auto`, `skip_permissions`, and `skip_permissions_argv` agent
  keys actionable, source-aware migration errors for both shared and local
  config while preserving generic errors for genuinely unknown keys.
- Update the live and packaged architecture contexts, scaffold comments, and
  config regression coverage to match the migration contract.

### Test plan

- `/tmp/coga-removed-agent-review-venv/bin/python -m pytest` — 1222 passed,
  1 skipped.
