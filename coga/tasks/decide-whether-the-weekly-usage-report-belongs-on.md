---
title: Decide whether the weekly usage report belongs on coga-important
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
launch_generation: aeac9f9c-9bcf-41b3-a40d-7905b36ac1bb
---

## Description

Filed by Dream 2026-W40, Phase 6 (shard ks-19, class stale, target `docs/contexts/coga/important/SKILL.md`). `coga/important` says the important destination is only for notifications that need a human to act ("Nothing else goes there"). This repo's local recurring template `coga/recurring/usage-report` (`ticket.py` ~line 30, `post(cfg, text, important=True, fatal=False)`; its `ticket.md` step 3) posts a weekly token-usage FYI there, a routing the owner chose explicitly in done ticket `agent-usage-report`. Contract and repo disagree; the owner decides which yields: move the usage report to the flow webhook, or record in `coga/important` (and its packaged twin) that a repo may deliberately route a low-volume periodic report there and why. State also whether repo-local templates are in scope for the `coga/notifications/producers` inventory.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/944
branch: usage-report-flow

## Peer review

Tool: Claude `/code-review` (default effort) against
`origin/usage-report-flow` vs `main`. The review **returned** (2026-09-30).
- Finding (low, applied): the template `ticket.md` had a relative link
  `../../../docs/contexts/coga/important/SKILL.md`. `recurring.py` copies that
  body unchanged into the deeper `coga/tasks/recurring/usage-report/<slug>/ticket.md`,
  where the link would break. It is now a plain-text `coga/important` topic
  reference, matching other recurring templates.
- No other findings. The review confirmed several points: the default flow
  routing is correct, `fatal=False` is kept, the test assertion is right, the
  skill and workflow links resolve, and the producer topic twins are
  byte-identical.
- The review found no stale important-route references (checked by `git grep`).
- There is no TTY or rendered surface beyond the Slack text. That text is
  unchanged, and only its webhook destination moves.
- Freshened the branch with a rebase onto `origin/main` (45 commits, no
  conflicts). The full suite on the rebased branch gave **3135 passed**.
  After the fix, `tests/test_usage_report.py tests/test_packaging.py
  tests/test_recurring.py` gave **496 passed**, and `git diff --check` was
  clean. Committed `peer-review: apply review findings` and force-pushed with
  lease. The branch is now 2 commits ahead of `main`, and the checkout is back
  on a clean `main`.

## PR

Route the weekly usage report to flow (resolves the Dream 2026-W40 stale
finding against `coga/important`).

`coga/important` reserves the important destination for notifications that need
a human to act. The repo-local `coga/recurring/usage-report` template was
posting its weekly token-usage FYI there. The owner decided the contract holds,
so the report moves instead:

- `coga/recurring/usage-report/ticket.py` posts with default (flow) routing,
  keeping `fatal=False` and the CLI bump.
- The template `ticket.md` now owns the routing decision and its rationale. The
  `usage-report/post` skill and workflow link to it instead of restating the
  route.
- `coga/notifications/producers` (canonical and packaged twin, byte-identical)
  now scopes its inventory to package and bundled producers. Repo-local
  templates own their routing in their own `ticket.md`.
- `tests/test_usage_report.py` asserts that the shim no longer passes
  `important`.

Test plan: `python -m pytest` (3135 passed on the rebased branch).

## Resumed implementation (2026-09-30)

Owner approved moving the weekly FYI to flow and excluding repo-local
templates from the packaged producer inventory. Their own `ticket.md` owns
routing. Keep the important action-needed bar unchanged; update the report,
its live instructions, and the producer topic plus packaged twin.

Start check: clean `main`; fetched `origin/main` and fast-forward check passed.
The earlier unrelated dirty ticket is now clean. Its branch-sweep fix is
already implemented in open PR #937 and its ticket is on owner-held review;
remaining work there requires a separate owner-assist launch.

## Implement handoff (2026-09-30)

Pushed `usage-report-flow`, rebased onto current `origin/main`, and returned
this checkout to clean `main` before writing this handoff. No PR opened.

- `coga/recurring/usage-report/ticket.py`: its module-level
  `coga.notification.post` call now uses default flow routing, preserving
  `fatal=False` and the CLI bump. The weekly report asks for awareness, not
  action, so the owner declined a periodic-report exception to important.
- The template's `ticket.md` owns that routing decision and rationale;
  its skill and workflow link there instead of repeating the old route.
- `coga/notifications/producers` now explicitly covers package and bundled
  producers, excluding repo-local templates whose own tickets own routing.
  Canonical and packaged topics are byte-identical.
- Updated the existing shim routing test before fixing the script and
  observed its expected failure on the old `important=True` call.
- Verification: `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest -q`
  gave **3135 passed**. After rebase (incoming changes were another ticket's
  notes only), `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest -q tests/test_usage_report.py tests/test_packaging.py`
  gave **38 passed**. `git diff --check` and producer-topic `cmp` passed.
  No config, task-model, or workflow semantics changed, so fixture validation
  was not required.
- The owner also asked about the earlier unrelated branch-sweep edits.
  They are no longer dirty; the fix is already in open PR
  https://github.com/FastJVM/coga/pull/937 on its owner review step. Its
  post-merge recurring-sweep rerun remains. This session did not work that
  separate ticket; resume with
  `coga launch autofix/make-branch-sweep-retirement-survive-an-existing-r --agent codex`.

## Implement attempt 2026-09-30 (megalaunch) — blocked on owner decision

Evidence:
- `docs/contexts/coga/important/SKILL.md` opening: important is "for notifications that need a human to act. Nothing else goes there."
- `coga/recurring/usage-report/ticket.py` (module-level `post(cfg, text, important=True, fatal=False)`, comment "on the important route the owner chose for it") and `ticket.md` step 3 route the weekly FYI to important.
- `docs/contexts/coga/notifications/producers/SKILL.md` inventories only package/bundled producers (e.g. `recurring/phone-home` → flow); no repo-local template rows.

Recommendation (agent, not decided): move the usage report to flow (drop `important=True`, update its `ticket.md` step 3). That keeps `coga/important` strict, needs no twin edit, and matches phone-home (the closest analog: a weekly FYI that goes to flow). Scope the producers inventory to package and bundled producers, and add one sentence saying repo-local templates own their routing in their own `ticket.md`.
Alternative: add a carve-out to `coga/important` and its packaged twin for deliberate low-volume periodic reports.

Also: the start check failed because `coga/tasks/autofix/make-branch-sweep-retirement-survive-an-existing-r/ticket.md` has unstaged edits on main, so no branch was cut.

---

## Blockers

- [x] [2026-09-30 11:09] [agent:claude] id=20260930T110914 Owner decision needed: should the weekly usage report (coga/recurring/usage-report/ticket.py, important=True) move to the flow webhook (agent recommendation, matches the phone-home precedent), or should coga/important plus its packaged twin get a carve-out for deliberate low-volume periodic reports? And should the coga/notifications/producers inventory cover repo-local templates (recommendation: no, they own their routing in their own ticket.md)? Note: main is also dirty (unstaged edits to autofix/make-branch-sweep-retirement-survive-an-existing-r/ticket.md), so no branch was cut.
  resolved: [2026-09-30 15:17] [human:nicktoper] Owner chose to move the weekly usage report to flow and keep the notification producers inventory scoped to package and bundled producers; repo-local templates document their routing in their own ticket.md. The prior dirty-checkout observation will be rechecked before branching.
