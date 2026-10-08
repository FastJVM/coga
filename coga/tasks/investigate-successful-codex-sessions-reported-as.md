---
title: Investigate successful Codex sessions reported as failed
status: draft
owner: nicktoper
workflow: code/design-then-implement
---

## Description

Determine why apparently successful Codex sessions receive failed status, and correct classification only where lifecycle and process evidence prove it wrong. A success-looking final message alone is not proof of successful completion.

Reproduce a reported example and capture the launch target, process exit code, supervisor outcome, done sentinel, and expected workflow progress. Cover ordinary tickets and bootstrap or stateless sessions; preserve real failures, interrupts, timeouts, and no-progress failures. Add a regression for the confirmed mechanism and document the status meaning. The suspected Codex exit code at shutdown is a hypothesis, not an established cause.

## Context

### Report relayed by the owner — 2026-10-07

Another AI reports that all 24 failed sessions in its sample were Codex, with no Claude failures. Example: a 2026-10-05 bootstrap/orient session ended with “Merged all five open PRs… 80 passed” but was recorded failed. No raw record, repository path, or process exit evidence was supplied. Preserve this as a lead, not a confirmed false positive or proof of Codex-specific causality.

Hypothesis to test: Codex's exit code on closing may be interpreted as failure despite successful work. Compare the recorded activity status with supervisor classification and workflow progress; identify which field was actually called failed. Do not classify success from prose or passing tests alone.

Related draft where-have-code-review-disappeared owns missing workflow handoffs and already investigates `repl_supervisor._classify_exit`, `run_with_done_marker`, sentinel propagation, and no-progress exits. The canceled codex-doesn-t-exist-properly-for-agent-restart was consolidated there. This ticket owns inaccurate recorded outcomes; share evidence and avoid separate fixes if the mechanism proves identical.

Read coga/launch (`docs/contexts/coga/launch/SKILL.md`) and coga/internals/activity-capture (`docs/contexts/coga/internals/activity-capture/SKILL.md`), cited rather than attached; inspect completion classification and outcome capture. Start with `src/coga/repl_supervisor.py`, `src/coga/commands/launch.py`, and `src/coga/usage.py`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
