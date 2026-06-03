The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

- branch: `atomic-state-writes`
- worktree: `../relay-atomic-state-writes` (based on `main`, which already carries this
  ticket's active/in_progress commits)
- pr: https://github.com/FastJVM/relay/pull/273
- CI: no checks configured on this repo (`gh pr checks` reports none) — no green/red gate.
  Local suite green: 528 passed, 1 skipped.
- Note: main checkout has unrelated uncommitted `_TTY_SANITIZE` work in
  `repl_supervisor.py` + its test — left untouched; branching from main isolates this fix.

## Implementation plan (confirmed)

1. `Ticket.write` (`ticket.py:96`) → atomic temp-in-same-dir + fsync + `os.replace`.
2. `emit_done_marker` (`repl_supervisor.py:340`) → same atomic-rename pattern.
3. Harden legacy bare-touch branch (`_sentinel_signals_done`, `:87`): require non-empty
   content. Caller audit (bump/mark/panic/launch) shows ALL production callers pass a real
   `session_id` (resolved ticket path); nothing relies on `session_id=None`, so removal would
   be safe too — but ticket prefers hardening (lower risk), so we harden.
4. Shared helper `src/relay/atomicio.py::atomic_write_text` for both call sites.
5. Regression test: simulate interrupted write, assert prior content survives.
6. `append_log` left as-is — acceptance doesn't require it; line-atomic appends are fine.

## Implementation outcome (implement step)

Done. Commit `811e36e` on branch `atomic-state-writes`.

- New `src/relay/atomicio.py::atomic_write_text` — same-dir temp + fsync + `os.replace`.
  Same-dir is load-bearing (cross-fs rename degrades to non-atomic copy); cleans up the
  temp on any failure.
- `Ticket.write` and `emit_done_marker` now route through it.
- `_sentinel_signals_done` legacy `session_id is None` branch hardened: requires non-empty
  content (a zero-byte partial no longer reads as "done"). Kept rather than removed per ticket
  preference, though caller audit shows nothing relies on `session_id=None`.
- Tests: `tests/test_atomicio.py` (atomic replace, no temp debris, interrupted-write preserves
  prior content for both the helper and `Ticket.write`) + 3 hardening tests in
  `tests/test_repl_supervisor.py`.

**Test run:** 526 passed, 1 failed. The single failure —
`test_packaging.py::test_wheel_includes_bootstrap_batteries` — is PRE-EXISTING on the `main`
base this worktree branched from: a wheel-build duplicate-file collision on
`resources/templates/relay-os/skills/_template/SKILL.md` (force-include vs `packages` grab).
It touches none of my 5 files and is already fixed in the commits the working branch carries
ahead of main. Left untouched (out of scope). Ran with the relay venv python (3.12) since the
default `python3` is 3.9 and lacks `tomllib`.

Note for reviewer: this branch is based on `main`; the unrelated `_TTY_SANITIZE` work sitting
uncommitted in the primary checkout is NOT included here.

## Peer review (codex)

Reviewed branch `atomic-state-writes` against `main` with `codex review --base main`.
Codex found two must-fix regressions:

- `atomic_write_text` used `mkstemp`'s default `0600` mode, so replacing an
  existing markdown state file would drop group/world readability. Fixed by
  applying the existing target mode to the temp file, or the normal
  `0666 & ~umask` mode for new files, before `os.replace`.
- `test_sentinel_file_terminates_child` still used a zero-byte `touch`, so the
  hardened sentinel predicate ignored it and the test waited through the
  fallback `sleep 30`. Fixed the integration command to write a non-empty
  sentinel so it still exercises watcher teardown.

Added regression tests for existing-mode preservation and new-file umask
behavior. Verification:

- `PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest tests/test_atomicio.py tests/test_repl_supervisor.py`
  → 21 passed.
- `PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest`
  → 528 passed, 1 skipped.

## Bootstrap decisions

- workflow: `code/with-review` (small, self-contained fix + test; peer review is cheap).
- assignee: `claude`.
- contexts: `relay/architecture` attached (human call) — gives the implementer the
  atomicity-vs-locking boundary so they don't drift into the separate file-locking concern.
- Refreshed stale `repl_supervisor.py` line refs (legacy path `:70-71`→`:87-90`,
  done-marker write `:316`→`:340`); the file had been modified since the ticket was drafted.
- Added implementation notes to `## Context` (same-dir temp for os.replace; prefer hardening
  the legacy bare-touch branch over removing it).

## Evaluator review

I have everything I need. Here is my assessment.

## Evaluation: `atomic-writes-for-ticket-log-and-done-marker-files`

**1. Clarity & accuracy of references**
The description is excellent — among the clearest I'd expect to pick up cold. It states the problem, the honest scope, the fix, and acceptance criteria. The technical claims are all **correct**:
- `Ticket.write` is a bare `path.write_text(self.render())` — confirmed (truncate-then-write, no atomicity).
- `append_log` uses plain `open("a")` with no fsync — confirmed.
- `emit_done_marker` does `open(..., "w").write(...)` with no `os.replace` — confirmed.
- The legacy `session_id is None` branch returns `True` on *any* existing file (incl. a zero-byte partial) — confirmed; this is the genuine footgun.

**Caveat — line numbers have drifted.** `ticket.py:96-97` and `logfile.py:22` are still accurate. But in `repl_supervisor.py` the cited lines are stale: the supervisor was modified (24 lines added, it's `M` in git status). Actual current locations are `:87-88` (legacy branch, ticket says `:70-71`) and `:340-341` (done-marker write, ticket says `:316`). An agent grepping for the described code (`session_id is None`, `open(sentinel, "w")`) will find it immediately, so this is low-friction, but the references are wrong as written and should be refreshed before launch.

**2. Does `code/with-review` fit?**
Yes, good fit. This is a small, self-contained code change (temp + `os.replace`, a few lines across 2-3 files) plus a test. Peer review by the other agent is appropriate and cheap. No mismatch — this is exactly the shape `code/with-review` targets. It's not large enough to need decomposition, not vague enough to need a design/spike workflow.

**3. Contexts (currently none)**
The empty `contexts: []` is a gap worth filling. This work touches the **task-state write path**, which is core behavioral contract territory. Per CLAUDE.md, `architecture/SKILL.md` covers "primitives, planes... and locking" — directly relevant, since atomicity vs. the related locking ticket is the conceptual boundary here. I'd attach `architecture` (and possibly `codebase` for the test-layout expectation). Not strictly blocking — the ticket is self-describing — but the implementer would benefit from the architecture context to avoid drifting into the locking concern.

**4. Scope**
Reasonable and well-bounded. It's a single coherent concern (atomic durability of self-written state files), and it explicitly fences off `file-locking-for-concurrent-task-mutation` as separate. It does bundle three call sites, but they're the same fix applied uniformly, not three tickets. One soft edge: the acceptance criteria require atomicity for **ticket + done-marker** writes, but the body also flags `append_log`'s missing fsync. The ticket wisely doesn't demand fixing the log (line-atomic appends are fine), but "consider fsync on the critical writes" is left as a judgment call. That's acceptable for a low-priority ticket, just slightly open-ended.

**5. Assumptions to question before launch**
- **The "remove or harden the legacy bare-touch path" decision is left open.** Acceptance says "removed or hardened" — but removing it is an API/behavior change that could affect any caller relying on `session_id=None`. The implementer should check callers of `emit_done_marker()` / `_sentinel_signals_done()` with no session id before deleting the branch. Hardening (e.g. requiring non-empty content) is the lower-risk default; the ticket should probably nudge toward that rather than leaving it 50/50.
- **`os.replace` atomicity assumes same-filesystem temp.** Standard pitfall: write the temp file in the *same directory* as the target, not `/tmp`, or the rename degrades to a non-atomic copy. Worth stating so the implementer doesn't get it subtly wrong.
- **Priority/sequencing:** the ticket self-describes as a fast-follow to recurring/watchdog work and a "legitimate wontfix" if Relay never runs unattended. The human should confirm recurring/unattended operation is actually on the roadmap before spending review cycles — otherwise this is a defensible defer.

**Bottom line:** High-quality, launchable ticket. Two things to fix first: (a) correct the `repl_supervisor.py` line references (`:87-88` and `:340-341`), and (b) consider attaching `architecture` context. Everything else is sound.
