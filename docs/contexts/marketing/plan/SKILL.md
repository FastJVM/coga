---
name: marketing/plan
description: Approved V1 campaign — one argument, a working first task, PostHog, then Show HN — with its publication and measurement policy.
---

# Coga V1 marketing plan

**Owner decision, 2026-09-21.** Publish the argument, learn from the reaction,
then launch the working product on Show HN. The approved message and proof
limits live in [positioning](../positioning/SKILL.md). The earlier catalogue
review, separate story/pitch/narrative pipeline and three-essay campaign are
superseded. Historical material is indexed in [the catalogue](../map/SKILL.md).

## Before launch

- [Installer and one-task onboarding](../../../../coga/tasks/marketing/fix-installer/):
  a clean installation reaches one useful completed task with human direction
  and review. Prove the actual installed-package path.
- PostHog live clean-wheel proof
  ([ticket](../../../../coga/tasks/marketing/verify-posthog-telemetry-with-the-live-clean-wheel.md)):
  the one open telemetry launch gate. The contract is
  [`coga/telemetry`](../../coga/telemetry/SKILL.md).

**Final V1 release (owner decision, 2026-10-02).** Publish `1.0.0` as the
last V1 product-delivery step, after the remaining V1 changes and readiness
checks and before the public product launch. The [final release ticket](../../../../coga/tasks/marketing/publish-coga-1-0-as-the-final-v1-step.md)
owns candidate preparation, publication and verification under the
[release runbook](../../coga/releasing/SKILL.md).

## Publication sequence

1. [One idea piece](../../../../coga/tasks/marketing/idea-piece.md) publishes the
   argument, supported by the README's thinkpick example.
   It is not a separate full product launch. The owner selects the venue,
   edits/approves the piece and publishes it.
2. Let the argument circulate, collect objections and first-run feedback,
   and correct the README/onboarding where the response exposes friction.
3. Launch the working product on Show HN, targeting roughly one week after
   the piece, conditional on readiness and owner availability. The submission
   stands alone for readers who never saw the argument.

[Launch execution](../../../../coga/tasks/marketing/build-the-launch-plan.md) owns
readiness evidence, publication coordination, the Show HN package, response
triage and recorded outcomes. Publication remains an owner action.

## Distribution and measurement

The idea piece's venue is the owner's editorial choice; no further channel
sequence is implied. Before Show HN, verify the current
[submission guidance](https://news.ycombinator.com/showhn.html) and the
working product/install links. Publish the argument as ordinary reading,
not as a Show HN. Share links without soliciting votes or comments.

Launch execution records dated reactions, objections, first-run friction
and adoption/activity observations with their limits. The weekly PostHog
signal ([`coga/telemetry`](../../coga/telemetry/SKILL.md)) counts repos with
active sweeps, not installs, and is not a productivity result or proof of
attribution. Stars, downloads and voluntary feedback can supplement it.

## Out of scope for V1

No separate audience/story/pitch pipeline, three-essay campaign,
Discord/community prerequisite, domain purchase or extra channel campaign.
The old numeric scorecard, day-14 gate and token/time experiment are not
revived. First-user targeting (the `marketing/1st-users/` and
`recruit-first-users` tickets) does not gate Show HN. Live ticket state is
`coga status`, not this page.
