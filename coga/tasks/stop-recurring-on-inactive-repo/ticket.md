---
title: stop recurring on inactive repo
status: draft
owner: nicktoper
workflow: code/design-then-implement
---

## Description

Recurring sweeps keep firing Dream, digest, skill-update, blocker-reminders and
friends on repos nobody is working in. xpllm is the live example: last human
commit 2026-09-04, yet recurring kept producing period runs, Sync commits and
autofix tickets (2026-09-11, 2026-09-14) — machine work feeding on machine
work. Make a scheduled sweep skip due templates when the repo is **inactive**:
no human activity within an idle window (default **14 days**, configurable).

Intended behavior (settled with the owner during authoring; `code/design` turns
it into the acceptance checklist):

- **Activity signal** = human commits on the default branch's first-parent
  history, *excluding* Coga machine commits (`Log:`, `Sync coga state`,
  `Ticket: recurring/…`, `Autofix:`, `Ticket: autofix/…`, Dream,
  `Update Coga-managed skills`) **and merges of machine-generated PRs** (Dream
  branches, `coga/skill-update`). Ticket transitions were measured too and add
  nothing beyond commits (every human ticket event already lands as a commit),
  so they need not be a separate signal unless design finds a reason.
- **What pauses:** every template by default, except `autoclose-merged` (a PR
  can still merge on a quiet repo). A template can opt in to running while
  inactive; the idle window is configurable.
- **Visibility and override:** the sweep reports a skip like
  `skip (repo inactive since <date>)`. `--force` and named launches
  (`coga dream`, `coga recurring launch <name>`) bypass the check. The repo
  wakes automatically on the next human commit — no persisted dormant state.

**Done** when the inactivity check, evaluated against the three repos as of
2026-09-25, reproduces the baseline below — coga active, magicator active,
xpllm inactive since 2026-09-04 — and would have made xpllm dormant from about
2026-08-14 and again from 2026-09-18, while never making coga dormant and
never making magicator dormant during its September work (gaps ≤ 8 days). The
behavior is documented in the owning topic and covered by tests.

## Context

**Baseline data (measured 2026-09-25, since 2026-05-01, `origin/main`
first-parent).** Reproduce with the sibling `measure-activity.py`, which is the
reference classifier for this ticket:

| Repo | Last human activity | Gaps ≥ 5 days |
|---|---|---|
| coga | 2026-09-25 | none (max 4) |
| magicator | 2026-09-22 | 15, 28, 9, 13 (May–Jul); 6, 6, 8 (Sep) |
| xpllm | 2026-09-04 | 6; 35 (Jul 31 → Sep 4), idle since |

Key finding: **without excluding machine-PR merges, magicator looks active on
2026-09-23** — that day was purely the owner merging Dream PRs #924–#927. A
naive "any human-authored commit" signal lets recurring keep itself alive.
Subject-regex classification is what the baseline script does, but it is
fragile; the design step should decide whether a sturdier marker (a commit
trailer on machine commits, branch-prefix rule for machine PRs) is worth it,
keeping the baseline result as the pass/fail check either way.

**Code and docs.** Sweep logic is in `src/coga/recurring_runner.py` (sweeps,
admission, `--all`); templates and ledger in `src/coga/recurring.py`. The
owning topic to update is `docs/contexts/coga/recurring/scheduling/SKILL.md`
(cited, not attached — it will be edited): see "What a sweep does per
template", "Variants" (`--force` "does not bypass branch, owner or TTY gates";
decide where the inactivity gate sits relative to those), and "Failures and
exit code" (a skip reason must not make the sweep exit 2 — only
`skip (already handled on control)` is currently exempt, so the design must
say how an inactivity skip is classified). Template fields (the opt-in flag)
are owned by `docs/contexts/coga/recurring/templates/SKILL.md`. Remember the
packaged twins under `src/coga/resources/templates/coga/` if a shipped topic
or template changes (`tests/test_packaging.py` enforces byte-identity).

**Out of scope:** notifying when a repo goes dormant; reaping existing period
tasks on already-idle repos.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
