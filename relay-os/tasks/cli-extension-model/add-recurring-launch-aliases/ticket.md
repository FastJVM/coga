---
title: Add recurring-launch aliases
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/codebase
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
step: 4 (review)
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
