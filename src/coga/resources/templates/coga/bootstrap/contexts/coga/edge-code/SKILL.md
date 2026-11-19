---
name: coga/edge-code
description: Wheel-owned edge implementations, repo shims, upgrades, and explicit local forks.
---

# Using wheel-owned edge code

## Wheel-owned edge implementations

Default implementations of some edge jobs ship as the `coga_edge` package in
the **same distribution** as `coga`: one version, one install and upgrade,
no extra dependency, registry or CLI. Repo shims select the implementation.

A `ticket.py` shim may import a stable module `main` and return its exit
code. The bundled recurring definition ships the shim in the package (init no
longer seeds a repo copy); recurring creation copies the selected
definition's shim bytes into each period. On the next
process invocation it uses the installed implementation, even if the template
script later changes or disappears. The shim contains no job logic or duplicate
completion. A missing module is an ordinary script failure, never a fallback.
Installing a wheel does not discover or rewrite repositories. Legacy full
copies adopt the shim once through the
[reviewed migration procedure](edge-code-upgrades.md); until then they retain
their old code. Local overrides still need reviewed repo edits for Markdown,
schedules, workflows and shim contracts. Package-backed definitions instead
follow package upgrades for future periods; existing frozen periods stay intact.

Ordinary Python attachments have the same shipping option: a worker has a
direct module entry point invoked explicitly by instructions, or a plain named
attachment shim. Only the reserved `ticket.py` participates in automatic
execution and recurring copying. There is no general dispatcher or additional
attachment discovery/copying.

Default period tasks freeze the shim, not its imported implementation. Retain
the exact wheel artifact/hash and repo revision for reproducibility; a version
string alone cannot distinguish unreleased main-branch builds. Running
processes are not promised hot upgrades.

### Explicit local forks

A full implementation replacing either template or period `ticket.py` is
repo-owned. A template fork is a full local override: the job's `ticket.md`
and its siblings in `coga/recurring/<name>/`, never a lone `ticket.py` beside a
state-only carrier (an incomplete fork that is reported, not inherited). New periods copy the template fork; existing periods retain their
own script. Neither installation nor launch overwrites, merges or bypasses it.
Editing a wrapper that still imports the default is not an implementation fork.
A fork stops receiving upstream fixes and must remain compatible with the
shared core it imports; restoring the stock shim rejoins wheel updates.

Phone-home's module is self-contained, so a copy of the single file works as
a local fork. The migration procedure includes source inspection and copy
commands; do not run production telemetry to find its source.

Dream's Phase 1 and 5 workers (`coga_edge.validate_drift`,
`coga_edge.cleanup_orphan_markers`) are ordinary attachments of this kind:
the packaged Dream body runs them as `python -m coga_edge.<worker>`. Each
imports only the standard library, Coga's own runtime dependencies and shared
`coga` infrastructure — never another `coga_edge` module — so a full local
Dream fork copies the module beside its `ticket.md` and points that
phase's command at the copy. The [upgrade procedure](edge-code-upgrades.md)
ships the exact old, new and fork passages.

The blocker-reminders, skill-update and autoclose recurring jobs
(`coga_edge.blocker_reminders`, `coga_edge.skill_update`,
`coga_edge.autoclose`) are self-contained the same way. Their packaged shim
calls the module's `main`, which runs `runner.run_entry`: report, publish, and complete the step only when launch
named that task as its script. A hand run (`python -m coga_edge.<module>`)
never advances a task. A copy of the module over a template or period
`ticket.py` is therefore a full local fork that still completes its step. The
[upgrade procedure](edge-code-upgrades.md#recipe-backed-recurring-shims)
covers shims written while these jobs were registered recipes.

Report command tickets ship complete scripts under `bootstrap/`, rather
than import wrappers in `coga_edge`. Copy the whole selected directory to
`coga/bootstrap/<name>/` for a local fork, including any helpers. Removing
that override restores package updates.

## Audit retention adoption

Fresh init selects the weekly trim-log job with default-on 30-day retention.
A wheel upgrade alone enables no new schedule in an existing repo. After
upgrading every writer, use the feature-specific `python -m
coga_edge.trim_log --install` with the upgraded CLI's interpreter; it records
the selection and attribute rule instead of copying definitions. Follow the
[adoption and recovery guide](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/trim-log/operations.md)
for the exact command, allowlist, customization/parking checks and compatible
two-phase rollout. The command writes only this feature's selection and attribute.

## Forking the megalaunch command

The complete queue policy is the single `coga_edge.megalaunch` module. Copy
`bootstrap/megalaunch/ticket.md` and the module itself into the repository as
`coga/bootstrap/megalaunch/{ticket.md,ticket.py}`. Locate their installed source
with the CLI interpreter, without running the queue:

```python
from pathlib import Path
from shutil import copyfile
import coga_edge.megalaunch as queue
from coga.paths import packaged_template_path

local = Path("coga/bootstrap/megalaunch")
local.mkdir(parents=True, exist_ok=True)
copyfile(packaged_template_path("bootstrap", "megalaunch", "ticket.md"), local / "ticket.md")
copyfile(queue.__file__, local / "ticket.py")
```

Run from the host repo root (adjust the destination for a root-layout Coga OS).
The copied implementation imports shared core, never the installed edge module.
Edit selection, ordering, budgets or summary locally and invoke the same aliases.
Wheel upgrades leave the fork unchanged; it stops receiving upstream queue fixes
and must remain compatible with shared core. Removing the complete local
override rejoins packaged definitions and wheel updates. Restoring the stock
shim beside a local ticket also selects the installed implementation again.
The discover/copy command is being delivered separately; this manual full-copy
route exposes the same complete implementation in the meantime.

## Forking the slack command

`coga slack` uses the same full-copy route: copy `bootstrap/slack/ticket.md`
to `coga/bootstrap/slack/ticket.md` and the `coga_edge.slack` module file (not
the shim) to `coga/bootstrap/slack/ticket.py`, then edit operands, message
format or route selection there. The fork must keep the help-marker refusal
([coga/script-tickets](../script-tickets/SKILL.md#stateless-command-help-and-interrupts)).
A forked FYI cannot complete a session: script isolation clears the done
sentinel, and stateless completion stays `coga mark done bootstrap/<name>`.
