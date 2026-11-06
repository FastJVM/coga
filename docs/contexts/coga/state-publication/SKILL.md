---
name: coga/state-publication
description: Which Coga files publish to control and when, eligibility, avoiding publication before review, control versus feature checkouts, how lifecycle commands reconcile a ticket with fresh control before changing it, the strict `coga run publish-state` recipe, and recovering a failed publication.
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

- **Lifecycle commands** first reconcile the ticket with freshly fetched
  control ([prepared ticket transactions](#prepared-ticket-transactions)),
  then publish their own task write with an attributed message as soon as
  the write, log line, and notification are final.
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
  checkout ([coga/checkouts](../checkouts/SKILL.md)). Ordinary managed agent
  startup publishes its prepared lifecycle, branch linkage, and launch audit
  together before execution. [Launch publication boundaries](launch-boundaries/SKILL.md)
  owns the commit bound, counting interval, and paths with separate deadlines.
- **Session teardown**, including `coga chat`, publishes the log after usage
  capture. The agent's final answer precedes this write, so its claim of a
  clean checkout cannot cover the usage record. Log publication requires the
  file to be included or already on control; an excluded log (for example an
  ignored, untracked `log.md`) is a reported failure. Failed or skipped
  publication adds a session-end warning naming the retained log, alongside
  the Git diagnostic. Usage keeps the agent's actual result; a direct chat's
  failed checkout return has the command-level result specified by
  [chat checkouts](../checkouts/chat/SKILL.md). Explicitly disabled
  Git keeps its usual informational note instead of that warning.
  A stateful launch or megalaunch session publishes its ticket with that
  log, from the invoking process and so outside the child's sandbox, after
  the child exits for any reason and before the supervisor rereads the
  ticket to chain. A lifecycle write the child could not publish (for
  example because its Git object store was read-only) lands then. If control
  already holds those exact bytes, that confirmation is recorded as this
  checkout's provenance with no new commit. Nothing is replayed, and a
  refused ticket still lets the log publish. Bootstrap and guided-authoring
  sessions publish only the log.
- **Guided authoring** (`coga ticket`) publishes its launch line before the
  session starts, as `coga chat` and launch do, so an attended session never
  holds the log dirty. At the end it validates every surviving authored
  ticket, including siblings edited during `coga ticket <slug>`, before
  publishing any part of **one** guarded transaction with the changed
  context, skill, workflow, and config files. An existing named target is
  validated even when unchanged; canceling or deleting it does not hide
  sibling edits. Deleted ticket and attachment paths and both sides of a
  file-to-directory promotion are included, with no deleted body to validate.
  Selection compares file content and mode with the interview's entry
  snapshot. Untouched files are excluded even if already dirty, including
  attachments beside an edited ticket. A previously dirty file edited again
  is selected in full: the snapshot identifies files, not authorship of hunks.
  An authored change to the Git destination (`[git]` enabled, remote, or
  control branch) refuses. Ambiguous ticket identities, such as both shapes
  left by an incomplete promotion, also refuse. Validation or publication
  refusal keeps edits on disk, exits non-zero, withholds the command's sweep, and identifies the
  retained roots and recovery command. Resolve the reported problem before
  retrying the interview or using [strict publication](#strict-publication-on-demand).
  The transaction covers finalization only: earlier lifecycle commands and
  their sweeps may already have published state. An authorized cancellation
  stands; recovery never replays or rolls it back. The ordinary sweep can
  still publish entry dirt after successful finalization.
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
- **Ordinary managed startup** appends activation, start, and launch audit
  inside its startup publication, before switching or spawning. A failed or
  interrupted group retains its evidence with a withheld-sweep report; no
  startup line is deferred through the agent session to its eventual bump.
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

Publication reads working files independently of the index. Before staging
landed files to advance the local control checkout, it proves the existing
index for the entire selected set: each entry must equal HEAD or the landed
revision, including its mode. A distinct staged draft, deletion, rename, or
union-log version is preserved; no selected path is staged or rewritten and
local control is left behind. With a remote, working state may already have
published successfully; that does not make the staged version disposable.
Without a remote, inability to advance the only durable control ref is a
publication failure. This safeguard applies to every publication caller,
including lifecycle commands during a chat, not only chat teardown.
Reconcile the retained versions under
[checkout recovery](../checkouts/launch-boundary/SKILL.md#checkout-recovery).

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

**Committed-state boundary.** On a feature or detached checkout, clean
committed files stay with the branch except for the configured task directory
and log. The task directory includes materialized `tasks/recurring/` periods
and their attachments. Files under the configured recurring directory wait
for merge as whole files: template definitions, scripts, parent blackboards,
and siblings such as `retires.md`. This covers additions, edits, deletions,
renames, and repeated sweeps after control reverts an earlier publication.
Contexts (including relocated ones), skills, workflows, and shared config
also wait for merge. A clean control checkout still recovers hand commits
of eligible files anywhere in the roots.

**Pre-review publication hazard.** The sweep and guided authoring run from
whichever checkout invoked them. A feature or detached checkout's *dirty*
files in the roots — ticket prose, log, recurring template (including
`ticket.py`), context, skill, workflow, or shared config — land on control
before review. Staged but uncommitted files are dirty too. Commit an edit you
want reviewed before running a sweeping command and keep that file clean:
a later runtime blackboard write makes the whole template publishable,
including any committed definition changes in it. A clean committed sibling
still waits for merge. Dirty runtime writes to recurring blackboards and
machine-written siblings continue to publish normally.

Committed state is adopted only when control still holds a version this
checkout was based on. If control has moved on, reconcile with current
control before retrying. A clean copy merely behind control is never
republished.

## Prepared ticket transactions

Every lifecycle command — `bump` (including completion and human rewinds),
each `mark` verb, `block`, `unblock` (each `--all` answer too), `owner`, and
autoclose's merged-PR completion — reads control before deciding. It fetches
the control branch, reads that ticket's control copy, and reconciles it with
this checkout's copy *before* checking eligibility, gates, or the supervised
step, deriving messages, or writing anything:

- **No local edit** — the local copy equals the newest copy this checkout
  provably shares with control: control's copy is used, from a feature
  branch, a detached HEAD, or a control checkout that cannot fast-forward
  alike. Nothing switches branches or touches other files or the index.
- **Only one side changed** — that side's version is used. A local pause,
  blocker, or deliberate rewind is kept even though it is not progress.
- **Both changed** — frontmatter merges per key (the frozen workflow is one
  value) and the body, blackboard included, by a three-way text merge. When
  both moved the lifecycle, the demonstrably later position wins whole:
  `draft` < `active` < `in_progress` < terminal, then the higher step under
  an unchanged workflow. A terminal winner carries no step.
- **Cannot reconcile** — overlapping prose, different edits of one metadata
  value, a control copy deleted after it was shared, no provable shared copy,
  or a status pair the ordering cannot rank (`paused` or `blocked` against
  another status, `done` against `canceled`). The command exits 75 before
  writing, logging, notifying, or ending a session; both copies stay intact,
  no conflict markers are written, and the sweep is withheld. Save or
  reconcile your local edits, take control's copy with
  `git checkout <remote>/<control> -- <path>`, redo the edit, and retry. An
  unrankable status pair also asks a human through a review PR (below).

The shared copy is chosen from this checkout's HEAD copy, the HEAD/control
merge-base copy, and the copy this worktree last published, counting only
copies control's own history carried and taking the one it carried most
recently. An unpublished feature-branch commit of the ticket is therefore a
local edit, not a base.

The command then validates and edits that reconciled view, writes it once
(exit 75 if the local file changed since it was read), and publishes it
against the exact control bytes it read. Another checkout changing the ticket
in between is refused, never merged a second time; an unrelated control
commit uses the ordinary push retry. A retryable failure (for example a
read-only object store in an agent sandbox) remembers that expectation in
the machine-local `.coga/pending-publication.json`: the session-teardown
retry and the sweep publish that ticket only against it, and a refused one
waits until its copy matches control or another lifecycle command reconciles
it.

If the fetch cannot run, or the remote has no control branch, the command
says so and works from the local copy with today's guarded publication; a
cached remote-tracking ref is never treated as fresh. Git-disabled, non-Git,
and no-control checkouts are unchanged, and without a configured remote the
local control branch is canonical. Launch, megalaunch, and recurring keep
their stricter exact-byte, launch-generation, and lease checks instead of
merging.

## Human review of status conflicts

An unrankable status pair is a decision only a human can make, so the
refusing lifecycle command also opens a pull request asking for it. This is
the one place Coga opens a PR outside a ticket's workflow; it is not that
ticket's implementation PR.

- **Title and target.** `Human Review needed: <ticket slug> — lifecycle merge
  conflict`, based on configured control. The description lists the
  conflicting fields and the base, local, and control copies (each truncated
  past 18,000 characters).
- **Head.** A branch `coga/human-review/<slug>-<key>` holding this checkout's
  copy, committed on top of the control commit that introduced the shared
  copy and built without touching the checkout, its index, or its branches.
  Merging it into control shows the real Git conflict.
- **Identity.** The key hashes the ticket path with the base, local, and
  control blob ids, so every checkout meeting the same conflict finds the
  same PR. An open PR is reused and its URL reported; an existing branch is
  never pushed again, so human edits on it survive. A changed control or
  local copy is a different conflict and gets its own PR.
- **No workflow linkage.** No `Closes ticket:` footer, no `## Dev`
  `branch:`/`pr:` line, and the ticket's own workflow is untouched.
  `bootstrap/resolve-conflicts` and `bootstrap/address-pr-comments` report
  these PRs as `skipped-human-review` and leave them for the human.
- **Unavailable.** When GitHub, its auth, the network, or the push fails, the
  command still refuses as above and says no review PR was created; it never
  reports one that does not exist.

The command exits 75 in every case. Resolution comes back through the next
lifecycle command in the refusing checkout, which remembers the PRs it opened
in machine-local `.coga/human-review.json`:

- **Merged** — control's copy is the human's resolution. An unchanged local
  copy adopts it; edits made locally after the PR was opened merge onto it
  three-way, with the PR's copy as the base. Once that ticket is written,
  control's copy is recorded as this worktree's provenance and the record is
  dropped. A merge that kept control's copy unchanged is recognized from any
  checkout, because the conflict key still matches.
- **Closed unmerged** — the command refuses again and opens no new PR; take
  control's copy and redo the edit.
- **Open** — the command refuses again and reports the same PR.

Taking control's copy by hand ends the conflict, and the record with it; a
review PR still open is then the human's to close.

## Strict publication on demand

The sweep cannot tell its caller whether a file landed. A handoff that hands
files to someone else's fresh clone runs `coga run publish-state [--message M]
[PATH...]` instead. It fetches the configured remote control branch (or uses
local control when no remote is configured), then publishes eligible changes
under the roots and requires each named file to be on control. It uses the
same dirty/committed selection as the sweep: naming a committed feature-branch
knowledge edit, including a recurring file, does not make it publishable.
An excluded file must already match control, including its mode, or the
recipe refuses before publishing accompanying task/log writes. Merge that
reviewed edit first if the recipe refuses it.

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
[trim-log recovery](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/trim-log/operations.md).

Size exception: eligibility, publication deadlines, and recovery stay together so an operator can determine both what a failed command retained and how to publish it safely; launch accounting lives in its own leaf.
