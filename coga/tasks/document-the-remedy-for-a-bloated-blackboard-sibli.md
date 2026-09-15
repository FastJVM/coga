---
title: 'Document the remedy for a bloated blackboard: sibling attachments and unattached
  contexts'
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
step: 2 (peer-review)
agent: claude
---

## Description

Dream 2026-W38 gap finding. Two marketing tickets independently solved the same problem the same way with no context to reach for: when the blackboard becomes the largest composed prompt layer, promote the task to directory form and move dated evidence into sibling attachments; move superseded program material into an unattached context. The architecture context only says the --prompt-report line is how a bloated blackboard gets noticed, not what to do next. Draft paragraph in Context.

## Context

Evidence (two independent tickets, same remedy, no context to reach for):

- `marketing/phase-0-audit` recorded that the full step-1 evidence "pushed the
  blackboard to 58 KiB, all of which composes into every launch prompt for this
  task. It is moved, not deleted" into two sibling attachments
  (`coga/tasks/marketing/phase-0-audit/audit-history.md`,
  `narrative-candidates.md`), each opening with a comment naming the task and
  the date it was moved out, leaving only the current handoff and worklist on
  the blackboard.
- `marketing/build-the-launch-plan` "archived the superseded program and proof
  apparatus in the unattached `marketing/launch-history` context. It stays
  durable and is committed by Coga state sync but adds zero composed tokens to
  live tickets", and recorded the resulting layer sizes.
- `coga validate` flags `large-blackboard` (32 KiB warning threshold); this run
  flagged `reconcile-recurring-wrapper-tty-admission-guidance` at 54 KiB. The
  `coga/architecture` Layer-6 passage says the `--prompt-report` entry "is how a
  bloated blackboard gets noticed" but not what to do next; the attachments
  passage describes directory-form tasks without this use; `draft-for-human.md`
  only says "if it is large, record the path or link".

Proposed change — one paragraph after the "how a bloated blackboard gets
noticed" sentence in `coga/contexts/coga/architecture/SKILL.md` (and its
packaged twin under `src/coga/resources/templates/coga/bootstrap/contexts/`):

```markdown
When the blackboard entry in `--prompt-report` is the largest layer, do not
trim history by deleting it. Promote the task to directory form and move
dated evidence into sibling attachments (`tasks/<slug>/<topic>.md`) that open
with an HTML comment naming the task they belong to and the date they were
moved out; leave the blackboard holding only the current handoff, worklist
and verification, with a pointer to each attachment. Superseded program
material that several tickets may still cite belongs in an *unattached*
context (one no live ticket lists under `contexts:`): it stays git-tracked
and synced but composes zero tokens. Record the resulting layer sizes on the
blackboard so the next author can see what the split bought.
```

Open PRs #790 and #798 edit the architecture context in other hunks; rebase
over whichever lands first. Consider whether `validate-drift`'s
`large-blackboard` remediation line should point at this paragraph once it
exists.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: bloated-blackboard-remedy
worktree: /home/n/Code/claude/coga-bloated-blackboard-remedy

## Implement — 2026-09-15

Commit `81cda358` on the branch above (one commit, rebased on `origin/main`
`ec8a3919`; PRs #790 and #798 had already landed, so no conflict to rebase
over).

What changed:

- `coga/contexts/coga/architecture/SKILL.md` + packaged twin: the proposed
  remedy paragraph now follows the "how a bloated blackboard gets noticed"
  sentence in the Layer-6 passage. Two additions beyond the ticket's draft,
  each verified: it points back at the promotion recipe already in the
  attachments passage (`mkdir <slug>/ && mv <slug>.md <slug>/ticket.md`),
  and it states that attachments are never composed — `compose.py` reads only
  `task_ref.ticket_path`. It closes by naming `BLACKBOARD_WARN_BYTES` (32 KiB)
  and that `validate-drift` routes the warning here.
- `src/coga/dream_validate_drift.py`: the `large-blackboard` remediation no
  longer says "reviewed blackboard condensation"; it names the
  `coga/architecture` remedy (directory form, sibling attachments, unattached
  context, "move, do not delete"). Test added in
  `tests/test_dream_validate_drift.py::test_classifies_large_blackboard_as_attachment_remedy`,
  mirroring the neighbouring `classify_issue` tests.
- `coga/contexts/coga/blackboard/SKILL.md` + packaged twin: one clause after
  the `BLACKBOARD_WARN_BYTES` sentence saying the remedy is owned by
  `coga/architecture` — a pointer, not a restatement, per "one owner per
  fact".

Not changed, deliberately: `draft-for-human.md` ("if it is large, record the
path or link") is about where an artifact lands, not blackboard size, so it
does not need the pointer.

Verification: `python -m pytest` in the worktree (via the primary `.venv`,
Python 3.12) — 2496 passed. `tests/test_packaging.py` confirms both twin
pairs byte-identical.
