---
name: marketing/distribution
description: V1 publication and measurement policy, plus dated account observations.
---

# Coga distribution

**Owner decision, 2026-09-21:** the [V1 plan](../plan/SKILL.md) selects
publication of one argument followed by Show HN as the product launch.
The idea piece's venue remains an owner editorial choice; no additional
channel sequence is implied. The launch ticket records actual dates and the
owner's availability to answer product questions.

Before Show HN, verify the current [submission guidance](https://news.ycombinator.com/showhn.html)
and the working product/install links. The submission must stand alone and
let people try the product. Publish the argument as ordinary reading material,
not as a Show HN. The owner approves and performs publication/personal-account
actions. Share links without soliciting votes or comments to boost ranking.

The [previous distribution runbook](../../../archive/launch-programs/three-essay-distribution.md)
is historical; its channel order, YC timing and thresholds are not requirements.

## Recorded surfaces and outstanding facts

Extracted from the audit on 2026-09-09. Public observations were recorded on
**2026-09-02/03**; no live account or website was rechecked for the September
10 inventory. Recheck applicable facts, rules and links when selecting a
channel and again before submission. Sources:
[audit evidence](../../../archive/launch-programs/phase-0-audit/step-1-findings.md),
[audit history](../../../archive/launch-programs/phase-0-audit/audit-history.md), and
[the earlier campaign research](../../../archive/launch-programs/campaign-ticket-briefs.md).

| Surface | Recorded observation | Input if the new plan uses it |
|---|---|---|
| [Blog](https://deviantabstraction.com) | WordPress/Jetpack; email signup present; most recent post then was 2026-06-02. No Coga mention found in that audit. | Subscriber count, trailing-30-day views, working subscribe flow and a current reader-path check. |
| [HN account](https://hacker-news.firebaseio.com/v0/user/top256.json) | `top256`, joined 2016; karma 213 as confirmed September 3. Audited history: 26 stories, four scores of 30+ points (87, 52, 47, 32), six Show HN submissions at 1–6 points. | Founder availability, current submission rules, format and supported title. Scores are not observed front-page placement or proof that a title caused a result. |
| [Lobsters account](https://lobste.rs/u/ntoper) | `ntoper`, created 2025-06-05; karma 55. A self-authored submission scored 26 points / 19 comments. | Current community fit, tags, rules and account standing. Previous `vibecoding` / `practices` advice is dated. |
| [Reddit account](https://www.reddit.com/user/Let047/) | Owner reported 7,781 karma, 2,609 contributions, six years and 56 followers; unauthenticated fetches were blocked. | Joined communities and current self-promotion rules. The owner report is not a fresh account check. |
| Bookface / YC | Login-gated; owner standing and feasibility remain unreported. Earlier proposals included a friendly read, Launch YC and YC amplification. | Owner confirms access and decides whether and how to use those surfaces. Prior Bookface-before-HN and second-run timing are archived choices. |
| [fastjvm.com](https://fastjvm.com) | Audit found a JVM research index without a natural Coga link slot; the owner previously chose a one-time announcement. | Reconsider the purpose and placement in the new campaign. |
| Community | Audit found Discussions disabled and no Discord link. | No community setup is required for V1; the earlier proposal is archived. |
| X and personal share asks | Options in the earlier runbook, without an audited account baseline here. | Decide their fit, workload and timing if selected. |

## Measurement and interpretation

The measurement policy belongs to [`coga/principles`](../../coga/principles/SKILL.md)
(§5, "Yours"). The concrete
[payload and sweep contract](../../coga/telemetry/SKILL.md) owns the weekly
PostHog signal, opt-out and limits; [operator procedures](../../../../docs/telemetry.md)
cover queried-row acceptance in shared project 606347. This measures repos with
active sweeps, not installs. Owner ingestion proof remains a release gate.

Launch execution records dated reactions, objections, first-run friction,
and available adoption/activity observations, with their limits. PostHog's
approximate activity is not a productivity result or proof of attribution.
Public stars/downloads and voluntary feedback can supplement it; do not
reinstate the old subscriber/community thresholds or a day-14 follow-up gate.
The marketing token/time experiment remains dropped.

Jetpack referrers plus timestamps, if the owner selects the blog, support
only coarse attribution. Email clients may suppress referrers and individual
subscriptions cannot be assigned a source from that evidence. Private account
counters require owner access. Recheck dated observations before relying on them.
