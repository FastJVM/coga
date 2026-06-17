The blackboard is a notepad to be written to often as the human and agent works through a task.

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
