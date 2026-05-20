---
title: Add bootstrap/extend-ticket-format skill for per-repo field extensions
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills:
- bootstrap/ticket
workflow: null
---

## Description

A repo eventually needs a ticket frontmatter field that the base
relay format doesn't cover — `customer:`, `docket:`, `linear_issue:`,
whatever fits the domain. Today the only path is "edit a context
manually and remember to update every consumer." That's fragile and
undiscoverable.

The idea: declare frontmatter extensions directly in `relay.toml`
under a new `[ticket.fields.<name>]` section. The TOML is the spec.
The ticket template has a fixed insertion point. Two consumers honor
the spec: ticket creation writes the declared fields into every new
ticket, and `relay validate` enforces them.

No new prompt-composition logic — the field lives in the
frontmatter itself, which is already in every composed prompt.

### Example

```toml
[ticket.fields.docket]
description = "USPTO docket number"

[ticket.fields.application_number]
description = "USPTO application number"
required = true
```

Yields a freshly-created `ticket.md` whose frontmatter ends with:

```yaml
workflow: null
# --- extensions ---
docket: ""
application_number: ""
---
```

The human (or the `bootstrap/ticket` interview) fills in real values
before `relay mark active`.

## Design

- **Insertion point in the template.** `relay-os/tasks/_template/ticket.md`
  carries a literal `# --- extensions ---` line as the last
  frontmatter line before the closing `---`. The line is a YAML
  comment, so parsing is unaffected. Both creation paths and
  `relay validate` use this marker as the contract for "everything
  below me is an extension."
- **Two creation surfaces, one mechanism.** `relay draft` (raw
  `scaffold_task()` in `src/relay/commands/create.py`) and the
  `bootstrap/ticket` interview skill both write declared fields
  below the marker. `draft` scaffolds the field skeleton with the
  default (or `""` if none). The interview optionally fills them
  in by asking the human. Identical shape either way.
- **`relay validate` enforces declared constraints.** Anything
  below the marker must match a declared `[ticket.fields.*]`.
  Declared-but-missing fails loud. Present-but-undeclared fails
  loud. Enum violations fail loud.
- **`relay mark active` gates required fields.** Refuses to
  activate a draft that has empty values for fields declared
  `required = true`. Required-empty at draft time is fine;
  required-empty at activation time is not.
- **Reserved-name collision check at config load.** Refuse to start
  if `[ticket.fields.<name>]` collides with canonical frontmatter
  names (`title status mode owner human agent assignee watchers
  workflow step contexts skill`). Same pattern as alias collisions —
  fail loud at TOML load, point at the canon doc.
- **Old tickets break loud when the schema changes.** Adding a new
  field today means yesterday's tickets fail `relay validate`. That
  is the point. No silent backfill, no `--fix` magic. The human
  reads the diff and edits each affected ticket — or removes the
  field declaration if they didn't mean it.
- **Removing an extension is symmetric.** Delete the TOML section.
  Existing tickets keep the field as orphan frontmatter; `relay
  validate` warns but doesn't error. No migration step.
- **Hard line against schema creep.** v1 supports four keys per
  field: `description` (string, required), `values` (list of
  strings, optional enum), `default` (string, optional),
  `required` (bool, optional). That's it. No types beyond string,
  no conditionals, no regex, no computed defaults, no nested
  structs. Anything richer goes through a context the old way.

## Out of scope

- Synthesized prompt blocks describing extensions to the agent.
  The frontmatter itself is in the composed prompt; no extra layer.
- Always-on context tier coupling. This ticket ships independently.
- Non-string types (booleans, numbers, lists). Add later if a real
  need surfaces.

## Context

- `relay.toml` already has `[aliases]`, `[agents.<type>]`,
  `[assignees.<user>]`, `[slack]` — `[ticket.fields.<name>]` slots
  into the same pattern. See `relay-os/relay.toml`.
- Template: `relay-os/tasks/_template/ticket.md`.
- Raw scaffold: `src/relay/commands/create.py` → `scaffold_task()`
  in `src/relay/scaffold.py`.
- Interview skill: `relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md`.
- Validator: `relay validate` command (wherever it lives in `src/relay/`).
- Canonical reserved frontmatter names live in
  `relay-os/contexts/relay/architecture/SKILL.md`.
