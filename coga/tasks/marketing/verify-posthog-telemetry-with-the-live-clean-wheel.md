---
title: Verify PostHog telemetry with the live clean-wheel proof
status: draft
owner: nicktoper
contexts:
  - coga/telemetry/operations
workflow:
  name: brief-for-human
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: owner
  - name: verify-read-only
    skills: []
    assignee: agent
step: 1 (brief-and-hand-off)
---

## Description

Run the owner-only live clean-wheel proof for the weekly PostHog snapshot that
merged in PR #880 without it. On 2026-09-22 the owner deferred this proof
("assume it works; owner will test later"), so no real `coga_weekly_snapshot`
row has been queried yet. The V1 plan (`marketing/plan`) makes this
verification a launch gate that marketing simplification does not waive, and
`marketing/build-the-launch-plan` needs its evidence before Show HN.

Build the wheel from `main` at a recorded commit (PR #880 is merged, so there
is no separate review checkout). Record the evidence on this ticket's blackboard.
The procedure says "in the PR", but that PR is already merged. Done means the
blackboard records all of the following:

- The commit, the wheel version and the wheel hash (`sha256sum`).
- The UTC run windows, the prepared payload values from the Slack receipt, the
  period report and the exact qualifying audit lines.
- The exact query text and results for three observations:
  1. The first sweep produces one row with the minted repo UUID and zero
     movement, and it matches the receipt's prepared envelope.
  2. After a known forward advance or completion, a later run produces another
     row with the same UUID and the expected movement count.
  3. After setting `[telemetry] enabled = false`, a run produces zero rows in
     the post-disable window, paired with the automated no-worker/no-HTTP checks.
- The property keys are checked: no IP, GeoIP or other unexpected enrichment.
  Unexpected fields block acceptance until they are explained.

At `human-executes`, the owner runs the proof, pastes the results and updates
the PostHog readiness line on `marketing/build-the-launch-plan`'s blackboard.
The owner may ask the attended agent to write it. At `verify-read-only`, the
agent checks the pasted evidence against the procedure. It runs no
`posthog-cli`, capture or deletion commands itself.

## Context

The procedure is the attached `coga/telemetry/operations` topic, section
"Clean installed-wheel proof (owner at review)". Follow it exactly, including
its project-check and credential rules. Its disable, deletion and rotation
sections are not part of this task. Two topics are cited rather than attached:

- The parent `coga/telemetry` (`docs/contexts/coga/telemetry/SKILL.md`). Read
  "Admission and configuration" for why the proof must run outside every Coga
  source tree with no pytest or CI environment.
- `coga/notifications` (`docs/contexts/coga/notifications/SKILL.md`) for
  enabling Slack in the scratch repo before the first sweep. Fresh init has no
  notification channels.

Other notes:

- The implementing ticket is `marketing/add-telemetry` (done). See its blackboard
  "Owner review decision — 2026-09-22" for the deferral.
- Out of scope: changing telemetry code, rotating the key, and editing the
  Multiply repo. If the proof fails, record the failure and open a fix ticket
  instead of patching here.

<!-- coga:blackboard -->

## Verify PostHog telemetry with the live clean-wheel proof

Working memory for this task. No work has started.
