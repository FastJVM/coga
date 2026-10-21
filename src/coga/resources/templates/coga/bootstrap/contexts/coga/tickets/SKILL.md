---
name: coga/tickets
description: The ticket file contract — canonical and extension frontmatter keys, who may write which part, and the body regions that compose; task discovery and refs, creating and authoring tickets, and ownership live in its leaves.
---

# Tickets

A ticket is one unit of work, git-backed while it lives and disposable once
done (what it taught moves into contexts): YAML frontmatter, a body, the fence
line `<!-- coga:blackboard -->`, then the blackboard region. The blackboard
writer's contract is [coga/blackboard](../blackboard/SKILL.md); status and
step movement are [coga/lifecycle](../lifecycle/SKILL.md).

New tickets also carry a field guide as an HTML comment under `## Context`,
rendered from `src/coga/resources/ticket.md`. It documents frontmatter and
blackboard field shapes; the editing rules below and in the base prompt hold
whether or not a ticket carries it.

## Leaves

- [coga/tickets/discovery](discovery/SKILL.md) — where tasks live, file
  versus directory form, parked and group directories, task refs, and
  finding a retired task in Git.
- [coga/tickets/authoring](authoring/SKILL.md) — `coga create`, the guided
  `coga ticket` interview and its authoring agent, and `coga show`.
- [coga/tickets/ownership](ownership/SKILL.md) — `owner:` reassignment and
  ticket-to-ticket relationships.

## Frontmatter

`src/coga/ticket.py` `CANONICAL_TICKET_KEYS` is the reserved set: `title`,
`status`, `owner`, `agent`, `workflow`, `step`, `contexts`, `skills`,
`delegate`, `period_generation`, `launch_generation`, `secrets`.
`validate.REQUIRED_TASK_KEYS` is `title`, `status`, `owner`, `workflow`; a new
draft is exactly those four (`status: draft`, `workflow: null`) plus a body.

- An activated task must have an `agent` naming a configured agent. Null,
  blank, unknown, or since-removed names fail validation. Activation fills
  an absent draft value using `Config.default_agent()`; default resolution
  belongs to [coga/agents](../agents/SKILL.md#the-default-agent).
- `contexts`, `skills`, `secrets`: absence is empty and an empty list is not
  written. A malformed falsy value (`contexts:` null, `""`, `0`) stays on disk
  so validation names it. `secrets` syntax is owned by
  [coga/secrets](../secrets/SKILL.md).
- `delegate` and `period_generation` are system-written and legal only on a
  materialized task directly under `tasks/recurring/`
  ([coga/recurring](../recurring/SKILL.md)); `launch_generation` is
  megalaunch's claim token ([coga/megalaunch](../megalaunch/SKILL.md)).
- **Removed keys are errors**: `slug`, `human`, `assignee`, `watchers`
  (`REJECTED_TICKET_KEYS`, validate kind `removed-ticket-field`). Every writer
  refuses such a ticket; there is no compatibility reader. Recurring templates
  reject them at load.

**Extensions.** A repo declares fields under `[ticket.fields.<name>]` in
`coga.toml` with only `description` (required), `values` (enum), `default`,
and `required`; strings only, no nesting, no canonical-name collisions
(`config._RESERVED_TICKET_FIELD_NAMES`). `coga create`/`coga ticket` write
each declared field below the `# --- extensions ---` marker, seeded with its
default or `""`. `coga validate` fails on a missing declared field or enum
violation and only warns on an undeclared orphan key. `coga mark active`
refuses empty `required` fields. Extensions reach prompts only as part of the
ticket, not as a separate layer.

**Who writes what.** Agents may edit `contexts` and the body sections, plus
the blackboard; every other frontmatter field belongs to CLI commands and
humans (base prompt `prompt.md`). A specialized authoring skill may grant an
explicit exception. `coga/log.md` is written only by CLI commands.

## Body regions

Only `## Description`, `## Context`, and the live blackboard reach the agent
([coga/prompt-composition](../prompt-composition/SKILL.md)). Each section runs
to the next `##` line, so any other `##` above the fence is **uncomposed**: a
`## Acceptance Criteria` or `## Proposed Shape`, and equally a `## What broke`
written after Description prose, which also cuts that Description short.
Text before the first real `##` heading is also uncomposed, including the
entire body when it has no such heading. Move substantive preamble prose into
`## Description` or `## Context`; whitespace alone needs no repair.

The contract is relocate, not compose. Spec material (acceptance criteria,
proposed shape, out of scope, evidence) goes as `###` subsections under
`## Description`, background under `## Context`, and working notes below the
fence. Coga deliberately does not compose extra `##` sections: an allowlist of
intent names would drop the next unlisted one, and composing every heading
would pull operational material into intent. `## PR` is the one operational
section allowed above the fence (legacy PR preparation read by `open_pr`,
never composed).

The drop is not silent. `coga validate` warns `uncomposed-section` on every
non-terminal ticket, naming each omitted heading or preamble and the repair;
`coga launch` and `--prompt-report` use the same diagnostic from
`taskfile.uncomposed_body_message`. A nonempty Description does not suppress
the preamble warning. While a body has either kind of omitted material,
validate reports it instead of `empty-description`, because the write-up is
already on disk. Terminal tickets remain exempt from these validation
warnings. Compose, validate, `open_pr`'s request
snapshot and create-time checks share one parser, `taskfile.body_sections`:
a `##` inside a backtick or tilde code fence is text, a fence never closed is
not a fence, a heading may be indented up to three spaces and carry a closing
`#` run, and the region below the blackboard fence is never read as body
sections.
