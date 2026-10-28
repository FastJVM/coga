---
title: Coalesce Coga state commits to one per lifecycle event
status: in_progress
owner: nicktoper
contexts:
- coga-dev/principles
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
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 4 (implement)
agent: claude
launch_generation: pending:0000ba94-dc39-4476-8910-7ccca8ba582c
---

## Description

Coga's own state publication buries real work in `git log`: of the last 300
commits on `main` examined on 2026-10-23, 233 were bookkeeping (`Ticket: …`,
`Log: …`, and `Sync coga state …`), with several commits per launched step.
Design and implement coalescing of writes that can share a publication
boundary, reducing bookkeeping without delaying state another operator needs.

The design step establishes and justifies an achievable commit bound for
explicit launch scenarios; the owner approves it before implementation. One
lifecycle commit plus at most one teardown log commit is a hypothesis for a
step with no separate startup publications, not a promised total for every
launch. The usage record is captured after the agent's final lifecycle sync;
activation, start, branch linkage, and queue admission can introduce other
publication deadlines that the design must account for.

### Proposed bound and counting interval

Propose **three commits for a successful ordinary managed agent step**:
one startup publication, one lifecycle handoff, and one usage publication.
This is a proposal for `review-design`, not an approved implementation contract.
Startup is work with its own deadline; a whole-launch limit of two would
require relaxing that deadline or the later usage contract.

Count new commits reachable from the bare remote's control ref from immediately
before CLI launch entry until after usage capture, checkout return, and the
outer CLI sweep. Include entry settlement and every startup publication in
that interval. Seed commits and pre-existing branch linkage precede the start
OID. Count local control too, and require it to finish at the remote tip.

The bounded workload starts clean and current with working Git, no competing
publisher, no `ticket.py`, no resumed blocker or recorded human assist, and
an agent-held step. It stays on control or uses automatic branch preparation;
its only session edits are its own handoff/blackboard followed by one CLI bump
to an owner-held step. Usage capture appends exactly one deterministic record.
The agent runs no other mutating command and writes nothing after bump.

| Ordinary entry | Measured current commits: control or reuse / create | Proposed maximum, including usage |
| --- | ---: | ---: |
| Resumed `in_progress` | 3 / 4 | 3 |
| Initial `active` | 4 / 5 | 3 |
| Initial `draft` with activation | 5 / 6 | 3 |

The current measurements used real publication and checkout code; their
method and limitations are on the blackboard. The proposed counts still need
implementation tests. With no new usage line, teardown may contribute zero
commits; it must still attempt publication or report failure. In the fixture
above, assert exactly three and their contents, not merely `<= 3`.

No fixed total covers arbitrary agent work. An entry settlement of pre-existing
eligible dirt is an additional publication before the authoritative read;
another mutating command can publish a blackboard edit before bump; later
eligible edits can require checkout settlement. Keep those publishers and
count the additional events explicitly in separate tests. Do not suppress the
sweep or absorb unrelated dirty roots merely to pass the three-commit case.
An unchanged sweep, including a repeated sweep after return, adds zero.

### Publication boundaries and path classification

1. **Ordinary managed startup.** Activation, start, new branch linkage, and
   the launch audit share one pre-spawn boundary. Prepare all of them before
   writing; publish the final ticket and audit together before switching or
   exposing an executable agent. Keep activation and start as distinct audit
   events in their current order. A resumed step with no new linkage still
   needs its log-only startup commit: the start line must not stay dirty
   throughout an attended session. No startup line is deferred to bump.
2. **Handoff.** Bump/mark/block continue publishing the finalized ticket and
   event log before their command returns or releases the session. The
   launcher must not hold that publication until it can append usage. An
   ordinary lifecycle subject stays `Ticket: <slug> — <event>`; a bump keeps
   its numbered destination step. Its blackboard handoff is in that commit.
3. **Teardown.** Usage is only available after the agent's final command.
   Preserve the log-only, union-safe teardown publication and its warning.
   Checkout return and the final sweep remain independent safety nets and
   must be no-ops for the bounded workload.

Other paths retain their current publication contracts in this ticket:

| Path | Accounting and retained boundary |
| --- | --- |
| Megalaunch, active or unclaimed `in_progress`, one bump on control | 4 commits with usage: pending start claim, admitted generation plus launch audit, bump, usage. The first two straddle held-child release and cannot be combined. |
| Megalaunch, explicit draft/paused activation | Add 1 activation commit: 5 in the equivalent clean case. Keep the existing independently committed strict activation transaction and its rollback/uncertainty semantics. This is a deliberate scope choice, not a claim that an atomic activation-plus-claim redesign is impossible. Dependency-drain blocker resolution remains durable before claiming. |
| Megalaunch with agent-created branch or additional commands | Add their actual publications. The queue does not call ordinary managed branch preparation; three is not its bound. |
| Agent bootstrap, including chat/orientation | Start log plus usage: 2 for a no-write session. State written by the agent adds settlement/sweep publications. No task lifecycle sync can substitute for the start log. |
| Guided authoring (`coga ticket`) | Keep immediate start-log publication, usage teardown, then the guarded authored-set publication (3 when that set changes), plus any independent agent commands. Never leave the start line dirty during the interview or split refused authored state through a fallback sweep. |
| Stateful `ticket.py` launch | Keep activation if needed, start if needed, script launch log before user code, any lifecycle commands run by the script, and the script-exit line's settlement/sweep. A clean active script that bumps once has 4 commits; draft adds activation, resumed `in_progress` removes start. A later agent phase has its own audit/usage. Stateless scripts have no task startup audit/lifecycle and are counted by their actual writes. |
| Recurring period and delegated bootstrap | Keep period creation/adoption, strict start/lease checks, delegated-launch audit, child audit/usage, result publication and serviced-period ledger publishers in their existing order. Count each selected phase; neither the ordinary three nor the queue four is a whole recurring-run bound. |
| Exempt/unmanaged launch, recorded assist, blocked resume, Git disabled | Preserve their current routes and diagnostics. No three-commit promise; Git-disabled publication produces no commits and claims no remote durability. |

The owner must approve both the ordinary reduction and these exclusions.
In particular, resumed ordinary reuse already costs three and resumed queue
work already costs four: this proposal does not promise savings there.

### Acceptance criteria

- [ ] The owner has approved the bound, path exclusions, and changed ordinary
  startup/failure semantics at `review-design`; implementation records the
  decision and does not silently substitute a different bound.
- [ ] Seeded real-Git tests cover the nine ordinary status/checkout combinations
  above, each with one owner handoff and one usage record. Add a draft with a
  workflow-name reference to exercise freezing and agent selection, not just
  an already frozen draft, and cover paused reactivation if it uses grouping.
  Assert remote commit counts, ordered subjects,
  changed paths, audit lines, handoff bytes, and final clean/current control.
- [ ] Before agent execution, remote control holds the final startup ticket,
  audit, and any new linkage; before a branch switch the invoking control
  checkout is clean. After the child bump returns but before usage capture,
  remote control already holds the next step and handoff. The usage record
  appears only in the later log publication. No startup/usage line is lost
  or duplicated by repeated publication or concurrent remote log appends.
- [ ] The ordinary start group emits one commit even when activation and
  branch creation both occur. The unchanged `bump` publication is one commit;
  entry, return, and final sweeps contribute zero for this workload. Separate
  tests show an intervening mutating command/extra eligible edit remains
  publishable and is honestly counted outside that workload.
- [ ] Before any startup write, composition, secret, policy, target-branch,
  occupancy, ignored-path, and source-ticket refusals start no agent and emit
  no launch audit. A reserved branch/receipt can survive for retry. Startup
  publication failure/refusal/uncertainty starts no agent, retains written
  evidence, and withholds return/sweep with exit 75. Failed verification after
  a push never rolls control backward or publishes a compensating transition.
- [ ] Natural exit without a transition, nonzero child exit, timeout,
  SIGINT/SIGTERM cleanup, and spawn failure each retain publish-or-report
  behavior. A dirty handoff without bump is published by existing settlement
  or retained with diagnostics; usage failure preserves the child's result.
  Ignored logs, unavailable control, stale tickets, and return refusal still
  produce the existing retained-log/session-end/withheld-sweep reports. Test
  abrupt process death separately as next-entry recovery, not a promise that
  uncatchable termination executes `finally`.
- [ ] Queue real-Git cases assert 4/5 as classified above and preserve the
  pending seal, post-release admission, exact-source guards, compensation,
  retained `released:` evidence, and concurrent-claim exclusion. Bootstrap,
  authoring, script, recurring, and exempt-path regression coverage confirms
  their publishers were not accidentally opted into ordinary grouping.
- [ ] Commit classification is unchanged: ordinary lifecycle subjects are
  activity; ordinary `Log:` and `Sync coga state` are machine activity;
  `Log: bootstrap/...` is activity; recurring/autofix lifecycle subjects and
  blocker reminders remain machine activity. Test representative generated
  startup, bump, and teardown subjects against the existing classifier.
- [ ] Re-inventory every `append_log` call under `src/`. For each changed
  writer, document its exact later publisher and every exit before it;
  failure records remain reported without a retry loop. Update the owning
  publication/launch/checkout topics and shipped twins in the implementation
  PR, and run `python -m pytest` with exact command/count receipts.

### Proposed shape

Keep grouping local to ordinary managed launch startup. Do not add a global
publication queue, cross-process accumulator, or a default that disables
publication in lifecycle helpers. Existing direct commands and strict callers
must retain their current behavior.

1. In `src/coga/launch.py`, change `_LaunchInvocation`'s ordinary agent-only
   path so `_commit_auto_activate` and `_start_session` do not independently
   publish before `_prepare_step_checkout`. Carry the captured authoritative
   source bytes and a prospective lifecycle view through the first loop
   iteration: `_supervise_steps` currently re-reads the ticket, which would
   otherwise discard an in-memory activation. Restrict opt-in to an armed,
   managed, agent-only launch; scripts, assists, blocked resumes and guarded
   recurring/queue entry points stay on their existing routes. Later chained
   managed steps each perform their own startup group and teardown.
2. In `src/coga/mark.py`, reuse `prepare_active` for validation/freezing/main
   agent selection and extract a small pure preparation seam from
   `mark_in_progress` if needed. The durable wrappers continue to own their
   standalone writes, audit, and failure behavior; launch uses preparation
   plus one explicit startup finalizer. Preserve event text, actors, prior
   status, and notification cardinality. Send a successful-start notification
   only after grouped publication is confirmed; notification failure remains
   non-fatal and its failure record follows the existing report/sweep rules.
3. In `src/coga/checkouts.py`, split `plan_ticket_checkout`'s reservation and
   validation from `_publish_linkage`'s durable write. Planning must prove
   clean control against the captured **source** ticket, then derive the
   policy/notice and prospective `branch:` from the prepared final ticket.
   Reserve/create using `_reserve_and_create`; do not write linkage just to
   compose. Keep the reserved OID/name and existing branch-occupancy,
   ignored-file, stranded-ticket, and reuse proofs. Compose from the
   prospective ticket/notice only after those checks pass.
4. Finalize startup under `git.state_lock`: recheck local source bytes and
   the planned contract; write the final ticket only if changed, append
   applicable activation/start/launch events, and call the existing
   `src/coga/git.py::publish` once for that task and log. Pin the original
   ticket with `expect` and require the log, retaining all existing candidate,
   provenance, regression, union-merge, and push-retry guards. A log-only
   resume must also revalidate the ticket before entering: `expect` alone
   does not guard an unchanged, unselected ticket. Require a confirmed
   publication result, including already-held state where appropriate.
5. Re-prove fetched control and its ticket after publication; update the
   reservation receipt to published only when linkage is confirmed. Rebase
   the checkout plan on that control snapshot via
   `src/coga/checkouts.py::confirm_ticket_checkout` and retain all of
   `enter_ticket_checkout`'s cleanliness, switch, projection, and provenance
   checks. Recompose if compatible owner notes changed; refuse changed
   lifecycle/routing/policy/branch identity. Pass `record_launch=False` to
   `src/coga/launch.py::spawn_agent_session` only after the audit is durable.
   Preserve `spawn_agent_session`'s usage `finally` and log-only publication.
6. On grouped publication failure, use the existing checkout refusal path:
   preserve final local ticket/log and reservation, report refused versus
   failed versus uncertain, withhold sweep/return, and exit 75. A later
   ordinary entry first reconciles retained state. Never re-run an already
   recorded lifecycle transition as a publication retry. Before materializing
   the group, a failed plan leaves the source ticket/log unchanged. This
   changes the intermediate states left by failed startup and needs the
   owner decision below.

For startup subjects retain `Ticket: <slug> — in_progress` when starting
(including activation); otherwise retain the branch-event subject when
recording a new branch; use `Log: <slug>` when only an audit is new. These
preserve the activity contributed by the corresponding existing commits.
Do not relabel a log-only resume as an ordinary lifecycle event.

Add integration coverage beside `tests/test_launch.py` / `tests/test_checkouts.py`
using `tests/conftest.py::init_git_repo` (or its `git_repo` fixture). Replace
only the agent/usage/environmental dependencies; exercise real composition,
startup, lifecycle publication, union merge, checkout return, and
`src/coga/cli.py::main`'s sweep. A `CliRunner().invoke(app, ...)` alone bypasses
that outer sweep and is insufficient for the whole-command count. Keep
cross-checkout and held-child race coverage in `tests/test_megalaunch.py`;
pin subject classification in `tests/test_recurring_activity.py`.

### Out of scope

Log retention/compaction (the sibling ticket), shared-history rewriting or
force pushes, removing audit events, broadening inactivity classification,
sandbox Git-access remedies, delayed lifecycle handoffs, batching across
agent steps or commands, and a general transaction framework. Also excluded
are queue ownership/admission redesign, folding strict queue activation into
its pending claim, broadening a task publication into a root sweep, and
changing authoring/script/recurring publication contracts. Their existing
safety tests and explicit accounting remain required.

## Context

Split from `fix-the-commit-git-journal` (deleted); sibling
`commit-journal/trim-the-audit-log` owns log size and retention.

### Prerequisite already landed

`commit-journal/publish-log-lines-left-uncommitted` landed in
[PR #1117](https://github.com/FastJVM/coga/pull/1117) on 2026-10-26. Its durable
contract is in `coga/state-publication`, "Every log line has a publisher":
each log write publishes before its command exits, reports retained lines,
or has a documented later publisher. The inventory distinguishes lifecycle
syncs, explicit log syncs, and sweeps; initialization's human-owned first
push, usage teardown, writer-owned later publishes, and withheld-state exits
are deliberate exceptions. Failure records are covered by the failure
report, not retried in a publication loop.

That work deliberately made `coga ticket` publish its start line immediately,
matching chat and ordinary launch: a dirty log throughout an attended session
can block fast-forwards and clean-checkout checks. Any proposed deferral must
address that reason and identify its later publisher, including when the
agent never bumps. Re-inventory `logfile.append_log` callers across `src/`
and update the owning topic's deliberate-deferral list for every changed path.
`src/coga/checkouts.py::enter_ticket_checkout` requires clean control before switching;
deferring the managed launch audit must preserve that precondition.

### Where commits come from

- `src/coga/git.py::sync_log` publishes `log.md` alone. In
  `src/coga/launch.py`, `_LaunchInvocation._prepare_step_checkout` calls it
  before switching; unmanaged launches pass `commit_log=True` from
  `_LaunchInvocation._supervise_steps` to `spawn_agent_session`.
  `src/coga/commands/ticket.py::_run_authoring_session` passes it too.
  Script and recurring launch writers have their own paths.
- `src/coga/git.py::sync_task_state` publishes a task and the log together.
  Besides `src/coga/bump.py::advance_step`, inspect
  `src/coga/mark.py::mark_active` / `mark_in_progress` and
  `src/coga/checkouts.py::_publish_linkage`: launch startup can publish
  before the final bump. Commit subjects must still name the ticket and event, such as
  `Ticket: <slug> — step 4 (review)`.
- `src/coga/megalaunch.py::_launch_until_stop` publishes a strict start claim;
  its `_admit_launch_claim_after_release` separately publishes the
  admitted generation and launch audit after releasing the held child. Their
  ordering protects concurrent launches and cannot be folded away casually.
- `src/coga/git.py::sync_coga_state` covers entry/return settlement and the
  exit sweep selected by `src/coga/cli.py::_should_sweep_coga_state`. An agent's blackboard edit can
  be swept by a command before bumping; the historical extra sweep
  `a2388fbe0` carried such a `pr:` edit.
- `src/coga/launch.py::spawn_agent_session` captures usage in `finally` and
  then calls `src/coga/git.py::sync_log`, after the agent's final
  `bump`/`mark` publication. `src/coga/cli.py::_warn_unpublished_log_lines`
  checks changed logs at command exit,
  including after a sweep; coalescing must preserve this failure reporting.

### Log-writer inventory for implementation

AST inspection of `src/**/*.py` on the design baseline found these direct
`append_log` call sites (including nested functions). Recheck after edits;
this ticket snapshot does not replace the publication topic's contract.

| Source and symbols | Publisher class / treatment |
| --- | --- |
| `src/coga/launch.py`: `_LaunchInvocation._prepare_step_checkout`, `spawn_agent_session.record_and_publish_launch_audit` | Managed startup changes to the group; all other spawn callers retain immediate or caller-guarded publication. |
| `src/coga/mark.py`: `mark_active`, `mark_in_progress`, `mark_done`, `mark_canceled`, `mark_blocked`, `mark_paused`; `src/coga/bump.py`: `advance_step` | Lifecycle writers; only managed launch's activation/start call sequence changes. Standalone commands and strict callers stay immediate. |
| `src/coga/commands/owner.py`: `owner`; `src/coga/commands/unblock.py`: `_apply_unblock` (two calls) | Existing task-plus-log publication. |
| `src/coga/create.py`: `create_task`; `src/coga/commands/init.py`: `_do_init` | Creation caller owns publication; init's scaffold commit leaves first push to the human. |
| `src/coga/commands/slack.py`: `slack` | Existing command-exit sweep. |
| `src/coga/launch_script.py`: `run_script_phase` (launch and exit calls) | Start publishes before user code; exit rides strict-assist result publication, settlement, or sweep. |
| `src/coga/recurring.py`: `create_template`, `promote_task`, `_record_run`; `src/coga/recurring_runner.py`: `_append_forced_reused_log` | Existing recurring transaction/ledger or command sweep; no new deferral. |
| `src/coga/recurring_runner.py`: `_run_delegated_task.start_period` | Explicit launch-log publication under the existing period lease checks. |
| `src/coga/usage.py`: `append_record` | `src/coga/launch.py::spawn_agent_session` captures then publishes at teardown. |
| `src/coga/git.py`: `record_sync_failure`, `_guard`, `refresh`; `src/coga/notification/slack.py`: `SlackChannel.send.fail`; `src/coga/recurring_runner.py`: `_append_sync_failure`; `src/coga_edge/phone_home.py`: `run_phone_home` | Failure reports cover their audit lines; no recursive publish retry. |

### Inactivity classification

Preserve `src/coga/recurring_activity.py::is_machine_commit` and `_MACHINE_SUBJECT`
semantics, including the exceptions. Ordinary ticket lifecycle commits
count as activity; `Ticket: recurring/…`, `Ticket: autofix/…`, and blocker
reminders remain machine activity. Ordinary `Log:` and `Sync coga state`
commits remain machine activity, while `Log: bootstrap/…` counts as activity.
A coalesced ordinary lifecycle event must keep its activity classification,
and coalescing must not turn recurring/autofix lifecycle events into human
activity. Pin the affected subjects in regression coverage, using
`tests/test_recurring_activity.py` as the existing reference. Do not broaden
the classifier to make the repository look idle.

### Topics (cited, not attached; read before design)

- `coga/state-publication` at
  `docs/contexts/coga/state-publication/SKILL.md`, "When Coga publishes" and
  "Every log line has a publisher", plus "Control versus feature checkouts",
  owns publication deadlines and the deliberate deferrals summarized above. This is an edit target; update it
  and its twin at
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md`
  together.
- `coga-dev/internals/state-publication` at
  `docs/contexts/coga-dev/internals/state-publication/SKILL.md`, "Invariants"
  and "The end-of-command sweep", owns control as canonical, retaining
  failed writes, candidate selection, and deliberate sweep skips. Its leaf
  `coga-dev/internals/state-publication/publish` at
  `docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md`,
  "`publish` and its wrappers" and "Best-effort versus strict", owns the
  guarded transaction and failure distinctions that coalescing must retain.
- `coga-dev/internals/spool-merge` at
  `docs/contexts/coga-dev/internals/spool-merge/SKILL.md`, "How `publish`
  lands a union path" and "Crash-safe replacement is not a lock", owns
  concurrent append preservation and duplicate suppression. Keep log
  publication on that union-safe path; atomic writes and the per-checkout
  lock do not provide a cross-checkout lock.
- `coga-dev/internals/launch-claims` at
  `docs/contexts/coga-dev/internals/launch-claims/SKILL.md`, "Strict claim
  publication", "The pending seal", and "Held child and admission", owns
  the claim ordering summarized above. Account for those boundaries without
  redesigning launch ownership in this ticket.
- Also read the edit targets `coga/launch` at
  `docs/contexts/coga/launch/SKILL.md` ("Agent preflight order"),
  `coga/lifecycle` at `docs/contexts/coga/lifecycle/SKILL.md` ("Status"),
  `coga/checkouts` at `docs/contexts/coga/checkouts/SKILL.md` ("In a launched
  session"), and `coga/checkouts/launch-boundary` at
  `docs/contexts/coga/checkouts/launch-boundary/SKILL.md` ("Preparation and
  return"). Update their descriptions of grouped startup, intermediate
  state, and refusal recovery, with each corresponding packaged topic under
  `src/coga/resources/templates/coga/bootstrap/contexts/`. Link to
  `coga/state-publication` for the counting contract rather than duplicating it.
  The local-only source-order account in `coga-dev/internals/agent-spawn` at
  `docs/contexts/coga-dev/internals/agent-spawn/SKILL.md` ("Launch API and
  phases", "Order inside one call") must agree with the new call sequence.

Update any cited topic whose behavior changes in the same PR, keeping shipped
twins identical. Out of scope: log retention/compaction and sandbox Git-access
failures; this ticket preserves their existing reporting and recovery.

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

## Dev

branch: coga/coalesce-state-commits

## PR

```yaml
title: Coalesce ordinary managed launch startup publication
author: codex
author_evidence: This implement session used Codex, not the ticket-configured Claude. No delegated implementation
  or code review ran.
head: 4e5f4b03c811f39f3a3721212d48862391fae060
base: 36c85653c2ce522882d73e7d9226ff42dc98d1f5
depth: deep
rationale: Changes startup publication and refusal semantics; inspect the guards and real-Git race tests.
  The full suite has a reproduced unrelated baseline failure and code review has not run.
implementation: Prepare activation/start and checkout linkage in memory, publish the final ticket and
  startup audit once before switch/spawn, and confirm every plan against fetched control. Handoff and
  usage remain immediate independent publications. Start notification follows confirmed checkout entry.
  Ordinary count fixtures assert three commits; queue, bootstrap, scripts and extra events retain their
  classified boundaries.
deviations: No implementation scope deviation. The implement step is blocked instead of advanced because
  code/implement requires escalation of unrelated test failures.
limitations: The untouched docs/README.md anchor failure must be repaired or explicitly waived by the
  owner before this step can complete. Native Windows cases and a Python 3.11 test run are not covered
  by this Linux/Python 3.12 receipt. Peer review and PR creation remain later workflow steps.
files:
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: Align internal phase order and caller-owned startup
    audit with grouped publication.
  docs/contexts/coga-dev/internals/state-publication/SKILL.md: Document grouped startup guards and retained-state
    semantics within the existing publication machinery.
  docs/contexts/coga-dev/internals/state-publication/log-writers/SKILL.md: Inventory all 32 direct audit
    writers, their publishers, and exits that retain evidence.
  docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md: Document grouped startup guards
    and retained-state semantics within the existing publication machinery.
  docs/contexts/coga/checkouts/SKILL.md: Align the owning launch/lifecycle/checkout/publication contract
    with grouped startup and its failure recovery; keep the shipped twin identical.
  docs/contexts/coga/checkouts/launch-boundary/SKILL.md: Align the owning launch/lifecycle/checkout/publication
    contract with grouped startup and its failure recovery; keep the shipped twin identical.
  docs/contexts/coga/launch/SKILL.md: Align the owning launch/lifecycle/checkout/publication contract
    with grouped startup and its failure recovery; keep the shipped twin identical.
  docs/contexts/coga/lifecycle/SKILL.md: Align the owning launch/lifecycle/checkout/publication contract
    with grouped startup and its failure recovery; keep the shipped twin identical.
  docs/contexts/coga/state-publication/SKILL.md: Align the owning launch/lifecycle/checkout/publication
    contract with grouped startup and its failure recovery; keep the shipped twin identical.
  docs/contexts/coga/state-publication/launch-boundaries/SKILL.md: Own the approved commit-count workload,
    interval, subjects and explicit path exclusions; keep the shipped twin identical.
  src/coga/checkouts.py: Prepare prospective linkage against captured source bytes, recheck paths/target,
    and confirm control-only as well as branch plans.
  src/coga/launch.py: Group only ordinary managed agent startup, preserve the prospective lifecycle across
    supervision, and retain/report unconfirmed writes before any spawn.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: Align the owning launch/lifecycle/checkout/publication
    contract with grouped startup and its failure recovery; keep the shipped twin identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/launch-boundary/SKILL.md: Align
    the owning launch/lifecycle/checkout/publication contract with grouped startup and its failure recovery;
    keep the shipped twin identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: Align the owning launch/lifecycle/checkout/publication
    contract with grouped startup and its failure recovery; keep the shipped twin identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md: Align the owning launch/lifecycle/checkout/publication
    contract with grouped startup and its failure recovery; keep the shipped twin identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Align the owning
    launch/lifecycle/checkout/publication contract with grouped startup and its failure recovery; keep
    the shipped twin identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/launch-boundaries/SKILL.md: Own
    the approved commit-count workload, interval, subjects and explicit path exclusions; keep the shipped
    twin identical.
  tests/conftest.py: Share deterministic usage capture through the real audit writer for publication-count
    fixtures.
  tests/test_checkouts.py: Exercise whole CLI publication counts, exact contents, startup refusals/races,
    recovery, cleanup, notification failure, and excluded bootstrap/script routes with real Git.
  tests/test_megalaunch.py: Assert retained four/five-commit queue boundaries around held-child release
    and admission.
  tests/test_packaging.py: Register the new shipped launch-boundaries topic in the required distribution
    manifest.
  tests/test_recurring_activity.py: Pin startup, linkage, bump, teardown and exceptional activity classifications.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Code review belongs to the later peer-review step. Design approval is not code review; implement
    has not bumped because of the baseline test failure.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest
  status: failed
  head: 4e5f4b03c811f39f3a3721212d48862391fae060
  base: 36c85653c2ce522882d73e7d9226ff42dc98d1f5
  detail: 'Python 3.12.12: 4186 passed, 10 skipped, 1 failed in 479.31s. Only failure: tests/test_packaging.py::test_context_navigation_has_no_broken_links,
    the pre-existing docs/README.md link to missing ../README.md#key-concepts. Reproduced on baseline
    36c85653c2ce522882d73e7d9226ff42dc98d1f5. Skips: 2 native Windows job-object integration cases, 5
    native Windows PowerShell 5.1 cases, 3 native Windows Job Object recovery cases. No exclusions were
    added. Staged tree 92f1633a4a86f9574cb4cc7947052610394f2135 and all 23 changed-file SHA-256 hashes
    were verified unchanged before commit; the commit has that exact tree.'
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python
    -m coga.cli validate --json
  status: passed
  head: 4e5f4b03c811f39f3a3721212d48862391fae060
  base: 36c85653c2ce522882d73e7d9226ff42dc98d1f5
  detail: 'Run from tests/fixtures/seeded-repo/coga: 4 valid tasks, no issues.'
- command: git diff --cached --check
  status: passed
  head: 4e5f4b03c811f39f3a3721212d48862391fae060
  base: 36c85653c2ce522882d73e7d9226ff42dc98d1f5
  detail: No whitespace errors in the staged implementation tree, verified identical to the committed
    tree.
- command: python3.11 -m pytest
  status: not-run
  detail: Python 3.11.15 is present, but python3.11 -m pytest --version reports No module named pytest.
    The executed full-suite receipt covers Python 3.12.12 only.
```

## Implementation handoff

Implementation is committed and pushed at `4e5f4b03c811f39f3a3721212d48862391fae060` on `coga/coalesce-state-commits`.
Fetched control remained at `36c85653c2ce522882d73e7d9226ff42dc98d1f5` through the tested commit and final
rebase (a no-op); source and topic bytes match the recorded tested tree. The
later control movement only publishes this ticket’s notes. Returned to clean,
current main before writing this handoff. No PR was opened and no workflow
bump ran.

The full suite completed with **4186 passed, 10 skipped, 1 failed**. The only
failure is the reproduced pre-existing README anchor; the new topic manifest
registration is fixed and all distribution/twin checks pass. Do not fix or
waive that unrelated failure under this ticket without owner direction.
Repair the link on control, or explicitly authorize a baseline exception;
then resume implement, reconcile the pushed branch, refresh verification as
needed, and bump once to peer-review. No implementation bug remains known.

## Implementation

2026-10-27: Owner approval is recorded by the human `nicktoper` advancing
`review-design` to `implement` in commit `fe2bf3293fe32839d00dc61acfee1b303fbf3b22`
and the corresponding audit event. Proceeding with the specified three-commit
ordinary bound, explicit path exclusions, and retained-state startup failure
contract. The older design questions below are resolved by that owner gate.
Actual implementer: Codex (GPT-6); the ticket's configured agent is not this
session's implementation identity. Started on clean, fetched main at
`f39663577`; no previous feature branch or PR. Following the manual checkout
procedure because the runtime supplied no branch preparation.

Plan: separate lifecycle/checkout preparation from the one ordinary startup
publication; preserve all other publishers; prove counts and refusal behavior
with the real-Git fixtures; update canonical topics and shipped twins. Review
and PR creation remain later workflow steps.

Implementation progress: ordinary startup now plans against captured source
bytes, prepares linkage without a ticket write, and publishes final lifecycle,
linkage and audit together. Publication guards cover unchanged control-only
resumes; every plan is confirmed again before entry. Successful-start delivery
runs after checkout entry so a reported notification failure cannot dirty
control before its switch proof. Direct lifecycle commands, queue claims,
script/authoring/recurring paths, handoff and log-only usage remain separate.

Real-Git tests now assert exactly three publications for the nine ordinary
status/checkout combinations, named-workflow activation and paused startup;
four/five for queue claim/admission paths; bootstrap and script boundaries;
and extra entry/intervening-command/return events outside the bound. Targeted
failure tests cover no-write preflight refusal, failed/refused/skipped/uncertain
publication, post-push uncertainty, control-only routing races, concurrent log
appends, cleanup and abrupt-death next-entry recovery. Full verification and
commit receipts are recorded under `## PR`; the baseline failure prevents advancement. AST inventory finds 32 direct append_log sites;
the new internal log-writers topic records their publisher and retained exits.

### Verification blocker discovered during implementation

The broader regression run found the pre-existing navigation failure
`tests/test_packaging.py::test_context_navigation_has_no_broken_links`:
`docs/README.md` still links to `../README.md#key-concepts`, but that heading
no longer exists. No matching repair ticket was found. Neither file is changed
by this implementation. A separate, archive-excluding export of baseline
`36c85653c2ce522882d73e7d9226ff42dc98d1f5` reproduced the exact failure:

```sh
cd /tmp/coga-coalesce-baseline-36c85653c2ce
PYTHONPATH=/tmp/coga-coalesce-baseline-36c85653c2ce/src /home/n/Code/coga/.venv/bin/python -m pytest -q tests/test_packaging.py::test_context_navigation_has_no_broken_links
```

Result: **1 failed in 0.63s**, solely the missing README anchor. The initial
broad branch run had **583 passed, 2 failed**: the second failure was this
change's missing new-topic manifest entry and has been corrected in
`tests/test_packaging.py::REQUIRED_BOOTSTRAP_CONTEXT_REFS`. The full suite is
running without exclusions. Per `code/implement`, unrelated failures are
reported for owner resolution rather than fixed or waived in this ticket.

Seeded validation passed, **4 valid tasks, no issues**:
`env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json`
from `tests/fixtures/seeded-repo/coga`. Tests run on Python **3.12.12**;
Python 3.11.15 is present but has no pytest installation, so no 3.11 receipt
is claimed.

## Evaluator review

2026-10-27: **Ready for owner review; no must-fix design findings.** Reviewed
the Description and Context as the implementer's specification, then checked
the current source, owning topics, fixtures, and frozen workflow. This is
readiness evidence, not owner approval of the bound or failure semantics.
Both decisions under `## Open Questions` remain for `review-design`.

### Evidence and scope

- The requirements compose correctly: Acceptance criteria, Proposed shape,
  Out of scope, and the counting contract are `###` subsections under
  Description. The frozen workflow matches the shipped
  `src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md`:
  this step hands to owner `review-design` before implementation.
- The three publication boundaries have concrete source support.
  `src/coga/launch.py::_LaunchInvocation._prepare_agent` currently publishes
  activation/start before `_prepare_step_checkout`, which can separately
  publish linkage and the launch audit. `src/coga/bump.py::advance_step`
  publishes the ticket and handoff immediately; `spawn_agent_session` captures
  usage and calls `sync_log` in its later `finally`. Grouping only the startup
  writes is coherent and does not require delaying the handoff. The explicit
  prospective-ticket carry across `_supervise_steps` addresses its disk reread.
- The exclusions match their actual publishers: megalaunch's
  `_launch_until_stop` and `_admit_launch_claim_after_release` straddle child
  release; `commands/ticket.py::_run_authoring_session` publishes the start
  before the interview and finalizes the authored set afterward;
  `launch_script.py::run_script_phase` separately records script start/exit;
  `recurring_runner.py::_run_delegated_task.start_period` retains its lease
  and launch-log boundaries. The proposal correctly makes no savings claim
  for a resumed ordinary reuse or a queue step.
- `src/coga/git.py::publish` supplies the required transaction, union merge,
  and refusal/uncertainty distinctions. Its `expect` applies only to selected
  paths, as the design notes. `cli.py::main` owns the outer sweep, so requiring
  that entry point in count tests is necessary. The changes stay within the
  shared launch/publication machinery permitted by `coga-dev/microkernel`.
- Re-inventoried `append_log` calls with AST inspection of `src/**/*.py`:
  **29 direct call sites**, matching the ticket's inventory. The classifier
  in `src/coga/recurring_activity.py` also matches the stated subject classes.
  Git history confirms prerequisite PR #1117 merged as `ac899dddc`.

### Optional implementation recommendations

1. Give control-only resumes an explicit concurrent-change regression.
   `src/coga/checkouts.py::confirm_ticket_checkout` and
   `enter_ticket_checkout` currently return immediately for non-switch plans;
   `_authoritative_ticket` checks status, step, workflow and checkout policy,
   but is not a complete routing comparison. The design already requires a
   stronger post-publication proof. Pin that requirement with an unchanged
   `in_progress` ticket whose remote lifecycle/routing changes during the
   log-only publication, including the retained-state exit and withheld sweep.
   Branch-switch coverage alone would miss this path.
2. Specify the notification's placement relative to the cleanliness proof in
   the implementation, and exercise delivery failure. The proposed successful
   start notification moves after confirmed publication, while
   `src/coga/notification/slack.py::SlackChannel.send.fail` appends a failure
   line. Posting between publication and `enter_ticket_checkout` could make
   control dirty and turn a non-fatal delivery failure into a launch refusal.
   Preserve the required non-fatal behavior and report/later-publisher rule
   without adding a commit to the normal successful-start fixture.

### Verification and handoff

On Python **3.12.12**, the following baseline command passed:

```sh
PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q \
  tests/test_recurring_activity.py \
  tests/test_checkouts.py::test_implementation_starts_on_a_published_branch_and_chains_through_review \
  tests/test_checkouts.py::test_resume_projects_newer_control_ticket_and_a_separate_bump_publishes \
  tests/test_checkouts.py::test_refused_preparation_records_no_launch \
  tests/test_checkouts.py::test_completed_reservation_receipts_never_resurrect_a_removed_branch \
  tests/test_launch.py::test_launch_uses_step_one_role_after_freezing_draft \
  tests/test_launch.py::test_launch_refusal_leaves_draft_unactivated \
  tests/test_launch.py::test_spawn_reports_unpublished_session_log \
  tests/test_launch.py::test_spawn_captures_supervisor_exception_as_failed_without_exit_fields \
  tests/test_launch.py::test_launch_teardown_refusal_preserves_work_result_and_stops_chaining \
  tests/test_megalaunch.py::test_pending_claim_blocks_remote_lifecycle_between_final_fetch_and_gate \
  tests/test_megalaunch.py::test_failed_post_release_admission_retains_released_recovery_witness
```

Result: **50 passed in 14.90s**. These exercise the current primitives and
failure contracts; they do not prove the unimplemented three-commit bound.
The design's disposable count probes were not rerun in this evaluation.
The full suite and new whole-command count tests remain implementation work.

`PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task commit-journal/coalesce-coga-state-commits --json`
reported **one valid ticket, no issues**; `git diff --check` passed. A byte
comparison against HEAD verified that only `## Evaluator review` was added:
frontmatter, ticket body, and all prior blackboard content were preserved.

Reconciliation fetched `origin` before review and again before this handoff:
clean `main` and `origin/main` both at
`5a5ffde9d6c953fa5218bbe96cb77790727aceb3`, with no intervening changes.
Only this evaluator section was authored; no ticket-body edit, implementation
branch, code change, or PR was produced. Next action is one bump to owner
`review-design`.

## Design investigation

2026-10-27: started on clean, fetched `main` at
`9665e4fb1771d8f13001910be3c525669c22c323`; no implementation branch or PR.
Read the publication, spool-merge, launch-claims, checkout, and reconciliation
contracts. Only the ticket is being edited in this design step.

An isolated real-Git probe used `tests/conftest.py::init_git_repo`, bare local
remotes, real `src/coga/cli.py::main` launch/sweep and a subprocess CLI bump,
a deterministic replacement for the PTY agent, and one fixed
`src/coga/usage.py::UsageRecord`. The next
step was owner-held, so every run stopped after one bump. Inspected the actual
remote commit diffs, including the handoff and usage, and verified return to
clean `main`. Nine successful cases measured:

| Entry status | Control step | Reused branch | Created branch |
| --- | ---: | ---: | ---: |
| `in_progress` | 3 | 3 | 4 |
| `active` | 4 | 4 | 5 |
| `draft` | 5 | 5 | 6 |

Draft probes used an already frozen workflow; implementation coverage must
also exercise activation from a workflow-name reference. Commit contents were
activation when needed, start when needed, linkage when created, launch log,
bump plus handoff, and usage log. Entry, return, and final sweeps added zero
commits in this clean workload. Temporary local evidence (not a dependency
for the next step): `/tmp/coga-coalesce-design-ofh0pteg/results.json` and its
per-case repositories/output. One discarded probe attempt failed because its
synthetic owner step lacked instructions; the successful runs supplied a
valid owner step.

The proposed reduction is one pre-spawn publication for ordinary managed
startup, one immediate handoff, and one usage publication. Deferring the
launch audit throughout the agent session cannot satisfy the existing clean
checkout contract. Megalaunch's pending claim and post-release admission
are distinct boundaries; this proposal must not collapse them.

Three additional real-Git probes exercised the actual megalaunch CLI with a
fixed selection and a deterministic PTY replacement that invoked the real
held-child admission callbacks under their release guard. Before simulated
release, remote control carried `pending:`; afterward it carried the admitted
generation plus audit. Active and unclaimed `in_progress` entries each made
4 commits; an explicitly selected draft made 5. Remote diffs showed the
separate activation (draft only), pending claim, admission, bump, and usage.
All finished clean on control; repeating `src/coga/git.py::sync_coga_state`
added no commit. Temporary evidence:
`/tmp/coga-coalesce-mega-iw7s3_yz/results.json`.

## Verification

Baseline regression command (Python 3.12, unchanged implementation):

```sh
PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_recurring_activity.py tests/test_launch.py::test_spawn_reports_unpublished_session_log tests/test_checkouts.py::test_resume_projects_newer_control_ticket_and_a_separate_bump_publishes tests/test_checkouts.py::test_refused_preparation_records_no_launch tests/test_megalaunch.py::test_pending_claim_blocks_remote_lifecycle_between_final_fetch_and_gate tests/test_megalaunch.py::test_failed_post_release_admission_retains_released_recovery_witness
```

Result: **42 passed in 6.28s**. The 12 disposable launch probes above are
additional design measurements, not tests of an implemented reduction.
`PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task commit-journal/coalesce-coga-state-commits --json`
reported one valid ticket and no issues; `git diff --check` passed. The full
suite and the new commit-bound assertions belong to implementation.

Pre-handoff reconciliation fetched and fast-forwarded to
`c52fe40c7` (two README-only commits since the investigation baseline).
The ticket and relevant source/contracts had no intervening changes. Saved
and verified the ticket plus patch and original HEAD under
`/tmp/coga-coalesce-design-reconcile-9665e4fb`, restored only this session's
ticket edit for the fast-forward, and reapplied its bytes unchanged. The
design measurements and regression results therefore still describe the
current implementation.

## Open Questions

For the independent evaluator, then the owner at `review-design`:

1. Approve the proposed three-commit ordinary bound and the explicit
   exclusions, particularly the retained four/five queue commits? This saves
   one to three commits on startup-heavy ordinary launches, but none on a
   resumed ordinary reuse or ordinary queue step. Recommendation: accept
   this bounded improvement without weakening startup, handoff, or admission
   deadlines; do not present it as a two-commit whole-launch promise.
2. Approve the changed ordinary startup failure contract? Activation/start
   and new linkage are prepared together and appear on control only in the
   final startup transaction; successful-start notification follows confirmed
   publication. Preparation failure can leave only a reserved branch/receipt;
   failure after writing the group retains the final local ticket/log, exits
   75 and starts no agent, including for a control-only step. Recommendation:
   accept this explicit publication gate, retaining evidence and recovery
   rather than continuing after an unconfirmed grouped start. If rejected,
   revise the bound and design before implementation.

## Handoff

The proposed spec and checklist are under `## Description`, with verified
source relationships, the log-writer inventory, and documentation targets
under `## Context`. Next is independent `evaluate-design`; owner approval
remains required before implementation. No production code or topic contract
has changed in this design step.

---

## Blockers

- [ ] [2026-10-27 19:05] [agent:claude] id=20261027T190525 Repair the pre-existing docs/README.md link to missing README.md#key-concepts on control, or explicitly approve proceeding with that baseline test failure. The full suite reports 4186 passed, 10 skipped, and only test_context_navigation_has_no_broken_links failed; the same failure reproduces on untouched baseline 36c85653c2ce. Implementation is pushed on coga/coalesce-state-commits at 4e5f4b03c, with complete receipts on the blackboard. code/implement requires escalation of unrelated failures before advancing to peer-review.
