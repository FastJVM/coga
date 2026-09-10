---
slug: marketing/phase-0-audit
title: Phase 0 audit
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: human
  - name: report-to-coga
    skills: []
    assignee: agent
secrets: null
step: 2 (human-owns-and-finishes)
---

## Description

First reference and group all existing marketing material so the owner can
review it as a usable catalogue. Then prepare a fresh planning sequence that
uses the previous work as inspiration. The owner clarified and approved this
reset on 2026-09-10; the earlier three-essay campaign is not the default.

Keep the prior ideas, research and drafts accessible with their dates and
source limits. Update the follow-up writing briefs so they make new choices
with the owner. This authoring work prepares the catalogue and planning
briefs; it does not choose or execute a new campaign.

## Context

### Authored homes and concrete deliverables

- Edit `coga/contexts/marketing/map/SKILL.md` into a catalogue grouped by
  positioning/strategy, previous campaigns/drafts, evidence/examples,
  distribution/audience, writing methods, and public surfaces/dependencies.
  Include all marketing files and relevant material elsewhere in the repo,
  including the parked Relay-era domain proposal. Identify each source's role.
- Edit `coga/contexts/marketing/plan/SKILL.md` as the starting point: catalogue
  review first; then audience/outcome and story/example decisions, reviewed
  pitch, fresh campaign choices, and selected execution work with owners.
- Preserve previous campaign material as linked reference files under
  `coga/contexts/marketing/launch-history/`. Keep historical imperative
  wording clearly outside the current instructions.
- Keep `marketing/positioning` and `marketing/distribution` focused on
  current message status, product/source limits and dated observations.
  Their former creative choices, channel schedule and scorecard are prior
  work to reconsider, not binding inputs.
- Revise the existing drafts
  `marketing/plan/collect-public-examples-for-the-launch` and
  `marketing/plan/write-the-pitch-and-narrative`. The first makes options
  and reaches a story decision with the owner; the second writes final copy
  from that decision. Both keep their human review workflow.
- Reconcile the launch-plan, essay, README and community briefs and writing
  procedure with the reset. Existing drafts remain candidate work until the
  owner selects and briefs them; an existing ticket does not choose a format
  or create a publication gate.
- Leave the current worklist and verification on this blackboard. The existing
  `marketing/build-the-launch-plan` ticket owns later campaign choices and
  the keep/change/defer/drop decisions.

These contexts are editing targets, so name and read their files rather than
attaching their full bodies to this ticket. No new context namespace or
workflow is needed.

### Decisions and limits

The owner wants to start afresh. Audience, story, strategic fork, tone,
deliverable count/format, channels, sequence and campaign-specific readiness
and success criteria remain open. Prior wording is inspiration. Product
purpose and behavior remain grounded in `docs/vision.md` and the Coga
contracts; fresh copy must describe the product accurately.

The owner dropped the marketing token/time experiment on 2026-09-09. Do not
restore receipt collection, paired runs, a token-measurement ticket or an
efficiency-result gate. Audience measurement remains in scope; the new
campaign must choose its own objective, signals and checkpoints.

Examples may be newly authored illustrations or public demonstrations.
Identify them honestly. Observed-event claims need public support; a context
appearing in a prompt alone does not demonstrate successful reuse. All
private-repo narrative quotations are excluded. The existing
`narrative-candidates-md-publishes-log-text-the-own` ticket owns the
attachment's disposition; do not copy or inspect the private-repo sources.

The original audit checks are complete. Preserve `step-1-findings.md` and
`audit-history.md` as dated sources. September 2–3 account observations are
not live certification. Existing product fixes keep their own scope; this
catalogue does not make the whole cleanup queue a new campaign prerequisite.

Keep the context root and all task lifecycle/role fields and frozen workflows.
The documentation-reorganization ticket owns any later relocation. Product
implementation, account actions, external publication and ticket lifecycle
transitions are outside this authoring work. The audit stays at step 2,
`human-owns-and-finishes`, until an explicit owner transition.

### Completion checks

- Every core marketing file and relevant related source is referenced and
  grouped, with current/reference/dated/excluded status clear.
- Previous campaign material is preserved and no longer governs new work.
- The plan and follow-up briefs expose the open decisions, outputs and owners;
  the story decision precedes final copy.
- No current brief or writing procedure restores the old three-post,
  channel-order, scorecard or token-measurement prerequisites.
- Local links, source coverage, validation against baseline, metadata
  preservation and an independent authoring review are recorded.

<!-- coga:blackboard -->

## Current handoff — 2026-09-10

The owner approved completing the subject catalogue and preparing a fresh
planning sequence. The prior campaign is inspiration; no replacement
campaign has been selected. Catalogue, plan, source contexts and follow-up
briefs have been revised. Link/coverage checks and independent authoring
review are in progress. The frozen human step remains unchanged.

## Worklist

- [agent → nicktoper] Review the grouped catalogue and fresh preparation brief.
- [claude → nicktoper] Story/examples draft: choose reader/outcome and story.
- [claude → nicktoper] Pitch/narrative draft: write from the chosen story.
- [nicktoper] Existing launch-plan gate: select campaign, audience measurement,
  necessary dependencies and keep/change/defer/drop dispositions.
- [selected ticket assignees] Author execution briefs and workflows after selection.
- [nicktoper] Existing confidentiality and audit-status tickets retain their
  separate ownership. No lifecycle transition is part of this authoring work.

## Earlier extraction record — before the fresh start

Historical decisions, task states and verification below describe the
September 9 extraction. Their campaign commitments were superseded by the
September 10 owner reset; the earlier product observations retain their dates.

### Decisions — 2026-09-09

- Owner approved extracting the audit into marketing contexts and creating
  follow-up writing tickets under `marketing/plan/`.
- Owner corrected the first writing task on 2026-09-09: make and decide the
  story/examples, rather than collecting an existing source packet. Newly
  authored illustrations are allowed; factual event claims still need support.
- Owner dropped token measurement from the marketing launch. The former
  protocol is archived in `marketing/launch-history`; real public examples
  remain required.
- Original research is preserved in `step-1-findings.md` and
  `audit-history.md`. Reusable decisions now live in the contexts above;
  this blackboard owns the current handoff.
- The frozen workflow remains at step 2, `human-owns-and-finishes`.
  Extraction does not authorize closing the audit or running a next step.

### Worklist

Recorded repo state on 2026-09-09; external observations retain their original
dates in `marketing/distribution`.

- [agent] Knowledge extraction — `marketing/map`, `marketing/distribution` and the revised `marketing/plan` prepared; consumers updated for the owner decision.
- [claude → nicktoper] Make and decide the story/examples — draft `marketing/plan/collect-public-examples-for-the-launch`; make options, recommend one, then record the owner's decision before final copy.
- [claude → nicktoper] Pitch and narrative — draft `marketing/plan/write-the-pitch-and-narrative`; write from the chosen story and examples.
- [nicktoper] Campaign and keep/drop decisions — existing `marketing/build-the-launch-plan` owner gate; reconcile the new message, retained essays and audience scorecard.
- [cleanup assignees] Product prerequisites — branch-detection and source/debug-install tickets done; Python 3.11 fix at peer review; release, placeholder yank, first-run noise, Slack error handling, repo hygiene and demo check remain drafts.
- [nicktoper] Release — `cleanup/publish-coga-1-0-to-pypi`; land the Python 3.11 fix before publishing.
- [post-1 agent, nicktoper] Install proof — after release, record a fresh Python 3.11 README run from PyPI through a real first agent launch, including version and environment.
- [marketing/readme-top] Landing page — draft; apply the reviewed pitch and provide a clear reader path. Workflow still needs authoring before activation.
- [nicktoper, marketing/discord] Community — choose Discussions or Discord, create it, test a real question and put the exact URL in the post. Ticket is a draft without a workflow.
- [nicktoper] Account inputs — Bookface standing, Reddit joined-subreddit list and a founder-present HN window remain unrecorded. Reddit can be omitted if no eligible community fits.
- [nicktoper, retro agent] Baseline — record blog subscribers, trailing-30-day views, community count, stars and downloads, plus a completed subscribe test; use `marketing/distribution` for definitions.
- [agent] Audience follow-up — create `marketing/phase-1-retro` before post 1 with the baseline, scorecard and dated 24-hour / 72-hour / day-14 checkpoints.
- [post-ticket agent, nicktoper] Post package — public sources, full draft/replies, craft and claim checks, approved titles and channel copy remain to produce; author the post workflows before activation.
- [nicktoper] Confidential attachment — resolve the existing `narrative-candidates-md-publishes-log-text-the-own` ticket before closing or archiving this task directory; no private quotation belongs in the new source packet.
- [nicktoper] Audit lifecycle — reconcile `phase-0-audit-is-complete-per-the-plan-but-still-i` at the owner gate; this session makes no lifecycle transition.
- [dropped, owner] Marketing token experiment — no collection ticket, paired runs, receipt quota or measurement-dependent publication gate.

### Verification

- Coverage checked on 2026-09-09: all 19 current marketing context, skill,
  ticket and attachment files are represented in the map; no missing files
  or broken local links.
- Local links in the new/revised context map and audit attachments: pass.
- `git diff --check`: pass.
- `coga validate --json`: no new errors against the saved baseline. The two
  new drafts add the expected `unfrozen-workflow` warnings for their
  authoring-time workflow names; activation freezes them.
- `coga launch <slug> --prompt-report` composed the audit and both new
  drafts without starting agents. Coga's accompanying Git fetch initially
  hit the network sandbox; the approved retry succeeded.
- Existing lifecycle fields, role fields and frozen workflows were compared
  with their pre-edit values and preserved. Marketing contexts/skill have
  no packaged twins.
- Independent review found one unsupported duration in positioning. Removed
  it, corrected the stale fork pointer and consolidated the opening guidance;
  the reviewer verified the fixes. The optional broader positioning trim is
  carried by the pitch ticket.
