---
title: Build the launch plan
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

Build a fresh marketing campaign from the reviewed source catalogue, chosen
story/examples and accepted pitch. The owner requested this reset on
2026-09-10. Previous campaigns are inspiration; no three-post sequence,
strategic fork, channel order or scorecard is inherited.

Use `marketing/plan/collect-public-examples-for-the-launch` for the story
decision and `marketing/plan/write-the-pitch-and-narrative` for the copy.
This ticket owns the resulting campaign choices and execution handoff at its
existing human review step.

## Context

### Inputs and owner decision

Read `coga/contexts/marketing/map/SKILL.md` and the preparation sequence in
`coga/contexts/marketing/plan/SKILL.md`. Plan and distribution are editing
targets; read their files rather than attaching them. Finalize the campaign
after the story and pitch decisions exist; use this gate to resolve their
implications instead of independently commissioning the same work.

The [previous campaign briefs](../../contexts/marketing/launch-history/campaign-ticket-briefs.md)
preserve this ticket's earlier research and proposal. Earlier agent output
on the blackboard is historical. Evaluate it alongside other options; its
“settled” sections do not constrain the new decision.

Produce a concrete campaign with:

- the intended reader, desired action and success objective from the
  reviewed story, plus the accepted message and source examples;
- the selected deliverables and formats, with a reason for each, an owner
  and an observable completion condition;
- the selected channels, order, timing and owner availability, with current
  account/rule checks for the chosen surfaces;
- the product, install, documentation or community prerequisites actually
  needed for that reader path, linked to their existing tickets;
- an audience measurement plan with defined baselines, checkpoints, success
  criteria, evidence limits and responses to a miss;
- an explicit keep/change/defer/drop disposition for the earlier essays,
  README revision, community and domain proposals, channel ideas and other
  inventoried material that was considered.

The prior three essays can be retained, combined, rewritten or dropped.
A product announcement, demonstration or another format can also be chosen.
Do not assume the whole cleanup queue or a new community home is necessary
before deciding what the campaign asks a reader to do.

### Durable output

After the owner decides, record the selected campaign in
`coga/contexts/marketing/plan/SKILL.md` and the selected distribution and
measurement policy in `coga/contexts/marketing/distribution/SKILL.md`.
Link the accepted message in positioning. Rewrite or author the selected
execution tickets with workflows and review gates before they are activated.

Create an audience-follow-up ticket if the selected measurement plan needs
one. Its name and checkpoints should fit the new campaign; the earlier
`marketing/phase-1-retro` name and day-14 gate are not requirements.

### Boundaries

Public observations in the source library retain their dates; verify the
facts needed for the selected plan. Use public support for observed claims
and identify authored illustrations. Private-repo narrative quotations,
unsupported productivity claims and the dropped token/time experiment
remain excluded. User instrumentation is not authorized by this planning
work or by the empty telemetry draft.

Writing full assets, fixing the product and publishing are later work.
Preserve the current frozen workflow and human step; authoring this revised
brief does not advance, cancel or launch any ticket.

<!-- coga:blackboard -->

## Fresh-start handoff — 2026-09-10

The owner reset campaign planning. Wait for the reviewed catalogue, story
and pitch decisions before choosing the new campaign. No format, post count,
channel order or scorecard has been selected in this revision. The existing
human step remains in place.

## Earlier campaign work — historical

The following records the previous proposal and its review, before the
September 10 reset. It preserves provenance, not current instructions.

### 2026-09-04 — agent-produces

- Owner approved a three-post plan: decluttering first, with ownership/trust
  folded into that post; human amplification second; productivity-as-mechanism
  third.
- Required sequencing gate is not yet satisfied. PR #754
  (`write-post-skill`) remains open and unmerged; the current `main` copy of
  `marketing/plan` still contains the procedure that PR removes. Do not edit
  the overlapping context or advance this step until #754 lands (or the owner
  explicitly chooses a different integration path).

#### Gate resolved

- Owner reported #754 merged; `main` was synced to `origin/main` at
  `61bf9af3`, with the local launch commit rebased and working changes
  preserved. The live plan is now thinned and `marketing/write-post` owns the
  procedure as intended.
- Draft direction: three posts, all retaining independence/ownership as the
  causal spine. Post 1 makes async megalaunch an example inside the
  decluttering claim and folds ownership in as the trust answer. Post 2 makes
  the correction loop an offensive human-amplification claim. Post 3 keeps
  documentation-as-cache as the mechanism form of productivity.
- The only publishable narrative evidence is Coga working on Coga. The plan
  will treat its public reproducibility as the strength and concede, in one
  sentence, that private-repo use cannot serve as evidence of generality.

### Draft delivered

- Rewrote `marketing/plan` as a genuinely operational three-phase plan. It
  now fixes each post's one claim, opponent/title brief, exclusions, bridge,
  content beats, cumulative preconditions, exact Day-0 / HN / Lobsters /
  conditional-Reddit order, owners, phase gates, and the post-1 retro.
- Fixed the phase-1 scorecard at the audit's grounded proposal: HN observed
  front page + 30 points; Lobsters 15 points / 5 comments; +25 subscribers;
  community threshold adapted natively for Discord vs Discussions; and one
  unprompted vocabulary use. Each miss now routes to a specific retry, funnel
  repair, message repair, channel omission, or owner hold instead of a vague
  "review performance" step.
- **Superseded 2026-09-09:** the former one-off token-receipts task and paired-run
  gate were dropped by the owner. Public examples now support the mechanism.
  `marketing/phase-1-retro` is a separate planned task for the 24-hour,
  72-hour, and day-14 checkpoints; this avoids using a writing ticket as a
  hidden timer.
- Archived the superseded program and proof apparatus in the unattached
  `marketing/launch-history` context. It stays durable and is committed by
  Coga state sync but adds zero composed tokens to live tickets. The proof post
  remains an owner-reopenable option, not phase 4.
- Updated all three post-ticket bodies and `marketing/readme-top` to match the
  new plan. `post-async-megalaunch` and `post-you-own-it` are retained and
  rescoped; `post-doc-as-cache` is retained and sharpened. Their old
  frontmatter titles/slugs remain stable bookkeeping, not editorial titles.
- Updated `marketing/write-post` only where the new plan made its pointers
  stale: canonical-URL/referrer attribution, the archive location, and the
  fact that repo-visible receipt notes are working support rather than secret
  material.

### Human-review weak spots

- Bookface standing and the Reddit joined-subreddit list remain owner-only and
  unknown. The draft makes Bookface a hard pre-HN decision and makes Reddit
  optional rather than allowing either unknown to disappear.
- The +25 subscriber bar was the audit's softest proposed number and still has
  no baseline. The owner should accept or replace it before post 1; the plan
  prevents publishing until the baseline exists.
- Day 0 → HN on day +2/+3 → Lobsters the next day is an operational judgment,
  not a performance inference; the HN history showed no useful day/hour
  effect. Its purpose is Bookface feedback and one founder-attended thread at a
  time.
- `marketing/phase-1-retro` remains a planned ticket required before post 1.
  The owner dropped the former token-receipts ticket on 2026-09-09.
- The live plan is 25,542 bytes after adding the operation the old context
  lacked. The 2,283-byte history context is no longer composed. If prompt cost
  is judged too high, split the channel/measurement runbook later; do not move
  message truth back into the writing skill.

### Verification

- `git diff --check` — pass.
- `coga validate --json` — 169 ok; 29 existing repo-wide issues; zero issues
  on the touched marketing tickets or the three changed context/skill refs.
- Confirmed there is no packaged marketing-context twin under
  `src/coga/resources/templates/coga/contexts/`; live `coga/` copies are the
  only required edit.

### 2026-09-09 — owner input: YC channels

- Coga is YC-backed, so two product-launch channels exist that the essay
  channels do not cover: a **Launch YC** post and **YC amplifying** it from its
  own accounts. Both are owner actions. Recorded in `marketing/distribution`
  under `## YC channels and personal asks`, with the friends share ask.
- **Owner placed them after phase 1, with the second run.** Post 1 stays a pure
  essay opening. Open for this ticket: where exactly they sit against post 2's
  window, given post 2 does not publish until day 14 plus a recorded proceed
  decision, and the Day-0-to-+3 founder window belongs to the HN thread.
- Genre tension to reconcile while planning: `marketing/plan`'s play states the
  launch is *not* a product announcement, and a Launch YC post is one. Both
  contexts now say the YC channels sit outside the play rather than replacing
  it; confirm that is the framing the owner wants.
- Note: this ticket carries `contexts: []`, so neither `marketing/plan` nor
  `marketing/distribution` is composed into its launches — hence this summary
  on the blackboard. Attach them if a later step needs the full policy.
