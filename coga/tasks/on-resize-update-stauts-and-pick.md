---
slug: on-resize-update-stauts-and-pick
title: on resize update stauts and pick
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 2 (peer-review)
---

## Description

The interactive picker shown by `coga megalaunch` does not redraw when the
terminal window is resized: the layout stays at the old width/height until the
next keypress. Handle terminal resize (SIGWINCH) in the picker loop so the
status table and picker viewport are recomputed and re-rendered immediately on
resize — the normal behavior for a TUI.

## Context

- The picker main loop is `_pick_selection` in
  `src/coga/commands/megalaunch.py` (~line 269). It uses a Rich `Live` with
  `auto_refresh=False` and only calls `live.update(...)` after `_read_key()`
  returns, and `_read_key` (~line 252) blocks in `os.read(fd, 1)` — so a
  resize triggers no redraw.
- `_picker_view` (~line 323) already reads `console.size` fresh on every
  render, and `_picker_window` (~line 307) recomputes the viewport from row
  count — so re-rendering on resize is sufficient; no layout code needs
  changing.
- Suggested approach: install a `signal.SIGWINCH` handler for the duration of
  the picker, restored via `try/finally` (note `_pick_selection` has multiple
  return paths: quit, enter, Ctrl-C). Important (PEP 475, Python 3.5+): a
  Python-level `os.read` does *not* raise `InterruptedError` on a signal — it
  runs the handler and retries the read, so a handler that merely sets a flag
  for the main loop will never trigger a redraw while the loop stays blocked.
  Either (a) re-render directly inside the SIGWINCH handler (it runs on the
  main thread between bytecodes; the `Live` object must be reachable), or
  (b) restructure `_read_key` around `select()` plus
  `signal.set_wakeup_fd`/self-pipe. Do not write EINTR-catching code — it
  would be dead code.
- `_read_key` toggles raw mode per keypress, so a resize can land during raw
  or cooked mode; whichever design is chosen must render correctly in both —
  test both cases manually.
- Reference for existing SIGWINCH handling in this codebase:
  `src/coga/repl_supervisor.py` (~line 242) installs/restores a handler and
  resizes the child PTY. Don't touch that code; it already works.
- Out of scope: plain `coga status` (`render_status` in `src/coga/views.py`)
  is a one-shot print that exits immediately — resize refresh does not apply
  to it.
- Verification is manual: run `coga megalaunch`, resize the terminal while the
  picker is open, confirm the table reflows and the viewport height adjusts.
  Automated tests for SIGWINCH delivery are brittle; a unit test around the
  key-read/redraw plumbing is welcome but optional.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Plan (implement step)

Chose the ticket's option (b): restructure `_read_key` around `select()` on
stdin plus a `signal.set_wakeup_fd` self-pipe, rather than rendering inside
the SIGWINCH handler. Reason: `tty.setraw` clears OPOST, so a render from
inside the handler while `_read_key` holds raw mode would staircase the
output; with the self-pipe, `_read_key` returns a synthetic "resize" action
after its `finally` restores cooked mode, so every render stays in the main
loop in cooked mode — correct in both modes by construction.

Mechanics:
- `_pick_selection` owns the pipe + handler lifecycle in `try/finally`
  (covers all return paths): `os.pipe()`, non-blocking write end,
  `signal.set_wakeup_fd(w)`, and a no-op `signal.signal(SIGWINCH, ...)`
  handler (needed — default SIGWINCH disposition is ignore, and only signals
  with a Python handler reach the wakeup fd).
- `_read_key(resize_fd)` selects on `[stdin, resize_fd]`; wakeup byte wins,
  gets drained, returns "resize". The main loop treats "resize" like any
  ignored key: no state change, falls through to `live.update(...)`, and
  `_picker_view` already reads `console.size` fresh.
- The wakeup fd stays installed across the whole picker, so a resize landing
  in cooked mode (between keypresses) is buffered in the pipe and the next
  `select` returns immediately.

Test-harness impact: `_feed_keys` in tests/test_megalaunch.py stubs
`_read_key` with a zero-arg lambda; widened to take the new resize-fd
parameter.

## Implemented (commit 615053b3 on the branch)

- `_read_key(resize_fd)` selects on `[stdin, resize_fd]`; a wakeup byte is
  drained and returned as "resize". `_pick_selection` owns the
  pipe/`set_wakeup_fd`/no-op-handler lifecycle in `try/finally` and restores
  all of it on every return path.
- Extra finding while testing: `tty.setraw` defaults to `when=TCSAFLUSH`,
  which discards queued input on every `_read_key` entry — so a keypress
  racing a resize redraw would be dropped. Changed to
  `tty.setraw(fd, termios.TCSADRAIN)` so type-ahead survives; this is what
  makes the "key pressed during resize is not lost" semantics hold.
- Tests added: `test_read_key_resize_beats_pending_keypress` (pty +
  self-pipe, deterministic, no signals) and
  `test_megalaunch_cli_picker_resize_keeps_state` (synthetic "resize" action
  leaves selection intact; SIGWINCH handler restored after the picker).

## Verification

- `python3.12 -m pytest` in the worktree: 1372 passed, 1 skipped (run twice,
  before and after rebasing onto origin/main d3927f29).
- Manual-equivalent E2E (no attended terminal available): scripted a pty
  harness (scratchpad `resize_e2e.py`) that runs `_pick_selection` in a child
  on a pty, shrinks the winsize + delivers SIGWINCH with no keypress, and
  asserts fresh redraw output arrives (both shrink 80x24→40x10 and grow back);
  `q` then exits cleanly. Passed. The raw-mode case (resize while blocked in
  select) is exactly what this harness exercises; the cooked-mode window is
  covered by the pipe buffering (byte waits until the next select). A quick
  human resize-check of `coga megalaunch --pick` during review is still
  worthwhile.

## Dev

branch: picker-sigwinch-redraw
worktree: /home/n/Code/codex/coga-picker-sigwinch-redraw

## Dream Skill: validate-drift

Generated: 2026-07-21T04:33:08+00:00
Command: `coga validate --json --fix`
Task: `on-resize-update-stauts-and-pick`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-21T04:35:03+00:00
Command: `coga validate --json --fix`
Task: `on-resize-update-stauts-and-pick`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.
