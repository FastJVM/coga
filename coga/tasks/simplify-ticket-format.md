---
title: simplify ticket format
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 6 (review)
---

## Description

Simplify ticket frontmatter by removing unused or redundant fields and omitting
empty optional metadata. The human approved the field-removal proposal on
2026-09-09; retain an optional per-ticket agent choice and preserve workflow
routing, human approval gates, ownership, and nonempty contexts/skills/secrets.

The owner approved the reviewed design and implementation handoff on
2026-09-10: freeze the main agent at activation, retain ephemeral override
semantics, bound delegation to one explicit agent step without completion
requirements, and use one coordinated PR with the writer quiet window in
Shape 7. The merge-time writer inventory and shutdown confirmations remain
required at cutover; design approval does not certify that writers are stopped.

### Acceptance criteria

- [ ] Normal ticket metadata retains `title`, `status`, `owner`, `workflow`,
  and a current `step` when the lifecycle requires one. Remove top-level
  `slug`, `human`, `assignee`, and `watchers`, their accessors, authoring inputs,
  and supported behavior. Remove residual `script: null` and its obsolete
  parser accommodation. Keep path-qualified `TaskRef` identity, including
  file-form and directory-form addressing, command results, and log tags.
- [ ] One shared, pure operator resolver supplies launch, transitions,
  script handoffs, status/show, notifications, and sweep eligibility. Workflow
  step `assignee` remains a role declaration. Human roles resolve to `owner`;
  no command persists the resolved operator or offers independent assignment.
- [ ] The optional main-agent choice follows the timing contract below.
  Explicit choices survive creation, activation, pause/resume, peer review,
  and completion. Missing/invalid agent configuration fails before dispatch;
  a failed preparation does not write a newly chosen agent to a real ticket.
- [ ] Empty top-level `contexts`, `skills`, and `secrets` disappear from new
  and rendered tickets. Absence is empty. Nonempty lists keep their ordering,
  validation, composition, and inline secret-reference semantics. Malformed
  falsy values are not silently erased as though they were empty lists.
- [ ] Creation and the `bootstrap/ticket` interview author the new shape;
  launch/interview agent overrides remain ephemeral. Activation still requires
  a workflow and preserves frozen step order and completion gates.
- [ ] Human gates remain handoffs. Explicit assists preserve their TTY,
  recorded-checkout, PR, publication, blocker-resolution, and completion-gate
  protections. Ordinary megalaunch/recurring overrides do not authorize human
  assists. Script-first execution and supervised stop/chain behavior survive.
- [ ] Bootstrap targets and recurring creation, promotion, retries,
  delegation, and megalaunch use the same role inputs. Preserve recurring
  `delegate`, `period_generation`, `launch_generation`, stable refs, state
  snapshots, serviced-period history, and owner-based selection.
- [ ] Delegated periods obey the bounded workflow contract in Shape 5:
  exactly one explicit agent step without a completion requirement. Reject
  peer steps, owner steps, additional steps, and completion requirements
  before materialization or dispatch, including retries and direct launches.
- [ ] Owner notifications still work live and through the digest; watcher
  arguments, spool writes, and cc rendering are removed. Old queued records
  remain readable but their watcher values have no effect.
- [ ] Repository extensions retain their existing defaults, ordering,
  validation, activation gates, and prompt handling. Removed core metadata
  cannot be reintroduced as an extension that restores assignment behavior.
- [ ] Convert the current ticket population, templates, bootstrap targets,
  recurring instances, fixtures, and documentation in the same reviewed change.
  Apply the exception dispositions below; preserve status, step, owner, body,
  blackboard, attachments, and all existing explicit agent selections.
- [ ] Required live/packaged twins are byte-identical. Regression tests cover
  the routing/default/override matrix and publication races below. Run the full
  suite and real/example validation against the changed source, recording
  baseline findings separately and introducing no new validation findings.
- [ ] The cutover follows the checkout procedure below. No older supervisor,
  installed writer, or stale feature checkout may publish converted tickets.

### Proposed shape

#### 1. Ticket shape and ownership

The minimal newly created draft has `title`, `status: draft`, `owner`, and
`workflow: null`, plus its Description, Context, and blackboard. A workflow
chosen at creation is still frozen then; a string reference is still frozen at
activation. This change does not re-freeze an existing snapshot.

`agent` is the optional **main-agent choice**, not the current operator.
`contexts`, `skills`, and `secrets` are optional declarations. `delegate`,
`period_generation`, and `launch_generation` keep their existing conditional,
system-owned meanings. Do not add a schema version, routing cache, resolved
assignee field, or a per-ticket peer field.

In `ticket.py`, remove the four accessors and update `CANONICAL_TICKET_KEYS`.
`Ticket.parse` continues preserving malformed input for diagnostics;
`Ticket.render` omits actual empty lists for contexts/skills and null/empty
secrets. Keep the existing rejection of explicit null contexts/skills and of
malformed non-list values. An explicitly present agent must be a nonempty,
configured agent name; do not silently treat null/blank/unknown as default.
Rendering must not mutate the caller's frontmatter or rewrite the body.

Treat the removed top-level names as rejected metadata, rather than ordinary
warn-only orphan extensions: validation names the offending fields and tells
the operator to use the simplified format. Writers refuse them rather than
silently interpreting or perpetuating them. Keep those names reserved against
extension declarations in `config.py`; this is a rejection, not a compatibility
reader or migration facility. Other extensions retain their existing rules.
Remove the special `script: null` pop once stored tickets have been converted;
the retired top-level `script` likewise never becomes a dispatch input.

Keep `Ticket.agent` a raw accessor. Configuration resolution belongs in shared
routing infrastructure, never an accessor that loads config or writes a file.
`TaskRef.slug`, `TaskRef.id_slug`, `COGA_TASK_SLUG`, and result/log keys named
`slug` continue to mean filesystem identity; this is not a repository-wide
rename of the word "slug".

#### 2. Derive the operator from the workflow

Consolidate routing in the existing `bump.py` infrastructure. A concrete shape
is `resolve_operator(cfg, ref, ticket, *, step_index=None) -> Operator | None`,
with a small value containing the effective role and concrete name. Keep
main-agent resolution and effective-step-role lookup as pure helpers shared
with validation and preparation. The exact helper names can change during
implementation; every consumer must use the same rules.

| Ticket/step state | Derived operator |
| --- | --- |
| Current step declares `owner` | Ticket owner, a human handoff |
| Current step declares `agent` | Main agent |
| Current step declares `other-agent` | Main agent's configured peer, or the sole other configured type |
| Current step omits its role | Inherit the nearest preceding declared role; before any declaration, use `owner` |
| Draft has no current step, including bare workflow refs | Owner for triage; launch must derive again from prepared activation |
| Terminal task has no current step | No current operator; display an empty/dash value |
| Live normal task has a missing/invalid workflow or step | Structural error, never a fallback to owner or agent |
| Stateless `BootstrapRef` without a workflow | Its explicit agent or configured default; no lifecycle mutation |

Inheritance is a scan of the frozen steps, not a scan of the audit log or a
memory of the last person to run the task. This preserves the old "leave the
assignment unchanged" intent while making forward moves, restarts, and human
rewinds deterministic. A preceding `other-agent` remains that role; it is
resolved against the main-agent choice, not made into a permanent nickname.
Use the role to distinguish human gates, not merely membership of the
resolved name in `[agents]`.

Rewrite `assignee: human` to `assignee: owner` in shipped workflows and every
stored snapshot. The new role vocabulary is `owner`, `agent`, `other-agent`;
`human` is rejected rather than retained as a second spelling. Do not change
step names such as `human-executes` or the skill/inline-instruction sources.
Literal human/agent nicknames remain invalid workflow role declarations.

Derive both the current and prospective next operator before a bump. Remove
`advance_step(new_assignee=...)` and all assignment writes from create, freeze,
bump, and blocked-resume compensation. Status changes still own only their
current lifecycle effects. Restoring an unanswered blocked resume restores the
original step and routing inputs, never a copied concrete assignment.

#### 3. Optional agent timing — approved activation-time selection

Leave `agent` absent on new drafts unless explicitly chosen;
when activation first approves work, resolve `Config.default_agent()` and
persist that name in the existing `agent` field. The default is the first
declared agent in the effective, merged configuration. Creation straight to a
live status (recurring and retire) performs the same selection. This gives up
omission on activated tickets in exchange for a stable main-agent identity.
The owner accepted this timing contract at review on 2026-09-10.

Selection belongs in pure prospective preparation, committed with the
successful lifecycle transition. A draft with a frozen workflow still defers
default-agent persistence until activation. Read-only status, show, compose,
and validate may report the effective/prospective default but never persist it.
An activated task must retain its selected agent: a
hand-authored live ticket with the field missing is an activation-invariant
validation error, just as an unfrozen live workflow is. The human can choose
`agent` explicitly through authoring or run `mark active` to select the
default. Plain bump/block/pause transitions must not choose a main agent at a
peer step. This conditional requirement is part of the accepted tradeoff;
the field remains optional for drafts, terminal records, templates,
and stateless targets.

Once selected, pause/resume, unblock, bump, and terminal transitions retain
`agent`. Reordering config defaults changes only future activations. Removing
a selected agent from configuration is a clear validation/preflight error,
not permission to replace it. Changing the agent's CLI settings affects the
next launch as today. Peers are still **live configuration**, not frozen
ticket metadata: changing the selected main agent's `peer` changes subsequent
peer launches, including after pause; an already-running child is unaffected.
With unchanged config, main A -> peer B -> main A is stable. A peer-only local
config override can still select a different reviewer on another machine;
document that consequence without inventing another stored role input.

Live default resolution was not selected: reordering agents between launches
could turn an omitted ticket's A -> peer B -> A sequence into A -> peer A -> B.
Implement activation-time selection only, without a second mode or a
configuration switch.

#### 4. Overrides, attribution, and publication

Preserve the existing override boundaries. Direct `launch --agent X` selects X
for the initial agent phase and continues through directly consecutive steps
**explicitly declaring** `assignee: agent`. An omitted role, owner step, or
`other-agent` ends propagation permanently for that launch. An inherited agent
role can execute, but does not broaden this explicit-role override contract.
A strict human assist applies to its one human step and never arms propagation.
Neither kind writes X to `agent`; activation, if needed, selects its main
agent independently from the override.

Megalaunch retains its narrower override: X runs picked-draft interviews and
the first launched step of each ticket; subsequent steps use derived routing.
It keeps skipping human-owned work even with `--agent`. Recurring's override
still selects only actual agent launches and leaves script-only jobs alone.
When an explicit direct launch assists a human step, preserve all current
assist proofs and expiry across script-to-agent handoffs.

Tradeoff retained deliberately: an override does not change who
`other-agent` is relative to. With main Claude and peer Codex, direct
`--agent codex` can produce Codex -> Codex -> Claude. A human who wants Codex
to become the main agent must explicitly choose `agent: codex` through
authoring; do not describe an ephemeral override as guaranteeing an independent
reviewer. The owner accepted this consequence at review on 2026-09-10.

The configured-main-agent requirement also deliberately removes the current
override recovery path: if a ticket selects Claude and configuration becomes
Codex-only, `launch --agent codex` must refuse before dispatch. The operator
must restore the selected agent's configuration or explicitly change the
ticket's main-agent choice through authoring. An ephemeral override cannot
repair an invalid routing input. Keep refusal coverage separate from successful
override propagation with a valid main agent.

Transition/handoff messages derive their ordinary operator from the same
resolver. Launch and usage records continue naming the actual spawned agent;
verified assists keep their existing `COGA_ASSIST_AGENT` attribution. There
is no equivalent ordinary-override identity in `task_env.py` today: do not
pretend there is, reuse assist authority for it, or rewrite ticket routing to
carry it. Ordinary transition messages may name the configured operator while
the launch record names the temporary worker, as today. Keep human CLI actors
and ownership distinct, and label human operators as humans.

Replace the `(status, step, assignee)` lifecycle identity used in
`git._ticket_lifecycle_state`, `FeaturePublicationLease`, launch's assist
checks, and script freshness checks. Compare the persisted routing **inputs**
(owner, explicit agent, frozen workflow role declarations, current position),
alongside status, without loading mutable config inside Git byte comparison.
A changed owner, main-agent choice, or role must invalidate the same-step
lease. Keep the exact ticket/task object comparisons, pending/released launch
claims, PR proofs, rollback, and no-sweep refusal behavior intact. Resolve the
operator again after every existing config/ticket reload before dispatch.

#### 5. Authoring, bootstrap, recurring, and notification surfaces

Remove `human`, `assignee`, and `watchers` from `create_task` arguments and
update all callers, including `commands/create.py`, `commands/retire.py`,
`recurring.py`, and `recurring_autofix.py`. Explicit agent choices previously
passed through the assignment argument become `agent=...`. The raw create CLI
does not need new flags. The interview asks for an optional main agent and
ownership, explains the derived operator, and has an explicit authoring
allowlist for those choices. Its `--agent` selects the interviewer only.
Preserve valid lifecycle fields and existing workflow snapshots during edits.

Bootstrap targets remain stateless. Convert their configured top-level agent
assignments to optional `agent`; preserve nonempty top-level skills. A direct
bootstrap launch uses override > target agent > configured default. A
bootstrap human gate must be expressed by an ordinary workflow ticket rather
than a second top-level assignment model; none of the current targets needs
such a conversion. Guided authoring and megalaunch's draft interview share
their current selection precedence after the rename: explicit override,
bootstrap/ticket's explicit agent, edited ticket's explicit agent, configured
default. This selection never persists onto the edited ticket by itself.

Recurring templates accept optional `agent` in their pass-through metadata;
promotion retains it instead of dropping it. Remove assignment/watchers from
`_TEMPLATE_PASSTHROUGH` and agent from `_TASK_ONLY_FIELDS`. A template without
a workflow still materializes `direct/body` (whose step explicitly declares
`agent`); it does not create a workflow-less active task. Continue the existing
rule that template-level skills are not copied: promotion warns and drops
them, while nonempty skills on normal tasks and bootstrap targets survive.

For an ordinary period, pass the template's explicit agent into `create_task`
or select the configured default at activation. For a delegated period,
choose template agent > bootstrap target agent > configured default at
materialization and store that choice as the period's main agent. Run the
frozen target using that period choice (or an explicit ephemeral override),
so retries and status agree on the worker even if the template/target agent
later changes. Bootstrap contents still reload under the existing dispatch
lease; only the selected main-agent identity is stable. The target's own agent
remains the choice for a direct stateless bootstrap launch. Keep delegated
sentinel completion, generation leases, owner gates, and script exclusion.
Do not let delegation bypass a period workflow's derived human handoff.

**Delegated workflow bound — approved 2026-09-10.** A delegated
period represents one bootstrap agent job. Its resolved workflow must contain
exactly one step, explicitly declaring `assignee: agent`, with no `requires`
completion gate. The default `direct/body` meets this bound; a custom workflow
may use another name but must have the same shape. Its sole step is the period's
lifecycle envelope: the bootstrap target remains the source of the executed
instructions, as today. The period must be at step 1 after any prospective
activation. Missing or malformed live workflow/position is an error under the
ordinary structural rules, never a reason to rebuild the snapshot.

Check the resolved template workflow before materialization and the frozen
period workflow before every retry or direct launch, before activation/start
is committed. Validation reports the same violations on templates and stored
periods. Recheck the bound after the existing ticket/config reloads and before
spawn and sentinel completion, under the existing exact-ticket/generation
leases. Reject `other-agent`, `owner`, an omitted role, any additional step,
or any completion requirement, even if that requirement currently passes.
A refusal must not spawn a target, advance/complete the period, or persist a
new agent choice. This makes the period's derived operator agree with its
selected main agent and leaves no later gate for whole-period completion to
skip. Keep successful one-step sentinel completion, retry behavior, state
publication, and all generation/parent leases.

Tradeoff: delegated periods cannot execute multi-step, peer-review, or gated
workflows. Those jobs use ordinary recurring execution without `delegate`;
role-aware, step-aware delegation is outside this change. The only current
delegating template, `resolve-conflicts`, already uses the qualifying default
workflow, and there are no materialized delegated periods at review time.
Refresh that inventory at implementation and cutover rather than assuming it
will remain true. The owner accepted this restriction as the disposition of
evaluator finding 1.

Display the derived operator in status/show; retain the existing
`--order-by assignee` spelling as sorting that computed column, with help text
making the derivation clear. It is a read-only sorting option, not an
assignment input or another ticket schema. Invalid routing gets a visible
diagnostic without crashing the whole listing or consulting the network.
Keep task refs and owner columns. Launch and handoff banners distinguish
configured operator from an ephemeral executing agent when they differ.

Remove watcher parameters and behavior through `notification/__init__.py`,
`notification/slack.py`, `blocker_reminders.py`, and every posting caller.
Digest records no longer write watchers; readers ignore the inert key in old
queued records and never cc it. Keep owner mention lookup, outcome sections,
important/default channels, and delivery-failure behavior. No historical log
or posted message rewrite, and no notification-config changes.

#### 6. In-place conversion and recorded exceptions

Refresh the inventory at implementation and again immediately before merge.
The design snapshot is 207 tasks at `a3b23d60`, including 81 parked `v2/`
tasks and four recurring instances. Convert actual frontmatter, not matching
text inside descriptions, archived designs, examples, or the log. Keep all
207 explicit agent choices initially, including the eight Codex selections;
an explicit value equal to today's default is not evidence it is disposable.

For the ten explicit-role mismatches, the proposed disposition is to remove
the obsolete manual assignment and honor the existing frozen agent role on
the next authorized resume. None is in an executing lifecycle state. Status
and blockers continue to gate resumption; do not activate, rewind, or change
ownership as part of conversion.

| Task ref | Preserve lifecycle/position | Removed assignment -> derived operator |
| --- | --- | --- |
| `run-recurring-agent-templates-off-the-control-bran` | blocked, 1 (design), open sibling-merge ask | nick -> claude |
| `v2/acceptance-criteria` | paused, 1 (design), owner zach | nicktoper -> claude |
| `v2/automerge-ticket` | paused, 1 (implement) | nicktoper -> claude |
| `v2/gh-merge-requirement` | paused, 1 (design) | nicktoper -> claude |
| `v2/identify-blocking-issues` | paused, 1 (design), owner zach | nicktoper -> claude |
| `v2/implement-accepted-ticket-interview-improvements` | paused, 1 (implement) | nicktoper -> claude |
| `v2/issue-inbox-slack` | paused, 1 (implement), owner zach | nicktoper -> claude |
| `v2/overload-ticket-locally-easily` | paused, 1 (implement), resolved blocker history | nicktoper -> claude |
| `v2/relay-design-repositories` | paused, 1 (design), owner zach | nicktoper -> claude |
| `v2/use-worktree-when-starting-a-dev-task` | draft, 1 (implement), evaluator notes | nicktoper -> claude |

The two snapshots on `v2/debug-surface-for-recurring-tasks-streamed-output`
and `v2/rename-workflow-primitive-to-playbook` omit roles at steps 1, 3, and 4.
Leave those snapshots in place: the inheritance rule gives owner at step 1
and after their step-2 owner gate, matching their current human routing. Do
not silently retrofit today's agent roles or additional evaluator/gate steps.

Five snapshots contain `human` roles: the two
`cleanup/{check-the-demo-video-against-current-cli-names,publish-coga-1-0-to-pypi}`
tickets, `marketing/build-the-launch-plan`, `marketing/phase-0-audit`, and
`v2/autotrigger-ticket-type`. Change only the token to owner; the cleanup pair
now names nicktoper rather than nick, consistent with the approved owner model.
Human role fields differing from owner elsewhere simply disappear. Preserve
all 15 Zach owners, including notes recording Nick's involvement; independent
manual assignment no longer transfers accountability.

Preserve the three marketing drafts' `marketing/write-post` skills. Remove
only the stale `bootstrap/ticket` entries on
`v2/autotrigger-ticket-type`, `v2/pass-secrets-to-skills-with-per-skill-scope`,
and `v2/use-slack-as-a-sync-channel-for-tickets`, because the interview is
already injected by the authoring command and must not run as task work.
Preserve the remaining nonempty declarations byte-for-byte in meaning. Add
short conversion notes only where needed to explain an exception; retain
existing ticket bodies and working memory rather than rewriting parked plans.

#### 7. One coordinated PR and checkout cutover

Keep code, data, fixtures, and contract updates in **one PR**. This is a broad
but single schema/routing change; separate code/data merges would leave the
running CLI and tickets disagreeing. Use focused commits for routing and
consumers, format/resources/docs, and the mechanical current-ticket conversion
so the semantic diff can be reviewed separately from repeated field deletion.
Do not add a standalone migration command, framework, compatibility flag, or
dual reader/writer period.

Use the separate feature-checkout layout from `dev/code`. Until merge, the
control checkout and its installed writer retain the old code and schema;
this ticket's implement/open-pr transitions run there, with its current
frontmatter preserved. Converted data and changed contexts stay committed on
the feature branch. Never run a mutating Coga command from that feature
checkout: the exit sweep can publish its converted `coga/` files before the
code lands. Test state-changing paths only in isolated fixtures without the
production remote. Use source-pinned read-only validation for the feature's
converted real/example copies.

At the owner merge gate:

1. Finish this ticket's old-schema workflow handoff to its final human review
   gate. Stop recurring/megalaunch dispatchers and allow **all** old Coga
   supervisors/children to finish their teardown and state sync. Also suspend
   scheduled entry points and direct state writers on other machines. Pausing
   a ticket or updating the `coga` binary alone does not stop a loaded process.
2. Inventory `git worktree list` plus independent clones and installed/editable
   Coga entry points that can reach this control branch. Preserve local work;
   do not delete, reset, or overwrite stale checkouts. The operator confirms
   which writers are stopped and which checkouts remain barred from mutation.
3. Catch up control, reconcile pending ticket/log writes, and refresh the
   conversion commit from that exact control revision, including this ticket's
   latest review step/blackboard/PR linkage. Verify the allowed field/token
   diff for every surviving ticket; include new tickets and do not resurrect
   deleted ones. A concurrent control change invalidates this comparison:
   refresh and review again rather than choosing one side wholesale.
4. Merge code and conversion together through the ordinary owner-reviewed PR.
   Update the control checkout and every usable installed writer to that
   revision. Confirm import paths and restart processes. Rebase/reconcile any
   feature checkout before permitting Coga writes from it; stale checkouts may
   remain parked but cannot run mutating commands or launch teardown.
5. Re-run read-only validation on the converted control state, then resume
   dispatch. Close this ticket using the new CLI only when its owner approves
   the final gate. Do not replay an old supervisor's finalizer after merge.

Existing state-regression guards compare lifecycle progress; they are not a
schema cutover barrier and cannot stop an already-running older writer from
restoring obsolete fields at the same step. The procedure above supplies that
boundary without new hidden machinery. If the owner cannot arrange this quiet
window, do not claim one-PR rollout is safe: return a split proposal for a
separately reviewed, preinstalled writer-admission guard followed by the atomic
format cutover. Such a guard is not part of this proposed implementation.

### Verification

Use meaningful behavior tests with temporary tickets and fake agent CLIs,
including both file forms and path-qualified refs. Cover:

- Draft creation and guided editing with absent optionals; nonempty context,
  top-level skill, workflow-step skill, and inline `op://`/`env:` secret lists;
  malformed falsy values; extension preservation; rejected removed fields.
- Creation with frozen workflow versus activation from a bare ref; current
  agent/owner/peer roles; omitted first and intermediate roles; terminal/no-step
  display; malformed live state; all peer configurations (two-agent inference,
  explicit peer among three, absent/invalid/ambiguous selection).
- Explicit/default main agents, default reordered before/after activation,
  pause/resume, peer config edits, main -> peer -> main, and failed preflight
  leaving agent/status/ticket bytes unchanged.
- Direct override continuation and expiry, megalaunch's first-step override,
  human assists, owner-gate refusal without an assist, derived transition
  operators, actual-agent launch/usage records, and verified assist attribution.
  Include the retained same-worker/peer override consequence and refusal when
  an override is valid but the ticket's selected main agent is no longer
  configured; keep successful propagation with a valid main agent covered.
- Script-only and script-to-agent handoffs, unanswered blocked-resume
  restoration, and stale owner/agent/role edits invalidating same-step assist
  leases and pre-spawn checks. Preserve the existing pending-claim and rollback
  regression coverage; do not weaken those fixtures to get the suite green.
- Stateless bootstrap dispatch, guided authoring, normal/delegated recurring
  creation and retry, promotion, template-without-workflow materialization,
  scoped secrets, human handoffs, and megalaunch owner/blocker eligibility.
- Delegation's approved bound: accept default/custom one-step explicit-agent
  workflows without `requires`; reject a current peer step, an agent step
  followed by an owner gate, any additional agent step, an omitted first role,
  and a one-step workflow with a completion requirement (satisfied or not).
  Cover refusal before materialization, scheduled/named retries, direct launch,
  and edits observed after reload or while a child runs. No refused case may
  spawn or publish completion; retain successful sentinel/generation-lease and
  rollback regressions for the permitted shape.
- Owner notifications and digest rendering without watcher cc, including an
  old queued record; required live/packaged twin parity; no writer restores
  removed keys after activation, bump, block/unblock, or terminal transitions.

Run `python -m pytest` with this checkout's absolute `src` on `PYTHONPATH`,
using the installed test dependencies. Run source-pinned `coga validate --json`
in the converted real repo and `example/`. Unset an inherited bare
`SLACK_WEBHOOK_URL` for the example, whose config does not declare it; do not
change config or probe live secrets/webhooks to perform validation. Save
before/after reports and compare by task/kind, allowing time-dependent idle
durations and the intended removal of old assignment warnings. Record exact
verification commands in the implementation handoff/PR.

### Out of scope

Workflow/playbook renaming; re-freezing snapshots; adding reviewer steps or
completion gates to old tickets; changing statuses/owners to clean the queue;
adjudicating parked designs; fixing pre-existing blackboard hygiene findings;
changing agent/peer or notification config; adding per-ticket peers or a
persistent launch-override flag; redesigning recurring dispatch, launch claims,
or Git publication; general CLI/core decomposition; historical log/git rewrites;
and a frontmatter migration tool or permanent old-schema support.

## Context

The audit examined all 207 task files at `e49fc7f9` (81 parked under `v2/`, four
recurring instances), eight historical snapshots from May through September,
and relevant commits/source consumers. The snapshot history is a sample, not
every ticket revision. Evidence behind the accepted cuts:

- `human` equals `owner` on 191 current tickets; the other 16 have
  `owner: nicktoper` / `human: nick`. One historical draft,
  `marketing/auto-width-200` at `b2aaa496`, named Nick and Zach separately but
  its workflow did not use the `human` role.
- Of 89 tickets with an explicit current step role, 79 stored assignments match
  and ten differ (blocked/paused/draft); two additional current steps omit a
  role. `65b52b13` (#779) fixed a real activation bug caused by disagreement
  between stored assignee and the first step's role.
- All 207 `slug` values duplicate the task ref. No current task has `watchers`,
  and HEAD-history searches for its declaration under both `coga/tasks/` and
  the former `relay-os/tasks/` found no commits.
- Current `agent` values are 199 Claude / eight Codex. Historical commit
  `bce4e209` deliberately reassigned seven tickets to Codex. Owner is also
  meaningful: 15 current tickets belong to Zach.
- Empty metadata accounts for 150 `contexts` lists, 201 `skills` lists, 148
  `secrets: null` declarations, and 22 retired `script: null` entries. Three
  marketing drafts actually use `marketing/write-post`; three parked drafts
  incorrectly persist `bootstrap/ticket`. Bootstrap targets also use top-level
  skills. Preserve real skill use while dropping empty scaffolding.

### Code and contract map

The implementation inventory at `a3b23d60` has these concrete seams:

| Concern | Existing source to change or verify |
| --- | --- |
| Ticket IO and addressing | `src/coga/ticket.py`: canonical keys, accessors, parse/render; `tasks.py`: `TaskRef`, `BootstrapRef`, discovery |
| Construction/default | `create.py:create_task`, `_default_agent_for`; `config.py:Config.default_agent`, reserved extension names; all four creation callers named above |
| Routing and lifecycle | `bump.py:resolve_role_token`, `resolve_other_agent`, `resolve_first_step_assignee`, `resolve_step_assignee`, `advance_step`; `mark.py:_freeze_workflow_ref`, `prepare_active`; `workflow.py:VALID_ASSIGNEE_ROLES`, `Workflow.freeze` |
| Launch/restore | `commands/launch.py:_prospective_activation_identity`, nested `_read`, `_refuse_human_handoff_launch`, `consecutive_agent_override`, `_reblock_unresolved_resume`; `launch_script.py` freshness and continuation checks |
| Transition consumers | `commands/bump.py`, `commands/mark.py`, `commands/block.py`, `commands/unblock.py`, `mark.py`; inspect finalizers and compensation, not only successful forward movement |
| Sweep/authoring | `megalaunch.py:_author_draft`, `_launch_until_stop`, eligibility/chain-stop checks; `commands/ticket.py`; `authoring.py` final validation; `commands/init.py` owner placeholder replacement |
| Recurring | `recurring.py:_TASK_ONLY_FIELDS`, `_TEMPLATE_PASSTHROUGH`, `_create_at_slug`, `_template_frontmatter`; `recurring_runner.py:_run_delegated_task`; `recurring_autofix.py` creation and notification callers |
| Git proofs | `git.py:_ticket_lifecycle_state`, `FeaturePublicationLease`, `guard_ticket_state`, `_assist_control_ticket_guard`, `feature_publication_lease`; launch/mark/script callers passing expected lifecycle tuples |
| Read/validation | `views.py:render_status`, `render_show`, `ORDER_BY_CHOICES`; `validate.py:REQUIRED_TASK_KEYS`, `_check_frontmatter_schema`, `_check_step_shape`, recurring checks; `dream_validate_drift.py` for changed diagnostic kinds |
| Prompt/secret preservation | `compose.py:compose_prompt_report`; `task_env.py:TASK_ENV_KEYS`; `config.py:parse_inline_secrets`, `select_launch_secrets`, `build_launch_env`; correct the stale `Ticket.secrets` comment |
| Notifications | `notification/__init__.py:post`, `notify`, digest watcher renderer; `notification/slack.py:SlackChannel`; `blocker_reminders.py`; posting calls in launch, lifecycle, recurring, and `commands/slack.py` |

Tests are in `tests/test_ticket.py`, `test_create.py`, `test_mark.py`,
`test_done_marker_emission.py`, `test_launch.py`, `test_launch_script.py`,
`test_launch_restart.py`, `test_megalaunch.py`, `test_recurring.py`,
`test_recurring_autofix.py`, `test_validate.py`, `test_config.py`,
`test_compose.py`, `test_env_isolation.py`, `test_git.py`, `test_views.py`,
`test_status.py`, `test_notification.py`, `test_notification_messages.py`,
`test_bootstrap_ticket_skill_template.py`, and `test_packaging.py`, plus any
remaining consumers found by search. Keep assertions about behavior and race
refusal, not just replacement fixture field names.

`docs/spec.md` and `coga/contexts/coga/cli/SKILL.md` no longer exist.
Update `docs/concepts.md`, `docs/reference.md`, `docs/operations.md`, and
affected examples in README/getting-started material instead of recreating
those retired documents. Update the affected sections of
`coga/contexts/coga/{architecture,launch-internals,sync,recurring,codebase,current-direction,principles}/SKILL.md`,
`coga/contexts/dev/code/SKILL.md`, `src/coga/resources/prompt.md`, the live and
packaged task templates, bootstrap launch targets, recurring resources, and
`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`.
That authoring skill has no live counterpart at this revision. Search the
shipped skills for instructions that would write removed metadata; keep
historical ticket prose separate from current operational instructions.

These contexts are editing targets, so their full bodies are intentionally
omitted from `contexts:`; read the cited sections before implementation.
Follow the separate-checkout procedure in `dev/code`. In particular,
`coga launch --prompt-report` is not a safe read-only verification command:
it refreshes skill views and can sweep Coga state. Use the pure composition
functions instead. A feature checkout must pin absolute `PYTHONPATH` to its
own `src`; the installed CLI may otherwise import another checkout.

### Validation baseline — 2026-09-10

Source-pinned real-repo `coga validate --json` exits 1 with four existing
`unsynthesized-draft-blackboard` errors on `v2/autotrigger-ticket-type`,
`v2/measure-relay-prompt-scope-and-agent-precision`,
`v2/split-context-to-doc-user-accessible-and-editable`, and
`v2/use-worktree-when-starting-a-dev-task`. There are also 29 warnings:
17 unfrozen draft workflows, five idle in-progress tasks, two large
blackboards, and five unknown assignees. The last five are on
`v2/{acceptance-criteria,clean-uncommitted-work,identify-blocking-issues,issue-inbox-slack,relay-design-repositories}`
and should disappear with removal of the assignment surface. `v2/clean-uncommitted-work`
has no current step and therefore is not an extra current-step mismatch.
Other findings are baseline drift, not permission to change parked intent.

The example has zero findings and exits 0 with its unrelated inherited bare
`SLACK_WEBHOOK_URL` unset. Without that environment cleanup config load exits
2 before validation. Local full reports are
`/tmp/simplify-ticket-format-real-baseline.json` and
`/tmp/simplify-ticket-format-example-baseline.json`; the durable categories and
error-task identities are recorded here so the reports are not required to
understand the baseline. Refresh all counts before the eventual cutover.

<!-- coga:blackboard -->

## Design investigation — 2026-09-10

- Rechecked the population at `a3b23d60`: 207 tasks, 81 under `v2/`,
  199 explicit Claude selections and eight Codex. The ten current-step
  assignment mismatches and two missing current-step roles remain present.
- Routing also feeds script-phase handoffs, blocked-resume restoration,
  recorded-assist Git leases, guided authoring, and recurring delegation;
  replacing only launch/bump would leave independent assignment consumers.
- `docs/spec.md` and a `coga/cli` context do not exist at this revision.
  The current documentation targets are `docs/concepts.md`,
  `docs/reference.md`, `docs/operations.md`, and the Coga contexts.
- `config.parse_inline_secrets` / `select_launch_secrets` already treat
  absent, null, and empty declarations as no declared secrets. The
  three-way/blanket-injection comment on `Ticket.secrets` is stale; preserve
  the current inline-reference resolver and scoped environment construction.
- The spec is under `## Description` / `## Context` with acceptance criteria,
  shared routing rules, the exact mismatch dispositions, implementation
  pointers, test cases, and a coordinated one-PR cutover. The default-agent
  section was a proposal at design time; the Owner review disposition below
  records the subsequently approved timing contract.
- The one-PR recommendation depends on stopping old writers at merge. Ten Git
  worktrees were registered at investigation time; that list does not prove
  which processes, independent clones, or remote machines are still writing.
  Refresh the inventory during the owner-controlled cutover.
- Verification: `PYTHONPATH=/home/n/Code/codex/coga/src coga validate --task
  simplify-ticket-format --json` exits 0, no findings. Pure
  `compose_prompt_report` includes acceptance criteria, proposed shape,
  out-of-scope, conversion table, cutover, baseline, and open questions.
  Frontmatter bytes match the starting revision; there is one blackboard fence.
  `git diff --check -- coga/tasks/simplify-ticket-format.md` passes.
- Source-pinned real/example repo baselines are recorded in Context. The
  example passes with the inherited bare Slack variable unset. No code,
  tests, shared contracts, config, branch, or PR changed in this design step.
  The full pytest suite belongs to implementation. `coga/log.md` was already
  dirty at session start and was not hand-edited.

## Open Questions

None for implementation. The owner approved all four presented decisions and
explicitly requested the handoff on 2026-09-10 ("bump it"). See the Owner review
disposition below. Writer shutdown and checkout reconciliation are still
merge-time prerequisites under Shape 7, not completed operations.

## Evaluator review

Cold review on 2026-09-10 against `146f6557`. **Not ready for implementation:**
one delegation contract gap needs a disposition, and the three existing owner
decisions remain open. The shared resolver fits the microkernel rule; the
code/data/docs cutover is one coherent change, conditional on the writer quiet
window. The frozen `evaluate-design` -> `review-design` handoff fits this work.

### Must resolve before implementation

1. **P1 — Define which workflows a delegated period can execute and finish.**
   Proposed Shape 2 makes the workflow role authoritative, but Shape 5 runs
   the target using the period's main agent and retains whole-period sentinel
   completion. Those rules disagree for a period at `other-agent`, or one
   with an owner gate after its current agent step. Checking only the current
   human handoff cannot protect a later gate.

   Evidence: `src/coga/recurring.py:Template.load`, `_create_at_slug`, and
   `resolve_agent_delegate` accept a custom period workflow without restricting
   its roles or length. `src/coga/recurring_runner.py:_run_delegated_task`
   launches the bootstrap target and calls `mark_done` directly on its done
   signal; it does not advance the period workflow. In an isolated temporary
   fixture with Git/notifications disabled and a fake bootstrap completion,
   a valid `other-agent` -> `owner` period with main Claude had **zero validation
   findings**, derived Codex at step 1, selected the Claude bootstrap target,
   and ended `done` with no step, skipping owner approval. This is an existing
   behavior the new contract must reconcile, not a proposed implementation bug.

   Decide either a bounded allowed workflow shape for delegation, rejected
   before materialization and again on retries/direct launches, or specify
   role-aware dispatch and step-aware completion and revise the recurring
   redesign exclusion accordingly. Add explicit acceptance cases for a peer
   current step, a later owner gate, and a completion requirement; preserve
   the existing one-step delegation leases and sentinel behavior.

2. **P1 — Settle the explicitly approval-dependent contracts.** The body
   deliberately leaves activation-time persistence versus live default
   resolution undecided (Shape 3), asks the owner to accept the possible
   same-worker override/peer sequence (Shape 4), and conditions one-PR rollout
   on stopping every old writer (Shape 7). Record those dispositions in the
   spec before handing it to implementation; field-removal approval alone
   does not select them. If the quiet window is infeasible, use the separately
   reviewed guard proposal already described by the ticket.

   Evidence: `src/coga/config.py:Config.default_agent` selects the first merged
   agent; `src/coga/create.py:create_task` currently persists it at creation,
   while `src/coga/mark.py:prepare_active` does not select an agent. The proposed
   timing is therefore a behavior change.
   `src/coga/commands/launch.py:consecutive_agent_override` and
   `src/coga/bump.py:resolve_other_agent` keep temporary execution and the stored
   main agent separate. `src/coga/git.py:_ticket_lifecycle_state` compares only status,
   step, and assignment today; `coga/sync`'s "catch-all subtree sweep" confirms
   why older writers cannot safely remain active during this cutover. Local
   inspection cannot certify the other machines or scheduled writers.

### Optional recommendations

- Explicitly call out the loss of the existing override recovery path when a
  stored main agent is absent from config. The configured-agent requirement
  in Shapes 1/3 implies refusal, but
  `tests/test_launch.py:test_launch_agent_override_follows_consecutive_agent_role_steps`
  currently proves success for a Claude-main ticket after config becomes
  Codex-only, using `--agent codex`. If retaining the proposed requirement,
  document this tradeoff and retain separate tests for that refusal and for
  successful override propagation with a valid main agent.
- Keep the mandated fresh inventory, rather than treating 207 as a fixed
  conversion target. This review found **208 tasks**, 81 parked `v2/` tasks,
  four recurring instances, 200 Claude/eight Codex selections, and all 15 Zach
  owners. The ten explicit agent-role mismatches, two omitted-current-role
  snapshots, five `human` snapshots, and six nonempty top-level skill lists
  still match the recorded exception dispositions. No ticket has watchers or
  a path/slug mismatch. This is expected population drift, not a scope defect.

### Verification and limits

Checked ticket IO, creation/activation, role/override dispatch, script handoffs,
authoring, recurring delegation, publication leases, notification watcher
consumers, validation, and the cited live/package contracts. No implementation,
manual ticket-body/frontmatter edit, branch, or PR was produced. The existing dirty
`coga/log.md` was not hand-edited.

The following focused existing tests passed: **13 passed** including
parameterized cases. This verifies current behavior, not the future format;
the full suite remains an implementation requirement.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/n/Code/codex/coga/src python -m pytest -q \
  tests/test_create.py::test_create_initial_assignee_resolved_from_workflow_step \
  tests/test_mark.py::test_mark_active_resolves_step_one_assignee \
  tests/test_launch.py::test_launch_agent_override_follows_consecutive_agent_role_steps \
  tests/test_megalaunch.py::test_megalaunch_agent_override_applies_to_first_step_only \
  tests/test_recurring.py::test_delegated_task_launches_target_and_owns_lifecycle \
  tests/test_launch_script.py::test_script_only_launch_is_headless_and_receives_task_contract \
  tests/test_packaging.py::test_live_and_packaged_copies_stay_identical
```

Source-pinned read-only validation used
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/n/Code/codex/coga/src coga validate --json`
from the real checkout, and the same command prefixed by
`env -u SLACK_WEBHOOK_URL` from `example/`. Reports are at
`/tmp/simplify-ticket-format-evaluator-{real,example}-validation.json`.
The real repo still has the same four draft-blackboard errors; warnings are
now 28 (16 unfrozen workflows, five idle tasks, two large blackboards, five
unknown assignments). The example has no findings. These are pre-change
observations, not conversion results; no live webhook or secret was probed.
Ticket-only validation (`coga validate --task simplify-ticket-format --json`,
with the same source pin) passes with no findings after recording this review.
Byte comparisons confirm the original frontmatter, body, and unrelated
blackboard remain unchanged, with exactly one fence and evaluator section;
`git diff --check -- coga/tasks/simplify-ticket-format.md` passes.

## Owner review preparation — 2026-09-10

Historical preparation; the approval recorded below supersedes its pending
decision status.

- This is frozen step 3, the owner `review-design` gate. The evaluator's
  existing findings remain intact. No owner approval or advancement is implied
  by this preparation.
- Proposed disposition for evaluator finding 1 is now concrete in Shape 5,
  Acceptance criteria, and Verification: one explicit agent step, no completion
  requirement; reject incompatible shapes before creation/activation/dispatch
  and on reload/completion. This keeps whole-period sentinel completion without
  adding step-aware delegation. Owner acceptance is still required.
- Rechecked `recurring.Template.load`, `_create_at_slug`, and
  `recurring_runner._run_delegated_task` at `e8eb757b`: the current creator can
  freeze a custom workflow, while delegated completion calls `mark_done`
  directly. A current-role-only check would leave later gates unprotected.
- A read-only frontmatter inventory found only `resolve-conflicts` declaring
  `delegate` in both live and packaged recurring templates. It omits workflow
  and therefore uses the existing one-step explicit-agent `direct/body`.
  No real/example task or example recurring template declares delegation.
  Source-pinned `list_tasks(load_config())` discovers 208 real tasks; the older
  207-task snapshot is not a fixed conversion target.
- Incorporated the evaluator's optional recovery-path clarification in Shape 4
  and Verification: an override cannot rescue a ticket whose chosen main agent
  is absent from config. This follows the proposed configured-agent invariant;
  valid-main override propagation retains separate coverage.
- The default timing, same-worker override consequence, delegation restriction,
  and ability to arrange a writer quiet window remain owner decisions. Local
  inspection cannot certify stopped writers on other machines. Do not bump
  until the owner settles these choices and explicitly authorizes the handoff.
- Only this ticket's body/blackboard was edited; current-schema frontmatter,
  source, tests, shared contracts, configuration, and the existing dirty
  `coga/log.md` were left intact. The full suite remains implementation work.
- Verification: `PYTHONDONTWRITEBYTECODE=1
  PYTHONPATH=/home/n/Code/codex/coga/src coga validate --task
  simplify-ticket-format --json` exits 0 with no findings;
  `git diff --check -- coga/tasks/simplify-ticket-format.md` passes.
  Byte comparisons against `e8eb757b` preserve the original frontmatter and
  evaluator review, with exactly one blackboard fence.

## Owner review disposition — 2026-09-10

- The owner responded "bump it" to the four explicit decisions and the request
  to hand off to implementation. The design is approved; the body now records
  the selected contracts instead of leaving approval-dependent alternatives.
- Evaluator finding 1 is resolved by the accepted one-step explicit-agent,
  no-completion-requirement delegation bound. Creation, retries, direct launch,
  reload, and completion checks and regression cases are specified in Shape 5
  and Verification. Step-aware delegation remains out of scope.
- Evaluator finding 2 is resolved: freeze the default main agent at activation;
  keep overrides ephemeral, accepting possible same-agent review and refusal
  when the chosen main agent is absent from config; use one coordinated PR with
  the owner-arranged writer quiet window. This is approval of the cutover plan,
  not evidence that old writers are already stopped. Shape 7's final inventory,
  reconciliation, shutdown confirmation, and owner merge gate remain mandatory.
- Both optional evaluator recommendations are incorporated: override recovery
  refusal has an explicit contract/test case, and the current 208-task inventory
  must be refreshed during implementation and again immediately before merge.
- Handoff: implement only in the separate feature checkout described by the
  ticket. Preserve the control checkout's current schema for this ticket's
  remaining pre-merge transitions; no mutating Coga command may run from the
  converted feature checkout. No implementation work was started in this review.
- Review verification passed: `PYTHONDONTWRITEBYTECODE=1
  PYTHONPATH=/home/n/Code/codex/coga/src coga validate --task
  simplify-ticket-format --json` exits 0 with no findings, and
  `git diff --check -- coga/tasks/simplify-ticket-format.md` passes. Before the
  CLI handoff, byte comparison confirmed the original frontmatter and step 3
  were intact, with one blackboard fence; the checkout is on `main`.

## Dev

pr: https://github.com/FastJVM/coga/pull/784
branch: simplify-ticket-format
worktree: /home/n/Code/codex/coga-simplify-ticket-format

## Implementation — 2026-09-10

Implemented in the separate feature checkout above; three focused commits on
`simplify-ticket-format`, rebased onto control `4c03f865`. Nothing mutating was
run from the feature checkout — the converted data stays there until the owner
merge gate.

### What landed

- **`bump.py` owns one shared, pure resolver.** `resolve_operator(cfg, ref,
  ticket, *, step_index=None)` returns an `Operator(role, name)` (or None for a
  terminal task) from the frozen step's role, with `resolve_main_agent`,
  `resolve_other_agent`, `effective_step_role`, and `operator_for_role` as the
  shared helpers. Every consumer reads it: launch, `commands/{bump,mark,block,
  slack}`, `launch_script`, `views`, `megalaunch`, and validation. `advance_step`
  lost `new_assignee` — it writes only `step:`. `AssigneeResolutionError` became
  `OperatorResolutionError`, and `bump.py` no longer imports `validate` at module
  scope (it was the cycle that blocked `launch_script` from importing the pure
  resolver).
- **`agent` is the main-agent choice, frozen at activation.**
  `mark._select_main_agent` + `_assert_operator_resolves` run inside
  `prepare_active`, so selection and role resolution are prepare-side: a refused
  activation writes nothing. `MainAgentUnavailable` joins the prepare-side ladder
  in `commands/mark`, `commands/launch`, `megalaunch._PREPARE_ACTIVE_ERRORS`, and
  the recurring runner. `create_task` selects the default only for a live create.
- **Rendering and rejection.** `Ticket.render` omits actual empty
  `contexts`/`skills`/`secrets` and keeps malformed falsy values;
  `REJECTED_TICKET_KEYS` drives a `removed-ticket-field` **error**, which is what
  makes every writer refuse the old shape, and `config._RESERVED_TICKET_FIELD_NAMES`
  keeps those names out of `[ticket.fields.*]`.
- **`git.TicketRoutingState`** replaces `(status, step, assignee)` in
  `FeaturePublicationLease`, `guard_ticket_state`, the assist guards, and
  `launch_script` freshness: status plus owner, main agent, frozen step roles,
  and position, computed from committed bytes with no config load.
- **Delegated bound** (`recurring.assert_template_delegation` /
  `assert_frozen_delegation`) checked before materialization and at every leased
  boundary including completion; reported by validation as
  `unbounded-delegated-workflow`.
- Watcher arguments, spool writes, and cc rendering removed;
  `dream_validate_drift` classifies the five new validator kinds;
  `scripts/human_minutes.py` reads identities from `owner` only.

### Decisions made during implementation

- **A wholly role-less workflow is owner-held end to end.** That follows from the
  approved inheritance rule (`owner` before any declaration). Test fixtures that
  meant "an ordinary agent workflow" now declare `assignee: agent`, the way a
  real one does. Consequence worth knowing at cutover: a *live* ticket whose
  frozen snapshot declares no role anywhere is now a human handoff, and
  `coga launch` refuses it without `--agent`. No such ticket exists in the
  converted population — the only two omitted-role snapshots already routed to
  the owner (verified below).
- **Validation checks the delegated step-1 position only when a step exists.** A
  finished period has had `step:` popped and a draft/paused one may never have
  been activated; requiring a position there made `mark done` fail on a healthy
  delegated completion. The runner still requires step 1 at dispatch.
- `--order-by assignee` is retained as an alias for the new `operator` column
  (read-only sorting, per the spec) rather than removed.
- `coga/coga.toml` still carries a comment mentioning `watchers` in its
  `[notification.slack.users]` note. Left alone deliberately: editing
  `coga.toml` is outside this ticket's boundaries, and the packaged seed copy
  (the twin a fresh repo gets) is updated.

### Verification

Run from the feature checkout with its own absolute `src` pinned:

```sh
cd /home/n/Code/codex/coga-simplify-ticket-format
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/n/Code/codex/coga-simplify-ticket-format/src \
  python3.12 -m pytest -q --no-header -p no:randomly
# → 2405 passed, 1 failed
```

The single failure is `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries`,
which is **pre-existing and environmental**: no interpreter on this machine can
import `hatchling.build`, so `pip wheel` cannot run. It fails identically on the
control checkout at `4c03f865` (verified), so it is a baseline finding, not a
regression. Everything else in `test_packaging.py` passes, including the
live/packaged twin parity check.

Source-pinned read-only validation (never `launch --prompt-report`, which
refreshes skill views and can sweep state):

```sh
cd /home/n/Code/codex/coga-simplify-ticket-format/coga
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/n/Code/codex/coga-simplify-ticket-format/src \
  python3.12 -m coga.validate --json          # exit 1, 4 errors + 24 warnings
cd ../example/coga
env -u SLACK_WEBHOOK_URL PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/home/n/Code/codex/coga-simplify-ticket-format/src \
  python3.12 -m coga.validate --json          # exit 0, no findings
```

Compared against the *same* control revision, validated the same way:

| | control (old code + data) | converted branch |
| --- | --- | --- |
| `unsynthesized-draft-blackboard` (error) | 4 | 4 — same four tasks |
| `unfrozen-workflow` | 16 | 17 |
| `stuck-in-progress` | 5 | 5 |
| `large-blackboard` | 2 | 2 |
| `unknown-assignee` | 5 | **0** |

No new finding kinds and no new error identities. The five `unknown-assignee`
warnings are the intended removal of the assignment surface; the extra
`unfrozen-workflow` is the `allow-description-and-owner-on-create` draft control
created during implementation. Reports:
`/tmp/claude-1000/-home-n-Code-codex-coga/{real-after2,example-after,real-control}.json`.

Pure `compose_prompt_report` was used for prompt checks: nonempty contexts,
top-level skills, workflow-step skills, and ticket bodies all still compose
(`marketing/post-doc-as-cache` keeps its two contexts and `marketing/write-post`).

### Refreshed conversion inventory (at control `4c03f865`)

209 tasks, 81 parked under `v2/`, four recurring instances; 201 Claude and 8
Codex explicit selections; 16 Zach owners, 3 `nick`, 190 `nicktoper`. Removed
across the population: 211 × `slug`/`human`/`assignee`, 22 × `script: null`,
208 empty `skills`, 153 empty `contexts`, 152 null/empty `secrets`. No task
carried `watchers`. Verified per ticket that only those keys disappeared, every
survivor is byte-equal, key order is unchanged, and no body, status, step,
owner, or explicit agent changed. The one `agent` removal is the hand-rewritten
`coga/tasks/_template/ticket.md`, where it is now a commented optional example.

All recorded exception dispositions re-verified after conversion:

- The ten former assignment mismatches derive `claude` from their frozen role,
  with status, position, and owner untouched.
- The five `human` snapshots became `owner`; the cleanup pair resolves to
  `nicktoper`.
- `v2/debug-surface-for-recurring-tasks-streamed-output` and
  `v2/rename-workflow-primitive-to-playbook` keep their omitted roles and derive
  `owner` at every step, matching their current human routing.
- The three marketing drafts keep `marketing/write-post`; the three stale
  `bootstrap/ticket` entries are gone.
- Every task in the population resolves an operator with no error.

### Adjacent finding (not fixed here)

`tests/test_packaging.py::test_wheel_includes_bootstrap_batteries` cannot run on
this machine — `pip wheel --no-build-isolation` needs `hatchling` importable by
the interpreter running the suite, and neither `python3.12`, `python3.11`, nor
the installed `coga` tool env has it. Symptom:
`BackendUnavailable: Cannot import 'hatchling.build'`, assert `2 == 0` at
`tests/test_packaging.py:433`. Reproduces on control at `4c03f865`, so it is a
dev-environment/setup gap (install the `[test]` extra plus `hatchling` into one
env), not a packaging defect. No existing follow-up ticket found.
`retro/done-ticket` owns carrying this into a durable context before this ticket
is deleted.

### Merge-gate prerequisites — still open, owner-controlled

Shape 7 is unchanged and unsatisfied by this step. Before merge the owner must:
stop recurring/megalaunch dispatchers and let every old supervisor finish its
teardown and state sync; suspend scheduled entry points and direct writers on
other machines; inventory `git worktree list` plus independent clones and
installed/editable entry points; catch control up and refresh the conversion
commit from that exact revision; then merge code and data together and update
every usable installed writer.

Two concrete facts for that inventory. **Control moved twice during
implementation** — `2618c2d3` → `4c03f865` → `247313a7`, other sessions running
`add-an-agent-picker-for-recurring` and `allow-description-and-owner-on-create`
— which is precisely the concurrent change Shape 7 says invalidates the
comparison. Each rebase conflicted on the tickets those sessions had advanced,
and both were resolved the way the spec requires: take control's lifecycle state
for the conflicting ticket, re-apply the conversion to it, and convert the new
tickets control created. Never choose one side wholesale. Expect to repeat this
at the real gate, and expect it more than once. **Ten worktrees were registered
at implementation time**, which still does not prove which processes or machines
are writing.

The branch is rebased onto control `247313a7` with the full suite re-run green
(2407 passed, plus the environmental packaging failure above) and the population
re-verified after each rebase.

## Open-PR — 2026-09-10

PR https://github.com/FastJVM/coga/pull/784, opened by `coga open-pr` from the
primary control checkout on `main`; `pr:` is recorded under `## Dev` above. No
review was in flight — this ticket's frozen workflow has no `self-qa` or
`peer-review` step, and `code/implement` orders none.

Control moved twice more during this step, so the branch was stale on the first
two `coga open-pr` attempts (both refused cleanly, nothing pushed). Rebased onto
`origin/main` twice:

- `247313a7` → `8414dda8`: conflicts on `allow-description-and-owner-on-create`,
  `stop-syncing-task-state-onto-the-feature-branch`, and this ticket.
- `8414dda8` → `58c9e283`: conflict on `allow-description-and-owner-on-create`
  again (another session advanced it to step 4 mid-verification).

Every conflict was resolved the way Shape 7 requires and the implementation note
predicted: take control's version of the ticket wholesale — lifecycle, body, and
blackboard — then re-apply only the mechanical key removals to it. Verified by
diffing each resolved file against `git show origin/main:<path>`: the diffs are
pure deletions of `slug`, `human`, `assignee`, empty `skills`/`contexts`, and
`secrets: null`. No side was taken wholesale and no lifecycle state was reverted.

Verification after each rebase, from the feature checkout with its own absolute
`src` pinned:

```sh
cd /home/n/Code/codex/coga-simplify-ticket-format
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/n/Code/codex/coga-simplify-ticket-format/src \
  python3.12 -m pytest -q --no-header -p no:randomly
# → 2407 passed, 1 failed (both runs)
cd coga && PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/home/n/Code/codex/coga-simplify-ticket-format/src \
  python3.12 -m coga.validate --json
# → exit 1: the same 4 baseline unsynthesized-draft-blackboard errors,
#   22 warnings (15 unfrozen-workflow, 5 stuck-in-progress, 2 large-blackboard),
#   0 unknown-assignee, no new finding kinds
```

The single failure is the pre-existing environmental
`test_packaging.py::test_wheel_includes_bootstrap_batteries` (`hatchling.build`
not importable on this machine); it reproduces on control and is carried as the
adjacent finding above. A read-only frontmatter scan of the rebased population
shows 211 tasks with **zero** residual `slug`/`human`/`assignee`/`watchers`/
`script` keys and zero empty `contexts`/`skills`/`secrets` declarations.

Nothing mutating was run from the feature checkout. The control checkout keeps
its old-schema copy of this ticket for the remaining pre-merge transitions.

**Merge-gate note.** Control has now moved four times across implementation and
this step, twice within the ~10 minutes of this session. That is direct evidence
for Shape 7's warning: the conversion commit must be refreshed from the exact
control revision at the gate, and the field/token diff re-verified, and it will
likely need repeating. Stopping the dispatchers first is what makes that
comparison hold still.

## PR-review assist — 2026-09-10

- Verified the recorded feature checkout is clean on `simplify-ticket-format`.
  PR #784 is open, its actual head repository matches the sole configured
  `origin` push URL (`https://github.com/FastJVM/coga`), and a fresh private-ref
  fetch matches both local HEAD and the reported PR head at `a4c6b5921902`.
  The private verification ref was deleted after recording the OID.
- The attending owner approved all four fixes with "ok" after the concrete
  plan and tradeoffs. Applied them in the recorded feature checkout:
  - `Template.load` rejects every `REJECTED_TICKET_KEYS` field before named or
    scheduled materialization; validation reports the offending names as
    `bad-recurring-template`. Tests cover all four fields and confirm no period,
    audit write, or template mutation occurs.
  - Bootstrap completion uses `resolve_main_agent` for the target's explicit
    agent or configured default. Invalid explicit choices refuse before
    posting, auditing, or emitting completion. Tests verify message and audit
    attribution, the completion sentinel, and unchanged target bytes.
  - Frozen future peer steps validate against the prospective default when
    `agent` is absent, without persisting it. Tests cover one/two/three-agent
    configurations, explicit peers, ambiguity, and malformed explicit values
    retaining their schema diagnostics.
  - Corrected current-direction, architecture and recurring contexts, existing
    packaged twins, code/docs review workflows, and calendar-reminder examples
    to describe derived operators, live peers, and ephemeral overrides.
    Removed the remaining instructions to write a top-level assignment.
- Saved source-pinned read-only validation baselines in
  `/tmp/coga-pr784-review-{real,example}-before.json`: real has the same four
  draft-blackboard errors and 22 warnings (15 unfrozen workflows, five idle
  tasks, two large blackboards); example has no findings. The inherited bare
  Slack variable was unset for the example; no webhook or secret was probed.
  After-fix reports at the corresponding `*-after.json` paths have exactly the
  same task/kind/severity counts: no findings added or removed. Real validation
  exits 1 for its four existing errors; example validation exits 0.
- Resolved the previously reported test-environment gap without changing an
  installed writer: created `/tmp/coga-pr784-review-venv` using Python 3.12
  with system site packages and installed the declared Hatchling test
  dependency there. The earlier packaging failure is therefore no longer an
  unverified exception: the full source-pinned suite, including wheel build and
  twin parity, passed: **2425 passed in 206.04s (0:03:26)**. The focused
  regressions and twin check passed **20 tests in 1.74s**. Full output is saved
  at `/tmp/coga-pr784-full-suite.txt`; `git diff --check` passes.
- Committed and pushed `55f8829906a324f5f9f86e35c38666fae42d5821`
  (`Fix simplified ticket routing review findings`). Fresh PR metadata and a
  new private-ref fetch agreed on `a4c6b5921902`; ancestry proof passed and the
  push used that exact tip as its lease. GitHub's post-push head and local HEAD
  both equal the fix commit. Re-read each thread immediately before replying;
  all four now have one fix/test reply and remain unresolved for the owner.
- The feature checkout is clean. The control ticket remains old-schema,
  `in_progress`, step `6 (review)`; only this blackboard changed there, and the
  existing dirty `coga/log.md` was not edited or staged. No mutating Coga command
  ran in the feature checkout. No bump, completion, merge, branch deletion, or
  thread resolution was performed. Shape 7's writer quiet window, final
  control/conversion reconciliation, and owner merge decision remain open.

```sh
# From the recorded feature checkout:
PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/home/n/Code/codex/coga-simplify-ticket-format/src \
  /tmp/coga-pr784-review-venv/bin/python -m pytest -q --no-header \
  -p no:randomly -p no:cacheprovider

# From its coga/ directory:
PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/home/n/Code/codex/coga-simplify-ticket-format/src \
  /tmp/coga-pr784-review-venv/bin/python -m coga.validate --json

# From its example/coga/ directory:
env -u SLACK_WEBHOOK_URL PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/home/n/Code/codex/coga-simplify-ticket-format/src \
  /tmp/coga-pr784-review-venv/bin/python -m coga.validate --json
```
