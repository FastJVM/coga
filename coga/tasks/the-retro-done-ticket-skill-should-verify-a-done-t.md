---
title: The retro done-ticket skill should verify a done ticket's claimed fix reached
  main before extracting it
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
step: 4 (review)
agent: claude
---

## Description

Filed by Dream 2026-W39, Phase 6. Route: `gap` finding with no open owner. Retro (and Dream's extract path) takes a done ticket's self-reported verification at face value; two tickets show a claimed fix that never or only half reached main. Decide whether `retro/done-ticket` (packaged file is the single owner; no live twin under `coga/skills/retro/`) should require verifying the exact token/path on the control branch before treating a claim as durable knowledge, and what to record when it is not. Related extract finding F2 (`test-recurring-create-is-silent-fixture-fix-is-hal`, source done) was handed to Phase 4 Retro this run.

**F42 — A done ticket's self-reported verification is not proof its scoped change reached main**  
(Dream 2026-W39 Phase 2, shard ks-10, ks-10 (merged); class `gap`; target `src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md (packaged file is the single owner; no live twin)`)

Two independent tickets record the same failure: a `status: done` ticket whose blackboard claims a fix that never (or only half) reached `main`, and every later reader — Retro, Dream, the next implementer — took the claim at face value. `coga/tasks/the-autofix-analyst-ticket-closed-without-shipping.md` (done, PR #816) documents that `fix-the-autofix-analyst` was marked done on the strength of an unrelated change (PR #724, the Claude subscription fallback) while none of the three defects its `## Description` scoped ever touched `src/coga/recurring_autofix.py`; closing it "removed the surface that would have kept the three defects visible", and the W36 backlog line that captured two of them did not drain. `coga/tasks/test-recurring-create-is-silent-fixture-fix-is-hal.md` (done) documents that `give-a-ticket-s-superseded-design-one-documented-h`'s `## Verification` claimed the fixture fix landed in `4012c5e9` when `c4482fae` carried half of it, so four later done tickets each re-recorded the failure as "pre-existing on main, worth its own ticket" and none checked the claim. The knowledge in the corpus covers only fragments: `bootstrap/dream/scan/knowledge-scan` tells the scan that a done ticket is "evidence to inspect, not an open owner" for *gap-owner* resolution, and `retro/done-ticket` says a ticket's `status: done` "says nothing about whether its adjacent bugs are fixed" and "do not ... claim one has landed" — for adjacent bugs only. Neither surface says the general rule these two tickets each had to rediscover: before Retro extracts from, deletes, or cites a done ticket as delivery evidence, compare the ticket's `## Description` acceptance scope against `main` (the named source path, test, or context) rather than against its own `## Implemented` / `## Verification` prose; a done ticket whose scoped change is absent on `main` is an unshipped ticket to report (a follow-up bug ticket, as `the-autofix-analyst-ticket-closed-without-shipping` did), not knowledge to extract or a fix to cite. No open ticket owns this (grep of `coga/tasks/` for `half-applied`, `closed without shipping`, `claimed ... landed`, `self-reported` hits only the two done tickets above). Suggested home: a short "Done is a status, not a receipt" paragraph in `retro/done-ticket`'s read-the-blackboard section, with a one-line pointer from `coga/lifecycle` (`docs/contexts/coga/lifecycle/SKILL.md`, which now owns the former `coga/contexts/coga/architecture` "Two state machines per ticket" section) (`done` is a control-plane transition and carries no proof the description shipped).

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/887
branch: retro-verify-done-scope
worktree: /home/n/Code/coga-retro-verify-done-scope

## Implemented (commit 4a0b6909a)

Decision, confirmed with the owner: Retro **preserves and reports** the gap and does not file a follow-up ticket itself. Routing the follow-up stays with the caller (Dream Phase 6 or a human). This keeps a knowledge PR limited to knowledge edits and source deletions.

- `retro/done-ticket` (packaged-only owner): new `### Done is a status, not a receipt` subsection after `### Unresolved adjacent bugs`. It checks the `## Description` scope (path, symbol, test, context token) against the isolated checkout's current files, which are the fresh control-branch tip. The check reads the current tree only, so it is consistent with the skill's no-history baseline rule. When the scope is absent or partial, Retro does not extract or cite the claimed fix and preserves the gap as a known failure mode. The source counts as knowledge-bearing, so it is never direct-deleted. Also added:
  - a step-3 reference to the new subsection;
  - a `Unshipped scope` classification row;
  - a step-9 deletion gate;
  - a PR-body `Unshipped scope:` line.
- `coga/lifecycle` (canonical copy and bootstrap twin, byte-identical): a bullet saying `done` is a control-plane transition, not a receipt, pointing to `retro/done-ticket`.
- Test: `tests/test_dream_worker_templates.py::test_retro_checks_a_done_tickets_scope_reached_the_control_branch`.

## Verification

- Full suite (py3.12, uv ephemeral env): 2876 passed and 2 failed. Both failures are in `test_packaging` wheel builds, because that env has no pip. They are environmental, not caused by this change.
- In a real py3.12 venv with `pip install -e ".[test]"`: `tests/test_packaging.py` plus `tests/test_dream_worker_templates.py` gave 37 passed.
- Note: the system `python` here is 3.9, and there is no repo `.venv`.


## Peer review

- `codex review --base main` returned with no actionable findings. Its attempted targeted test run lacked `tomlkit`; the full run below used the complete Python 3.12 environment and passed.
- Ran `git fetch origin main` and `git rebase --autostash FETCH_HEAD`; rebase completed without conflicts. Reviewed implementation is now commit `cab1e5a73`, one commit ahead of fetched main (`996fa06c9`). No review fixes were needed.
- Verification: `PYTHONPATH=/home/n/Code/coga-control/src /tmp/claude-1000/-home-n-Code-coga-control/b29692c5-07f5-471d-8d1b-bfece98eb698/scratchpad/venv/bin/python -m pytest` — **2878 passed** in 168.19s. Output: `/tmp/retro-peer-review-pytest.log`. `git diff --check` passed.
- Reviewed the instructions against the existing current-tree baseline, missing/partial-scope reporting, and deletion rules. No terminal or rendered UI surface changed; no manual terminal exercise applies. The template assertions guard instruction presence, not agent compliance.
- Corrected the checkout handoff: `/home/n/Code/coga-control` is a linked checkout, so it cannot use open-pr's single-checkout exception. Returned it to `main` and moved the committed feature branch to `/home/n/Code/coga-retro-verify-done-scope`, with local config seeded. The feature worktree is clean. Task/log state remains in the control checkout for CLI publication.

## PR

Retro previously trusted a done ticket's claimed fix without checking whether its description's scope reached the control branch. Require a current-tree check before extracting or citing that claim. Preserve absent or partial scope as a known failure mode in the knowledge PR, and report it for the caller to route follow-up work before deleting the source.

Update the packaged Retro skill, the lifecycle topic and its identical bootstrap twin, and the template regression test. Retro continues to leave follow-up ticket creation to its caller.

Test plan: `PYTHONPATH=/home/n/Code/coga-control/src /tmp/claude-1000/-home-n-Code-coga-control/b29692c5-07f5-471d-8d1b-bfece98eb698/scratchpad/venv/bin/python -m pytest` — 2878 passed; `git diff --check` passed.
