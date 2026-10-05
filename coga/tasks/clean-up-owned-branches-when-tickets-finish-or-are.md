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
step: 1 (implement)
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
