---
title: Fail loud when relay launch starts an interactive session without a TTY
status: active
mode: interactive
owner: nick
assignee: claude1
workflow:
  name: code/with-review
  steps:
  - name: implement
    skill: code/implement-and-pr
  - name: review
step: 1 (implement)
contexts:
  - relay/codebase
  - relay/cli
  - relay/principles
---

## Description

`relay launch` on a `mode: interactive` ticket assumes a real
terminal: the agent process inherits the parent's stdin/stdout and
converses with the human. When the parent has no TTY (called from
inside another agent's Bash tool, from CI, from a wrapper script),
the inner agent runs but has no channel to ask questions. It produces
a partial artifact that *looks* like progress and silently leaves the
ticket in a half-baked state.

Violates "fail loud, never silent-wrong-answers" in
`relay/principles`. The check is cheap; skipping it costs real work
(see the empty-body draft at
`tasks/clear-step-field-when-bump-marks-task-done/` and this very
ticket — both produced when bootstrap/ticket was launched from inside
another agent's Bash tool, where the inner agent had no way to
converse).

## Repro

From inside any non-TTY parent (e.g. Claude Code's Bash tool):

```
relay create "any title"
```

Today: scaffolds the directory, launches the bootstrap/ticket agent,
the agent's clarifying questions go to captured stdout, the agent
exits with empty `## Description` / `## Context`. Exit code 0. No
error.

## Fix

In `src/relay/commands/launch.py`, after resolving the ticket and
before `subprocess.run` (and before the lock is acquired), add:

```python
if ticket.mode == "interactive" and not (
    sys.stdin.isatty() and sys.stdout.isatty()
):
    _bail(
        f"Cannot launch {ref.id_slug!r}: mode=interactive requires a TTY "
        "(stdin and stdout must both be terminals). Run from a real "
        "shell, or change the ticket to mode: auto / mode: script."
    )
```

Order matters — apply the check *before* `TaskLock(...).acquire()` so
a refused launch doesn't leave a stale lock behind.

`mode: auto` (one-shot, doesn't need stdin) and `mode: script` (no
agent at all) are unaffected.

## Out of scope

- A `--no-launch` flag on `relay create` / bootstrap factory shims
  for "scaffold a draft from inside an agent and exit". Useful
  follow-up — once this lands, the scaffold-and-exit pattern an
  agent might want from `relay create` will hard-fail under the new
  TTY check, and a flag is the clean answer. Track separately.
- Detecting parent context more cleverly (`$CLAUDE_CODE`, `$CI`,
  etc.). TTY check is portable and covers all of them.

## Tests to update

- `tests/test_launch.py` — new case that monkeypatches
  `sys.stdin.isatty` / `sys.stdout.isatty` to return `False`,
  asserts `relay launch <interactive-ticket>` exits non-zero with a
  clear message, and asserts no `task.lock` was created.
- Existing TTY-positive launch tests likely need to monkeypatch the
  same functions to return `True` (depending on how launch is
  currently exercised — check what the CI runner gives).

## Open question

The follow-up scope-out (`--no-launch` flag) is real and known —
worth opening as a separate draft now so it's tracked, or wait until
this lands and the friction shows up?
