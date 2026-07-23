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

last_serviced_period: 2026-W30

## Rebase Run Summary

Run 2026-W30 (base: origin/main @ e842c8d3). 28 live branches enumerated (25
worktree branches + 3 origin-only ticket branches); all stale vs the new base.
No branch rebased to a clean, non-empty state, so **no pushes** this run. Every
clean rebase collapsed to empty-vs-main (already-merged residue → branch-sweep);
every non-empty branch conflicts semantically with the advanced main.

Skipped (never touched):
- megalaunch-pick-all-nonterminal — skipped (this sweep's own live checkout; dirty with recurring state files)
- human-minutes-ledger — skipped-dirty (uncommitted changes, no-upstream)
- ticket-script-authoring — skipped-dirty (uncommitted changes, no-upstream)

Rebased-local, empty vs main (branch-sweep candidates, not pushed):
- fix/annotated-dev-metadata — rebased-local (empty; all commits already in main)
- picker-sigwinch-redraw — rebased-local (empty)
- validate-frozen-workflow — rebased-local (empty)
- cleanup/workflow-inventory — rebased-local (empty, no-upstream)
- codex/fail-unsynthesized-draft-validation — rebased-empty via origin (worktree dir gone; branch-sweep candidate)
- workflow-cleanup — rebased-empty via origin (origin-only ticket branch; branch-sweep candidate)

Conflict — human needed (rebase aborted, worktree left exactly as found):
- fix/attended-ask-not-block — architecture SKILL twins, prompt-megalaunch.md, test_compose/test_megalaunch
- browser-bootstrap — README, browser-automation ticket/SKILL twins, cli SKILL, test_compose/test_init/test_packaging
- marketing/rewrite-readme-wedge — README.md, docs/velocity-report.md
- megalaunch-blocker-drain — architecture SKILL twins, megalaunch.py (cmd+lib), test_megalaunch
- fix/open-pr-primary-checkout — open-pr skill/recipe/workflow twins, architecture SKILL, open_pr.py, docs/reference, tests
- codex/redact-slack-webhook-errors — src/coga/slack_response.py, test_notification
- remove-autonomy-triage — brief/draft-for-human workflow twins, bootstrap ticket/browser SKILL, test_browser_automation_bootstrap/test_init
- resolve-conflicts-command — resolve-conflicts ticket twins, docs/reference, test_launch
- codex/canceled-ticket-status — via origin; 17 files (megalaunch/mark/recurring_runner/validate + SKILL twins + tests)
- fix/dream-task-env — via origin; launch.py, launch_script.py, architecture SKILL twins, test_launch
- harden-install-gate — via origin; scripts/verify-clean-install-container.sh, test_clean_install_gate
- log-session-activity — via origin; launch.py, ticket.py, test_launch
- real-coga-docs — via origin; README + docs/{concepts,development,getting-started,operations,reference}.md
- fix/recurring-remote-dedup — via origin; recurring_runner.py, sync/architecture/current-direction SKILL twins, test_recurring
- recurring-skip-unconfigured — via origin; recurring_runner.py, architecture/cli SKILL twins, test_recurring
- fix/removed-skill-hint — via origin; src/coga/validate.py, test_validate
- fix/retro-worktree-isolation — via origin; retire.md, dream ticket, retro SKILL twin, test_dream/test_retire/test_retro
- commands-as-tickets-open-pr — via origin (origin-only ticket branch); launch.py, launch_script.py
- docs/custom-recurring-tickets — via origin (origin-only ticket branch); coga/contexts/coga/recurring/SKILL.md

Ticket-referenced branches that no longer exist locally or on origin (nothing
to rebase): drop-important-recipient, dev-testing-contract,
codex/relay-prompt-scope-report, codex/auto-persist-launch-dirt.

No ticket's open-pr step was unblocked this run (the only clean rebases left
empty branches; nothing pushed). All conflicted rebases were aborted; every
worktree left clean, exactly as found. GONE-DIR branches (worktree dir cleaned
from /tmp) were rebased from origin/<branch> in disposable temp worktrees;
each such local ref equaled origin (no unpushed work), and temp worktrees were
removed after use — no worktree or branch was deleted.
