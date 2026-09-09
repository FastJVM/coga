---
slug: ticket-relationships-and-ownership-have-no-mechani
title: Ticket relationships and ownership have no mechanism
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

Three related ticket-model gaps, all found by Dream's knowledge scan with
evidence from tickets that hand-rolled a workaround. They share one question —
what relationships between tickets, and between a ticket and a person, does the
model carry? — so they are scoped together and may still split into siblings.

**1. Supersession is prose-only.** Seven `v2/` tickets annotate supersession by
hand and each invents its own shape: `v2/acceptance-criteria` uses a bold
"**Superseded by `<slug>` (2026-09-01).** … Do not work this ticket" paragraph
in `## Context`; `v2/cleanup-core-commands/work-orchestration-commands-to-tickets`
buries "The dedicated removal ticket supersedes the project-planning portion of
this work" mid-`## Description` without naming the successor;
`dream-recurring-persist-done-stop-inline-delete`,
`auto-persist-dirty-launch-worktrees-to-pushed-bran`,
`use-worktree-when-starting-a-dev-task` and
`cleanup-core-commands/launch-decomposition` each differ again. Nothing in the
model supports it: `CANONICAL_TICKET_KEYS` in `src/coga/ticket.py` has no
`supersedes`/`superseded_by`, and `src/coga/lifecycle.py` allows only
draft/active/in_progress/blocked/paused/done/canceled — no superseded terminal.
So a superseded ticket sits at `paused` or `draft` and keeps surfacing in
queues, blocker sweeps and launch candidates as live work.

**2. Ticket-to-ticket dependency ordering has no mechanism.**
`v2/identify-blocking-issues` asks for it directly ("possibly another field in
the ticket labelled 'dependencies'"), and
`v2/op-service-account-auth-to-skip-op-read-prompt` already implements it by
hand with a `### Blocks` section naming a successor that "**cannot be done
until this ticket ships**". `CANONICAL_TICKET_KEYS` has no dependency field, and
`blocked` is a runtime blocker-ask mechanism (`coga block` / `coga unblock` on
open questions), not a declared prerequisite between tickets — so an ordering
constraint recorded in prose is invisible to `coga status`, blocker sweeps and
launch selection.

**3. No command reassigns `owner:` / `human:`.** `v2/acceptance-criteria`
records the problem in its own body: taken over on 2026-09-01, "the
`owner:`/`human:` frontmatter still reads `zach` — there is no CLI command to
reassign it, and those fields are not agent-editable, so a human needs to change
them by hand". Fifteen tickets under `coga/tasks/` still carry `owner: zach`,
several paused with `assignee: nicktoper`, so the frontmatter and the body
disagree. `src/coga/commands/` has no assign module, which makes hand-editing
the only path and drift the default.

## Context

Each part has two honest outcomes and the design step should pick per part:
add the mechanism (a frontmatter field, a lifecycle transition, a command), or
document the convention so readers and tooling can rely on one spelling and
stop trusting what the model does not carry.

The natural home for a documented convention is
`coga/contexts/coga/architecture/SKILL.md` (with its enforced packaged twin);
a mechanism touches `src/coga/ticket.py`, `src/coga/lifecycle.py`,
`src/coga/validate.py` and possibly a new command.

Note: `document-design-pivot-in-blackboard-convention` was canceled, but it
covered a different shape — a design pivot inside one ticket — so that
cancellation does not close part 1.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
