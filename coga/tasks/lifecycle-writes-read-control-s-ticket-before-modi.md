---
title: Lifecycle writes read control's ticket before modifying it
status: in_progress
owner: nicktoper
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
step: 2 (evaluate-design)
agent: claude
---

## Description

Lifecycle commands currently derive transitions from the checkout's ticket
and discover conflicting control state only when publishing. A dirty control
checkout or a feature checkout can stay behind indefinitely. The command then
leaves a local transition that control refuses, requiring the human to recover
control's copy and redo the edit. A sandboxed write published by another
process can cause the same refusal on the originating checkout's next bump
because that checkout never recorded the landed blob as provenance.

The ticket's reported September 2026 log counts are 97 sync refusals and 194
read-only publication failures in Coga, and 23 refusals and 42 read-only
failures in multiply. These are incident evidence supplied with the ticket,
not measurements repeated during design. The older "would move backward"
diagnostic predates the current provenance guard.

Before modifying an existing ticket, fetch control, reconcile its ticket with
local unpublished edits, and derive the requested transition from that result.
Adopt a merely stale copy; merge independent edits; prefer demonstrably later
lifecycle progress when both sides changed the same lifecycle fields. An
ambiguous status conflict creates a PR whose title starts with
`Human Review needed`, preserving both versions for the human to resolve;
other genuine conflicts retain the existing refusal. After each supervised
agent session, retry publication outside the agent sandbox and remember
confirmed publication in the invoking checkout, including an idempotent retry
where another process already landed the same bytes. The cost is a fetch per
online lifecycle transaction and narrower automatic merging than a blind
"control wins" policy. Offline writes retain today's behavior.

### Acceptance criteria

- [ ] `bump` (including final completion and human rewind), all `mark` verbs,
  `block`, `unblock` (including each `--all` write), and `owner` prepare the
  target from freshly fetched control before checking ticket-dependent
  eligibility, deriving messages/operators/gates, or changing ticket bytes.
  Shared lifecycle writers and their launch, script, autoclose, megalaunch,
  and recurring callers participate in this boundary or supply an already
  verified exact snapshot. No caller may silently overwrite that snapshot
  with a newly reconciled ticket after preflighting different work.
- [ ] A stale clone with no unpublished target edits adopts control's ticket
  for its operation even when HEAD is a feature branch, detached, or control
  cannot fast-forward because of unrelated dirt. An unsupervised bump from
  local step 1 while control is at step 2 advances control's step 2 to step 3,
  subject to step 2's gate. Preserve control's body, blackboard, workflow,
  owner, agent, and extension fields. Do not switch branches or touch
  unrelated files/index entries.
- [ ] With unpublished local edits, a three-way reconciliation keeps
  independent changes from both sides. With an unchanged frozen workflow,
  base step 1, local step 2 plus a local note, and control step 3 plus an
  independent note, preparation selects step 3 and keeps both notes; a new
  unsupervised bump advances once to step 4. A terminal winner has no step.
  Ordinary one-sided changes, including a pause, blocker, or deliberate
  rewind, are not discarded merely because they are not forward progress.
- [ ] A genuine body/blackboard conflict, incompatible workflow/metadata
  conflict, unprovable merge base, or delete-versus-modify conflict refuses
  before this command writes a transition, appends/resolves a blocker, posts
  a notification, or emits a done marker. Keep the original local ticket
  bytes and control ticket intact; never write conflict markers into the
  live ticket. Name the path and conflict, retain the existing take-control-
  and-redo remedy, and tell the operator to save/reconcile local edits first.
  Suppress the generic CLI sweep for this refusal with exit 75 so it cannot
  publish the rejected local state. Ambiguous status conflicts use the review
  PR path below instead of choosing a winner.
- [ ] When both sides changed status and the ordering cannot choose a winner
  (`paused`/`blocked` against another status, or `done` versus `canceled`),
  leave the requested lifecycle operation unapplied and create a PR titled
  `Human Review needed: <ticket slug> — lifecycle merge conflict`. Its base
  is configured control; its head preserves the local ticket on a branch
  rooted at the proven provenance commit, exposing the unresolved conflict
  with control. Include the base, local, and control versions and the
  conflicting fields in the PR description. Do not resolve the conflict,
  auto-merge, or put conflict markers into the live ticket.
- [ ] Repeating the same status conflict reuses its open PR without
  overwriting human edits. Report its URL, preserve both original ticket
  versions, and exit 75 with the generic sweep suppressed. If GitHub/auth,
  network, or Git writes are unavailable, retain the existing local refusal
  and report that the review PR could not be created; never claim it exists.
  Coga's automatic conflict-resolution and PR-comment sweeps must leave
  `Human Review needed` PRs for the human. A reconciliation PR must not
  replace the ticket's implementation `## Dev` PR or complete its workflow.
- [ ] Validation uses the reconciled snapshot. A now-terminal control copy
  cannot be reopened by a stale `mark active`/pause/block; owner and PR/branch
  gates are rechecked. A supervised bump whose expected step differs from
  the reconciled step refuses as stale context instead of finishing another
  session's step. Human-only rewinds still deliberately move backward after
  reconciliation, with their existing authorization and publication rules.
- [ ] Keep the exact control bytes read as the publication expectation.
  Another checkout changing this ticket between preparation and publication
  must still cause a refusal, not an implicit second transition. An unrelated
  control commit may use the existing bounded push retry. Keep pending and
  released launch-generation protections, recurring leases, explicit
  `expect`/`guard` checks, and strict rollback/uncertain-publication semantics.
- [ ] If a fetch is unavailable (including sandbox Git/network denial),
  ordinary best-effort commands report the miss and retain today's local
  read/write and guarded publication behavior. Do not merge against a cached
  ref while claiming it is fresh. Git-disabled, non-Git, and no-control
  soft-skips remain compatible; without a configured remote, local control
  remains canonical. Existing strict callers do not gain an offline bypass.
- [ ] After an actually started stateful execution session exits, launch and
  megalaunch retry the target ticket plus log publication outside the child
  sandbox, before their ticket reread/chain decision and launch refresh.
  Cover clean completion, timeout, nonzero exit, and handled interruption.
  Keep the child's exit/termination result and the local write on failure;
  report the publication miss. No retry runs for a refused/unreleased spawn.
  Bootstrap and guided-authoring sessions keep their existing publication
  boundaries. Other tasks/recurring files remain covered by the ordinary
  end-of-command sweep.
- [ ] A successful retry, including `publish` returning `False` because
  control already has the candidate tree, records the confirmed blobs under
  the invoking checkout's `refs/worktree/coga/published`. No extra control
  commit is made for equality, no lifecycle command is replayed, and no other
  worktree's provenance is changed. Failed/unconfirmed publication never
  records proposed bytes as landed.
- [ ] Real-Git regression coverage reproduces the 2026-09-27 multiply
  improve-banners sequence: a child bump changes local ticket/log but cannot
  write Git objects; a peer publishes the exact ticket; the parent confirms
  that state and records provenance; the next human bump in the same feature
  checkout succeeds. Also prove recovery when no peer publishes first.
- [ ] Update the owning state-publication and git-regressions topics and the
  sync overview, plus affected lifecycle, git-refresh, agent-spawn, launch,
  and assist-publication statements and their packaged twins. Include the
  narrowly scoped conflict-PR exception to ordinary state publication and the
  human-review exclusion in both live and packaged PR-maintenance tickets. The
  implementation's regression suite and scoped validation pass with exact
  commands/counts recorded on this ticket.

### Proposed shape

1. **Prepare one ticket transaction in shared Git infrastructure.** Add a
   small snapshot/result type and preparation boundary in `src/coga/git.py`
   (for example `prepare_ticket_update`, a proposed new symbol). Under
   `state_lock`, capture the exact local bytes, fetch via `fetch_control`,
   pin the returned revision, and read the same path with `tree_bytes`.
   Return the reconciled `Ticket`, original local bytes, and exact control
   expectation. Prepare in memory; command checks and body edits must consume
   this view rather than rereading the stale file. Commit the final candidate
   once, atomically, after rechecking local bytes. Hold/reacquire the local
   lock through write and publication; any unlocked preflight or human prompt
   requires a fresh check before mutation. Do not hold it while prompting.
   A conflict is a distinct refusal, never a swallowed fetch failure.

2. **Choose a real provenance base.** `src/coga/git.py` `_provenance` supplies
   an eligibility set, not an ordered merge base. Use HEAD, the HEAD/control
   merge base, and this worktree's `PUBLISHED_REF` as candidate snapshots;
   verify their relationship to the pinned control path's history. An
   unpublished feature-branch commit is a local edit, not automatically a
   shared base merely because it is HEAD. Exact local/control equality needs
   no merge. Local bytes equal to a proven shared snapshot have no new bytes
   to replay and can adopt control. Otherwise use the newest verifiable
   shared per-path snapshot by commit ancestry, not timestamps, preferring
   the worktree's later published blob
   over an older branch point, but a subsequently incorporated control copy
   over an older publication record. If that relationship cannot be proved,
   refuse rather than select an arbitrary member of the provenance set or
   substitute current control as the base. Missing-on-control after a known
   base is deletion, not permission to resurrect. An unpublished new ticket
   whose path is absent on control retains the existing create path.

3. **Merge tickets structurally and conservatively.** Use ordinary three-way
   rules for frontmatter keys (including absent values): identical sides
   agree; an unchanged side yields to the changed side; incompatible edits
   to the same value conflict. Treat a frozen workflow as one routing value,
   not a list to union. Merge the full body, including the blackboard, with
   standard three-way text merging in temporary files, without `--union`;
   keep the existing union merge only for append-only paths such as the log.
   Preserve independent changes and validate the resulting ticket.

   For overlapping lifecycle conflicts, factor an explicit comparator from
   `src/coga/git.py` `_STATUS_RANK`/`_lifecycle`: ranked progress is draft,
   active, in_progress, then terminal; within the same status and unchanged
   frozen workflow, compare valid numeric step positions. Select a coherent
   lifecycle result, not independent maxima that combine a terminal status
   with a live step. The ordering does not decide arbitrary metadata,
   different workflows, generation IDs, or tied terminal outcomes. The owner
   resolved Q1 by requiring a human-review PR for incomparable status changes.
   `ticket_regression_reason` still runs as an
   independent launch-claim check; it is not currently a lifecycle comparator.

   **Human-review PR for an ambiguous status conflict.** Return the captured
   path, proven base commit/blob, local bytes, pinned control commit/blob,
   conflicting fields, and requested operation as a structured conflict to a
   shared reporter used by the lifecycle command callers. Keep GitHub work
   out of raw `publish` and its generic sweep. Build a dedicated branch from
   the proven base commit with only this ticket's local bytes overlaid, using
   an isolated temporary index or checkout. Push that branch to the configured
   repository and use `gh pr create` with the exact title prefix above and a
   file-backed PR body. The normal Git merge conflict and the description
   expose both choices; never manufacture malformed ticket bytes to force
   GitHub to label a semantic conflict as unmergeable.

   Identify retries by ticket path and base/local/control ticket-blob
   fingerprints, not the global control commit (unrelated log appends must
   not create duplicate PRs). Reuse an open matching PR; never force-push over
   a human's resolution. Print the PR URL and record the escalation through
   the normal audit writer. Do not use `open_pr`'s implementation-PR path or
   its `Closes ticket:` footer, and do not overwrite `## Dev` `branch:` or
   `pr:`. After a human resolves and merges it, retry the original lifecycle
   command against fresh control; creating or merging the reconciliation PR
   is not itself a bump or task completion. No permission/configuration bypass
   or hidden retry queue is added when PR creation fails.

   Update `coga/bootstrap/resolve-conflicts/ticket.md` and
   `coga/bootstrap/address-pr-comments/ticket.md` (and packaged twins) to read
   the PR title and report `Human Review needed` PRs without editing them.
   This keeps an automated rebase from deciding the status conflict the
   owner explicitly reserved for human judgment. The state-publication and
   git-regressions topics own this narrow exception: control remains
   canonical, while the PR branch is a proposed reconciliation only.

4. **Wire readers as well as writers.** In `src/coga/commands/bump.py` `bump`,
   reconcile before status, supervised-step, workflow, and `requires:` checks;
   pass the prepared snapshot through `src/coga/bump.py` `advance_step` or
   `src/coga/mark.py` `mark_done`. In `commands/mark.py`, replace the stale
   `_load`/check/write split with the same boundary around each verb. In
   `commands/block.py` `block` and `commands/unblock.py` `_apply_unblock`,
   reconcile before changing asks and keep the ask plus status change in one
   ticket write; revalidate asks after an interactive answer. In
   `commands/owner.py` `owner`, preserve strict publication and rollback, but
   distinguish original local bytes from fetched control bytes when choosing
   the rollback snapshot versus `expect`.

   Audit every `src/coga/mark.py` shared writer's callers. In particular,
   `src/coga/autoclose.py` `_try_bump_one` must validate the current PR linkage
   and final-step eligibility after reconciliation, not close a replacement
   ticket using a prior PR lookup. Launch/script preparation must recompose
   or refuse when freshness changes the ticket it preflighted. Megalaunch and
   recurring already supply stricter exact-byte/generation proofs: carry
   those through unchanged rather than automatically merging a different
   revision into their preflighted write. `prepare_active` remains pure.
   Avoid hiding reconciliation in `git.write_ticket`, which receives an
   already-mutated object too late to fix its caller's decisions.

5. **Keep publication compare-and-swap.** Thread the prepared control bytes
   into `src/coga/git.py` `sync_task_state`/`publish` and the shared mark
   publication path. Ensure the explicitly prepared ticket participates even
   if its final bytes happen to equal HEAD, rather than losing its expectation
   through `_candidates`. Preserve stricter existing `expect`/`guard` inputs.
   A same-ticket race after the read is reported with existing post-write
   retention/rollback behavior; do not rerun bump, append a blocker, or repeat
   notifications inside a Git push retry. Raw publication and the generic
   sweep retain their guards; they do not become automatic ticket mergers.

6. **Repair post-session publication and provenance together.** In
   `src/coga/commands/launch.py` `spawn_agent_session`, extend teardown after
   usage capture for actually started stateful execution sessions to retry
   `sync_task_state` for the invoking checkout's target plus log. Fetch before
   confirming an already-landed retry. Retain a separate `sync_log` attempt
   if ticket publication refuses, so a stale target cannot suppress usage.
   Keep guided authoring (`stateless_identity`) on `authoring.finalize_authored`
   and bootstrap on its current log path. Do not follow a blackboard
   `worktree:` pointer into another clone, retry a lifecycle transition, or
   add Git-writing policy to the PTY watcher in `repl_supervisor.py`.

   In `src/coga/git.py` `_publish_locked`, record confirmed candidate blobs
   before the equal-tree `False` return as well as after a successful push.
   This repairs the precise peer-published case; only recording provenance
   when creating a new commit would leave it broken. Preserve the distinction
   between a durable write and a failed attempt to record its local witness.
   A supervisor publication failure remains best-effort under today's
   lifecycle contract; changing chain policy is not part of this ticket.

7. **Prove behavior with real Git before broad regression checks.** Extend
   `tests/test_git.py` using `tests/conftest.py` `git_repo` and the existing
   peer-clone helpers. Exercise file and directory tickets, nondefault
   remote/control names, a detached/dirty feature checkout, committed local
   ticket edits, newer HEAD versus older publication provenance, repeated
   feature publication, independent prose edits, a true blackboard conflict,
   terminal progress, and a same-ticket race after preparation. Assert both
   working bytes and the actual bare remote tree, plus no unrelated index or
   branch changes. Cover fetch failure and read-only object-write failure by
   injecting only the failing Git operation while keeping the repositories,
   merge, push, and provenance reads real.

   Add command-level tests in `tests/test_commands.py`, `tests/test_mark.py`,
   and `tests/test_owner.py` for fresh eligibility, stale supervised bump,
   blockers, rewind, and refusal sweep suppression. Update tests that
   currently require a known-stale online command to mutate locally first;
   keep low-level `publish` refusal tests. Extend `tests/test_launch.py`
   around `test_spawn_commits_usage_log_at_teardown` and
   `test_spawn_publishes_usage_log_to_control_after_pr_gated_handoff` for
   post-session retry and the peer-published sequence, including linked
   worktree provenance isolation and authoring/no-spawn exclusions. Verify
   the shared path is reached by megalaunch, while existing launch-claim,
   script, recurring, and autoclose suites retain their stricter guarantees.
   Add real-Git fixtures for each ambiguous-status pair that verify the
   preserved divergent history and ticket-only PR diff. Stub only the GitHub
   API/CLI boundary to verify the title prefix, evidence, returned URL,
   identical-conflict reuse, preservation of human branch edits, and auth/
   network failure fallback. Verify no implementation PR linkage or lifecycle
   transition is written, and cover the automatic-maintenance exclusions and
   their packaged twins.
   Run focused suites first, then the full suite using an absolute source
   `PYTHONPATH`, `tests/test_packaging.py`, and scoped `coga validate`.

### Out of scope

- Checkout normalization, switching to main, cleaning state, stashing,
  rebasing, or altering the downstream launch-normalization design.
- New lifecycle states, flags, config knobs, workflow changes, or automatic
  resolution of conflicting prose, arbitrary metadata, or launch claims.
- Broadly changing raw `publish`, the sweep, guided ticket interviews,
  creation/deletion contracts, or arbitrary hand edits into read-before-edit
  transactions. Preserve their existing protections.
- Generating review PRs for every publication refusal. The owner-requested
  PR escalation is for ambiguous status conflicts; ordinary body/metadata
  conflicts and launch-generation/lease refusals keep their specified handling.
- Changing agent sandbox permissions, adding a daemon/queue, discovering
  writes in arbitrary external clones, or giving the supervisor a new
  cross-checkout ownership protocol. The recovery checkout is the one that
  invoked the session; normal other-state sweeping stays in place.
- Reproducing historical production runs with real model sessions or
  re-counting the incident logs. Regression fixtures encode the reported
  failure sequence without invoking a model or changing sandbox settings.

## Context

Topics are cited rather than attached because this change edits their owning
contracts. Read `coga/internals/state-publication`
(`docs/contexts/coga/internals/state-publication/SKILL.md`), especially
"Invariants", "Best-effort versus strict", and "The end-of-command sweep";
`coga/internals/git-regressions`
(`docs/contexts/coga/internals/git-regressions/SKILL.md`), "The provenance
check", "Hooks", and "Other refusals"; and `coga/sync`
(`docs/contexts/coga/sync/SKILL.md`), "Control versus feature checkouts".
The implementation must update their packaged copies under
`src/coga/resources/templates/coga/bootstrap/contexts/` too.

Also cite and read `coga/lifecycle` (`docs/contexts/coga/lifecycle/SKILL.md`),
"Status", "Step", and "Writer validation timing"; `coga/internals/git-refresh`
(`docs/contexts/coga/internals/git-refresh/SKILL.md`), the inbound-refresh
contract; `coga/internals/agent-spawn`
(`docs/contexts/coga/internals/agent-spawn/SKILL.md`), "Order inside one call";
and `coga/internals/launch-claims`
(`docs/contexts/coga/internals/launch-claims/SKILL.md`), its exact-byte and
pending-seal rules. Update affected summaries in `coga/launch` and
`coga/internals/assist-publication` with their twins; link to the owner rather
than duplicating the new merge specification. In particular, git-refresh's
blanket statement that state sync never copies a control ticket into a feature
checkout must distinguish whole-checkout refresh from this new preparation.

Load-bearing source relationships at design time:

- `src/coga/git.py` `publish` calls `_publish_locked`; `_publish_locked`
  computes `_candidates`, calls `_guard` with `_provenance`, builds a tree,
  and pushes it. The hot path currently uses a tracking ref without fetching;
  its equal-tree return precedes `_record_published`. `_record_published`
  stores a per-worktree tree of blobs, not an ordered history or merge base.
- `src/coga/git.py` `ticket_regression_reason` seals pending launch claims
  and rejects released witnesses. `stale_coga_task_rels`, not that guard,
  uses `_STATUS_RANK` and `_lifecycle` for the read-only progress warning.
- `src/coga/commands/bump.py` `bump` reads disk before gates and calls
  `src/coga/bump.py` `advance_step` or `src/coga/mark.py` `mark_done`.
  `git.write_ticket` locks only the write, which does not make those earlier
  reads fresh. `_assert_supervised_step_is_current` binds a bump to its
  launched task and step; it must examine the prepared ticket.
- `src/coga/commands/block.py` `block` and `commands/unblock.py`
  `_apply_unblock` edit the blackboard before invoking shared mark writers.
  `src/coga/commands/owner.py` `owner` already holds a lock and publishes
  with exact `expect`, but its source is still the local file.
- `src/coga/commands/launch.py` `_launch` and `src/coga/megalaunch.py`
  `_launch_until_stop` call `spawn_agent_session` and reread the task after it
  returns. That shared function captures usage and calls `git.sync_log` in
  `finally`; `_launch` later calls `_refresh_launch_checkout`, which delegates
  to `git.refresh`. A log-only retry cannot repair ticket provenance.
- `src/coga/recurring_runner.py` `_verify_period_on_control` fetches before
  comparing period/parent leases; its `_run_delegated_task` completion calls
  `mark_done(strict=True)` only after lease verification. Do not turn that
  exact-generation decision into an automatically merged completion.
- `tests/conftest.py` `_stub_git` disables publication by default;
  `git_repo`/`real_git` opt out. The new fetch/preparation seam needs the same
  isolation so mocked agent subprocess tests do not accidentally use Git.
- `src/coga/open_pr.py` `open_pr` checks an implementation branch and writes
  its URL through `set_dev_pr`; `_pr_body` adds `Closes ticket:`. The new
  reconciliation PR must not reuse those lifecycle effects.
  `coga/bootstrap/resolve-conflicts/ticket.md` "Run order" currently selects
  conflicting PRs and resolves them with agent judgment, so its title-based
  human-review exclusion must ship with this behavior. The adjacent
  `coga/bootstrap/address-pr-comments/ticket.md` "Run order" must honor the
  same boundary even if Git considers the semantic conflict mergeable.

This absorbs the failure described by
`coga/tasks/ticket-sync-fails-with-read-only-git-inside-agent.md`; no sandbox
policy change is needed. Land it before
`coga/tasks/launch-moves-the-checkout-to-main-before-and-after.md`: that
ticket's evaluator finding 2 identifies unpublished state that can otherwise
make launch entry refuse and suppress the very sweep needed to recover it.
This prerequisite does not by itself resolve that ticket's admission policy.

<!-- coga:blackboard -->

## Design investigation — 2026-09-27

- `src/coga/git.py` `_provenance` returns an unordered set of eligible
  blobs (HEAD, merge base, per-worktree `PUBLISHED_REF`); a three-way merge
  needs an explicit base-selection rule, not an arbitrary member of that set.
- `src/coga/git.py` `ticket_regression_reason` now protects pending and
  released launch generations only. `_STATUS_RANK` and
  `stale_coga_task_rels` retain the progress ordering used by the status
  warning. Paused/blocked have no rank; done/canceled tie.
- `src/coga/git.py` `_publish_locked` returns `False` for an already-equal
  control tree before `_record_published`. This leaves the originating
  feature checkout without provenance when another process landed its bytes.
- `src/coga/commands/launch.py` `spawn_agent_session` is shared by launch and
  megalaunch and publishes only the log in teardown. Retry ticket publication
  there before callers reread state; preserve authoring's validation boundary
  and recurring/megalaunch exact-byte claims.
- Read the folded sandbox-sync ticket and the downstream launch-normalization
  evaluator. This ticket must land first; it does not normalize branches.

## Design handoff

- Written specification is under `## Description` with acceptance criteria,
  proposed shape, and scope; source relationships and owning topics are under
  `## Context`. The later implementation must update the owning topics and
  twins together. This step changed only this ticket, with no source edits,
  branch, or PR.
- `coga validate --task lifecycle-writes-read-control-s-ticket-before-modi
  --json`: 1 valid task, 0 issues, 0 fixes.
- `git diff --check`: clean. A read-only structural check confirmed the
  original frontmatter is unchanged, exactly one blackboard fence exists,
  and code citations use symbols rather than line numbers. Source-pinned
  `compose_prompt_report` confirmed all three spec subsections and Q1 appear
  in the composed prompt. Runtime tests belong to implementation.
- Q1 was resolved by the owner on 2026-09-28; the updated acceptance criteria
  and proposed shape require a human-review PR instead of choosing precedence.
  The independent evaluator still needs to assess the amended design.

## Owner decision — 2026-09-28

- For an ambiguous status conflict, create a PR containing the merge conflict
  and prepend its title with the exact text `Human Review needed`.
- Incorporated into the ticket's composing specification: preserve the
  competing versions, leave the requested transition unapplied, isolate the
  proposed reconciliation from canonical control, and reserve resolution for
  the human. This is a narrowly scoped exception to the ordinary rule that
  lifecycle state is published directly to control rather than through a PR.
- This follow-up amends the design only. It stays at `evaluate-design`;
  the author has not performed or bypassed the independent evaluator step.

## Open Questions

- Q1 — Resolved: create the human-review PR specified above; no automatic
  winner for incomparable status changes. No unanswered owner question is
  currently recorded.
