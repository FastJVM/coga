---
title: Route large-blackboard validate issues as state edits, not PR proposals
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
step: 2 (peer-review)
agent: claude
launch_generation: pending:3c5e63e1-3797-4545-b82c-65e5ef6b0e1d
---

## Description

Filed by Dream 2026-W44 (Phase 6; knowledge-scan ks-23; Phase 1 validate-drift: large-blackboard). Targets: src/coga/dream_validate_drift.py classify_issue (~L321-343) and the Dream template coga/recurring/dream/ticket.md 'Phase 1 PR proposals' paragraph (plus packaged twin).

dream_validate_drift classifies large-blackboard (and unsynthesized-draft-blackboard) as ACTION_PR_PROPOSAL, so Dream must route each as a pr-required proposal never applied on main. But the remedy (coga/blackboard 'Size and its remedy') edits only the ticket's blackboard and sibling attachments under coga/tasks/**, which coga/state-publication says never rides a PR (coga open-pr refuses a state-only branch). Precedent: slim-the-40-9-kib-blackboard-of-the-macos-and-wind was filed as a code/with-review draft and actually done on main as a state edit, closed with mark done. Decide: classify these as owner/state-edit actions (a draft whose workflow needs no branch/PR, or a direct owner edit) and say so in the Dream template, or state in coga/blackboard that the remedy publishes by state sync.

This run's members (validate-drift: large-blackboard, PR Proposal bucket): context-audiences/02-move-coga-dev-contexts-out-of-the-shipped-set (47.4 KiB) and windows-native/01-core-port-cli-and-test-suite-pass-on-native-window (32.7 KiB). Both are done tickets left on disk as retirement debt (their branches survive in sibling clones), so coga retire <slug> disposes of them; no slimming is needed unless they stay. coga validate --json is the live member list.

## Context

`src/coga/dream_validate_drift.py` — `classify_issue` selects the remediation
bucket consumed by Dream's Phase 6. Cite `coga/blackboard` (read “Size and its
remedy” and “Draft-activation readiness”) and `coga/state-publication` (read
“Control versus feature checkouts”) for the cleanup and publication contracts.
Dream's own routing instructions live in `coga/recurring/dream/ticket.md`;
keep its packaged twin in sync.

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

branch: coga/route-large-blackboard-state-edits-20261027

## Implement handoff

Implemented and pushed `33db39ff3af79eb23e77eab2b915ef2cc8f328df` on the branch
above. This session used Codex, not the ticket's configured Claude agent.

- `src/coga/dream_validate_drift.py` — `classify_issue` routes both
  `large-blackboard` and `unsynthesized-draft-blackboard` to `human-needed`.
  Remediation preserves owner judgment, historical evidence, and intentional
  production notes, and directs publication through Coga state sync.
- Dream files/reuses `brief-for-human` drafts without branch/PR requirements.
  Its template also reroutes these kinds when an older recipe still reports
  them as PR proposals, so the instruction remains compatible with control's
  old classifier if recurring-state publication reaches it before the code.
- Done tickets keep the existing Retro/retirement route; a recurring writer's
  state goes to that writer's owner. The example tickets were not modified.
- The blackboard topic owns cleanup publication guidance. Both changed
  canonical files match their packaged twins. A seeded owner-workflow draft
  represents the intended route without adding an oversized blackboard.
- Four regression tests failed before the fix. Final committed-tree results:
  4,123 passed, 10 native-Windows skips; seeded validation: 5 OK, no issues.
  Live validation: 149 OK, 49 warnings (22 stuck, 19 unfrozen workflow,
  5 empty description, 3 large blackboard). All three large-blackboard issues
  classify as human-needed: the two cited completed tickets and recurring/dream.
- Final fetch/rebase found no main drift; the tested commit stayed unchanged.
  The branch is pushed, and this manual checkout returned to clean, current
  main before writing this handoff. No PR has been opened. Independent review
  is the next workflow step; it must refresh preparation after any changes.

## PR

```yaml
title: Route blackboard validation cleanup through owner state edits
author: codex
author_evidence: This implement session ran Codex; the configured ticket agent was not used as authorship evidence.
head: 33db39ff3af79eb23e77eab2b915ef2cc8f328df
base: 13f9847a11bf340225bd5f9afbc661655665f4bf
depth: deep
rationale: Bounded routing correction with passing checks; independent code review is pending the next workflow step.
implementation: Route both blackboard warning kinds to human-needed, retain owner and retirement decisions, document state publication, and cover the classifier, report buckets, template, and seeded workflow.
deviations: None. Reused the existing human-needed bucket and brief-for-human workflow.
limitations: No live Dream agent run. Linux verification passed; native Windows checks were skipped by their platform guards.
files:
  src/coga/dream_validate_drift.py: Classify blackboard cleanup as owner-directed state work and describe its publication route.
  coga/recurring/dream/ticket.md: Route cleanup through owner drafts and handle old recipe output before the PR-proposal rule.
  src/coga/resources/templates/coga/recurring/dream/ticket.md: Ship the matching Dream routing instructions.
  docs/contexts/coga/blackboard/SKILL.md: Document state publication for draft synthesis and size cleanup.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: Ship the matching blackboard publication guidance.
  tests/test_dream_validate_drift.py: Regress both classifications and prevent blackboard issues from entering the report's PR bucket.
  tests/test_dream_worker_templates.py: Verify the owner route, retirement/writer exceptions, and compatibility with older recipe output.
  tests/fixtures/seeded-repo/coga/tasks/blackboard-state-cleanup.md: Represent an owner cleanup draft with a frozen workflow and no branch or PR gates.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Implement ends before the workflow's independent peer-review step; no code review was claimed.
checks:
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest > /tmp/coga-blackboard-state-edits-pytest.log 2>&1
    status: passed
    head: 33db39ff3af79eb23e77eab2b915ef2cc8f328df
    base: 13f9847a11bf340225bd5f9afbc661655665f4bf
    detail: 4123 passed, 10 skipped in 416.03 seconds; skips require native Windows Job Objects or PowerShell. Ran on the committed tree; final rebase was a no-op.
  - command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/coga validate --json
    status: passed
    head: 33db39ff3af79eb23e77eab2b915ef2cc8f328df
    base: 13f9847a11bf340225bd5f9afbc661655665f4bf
    detail: From tests/fixtures/seeded-repo/coga; exit 0, 5 OK, no issues or fixes.
  - command: PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/coga validate --json > /tmp/coga-blackboard-state-edits-live-validation.json
    status: passed
    head: 33db39ff3af79eb23e77eab2b915ef2cc8f328df
    base: 13f9847a11bf340225bd5f9afbc661655665f4bf
    detail: Live repo read-only validation exited 0; 149 OK and 49 warnings, including three large blackboards; no validation errors.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: 33db39ff3af79eb23e77eab2b915ef2cc8f328df
    base: 13f9847a11bf340225bd5f9afbc661655665f4bf
    detail: Ran on the feature branch after final fetch/rebase; no whitespace errors.
```
