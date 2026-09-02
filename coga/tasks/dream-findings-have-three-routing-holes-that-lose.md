---
slug: dream-findings-have-three-routing-holes-that-lose
title: Dream findings have three routing holes that lose work every run
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

Dream's own body opens with "Every Dream finding ends in a durable artifact — a PR, a
draft ticket, or a recorded marker — never only in this task's blackboard." Three
routing holes break that promise, and the 2026-W36 run hit all three.

**Hole 1 — Phase 1 `human-needed` validator issues have no route at all.** Phase 6 says
"Every **Phase 2 and Phase 3** finding gets a durable home". Phase 1's buckets are
excluded by construction: nothing routes a `human-needed` issue anywhere but the
`## Dream Skill: validate-drift` blackboard section, which the recurring scanner deletes
at the next firing. `coga/log.md` shows W33 23, W34 23, W35 29, W36 22 — four runs, no
downward trend, no ticket, no marker.

**Hole 2 — `extract` findings whose source ticket is not Retro-eligible fall through.**
Phase 6 routes `extract` as "already handled by Phase 4". In 2026-W36 all 18 `extract`
findings named tickets that carry a real `## Dev` checkout (retirement debt) or are
canceled, so Phase 4 could not consume a single one. Nothing in the body says what
happens then.

**Hole 3 — nothing stops a shard refiling a gap that is already ticketed.** The
`knowledge-scan` skill never tells a shard to check for an existing owner before
classifying a `gap`, so runs refile work previous runs already filed.

Deliverable: a routing rule for each. These are related enough to design together and
small enough to land together, but splitting into siblings is a legitimate outcome of
the design step.

## Context

Citations name symbols and files, not line numbers.

**Hole 1 evidence.** `human-needed` is defined in
`coga/.agent-skills/bootstrap/dream/tasks/validate-drift/SKILL.md` as a classification;
neither that skill nor `coga/recurring/dream/ticket.md` routes such an issue past the
blackboard. Two of the reported items are provably the *same* ones every run, not fresh
churn: `coga/tasks/secrets-instructions-correction.md` is `stuck-in-progress` at ~469h
idle with its last log entry 2026-08-13 (before W34), and
`coga/tasks/v2/document-contexts-as-prompt-payload-not-tags-princ.md` at ~1030h with its
last entry 2026-07-21. The `unfrozen-workflow` (8 tickets in W36) and
`unknown-assignee: 'nicktoper'` (5 v2 tickets) classes are systematic, not per-ticket
accidents.

Design constraint worth stating: **one draft ticket per systematic class, not per issue** —
22 issues must not become 22 tickets. The alternative shape is a persistent hygiene ledger
outside the period blackboard so each run reports a delta rather than a total. Choosing
between those is the judgment call.

**Hole 2 evidence.** The Dream 2026-W36 blackboard records the full analysis, and the
18 orphaned findings are carried in the sibling ticket
`dream-2026-w36-extract-backlog-18-findings-phase-4` so they survive that blackboard's
deletion. The structural question this ticket owns is what Dream should *do* in that
case — extend Phase 4 eligibility, let Phase 6 open knowledge PRs itself, or file a
backlog ticket as W36 did by hand.

Note the interaction with retirement: a done ticket with a `## Dev` checkout is
deliberately left on disk so the human-typed `coga retire <slug>` stays valid, and
21 such tickets are currently outstanding. As long as that backlog exists, `extract`
findings will keep pointing at ineligible tickets — so this is a standing condition, not
a one-off.

**Hole 3 evidence.** Four owned tickets show the cycle:

- `coga/tasks/v2/document-design-pivot-in-blackboard-convention.md` ("Surfaced by Dream
  W22 Phase 2 knowledge scan (G8)") and
  `coga/tasks/give-a-ticket-s-superseded-design-one-documented-h.md` ("Found by Dream
  2026-08-24, Phase 2 knowledge scan (shard-12), classified `gap`") are two drafts filed
  by two different Dream runs for the **identical** gap — where a pivoted ticket's
  superseded design lives. The later one can only say "check it for premise before
  starting, and fold it in or cancel it."
- `coga/tasks/ticket-specs-should-cite-symbols-not-line-numbers.md` is a third
  Dream-filed draft.
- `coga/tasks/the-ticket-interview-never-asks-what-done-means.md` records the sharpest
  case: "Dream 2026-08-24, Phase 2 knowledge scan (shard-12), classified this a `gap` and
  filed the present ticket, unaware of all three" prior efforts.

All four are still `draft`. The fix has two halves: the scan skill should require a shard
to search existing ticket titles and bodies for an owner before emitting a `gap`, and
report "already ticketed as `<slug>`" instead of a new finding; and Phase 6 should
reconcile against open drafts, not only against contexts and skills.

A fourth, related observation this ticket may absorb or spin out: Dream `gap` tickets get
filed at the top level, but several have drifted into `coga/tasks/v2/` and decayed there.
`coga/tasks/v2/README.md` defines v2 as the parking area for work not on the execution
path; nothing says a freshly-filed Dream gap must not be parked there.

Files this touches: `coga/recurring/dream/ticket.md` and its packaged twin
`src/coga/resources/templates/coga/recurring/dream/ticket.md` (an **enforced**
byte-identical pair), plus the packaged
`.../bootstrap/skills/bootstrap/dream/scan/knowledge-scan/SKILL.md` and
`.../bootstrap/dream/tasks/validate-drift/SKILL.md`. Note `coga/.agent-skills/` is a
generated gitignored symlink view — edit the packaged files, not the view.

Filed by Dream 2026-W36, Phase 2 knowledge scan (shards `ks-03`, `ks-10`, `ks-11`),
classified `gap`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
