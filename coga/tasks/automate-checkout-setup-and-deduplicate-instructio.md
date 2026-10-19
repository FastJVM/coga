---
title: Automate checkout setup and deduplicate instructions
status: in_progress
owner: nicktoper
contexts:
- coga/knowledge
- coga/extension-model
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
step: 4 (implement)
agent: claude
---

## Description

Move repeated checkout mechanics into shared code used by ticket launch and ad-hoc chat, and remove the duplicated Git recipes in the same change. Keep a complete explanation for humans and agents in the owning checkout documentation.

The current implementation already prepares current control and safely returns ordinary launches and direct chat to control. The remaining branch setup, record publication, and agent handoff instructions are repeated across the base prompt, checkout contexts, implementation/review skills, and code/docs workflows. Implement the missing automation and then shorten those instructions.

### Agreed direction

- Use the ticket's existing workflow and current step to select checkout behavior. Do not introduce another ticket field that merely repeats the current phase. For the shipped code/docs flows: design stays on control, implementation creates or reuses the recorded branch, code review/fixes use that branch, and PR publication operates from control. Distinguish design review from code/PR review, including owner assists; a generic step name alone does not establish semantics.
- Share the deterministic branch-preparation implementation between launch and a callable operation for an agent already inside coga chat. Reuse a recorded branch without resetting its unique work. For a new ticket branch, record and publish the linkage on control before switching. Keep workflow-specific selection separate from shared Git mechanics.
- Chat begins without a task or workflow and may remain discussion-only. When the human requests edits, the agent invokes the same preparation operation for an ad-hoc branch. Do not require creating a ticket or inventing a workflow transition. The existing launcher owns safe checkout return at session exit, not after each conversation turn.
- Preserve one complete, coherent explanation of the lifecycle in the owning checkout topic and its focused exception/recovery references. Humans and agents use the same documentation. Normal prompts describe the actual prepared branch and who handles return; chat has a short instruction to read the procedure and invoke preparation before editing.
- Leave implementation choices, selecting changes to commit, meaningful conflict resolution, tests, review, and handoff content to the agent. Automation checks preconditions and reports actionable failures while preserving unfinished work.

### Acceptance criteria

- [ ] Before an ordinary implementation agent starts, its branch exists and its `## Dev` linkage is confirmed on configured control. Resumes reuse the first recorded workflow branch without resetting commits; an interrupted allocation retries the same reservation instead of allocating another branch.
- [ ] The mapping below selects the right checkout for every shipped code/docs step, including design-review and PR-review owner assists, the `pr` spelling, and supported older frozen snapshots. Each chained agent uses freshly authoritative ticket state. There is no new phase/checkout field on tickets or workflow steps, no entry interpretation of `requires:`, and no generic step-name inference.
- [ ] Unrecognized workflows or locally changed instructions receive an explicit manual fallback. Existing instruction-resolution errors still refuse; missing inline definitions/sections retain their existing composition/validation treatment and never qualify as a recognized contract. Fallback does not hide an error or rewrite a frozen workflow.
- [ ] Ad-hoc chat stays on control during discussion and can prepare its one session-owned branch through the shared operation without a ticket. Repeated calls reuse it, including while it contains the session's dirty work. A different branch, stale session identity, conflicting reservation, or occupied checkout is refused without taking ownership.
- [ ] Preserve the existing clean-entry, publication, safe-return, recorded-assist, sandbox-clone, configured-remote/control, and Git-disabled/non-Git/remote-less contracts where applicable. Account explicitly for script phases, recurring/delegated launches, megalaunch, and prompt-report rather than broadening dispatch accidentally.
- [ ] Dirty or unpublished work, stale state, conflicting linkage, and unavailable Git access produce specific diagnostics with the failed stage and recovery location. Publication failure or interruption preserves reservations, refs, and unique work; no code commit, transition, automatic rebase, or destructive rollback is performed by preparation.
- [ ] After switching, the working ticket and composed ticket describe the same authoritative step and linkage. Only the current ticket may be projected unstaged from control, after checking for stranded or unpublished local intent; no branch ticket commit or wholesale replacement of Coga state is used. Before spawn, strictly record and verify this ticket's exact projected control blob as cross-process publication provenance, even on a resume with no ticket publication. A real handoff/bump can publish from that baseline; later competing ticket changes still refuse.
- [ ] A first sandbox Git-write refusal after successful host preparation preserves the prepared branch and all source/ticket edits. Recovery stops the agent's implementation work, uses permitted host access to verify an independent clone, return the primary to control and publish its linkage, then relaunches the same step. The primary may remain on the prepared branch until that recovery succeeds; no in-session host-control API, automatic dirt cleanup, or compensating transition is introduced.
- [ ] A runtime checkout notice reports the observed branch, relevant ticket path, preparation outcome and return owner. Managed prompts no longer require the agent to perform automated startup/return steps. Pure composition and unmanaged/manual sessions make no claim that preparation ran and link complete guidance.
- [ ] Already-satisfied work remains an agent judgment backed by evidence. An unused prepared branch does not force a code commit or PR, and preparation never closes a ticket or deletes that branch.
- [ ] Update the owning checkout, launch, workflow, composition, and extension topics as needed, plus applicable packaged twins. Remove obsolete procedural copies from the base prompt, dev/code overview, code skills, code/docs workflows, and orientation guidance in the same PR. Preserve required instructions in skilled and inline workflow steps.
- [ ] Add meaningful real-Git coverage for fresh/resumed work, step selection and chaining, chat discussion-to-edit, repeated calls, interruption, and dirty/publication failures. Update seeded launch fixtures where behavior changes. Run relevant Git/launch/compose/workflow/packaging tests, the required implementation checks, and coga validate --json.
- [ ] Compare representative prompts through the read-only compose API. Verify required guidance still arrives and repeated checkout recipes have disappeared; do not use a real launch or its sweeping prompt-report option just to measure.

### Proposed shape

The following interface and module names are proposals, not existing commands.
Implement the shared preparation and its launch integration before removing
instructions. The owner approved manual fallback for unrecognized behavior,
the narrow chat recipe, retention of an unused prepared branch, and explicit
host recovery/relaunch for a first sandbox refusal after switching. The
blackboard records these decisions and the evaluator dispositions.

#### 1. Select from the existing step contract

Put the lifecycle and this mapping in `dev/checkouts`; `coga/workflows` links
it and continues to own freezing and completion gates. Implement a small,
pure `select_checkout_policy` in a proposed `src/coga/checkout_policy.py`.
Its inputs are the authoritative frozen workflow/current step and the
resolved instruction identity. It returns control, create-or-reuse,
reuse-required, or manual, with a reason. Keep it separate from Git operations.

| Workflow | Current step | Entry policy |
| --- | --- | --- |
| `code/design-then-implement` | `design`, `evaluate-design`, `review-design` | control |
| All four shipped code/docs workflows | `implement` | create-or-reuse recorded branch |
| `code/with-review`, `docs/with-review` | `peer-review` | reuse recorded branch |
| `code/with-self-review` | `self-qa` | reuse recorded branch |
| `code/design-then-implement`, `code/with-review`, `docs/with-review` | `open-pr` | control |
| `code/with-self-review` | `pr` | control |
| All four shipped code/docs workflows | owner-held `review` assist | reuse recorded branch |

This is a closed compatibility table, not a name heuristic. A row requires
the qualified workflow name and the expected current step instruction shape:
`code/design`, `code/review-design`, `code/implement`, `code/self-qa`,
`code/open-pr`, or `code/address-pr-comments` as applicable; shipped peer
review, docs implementation/publication, and design approval are inline.
An unrelated workflow's `review` or `implement` means nothing to this table.
Ticket-wide skills do not select entry behavior. Existing routing still
decides whether a step can launch, including explicit owner assists.

Use the frozen current step, not its ordinal in today's workflow definition.
Support old snapshots without `evaluate-design` and without `requires:`;
neither changes the meaning of the remaining steps. Explicitly recognize
the older empty-`skills` PR `review` entries through their shipped live
inline instruction contract. Do not infer those semantics for an arbitrary
skill-less `review` elsewhere, or re-freeze old tickets.

For a matched row, verify the instructions the step actually consumes:
resolved step-skill bytes, or the applicable live inline section, must match
the shipped contract. Byte-identical local twins qualify; unrelated changes
to another workflow section need not disable this step. A changed applicable
section, changed skill body, additional/replaced step skills, or unknown
workflow selects manual with its reason. Local-first resolution and its
existing unreadable/malformed-file failures remain intact. This deliberately
trades automatic handling of benign local prose edits for no semantic guessing.

For manual policy, ordinary launch still prepares/returns control as today;
the notice says branch setup was not performed and points to the complete
procedure before edits. The implementation does not add an override registry
or infer a policy from gates, prose keywords, or roles alone.

#### 2. One shared preparation implementation

Add a focused `src/coga/checkouts.py` with typed preparation inputs/results
and entry points such as `prepare_ticket_checkout` and
`prepare_chat_checkout`. Both call the same branch-preparation implementation
for preconditions, reservation, branch creation/reuse, switching and final
verification. Reuse `src/coga/git.py`'s `publish`, `state_lock` and
`prepare_control_checkout` rather than copying shell recipes. A result records what actually
happened: checkout root, control revision, branch, ticket projection when
present, return responsibility, and any manual/exempt reason.

The two actual consumers are ordinary launch and the callable chat recipe
below. Shared mechanics therefore belong in core under `coga/extension-model`.
The recipe is a proposed reviewed addition to `src/coga/runner.py`'s fixed
`RECIPES` table: it needs a repository-independent argv/output/exit contract
and must agree with launch's private live-session witness and preparation
receipt. Document that placement in `coga/extension-model`. Do not add a Typer
command head, alias, ticket plugin, or general preflight/phase registry.

#### 3. Ticket branch transaction and recovery

Operate only after current-control admission and the existing refusing agent
preflights. Under the existing local state lock, recheck the canonical task,
expected lifecycle/step, Git destination, branch ownership evidence and
checkout before each mutation. Do not hold the lock across an agent session.

1. Read the authoritative `## Dev` on control. The first branch is the
   workflow branch; auxiliary branches remain untouched. Reject invalid or
   control-named branches and conflicting records. A recorded external
   checkout follows the exception below instead of creating a local substitute.
2. With no branch on an implementation step, reserve one generated valid name
   once, for example `coga/<task-ref>-<short-id>`. Store the task/root identity,
   chosen name and pinned creation OID atomically in the existing ignored
   `.coga/` area before creating the ref. This small local receipt is retry
   evidence, not task state or a workflow phase. Never adopt a pre-existing
   colliding ref or choose another name silently on retry.
3. Create the reserved branch at that OID without switching off control.
   Write only its `branch:` linkage into the current ticket's blackboard,
   preserving frontmatter, other `## Dev` entries and prose. Publish with an
   exact expected-ticket guard and strict failure propagation. Confirm the
   recorded linkage on fetched control and require a clean control checkout
   before switching. A best-effort sweep's zero process exit is insufficient.
4. On resume, use the recorded branch. If only its remote ref exists, fetch
   that exact branch and create the local ref at the fetched OID. A merely
   behind local branch may fast-forward to the pinned remote tip. Preserve
   local ahead/divergent commits and report that agent reconciliation is
   needed; never reset or automatically rebase them onto control. A recorded
   branch absent locally and remotely is a refusal, not permission to recreate
   an empty replacement. Check other-worktree occupancy and ignored-file
   collisions before switching.
5. Verify the selected branch has no unique committed ticket intent that
   would be hidden by a control projection. A ticket still at its shared base,
   or a version proved already incorporated on control, may be replaced in
   the working tree. Stranded ticket changes require reconciliation first.
   Switch normally, then atomically materialize only this ticket from the
   final authoritative control snapshot, unstaged. This also covers a branch
   predating the ticket's creation. Leave the index and branch commits alone.
6. Establish and verify the projected ticket's publication baseline as below,
   then verify HEAD and all expected bytes before admitting the agent. The only
   permitted entry dirt is the identified ticket projection or already-proved
   publication state; say which paths these are in the runtime notice. Do not
   present such a checkout as wholly clean. Return the same ticket object and
   path used for composition and task/expected-step metadata.

**Projection provenance is part of admission.** Under the same short state
lock, extend the existing per-worktree `git.PUBLISHED_REF` tree to remember
this ticket's exact blob from the final verified control revision. Its
meaning now includes a control blob that preparation verified and projected,
not only blobs this checkout pushed. Update only the current ticket's entry,
preserve every other entry, and verify the stored OID before spawn. The
preconditions bind the checkout/root, configured destination, ticket path,
selected branch, control revision and projected bytes; a receipt or a merely
read control snapshot alone cannot establish this baseline. No commit to the
feature branch, push, transition, or refresh of unrelated paths is involved.

Give this admission write a strict error path in the shared Git infrastructure:
`_record_published` currently catches failures, which is insufficient here.
A failed or unverifiable baseline write refuses spawn, preserves the ref,
receipt and projected file, and withholds teardown publication. An interrupted
projection retries only after proving its recorded snapshot and actual bytes;
it must not overwrite new notes or bless them as a fetched baseline. Already
equal publication and a log-only launch audit are not substitutes for this
explicit write. Keep ordinary publication callers' existing error behavior
unless a separately justified contract change is necessary.

The durable, per-worktree entry lets a later `bump` process use ordinary
`_provenance` without an inherited environment variable or an `expect` bypass.
It records the verified snapshot, never a later fetched ticket over edited
working bytes. Subsequent competing changes still fail the existing
compare-and-swap, including a refetch after a rejected push. The provenance
set and its new source belong in `coga/internals/git-regressions`; the strict
recording behavior belongs in `coga/internals/state-publication/publish`.

The receipt must make interruption boundaries testable: reserved but not
created; created but not linked; linkage written but not published; published
but not switched; switched but projection incomplete; projected but provenance
not yet verified. Retry derives progress
from observed refs, exact ticket bytes and the receipt, not a success bit
alone. An unlinked reserved branch is reusable only with matching reservation
and creation evidence; unexpected commits or changed linkage are a refusal.
A completed reservation never overrides a later authoritative `branch:`.
Keep ambiguous receipts for diagnosis; receipt cleanup never deletes a branch.

On publication refusal/failure, stay on control if still there, retain the
branch and ticket edit, identify what did and did not land, and withhold the
outer sweep. If a later stage already switched, report that actual position
and preserve it. Do not let teardown blindly retry a refused transaction or
roll it back. A subsequent invocation recovers against fresh control; it does
not replay activation, a step transition or a launch audit as a recovery trick.

An idempotent call on this operation's already prepared branch is a validation
and no-op, even with that session's dirty work. It must not sweep those edits,
switch through control, or refresh over notes. A different HEAD, changed task
identity or conflicting receipt fails explicitly.

#### 4. Fit the existing launch order

Keep `src/coga/launch.py`'s `_CheckoutBoundary.enter` as the current-control
admission boundary.
Keep scripts on their existing entry path: `ticket.py` runs before any new
agent-branch preparation, and each deterministic phase settles before the
next dispatch decision. Do not select a feature branch for a script merely
because its current step also has an implementation skill.

For each ordinary agent phase, including every chained phase, perform:
fresh control/config/task read; routing and complete non-mutating agent
preflights; existing authorized activation/start publication; policy and
branch/link preparation; final authoritative composition; switch/projection;
observed checkout notice; spawn. Split preparation's plan/publication from
its switch where needed to preserve that order. Move or reuse the ordinary
launch-audit publication so it completes on control before the final snapshot
and switch, exactly once. A publication that advances control requires
re-reading and revalidating the task before spawn. If its step, linkage,
destination or required instructions changed, re-plan from control with a
bounded retry or refuse; do not spawn the stale prepared step.

Use `src/coga/launch.py`'s existing
`spawn_agent_session(composed_prompt=...)` seam for the authoritative
composition. Do not switch and then accidentally recompute
routing, secrets or instructions from the feature branch's older files.
Preserve the existing refusal-before-lifecycle-write guarantees for agent
preflights. A failure after an existing lifecycle write reports the saved
state and does not fabricate an agent completion or a compensating transition.

The agent writes its handoff into the projected live ticket, never commits
that projection, and bumps last. It need not run an unconditional Git restore
that could erase notes. Before handoff, the existing reconciliation rule still
applies to control changes made during the session; a stale publication needs
preserving/reconciling prose, never another bump. The existing boundary returns
after the session, reloads control and only then considers chaining.

#### 5. Callable preparation inside chat

Proposed spelling: `coga run prepare-checkout --session <id>`. The runtime
notice supplies this exact invocation, so it also works when an agent's shell
does not inherit launch environment variables. The recipe consumes no task
ref or workflow, emits no transition/done signal, and does not launch an agent.

Extend the existing direct-orientation occupancy guard with a checkout-local
receipt identifying its live supervisor/session and one reserved generated
branch, for example `coga/chat-<id>`. Reserving a name does not create a Git
branch; discussion-only chats allocate no branch and publish no ticket linkage.
The recipe must prove the session matches the current root and the still-live
guard. A stale file or user-supplied identifier alone is not evidence of a live
session. Keep this a companion to the existing guard, not another lock service.
Install/invalidate its identity and inspect it under the same short state
lock, so a newly admitted guard cannot expose a previous session's receipt.

On the first edit request, preparation proves control entry and creates and
switches to the reserved branch using the shared mechanics. On repeated calls,
the exact active session/branch association permits a no-op with dirty work;
do not publish that work as a side effect. Partial preparation retries the
same reservation. If HEAD moved elsewhere, a receipt conflicts, or the
supervisor died, fail without adopting another branch. A new chat does not
silently resume an old chat branch: its work is recovered explicitly under
`dev/checkouts/launch-boundary`. There is no `--force` or arbitrary adopt option.

Return a concise branch/root/outcome report on stdout; return 0 only for a
verified prepare/reuse or an explicitly reported Git exemption, 2 for invalid
invocation, and 75 for stale, occupied or incomplete preparation. Report the
stage and retained paths on stderr. Exclude this recipe from the CLI's general
exit sweep on success, failure and pre-dispatch config refusal, following
`src/coga/cli.py`'s `_should_sweep_coga_state` exception for `publish-state`:
repeated calls must not publish unfinished contexts or skills. Its own
required publication remains guarded; a successful no-op emits no misleading
failed-publication warning.
Retain the runner's normal failure-report contract without inventing a chat
blackboard. The direct-chat guard remains held until the launcher's existing
return and final sweep; conversation turns do not return the checkout.

#### 6. Exemptions and unusual outcomes

- **Recorded assist already in its checkout:** preserve the current exemption,
  PR-head verification, alignment and assist-attribution rules. Do not layer
  ordinary branch preparation over it or grant its special identity to a
  normal owner assist merely because that assist now starts on the PR branch.
- **Recorded sandbox clone from the primary checkout:** keep the primary on
  control with the authoritative ticket; verify/name the recorded code checkout
  and branch, and direct the agent there. Never `chdir`, silently follow a stale
  path, allocate a competing branch or create a worktree. Preserve the documented
  independent-clone fallback and local-config seeding for restricted agent Git
  access. A missing or conflicting recorded clone needs recovery, not replacement.
- **First sandbox refusal after automatic switching:** use explicit host
  recovery and relaunch, as approved at design review. Stop implementation
  writes and explain the failed Git operation and retained paths. Record the
  prepared branch/OID and preserve verified copies of all staged, unstaged,
  untracked and ticket work before any cleanup. A permitted independent clone
  may be created for preservation, but do not continue implementation in it
  until the host has completed the sequence below. Do not bypass the sandbox,
  allocate another feature branch, bump, or signal successful step completion.

  Ask the attending human to finish the recovery from a permitted host shell
  after ending the agent session; unattended sessions escalate the unavailable
  capability through their existing conduct. The launcher attempts its normal
  safe return on exit. It can return a clean or already-published primary;
  source dirt or failed publication still refuses and remains intact. The
  primary may stay on the prepared feature branch until host recovery succeeds.
  Do not claim the recorded-clone entry guarantee held during this first
  failed session, and do not add automatic same-step relaunch or host RPC.

  On the host, follow reconciliation: create or verify an independent clone
  using the already-prepared branch at its actual tip, preserve its unique
  commits and transfer the staged/unstaged/untracked source changes with
  byte/mode/deletion checks. Keep the ticket and audit authoritative in the
  primary; do not commit their projection or copy ignored credentials. Verify
  the retained backups and clone before clearing any replicated primary dirt,
  and clear only those proved copies under the explicit recovery authorization.
  Publish/reconcile saved primary ticket state without replaying any lifecycle
  command, then use the existing safe return to reach clean current control.
  Only after that succeeds, verify the clone's remote, branch and retained work,
  seed its local config through the existing helper, and write/publish its
  `worktree:` beside the unchanged `branch:` under the exact-ticket guard.
  Confirm the linkage on control before the human relaunches the same step.
  The ordinary recorded-clone path then keeps the primary on control.

  Any interrupted or refused stage retains its backups, clone, branch and
  notes, names what remains unpublished and stops; a candidate clone is not
  active linkage until the host verifies and publishes it. This exception
  replaces the obsolete instruction to continue immediately after agent-side
  branch creation fails. Its procedure and primary-HEAD guarantee belong in
  `dev/checkouts/sandbox-clone`, linked from the other checkout guidance.
- **Git disabled, non-Git or remote-less:** preserve current exemptions and
  state-publication behavior; report that branch preparation/freshness was not
  provided. Do not create branches merely because the policy says implement.
  Without a direct-chat guard, issue no preparation capability or invocation;
  manual guidance applies. A guarded remote-less chat can report an exemption.
  Loss of a remote after an admitted managed session is a failure, not a newly
  available exemption. Use configured remote/control names throughout.
- **Recurring/delegated launches and megalaunch:** retain their current admission,
  claim, dispatch and return paths. No automatic step-branch setup in this change;
  report the manual/exempt behavior and keep the complete procedure reachable.
  Do not put automatic preparation in the shared spawn function where it would
  bypass these callers' transaction boundaries. Other bootstrap targets remain
  exempt; delegated orientation receives no direct-chat preparation capability.
- **Prompt reports:** no new preparation, branch reservation, session receipt or
  checkout claims. Preserve the existing report's documented sweep behavior;
  measurement uses only the read-only compose API.
- **Already satisfied:** a fresh implementation can discover no work only after
  its empty branch has been prepared. Permit evidence-backed closure without a
  fabricated commit or PR; preserve the branch for existing cleanup policy. For
  self-QA with no branch but prior `## Already satisfied` evidence, stay on control
  for agent verification and say why. Missing branches without that evidence
  still fail; the text is permission to verify, never proof for automatic closure.
- **Exceptional fixes during docs publication:** keep publication on control.
  Preserve the docs step's mergeability, conflict-resolution, re-verification and
  refreshed-PR-evidence obligations, but move its conditional checkout/return
  recipe to the owning checkout procedure. Ordinary code publication retains
  its existing mechanical-only remit. Do not silently delete a judgment obligation
  while removing duplicated Git instructions.

#### 7. Runtime guidance and documentation cleanup

Add an optional typed checkout result to `src/coga/compose.py`'s
`compose_prompt_report` and `compose_prompt`, rendered as a short runtime appendix after the contiguous
ticket layers and before launch arguments/the launch marker. It names observed
state, any ticket projection, and who returns the checkout; an eligible direct
chat also gets its exact preparation invocation. Composition performs no Git operations. With no
result, it states that preparation was not supplied and points to `dev/checkouts`;
it must never infer a prepared branch from a workflow or ambient environment.
Cover repo resource overrides so the runtime truth is independent of an old
base-prompt override; do not overwrite repo-owned prose.

Keep the complete start/work/handoff/end explanation in `dev/checkouts`, with
its existing recovery, reconciliation and sandbox leaves owning their focused
rules. Update `coga/launch`, `coga/workflows`, `coga/prompt-composition` and
`coga/extension-model` for their portions of the contract,
`coga/internals/state-publication/sweep` for the recipe's exit-sweep exclusion,
`coga/internals/git-regressions` and `coga/internals/state-publication/publish`
for verified projection provenance, and `dev/checkouts/sandbox-clone` for the
first-refusal host recovery and its different primary-HEAD guarantee.
Neighbouring overviews
link rather than restate the mapping or algorithm. Review topic size while
editing instead of duplicating a short agent version beside the human version.

Remove obsolete branch-allocation, pre-branch Python sweep, unconditional
ticket-restore, start-on-main and conditional-return recipes from
`src/coga/resources/prompt.md`, `dev/code`, the code implementation/self-QA/
publication/PR-assist skills, all code/docs workflows, and orientation guidance.
Keep a short fallback pointer in the shared base/step guidance so older snapshots,
manual/API sessions and exempt callers remain operable. Keep publication safety,
selective staging, meaningful reconciliation, test/review requirements, evidence
and owner gates. PR-assist head/repository/lease verification is not redundant
with branch selection and must remain. Audit both the skilled and inline prompt
paths, including inline legacy owner review. Refresh every applicable packaged
twin in the same implementation PR.

### Verification plan

Extend the existing real-Git fixtures and launch-return tests. Cover creation
and confirmed linkage before spawn; resume with unique commits; remote-only
and missing recorded branches; configured remote/control; clean versus dirty
entry; stale publication races; ignored collisions; competing branch holders;
and interruption at each reservation/publication/switch/projection/provenance
boundary.
Check working ticket bytes, branch OIDs and remote control contents, not just
return codes. Exercise a final spawn through the real composition/audit path,
not only a stub that replaces all of `spawn_agent_session`.

Add a real-Git resume whose recorded branch predates another checkout's
ticket edit, with `status: in_progress`, no activation/linkage write and no
matching ticket entry in `PUBLISHED_REF`. Launch it through the real audit and
composition path, add handoff notes, run a real bump from another process and
return; assert the handoff and exactly one advance reached control. In a
second case, change that ticket from a competing checkout after preparation
and prove the local handoff/advance is retained while publication refuses and
the competing bytes stay intact. Cover baseline-write failure, interrupted
projection, unrelated provenance entries, and a retry that must not overwrite
new notes or silently advance their baseline.

Cover a first sandbox refusal with no initial `worktree:`, after successful
host branch preparation, both before source edits and with new staged,
unstaged, deleted and untracked files. Assert the host return refuses source
dirt without losing it; exercise the documented host recovery with a clone
and verified copies, linkage publication after clean control return, and a
relaunch of the unchanged step using that clone. A failed copy, conflicting
clone, denied host access or failed linkage publication must preserve all work
and prevent continuation. Also exercise an agent-driven rebase with the entry
ticket projection and new blackboard notes: preserve/reconcile them separately,
restore them unstaged, and prove the implementation commit contains no ticket.

Parameterize the mapping across every table row, current/older frozen forms,
owner assists, missing gates, local identical twins, applicable local edits,
custom names and contradictory skill lists. Chain implementation to review to
publication with control advancing between sessions; assert each agent sees
the correct branch, prompt, expected step and latest blackboard. Add script
handoff and exemption regressions without replacing existing admission proofs.

Exercise direct chat discussion-only, first preparation, repeated dirty calls,
partial retries, stale/mismatched session identifiers, second-chat refusal,
supervisor interruption, safe return and refused return. Invoke the recipe
through the CLI in at least one test so its sweep behavior is covered.

Before/after read-only composition samples must cover code implementation,
peer review, self-QA, both owner review kinds, code/docs publication, docs inline
implementation, an old frozen snapshot, manual/exempt mode and chat. Inspect
required guidance and removal of actual duplicate recipes, not only token
counts. Never measure by launching or editing live workflow/frontmatter state.

Run targeted Git, launch/script, compose, workflow/validation, runner, environment
isolation and packaging/resource tests; then the full suite required by
`code/implement`, `coga validate --json`, and relevant seeded-fixture validation.
Use an absolute checkout `PYTHONPATH` and an interpreter with the test extras;
record exact commands, counts and any Python-floor gap per `coga/testing`.

### Out of scope

Worktree isolation, branch deletion policy, automatic implementation commits
or pushes, automatic rebases/conflict resolution, changing owner gates,
automatic custom-workflow migration, cross-session chat-branch adoption,
in-session host-control RPC or automatic sandbox dirt migration, a general
lifecycle/publication redesign, and a new execution/plugin framework.
This change does not teach launch to decide that a PR merged or work is done.
Deliver automation, documentation and instruction removal together.

## Context

The attached knowledge and extension-model topics govern where the explanation
and the shared implementation belong. The behavior topics below are cited
rather than attached; read the named sections before designing or changing
their behavior, and update their owners and packaged twins with implementation.

- `dev/checkouts` (`docs/contexts/dev/checkouts/SKILL.md`): read "Start, work,
  end", "Publish pre-branch ticket edits", and "Which checkout you invoke
  Coga from". `src/coga/git.py` plus `sync_coga_state` publishes Coga state;
  branch switching alone does not publish the ticket linkage. Its
  `prepare_control_checkout` provides the existing safe control preparation.
- `dev/checkouts/launch-boundary`
  (`docs/contexts/dev/checkouts/launch-boundary/SKILL.md`): read "Preparation
  and return" and "Checkout recovery", including exemptions.
  `src/coga/launch.py` plus `_CheckoutBoundary.enter` and `.settle` already
  wrap ordinary launches and direct orientation in state publication and
  control preparation; `_checkout_exemption` preserves recorded checkouts.
- `coga/launch` (`docs/contexts/coga/launch/SKILL.md`): read "Checkout boundary"
  and "Phases and routing". `src/coga/launch.py` plus `_LaunchInvocation`
  coordinates dispatch, and `_supervise_steps` rereads the ticket for each
  step. Branch preparation must fit that order without composing from stale
  feature-branch ticket state or interfering with script phases.
- `coga/workflows` (`docs/contexts/coga/workflows/SKILL.md`): read step format,
  freezing, and "Step completion gates". `src/coga/ticket.py` plus
  `Ticket.current_step` resolves the existing frozen step; `src/coga/workflow.py`
  plus `Workflow.load` reads workflow definitions. Completion gates do not
  currently describe entry behavior. Define the checkout mapping without
  assuming arbitrary custom step names have shipped-workflow semantics.
- `coga/prompt-composition`
  (`docs/contexts/coga/prompt-composition/SKILL.md`): read "Layer order" and
  "What each layer reads". `src/coga/compose.py` plus
  `compose_prompt_report` measures a prompt without a launch; `_step_layers`
  selects either step skills or the live inline step body. A skill-backed
  step does not receive its workflow's inline prose. Links do not load topics.
- `coga/testing` and `coga/packaging`
  (`docs/contexts/coga/testing/SKILL.md` and
  `docs/contexts/coga/packaging/SKILL.md`): read the verification and twin
  requirements before implementation. `src/coga/paths.py` plus
  `resolve_context_path` and `resolve_skill_path` select local or packaged
  resources, rather than composing both copies.

The audit found repeated entry/return instructions in `dev/code`,
`dev/checkouts`, `coga/skills/code/{implement,self-qa,open-pr,address-pr-comments}/SKILL.md`,
and packaged `bootstrap/workflows/{code,docs}/` definitions. The implementation
skill also repeats them within its introduction, procedure, and acceptance
checklist. Its resumed-branch guidance has no equivalent in the copied docs
implementation startup procedure. Use these as starting points for the
cross-surface audit, not a closed list.

Direct chat is `bootstrap/orient`; its packaged `ticket.md` deliberately has
no task lifecycle. The base prompt is `src/coga/resources/prompt.md`.
Tests already covering return include `tests/test_launch.py` plus
`test_launch_returns_a_feature_branch_handoff_before_the_next_step` and
`test_launch_returns_the_checkout_after_a_failed_session`; extend the
existing real-Git test approach rather than mocking away checkout behavior.

### Verified integration points

- `src/coga/launch.py`: `_prepare_agent` performs full composition, secrets
  and push-auth preflights before committing deferred activation and starting
  the session; `_supervise_steps` then rereads each step and calls
  `spawn_agent_session`. That function normally composes again and publishes
  the launch audit after composition. Its `composed_prompt` argument can retain
  the control-derived prompt, but the new preparation must also account for
  that later audit write. `_CheckoutBoundary.settle` reloads configuration,
  publishes state, prepares control and stops chaining on refusal.
- `src/coga/launch.py`: `_orientation_checkout_guard` holds the nonblocking
  Git-toplevel lock; `checkout_guard_scope` extends its lifetime through the
  CLI sweep. It currently has no per-chat branch/session receipt. Add the
  callable operation here through shared mechanics, not a second launcher.
- `src/coga/git.py`: `sync_coga_state` catches publication failures;
  `sync_task_state(strict=True, expect=...)` propagates them after reporting;
  `publish` supports guarded publication and `require_paths`. A false return
  can mean there was nothing new to publish, so success needs content proof.
  `prepare_control_checkout` only prepares control and performs no publication.
  `stale_coga_task_rels` is a fail-open lifecycle warning, not a sufficient
  proof that overwriting a ticket would preserve all prose.
- `coga/internals/git-regressions`
  (`docs/contexts/coga/internals/git-regressions/SKILL.md`) and
  `coga/internals/state-publication/publish`
  (`docs/contexts/coga/internals/state-publication/publish/SKILL.md`) are cited
  rather than attached: read "The provenance check", "`publish` and its
  wrappers", and "Best-effort versus strict". `src/coga/git.py` plus
  `_provenance` reads HEAD, merge base and `PUBLISHED_REF`; `_record_published`
  writes the latter but currently swallows write failures. `_publish_locked`
  returns from an already-equal tree without recording its blobs, and
  `src/coga/bump.py` plus `advance_step` publishes without an `expect` override.
  Preparation must establish the strict per-ticket baseline described above.
- `dev/checkouts/sandbox-clone`
  (`docs/contexts/dev/checkouts/sandbox-clone/SKILL.md`) is cited rather than
  attached: read "Sandbox clone fallback" and "What a fresh checkout lacks".
  `src/coga/launch.py` plus `_CheckoutBoundary.settle` returns after an agent
  exits but refuses uncommitted source changes; `_supervise_steps` stops on an
  unchanged step. The new first-refusal recovery uses those boundaries and
  explicit host action, not a transition or the chat-only preparation recipe.
- `src/coga/blackboard.py`: `update_blackboard_under_barrier` combines
  `git.state_lock` with expected-byte checks and delegates to
  `src/coga/taskfile.py`'s `replace_blackboard`, preserving text outside the
  fence. Use this path for linkage rather than round-tripping all frontmatter.
- `src/coga/autoclose.py`: `parse_branch_names`, `parse_branch_name`,
  `parse_worktree_path` and `parse_pr_url` interpret the real `## Dev` section
  and ignore fenced examples. `src/coga/open_pr.py`'s `_stranded_ticket_detail`
  and publication preflights are relevant preservation checks; do not replace
  them with branch-name guesses or a lifecycle-rank comparison.
- `src/coga/compose.py`: `_step_layers` uses frozen skill refs when present,
  otherwise loads `Workflow.inline_instructions` from the live definition.
  Thus a legacy empty-skills review still consumes inline prose even when new
  tickets freeze an assist skill. `src/coga/paths.py`'s
  `resolve_workflow_path` and `resolve_skill_path` decide local precedence.
- `src/coga/task_env.py`: `apply_task_env` rebuilds metadata from the supplied
  ticket/ref; `src/coga/repl_supervisor.py`'s `build_supervised_step_env`
  separately pins expected task/step and strips inherited return authority.
  Keep both consistent with the final authoritative ticket. The proposed chat
  recipe takes its session identifier explicitly and need not add a task field
  or depend on inherited shell variables.
- `src/coga/runner.py`: `run_recipe` selects only `RECIPES` and `_record_failure`
  records failures when there is a valid task blackboard. `src/coga/cli.py`'s
  `_should_sweep_coga_state` already excludes `run publish-state` even before
  dispatch; extend that narrow exclusion for the new recipe. Its
  `_sweep_coga_state` also honors `git.state_sweep_withheld`, used by failed
  launch boundaries. These keep a guarded result from an unrelated publication.
- `coga/internals/state-publication/sweep`
  (`docs/contexts/coga/internals/state-publication/sweep/SKILL.md`) is cited
  rather than attached: read "The end-of-command sweep" and "Strict publication
  on demand" for the exclusion and failure-recovery contract. Its code owners
  are `src/coga/cli.py`'s `_should_sweep_coga_state` and
  `src/coga/publish_state.py`'s `run_publish_state_recipe`.
- `tests/test_launch.py`: `_CheckoutSession` and `_checkout_launch_env`
  replace the entire spawn function. They exercise real Git return well but
  cannot alone prove final prompt/audit ordering; retain real spawn preparation
  in an additional integration test while replacing only the agent process.

The live-ticket survey found older design snapshots without the evaluator,
implementation steps without a branch gate, publication steps without a PR
gate, and owner PR-review steps with empty skills. These are compatibility
fixtures to encode explicitly, not reasons to modify live ticket frontmatter.

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
implementation and evidence, never placeholders; coga/internals/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

## Design handoff

Design investigated against `f973db63c` on control. The spec now lives under
`## Description`, with verified source relationships under `## Context`.
Only this ticket was edited; implementation and changes to behavior topics,
templates or tests have not started.

The owner originally approved shared automation, existing workflow/current-step
selection, complete owning documentation and in-session ad-hoc edits. During
this design session the owner explicitly approved manual fallback for custom
workflows or locally changed step instructions. The proposed closed mapping
therefore verifies the consumed instruction contract and supports the observed
older frozen forms without changing their metadata or completion gates.

The key integration risks are the launch audit after composition, the stale
ticket on a resumed branch, and repeated chat preparation accidentally running
the CLI's general state sweep. The spec addresses these together: publish on
control before the final snapshot, project only the authoritative ticket
unstaged, and make repeated preparation a non-publishing no-op.

## Open Questions

No unresolved product choices. The owner approved both original questions and
the first-time sandbox recovery choice during review; see Owner design review
below. The owner also approved the revised spec and explicitly authorized
advancing to implementation on 2026-10-19.

## Verification

Read-only `compose.compose_prompt_report` sampling covered twelve shipped
code/docs step cases plus orientation, with in-memory workflow/ticket copies.
It confirmed repeated checkout instructions in both skill-backed and inline
paths (the implementation sample alone includes three `git switch` mentions).
No real launch, prompt-report launch or trial frontmatter mutation was used.
The live-ticket metadata survey confirmed the compatibility variants above.

- `PYTHONPATH=/home/n/Code/codex/coga/src /home/n/.local/share/uv/tools/coga/bin/python -m coga.cli validate --task automate-checkout-setup-and-deduplicate-instructio --json`
  returned exit 0, 1 task OK, no issues, including after reconciliation.
- With the same source/interpreter prefix, `python -m coga.cli validate --json`
  returned exit 1: 126 OK, 2 errors and 47 warnings. Both errors are missing
  `marketing/plan` and `marketing/positioning` contexts on
  `marketing/demo-hackability-ask-claude-to-add-a-command-live`. Its ticket is
  byte-identical to committed control, where neither context exists in the
  canonical or packaged tree. These are real unresolved repository errors,
  independent of this design-only edit; no other ticket was changed.
- `git diff --check` passed. Read-only compose assertions confirmed unchanged
  frontmatter and ticket guide, no uncomposed body sections, and all acceptance,
  proposed-shape, scope, integration and open-question sections present in the
  prompt. No implementation test run is claimed for this ticket-only step.
- Final reconciliation fetched and fast-forwarded to `c4cebeea4`, whose
  intervening changes retire other tasks; the source, governing instructions
  and this ticket's control copy were unchanged. The design was backed up,
  restored after fast-forward, and checked byte-for-byte. Only this ticket
  remains in the working diff. Ready for the independent design evaluator;
  owner decisions above remain pending.

## Evaluator review

Cold review on 2026-10-19 against `073af0f1a`, reconciled to `c80511fc1`;
intervening commits change only unrelated tickets and their audit. **Needs revision
before implementation** for the two findings below. This is evaluation, not
owner approval; the two existing Open Questions still belong to owner review.

The intent and requirements reach composition through `## Description` and
`## Context`. The four shipped workflow definitions, skilled versus inline
resolution, older empty-skills review handling, launch-audit ordering, and
exit-sweep exclusion seam match the source. The proposed shared mechanics
have two actual consumers and the recipe has a stated co-versioning reason.
Automation and removal of its replaced instructions form one coherent PR.

### Must fix before implementation

1. **[P1] Establish publication provenance for the projected ticket.**
   Proposed shape 3 materializes the current control ticket on a resumed
   branch, but does not establish the baseline subsequent ticket publication
   needs. `src/coga/git.py` `_provenance` recognizes only `HEAD`, the merge
   base, and `PUBLISHED_REF`; it does not remember a control snapshot merely
   because preparation read or copied it. `_publish_locked` also returns
   from an already-equal publication without recording those blobs.
   `src/coga/bump.py` `advance_step` publishes without an `expect` override.
   An `in_progress` resume with existing linkage need not publish this ticket
   during startup, and publishing its launch audit records only the log.

   This fails when another checkout updated the ticket after the feature
   branch point, even with no concurrent change during the new session.
   A disposable real-Git probe fetched/prepared control, published the launch
   log, switched to the old recorded branch, and copied the exact fetched
   ticket. Adding a handoff then calling `sync_task_state(strict=True)` raised
   `StateRegressionError: control copy changed since this checkout last saw
   it`; the handoff stayed local and did not reach control. Normal bump can
   therefore save an advance locally while refusing its publication.

   Specify how the verified projection establishes a narrowly scoped,
   cross-process publication baseline for this ticket, with later control
   changes still refusing. Include the state-publication owner/twin if that
   contract changes. Add a real-Git resume test with no matching published
   ticket baseline, no activation/linkage write, a real handoff/bump and
   return; also prove a subsequent competing ticket edit is not overwritten.
   Do not repair this by replaying a transition or committing the projection.

2. **[P2] Define first-time sandbox fallback after automatic switching.**
   Proposed shape 6 defines the already-recorded clone case, but preserving
   the existing fallback also requires the case where restricted Git access
   is discovered for the first time inside the agent. The host launch can
   prepare and switch successfully while the agent's sandbox cannot write
   the primary Git metadata. At that point the primary is already on the
   prepared feature branch, possibly with new source edits.

   `docs/contexts/dev/checkouts/sandbox-clone/SKILL.md`, "Sandbox clone
   fallback", and `coga/skills/code/implement/SKILL.md`, step 3, currently
   create the independent clone after agent-side branch creation fails and
   keep the primary on control. That startup sequence no longer applies;
   the agent cannot simply switch the protected primary back. The proposed
   chat-only recipe supplies no ticket-session handoff for this case.

   Decide the supported recovery sequence and primary-HEAD guarantee before
   removing those instructions: who returns the primary, when clone linkage
   is published, and how the reserved branch and any new edits survive.
   Update the sandbox owner/twin and add coverage starting without
   `worktree:`, with successful host preparation followed by an agent-side
   Git-write refusal. Handling only a pre-existing clone does not verify the
   promised fallback.

### Optional recommendations

- Exercise an agent-driven rebase with both an entry projection and new
  blackboard notes. The reconciliation topic already explains preserving
  dirty work, but the new normal entry is dirty while `code/implement` step
  8 and peer-review currently expect a clean branch for rebase. Verify the
  revised guidance preserves notes, leaves the ticket unstaged, and never
  includes it in an implementation commit.
- Correct the Context source map's `run_reported` reference: this tree has
  `src/coga/runner.py` `run_recipe` calling `_record_failure`; no
  `run_reported` symbol exists there. The intended failure contract is real.

### Verification and scope

The real-Git probe used `tests/conftest.py` `init_git_repo` and
`tests/test_git.py` `_seed_ticket` / `_ticket_text`, with a competing control
commit from a second clone. It verified both the retained working bytes and
the unchanged remote ticket. No production implementation was added.

The following baseline checks passed: **12 passed in 3.66s**, Python 3.12.12.
This is targeted design evidence, not an implementation or Python 3.11-floor
verification.

```sh
PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m pytest -q tests/test_git.py::test_expect_pins_the_exact_control_copy tests/test_git.py::test_a_feature_checkout_keeps_publishing_its_own_ticket tests/test_launch.py::test_launch_returns_a_feature_branch_handoff_before_the_next_step tests/test_launch.py::test_spawn_agent_session_uses_precomposed_prompt_without_rederiving_it tests/test_launch.py::test_orientation_guard_is_per_git_checkout_not_coga_root tests/test_launch.py::test_orientation_guard_is_released_when_its_process_dies tests/test_bootstrap_workflow_review_sections.py
```

`PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m coga.cli validate --task automate-checkout-setup-and-deduplicate-instructio --json`
returned exit 0, 1 task OK, no issues. `git diff --check` passed, and a
byte-prefix comparison against committed control confirmed that the entire
pre-existing ticket, including its blackboard, was preserved.
Final reconciliation backed up the review, fast-forwarded control, reapplied
the review and verified it byte-for-byte; relevant source, instructions and
this ticket's committed bytes were unchanged.

Only this Evaluator review was added. The ticket body, frontmatter, existing
blackboard sections, source, documentation, and tests were not edited; no
implementation branch or PR was created.

## Owner design review

Review on 2026-10-19, starting from clean control `3db2b4413`, current with the
fetched remote. This section supersedes the earlier pending product questions
and records revisions responding to the evaluator; implementation has not begun.

Owner decisions, explicitly confirmed in this attended session:

- Approve `coga run prepare-checkout --session <id>` and one generated branch
  per live chat, without force/adopt options. Custom naming and adoption of
  earlier chat work remain manual recovery.
- Allow an unused prepared branch when the agent proves the work already
  satisfied. No fabricated commit/PR; existing cleanup policy remains.
- Use explicit host recovery and relaunch for the first sandbox Git-write
  refusal after automatic switching. Preserve the prepared branch and all
  edits; the host verifies the clone, returns the primary to control and
  publishes linkage before the same step resumes. The accepted tradeoff is a
  relaunch instead of an in-session host-control interface.

Evaluator dispositions:

- **P1 accepted and specified.** Proposed shape 3 now requires a strict,
  verified, current-ticket-only update to existing per-worktree publication
  provenance before spawn. It survives a later bump process without granting
  permission to overwrite subsequent competing changes. The implementation
  must update the provenance and publication owners/twins and cover real
  resumed handoff/bump/return, stale writes and interrupted baseline recording.
- **P2 accepted and specified with the owner's recovery choice.** Proposed
  shape 6 now distinguishes first-time failure after switching from entry with
  an already-recorded clone. The primary can remain on the prepared branch
  until host recovery succeeds; no claim of a clean control checkout or
  completed step is made meanwhile. Source dirt is never automatically cleared.
  The sandbox owner/twin and first-refusal/relaunch coverage are required.
- **Both optional recommendations accepted.** The verification plan now covers
  a rebase with the projected ticket plus new notes, and the source map names
  `runner._record_failure` instead of the nonexistent `run_reported`.

Only the ticket body and blackboard changed. Lifecycle frontmatter and the
ticket guide remain intact. On 2026-10-19 the owner explicitly approved the
revised spec and the requested `coga bump` handoff to implementation.

Review verification (Python 3.12.12; no Python 3.11-floor run or implementation
verification claimed):

- A disposable real-Git probe used the existing test fixtures and
  `_record_published` to model the proposed per-ticket baseline. A separate
  process called the real `bump.advance_step`: the handoff and advance reached
  control, return was clean, the feature tip stayed unchanged, and unrelated
  log provenance was preserved. With a later competing edit, publication and
  return refused, preserving the local handoff/advance and the remote edit.
  Both cases passed. This validates the provenance approach, not the unbuilt
  strict admission helper or full launch integration. The probe ran via Python
  stdin with the absolute source/interpreter prefix below; its disposable
  repositories are under `/tmp/coga-projection-design-probe-lyh5v0sj`.
- `PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m pytest -q tests/test_git.py::test_expect_pins_the_exact_control_copy tests/test_git.py::test_a_feature_checkout_keeps_publishing_its_own_ticket tests/test_launch.py::test_launch_returns_a_feature_branch_handoff_before_the_next_step tests/test_launch.py::test_launch_returns_the_checkout_after_a_failed_session`
  passed: **4 passed in 2.77s**.
- `PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m coga.cli validate --task automate-checkout-setup-and-deduplicate-instructio --json`
  returned exit 0, 1 task OK, no issues.
- Read-only `compose.compose_prompt_report` checks verify the revised
  provenance/recovery requirements and owner dispositions reach the prompt,
  only Description/Context own body sections, and frontmatter, ticket guide
  and historical evaluator review are unchanged. `git diff --check` passed.

Reconciled to fetched control `47e9c5316`: only unrelated tickets and the
audit changed; relevant source, instructions and this ticket's control bytes
were unchanged. Backed up and verified the complete edit, restored the tracked
ticket, fast-forwarded, and reapplied it byte-for-byte. Only this ticket is
edited. Before the authorized handoff, fetched and fast-forwarded again to
`572e4c4c2`; only unrelated tickets and the audit had changed. This ticket and
the relevant source/instructions were unchanged. Design review is complete;
the next step implements the revised spec and its required owner/twin updates.
