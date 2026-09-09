---
slug: title-only-tickets-have-no-convention-and-no-valid
title: Title-only tickets have no convention and no validator
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

Twenty-one tickets under `coga/tasks/` have a literally empty `## Description`
and `## Context`. Eleven were found in a single Dream shard: `manage-security-and-pii`,
`autoroute-agent-based-on-remaining-usage`, `pick-model-on-workflow-to-save-on-cost`,
`why-ai-asks-me-to-bump-instead-of-doing-it`, `remote-stale-command-line-toosl`,
`in-general-relay-files-should-be-easier-to-access`,
`generic-lib-to-use-e-g-patent-models`,
`project-manager-split-spec-in-tickets-block`,
`update-all-doesn-t-copy-workflow-correctly-to-atta`, and two
`create-vault*-and-service-account-for-*-trust-sec` tickets.

All that survives is a title, sometimes a typo'd one, so the intent is
unrecoverable by anyone but the author — `remote stale command line toosl` and
`generic lib to use e.g. patent models` cannot be launched or even
premise-checked. `src/coga/validate.py` checks blackboard size and workflow
shape but never that the body says anything, so these are invisible to every
sweep.

This is a different shape from the tracked workflow-less concept-capture draft:
a workflow-less draft is a decision deferred, a body-less draft is a thought
that was never written down.

Three such stubs also sit at the `coga/tasks/` root rather than in `v2/` —
`add-an-agent-picker-for-recurring`, `remov-digest-in-recurring`, and
`make-sure-repo-clietn-don-t-edit-coga` — where they read as current work in
`coga status` rather than as dated parked artifacts. The only document that
governs the stub habit is `coga/tasks/v2/README.md`, whose premise-check
contract is scoped entirely to the parking area, and the three open triage
tickets built on it all count and act only within `coga/tasks/v2/`.

## Context

Two directions, and the design step should pick one (or both):

- add a validator warning for an empty `## Description` so the capture path
  stays honest — note `validate.py`'s `unsynthesized-draft-blackboard` rule
  fires only when a draft blackboard carries pre-launch authoring notes, so an
  untouched placeholder is silent everywhere today; or
- document title-only capture as a supported shape with an explicit expiry,
  and either generalize the v2 README's "read every draft as a dated artifact"
  contract to any title-only draft wherever it sits, or rule root-level capture
  out so the habit lands in the one directory that has a triage contract.

Guard, carried verbatim by three existing tickets and by no context: a green
`coga validate` is never a reason to cancel a draft — it is a consequence of
correct verdicts, never an input to them.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
