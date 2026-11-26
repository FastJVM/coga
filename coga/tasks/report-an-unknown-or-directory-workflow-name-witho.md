---
title: Report an unknown or directory workflow name without a traceback
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: open-branch
    skills: []
    assignee: agent
    requires: branch
    run: git/open-branch
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: push-and-open-pr
    skills: []
    assignee: agent
    requires: pr
    run: git/push-and-open-pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 4 (push-and-open-pr)
agent: claude
---

## Description

`coga create --workflow code` crashes with an uncaught `WorkflowNotFoundError` and a full Rich traceback (`create_task` in `src/coga/create.py` calls `Workflow.load(resolve_workflow_path(...))`, and `create_draft` in `src/coga/commands/create.py` does not catch it). `code` is a directory of workflows (`code/with-review`, `code/with-self-review`, `code/design-then-implement`, `code/agent-merge`), not a workflow, so this is an easy mistake to make.

Observed 2026-11-23 while creating a ticket from `coga chat`.

### Requirements

- An unknown workflow name exits non-zero with a one-line error and no traceback, from `coga create` and every other command that resolves a workflow name (check `coga ticket` and any frontmatter `workflow:` resolution at launch or validate).
- When the name is a workflow directory, the error lists the workflows inside it, for example "`code` is a workflow group; use one of: code/agent-merge, code/design-then-implement, code/with-review, code/with-self-review".
- Otherwise, suggest close matches when there are any. Resolution stays local-first, then bundled, and suggestions cover both.
- Add tests for a directory name, an unknown name, and a typo with a close match.

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
        - name: open-branch
          run: git/open-branch               # Local-first skill directory containing run.py.
          assignee: agent
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (open-branch)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
A workflow run: selects a script for its step. A sibling ticket.py supplies the default script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

The recurring runner writes delegate on materialized period tickets. It
names the parent template's frozen bootstrap/<name> target.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev records branch:, base:, remote:, reviewed: (the commit OID),
and pr: (the full /pull/ URL). Write one field per line and omit unknown
values. coga/git owns the fields and the workflow that writes them.

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

branch: coga/report-an-unknown-or-directory-workflow-name-wit-41c8d8
base: main
remote: origin
reviewed: 7b1aa74f11c6c182fca335b2d405c095f50f6a26

## Peer review notes

- Reviewed the complete diff against fetched `origin/main`. The corrections
  cover launch preflight, guided authoring, validation of recurring templates,
  and suggestions for unqualified typos. The launch tests cover drafts and
  active tickets with a bare workflow name and verify that refusal leaves the
  ticket bytes intact.
- The Python 3.11 context-symlink failure reproduces on the recorded base.
  On this host `Path.rglob("SKILL.md")` omitted a dangling symlink on 3.11.15
  and found it on 3.12.12. The failing test exercises context discovery.
- Native Windows and macOS verification is deferred to release.

## PR

```yaml
title: Report an unknown or directory workflow name without a traceback
author: claude
author_evidence: >-
  Claude Code (claude-opus-5-5) implemented 82e979f97b5d5bd6262f8b7c25b9489cf0b44e04
  in megalaunch run 2d5a580a-a4fc-46af-8205-25b5dbc0767f. Codex authored
  review corrections in 148fedb0b, c9f48ff09 and 7b1aa74f1.
head: 7b1aa74f11c6c182fca335b2d405c095f50f6a26
base: 1bb7e63e2c5a724321660e28eed825d88a4dbd10
depth: deep
rationale: >-
  The diagnostic spans multiple command boundaries. The Python 3.11 full suite
  reproduced a context-symlink failure also present on the base. The Python
  3.12 full suite and Python 3.11 focused workflow checks passed.
implementation: >-
  Resolve workflow refs local-first and then from bundled definitions. Report
  an absent ref with the members of its group or close matches, including
  matches for a bare-name typo. Creation, activation, bump, launch, guided
  authoring, and recurring workflows use that diagnosis. Validation reports a
  broken workflow error for an unloadable ref on a task or recurring template.
deviations: >-
  The create library keeps its WorkflowError contract. The CLI converts that
  error to a nonzero exit and a diagnostic.
limitations: >-
  Frozen snapshots use the documented missing-inline-definition placeholder
  in prompt composition. Native Windows and macOS checks are deferred to
  release.
files:
  src/coga/commands/bump.py: "Diagnose an unknown bare workflow ref during bump."
  src/coga/commands/create.py: "Render workflow errors at the create CLI boundary."
  src/coga/commands/ticket.py: "Report a single authored workflow error on one line."
  src/coga/create.py: "Load the requested workflow through the shared diagnostic."
  src/coga/launch.py: "Surface an unloadable workflow ref during launch preflight."
  src/coga/launch_script.py: "Use the shared workflow loader when selecting a draft script."
  src/coga/mark.py: "Use the shared workflow loader when freezing a ref on activation."
  src/coga/paths.py: "List group members and close matches across both workflow roots."
  src/coga/recurring.py: "Use the shared loader for recurring-template workflow checks."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: "Document the workflow-name diagnostic."
  src/coga/resources/templates/coga/bootstrap/recurring-promote/promotion.py: "Use the shared loader when validating promoted templates."
  src/coga/validate.py: "Report errors for unloadable task and recurring-template workflow refs."
  src/coga/workflow.py: "Use the shared workflow loader for launch Git-mode selection."
  tests/test_create.py: "Cover an unknown name, group, typo, and escaped newline at the CLI."
  tests/test_launch.py: "Cover draft and active bare refs at launch with no ticket mutation."
  tests/test_paths.py: "Cover both roots, starter exclusions, group members, and close matches."
  tests/test_recurring.py: "Expect the shared unknown-workflow diagnostic from a recurring scan."
  tests/test_ticket.py: "Exercise guided authoring finalization after an invalid workflow selection."
  tests/test_validate.py: "Check task and recurring-template errors and one-line group output."
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 7b1aa74f11c6c182fca335b2d405c095f50f6a26
  base: 1bb7e63e2c5a724321660e28eed825d88a4dbd10
  detail: >-
    Codex reviewed the full base-to-head diff and traced the workflow-name
    resolution paths in a session separate from Claude's implementation.
    Codex authored and self-reviewed the correction commits. No unresolved
    workflow-diagnostic findings on this head.
checks:
  - command: 'TMPDIR=/tmp/coga-workflow-review.pvMN3rO0/py312 PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q'
    status: passed
    head: 7b1aa74f11c6c182fca335b2d405c095f50f6a26
    base: 1bb7e63e2c5a724321660e28eed825d88a4dbd10
    detail: "Pop!_OS 24.04 LTS, Python 3.12.12. 3254 passed, 29 skipped in 209.64s."
  - command: 'TMPDIR=/tmp/coga-workflow-review.pvMN3rO0 PYTHONPATH=$PWD/src /tmp/coga-workflow-review.pvMN3rO0/venv/bin/python -m pytest -q'
    status: failed
    head: 7b1aa74f11c6c182fca335b2d405c095f50f6a26
    base: 1bb7e63e2c5a724321660e28eed825d88a4dbd10
    detail: >-
      Pop!_OS 24.04 LTS, Python 3.11.15. 3253 passed, 29 skipped, 1 failed
      in 213.32s. tests/test_config.py::test_layout_context_artifact_symlink_rejected
      also failed in the archived source snapshot of the recorded base
      on the same interpreter (1 failed in 0.46s).
  - command: >-
      TMPDIR=/tmp/coga-workflow-review.pvMN3rO0 PYTHONPATH=$PWD/src /tmp/coga-workflow-review.pvMN3rO0/venv/bin/python -m pytest -q
      tests/test_paths.py tests/test_create.py tests/test_launch.py tests/test_ticket.py
      tests/test_validate.py tests/test_recurring.py -k 'unknown_workflow or
      workflow_not_found or workflow_group or unknown_authored_workflow or
      unknown_recurring_template_workflow or unresolvable_workflow'
    status: passed
    head: 7b1aa74f11c6c182fca335b2d405c095f50f6a26
    base: 1bb7e63e2c5a724321660e28eed825d88a4dbd10
    detail: "Pop!_OS 24.04 LTS, Python 3.11.15. 13 passed, 761 deselected in 0.79s."
  - command: 'PYTHONPATH=$PWD/src /tmp/coga-workflow-review.pvMN3rO0/venv/bin/python -m coga.cli validate --json > /tmp/coga-workflow-review.pvMN3rO0/validate.json'
    status: passed
    head: 7b1aa74f11c6c182fca335b2d405c095f50f6a26
    base: 1bb7e63e2c5a724321660e28eed825d88a4dbd10
    detail: "Pop!_OS 24.04 LTS, Python 3.11.15. Exit 0 with 0 errors and 82 warnings."
  - command: 'env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /tmp/coga-workflow-review.pvMN3rO0/venv/bin/python -m coga.cli create --workflow code "Workflow review probe"'
    status: passed
    head: 7b1aa74f11c6c182fca335b2d405c095f50f6a26
    base: 1bb7e63e2c5a724321660e28eed825d88a4dbd10
    detail: >-
      Pop!_OS 24.04 LTS, Python 3.11.15. In a disposable fixture, exit 2
      and one line listing all four code group members.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: 7b1aa74f11c6c182fca335b2d405c095f50f6a26
    base: 1bb7e63e2c5a724321660e28eed825d88a4dbd10
    detail: "Exit 0 with no whitespace findings."
```
