The blackboard is a notepad to be written to often as the human and agent works through a task.

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
