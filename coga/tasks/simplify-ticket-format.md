---
slug: simplify-ticket-format
title: simplify ticket format
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts: []
skills: []
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
secrets: null
step: 2 (evaluate-design)
---

## Description

Simplify ticket frontmatter by removing unused or redundant fields and omitting
empty optional metadata. The human approved the field-removal proposal on
2026-09-09; retain an optional per-ticket agent choice and preserve workflow
routing, human approval gates, ownership, and nonempty contexts/skills/secrets.

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

#### 3. Optional agent timing — proposal for owner review

Proposed default: leave `agent` absent on new drafts unless explicitly chosen;
when activation first approves work, resolve `Config.default_agent()` and
persist that name in the existing `agent` field. The default is the first
declared agent in the effective, merged configuration. Creation straight to a
live status (recurring and retire) performs the same selection. This gives up
omission on activated tickets in exchange for a stable main-agent identity.
The attended owner has been asked to choose this versus live resolution; do
not treat the proposal as approved until the question below is settled.

Selection belongs in pure prospective preparation, committed with the
successful lifecycle transition. A draft with a frozen workflow still defers
default-agent persistence until activation. Read-only status, show, compose,
and validate may report the effective/prospective default but never persist it.
Under this proposal, an activated task must retain its selected agent: a
hand-authored live ticket with the field missing is an activation-invariant
validation error, just as an unfrozen live workflow is. The human can choose
`agent` explicitly through authoring or run `mark active` to select the
default. Plain bump/block/pause transitions must not choose a main agent at a
peer step. This conditional requirement is part of the tradeoff the owner is
reviewing; the field remains optional for drafts, terminal records, templates,
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

For the alternative of live default resolution, the owner must explicitly
accept that reordering agents between launches can turn an omitted ticket's
A -> peer B -> A sequence into A -> peer A -> B. Implement only the selected
contract, not both modes or a configuration switch between them.

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
reviewer. Flag this consequence for the owner review.

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
  Include the retained same-worker/peer override consequence.
- Script-only and script-to-agent handoffs, unanswered blocked-resume
  restoration, and stale owner/agent/role edits invalidating same-step assist
  leases and pre-spawn checks. Preserve the existing pending-claim and rollback
  regression coverage; do not weaken those fixtures to get the suite green.
- Stateless bootstrap dispatch, guided authoring, normal/delegated recurring
  creation and retry, promotion, template-without-workflow materialization,
  scoped secrets, human handoffs, and megalaunch owner/blocker eligibility.
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
  section is explicitly a proposal pending the owner's choice, not approval.
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

- **Default-agent timing:** the attended owner was asked whether activation
  should freeze the default. This spec recommends freezing and states its
  conditional requirement on live tickets. The alternative is leaving agent
  omitted and accepting config-driven main/peer changes between launches.
  Await the human's choice; settle it at `review-design` before implementation.
- **Override/peer consequence:** confirm retention of the existing ephemeral
  override boundary, including possible Codex -> Codex -> Claude routing when
  overriding a Claude-main workflow. An override is not a main-agent choice;
  a guarantee of a different actual reviewer would require a separate design
  choice, not an implicit change during field deletion.
- **Cutover feasibility:** can the owner arrange the described quiet window
  across the control checkout, feature checkouts, installed writers, and
  scheduled/supervised sessions? If not, approve a split for a preparatory
  writer-admission guard before attempting the atomic format PR. Do not claim
  the current lifecycle guard already provides that protection.
