> Archived 2026-10-15 from `docs/contexts/marketing/plan/SKILL.md`.
> Historical planning material; not current instructions. Agent reading
> requires an explicit human request.

# Coga V1 marketing plan

**Owner decision, 2026-09-21.** Publish the argument, learn from the reaction,
then launch the working product on Show HN. The message is
[README.md](../../../README.md); claim and proof limits live in
[positioning](positioning.md). The earlier catalogue
review, separate story/pitch/narrative pipeline and three-essay campaign are
superseded. Historical material is indexed in [the catalogue](map.md).

## Before launch

- Installer and one-task onboarding: a clean installation reaches one useful
  completed task with human direction and review. Prove the actual
  installed-package path. Contracts: [`coga/install`](../../contexts/coga/install/SKILL.md)
  and [`coga/first-task`](../../contexts/coga/first-task/SKILL.md); current work:
  [installer tickets](../../../coga/tasks/marketing/fix-installer).
- PostHog live clean-wheel proof: the one open telemetry launch gate. The
  contract is [`coga/telemetry`](../../contexts/coga/telemetry/SKILL.md) and the proof
  runbook its [operations](../../contexts/coga/telemetry/operations/SKILL.md); current
  work: [ticket](../../../coga/tasks/marketing/verify-posthog-telemetry-with-the-live-clean-wheel.md).

**Final V1 release (owner decision, 2026-10-02).** Publish `1.0.0` as the
last V1 product-delivery step, after the remaining V1 changes and readiness
checks and before the public product launch. Candidate preparation,
publication and verification follow the
[release runbook](../../contexts/coga/releasing/SKILL.md); current work: the
[final release ticket](../../../coga/tasks/marketing/publish-coga-1-0-as-the-final-v1-step.md).

## Publication sequence

1. One idea piece publishes the argument, supported by the README's thinkpick
   example (current work: [idea piece](../../../coga/tasks/marketing/idea-piece.md)).
   It is not a separate full product launch. The owner selects the venue,
   edits/approves the piece and publishes it.
2. Let the argument circulate, collect objections and first-run feedback,
   and correct the README/onboarding where the response exposes friction.
3. Launch the working product on Show HN, targeting roughly one week after
   the piece, conditional on readiness and owner availability. The submission
   stands alone for readers who never saw the argument.

Launch execution covers readiness evidence, publication coordination, the
Show HN package, response triage and recorded outcomes, under this plan and
the owner; publication remains an owner action. Current work:
[launch execution](../../../coga/tasks/marketing/build-the-launch-plan.md).

## Distribution and measurement

The idea piece's venue is the owner's editorial choice; no further channel
sequence is implied. Before Show HN, verify the current
[submission guidance](https://news.ycombinator.com/showhn.html) and the
working product/install links. Publish the argument as ordinary reading,
not as a Show HN. Share links without soliciting votes or comments.

Launch execution records dated reactions, objections, first-run friction
and adoption/activity observations with their limits. The weekly PostHog
signal ([`coga/telemetry`](../../contexts/coga/telemetry/SKILL.md)) counts repos with
active sweeps, not installs, and is not a productivity result or proof of
attribution. Stars, downloads and voluntary feedback can supplement it.

## Out of scope for V1

No separate audience/story/pitch pipeline, three-essay campaign,
Discord/community prerequisite, domain purchase or extra channel campaign.
The old numeric scorecard, day-14 gate and token/time experiment are not
revived. First-user targeting (the `marketing/1st-users/` and
`recruit-first-users` tickets) does not gate Show HN. Live ticket state is
`coga status`, not this page.
