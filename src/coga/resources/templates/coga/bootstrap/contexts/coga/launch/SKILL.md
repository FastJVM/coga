---
name: coga/launch
description: What `coga launch <target>` accepts, a summary of the checkout boundary around each ticket launch, how status and routing decide what runs, the preflight order before any lifecycle write, the step-chaining supervisor's stop rules, and the `--agent`, `--prompt-report`, and liveness options.
---

# Coga launch

`coga launch <target> [args...]` starts or resumes work on one target. It is
the attended path: a human typed it. Queue draining is `coga megalaunch`
([megalaunch](../megalaunch/SKILL.md)); scheduled work is `coga recurring`.

## Targets

`coga launch <task>` opens the current step of a local ticket. A
`bootstrap/<name>` target is a stateless command or discussion ticket.
`recurring/<name>` is a period task with the repo's recurring owner policy.
A frozen recurring delegate routes through its bootstrap target.

Launch works in the invoking checkout. A workflow can use an explicit Git
script to switch branches. [Git](../git/SKILL.md) owns those steps.

## Read-only command dispatch

`coga launch --read-only bootstrap/<name> [args...]` runs one deterministic
bootstrap script against the invoking checkout, including dirty effective local
definitions. An alias can select it (`inspect = "launch --read-only
bootstrap/inspect"`, written on one TOML line). This mode needs neither a
configured user nor an agent or TTY. It still requires valid existing repo
configuration; it never initializes a repository.

Only a bootstrap target with the exact `ticket.py` entry qualifies. Stateful
and agent-only targets refuse with exit 2, as do combinations with `--agent`,
`--prompt-report`, or REPL/internal launch options. A vanished entry refuses;
there is no agent fallback. Arguments remain separate ordered argv elements;
the child inherits stdin/stdout/stderr and runs from the host repository root.
Stdout belongs to the script; Coga errors and alias framing use stderr.

Coga performs no audit, notification, usage capture, skill-view refresh,
checkout preparation/return, fetch, refresh, push probe, publication or CLI
exit sweep, on success or refusal. Declared secrets still resolve before
spawn, with the ordinary scoping/redaction and fresh script environment
([script tickets](../script-tickets/SKILL.md#coga_task_-contract)); outer
completion and assist authority are cleared. One subprocess's exit is the
invocation's result, using the usual process-status convention; zero completes
only this stateless invocation, and 75 also has no refresh or sweep.

This is a cooperative procedure contract, not a Python sandbox: the selected
reader must itself avoid writes, including nested lifecycle commands. A writer
must use ordinary launch. A mixed read/write procedure chooses its invocation
policy before execution, through separate explicit invocations or a thin
argv-parsing adapter calling the same launch API. A read-only entry rejects
write operands; a child cannot upgrade its dispatch policy. Ordinary launch
remains the default and retains its publication and completion boundaries.
The withheld publication is scoped to the read-only call itself: an in-process
API caller gets its own sweep policy back when the call returns or refuses, so
a writer command that reads this way still publishes at its exit.

The shipped report aliases and the `recurring list` adapter use this same
boundary; their owning command tickets define selection and presentation.
Use `--` before script flags so `--help` reaches the report parser. Report
help therefore describes the effective, possibly local, script and needs the
same valid repo configuration: outside a repository, or with a broken
`coga.toml`, `coga status --help` refuses with exit 2 like any other read
(owner decision, 2026-11-16, accepted over a package-only help fallback).

## Status is the signal

Draft and paused tickets activate after readiness checks. Active tickets
move to `in_progress` as execution starts. Terminal tickets refuse launch.

A blocked agent ticket can launch from an attended terminal with the
blocker-resolution preamble. Its status stays `blocked` until an answer is
recorded. A blocked script requires an answer before launching. See
[lifecycle](../lifecycle/SKILL.md).

## Phases and routing

First, launch resolves the current step and any deterministic phase. A step
with `run:` selects that script. Other steps use the ticket's `ticket.py`
when present. The script can advance the step or leave agent work open.
If the step routes to the owner, launch stops at that handoff. An explicit
`--agent` can start a human-step assist, with audit attribution to the
selected agent. [Script tickets](../script-tickets/SKILL.md) and
[human assist](../human-assist/SKILL.md) own the details.

## Agent preflight order

For an agent phase, launch resolves the operator, checks the terminal and
agent CLI, resolves secrets, and prepares the prompt before starting the
session. Windows command packaging and terminal support belong to the
agent executor. Launch and usage audit lines append to the local log.

## The step chain

An advancing script or agent hands the next step back to the supervisor.
It resolves the next executor from the current ticket file. Owner-held
steps, terminal states, blocked states and paused states stop the chain.
Agent sessions also stop on process failure or a liveness limit.

## Run state

A launch provides ignored, repo-local storage for unversioned state under
`<coga root>/.coga/` (`src/coga/run_state.py`):

- `data/tasks/<id_slug>/` (a task) or `data/bootstrap/<name>/` (a bootstrap
  target) is durable and exported as `COGA_TASK_DATA_DIR`. Each carries a
  `.coga-owner` record naming its target, so attribution never depends on how
  task paths nest. Files with unreadable ownership metadata are attributed to
  the nearest readable owner, if one exists. `data/_shared/` holds cross-ticket state; `COGA_DATA_DIR`
  names `data/`. In a linked Git worktree `data/` resolves to the primary
  checkout, so durable state survives `git worktree remove`. Nothing deletes
  durable state automatically.
- `tmp/<token>/` is one launch's temp area. `TMPDIR`, `TMP` and `TEMP` point
  at it, so `mktemp`, Python `tempfile` and most tools land there.
  `COGA_SYSTEM_TMPDIR` keeps the original system temp (inherited if already
  set), and Coga's own short-lived files (per-user locks, prompt files,
  `coga-done-*` sentinels, skill scratch) resolve through it via
  `oscompat.system_tmpdir()`, so locks keep excluding each other across
  checkouts and nothing live is purged.

Every `_launch` (attended, recurring period, delegated) opens exactly one
tmp scope once its config is known and holds it for the whole step chain;
megalaunch opens one per child chain and recurring clone scripts one per
run. Guided `coga ticket` opens one per interview and creates the durable
directory for the selected task, or for `bootstrap/ticket` when no target is
given. A clone script gets `COGA_DATA_DIR` but no task identity. Read-only
dispatch gets a tmp scope but no data variables, creates no `data/`, and
never sweeps. `--prompt-report` and parser-only script help create nothing.
A nested launch creates its own sibling token and never touches its
parent's.

The scope holds an exclusive lock on `tmp/<token>.lock` from before the
directory exists until after it is deleted. When the launch ends, normally,
on failure or on interrupt, it removes its own directory while still holding
the lock, then retires the lock file (POSIX unlinks it while held; Windows
closes, then unlinks). Launch purge and the sweep below also remove
read-only content a tool left in the area (a copied package tree, a Go
module cache): on a permission error they grant the owner write access
to directories inside the area (and, on Windows, to files), never through a
symlink and never changing a POSIX file's mode, and retry once. A removal it
cannot complete warns once on stderr and
leaves the rest for the sweep; it never fails the launch. On POSIX a file a
background process still holds open is unlinked but keeps its disk space
until that process exits.

A launch first sweeps sibling tokens whose lock it can take without blocking,
including lock files with no directory. It claims a lock before removing a
lockless directory older than 60 seconds and rechecks the age under the lock.
On POSIX launch and sweep both verify that the acquired lock still names the
same file. `coga validate`
reports the same orphans read-only as `orphan-tmp`, and only a repo-wide
`coga validate --fix` removes them. A linked worktree created under a
purged tmp area leaves stale metadata that `git worktree prune` clears.

`coga validate` also reports what this storage holds. The report is not an
issue, so a clean repo still prints `All good`. Text output prints
`State: <root> <size>`, then one line per entry with owner, kind, size, file
count and path. `--json` adds a top-level `state` object with `root`,
`data_root`, `total_bytes` and `entries`. An entry's `owner` is an
`<id_slug>`, `(shared)`, `(unattributed)` or `(tmp)`, and its `kind` is
`data`, `tmp-live` or `tmp-orphan`. A `stale-state` warning names a durable
`data/` directory whose ticket is `done`, `canceled` or no longer resolves.
Nothing removes that data, `--fix` included, and deleting or retiring the
ticket leaves it in place, so delete it by hand once it is no longer needed.

If the absolute tmp path exceeds 64 bytes, every launch warns once on stderr
with the path and the ~108-byte Unix socket limit, and still uses it: a
silent fallback to `/tmp` would break the rule. The prompt rule agents follow
is in the base prompt's "Unversioned state" section, including the cleanup
requirement for disposable scratch outside the checkout.

## Options and exits

- `--prompt-report` prints each composed layer, exact refs, bytes, and
  `characters / 4` token estimates without spawning. It refuses a `ticket.py`
  target and never executes ticket code. It refreshes the agent-skill view
  and selects the read-only prompt path, so measuring a prompt never
  publishes the edits being measured.
- `--idle-timeout` / `--max-session` (off by default) tear down a stalled or
  runaway REPL; the launch then exits 124 and does not chain.
- On native Windows the agent owns the console, so idleness cannot be
  measured: an explicit `--idle-timeout` exits 2 before any state change,
  and names `--max-session`.
  Recurring and megalaunch sessions that arm it from defaults or config warn
  once and run with `max_session` only.
- On native Windows, an agent command that no transport can represent exits
  2 before activation, audit or spawn. That means a
  pointer-form command over CreateProcess's 32,767 UTF-16 units (or cmd.exe's
  8,191 for a `.cmd`/`.bat` CLI), or a raw CR/LF in a `.cmd`/`.bat` CLI's
  title, launch option, discussion token or kickoff. The message names the
  limit or argument role, never its value. A prompt too large for the command
  line always falls back to its file pointer instead.
- Refusals exit 2. A nonzero agent or script exit propagates.

The Python launch API, its internal phases, and the shared spawn path are in
[coga-dev/internals/agent-spawn](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/agent-spawn/SKILL.md).
