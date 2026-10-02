---
title: Tell agents never to git-commit coga task and log state
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

Agents sometimes run `git add`/`git commit` on `coga/tasks/**` and `coga/log.md` on the control branch. Coga publishes that state itself, straight to origin, and fast-forwards the checkout; a hand commit makes local main diverge, so later publishes cannot fast-forward it, `coga/log.md` stays dirty, and `coga launch` refuses until a human rebases and pushes. Add one rule to the base prompt (`src/coga/resources/prompt.md`, the ticket-and-blackboard section near the `coga/log.md` paragraph): never `git add` or `git commit` `coga/tasks/**` or `coga/log.md`; the CLI publishes them. Update the owning topic (`coga/prompt-composition` or `coga/sync`, whichever states the agent-side rule) and any packaged twin in the same PR.

Done when: the composed prompt of a launched session carries the rule; `tests/test_packaging.py` and `python -m pytest` pass; the PR cites the 2026-10-01 incident below.

Incident (2026-10-01): an attended `bootstrap/orient` session (Claude, session `94bb601e-cc9a-4e52-8e94-7c67ada785fb`) unblocked `marketing/fix-installer/offer-agent-cli-install-and-setup-at-init` and switched its workflow, then ran `git add … && git commit -qm "Blackboard: …"` (15:33) and `git add coga/log.md coga/tasks/… && git commit -qm "Ticket: … — workflow code/with-review"` (16:00), mimicking Coga's own subjects, and never pushed. The reflog shows them as plain `commit:` entries against Coga's `merge …: Fast-forward` publishes. The next `coga launch` refused with "local 'main' has commits not on origin/main"; the operator's `git pull --rebase` then refused on the dirty log. Nothing in the composed prompt forbade the commit: the base prompt only says not to *edit* `log.md`, and `coga/sync` is not attached to orient sessions. Companion guard ticket: "Recover when local main carries hand commits of coga state".

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
