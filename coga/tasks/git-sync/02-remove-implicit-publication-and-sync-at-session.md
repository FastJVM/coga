---
title: Remove implicit publication and sync at session end
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
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 2 (evaluate-design)
agent: claude
launch_generation: pending:cbc9d672-1982-4bf1-abfc-8a90f1b2c633
---

## Description

Second ticket of the `git-sync/` project. It depends on
`git-sync/01-add-an-explicit-coga-sync-command` being merged: the implement
step must not start until `coga.sync.run_sync` exists on main. The step
switches Coga to explicit publication. It removes the end-of-command sweep
and every per-command or per-transition publication, and it makes launched
and unattended sessions run `coga sync` at session end, so no work is
stranded when no human is present.

Done means a merged PR in which no command publishes implicitly. The
`coga launch` supervisor, megalaunch and the recurring runner sync at session
end. Tests cover these behaviors, and the topics, base prompt and step skills
describe the explicit model.

The governing rule of this spec: **reads of fresh control stay, and writes
to control go.** Fetching control and reconciling with it (prepared ticket
transactions, `git.refresh`, launch checkout preparation, recurring
control-ledger reads) is pulling, and it stays. Every call that pushes is
removed. Code that exists only to handle a publication outcome is removed
with it (restore-on-refusal, uncertain-publish evidence, `bind_published`,
"sweep withheld" signalling). Every check that compares *control* to this
process's own unpublished writes becomes a local check, because control no
longer carries those writes until the session ends.

### Design decisions (resolving the ticket's open items)

1. **Launch entry only pulls, and supervisors start clean.** `coga launch`,
   `coga megalaunch` and the recurring runner refuse to start when the
   checkout has *unsynced Coga state*. That means a dirty, unignored path
   under `git.coga_root_paths(cfg)`, or a root change between
   `merge-base(<remote>/<control>, HEAD)` and `HEAD`. The refusal names the
   paths and the remedy (review them, then `coga sync`). The reason: the
   session-end sync commits the whole Coga roots, so a supervisor that starts
   dirty would silently publish a human's unrelated edits, such as a fork
   override, at session end. That is exactly the implicit publication this
   project removes. Launch already gets this refusal from
   `git.prepare_control_checkout` once the pre-launch sweep is gone, so it
   only needs the new remedy text. Megalaunch and the recurring runner gain an
   explicit check.
2. **Session end.** Each supervisor syncs after every agent session it
   started, after every checkout settle (which covers `ticket.py` phases),
   and once more as its last act. The sync runs after usage capture, so the
   usage record rides it, and before the supervisor rereads the ticket to
   chain. Discussion sessions (`launch.DISCUSSION_BOOTSTRAP_TICKETS`:
   `coga chat` and the `coga ticket` interview) do not sync. A human is in
   the loop there and syncs explicitly.
3. **Supervisor crash.** Nothing recovers stranded state automatically.
   Uncommitted state stays dirty, and a sync that failed mid-way leaves its
   `Sync coga state` commit on the local branch (ticket 01's contract). The
   next supervisor run in that checkout refuses under decision 1, names the
   paths and says to run `coga sync`. An unattended recurring run reports that
   refusal through the Important channel, so a human learns about it. Agents
   may also run `coga sync` mid-session. It is idempotent, and the
   supervisor's later sync becomes a no-op.
4. **Failed session-end sync.** When `run_sync` exits non-zero (a conflict, a
   push failure, or a refused precondition), the supervisor reports it in red
   with sync's own stderr. It stops chaining and exits 75. Megalaunch ends the
   queue instead of starting the next pick on unsynced state. The recurring
   runner stops servicing that repo and posts an Important notification. The
   session's own result is never rewritten.
5. **Launch audit lines and notifications fire on the local write.** Lines
   appended with `append_log` and Slack posts happen when the transition
   happens locally. They reach main at the next sync. Coga has no digest or
   queue, and a post tied to a later publication could never be delivered
   once its process has exited.
6. **Megalaunch and recurring admission have no claim exception.**
   Megalaunch always takes its existing Git-disabled claim path: a plain-UUID
   `launch_generation`, no `pending:` seal, no fresh-control proof of the held
   child, and no admission publication. Recurring period creation writes
   locally after reading control's ledger. Two clones can therefore admit the
   same ticket or period between syncs. Cross-clone exclusion is now the
   owner's job, as the owner decided. The race surfaces loudly at the second
   clone's session-end sync: `git.merge_ticket_bytes` conflicts on the
   differing `launch_generation` or `period_generation`, and sync exits 1 with
   the path. Within one supervisor, chaining is unaffected, because it rereads
   the local ticket and syncs before every next step.
7. **Inactivity.** `run_sync` gains a keyword-only `subject` parameter
   (Python only, so the CLI stays option-less). The recurring runner syncs
   with subject `Sync coga state: recurring`. Every other sync uses
   `Sync coga state`. In `recurring_activity._MACHINE_SUBJECT`,
   `Sync coga state` (machine) becomes `Sync coga state: recurring`, so a
   human's or a launched session's sync counts as activity. Without this
   change, almost every control commit would read as machine activity and
   every repo would look idle.
8. **Strict publication is retired.** `coga run publish-state` is a
   publication path, and `coga sync` is now the only one. It leaves
   `runner.RECIPES`, and every remedy that named it names `coga sync`.
9. **An exit hint replaces the sweep.** When a former sweeping command
   (`cli._should_sweep_coga_state` is true) exits with unsynced Coga state,
   and no supervisor is running it (`repl_supervisor.SENTINEL_ENV` is unset),
   the CLI prints one stderr line:
   `[coga] Coga state is not published; run \`coga sync\` to publish it.`
   It runs no Git writes and never changes the exit code. Fail loud,
   cheaply.
10. **Trim-log keeps its guarded publication for now (Open Question 2).**
    `coga_edge/trim_log.py` removes events only after proving they are
    reachable on control. That is a deliberate destructive audit transaction,
    not a command's implicit write, and removing its publish would destroy
    unarchived events. It is listed as a named, temporary exception, and
    nothing else may call `git.publish` after this ticket.

### Acceptance criteria

Removal
- [ ] No module under `src/` except `src/coga/git.py`, `src/coga/sync.py`
      and `src/coga_edge/trim_log.py` calls `git.publish`,
      `git.sync_task_state`, `git.sync_coga_state`, `git.sync_log` or
      `git.retry_session_publication`. A test enforces this with a grep or AST
      scan over `src/`, with that allowlist.
- [ ] `cli._sweep_coga_state` and `cli._warn_unpublished_log_lines` (with
      `_LogMark`, `_log_mark`, `_control_log_lines`) are gone. `main()`
      instead calls the exit hint from decision 9. `_should_sweep_coga_state`
      may survive, renamed, as the hint's predicate.
- [ ] No user-visible text says that a sweep ran, was withheld or will retry.
      Exit 75 keeps its meaning: retained state, retry after reconciling.
- [ ] `coga run publish-state` is removed from `runner.RECIPES`, and
      `src/coga/publish_state.py` is deleted. `coga run publish-state` exits
      with the runner's unknown-recipe error.
- [ ] Every converted call site keeps its local write, its log line and its
      notification. For each lifecycle command (`bump` including rewinds,
      every `mark` verb, `block`, `unblock` including `--all`, `owner`,
      `create`, `delete`), a test asserts that the file and log change
      locally, that `refs/remotes/origin/main` and the remote are unchanged
      afterwards, and that a following `coga sync` lands the change.

Supervisor start
- [ ] `_CheckoutBoundary.enter` no longer calls `git.sync_coga_state`. When
      `prepare_control_checkout` refuses because of Coga-root paths, the
      message adds `Coga state here is not published: review it, run
      \`coga sync\`, then retry.` A test runs `coga create x`, then
      `coga launch x`: launch refuses with exit 75 and starts no agent. After
      `coga sync`, the launch proceeds.
- [ ] `run_megalaunch` and each recurring repo run check for unsynced state
      (decision 1) through a shared `coga.sync.unsynced_paths(cfg)`, before
      picking, refreshing or creating anything. Unsynced state refuses: exit
      75 for megalaunch, and for recurring a refused-repo report plus an
      Important notification. Tests cover both. A dirty path outside the Coga
      roots does not trigger the refusal.
- [ ] The in-process `launch` from `bootstrap/retire/ticket.py` keeps working.
      Retire calls `run_sync` explicitly after creating its task and before
      launching it, and a test covers this.

Session end
- [ ] `spawn_agent_session` takes `sync_at_end: bool`. After usage capture it
      calls `run_sync(cfg)` in place of the `git.sync_log` /
      `git.retry_session_publication` block. `launch.py` passes `True` except
      for `DISCUSSION_BOOTSTRAP_TICKETS`. `megalaunch.py` passes `True` and
      `commands/ticket.py` passes `False`. The recurring delegated runs pass
      `True` through launch.
- [ ] `_CheckoutBoundary.settle` calls `run_sync` in place of
      `git.sync_coga_state`, then `prepare_control_checkout` as today. A
      non-zero sync result counts as a refused return (decision 4).
- [ ] `_launch`, `run_megalaunch` and the recurring runner's per-repo entry
      point (`_run_repo_recurring`, plus `run_recurring_named` and
      `run_recurring_scan` when called directly) each run one final
      `run_sync` in a `finally` once they have passed the start check. The
      recurring runner passes `subject="Sync coga state: recurring"`.
- [ ] Integration test against a bare remote: a launched step whose fake agent
      runs `coga bump` leaves the bump, its log line and the usage record on
      `origin/main` after the launch returns. Megalaunch with two picks lands
      each pick's state before the next pick starts. A recurring period's
      creation and run land as `Sync coga state: recurring`.
- [ ] A failed session-end sync (for example a remote that rejects the push)
      leaves the local state committed, prints sync's diagnostic plus
      `Not chaining further`, exits 75, and a megalaunch with a second pick
      does not start it. Tested.
- [ ] `_terminal_status_probe` always watches the local ticket file. The
      remote-tracking-ref source is removed, and the five-second stability
      window stays. Tested with Git and a remote enabled.

Claims and leases (decision 6)
- [ ] Megalaunch preflight always writes a plain-UUID `launch_generation`.
      `_revalidate_launch_claim_before_spawn` and
      `_admit_launch_claim_after_release` take their existing
      `not cfg.git_enabled` branches unconditionally. Readers still refuse a
      ticket that already carries a `pending:` or `released:` generation, and
      still point to `coga launch <slug>`. `coga launch`'s
      released-admission reconciliation (around the "reconcile released launch
      admission" publish in `launch.py`) writes the admitted form locally,
      without publishing.
- [ ] `checkouts._publish_linkage` writes `branch:` locally. Checkout
      planning reads the ticket's linkage from the local file instead of from
      control after publication.
- [ ] Recurring guards that compared control's copy against this run's own
      writes (`_revision_period_lease` / `_revision_parent_state_lease` checks
      at later boundaries, and the guards passed to the removed
      `git.publish` calls) are deleted or switched to their `_local_*`
      variants. The run does not refuse its own unpublished writes. The
      control-ledger *read* that decides "already serviced on control" stays.
- [ ] A test with two clones shows that duplicate admission of one ticket
      makes the second clone's session-end sync exit 1 with the ticket path,
      and that the second clone's local state is retained.

Inactivity (decision 7)
- [ ] `run_sync(cfg, *, subject="Sync coga state")` uses `subject` for both
      commits. `_MACHINE_SUBJECT` matches `Sync coga state: recurring` but not
      a bare `Sync coga state`. `tests/test_recurring_activity.py` covers both.

Topics, prompts and skills (same PR)
- [ ] `coga/state-publication` is rewritten around the explicit model: what
      `coga sync` carries, who calls it (humans, agents, supervisors at
      session end), the start-clean rule, crash recovery, and the exit hint.
      The sections on the sweep, held for merge, launch publication
      boundaries and strict publication are removed. Prepared ticket
      transactions and human review of status conflicts stay, reworded as
      local reconciliation. The topic states that this deliberately reverses
      the old invariant that publication happens "without committing on a
      local branch, stashing, or rebasing", and links `coga/sync/command`
      (ticket 01). Delete the `state-publication/launch-boundaries` leaf, or
      reduce it to a pointer.
- [ ] `coga/sync` (map), `coga/checkouts` (including "Stranded ticket
      writes"), `checkouts/launch-boundary`, `checkouts/reconciliation`,
      `checkouts/manual`, `checkouts/sandbox-clone`, `checkouts/chat`,
      `coga/launch`, `coga/megalaunch`, `coga/notifications/producers`,
      `coga/recurring/scheduling/inactivity` and `coga/cli` describe the
      explicit model. None of them mentions the sweep, held for merge or
      `publish-state`.
- [ ] Base prompt `src/coga/resources/prompt.md` ("Reconcile before
      publishing") and `prompt-ticket.md` say that state the agent writes
      reaches main at session end, or when the agent runs `coga sync`. In a
      manual or API session, the agent runs `coga sync` itself before
      handing off. `prompt-queue.md` and `prompt-megalaunch.md` match.
- [ ] Every shipped skill, ticket and runbook that the Context grep finds
      describing implicit publication is corrected. `coga validate --json`
      and `python -m pytest` pass.
- [ ] `coga-dev/internals/state-publication`, `coga-dev/internals/launch-claims`
      and `coga-dev/internals/claim-recovery` are updated, and
      `coga-dev/codebase` drops `publish_state.py`.

### Proposed shape

Order of work: decisions first, then removal, then tests, then docs.

1. **`src/coga/sync.py`** (from 01). Add the `subject` keyword and
   `unsynced_paths(cfg) -> list[str]`: dirty unignored paths under the roots,
   plus root paths changed since the merge-base with the remote control tip
   (with no remote, local control). Reuse the helpers 01 already uses. Add
   `session_end_sync(cfg, *, label, subject=...) -> bool`, which runs
   `run_sync`, echoes its stage lines, reports failure in decision 4's form
   and returns success. All supervisors call this one helper.
2. **`src/coga/cli.py`.** Delete the sweep and the unpublished-log warning.
   Add `_hint_unsynced(cfg)` as decision 9, where `main()` used to sweep.
3. **`src/coga/launch.py`.**
   - `_CheckoutBoundary.enter` and `settle` follow the criteria.
   - Remove `_publish_startup`'s `git.publish`. Startup writes stay local,
     under the same lock and validation.
   - Remove the `git.sync_log` in `_prepare_step_checkout`.
   - Convert the released-admission reconciliation to a local write.
   - `spawn_agent_session` gets `sync_at_end`.
   - `_terminal_status_probe` reads only the local file.
   - Add the final sync in `_launch`'s `finally`.
4. **`src/coga/megalaunch.py`.**
   - Add the start check.
   - Claims follow the Git-disabled path.
   - Remove the `sync_task_state` and `git.publish` calls in
     `_publish_partial_dependency_resolution`, deferred activation and
     `_admit_launch_claim_after_release`, along with their uncertain/restore
     branches.
   - Pass `strict=False` (or drop `strict`) to `mark_in_progress` /
     `mark_active`.
   - Run the final sync.
5. **`src/coga/recurring_runner.py`.** Add the start check, then do the
   period-creation writes locally. Remove `git.publish` / `sync_task_state`
   with their guards and `bind_published` (`_sync_period_creation` and its
   helpers around the "recurring create" messages). Convert the control
   leases. Run the final sync with the recurring subject.
6. **Lifecycle and other callers.** Delete the publish calls and their
   outcome handling. The prepared-ticket *read* (`prepare_lifecycle_ticket`
   / `git.prepare_ticket`) stays everywhere:
   - `bump.advance_step`'s `sync_state`, and the rewind
     `StateRegressionError` handler in `commands/bump.py`.
   - `mark._publish` and both `mark` `sync_task_state` calls.
   - `commands/create.py`, `delete.py` (the publish only; keep
     `--keep-control-checkout`'s precondition), `owner.py` (move
     `prepared.finish_resolution(published=True)` to right after the local
     write, and drop the restore/retract branch), `unblock.py`, and
     `recurring.py` (`promote` and `list_recurring`'s withheld flag).
   - `branchsweep.py`: write the worklist locally, and drop the
     restore-on-failure branch.
   - `recurring_autofix.py`, `blocker_reminders.py`,
     `coga_edge/phone_home.py` and `launch_script.py`: `sync_log`, the assist
     `sync_task_state`, and the post-publish re-derivation become plain local
     flow.
   - `authoring.finalize_authored`: validate and write only. The refusal for
     a destination change may stay.
   - `bootstrap/retire/ticket.py`: create and block are local, delete is
     local, and an explicit `run_sync` comes before the in-process launch.
   - Docstrings in `github_preflight.py` and `notification/__init__.py`.
7. **`src/coga/recurring_activity.py`.** Change the regex.
8. **Tests.** Write the new tests first (lifecycle-local, supervisor start,
   session end, failed sync, two-clone race, probe, hint, grep guard). Then
   fix or delete the tests that assert implicit publication. The inventory is
   in Context. `conftest._stub_git` stops stubbing removed functions and
   stubs `coga.sync.run_sync` where a test needs no remote.
9. **Docs.** Rewrite the owners first (`coga/state-publication`,
   `coga/checkouts/*`, `coga/launch`, `coga/megalaunch`, `inactivity`, the
   prompts), then run the grep sweep in Context over the remaining surfaces.

### Out of scope

- Deleting now-dead machinery in `git.py`: `_publish_locked`, `_candidates`,
  `_guard`, the held-for-merge helpers, `PUBLISHED_REF` and pending
  bookkeeping, `state_sweep_withheld` / `control_relay_started` if they have
  no remaining readers, `sync_failure_report` and `record_sync_failure`. That
  belongs to `git-sync/03`. Unread symbols may remain after this ticket, but
  no caller outside `git.py`/`sync.py` may use the publication ones.
- Rehoming trim-log onto `coga sync` (decision 10, Open Question 2).
- Simplifying the `pending:`/`released:` generation grammar in `ticket.py`.
  Readers keep recognizing the legacy forms.
- Any `coga launch --sync` convenience, or an auto-sync at launch entry
  (Open Question 1).
- Changing `coga sync`'s own contract beyond the `subject` keyword and the
  two helpers above.

## Context

### Inventory of implicit publication (design-time, 2026-11-17)

Line numbers drift and are given only for navigation.

- **CLI.** `cli._sweep_coga_state` → `git.sync_coga_state`. The sweep set is
  `_SWEEPING_COMMANDS` / `_SWEEPING_SKILL_SUBCOMMANDS` /
  `_SWEEPING_MARK_SUBCOMMANDS`. `_warn_unpublished_log_lines` warns about
  unpublished log lines.
- **Launch (`launch.py`).**
  - `_CheckoutBoundary.enter` calls `sync_coga_state("Sync coga state before
    launch")` before `git.prepare_control_checkout`. `settle` calls
    `sync_coga_state("… before checkout return")` before preparation.
    Preparation refuses any unproven dirty Coga path ("uncommitted changes
    would be lost"; `git._plan_preparation`). That is why removing the
    pre-sweep yields decision 1 for free.
  - `_publish_startup` makes the guarded `git.publish` of ticket + log
    before spawning. `_prepare_step_checkout` calls
    `git.sync_log("Log: <slug>")`.
  - The released-admission reconciliation publishes "Ticket: reconcile
    released launch admission".
  - The `spawn_agent_session` teardown calls `git.sync_log` for stateless
    sessions and `git.retry_session_publication` for task sessions. It is the
    shared session-end point: callers are `launch.py` (supervised steps),
    `megalaunch.py` and `commands/ticket.py`. `coga chat` is the alias
    `launch bootstrap/orient`.
  - `_terminal_status_probe` reads `refs/remotes/<remote>/<control>` when a
    remote exists, because today a lifecycle command publishes. It must
    switch to the local file.
  - `settle_delegated_period` is the recurring runner's settle entry.
- **Megalaunch (`megalaunch.py`).**
  - `_publish_partial_dependency_resolution` and the deferred activation
    (`mark_active(sync_state=…)` + strict `sync_task_state`) publish.
  - `_admit_launch_claim_after_release` publishes "Ticket: <slug> — launch
    admitted".
  - `_preflight_agent_launch` picks `pending:<uuid>` only when
    `cfg.git_enabled`. `_revalidate_launch_claim_before_spawn` and
    `_admit_launch_claim_after_release` already return early when Git is
    disabled. That is decision 6's target behavior.
  - `commands/megalaunch.py` calls `git.refresh` first.
- **Recurring runner (`recurring_runner.py`).**
  - `sync_task_state` "Ticket: <slug> — recurring create" runs when the
    template dir is missing. The period-creation `git.publish` calls use
    `expect=` / `guard=` (`refuse_if_serviced`, `guard_fallback`,
    `guard_log_publication`) against control's ledger.
  - The control leases are `_revision_period_lease`,
    `_revision_parent_state_lease` and the control-lease check that calls
    `git.fetch_control` at boundaries.
  - Entry points are `run_recurring_all_repos` → `_run_repo_recurring`,
    `run_recurring_scan`, `run_recurring_named`, and
    `_service_from_control_worktree` (temp control worktree when the host is
    off control).
- **Lifecycle.**
  - `bump.advance_step` (inner `sync_state`, strict for rewinds).
  - `mark._publish` serves `mark_done` (which also bundles the recurring
    parent `ticket.md`), `mark_active`, `mark_in_progress` and
    `mark_paused`. `mark_canceled` and `mark_blocked` call `sync_task_state`.
  - `commands/create.py`, `commands/delete.py`
    (`fast_forward=not keep_control_checkout`), and `commands/owner.py`
    (strict, restore on failure, `finish_resolution` only after a confirmed
    publish).
  - `commands/unblock._apply_unblock`.
  - `commands/recurring.py` (`promote` publishes; `list_recurring` toggles
    `state_sweep_withheld`).
- **Other publishers.**
  - `branchsweep.py`: worklist `git.publish` with `expect` and
    restore-on-failure.
  - `recurring_autofix.py`: "Autofix: … — created".
  - `blocker_reminders.py`: "— blocker reminder".
  - `checkouts._publish_linkage`: strict branch-linkage publish, followed by
    a control re-read.
  - `launch_script.py`: `sync_log` before the script, an assist
    `sync_task_state`, and a re-derivation after the "moving sync".
  - `authoring.finalize_authored`: one guarded transaction.
  - `publish_state.py`: the recipe.
  - `bootstrap/retire/ticket.py`: create, block, then in-process `launch`,
    and the delete publish.
  - `coga_edge/phone_home.py`: "Telemetry: reserve weekly snapshot" with
    `expect`.
  - `coga_edge/trim_log.py`: archive and trim publishes with
    `log_transaction` receipts and guards (decision 10).
- **Docstrings only.** `github_preflight.py` and `notification/__init__.py`.
- **Already gone.** The related tickets named at design time,
  `fix-git-sync-failure` (canceled) and the done tickets
  `hold-dirty-context-edits-on-feature-checkouts-unti` and
  `correct-state-publication-internals-for-pending-pu`, need no action.
  Their behavior (held for merge, pending expectations) is what this project
  removes.

### Tests that assert implicit publication

An AST scan for publication markers flags roughly 420 test functions as an
upper bound. The heaviest files are `test_git.py` (~143; mostly 03's
territory, but `sync_coga_state` sweep tests go here), `test_recurring.py`
(~55, `origin_tracks` / `push_competing_commit`), `test_checkouts.py` (~43),
`test_launch.py` (~37), `test_authoring.py` (~19), `test_launch_script.py`
(~15), `test_megalaunch.py` (~15), `test_open_pr.py` (~13),
`test_review_conflict.py` (~12), `test_trim_log.py` (~11) and
`test_cli.py` (~10). Lighter ones are `test_mark.py`,
`test_publish_state.py` (delete it), `test_validate.py`, `test_owner.py`,
`test_branchsweep.py` and `test_recurring_activity.py`. `conftest._stub_git`
stubs `publish`, `sync_task_state`, `sync_log`, `retry_session_publication`,
`sync_coga_state`, `prepare_ticket` and `refresh`. `GitRepo.origin_subjects`,
`origin_tracks` and `push_competing_commit` are the remote assertions to
repoint at `coga sync`.

### Doc sweep

Run `grep -rln -i 'sweep\|publish-state\|held for merge\|end-of-command\|publishes'
src/coga/resources docs/contexts --exclude-dir=archive`. At design time this
matched about 80 shipped files: 47 topics under
`templates/coga/bootstrap/contexts/coga/`, the step skills `code/implement`,
`code/open-pr`, `code/merge-pr`, `code/address-pr-comments`,
`code/self-qa` and `code/design`, the `bootstrap/*` skills (`import`,
`ticket`, `skill-update`, `dream/scan/*`), `coga/*` skills (`autoclose`,
`blockers/remind`, `branch-sweep`, `recurring/verify`, `releasing`,
`ticket/finalize`), the recurring `ticket.md` / `operations.md` files, and
`resources/{prompt-queue,retire}.md`. `compose.py` and `status/ticket.py`
print `publish-state` remedies. "Publishes" also matches unrelated PR
publication, so check each hit.

### Project decisions (owner, 2026-11-17)

These apply to the whole `git-sync/` project (01 → 02 → 03):

- **Publication is explicit everywhere.** No command auto-publishes, including
  lifecycle transitions (`bump`, `block`, `mark`, `create`, launch audit
  lines). Their writes reach other checkouts only when `coga sync` runs, called
  by a human, an agent, or the session end.
- **`coga sync` is the only publication path.** It commits the Coga state
  directory (`coga/`, plus the contexts root if configured outside it), fetches
  main, pushes that state to main, and rebases the current branch onto main.
  When the rebased branch has already been pushed, it force-pushes
  automatically with `--force-with-lease`.
- **State goes to main from any checkout.** On a feature checkout, Coga state
  is still pushed straight to main while code stays on the branch. The current
  held-for-merge behavior is dropped.
- **No atomic-publish exception for megalaunch/recurring admission claims**
  (`launch_generation`). Tickets have an owner, so the owner rejected
  protecting cross-clone admission races with an exception.
- **End state: `src/coga/git.py` becomes trivial.**
- This deliberately reverses the current `coga/sync` invariant that Git
  publication happens "without committing on a local branch, stashing, or
  rebasing". Say so in the topics you rewrite.

Origin: the end-of-command sweep (`git.sync_coga_state`) publishes every
dirty eligible file on control, including definition edits, so a fork command
would publish a byte-identical override that silently stops following package
updates (`v1/microkernel/05-make-packaged-behavior-discoverable-and-editable`).

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
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
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

## Design notes (design step, 2026-11-17)

The spec is under `## Description` (ten decisions, acceptance criteria,
proposed shape, out of scope) and `## Context` (caller inventory, tests and
doc sweep). How it was derived:

- The inventory was taken by grep plus a read of each call site. A subagent
  covered the non-supervisor callers. Its key findings are folded into the
  spec: owner `finish_resolution`, the retire in-process launch, trim-log,
  the `refresh` failure with a dirty log, and the cross-clone compare-and-swap
  sites.
- **Start-clean is the load-bearing decision.** The session-end sync commits
  the whole roots, so without it every supervisor would publish pre-existing
  human dirt. Launch gets the refusal for free from `_plan_preparation`.
- **Megalaunch has a complete Git-disabled claim path already**, so
  decision 6 is "always take it", not new code.
- Dependency: 01 is still at review-design, and its evaluator asked for
  revisions. 02 relies only on `run_sync(cfg) -> result with exit_code`
  0/1/2 and its stage output, plus the `subject` keyword and two helpers that
  02 adds. If 01's contract changes, recheck decisions 3, 4 and 7.
- Related tickets: all three are already canceled or done. Nothing to fold.

## Open Questions

1. **Launch entry: refuse or sync?** The spec refuses to start any supervisor
   on unsynced Coga state, so `coga create x && coga launch x` needs a
   `coga sync` in between. The alternative is for launch entry to run
   `coga sync` itself, because the human invoked it. That is smoother, but it
   silently publishes unrelated edits, including fork overrides, which is the
   origin problem. A `--sync` flag is a possible middle ground. Which one?
2. **Trim-log.** Keep its own guarded `git.publish` as the single named
   exception until a follow-up rehomes it onto `coga sync`, as the spec does?
   Or must 02 rehome it? Rehoming means sync → trim locally with the
   `log_transaction` receipt → sync, and making sure ticket 01's sync honors
   pending receipts, which 01's evaluator already flagged.
3. **Inactivity subject.** Is `Sync coga state: recurring` acceptable as the
   machine marker (decision 7)? It needs a keyword on `run_sync`, so ticket 01
   should know. The alternative is classifying a landing commit as machine
   activity when it touches only `tasks/recurring/**`, the log and recurring
   runtime siblings.
4. **Cross-clone exclusion is now best-effort for things beyond admission.**
   This covers the branch-sweep `retires.md` worklist, the blocker-reminder
   watermark (duplicate Slack reminders across clones), autofix duplicate
   detection, the phone-home weekly reservation, and branch linkage. They
   become local writes and merge or conflict at sync. The spec reads the
   owner's "no exception" decision as covering all of them. Confirm.
5. **PR size.** The doc sweep touches about 80 shipped files, and about 400
   tests need edits. Keep it as one PR (repo rule: the owner topic changes in
   the same PR), or split the docs-only follow-through into a sibling ticket
   that merges back-to-back?
