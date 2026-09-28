---
title: 'Record the attended ticket-switch recipe: launch, do not mark active'
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
step: 3 (open-pr)
agent: claude
---

## Description

Dream 2026-W39, Phase 2 gap G4. Two attended sessions (native-runtime/1-debug-and-platform-failure-contract, section 'Handoff requires a task launch — 2026-09-16', and native-runtime/2-macos-arm64-runtime-readiness, 'Pending design handoff — 2026-09-17') hit the same dead end after the owner redirected the session to a prerequisite ticket: the agent ran coga mark active <slug>, authored the full step, then coga bump refused (Task is 'active'. Cannot advance.) because bump requires in_progress and only coga launch performs the start transition. One session burned a block/unblock cycle purely for this. CLAUDE.md only says mark active activates a draft without launching it; no context carries the recipe. Deliverable: a short section in coga/contexts/coga/recipes/SKILL.md ('Switching an attended session to another ticket'): have the owner run coga launch <slug> from their own terminal before the agent does the step's work; do not mark active and author first; if work was already done under active, record a handoff note and ask for the launch — the next launched session verifies the note and bumps once. Coordinate with Dream PR #104, which edits the same context.

## Context

<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: attended-ticket-switch-recipe

Placement (owner decision, 2026-09-28): the multiply path `coga/contexts/coga/recipes/SKILL.md` has no coga counterpart and coga PR #104 is an unrelated merged relay-era PR, so there is nothing to coordinate. The recipe goes under the Attended posture in `docs/contexts/coga/session-conduct` (+ packaged bootstrap twin) plus one bullet in the composed `src/coga/resources/prompt-attended.md`.

## Implement handoff (2026-09-28)

Commit `4dae8a53d` on `attended-ticket-switch-recipe` (pushed, rebased on origin/main `60ca77915`):
- `docs/contexts/coga/session-conduct/SKILL.md` + packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/session-conduct/SKILL.md`: new *Switching to another ticket* paragraph under the Attended posture — ask the human to `coga launch <ref>`; don't `mark active` and author (bump refuses `Task is 'active'. Cannot advance.`; block/unblock doesn't fix it); if work was already done under `active`, leave a handoff note on that ticket's blackboard and ask for the launch; the launched session verifies against disk and bumps once. Links `coga/lifecycle` for the start transition.
- `src/coga/resources/prompt-attended.md`: one bullet, "Switching tickets needs a launch", so the rule is in every attended prompt (the two failing sessions never read a topic). No canonical twin exists for this resource.
- No example-fixture change: no task layout or workflow semantics changed; composition only gains prose.

Verification: `.venv/bin/python -m pytest -q` → 2945 passed (pre-rebase); after rebase, `tests/test_packaging.py tests/test_compose.py tests/test_launch.py` → 254 passed.

Reviewer note: the multiply path named in the Description (`coga/contexts/coga/recipes/SKILL.md`) and "Dream PR #104" don't apply in this repo (coga #104 is an unrelated merged relay-era PR).

## Peer review

2026-09-28: `codex review --base main` **returned** with exit 0 and no findings.
No fixes were needed. The reviewer also ran
`PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_compose.py tests/test_packaging.py`
— 80 passed.

Fetched `origin/main` and ran `git rebase FETCH_HEAD` without conflicts. Final
commit: `d225a2ff1`, based on `8e4347d3e`. `git range-diff` confirmed the
rebased patch is identical to the reviewed patch. Pushed with
`git push --force-with-lease origin attended-ticket-switch-recipe`; the local
and remote feature branches match and are one commit ahead of `main`.

Verification:

- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest` — **3039 passed** after rebase.
- `git diff --check origin/main...HEAD` — clean.
- `cmp docs/contexts/coga/session-conduct/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/session-conduct/SKILL.md` — byte-identical.
- Inspected `compose_prompt_report` output for this ticket: the new launch
  instruction appears in the attended conduct layer only; megalaunch and
  recurring select their existing queue layers. Both context lifecycle links
  resolve. This change adds prose only, with no terminal, pager, or Slack UI
  requiring an interactive exercise.
- `coga validate --task record-the-attended-ticket-switch-recipe-launch-do --json`
  on `main` — one valid task, no issues.

Returned to clean `main` at `8e4347d3e` before writing this handoff and the PR
body. The review is complete; no review process remains in flight.

## PR

Attended ticket switches could leave completed work on an `active` ticket,
where `coga bump` refuses to advance. Document the launch-first recipe and
recovery handoff in the session-conduct context and its packaged twin, and
include the instruction in every attended prompt.

Test plan: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest` — 3039 passed; inspected composed conduct for all three launch contexts and verified context twin identity.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `record-the-attended-ticket-switch-recipe-launch-do`
Recorded: 2026-09-28T20:01:48+00:00

    Branch 'attended-ticket-switch-recipe' is not safe to publish. refs/heads/attended-ticket-switch-recipe does not contain latest origin/main. Rebase or merge before opening a PR, e.g. `git fetch origin main` then `git rebase origin/main`. Reconcile it and relaunch, or `coga block --task record-the-attended-ticket-switch-recipe-launch-do`.
