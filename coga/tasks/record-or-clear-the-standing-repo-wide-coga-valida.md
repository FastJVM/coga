---
slug: record-or-clear-the-standing-repo-wide-coga-valida
title: Record or clear the standing repo-wide coga validate baseline
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
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
secrets: null
step: 1 (implement)
---

## Description

`coga validate --json` exits 1 repo-wide as a matter of course, because four
`v2/` drafts carry unsynthesized blackboards: `v2/autotrigger-ticket-type`,
`v2/measure-relay-prompt-scope-and-agent-precision`,
`v2/split-context-to-doc-user-accessible-and-editable`, and
`v2/use-worktree-when-starting-a-dev-task`.

Independent tickets keep re-establishing this from scratch as part of their own
verification. `service-account-scoping-single-vault-rule-conflict` recorded "45
issues, 4 errors, all four pre-existing `unsynthesized-draft-blackboard` errors
on unrelated `v2/` drafts"; `redo-documentation-dir-and-merge-it-with-context-b`
recorded "exit 1, 175 OK, 40 warnings, four existing
`unsynthesized-draft-blackboard` errors" and named all four slugs. This Dream
run's own validate-drift pass found the same four.

`triage-the-v2-parking-area-empty-descriptions-prem`, whose title is literally
about the permanently red validate, is `canceled` — so nothing is scheduled to
clear it.

`coga/contexts/coga/codebase/SKILL.md` already tells agents to prefer
`coga validate --task <slug>`, but does not say that the repo-wide run is
expected to be red, which four errors are the standing baseline, or that they
must not be auto-fixed under an unrelated ticket.

## Context

Either outcome closes this, and they are not equivalent:

- **Record the baseline** beside the existing `--task` bullet in
  `coga/contexts/coga/codebase/SKILL.md` (and its enforced packaged twin) with
  its date and the four slugs, plus the rule that they must not be swept up by
  an unrelated ticket; or
- **clear it** by synthesizing or adjudicating those four drafts, so the
  repo-wide gate can go green and stay meaningful.

The second is better if the drafts are being adjudicated anyway — see the
sibling ticket `adjudicate-parked-and-active-tickets-whose-premise`, which
covers several of the same files. Sequence this behind it if both are worked.

Guard: a green validate is never a reason to cancel a draft.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
