---
slug: bug-if-not-on-megalaunch-don-t-block-ask
title: 'bug: if not on megalaunch  don''t block ask'
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- dev/code
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

## Dev
pr: https://github.com/FastJVM/coga/pull/622
branch: fix/attended-ask-not-block
worktree: /home/n/Code/codex/coga-attended-ask

## PR

Summary:

- Make ordinary attended launches ask the human and wait, reserving
  `coga block` for an explicit request to park the ticket.
- Remove conflicting generic block directions from the base prompt and stock
  code steps, while keeping megalaunch's terminal queue-block contract and its
  explicit existing-blocker resolution path.
- Document the escalation boundary in the live and packaged architecture
  context and cover real composed stock prompts plus the megalaunch suffix.

Test plan: `python -m pytest` (1374 passed, 1 skipped); `coga validate --task bug-if-not-on-megalaunch-don-t-block-ask` (all good).

## Plan

- `src/coga/resources/prompt-agent.md`: make the attended default authoritative —
  ask the present human and wait; `coga block` only on explicit human request;
  state that this mode rule overrides generic block directions in base
  prompt/workflow/step skills, and that an appended queue directive
  (megalaunch) overrides it the other way.
- `src/coga/resources/prompt.md`: consolidate the "Never stop silently" loop
  rule and the "Blocking" section so they defer to the mode section instead of
  generically directing `coga block` whenever input is needed.
- `src/coga/resources/prompt-megalaunch.md`: state explicitly that the queue
  directive overrides the attended ask-and-wait default and requires terminal
  `coga block` when unavailable input prevents progress.
- `coga/skills/code/implement/SKILL.md` + packaged copy: reword the generic
  "block/stop" escalation lines to be mode-aware (the two copies have a known
  pre-existing divergence: the packaged copy carries a read-only-git /tmp
  clone fallback the live copy lacks — leaving that divergence untouched).
- Architecture SKILL.md (live + packaged): document the attended vs queue
  escalation boundary in the prompt-composition section.
- Tests: new semantic test in tests/test_compose.py over a full ordinary step
  prompt; extend the megalaunch suffix assertions in tests/test_megalaunch.py.

## Implement outcome

Committed on `fix/attended-ask-not-block` (e65ef462), rebased onto current
`origin/main` (no new commits), clean tree. Changes, per plan:

- `prompt-agent.md`: rewrote operating rules — "This launch is attended — ask
  and wait"; `coga block` only on an explicit human request to park/block;
  attended rule declared authoritative over generic block wording, overridden
  only by an appended queue directive. Escalation section matches.
- `prompt.md`: loop rule 4 and the Blocking section now defer to the mode
  section ("ask the human when your session is attended, `coga block` when no
  answer is available in-session"); "Don't go backward" bullet made
  mode-aware. No parallel rule added — conflicting wording replaced in place.
- `prompt-megalaunch.md`: intro now says the TTY is transport and the queue
  directive "overrides the attended ask-and-wait default in Agent mode";
  second bullet opens "Do not ask-and-wait for missing input here" and keeps
  terminal `coga block` required. Queue-release contract unchanged.
- `code/implement` SKILL.md (live + packaged): four generic block/stop lines
  reworded to "escalate per your launch mode — ask the attending human, or
  `coga block` in a queue run"; packaged copy's read-only-git fallback
  escalation sentence made mode-aware too. The pre-existing live/packaged
  divergence (the /tmp clone fallback exists only in the packaged copy) was
  left as-is.
- Architecture SKILL.md (live + packaged): prompt-composition section now
  documents the escalation boundary carried by the spawn seam.
- Tests: `test_compose_agent_prompt_attended_ask_and_wait` (positive
  ask-and-wait/explicit-request assertions plus negative assertions that the
  old generic block directions and the megalaunch directive are absent from
  an ordinary step prompt); megalaunch liveness-backstop test now asserts the
  suffix overrides the attended default and requires terminal `coga block`.

Verified: focused tests, then full `python -m pytest` (via python3.12 —
default `python` here is 3.9, below Coga's floor): 1362 passed, 1 skipped.
`coga validate --task bug-if-not-on-megalaunch-don-t-block-ask`: all good.
Example fixture untouched — it carries none of the edited prompt/skill copies
(checked repo-wide for the old wording).

## Peer review

`codex review --base main` found two must-fix prompt-contract gaps:

- Real stock step layers (`peer-review`, `code/self-qa`, `code/open-pr`, and
  `direct/body`) still appended unconditional `coga block` directions after
  the attended mode layer. The semantic compose test used a neutral fixture
  skill and therefore did not exercise a shipped step prompt. Fix: make the
  directly conflicting live/packaged wording mode-aware and cover a packaged
  stock step prompt.
- Megalaunch's blanket no-wait suffix also overrode the existing
  resolve-or-re-block preamble for a human's explicitly picked blocked task.
  Fix: retain a narrow existing-blocker resolution exception (resolve and
  unblock, or terminally re-block) while keeping new unavailable input on the
  queue-required terminal `coga block` path. No lifecycle, TTY, or launch-mode
  flag change is needed.

Review verification: focused prompt/megalaunch tests passed (65 passed). Full
suite passed after clearing inherited live-launch `COGA_*` task paths (1362
passed, 1 skipped); the first review subprocess run's single failure was an
environment artifact from `validate-drift` following the parent task's
blackboard path into the read-only control checkout.

Applied both findings in the feature worktree. Directly conflicting stock
step wording is now mode-aware in the live/packaged `peer-review`,
`code/self-qa`, `code/open-pr`, and `direct/body` sources. The ordinary compose
test now uses the packaged peer-review step, with additional semantic cases for
the other stock steps. Megalaunch retains its queue-wide no-wait/terminal-block
rule plus a narrowly documented exception for already-open blockers in an
explicitly selected resolution session. Focused tests: 68 passed. Full suite:
1365 passed, 1 skipped.

Final handoff: committed peer-review fixes, fetched `origin/main`, and rebased
cleanly onto `e3fab9b3`. Final feature commits are `a9df2d84` and `865cdd57`;
the branch is clean, two commits ahead, and zero behind `origin/main`.
Post-rebase full suite: 1374 passed, 1 skipped. Task-scoped validation: all
good.

## Dream Skill: validate-drift

Generated: 2026-07-21T01:05:57+00:00
Command: `coga validate --json --fix`
Task: `bug-if-not-on-megalaunch-don-t-block-ask`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.
