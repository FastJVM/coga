---
title: Record that preserved tmp worktrees do not survive; only the branch does
status: in_progress
owner: nicktoper
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
agent: claude
---

## Description

Dream 2026-W39, Phase 2 gap G7. Work 'deliberately preserved' in a /tmp worktree is gone by the time anyone acts on it, while the local branch silently keeps the only copy. Evidence: autofix/make-dream-block-instead-of-done-when-its-retro-ch — Dream W36 preserved /tmp/dream-retro-2026-W36 plus branch dream/retro-2026-W36-1788212557; the directory and its worktree registration are gone today, but git log main..dream/retro-2026-W36-1788212557 still shows the two unlanded coga/log.md commits (d420b30, 3e4c60a), so the ticket's cleanup recipe is half-impossible and the branch is the sole copy. autofix/persist-autoclose-retire-follow-ups-beyond-the-per: 11 terminal tickets carry stale worktree lines pointing at gone directories. coga/recurring/autoclose-merged/ticket.md lists four auto-closed tickets whose /tmp ex-worktrees are gone while their branches survive in another clone, and retires.md's discharge rule then drops them as if retired. The Dream template itself put the retro clone under /tmp until this run (W39 used a sibling path). Deliverable: a short section in coga/contexts/coga/recipes/SKILL.md stating that /tmp worktrees are ephemeral on this machine; anything preserved 'for durability' must be pushed or cherry-picked onto main before the run ends; a gone worktree leaves a prune-able registration and a branch that still holds the commits; recovery is git log main..<branch>, cherry-pick/push from the primary checkout, then git branch -D. The active make-dream-block ticket's item 3 covers Dream's audit-line single point of failure; this ticket is the durable context note it does not cover. Coordinate with Dream PR #104, which edits the same context.

## Context

<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/917
branch: doc-tmp-checkouts-ephemeral

Plan: the ticket's target `coga/contexts/coga/recipes/SKILL.md` is a multiply path; no such topic exists here, and PR #104 here is an unrelated merged relay-era PR. Human chose `dev/checkout-cleanup` (plus its packaged bootstrap twin) as the owner. Add one short section: /tmp checkouts are ephemeral; push or land preserved work before the run ends; a gone checkout leaves a prunable registration and a branch holding the commits; recovery recipe.

## Handoff (implement)

- Commit 098109b34 on `doc-tmp-checkouts-ephemeral` (pushed, rebased on origin/main): new section "`/tmp` checkouts do not survive; the branch does" in `docs/contexts/dev/checkout-cleanup/SKILL.md`, copied byte-identically to the packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/dev/checkout-cleanup/SKILL.md`.
- Covers the ticket's four points: /tmp checkouts are ephemeral; push or land preserved work before the run ends (a `worktree:` line is not preservation); a gone worktree leaves a `git worktree prune`-able registration plus a branch holding the commits; recovery = `git log main..<branch>`, cherry-pick/push from the primary checkout, then `git branch -D`.
- Not done (out of scope here): the multiply-side evidence (dream/retro-2026-W36 branch, stale `worktree:` lines, autoclose list) lives in the multiply repo and was not touched.
- Tests: `.venv/bin/python -m pytest` — 3050 passed (system `python` lacks `tomlkit`; use the repo `.venv`).

## Peer review

- `codex review --base main` **returned** (exit 0) with one P2 finding: `git log main..<branch>` lists ancestry differences, including changes already landed by squash merge, so it cannot alone identify work to replay. The review reproduced this with identical trees and two branch commits still in the log.
- Resolved in published commit `ecaa9f2c7`: refresh `main`, treat the log as candidate commits, and check merged-PR history or patch equivalence before recovering only missing, wanted work. Both topic copies match. A concurrent review pushed this equivalent fix while this session ran; preserved that version and dropped the redundant local fix after the push lease refused the stale head. No must-fix findings remain.
- Final verification on `ecaa9f2c7`: `.venv/bin/python -m pytest` — **3050 passed** (179.13s); `git diff --check main...doc-tmp-checkouts-ephemeral` — clean; `cmp docs/contexts/dev/checkout-cleanup/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/dev/checkout-cleanup/SKILL.md` — identical. Only markdown changed; no terminal or rendered UI surface requires an interactive check.
- Refreshed with `git fetch origin main` and `git rebase FETCH_HEAD`; final branch commits are `e8c2887f2` and `ecaa9f2c7` atop `abbeb6538`. `git push --force-with-lease -u origin doc-tmp-checkouts-ephemeral` succeeded. Returned to clean `main` before writing this handoff; the ticket was still on `peer-review`.

## PR

Temporary checkouts can disappear while their linked-worktree branches retain unlanded commits. Document the preservation and recovery rules in `dev/checkout-cleanup`, including checking whether changes already landed before replaying them, and keep the packaged bootstrap twin identical.

Test plan: `.venv/bin/python -m pytest` — 3050 passed; `git diff --check main...doc-tmp-checkouts-ephemeral`; `cmp docs/contexts/dev/checkout-cleanup/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/dev/checkout-cleanup/SKILL.md`.
