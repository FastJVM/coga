---
title: Execute the V1 launch
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
step: 2 (human-owns-and-finishes)
---

## Description

Execute the approved V1 marketing plan: publish one argument for Coga as a
human instrument, learn from the response, then launch the working product on
Show HN. The owner approved this simplification on 2026-09-21 and explicitly
confirmed that PostHog must be finished before launch.

This ticket owns launch readiness, the owner publication checklist, response
triage and the Show HN package. Done means the idea piece and Show HN have
actual URLs/dates recorded, the README/install/onboarding/PostHog prerequisites
have verification evidence, and the owner has recorded the useful feedback
and next actions. It remains at its existing human-owned execution step.

## Context

This ticket owns the remaining publication decisions. The README is the
public presentation; the [idea-piece brief](idea-piece.md#claim-and-wording-limits)
owns the argument and claim limits, which also apply to the Show HN package.
Read those live sources when preparing copy. The marketing context library
was archived by owner decision on 2026-10-15; current work must not depend on
reading it. Record accepted publication changes here and editorial changes
in the idea-piece ticket or README.

### Execution checklist

- Track `finish-the-readme-launch-checks-left-open-by-readm` (the remaining
  checks from retired `marketing/readme-top`), the `marketing/fix-installer/` tickets
  (clean-install harnesses, then the run that files each issue; including
  one-task onboarding). The authenticated Linux/macOS × PyPI/main rerun is
  owned by `marketing/fix-installer/complete-the-authenticated-clean-install-audit`;
  the earlier installer audit closed with authentication blockers and does
  not establish a completed first task. Track that evidence alongside
  the [weekly snapshot contract](https://github.com/FastJVM/coga/blob/main/coga/recurring/phone-home/ticket.md). Record the verified first-run
  path and PostHog acceptance evidence; this ticket does not implement them.
- `marketing/idea-piece` produces the single argument and concrete proof.
  The owner chooses its publication venue and approves/publishes the copy.
  This is publication of an argument, not a separate full product launch.
- Collect objections and first-run feedback after publication. Route concrete
  README/onboarding corrections to the existing tickets before Show HN.
- Prepare a self-contained Show HN title, introduction, working product link,
  install/example path and replies. Readers need not have seen the argument.
- Before the public product launch, obtain the verified release links from
  `marketing/publish-coga-1-0-as-the-final-v1-step`, following the final-release
  ordering: finish remaining V1 changes and readiness checks, publish and
  verify 1.0.0 as the last product-delivery step, then launch publicly.
- Target roughly one week after the idea piece, conditional on readiness and
  owner availability. Recheck Show HN rules and links before submission;
  the owner submits and is available to discuss the work. No vote solicitation.
- Use the existing PostHog ticket's adopted measurement contract plus dated
  public/voluntary feedback. Record observations and limitations after the
  launch; do not reinstate old numeric scorecards or a day-14 gate.

### Measurement and distribution

The idea piece's venue is the owner's editorial choice; publish it as ordinary
reading, not a Show HN. No additional channel sequence is implied. Before
Show HN, verify the current [submission guidance](https://news.ycombinator.com/showhn.html)
and working product/install links. The owner publishes and handles personal
accounts; preparing this ticket grants no publication authorization.

Record dated reactions, objections, first-run friction and adoption/activity
observations with their limits. The weekly PostHog signal counts repos with
active sweeps, not installs; it proves neither productivity nor attribution.
Stars, downloads and voluntary feedback may supplement it. The owner-only
live clean-wheel proof in `marketing/verify-posthog-telemetry-with-the-live-clean-wheel`
remains a launch gate.

### Approved scope and disposition

Keep README, installer/onboarding and PostHog. Consolidate story, pitch,
narrative and the three essays into the idea piece. Drop Discord/community
setup as a V1 prerequisite. No separate creative pipeline, three-essay
campaign, token/time experiment or additional channel campaign is required.
Domain purchase and first-user targeting/recruiting are not launch gates.

The earlier launch-plan ticket is preserved in
`docs/archive/launch-programs/launch-plan-before-v1.md`; the audit
and its public evidence are under `docs/archive/launch-programs/phase-0-audit/`.
These are dated references, not current work. Existing lifecycle status,
step and frozen roles are preserved; this revision authorizes no publication
or workflow advancement.

<!-- coga:blackboard -->

## Owner decision — 2026-09-21

Approved the instrument positioning, one idea piece followed by Show HN,
README and installer/one-task onboarding prerequisites, and completion of
PostHog. The proposed zero-telemetry substitution was explicitly rejected.
Prior campaign decisions are archived outside this ticket; the current body
and marketing contexts own the V1 plan. Existing human step is preserved.

## Readiness — 2026-09-25

- PostHog: implemented and merged (PR #880, 2026-09-22) and documented in
  `coga/telemetry` and `coga/telemetry/operations`. The live clean-wheel proof
  was deferred by the owner and has **not** run. It is tracked in
  `marketing/verify-posthog-telemetry-with-the-live-clean-wheel` (draft).
  It is a launch gate.
- README (`marketing/readme-top`), installer/onboarding
  (the `marketing/fix-installer/` tickets) and the idea piece (`marketing/idea-piece`) are
  still drafts and have not been launched.

## Authoring handoff

Current README follow-up (2026-10-26):
`finish-the-readme-launch-checks-left-open-by-readm` owns the remaining
README links, first-steps reconciliation, demo verdict, and carry-forward
example. The September readiness snapshot above is historical; do not route
new work to the retired `marketing/readme-top`.

This revision consolidates the marketing queue and moves public audit evidence
to the launch-history references. No product implementation or external
publication has happened as part of this planning change.

## Evaluator review — V1 ticket consolidation

No blocking brief-content defects found.

- **Launch execution:** Clear prerequisites, evidence, Show HN package and outcome ownership. Preserves the existing human step. Roughly one-week timing remains conditional; PostHog is explicitly required.
- **Idea piece:** Clear reader, argument, observed proof requirement and owner publication boundary. `draft-for-human` fits. Minor improvement: explicitly say the agent-production phase stops with the publication package; write-post’s post-publication checks belong to the later report phase.
- **README:** Bounded edit with meaningful merge/link/claim criteria. Marketing attachments fit. Exact command coordination with installer prevents competing onboarding instructions.
- **Installer/onboarding:** Ready for investigation and implementation: reproduce first, test installed artifact and minimum Python, demonstrate one completed task. Cites relevant architecture/codebase contracts, preserves package boundaries and excludes release authorization.

**Must fix before declaring prompt-scope verification complete:** The supplied report omits workflow layers for all three draft tickets. Measure their planned steps using in-memory frozen workflows and candidate contexts; the current figures establish only draft prompt sizes, not full execution scope.

Current context links and affected docs’ relocated audit links resolve. Superseded campaign instructions are confined to clearly historical references. No files modified.

### Disposition

Scoped idea-piece production explicitly to the prepublication package and the
report phase to post-publication checks. Recomputed prompt scope across all
planned workflow steps using in-memory frozen snapshots, including installer
architecture/codebase candidate attachments; no lifecycle fields were changed.

### Final review and owner acceptance

Independent follow-up found the prompt-scope gap resolved across all planned
steps. Keep plan/positioning attached for the idea piece and README; keep
architecture/codebase cited for installer work, with explicit section reads.
The publication/report boundary is now explicit. No must-fix findings remain.
The owner accepted the strategic evaluation before this change was committed.

### Verification of the planning change

- `coga validate --json`: same two pre-existing errors; the three revised
  drafts have expected unfrozen-workflow warnings.
- In-memory prompt composition covered all planned steps and installer
  candidate attachments without changing persisted workflow positions.
- Local links in changed marketing references and affected docs resolve.
- Packaging twin assertion passed directly; pytest's fixture setup was
  unavailable because the local test interpreter lacks `tomlkit`.
- `git diff --check`: passed. PostHog ticket bytes were preserved.
