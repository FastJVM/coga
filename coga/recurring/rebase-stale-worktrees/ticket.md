---
schedule: "0 8 * * 1"
schedule_comment: "Every Monday at 8am — after branch-sweep deletes dead branches, rebase the live stale ones"
title: "Rebase stale worktrees"
# Runs as an agent: a rebase can hit conflicts, and deciding whether a
# textually-clean rebase is still semantically right needs judgment — the
# exact judgment the deterministic `coga open-pr` command refuses to fake.
# Launch on demand with `coga recurring launch rebase-stale-worktrees`
# whenever the open-pr staleness gate fires.
---

## Description

Bring live feature branches back up to date with the control branch so the
`code/open-pr` staleness gate passes on relaunch.

The `coga open-pr` command fails loud when a branch is materially stale relative
to `origin/main` — correct fail-loud behavior, because a stale PR can
reintroduce reverted work, but the remedy (rebase, re-verify, force-push) is
manual per branch. This task is that remedy, run over every live branch at
once. It is the counterpart to `branch-sweep`: branch-sweep deletes branches
whose work already landed; this task rebases branches whose work is still in
flight. Neither touches the other's set.

### Scope — what counts as live

1. Every non-main branch checked out in a worktree (`git worktree list`).
2. Every `branch:` recorded under a non-terminal ticket's `## Dev` section.

Skip everything else. A stale branch with no worktree and no live ticket is
abandoned or already-merged residue — branch-sweep's problem, not this task's.

### Run order

1. **Enumerate** — `git fetch origin main`, then for each live branch check
   `git merge-base --is-ancestor origin/main <branch>`. Collect the stale
   ones; record the up-to-date ones as no-ops.
2. **Rebase** — in the branch's own worktree when it has one, otherwise in a
   temporary worktree, and only from a clean tree: a dirty worktree is
   skipped and reported, never stashed. Then `git rebase origin/main`.
3. **Conflicts** — resolve only trivial mechanical conflicts (both sides
   appended to the same list, whitespace). Anything semantic:
   `git rebase --abort`, leave the worktree exactly as found, and report the
   branch with its conflicting files.
4. **Verify** — a textually clean rebase can still be semantically wrong
   (docs describing behavior main since changed, code building on a reverted
   commit). Re-read the branch's diff against the new base; run
   `python -m pytest` when it touches `src/` or `tests/`. Report — don't
   push — a branch whose content no longer holds.
5. **Push** — `git push --force-with-lease` only for branches that already
   have an upstream; an existing PR updates automatically. Never open a PR
   here — that belongs to each ticket's own `code/open-pr` step, which now
   passes its staleness gate on relaunch.
6. **Summarize** — replace the `## Rebase Run Summary` section in this
   blackboard with one line per branch: `rebased-pushed`, `rebased-local`,
   `up-to-date`, `conflict — human needed`, `skipped-dirty`, or
   `skipped-verify-failed`, plus the `coga launch <slug>` command for any
   ticket whose open-pr step is now unblocked. Replace, don't append — the
   blackboard is composed into every launch and must stay bounded.

### Safety rules

- Never delete a branch or worktree — branch-sweep owns deletion.
- Never touch `main`; never push without `--force-with-lease`.
- Never stash, commit, or reset a dirty worktree; skip and report it.
- A worktree already mid-rebase or mid-merge at the start of the run is
  someone's live session: report it, don't touch it.

<!-- coga:blackboard -->

`coga recurring` keeps the serviced-period high-water mark here as
`last_serviced_period`. Each run replaces the `## Rebase Run Summary`
section below with its results.

last_serviced_period: 2026-W29

## Rebase Run Summary

Run 2026-W29 (base: origin/main @ 1da0a296). All 20 worktree branches were
stale; all worktrees clean, none mid-op, none with an upstream (so no pushes).

- docs-cleanup — rebased-local (all commits dropped as already-applied; branch now empty vs main — branch-sweep candidate)
- megalaunch-usage-probe — rebased-local (same: empty vs main — branch-sweep candidate)
- move-read-views-to-views-module — rebased-local (same: empty vs main — branch-sweep candidate)
- branch-sweep — conflict — human needed (10 files: coga+packaged branch-sweep skill/workflow/ticket, src/coga/branchsweep.py, tests/test_branchsweep.py)
- commit-coga-state-sweep — conflict — human needed (7 files: sync SKILL twins, cli.py, git.py, tests)
- direct-body-strand-guard — conflict — human needed (4 files: commands/mark.py, git.py, mark.py, test_git.py)
- docs-sandbox-dev-loop-friction — conflict — human needed (1 file: codebase SKILL.md; main already carries an evolved superset — likely superseded)
- docs-with-review-workflow — conflict — human needed (2 files: with-review.md twins; main already has an evolved docs/with-review — likely superseded)
- fix-control-branch-mismatch-guidance — conflict — human needed (git.py, test_git.py; main has an evolved `_git_ref_present` version of the same fix — likely superseded)
- init-in-subdir — conflict — human needed (4 files: commands/init.py, update.py, cli SKILL twin, test_init.py)
- launch-blocked-chat — conflict — human needed (5 files: architecture SKILL twins, commands/launch.py, cli SKILL, test_launch.py)
- launch-end-refresh — conflict — human needed (7 files: sync SKILL twins, launch.py, git.py, views.py, tests)
- megalaunch-user-specific — conflict — human needed (4 files: config.py, megalaunch.py, tests)
- open-pr-gate-in-bump — conflict — human needed (13 files: open-pr skill/workflow twins, launch.py, tests)
- open-pr-script — conflict — human needed (13 files: same open-pr surface as open-pr-gate-in-bump — the two branches collide with main and with each other)
- recurring-scan-target — conflict — human needed (15 files: recurring/launch surface + contexts + tests)
- sync-context-nonfatal-git — conflict — human needed (2 files: sync SKILL twins; main text is already more evolved than the branch's fix — likely superseded)
- telemetry — conflict — human needed (README.md, cli.py, config.py; branch predates the README rewrite)
- unblock-auto-launch — conflict — human needed (18 files: recurring tickets/templates, launch/recurring/retire commands, tests)
- warn-version-skew — conflict — human needed (version_skew.py, test_version_skew.py; main has an evolved `_is_running_live_source` version — likely superseded)

Ticket-referenced branches that no longer exist locally or on origin (nothing
to rebase): codex/auto-persist-launch-dirt, codex/relay-prompt-scope-report,
codex/write-real-coga-documentation, dev-testing-contract,
refuse-blackboard-synthesis, retire-deletes-branch.

No ticket's open-pr step was unblocked this run (the only clean rebases left
empty branches). All conflicted rebases were aborted; every worktree left
clean, exactly as found.
