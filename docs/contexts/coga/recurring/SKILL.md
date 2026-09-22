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
  `done` from the *current* period (finished work) and human-parked `paused`
  runs stay skipped. A watchdog-paused run stays parked but is an unresolved
  failure: every sweep shows `needs attention (watchdog timeout)` with the
  exact resume command, counts it in `problems:`, emits a recurring-error
  notification, and returns non-zero after running other due tasks. This also
  works with no TTY or no other due work, independently of the autofix analyst.
  Provenance comes from the latest pause audit entry's `system:watchdog`
  actor, so existing watchdog pauses are detected without migration. The
  scanner compares audit timestamps (append order breaks same-minute ties),
  and a later human pause or task creation supersedes old timeout evidence.
  It streams the log once only when there are paused periods to classify.
  A `done` run left over from a **prior** period —
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
  secrets and freshly derived `COGA_TASK_*` metadata.
  **`ticket.py` selects a deterministic *phase*, not necessarily a wholly
  deterministic period.** Whether an agent follows is decided after the script
  exits, from the step it left behind — `run_script_chain` in
  `src/coga/launch_script.py` classifies three outcomes. A script that closed
  the last step ends the launch with no prompt composed and no agent started;
  that is the shape every shipped template is written for and the only one an
  unattended sweep can complete. A script that bumped into a step assigned to a
  **configured agent does not hand off there** — `run_script_chain` sets
  `current = after` and loops, running `ticket.py` again for the new step. The
  deterministic phase repeats for each consecutive agent-owned step, and the
  agent is only reached once a phase leaves its step unchanged or the loop
  revisits a step it already ran (`while current.step not in ran_steps`). So a
  script that bumps can execute the next step itself, and can advance past it
  again; a template author must not assume the agent runs the step their bump
  landed on. The chain stops and returns to the caller only when the next step
  is assigned to a human or is unassigned — the deterministic chain honors the
  same approval boundary as the agent supervisor.
  A script that exits 0 leaving the step **unchanged** is read as
  "deterministic preparation succeeded and the agent continues that same open
  unit of work" and returns `chain=True` — also an agent launch.
  `src/coga/recurring_runner.py` carries the same hybrid notion explicitly,
  which is why the temporary-worktree mode below has to thread a hard no-agent
  reason through shared launch instead of assuming file presence means the
  script is the whole run.
  The launcher marks `active → in_progress` before starting and then leaves
  the workflow alone: the script closes its own step (`coga bump`), exactly as
  an agent does. A non-zero exit halts that launch and leaves the task
  unfinished — but it does **not** stop the sweep. The failure is recorded —
  its exit code in the run record, and its stderr tail on the period
  blackboard by the recipe layer (see the recipe reporting contract under
  "Extend recurring with a task-specific workflow") — and
  the remaining due templates still run; the sweep names every failed template
  in its summary and run record, then exits with the first failing code. One
  template's problem is not its licence to cancel the ones behind it, which is
  the same isolate-and-aggregate posture `coga recurring --all` takes across
  repos and the same posture as the `--force` bullet below, whose canceled-task
  refusal also continues through later templates.

  It used to stop, and the failure mode is worth remembering: the scan returned
  the child's exit code from inside its own launch loop, so every template
  admitted behind the failure was abandoned **and went unreported** — no
  outcome record was ever built for them. On 2026-09-08 one routine URL-skill
  digest conflict made `skill-update` exit 1, the four templates behind it
  never ran and were never named, and the record read `templates scanned: 7 /
  tasks run: 3 / problems: 1` (see
  `coga/tasks/autofix/stop-one-failing-ticket-py-from-starving-the-rest/run-log.md`).

  Two exit classes are exempt from the aggregation, because they are not
  template failures and continuing would let the sweep start work that was just
  forbidden. Both re-raise immediately, stopping the sweep where they happened:

  - **75** (`git.RETRY_WITHOUT_SWEEP_EXIT_CODE`) — an aligned-assist
    publication or teardown refused and deliberately left dirty retained state
    for the operator to reconcile. No later template may run a refresh, sync,
    or agent that could disturb or publish those bytes first.
  - **≥ 128** — a process-level interrupt. `commands/launch.py` turns
    SIGINT/SIGTERM into `SystemExit(128 + signum)`, and an explicit
    cancellation must never initiate additional work.

  Those are the only deliberate stops; a period whose reconciled ticket
  cannot be classified after admission is refused and skipped like any other
  per-task refusal. Whatever does leave the launch loop — those two exits or
  an error escaping a launch or its lifecycle bookkeeping — the sweep never
  again abandons work silently: `recurring_runner._record_abandoned_due`
  records the stopping task and reason in the sweep notes. If that task has
  no launch outcome, it also becomes an `## Unresolved recurring failures`
  entry counted in `problems:`, even when it was the only or last due task.
  Every due task admitted behind it is listed there as `admitted as due but
  never launched`, counted in `problems:`, and named in a sweep note.
  This reporting uses the captured task identities without rereading or
  mutating retained task state.
  A report whose `tasks run:` is short of its due count therefore always
  says why.
- `coga recurring --force` — ignores schedule and status filters and attempts
  the real period task for every template, reactivating `done` and `paused`
  runs. A `canceled` task remains terminal: the runner reports a controlled
  refusal for it, continues through later templates, and exits non-zero after
  the sweep. This status refusal takes precedence over agent admission: a
  headless or temporary-control-worktree scan retains an already materialized
  canceled agent period so the force runner can report the refusal instead of
  silently filtering it as unavailable. No agent is admitted by doing so.
  Deleting that canceled period task is the explicit prerequisite for a fresh
  run.
- `coga recurring --all <path>` — discovers every Coga repo below an explicit
  parent directory, pruning dependency/tool-state, `_`-prefixed directory
  trees, and the prefix-plus-owner-marker parents of Coga's temporary control
  worktrees. That last exclusion still applies when `<path>` contains the
  system temp directory (including `/tmp` or `/`). It runs the ordinary due
  sweep in each configured target, sequentially. A missing local `user` or
  another intentional Coga config guard
  makes a scratch checkout an unconfigured non-target: these are omitted from
  dispatch, summarized once by count, and do not make the parent fail. That
  exemption is about *targets*; the parent's own config carries a second,
  narrower one. `cli.main` in `src/coga/cli.py` catches `ConfigError` from its
  eager `find_repo_root()` / `load_config(require_user=False)` and from
  `_validate_aliases`, and — when and only when the invoked command is
  `coga init` / `coga uninstall` or a cross-repo `coga recurring --all` —
  warns on stderr (`Note: ignoring current config error so the cross-repo
  recurring sweep can run`), discards this repo's alias map, and dispatches on
  `_DEFAULT_ALIASES` alone. Every ordinary command still exits 2 on the same
  error. This is deliberate rather than a hole in fail-loud: the parent's own
  checkout may be legacy or half-migrated while the repos under `<path>` are
  fine, and each of those loads its own config in its own process anyway. Do
  not tighten alias or config validation without preserving it, or the change
  silently re-breaks every cross-repo sweep started from an old checkout. Each
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
  A `ticket.py`-backed template's workflow step still declares
  `assignee: agent`, and that is not a lie to fix: `VALID_ASSIGNEE_ROLES` has
  no script token, and adding one would be the execution-mode field this
  design deliberately refuses. The step *is* the derived agent step — launch
  runs the deterministic phase first and falls through to that agent only if
  the script leaves the step open. `example/coga/workflows/deterministic/
  check.md` ships the same shape on purpose.
- `delegate` — optional `bootstrap/<name>` command-ticket ref, mutually
  exclusive with a `ticket.py` sibling. It does not select deterministic-vs-
  agent execution — that stays deduced from the file. It declares *which*
  stateless bootstrap target an agent period hands its work to, which no
  file's presence can express. The template's period is then serviced by
  launching that target rather than by an agent session on the period task:
  the runner preflights push access for the materialized period (the stateless
  bootstrap target would otherwise self-skip that gate), fully preflights and
  composes the bootstrap launch, then publishes `in_progress` strictly (the
  publish's provenance check is the compare-and-swap) before announcing the
  start. The materialized task carries a creator-owned `period_generation:`
  token that changes on every supported rematerialization; the verification
  covers that bounded witness plus the exact ticket bytes, read from freshly
  fetched control, without rereading the unbounded global audit log. Launch then
  reloads config and target state and
  redoes every preflight and composition step because start publication may
  fast-forward the control checkout. Immediately before spawn, the runner
  requires that same ticket-plus-generation state, `in_progress` status, and
  frozen delegate on control. Any concurrent terminal transition, replacement, dispatch
  change, ticket edit, or new generation refuses the spawn. The launch remains
  in-process — in the operator's own terminal, under the sweep's `--agent`
  override, selected queue session conduct, and idle/max-session liveness
  bounds — and the
  period task reaches `done` only when the bootstrap target emits its done
  sentinel. After the child exits, completion and watchdog pause verify the
  same generation against control and publish strictly; an older child's
  result can never mutate a replacement at the stable path. A natural/crashed
  exit fails with the period left retryable; a multi-task sweep pauses a
  watchdog timeout and continues only after that pause is verified on control.
  A stale or failed pause refuses the run; a named launch fails and leaves it
  `in_progress` for retry. At final spawn admission the runner also freezes the
  exact parent recurring ticket named by the period's state snapshot and
  verifies that input on control. Completion verifies the same parent state
  and publishes it with the `done` transition, so a concurrent parent/cursor
  edit refuses instead of being overwritten, and the child's cross-run cursor
  update cannot remain local while the period reaches `done` on control. The
  live completion notification waits until publication succeeds. A refused or
  definitely failed strict publication restores the leased bytes and retracts
  its audit lines; if a push reply is lost and control cannot be re-read, the
  runner refuses and retains the local state for explicit reconciliation
  rather than manufacturing a split.
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

  **A delegated period is bounded to one agent step.** Its resolved workflow must
  contain exactly one step, that step must *explicitly* declare
  `assignee: agent`, and it must carry no `requires:` completion gate. The
  default `direct/body` satisfies this; a custom workflow may use another name
  but must have the same shape. The sole step is the period's lifecycle envelope
  — the bootstrap target remains the source of the executed instructions — and
  the period must be at step 1 after any prospective activation.

  The bound exists because delegation launches the target and completes the
  *whole period* on that target's done signal, without advancing the period
  workflow. Anything the snapshot promised beyond one agent step would therefore
  be skipped: a second step, a later `owner` gate, a peer (`other-agent`) or
  omitted role that derives a different operator than the agent actually
  working, or a completion gate nothing evaluates. A `requires:` is rejected even
  when it currently *passes*, because whether it passes is run state rather than
  a property of the contract.

  It is checked on the resolved template workflow before materialization, and on
  the frozen period workflow before every retry, direct launch, and sentinel
  completion — after each existing ticket/config reload, under the existing
  exact-ticket and generation leases — so a workflow edited while the child runs
  cannot slip a gate past completion. A refusal spawns no target, advances or
  completes nothing, and persists no new agent choice. `coga validate` reports
  the same violation on templates and stored periods
  (`unbounded-delegated-workflow`).

  Jobs that genuinely need multiple steps, peer review, or a completion gate run
  through ordinary recurring execution, without `delegate:`. Role-aware,
  step-aware delegation is deliberately out of scope.
- `period_generation` is runner-owned materialized-task state, not a template
  input. The creator stamps it once per new stable-path generation; templates
  or ordinary tasks that declare it are rejected rather than accepting a stale
  or forged lease identity.
- `title` — the created period task's title (else the humanized name).
- `workflow` — optional. A template that names none creates with the
  one-step `direct/body` workflow, which runs the ticket body's ordered
  phases directly as the prompt; Dream is the canonical example. (The task is
  still workflow-carrying and bumpable — `direct/body` is the workflow.)
- `owner`, `agent`, `contexts`, `secrets` — passed through to the created
  period task. `agent` is the template's optional main-agent choice; promotion
  retains it and every period task inherits it.
- Top-level `slug`, `human`, `assignee`, and `watchers` are rejected when a
  template is loaded, before period creation or reuse. Validation names the
  offending fields as a `bad-recurring-template` error. Remove those fields
  and declare any main-agent preference with `agent:`; the template cannot
  silently discard an old assignment and run the configured default instead.

## Recurring runs start on the control branch

Every launching entry point reads and writes period state **from the configured
control branch**: the bare sweep, `--force`, `coga run recurring-scan`,
`coga recurring launch <name>` (including aliases such as `coga dream`), and
direct `coga launch recurring/<name>` for a frozen delegating period. There is
deliberately no override: `--force` bypasses schedule and status filters, not
the branch requirement.

Off that branch, the two single-repo entry points — the bare/forced sweep and
`coga recurring launch <name>` — do not dead-end. They look for another
worktree of the same repo that **already has the control branch checked out**
and re-run themselves from there, returning that child's exit code. The child
starts in that worktree's counterpart of your own Coga workspace — the same
position relative to the checkout — so a monorepo keeping Coga in a
subdirectory relays like any other layout, and a checkout with no `coga.toml`
at that mirrored position is not treated as one. Nothing is
created, copied, or deleted: no worktree is added, the operator's checkout is
never switched or stashed, and no lock is held beyond what an ordinary
on-control run holds. The relayed child is simply an ordinary on-control run
that started in a different directory, so every existing scan, sync, ledger,
and push path applies unmodified. Consequences worth knowing:

- **It reads the control tip, not your feature tree.** Templates, period tasks,
  and `coga/log.md` all come from the control worktree. That is the intended
  semantics — a sweep driven by a half-finished feature branch could re-fire
  runs the control branch already serviced — but it does mean a template you
  are editing on a feature branch is *not* what runs.
- **Agent-backed templates are admitted.** stdio is inherited, so the TTY
  survives the hop and admission works exactly as on control. A **dirty**
  control worktree is not gated, for the same reason today's on-control sweep
  does not gate a dirty primary checkout; it is the same run in a different
  directory. The checkout is durable and operator-owned, so there is no
  temp-worktree data-loss or cleanup question — but do expect a session to be
  working in a checkout you may also be using.
- **`delegate:` templates work unchanged.** The child *is* the sweep, and its
  terminal is yours, so the delegated launch keeps its TTY admission and its
  `coga/log.md` slack-sentinel completion path — writing the control branch's
  log, which is the correct one.
- **`coga.local.toml` travels, it is not copied.** The file is gitignored, so a
  worktree made by plain `git worktree add` has none. The relay exports
  `COGA_LOCAL_CONFIG` pointing at your own copy; nothing is written into the
  other checkout. What that file holds — `user`, agent paths, notification
  webhooks — describes the machine and operator rather than the checkout.
- **One hop, never two.** The child carries `COGA_RECURRING_CONTROL_RELAY`, so
  it takes the ordinary path (or the refusal) rather than relaying again.

When **no** worktree holds the control branch, the refusal stands: it names the
current branch, the configured control branch, and now the absence itself,
offering `git worktree add ../<repo>-<control> <control>` alongside
`git switch <control>`. Adding that worktree once makes every later off-branch
sweep relay by itself. A worktree that holds the branch but **cannot be relayed
into** — no `coga.toml` at the mirrored workspace position, or a registration
whose directory is gone — is a different refusal: it names that worktree and
tells you to bring it up to date or remove it (`git worktree remove <path>`,
`git worktree prune` for a missing directory) before recreating it, because
Git will not check the branch out a second time and `git worktree add` would
only fail. `coga launch recurring/<name>` has no relay and its refusal says
nothing about worktrees, so the message never promises behavior that spelling
does not implement.

The outer sweep gate checks only the local branch. Its initial fetch and
fast-forward (`git.refresh`) remains a warning for bare and named interactive
single-repo scans, but a remote-backed
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
whole public launch path. Delegated children verify their exact
ticket-plus-generation state on control instead, and any transport failure
while confirming or publishing it refuses the child. The
unattended `coga recurring --all <path>` child keeps its stricter existing
precondition: it must also fetch and integrate the latest remote control tip
before scanning. Being off the control branch is not a refusal for that child
either — see "An `--all` child services an off-branch checkout from a
temporary worktree" below — but it gets there by *creating* a worktree, where
the single-repo entry points only reuse one that already exists. Repos with `[git].enabled = false` and workspaces outside a
git checkout have no Coga-managed control checkout, so the branch-only gate
does not apply to them. Only a confirmed non-git workspace self-skips: a Git
inspection failure refuses rather than silently treating the checkout as
unmanaged — and it refuses rather than relaying, so a broken probe can never be
read as "no worktree holds control".

The forwarding CLI skips its end-of-command state sweep, including after a
child failure or interruption. Only the control-worktree child performs the
ordinary sweep; returning to the caller must never commit its dirty files.
SIGTERM sent to the forwarding PID is forwarded to the child, and the parent
waits for its exit before returning 143. Terminal access remains inherited.
Ctrl-C already reaches the child through the foreground process group; the
parent waits for cleanup without sending a second SIGINT.

## An `--all` child services an off-branch checkout from a temporary worktree

The branch gate above is right — the scan reads working-tree templates and
period tasks and writes period state, so running it from a stale feature branch
could re-fire runs the control branch already serviced. What was wrong was the
only recovery: a human noticing cron output and running `git checkout` by hand,
while every sweep failed the repo in the meantime.

So when an `--all` child's catch-up fails *only* because the control branch is
not checked out here, the child does not give up. Nothing holds that branch, so
it checks it out in a temporary linked worktree under the system temp dir,
creating a missing local control ref from the freshly fetched remote-tracking
ref (`git.fetch_control`), so a single-branch or narrow-refspec clone is
serviceable without trusting checkout-wide `FETCH_HEAD`. It then seeds the gitignored `coga.local.toml` into it (without
that file there is no `user` and `load_config` raises), and re-dispatches from
the mirrored Coga workspace itself — the checkout directory in a root layout,
or the nested Coga directory in a monorepo. Before removing
the worktree, it copies every machine-local `.coga/recurring-runs/*.md`
transcript into the matching workspace in the operator's durable checkout;
same-name, different-content records are kept side by side. If that transfer
fails, the registered temp worktree is retained rather than destroying the
only copy. The inner scan starts in its own process session. Once its process
handle is known, cancellation signals the entire process group and waits for
its leader to exit, so a `ticket.py` descendant cannot continue against a
checkout that has already been removed. Known-safe cleanup then runs in a
`finally` — on success, on a recipe's non-zero exit, on an exception, and on
SIGINT/SIGTERM. If an asynchronous interruption lands after the child may have
forked but before its handle and process-group ID can be published, cleanup
instead retains the registered worktree without reading its possibly-live run
records; the operator must verify no process still uses it before removal.

Each temp parent carries a versioned repo/branch/workspace ownership marker
with the wrapper PID and the isolated child's spawn state. It publishes
`starting` before spawn and the process-group ID immediately afterwards. If
SIGKILL bypasses cleanup, the next run removes that exact Coga-owned checkout
only when the wrapper is dead and either no child had started or the published
process group is also dead. Immediate cleanup and later stale recovery both
retain an ambiguous `starting` window; a live wrapper or group, an old/invalid
marker, and every unrelated user worktree remain protected by the ordinary
branch-lock refusal. Stale recovery also transfers the saved run records before
removal and retains the checkout if it cannot.

Three properties make this shape the right one:

- **The operator's project state is never moved.** No stash, no switch, no
  restore. Their branch, tracked and untracked project files (dirty or not),
  and stash list are unchanged; the one deliberate local write is the
  gitignored run transcript copied into `.coga/recurring-runs/`. A
  stash-and-switch would hold their work hostage for the whole
  sweep, conflict on `stash pop` against the scan's own writes to
  `coga/tasks/**` and `coga/log.md`, race Coga's own concurrent sessions, and
  strand the work outright on a cron timeout.
- **The branch is genuinely checked out, so nothing downstream changes.**
  `git.sync_log` and `_sync_recurring_create_paths` both refuse to publish from
  a detached HEAD, and the serviced-period ledger line is what stops the next
  sweep re-firing the period once Dream reaps the task. A worktree detached at
  the remote tip would land the period task without its ledger line; checking
  the branch out gets the whole publication path for free.
- **`git worktree add` is the concurrency lock.** Git refuses to check one
  branch out twice, so a second sweep — or any unrelated worktree already
  holding the control branch — loses the race there and falls back to the loud
  refusal, which names the holder and the manual remedy.

Only deterministic `ticket.py` phases run in this mode, whether or not a TTY
exists: a throwaway worktree is the wrong place to spawn an agent REPL that
composes prompts, edits files, and opens PRs. Existing periods are admitted
from the frozen `ticket.py` in their materialized task, not from a template
that may have changed since creation, including every status surfaced by
`--force`. File presence admits the script; it does **not** assert that the
script completes the period, because ordinary tickets may combine deterministic
and agent phases. The inner runner therefore carries a hard no-agent reason
through shared launch. If a script leaves its current or next agent-owned step
open, launch returns before agent-only setup, keeps the deterministic output,
and the runner pauses that exact period for a later launch from a durable
checkout. Each skipped agent template or refused hybrid handoff is reported by
name with the temporary-worktree reason rather than the (here false) "an agent
run requires a TTY". The `--all` summary lists these repos separately from
ordinary sweeps.

The *ahead or diverged* control checkout — on the control branch, but not
fast-forwardable to the fetched tip — is deliberately out of scope and still
fails loud, naming `git pull --rebase`. Coga never rebases a human's commits,
and servicing it from a worktree at the remote tip would silently step around
commits a human has to reconcile.

Single-repo runs are unchanged: bare `coga recurring`, `coga recurring launch
<name>`, and `--interactive` still refuse off the control branch, because they
scan the working tree they are in.

A create made in a feature checkout publishes to control like any other
write (`coga/sync`): the period task and log line land, and the checkout
keeps its own copies dirty. Normal recurring commands refuse that checkout
before creating anything, so this is reachable only through direct calls.

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
into the remote-tracking ref and reads `owner` directly from that exact
commit's `coga.toml`; a stale local control checkout can predate an owner
addition or transfer, and its working tree can carry an uncommitted takeover.
Checkout-wide `FETCH_HEAD` is never an authorization source. The lookup
fetches from the remote's sole effective **push** URL — the repository
`git push <remote>` actually writes the period state to, which git
distinguishes from the fetch URL — and refuses a remote with several push
URLs, because state spread across destinations has no single owning
repository to authorize against.

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
- `status:` and `step:` are dropped — per-run state the creator re-derives for
  every period task. `title`, `owner`, `agent`, `contexts`, and `secrets` pass
  through; `agent:` is a real preference, so promotion keeps it rather than
  making every future period re-pick the default. A frozen `workflow:` snapshot collapses back to its name so the
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

To see a new or changed template fire before it merges — without posting to
Slack, reading the vault, or pushing to the real remote — follow the
`coga/recurring/verify` skill. It fires the job for real inside a disposable
clone and says which parts of a firing that does and does not prove.

**A new template fires retroactively on its first sweep.** The scan takes the
schedule's *last* firing before now (`_last_firing`), buckets it into a period
key, and creates the period task unless `coga/log.md` already holds a
`created|reused` line at or after that period. A brand-new template has no
line, so an annual reminder dropped in September is serviced for the March
that already passed. Do not try to pre-empt that by seeding a mark: the old
template field `last_serviced_period:` no longer exists, and the failure it
invited — an agent wrote `none` because it read as more honest than inventing
a period, and string comparison then suppressed the template forever while
`coga status` showed `ran this period` — is why the mark moved into the
append-only log with a validated shape. There is no seeding path, nothing to
hand-edit, and no create-only sweep: the first bare `coga recurring` records
the period and launches it in one pass. Keep a new template parked with the
`_` prefix until the firing you want has passed, then rename it so the next
sweep selects that firing. Enabling it *before* that date does not suppress
anything: a March 1 annual template enabled on February 28 selects March 1
of the previous year. `_last_firing` is strictly before the scan time, so
enable it after the intended firing instant, not at that exact instant. When
parking is impractical, write the body so the run tolerates an already-handled
period
(read the ledger and the parent's cursor, then no-op — the `coga/period-task`
shape). If an unwanted retroactive run already happened, the period is
serviced regardless; do not `coga mark canceled` its task to say so — a
`canceled` task at the stable path is returned as the existing task on the next
period and refused, so the template stays stuck until that task is deleted
(see `--force` above).

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
routing, blocker, and completion machinery. The sweep selects an explicit
deterministic half before falling back to an ordinary agent launch, and adds
post-launch handling for unfinished runs as described below.

To schedule a task-specific workflow:

1. Define the workflow and any skills or contexts through their ordinary Coga
   paths.
2. Create a non-underscore directory such as
   `coga/recurring/weekly-deliverability/` with a `ticket.md` — copy an
   existing template (e.g. `skill-update/`) or start from the example below.
3. Set the template's `schedule:`, explicit `workflow:`, `contexts:`, `owner:`,
   and optional `agent:`, then replace its `## Description` with the per-firing
   instructions.
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
agent: claude
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

This extension seam has six important constraints:

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
  `in_progress`. **Exiting 0 without closing the step is the third outcome and
  the commonest authoring mistake — it is not a no-op.** An unchanged step is
  exactly the chain-to-agent signal described under dispatch above, so a
  template this context calls headless becomes an agent-requiring launch: an
  unattended sweep has no TTY for it and reports the period `unfinished`. That
  is why every shipped script ends in an explicit completion shell-out — see
  `coga/recurring/blocker-reminders/ticket.py`, which finishes with
  `subprocess.run([sys.executable, "-m", "coga.cli", "bump",
  os.environ["COGA_TASK_SLUG"]])` rather than calling the Typer command
  in-process, where option defaults would arrive as `OptionInfo` sentinels.
  Deliberately exiting non-zero to keep a period visible until a human looks at
  it is an available idiom — `coga/recurring/skill-update/ticket.md` documents
  using it that way — but price it first: the period is left unfinished and
  `in_progress`, and the sweep — which does run every template behind this one
  (see the dispatch bullet above) — exits with that code and names the failure
  in every run record until someone resolves it. `coga block` buys the same
  visibility with a better record: the ask is recorded on the period ticket,
  the script-recorded `blocked` lifecycle is preserved rather than paused, and
  the run is reported as `unfinished` with its reason rather than as a bare
  non-zero exit.
- **The recipe reporting contract: the period blackboard is a per-run report
  surface, and the recipe layer records failures there.** Code reaches the
  period task's blackboard through `COGA_TASK_BLACKBOARD` /
  `coga.task_env.blackboard_from_env`, and that helper answers only *which
  repo* (it refuses a path outside the `tasks/` tree of the root the recipe is
  operating on). *Which task and for how long* is this rule: under a recurring
  template the path is always `coga/tasks/recurring/<name>/ticket.md`, the
  period task the next firing deletes. So a report appended there is
  **per-run**: it travels into the sweep's run record (the analyst-channel
  section below) and the `run-log.md` of any autofix ticket, and it is then
  gone with the period. That is the right home for a run summary whose durable
  product is elsewhere — a PR, a posted notification, a closed ticket — and
  the wrong home for anything a later run or a human must find: the
  2026-09-03 autoclose defect wrote its only copy of the pending `coga retire`
  follow-ups there, and `render_retire_report`'s docstring calling the target
  "a long-lived recurring task's blackboard" is exactly why review missed it.
  Anything that must outlive the period goes to one of three surfaces: the
  template's own blackboard region (`coga/recurring/<name>/ticket.md` below
  the fence — cross-run cursors and keys, see "Last-run state" below); a
  template sibling file in a fixed machine-written shape (the retired digest
  template's `spool.md` was the precedent, and `persist-autoclose-retire-follow-ups`
  gives autoclose a `retires.md` worklist the same way); or the repo-global,
  append-only `coga/log.md` for one-line audit facts. Successful runs owe no
  report — a finished deterministic period whose blackboard still holds only
  the seeded placeholder is normal — but a template whose findings the
  analyst should see writes them itself, and a recipe whose failure is
  structured beyond a stderr line (skill-update's `## Skill Update` failure
  report names the command and the unconfirmed PR) writes that itself too.
  **Failure is owed a reason, and the layer pays it once.** The sweep discards
  a `ticket.py` child's stderr; only the blackboard reaches the run record, so
  a recipe that exited non-zero to stderr alone showed up as "failed, blank
  blackboard, no reason" — a problem counted, with nothing to read about it.
  `coga.runner.run_recipe` — the one seam every registered recipe crosses,
  from `coga run` and from every shipped shim, which is why the shims call
  `run_recipe(load_config(), "<name>", [])` rather than importing the recipe
  function — copies the recipe's stderr while it runs and, on a non-zero
  return or an escaping exception (traceback included), appends a
  `## Recipe Failure` section (recipe, exit, task, and stderr tail) to the
  blackboard `blackboard_from_env` resolves against the recipe's effective
  target root, including `--cwd`. A refusal by that containment check cannot
  be bypassed by using the invoking config's root for the failure report.
  The whole section fits the run record's per-task budget, and diagnostics
  are indented so quoted ticket fences and headings remain data. No
  blackboard means no extra write: `coga run` from a shell
  already showed its stderr. A refused or failed write is a stderr warning and
  never replaces the recipe's exit. Do not add a per-recipe copy of that write
  for the stderr tail; put the recipe's structured detail on top of it. A
  template-owned `ticket.py` that is not a registered recipe gets the same
  property by routing its deterministic work through `run_recipe` or by
  writing its own reason before exiting non-zero — exiting to stderr alone is
  the one shape the sweep cannot report.
- **A scheduled agent run must reach `done` in one launch.** When a bare
  `coga recurring` sweep gets control back from an unfinished agent launch, it
  pauses the period task before continuing. That includes an intermediate
  human or unassigned handoff and a task that invoked `coga block`; the paused
  run cannot use ordinary `bump` / `unblock` from that state, and the
  `blocker-reminders` sweep never surfaces its unresolved ask — that recipe
  filters on `status: blocked` only, so a paused period's `## Blockers` entry
  is reminded to nobody (see `coga/blockers/remind`). Watchdog timeouts
  keep failing subsequent sweeps until explicitly resumed: use
  `coga launch recurring/<name>` to continue the saved step, or
  `coga mark active recurring/<name>` to make the next sweep resume it.
  `--force` also resumes paused runs; its resulting task outcome determines
  success instead of counting the pre-recovery pause twice. A paused run is
  never replaced just because another period is due. Its ticket and findings
  remain intact; route unfinished findings into durable artifacts before
  explicitly closing a run instead of resuming it.
  Do not put human gates or expected blockers in a scheduled
  agent workflow. Use the on-demand `coga recurring launch <name>` path (then
  drive the ordinary ticket handoff) or an ordinary task when a run needs
  those intermediate states.
- **Agent work needs a TTY; a `ticket.py` half does not.** An agent-backed
  template needs stdin and stdout TTYs and runs under the REPL supervisor; a
  TTY-less sweep skips it with a warning. A delegating template
  (`delegate: bootstrap/<name>`) is agent-backed for this purpose — its
  delegated run is an agent launch — and is skipped headless the same way,
  including when an `active` / `in_progress` period already exists from an
  earlier attended sweep. A scan can still inspect and report a paused
  period without admitting an agent; a forced launch retains the TTY gate.
  Refused watchdog recovery remains an unresolved failure, not a task run.
  So does a recovery that was *admitted* and then never ran: an admitted
  watchdog recovery must produce a completed outcome, and the sweep exits 2
  naming any slug that did not. The check is absence-based on purpose —
  several paths (a period lease that changed after admission, a control
  refresh that skips the launch, a removed period) record only a note and
  continue with no outcome at all, so looking for a failed outcome would see
  nothing and report success while the task stayed paused.
  Admission leaves that period untouched and continues
  to later deterministic jobs. A template carrying `ticket.py` runs directly
  without a TTY and is the appropriate shape for an unattended scheduler.
  A period the sweep *created* is held to the same absence rule: a create
  refused at admission stays in the scan table and run record as
  `skip (<reason>)`, and a created period with no launch outcome is a
  problem, so the sweep exits 2 rather than reporting a clean "No recurring
  tasks due." over work it created and dropped. The exception is
  `skip (already handled on control)`: control had already serviced that
  period, so nothing was lost and it is not a problem.

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

A durable *worklist* a run maintains can instead be a sibling file of the
template, when it is machine-written in a fixed shape and a blackboard
region would be the wrong container for it. The shipped instance is
`coga/recurring/<name>/retires.md`, the autoclose sweep's list of feature
checkouts its disposal proofs refused, owned by `src/coga/retire_worklist.py`.
The sweep resolves that path from the period task it is running under
(`tasks/recurring/<name>/` names the template; nothing hardcodes
`autoclose-merged`), records the run's preserved closures there keyed by
slug, and on every run — period task or hand run — re-judges the open entries
of every worklist and drops those whose recorded worktree directory and local
branch are both gone; `coga retire <slug>` drops its own entry the same way.
The write is barrier-held, compare-and-swap, and atomic; the file is
`merge=union` like `log.md`, so union-merge duplicates and resurrected lines
heal on the next reconcile rather than needing a second mechanism. A run that
is not a period task never *records* into a worklist. The 2026-09-03 defect this
replaces wrote the only copy of that list to the period task's blackboard,
where the next period's scan deleted it.

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
  reachable by every other writer of that region. A run that rewrote its
  own state section swallowed a mark appended after it — and each erasure
  made the next `coga recurring` delete the completed task and re-run the
  job, reposting its result. An appended line cannot be clobbered that way, is
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
  sweep binds this pre-create result to the caught-up checkout revision. The
  create guard reuses it while the fetched control revision matches, without
  materializing the Git log blob again. Before the first successful create
  publication, a different fetched revision refreshes the snapshot for the
  **complete target set**, including on a non-fast-forward push retry. This
  prevents a competing completed/reaped period published after the scan from
  being recreated. Without a confirmed catch-up, the first successful control
  fetch supplies the same target-aware snapshot. Changed-revision reads may
  materialize the control log; unchanged-revision local reads remain bounded.
- **One shared file, so publication changes the freshness rule.** The first
  create publication carries pending log records for other templates in the
  same sweep. The guard retains its competitor snapshot and records each
  successful own publication's revision instead of treating those pending
  records as rival work. When control subsequently advances, a Git diff of the
  log against that known revision identifies templates whose serviced-record
  lines were added, removed, or changed externally. Those templates refuse
  admission visibly for the rest of the sweep; unchanged templates remain
  serviceable. Even a changed line with the same period is conservatively
  refused: the merged log cannot establish which checkout owns that claim.
  Ordinary audit appends and revisions with no ledger change do not invalidate
  another template's decision. The same rule applies to later create retries.
  If the first create fetch fails and generic path sync recovers, its existing
  publication guard refreshes the competitor snapshot before landing and on
  retries. Its accepted control revision becomes a known own publication too;
  a later template must not refresh through this sweep's pending records.
  Audit-only pushes after a create loses a race also count as own publications,
  with the same ledger guard on a rejected audit-push retry.
  The revision is read from the remote-tracking ref the successful push just
  advanced, not from a subsequent fetch that could accidentally attribute a
  rival's intervening commit to this sweep. Both the create and the
  audit-only publish re-run the ledger check through `publish`'s `guard` at
  every base they push on (`coga/sync`), because the union-merged log is a
  candidate only while it is dirty and a blob pin on it would otherwise go
  unevaluated on a control checkout.
- **Freshness refusals are not best-effort sync failures.** An unreadable
  fetched ledger, or ambiguous ledger changes after own publication, raises a
  recurring admission error and excludes the task from dispatch. A rejected
  local create is restored to the fetched control task or its absence, so it
  cannot survive as a local-only orphan and bypass create-sync on the next
  sweep. Peer tasks and their generations are preserved. Reused tasks also
  fetch and validate the ledger; malformed records cannot be bypassed by reuse.
  The append-only audit remains intact, including local create records for
  refused candidates; refusal does not prove execution, and an intentional
  rerun uses the existing explicit override. `--force` and named launches
  bypass period dedup, while still validating the freshly observed ledger and
  respecting task/generation guards. A forced reuse preserves operator edits.
- **This is an observed-revision boundary, not global exactly-once execution.**
  A rival advancing control before a create push rejects that push; the bounded
  retry fetches again and applies the refresh/refusal rules above. A rival can
  still advance after a successful publication. The existing exact per-child
  admission checks then guard task bytes, generation, and launchable status;
  the ledger is not a distributed execution lock. A byte-identical competing
  record, or intervening changes with no net ledger diff, cannot be attributed
  by the post-publication guard. Initial fetch failures retain
  the existing best-effort generic sync fallback, and exhausted transport
  failures keep their existing reporting. The stricter remote-backed child
  admission and `--all` pre-scan catch-up requirements remain as described in
  **Recurring runs start on the control branch**.
- Period tasks create **straight to `status: active`** — ready jobs, not
  drafts to triage. Because every active task must carry a workflow, a
  template that declares none creates with `direct/body` (it would otherwise
  be un-activatable and `coga validate` would flag it as a stuck task).
- `agent` defaults to the repo's configured **default agent** when the template
  omits it. Period tasks create straight into a live status, so they perform the
  same main-agent selection activation would — a workflow-less template like
  Dream is therefore launchable the moment it materializes. Who actually holds
  the period is still derived from its workflow step's role.
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
the fresh task at the stable path — but only after proving the replacement can
be created: the template's `workflow:` and every step skill it names must
resolve first. A template pointing at a removed workflow is one per-template
scan error, its stale `done` task stays on disk, and the rest of the sweep
runs; the delete never runs ahead of a create that would fail. This is also
how Dream's own completed task is removed: Dream marks itself `done` and
stops, then the next firing's scan
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
   unfinished, refused by `--force`, or `damaged-template` when the firing
   changed the template instructions it was composed from), the ticket's
   status afterwards, and the period task's **blackboard**, plus any template
   that failed to load. It is
   *built*, not scraped: tee-ing fd 1 would make `isatty` false and every
   interactive agent launch would then refuse itself. The blackboard is read
   instead because it is the only durable per-run channel Coga owns; the
   console is not one. **Successful runs populate it only when they choose to
   write a report.** Failures follow the recipe reporting contract above.
   Nothing in the `ticket.py` contract asks for a successful run report — the
   completion-contract bullet above asks a script to run headlessly, close its
   own step, and record an unavailable prerequisite with `coga block`, and no
   more. Of the shipped templates `skill-update` writes one on every run,
   through `render_blackboard_report` / `append_report` in
   `src/coga/skill_update.py`, which appends a `## Skill Update` section.
   `autoclose-merged` writes one **conditionally**: when it closes a ticket
   that still has a recorded branch or worktree, `_report_retire_followups`
   renders the pending-retire report and `_append_blackboard_report` writes it
   to the period task, so that run does give the analyst more than the seeded
   placeholder. That section is the run record, not the worklist — the same
   run records the follow-ups in the template's durable `retires.md` (see
   "Last-run state" below). A sweep that closed nothing, or nothing needing
   retire, still leaves only the placeholder. `branch-sweep` writes a `## Branch Sweep`
   section on every run — outcome lists plus each per-branch decision — since
   the 2026-09-08 period landed with an empty blackboard and no record of
   what the sweep decided. `blocker-reminders` still hands the analyst a
   period blackboard holding nothing but the seeded placeholder (the committed
   run records under `coga/tasks/autofix/` show exactly that), so for that
   run the analyst can see *that* it ended cleanly and nothing about what it
   did, and `skill-update` is faulted more often partly because it is one of
   the runs that always says something. A template whose findings should be
   analyzed has to write them to the period blackboard itself.
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

Template damage also has a synchronous path that does not depend on this
analyst. Immediately before dispatch, the runner snapshots the template's
Description — the bytes above its single blackboard fence — and compares that
region after the firing. A changed Description, or a template that is no longer
readable with exactly one fence, records `damaged-template` and prints an
immediate stderr warning even when `COGA_AUTOFIX=0`; the next firing must not
silently consume the corrupted instructions. `coga validate` independently
reports a missing or duplicated template fence as
`recurring-template-fence`. Repair from git history before another firing:
distinguish a run that overwrote the fence from notes that duplicated a quoted
fence, restore the intended Description, and keep cross-run notes below the
single fence. Do not merely append a fence to the damaged file — that would
preserve the previous run's output as the next run's instructions.

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

- `COGA_AUTOFIX=0` disables the analysis and autofix-ticket loop, but not the
  direct template-damage warning or static validation above.
  `COGA_AUTOFIX_TIMEOUT` (seconds) bounds the call, which defaults to 300s and
  disarms at `<= 0`. The bound is on the analysis, not on each subprocess
  inside it: the first attempt, the `claude auth status` probe, and the
  subscription retry share one deadline, so the auth fallback below cannot
  stretch the wait a sweep signed up for.
- Every run record is also written machine-locally to
  `.coga/recurring-runs/<stamp>.md` (gitignored — one operator's sweep
  transcript is not team state), whether or not it gets ticketed. A scan in a
  temporary control worktree copies that record back to the matching durable
  workspace before cleanup; a transfer failure retains the temp worktree.
- `coga run autofix-analyze [<run-log.md>] [--dry-run]` re-runs the analysis
  over a recorded run by hand; with no path it takes the most recent one.
- The argv for the one-shot call is built in for `claude` and `codex`. Another
  CLI needs `[agents.<name>].analyze` in its effective agent table — shared
  `coga.toml` or machine-local `coga.local.toml` (e.g.
  `analyze = "-p {prompt}"`); without it the loop skips loudly rather than
  guessing an argv and opening a REPL nobody can drive.
- Which agent type analyzes: the explicit `--agent` flag on `coga recurring`
  or `coga run autofix-analyze`, then the shared `[autofix] agent = "<type>"`
  key in `coga.toml`, then the first-declared `[agents.*]` table (the same
  create-time default new tickets get). The key exists because the other two
  levers are wider than the intent — reordering `[agents.*]` also changes every
  new ticket's default, and `--agent` also reroutes every agent-backed period
  task in the sweep — and the meta-loop is a place you may *want* a different
  vendor: a second opinion on a sweep the default agent ran, on an auth path
  that did not just break. It must name a type in the effective agents table
  (a typo fails at config load, not at the end of an unattended sweep), it is
  one key and one branch rather than a per-command routing table, and it is
  shared-only: which vendor analyzes the sweep is repo policy.
- The analyst runs with its stdin closed (`/dev/null`), never the sweep's:
  `codex exec` appends a piped stdin to the prompt as a `<stdin>` block, so an
  inherited pipe would silently graft unrelated bytes onto the analysis.
- A non-zero analyst exit is reported with *both* of its streams, each under a
  `stdout:` / `stderr:` label and each keeping its own tail. Picking one
  stream — the old `stderr or stdout` — once told the operator about a
  connectors warning on stderr while the cause, `Credit balance is too low`,
  sat on stdout: loud, but loudly wrong.
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

- **In Coga's source repository, shipped recurring templates have a live copy
  at `coga/recurring/<name>/` and a packaged twin at
  `src/coga/resources/templates/coga/recurring/<name>/` — edit both.** The
  packaged copy is what a fresh `coga init` writes into every new repo, and
  nothing refreshes it afterwards. Because the `ticket.md` body *is* the run
  prompt (its `## Description` is composed verbatim into every period task),
  drift between the copies is not a stale doc: it means a repo initialized
  while they differed runs a different sweep than this one, and keeps doing so
  until someone diffs the two by hand. The same goes for a template's
  `ticket.py`. `tests/test_packaging.py` starts from the packaged tree and
  checks byte-identity only where a live counterpart exists, so a one-sided
  edit to a shipped pair fails the suite — see the `coga/codebase` context for the rule and
  the rebase hazard that can reintroduce drift after a green run.
  Repo-specific templates, including jobs created by `coga recurring promote`,
  need no packaged counterpart. In a downstream repo, edit the git-backed
  `coga/recurring/<name>/` template; do not create a source-tree twin or edit
  installed package resources to satisfy this Coga-source-only rule.

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

- **A job that pushes to a dedicated long-lived branch must resolve the remote
  tip at push time, not trust a tracking ref.** `coga skill update --pr` reuses
  one fixed branch (`coga/skill-update`), and the sweep never fetches with
  `--prune`. A bare `git push --force-with-lease` takes its expected OID from
  `refs/remotes/<remote>/coga/skill-update`, so once the previous period's PR is
  merged *and its remote branch deleted*, that ref still points at the old SHA,
  the lease names an OID the remote has never heard of, and the push fails with
  `! [rejected] coga/skill-update -> coga/skill-update (stale info)` — exit 2,
  and the period task looks like a real failure. It recurred **every period
  after a merge+delete cycle**, not once.

  `src/coga/skill_manager.py` now asks `git ls-remote` for the tip at push time
  and leases against that exact OID, pushing with no lease at all when the
  branch is genuinely absent — so the tracking ref is no longer consulted and
  the trap is closed at the source. `git fetch --prune <remote>` remains a
  correct local cleanup for a checkout carrying a dead tracking ref, but it is
  no longer the remedy for this failure. Any recurring job that force-pushes a
  reused branch inherits the trap until it resolves its tip the same way;
  `src/coga/open_pr.py`, `src/coga/branchcleanup.py` and `src/coga/git.py` all
  already do.

  Note what the lease does *not* buy here: `_commit_skill_updates` rebuilds the
  branch with `git checkout -B <branch> <control-branch>` every period, so the
  push is always a history rewrite and a freshly-resolved lease can never fail.
  A commit pushed onto the open skill-update PR by hand is discarded by the next
  period without a rejection.

## What this context does NOT cover

Scheduler wiring, how to write a run's skill or body
logic, and notification posting mechanics (see `coga/sync`). Implementation lives
in `src/coga/recurring.py` and `src/coga/recurring_runner.py`.
