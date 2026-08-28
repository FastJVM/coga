---
name: coga/recurring
description: How Coga's recurring task system works — recurring tasks as ticket-format directories under coga/recurring/, the creation contract, period-task naming, and where last-run state persists. Attach to any ticket that adds or changes a recurring task.
---

# Recurring tasks

Recurring tasks are machine-authored jobs that re-create on a schedule.
Each one re-runs every period; `coga recurring` turns due ones into real
per-period tasks.

## A recurring task is a ticket-format directory

A recurring task lives under `coga/recurring/<name>/` and has the same
shape as any task directory:

- `ticket.md` — YAML frontmatter (`schedule`, `title`, …) plus the
  run body. This is the recurring task's definition.
- the **blackboard region** (in `ticket.md`, below the
  `<!-- coga:blackboard -->` fence) — **persists across every run.** This is
  where a recurring task stores last-run state.

Append-only run history is not beside the template: `coga recurring` adds a
line to the repo-global `coga/log.md` (tagged `recurring/<name>`) each time
it creates a period task.

Templates deliberately live outside `tasks/`. Anything holding a `ticket.md`
under `coga/tasks/` *is* a task — discovered, status-carrying, launchable —
with no exceptions, and a template is none of those: it carries no `status:`,
is never launched directly, and must survive across periods. Its instances
are the opposite — ordinary tasks the scanner deletes and recreates each
period. Keeping the two in separate directories keeps the task-tree invariant
exception-free (no "unless it's a template" branch in status, validate, or
megalaunch) and makes the instance path itself the marker: the `recurring/`
prefix under `tasks/` says "machine-generated, safe to reap and regenerate",
which is what licenses the scan to replace a prior-period `done` task and
Dream's retro pass to direct-delete finished period tasks without a PR. A
hand-authored task never gets that treatment.

A directory whose name starts with `_` is inert — the scanner skips it. That
is how you park a live template without deleting it: rename `foo/` to
`_foo/`. There is no starter template directory; the whole mechanism is
"non-underscore directory under `coga/recurring/` with a `schedule:` in its
`ticket.md`", and the frontmatter shape is documented in this context (see
the example under "Extend recurring with a task-specific workflow").

- `coga recurring` (bare) — the public command head translates
  `--interactive`, `--force`, and `--agent` into ordinary argv for the fixed
  `recurring-scan` recipe and invokes it through `coga run`. There is no
  bootstrap target or `COGA_RECURRING_*` argument channel. The recipe scans
  every recurring task,
  get-or-creates the stable instantiated task at
  `coga/tasks/recurring/<name>/`, records the current period as a
  `created|reused <task-ref> for <period>` line in the repo-global
  `coga/log.md`, and launches the ones
  still `active` or orphaned `in_progress`. **Launch order is phased, not
  alphabetical:** the
  cleanup template — Dream, the recurring janitor (see below) — is sorted
  **last** so its retro pass acts on the period tickets the *same* sweep just
  drove to `done`, instead of trailing them by a full sweep. Among the
  non-cleanup templates the existing order holds — orphaned `in_progress`
  resumes first, then fresh launches, each most-overdue first — and a resuming
  Dream orphan still sorts last (cleanup-after-the-rest wins for the janitor
  itself). Invoke it directly from whatever operator-owned scheduler exists
  outside Coga. A current-period task
  left `in_progress` by a sweep whose supervisor died mid-run (laptop sleep,
  SSH drop) is **relaunched from its frozen period ticket**, not skipped:
  ordinary agent work re-composes from `step:`, while a frozen `delegate:`
  re-launches that bootstrap target. If an interactive launch returns
  unfinished, the sweep pauses it before continuing, so a frozen `in_progress`
  period task can still mean "dead run's orphan" rather than "human parked it".
  `done` from the *current* period (finished work) and `paused` (a human
  parked it) stay skipped. A `done` run left over from a **prior** period —
  finished but never reaped by Dream's retro pass — is **deleted before a
  fresh task is created** from the current template. The new task starts
  `active` at workflow step 1 with a fresh blackboard, a re-baselined state-key
  snapshot, and an advanced serviced-period record; reactivating a terminal
  task would preserve stale run instructions and residue. A live
  stale leftover under `tasks/recurring/<name>/` is resumed before any new
  period work for that template; there is only one instantiated path per
  template. Dispatch is always frozen with that materialized task: a copied
  `ticket.py` selects deterministic work, a copied `delegate:` selects a
  one-hop bootstrap agent launch, and neither means the ordinary period-task
  agent session. Direct `coga launch recurring/<name>` obeys the same snapshot;
  it never re-reads mutable template dispatch. A task carrying `ticket.py` runs
  that file as a subprocess from the host repo with the period ticket's scoped
  secrets and freshly derived `COGA_TASK_*` metadata; no prompt is composed and
  no agent starts.
  The launcher marks `active → in_progress` before starting and then leaves
  the workflow alone: the script closes its own step (`coga bump`), exactly as
  an agent does. A non-zero exit halts the launch, leaves the task unfinished,
  and stops the sweep after reporting it.
- `coga recurring --force` — ignores schedule and status filters and attempts
  the real period task for every template, reactivating `done` and `paused`
  runs. A `canceled` task remains terminal: the runner reports a controlled
  refusal for it, continues through later templates, and exits non-zero after
  the sweep. Deleting that canceled period task is the explicit prerequisite
  for a fresh run.
- `coga recurring --all <path>` — discovers every Coga repo below an explicit
  parent directory, pruning dependency/tool-state and `_`-prefixed directory
  trees, and runs the ordinary due sweep in each configured target,
  sequentially. A missing local `user` or another intentional Coga config guard
  makes a scratch checkout an unconfigured non-target: these are omitted from
  dispatch, summarized once by count, and do not make the parent fail. Each
  selected repo runs in a fresh CLI process so its config, launch supervision,
  and end-of-command git sync stay repo-local. TOML parse errors and failures
  after dispatch are reported without preventing later repos from running; the
  parent command exits non-zero after the sweep. `--force` may be combined with
  `--all <path>` to force every template in every selected repo. The owner gate
  below applies per repo: repos owned by someone else are skipped and named in
  the summary, and the sweep continues rather than failing.
- `coga recurring launch <name>` — creates one named recurring task now,
  ignoring its schedule. `<name>` is the directory name. Unless
  `--interactive` is set, the launched REPL receives the same concrete
  `idle_timeout` / `max_session` limits the scheduled sweep would pass, so the
  in-process launch path never relies on Typer option sentinels.
- `coga recurring promote <task> --schedule "<cron>"` — turns an existing task
  into a recurring template. See "Dropping a new recurring task" below.

`ticket.md` frontmatter fields:

- `schedule` — a 5-field cron string. **Required**; a recurring task without
  it (or without `ticket.md`) is skipped with a stderr warning and an entry
  in the run's Slack summary. `coga validate` also checks it statically and
  reports a missing or malformed cron as an `invalid-recurring-schedule`
  error, so a template that would silently never fire fails validation
  instead of surprising you at the next sweep. A parked `_`-prefixed
  directory is exempt — it is inert by design.
- there is no `mode` field and no `recipe:` field. Execution is **deduced**:
  a template that carries the reserved sibling `ticket.py` is deterministic;
  one that does not is agent-backed. Agent templates need a TTY and run under
  the REPL supervisor; `ticket.py` templates run headlessly. A leftover
  `recipe:` key from the old format is inert — it selects nothing and is not a
  validation error.
- `delegate` — optional `bootstrap/<name>` command-ticket ref, mutually
  exclusive with a `ticket.py` sibling. It does not select deterministic-vs-
  agent execution — that stays deduced from the file. It declares *which*
  stateless bootstrap target an agent period hands its work to, which no
  file's presence can express. The template's period is then serviced by
  launching that target rather than by an agent session on the period task:
  the runner preflights push access for the materialized period (the stateless
  bootstrap target would otherwise self-skip that gate), fully preflights and
  composes the bootstrap launch, then publishes `in_progress` as an exact
  compare-and-set before announcing the start. The materialized task carries a
  creator-owned `period_generation:` token that changes on every supported
  rematerialization; the lease covers that bounded witness plus the exact
  ticket bytes without rereading the unbounded global audit log. Launch then
  reloads config and target state and
  redoes every preflight and composition step because start publication may
  integrate a newer control tip. Immediately before spawn, the runner requires
  that same ticket-plus-generation lease, `in_progress` status, and frozen
  delegate on control. Any concurrent terminal transition, replacement, dispatch
  change, ticket edit, or new generation refuses the spawn. The launch remains
  in-process — in the operator's own terminal, under the sweep's `--agent`
  override, selected queue session conduct, and idle/max-session liveness
  bounds — and the
  period task reaches `done` only when the bootstrap target emits its done
  sentinel. After the child exits, completion and watchdog pause consume the
  same generation lease as another exact compare-and-set; an older child's
  result can never mutate a replacement at the stable path. A natural/crashed
  exit fails with the period left retryable; a multi-task sweep pauses a
  watchdog timeout and continues only after that pause is verified on control.
  A stale or failed pause refuses the run; a named launch fails and leaves it
  `in_progress` for retry. At final spawn admission the runner also freezes the
  exact parent recurring ticket named by the period's state snapshot and
  verifies that input on control. Completion consumes the same parent lease in
  its strict publication, so a concurrent parent/cursor edit refuses instead
  of being overwritten, and the child's cross-run cursor update cannot remain
  local while the period reaches `done` on control. If the digest spool is
  installed, the completion event is
  appended first and joins that transaction; a live notification waits until
  publication succeeds. Strict lifecycle publication unwinds an unaccepted
  local feature/control commit before restoring runner-owned files. If a push
  reply is lost, it probes the exact control candidate across every effective push
  destination: confirmed acceptance succeeds, while disagreement or any other
  unprovable outcome refuses and retains generated local state for explicit
  reconciliation rather than manufacturing a split.
  Creation copies the
  target into canonical period-task frontmatter; sweep retries, named retries,
  and direct `coga launch recurring/<name>` route only from that frozen field,
  re-read from the durable period after launch reconciliation, so changing a
  template or refreshing/replacing a task cannot reroute live work from stale
  scan state. The direct spelling is also the normal readiness signal: a
  paused/draft delegated period activates inline before its guarded start;
  scheduled and named recurring scans continue to leave paused work parked. A materialized
  period that later acquires its own `ticket.py` is invalid and refused rather
  than choosing between the two dispatch signals. Because the delegated run is
  still an agent launch, a delegating template stays in the agent-backed
  admission class: a headless sweep refuses it *before the period task is
  created*, exactly like any other agent template. The target itself must also
  be agent-backed: a bootstrap `ticket.py` target is rejected before creation,
  because deterministic recurring work belongs in the template's own
  `ticket.py`. `coga validate` checks both the template and frozen task.
- `period_generation` is runner-owned materialized-task state, not a template
  input. The creator stamps it once per new stable-path generation; templates
  or ordinary tasks that declare it are rejected rather than accepting a stale
  or forged lease identity.
- `title` — the created period task's title (else the humanized name).
- `workflow` — optional. A template that names none creates with the
  one-step `direct/body` workflow, which runs the ticket body's ordered
  phases directly as the prompt; Dream is the canonical example. (The task is
  still workflow-carrying and bumpable — `direct/body` is the workflow.)
- `owner`, `assignee`, `watchers`, `contexts`, `secrets` — passed through to
  the created period task.

## Recurring runs start on the control branch

Every launching entry point requires the configured control branch to be
checked out before it reads or writes period state: the bare sweep, `--force`,
`coga run recurring-scan`, `coga recurring launch <name>` (including aliases
such as `coga dream`), and direct `coga launch recurring/<name>` for a frozen
delegating period. A refusal names both the current branch and the configured
control branch and tells the operator to switch branches. There is deliberately
no override: `--force` bypasses schedule and status filters, not the branch
gate.

The outer sweep gate checks only the local branch. Its initial fetch or rebase
remains a warning for bare and named interactive single-repo scans, but a remote-backed
period is admitted with its exact ticket bytes and creator-owned period generation
before the first child starts, then refreshed again immediately before its own
launch. That narrow per-child check resolves only the exact task ref, fails
closed if remote-backed control cannot be verified, and skips a task removed,
replaced, or changed to `done`, `canceled`, or `paused` while an earlier child
was running; an offline operator therefore cannot start new remote-backed
period work from a stale scan snapshot, and a removed ref cannot alias a prefix
sibling. A Git checkout with no configured remote freezes that local-only class
at outer admission and uses its exact local control state; if a remote existed
at admission but disappears before a later child, the child refuses instead of
silently changing classes. Every
ordinary period launch also returns its exact ticket-plus-generation lease: the
refreshed admission lease for a deterministic `ticket.py` child, recaptured
immediately before every agent spawn only after the bounded token, launchable
status, and full ticket snapshot still match the work just composed. A parked,
closed, advanced, or otherwise edited same-generation ticket therefore cannot
run a stale prompt. If either child exits
unfinished, the sweep compares that bounded token, which stays stable across
the child's ticket edits and launch/usage audit appends but changes when the
path is materialized again. Only the same
generation gets a fresh exact lease, and the pause is rendered from those newly
leased bytes so a concurrent same-generation edit is preserved; a replacement
refuses teardown instead of parking the task now occupying the stable path. The
direct `coga launch recurring/<name>` spelling requires a verified catch-up
**before resolving the local ref or reading dispatch** whenever a remote is
configured; a remote-backed control checkout whose fetch or integration fails
is refused before any work starts, while a Git checkout with no remote uses
local `HEAD` as its only control state. It then reloads configuration and
resolves the refreshed period so a remotely materialized task, integrated
completion, or replacement wins. A bare sweep and
`coga recurring launch <name>` perform their full public admission once at the
outer boundary; the typed in-process seam rechecks branch/owner plus only the
latest period state before each ordinary child rather than re-entering the
whole public launch path. Delegated children use their stricter exact
ticket-plus-generation control lease instead, and any transport failure while
confirming or publishing that lease refuses the child. The
unattended `coga recurring --all <path>` child keeps its stricter existing
precondition: it must also fetch and integrate the latest remote control tip
before scanning. Repos with `[git].enabled = false` and workspaces outside a
git checkout have no Coga-managed control checkout, so the branch-only gate
does not apply to them. Only a confirmed non-git workspace self-skips: a Git
inspection failure refuses rather than silently treating the checkout as
unmanaged.

The control-landing path for recurring state still handles a create made on a
feature branch. Normal recurring commands no longer reach that case, but the
logic remains valid for repos mid-upgrade that already have feature-branch
state to land; a later cleanup may remove it once that migration case expires.

## One operator owns recurring: the `owner` gate

A repo may name a recurring owner with a top-level `owner = "<name>"` in the
**committed** `coga.toml`. With it set, every launching entry point — the bare
sweep, `--force`, `coga run recurring-scan`, `coga recurring launch <name>`,
and direct launch of a frozen delegating period — refuses to run for any
operator whose machine-local `user` (in `coga.local.toml`) differs, naming the
owner so they know who to ask. Leave `owner` unset and recurring is ungated,
exactly as before, so a repo opts in by naming someone.

Authorization does not trust the config object loaded when the command started
or an uncommitted working-tree edit. It fetches the configured control branch
through a command-scoped ref and reads `owner` directly from that exact commit's
`coga.toml`; a stale local control checkout can predate an owner addition or
transfer, and its working tree can carry an uncommitted takeover. Checkout-wide
`FETCH_HEAD` is never an authorization source. The lookup fetches from the
remote's sole effective **push** URL — the repository `git push <remote>`
actually writes the period state to, which git distinguishes from the fetch URL
— and refuses a remote with several push URLs, because state spread across
destinations has no single owning repository to authorize against.

Only a checkout with **no configured remote** falls back to reading `owner`
from local `HEAD`. `[git].enabled = false` does not qualify: it is the sync
opt-out documented for a remote-less repo, and letting a machine-local,
uncommitted setting decide would make it a silent override of committed
policy — a stale clone would read no owner at all, and a former owner would
stay authorized after a transfer, while the sweep still created period state
and launched real work.

The `--all` parent uses the same
control-tip value before duplicate-checkout selection; if it cannot confirm the
value, it dispatches the child, whose existing mandatory freshness gate fails
before any period state is touched. An owner addition or transfer therefore
takes effect on the next reachable sweep instead of a stale clone continuing
under the old name. A locally owner-less repo keeps the pre-gate best-effort
behavior while its remote is unavailable; once the local config has opted in,
an apparent owner cannot launch offline because a transfer could be waiting
upstream.

Why: a sweep mutates shared period state (the created period task, the
serviced-period record in the repo-global log) and then launches real work.
Two *different* operators sweeping the same repo from their own clones race
each other, and the same period gets launched twice. Naming one owner in
committed config is the cheapest thing that closes that: every clone reads the
same name.

This is a **policy gate, not a lock.** Same-machine overlap is already
prevented by the sweep being sequential and foreground; the owner running two
of their own clones concurrently can still race, and the gate does not try to
stop them. There is deliberately no override flag — `--force` forces the
*schedule and status filters*, not the gate — so taking recurring over is an
explicit, reviewable change to the committed `owner`. Read-only
`coga recurring list` and the non-launching `coga recurring promote` stay
ungated.

## Dropping a new recurring task

Two paths, both landing on the same thing — a non-underscore directory under
`coga/recurring/` whose `ticket.md` carries a valid `schedule:`.

- **Author it.** Create `coga/recurring/<name>/ticket.md` by hand (copy an
  existing template, or the example in the next section), then
  `coga validate --json`.
- **Promote an existing ticket.** `coga recurring promote <task> --schedule
  "0 9 * * 1"` moves `coga/tasks/<slug>` (either on-disk shape) to
  `coga/recurring/<slug>/ticket.md`. This is also the "make it recurring at
  creation time" path: `coga create` the ticket, write its body, then promote
  it. `--name` overrides the template directory name (it defaults to the
  task's leaf slug); directory-form attachments travel with the ticket.

What promote does to the ticket, and why:

- The body above the blackboard fence travels verbatim — the `## Description`
  is what each period task runs.
- The blackboard is **reset**. A task blackboard is one run's scratch; a
  template blackboard is durable cross-run state (run cursors). The old
  text stays in git history.
- `status:`, `step:`, `slug:`, `human:`, and `agent:` are dropped — per-run and
  per-launch fields the creator re-derives for every period task. `title`,
  `owner`, `assignee`, `watchers`, `contexts`, and `secrets` pass
  through. A frozen `workflow:` snapshot collapses back to its name so the
  creator re-freezes it each period; a ticket with no workflow stays that way
  and creates with `direct/body`.
- Ticket-level `skills:` are dropped, with a warning: they are never copied
  into a period task. Put process skills on the template workflow's steps.

Promote refuses rather than guessing:

- An existing `coga/recurring/<name>/` is never overwritten — pass `--name` or
  remove it first.
- The cron is validated before anything moves, so a bad `--schedule` leaves the
  source ticket untouched.
- The transformed workflow name must still resolve. A terminal ticket can
  outlive a deleted workflow definition; promote catches that stale snapshot
  before deleting the source ticket.
- An `in_progress` or `blocked` task is refused: a template cannot hold a live
  run's step or blocker. Land or unblock the run first.

Then `coga validate --json` and, for an explicit first run,
`coga recurring launch <name>`.

## Extend recurring with a task-specific workflow

Yes: recurring templates are not restricted to Dream or the shipped janitor
shape. At materialization time, a template may name any resolvable workflow
that an ordinary task in the repo can use and may attach any resolvable set of
contexts. There is no separate registry of recurring-capable workflows. That
is structural support, not a promise that every workflow shape can finish in a
scheduled sweep; shape the run around the dispatch constraints below.

On each firing, the recurring creator routes the template through the ordinary
task creator. That path resolves and freezes the named `workflow:`, validates
its step-skill and `contexts:` references, copies the template body into the
period task, and appends `coga/period-task` to its contexts. The resulting
`coga/tasks/recurring/<name>/` ticket uses the normal lifecycle, per-step
assignee, blocker, and completion machinery. The sweep selects an explicit
deterministic half before falling back to an ordinary agent launch, and adds
post-launch handling for unfinished runs as described below.

To schedule a task-specific workflow:

1. Define the workflow and any skills or contexts through their ordinary Coga
   paths.
2. Create a non-underscore directory such as
   `coga/recurring/weekly-deliverability/` with a `ticket.md` — copy an
   existing template (e.g. `skill-update/`) or start from the example below.
3. Set the template's `schedule:`, explicit `workflow:`, `contexts:`, and role
   fields, then replace its `## Description` with the per-firing instructions.
4. Run `coga validate --json`, then use
   `coga recurring launch weekly-deliverability` for an explicit real run or
   `coga recurring` for the scheduled sweep.

For example:

```yaml
---
schedule: "0 9 * * 1"
title: "Weekly deliverability review"
workflow: deliverability/weekly-review
owner: nick
assignee: claude
contexts:
  - email/deliverability
  - customers/current-campaigns
---

## Description

Run the weekly deliverability review; this scheduled workflow must reach
`done` in the current launch.

<!-- coga:blackboard -->

The cross-run state for this recurring task goes here.
```

This extension seam has five important constraints:

- **One instantiated task per template.** Every firing uses the stable ref
  `recurring/<name>` at `coga/tasks/recurring/<name>/`. A still-live prior run
  is resumed before new-period work; recurring does not create overlapping
  period tickets or a backlog under different slugs.
- **The period task is fresh each firing.** Its blackboard is scratch space for
  that run and is deleted with the task. Put cursors and other cross-run state
  in the recurring template's own blackboard, optionally naming them in
  `state_keys:` so completion warns when a run forgets to advance one.
- **The deterministic half is one fixed filename, not a plugin table.** A
  template's `ticket.py` is copied into each period task and run as
  `[sys.executable, "<task>/ticket.py"]` with no operands; per-run argv belongs
  on an explicit `coga run` invocation instead. The script owns the whole
  deterministic run *including its own completion* — it ends in `coga bump` /
  `coga mark done`, or records an unavailable prerequisite with `coga block`;
  the launcher never advances the workflow on its behalf. A blocked script
  completion stays `blocked`; a non-zero exit leaves the period task
  `in_progress`.
- **A scheduled agent run must reach `done` in one launch.** When a bare
  `coga recurring` sweep gets control back from an unfinished agent launch, it
  pauses the period task before continuing. That includes an intermediate
  human or unassigned handoff and a task that invoked `coga block`; the paused
  run is skipped by later sweeps and cannot use ordinary `bump` / `unblock`
  from that state. Do not put human gates or expected blockers in a scheduled
  agent workflow. Use the on-demand `coga recurring launch <name>` path (then
  drive the ordinary ticket handoff) or an ordinary task when a run needs
  those intermediate states.
- **Agent work needs a TTY; a `ticket.py` half does not.** An agent-backed
  template needs stdin and stdout TTYs and runs under the REPL supervisor; a
  TTY-less sweep skips it with a warning. A delegating template
  (`delegate: bootstrap/<name>`) is agent-backed for this purpose — its
  delegated run is an agent launch — and is skipped headless the same way,
  including when an `active` / `in_progress` period already exists from an
  earlier attended sweep. Admission leaves that period untouched and continues
  to later deterministic jobs. A template carrying `ticket.py` runs directly
  without a TTY and is the appropriate shape for an unattended scheduler.

The creator performs a deliberate template-to-ticket transform, not an
arbitrary frontmatter clone. Use the recurring fields documented above. In
particular, put process skills on workflow steps: ticket-level `skills:` and
repo-defined extension-field values are not copied from the template into the
period task.

## Last-run state lives in the recurring task's blackboard

Each scheduled firing uses the stable instantiated task path
`coga/tasks/recurring/<name>/`, with its own fresh blackboard. That task
directory is deleted after completion and recreated later, so the run
blackboard does **not** carry over.

So a recurring task that needs continuity between runs (a last-processed
commit SHA, a cursor, a posted/skipped flag) keeps that state in **its own**
blackboard region: the part of `coga/recurring/<name>/ticket.md` below the
fence. The *schedule* high-water mark is deliberately **not** kept there: it
lives in the repo-global log, out of reach of any run that rewrites a
region of this blackboard.

When designing a recurring task that carries cross-run state, name in the
body *which* keys it persists (e.g. `last_commit`, a cursor section). You
do **not** need to re-teach the launched run *where* state lives — the
creator auto-attaches the `coga/period-task` context to every period
task, which carries that rule.

## The creation contract

- **Instantiated task ref** is `recurring/<name>`, backed by
  `coga/tasks/recurring/<name>/`. The `recurring/` directory is the
  identity marker. The period is not in the slug.
- **The repo-global `coga/log.md` is the period high-water mark.** Each
  serviced period appends one `created|reused <task-ref> for <period>` line
  tagged `recurring/<name>`. The period key buckets the firing: hourly →
  `YYYY-MM-DD-HH`, daily → `YYYY-MM-DD`, weekly → `YYYY-Www`, monthly →
  `YYYY-MM`, and schedules outside those four buckets → `YYYYMMDDTHHMM`.
  Bare `coga recurring` validates those exact shapes and their calendar values,
  then compares their normalized calendar positions before creating. A
  malformed record is a template error in the sweep, `coga recurring list`,
  and `coga status`; it never counts as "ran this period." If the newest valid
  record is at or after the current period, that period has been handled — it
  is not re-created and not re-launched. The on-demand
  `coga recurring launch <name>` (and aliases like `coga dream`) bypass this
  skip: it's the explicit override.
- **Why the log and not the template.** A mark in the template blackboard is
  reachable by every other writer of that region. The digest run rewrites
  its `### Digest State` section, which swallowed a mark appended after it —
  and each erasure made the next `coga recurring` delete the completed task
  and repost the digest. An appended line cannot be clobbered that way, is
  union-merged across checkouts, and outlives the task Dream reaps. Dedup
  therefore *does* parse the log, so the line's wording is a contract with one
  writer and one shared parser (`format_serviced_log` /
  `parse_serviced_period_entries`), pinned by a test. Logs are still never
  composed into prompts, so history can grow
  without bloating the next run.
- **The ledger read is bounded to the log's tail.** The log is allowed to grow
  without bound, so repeated same-period scans should not pay for the repo's
  whole history. `read_serviced_ledger` takes the finite mapping of
  `recurring/<name>` refs to the exact periods the caller is deciding, reads
  `coga/log.md` **backwards**, and stops once every ref has a valid record at or
  after its target. The target is the proof for that stop: `merge=union` can
  leave a template's newer record arbitrarily far *above* an older record, so
  neither the first hit nor a fixed slack window can establish the true
  high-water mark. An older hit therefore stays unresolved and a due template
  walks the whole log on the first scan of a new period; after that period is
  recorded, repeated scans resolve from the tail. A malformed record reached
  before the target remains a template error; older unreachable malformed
  history is allowed to heal. When the pre-scan control catch-up succeeds, the
  sweep carries this pre-create result into the control guard as its pinned
  snapshot instead of materializing the same Git blob again. If catch-up could
  not be confirmed and the later best-effort control fetch succeeds, that
  fallback applies the same complete target set to one pinned control read.
- **One shared file, so a sweep pins one snapshot.** Because every template
  records into the same log, the first sync of a sweep publishes records for
  templates it has not synced yet. The cross-checkout "did someone else handle
  this?" check therefore reads control's ledger once per run, before the sweep
  publishes anything — otherwise a template mistakes its own pending record
  for a rival's and deletes the task it just created.
- Period tasks create **straight to `status: active`** — ready jobs, not
  drafts to triage. Because every active task must carry a workflow, a
  template that declares none creates with `direct/body` (it would otherwise
  be un-activatable and `coga validate` would flag it as a stuck task).
- `assignee` defaults to the repo's configured **default agent** when the
  recurring task omits it — never the human `owner`, which `coga launch`
  cannot resolve to an agent type.
- `coga validate` resolves every workflow-step skill referenced by each
  materialized recurring template, before a period task exists. Missing refs
  report the local and bundled paths checked; the removed bundled
  `coga/megalaunch/run` ref instead gives its migration directly: megalaunch
  is on-demand only, so delete the leftover recurring template and workflow.
  Validation compiles a template's `ticket.py`, when it has one, before a
  period task exists.
- The period task's `## Description` is taken from the `ticket.md` body's
  `## Description` section: everything from that heading to the next
  top-level `## ` heading. **Convention:** keep every other heading in the
  body at `###` so the whole run instruction lands in the description.

## REM is user-space recurring maintenance

REM is repo/user-specific recurring maintenance — the place for operational
checks meaningful to this repo, team, or user: product or operations health
checks; customer, email, payment, or deployment follow-ups; repo-specific
context audits; domain-specific recurring reports; reminders that depend on
this repo's tasks and blackboards. A REM task is an ordinary template authored
with the procedure above; it owns its own cadence, ticket scan, skill order,
output conventions, and review gates.

REM is not Dream. Dream is Coga's generic ticket cleanup pass; generic Coga
cleanup does not belong in a REM pass, and neither does branch hygiene unless
the REM task is explicitly a dev maintenance loop. Have each run write one
concise summary to its period task's blackboard, listing any PRs opened,
tickets created, or human gates.

## Dream is the recurring janitor

A finished current-period task normally sits on disk as an ordinary
`status: done` ticket at `tasks/recurring/<name>/` until Dream runs at the end
of the same sweep. Dream's Phase 4 retro pass processes each eligible done
ticket; recurring period tasks normally carry nothing durable — their output was
the notification post or PR they already produced — so Retro direct-deletes them
via `coga delete recurring/<name>` with no PR or marker. *Normally*, not always:
a wrapper run that discovered a reusable gotcha writes it to its own blackboard
(see `## Gotchas`), and that is worth extracting before the delete. Read the
period task's blackboard rather than direct-deleting on class alone.

Checkout-bearing done tickets are deliberately not eligible for Dream. A real
`branch:` or `worktree:` under blackboard `## Dev` preserves the source ticket
and its checkout evidence until a human runs the exact `coga retire <slug>`
follow-up. Dream records those tickets as deferred retirement debt; it neither
duplicates retire's checkout safety proofs nor makes that human-typed cleanup
implicit.

The scheduler is the liveness fallback. If any completed recurring task
survives into a later period, it deletes that stale artifact before creating
the fresh task at the stable path. This is also how Dream's own completed task
is removed: Dream marks itself `done` and stops, then the next firing's scan
deletes that prior-period task before creating the new Dream run. Git history
is the audit trail; the log's serviced-period record remains persistent.

## The autofix loop closes the sweep

Every sweep ends with one analysis call. `coga recurring` used to print what it
did and exit — and under cron that console output is the only place a failing
`ticket.py`, a wedged agent REPL, or a refused forced launch was ever
described.
The output is unchanged; the loop is what got added after it
(`src/coga/recurring_autofix.py`):

1. **The sweep builds a run record as it works** — per period task: how the
   launch ended (clean, timed out, stopped by a failing `ticket.py`, left
   unfinished, refused by `--force`), the ticket's status afterwards, and the
   period task's **blackboard**, plus any template that failed to load. It is
   *built*, not scraped: tee-ing fd 1 would make `isatty` false and every
   interactive agent launch would then refuse itself. The blackboard is read
   instead because it is where a `ticket.py` phase and an agent session both
   already write what they found — the durable report channel, which the
   console is not.
2. **One agent call reads that record** and answers `ok`, `duplicate`, or
   `problem` plus a ticket body. This is the only place Coga spawns an agent
   without a PTY — a one-shot, text-in/text-out call with no REPL and no
   lifecycle. It cannot answer a permission prompt, so it is told not to mutate
   anything; Coga does every write itself.
3. **A `problem` becomes an `active` ticket** under `coga/tasks/autofix/` on
   the `code/with-self-review` workflow, with the run record committed beside
   it as `run-log.md`. The next `coga megalaunch` picks it up; the human gate
   is the workflow's owner PR review, and a finding that turns out to be
   transient closes through the workflow's already-satisfied path.

The loop runs after **every** sweep, including one with nothing due and one
that died partway through — a sweep that failed mid-run is the one most worth
analyzing. On-demand `coga recurring launch <name>` (so `coga dream`,
`coga autoclose`, `coga skill-update`) closes the same loop: it runs a real
template, so a wedge or a failed `ticket.py` there is as worth ticketing as one
in the sweep. A gate that refuses to launch — a closed or human-parked
template, one already handled on control — is not a run and is not analyzed.

That cadence is also why the analyst is told what is already ticketed: the open
`autofix/` tickets go into the prompt so a template that fails every night
answers `duplicate` instead of minting a ticket a night.

Two properties keep a broken analyst from becoming a broken sweep:

- **It never changes the sweep's exit code.** The sweep's return value reports
  on the work it ran; an analyst that times out, exits non-zero, or is not
  installed is loud on stderr and nothing more.
- **It fails toward surfacing.** An unparseable reply is treated as a problem
  carrying the raw text, because the alternative is a broken analyst quietly
  swallowing every failure it was hired to report.

One consequence to keep in mind when writing a `ticket.py` phase: whatever it
writes to the period task's blackboard travels verbatim into the analysis
prompt and, when a ticket is created, into a committed `run-log.md`. Coga never
logs a resolved secret value itself, and a run must not write one to its
blackboard either — that existing rule now has a second reason.

Operating it:

- `COGA_AUTOFIX=0` disables the loop; `COGA_AUTOFIX_TIMEOUT` (seconds) bounds
  the call, which defaults to 300s and disarms at `<= 0`. The bound is on the
  analysis, not on each subprocess inside it: the first attempt, the
  `claude auth status` probe, and the subscription retry share one deadline, so
  the auth fallback below cannot stretch the wait a sweep signed up for.
- Every run record is also written machine-locally to
  `.coga/recurring-runs/<stamp>.md` (gitignored — one operator's sweep
  transcript is not team state), whether or not it gets ticketed.
- `coga run autofix-analyze [<run-log.md>] [--dry-run]` re-runs the analysis
  over a recorded run by hand; with no path it takes the most recent one.
- The argv for the one-shot call is built in for `claude` and `codex`. Another
  CLI needs `[agents.<name>].analyze` in `coga.toml` (e.g.
  `analyze = "-p {prompt}"`); without it the loop skips loudly rather than
  guessing an argv and opening a REPL nobody can drive.
- Claude Code normally honors an ambient `ANTHROPIC_API_KEY`. If that key's
  call fails specifically for authentication or billing, the analyst checks
  for an existing signed-in claude.ai account with the variable removed and,
  when `claude auth status` confirms a first-party Pro, Max, Team, or Enterprise
  subscription permitted by local login policy, announces and makes one
  subscription-authenticated retry. The retry is limited to Claude's built-in
  analysis argv and standard auth routing: a custom `[agents.<name>].analyze`,
  `ANTHROPIC_BASE_URL`, or `ANTHROPIC_CUSTOM_HEADERS` keeps the original failure
  because a bare status probe cannot prove which credentials that call would
  use. A working key remains the first and only call; an API-key-only setup,
  unrelated failure, or other agent CLI never switches authentication.

## Gotchas

- A stray top-level `## ` heading anywhere in the body — including inside a
  fenced code block — truncates the extracted description there. Indent
  example blocks or use `###`.
- Do not store last-run state in the instantiated task's blackboard under
  `coga/tasks/recurring/<name>/` — it is fresh for one run and deleted on
  cleanup. Use the recurring task's own blackboard region in
  `coga/recurring/<name>/ticket.md`.

- **A template whose work is "launch another Coga command" must declare
  `delegate:`, never shell out to a nested `coga launch`.** The two levels are
  easy to conflate, and conflating them reproduces a real bug: the recurring
  supervisor owns TTY admission for the sessions *it* spawns, but that
  ownership does not extend one level down to a launch an agent improvises
  from its own tool shell — `coga launch` refuses an agent launch without a
  TTY on *both* stdin and stdout, and a tool subprocess has neither, so the
  nested launch exits 2. Faking a terminal (`script -qec ...`) is not the
  sanctioned workaround; it was, and agent harnesses refused to execute it.
  With `delegate: bootstrap/<name>` there is no inner shell-out at all: the
  sweep itself performs the delegated launch in the operator's terminal and
  keeps the period task's lifecycle bookkeeping, so no wrapper agent session
  exists in between. The delegated command's own success signal — e.g. its
  `coga slack` roll-up line in `coga/log.md`, which emits the bootstrap done
  sentinel — is the only path to period completion; a natural REPL exit is not
  success. Start, spawn, completion, and timeout are guarded by the exact
  materialized ticket plus its creator-owned period generation, so an old child cannot
  mutate a later period at the same stable path. Delegation is only for an
  agent-backed bootstrap command. If the
  target has `ticket.py`, move that deterministic work to the recurring
  template's own `ticket.py`; Coga rejects the delegate before creating a
  period task rather than relocating admission failure into the run.

- **A job that pushes to a dedicated long-lived branch must prune the remote
  ref before pushing.** `coga skill update --pr` reuses one fixed branch
  (`coga/skill-update`) and pushes it with a bare `git push --force-with-lease`
  (`src/coga/skill_manager.py`), with no fetch first. Once the previous
  period's PR is merged *and its remote branch deleted*, the local
  `refs/remotes/<remote>/coga/skill-update` still points at the old SHA, so the
  lease cannot be satisfied and the push fails with
  `! [rejected] coga/skill-update -> coga/skill-update (stale info)` — exit 2,
  and the period task looks like a real failure. This recurs **every period
  after a merge+delete cycle**, not once. `git fetch --prune <remote>` clears
  the dead tracking ref and the rerun succeeds; pruning is local-only, touches
  no remote state, and is safe to run before retrying. Any recurring job that
  force-pushes a reused branch inherits the same trap.

## What this context does NOT cover

Scheduler wiring, how to write a run's skill or body
logic, and notification posting mechanics (see `coga/sync`). Implementation lives
in `src/coga/recurring.py` and `src/coga/recurring_runner.py`.
