---
title: Detect missing skills
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/codebase
- relay/current-direction
- relay/project-stage
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
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Decide and implement how Relay detects a *missing skill* — the trigger that
tells the skill-import pass (sibling ticket
`add-bootstrap-skill-for-importing-external-skills`, "Add a skill-import pass")
when to fire.

There are two senses of "missing," and they are not equally tractable:

1. **Referenced-but-absent** — a ticket or workflow step names a `skill:` that
   has no file. This is *already detected*: `relay validate` emits a
   `broken-skill` issue (`validate.py:549–577`) and `compose.py` hard-fails at
   launch via `_missing_skill_message` (`compose.py:300,323`) rather than
   silently dropping the layer. Scope here is to confirm/round out that
   coverage and surface it well, not rebuild it.
2. **Capability gap** — a need that *should* have a skill but where no step
   references one (e.g. "this repo keeps hand-rolling changelog steps; there
   should be a changelog skill"). This is **not** statically detectable. It is
   a judgment currently surfaced only in the `bootstrap/ticket` interview. The
   real question this ticket answers: is a heuristic/lint worth building, or
   does the interview gap-point remain the only honest detector?

If the recorded decision is "interview-only, no detector built," the implement
step still produces a non-empty branch: its deliverable is the recorded
decision (see acceptance criteria) plus any doc/test additions, which `open-pr`
then PRs. Do not leave the branch empty.

## Context

This split out of "Add a skill-import pass." That ticket added the `import`
pass and a `bootstrap/ticket` step-4 hook that runs the import check at the
gap point; this ticket owns the *detection* side that feeds it. The hook lives
in `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md`
(step 4). Read the sibling ticket's blackboard before deciding — its status is
`active` and the import-pass shape may still be moving.

Key code already in place:

- `src/relay/validate.py` — `broken-skill` check over ticket-level and
  step-level `skills:` refs, using `resolve_skill_path` / `skill_resolution_paths`.
- `src/relay/compose.py` — `_missing_skill_message`, raised on compose so a
  missing skill is a hard failure, not a silent drop.

Open design questions for the interview:

- Is capability-gap detection in scope, or explicitly out (interview-only)?
- If in scope, what's the signal — repeated inline step prose with no skill,
  a per-step "no skill attached" warning, something else? Avoid false-positive
  noise (many steps legitimately have no skill).
- Does anything need to change so the import pass can consume the detection
  output programmatically, or is a human reading `relay validate` enough?

## Acceptance criteria

- [ ] Documents the two senses of "missing skill" and which Relay detects today.
- [ ] Confirms/extends referenced-but-absent detection coverage
      (`validate` + `compose`) with tests if any gap is found.
- [ ] Makes an explicit, recorded decision on capability-gap detection:
      build a heuristic (define it) or declare it interview-only (and say why).
- [ ] The decision is recorded durably (not only in chat/PR): in this ticket's
      `relay-os/tasks/detect-missing-skills/blackboard.md`, and if the outcome
      is interview-only, also noted in `relay-os/contexts/relay/current-direction/SKILL.md`
      so the import-pass sibling can rely on it.
- [ ] If a new detector is built, it has focused tests and avoids false
      positives on steps that legitimately have no skill.
- [ ] `python -m pytest` and `relay validate --json` are green.

