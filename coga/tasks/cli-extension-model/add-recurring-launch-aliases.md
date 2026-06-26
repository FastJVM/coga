---
slug: cli-extension-model/add-recurring-launch-aliases
title: Add recurring-launch aliases
status: done
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- coga/codebase
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
---

## Description

**Part of `cli-extension-model/`. Depends on
`audit-cli-extension-mechanisms` — do that first; it justifies exactly which
aliases ship here.**

Add the recurring-launch aliases the audit confirmed as pure passthroughs.
Recon (and the expected audit finding) says that is exactly two:

- `skill-update` → `recurring launch skill-update` (exact mirror of the
  existing `dream` default)
- `autoclose` → `recurring launch autoclose-merged`

Implement them as additions to `_DEFAULT_ALIASES` in `src/relay/cli.py` — NOT
as `relay.toml` `[aliases]` edits. Defaults shipped to every repo live in code;
`[aliases]` is for per-repo user overrides. Confirm `_validate_aliases` accepts
both (it only checks the expansion target exists and there's no built-in
collision — a renaming alias like `autoclose` is legal).

The `autoclose` verb name is a **deliberate** choice (short public verb), even
though it renames the target dir and sits next to the existing `automerge`
built-in. Add a one-line `help=`/comment distinguishing `autoclose` (sweep
merged PRs) from `automerge` (mark a merged task done) so the proximity doesn't
confuse users.

Done = both aliases in `_DEFAULT_ALIASES`; the `_DEFAULT_ALIASES` round-trip
test in `tests/test_aliases.py` extended to cover them; `python -m pytest`
green. (Do NOT rely on `relay validate` — it checks repo/task structure, not
the default-alias table.)

## Context

- `_DEFAULT_ALIASES` lives at `src/relay/cli.py` ~lines 121–124, alongside the
  existing `chat` and `dream` defaults — `dream` → `recurring launch dream` is
  the exact pattern to copy.
- `_validate_aliases` (~132–165) is the acceptance gate; `_BUILTIN_COMMANDS`
  (~101–107) is the collision set (note `automerge` is already a built-in).
- The round-trip test to extend is in `tests/test_aliases.py` (~line 209).
- The recurring targets exist: `relay-os/recurring/skill-update/` and
  `relay-os/recurring/autoclose-merged/`. Launch path is `recurring launch
  <name>`.

**Out of scope:** aliasing anything that needs pre/post logic (those stay
built-ins — see the audit), and the declarative-shim mechanism (ticket 3's
proposal + its follow-up). This ticket is ~4 lines of `cli.py` plus a test.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: add-recurring-aliases
worktree: ../relay-add-recurring-aliases
pr: https://github.com/FastJVM/relay/pull/421
ci: no checks configured on this repo (`gh pr checks 421` → "no checks reported")

## Plan / notes
- Add two default aliases to `_DEFAULT_ALIASES` in `src/relay/cli.py`:
  - `skill-update` → `recurring launch skill-update` (mirror of `dream`)
  - `autoclose` → `recurring launch autoclose-merged` (renaming alias; legal,
    `_validate_aliases` only checks target verb is a built-in + no key collision;
    `recurring` is a built-in).
- Extend `tests/test_aliases.py` with dispatch round-trip coverage for both,
  mirroring `test_default_build_alias_dispatches_without_user_aliases_section`.

## Result
- Implemented both aliases + clarifying comment in `src/relay/cli.py`.
- Extended `tests/test_aliases.py`: `test_recurring_launch_aliases_are_defaults`
  + parametrized `test_default_recurring_alias_dispatches_without_user_aliases_section`.
- Full suite green: 842 passed, 1 skipped (hatchling packaging importorskip).
  Ran via `PYTHONPATH=<worktree>/src python3.12 -m pytest` (system python is 3.9,
  no tomllib; no .relay/.venv present).
- Committed on branch `add-recurring-aliases` (commit 8ac07f1). No push / no PR
  (left for code/open-pr).

## Discrepancy noted (not a blocker)
The ticket says "automerge is already a built-in" and asks for a comment
distinguishing `autoclose` (sweep merged PRs) from `automerge` (mark a merged
task done). In the actual code there is NO `automerge` command — it's not in
`_BUILTIN_COMMANDS` and nothing registers it. The merged-task close path is
`relay mark done` / the autoclose-merged recurring sweep (see
status.py:103 and the autoclose-merged ticket which says "no manual automerge
command"). I wrote the clarifying comment accurately rather than referencing a
command that doesn't exist.

## Peer review
- Ran `codex review --base main` from `../relay-add-recurring-aliases` after the
  sandboxed attempt failed with the known read-only app-server error. Review
  found no correctness issues and no must-fix findings.
- No code changes were made during peer review.
- Verification: `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/n/Code/codex/relay-add-recurring-aliases/src python3.12 -m pytest -p no:cacheprovider`
  passed: 842 passed, 1 skipped.
