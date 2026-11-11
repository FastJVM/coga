---
title: Keep unfinished dependency blockers open in megalaunch
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
step: 2 (peer-review)
agent: claude
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

## Dev

branch: coga/keep-unfinished-dependency-blockers-open-in-mega-3a6dfd


## Implement progress

- Human approved targeted resolutions with partial progress kept blocked and the existing atomic activation/publication safeguards retained.
- `src/coga/megalaunch.py` + `_finished_blocker_dependencies` selects satisfied entries; `_publish_partial_dependency_resolution` publishes partial answers against exact ticket bytes; `_activate_for_launch` answers only selected records before its existing guarded publication.
- `src/coga/blackboard.py` + `resolve_blockers_text` targets full captured blocker records, preserving inert examples, superseded designs, legacy asks, and existing answers. Records rather than IDs are necessary because `_blocker_id` uses whole seconds and different asks can share an ID. ID generation is unchanged; broader ID-consumer implications remain an adjacent finding, with no existing follow-up found.
- Regression-first run: all four new multi-blocker cases failed on the original implementation (active/canceled/human asks cleared; two done dependencies answered with the wrong task name). First focused fixed run: 191 passed in 20.43s. Final verification and publication receipts are recorded below.
- Shipped lifecycle topic owns the multi-dependency/mixed-ask contract; megalaunch links it and owns exact publication and retry behavior. No fixture shape or workflow snapshot changed; runtime regressions use the existing megalaunch fixtures.
- Independent code review belongs to the next workflow step; none has run in implement.
- Final head pushed: `975a5b81d1191fa1da74bb1309118e0a40ee9f34`; base `d53c5566e3454ae6ecdb1809ce131279146cf0f0`. Includes the human-approved one-link navigation repair as a separate commit.
- Post-rebase focused/packaging run: 232 passed, 1 failed in 20.88s. Failure: `tests/test_packaging.py::test_context_navigation_has_no_broken_links`, because the unchanged local development branch-sweep topic links to removed anchor `#review-and-release-a-retained-local-draft` in the shipped branch-sweep topic. Both paths have zero diff from origin/main. Human approved removing the stale fragment so the link opens its owning topic; implemented in `975a5b81d`. The first full-suite run was interrupted before completion to restart verification on the final commit; it is not a full-suite receipt.
- Repo validation passed (107 OK, 10 warnings, no errors); seeded fixture validation passed (5 OK, no issues).
- Native Windows suite is required before merge for the new Git publication path under `coga-dev/testing`. Existing harness host no longer exists. Human explicitly deferred Windows verification to review; it remains required before merge. No host was provisioned. The harness requires approval outside windows-native tickets. AWS profile `coga-test` is configured; a read-only status attempt needed escalation to refresh SSO cache.

## Implement handoff

- Implemented and pushed both commits on the recorded branch. Fresh final fetch confirms the branch contains current `origin/main`; no implementation changes are uncommitted. The projected ticket remains outside the implementation commits.
- Final Linux receipts: full suite **4,719 passed, 33 skipped in 960.48s**; focused megalaunch/blackboard plus packaging **233 passed in 33.07s**. Repo validation: **107 OK, 10 warnings, no errors**. Seeded fixture validation: **5 OK, no issues**. Exact commands, tested head/base, platform, interpreter, and omission reasons are in PR preparation below.
- No PR opened. Independent review is the next workflow step. Actual implementer is **Codex**, despite the ticket's configured `agent: claude`; assess review independence using the actual identity, as the preparation contract requires.
- Human explicitly deferred the required native Windows full-suite receipt to review; obtain it before merge. No Windows resources were provisioned. Local tests used Python 3.12.12, so this step supplies no Python 3.11 floor receipt.
- Residual adjacent finding: timestamp-only blocker IDs can collide for asks appended within one second (`blackboard._blocker_id`). This implementation safely targets complete captured records. Other ID consumers and ID generation remain outside scope; no existing follow-up ticket was found. Preserve this finding for the later durable-knowledge/Retro handoff.

## PR

```yaml
title: Keep unfinished dependency blockers open in megalaunch
author: codex
author_evidence: Actual implement session used Codex, based on GPT-6. No model override was requested;
  an exact runtime model identifier is not exposed. The ticket configures claude, which is not the implementing
  identity.
head: 975a5b81d1191fa1da74bb1309118e0a40ee9f34
base: d53c5566e3454ae6ecdb1809ce131279146cf0f0
depth: deep
rationale: Changes dependency-drain publication and activation decisions. Independent review is the next
  workflow step; the required Windows receipt was deferred there by the human.
implementation: Resolve each satisfied dependency blocker with its own automatic answer using the captured
  blocker record. Publish partial answers under an exact ticket lease while retaining blocked; publish
  the remaining targeted resolutions and activation together before launch. Preserve all-open manual unblock
  behavior.
deviations: Human approved a separate one-link repair for an existing packaging navigation failure. Windows
  verification was explicitly deferred to review.
limitations: Native Windows full-suite evidence is still required before merge. Local verification uses
  Python 3.12.12; Python 3.11 floor evidence was not collected in this step.
files:
  docs/contexts/coga-dev/internals/branch-sweep/SKILL.md: Human-approved removal of a stale anchor found
    by the required packaging navigation check.
  src/coga/blackboard.py: Add targeted resolution of captured blocker records while preserving other asks,
    historical answers, and inert text.
  src/coga/megalaunch.py: Select satisfied dependency entries; publish partial resolutions while blocked
    and retain atomic activation when every remaining ask is satisfied.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md: Own the explicit multiple-dependency
    and mixed human/dependency blocker contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md: Document partial publication,
    exact snapshots, activation, recovery, and reconsideration in the drain.
  tests/test_blackboard.py: Cover exact-record targeting despite duplicate IDs and preservation of archived,
    fenced, legacy, and previously answered entries.
  tests/test_megalaunch.py: Cover unfinished/canceled/human blockers, two satisfied dependencies, same-run
    fixed points, multiple refs per ask, and partial publication success/refusal/uncertainty.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Independent code review belongs to the following peer-review workflow step; design/approach
    confirmation is not code review.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest tests/test_packaging.py
    tests/test_megalaunch.py tests/test_blackboard.py -q
  status: passed
  detail: '233 passed in 33.07s; Pop!_OS 24.04 LTS, Linux x86_64, Python 3.12.12. Log: /tmp/coga-dependency-final-focused-pytest.log.'
  head: 975a5b81d1191fa1da74bb1309118e0a40ee9f34
  base: d53c5566e3454ae6ecdb1809ce131279146cf0f0
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest -q
  status: passed
  detail: '4719 passed, 33 skipped in 960.48s (0:16:00); Pop!_OS 24.04 LTS, Linux x86_64 (kernel 7.2.15-76070215-generic),
    Python 3.12.12. Code, tests, and docs matched the committed tree throughout this final run. Log: /tmp/coga-dependency-final-full-pytest.log.'
  head: 975a5b81d1191fa1da74bb1309118e0a40ee9f34
  base: d53c5566e3454ae6ecdb1809ce131279146cf0f0
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --json
  status: passed
  detail: 107 OK; 10 warnings; 0 errors. Python 3.12.12 on Pop!_OS 24.04 LTS.
  head: 975a5b81d1191fa1da74bb1309118e0a40ee9f34
  base: d53c5566e3454ae6ecdb1809ce131279146cf0f0
- command: cd tests/fixtures/seeded-repo/coga && env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src
    /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json
  status: passed
  detail: 5 OK; 0 warnings; 0 errors. Python 3.12.12 on Pop!_OS 24.04 LTS.
  head: 975a5b81d1191fa1da74bb1309118e0a40ee9f34
  base: d53c5566e3454ae6ecdb1809ce131279146cf0f0
- command: Native Windows full suite at the reviewed head
  status: not-run
  detail: Human explicitly deferred Windows verification to review. The new Git publication path requires
    this receipt before merge under coga-dev/testing. No Windows host was provisioned.
- command: git diff --check
  status: passed
  head: 975a5b81d1191fa1da74bb1309118e0a40ee9f34
  base: d53c5566e3454ae6ecdb1809ce131279146cf0f0
  detail: No whitespace errors in the implementation or projected handoff.
```
