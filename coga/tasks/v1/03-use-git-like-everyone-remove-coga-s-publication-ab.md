---
title: 'Use Git like everyone: remove Coga''s publication abstraction'
status: in_progress
owner: nicktoper
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
---

## Description

Coga stops abstracting Git: no control branch, no automatic publication or sweep, no locks. Branch creation and PR become workflow script steps; the launch kernel no longer knows Git. Owner decisions from the 2026-11-19 chat are recorded below.

This is not the microkernel group: the microkernel decides where behavior
lives (kernel vs ticket); this ticket stops abstracting Git. It supersedes
the parts of `v1/microkernel/` and `v1/why-is-the-code-so-big` that move or
polish publication, checkout, sweep and claim machinery.

### Target model: three orthogonal layers

The new system separates three concerns that today's launch fuses. Each can
change without touching the others.

1. **The kernel runs tickets.** It reads the ticket once per step, picks the
   step's executor, runs it, and records status and step in the ticket file.
   That is all. It knows nothing about Git, branches, PRs, remotes or
   publication, and it takes no locks: the ticket's owner is its single
   writer.
2. **Executors decide how a step is computed.** A step is a **script**
   (`ticket.py`: deterministic, one computation, zero tokens), an **agent**
   (an LLM session, for judgment), or **text** for a human. Deterministic by
   default; call an agent only where judgment is needed. The documented
   hybrid (`coga/script-tickets` "Chaining": a script that leaves its step
   open hands it to the agent) stays. A failure is not repaired inside the
   ticket: it becomes another ticket. Script and agent present the same
   shape to the kernel (environment, spawn, exit status); Windows and
   terminal specifics stay inside the agent executor.
3. **Version control is plain Git, outside Coga.** Humans and agents use
   `git` as in any repo. Coga's files are ordinary files in the checkout:
   on a branch, the ticket's state travels with the code and reaches main
   through the PR. Branch and PR helpers exist only as workflow script steps
   (for example `open-branch` first, `push-and-open-pr` last); a workflow
   without them, such as a recurring job, simply commits where it runs, or
   not at all. Coga would work in a directory without Git. `coga/log.md` is
   append-only, so its conflicts resolve by keeping both sides.

Failure rule across all three layers: **stop simply**. When something is
not clean (a Git conflict, a failed push, a script error), stop, keep local
state, say what happened. Recovery is a human or agent act, never kernel
machinery.

Example workflow under this model:

    1. script  open-branch        git switch -c <ticket>
    2. agent   implement
    3. agent   review
    4. script  push-and-open-pr   git push; gh pr create

What disappears: the control branch, automatic publication and the
end-of-command sweep, `prepare-checkout`, per-step `checkout:` policy, claims, generations and leases, byte-guarded
publication and retraction, exit-75 threading, blocked re-parking, the
terminal-status probe and done sentinel (session ends itself), the
one-session-per-checkout guard, and `git.py`.

### Owner decisions (2026-11-19)

1. **Git like everyone.** No control branch, no automatic publication, no
   end-of-command sweep, no `prepare-checkout`. Launching a ticket creates
   (or reuses) its branch; work and ticket state live there; the end is a PR.
   Forgetting to push is the human's (or agent's) problem, as with any Git
   use. A `coga sync` command is probably unnecessary.
2. **Branch and PR are workflow steps**, e.g. a script step that opens the
   branch and a script step that pushes and opens the PR. The kernel does not
   know Git. Workflows without such steps (recurring, script-only, text)
   simply commit where they are, or not at all.
3. **The owner is the ticket's single writer: no locks.** Drop the megalaunch
   claim transaction (`pending/admitted/released` generations, held-child
   admission, released-witness reconciliation, byte re-checks), the recurring
   period lease, and `expect`-guarded ticket publication. A crash between
   status write and spawn "is not supposed to happen": the human relaunches.
4. **Fail-stop, no automatic recovery.** If a Git operation is not clean,
   stop, keep local state, say so. No retraction, no uncertain-push
   retention, no exit-75-plus-withheld-sweep threading.
5. **`coga/log.md` is append-only**: resolve its conflicts by keeping both
   sides (union). It is the one genuinely shared file.
6. **Launch never touches `blocked`.** A launch on a blocked ticket starts
   the session with the resolve preamble and leaves the status `blocked`;
   `coga unblock --answer` moves it to `in_progress` while a session runs. A
   session ending without an answer leaves it blocked: nothing to re-park.
   No `ticket.py` runs on a blocked ticket.
7. **One ticket read per step**, one environment-isolation function, Windows
   specifics confined to the agent executor (kept from today).
8. **A ticket is a script, an agent, or text (MD).** The documented hybrid
   chaining (`coga/script-tickets` "Chaining") stays. A failure does not
   escalate inside the ticket: make another ticket.
9. **Git is outside the kernel; `git.py` disappears.** Coga could in
   principle run without Git at all. Git helpers that speed things up are
   workflow steps (scripts), never kernel code. There is no `coga sync`
   command: syncing is `git pull` / `git push`. The `git-sync/` group (01 add
   `coga sync`, 02 automatic sync at session end, 03 shrink `git.py`) was
   canceled on 2026-11-19 as a trap that kept the two-destination model;
   03's goal is absorbed here as "delete `git.py`".
10. **The per-step `checkout:` field goes**, with `checkout_policy.py`,
    `checkouts.py` and launch's `_prepare_step_checkout`. Opening a branch
    is a command or script a workflow may use, never an obligation of the
    model. `v1/microkernel/18-retire-the-legacy-checkout-policy…` was
    canceled as moot.
11. **No one-session-per-checkout guard.** Drop the chat guard (the
    toplevel-keyed `flock`, chat receipt, `checkout_guard_scope`,
    `_orientation_checkout_guard`) and launch's "occupied checkout" checks.
    Two sessions in one checkout are the human's business, as with two
    editors on one repo. Session end no longer needs a per-checkout channel
    (see the script-or-agent ticket).

### Documentation

`coga-dev/principles` gained "Deterministic by default" and "Use tools
plainly" and a stop-simply clause in "Fail loud" on 2026-11-19, ahead of
implementation. Align the README with them in this ticket's implementation
PR, not before, so first users never read about behavior that does not
exist yet. Rewrite or delete the user topics that describe today's
publication model (`coga/checkouts`, `coga/state-publication`, `coga/sync`,
`coga/checkout-cleanup`, the base prompt's checkout and reconciliation
sections) in the same PR. Also fix the stale ticket ref in
`src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md`:
`v1/44-verify-the-macos-full-suite-procedure-on-the-ec` is now
`v1/11-verify-the-macos-full-suite-procedure-on-the-ec` (renumbered
2026-11-19).

### Design decisions (owner, 2026-11-20 design chat)

12. **One implementation PR.** The frozen workflow's single `implement`
    step delivers the whole change; docs and README land in the same PR.
13. **Branch and PR are `run:` steps.** A workflow step may declare
    `run: <name>`; that step is executed by a script, not an agent (see
    Proposed shape §3). This settles the earlier "workflow step vs
    ticket-level" question in favor of the workflow. Ticket
    `v1/04-script-or-agent…` may later fold `run:` into its single executor
    model.
14. **Delete control-dependent branch hygiene**: branch sweep, branch
    cleanup, checkout disposal, the retire worklist and autoclose. Cleaning
    branches is plain `git branch -d` / `gh`.
15. **The owner's final bump on the branch marks the ticket done.** The
    commit carrying `status: done` reaches main with the PR merge. Nothing
    closes tickets in the background.

### Acceptance criteria

Kernel without Git:
- [ ] `src/coga/git.py` is deleted, and so are `publish_state.py`,
      `state_sweep.py`, `log_publication.py`, `log_transaction.py`,
      `checkouts.py`, `checkout_policy.py`, `checkout_disposal.py`,
      `claimed_session.py`, `review_conflict.py`, `branchsweep.py`,
      `branchcleanup.py`, `retire_worklist.py`, `autoclose.py` and
      `open_pr.py`. `rg -n "coga\.git\b|from coga import git|from \.git import" src tests`
      finds nothing.
- [ ] No module under `src/coga/` (package core, not `resources/` or
      `coga_edge/`) runs a `git` or `gh` subprocess, except
      `skill_manager.py` installing a skill from a Git URL (Git used as a
      download tool, single consumer, inlined there).
- [ ] In a temporary directory with **no `.git`**, `coga init`, `coga
      create`, `coga mark active`, `coga launch` of a `run:`-only workflow,
      `coga bump`, `coga block` and `coga unblock --answer` all succeed. A
      test covers this sequence.
- [ ] No command commits, pushes, fetches or switches branches by itself.
      The end-of-command sweep (`cli.main` → `_sweep_coga_state`) and
      `runner._publish_after` are gone. A test asserts that `git status`
      after `coga bump` shows the ticket and `coga/log.md` modified and
      nothing committed.
- [ ] Exit code 75 has no Coga meaning: `RETRY_WITHOUT_SWEEP_EXIT_CODE`,
      `STALE_CONTROL_EXIT_CODE`, `state_sweep_withheld` and
      `control_relay_started` no longer exist.
- [ ] `runner.RECIPES` no longer lists `publish-state`, `prepare-checkout`,
      `branch-sweep`, `autoclose` or `open-pr`, and gets no forwarding
      entries.

Lifecycle writes:
- [ ] `bump`, `mark`, `block`, `unblock`, `owner`, `create` and `delete`
      read the local ticket, compute, and write it atomically
      (`atomicio`). There is no three-way merge with a control copy
      (`prepare_ticket`, `PreparedTicket`, `merge_ticket_bytes`,
      `lifecycle_winner`, `TicketConflictError`, `TicketChangedError` and
      `expect=` guards are gone).
- [ ] `state_lock` is gone. `logfile.append_log` appends with one
      `O_APPEND` write.
- [ ] The `launch_generation` and `period_generation` frontmatter fields
      are no longer written, read or validated as known keys. `coga
      validate` reports a leftover one as an `obsolete-key` warning, not an
      error. This repo's tickets that carry them are cleaned in the same
      PR.

Workflows:
- [ ] The per-step `checkout:` key is no longer parsed, frozen or
      validated as a policy. In a frozen snapshot it is ignored and `coga
      validate` warns `obsolete-key`, so live tickets keep launching.
      `Workflow.freeze` does not write it.
- [ ] `WorkflowStep` has an optional `run:`. Launch executes the named
      script for that step (§3). A `run:` step whose resolved role is
      `owner` is a `bad-shape` validation error.
- [ ] Packaged skills `git/open-branch` and `git/push-and-open-pr` exist,
      each with a `run.py`, and are listed in
      `tests/required_package_resources.txt`.
- [ ] Packaged `code/with-review`, `code/with-self-review`,
      `code/agent-merge`, `code/design-then-implement` and
      `docs/with-review` start their branch work with an `open-branch` `run:`
      step and open the PR with a `push-and-open-pr` `run:` step. None of
      them declares `checkout:`.
- [ ] `requires: branch|pr` gates still work unchanged. They read
      `## Dev` text only.

Launch:
- [ ] Launch never changes branches or refuses because of checkout state:
      `_prepare_step_checkout`, `_CheckoutBoundary`, `return_checkout`,
      `_manages_branch_checkout`, `_checkout_exemption` and the checkout
      refusal messages are gone. The composed prompt no longer has a
      "Checkout (runtime)" layer.
- [ ] There is no chat guard: `checkout_guard_scope`,
      `_orientation_checkout_guard`, `_CHAT_SESSION` and the
      chat-receipt/flock machinery are gone. Two `coga chat` sessions in one
      checkout both start.
- [ ] Megalaunch launches its picks in sequence without claims. The
      pending/admitted/released transaction, the held-child gate in
      `repl_supervisor.py`/`repl_supervisor_nt.py`
      (`_admit_held_child`, the gate fd) and released-witness
      reconciliation are gone.
- [ ] Recurring has no period lease and no control relay: `PeriodLease`,
      `_ParentStateLease`, `_verify_period_on_control`,
      `_relay_to_control_worktree`, `_ControlWorktreeOwner` and its reaping
      are gone. The due scan and ledger read local files in the current
      checkout.
- [ ] **Blocked:** `coga launch` on a `blocked` ticket with a TTY starts
      the agent with the blocker-resolution preamble and leaves `status:
      blocked`. Without a TTY it refuses as today. It never runs
      `ticket.py` or a `run:` script on a blocked ticket; that case refuses
      with "answer with `coga unblock --answer`". After the session ends,
      nothing re-parks the ticket (`reblock_unresolved_resume`,
      `reblock_after_script`, `should_reblock_after_script`,
      `_park_unanswered_resume` and megalaunch `_reblock_unresolved` are
      gone).
- [ ] `coga unblock --answer` on a `blocked` ticket moves it to
      `in_progress` when run inside a launched session for that ticket
      (the `COGA_TASK_*` environment names it), and to `active` otherwise.
      Tests cover both.

Docs, README and packaging:
- [ ] The user topics `coga/checkouts` (all children), `coga/state-publication`
      (all children), `coga/sync`, `coga/checkout-cleanup` (all children)
      and the coga-dev internals listed in Context are deleted. A new short
      user topic `coga/git` owns the plain-Git conventions (§6).
      `REQUIRED_BOOTSTRAP_CONTEXT_REFS` and
      `tests/required_package_resources.txt` match.
- [ ] `src/coga/resources/prompt.md` replaces "Check the starting checkout"
      and "Reconcile before publishing" with one short "Git" section that
      points to `coga/git`. `prompt-ticket.md` loop step 3 and `AGENTS.md`'s
      reconciliation line point to `coga/git`.
- [ ] Every remaining topic, skill, workflow and the ticket template
      (`src/coga/resources/ticket.md`) is free of control-branch,
      publication, sweep, claim, lease and `checkout:` wording. A grep for
      `control branch|publish-state|prepare-checkout|state sweep|checkout:`
      over `src/coga/resources docs/contexts README.md AGENTS.md` finds
      nothing stale.
- [ ] The README matches `coga-dev/principles` ("Use tools plainly",
      "Deterministic by default", "Fail loud").
- [ ] The macOS clean-install skill refers to
      `v1/11-verify-the-macos-full-suite-procedure-on-the-ec`.
- [ ] `python -m pytest` passes and `coga validate --json` reports no
      errors on this repo. The PR lists both commands with their results.

### Proposed shape

Work in this order. Each stage leaves the suite green on the branch, so a
reviewer can read the PR commit by commit.

**§1 Stop publishing (lifecycle goes local).**
- `cli.py`: delete `_sweep_coga_state`, `_should_sweep_coga_state`, and the
  `deferred_done_marker` wrapper that waits for the sweep (the sentinel
  itself stays for `v1/04`). `runner.py`: delete `_publish_after`. Delete
  `state_sweep.py` and `publish_state.py`.
- `bump.py`, `mark.py`, `commands/{bump,mark,block,unblock,owner,create,delete}.py`,
  `commands/common.py`: replace `prepare_ticket`/`PreparedTicket`/
  `sync_task_state`/`write_ticket(prepared=)` with "read the file, build the
  new bytes, `atomicio.atomic_write_bytes`". Delete
  `commands/common.prepare_lifecycle_ticket`'s conflict branch,
  `bail_ticket_changed` and `_refuse_conflict`, and `review_conflict.py`.
- `logfile.py`: drop `retract_log_append`, `retract_log_lines` and
  `replace_log`'s publication receipt. Delete `log_publication.py` and
  `log_transaction.py`. `coga_edge/trim_log.py` rewrites `log.md` locally
  and stops publishing.
- `.gitattributes`: in the package scaffold
  (`src/coga/resources/templates/coga/.gitattributes`) and this repo's
  `coga/.gitattributes`, replace `/log.md -merge` with `/log.md
  merge=union` and drop the `retires.md` line. Keep the twin entry in
  `INTENTIONALLY_DIVERGENT_TWINS` consistent.
- Edge callers of `publish`/`sync_task_state` (`coga_edge/phone_home`,
  `blocker_reminders`, `megalaunch`, `trim_log`; resources
  `recurring-promote/ticket.py`, `retire/ticket.py`, `status/ticket.py`)
  write locally and stop publishing.

**§2 Drop checkout policy and the chat guard.**
- Delete `checkout_policy.py` and `checkouts.py`. In `workflow.py`,
  `_parse_step` stops reading `checkout` (it ignores the key when present),
  `Workflow.freeze` stops writing it, and `CHECKOUT_POLICIES` and
  `DEFAULT_CHECKOUT` go. `validate.py`: the step-shape check warns
  `obsolete-key` for a present `checkout:`.
- `launch.py`: delete `_prepare_step_checkout`, `_CheckoutBoundary`,
  `return_checkout`, `_manages_branch_checkout`, `_checkout_exemption`,
  `_checkout_refusal_message`, `_orientation_checkout_guard`,
  `checkout_guard_scope`, `_CHAT_SESSION` and `_CHECKOUT_GUARD_SCOPE`.
  `compose.py`: delete the `checkout_notice` layer and
  `UNSUPPLIED_CHECKOUT_NOTICE`. The `retire/ticket.py` caller of
  `checkout_guard_scope` goes with it.
- `_terminal_status_probe` (`launch.py`) reads the local ticket file
  instead of the control ref's blob and stops matching
  `period_generation`. Removing the probe itself is `v1/04`'s job.

**§3 `run:` steps, `git/open-branch` and `git/push-and-open-pr`.**
- `workflow.py`: `WorkflowStep.run: str | None`. `_parse_step` accepts a
  non-empty string, `freeze` writes it, and `validate.py` checks that it
  resolves and that the step's resolved role is not `owner`. Resolution
  follows skills: `<name>` is a skill directory resolved local-first then
  package, and its `run.py` is the entry point. This keeps local override
  and package fallback with no new resolver.
- `launch_script.py`: generalize `script_entry_point(ref)` to
  `script_entry_point(ref, ticket)`. If the current frozen step has `run:`,
  return that skill's `run.py`; otherwise return the ticket's `ticket.py`
  as today. Update its callers in `launch.py` (`_run_initial_script`,
  `_supervise_steps`) and the re-stat in `run_script_chain`. Environment,
  `system` attribution, gates and the "Chaining" rules are unchanged: a
  `run:` script that bumps chains to the next step, and one that leaves the
  step open hands it to the agent.
- `git/open-branch/run.py` (edge, imports only shared core infra): if
  `## Dev` already records `branch:`, run `git switch <branch>`. Otherwise
  derive the name from the ticket slug (move `checkouts._fresh_branch_name`
  logic here), run `git switch -c <branch>` from the current HEAD, and
  record `branch:` with the existing `## Dev` writer
  (`insert_branch_line`). Then `coga bump`. Any non-zero `git` exit:
  print Git's message and exit non-zero without bumping (fail-stop).
  Uncommitted changes travel under Git's own rules.
- `git/push-and-open-pr/run.py`: require `## Dev` `branch:` to equal the
  current branch. Commit the ticket and `coga/log.md` if modified, run
  `git push -u <remote> HEAD`, and create the PR with `gh pr create` (or
  `gh pr view` when one exists), building the body from `## PR` evidence by
  moving `open_pr._pr_presentation`/`_receipt` here. Then record `pr:`
  (`set_dev_pr`) and `coga bump`. Remote: the branch's upstream, else
  `origin`. Drop open_pr's control gates (`_checkout_mode`,
  `github_preflight.check_branch_contains_control`, the stale-branch checks).
- Workflows: `code/with-review` becomes `open-branch` (run, agent) →
  `implement` (agent, requires branch) → `peer-review` (other-agent) →
  `push-and-open-pr` (run, agent, requires pr) → `review` (owner). Apply the
  same shape to `code/with-self-review`, `code/agent-merge` (its `merge`
  step stays an agent step), `code/design-then-implement` (design steps
  first) and `docs/with-review`.
- Skills: `code/implement` drops "launch prepared the branch" and
  freshness against control. If `## Dev` has no branch (legacy frozen
  snapshot), it runs `git/open-branch`'s script first. `code/open-pr` stays
  as a thin agent skill that runs `git/push-and-open-pr`'s script, so live
  tickets frozen with an agent `open-pr` step still work. `code/peer-review`,
  `self-qa`, `merge-pr`, `address-pr-comments`, `bootstrap/orient/ticket.md`
  and `docs/with-review`: drop the "Checkout (runtime)" references.

**§4 Drop claims, leases and blocked re-parking.**
- Delete `claimed_session.py`. `launch.py`: delete the
  `run_claimed_agent_session` re-export, `_reconcile_released_launch_admission`,
  the pending/released refusal in `_launch`, and the `after_spawn`/
  `spawn_release_guard`/`after_spawn_release`/`on_spawn_admission_failure`
  hooks that `spawn_agent_session` passes to `run_with_done_marker`.
  `repl_supervisor.py`/`repl_supervisor_nt.py`: delete the held-child gate.
  `ticket.py`: delete the `launch_generation` helpers and prefixes.
  `mark.py`/`bump.py`/`commands/owner.py`: stop popping or checking it.
- `coga_edge/megalaunch.py` `_launch_until_stop`: for each pick, read the
  ticket, `resolve_operator`, activate or mark `in_progress`, then
  `spawn_agent_session`. Delete `_restore_after_failed_start`, the `expect=`
  in `_publish_partial_dependency_resolution` and `_drain_satisfied_blockers`,
  and `_activate_for_launch`'s claim path. Keep selection, ordering, drain
  and summary.
- Recurring: delete the lease in `recurring.py` (`PeriodLease`,
  `period_generation_from_ticket_bytes`, `local_period_lease`,
  `same_period_lease`) and in `recurring_runner.py` (`_ParentStateLease`,
  `_revision_period_lease`, `_local_parent_state_lease`,
  `_revision_parent_state_lease`, `_verify_period_on_control`,
  `_require_period_bytes`, `_restore_period_bytes`, `admitted_period_leases`,
  `confirm_control_lease`), plus `launch.py`'s `capture_launched_period_lease`,
  `_refresh_recurring_period_before_launch`, `_exact_recurring_period_for_launch`
  and the `expected_period_lease` parameters. Delete the control relay
  (`_relay_to_control_worktree`, `_ControlWorktreeOwner` and its read/write/
  reap, `_control_already_has_period` → local ledger,
  `_control_remote_present_at_admission`, `_sweep_stopping_exit`).
  `recurring --all` runs each repo in its current checkout.
  `workspace_discovery.py` drops the `CONTROL_WORKTREE_*` markers.
  `period_state.py` (state-key snapshots) stays.
- Blocked (decision 6): in `_launch`, a blocked ticket keeps
  `blocked_resume` and composes the preamble (already keyed on open asks in
  `compose._blocker_preamble`), but skips `_auto_activate` and the
  `in_progress` flip. The script branch refuses on `blocked`.
  `commands/unblock._apply_unblock`: `blocked` → `in_progress` when
  `COGA_TASK_*` names this ticket, otherwise `mark_active`. Delete the
  re-park functions listed in the acceptance criteria.

**§5 Delete git.py and control-dependent Git helpers.**
- Replace the remaining non-publication uses: `toplevel`/`relative_to_root`
  → `config.find_checkout_root`/`find_repo_root` or `pathlib`;
  `symlink_component` → a `paths.py` helper; `is_linked_worktree` → its
  callers go with the deleted modules; `views` drops the
  `last_commit_times` fallback and uses `logfile.last_activity_map`; the
  `status` bootstrap ticket drops `stale_coga_task_rels`,
  `feature_sync_plan` and `stale_index_lock`; `skill_manager` inlines its
  one `git ls-remote`-style call and `_git_env`.
- `commands/init.py`: write the files and print "commit `coga/` when ready".
  Drop the commit, the git-identity probe, `control_branch_present`/
  `symbolic_head` and `_render_git_control_branch_table`. `init` works in a
  non-Git directory.
- `config.py`: delete `_parse_git`, `_resolve_git_enabled`,
  `git_control_branch` and `worktrees_ticket_owned`. A `[git]` table in
  `coga.toml`/`coga.local.toml` loads with an `obsolete-key` warning from
  `coga validate`.
- Delete `branchsweep.py`, `branchcleanup.py`, `checkout_disposal.py`,
  `retire_worklist.py`, `autoclose.py`, `open_pr.py`, the
  `branch-sweep` and `autoclose-merged` recurring templates, workflows
  (`branch-sweep/sweep`, `autoclose-merged/sweep`) and skills, and
  `github_preflight`'s control-drift helpers (`check_branch_contains_control`,
  `coga_root_prefix`, `is_coga_state_path`). `retire/ticket.py` retires
  ticket files only. `pr_assist.py`: drop `verify_recorded_assist_pr_head`'s
  `autoclose.pr_view` dependency, or delete the module if nothing else
  needs it. Then delete `git.py`.
- `coga-dev/microkernel` "Open command placements" and
  `runner.RECIPES` lose the deleted entries.

**§6 Docs and README.**
- New user topic `coga/git` (about 60 lines). Coga's files are ordinary
  files. A code workflow opens a branch with `git/open-branch`, and the
  ticket state travels on that branch. `push-and-open-pr` opens the PR. The
  owner's final `coga bump` (done) is committed on the branch before the
  merge. `coga/log.md` merges by union. Pushing, pulling and cleaning
  branches are plain `git`/`gh`. When Git is not clean, stop and say so.
  Fold the useful part of `coga/checkouts/reconciliation` (rebase on the
  base branch, preserve unique work) into it.
- Delete the topics listed in Context. Edit-pass the topics that mention
  the model in passing (listed in Context). Update `coga/workflows` for
  `run:` and `coga/script-tickets` for step scripts. Rewrite
  `coga/pr-publication` around `push-and-open-pr`.
- README: align with the principles. AGENTS.md: point the reconciliation
  line at `coga/git`. Fix the macOS skill's stale ref.

**§7 Tests and fixtures.**
- Delete `tests/test_git.py`, `test_checkouts.py`, `test_branchsweep.py`,
  `test_branchcleanup.py`, `test_publish_state.py`,
  `test_autoclose_dispose.py`, and `test_autoclose_sweep.py` if it covers
  the deleted autoclose. Cut the claim, lease, sweep and publication cases
  from `test_megalaunch.py`, `test_recurring.py`, `test_launch.py`,
  `conftest.py`, `test_cli.py`, `test_authoring.py`, `test_launch_script.py`,
  `test_runner.py`, `test_trim_log.py`, `test_mark.py`, `test_retire*.py`
  and `test_period_state.py`/`test_recurring_state.py` where they cover
  leases.
- New tests: the no-`.git` lifecycle sequence; `run:` parse/freeze/
  validate/launch (script bumps → chains; script leaves the step open →
  agent; owner-role `run:` rejected); `open-branch` creates or reuses and
  fails stop on a Git error; `push-and-open-pr` with `gh` stubbed; blocked
  launch keeps `blocked`; `unblock --answer` in-session vs out of session;
  `obsolete-key` warnings for `checkout:`, `launch_generation`,
  `period_generation` and `[git]`.
- Seeded fixture `tests/fixtures/seeded-repo/coga/`: update its workflows
  to the new shape. Keep `deterministic/check.md` working.

### Out of scope

- Launch's single step loop, executor shape, mode flags, the done
  sentinel, the terminal probe's removal and `coga exit`: all `v1/04`.
- Reworking the script/ticket model beyond adding `run:`.
- A `coga sync` command (decision 9: none).
- Canceling or rescoping `v1/microkernel/*` and `v1/why-is-the-code-so-big`
  tickets. The owner decides; the blackboard lists candidates.
- Committing or pushing recurring-job output. Recurring workflows write
  the working tree; adding a commit `run:` step to one is a later choice.
- Branch cleanup automation of any kind.

## Context

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

### Codebase facts (design survey, 2026-11-20, main at 45aeecd86)

These are symbols, not line numbers. Re-grep before relying on any of them.

- **git.py importers.** About 45 modules import `coga.git`: core modules,
  `commands/*`, `coga_edge/{blocker_reminders,megalaunch,phone_home,trim_log}`,
  and the resource scripts `recurring-promote/{ticket,promotion}.py`,
  `retire/ticket.py` and `status/ticket.py`. Run `rg -l "coga.git import|from coga import git" src`
  for the live list.
- **Non-publication helpers in git.py with callers that survive.**
  - `state_lock` is an OS file lock used by `logfile`, `blackboard`,
    `validate`, `recurring_state`, `delete_task` and `commands/owner`. It
    is deleted (§1).
  - `write_ticket` is an atomic write plus a CAS. It is replaced by
    `atomicio`.
  - `toplevel`, `relative_to_root`, `symlink_component` and
    `last_commit_times` (in `views`) are covered in §5.
  - `union_merge_paths` is used by `open_pr` only.
- **Sweep and publish call sites.** `cli.main` → `_sweep_coga_state` →
  `state_sweep.sweep_root` → `git.sync_coga_state`. `runner.run_reported`/
  `run_entry` → `_publish_after` does the same for recipes and every
  `coga_edge` entry. In-command publishes go through `sync_task_state`/
  `publish` in `bump`, `mark`, `commands/{create,owner,unblock,delete}`,
  `launch` and `recurring_runner`. Exit 75 is threaded through about 75
  references in 21 files, most of them in `launch.py`, `cli.py` and
  `recurring_runner.py`.
- **Lifecycle merge with control.** `git.prepare_ticket` returns a
  `PreparedTicket` after a three-way merge against the control copy. Its
  consumers are `bump`, `mark`, `commands/{common,bump,mark,unblock,block}`,
  `autoclose` and `review_conflict`. Removing it is what makes lifecycle
  writes local.
- **Checkout policy.** `workflow._parse_step` validates `checkout` against
  `checkout_policy.CHECKOUT_POLICIES`, and `Workflow.freeze` always writes
  it. `launch._supervise_steps` → `_prepare_step_checkout` →
  `checkouts.select_ticket_policy`/`plan_ticket_checkout`/
  `enter_ticket_checkout`. Branch creation today is the private
  `checkouts._reserve_and_create`/`_fresh_branch_name` plus
  `insert_branch_line`.
- **Gates.** `step_gate.STEP_GATES` holds `branch` → `_has_branch_linkage`
  and `pr` → `_has_pr`. Both parse `## Dev` text through `autoclose`'s
  `parse_branch_name`/`parse_pr_url`, so move those two parsers into
  `step_gate.py` (or `blackboard.py`) before deleting `autoclose.py`.
  Gates are enforced only for forward bumps in `commands/bump.py`.
- **Script phase.** `launch_script.script_entry_point(ref)` looks only for
  `<task_dir>/ticket.py`. `run_script_phase` spawns
  `[sys.executable, ticket.py]` with `COGA_TASK_*` and `COGA_SCRIPT_TASK`.
  `_classify_script_handoff` implements Chaining and never runs a script on
  an owner-held step. `bump`/`mark done` credit `system` when
  `COGA_SCRIPT_TASK` matches. Valid assignee roles are `owner`, `agent` and
  `other-agent`, so a `run:` step needs an agent role to be launchable.
- **Blocked today.** `_launch` sets `blocked_resume` on a TTY. The script
  branch auto-activates `{"draft","paused","blocked"}` and then
  re-blocks via `should_reblock_after_script`/`reblock_after_script`. The
  preamble comes from `compose._open_asks` + `_blocker_preamble`
  (`prompt-blocker-resolution.md`), keyed on open asks, not on status.
  `commands/unblock._apply_unblock` sends `blocked` → `mark_active`; on
  `in_progress` it resolves the asks only.
- **Done sentinel entanglement.** `cli.py` wraps the sweep in
  `deferred_done_marker`, `.pending-<pid>` protects a command that is still
  publishing, and `_terminal_status_probe` reads the control ref through
  `git._blob_oid`/`_blob_bytes`/`_parse_ticket` and matches
  `period_generation`. §2 keeps the sentinel but rebases the probe on the
  local file.
- **Fields to clean in this repo.** `launch_generation:`/
  `period_generation:` appear in `coga/tasks/recurring/*/ticket.md` and
  `coga/tasks/fix-the-windows-aws-walk-step-and-add-the-v1-14-at.md`.
  `coga/coga.toml` has a commented "Git sync" block documenting `[git]`.
- **User topics to delete** (under
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/`):
  `checkouts/` with `reconciliation`, `launch-boundary`, `chat`, `manual`
  and `sandbox-clone`; `state-publication/` with `launch-boundaries`;
  `sync/`; `checkout-cleanup/` with `branch-sweep` and `terminal-owners`.
  If `sandbox-clone`'s seeding of `coga.local.toml`/`.coga/` is still
  needed, move that part into `coga/sandboxes`.
- **User topics to rewrite:** `pr-publication` (and `preparation`, lightly).
- **User topics to edit for passing mentions:** launch, workflows,
  lifecycle, megalaunch, tickets (+authoring), recurring (+scheduling,
  autofix, delegation, templates, inactivity), configuration,
  architecture, cli, first-task, human-assist, blackboard, uninstall,
  prompt-composition, sandboxes, important, usage, script-tickets,
  notifications/producers, context-layout, extension-model,
  skill-management and knowledge.
- **coga-dev internals to delete** (under `docs/contexts/coga-dev/internals/`):
  `state-publication` (+`publish`, `log-writers`), `git-regressions`,
  `git-refresh`, `launch-claims`, `claim-recovery`, `branch-sweep`,
  `recurring-control` and `recurring-temp-worktrees`.
- **coga-dev internals to rewrite:** `assist-publication` and `spool-merge`.
- **coga-dev topics needing light edits:** `internals/`, `codebase/`
  (+`gotchas`), `patterns/`, `packaging/`, `testing/`, `current-direction/`,
  `microkernel/` (+`objectives`), `compose/`, `agent-spawn/`,
  `notifications/`, `blackboard-io/`, `activity-capture/`,
  `recurring-admission/` and `recurring-autofix/`.
- **Prompt surfaces.**
  - `src/coga/resources/prompt.md` has "Check the starting checkout" and
    "Reconcile before publishing".
  - `prompt-ticket.md` loop step 3.
  - The "Checkout (runtime)" layer is generated in `compose.py`.
  - These code skills cite it: `implement`, `peer-review`, `self-qa`,
    `merge-pr`, `open-pr` and `address-pr-comments`.
- **Packaging lists.** `tests/required_package_resources.txt` lists the
  checkout, checkout-cleanup, pr-publication, state-publication and sync
  topics, plus the branch-sweep skill, workflow and recurring template.
  `tests/test_packaging.py` `REQUIRED_BOOTSTRAP_CONTEXT_REFS` lists those
  topics, and `coga/sync/SKILL.md` is also used as a test fixture there.
- **Size.** About 11k lines of source go with `git.py` and the deleted
  modules, plus large cuts in `launch.py` (4.6k lines) and
  `recurring_runner.py` (5.6k lines). Dedicated test files to delete total
  about 13.7k lines.

<!-- coga:blackboard -->

## Production notes

### Launch audit (2026-11-19, main at 470238016)

Read-only audit of `launch.py` and its satellites, done in an orient chat.
Line numbers are against that revision.

Size: launch machinery ~8,900 lines (`launch.py` 4,631; supervisors 1,730;
`compose.py` 891; `launch_script.py` 702; `claimed_session.py` 654). Git /
checkout modules ~10,900 (`git.py` 3,772; `autoclose.py` 1,842;
`branchsweep.py` 1,730; `checkouts.py` 1,198; `branchcleanup.py` 1,175;
`open_pr.py` 1,018).

`launch.py` by concern (overlapping): agent ~31%, Git/sync ~24%,
mode-specific (recurring, megalaunch, chat, prompt-report, read-only) ~17%,
lifecycle ~11%, script ~6%.

Findings:
- Script is a pre-phase of an agent loop; the in-loop re-run drops args,
  exit-75 handling, spawn refusal. Megalaunch has no script phase at all: a
  ticket with `ticket.py` gets an agent there.
- "Step unchanged" means "agent continues" after a script but "failure"
  after an agent in megalaunch.
- Three step loops (`run_script_chain`, `_supervise_steps`, megalaunch
  `_launch_until_stop`); four `ticket.py` spawn sites with different
  primitives; four `in_progress` flip implementations; three env-scrub copies.
- Seven distinct sync points; exit 75 + withheld sweep at ~27 sites.
- `_launch` has 16 mode parameters; `_manages_branch_checkout` is a 13-term
  exclusion. Recurring delegation runs `_launch` twice with an
  exception-driven restart. Private imports go both ways launch ↔
  recurring_runner and launch ↔ claimed_session.
- Ticket read ~12 times, operator derived ~15 times per launch.
- Dead code: `_prospective_assist_ticket` (no references), ~8 unreachable
  returns.

Guarantee families and their fate: (1) byte-guarded publication → plain
commit/push, fail-stop; (2) reload after sync → once per step; (3) env
isolation → kept; (4) claim/admission/lease → dropped (owner is single
writer); (5) blocked re-park → launch never touches blocked; (6) Windows →
kept in the agent executor.

### Next

- Re-evaluate every `v1/microkernel/` ticket and `v1/why-is-the-code-so-big`
  against these decisions; drop what this ticket supersedes (owner request,
  2026-11-19).

## Open Questions

Design step, 2026-11-20. Settled in chat: one PR, `run:` steps, delete control-dependent hygiene, final bump on the branch (decisions 12-15).

1. **`state_lock` removal.** The spec deletes the local file lock (decision 3: "no locks"). Ticket writes become atomic replaces, and log appends become a single `O_APPEND` write. Cost: two local commands racing on the same ticket can lose one update. Keep a process-local mutex instead?
2. **Autoclose is deleted outright.** Decision 15 makes it redundant, which also makes `v1/microkernel/17` (move autoclose to the edge) and `16` (move branch-sweep) moot. Confirm, and cancel those two?
3. **`code/open-pr` compatibility.** The spec keeps it as a thin agent skill that runs `git/push-and-open-pr`, so live tickets frozen with an agent `open-pr` step still finish. Alternative: delete it and accept that those tickets need `coga bump --to`.
4. **`unblock --answer` target status.** Inside a launched session for the ticket (the `COGA_TASK_*` env names it) it goes to `in_progress`; elsewhere it goes to `active`. Is "elsewhere → active" right, or should an out-of-session answer also go to `in_progress`?
5. **`coga.toml` "Git sync" comment block.** Agents may not edit `coga.toml`, so the owner removes the block in the implementation PR (or allows the implementer to). `[git]` keeps loading with an `obsolete-key` warning.
6. **Branch base for `open-branch`.** The spec branches from the current HEAD. Should the script instead fetch and branch from the remote default branch? That is faster to start fresh, but the script then fetches by itself.
7. **`run:` step role.** A `run:` step must resolve to an agent role (owner steps are never launched). Should a `run:` step with no `assignee:` default to `agent` instead of inheriting, so workflows can omit it?
