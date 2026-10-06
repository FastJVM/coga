---
title: Clean up owned branches when tickets finish or are canceled
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

Terminal tickets leave abandoned branches behind because cleanup generally requires a merged PR. A deliberately closed, unmerged PR plus a done or canceled owning ticket should also authorize cleanup. The owner requested this change on 2026-10-05 after reviewing the branch backlog.

Agreed behavior:
- When a ticket becomes done or canceled, clean up all local and remote feature branches it explicitly owns once their PRs are merged or deliberately closed. A closed PR alone or a mere textual mention in a ticket is not ownership or deletion authorization.
- Preserve branches needed by another live ticket or any open PR. Preserve existing control/shared-branch and checkout safety protections.
- Detect and report source changes added after the PR closed or merged; do not silently discard unreviewed work. Handle multiple owned branches and local/remote divergence explicitly.
- Keep the existing lightweight retired/<branch> tag archive before branch deletion where applicable. Recovery is rare; do not introduce a new recovery service, UI, or elaborate retention machinery.
- Make refused cleanup visible and retryable through the existing cleanup paths. Determine the appropriate terminal-transition and recurring-sweep integration without deleting a checkout out from under an active session.

Acceptance:
- Tests cover merged PRs, closed-unmerged PRs with done/canceled owners, active owners, shared ownership, open PRs, incidental branch mentions, post-closure commits, and archive/checkout failures.
- Update the owning cleanup/lifecycle/scheduling contracts and relevant skills in the same PR; keep packaged twins synchronized.
- Audit the existing backlog against the new rules, record each branch disposition, and clear branches proven eligible. Work still wanted or lacking a clear disposition must be reported for a human decision, not inferred from a closed PR.

Starting evidence (2026-10-05; recheck before acting): GitHub had no open PRs and delete_branch_on_merge=false. This clone had 27 local feature branches; GitHub had 21. Some local origin refs were stale. The weekly sweep report at commit 4c937f2d4 (coga/tasks/recurring/branch-sweep/ticket.md) recorded 20 skips, including closed-unmerged PR branches such as usage-report-flow and split-ticket-contract, live-ticket claims, and refs with additional source changes. These are audit candidates, not an approved deletion list.

Read docs/contexts/dev/checkout-cleanup/SKILL.md, docs/contexts/coga/lifecycle/SKILL.md, docs/contexts/coga/recurring/scheduling/SKILL.md, and docs/contexts/coga/extension-model/SKILL.md before designing the change. Reuse the existing terminal finalization, retire/autoclose, and branch-sweep machinery; do not change GitHub settings as a substitute for the ownership rules.

## Context

<!-- coga:blackboard -->

## Dev
pr: https://github.com/FastJVM/coga/pull/963
branch: terminal-branch-cleanup-retire-sweep

Owner decision, 2026-10-05: two sessions implemented this ticket in parallel.
The owner chose `terminal-branch-cleanup-retire-sweep` (commits `89075137d`,
`3d611862a`, `fb331c25a`): terminal transitions delete nothing, and retire,
autoclose disposal and the daily/weekly sweep apply the terminal-owner
closed-PR rule. The *Implement handoff* below describes the abandoned
`terminal-branch-cleanup` branch (inline cleanup in `mark_done` /
`mark_canceled`). Its backlog deletions did happen, and its audit page is
carried on the chosen branch as `docs/evidence/branch-cleanup-audit-2026-10-05.md`,
together with a second pass from `/home/n/Code/coga`. Verification on the
chosen branch: full suite 3284 passed, 1 failed; the failure,
`test_edge_distribution::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`,
fails the same way on clean `main`. Still open: the owner-approved manual
removals listed in that audit page (refused by tool permissions), and the
`branchsweep._local_branches` follow-up noted below.

Re-implement handoff, 2026-10-05 (late): rebased the chosen branch onto
`origin/main` `b444a4af9` (README-only commits came in; no conflicts) and
force-pushed it with a lease. The branch is now at `4378fed01` (implementation
`660778187`, audit `5e4572b97`, audit consolidation `4378fed01`). Full suite:
3284 passed, with `test_edge_distribution::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`
deselected. Run on its own, it fails with the same `inventory` assertion as on
clean `main`. `git diff --check` is clean. No PR opened. The manual
backlog removals listed in the audit page, under *Second pass*, are still for
the owner to run.

## Plan

Owner approved the design on 2026-10-05: share explicit ownership checks across
terminal transitions, retire/autoclose, and sweeps; support multiple recorded
branches; permit closed-unmerged PR cleanup only for terminal owners; archive
before deletion and preserve unsafe refs with retry reasons. Defer cleanup
inside active sessions so no checkout disappears beneath the agent.

Read `src/coga/mark.py` (`mark_done`, `mark_canceled`),
`src/coga/checkout_disposal.py` (`dispose_checkout`, `live_checkout_claim`), and
`src/coga/branchsweep.py` (`sweep_branches`, `merged_pr_verdict`). Existing
sweep archives and merged-history proofs are the shared foundation. Backlog
must be rechecked: the snapshot changed and PR #961 is now open.

## Implement handoff — 2026-10-05

Pushed `terminal-branch-cleanup` at `1a6ca9893` (implementation `2dc7937a4`,
audit/diagnostics `1a6ca9893`), based on current `origin/main` `feb45858b`.
No PR opened. Returned this checkout to clean `main` before this handoff.

- `autoclose.parse_branch_names` reads every explicit Dev branch record;
  the first still drives ordinary PR/workflow consumers. Prose, attachments,
  and fenced examples grant no ownership.
- `checkout_disposal.checkout_records` scans all supported Coga workspaces;
  `branchsweep.sweep_branches` preserves live claims/open PRs and admits
  closed-unmerged heads only with a surviving terminal owner. It archives
  before disposal, inspects extra local source commits, judges remote tips
  separately, and retains foreign/unknown recorded checkouts. An incomplete
  remote or ownership scan preserves refs.
- `mark.mark_done` and `mark.mark_canceled` attempt cleanup after successful
  publication. `cleanup_terminal_ticket` scopes it to owned branches, records
  outcomes, and defers in task/supervised sessions or off control; it never
  removes checkouts. Daily/weekly sweeps retry. Retire iterates all branches;
  legacy owner-less worklist entries remain merged-only.
- Cleanup/lifecycle/scheduling and Dev-record contracts, invocation skills,
  shipped recurring-template prose, packaged twins, and the canceled example
  ticket were updated together. The recurring template change is intentional
  shipped source, not an operational period-task/blackboard change.

### Verification

- `.venv/bin/python -m pytest -q`: **3,275 passed**, including a fresh run
  after rebasing onto `feb45858b` (242.71 seconds).
- `.venv/bin/python -m pytest tests/test_branchcleanup.py tests/test_branchsweep.py -q`:
  **146 passed** after the final wording-only closed-PR diagnostic correction.
- From `example/coga`, `env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m coga.cli validate --json`:
  four valid tickets, no issues.
- `git diff --check`: clean. Initial regression run failed the new terminal
  ownership/multiple-branch/post-closure cases before implementation.

### Completed backlog cleanup and remaining decisions

The branch carries `docs/evidence/branch-cleanup-audit-2026-10-05.md`, with
all **48 branch names** and their before-tips, explicit owners, PRs, archives,
and dispositions. Refreshed the evidence before acting; did not use stale
origin refs or the prior weekly report as deletion authority.

Archived and deleted **24 local refs and eight remote refs**, across **31
branch names**, including closed-unmerged `usage-report-flow` and
`v2-premise-adjudication`. No checkout removed; no GitHub setting changed.
Fresh local/remote enumeration confirmed all deleted refs absent and all
31 archive tags present. Preserved **17 branch names**, including this branch
and three other live-owned branches. The audit names every remaining ask.

Human disposition is still needed for unowned closed branches (`dream-w40-testing-baseline`,
`fix/codex-peer-review-in-sandbox`, `publish-off-control`, `recurring-crlf-lease`,
`retire-worklist-linked-only`, `slack-important-alert`,
`wedge-ticket-admin-reproduction`); unowned/unlanded refs
(`docs/w40-workflow-corrections-duplicate-d4dea0eee`, `nicktoper-patch-1`);
the changed remote `recurring-ledger-from-log`; and checkout-held/foreign
`release-0.4.0`, `shebang-exec-check`, and `split-ticket-contract`.
No abandonment or completion was inferred for those. Live owners retain
`docs/v2-batch-verdicts`, `fix/retire-followup-owner`, and
`launch-marker-usage-match` (PR #961 remains open in the audit).

### Adjacent concern for follow-up

Existing `branchsweep._local_branches` ignores a failed `git for-each-ref`
return code. A failed local enumeration can therefore look like no local refs,
allowing an otherwise authorized remote-only cleanup attempt without a known
local inventory. This predates the change and was not exercised by the successful
live audit; it remains unresolved under the implement skill's no-adjacent-fixes
rule. No existing ticket was found for that exact failure. Keep the finding
for Retro to route into durable ownership/follow-up.

## Peer review

2026-10-06: peer review complete; the owner explicitly approved applying the
review fixes. Every Codex review **returned** before this handoff; none remains
in flight. The initial `codex review --base main` found two P1 live-claim
omissions and P2 loss of secondary branch debt. A second returned review found
P1 foreign-checkout ownership bypass. The last `codex review --base origin/main`
returned P1 list-contained fenced examples and P2 loss of ownership proof after
successful worktree removal. Manual review also reproduced ordinary fenced
examples authorizing deletion. All identified must-fix findings were addressed:

- One branch parser ignores fenced examples (including list/quote containers),
  indented examples, and empty values; both first-branch and all-branch readers
  use it. Every recorded live branch protects cleanup, including recurring
  tickets and claims in other workspaces.
- Each additional disposal candidate gets its own cross-workspace live-claim
  check, including merged branches. Incomplete scans preserve the candidate.
- An optional additional `branches` list in `retires.md` retains all local
  branch debt through ticket deletion and union merges. Reconciliation
  backfills surviving exact-slug tickets before discharge; old lines remain
  readable. The owning repository must release every listed local branch.
- A terminal ticket recording a foreign or unreadable checkout cannot grant
  closed-PR authority here. A disposal that just verified and removed a local
  linked worktree carries that exact path's proof through its restricted sweep;
  all other gates still run, and an already-missing or recreated foreign path
  gets no exception.

The final five edge-case regressions failed before their fixes and passed
with them. The final code was verified with the tests below after the returned
review findings were fixed; no separate no-findings review verdict is claimed.
Contracts and packaged twins are synchronized. Real Git fixtures drove branch,
archive, checkout, and retry behavior; the diff adds no raw-terminal loop,
pager, TTY prompt, or rendered-message layout requiring separate terminal QA.
No production backlog branches were deleted in this peer-review session.

Branch `terminal-branch-cleanup-retire-sweep` is committed and force-pushed
with a lease at `e51e558af`, containing `origin/main` `658ed49da`. The checkout
returned to clean `main` before this handoff. Rebased unconditionally and
without conflicts; the last rebases after full validation changed only
`README.md` (verified by comparing the tested and final tips). Verification:

- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q`:
  **3319 passed in 254.44s** at `31e5cdd58`, with no deselection; final source
  and tests are byte-identical to that tested tip. The earlier legacy-adoption
  failure did not reproduce with this explicit checkout import path.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_autoclose.py tests/test_branchsweep.py tests/test_autoclose_dispose.py tests/test_retire_worklist.py tests/test_retire.py tests/test_packaging.py -q`:
  **370 passed** after all cleanup fixes.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_packaging.py -q`:
  **23 passed** after the first README-only refresh.
- From `example/coga`, `env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json`:
  **4 valid tickets, no issues**.
- `git diff --check`: clean.

The audit's previously recorded owner-run manual removals and the adjacent
local-enumeration follow-up remain as documented above; this review did not
infer new deletion authority. No PR opened in this step.

## PR

Allow retire, autoclose disposal, and daily/weekly branch sweeps to clean up
explicitly terminal-owned branches whose PRs were deliberately closed without
merging. Terminal transitions delete nothing. Cleanup preserves live claims,
foreign checkouts, open PRs, and post-closure source changes; sweep deletions
retain the retirement-tag archive gate. Multi-branch retry records survive
ticket deletion, and Markdown examples never grant branch ownership.

Updates the owning cleanup/lifecycle/scheduling contracts and packaged twins,
and includes the dated branch-backlog audit.

Test plan: full pytest suite (3319 passed; later rebases changed only README),
focused cleanup/retire/packaging tests (370 passed), packaging refresh (23
passed), example validation (4 valid, no issues), and `git diff --check`.
