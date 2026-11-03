---
name: coga/recurring/templates
description: How to author or promote a recurring template — fields, parking, the template-to-period transform, first-firing behavior, cross-run state surfaces, and the ticket.py completion and reporting contract.
---

# Recurring templates

A template is a ticket-format **definition** (frontmatter plus run body) with
optional siblings: a repo-local `coga/recurring/<name>/ticket.md`, or a
bundled job in the installed package's `templates/coga/recurring/<name>/`.
Its cross-run state, the blackboard below `<!-- coga:blackboard -->`, always
lives in the repo at `coga/recurring/<name>/ticket.md` (see [selection and
state](#selection-and-state)). A local non-underscore directory with a valid
`schedule:` is live; rename `foo/` to `_foo/` to park it (the scanner and
validation skip it). There is no starter directory — copy an existing template.

The template owns its job's behavior and run procedure. Shared machinery stays
in contexts; reusable process stays in skills. Keep job-specific maintenance
in supporting files beside the template and link them for reading when needed,
with the persistent template path: periods do not copy supporting Markdown.
The ownership rule is [coga/knowledge](../../knowledge/SKILL.md).

## Selection and state

One effective catalog (`recurring.iter_template_sources` and
`resolve_template_source`) serves every consumer: scans, clone scans, named
launch, `coga recurring list`, status and `coga validate`. Per job name it
reports the selected definition, its origin (`local` or `package`), its
selection status, and the repo-local state directory separately.

Activation is chosen in the repo-owned `coga/recurring/jobs.toml`:

```toml
[jobs]
dream = true          # local definition if present, else the bundled one
skill-update = false  # disabled: local or bundled
```

- `true` enables the local definition if present, otherwise the bundled one;
  a `true` entry naming no definition is an error.
- `false` disables either. A sweep (including `--force`) does not schedule
  it and a named `coga recurring launch` refuses with the path and remedy.
  An already materialized period keeps its ordinary lifecycle.
- No entry (or no file): a local definition keeps today's activation; a
  bundled-only job is available but not selected. A job added by a package
  upgrade therefore stays off until selected. State alone never selects.
- Invalid TOML, unknown keys, invalid names, non-boolean values and
  unreadable selection files (including dangling links) are configuration
  errors, reported rather than guessed. A broken selection never restores
  local-only activation.
- A parked `_name/` parks the job, bundled fallback included, regardless of
  selection; its state moves with the directory. An active local definition
  beside a parked one, or state in both, is an ambiguous configuration and is
  reported.

`coga init` writes the file once for a fresh repo; nothing refreshes it. An
existing repo keeps working unchanged after an upgrade; to move its stock
copies onto the package, follow the reviewed
[migration and rollback procedure](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/package-definitions-migration.md).

**Resolution is by artifact, not by merging text.** A local definition owns
its whole directory: a local `ticket.md` with no `ticket.py` is agent-backed
(omission does not inherit the packaged script), so copy every sibling a
customized job needs. A package-backed job keeps only a **state-only
carrier** at `coga/recurring/<name>/ticket.md`:

```markdown
---
{}
---
<!-- coga:recurring-state -->

<!-- coga:blackboard -->
...saved blackboard...
```

The shape is exact: definition fields or prose above the fence in a marked
file, or an unmarked ticket with no `schedule:`, are errors, never a quiet
fallback. Only recognized runtime state (`retires.md`) may sit beside a
carrier or alone; a `ticket.py` or runbook beside a carrier is an incomplete
fork to repair, not an inherited file. An empty or cache-only directory
counts as absent. The first admitted repo-scoped run creates the carrier
once from the packaged definition's initial blackboard, before snapshotting
`state_keys`; listing, status and validation never create it, and existing
state (even an empty region) is never reseeded. Initialization and existing
state lookup validate the parent under the shared state lock, including direct
writers. The first carrier publishes with its period and ledger, pinned to
control's absence; retries preserve a competing writer's complete state.
`coga.recurring_state` owns
this classification; writes always target the repo path, never the package.

## Fields

- `schedule` — required 5-field cron. Missing or malformed: the sweep skips the
  template with a warning and a summary entry; `coga validate` reports
  `invalid-recurring-schedule`.
- Execution is **deduced, never declared**: a reserved sibling `ticket.py` means
  a deterministic phase runs first; no `ticket.py` means agent-backed. There is
  no `mode:` field; a leftover `recipe:` key is inert. A `ticket.py` template's
  step still says `assignee: agent` — that is the agent a hybrid run falls
  through to, not an error.
- `scope` — `repo` (default) or `clone`. A clone-scoped template runs its
  `ticket.py` in every clone with no period task; it requires `ticket.py` and
  rejects `delegate`, `state_keys` and `workflow`. The transform, promotion
  and cross-run surfaces below are repo-scope only. See
  [scheduling](../scheduling/SKILL.md#repo-scope-and-clone-scope).
- `delegate: bootstrap/<name>` — optional, mutually exclusive with `ticket.py`;
  see [delegation](../delegation/SKILL.md).
- `workflow` — optional; none means the one-step `direct/body` workflow, which
  runs the body's ordered phases (Dream is the canonical case). Any workflow an
  ordinary task can resolve is allowed; there is no recurring-capable registry.
- `title` (else the humanized name), `owner`, `agent`, `contexts`, `secrets` —
  passed to each period task. `agent` omitted means the repo default agent.
  A template meant for other repos leaves `owner:` and `agent:` empty so each
  repo's defaults apply; an explicit `agent:` naming a type the repo lacks
  blocks period creation even with a launch override.
- `run_when_inactive` — optional boolean, default false; exempts the template
  from the [repo inactivity gate](../scheduling/inactivity/SKILL.md). The shipped
  `autoclose-merged`, `branch-sweep` and `trim-log` opt in. Non-booleans are template
  errors, reported by the sweep (inactive or not) and `coga validate`. On an inactive sweep, a template without the exemption is
  skipped without strict validation, so its other errors wait until the repo
  wakes or `coga validate` runs. The field stays on the template and is never
  copied to a period task.
- `state_keys` — list of parent-blackboard keys a run must advance (see
  [coga/period-task](../../period-task/SKILL.md)).
- Rejected: top-level `slug`, `human`, `assignee`, `watchers`
  (`bad-recurring-template`, before any period is created or reused) and
  `period_generation`, which is creator-owned period state.

## The template-to-period transform

Each firing goes through the ordinary task creator. It:

- creates directory-form at `recurring/<name>` straight to `status: active`,
  freezing the workflow and selecting the main agent as activation would;
- copies the body above the fence verbatim and starts a fresh blackboard. Only
  `## Description` and `## Context` are composed into the prompt, so keep every
  other heading in the run instructions at `###`; a stray top-level `## `
  ends the Description there (one inside a fenced example is text, not a
  heading);
- appends `coga/period-task` to `contexts:` (idempotently, always);
- freezes `delegate:` and stamps a fresh `period_generation`;
- copies only the reserved `ticket.py` from the selected definition; other
  siblings stay with the definition (the package's directory for a bundled
  job), so instructions name supporting files by their resolved location;
- writes a `state_keys` snapshot when keys are declared.

Ticket-level `skills:` and repo extension-field values are not copied into a
period task; put process skills on workflow steps. `coga validate` resolves
every step skill of each template and compiles its `ticket.py` before a period
exists.

## Promotion

`coga recurring promote <task> --schedule "<cron>" [--name <name>]` moves a task to `coga/recurring/<name>/ticket.md` —
also the "recurring from creation" path (`coga create`, write the body,
promote). The body above the fence travels verbatim; the blackboard resets to
cross-run state. `status`, `step`, `period_generation` drop; a frozen workflow
collapses to its name (none stays none); `title`, `owner`, `agent`, `contexts`
(minus `coga/period-task`), `secrets` and extension fields pass through;
ticket `skills:` drop with a warning. Directory-form attachments are copied
except `.state-snapshot.json`. It refuses: an existing destination, a bad cron
or name (checked before anything moves), an unresolvable workflow, and an
`in_progress` or `blocked` task. The template is reloaded before the source is
deleted.

## First firing is retroactive

The scan takes the schedule's last firing strictly before now. A new template
has no ledger line, so its first sweep services the most recent past firing —
an annual template enabled in September runs for last March. There is no
seeding field. Keep it parked with `_` until after the intended firing, or
write the body to no-op on an already-handled period. Never `coga mark
canceled` an unwanted run: a canceled task at the stable path blocks the
template until deleted.

## Cross-run state surfaces

The period task and its blackboard are deleted each period. Durable output goes
to one of: the template blackboard (cursors, `state_keys`); a machine-written
template sibling in a fixed shape (`autoclose-merged/retires.md`, owned by
`src/coga/retire_worklist.py`, `merge=union`, CAS-written; rules in the
`coga/autoclose/sweep` skill); or one-line facts in `coga/log.md`. The schedule
high-water mark lives only in the log
([ledger](../scheduling/SKILL.md#periods-and-the-serviced-period-ledger)).
The [autoclose template's upgrade guide](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/autoclose-merged/operations.md) owns worklist setup for older repos.

## `ticket.py` completion and reporting

The script runs as `[sys.executable, "<task>/ticket.py"]` with no operands and
must close its own step: shell out to `coga bump` / `coga mark done` (via
`python -m coga.cli`, not the Typer function), or `coga block` for a missing
prerequisite. Chaining is specified in [coga/script-tickets](../../script-tickets/SKILL.md).
Outcomes: closed step — done, no agent; non-zero exit — period stays
`in_progress` and the sweep reports it; **exit 0 with the step open hands the
same period to an agent**, which an unattended sweep cannot run — the commonest
authoring mistake. Exiting non-zero to keep a period visible works but fails
every sweep until fixed; `coga block` records the ask instead.

The period blackboard (`COGA_TASK_BLACKBOARD`, `task_env.blackboard_from_env`)
is a per-run report surface: it reaches the sweep's run record and any autofix
`run-log.md`, then is deleted. Successful runs owe no report. On a non-zero exit
or escaping exception, `runner.run_recipe` appends a `## Recipe Failure`
section (recipe, exit, task, stderr tail) because the sweep discards child
stderr; shims call `run_recipe(load_config(), "<name>", [])` for that reason.
Do not duplicate that write; add structured detail on top. Never write secrets.

The `COGA_TASK_*` variables a script and recipe receive are specified in
[coga/script-tickets](../../script-tickets/SKILL.md).

A script writes either blackboard through the fence-aware API only:
`coga.taskfile.read_blackboard` / `replace_blackboard`, or
`coga.blackboard.append_blackboard_report` / `append_to_section` — never
`open(path, "a")` or a whole-file rewrite. Pass the captured `expected_bytes`
to detect concurrent change, preserve the region's leading newline, and if the
file ends at the fence with no newline, start your text with one (those helpers
do not add it). Own only your keys ([coga/period-task](../../period-task/SKILL.md));
test both orderings and repeated alternating writes against the other writers.

The trim-log maintenance job has one narrow cross-parent write: before deleting
history it may migrate phone-home's valid schema-1 cursor to schema 2 without
sending, minting an identity or advancing `run`. The joint guarded publication
preserves all unrelated parent content; subsequent trims only read the cursor.
The [phone-home ticket](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/phone-home/ticket.md)
owns migration and unread movement semantics.
