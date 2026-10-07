---
title: Skip inactive-repo recurring templates without strict validation
status: draft
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
---

## Description

On an inactive repo, `scan_due` (src/coga/recurring.py) runs the strict `Template.load` before the inactivity skip. A stale non-exempt template (e.g. a pre-simplification `assignee:` key, seen on xpllm 2026-10-07) therefore errors and fires an --important alert for a repo the owner has stopped working on.

The full load exists only to read `run_when_inactive` (and the schedule for the table row). Change: on an inactive, non-forced sweep, read just those fields leniently; non-exempt templates get the normal `skip (repo inactive since …)` row with no strict validation and no alert. Exempt templates, active repos and `--force` keep full validation. Frontmatter that cannot be parsed at all still reports loudly.

Tradeoff accepted by the owner: a broken template on a dormant repo surfaces only when the repo wakes (or via `coga validate`).

Done when: the `## Repo inactivity` section of coga/recurring/scheduling ("Inactive templates are loaded and validated, then skipped") and the `run_when_inactive` bullet in coga/recurring/templates are updated, packaged twins stay in sync, and tests cover: inactive + rejected-key template → skip row, no scan error; inactive + exempt broken template → error; active broken template → error.

Out of scope (separate ticket if wanted): checking inactivity right after the fetch so a diverged inactive repo (thinkpick) is skipped instead of failing control catch-up.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
