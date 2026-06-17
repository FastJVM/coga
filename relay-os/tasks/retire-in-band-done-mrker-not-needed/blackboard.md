The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

- branch: retire-done-marker
- worktree: /home/n/Code/claude/relay-retire-done-marker
- pr: https://github.com/FastJVM/relay/pull/377

### PR opened (claude, 2026-06-16, open-pr step)

Pushed `retire-done-marker` and opened PR #377. `gh pr checks 377` reports
no checks configured on this repo, so there is no CI gate to wait on —
verification rests on the local suite (750 passed, 1 skipped) and the codex
peer review recorded below.

### Recovery note (claude, 2026-06-16, relaunch)

Picked up the `implement` step and found the worktree did NOT match the log
below: nothing was committed, and only `repl_supervisor.py` was modified —
partially and **broken** (the `DONE_MARKER` constant was deleted but still
referenced at the `marker=` default arg, the `marker in buf` block, the
stdout fallback, and `__all__`, so the module raised `NameError` on import;
`compose.py`/`launch.py`/tests/docs were untouched). The "Implementation
log" below described work that was never saved.

Completed the implementation for real this time, matching that plan, and
committed it (worktree commit `9438443`). `python3.12 -m pytest`:
**750 passed, 1 skipped**. The notes below are accurate as a description of
what is now on disk and committed.

### Implementation log (claude, 2026-06-16)

Verified all ticket line numbers against source before editing — accurate.
Removing the in-band PTY byte-match channel entirely:

- `repl_supervisor.py`: dropped `DONE_MARKER` const + `__all__` entry;
  removed `marker` param, the `marker in buf` PTY-match block, and the
  now-unused `buf` bytearray from `run_with_done_marker`; removed the
  stdout fallback in `emit_done_marker` (a failed sentinel write is now
  swallowed best-effort — degrades to the supervisor's idle/max-session
  backstop, the only remaining channel). Rewrote module + function
  docstrings to describe one channel.
- `compose.py`: dropped `_defuse_done_marker` + the two module constants +
  the `DONE_MARKER` import; `prompt` returns assembled text directly.
- `launch.py`: updated the stale `DONE_MARKER` comment.
- Docs: both architecture SKILL.md copies (live + template) and
  `prompt.md` updated.
- Tests: dropped `test_compose_defuses_*` (x2),
  `test_marker_in_child_output_terminates_child`, and
  `test_emit_done_marker_prints_only_if_file_write_fails`; converted
  marker-leak assertions in `test_done_marker_emission.py` to
  sentinel-presence/absence assertions.

### Peer review (codex)

Ran `codex review --base main` from `/home/n/Code/claude/relay-retire-done-marker`.
The sandboxed attempt hit the known app-server read-only-filesystem failure, so
it was rerun outside the sandbox. Codex review found no actionable regressions.

Verification:

- `PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest -q -p no:cacheprovider`
  from the feature worktree: **750 passed, 1 skipped**.
- `git diff --check main...HEAD`: clean.
- Targeted `rg` for in-scope `DONE_MARKER`, defusal, PTY byte-match, and
  literal marker references under `src`, `tests`, and the live architecture
  context: no matches.

No peer-review fix commit was needed.

## Bootstrap notes (nick + claude, 2026-06-16)

Filled the draft via `bootstrap/ticket`.

- Workflow: `code/with-review` (chosen by nick). Two agent types configured
  (claude + codex), so `other-agent` peer-review resolves unambiguously.
- Assignee/agent: claude implements, codex peer-reviews.
- Contexts: empty by design. The needed facts are inlined in `## Context`;
  `relay/architecture` is a file the implementer *edits*, so attaching it
  read-only would be redundant/contradictory.
- The task = retire the legacy in-band PTY byte-match DONE marker; the
  sentinel file (`$RELAY_DONE_SENTINEL`) is already the primary channel.
  Removing the in-band channel also removes the need for compose defusal.
- A codebase scan produced the exact file/line map now in `## Context`
  (verify line numbers before editing — they drift).

## Evaluator review

I have enough to assess. There's an additional test (`test_marker_in_child_output_terminates_child` at line 115) that the ticket's test inventory does not explicitly call out — it lists the `prints_only_if_file_write_fails` test at ~330–353 but not this PTY-byte-match test at ~115. That's a minor omission. Here is my assessment.

---

## Evaluation: `retire-in-band-done-mrker-not-needed`

**Overall: this is a well-scoped, accurate, ready-to-launch ticket.** I verified every file path, line range, and claim against the code and they are correct.

### 1. Description clarity — clear
An agent with no prior context could start. The Description states the *why* (in-band marker isn't task-scoped → cross-talk bugs), the *what* (remove marker constant, PTY detection, stdout fallback, compose defusal), and a concrete "Done looks like" with `pytest` green as the gate. The code comments in `repl_supervisor.py` and `emit_done_marker` corroborate the framing precisely — the design rationale is already documented in-source, so the agent isn't taking the ticket's word for it.

### 2. `code/with-review` fit — good fit
This is a multi-file source deletion touching supervisor logic, prompt composition, and a teardown protocol with subtle failure modes (partial writes, parent/child signal scoping). A removal that changes how supervised sessions detect completion is exactly the kind of change that benefits from peer review before a PR. No mismatch.

### 3. Contexts — empty is the right call here
The needed facts are inlined and the durable behavioral contract lives in `architecture/SKILL.md`, which the ticket already names as a file to *edit*. Attaching it as a read-only context would be redundant and slightly contradictory (you don't want it composed as authoritative while you're rewriting it). Per CLAUDE.md the agent must read the architecture context before changing behavior — the ticket directs them straight to it. Nothing important is missing.

### 4. Scope — reasonable, single ticket
Four coupled changes (marker constant + PTY detection + stdout fallback + compose defusal) that only make sense removed together, plus their tests and the two doc copies. The "Out of scope" section correctly fences off the sentinel protocol itself and the two cross-talk bug tickets. This does not bundle multiple tickets.

### 5. Assumptions / accuracy — claims hold, two small notes

- **All line numbers and paths verified accurate** as of now: `DONE_MARKER` (line 45), `SENTINEL_ENV` (49), `__all__` (482–490), `emit_done_marker` stdout fallback (479), PTY byte-match `if not sent_term and marker in buf` (327–330), `marker` param (146), compose defusal (47–54, applied at 98, import at 22), all three callers, launch.py call (469), architecture SKILL.md (203–207 and 258–268), prompt.md (63). Both template/live copies exist.

- **Minor test-inventory gap:** the ticket lists the `test_emit_done_marker_prints_only_if_file_write_fails` test (353) to drop, but does not call out `test_marker_in_child_output_terminates_child` at line ~115, which spawns a bash child that echoes the marker and asserts PTY-byte-match teardown. That test *also* becomes obsolete once the byte-match path is removed and must be deleted, or the suite won't stay green. An agent following "drop assertions tied to the removed fallback" would likely catch it, but the ticket's explicit list misses it. Worth flagging so it isn't missed.

- **One judgment call left open (appropriately):** the `marker: bytes = DONE_MARKER` parameter of `run_with_done_marker` is part of the public-ish signature used by tests via `_run_through_pty`. Removing it ripples into the test helpers. The ticket flags removing the param but doesn't note the helper churn — not a blocker, just expect test-helper edits beyond the listed assertions.

**Recommendation:** Launch as-is. The only thing I'd add before/at launch is a one-line note that `tests/test_repl_supervisor.py::test_marker_in_child_output_terminates_child` (~115) is part of the "PTY byte-match fallback" removal, not just the `prints_only_if_file_write_fails` test.

---

_Follow-up: the evaluator's flagged test (`test_marker_in_child_output_terminates_child`, ~115) and the `marker`-param helper churn have since been folded into the ticket's `## Context` test list._
