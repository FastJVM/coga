---
title: Prevent parent-ticket assumptions during task splits
status: draft
owner: nicktoper
agent: claude
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

Prevent Coga authoring guidance from leading an assistant to invent a parent
or umbrella ticket when splitting related work into a directory. During the
2026-09-09 Multiply updater review, the assistant twice proposed keeping
`v1/updater/3-auto-update` as a parent with shared design, open questions, and
responsibility for the complete outcome. The owner corrected it: related
Coga tickets are grouped by a directory, not a parent ticket.

This is a concrete agent-guidance failure, not a request to add parent/child
task primitives. Strengthen Coga's canonical context and ticket-authoring
examples so a fresh session uses a plain directory and assigns every outcome
to an actual ticket. The immediate local correction lives in
`coga/contexts/coga/task-grouping/SKILL.md` and is linked from `AGENTS.md`.

### Acceptance criteria

- [ ] Record the reproduced mistake and owner correction in Coga's durable
  guidance: a directory groups work, and its README can hold shared material,
  but the group has no ticket workflow, status, assignee, or completion gate.
- [ ] Clearly distinguish a plain grouping directory from a directory-form
  task containing `ticket.md`. Explain that discovery stops at a task
  directory, so nested tickets would not be found.
- [ ] Update canonical authoring/splitting guidance to transfer decisions and
  deliverables to actual tickets, preserve common material in README/context,
  and rewrite live dependencies to exact successors before retiring the old
  task. Do not create umbrella tickets or parent/child frontmatter fields.
- [ ] Make the rule available in the prompt surfaces used for orientation and
  ticket authoring; a context that exists but is never composed or linked is
  insufficient. Update the relevant packaged copies through Coga's owning
  repository/package workflow rather than editing an installed cache.
- [ ] Use a cold authoring review of the updater split as a regression scenario:
  the proposed output is a directory with three independently scoped tickets,
  no `ticket.md` at the group root, and no gate waiting for a directory to
  become `done`. Reuse existing discovery/README coverage unless implementation
  changes introduce a concrete need for new behavioral tests.

### Out of scope

Adding a hierarchy/rollup engine, teaching Coga a new parent lifecycle,
redesigning the Multiply updater, or changing unrelated historical tickets.

## Context

The observed exchange was in the owner review of Multiply's former
`coga/tasks/v1/updater/3-auto-update.md`. The assistant proposed retaining it
as a parent when presenting three implementation scopes, even though Coga
already has directory grouping. The owner explicitly asked for this context
clarification and follow-up ticket. The resulting local example is
`coga/tasks/v1/updater/3-auto-update/README.md` and its three sibling tickets.

This follow-up is tracked in Multiply's Coga task list. The reusable fix belongs
in the Coga project (`FastJVM/coga`), with the installed package's provenance
used to locate the right source checkout. Inspect that repository's own agent
guide and contexts before working there; do not implement Coga package changes
inside Multiply or edit the user's installed package files.

Source pointers from the installed Coga package: `src/coga/tasks.py` excludes
`README.md`, recursively discovers plain grouping directories, and stops at
`ticket.md`; `src/coga/create.py::_normalize_create_dir` refuses nesting under
an existing directory-form task. These behaviors support the owner's model.
The guidance candidates are package-bootstrap `contexts/coga/architecture`,
`contexts/coga/cli`, and the `bootstrap/ticket` skill, plus the source's tests
and packaging conventions. Preserve the microkernel boundary: this is primarily
context/authoring guidance work, with code changes only for an evidenced gap.

### Authoring review

The independent reviewer confirmed the directory/discovery guidance and the
owning-repository boundary. The standard `code/implement` workflow skill was
2,502 of the initial 6,178 composed tokens (40.5%); it is a shared-skill trim
candidate, not ticket-context bloat or a blocker for this focused follow-up.

<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise. Multiply's local `coga/task-grouping` context override (the owner clarification this ticket wants upstreamed) is attached as `multiply-task-grouping-context.md`; the context ref was dropped because it does not exist here.


The blackboard is a notepad to be written to often as the human and agent works through a task.
