---
slug: marketing/phase-0-audit
title: Phase 0 audit
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
  - marketing/map
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

Extract the reusable knowledge from the completed phase-0 audit into focused
marketing contexts, and leave a current worklist with clear owners. Make
`marketing/plan` the starting point: locate the documents, list needed
deliverables and cuts, make and decide the story/examples, write the pitch/narrative,
then carry the decisions into the existing cleanup and launch tickets.

The owner approved this organization and dropped the marketing token/time
experiment on 2026-09-09. Prepare the writing work as draft tickets under
`marketing/plan/`. This authoring session does not execute those new tickets
or advance this audit's frozen workflow.

## Context

### Authored homes and handoffs

- `marketing/map`: document locations, authority by subject, and owning
  tickets, including the newer pitch in the documentation-reorganization
  ticket. Read the full mapped sources only as needed.
- `marketing/distribution`: dated account/surface observations, channel
  policy, attribution, audience scorecard and response branches.
- `marketing/plan`: preparation sequence, needed launch deliverables,
  retained essay briefs, publication gates and execution owners.
- `marketing/positioning`: reusable message direction, audience, voice and
  honest limits. The owner clarification of 2026-09-08 leads with managing the
  intent, instructions, knowledge and state an AI session works from. Final
  wording is still the writing ticket's deliverable.
- `marketing/plan/collect-public-examples-for-the-launch`: first, make concrete
  story/example options and decide with the owner which to use. The old
  collection ref is retained; this is a creative and editorial task.
- `marketing/plan/write-the-pitch-and-narrative`: then write the reusable
  pitch and narrative from that material, for owner review.
- `marketing/build-the-launch-plan`: use the supported message to finalize
  the campaign and keep/drop list. Existing README, community, post and
  cleanup tickets execute the retained work.

### Current decisions and limits

The three existing post tickets remain retained. Their angles are decluttering,
human amplification and documentation as a cache. The new pitch must be
reconciled with those briefs at owner review; extraction alone does not cancel
a post or approve final copy.

The token experiment, receipt quota, paired task launches and requirement to
create `marketing/token-receipts` are dropped. Post 3 instead needs an exact
public context, the question it answers and a later session showing the
understanding in use. Do not infer an efficiency result from that example.
Audience measurement remains part of the launch.

All private-repo narrative quotations are excluded from launch sources. The
existing `narrative-candidates-md-publishes-log-text-the-own` ticket owns the
attachment's disposition. Do not copy the quotations into a new context or
source packet.

The original audit checks are complete. Preserve them in the dated
`step-1-findings.md` and `audit-history.md` attachments, rather than rerunning
them or treating their old instructions as current gates. Public account
observations are dated September 2–3; this extraction does not certify live
sites or refreshed metrics.

Keep the current context root. The separate
`redo-documentation-dir-and-merge-it-with-context-b` ticket owns any move to
`docs/contexts`; its proposed marketing map must include this extraction and
must not recreate the retired token requirement. No product fixes, external
publication, configuration edits, or ticket lifecycle changes are part of this
authoring work.

### Completion checks for this extraction

- Each reusable subject has an authored home linked from the map and plan.
- Needed deliverables, approved cuts and unresolved owner inputs have named
  owners in the worklist.
- The new writing tickets have concrete outputs, source constraints, a human
  review workflow and an explicit story-decision-before-final-copy dependency.
- Active consumers have no token-measurement prerequisite; historical notes
  are clearly labeled.
- Links, task/context validation and an independent authoring review are
  recorded. Preserve the current `draft-for-human` snapshot and human step.

<!-- coga:blackboard -->

## Decisions — 2026-09-09

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

## Worklist

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

## Verification

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
