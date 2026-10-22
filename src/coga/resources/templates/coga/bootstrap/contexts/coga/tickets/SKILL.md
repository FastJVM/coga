---
name: coga/tickets
description: The ticket file contract — frontmatter validation rules, who may write which part, the body regions that compose, and `owner:` reassignment and ticket relationships; task discovery and refs, and creating and authoring tickets, live in its leaves.
---

# Tickets

A ticket is one unit of work, git-backed while it lives and disposable once
done (what it taught moves into contexts): YAML frontmatter, a body, the fence
line `<!-- coga:blackboard -->`, then the blackboard region. The blackboard
writer's contract is [coga/blackboard](../blackboard/SKILL.md); status and
step movement are [coga/lifecycle](../lifecycle/SKILL.md).

New tickets carry a field guide as an HTML comment under `## Context`,
rendered from the `ticket.md` resource. It owns frontmatter and blackboard
field shapes; the rules below and in the base prompt hold whether or not a
ticket carries it.

## Leaves

- [coga/tickets/discovery](discovery/SKILL.md) — where tasks live, file
  versus directory form, parked and group directories, task refs, and
  finding a retired task in Git.
- [coga/tickets/authoring](authoring/SKILL.md) — `coga create`, the guided
  `coga ticket` interview and its authoring agent, and `coga show`.

## Frontmatter validation

- An activated task must have an `agent` naming a configured agent. Null,
  blank, unknown, or since-removed names fail validation. Activation fills
  an absent draft value with the configured default agent; default resolution
  is explained beside `default_agent` in the shipped `coga.toml`
  ([coga/configuration](../configuration/SKILL.md)).
- `contexts`, `skills`, `secrets`: absence is empty and an empty list is not
  written. A malformed falsy value (`contexts:` null, `""`, `0`) stays on disk
  so validation names it.
- Removed keys are errors (validate kind `removed-ticket-field`). Every writer
  refuses such a ticket; there is no compatibility reader. Recurring templates
  reject them at load.
- Extension fields are strings only, with no nesting and no canonical-name
  collisions. `coga validate` fails on a missing declared field or enum
  violation and only warns on an undeclared orphan key. Extensions reach
  prompts only as part of the ticket, not as a separate layer.

**Who writes what.** Agents may edit `contexts` and the body sections, plus
the blackboard; every other frontmatter field belongs to CLI commands and
humans (base prompt). A specialized authoring skill may grant an explicit
exception. `coga/log.md` is written only by CLI commands.

## Body regions

Only `## Description`, `## Context`, and the live blackboard reach the agent
([coga/prompt-composition](../prompt-composition/SKILL.md)). Each section runs
to the next `##` line, so any other `##` above the fence is **uncomposed**: a
`## Acceptance Criteria` or `## Proposed Shape`, and equally a `## What broke`
written after Description prose, which also cuts that Description short.
Text before the first real `##` heading is also uncomposed, including the
entire body when it has no such heading. A `##` inside a code fence is text.

Relocate rather than add headings. Spec material (acceptance criteria,
proposed shape, out of scope, evidence) goes as `###` subsections under
`## Description`, background under `## Context`, and working notes below the
fence. Coga does not compose extra `##` sections.

The drop is not silent. `coga validate` warns `uncomposed-section` on every
non-terminal ticket, naming each omitted heading or preamble and the repair;
`coga launch` and `--prompt-report` print the same diagnostic. A nonempty
Description does not suppress the preamble warning. While a body has omitted
material, validate reports it instead of `empty-description`, because the
write-up is already on disk. Terminal tickets are exempt.

## Owner and relationships

`owner:` is the human of record: owner steps route to that person, megalaunch
filters by owner, and notifications mention them. Reassign with
`coga owner <slug> <name>`; it preserves status, step, and body, rejects blank
or unchanged names and terminal records, and writes an audit line without a
Slack post.

- An `in_progress` agent step must stop and be paused first.
- An `in_progress` **owner-held gate** instead requires `--assist-stopped`:
  the human attests, from outside that ticket's supervised session, that any
  assisting agent has stopped. The gate is preserved so its new owner can
  bump it. Coga has no live-session registry to check this.
- A supervised session cannot reassign its own ticket, and an outstanding
  `launch_generation` is refused. A plain or `released:` claim recovers
  through `coga launch <slug>`; finish or pause that session, then retry. A
  `pending:` claim needs the human to reconcile local and control evidence.
  Never clear a claim merely to force reassignment.
- A publication failure exits 75; refresh and reconcile control before
  retrying.

Ticket-to-ticket relationships use the dependency and supersession
conventions in [coga/lifecycle](../lifecycle/SKILL.md), not
`dependencies:` or `superseded_by:` frontmatter. Successor-side "this blocks
X" prose is a human pointer, not machine-readable ordering.
