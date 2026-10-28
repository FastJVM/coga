---
title: Activate trim-log in this repo after retention merges
status: active
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
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
step: 1 (design)
agent: claude
---

## Description

Activate audit retention in this repository after the compatible implementation
from PR #1129 reaches current main; that PR closes
`commit-journal/trim-the-audit-log`, while this ticket owns the operational
rollout and its cleanup. After owner review of the rollout plan, quiesce and
upgrade every participating writer, run the documented interpreter-resolved
`python -m coga_edge.trim_log --install`, review and publish its five repo
artifacts, and remove the staging copy and temporary packaging exception
through a reviewed cleanup PR. Done means the compatible writers can resume,
the intended weekly job is discoverable on control with existing retention
settings preserved, the effective log merge attribute is unset, all five live
artifacts match their packaged copies, and the cleanup has merged with the
required checks passing. Do not trim the live log manually or force a
production maintenance run to demonstrate activation.

## Context

### Rollout plan and prerequisite

[PR #1129](https://github.com/FastJVM/coga/pull/1129) was open on 2026-10-28.
Before merge, inspect its fetched head `coga/trim-the-audit-log` for the
references below. Recheck merge evidence and control content before adoption.

The design step plans this rollout only. Inventory participating checkouts,
interpreters, long-running sessions and recurring launchers; ask the owner
about writers outside local visibility. The `review-design` gate approves
quiescence, upgrade evidence (wheel artifact/hash and repo revision), checkout
and publication order, verification, compatible recovery and resumption.
Enable files only after the core merges and every writer is quiesced and
upgraded; restart long-running writers before resuming. Task activation queues
planning. Cleanup goes through the later code-review and PR steps.

### Runbook and installer

Required read: `coga/recurring/trim-log/operations.md`, "Adoption after the
compatible wheel upgrade" and recovery sections; before adoption it lives at
`rollout/trim-log/coga/recurring/trim-log/operations.md`. Resolve `COGA_PY` using
`docs/contexts/coga/edge-code/edge-code-upgrades.md`, `migration:interpreter`,
preserving the launcher's interpreter environment. On fresh control, run
`"$COGA_PY" -m coga_edge.trim_log --install`; review these five possible edits:

- `coga/recurring/trim-log/ticket.md`
- `coga/recurring/trim-log/ticket.py`
- `coga/recurring/trim-log/operations.md`
- `coga/workflows/trim-log/run.md`
- `coga/.gitattributes`

`src/coga_edge/trim_log.py`, `install` and `_attribute_plan`, own the bounded
installer. Preserve configuration (including retention `0`), unrelated
attributes, parking, forks and phone-home state; resolve installer refusals
with the owner. Configuration changes, retention redesign, other repositories
and manual log/cursor rewrites are outside scope.

### Publication, cleanup and proof

Coordinate adoption with removal of `rollout/trim-log/` and the
`coga/.gitattributes` exception in `tests/test_packaging.py`,
`INTENTIONALLY_DIVERGENT_TWINS`: installation makes that exception invalid
immediately, so publishing adoption first would break packaging checks.
Design must resolve this ordering before owner approval. Remove obsolete
staging assertions/fallbacks while retaining live/package coverage, and update
the runbook's staging paragraph and remaining staging references with their
packaged twins under `src/coga/resources/templates/coga/`.

Verify installer idempotence before editorial runbook cleanup, or upgrade to
the matching reviewed wheel before repeating it: `trim_log.install` compares
against its installed package, not this source tree. Verify the five published
twins, `git check-attr merge -- coga/log.md` reports `unset`, and the Monday
04:00 local-time schedule and preserved retention setting are discoverable.
Record writer/resumption evidence, published revisions, packaging checks,
scoped Coga validation and workflow-required tests; production trimming is
not required.

`coga-dev/packaging` (`docs/contexts/coga-dev/packaging/SKILL.md`) is cited
rather than attached: read "Canonical copies and twins". Its mapping and
exception rules are enforced by `tests/test_packaging.py`,
`_discover_live_packaged_twins` and
`test_intentional_divergences_stay_real_and_explained`.
`coga/state-publication` (`docs/contexts/coga/state-publication/SKILL.md`) is
cited rather than attached: read "When Coga publishes", "Control versus
feature checkouts" and "Strict publication on demand". Dirty Coga files and
eligible committed recurring state can publish ahead of a PR; a feature
branch alone does not prevent activation.

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
