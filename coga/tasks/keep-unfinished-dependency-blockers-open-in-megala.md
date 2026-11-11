---
title: Keep unfinished dependency blockers open in megalaunch
status: draft
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
    skills:
    - code/peer-review
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
---

## Description

### Problem

Coga 0.4.1 can release a dependent ticket too early when it has more than one open dependency blocker. `_finished_blocker_dependency` selects the first named task that is done, but the dependency-drain publication calls `resolve_open_blockers`, which marks every open blocker resolved. If B depends on A and C, A is done, and C is still active, the bare megalaunch drain can clear both asks and activate B.

This behavior also clears unrelated human asks that happen to coexist with a satisfied dependency blocker.

### Reproduction

1. Create active tickets A, C, and dependent ticket B.
2. Run `coga block --task B --reason "Depends on A: need its result"`.
3. Run `coga block --task B --reason "Depends on C: need its result"`.
4. Mark A done while C remains active.
5. Run a bare `coga megalaunch` sweep.

Observed in a minimal reproduction: the drain selects A, then both blocker entries become resolved. The existing single-dependency drain test still passes, so the missing coverage is the multi-blocker case.

### Required behavior

- Resolve only open dependency blocker entries whose exact named task is done or was seen and then retired.
- Preserve every unsatisfied dependency blocker and every unrelated human blocker.
- Keep the dependent ticket blocked and do not launch it while any open blocker remains.
- When all remaining blockers are satisfied, publish their targeted resolutions and activation atomically before the launch claim, preserving current race and recovery guarantees.
- Preserve the manual `coga unblock` contract: an explicit human answer may continue to resolve all open asks in one transition.
- Preserve exact path-qualified task-reference matching and the rule that cancellation is not dependency completion.

### Implementation and documentation

Introduce targeted blocker-resolution behavior rather than reusing the all-open resolver in the dependency drain. Update the shipped `coga/lifecycle` and `coga/megalaunch` topics in the same change so multiple dependencies and mixed dependency/human blockers have one explicit contract.

### Acceptance criteria

- A regression test proves that with A done and C active, only the A blocker is resolved and B stays blocked.
- A regression test proves that two satisfied dependencies can be resolved and B can drain normally.
- A regression test proves that a satisfied dependency does not resolve an unrelated human ask.
- Existing single-dependency, activation-refusal, exact-reference, publication, and race tests remain green.
- Focused megalaunch tests, the full test suite, packaging checks, and `coga validate --json` pass.

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
