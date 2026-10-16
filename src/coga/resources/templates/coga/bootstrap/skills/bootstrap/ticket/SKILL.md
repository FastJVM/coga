---
name: bootstrap/ticket
description: Create or edit Coga tickets and maintain their blackboards using the annotated template; run the guided interview when invoked through the ticket editor.
---

# Write a ticket

Read [template.md](template.md) for the annotated ticket shape and optional
fields. Use the exact task path supplied by the session. Ordinary tickets are
`tasks/<slug>.md`; use `tasks/<slug>/ticket.md` when attachments are needed.
The template explains the format; `coga create` scaffolds actual drafts.

For `coga ticket`, megalaunch’s draft editor, or a direct
`bootstrap/ticket` launch, follow [interview.md](interview.md). That procedure
handles the greeting, interview, evaluation, and human approval. Reading this
skill during implementation or for a routine edit does not start an interview
or grant permission to change lifecycle metadata.

## Editing boundaries

For ordinary edits, change `contexts`, body prose, and the blackboard only.
Other frontmatter belongs to CLI commands and humans; the guided interview
has its own explicit authoring exception. Preserve field order and formatting,
and write lists one item per line. Never invent fields. `coga/log.md` is the
CLI-written audit trail; do not edit it.

Read the latest ticket before writing. Scope edits to the intended region;
never locate the blackboard fence by substring, since prose may quote it.
For programmatic edits use `taskfile.read_blackboard` / `replace_blackboard`
and the concurrency contract in `coga/blackboard`. Reconcile with control
before publishing; `dev/checkouts` owns which checkout holds the live ticket.

## Working notes

Keep the body describing the current task, and keep decisions, reasons,
verification, next actions, and blockers in the live blackboard. Rewrite
current values in place. Preserve resolved blocker records; `coga unblock`
records their resolution. The template documents optional linkage fields.

Authoring scratch (`## Evaluator review`, `## Ticket authoring notes`,
`## Proposals`) is synthesized into the body before launch. At the end of a
guided draft interview, retain superseded designs and reset the rest to the
stock blackboard. For an existing non-draft ticket remove only the authoring
sections used by that interview, preserving working notes. A live workflow’s
review is handoff state, not leftover draft scratch.

## Design changes

Rewrite the body for the current direction. Preserve abandoned plans below
the fence in one `## Superseded designs` section, appending oldest first:

```markdown
## Superseded designs

### YYYY-MM-DD — <abandoned direction>

Superseded by: <current direction or decision>
Reason: <why the ticket pivoted>

<prior plan and evidence worth retaining; copied headings at #### or deeper>
```

Keep enough to reconsider the old plan. Launch includes only a pointer to
this section, so keep reasons still needed for current work in live notes.
The body may carry one short history pointer. Do not scatter old plans under
alternative headings or leave Git as their only explanation.

## Oversized blackboards

For a live ticket with a size warning, move dated evidence to sibling
attachments (promote a file-form ticket to directory form if needed). Begin
each attachment with an HTML comment naming the task and move date; leave a
same-named section with a pointer in the blackboard. Keep the current handoff,
worklist, and verification live, and keep `## Dev` and `## Blockers` in place:
CLI readers do not follow attachment links. Material several tickets need
belongs in an unattached context. Record before/after prompt-layer sizes.
Move history; do not delete it to meet a limit.

Do not trim a done ticket: without a live recorded checkout it belongs to
Dream’s retro pass; with one it is retirement debt (`coga/dream`). Do not
manually trim sections a recurring writer replaces on every run; route the
size decision to that writer’s owner. Period tasks preserve only their own
keys (`coga/period-task`); durable gotchas and parent-template state must
survive before the period blackboard is deleted.

## Citing code in `## Context`

Code facts copied into `## Context` are read days or weeks later, against a
tree that has moved on. Cite them in the form that survives that:

- **Cite module plus symbol, never a bare line number.** Write
  `git.sync_task_state` or `step_gate.gate_unmet_reason`, not
  `src/coga/git.py:214`. Line numbers drift within days; one ticket's cold
  evaluator counted nine stale citations against source ten days newer, one
  pointing at the wrong module entirely.
- **When a range genuinely helps, name the symbol first and mark the range
  as an aid** — `git.sync_task_state` (near line 700 as of this writing) —
  so a reader hunting through a 7,000-line module still has a starting
  point, and knows the number is expected to rot.
- **State the relationship that makes the fact load-bearing, not its
  coordinates.** "The gate-checked copy and the synced copy are the same
  `TaskRef`, so they cannot disagree" survives a refactor; "see line 87"
  does not. The relationship is what the implementer actually needs.

This is the same rule `code/review-design` applies to evaluator findings.

The same holds for a ticket cited in `## Context`: copy the substance this
task needs, and cite the slug only for provenance. Retro and `coga retire` may
delete it first. When the source is already gone, recover its body with the
retired-task recipe in `coga/tickets/discovery` (`Where tasks live and how they are
named`), which also searches the pre-rename `relay-os/tasks/` tree.

## Verification

After structural edits, run `coga validate --json` and address errors caused
by the edit. An ordinary writing session does not start or advance a ticket;
workflow transitions remain the current step’s responsibility. Guided
interviews finish with their own cleanup and handoff in `interview.md`.

Implementation contracts remain in `coga/tickets` (file schema and body
parsing), `coga/blackboard` (blackboard parsing, readiness, and concurrent
writers), and `coga/workflows` (workflow gates). Read them when changing those
mechanisms, not merely to fill in a ticket.
