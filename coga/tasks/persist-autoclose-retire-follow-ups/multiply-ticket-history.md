---
slug: autofix/persist-autoclose-retire-follow-ups-beyond-the-per
title: Persist autoclose retire follow-ups beyond the period task
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 4 (review)
---

## Description

The 2026-09-03 autoclose sweep completed with exit 0 and `problems: 0`, but its
one actionable output — the stranded `coga retire` follow-up — was written to a
file that the next daily run deletes. The debt it names is silently lost.

## What broke

`coga/recurring/autoclose-merged/ticket.md` (the parent template) states in its
blackboard region:

> This blackboard persists across every run of this recurring task. […] The one
> thing a run appends is a `## Autoclose Sweep: retire follow-ups` section, and
> only when it closed a ticket that still records a feature checkout.

That contract is not honoured. The section is appended to the **period task**
blackboard at `coga/tasks/recurring/autoclose-merged/ticket.md`, and `coga
recurring` deletes the period task at the start of the next period.

## Evidence

- This run's section — `Generated: 2026-09-03T18:07:58+00:00`, naming
  `v1/persistent-codex-m-managed-checkout` (worktree
  `/tmp/coga-persistent-codex-m-managed`, branch `codex-m-persistent-managed`) —
  is currently in `coga/tasks/recurring/autoclose-merged/ticket.md:62`.
- The parent template `coga/recurring/autoclose-merged/ticket.md` has no such
  section, and `git log -S "Autoclose Sweep: retire follow-ups" --
  coga/recurring/autoclose-merged/ticket.md` shows no run has ever appended one.
- Deletion is routine, not hypothetical. `coga/log.md` for this very sweep:
  `2026-09-03 11:07 [recurring/autoclose-merged] [system] deleted completed
  prior-period task before 2026-09-03`. `git log --diff-filter=D --
  'coga/tasks/recurring/autoclose-merged/*'` shows three
  `Ticket: recurring/autoclose-merged — deleted` commits already.
- The loss has already happened at least once. `coga/log.md:549` records
  `Autoclose sweep 2026-08-28: closed 3 merged final-step tickets (PRs #27, #28,
  #29); all 3 need a coga retire follow-up — see blackboard.` The blackboard it
  points at no longer exists; nothing in the repo now names those three retires.
- Autoclose only inspects tickets it closes *in that run* (`coga.autoclose`
  scans `active`/`in_progress`), so a missed follow-up is never re-detected. The
  backlog is consistent with this: 14 ticket files still carry a `worktree:`
  line under `## Dev`, e.g. `coga/tasks/v1/1-base-plugin.md:144`,
  `coga/tasks/v1/codex-m-untouchable.md:120`,
  `coga/tasks/v1/telemetry/ram-only-event-sender.md:300`.
- Only a free-text line in `coga/log.md:748` survives this run
  (`Retire follow-up stranded: coga retire v1/persistent-codex-m-managed-checkout`),
  which is a firehose, not an actionable worklist.

Because `autoclose-merged` runs on `0 8 * * *`, the section written today is
scheduled for deletion tomorrow morning.

## Where it lives

- `coga/.agent-skills/coga/autoclose/sweep/SKILL.md:39-40` — says the section is
  "appended to the task blackboard", which the agent reasonably read as the
  period task. This is the ambiguity that produces the wrong write target.
- `coga/recurring/autoclose-merged/ticket.md:50-56` — the persistence promise
  that is currently false.
- `coga/workflows/autoclose-merged/sweep.md` — the step that drives the run.
- `coga/.coga/.venv/.../coga/autoclose.py` — `sweep_merged` computes the closed
  set and parses `branch:`/`worktree:` via `parse_branch_name` /
  `parse_worktree_path`, but does not itself emit the section; the emission is
  agent-side today.

## What a fix has to do

1. Pick one durable home for stranded retire follow-ups and make every document
   name it unambiguously. The parent template blackboard
   (`coga/recurring/autoclose-merged/ticket.md`) is the location the template
   already promises and the one that survives period-task deletion; the
   alternative is a dedicated file such as `coga/recurring/autoclose-merged/
   retires.md`. Do not leave the sole copy in the period task.
2. Update `coga/.agent-skills/coga/autoclose/sweep/SKILL.md` to say the chosen
   path explicitly rather than "the task blackboard", and reconcile the wording
   in `coga/recurring/autoclose-merged/ticket.md` and
   `coga/workflows/autoclose-merged/sweep.md` so the three agree.
3. Make entries idempotent and self-clearing: appending the same slug twice must
   not duplicate it, and an entry must be removable (or auto-dropped) once
   `coga retire <slug>` has disposed of the worktree and branch, so the list
   does not become a permanent wall of noise.
4. Backfill the currently stranded debt: re-derive retire follow-ups for done
   tickets that still carry a `branch:`/`worktree:` under `## Dev` — including
   `v1/persistent-codex-m-managed-checkout` from this run and the three from
   2026-08-28 (PRs #27, #28, #29) — and seed the durable list with them.
5. Add a regression check that a period-boundary deletion of
   `coga/tasks/recurring/autoclose-merged/ticket.md` leaves the follow-up list
   intact.

Scope note: this is only about where the follow-up is *recorded*. Autoclose must
still never dispose of a checkout itself — `coga retire` keeps the worktree and
branch safety proofs.

---

Written by the `coga recurring` autofix loop from the sweep this
ticket's `run-log.md` records. The finding is an agent's
reading of that run, not a verified diagnosis: confirm it against
`run-log.md` before changing anything, and close the ticket
through the workflow's already-satisfied path if the problem was
transient or already fixed.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/multiply/pull/46
branch: coga-retire-followups
worktree: /home/n/Code/coga-retire-followups

## Findings

Confirmed the symptom against `run-log.md`: the 2026-09-03 sweep's
`## Autoclose Sweep: retire follow-ups` section naming
`v1/persistent-codex-m-managed-checkout` landed in the period task, and
`coga/log.md:536` shows period-task deletion is routine.

**The ticket's diagnosis was wrong in one load-bearing place.** It states
"the emission is agent-side today" (`## Where it lives`). It is not:
`coga.autoclose._report_retire_followups` renders the section and appends it
to `blackboard_from_env(cfg.repo_root)` — whatever `COGA_TASK_BLACKBOARD`
names, which for a recurring template is the period task. So this was a
Python bug, not a doc ambiguity. `render_retire_report`'s own docstring said
the target was "a long-lived recurring task's blackboard", which is how it
survived review.

Two more corrections to the ticket:

- `coga/.agent-skills/` is generated and gitignored. The skill it names is a
  symlink into `/home/n/Code/claude/coga`, a *different repository*, so
  item 2 could not be done as written from a multiply branch.
- Item 4's backfill list is mostly discharged debt. Of 14 terminal tickets
  carrying a `## Dev` checkout, **4** are real, not the 2 recorded earlier in
  this step — that count checked branch liveness only. Running `prune` against
  the seeded file drops 10 and keeps 4: `v1/persistent-codex-m-managed-checkout`
  (branch live, worktree pruned), `v1/updater/0-hosting-evidence-probes` (both
  live), plus `add-a-launch-gates-skill-for-ticket-launch-precond` and
  `v1/1b-lifecycle-experiments`, whose branches are gone but whose worktree
  directories still exist — genuinely stranded checkouts `coga retire` should
  dispose of. The 2026-08-28 three (PRs #27/#28/#29) had their branches removed
  already — `branch-sweep` deletes branches for terminal tickets weekly.

## Decisions

Four asked of the human, who chose: fix the skill **upstream** in the coga
repo; use a dedicated `retires.md` rather than the template blackboard; seed
**all 14** per the ticket's literal ask; and implement items 3/5 as a real
script plus tests. On finding the Python bug, the human further chose to fix
`autoclose.py` upstream rather than reword around it.

Seeding all 14 is reconciled with item 3's "no wall of noise" by
self-clearing: `prune` drops the 10 discharged entries on first run, so the
backfill preserves the audit trail the ticket wanted without leaving false
debt behind.

At self-QA the human was asked once more, about `**/retires.md merge=union`:
union merge can resurrect an entry one branch pruned. They chose to keep
union — the resurrection is self-healing because the sweep runs `prune` daily
and it is idempotent, so a stale line survives at most a day, against real
merge conflicts on a file two branches may both legitimately append to.

## Changes

**multiply** (branch `coga-retire-followups`, 2 commits):

- `coga/recurring/autoclose-merged/retires.md` — durable worklist, sibling of
  the template `ticket.md`, seeded with the 14 entries. Follows the
  `recurring/digest/spool.md` precedent; `coga/.gitattributes` marks it
  `merge=union` for the same reason.
- `scripts/coga-retire-followups.py` — `add` (slug-keyed, cannot duplicate),
  `prune` (drops an entry once worktree *and* branch are gone), `list`.
- `tests/test_coga_retire_followups.py` — 8 tests, including the item-5
  regression: delete the period task, worklist still intact.
- Reconciled `coga/recurring/autoclose-merged/ticket.md` and
  `coga/workflows/autoclose-merged/sweep.md`.

**coga** (`/home/n/Code/claude/coga`, branch
`autoclose-retires-durable-home`, commit `fa3880b1`, **not pushed**):

- `_report_retire_followups` writes slug-keyed entries to the recurring
  template's `retires.md` via the new `durable_retire_list` /
  `parse_retire_list` / `_append_retire_list`. Non-recurring runs keep the
  blackboard/stdout surfaces unchanged.
- Wording reconciled in the sweep SKILL.md (both tracked copies), the shipped
  recurring template, its dogfooded copy, and the stale docstring.
- 8 new tests in `tests/test_autoclose.py`.

Integration checked directly: upstream's `parse_retire_list` reads multiply's
seeded file and round-trips all 14 entries, so the two implementations agree
on the format byte for byte.

## Self-QA

`/code-review` ran as a subagent; `/simplify`'s four cleanup agents all went
idle without ever delivering a result (messages and a write-to-file fallback
both produced nothing), so that pass was done by hand over the same four
angles. Feedback on the tool failure is queued.

**`/code-review` graded its four top findings against the wrong checkout.** It
read `/home/n/Code/coga`, a stale clone on `main`, and concluded no code writes
`retires.md`. The live `coga` is an *editable* install — `_editable_impl_coga.pth`
points at `/home/n/Code/claude/coga/src`, where `durable_retire_list` and
`RETIRE_LIST_FILENAME` are both present — so findings 1–4 do not hold. Likewise
`coga/.agent-skills/coga/autoclose/sweep` symlinks straight to the upstream
`SKILL.md` this branch edits, so there is no second contradictory write target.

Applied:

- **Heading/newline corruption** (both repos). `partition(HEADING + "\n")` was
  guarded by `HEADING in text`, so a file ending exactly at the heading put the
  whole text in `header` and re-appended the heading, silently doubling it.
  Fixed by normalizing a missing trailing newline and guarding on the full
  separator. Failing loudly was the other option and was rejected: a stripped
  trailing newline is a benign editor artifact and must not break the daily
  sweep. Regression test in each repo.
- **Union-merge duplicate slugs** (multiply). `retires.md` is `merge=union`, so
  one slug recorded on two branches arrives as two lines; the script replaced
  only the first match and `list` printed both. Added `collapse_by_slug` on
  read, matching upstream's dict semantics — later line refreshes the checkout,
  first sighting's date survives. Regression test added.
- **Batched branch lookup** (multiply). `prune` spawned one `git rev-parse` per
  entry; now one `git for-each-ref`. Verified identical result on the seeded
  file (10 dropped, 4 kept).
- **Skill described the wrong surfaces** (coga, both tracked copies). It named
  two surfaces keyed on "when run under a task"; the code has three, keyed on
  *recurring* task. Rewritten to name all three and to stop hardcoding
  `autoclose-merged`. Also rewrapped a >130-char line the implement step left
  in the recurring template.

Tried and reverted: hoisting `blackboard_from_env` into the branch that writes
the report. It looks dead on the durable path but the Slack `post` below uses
it for `task_path`; the tests caught the `UnboundLocalError`. Left hoisted with
a comment saying why.

Not applied (noted for the human reviewer): the worklist write is a
non-atomic read-modify-write, where coga's own `_append_blackboard_report` uses
a compare-and-swap; and `prune` resolves a relative `worktree` against the
process CWD. Both are latent — every recorded path is absolute and the script
has a single daily writer.

Reuse angle came back clean for a checkable reason: `coga` is **not importable**
from multiply's environment (`ModuleNotFoundError: No module named
'coga.autoclose'`), so the parallel format implementations are necessary, not
merely deliberate. The byte-identical round-trip check is the right guard, and
it still passes after every change above.

## Tests

- multiply: `python -m pytest` → **112 passed** (110 + 2 new regressions).
- coga: **2211 passed** (2210 + 1 new regression). One pre-existing failure,
  `test_wheel_includes_bootstrap_batteries`, is environmental (that venv has
  no `pip`) and fails identically with my changes stashed.
- Cross-repo: upstream's `parse_retire_list` still round-trips multiply's
  seeded file byte-for-byte, and multiply's parser reads all 14 entries.

At the `pr` step the branch was stale — 12 lifecycle / other-ticket commits had
landed on `origin/main`. Rebased onto `FETCH_HEAD`: clean, no conflicts, no
fixups needed, suite still **112 passed**. PR opened from the rebased branch.

## Follow-ups

- The coga commit is local and unpushed; it needs its own PR in that repo.
  Until it lands, multiply's docs and `sweep.md` describe behavior that only
  exists because the editable install points at this branch. On a released
  coga (0.3.1 has no `durable_retire_list`) the sweep would write to the period
  task again and the workflow's claim would be false. **These two PRs should
  land together**, coga first.
- 11 terminal tickets carry stale `## Dev` worktree lines pointing at
  directories that no longer exist. Not touched here — `prune` clears their
  worklist entries, but the ticket files keep the dead lines.
- The general class of bug is still open: nothing stops another writer from
  sending durable output to a period task blackboard. `durable_retire_list`
  fixes autoclose only. A shared "durable path for this run" seam would fix the
  class, but coga's microkernel rule wants 2+ real consumers before that moves
  into `src/coga/`, and there is one today.
