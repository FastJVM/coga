---
title: Attribute headless recurring completions to system
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
agent: claude
launch_generation: pending:cc9588ed-2cec-4afa-b2d2-f3c107334340
---

## Description

Make deterministic recurring completion identify the system in audit records and outcome wording. A successful `ticket.py` currently invokes child `coga bump`, which records a human actor and names the configured agent as finisher although no agent ran.

This is a provisional P2 fix scope from [the triage](triage-five-review-comments-that-merged-unanswered.md). Owner verdict is unset; keep the draft unactivated.

### Evidence and source

Original [PR 705 comment](https://github.com/FastJVM/coga/pull/705#discussion_r3834701954); source ticket: [migrate-recurring-templates-to-ticket-py-shims-and](migrate-recurring-templates-to-ticket-py-shims-and.md). Assessed 2026-09-18 at `4d828256d28bf772d17aa8ffa1b47d6f436ca57b`.

An isolated `launch_script.run_script_phase` probe executed a real script and real child CLI using the shipped shim's bump argv. The child had no `COGA_SUPERVISED`; its log said `[human:marc] task done` and its outcome said `claude finished`. The live append-only log still contains this attribution for `recurring/autoclose-merged` on 2026-09-18 08:33 (also 09-10/11). PR 786 removed the original digest template, but the other four bundled shims remain affected; PR 827's recipe-reporting change did not fix completion identity.

### Expected behavior and scope

Trace `src/coga/launch_script.py::run_script_phase`, `task_env.apply_task_env`, `commands/bump.py::bump` (terminal and intermediate-step paths), `commands/common.py::current_operator`, and lifecycle outcome writers. The launcher already audits script start as system; the missing link is deterministic child completion.

Provide a narrowly scoped system completion identity through the actual script-to-CLI subprocess boundary for `autoclose-merged`, `blocker-reminders`, `branch-sweep`, and `skill-update`. Reuse lifecycle validation/publication rather than writing status or log entries directly. An attribution marker must not grant owner-gate, assist, rewind, or launch authority, and it must not let a script signal an outer agent's done sentinel.

### Acceptance and focused verification

- Run a deterministic fixture through the real launcher/script/child-bump chain with recipes stubbed or otherwise isolated. Assert system actor and system finisher wording, not only the shim's command text.
- Check terminal completion and an intermediate step; lifecycle transitions still occur exactly once.
- Preserve human CLI attribution and real agent/recorded-assist behavior. A task or configured agent name alone must not imply that an agent actually ran.
- Failures and owner handoffs retain existing behavior; no new caller-controlled shortcut around lifecycle gates.
- Extend `tests/test_launch_script.py`, `tests/test_recurring_shims.py`, and relevant bump/notification tests. Do not execute production maintenance recipes.
- Update the script/lifecycle attribution contract in `coga/contexts/coga/architecture/SKILL.md` (and the narrower launch contract if affected), plus the PR 705 `coga/codebase` gotcha and packaged twins. If shims change, update both live `coga/recurring/<name>/ticket.py` and packaged equivalents.

Tradeoff: an explicit identity must cross a subprocess without becoming a privilege grant. Do not restore digest or rewrite historical `coga/log.md` records. General audit-identity redesign, GitHub replies and merge-policy changes are outside this ticket.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
