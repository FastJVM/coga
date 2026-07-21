---
slug: clean-up-workflows-and-make-sure-they-re-in-bootst
title: clean up workflows and make sure they're in bootstrap
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts:
- coga/codebase
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 2 (peer-review)
---

## Description

Audit every workflow that ships with Coga, delete the dead/one-off ones, and
make sure every keeper lives in the **correct** packaged tree. This is a
cleanup + correct-placement task, **not** a packaging-mechanism rewrite.

Explicitly out of scope: do **not** try to consolidate the two packaged
workflow locations into one. They are intentionally distinct lifecycles (see
Context) — collapsing them would lose a real property. The goal is hygiene:
remove cruft, triage the three unclassified one-offs, and ensure each surviving
workflow sits in whichever of the two trees matches its intended lifecycle,
with the live `coga/` copy and packaged copy in sync.

Done looks like: dead workflows deleted; the three one-offs each resolved
(keep / promote to a packaged tree / delete); every keeper in the right tree;
live and packaged copies in sync; `coga validate --json` and `python -m pytest`
clean; PR opened for review.

## Context

**The two packaged trees are intentional — keep both.** Packaged workflows live
in two locations that serve *different lifecycles*, verified in code
(`copy_fresh_templates`, `src/coga/commands/update.py:267`, copies the template
tree with `skip_top={"bootstrap"}`):

- `src/coga/resources/templates/coga/workflows/` — the **seed template**.
  Copied into a new repo's `coga/workflows/` at init, so the repo then *owns
  and can edit* these (e.g. autonomy levels, sweeps, onboarding, direct). They
  freeze at seed time and do not auto-upgrade. Currently holds:
  `autoclose-merged, autonomy, blocker-reminders, branch-sweep, browser,
  build/onboarding, direct, skill-update, _template.md`.
- `src/coga/resources/templates/coga/bootstrap/workflows/` — **bundled
  batteries**. Never copied into a repo; resolved at runtime and therefore
  *upgrade with the installed coga version*. Currently holds:
  `code, digest, docs, dream`.

So placement is a real decision per workflow: repo-owned/customizable →
seed tree; upgrades-with-coga → bootstrap tree. `resolve_workflow_path`
(`src/coga/paths.py:24`) is local-first: a repo's own `coga/workflows/<ref>.md`
overrides the packaged `bootstrap/workflows/<ref>.md` fallback.

**Investigate these three** (decide keep / promote-to-correct-tree / delete per
workflow — not assumed) — they exist in the live repo but in neither packaged
location, so they look like local one-offs:

- `coga/workflows/build/dry-run.md`
- `coga/workflows/coga/cutover.md`
- `coga/workflows/test/relaunch-chain.md`

**Keep the two copies in sync.** Per `CLAUDE.md`, any shipped-workflow change
must touch both the live repo copy under `coga/workflows/` and the packaged
copy under `src/coga/resources/templates/coga/…`. Note the live
`coga/workflows/` currently carries local copies of the batteries (code,
digest, docs, dream, plus coga/, test/) via the local-first override — factor
that into the sync plan. Watch the hatchling packaging gotcha the
`coga/codebase` context calls out (force-include of `_template` dirs).

**Files likely in scope:** the workflow markdown trees in both live and
packaged locations, `src/coga/validate.py`, and `pyproject.toml`/hatchling
include rules if a tree's file set changes. The resolver (`paths.py`) and
init-seed logic should **not** need behavioral changes — if you find yourself
rewriting them, the scope has crept past cleanup; stop and reconsider. Run
`coga validate --json` and `python -m pytest` after changes.

**Autonomy note:** triaged fully-automated, but the chosen `code/with-review`
workflow ends with an owner review gate — the human still approves the PR
before merge. That gate is intentional and fine; treat it as the commit point.

<!-- coga:blackboard -->

## Dev

branch: workflow-cleanup
worktree: ../coga-workflow-cleanup

## Audit findings (implement step)

Compared all three trees. Full inventory:

- **Seed template** (`src/.../coga/workflows/`): autoclose-merged, autonomy,
  blocker-reminders, branch-sweep, browser, build/onboarding, direct,
  skill-update, _template. The live `coga/workflows/` copies of all of these
  are legitimate init-seeded copies and **all diff clean** (in sync). Keep.
- **Bootstrap batteries** (`src/.../bootstrap/workflows/`): code (×3), digest,
  docs (×2), dream (×2). Resolved at runtime, never seeded into a repo
  (`copy_fresh_templates` uses `skip_top={"bootstrap"}`).

### The three unclassified one-offs → all DELETE

1. `coga/workflows/coga/cutover.md` — **DELETE (dead).** One-time relay→coga
   cutover for rename PR #454, which landed; migration script removed (#488);
   the `coga-cli-cutover` / `coga-rename-follow-ups` tickets are recorded as
   direct-deleted in the Dream ticket. `docs/migrating-to-coga.md` remains as
   the standing reference. Never useful again.
2. `coga/workflows/build/dry-run.md` — **DELETE (spent design probe).** It
   role-plays `coga build` "not yet built" to feed the
   `marketing/coga-build-onboarding-flow` design. `coga build` now ships
   (alias `build = "launch coga-build"` in coga.toml + `cli.py`; onboarding
   ticket `resources/templates/coga/tasks/coga-build.md`). The design
   deliverable no longer exists. Purpose served.
3. `coga/workflows/test/relaunch-chain.md` — **DELETE (soft call — flag at
   review gate).** Synthetic, human-gated probe of coga's launch
   auto-relaunch chain; self-describes as "Not a real delivery workflow; it
   exists to test coga itself." Zero references anywhere; not wired into the
   pytest suite (the `_harness_stop_reason` behavior it exercises is unit-
   tested in `launch.py`). Doesn't belong in seed (user repos don't need it)
   or bootstrap (ships to all user repos). As a coga-dev diagnostic it's
   recoverable from git if the chain ever needs re-probing. This is the one
   judgment call; owner can veto at the review gate to keep it local-only.

### Live battery SHADOWS → DELETE the live copies (keep bootstrap)

The live `coga/workflows/` carries local copies of the bootstrap batteries
(`code/`, `digest/`, `docs/`, `dream/`). These **shadow** runtime bootstrap
resolution (`resolve_workflow_path` is local-first), so bootstrap upgrades
never reach this repo for these workflows — defeating the very
"upgrades-with-coga" lifecycle they were moved to bootstrap for. Proof the
shadow isn't maintained: live `digest/post.md` has already **drifted stale**
vs the bootstrap copy (older spool wording). Decision: **delete the live
`code/`, `digest/`, `docs/`, `dream/` dirs** so bootstrap is the single
source. Safe — refs (e.g. `code/with-review`, used by this very ticket)
fall through to bootstrap automatically; no resolver/init change needed.
This is the concrete reading of "make sure they're in bootstrap."
Tradeoff: dogfood launches now read these from the installed package rather
than an editable live file — but for an editable install that source IS
`src/.../bootstrap/workflows/`, so live-edit still works; editing a battery
means editing the bootstrap source + reinstall, the documented model.

### Packaging / pyproject

No change needed. Only `src/coga` is shipped (`packages = ["src/coga"]`);
the live `coga/workflows/` working tree is not packaged. I am not changing
any *packaged* tree's file set, so hatchling include/exclude + `_template`
force-include rules are untouched and `test_packaging.py` is unaffected.

### Net changes

Delete (live-only): `coga/workflows/coga/`, `coga/workflows/build/dry-run.md`
(keep `build/onboarding.md`), `coga/workflows/test/`, and the shadow dirs
`coga/workflows/code/`, `coga/workflows/digest/`, `coga/workflows/docs/`,
`coga/workflows/dream/`. No packaged-tree deletions.

## Rebase reconciliation (important — read before review)

While this branch was in flight, a concurrent task landed overlapping
cleanup on `origin/main`. When I rebased, `origin/main` had **already
deleted the three one-offs** — `coga/cutover.md`, `test/relaunch-chain.md`,
`build/dry-run.md` — reaching the *same triage conclusions* documented
above (independent confirmation the delete calls were right). It had also
re-synced `digest/post.md` to the bootstrap copy (option B: keep the shadow
but freshen it) rather than deleting it.

So the branch was reset onto `origin/main` and the cleanup commit
cherry-picked. The **landed diff is now just the four battery shadows**:
deletes `coga/workflows/{code,docs,dream}/` and `coga/workflows/digest/post.md`
(581 deletions, 8 files). The `digest/post.md` deletion was a modify/delete
conflict — resolved by **deleting** (my rationale) rather than keeping the
freshly-synced shadow, so digest is consistent with code/docs/dream and no
battery shadow remains.

**Result:** live `coga/workflows/` is now byte-for-byte the seed-template
set (verified by diff) — zero battery shadows, zero one-offs. All bootstrap
batteries live only in `bootstrap/workflows/` and resolve at runtime.
`python -m pytest` → 1361 passed, 1 skipped. `coga validate --task` clean
(only the pre-existing gitignored `missing-user` warning).

Review-gate note: the only soft call left in the landed diff is deleting the
just-synced `digest/post.md` shadow instead of keeping it. Owner can veto to
keep digest as a synced local copy; all other shadows are unambiguous.

## Dream Skill: validate-drift

Generated: 2026-07-21T00:06:22+00:00
Command: `coga validate --json --fix`
Task: `clean-up-workflows-and-make-sure-they-re-in-bootst`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-21T00:09:22+00:00
Command: `coga validate --json --fix`
Task: `clean-up-workflows-and-make-sure-they-re-in-bootst`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.
