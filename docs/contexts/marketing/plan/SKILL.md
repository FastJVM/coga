---
name: marketing/plan
description: Approved V1 campaign — one argument, a working first task, PostHog, then Show HN.
---

# Coga V1 marketing plan

**Owner decision, 2026-09-21.** Publish the argument, learn from the reaction,
then launch the working product on Show HN. The approved message and proof
limits live in [positioning](../positioning/SKILL.md). The earlier catalogue
review, separate story/pitch/narrative pipeline and three-essay campaign are
superseded. Historical material is indexed in [the catalogue](../map/SKILL.md).

## Before launch

- [README](../../../../coga/tasks/marketing/readme-top.md): explain the instrument
  through concrete behavior and provide a clear next action.
- [Installer and one-task onboarding](../../../../coga/tasks/marketing/fix-installer/):
  a clean installation reaches one useful completed task with human direction
  and review. Prove the actual installed-package path.
- [PostHog](../../../../coga/tasks/marketing/add-telemetry.md): adoption/activity
  measurement is implemented (PR #880, merged 2026-09-22). The owner explicitly
  rejected replacing it with zero-telemetry measurement. The
  [weekly snapshot contract](../../coga/telemetry/SKILL.md) owns the implemented
  scope. The owner deferred the live clean-wheel proof in
  [operator verification](../../coga/telemetry/operations/SKILL.md) at review.
  It remains the one open PostHog launch gate, tracked in
  [its own ticket](../../../../coga/tasks/marketing/verify-posthog-telemetry-with-the-live-clean-wheel.md).
  Campaign simplification does not waive that gate.

**Final V1 release (owner decision, 2026-10-02).** Publish `1.0.0` as the
last V1 product-delivery step, after the remaining V1 changes and readiness
checks and before the public product launch. The published `0.4.0` is an
interim release. The [final release ticket](../../../../coga/tasks/marketing/publish-coga-1-0-as-the-final-v1-step.md)
owns candidate preparation, publication and verification under the
[release runbook](../../coga/releasing/SKILL.md).

## Publication sequence

1. [One idea piece](../../../../coga/tasks/marketing/idea-piece.md) publishes the
   argument, supported by megalaunch and one correction changing later work.
   It is not a separate full product launch. The owner selects the venue,
   edits/approves the piece and publishes it.
2. Let the argument circulate, collect objections and first-run feedback,
   and correct the README/onboarding where the response exposes friction.
3. Launch the working product on Show HN, targeting roughly one week after
   the piece, conditional on readiness and owner availability. The submission
   stands alone for readers who never saw the argument.

[Launch execution](../../../../coga/tasks/marketing/build-the-launch-plan.md) owns
readiness evidence, publication coordination, the Show HN package, response
triage and recorded outcomes. [Distribution](../distribution/SKILL.md) owns
channel and measurement policy. Publication remains an owner action.

## Scope

The remaining marketing work is launch execution, the idea piece, the README,
the `fix-installer/` ticket group, PostHog live-wheel verification, the final
V1 release and first-user targeting. First-user targeting is two draft
tickets the owner agreed on 2026-09-29: the
[first-user ICP audit](../../../../coga/tasks/marketing/1st-users/ticket.md)
records a `marketing/first-users` context before the idea piece is
published, so the piece and Show HN can target it, and
[recruiting first users](../../../../coga/tasks/marketing/recruit-first-users.md)
follows it. Neither gates Show HN. There is no separate audience/story/pitch
pipeline, three-essay commitment, Discord/community prerequisite, domain
purchase or additional channel campaign for V1. The writing ticket settles
editorial details directly with the owner. The old numeric scorecard,
day-14 gate and token/time experiment are not revived.

Preserved audit evidence and earlier ideas are references, not launch gates.
Product fixes outside the chosen first-run path retain their own scope.
