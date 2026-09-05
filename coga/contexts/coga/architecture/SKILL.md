---
name: coga/architecture
description: Mental model for coga — primitives, planes, composition. What an agent needs to know to reason about how coga works as a system.
---

# Coga architecture

Coga is a markdown-first, git-backed company OS. Everything an agent
operates on is a file in `coga/`. There is no database, no daemon,
no in-memory state.

## Primitives

- **Tickets** live as directories under `coga/tasks/`: a task is any
  directory containing a `ticket.md`, at **any depth** — directly
  (`tasks/<slug>/`) or in a sub-directory (`tasks/marketing/social/<slug>/`).
  The sub-directories are just plain directories you organize with
  `mkdir` / `mv` / `rm` (nest them as deep as you like), and a task directory
  is never recursed into. A task is referenced by
  its **path under `tasks/`** — its bare leaf at the top level, otherwise the
  relative path (`marketing/coga-crm`, `marketing/social/relaunch`) — used as
  the qualified slug across CLI commands, `coga status`, and notifications.
  Two sibling directories may therefore reuse a leaf name, and a nested task's
  bare leaf does not resolve on its own. Agents should use the composed
  prompt's exact task directory instead of reconstructing it from the slug.
  Coga reads this tree — `coga status <dir>` filters to a sub-tree — but
  never reimplements it. A task is a **single file or a directory**, whichever
  it needs: a self-contained task is a bare `tasks/<slug>.md`; a task that needs
  attachments is a `tasks/<slug>/` directory holding `ticket.md` plus the
  siblings. (`<slug>.md` and `<slug>/`
  must not both exist; promotion is `mkdir <slug>/ && mv <slug>.md
  <slug>/ticket.md`.) A `README.md` is never a task — it is documentation for
  the directory it sits in, so a task sub-directory documents itself the same
  way any other directory does. Either way the ticket is YAML frontmatter + body, then a
  fence line `<!-- coga:blackboard -->` followed by the free-form blackboard
  region (the workspace shared between human and agent). The append-only audit
  trail is not in the task file — it lives in one repo-global `coga/log.md`
  (written by CLI commands only), each line tagged with its task ref.
  A directory-form task may reserve the exact sibling name `ticket.py` for its
  deterministic launch phase. Launch stats that one path and subprocesses it;
  core never imports from the task directory. No other attachment changes
  dispatch, so an agent-called `run.py`, test helper, or reproduction script
  remains an ordinary file. File-form tasks have no siblings and are therefore
  agent-only.
- **Contexts** are domain knowledge — what's true about the world.
  Project-local contexts live in the repo's configured contexts directory —
  `coga/contexts/` unless `[layout] contexts` moves it (see "The contexts
  directory is relocatable" below); bundled Coga batteries live
  in the installed package's `bootstrap/contexts/` resources. Attached to
  tickets via `contexts:` frontmatter list. Local contexts override bundled
  contexts with the same ref.
- **Skills** are process knowledge — how to do a thing. Project-local skills
  live in `coga/skills/`; bundled Coga batteries live in the installed
  package's `bootstrap/skills/` resources. Attached to **workflow steps**, not
  tickets. Local skills override bundled skills with the same ref. The `skills:`
  ticket-level frontmatter field exists for skill refs that apply to the
  ticket as a whole; `bootstrap/ticket` is the authoring interview and must
  never appear there — `coga ticket` injects it into the launch prompt
  only, never persists it on the ticket.
- **Workflows** are ordered step definitions. A repo's own workflows live in
  `coga/workflows/`; package-backed reusable workflows (the core `code/*`
  loop, `code/with-self-review`, `docs/create-google-doc`,
  `docs/with-review`, and `digest/post`) live in
  package `bootstrap/workflows/` resources.
  Resolution is local-first, exactly like skills and contexts: a local
  `workflows/<ref>.md` overrides a bundled `bootstrap/workflows/<ref>.md`.
  Frozen into a ticket's frontmatter at creation, or when a bare workflow ref
  is activated. The snapshot preserves step metadata and routing, but a
  skill-less step still loads its inline instructions from the current named
  workflow definition. Deleting or renaming that definition, or removing a
  step's inline instructions, therefore degrades prompt composition and is a
  validation error for live tickets.
  Nothing ever re-freezes an existing ticket. `_freeze_workflow_ref`
  (`mark.py`) only converts a bare string ref and seeds `step: 1`; it is a
  documented no-op once `workflow:` is already a dict carrying a step. A
  `steps:` edit — an added `skills:` ref, a changed `assignee:` token, a new
  `requires:` gate — therefore reaches only tickets created afterwards, plus
  drafts still carrying a *bare-string* `workflow:` ref (hand-authored or
  guided-authored) when they are activated afterwards. Activation alone is not
  a refresh: `coga create --workflow <name>` freezes the snapshot at creation,
  so a draft made that way before the edit stays on the old steps no matter
  when it is activated, exactly like the tickets already in flight. Plan a
  workflow change around that whole parked population rather than expecting it
  to pick the change up.
  Adding `skills:` to a previously skill-less step has a second edge: from then
  on composition takes the skill layers *instead of* that step's inline prose,
  so any limit carried only in the prose has to be restated inside the skill or
  it silently stops reaching the agent.
  Each step may declare an `assignee:` role token (`owner` | `human` |
  `agent` | `other-agent`); on bump, the token resolves against the ticket's
  matching role field and rewrites `assignee:`. `other-agent` resolves to the
  ticket agent's explicit `[agents.<type>].peer` when set, otherwise to the
  single other configured type. This keeps two-agent repos configuration-free
  while making three-agent repos declare the intended reviewer instead of
  guessing. `peer` is one-directional: configuring Claude's peer does not
  configure Codex's. The token drives peer-review flips (e.g.
  `code/with-review`) and agent-rotation relaunches. Steps without one leave
  the assignee unchanged. Validation checks every frozen `other-agent` step
  against current config as an error, even before the ticket enters that step.
- **Recurring templates** live in `coga/recurring/`. `coga recurring`
  invokes the fixed `recurring-scan` recipe, which scans templates, creates
  the current run at the stable
  path-qualified task ref `tasks/recurring/<name>/` (`recurring/<name>` in
  CLI/status/notifications), records the serviced period as a
  `created|reused <task-ref> for <period>` line in the repo-global
  `coga/log.md`, and launches the due
  ones. That log line **is** the serviced-period ledger, not just history: the
  scan validates its calendar-period key and compares normalized period
  positions to decide whether a period has already run. A malformed key is a
  visible template error in scans and status, never an "already ran" result. It lives
  there because the log is append-only and union-merged — a co-writer
  rewriting a region of a template's blackboard cannot destroy an appended
  line, and the record outlives the period task Dream reaps. A template with a
  reserved `ticket.py` sibling has a deterministic half; the creator copies
  that file into each period task, and launch runs it as an isolated subprocess
  with the period task's scoped secrets and `COGA_TASK_*` metadata. Templates
  without it are agent work: ordinarily an agent workflow on the period task,
  or a frozen one-hop bootstrap launch when the template declares `delegate:`.
  Nothing declares deterministic execution — there is no `recipe:` or mode
  field.
  Every created task uses the same ticket, workflow, lifecycle, and blackboard
  machinery as any other task.
  `coga recurring --all <path>` is a parent dispatcher: it discovers Coga
  repos below the path while pruning dependency/tool-state, `_`-prefixed
  directory trees, and Coga temporary-control parents proven by their stable
  prefix plus owner marker. That exclusion applies even when the scan root
  contains the system temp directory. Workspaces rejected by Coga's intentional config guards —
  including a missing local `user` or a stale-key migration error — are not
  scheduler targets: the parent reports one unconfigured-repo count, does not
  dispatch them, and does not fail because of them. It groups the remaining
  eligible control checkouts by their resolved configured git remote plus the
  Coga workspace's path within the git checkout, and invokes one checkout in
  each group once (preferring the first locally configured checkout already on
  its control branch). Later checkouts of that same remote workspace are named
  and skipped, while distinct Coga workspaces in one monorepo still run. One
  scheduler entry therefore cannot race one control branch through multiple
  worktrees. Each dispatched child must fetch/rebase its checked-out control
  branch successfully before scanning. A child whose checkout is not on the
  control branch at all no longer fails the repo: the branch is free by
  definition, so the child checks it out in a temporary linked worktree under
  the system temp dir. If the local branch itself is missing, Coga seeds it
  from an exact command-scoped fetch rather than requiring a remote-tracking
  ref, so narrow clones work without trusting shared `FETCH_HEAD`. The child
  re-dispatches from the mirrored Coga workspace itself — the checkout
  directory for a root layout, or the nested Coga directory in a monorepo —
  and normally removes the worktree afterwards.
  The operator's branch, tracked and untracked project files, and stash are
  untouched; the machine-local run transcript is copied into that workspace's
  gitignored `.coga/recurring-runs/`. Every ordinary sync, ledger, and push
  path applies unmodified because the run really is on the control branch.
  Only deterministic `ticket.py` phases run that way — agent templates are
  named and skipped with that reason, not the misleading "requires a TTY";
  existing periods are admitted from their frozen materialized `ticket.py`,
  not the mutable template. Because that script may be one half of a hybrid
  period, its presence is not permission to spawn an agent: the inner run
  carries a hard refusal through shared launch, keeps completed script output,
  and pauses the exact period if agent work remains. The inner scan owns a
  separate process session; once its handle is known, cancellation signals the
  whole process group and reaps its leader before removing the checkout. If an
  interruption lands after a possible fork but before that handle and process
  group can be published, the current cleanup retains the registered checkout
  for manual reconciliation. A versioned SIGKILL-survivor marker carries the
  repo, branch, workspace, wrapper PID, and inner spawn state/process-group ID.
  A later run removes that exact Coga worktree only after both known processes
  are dead; it also retains the ambiguous spawn window. For every known-safe
  state, normal and stale cleanup first copy machine-local run records into the
  durable checkout, retaining the worktree if that transfer fails.
  `git worktree add`
  doubles as the concurrency lock, since git refuses to check one branch out
  twice: a second sweep, or an unrelated worktree already holding the branch,
  keeps the loud refusal. A *diverged* control checkout still fails loud; only
  a human can reconcile those commits. TOML parse errors and operational
  failures still fail that repo, and the parent keeps sweeping before returning
  the aggregate result, listing temp-worktree services separately from ordinary
  sweeps. `--force` is the explicit schedule/status bypass and composes with
  the parent sweep.
- **Bootstrap tickets** are stateless launch targets. With only `ticket.md`
  they compose an agent prompt; with the exact sibling `ticket.py` they run
  deterministically with no task lifecycle or blackboard. No status, no
  workflow. Resolution is **local-first**,
  exactly like skills/contexts/workflows: `coga launch bootstrap/<name>`
  checks a repo-local `coga/bootstrap/<name>/ticket.md` before the package
  `bootstrap/<name>/ticket.md` resource. Used for ticket-less re-entry points
  like `coga launch bootstrap/orient` (the `chat` alias) and command tickets
  such as `coga resolve-conflicts`. Trailing launch args (`coga launch <target>
  [ARGS...]`) arrive at an agent as ordered values in an appended `## Launch
  arguments` prompt block; a deterministic `ticket.py` receives no operands in
  v1. Repository-independent parameterized package commands use the registered
  recipe surface instead:
  `coga open-pr` is a default alias for the registered `open-pr` *recipe*,
  because a fixed name in `runner.RECIPES` is a genuine package command whose
  implementation belongs in importable core; `coga resolve-conflicts` is the
  agent-backed command ticket and consumes its optional PR selector from the
  prompt arg block. A repo mints its own agent-backed or no-operand
  deterministic `coga <verb>` with a local command ticket plus an `[aliases]`
  line — zero core Python. `coga launch`
  does not create new tickets merely because a target is under `bootstrap/`;
  use `coga create` for that.
- **Bundled batteries** are package-backed core skills, contexts, reusable
  workflows, hooks, and launch targets shipped in the installed package.
  `pip install coga` puts them in the wheel; `coga init` does not
  materialize them into `coga/bootstrap/`.
  Runtime resolvers read package resources directly after checking local
  overrides. Optional domain skills declared in Coga's managed-skill manifest
  install into `coga/skills/` through the public skill installer instead of
  being copied from templates; install failures for optional skills warn
  without breaking offline init. Copy a skill or context to the matching
  `coga/skills/` or configured-contexts-directory ref to override it.
- **Dream** is Coga's generic ticket cleanup pass. It is a recurring task
  template (`coga/recurring/dream/`) plus a `dream` alias — not a
  built-in command. `coga recurring` creates and launches it when its
  weekly schedule is due; the `coga dream` alias (`recurring launch dream`)
  creates and launches it on demand. The parent task runs six ordered phases:
  two registered recipes invoked directly, two sharded subagent scans, a
  delegated Retro pass, and a disposition phase. Its body scans the ticket
  set, runs fixed Coga housekeeping, proposes cleanup, and writes reviewable
  results to its blackboard. Retro owns preserving unresolved adjacent bugs
  parked on completed tickets' blackboards as durable known failure modes.
  The evidence and remaining follow-up move into a fitting context in the
  same reviewable PR that deletes the source ticket; finishing the original
  task does not resolve its adjacent bugs.
- **REM** is repo/user-specific recurring maintenance. A REM run is an
  ordinary recurring task whose body defines that repo's operational checks,
  domain skills, output conventions, and review gates.

Contexts and skills both use the SKILL.md format (frontmatter `name`
+ `description`, then body). Zero proprietary extensions — same format
Claude Code and Codex use.

## Canonical ticket frontmatter

Every ticket carries the same canonical key set. These names are
reserved — no extension or alias may collide with them:

`slug`, `title`, `status`, `owner`, `human`, `agent`,
`assignee`, `watchers`, `workflow`, `step`, `contexts`, `skills`, `delegate`,
`period_generation`, `launch_generation`, `secrets`.

That is `ticket.CANONICAL_TICKET_KEYS`, which
`config._RESERVED_TICKET_FIELD_NAMES` reuses to reject extension collisions;
it is also the set `validate.REQUIRED_TASK_KEYS` plus `OPTIONAL_TASK_KEYS`
admits.

`slug` is the task's path-qualified reference, recorded on the ticket for
legibility (the path under `tasks/` stays the addressing source of truth).

`delegate` is an optional, system-authored dispatch snapshot reserved for a
materialized task directly under `tasks/recurring/`. Creation copies its
template's `bootstrap/<name>` value into the period ticket; sweeps, named
retries, and direct `coga launch recurring/<name>` calls read only that frozen
value. Ordinary tasks may not declare it.

`period_generation` is likewise system-authored and reserved to a materialized
task under `tasks/recurring/`. The creator stamps it once per stable-path
generation and the runner's start lease reads it back as a bounded witness;
templates and ordinary tasks that declare it are rejected. See `coga/recurring`.

`launch_generation` is megalaunch's transient,
durable session-claim token. A Git-backed start or resume first publishes it as
`pending:<uuid>` while the spawned child is held before exec. Every Coga task
publisher seals that exact pending control revision, and ordinary `coga launch`
refuses it. Only after the supervisor delivers the child gate does megalaunch
remove the prefix and strictly publish the same UUID; the plain token means the
session was admitted and is available to ordinary explicit recovery. Another
megalaunch may not rotate either form. Advancing the workflow or marking the
admitted session blocked, paused, done, or canceled clears it, as does
activation. Git-disabled launches use the plain token behind the local release
barrier. Both generation fields are system-owned optional fields, never
repository extensions.

`secrets` is nullable and declared **inline** — there is no central
`[secrets]` catalog. Absent / `null` / `[]` inject nothing; otherwise it is a
list of single-key maps `- NAME: <ref>` where `<ref>` is an
`op://vault/item/field` 1Password reference (resolved live with `op read`) or
an `env:VAR` indirection (read from the operator's environment). At launch each
ref is resolved and injected as env var `NAME`; the source `env:VAR` is
scrubbed so the child sees only the scoped name. A bare-string entry (the
removed catalog-key form) or a raw literal value is rejected — a literal secret
may not live in a git-committed ticket. Secret names beginning with `COGA_` are
also rejected because Coga reserves that namespace for launch metadata and
control variables.

A repo may declare additional fields under `[ticket.fields.<name>]` in
`coga.toml` — see "Ticket frontmatter extensions" below.

## Ticket frontmatter extensions

Per-repo frontmatter fields are declared in `coga.toml`:

```toml
[ticket.fields.docket]
description = "USPTO docket number"

[ticket.fields.priority]
description = "P0/P1/P2 triage tier"
values = ["P0", "P1", "P2"]
default = "P2"
required = true
```

Each declaration accepts four keys: `description` (required string),
`values` (optional enum), `default` (optional string), `required`
(optional bool). No other keys, no nesting, no types beyond string.

Three mechanisms honor the spec:

- `coga create` / `coga ticket` write every declared field into the new
  ticket below the `# --- extensions ---` marker, seeded with the
  declared default (or `""`).
- `coga validate` enforces the schema — declared-but-missing fails
  loud; an enum violation fails loud; an undeclared key not in the
  canonical set is treated as an orphan (warn-only) so removing an
  extension is symmetric.
- `coga mark active` refuses to activate a ticket whose `required`
  fields are empty.

Extensions live in the same frontmatter the prompt composer already
reads, so no extra layer is needed — the field is in every composed
prompt by virtue of being on the ticket.

## The contexts directory is relocatable

Contexts are the one Coga primitive humans hand-edit as prose, and burying
them inside the machine-owned `coga/` tree puts them out of reach of the tools
people actually write docs in. So the directory is tunable:

```toml
[layout]
contexts = "docs/contexts"
```

Unset — the default — contexts stay at `coga/contexts/`, byte-identical to
before the key existed. Set, the directory moves and *everything* follows it:
ref resolution, prompt composition, `coga validate`, `coga create` /
`coga ticket`, the git state sweep, authoring sync, and the `coga init` /
`coga uninstall` lifecycle. `cfg.contexts_root` is the single accessor; the
product-stranding guard also excludes both the current root and a former root
recorded at its control-branch base. Nothing else joins the live path itself.

**The value is anchored at the git checkout root, not at the coga root.** This
is the part a reader gets wrong. `Config.repo_root` is `<checkout>/coga/` in
the nested layout but *is* the checkout root in the root layout, so the same
relative path would name two different places. The checkout root sits above
the coga root in both, which makes `docs/contexts` mean
`<checkout>/docs/contexts` either way. A coga root nested deeper in a monorepo
(`tools/ops/coga/`) therefore spells the full `tools/ops/docs/contexts`.
`coga init` applies the same anchor when a scaffolded `coga.toml` sets the key:
it materializes and commits the initial local contexts at that destination.

Every failure mode is loud at config load, because the quiet one is
catastrophic: `resolve_context_path` falls back to the packaged
`bootstrap/contexts/` batteries on a miss, so a mistyped *directory* would let
`coga/architecture` keep resolving to the bundled copy while every repo-local
context silently vanished from composed prompts. So load rejects an absolute
path, a `..` escape out of the checkout, the checkout root or another ancestor
of the coga root, symlinked path components, Git pathspec metacharacters that
could broaden the state sweep, Git's administrative directory or a nested
checkout, a directory that does not exist or is not a directory, and a repo
with no checkout to anchor against. A configured root must also contain at
least one tracked or unignored
file, must not itself be ignored, and must not contain an ignored real context
`SKILL.md`, so Git can reproduce everything Coga composes in a fresh clone;
use a trackable `.gitkeep` when the root is intentionally empty. The ignored
`_template` scaffold is exempt. The per-ref local-first fallback is unchanged
— that is how bundled batteries work.

The CLI reloads config at the end-of-command publication boundary, because a
long-running agent session can change the setting after dispatch. When the
setting changes, the state sweep finds the most recent distinct contexts root
in committed config history and commits tracked deletions from that former root
along with the destination. It does not keep sweeping the vacated root:
unrelated new files created there remain ordinary repo content.

`[layout]` is shared `coga.toml` policy and is rejected in `coga.local.toml`:
where a repo keeps its prose is a fact about the repo, not about one machine.
`[agents.*]` is machine capability instead: local agent tables overlay shared
tables at the key level, so a machine can override one CLI setting or append a
locally installed type while inheriting the rest of the committed policy.

An agent's optional `peer = "<type>"` names the reviewer selected by an
`other-agent` workflow step. The target must be another configured type. The
mapping is deliberately global and one-directional per agent type; it cannot
route one agent to different reviewers by ticket or workflow. A per-ticket
reviewer was considered and deferred: this is the smallest policy surface that
unblocks a third agent, and a narrower override can layer on later if a real
need appears.

Note the asymmetry `peer` has with the rest of the local overlay. The other
keys only decide which binary this machine runs and leave no committed trace,
whereas resolving `other-agent` rewrites the ticket's `assignee:` — committed
content. A `peer` declared only in `coga.local.toml` therefore makes durable
ticket state depend on which machine performed the bump. That is accepted:
declaring the peer locally is how a machine with a third agent installed wires
itself up without committing a type its teammates do not have. A repo that
wants one answer for everyone puts `peer` in `coga.toml`, where it is shared
policy like any other committed default.

## Config loading fails loud on unknown keys

`load_config` validates `coga.toml` **and** `coga.local.toml` against a fixed
schema. Any unrecognized key, at **any level of a fixed-schema table** —
top-level sections, `[notification]`, `[notification.slack]`, `[git]`, `[launch]`,
`[layout]`, `[ticket]`, `[agents.<name>]` — raises `ConfigError` naming
the offending key and listing the valid ones, in either file. This generalizes
the enforcement `[ticket.fields.*]` already had: a misspelled `[notification.slak]`
no longer silently resolves to "no webhook" and takes Slack dark. Adding a new
config section means adding it to its table's allowlist, or the next command
fails loud.

Two carve-outs keep it honest:

- **Free-form maps stay open.** `[aliases]`, inline `secrets`,
  `[notification.slack.gifs]`, and `[notification.slack.users]` map user-chosen
  names to values, so their *keys* are data, not schema — they are never
  rejected.
- **Deprecated / known-but-rejected keys run their dedicated migration errors
  *first*.** Top-level `[assignees]` and `[slack]` tables, a `[secrets]` table in
  coga.local.toml, and the removed `[agents.<name>]` keys (`auto`,
  `skip_permissions`, `skip_permissions_argv` — the 0.2.0 scaffold wrote `auto`)
  each raise their tailored guidance before the generic unknown-key check, so
  the friendlier message survives rather than being swallowed by a generic
  "unknown key".

## Workflow gated at activation, not draft time

`coga create` takes an
*optional* `--workflow <name>`. A workflow-less draft is a valid authoring
state — drafting captures intent before its shape is settled.

The bumpability guarantee moves to activation. `coga mark active` refuses
to activate a ticket that has no workflow, with an error pointing at either
`--workflow` or `coga ticket` for guided authoring. This closes the same
failure mode — a launched ticket no `coga bump` can ever advance — at the
moment work is approved rather than the moment it is drafted, so a
half-formed draft is never blocked on a workflow decision it isn't ready to
make.

The rule is symmetric, and `coga validate` enforces the other half: a
workflow is mandatory everywhere *except* `draft`. A workflow-less
`active`/`in_progress`/`blocked`/`paused` ticket is a structurally stuck task
that no `coga bump` can advance, so the validator reports it as an **error**
(`active-no-workflow`) — the activation gate and the validator now agree
instead of the validator nagging the one state (`draft`) where workflow-less
is allowed. A workflow-less terminal ticket (`done` or `canceled`) is closed,
so it is left alone.

For those same live statuses, validation also requires a frozen
`workflow.name` to load its current workflow definition. Each frozen step with
no `skills:` must still have non-empty inline instructions under the matching
`## <step-name>` heading in that definition. Both failures are errors because
inline prose is not part of the frozen snapshot: launch otherwise falls back
to a missing-workflow or no-instructions placeholder. Draft and terminal
tickets are left alone.

`coga ticket` (guided authoring) fills the workflow in through its
interview skill. The `recurring-scan` recipe, on-demand `recurring launch
<name>` (including the `coga dream` alias), and `coga retire` create their
own one-shots straight to `active`
by calling `create_task` directly — but they are **not** workflow-less
exceptions: a template that declares no workflow (and every retire task)
creates with the one-step `direct/body` workflow, which runs the ticket
body's ordered phases directly. There is no sanctioned workflow-less active
task; the invariant holds for machine-authored tasks too.

Validation also resolves workflow-step skills directly from materialized
recurring templates, rather than waiting for the scheduler to create an active
period task. Generic missing refs list both paths Coga checked; known removed
bundled refs may replace that list with specific cleanup instructions.

## Two state machines per ticket

- **Control plane (`status`)** — `draft`, `active`, `in_progress`, `paused`,
  and `blocked`, plus the terminal outcomes `done` and `canceled`. Governs
  *whether* work happens. The shared `coga.mark` finalizers own the
  `draft`/`active`/`paused`/`done`/`canceled` writes; the `coga mark` command
  exposes them directly, while a final-step `coga bump` delegates to
  `mark_done`.
  `coga block` owns the `blocked` transition, and `coga unblock` resolves
  open blocker asks and moves `blocked → active` while preserving `step:`.
  `coga launch`
  flips an `active` ticket to `in_progress` when its script or agent work
  begins, and —
  since launching is itself the readiness signal — also performs the
  `mark active` step inline for a ticket that is still `draft` or `paused`
  before that flip. `coga mark canceled <ticket> --message "<reason>"` accepts
  every non-terminal status, requires the audit reason, and clears `step:`.
  Cancellation from `blocked` leaves the blocker text as historical blackboard
  context. Both `done` and `canceled` are terminal: launch refuses them and no
  transition reactivates a canceled ticket. A `blocked` ticket is
  waiting on a concrete answer; an **interactive** launch from a TTY resumes
  it inline (`blocked → active → in_progress`, `step:` preserved) and the
  composed prompt gains a resolve-or-re-block preamble listing the open asks
  verbatim, so settling them with the human is the session's first job —
  recorded via `coga unblock <slug> --answer`, which on an already
  `in_progress` ticket resolves the asks without touching status or step.
  If any resumed phase exits before recording an answer, launch returns the
  ticket to `blocked` so blocker queues keep reporting it. This includes a
  `ticket.py` phase that fails, pauses, closes, or advances before an agent
  session starts; an unanswered ask wins, and launch restores the original
  live step and its assignee when a terminal transition cleared them. An
  invalid unassigned baseline fails closed instead of inheriting a later agent
  and misrouting the ask. TTY-less
  launches keep refusing a blocked ticket until `coga unblock` records the
  answer. `bump` owns workflow progression and enforces
  `status: in_progress` for a forward bump; at the terminal boundary it
  delegates the status transition to `mark_done`.
- **Data plane (`step`)** — current position in the frozen workflow.
  Format `N (step-name)`. Owned entirely by `coga bump`. Bare `coga bump`
  advances one step — only from `in_progress` — or marks the ticket `done`
  and clears `step:` when the current step is final; a human outside a
  supervised launch may rewind to an earlier step with `--to` or
  `--backward`. A rewind is reposition-only: it accepts `active`,
  `in_progress`, and `paused`, writes `step:`, may re-resolve `assignee:` for
  the target step, and never changes status. An `active` or `paused` rewind
  must target a configured agent so the human can resume it with `coga launch`;
  it refuses a human or unassigned target because ordinary launch is a hard
  handoff and a forward bump requires `in_progress`. An already `in_progress`
  ticket may rewind to either kind of target. Rewind also refuses a `blocked`
  ticket (run `coga unblock` first, which owns blocker resolution) and the
  terminal statuses, which have no `step:` to move. Rewind is an exceptional
  human debug/recovery operation, not normal lifecycle progression. Whenever
  its guarded publication is not confirmed — status refusal, transport failure,
  or no configured remote — Coga deliberately leaves the local debug mutation
  available for inspection, either dirty or in local history. The operator must
  reconcile that checkout with control before another mutating Coga command,
  branch push, or merge; read-only inspection remains safe. Pausing preserves
  the step; cancellation clears it.

Tickets without a `workflow` field have no steps and move through
statuses directly via `coga mark`. `coga bump` refuses them.

The split is deliberate: each state change has one shared writer. `coga create`
authors a draft, the `coga.mark` finalizers flip status across the lifecycle,
`coga bump` moves steps and delegates final completion to `mark_done`, and
`coga launch` drives the target's deterministic and/or agent phases — bringing
a `draft` or `paused` ticket to `active` first (reusing `coga mark active`),
then flipping `active → in_progress` as work begins.

## Ticket launch phases and registered recipes

There is no ticket execution-mode field and workflow skills remain prompt
contracts, not executable plugins. Instead launch checks the selected
directory for one fixed `ticket.py` sibling. When present, it subprocesses that
file headlessly before agent setup. The script receives task identity, current
step, and declared secrets, but no operands. A zero exit plus an open step
falls through to the assignee's agent; a completed step or terminal lifecycle
does not. After a step advance, launch repeats the deterministic phase only for
another configured agent-owned step; a human or unassigned handoff returns
control to the caller. Lifecycle and audit sync may move a control checkout, so
launch reloads config, ticket, target, secrets, and the fixed entry-point stat
after the last pre-script sync; a removed `ticket.py` becomes an agent-only
handoff instead of executing a stale path. Without `ticket.py`, launch goes
directly to the agent path. What a strict human assist must prove around that
script phase is in `coga/launch-internals`.

Only an actual agent phase composes the ticket prompt and spawns the
assignee's CLI in a live REPL, so only that phase requires stdin and stdout to
be TTYs. `coga bump`, `coga mark done`, `coga mark
canceled`, and `coga block` signal the session-scoped
`$COGA_DONE_SENTINEL`; the supervisor tears down the REPL, re-reads the ticket,
and either starts a fresh agent process for the next agent-owned step or stops
at a human handoff, terminal state, blocker, no-progress exit, or non-zero
exit. A stateless bootstrap agent has no lifecycle transition, so its final
`coga slack --task bootstrap/<name> ...` FYI is the completion signal.

A human-owned agent step remains a hard handoff when launched normally. An explicit
`coga launch <slug> --agent <type>` is the on-demand assist path: it selects a
configured agent for that launch only, prints the unusual assist in the banner,
and never rewrites the human `assignee:` on disk. The strict assist path is
entered only when the ticket is locally human-owned; an override on an
agent-owned ticket remains an ordinary launch. A human-step override without a
TTY is refused before recorded-checkout or PR validation. The proofs, leases,
and compensation behind that publication are in `coga/launch-internals`.

Blocked tickets can resume inline only from an interactive TTY. Their first
job is to resolve or re-block the open asks.

Every sweep ends with the **autofix loop**: the scan builds a structured
record of what each period task did (how the launch ended, resulting status,
and the period task's blackboard), one text-only agent call
reads that record, and a real problem becomes an `active` ticket under
`coga/tasks/autofix/` with the record committed beside it. That call is the
single place Coga spawns an agent without a PTY — one shot, text in, text out,
no REPL and no lifecycle, so it cannot answer a permission prompt; Coga
performs every mutation itself from the parsed reply. It lives behind the
registered `autofix-analyze` recipe for that reason, and it never changes the
sweep's exit code. `COGA_AUTOFIX=0` disables it. See `coga/recurring`.

Deterministic core jobs use `coga run <recipe> [args...]`. The fixed
`runner.RECIPES` table is explicit: there is no file discovery, config import,
or executable-skill plugin surface. Recipes receive ordinary argv, preserve
argument boundaries and option spelling, propagate their integer return code
and stdout/stderr, and re-derive `COGA_TASK_*` for instantiated recurring
tasks — including a ticket's own `ticket.py`, which may import a registered
recipe function directly. A recurring template's deterministic path is that
`ticket.py` sibling; without one, its period task is agent work and therefore
needs a TTY at admission. That agent work takes one of two shapes: by default
an agent session launched on the period task itself, or — with
`delegate: bootstrap/<name>` — a stateless bootstrap launch the sweep performs
in-process while keeping the period task's lifecycle bookkeeping. Only that
bootstrap session's scoped done sentinel completes the period; a natural exit
does not. The runner first completes a no-mutation launch preflight, publishes
the period start, then reloads and repeats target/config/secret/prompt/argv
derivation before the real spawn; the lifecycle sync is allowed to move the
control checkout without leaving stale instructions in the child. A final
pre-spawn lease requires the materialized period to remain `in_progress`, keep
the same frozen target, and match its post-publication ticket snapshot; any
concurrent completion, replacement, or edit refuses the child. Creation
freezes the target into the materialized period ticket, and all retries —
including direct `coga launch recurring/<name>` — route from that snapshot
reread after reconciliation rather than mutable template frontmatter or stale
scan cache. A direct launch first requires a verified recurring control
catch-up and re-resolves the exact period ref. Delegation is agent-only: a
bootstrap target carrying `ticket.py` is rejected before period creation;
deterministic recurring work belongs in the recurring template's own
`ticket.py`. A template therefore never instructs its agent to shell out to a
nested `coga launch`. `delegate:` and a template `ticket.py` sibling are
mutually exclusive; a materialized delegated period that later acquires its own
`ticket.py` is likewise invalid and refused rather than selecting one signal.

There is no `autonomy:` field. The old `auto`, `skip_permissions`, and
`skip_permissions_argv` agent keys are removed; config load rejects them with
a dedicated migration error.

### Megalaunch dependency drain

After a bare megalaunch sweep, Coga re-lists blocked tickets owned by the
current operator in the same directory scope and looks for exact
path-qualified task slugs in their open blocker text. A named dependency is
satisfied when its ticket is `done` or when a task ref seen earlier in the run
has disappeared (finished work may retire and delete its ticket). Megalaunch
first validates the prospective activation, then records that activation and
an automatic blocker answer naming the dependency as one exact mutation. With
Git enabled, both changes reach control through one whole-ticket
compare-and-set; only then does the normal launch claim lease the resolved
`active` revision. The resolution therefore exists before prompt composition,
so an unattended retry never inherits the interactive blocker-resolution
preamble. A drained ticket that refuses to activate (no workflow, an
unfreezable `workflow:` ref, an empty required extension field) keeps its open
ask and stays `blocked`, so `coga unblock` and the blocker reminders can still
act on it. An ordinary lost publication restores the same blocked revision;
an ambiguous accepted push retains its generated evidence for reconciliation.

The drain is a fixed-point walk: after each actual launch it restarts from the
oldest blocked ticket, and a complete pass with no launch ends the run. A task
is drained at most once per run, every real retry attempt shares `--max-tasks`
with the main sweep, and a late exact-gate reclassification consumes no budget
in either path. The summary keeps one result row per task with a separate
`drained` count. Explicit `--pick` and `--relaunch` selections do not run this
drain, because completing a selection must not expand into unpicked work.

### Step completion gates (`requires:`)

A frozen workflow step may declare `requires: <token>`. Before `coga bump`
advances **off** that step, it runs the token's predicate against the task
blackboard. A falsy result fails loud with the command that produces the
artifact. This is a data check, independent of which agent owns the step;
human rewinds (`--to` / `--backward`) are never gated.

Two tokens are registered. `requires: branch` gates the `implement` step of
all three packaged `code/*` workflows: it passes only when a usable `branch:`
*and* a usable `worktree:` are recorded under `## Dev` — a `(`-prefixed
placeholder reads as absent. `coga bump` sees only the ticket copy in the
checkout it runs from, so a `## Dev` write made inside the feature checkout
does not satisfy a bump run from the control checkout; the remediation names
both moves that fix it, and warns that a stale `## Dev` from an earlier attempt
satisfies the gate while stranding the current one.

`requires: pr` gates `code/open-pr`, an ordinary agent step. The agent runs
`coga open-pr <slug>` — a default alias for `coga run open-pr <slug>` — from
the checkout that owns the live ticket: the primary control checkout when
`worktree:` is a separate linked checkout, or the primary checkout's recorded
feature branch when both are the same checkout. The witness variables and
sync rules that make that safe are in `coga/launch-internals`. A skipped
command cannot be papered over with a bump because the gate reads the
recorded artifact.

The registry stays generic: a token owns its own predicate, remediation, and
transition policy — only `pr` sets `publish_current_branch`, which is what puts
the transition commit on the feature branch — and `bump` never hardcodes a
`code/*` skill name.

## Prompt composition

`coga launch` first checks only the selected target directory for the exact
`ticket.py` sibling. If present, it runs that file headlessly under the current
Python interpreter before agent-type, agent-CLI, prompt, or push-auth
preflight. A blocked ticket pays only its TTY/open-ask resume gate first. The
strict human-assist exception aligns the recorded PR checkout and publishes
its leased lifecycle before user code, so stale or unshared ticket code never
runs. After any lifecycle/log sync that can move the checkout, launch reloads
the final config, ticket, secrets, and entry point before exec. A nonzero exit
halts, and its code is audited/notified even if user code deleted or malformed
`ticket.md`. On zero, launch re-reads the ticket: a
completed/advanced/blocked step is not run by an agent, while a still-open step
continues into the agent path and sees any blackboard findings the script
appended. The launcher never advances a step for the script. This is a
fixed-path stat on one already-selected ticket, not recursive discovery or an
executable skill-plugin API.

When an agent phase remains, `coga launch` builds one composed prompt and
writes it to a temp file. Layers, in order:

1. Base prompt (`prompt.md`) — a package resource, not a file under `coga/`.
   It is neutral on conduct: it cross-references the selected layer below
   rather than carrying a default that something later overrides.
2. Session conduct — exactly one package resource, selected by launch context
   (see below). Never stacked, never appended after the task layers.
3. Repo context (`coga/context.md` — top-level facts about this
   surface).
4. Ticket contexts (everything in `contexts:` frontmatter list).
5. Ticket-level skills and the current workflow step's skill (if any).
6. The ticket itself, last and contiguous, in the order it sits on disk:
   `## Description`, then the inline `## Context`, then the blackboard region
   below the fence — those three regions and nothing else (see below).

Layer 6 is one block on purpose. These were three separate layers scattered
across the prompt, with skills wedged between them, back when they were three
files (`ticket.md` / `blackboard.md` / `log.md`); the single-file task format
collapsed the files and the split outlived its reason. They remain distinct
entries in `--prompt-report` so the blackboard can still be sized on its own —
that line is how a bloated blackboard gets noticed — but they compose as one
contiguous block.

**Layer 6 is a three-region extract, not the whole ticket body.** The section
extractor takes one `##` heading and stops at the next `##`, so composition
carries exactly `## Description`, `## Context`, and the blackboard region below
the fence. Every other `##` section above the fence is dropped silently — no
warning, no `--prompt-report` line, nothing the authoring step can observe.
Content a later step must read therefore has to sit under one of those two
headings or on the blackboard. A sibling `## Acceptance Criteria` or
`## Proposed Shape` is legible to a human reading the file on disk and
invisible to the launched agent. This is a constraint on how tickets are
written, not a guarantee about what the agent sees.

**Session conduct is selected, not appended.** The escalation boundary is
layer 2, and exactly one conduct resource is ever composed. The selector is
the caller's **ephemeral launch context** — `attended`, `megalaunch`, or
`recurring` — passed to `compose_prompt()` / `compose_prompt_report()` as
`launch_context`. It is never ticket frontmatter, never config, and never a
user-facing flag on an ordinary launch: how a session executes is a property
of the invocation, not of the task. `--prompt-report` names the selected
resource on the `session_conduct` line, and a missing one is a `ComposeError`
at the same preflight boundary as any other dropped layer — before the launch
publishes `in_progress` or spawns.

- `attended` (`prompt-attended.md`) — ordinary `coga launch` including a
  human-typed direct period-task launch, `coga chat`, guided `coga ticket`
  authoring, and every recurring spelling run with `--interactive`. A human is
  in the REPL: ask and wait, state a plan and let them confirm before
  substantive code, and reserve `coga block` for an explicit request to park
  the ticket.
- `megalaunch` (`prompt-megalaunch.md`) — `coga megalaunch`. The REPL still
  uses a TTY for live streaming and human interruption, but the TTY is
  transport, not an attending human, so queue execution must not pause for
  plan approval or wait on a question. The agent states a plan and continues,
  and when unavailable input truly prevents progress it runs a terminal
  `coga block` so the owner is notified; only `bump`, `mark done`,
  `mark canceled`, or `block` releases the queue. It also carries the
  dependency-drain rule (name the blocking task's exact path-qualified slug in
  `--reason`) and the narrow exception for a blocked task the human explicitly
  picked: its composed resolve-or-re-block preamble may discuss those
  already-open asks with the picker, then unblock and continue or terminally
  re-block. That does not turn the queue's TTY into general attendance; any
  new unavailable input still takes the terminal block path.
- `recurring` (`prompt-queue.md`) — runner-owned recurring execution: the bare
  sweep, `--force`, `coga run recurring-scan`, a named `recurring launch
  <name>`, an ordinary period task's agent phase, and a delegated stateless
  bootstrap session. Same queue posture, plus the stateless-bootstrap rule: a
  `bootstrap/<name>` ticket has no lifecycle to bump, so its final targeted
  `coga slack` is what releases the session.

The two queue resources are deliberately complete rather than a shared
fragment plus caller-specific tails. Only one ever reaches an agent, so their
repeated wording costs no runtime tokens, and the highest-consequence policy
stays readable as one unit. The shared spawn seam still appends genuinely
invocation-only input after the task layers — `## Launch arguments` — but
never conduct.

The blocker-resolution preamble is an independent, state-derived layer: it is
task-execution context, not generic blocker context. Guided
`coga ticket` authoring explicitly omits it and removes `step:` only from the
ephemeral ticket projected into prompt composition. The persisted ticket keeps
its workflow position, but the authoring prompt receives no current
workflow-step execution layer. It still retains blocker text in the ordinary
blackboard layer, so revising a blocked ticket neither executes its task,
resolves its asks, nor changes it to `active`.
This is ephemeral launch context, not ticket state or a new autonomy
frontmatter field.

The agent gets all of this as one input. There is no follow-up
loading. One delivery caveat: the prompt rides the agent CLI's argv, and
Linux caps a single argument at 128 KiB. Launch swaps a composed prompt over
~120 KB for a short argv pointer telling the agent to read the prompt file
(kept on disk for the whole session) — same content, one indirection, instead
of a guaranteed `E2BIG` exec failure. A prompt that big is usually context
bloat; `coga launch --prompt-report` shows which layer to trim.

Note what is deliberately **absent**: the `coga/log.md` audit log is never
a composition layer. It is the one repo-global, append-only file, lives outside
every task directory, and never enters an agent's context, so it can grow
without bound. Only the blackboard region (layer 6) carries state forward into
the prompt.
The consequence is a hard division of labor: working state that the next run
must read goes in the blackboard (and is therefore composed, so keep it
small); lifecycle history goes in the log (never composed, so let it
accumulate). Superseded ticket designs remain in the blackboard under
`## Superseded designs`, following `dev/code`.
Draft activation is also the first-launch readiness gate for the blackboard.
The stock placeholder counts as empty, but substantive pre-launch notes —
authoring/evaluator sections such as `## Evaluator review`, `## Ticket
authoring notes`, or `## Proposals`, plus large custom scratchpads — make
`mark active` and launch-time auto-activation refuse before workflow freezing,
status changes, log writes, Slack posts, prompt composition, or agent spawn.
`coga validate` reports the same condition as an error and exits nonzero, so a
ticket writer cannot mistake an activation-blocking draft for a valid one.
The operator must merge durable requirements into `## Description` /
`## Context` first. If blackboard content is intentionally part of the run,
put it under `## Production notes`; that marker tells activation to leave
the blackboard alone. The `## Superseded designs` section is separately
excluded from synthesis checks and preserved by draft-authoring cleanup;
its presence does not exempt unrelated authoring notes. Later `paused→active` reactivations and forced
recurring reruns do not recheck post-launch blackboard growth.

An interactive launch's PTY supervisor tears down the REPL when the
session-scoped `$COGA_DONE_SENTINEL` file names the launched task — its sole
done channel. Because the signal is a side-channel file whose content must
match the launched task's session id, there is nothing in the composed prompt
or PTY byte stream to trip: an agent that reads, greps, or quotes a teardown
string at runtime cannot end its own (or a parent's) session, so the composer
returns the assembled prompt verbatim with no defusal step.

## Status is the signal

There is no task-ownership mutex. The ticket's `status` (`draft`, `active`,
`in_progress`, `blocked`, `paused`, `done`, `canceled`) is the signal that
someone is — or isn't — working on a task. `coga launch` accepts an `active` or
`in_progress` ticket directly, and treats a launch of `draft` or `paused` as
the readiness decision itself: the ticket is run through `coga mark active`
inline before the agent starts. On the agent path that activation is prepared
in memory before prompt composition, but its durable ticket/log write is
deferred until every refusing preflight has passed, immediately before the
`in_progress` transition. A missing layer, agent CLI, secret, push credential,
or other preflight refusal therefore leaves a draft or paused ticket unchanged
on disk. A `ticket.py` path activates when the script is about to execute,
because executing user code is already the start of work. Terminal tickets
(`done` and `canceled`) are
refused and left untouched; launching one must not restart its workflow. A
workflow-less or required-extension-incomplete ticket still can't be activated,
so those launches fail loud with the same remedy `mark active` gives. The
failure mode of two divergent workers (two blackboard edits, two PR branches)
is visible and recoverable in git; the cost of a hard ownership mutex (stale
lock state, `--force` flags, orphan-lock cleanup) is not.

A much narrower local **state admission/publication barrier** does exist. It is
an OS-released advisory lock held while a Coga command creates, replaces, or
removes a task ticket or writes blocker state, while a Coga command
stages/publishes state, and while a megalaunch child remains held across its
provisional audit append, final proof, and pipe release. A task-file mutation
therefore becomes visible either before the final proof or after the child is
irrevocably released, including when Git sync is disabled. For strict lifecycle
mutations, the captured-byte comparison, ticket replacement, and rollback
arming are one barrier-held operation. A failed strict lifecycle mutation also
compares and conditionally restores its
generated bytes while holding the barrier. Shipped blackboard writers use the
same read/transform/compare/write boundary, including blocker and reminder
updates, PR records, task-scoped recurring reports, run summaries, and
validation safe fixes. The low-level task-file splice remains config-free;
command and recipe callers own admission. The barrier never decides who owns a
task or whether one is launchable. Its inert lock file lives outside the
worktree; process exit releases the kernel lock, so there is no stale ownership
state or cleanup protocol. The supervisor masks SIGINT and SIGTERM across the
one-byte release and its local released-state update. A pre-delivery failure
retracts the provisional audit; an interrupt observed after delivery retains
the audit and treats the child as launched. Cross-checkout and cross-machine
coordination still comes from exact Git compare-and-swap publication.

## Identity and capability boundaries

"Who is acting?" and "what may this action use?" resolve to three boundaries.
Coga stays classical: local files and standard CLIs first, with no secret or
account state committed to git.

- **Local user / operator.** Coga does **not** own the human's identity. The
  operator is the OS user plus the local tools they already authenticate: `git`,
  `ssh-agent` / git credential helpers, and `gh`. Coga inspects these and fails
  with actionable setup hints (`gh auth login`, fix your git remote); it never
  stores a GitHub PAT or reimplements GitHub auth for normal human PR work. Git
  transport uses the user's configured remote; GitHub PR/API operations use
  `gh` auth.
- **Repo / install identity.** The repo is identified by the git checkout and
  `coga/` config. Coga creates no hosted account or telemetry identity.
- **Skill / task capability.** A task's *declared* capabilities are its
  ticket-level `secrets:` list, declared **inline** — each entry is a single-key map
  `NAME: <ref>` whose `<ref>` is an `env:VAR` or `op://vault/item/field`
  indirection (both safe to commit — they are pointers, not values; a raw
  literal is rejected). There is no central `[secrets]` catalog: the ticket
  carries the reference directly, and the trust boundary on what an `op://`
  reference can read is 1Password's own vault/service-account permissions, not
  a Coga allow-list. Launch resolves each ref live and fails loud when it
  cannot be satisfied (`op` missing / not signed in / `op read` non-zero, or an
  unset `env:VAR`) — error messages name the Coga secret name and reference,
  never the value. The extension seam for new reference providers is **prefix
  dispatch in `config.py`** (`parse_inline_secrets` / `select_launch_secrets`),
  not a provider registry: a future provider is another explicit branch on the
  same shared secret path.

  **This is a declaration, not a sandbox.** `config.build_launch_env()` starts
  from the **full parent environment** and removes only the source variables an
  `env:VAR` ref names, then adds back the resolved, scoped destination aliases.
  Every variable the operator's shell carries is otherwise inherited by the
  child. That normally includes `OP_SERVICE_ACCOUNT_TOKEN`, so a launched agent
  can run `op read` against anything that service account can reach regardless
  of what the ticket declared. The exact declaration can change the final
  environment: `TASK_OP_TOKEN: env:OP_SERVICE_ACCOUNT_TOKEN` scrubs the
  well-known name, while declaring that same well-known name as a destination
  restores or replaces it. That scrub removes only service-account-token auth
  through that variable; it does not log out an inherited personal `op` session
  or remove other CLI/desktop authentication. The `secrets:` list bounds what
  Coga *resolves and names* for a task; it does not otherwise bound what the
  task's process can reach. Real confinement needs process isolation Coga does
  not yet have.

## One shared agent-spawn path

Every command that triggers an agent routes through a single single-shot entry
point — `spawn_agent_session(...)` in `commands/launch.py`, "spawn one agent
once": compose (or accept an already preflighted `composed_prompt`) → write the
prompt file → build the agent command → spawn under the PTY watcher → log →
cleanup. Megalaunch supplies that preflighted prompt together with its already
resolved environment and agent, binding the inputs checked before lifecycle
writes to the eventual spawn. Its pre-write compare-and-swap prevents a stale
local write; when Git sync is enabled, deferred activation and every start also
compare-and-swap against the exact whole-ticket control revision and require
strict control publication before spawn. Two checkouts starting from the same
revision therefore cannot both acquire a launch claim. The unattended sweep
also reapplies its owner, status, blocker, and current-step gates to the exact
preflight reread rather than trusting its earlier queue classification; a
gate-only reclassification does not consume `--max-tasks`. An exact local
reread after synchronous `in_progress` publication prevents a peer change
during that sync from reaching spawn. On detached HEAD, strict publication
seals the exact generated claim bytes in a scoped detached commit and overlays
only those leaves on control, so concurrent sibling attachments survive and a
later broad state sweep cannot replay retained claim state over a peer edit.
The shared state guard treats that generation as system-owned and requires the
checkout's committed ticket baseline to match freshly fetched control before
any same-generation blackboard or session-ending edit lands. Each accepted
detached edit advances that baseline with another exact-leaf commit.
At the shared pre-audit
`validate_before_spawn` seam, megalaunch rereads those exact local bytes and
freshly fetches every effective control destination; the whole control ticket,
including the pending `launch_generation`, must still match. It repeats that
proof through `validate_after_spawn` after the PTY child exists but while the
supervisor still holds it before exec. Megalaunch then appends the launch audit
and repeats the same proof after that append, immediately before release. The
local state admission/publication barrier spans that append, final proof, pipe
write, and post-release admission callback; every same-checkout Coga lifecycle
writer and Git publisher waits. Across checkouts, every task publisher refuses
to replace a control ticket carrying `pending:<uuid>`. A lifecycle transition
that begins after the last fetch therefore cannot overtake the gate: it is
refused while pending, or observes the plain admitted UUID only after the child
can execute.

After successful gate delivery, but before dropping the local barrier, the
callback strips only `pending:` and strictly publishes that exact one-field
transition under the original whole-ticket lease. If the pipe write itself
fails, the supervisor runs admission compensation first: it removes the
provisional audit and keeps the session out of usage teardown before killing
the still-held child. A changed or unverifiable pre-release claim conditionally
removes only the owned audit line, refuses the child, and retains the pending
`in_progress` state for explicit reconciliation. A post-release admission
failure kills the child but retains its audit and a local `released:<uuid>`
witness, whether the publication definitely failed or its result is uncertain.
Thus the audit stays out of `log.md` until the PTY child actually exists, while
an edit during the append cannot release stale preflighted work or publish a
false audit. An audit failure likewise kills the held child, so no unrecorded
work starts. Another megalaunch never reclaims any claim form. Ordinary
`coga launch` refuses pending claims; for a released witness it first fetches
control, verifies the whole ticket is the matching pending or admitted
revision, and strictly publishes the plain UUID before starting the explicit
recovery session. A step advance or lifecycle transition that ends or parks
that admitted session clears it. Megalaunch never compensates a refused claim
backward to `active`: retained claim state is the human-legible reconciliation
evidence.
`coga launch`'s
`while True:` supervisor chain
(per-step CLI re-resolution, claude↔codex rotation, `COGA_SUPERVISED`, the
done-sentinel, respawn) **wraps** that call per step; the chain stays
launch-only and is *not* pushed into the shared unit. `coga ticket` authoring
routes through the same helper, expressing its differences as explicit
parameters rather than forked code: `secrets` (none for authoring —
least privilege), a greet-first `kickoff` token (`coga ticket` opts in;
`coga chat` / general launch stay silent), `discussion`, an authoring-only
ticket projection with no current step, and suppression of the launch-only
blocker-resolution preamble for guided ticket authoring.

Don't hand-roll the compose→spawn sequence in a new command. A forked copy
drifts — the authoring copies once diverged to a bare `subprocess.run` and lost
the PTY watcher (so interactive REPLs stopped releasing on the done sentinel).
Add a new command's difference as a parameter on the shared path instead.

Because that one call does compose → prompt-file write → log append *before* it
spawns anything, a `FileNotFoundError` escaping it is usually a missing **file**
(a skill or context that vanished under a concurrent checkout, an unwritable
prompt destination), not a missing agent CLI. Callers therefore catch
`repl_supervisor.AgentCliNotFound` — raised only where a spawn actually fails to
exec the binary — for the install-the-CLI remedy, and report every other
`FileNotFoundError` through `missing_launch_file_message`, which names the
offending path. A blanket `except FileNotFoundError` around the shared call is
the bug this replaced: it answered "a prompt layer disappeared" with
"'claude' not found", two lines after `shutil.which` had already located
`claude`. Note the asymmetry that made this easy to miss — on the PTY path a
missing binary is the *child's* failed `execvp`, surfaced as exit 127, so in an
interactive launch the CLI-not-found branch could essentially only be reached by
an unrelated error.

## Command Surface

The command reference lives in `coga/cli`. The important architectural split
is that foreground commands operate on files in the current `coga/`; there
is no server-side state behind them.

### Registered recipes

Deterministic Coga jobs that need a stable command surface live as importable
core functions in the fixed `runner.RECIPES` table and are invoked through
`coga run`. Keeping the registry explicit makes the available code legible
and reviewable; installed skills are process contracts, not executable
plugins. This remains the repository-independent parameterized command surface;
ticket-owned deterministic behavior can instead live in `ticket.py`, which
launch subprocesses without adding it to the registry. State-machine commands
(`create`, `mark`, `bump`, `block`, `unblock`,
`launch`) remain ordinary core commands, as do shared gates, parsers,
preflights, and config/secrets machinery. `megalaunch` currently lives in core
as the queue/drain orchestrator, but that is implementation inventory rather
than a settled home: the co-versioning proof or migration required to classify
it remains open under `coga/extension-model`.

`open-pr` and `delete-task` are registered recipes like the rest: their
implementations live in `coga.open_pr` and `coga.delete_task`, they take the
target task as ordinary argv, and `coga open-pr` / `coga delete` are the
spellings on top. The obsolete open-pr command ticket that once carried
executable siblings is gone.

## Dream's known-skill contract

Dream is not a plugin host. The body of the `coga/recurring/dream/ticket.md`
template — composed into each Dream task's `## Description` — owns an explicit,
ordered list of known skills it will run and is the only control point.
Dropping a SKILL.md under `bootstrap/dream/tasks/` does not enable it; there is
no recursive discovery, no registry, and no daemon. Adding another Dream skill
is a normal Coga code/docs change to that list.

The `ticket.py` classifier does not weaken that contract. It stats one reserved
path inside the launch target already named by the caller; it never scans
Dream's skill tree, adds a command to a registry, or imports a plugin. A file
appearing in one ticket directory affects only that ticket.

Dream's deterministic workers are plain skills whose known-skill contracts
name registered recipes. The shipped contracts live under
`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/tasks/<name>/`
as `SKILL.md` files. Dream phases 1 and 5 read those contracts and invoke
`coga run validate-drift` and `coga run cleanup-orphan-markers` directly from
the parent Dream task. The recipes inherit that task's `COGA_TASK_*`, so their
reports land on the Dream blackboard; no child worker task or worker workflow
is created. Dropping another skill in the directory still enables nothing:
the template's ordered known-skill list and the fixed core registry are the
two explicit control points.

Dream's decide-half subagent scans (the knowledge scan and the contract
audit) are skills too, but **prompt-only**: they live under
`bootstrap/skills/bootstrap/dream/scan/<name>/` (referenced as
`bootstrap/dream/scan/<name>`), a sibling segment to the deterministic workers'
`tasks/`. A prompt-only scan skill carries just `name` + `description`
frontmatter and its prompt contract as the body — no executable entry point and
no `## Known Skill Contract` block; that shape belongs to the deterministic
workers and is the wrong archetype to copy for a subagent scan. The phase skills
carry their classification and partition rules, while the sibling
`bootstrap/dream/scan/scan-protocol` skill carries their shared bounded-read,
durable-output, heartbeat, completion, and retry-supersession rules. The Dream
template body builds the scan index and append-only manifest, delegates each
phase across bounded shard subagents, reconciles only active leaf assignments —
at the barrier, and by distinct completing shard id rather than by counting the
completion lines in the shared append-only `progress.md` — and merges their
on-disk findings into `## Findings`; a final message is not the delivery
mechanism. Known limitation: the contract audit's own corpus globs
(the configured contexts directory, `coga/skills/**`) do not cover package-backed
`bootstrap/skills/**`, so the bundled Dream skills — the scan skills included
— sit outside the surface that audit reads.

Every launched agent and ticket script subprocess receives
task metadata as environment variables:
`COGA_TASK_SLUG`, `COGA_TASK_DIR`, `COGA_TASK_TICKET`,
`COGA_TASK_BLACKBOARD`, `COGA_TASK_STEP`,
`COGA_COGA_OS_ROOT`, and `COGA_REPO_ROOT`. Three further names complete the
namespace — `COGA_ASSIST_AGENT`, `COGA_ASSIST_BRANCH`, `COGA_ASSIST_PR`, ten
members in all — and are described below. There is no `COGA_TASK_LOG`: the
audit log is one repo-global `coga/log.md`, so a per-task variable naming it
was a leftover from the three-file task layout and nothing ever read it. Derive
the path from `COGA_COGA_OS_ROOT` if a script needs it. `COGA_TASK_STEP` is the frozen
`<n> (<name>)` value and is absent when the target has no workflow step. The
shared launch boundaries
**clear the whole namespace and re-derive it** from the launched task, so
nested work cannot inherit the outer task's paths — and a variable the target
does not export cannot survive by inheritance either. `COGA_COGA_OS_ROOT` is
the `coga/` root; `COGA_REPO_ROOT` is the host repo (its parent when `coga/` is
nested in a repo).

Five of the ten members are conditional, and that is the whole point of the
second one. `COGA_TASK_STEP` is absent without a current workflow step.
`COGA_TASK_BLACKBOARD` is absent for a stateless bootstrap target, which has no
blackboard. Because the blackboard is the final region of the single ticket
file, `COGA_TASK_BLACKBOARD` and `COGA_TASK_TICKET` carry the same path when
both are set — but they are not interchangeable and neither is redundant: the
*presence* of the blackboard variable is the capability signal, and its absence
is what makes a recipe write its report to stdout. `COGA_TASK_TICKET` is always
set. Its
`ticket.md` is normally a packaged resource, and a report writer handed that
path appends into a file that ships in the wheel (a repo-local
`coga/bootstrap/<name>/ticket.md` override is corrupted the same way). Recipes
already treat an absent blackboard as "write the report to stdout", and they
refuse a path outside a `tasks/` tree for the same reason — defence in depth
on the reading side, for a value inherited from an older process.

The other three conditional members carry the assist capability, and they are
exported together or not at all. `COGA_ASSIST_AGENT`, `COGA_ASSIST_BRANCH`, and
`COGA_ASSIST_PR` — the effective launch agent, the exact aligned feature
branch, and the recorded `pr:` URL — are set only once launch has verified a
strict human-assist checkout, for both the agent session and a `ticket.py`
subprocess. An ordinary spawn drops all three before exec, so nested work
cannot inherit an outer session's publish rights. In-session lifecycle commands
opt into strict publication only when the assist branch and expected-task
witness are both present and the witness names the current task. Once that
predicate selects the strict path, a missing recorded PR or effective agent —
or an unknown agent — is refused. A missing branch or expected-task witness,
or a witness for another task, selects the ordinary non-assist path instead.
Launch itself exports the complete scoped capability together; clearing the
namespace before an ordinary spawn prevents a partial outer capability from
silently reaching nested work.

Each known skill's `SKILL.md` carries a `## Known Skill Contract` section
with these fields:

- `Purpose` — the maintenance question this skill answers.
- `Runs` — exact command or manual instructions.
- `Inputs` — files, commands, APIs, or task state the skill may read.
- `May change` — exact files/refs/state the skill may edit, or `none`.
- `Action` — one of `report-only`, `proposal-only`, `pr-required`,
  `direct-fix`.
- `Idempotency` — how reruns avoid duplicate work.
- `Stop and ask` — conditions that require human review before continuing.
- `Output` — blackboard section, PR link, created ticket, or no-op.

Each registered recipe writes its own `## Dream Skill: <name>` section to the
Dream task's blackboard. The orchestrator appends one `## Dream Run Summary`
that lists each skill's result using a small fixed vocabulary:
`no-op`, `reported`, `partial`, `proposed`, `direct-fixed`, `pr-opened`,
`human-needed`.

Destructive behavior (deleting task directories, deleting git refs,
changing lifecycle state, touching secrets) is never implicit. A known skill may declare a direct destructive change only when
the rule is deterministic, narrow, and named in `May change`; otherwise it
must use `proposal-only` or `pr-required`. Repos that want a different
maintenance loop define their own task (e.g. `rem` under
`coga/recurring/`) with its own dispatch rules — that is user space and
is not plugged into bootstrap Dream.

## What this context does NOT cover

- Where files live in source / how to test (see `coga/codebase`).
- The "why" / philosophy (see `coga/principles`).
- Current iteration's open decisions (see `coga/current-direction`).
- Reusable compositions of these primitives — e.g. the spool, a blackboard
  used as a producer/consumer queue (see `coga/patterns`).
- The strict publication invariants behind launch, the recurring runner, and
  the `requires: pr` gate — recorded-checkout and PR-head proofs, leases,
  compare-and-set publication, compensation, admission generations (see
  `coga/launch-internals`). This context carries the model; that one carries
  the guarantees, and is attached only to tickets that change those paths.
