---
title: retire in band DONE MRKER (not needed)
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
---

## Description

Retire the in-band DONE marker — the legacy PTY byte-match channel the
`relay launch` supervisor uses to detect a finished session. It is no
longer needed: the side-channel sentinel file (`$RELAY_DONE_SENTINEL`,
written by `emit_done_marker`) is the primary, reliable, task-scoped
signal. The in-band marker (`<<<RELAY_SESSION_DONE_...>>>` matched in the
PTY byte stream) is a fallback that is *not* task-scoped, which is the
root cause of the parent/child cross-talk bugs tracked in
`session-done-sentinel-leaks-and-agent-stops-respon` and
`session-done-sentinel-from-mark-done-bump-leaks-in` (a child `bump`/`mark
done` leaks the marker into the parent supervised launch and tears the
parent down).

Removing it also lets us delete the prompt-defusal machinery in
`compose.py` that exists *solely* to keep the literal marker bytes out of
composed prompts so they don't trip the PTY watcher. With no PTY watcher,
nothing needs defusing.

Done looks like: the supervisor relies only on the sentinel file; the
in-band marker constant, its PTY detection, its stdout fallback, and the
compose defusal are gone; tests and the architecture context are updated;
`python -m pytest` is green.

## Context

The scan below is current as of this ticket's creation — verify line
numbers before editing.

**Define / emit**
- `src/relay/repl_supervisor.py`
  - `DONE_MARKER = b"<<<RELAY_SESSION_DONE_a9f3c41e>>>"` (~line 45) and
    `SENTINEL_ENV = "RELAY_DONE_SENTINEL"` (~line 49); both in `__all__`
    (~482–490).
  - `emit_done_marker()` (~433–479): writes the sentinel file on success;
    **only** prints `DONE_MARKER` to stdout as a last-resort fallback when
    the file write fails — that stdout fallback is the in-band emission to
    remove.
  - `run_with_done_marker()` (~143–370): sentinel-file polling is primary
    (~289–291, via `_sentinel_signals_done`, ~117–140); the PTY byte-match
    fallback `if not sent_term and marker in buf` (~327–330) plus the
    `marker: bytes = DONE_MARKER` param (~146) are the in-band detection to
    remove.

**Defusal (delete once the PTY watcher is gone)**
- `src/relay/compose.py`: `_DONE_MARKER_TEXT` / `_DONE_MARKER_DEFUSED` /
  `_defuse_done_marker()` (~41–54) and its application in the `prompt`
  property (~98); import at ~22.

**Callers**
- `src/relay/commands/mark.py` (~22, ~156–161),
  `src/relay/commands/bump.py` (~17, ~188–220),
  `src/relay/commands/panic.py` (~13, ~66–71) — all call
  `emit_done_marker()`; the sentinel-file behavior stays, only the in-band
  fallback goes.
- `src/relay/commands/launch.py` (~44, ~461–475) — calls
  `run_with_done_marker`.

**Tests to update/remove**
- `tests/test_compose.py` (~17, ~252–290): the two defusal tests become
  obsolete.
- `tests/test_done_marker_emission.py`: the "does not leak marker /
  signals via sentinel not stdout" tests (~128–150, ~179–187, ~224–257)
  — keep the sentinel-signal assertions, drop assertions tied to the
  removed stdout fallback.
- `tests/test_repl_supervisor.py` (~13–23, ~330–353+): drop the
  `prints_only_if_file_write_fails` fallback test **and**
  `test_marker_in_child_output_terminates_child` (~115, asserts PTY
  byte-match teardown) — both are part of the in-band channel removal;
  keep sentinel tests. Expect helper churn too: `run_with_done_marker`'s
  `marker` param is exercised by test helpers (`_run_through_pty`), so
  removing it ripples into those.

**Docs / contexts to keep in sync (both copies)**
- `relay-os/contexts/relay/architecture/SKILL.md` and
  `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/architecture/SKILL.md`
  (~202–268): drop the "legacy DONE_MARKER PTY byte-match is fallback" and
  the prompt-defusal description.
- `src/relay/resources/prompt.md` (~61–63) and the live base prompt: the
  "Don't paste any marker string yourself" guidance can be simplified once
  there is no marker — implementer's judgment; keep the "exit cleanly, one
  step one session, don't chain" intent.

**Out of scope**: changing the sentinel-file protocol itself, or fixing
the two cross-talk bug tickets beyond what falls out of removing the
in-band channel.
