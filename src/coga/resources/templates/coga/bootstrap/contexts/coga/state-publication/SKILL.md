---
name: coga/state-publication
description: Which Coga files publish to control and when, eligibility, avoiding publication before review, control versus feature checkouts, the strict `coga run publish-state` recipe, and recovering a failed publication.
---

# Publishing Coga state

Coga state becomes durable on the configured control branch (`origin/main`
by default). The markdown on disk is always the write; publication only
carries it there.

Coga state and templates use UTF-8. Coga text writers emit LF on every platform,
including tickets, log lines, blackboards, config and local run records.
Readers accept LF and CRLF. Atomic replacement preserves POSIX modes on POSIX;
on Windows it leaves the new file writable instead of copying POSIX mode bits.
An existing Git checkout may use CRLF through its own attributes or configuration;
publication uses Git's clean-filter semantics while transaction guards retain
their exact-byte comparisons. Coga does not change user-repo line-ending policy.

Git paths use forward slashes on every platform. Publication preserves working
file modes on POSIX. On Windows, where executable bits are not filesystem
metadata, it preserves tracked files' Git index modes and gives new files mode
`100644`; checkout-return proofs use the same modes.

## The Coga roots

Everything in the Coga root and the configured contexts root publishes
automatically — tickets, the log, recurring templates, skills, workflows,
shared `coga.toml`, `context.md`, and contexts. There is no separate
knowledge PR for files inside these roots: instruction edits there land
directly, and Git history is the visible record and the correction
mechanism. A human may still choose a PR for a change they want reviewed;
this is an automatic publication boundary, not a permission barrier against
explicit Git commands.

The roots are the configured Coga directory and contexts directory, with a
nested root counted once. When a launch moves the contexts root, its return
publishes the old-path deletions, new files, and config together.

**Eligible** means a regular file Git does not ignore. Every consumer asks Git
(`status`, `ls-files --exclude-standard`), so `coga.local.toml`, `.coga/` run
records, generated agent-skill views, caches, and other ignored artifacts stay
local and are never force-added. Untracked symlinks discovered through a
directory pathspec are skipped; explicitly named or tracked symlinks and paths
with symlinked ancestors are refused before reading their working bytes. Root
membership is lexical: a directory link never adds its target to the
publication scope. Submodules are refused, including a dirty, staged, or
removed gitlink. Source outside the roots, including the packaged copies
under `src/`, is ordinary code: it reaches control only through a branch and
reviewed PR.

## When Coga publishes

- **Lifecycle commands** publish their own task write with an attributed
  message as soon as the write, log line, and notification are final.
- **The end-of-command sweep** runs after most commands that change state,
  succeed or fail, and publishes every dirty eligible file under the roots,
  plus eligible committed changes (see below). Read-only commands
  (`status`, `show`, `validate`, `usage`, `--help`, `launch --prompt-report`)
  never sweep, and neither do `init` and `uninstall`. The sweep is best-effort: a failed push is
  reported on stderr, the files stay as written, and the next command retries.
  A command that deliberately leaves retryable state dirty, or a launch whose
  checkout preparation or return refused, withholds its sweep so that state
  is not published. At exit, a changed log is checked for lines control does
  not hold, even after a sweep (which may have excluded an ignored log).
  The warning names up to 10 retained lines, counts any others, and gives the
  recovery command; it reports those lines rather than publishing them beside
  withheld state. After a checkout rewrite, the check can also name older
  retained lines. An unchanged log or explicitly disabled Git stays silent.
- **Launch** publishes routine state at entry and before returning the
  checkout ([coga/checkouts](../checkouts/SKILL.md)).
- **Session teardown**, including `coga chat`, publishes the log after usage
  capture. The agent's final answer precedes this write, so its claim of a
  clean checkout cannot cover the usage record. Log publication requires the
  file to be included or already on control; an excluded log (for example an
  ignored, untracked `log.md`) is a reported failure. Failed or skipped
  publication adds a session-end warning naming the retained log, alongside
  the Git diagnostic. The agent's exit result stands. Explicitly disabled
  Git keeps its usual informational note instead of that warning.
- **Guided authoring** (`coga ticket`) publishes its launch line before the
  session starts, as `coga chat` and launch do, so an attended session never
  holds the log dirty. At the end it publishes the authored tickets and
  every changed context, skill, workflow, or config file under the roots in
  **one** guarded publish. An authored change to the Git destination (`[git]`
  enabled, remote, or control branch) refuses. A refused or failed publish
  keeps every edit on disk and `coga ticket` exits non-zero.
- **Ordinary manual edits** inside the roots publish through the next
  command's sweep. Local prompt composition still reads local edits.

### Every log line has a publisher

Each `coga/log.md` write is published before its command exits, by the
lifecycle sync, an explicit log sync, or the end-of-command sweep, or else its
command reports it. Failure records (`sync failed`, `sync refused`, `refresh
failed`, `post failed`) are written because a publication or delivery failed;
the failure report covers them, and no command retries them in a loop. The
deliberate deferrals are:

- **Initialization** commits the onboarding creation line with the new
  scaffold; the first push is deliberately left to the human
  ([init](../init/SKILL.md)).
- **Session usage records** land after the agent's last lifecycle sync and
  publish at session teardown (above).
- **Lines in a writer's own later publish.** A recurring run's serviced-period
  ledger lines and a launched `ticket.py`'s exit line ride its recurring
  publication, the next checkout settlement, or the end-of-command sweep.
- **Retained state.** A retained-state exit (75), a withheld sweep, and a
  `bump --to`/`--backward` rewind skip the sweep on purpose. Their lines
  stay local with the state they describe, and the exit names them.

## Control versus feature checkouts

A **control checkout** (HEAD is the control branch) stays clean and level:
each publish fast-forwards it, or realigns it when its local-only commits are
Coga state that publication has already put on control. Local commits
touching anything else, state not yet on control, or an in-progress Git
operation leave it alone with the remedy.

When Git refuses a control fast-forward because local changes or untracked
files would be overwritten, the stderr note includes the first 10 paths
from each overwrite refusal, followed by a count of any omitted paths. The
paths stay with their error heading so the operator can identify what blocks
the move. Filename whitespace is preserved.

A **feature or detached checkout** publishes the same way but keeps its
published ticket and log dirty by design. `coga status` warns when control is
ahead of the local copy. Never `git add` `coga/tasks/**` or `coga/log.md`
into a PR; `coga open-pr` excludes that state from its cleanliness gate and
refuses a branch whose only commits are Coga state.

**Pre-review publication hazard.** The sweep and guided authoring run from
whichever checkout invoked them. A feature checkout's *dirty* files in the
roots — ticket prose, log, recurring template (including `ticket.py`),
context, skill, or workflow — land on control before review. Committed ones
on a feature branch stay with the branch unless they are routine task, log,
or recurring state, so commit an edit you want reviewed before running a
sweeping Coga command in that checkout.

Committed state is adopted only when control still holds a version this
checkout was based on. If control has moved on, reconcile with current
control before retrying. A clean copy merely behind control is never
republished.

## Strict publication on demand

The sweep cannot tell its caller whether a file landed. A handoff that hands
files to someone else's fresh clone runs `coga run publish-state [--message M]
[PATH...]` instead. It fetches the configured remote control branch (or uses
local control when no remote is configured), then publishes eligible changes
under the roots and requires each named file to be on control. It uses the
same dirty/committed selection as the sweep: naming a committed feature-branch
knowledge edit does not make it publishable. Merge that reviewed edit first
if the recipe refuses it.

- **Exit 0**: every named file is on control (landed now or already
  matching), listed on stdout; or `[git].enabled = false` leaves no control
  branch, which stdout says.
- **Exit 1**: refused, failed, uncertain, not a repository, or no control
  branch. Files stay as written, stderr names the cause, and a task run
  records a `## Recipe Failure` section on its blackboard.
- **Exit 2**: bad arguments, or a named path that is not a regular file
  inside the roots, before any publication write.

The recipe never runs the exit sweep, so nothing publishes tickets
separately from a required context it refused. Paths resolve against the
current directory; anchor them at the checkout root.

## Recovering a failed publication

A failed best-effort publication keeps the local write, and the transition it
recorded has already happened: rerunning `bump` (or any lifecycle command)
would advance again, never republish. Recover with the strict recipe, from
the same checkout, once Git can write where the failure said it was writing
(including an external object directory). The failure report names the
command, run from the Coga root it prints: `coga run publish-state <ticket
file> <log>` after task sync (a directory-form task names its `ticket.md`),
`coga run publish-state <log>` after log-only sync, or the no-path form after
the sweep or a deletion (a deleted path is not a valid argument, but the
recipe publishes it anyway). Requiring the retained log prevents an ignored
file from being silently skipped again by recovery. It adds no
transition, an immediate repeat is a no-op (`already on`), and while access
is still denied it exits 1 with the files kept. Coga never changes
permissions, sandbox configuration, Git environment routing, or object
storage to recover; restoring access is the operator's call
([coga/sandboxes](../sandboxes/SKILL.md#restricted-sandboxes)).

### A stranded log tail blocking catch-up

A log append left by an earlier command can block `main` from fast-forwarding
over newer remote log entries. The event-aware publisher preserves concurrent entries
during publication, but does not let Git overwrite an uncommitted file.
[Recurring catch-up](../recurring/scheduling/SKILL.md#variants) can identify an
isolated tail and offer the strict recipe as a remedy. Ordinary launch already
attempts state publication before preparing its checkout.

Review the pending changes first. From the affected workspace, run
`coga run publish-state /absolute/path/to/coga/log.md` and require exit 0
before retrying catch-up. The named path requires the log to land; it does
**not** restrict publication to that file: all eligible Coga state is swept.
Inspect any intervening changes before running it. This keeps concurrent
remote and local lines without hand-editing the audit trail or replaying the
chat. Recovery is offered rather than performed at recurring admission:
append-only bytes do not establish who wrote them or authorize publishing
other pending work.

## Audit mutations and retained recovery

Ordinary log publication preserves control's event order and merges new source
events. Missing source events are not a deletion request. Expired incoming
replays can be ignored only with exact reachable Git-history evidence and the
current protected state; a backdated timestamp alone proves nothing. Checkout
return and unpublished-log diagnostics use the same disposition. The stock
`/log.md -merge` makes competing native Git edits conflict visibly; the retire
worklist's union behavior remains separate.

Explicit deletion requires an exact preimage/postimage and whole-event receipt.
All append and replacement paths take the same reentrant checkout state lock.
An interrupted trim retains a temporary local Git receipt: ordinary publication
and checkout return refuse until the compatible trim script resolves it against
fresh control. A stateful script with this receipt propagates exit 75 without
settlement. Do not replay lifecycle commands or discard the receipt. Follow
[trim-log recovery](https://github.com/FastJVM/coga/blob/main/coga/recurring/trim-log/operations.md).
