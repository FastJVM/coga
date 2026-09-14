---
title: Dream findings have three routing holes that lose work every run
status: in_progress
owner: nicktoper
agent: claude
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
step: 3 (open-pr)
launch_generation: 10620454-1f46-48a9-ae65-c1e81f55a86b
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

## Dev

branch: dream-routing-holes
worktree: /home/n/Code/claude/coga-dream-routing-holes

## Plan (implement step, 2026-09-12)

Markdown-only change; no recipe code. The deterministic recipe already emits
`kind` per issue, which is all the new routing needs. Files: the Dream template
twin pair, `knowledge-scan/SKILL.md`, `validate-drift/SKILL.md`, and the
template-prose test `tests/test_dream_worker_templates.py`.

**Hole 1 — chosen: one draft ticket per systematic class, with an owner check.**
Rejected the persistent hygiene ledger: recurring cross-run state does live in
the parent template blackboard (`coga/period-task`), but Dream's own template
blackboard opts out ("Dream keeps no durable state here"), and a ledger is
exactly the hidden-state shape CLAUDE.md warns against. Rule: Phase 6 groups
`human-needed` issues by validator `kind`; machine-local kinds
(`missing-user`, `unset-secret-env`, `slack-*`, `github-*`) are summary-only;
every repo-state kind gets one `brief-for-human` draft, unless an open ticket
already carries the searchable tag `validate-drift: <kind>` — then the run
summary reports the delta against that owner instead of refiling. Membership is
not copied run to run: `coga validate --json` is the live member list.
`brief-for-human` ships in the same packaged tier as the Dream template.

**Hole 2 — chosen: route `extract` by the source ticket's Retro standing.**
Shards now record `source:` on every `extract` (`done`, `done+checkout`,
`canceled`). `done` → Phase 4 as today. `done+checkout` → deferred: no PR, no
carrier ticket — the source ticket on disk is the durable artifact and
`coga retire <slug>` runs Retro over it; the run summary lists these under
retirement debt with area + one line so the human can order retirements by
knowledge value. `canceled` → Phase 6 opens a `pr-required` knowledge PR
(same shape as `stale`), citing the source and leaving it on disk; Retro
refuses non-done tickets so nothing else would ever consume it. Rejected
extending Phase 4 eligibility (the checkout gate exists so the human-typed
`coga retire` stays valid) and the hand-filed backlog ticket (a second copy that
decays; W36's carrier was the right emergency move, not the rule).

**Hole 3 — chosen: both halves.** Shard: before emitting `gap`, grep
`coga/tasks/` (titles and bodies) for the target path and the finding's
distinctive terms; an open ticket covering it becomes `owner: <slug>` on the
finding, and the finding is still written so counts stay honest. Phase 6:
reconcile every `gap` against open tickets again with the full corpus view
(shards see one area), create nothing for an owned gap, and report
"already ticketed as `<slug>`". Dream files every draft at the top level;
parking under `coga/tasks/v2/` is a human decision (absorbs the fourth
observation). Every Dream-filed description names the run and shard and the
target path so later runs can find it by grep.

## Decisions / notes

- `unfrozen-workflow` on a draft "awaiting first launch" reads as a false
  positive class, not a hygiene problem — the class ticket is where the human
  decides that; not changed here (out of scope: `validate.py` emitter).
- Test pin "Every Phase 2 and Phase 3 finding gets a durable home" in
  `tests/test_dream_worker_templates.py` changes with the body.

## Implement handoff (2026-09-12)

Committed on `dream-routing-holes` as `8809d5a9`
"Route every Dream finding class to a durable home", rebased on
`origin/main` (`d10de92b`), working tree clean. No push, no PR.

Files: `coga/recurring/dream/ticket.md` + packaged twin (byte-identical,
`cmp` verified), `.../bootstrap/dream/scan/knowledge-scan/SKILL.md`,
`.../bootstrap/dream/tasks/validate-drift/SKILL.md`,
`tests/test_dream_worker_templates.py` (pinned phrase updated; new
`test_dream_routes_every_finding_class_to_a_durable_home` pins all three
rules plus the filing rules).

Verification: `PYTHONPATH=$PWD/src ../coga/.venv/bin/python -m pytest -q`
in the feature worktree — 2436 passed. `coga validate --json` — 30 issues,
all pre-existing repo state (`missing-user` is the worktree lacking
`coga.local.toml`); nothing structural changed.

Not a code change: no recipe or `validate.py` edit. The recipe already
prints `kind` per issue, which is all Phase 6 needs to group classes.

For the reviewer, the judgment calls worth pushing on:
- Hole 1 picked draft-per-class over a hygiene ledger (reasons in the plan
  above). `brief-for-human` is the workflow; it ships in the same packaged
  tier (`templates/coga/workflows/`) as the Dream template.
- Hole 2 makes retirement debt a *reported* condition, not a filed one: no
  carrier ticket like W36's. If that feels too passive, the alternative is
  Phase 6 opening knowledge PRs for `done+checkout` sources without deleting
  them — rejected here because W36 alone had 18 and Retro's batching and
  isolation machinery would be bypassed.
- Hole 3's owner search is grep-based and judgment-finished (read the hit's
  title and description). No new machinery.
- The fourth observation (gaps decaying in `v2/`) is absorbed as the
  top-level filing rule; nothing spun out.

## Peer review

`codex review --base main` **returned** (2026-09-12) after reviewing the
recorded feature worktree, rebased without conflicts onto freshly fetched
`origin/main` (`965ca368`). It found three P2 issues: canceled-source PRs
need deduplication across runs; hygiene-class routing must honor recorded
decisions after the owner closes; and config-only `unresolvable-step-assignee`
failures need the machine-local route. All are accepted for correction.

Independent review also found that a `done` ticket alone cannot suppress a
still-unfilled gap (the autofix follow-up is the concrete counterexample).
Require current corpus/PR evidence or an explicit extraction route instead.
Retirement remains the consumer for checkout-bearing sources; these corrections
do not change Retro eligibility or require a design restart.

Applied all three returned findings plus the independent completed-ticket
finding in `7f965367` (`peer-review: preserve Dream routing decisions across
runs`). These corrections supersede the simpler lookup rules in the implement
plan:

- Proposal routes inspect existing open tickets and all open PRs, including
  earlier Phase 6 proposals. Ownership must cover the same fact and target;
  overlapping paths alone do not count. An overlapping PR that lacks the
  finding gets a scoped, deduplicated draft carrying the evidence and PR link.
- Hygiene decisions keep the class tag, rationale, and scope in a context
  before their owner closes. Later runs apply the decision only to matching
  issues and route uncovered members normally. Untagged open owners are also
  recognized by title/description.
- Config-only `unresolvable-step-assignee` failures use summary-only reporting;
  frozen-role/shared-workflow corrections retain the hygiene route.
- `done` is never itself an open gap owner. Check current corpus/PR evidence,
  route actual unextracted knowledge as `extract`, or preserve an unfilled gap.
  Top-level create titles explicitly exclude `/` so embedded paths cannot
  accidentally nest the draft.

The native review returned before any fixes were applied; no second native
review was launched. Re-read the corrected rules against those findings and
the Retro contract. No unresolved review finding or design blocker remains.

Final freshness: after committing the fixes, ran `git fetch origin main` and
`git rebase FETCH_HEAD` in the feature worktree again; already current with
`965ca368`. Branch `dream-routing-holes` is clean with two commits ahead of
`main`: `e9d42234` and `7f965367`. The recorded worktree is unchanged.

Verification:

- The rebased pre-fix branch passed all 2436 tests in the native review and
  in a separate explicit-PYTHONPATH run.
- `PYTHONPATH=/home/n/Code/claude/coga-dream-routing-holes/src /home/n/Code/claude/coga/.venv/bin/python -m pytest -q -o cache_dir=/tmp/dream-routing-pytest-cache tests/test_dream_worker_templates.py tests/test_packaging.py`
  — 22 passed after the fixes.
- `PYTHONPATH=/home/n/Code/claude/coga-dream-routing-holes/src /home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --task dream-findings-have-three-routing-holes-that-lose --json`
  — one valid task, no task issues; only the existing missing local-user warning.
- `git diff --check main...HEAD` and
  `cmp coga/recurring/dream/ticket.md src/coga/resources/templates/coga/recurring/dream/ticket.md`
  — clean; twins remain byte-identical after the rebase.
- `PYTHONPATH=/home/n/Code/claude/coga-dream-routing-holes/src /home/n/Code/claude/coga/.venv/bin/python -m pytest -q -o cache_dir=/tmp/dream-routing-pytest-cache`
  — final run on `7f965367`: 2436 passed in 181.19s, no warnings.

Ready for the mechanical open-pr step. No push or PR was made in peer review.

## PR

Dream left validator decisions in a disposable run blackboard, dropped
extractions that Retro could not consume, and filed gaps that already had an
owner. Give each finding an explicit route and check existing ownership before
creating more work.

- Group repo-state validator issues into one human-decision draft per class;
  reuse open owners and scoped context decisions, and report machine-local
  configuration issues separately.
- Route extracts to Retro, reported retirement debt, or canceled-source
  knowledge proposals. Reuse existing tickets/PRs and preserve findings that
  overlap other proposals in scoped drafts.
- Search the ticket corpus during both gap classification and disposition;
  require evidence before treating a completed ticket as coverage, and file
  new drafts at the top level with searchable provenance.

Keep the live and packaged Dream templates in sync and update the bundled
knowledge-scan and validate-drift guidance. No core recipe changes.

Test plan: `PYTHONPATH=/home/n/Code/claude/coga-dream-routing-holes/src /home/n/Code/claude/coga/.venv/bin/python -m pytest -q -o cache_dir=/tmp/dream-routing-pytest-cache` — 2436 passed.
