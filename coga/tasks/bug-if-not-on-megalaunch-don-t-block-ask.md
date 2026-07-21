---
slug: bug-if-not-on-megalaunch-don-t-block-ask
title: 'bug: if not on megalaunch  don''t block ask'
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - dev/code
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

Fix Coga's launch instructions so an agent running in an ordinary, attended
`coga launch` asks the human for any needed decision, credential, permission,
or other input and waits for the answer in the REPL. It must not call
`coga block` merely to persist that question; during a normal launch it should
block only when the human explicitly asks to park or block the ticket.

Preserve the distinct `coga megalaunch` contract: when missing human input
prevents progress in a queue-run session, the agent must still call
`coga block` as its terminal action so the owner is notified and the queue can
continue. Done means the ordinary-launch and megalaunch instructions state
this boundary unambiguously, focused regression tests cover both prompt paths,
and the matching durable architecture documentation is updated.

## Context

- This is a prompt-contract correction, not a runtime restriction on the
  `coga block` command. A human in an ordinary launch must remain able to ask
  the agent to block the ticket explicitly.
- The ordinary-launch ask-and-wait rule is mode-specific and authoritative
  over generic downstream instructions to block in the base prompt, workflow,
  or step skills. The complete composed prompt must not contradict itself.
  Update directly conflicting agent-facing wording where needed (including
  live/packaged pairs such as `code/implement`), but do not turn this into a
  broad workflow or skill rewrite.
- The ordinary agent guidance is composed from
  `src/coga/resources/prompt.md` and
  `src/coga/resources/prompt-agent.md`. The latter currently says "ask or
  block," while the base prompt's stronger "Never stop silently" rule and
  blocking section can still steer an agent to persist a question instead of
  waiting for the human who is present in the TTY.
- Megalaunch appends `src/coga/resources/prompt-megalaunch.md` through
  `src/coga/megalaunch.py::_megalaunch_prompt_suffix`. Keep that queue-specific
  directive explicit: a TTY is transport for megalaunch, not evidence that a
  human is waiting to answer.
- Add semantic coverage for a full ordinary step prompt in
  `tests/test_compose.py`: it must direct the agent to ask and wait, reserve
  blocking for an explicit human request, and contain no conflicting generic
  direction to block merely because input is needed. In
  `tests/test_megalaunch.py`, assert that the appended queue directive
  overrides that attended default and requires terminal `coga block` when
  unavailable input prevents progress. Update the relevant launch/prompt-composition
  section of `coga/contexts/coga/architecture/SKILL.md` and its packaged copy
  under `src/coga/resources/templates/coga/bootstrap/contexts/coga/` in the
  same change. Run the focused tests, then `python -m pytest` and
  `coga validate --task bug-if-not-on-megalaunch-don-t-block-ask`.
- Prefer consolidating or replacing conflicting base-prompt wording over
  adding another parallel rule; the base prompt is already the largest
  composed layer.
- Do not add a launch mode flag, change blocker lifecycle/state transitions,
  weaken megalaunch's requirement to release the queue with a terminal Coga
  command, or change TTY detection.
- Keep this narrow bug separate from the empty draft
  `rewrite-coga-base-prompt-and-agent-mode-block`; broader prompt rewriting is
  out of scope here.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

Verdict: strong, cohesive draft; a future agent can start cold. One must-fix ambiguity remains before launch.

- The source and test pointers are correct. Ordinary agent prompts unconditionally compose `src/coga/resources/prompt.md` followed by `prompt-agent.md`. Megalaunch loads `prompt-megalaunch.md` in `_megalaunch_prompt_suffix()` and appends it after the ordinary composed prompt. `tests/test_compose.py` already houses base-prompt contract assertions, while `tests/test_megalaunch.py` already captures and asserts the queue suffix. The live and packaged architecture paths are also correct.
- The current behavior claims are accurate: ordinary agent launch requires a TTY and has no megalaunch suffix; megalaunch also requires a TTY for its interactive REPL but explicitly says that this does not imply a waiting human and requires a terminal `block` when input is unavailable.
- Must clarify precedence over workflow/skill instructions. The composed `code/implement` skill currently says to stop on ambiguity and to `coga block` when a human decision is needed; the workflow also contains generic block directives. If only the two shared prompt files change, a complete step prompt can remain internally contradictory. State whether the new launch-mode directive is authoritative over generic downstream “block” wording, or whether conflicting live and packaged workflow/skill text is also in scope. An explicit precedence rule would preserve the narrow scope; a broad skill audit would expand it considerably.
- `code/with-review` otherwise fits: this is a shipped prompt-contract code change with regression tests, synchronized documentation, peer review, PR creation, and owner review. The repository has exactly the two agent types required by `other-agent`.
- `dev/code` is relevant and should remain attached because this workflow produces a branch and PR. It is narrow, and the ticket already inlines the architecture facts needed for implementation; attaching broad `coga/architecture` or `coga/codebase` context would add unnecessary payload.
- Scope is one coherent bug. The exclusions correctly rule out runtime enforcement, launch-mode flags, blocker lifecycle changes, TTY changes, and the separate broad rewrite ticket.
- Tests should assert the semantic boundary, not merely headings: the ordinary full composition must direct the agent to ask and wait and reserve blocking for an explicit human park/block request; the megalaunch suffix must override that attended default despite having a TTY and require terminal `coga block` when input is unavailable.
- Prompt-size review: `base_prompt` is the only layer over the requested threshold at 1,640/4,055 tokens (~40.4%). It is structurally necessary and is itself the subject of this fix, so it should not be removed; treat it as a concrete consolidation target by replacing conflicting wording rather than adding another parallel rule. `dev/code` is ~30.9% and justified. No other layer is disproportionate.
