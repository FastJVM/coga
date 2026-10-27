---
title: Repair CI and resume with release-focused triggers
status: in_progress
owner: nicktoper
contexts:
- coga-dev/principles
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
launch_generation: 2a600154-82a6-46c3-9e2e-1eda1febbeb2
---

## Description

The owner paused the Test GitHub Actions workflow on 2026-10-26 after repeated failure notifications. Repair the failures and resume CI with a deliberate cadence that fits Coga's frequent PRs and automatic ticket/log pushes. The owner suggested running the full matrix only for releases; evaluate a pre-publication Linux/Windows gate plus manual checks for platform-sensitive changes before choosing the final trigger policy.

The observed failure is tests/test_packaging.py::test_live_and_packaged_copies_stay_identical: coga/recurring/blocker-reminders/ticket.md differs from its packaged twin. The live copy reached main through state sync ahead of its matching feature change. Coordinate with state-sync-published-unmerged-recurring-templates and recurring-unblock-launch; preserve unique work and reconcile against the behavior actually merged. Do not hide the failure by skipping the consistency check.

Evidence: https://github.com/FastJVM/coga/actions/runs/40403547211 failed on both platforms with one failing test (Linux: 4048 passed, 10 skipped; Windows: 3956 passed, 102 skipped). CI was introduced by https://github.com/FastJVM/coga/pull/1097. The all-push trigger and preserved main runs amplify one failure into repeated alerts.

Done when:

- The packaging mismatch and any remaining CI failures are repaired, with green hosted Linux and Windows results tied to the exact tested commit.
- The trigger policy is settled and documented in coga-dev/testing. Prefer the full matrix before release publication plus explicit manual validation; avoid rerunning it for every task/log-only push. If selective PR coverage is retained, define which changes require it and justify the feedback versus runtime tradeoff.
- If release gating is selected, both PyPI and TestPyPI publication paths wait for the required tests; manual test runs do not publish a package.
- Verify the chosen triggers, cancellation/concurrency behavior, and any required-check settings. Routine state updates must not recreate the notification flood.
- Resume the repaired workflow only after the trigger decision is implemented and verified, and confirm GitHub's enabled state.

Billing evidence checked 2026-10-26: FastJVM/coga is public and test.yml uses standard ubuntu-latest/windows-latest runners. GitHub documents their compute minutes as free for public repositories: https://docs.github.com/en/billing/concepts/product-billing/github-actions. Assess runtime, queueing, and notifications separately from billable usage; recheck pricing if repository visibility or runner class changes.

Required reading: docs/contexts/coga-dev/testing/SKILL.md (CI posture and receipts), docs/contexts/coga-dev/packaging/SKILL.md (canonical/package twins), docs/contexts/coga/state-publication/SKILL.md (pre-review publication hazard), and coga/skills/coga/releasing/SKILL.md (resolve its bundled fallback if absent). Keep .github/workflows/release.yml's publication behavior in view when designing a release gate.

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

### Immediate mitigation — 2026-10-26

- The owner asked to turn off CI, create a repair/resumption ticket, and consider
  release-only runs. This is a draft for the design workflow; no repair or new
  trigger policy has been implemented.
- Disabled GitHub workflow `Test` (`test.yml`, ID `394591152`) with
  `gh workflow disable test.yml --repo FastJVM/coga`. The API confirmed
  `state: disabled_manually`.
- Canceled all six active test runs: `40414860631`, `40414505496`,
  `40414500365`, `40414494051`, `40414474870`, and `40414471060`.
  A subsequent run listing showed no unfinished test runs.
- Updated `coga-dev/testing` to own the paused CI posture and the conditions
  for resumption. The workflow definition is retained for the future repair.
- Repository metadata confirmed public visibility. GitHub's billing policy
  makes standard hosted compute free here; the immediate concerns are feedback
  delay, duplicated work, and notifications. The release-focused cadence is a
  proposal, not a completed design decision.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
