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

Done means three observations are recorded on this ticket's blackboard (or
in a linked PR/comment), each with exact query text and results. The wheel
version and hash and the UTC run windows are recorded too.
1. The first sweep from a release wheel produces one row with the minted repo
   UUID and zero movement, and it matches the Slack receipt's prepared envelope.
2. A later run after a known forward advance or completion produces another
   row with the same UUID and the expected movement count.
3. A run after setting `[telemetry] enabled = false` produces zero rows in the
   post-disable window.
Also, no returned property carries IP, GeoIP or other unexpected enrichment.
Unexpected fields block acceptance until they are explained. Finally, the
readiness line in `marketing/build-the-launch-plan` is updated with the result.

## Context

The procedure is the attached `coga/telemetry/operations` topic, section
"Clean installed-wheel proof (owner at review)". Follow it exactly. The event
schema, admission gates and loss semantics live in the parent `coga/telemetry`
topic (`docs/contexts/coga/telemetry/SKILL.md`), which is cited rather than
attached. Read "Admission and configuration" for why the proof must run
outside every Coga source tree with no pytest or CI environment.

- The owner executes the task. Agents must not unset test gates, read the
  PostHog operator credential (`~/.posthog/credentials.json`), echo the capture
  key, or run capture or deletion calls themselves.
- Run `posthog-cli api call --json project-get '{}'` before every query, and
  stop unless it returns project `606347`, which is shared with Multiply.
- A capture HTTP success or a missing row alone is not acceptance. Only
  queried rows and receipts count as acceptance evidence.
- Slack must be configured in the scratch repo before the first sweep, because
  fresh init has no notification channels.
- The implementing ticket is `marketing/add-telemetry` (done). See its blackboard
  "Owner review decision — 2026-09-22" for the deferral.
- Out of scope: changing telemetry code, rotating the key, and editing the
  Multiply repo. Its event-catalog follow-up stays separate. If the proof fails,
  record the failure and open a fix ticket instead of patching here.

<!-- coga:blackboard -->

## Verify PostHog telemetry with the live clean-wheel proof

Working memory for this task. No work has started.
