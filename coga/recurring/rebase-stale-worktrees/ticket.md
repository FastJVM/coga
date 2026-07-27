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
6. **Summarize** — replace the `## Rebase Run Summary

Run 2026-W31 (base: origin/main @ 5785f6a5; advanced from 2f9aff94 mid-run by a
concurrent sync). 17 live branches enumerated: 16 worktree branches + 1
origin-only branch from a live ticket. All 17 stale. **Nothing pushed.**

Headline: 16 of 17 are already-merged residue. Every one maps to a MERGED PR (or
work that landed by another route), squash-merged — which is why `git cherry`
still reports their commits as unmerged and why replaying them onto main
conflicts. These are branch-sweep's set, not this task's. Only
`drop-important-recipient` carries genuinely unlanded work.

Rebased-local, collapsed to empty vs main (branch-sweep candidates):
- release-0.3.0 — rebased-local (empty; PR #587 merged)
- workflow-cleanup — rebased-local (empty; PR #619 merged)

Conflict, rebase aborted, worktree left exactly as found — all merged residue,
so the conflict is squash-merge noise, not real drift. Retire via branch-sweep
rather than rebasing:
- commands-as-tickets-open-pr (#625) — launch.py, launch_script.py
- microkernel-move-recipes (#645) — 23 files (autoclose/blockers/branch-sweep recipe twins, CLAUDE.md, codebase SKILL, tests)
- no-remote-notice (#644) — git.py, test_git.py (main has a strictly more evolved version)
- real-coga-docs (#608) — README + docs/{concepts,development,getting-started,operations,reference}.md
- recurring-promote (#649) — recurring SKILL, docs/reference, recurring.py, validate.py, tests
- gh-optional-at-init (#580) — README.md, test_init.py
- gh-rate-limit-hint (#582) — managed_skills.py, test_init, test_managed_skills
- init-agent-cli-hint (#589) — README.md, test_init.py
- init-identity-fail-loud (#584) — init.py, test_init.py
- reinit-message (#588) — init.py, test_init.py
- removed-agent-key-migration (#579) — architecture SKILL twins, test_config.py
- usage-records-to-log (#562) — usage SKILL, launch.py, usage.py, test_launch, test_usage
- vendor-cli-from-package (#590) — cli-extension-audit.md, init.py, update.py, test_init
- remove-budget-guard (no PR; work landed anyway — main's config.py already
  carries the "budget guard was removed" migration error) — megalaunch.py/cmd,
  config.py, cli SKILL twin, test_config, test_megalaunch

Conflict — human needed (the one real one):
- drop-important-recipient (ticket `important-alerts-the-task-owner-drop-important-rec`,
  in_progress; origin-only, rebased in a disposable detached temp worktree, aborted,
  origin ref untouched at 4ecf442c). Conflicts in the `coga/important` and
  `coga/sync` SKILL twins (live + packaged). **This one needs a product decision,
  not a merge:** main has since documented `important_recipient` as a deliberately
  parsed-but-not-yet-routed key, which reads as an argument against the branch's
  premise that it should be deleted. Resolve the premise first, then rebase.

Ticket branches that exist nowhere (nothing to rebase): codex/auto-persist-launch-dirt,
codex/relay-prompt-scope-report, dev-testing-contract.

No ticket's open-pr step was unblocked this run. No branch or worktree deleted;
no worktree stashed, committed, or reset; all 16 worktrees verified clean and at
their original commits afterwards (except the two empty rebases above, which now
sit at origin/main).

Next-run note: this task keeps re-conflicting on residue that branch-sweep should
have removed. If branch-sweep is not deleting merged branches that still have
worktrees, fixing that is worth more than another sweep here.
