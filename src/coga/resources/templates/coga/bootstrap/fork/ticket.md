---
title: Find and fork packaged behavior
---

## Description

Command ticket for the `fork` and `fork-copy` verbs, and the owner of their
contract. It has no agent phase: launch runs the sibling `ticket.py`
([coga/script-tickets](context:coga/script-tickets)). It creates no task and
writes no blackboard.

Two default aliases fix the dispatch policy; the kernel infers nothing:

- `fork = "launch --read-only bootstrap/fork -- inspect"` reports where a
  behavior is defined and implemented, and where a local override would go.
  [Read-only dispatch](context:coga/launch) runs it with no configured user,
  no TTY, and dirty files, and publishes nothing; the script itself writes
  nothing, imports no job implementation, and runs no job or agent.
- `fork-copy = "launch bootstrap/fork -- copy"` copies **one** packaged
  definition to its local override location. It runs through ordinary
  launch, so the usual end-of-command publication applies.

One alias cannot carry both a read-only and a write policy, which is why
there are two. Both accept `--json` and `--help`.

### Targets

A typed ref: `workflow:<ref>`, `skill:<ref>`, `context:<ref>`,
`bootstrap/<name>` or `bootstrap:<name>`, `recurring:<name>`,
`resource:<name>`, `task:<slug>`. An untyped word resolves, in order, as an
effective alias (defaults merged with `[aliases]`), a built-in command, a task
ref, then a definition name of exactly one kind. An unknown or ambiguous
target exits 1 and lists what was checked on stderr. Refs must be relative,
using slash-separated names without empty, `.` or `..` components, Windows
drives, backslashes or colons; invalid refs refuse before resolution or copying.

An alias reports its expansion and follows it: `launch bootstrap/<n>` to the
bootstrap ticket, `recurring launch <n>` to the recurring job, `launch <slug>`
to the task, `run <recipe>` to a kernel recipe, and any other head to a kernel
primitive. Built-in commands and `coga run` recipes are reported as **kernel
primitive (not an editable ticket)** with their package module; they are never
forkable.

### What `coga fork` reports

For each definition: kind, ref, selected origin (`local`/`package`), selected
path, packaged path, local override destination, and fork state:

- `stock` — nothing local;
- `fork (identical to installed package)` / `fork (modified)` — compared with
  what `coga fork-copy` would write from the installed package, so a wheel
  upgrade turns an unedited fork into `modified`;
- `local only` — no packaged counterpart;
- `broken: <reason>` — the resolver's own refusal. Never a silent fallback to
  the package text.

References follow with their own resolution: a workflow's step skills (with
each step's `checkout:`); a bootstrap or recurring ticket's `workflow`,
`skills` and `contexts`; a recurring job's selection and state carrier.

A `ticket.py` is classified by parsing it with `ast`, never importing it:

- **edge shim** — only imports `main` from `coga_edge.<module>` plus a
  `__main__` guard that only calls `main()` (optionally through
  `raise SystemExit(main())`); the implementation is the installed module file;
- **recipe adapter** — calls `coga.runner.run_recipe` with a literal name;
  the implementation is that kernel recipe, not forkable here;
- **full script** — anything else; the script is the implementation.

An edge module is parsed the same way. Its `coga.*` imports are shared-core
dependencies a fork must stay compatible with. A `coga_edge.*` or relative
import, or a missing `__main__` guard, makes it **not completely forkable**,
with the cause named.

`task:<slug>` separates what the ticket froze (workflow name and steps with
`checkout:`/`assignee:`/`requires:`) from what resolves live at launch (step
skills, ticket skills and contexts, sibling `ticket.py`). The live workflow
file is reported as not used by the frozen snapshot.

Exit 0 when nothing reported is broken; 1 for an unknown target or any broken
definition (the report still prints); 2 for usage errors. Text goes to stdout,
diagnostics to stderr.

### What `coga fork-copy` does

1. **Resolve one definition.** A typed ref, or an alias reaching one bootstrap
   ticket or recurring job. Task refs, kernel primitives, refs with no
   packaged definition, and refs already selected locally refuse with exit 1
   and write nothing.
2. **Plan the copy** to the resolver's local path: workflow
   `workflows/<ref>.md`; skill `skills/<ref>/`; context
   `<contexts root>/<ref>/` (honours `[layout] contexts`); bootstrap
   `bootstrap/<name>/`; recurring `recurring/<name>/`; resource
   `resources/<name>`. Executable attachment bits are preserved on POSIX; the local copy keeps
   repository write permissions even when the installation is read-only.
   Runtime caches and nested definitions (a child
   directory holding its own `SKILL.md`) are not copied.
3. **Refuse conflicts before any write**, listing every existing destination
   entry. The one exception is a recurring parent holding a valid state-only
   carrier: its `ticket.md` becomes the packaged ticket above the blackboard
   fence followed by the carrier's blackboard byte-for-byte, and runtime state
   (`retires.md`) stays. An incomplete parent, a parked `_<name>/`, or both
   refuse.
4. **Expand an edge shim.** When the packaged `ticket.py` is an edge shim
   whose module is completely forkable, the fork's `ticket.py` is the module
   source: the real implementation. Otherwise the shim or adapter is copied
   unchanged and the output says `implementation not forked: <reason>`.
5. **Write siblings first and the definition file last**, each atomically, so
   an interrupted copy leaves a definition-less directory the resolvers
   already reject as a broken override.
6. **Report** the files written, what to edit, a `coga fork-copy` command for
   each referenced definition that is still stock, a recurring job's resulting
   selection (a local definition with no `jobs.toml` entry is enabled;
   `<name> = false` under `[jobs]` keeps it off), and the return-to-stock steps.

Fork-copy never edits `jobs.toml` or config and never writes under the tasks
root: existing, running and parked periods keep their frozen script.

### Return to stock

Printed by `coga fork` for every fork:

- workflow or resource: delete the local file;
- skill, context or bootstrap: delete the local directory, keeping any nested
  definition directories it holds;
- recurring: replace everything above the blackboard fence in `ticket.md` with
  the exact carrier header from
  [coga/recurring/templates](context:coga/recurring/templates), keep the
  blackboard and runtime state, and delete the other siblings. Frozen periods
  keep their own script until they finish.
