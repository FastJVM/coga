---
slug: fix-windows-cli-import-crash
title: 'Windows: guard Unix-only imports so the CLI runs; decide full Windows-support path'
status: draft
owner: zach
human: zach
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow: code/design-then-implement
secrets: null
script: null
---

## Description

On native Windows, **every** `coga` command crashes at import time — not just
interactive ones — because the CLI imports Unix-only stdlib modules (`fcntl`,
`pty`, `termios`, `tty`, `select`) at module load. coga is currently unusable on
Windows.

This is a **two-tier** piece of work, and the design step must decide which
tiers are in scope before any code is written:

1. **Bandaid (low risk, partial):** guard the Unix-only imports so the import
   chain no longer breaks. This unblocks all *non-interactive* commands
   (`delete`, `status`, `validate`, `create`, `mark`, `bump`, ...) on native
   Windows. It does **not** make interactive `coga launch` work there.
2. **Full support (real code change):** decide between (a) porting the
   interactive REPL supervisor off `pty`/`termios` to Windows ConPTY (e.g.
   `pywinpty`) for native interactive launch, or (b) officially declaring **WSL
   the supported Windows path** and documenting it (no core change). Option (a)
   is a substantial change to terminal-handling code and must be proven not to
   regress Linux/macOS.

The bandaid alone is explicitly a partial fix. Do not let it close out the
question of true Windows support — that is the design decision this ticket
exists to force.

## Context

Root cause (verified against source on 2026-07-18):

- `cli.py` eagerly imports every command module at startup. The chain
  `cli.py` -> `commands/block.py:12` -> `repl_supervisor.py` triggers
  `import fcntl` at `src/coga/repl_supervisor.py:20`, alongside top-level
  `import pty` / `select` / `termios` / `tty` in the same module.
  `commands/megalaunch.py` (also imported by `cli.py`) imports
  `select` / `termios` / `tty` at top level too.
- None of those modules exist on Windows, so importing the CLI raises
  `ModuleNotFoundError: No module named 'fcntl'` **before any command runs**.
  That is why housekeeping commands that need none of the terminal machinery
  still fail — it is purely the eager import chain.
- `fcntl` has a single use site: `repl_supervisor.py:430` (a `TIOCSWINSZ`
  window-size ioctl). `pty`/`termios` are load-bearing for the interactive REPL
  supervisor and have **no native Windows equivalent** — that is why tier 2 is a
  real port, not a guard.

Repro: Windows 11, Python 3.12 — `pip install -e .`, then run any command
(`coga --help`, `coga delete <slug>`); observe the `fcntl` traceback.

Tier 1 sketch (for the implementer, once the design step approves it): guard the
Unix-only imports (lazy import or `sys.platform` check) in `repl_supervisor.py`
and `commands/megalaunch.py` so import always succeeds; have the pty/fcntl code
paths raise a clear "interactive launch is not supported on native Windows; use
WSL" error only when actually invoked. Hard constraint from the filer: whatever
ships must be verified not to change behavior on Linux/macOS.

Current workaround (no code change): run coga under WSL2 — real Linux, so
`pty`/`termios`/`fcntl` all exist and full functionality (including interactive
launch) works with the identical codebase.

Cross-OS verification (required before this ships — the filer's hard
constraint): there is no platform-matrix CI today, so no-regression must be
proven by hand. Named verifier — the same teammate on Unix (or the filer in
WSL) who runs `coga validate` runs the full `python -m pytest` suite, and it
must stay green. The Windows fix itself is smoke-checked on native Windows:
`coga --help` and a non-interactive command (e.g. `coga delete <slug>`) succeed,
and interactive `coga launch` raises the clear "use WSL" error instead of
crashing. The specific failure this guards against is a lazy-import or
`sys.platform` mistake that silently disables the Unix path, so the green Unix
suite is the gate.

Out of scope: tier-2 option (a) — the ConPTY / `pywinpty` port of the
interactive REPL supervisor — is a substantial terminal-handling rewrite that
does not fit this ticket's single `implement` step. If the design step chooses
it, it spins out to its own follow-up ticket. This ticket delivers **tier 1**
(the import guard) plus the **recorded tier-2 decision** (and the
WSL-supported docs, if that is the chosen path).

Scope note: this ticket is authored by hand because the filer is on Windows and
the `coga` CLI cannot run there to scaffold it. It was therefore **not** run
through `coga validate`; a teammate on Unix (or the filer in WSL) should
`coga validate --task fix-windows-cli-import-crash` before launching. No code
was changed in creating this ticket.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
