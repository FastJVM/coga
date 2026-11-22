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
step: 7 (review)
agent: claude
contexts:
- coga-dev/principles
---

## Description

Coga stops abstracting Git. There is no control branch, no automatic
publication or end-of-command sweep, and no locks. Branch creation and the
PR become workflow `run:` steps, and the launch kernel no longer knows Git.
This ticket supersedes the parts of `v1/microkernel/` and
`v1/why-is-the-code-so-big` that move or polish publication, checkout,
sweep and claim machinery. The microkernel decides where behavior lives;
this ticket stops abstracting Git.

### Target model (owner, 2026-11-19)

Three orthogonal layers. Each can change without touching the others.

1. **The kernel runs tickets.** It picks the step's executor, runs it, and
   records status and step in the ticket file. It knows nothing about Git,
   branches, PRs, remotes or publication. It takes no locks: the ticket's
   owner is its single writer. There is no claim transaction, period lease
   or `expect`-guarded write. If a crash lands between the status write and
   the spawn, the human relaunches.
2. **Executors compute a step.** A step is a **script** (deterministic,
   zero tokens), an **agent** (judgment), or **text** for a human.
   Deterministic is the default. The hybrid in `coga/script-tickets`
   "Chaining" stays: a script that leaves its step open hands it to the
   agent. A failure is not repaired inside the ticket; it becomes another
   ticket. Windows and terminal specifics stay inside the agent executor.
3. **Version control is plain Git, outside Coga.** Coga's files are
   ordinary files in the checkout. On a branch, the ticket's state travels
   with the code and reaches main through the PR. Branch and PR helpers
   exist only as workflow script steps. A workflow without them (recurring,
   script-only, text) commits where it runs, or not at all. Coga works in a
   directory without Git. Syncing is `git pull`/`git push`; there is no
   `coga sync` (the `git-sync/` group was canceled 2026-11-19). `git.py`
   disappears.

**Stop simply** across all layers. When something is not clean (a Git
conflict, a failed push, a script error), stop, keep local state, and say
what happened. Recovery is a human or agent act: no retraction, no
uncertain-push retention, no exit-75 threading.

Other owner decisions:

- **`coga/log.md` is append-only.** Its conflicts resolve by keeping both
  sides (`merge=union`). It is the one genuinely shared file.
- **Launch never touches `blocked`.** On a blocked ticket, launch starts
  the session with the resolve preamble and leaves the status `blocked`.
  `coga unblock --answer` inside a launched session for the ticket moves it
  to `in_progress`; outside one it moves it to `active`. A session that ends
  without an answer leaves the ticket blocked. No script runs on a blocked
  ticket.
- **The per-step `checkout:` field goes**, with `checkout_policy.py`,
  `checkouts.py` and `_prepare_step_checkout`. Opening a branch is a script
  a workflow may use, never an obligation of the model.
- **No one-session-per-checkout guard.** Two sessions in one checkout are
  the human's business, like two editors on one repo.
- **One implementation PR.** The frozen `implement` step delivers the whole
  change. Docs and README land in the same PR.
- **Delete control-dependent branch hygiene**: branch sweep, branch
  cleanup, checkout disposal, the retire worklist and autoclose. Cleaning
  branches is plain `git branch -d`/`gh`. This makes `v1/microkernel/16`
  and `17` moot; canceling them is the owner's call.
- **The final bump on the branch marks the ticket done.** The commit
  carrying `status: done` reaches main with the PR merge. Nothing closes
  tickets in the background.
- **No lock of any kind.** `state_lock` goes, with no process-local mutex.
  Two local commands racing on one ticket can lose an update, and that is
  accepted.
- The owner allows the implementer to delete the commented "Git sync"
  `[git]` block in `coga/coga.toml`. Nothing else in that file may change.

`coga-dev/principles` already has "Deterministic by default", "Use tools
plainly" and a stop-simply clause in "Fail loud" (2026-11-19). Align the
README with them in this PR, not before, so users never read about
behavior that does not exist yet.

### Contracts (owner, 2026-11-20 review-design)

**C1. `## Dev` is the ticket's Git record.** This is a general mechanism.
Steps hand Git facts to each other through `## Dev` lines in the ticket
file. One shared reader/writer in `blackboard.py` handles them. Move
`insert_branch_line` (`checkouts.py`), `set_dev_pr` (`open_pr.py`), and
`parse_branch_name`/`parse_pr_url` (`autoclose.py`) there. The
`requires: branch|pr` gates use it too. Fields, one per line:

    branch: <name>         # open-branch
    base: <branch>         # open-branch
    remote: <name>         # open-branch
    reviewed: <oid>        # code/peer-review, on approval: its HEAD
    pr: <full /pull/ URL>  # push-and-open-pr

Each writer sets only its own fields, and unknown lines are preserved.
Readers take branch, remote, base and reviewed head from these lines
instead of probing Git or `gh` for them. They stop with a message if a
field they need is missing or disagrees with Git (for example, the current
branch differs from `branch:`). The ticket template guide
(`src/coga/resources/ticket.md`) and `coga/git` document the fields.

**C2. `git/open-branch/run.py`** (edge; imports only shared core infra).
- If `branch:` is recorded, run `git switch <branch>`. Otherwise derive the
  name from the ticket slug (move `checkouts._fresh_branch_name` here, with
  a fixed prefix now that `[git]` config is gone), then
  `git switch -c <branch>` from the current HEAD. Never fetch.
- Record the missing fields. `base:` is the branch HEAD was on at creation;
  on reuse, or when HEAD is detached, it is the remote's default branch
  (`gh repo view --json defaultBranchRef`), or `--base <name>`. `remote:` is
  the base's upstream remote, else `origin`. This backfill lets live tickets
  that recorded only `branch:` reach the PR step.
- Then `coga bump`. With `--no-bump` it does the setup only.
- Any non-zero `git` exit: print Git's message and exit non-zero without
  bumping. Uncommitted changes travel under Git's own rules.

**C3. `git/push-and-open-pr/run.py`.**
- Refuse if anything other than the ticket file and `coga/log.md` is
  uncommitted or staged ("commit your work first").
- In order:
  1. Commit the ticket and log if they changed (path-limited:
     `git commit --only <ticket> coga/log.md`).
  2. `git push -u <remote> HEAD`.
  3. `gh pr view <branch> --json url,state,isDraft,baseRefName`. An open PR
     on `base:` is reused; a draft gets `gh pr ready`; closed, merged or
     wrong-base stops with a message. With no PR, run
     `gh pr create --base <base>`, building the body from `## PR` evidence
     (move `open_pr._pr_presentation`/`_receipt` here).
  4. Record `pr:` and run `coga bump`.
  5. Commit the ticket and log again, then push again.
- Forks are out of scope: whatever `gh` cannot resolve stops the script.
- A rerun after a partial success reuses the pushed branch and the existing
  PR, then finishes.
- Launch may append a `coga/log.md` line after the final push, so the
  remote can lag one log line. That is accepted and documented in
  `coga/git`.
- Drop `open_pr`'s control gates (`_checkout_mode`,
  `check_branch_contains_control`, the stale-branch checks).

**C4. State commits after the PR opens.** Whoever changes the ticket
commits and pushes it on the branch: the agent per its skill, the owner by
hand (`coga/git`). In owner-gated workflows, the owner's final done bump is
committed and pushed before merging. In `code/agent-merge`, `code/merge-pr`
does five things in order:
1. Stops if `reviewed:` is absent.
2. Bumps to done.
3. Commits the ticket and log, and pushes.
4. Waits for checks on that head.
5. Merges pinned to that head.

Before merging, it verifies that every commit after `reviewed:` touches
only the ticket file and `coga/log.md`, and stops otherwise. If a push or
merge fails after a local bump, it stops: nothing retracts the bump.

**C5. Legacy frozen snapshots.**
- `checkout:` keys are ignored.
- `code/implement` runs `git/open-branch/run.py --no-bump` when `## Dev`
  has no `branch:`, so `implement` stays the current step.
- The agent skills for old steps (`peer-review`, `open-pr`, `review`,
  `merge-pr`, `address-pr-comments`) start with `git switch <branch:>` when
  not on it. A dirty or conflicting switch means stop.
- Once the branch exists, the branch copy of the ticket is the live one.
- `code/open-pr` stays as a thin agent skill that runs
  `git/push-and-open-pr` (about 20 live tickets freeze it).
- Test: an old snapshot launched from the default checkout at `implement`
  ends on the branch with `step:` still at `implement`.

**C6. `run:` steps and dispatch.**
- `WorkflowStep.run: str | None`. `<name>` resolves like a skill (local
  first, then package) to a directory holding `run.py`; a local override
  wins.
- `validate` errors on a resolved directory without a readable `run.py`,
  and launch refuses it, naming the path. A `run:` step whose resolved role
  is `owner` is a `bad-shape` error. The assignee inherits like any step,
  and packaged workflows write `assignee: agent` explicitly.
- `validate._check_step_shape` exempts `run:` steps from the "skill-less
  step needs a `## <step>` section" rule.
- One function, `launch_script.script_entry_point(ref, ticket)`, returns
  the current step's `run.py`, else the ticket's `ticket.py`. `coga launch`
  (`_run_initial_script`, `_supervise_steps`, `run_script_chain`'s
  re-stat), megalaunch `_launch_until_stop` and recurring delegation all
  use it.
- Environment, `system` attribution, gates and Chaining are unchanged. A
  script that bumps chains to the next step. One that leaves the step open
  hands it to the agent.
- Megalaunch gains this script phase as new behavior, in its own commit
  and with its own test. Stateless `bootstrap/<name>` targets keep today's
  `ticket.py` behavior.

**C7. Scope against `v1/04`.** The target model is the end state across
this ticket and `v1/04`. This ticket deletes the Git, publication, claim,
lease, checkout and re-park paths. One ticket read per step, executor
unification, environment-isolation consolidation, the done sentinel's and
terminal probe's removal, and `coga exit` belong to `v1/04`. Here,
`_terminal_status_probe` only switches to reading the local ticket file.

**C8. Log compaction.** `coga_edge.trim_log` stays. It snapshots, trims,
and just before the atomic replace re-reads and appends any bytes beyond
the snapshot length. The remaining tiny race is accepted and documented in
`coga/git`. Test: an append between snapshot and replace survives.

**C9. Recorded assists.** `coga launch <task> --agent <name>` on an owner
step keeps only audit attribution (`ASSIST_AGENT_ENV`, with
`assist_session_from_env` reduced to the agent).
`verify_recorded_assist_pr_head`, the assist branch/PR env and checkout
alignment go; the human switches branches. In
`tests/test_launch_script.py`, keep the attribution cases and delete the
PR-head cases.

**C10. Surviving Git/`gh` subprocesses in core.** Each one gets a fate:
- `commands/update.py` work-tree probe: a `pathlib` check for `.git`.
- `recurring_activity.py` `git log` inactivity scan:
  `logfile.last_activity_map`.
- `config.py` `ls-files` calls and the `git` call in `validate.py`: replace
  them with `pathlib` walks or drop them with the features they serve.
- `github_preflight.py`: delete the control-drift helpers
  (`check_branch_contains_control`, `coga_root_prefix`,
  `is_coga_state_path`, `stranded_task_state_paths`/`_remediation` and its
  `validate` use). Move the remote/auth/`gh` checks that
  `push-and-open-pr` needs into that script, and delete the module. With
  it go `coga validate --check-github` (`validate._github_issues`) and
  `commands/bump`'s stranded-ticket-state warning.
- `dependencies.py` only names git as a dependency and stays.

### Acceptance criteria

Kernel without Git:
- [ ] Deleted: `git.py`, `publish_state.py`, `state_sweep.py`,
      `log_publication.py`, `log_transaction.py`, `checkouts.py`,
      `checkout_policy.py`, `checkout_disposal.py`, `claimed_session.py`,
      `review_conflict.py`, `branchsweep.py`, `branchcleanup.py`,
      `retire_worklist.py`, `autoclose.py`, `open_pr.py` and
      `github_preflight.py`.
      `rg -n "coga\.git\b|from coga import git|from \.git import" src tests`
      finds nothing.
- [ ] No module under `src/coga/` (core, not `resources/` or `coga_edge/`)
      runs a `git` or `gh` subprocess, except `skill_manager.py` installing
      a skill from a Git URL (inlined there) and invoking `gh skill` for
      skill management (owner-confirmed during peer review) (C10).
- [ ] In a temporary directory with **no `.git`**, `coga init`, `create`,
      `mark active`, `launch` of a `run:` fixture workflow, `bump`, `block`
      and `unblock --answer` succeed. A test covers this. The fixture
      script is non-Git and bumps (launch performs that bump). The next
      step is owner-held, so no agent spawns. A later local `coga bump`
      advances it.
- [ ] No command commits, pushes, fetches or switches branches by itself.
      `cli.main` → `_sweep_coga_state` and `runner._publish_after` are
      gone. A test asserts that `git status` after `coga bump` shows the
      ticket and `coga/log.md` modified and nothing committed.
- [ ] Exit code 75 has no Coga meaning: `RETRY_WITHOUT_SWEEP_EXIT_CODE`,
      `STALE_CONTROL_EXIT_CODE`, `state_sweep_withheld` and
      `control_relay_started` no longer exist.
- [ ] `runner.RECIPES` no longer lists `publish-state`,
      `prepare-checkout`, `branch-sweep`, `autoclose` or `open-pr`, with no
      forwarding entries.

Lifecycle writes:
- [ ] `bump`, `mark`, `block`, `unblock`, `owner`, `create` and `delete`
      read the local ticket, compute, and write atomically (`atomicio`).
      Gone: `prepare_ticket`, `PreparedTicket`, `merge_ticket_bytes`,
      `lifecycle_winner`, `TicketConflictError`, `TicketChangedError` and
      `expect=` guards.
- [ ] `state_lock` is gone. `logfile.append_log` appends with one
      `O_APPEND` write.
- [ ] `launch_generation` and `period_generation` are no longer written,
      read or known. `coga validate` warns `obsolete-key` for a leftover
      one. This repo's tickets that carry them are cleaned.

Workflows:
- [ ] `checkout:` is not parsed, frozen or validated as a policy. In a
      frozen snapshot it is ignored with an `obsolete-key` warning.
- [ ] `run:` steps work as in C6.
- [ ] Packaged skills `git/open-branch` and `git/push-and-open-pr` exist
      with `run.py` (C1-C3) and are listed in
      `tests/required_package_resources.txt`.
- [ ] Packaged `code/with-review`, `code/with-self-review`,
      `code/agent-merge`, `code/design-then-implement` and
      `docs/with-review` open the branch with an `open-branch` `run:` step
      and the PR with a `push-and-open-pr` `run:` step, and declare no
      `checkout:`.
- [ ] `requires: branch|pr` gates still work and read `## Dev` only.

Launch:
- [ ] Launch never changes branches or refuses because of checkout state.
      There is no "Checkout (runtime)" prompt layer.
- [ ] No chat guard: two `coga chat` sessions in one checkout both start.
- [ ] Megalaunch launches picks in sequence without claims, and runs
      `run:` steps (C6). The held-child gate in
      `repl_supervisor.py`/`repl_supervisor_nt.py` is gone.
- [ ] Recurring has no period lease and no control relay. The due scan and
      ledger read local files in the current checkout.
- [ ] **Blocked:** launch on a `blocked` ticket with a TTY starts the agent
      with the resolution preamble and leaves `status: blocked`. Without a
      TTY it refuses as today. A script or `run:` step on a blocked ticket
      refuses with "answer with `coga unblock --answer`". Nothing re-parks
      after the session (`reblock_unresolved_resume`,
      `reblock_after_script`, `should_reblock_after_script`,
      `_park_unanswered_resume`, megalaunch `_reblock_unresolved` are gone).
- [ ] `unblock --answer` → `in_progress` inside a launched session for the
      ticket (`COGA_TASK_*`), → `active` otherwise. Tests cover both.

Contracts:
- [ ] C1-C9 hold, with these tests:
      - `## Dev` writer round-trip, and a stop on a missing or mismatched
        field.
      - `open-branch`: create, reuse, backfill, `--no-bump`, and fail-stop
        on a Git error.
      - `push-and-open-pr` with `gh` stubbed: create, reuse, ready a draft,
        closed or wrong-base refusal, retry after a partial success, and
        the dirty-tree refusal.
      - `merge-pr`'s commits-after-`reviewed:` check.
      - The legacy snapshot at `implement`.
      - `run:` dispatch through launch, megalaunch and recurring.
      - The trim-log tail append.
      - Assist attribution.

Docs, README and packaging:
- [ ] Deleted: user topics `coga/checkouts`, `coga/state-publication`,
      `coga/sync` and `coga/checkout-cleanup` (all children), plus the
      coga-dev internals listed in Context. A new short user topic
      `coga/git` owns the plain-Git conventions.
      `REQUIRED_BOOTSTRAP_CONTEXT_REFS` and
      `tests/required_package_resources.txt` match.
- [ ] `src/coga/resources/prompt.md` replaces "Check the starting
      checkout" and "Reconcile before publishing" with one short "Git"
      section pointing to `coga/git`. `prompt-ticket.md` loop step 3 and
      `AGENTS.md`'s reconciliation line point to `coga/git`.
- [ ] A grep for
      `control branch|publish-state|prepare-checkout|state sweep|checkout:`
      over `src/coga/resources docs/contexts README.md AGENTS.md` finds
      nothing stale, including in `src/coga/resources/ticket.md`.
- [ ] The README matches `coga-dev/principles` ("Use tools plainly",
      "Deterministic by default", "Fail loud").
- [ ] The macOS clean-install skill
      (`src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md`)
      refers to `v1/11-verify-the-macos-full-suite-procedure-on-the-ec`
      instead of `v1/44-…`.
- [ ] `python -m pytest` passes and `coga validate --json` reports no
      errors. The PR lists both commands with their results.

### Proposed shape

These are work areas in a suggested commit order, and each commit keeps the
suite green. Where areas overlap, move a helper to its new home and migrate
its callers and tests before deleting the old owner. The acceptance
criteria list the deletions; this section names only what is not obvious.

**§1 Stop publishing.**
- Delete the sweep and `_publish_after`, keeping the done sentinel for
  `v1/04`. Replace `prepare_ticket`/`sync_task_state`/
  `write_ticket(prepared=)` in `bump.py`, `mark.py`, `commands/*` and
  `commands/common.py` with read, build, `atomicio.atomic_write_bytes`.
- `logfile.py` drops `retract_log_*` and `replace_log`'s publication
  receipt.
- Scaffold `src/coga/resources/templates/coga/.gitattributes` and this
  repo's `coga/.gitattributes`: `/log.md merge=union`, and drop the
  `retires.md` line. Keep `INTENTIONALLY_DIVERGENT_TWINS` consistent.
- Edge callers of `publish`/`sync_task_state` write locally:
  `coga_edge/{phone_home,blocker_reminders,megalaunch,trim_log}` and the
  resource scripts `recurring-promote`, `retire` and `status`.

**§2 Drop checkout policy and the chat guard.** `workflow._parse_step`
ignores `checkout`, `freeze` stops writing it, and `validate` warns. In
`launch.py`, delete `_prepare_step_checkout`, `_CheckoutBoundary`,
`return_checkout`, `_manages_branch_checkout`, `_checkout_exemption`,
`_orientation_checkout_guard`, `checkout_guard_scope` and `_CHAT_SESSION`.
Delete `compose.py`'s `checkout_notice` layer.

**§3 `## Dev` record, `run:`, and the Git scripts (C1-C3, C5, C6).**
Workflows: `code/with-review` becomes `open-branch` (run, agent) →
`implement` (agent, requires branch) → `peer-review` (other-agent, writes
`reviewed:`) → `push-and-open-pr` (run, agent, requires pr) → `review`
(owner). Give `with-self-review` the same shape, as well as `agent-merge`
(whose `merge` stays an agent step), `design-then-implement` (design steps
first) and `docs/with-review`. Skills: drop "Checkout (runtime)" and
control-freshness wording from `implement`, `peer-review`, `self-qa`,
`merge-pr`, `address-pr-comments`, `open-pr`, `bootstrap/orient/ticket.md`
and `docs/with-review`.

**§4 Drop claims, leases and re-parking.**
- Delete `claimed_session.py` and the `after_spawn*`/
  `spawn_release_guard`/`on_spawn_admission_failure` hooks in
  `spawn_agent_session`.
- Remove the `launch_generation` helpers from `ticket.py`, `mark.py`,
  `bump.py` and `commands/owner.py`.
- Megalaunch per pick: read the ticket, `resolve_operator`, activate or set
  `in_progress`, then run the script phase (C6) and `spawn_agent_session`.
  Keep selection, ordering, drain and summary.
- Recurring: delete `PeriodLease` and friends in `recurring.py`, and
  `_ParentStateLease`, `_verify_period_on_control`, the control relay and
  `_ControlWorktreeOwner` in `recurring_runner.py`. Delete the
  period-lease parameters in `launch.py`.
  `workspace_discovery.py` drops `CONTROL_WORKTREE_*`. `period_state.py`
  stays.
- Blocked: in `_launch`, keep `blocked_resume` and the preamble (already
  keyed on open asks), but skip `_auto_activate` and the `in_progress`
  flip.

**§5 Delete `git.py`.**
- `toplevel`/`relative_to_root` → `config.find_checkout_root`/
  `find_repo_root` or `pathlib`. `symlink_component` → `paths.py`.
- `views` uses `logfile.last_activity_map`.
- The `status` bootstrap ticket drops `stale_coga_task_rels`,
  `feature_sync_plan` and `stale_index_lock`.
- `commands/init.py` writes the files and prints "commit `coga/` when
  ready". It drops the commit, the identity probe and the control-branch
  table, and works without Git.
- `config.py` drops `[git]` parsing; a `[git]` table loads with an
  `obsolete-key` warning.
- Apply C10.
- Delete the `branch-sweep` and `autoclose-merged` recurring templates,
  workflows and skills. Remove the deleted entries from `coga-dev/microkernel`
  "Open command placements".

**§6 Docs.**
- `coga/git` (about 60 lines) covers:
  - the `## Dev` fields;
  - the branch → PR flow and who commits state;
  - the final bump on the branch;
  - the union log merge and the trim race;
  - plain `git`/`gh` for pushing, pulling and cleaning;
  - stop when Git is not clean;
  - from `coga/checkouts/reconciliation`: rebase on the base branch and
    preserve unique work.
- Update `coga/workflows` (`run:`) and `coga/script-tickets` (step
  scripts). Rewrite `coga/pr-publication` around `push-and-open-pr`.
  Edit-pass the topics listed in Context.

**§7 Tests and fixtures.**
- Delete `tests/test_git.py`, `test_checkouts.py`, `test_branchsweep.py`,
  `test_branchcleanup.py`, `test_publish_state.py`,
  `test_autoclose_dispose.py`, and `test_autoclose_sweep.py`.
- Cut the claim, lease, sweep and publication cases from `test_megalaunch`,
  `test_recurring*`, `test_launch*`, `conftest.py`, `test_cli`,
  `test_authoring`, `test_runner`, `test_trim_log`, `test_mark`,
  `test_retire*` and `test_period_state`.
- Update the seeded fixture `tests/fixtures/seeded-repo/coga/workflows/` to
  the new shape, and keep `deterministic/check.md` working.

### Out of scope

- Everything C7 assigns to `v1/04`.
- Reworking the script/ticket model beyond `run:`.
- A `coga sync` command.
- Canceling or rescoping `v1/microkernel/*` and
  `v1/why-is-the-code-so-big`. The owner decides.
- Committing or pushing recurring-job output; a commit `run:` step for
  recurring is a later choice.
- Branch cleanup automation of any kind.
- Forks in `push-and-open-pr`.

### This ticket runs on the old model until merge

This ticket's frozen snapshot uses today's `checkout:` policies and an
agent `open-pr` step. The editable install points at the main checkout's
`src/`, so every launch of this ticket runs today's code until the PR
merges. The owner chose to keep it that way:

- `implement` gets its branch from today's `create-or-reuse`. Work and test
  in that branch's checkout: pytest's `pythonpath = ["src"]` tests the
  branch code. Do not reinstall the package from the branch, and do not
  switch the main checkout.
- `peer-review` and `open-pr` run today's skills and code. Today's sweep
  keeps publishing this ticket's state to main.
- Keep this ticket file and `coga/log.md` out of the PR diff, and make no
  ticket-state commits on the branch. Contract C4 applies from the next
  ticket on.
- After merge, main runs the new code. The owner's final `review` bump is
  then a local write on main that the owner commits.

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

### Codebase facts (survey 2026-11-20, main at 45aeecd86)

These are symbols, not line numbers, and the survey is dated. Re-grep
before relying on any of them.

- **Importers of `coga.git`.** Run
  `rg -l "coga.git import|from coga import git" src` (about 45 modules).
  `state_lock` users: `logfile`, `blackboard`, `validate`,
  `recurring_state`, `delete_task` and `commands/owner`. `write_ticket`
  becomes `atomicio`. Only `open_pr` uses `union_merge_paths`.
- **Publish call sites.** `cli.main` → `_sweep_coga_state` →
  `state_sweep.sweep_root`. `runner.run_reported`/`run_entry` →
  `_publish_after`. In-command `sync_task_state`/`publish` calls are in
  `bump`, `mark`, `commands/{create,owner,unblock,delete}`, `launch` and
  `recurring_runner`. Exit 75 appears in about 21 files.
- **Gates.** `step_gate.STEP_GATES`: `branch` → `_has_branch_linkage`, and
  `pr` → `_has_pr`, through autoclose's parsers (moved per C1). Gates
  apply to forward bumps in `commands/bump.py` only.
- **Script phase.** `launch_script.run_script_phase` spawns
  `[sys.executable, ticket.py]` with `COGA_TASK_*` and `COGA_SCRIPT_TASK`.
  `_classify_script_handoff` implements Chaining and never runs a script
  on an owner-held step. `bump`/`mark done` credit `system` when
  `COGA_SCRIPT_TASK` matches. Valid roles are `owner`, `agent` and
  `other-agent`.
- **Blocked today.** `_launch` sets `blocked_resume` on a TTY. The script
  branch auto-activates `{"draft","paused","blocked"}` and then re-blocks.
  The preamble is built by `compose._open_asks` + `_blocker_preamble`
  (`prompt-blocker-resolution.md`). `unblock._apply_unblock` sends
  `blocked` → `mark_active`.
- **Done sentinel.** `cli.py` wraps the sweep in `deferred_done_marker`.
  `_terminal_status_probe` reads the control ref via `git._blob_*` and
  matches `period_generation`.
- **Named deletion targets (survey list; grep for them).**
  - `launch.py`: `_checkout_refusal_message`, `_CHECKOUT_GUARD_SCOPE`,
    `run_claimed_agent_session`, `_reconcile_released_launch_admission`,
    `capture_launched_period_lease`,
    `_refresh_recurring_period_before_launch`,
    `_exact_recurring_period_for_launch` and `expected_period_lease`.
  - Supervisors: `_admit_held_child` and the gate fd.
  - Megalaunch: `_restore_after_failed_start`, `_activate_for_launch`'s
    claim path, and `expect=` in `_publish_partial_dependency_resolution`
    and `_drain_satisfied_blockers`.
  - `recurring.py`: `period_generation_from_ticket_bytes`,
    `local_period_lease` and `same_period_lease`.
  - `recurring_runner.py`: `_revision_period_lease`,
    `_local_parent_state_lease`, `_revision_parent_state_lease`,
    `_require_period_bytes`, `_restore_period_bytes`,
    `admitted_period_leases`, `confirm_control_lease`,
    `_relay_to_control_worktree`, `_control_already_has_period` (becomes the
    local ledger), `_control_remote_present_at_admission` and
    `_sweep_stopping_exit`. `recurring --all` runs each repo in its current
    checkout.
  - `commands/common`: `prepare_lifecycle_ticket`'s conflict branch,
    `bail_ticket_changed` and `_refuse_conflict`.
  - `cli.py`: `_should_sweep_coga_state`.
  - `workflow.py`: `CHECKOUT_POLICIES` and `DEFAULT_CHECKOUT`.
  - `compose.py`: `UNSUPPLIED_CHECKOUT_NOTICE`.
  - `config.py`: `_parse_git`, `_resolve_git_enabled`, `git_control_branch`
    and `worktrees_ticket_owned`.
  - `init`: `control_branch_present`, `symbolic_head` and
    `_render_git_control_branch_table`.
  - `skill_manager`: inline its `git ls-remote`-style call and `_git_env`.
  - Delete the recurring-template workflows `branch-sweep/sweep` and
    `autoclose-merged/sweep`.
- **Fields to clean.** `launch_generation:`/`period_generation:` in
  `coga/tasks/recurring/*/ticket.md` and
  `coga/tasks/fix-the-windows-aws-walk-step-and-add-the-v1-14-at.md`.
- **Packaging lists.** `tests/required_package_resources.txt` and
  `tests/test_packaging.py` `REQUIRED_BOOTSTRAP_CONTEXT_REFS` list the
  checkout, checkout-cleanup, pr-publication, state-publication and sync
  topics and the branch-sweep skill/workflow/template. `coga/sync/SKILL.md`
  is also a fixture in `test_packaging.py`.

### Docs to change

- **User topics to delete** (under
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/`):
  - `checkouts/`, with `reconciliation`, `launch-boundary`, `chat`,
    `manual` and `sandbox-clone`. If `sandbox-clone`'s seeding of
    `coga.local.toml`/`.coga/` is still needed, move it into
    `coga/sandboxes`.
  - `state-publication/`, with `launch-boundaries`.
  - `sync/`.
  - `checkout-cleanup/`, with `branch-sweep` and `terminal-owners`.
- **User topics to rewrite:** `pr-publication` and, lightly, `preparation`.
- **User topics to edit for passing mentions:** launch, workflows,
  lifecycle, megalaunch, tickets (+authoring), recurring (+scheduling,
  autofix, delegation, templates, inactivity), configuration,
  architecture, cli, first-task, human-assist, blackboard, uninstall,
  prompt-composition, sandboxes, important, usage, script-tickets,
  notifications/producers, context-layout, extension-model,
  skill-management and knowledge.
- **coga-dev internals to delete** (under
  `docs/contexts/coga-dev/internals/`): `state-publication` (+`publish`,
  `log-writers`), `git-regressions`, `git-refresh`, `launch-claims`,
  `claim-recovery`, `branch-sweep`, `recurring-control` and
  `recurring-temp-worktrees`.
- **coga-dev internals to rewrite:** `assist-publication` and
  `spool-merge`.
- **coga-dev topics needing light edits:** `internals/`, `codebase/`
  (+`gotchas`), `patterns/`, `packaging/`, `testing/`,
  `current-direction/`, `microkernel/` (+`objectives`), `compose/`,
  `agent-spawn/`, `notifications/`, `blackboard-io/`, `activity-capture/`,
  `recurring-admission/` and `recurring-autofix/`.
- **Prompt surfaces.**
  - `src/coga/resources/prompt.md`: "Check the starting checkout" and
    "Reconcile before publishing".
  - `prompt-ticket.md`: loop step 3.
  - The `compose.py` "Checkout (runtime)" layer.
  - The code skills that cite that layer: `implement`, `peer-review`,
    `self-qa`, `merge-pr`, `open-pr` and `address-pr-comments`.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/1279
base: main
remote: origin
branch: coga/v1-03-use-git-like-everyone-remove-coga-s-public-9c8a83
reviewed: d8848841067e9c7cb9369107bf3d2b0177ee169b


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


## Implement handoff

The migrated branch was rebased onto `cea3f2980fdbb82997149d67d91198e845f1d761` and pushed at `8839ab94ed475f2ab5dfc1f35d26445b2d8a383f`.
The rebase preserved the implementation diff and the shared checkout's
working files. The final implementation and fixture checks ran in a clean
detached worktree at that head. Pytest reported 3148 passed and 29
skipped. Repository and seeded-fixture validation returned zero errors.

The branch diff excludes this projected ticket and `coga/log.md`. The owner
asked to leave the separate workflow-parser edits in the shared checkout
and bump after verification. Legacy launch may stop its checkout return
if those edits remain. Peer review and PR publication use the frozen
workflow and the pre-migration CLI.

## PR

```yaml
title: Run Coga on local ticket files and use ordinary Git workflows
author: codex
author_evidence: "Codex implemented and verified the migration in the supervised implement session."
head: d8848841067e9c7cb9369107bf3d2b0177ee169b
base: cea3f2980fdbb82997149d67d91198e845f1d761
depth: deep
rationale: "The change alters lifecycle writes, all launch modes, packaged workflows, and GitHub handoffs. Review the compatibility\
  \ paths and partial Git failures in addition to the kernel deletions."
implementation: "Remove implicit Git and publication, claims and period leases. Add local workflow script dispatch, a shared Dev record,\
  \ explicit branch and PR scripts, pinned merge, and updated docs and workflow fixtures."
deviations: "The owner approved a deterministic final merge step so its push and merge can finish after the local done bump. GitHub\
  \ CLI remains a dependency, and existing GitHub skill transport is preserved."
limitations: "The Linux suite exercises Git operations in temporary repositories and stubs GitHub calls in workflow tests. Windows and\
  \ macOS release suites did not run in this implement session."
files:
  AGENTS.md: "Point contributors to the current Git procedure and run-step packaging rule."
  README.md: "Explain the local-file model and how explicit scripts support a plain Git workflow."
  coga/.gitattributes: "Resolve concurrent audit log append conflicts with Git's union driver."
  coga/coga.toml: "Remove retired Git settings and preserve the rest of the configuration."
  coga/recurring/autoclose-merged/retires.md: "Remove the operational definition or reference for a retired mechanism."
  coga/recurring/autoclose-merged/ticket.md: "Remove the operational definition or reference for a retired mechanism."
  coga/recurring/branch-sweep/ticket.md: "Remove the operational definition or reference for a retired mechanism."
  coga/recurring/jobs.toml: "Align this repository's configured recurring jobs with local state and explicit Git."
  coga/recurring/upstream-coga/ticket.py: "Align this repository's configured recurring jobs with local state and explicit Git."
  coga/tasks/recurring/address-pr-comments/ticket.md: "Clean legacy state fields or replace references to the deleted publication topics."
  coga/tasks/recurring/autoclose-merged/ticket.md: "Remove the operational definition or reference for a retired mechanism."
  coga/tasks/recurring/autoclose-merged/ticket.py: "Remove the operational definition or reference for a retired mechanism."
  coga/tasks/recurring/blackboard-size/ticket.md: "Clean legacy state fields or replace references to the deleted publication topics."
  coga/tasks/recurring/blocker-reminders/ticket.md: "Clean legacy state fields or replace references to the deleted publication topics."
  coga/tasks/recurring/dream/ticket.md: "Clean legacy state fields or replace references to the deleted publication topics."
  coga/tasks/v1/microkernel/15-lifecycle-verbs-to-ticket-operations.md: "Clean legacy state fields or replace references to the deleted\
    \ publication topics."
  docs/README.md: "Keep the development topic or index aligned with local coordination and explicit workflow scripts."
  docs/contexts/coga-dev/codebase/SKILL.md: "Keep the development topic or index aligned with local coordination and explicit workflow\
    \ scripts."
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: "Keep the development topic or index aligned with local coordination and explicit\
    \ workflow scripts."
  docs/contexts/coga-dev/current-direction/SKILL.md: "Keep the development topic or index aligned with local coordination and explicit\
    \ workflow scripts."
  docs/contexts/coga-dev/internals/SKILL.md: "Keep the development topic or index aligned with local coordination and explicit workflow\
    \ scripts."
  docs/contexts/coga-dev/internals/activity-capture/SKILL.md: "Keep the development topic or index aligned with local coordination and\
    \ explicit workflow scripts."
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: "Keep the development topic or index aligned with local coordination and explicit\
    \ workflow scripts."
  docs/contexts/coga-dev/internals/assist-publication/SKILL.md: "Keep the development topic or index aligned with local coordination\
    \ and explicit workflow scripts."
  docs/contexts/coga-dev/internals/blackboard-io/SKILL.md: "Keep the development topic or index aligned with local coordination and\
    \ explicit workflow scripts."
  docs/contexts/coga-dev/internals/branch-sweep/SKILL.md: "Remove the operational definition or reference for a retired mechanism."
  docs/contexts/coga-dev/internals/claim-recovery/SKILL.md: "Remove the operational definition or reference for a retired mechanism."
  docs/contexts/coga-dev/internals/git-refresh/SKILL.md: "Remove the operational definition or reference for a retired mechanism."
  docs/contexts/coga-dev/internals/git-regressions/SKILL.md: "Remove the operational definition or reference for a retired mechanism."
  docs/contexts/coga-dev/internals/launch-claims/SKILL.md: "Remove the operational definition or reference for a retired mechanism."
  docs/contexts/coga-dev/internals/recurring-admission/SKILL.md: "Keep the development topic or index aligned with local coordination\
    \ and explicit workflow scripts."
  docs/contexts/coga-dev/internals/recurring-control/SKILL.md: "Remove the operational definition or reference for a retired mechanism."
  docs/contexts/coga-dev/internals/recurring-temp-worktrees/SKILL.md: "Remove the operational definition or reference for a retired\
    \ mechanism."
  docs/contexts/coga-dev/internals/spool-merge/SKILL.md: "Keep the development topic or index aligned with local coordination and explicit\
    \ workflow scripts."
  docs/contexts/coga-dev/internals/state-publication/SKILL.md: "Remove the operational definition or reference for a retired mechanism."
  docs/contexts/coga-dev/internals/state-publication/log-writers/SKILL.md: "Remove the operational definition or reference for a retired\
    \ mechanism."
  docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md: "Remove the operational definition or reference for a retired\
    \ mechanism."
  docs/contexts/coga-dev/microkernel/SKILL.md: "Keep the development topic or index aligned with local coordination and explicit workflow\
    \ scripts."
  docs/contexts/coga-dev/packaging/SKILL.md: "Keep the development topic or index aligned with local coordination and explicit workflow\
    \ scripts."
  docs/contexts/coga-dev/patterns/SKILL.md: "Keep the development topic or index aligned with local coordination and explicit workflow\
    \ scripts."
  src/coga/aliases.py: "Adapt aliases to the local ticket model and remove retired coordination."
  src/coga/authoring.py: "Adapt authoring to the local ticket model and remove retired coordination."
  src/coga/autoclose.py: "Remove the autoclose module as part of retiring implicit Git and coordination."
  src/coga/blackboard.py: "Share the Dev record reader and writer and replace guarded edits with atomic local writes."
  src/coga/branchcleanup.py: "Remove the branchcleanup module as part of retiring implicit Git and coordination."
  src/coga/branchsweep.py: "Remove the branchsweep module as part of retiring implicit Git and coordination."
  src/coga/bump.py: "Adapt bump to the local ticket model and remove retired coordination."
  src/coga/checkout_disposal.py: "Remove the checkout disposal module as part of retiring implicit Git and coordination."
  src/coga/checkout_policy.py: "Remove the checkout policy module as part of retiring implicit Git and coordination."
  src/coga/checkouts.py: "Remove the checkouts module as part of retiring implicit Git and coordination."
  src/coga/claimed_session.py: "Remove the claimed session module as part of retiring implicit Git and coordination."
  src/coga/cli.py: "Adapt cli to the local ticket model and remove retired coordination."
  src/coga/commands/block.py: "Streamline the block CLI entry point for local state and plain Git."
  src/coga/commands/bump.py: "Streamline the bump CLI entry point for local state and plain Git."
  src/coga/commands/common.py: "Streamline the common CLI entry point for local state and plain Git."
  src/coga/commands/create.py: "Streamline the create CLI entry point for local state and plain Git."
  src/coga/commands/delete.py: "Streamline the delete CLI entry point for local state and plain Git."
  src/coga/commands/init.py: "Streamline the init CLI entry point for local state and plain Git."
  src/coga/commands/launch.py: "Streamline the launch CLI entry point for local state and plain Git."
  src/coga/commands/mark.py: "Streamline the mark CLI entry point for local state and plain Git."
  src/coga/commands/owner.py: "Streamline the owner CLI entry point for local state and plain Git."
  src/coga/commands/recurring.py: "Streamline the recurring CLI entry point for local state and plain Git."
  src/coga/commands/skill.py: "Streamline the skill CLI entry point for local state and plain Git."
  src/coga/commands/ticket.py: "Streamline the ticket CLI entry point for local state and plain Git."
  src/coga/commands/unblock.py: "Streamline the unblock CLI entry point for local state and plain Git."
  src/coga/commands/update.py: "Streamline the update CLI entry point for local state and plain Git."
  src/coga/commands/validate.py: "Streamline the validate CLI entry point for local state and plain Git."
  src/coga/compose.py: "Remove the runtime checkout notice and retain blocker and assist attribution."
  src/coga/config.py: "Read workspace files directly and report obsolete Git configuration."
  src/coga/create.py: "Adapt create to the local ticket model and remove retired coordination."
  src/coga/delete_task.py: "Adapt delete task to the local ticket model and remove retired coordination."
  src/coga/dependencies.py: "Declare GitHub CLI for GitHub skill and workflow operations."
  src/coga/git.py: "Remove the git module as part of retiring implicit Git and coordination."
  src/coga/github_preflight.py: "Remove the github preflight module as part of retiring implicit Git and coordination."
  src/coga/launch.py: "Dispatch the step from local ticket state without Git, claims, or blocked re-parking."
  src/coga/launch_script.py: "Resolve workflow script entry points and retain deterministic chaining."
  src/coga/log_publication.py: "Remove the log publication module as part of retiring implicit Git and coordination."
  src/coga/log_transaction.py: "Remove the log transaction module as part of retiring implicit Git and coordination."
  src/coga/logfile.py: "Append audit records locally with a single write and expose last-activity lookups."
  src/coga/mark.py: "Adapt mark to the local ticket model and remove retired coordination."
  src/coga/notification/__init__.py: "Adapt   init   to the local ticket model and remove retired coordination."
  src/coga/open_pr.py: "Remove the open pr module as part of retiring implicit Git and coordination."
  src/coga/paths.py: "Adapt paths to the local ticket model and remove retired coordination."
  src/coga/pr_assist.py: "Adapt pr assist to the local ticket model and remove retired coordination."
  src/coga/publish_state.py: "Remove the publish state module as part of retiring implicit Git and coordination."
  src/coga/recurring.py: "Adapt recurring to the local ticket model and remove retired coordination."
  src/coga/recurring_activity.py: "Adapt recurring activity to the local ticket model and remove retired coordination."
  src/coga/recurring_autofix.py: "Adapt recurring autofix to the local ticket model and remove retired coordination."
  src/coga/recurring_clone.py: "Adapt recurring clone to the local ticket model and remove retired coordination."
  src/coga/recurring_runner.py: "Delegate from local recurring state without a period lease or control relay."
  src/coga/recurring_state.py: "Adapt recurring state to the local ticket model and remove retired coordination."
  src/coga/repl_supervisor.py: "Remove child admission plumbing while retaining terminal supervision."
  src/coga/repl_supervisor_nt.py: "Remove the Windows child admission gate while retaining terminal supervision."
  src/coga/resources/prompt-blocker-resolution.md: "Carry local-state and workflow step behavior into the prompt, scaffold, or executable\
    \ resource."
  src/coga/resources/prompt-ticket.md: "Carry local-state and workflow step behavior into the prompt, scaffold, or executable resource."
  src/coga/resources/prompt.md: "Carry local-state and workflow step behavior into the prompt, scaffold, or executable resource."
  src/coga/resources/retire.md: "Carry local-state and workflow step behavior into the prompt, scaffold, or executable resource."
  src/coga/resources/templates/coga/.gitattributes: "Resolve concurrent audit log append conflicts with Git's union driver."
  src/coga/resources/templates/coga/bootstrap/address-pr-comments/ticket.md: "Carry local-state and workflow step behavior into the\
    \ prompt, scaffold, or executable resource."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: "Document the current user contract and point to\
    \ the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: "Document the current user contract and point to the\
    \ plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/SKILL.md: "Remove the operational definition or reference\
    \ for a retired mechanism."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md: "Remove the operational definition\
    \ or reference for a retired mechanism."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/terminal-owners/SKILL.md: "Remove the operational definition\
    \ or reference for a retired mechanism."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: "Remove the operational definition or reference for\
    \ a retired mechanism."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/chat/SKILL.md: "Remove the operational definition or reference\
    \ for a retired mechanism."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/launch-boundary/SKILL.md: "Remove the operational definition or\
    \ reference for a retired mechanism."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/manual/SKILL.md: "Remove the operational definition or reference\
    \ for a retired mechanism."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/reconciliation/SKILL.md: "Remove the operational definition or\
    \ reference for a retired mechanism."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/sandbox-clone/SKILL.md: "Remove the operational definition or\
    \ reference for a retired mechanism."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: "Document the current user contract and point to the plain\
    \ Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: "Document the current user contract and point to\
    \ the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md: "Document the current user contract and point to\
    \ the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md: "Document the current user contract and point\
    \ to the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: "Document the current user contract and point to the\
    \ plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/git/SKILL.md: "Document the current user contract and point to the plain\
    \ Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/human-assist/SKILL.md: "Document the current user contract and point to\
    \ the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: "Document the current user contract and point to the plain\
    \ Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md: "Document the current user contract and point to the\
    \ plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: "Document the current user contract and point to the plain\
    \ Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md: "Document the current user contract and point to the\
    \ plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md: "Document the current user contract and point to the\
    \ plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/SKILL.md: "Document the current user contract and point to\
    \ the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/pr-publication/SKILL.md: "Document the current user contract and point to\
    \ the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md: "Document the current user contract and point\
    \ to the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md: "Document the current user contract and point to the\
    \ plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/delegation/SKILL.md: "Document the current user contract and point\
    \ to the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: "Document the current user contract and point\
    \ to the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/inactivity/SKILL.md: "Document the current user contract\
    \ and point to the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md: "Document the current user contract and point\
    \ to the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/package-definitions-migration.md: "Document the current\
    \ user contract and point to the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sandboxes/SKILL.md: "Document the current user contract and point to the\
    \ plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/skills/code/implement/seed_local_config.py: "Keep clone seeding beside the optional sandbox\
    \ procedure."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sandboxes/seed_local_config.py: "Keep clone seeding beside the optional\
    \ sandbox procedure."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: "Document the current user contract and point to\
    \ the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md: "Document the current user contract and point\
    \ to the plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: "Remove the operational definition or reference\
    \ for a retired mechanism."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/launch-boundaries/SKILL.md: "Remove the operational definition\
    \ or reference for a retired mechanism."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md: "Remove the operational definition or reference for a retired\
    \ mechanism."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md: "Document the current user contract and point to the plain\
    \ Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: "Document the current user contract and point to the\
    \ plain Git procedures where they apply."
  src/coga/resources/templates/coga/bootstrap/orient/ticket.md: "Carry local-state and workflow step behavior into the prompt, scaffold,\
    \ or executable resource."
  src/coga/resources/templates/coga/bootstrap/recurring-promote/promotion.py: "Carry local-state and workflow step behavior into the\
    \ prompt, scaffold, or executable resource."
  src/coga/resources/templates/coga/bootstrap/recurring-promote/ticket.md: "Carry local-state and workflow step behavior into the prompt,\
    \ scaffold, or executable resource."
  src/coga/resources/templates/coga/bootstrap/recurring-promote/ticket.py: "Carry local-state and workflow step behavior into the prompt,\
    \ scaffold, or executable resource."
  src/coga/resources/templates/coga/bootstrap/resolve-conflicts/ticket.md: "Carry local-state and workflow step behavior into the prompt,\
    \ scaffold, or executable resource."
  src/coga/resources/templates/coga/bootstrap/retire/ticket.md: "Carry local-state and workflow step behavior into the prompt, scaffold,\
    \ or executable resource."
  src/coga/resources/templates/coga/bootstrap/retire/ticket.py: "Carry local-state and workflow step behavior into the prompt, scaffold,\
    \ or executable resource."
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/delete-task/SKILL.md: "Update the packaged instructions for explicit\
    \ operations and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/import/SKILL.md: "Update the packaged instructions for explicit operations\
    \ and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/skill-update/SKILL.md: "Update the packaged instructions for explicit\
    \ operations and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/code/address-pr-comments/SKILL.md: "Update the packaged instructions for explicit\
    \ operations and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/code/implement/SKILL.md: "Update the packaged instructions for explicit operations\
    \ and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/code/merge-pr/SKILL.md: "Finish the ticket and merge on the verified head after\
    \ checks and the reviewed-path guard."
  src/coga/resources/templates/coga/bootstrap/skills/code/merge-pr/run.py: "Finish the ticket and merge on the verified head after checks\
    \ and the reviewed-path guard."
  src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md: "Update the packaged instructions for explicit operations\
    \ and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/code/peer-review/SKILL.md: "Update the packaged instructions for explicit operations\
    \ and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/code/self-qa/SKILL.md: "Update the packaged instructions for explicit operations\
    \ and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/coga/autoclose/sweep/SKILL.md: "Remove the operational definition or reference\
    \ for a retired mechanism."
  src/coga/resources/templates/coga/bootstrap/skills/coga/branch-sweep/sweep/SKILL.md: "Remove the operational definition or reference\
    \ for a retired mechanism."
  src/coga/resources/templates/coga/bootstrap/skills/coga/calendar-reminder/SKILL.md: "Update the packaged instructions for explicit\
    \ operations and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/coga/gmail/SKILL.md: "Update the packaged instructions for explicit operations\
    \ and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/coga/google-calendar/SKILL.md: "Update the packaged instructions for explicit operations\
    \ and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/coga/recurring/verify/SKILL.md: "Update the packaged instructions for explicit\
    \ operations and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md: "Update the packaged instructions\
    \ for explicit operations and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/coga/ticket/finalize/SKILL.md: "Update the packaged instructions for explicit operations\
    \ and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/direct/body/SKILL.md: "Update the packaged instructions for explicit operations\
    \ and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/skills/git/open-branch/SKILL.md: "Create or switch the branch and record its branch, base,\
    \ and remote before advancing."
  src/coga/resources/templates/coga/bootstrap/skills/git/open-branch/run.py: "Create or switch the branch and record its branch, base,\
    \ and remote before advancing."
  src/coga/resources/templates/coga/bootstrap/skills/git/push-and-open-pr/SKILL.md: "Push state, create or reuse the matching PR, and\
    \ advance and republish the ticket."
  src/coga/resources/templates/coga/bootstrap/skills/git/push-and-open-pr/run.py: "Push state, create or reuse the matching PR, and\
    \ advance and republish the ticket."
  src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md: "Update the packaged instructions for explicit operations\
    \ and legacy snapshot compatibility."
  src/coga/resources/templates/coga/bootstrap/status/ticket.py: "Carry local-state and workflow step behavior into the prompt, scaffold,\
    \ or executable resource."
  src/coga/resources/templates/coga/bootstrap/workflows/autoclose-merged/sweep.md: "Remove the operational definition or reference for\
    \ a retired mechanism."
  src/coga/resources/templates/coga/bootstrap/workflows/branch-sweep/sweep.md: "Remove the operational definition or reference for a\
    \ retired mechanism."
  src/coga/resources/templates/coga/bootstrap/workflows/build/onboarding.md: "Align the packaged workflow definition with explicit execution\
    \ and branch-local handoffs."
  src/coga/resources/templates/coga/bootstrap/workflows/code/agent-merge.md: "Align the packaged workflow definition with explicit execution\
    \ and branch-local handoffs."
  src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md: "Align the packaged workflow definition with\
    \ explicit execution and branch-local handoffs."
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md: "Align the packaged workflow definition with explicit execution\
    \ and branch-local handoffs."
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-self-review.md: "Align the packaged workflow definition with explicit\
    \ execution and branch-local handoffs."
  src/coga/resources/templates/coga/bootstrap/workflows/direct/body.md: "Align the packaged workflow definition with explicit execution\
    \ and branch-local handoffs."
  src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md: "Align the packaged workflow definition with explicit execution\
    \ and branch-local handoffs."
  src/coga/resources/templates/coga/bootstrap/workflows/skill-update/run.md: "Align the packaged workflow definition with explicit execution\
    \ and branch-local handoffs."
  src/coga/resources/templates/coga/coga.toml: "Remove retired Git settings and preserve the rest of the configuration."
  src/coga/resources/templates/coga/recurring/autoclose-merged/operations.md: "Remove the operational definition or reference for a\
    \ retired mechanism."
  src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.md: "Remove the operational definition or reference for a retired\
    \ mechanism."
  src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.py: "Remove the operational definition or reference for a retired\
    \ mechanism."
  src/coga/resources/templates/coga/recurring/branch-sweep/ticket.md: "Remove the operational definition or reference for a retired\
    \ mechanism."
  src/coga/resources/templates/coga/recurring/branch-sweep/ticket.py: "Remove the operational definition or reference for a retired\
    \ mechanism."
  src/coga/resources/templates/coga/recurring/dream/ticket.md: "Carry local-state and workflow step behavior into the prompt, scaffold,\
    \ or executable resource."
  src/coga/resources/templates/coga/recurring/skill-update/ticket.md: "Carry local-state and workflow step behavior into the prompt,\
    \ scaffold, or executable resource."
  src/coga/resources/templates/coga/recurring/trim-log/operations.md: "Carry local-state and workflow step behavior into the prompt,\
    \ scaffold, or executable resource."
  src/coga/resources/ticket.md: "Carry local-state and workflow step behavior into the prompt, scaffold, or executable resource."
  src/coga/retire_worklist.py: "Remove the retire worklist module as part of retiring implicit Git and coordination."
  src/coga/review_conflict.py: "Remove the review conflict module as part of retiring implicit Git and coordination."
  src/coga/runner.py: "Remove retired recipe entries and keep execution results local."
  src/coga/skill_manager.py: "Keep Git URL and GitHub skill install support independent of the removed Git module."
  src/coga/state_sweep.py: "Remove the state sweep module as part of retiring implicit Git and coordination."
  src/coga/step_gate.py: "Use the shared Dev record to decide branch and PR gates."
  src/coga/task_env.py: "Adapt task env to the local ticket model and remove retired coordination."
  src/coga/ticket.py: "Remove lifecycle generation metadata from the local ticket model."
  src/coga/validate.py: "Validate local files and workflow script shape and report obsolete keys."
  src/coga/views.py: "Adapt views to the local ticket model and remove retired coordination."
  src/coga/workflow.py: "Parse and freeze run steps while ignoring obsolete checkout policy fields."
  src/coga/workspace_discovery.py: "Adapt workspace discovery to the local ticket model and remove retired coordination."
  src/coga_edge/blocker_reminders.py: "Adapt the blocker reminders edge behavior to explicit operations and local ticket state."
  src/coga_edge/git_workflow.py: "Adapt the git workflow edge behavior to explicit operations and local ticket state."
  src/coga_edge/megalaunch.py: "Adapt the megalaunch edge behavior to explicit operations and local ticket state."
  src/coga_edge/phone_home.py: "Adapt the phone home edge behavior to explicit operations and local ticket state."
  src/coga_edge/skill_update.py: "Adapt the skill update edge behavior to explicit operations and local ticket state."
  src/coga_edge/skill_update_pr.py: "Adapt the skill update pr edge behavior to explicit operations and local ticket state."
  src/coga_edge/trim_log.py: "Adapt the trim log edge behavior to explicit operations and local ticket state."
  src/coga_edge/validate_drift.py: "Adapt the validate drift edge behavior to explicit operations and local ticket state."
  tests/conftest.py: "Align the shared test harness, fixture, or installed resource inventory with the new workflow contracts."
  tests/fixtures/authoring_cancellation.py: "Align the shared test harness, fixture, or installed resource inventory with the new workflow\
    \ contracts."
  tests/fixtures/edge-migration/phone-home-old.py: "Align the shared test harness, fixture, or installed resource inventory with the\
    \ new workflow contracts."
  tests/fixtures/seeded-repo/coga/tasks/auto/triage-inbound-email.md: "Exercise the current run-step workflow shape and preserve deterministic\
    \ ticket launch."
  tests/fixtures/seeded-repo/coga/workflows/code/with-review.md: "Exercise the current run-step workflow shape and preserve deterministic\
    \ ticket launch."
  tests/required_package_resources.txt: "Align the shared test harness, fixture, or installed resource inventory with the new workflow\
    \ contracts."
  tests/test_address_pr_comments_skill.py: "Verify address pr comments skill under the local-file model and retire obsolete expectations."
  tests/test_aliases.py: "Verify aliases under the local-file model and retire obsolete expectations."
  tests/test_authoring.py: "Verify authoring under the local-file model and retire obsolete expectations."
  tests/test_autoclose.py: "Remove autoclose tests for the retired command or implementation."
  tests/test_autoclose_dispose.py: "Remove autoclose dispose tests for the retired command or implementation."
  tests/test_autoclose_sweep.py: "Remove autoclose sweep tests for the retired command or implementation."
  tests/test_blackboard.py: "Verify blackboard under the local-file model and retire obsolete expectations."
  tests/test_blocker_reminders.py: "Verify blocker reminders under the local-file model and retire obsolete expectations."
  tests/test_bootstrap_workflow_review_sections.py: "Verify bootstrap workflow review sections under the local-file model and retire\
    \ obsolete expectations."
  tests/test_branchcleanup.py: "Remove branchcleanup tests for the retired command or implementation."
  tests/test_branchsweep.py: "Remove branchsweep tests for the retired command or implementation."
  tests/test_checkouts.py: "Remove checkouts tests for the retired command or implementation."
  tests/test_cli.py: "Verify cli under the local-file model and retire obsolete expectations."
  tests/test_code_implement_skill.py: "Verify code implement skill under the local-file model and retire obsolete expectations."
  tests/test_commands.py: "Verify commands under the local-file model and retire obsolete expectations."
  tests/test_compose.py: "Verify compose under the local-file model and retire obsolete expectations."
  tests/test_config.py: "Verify config under the local-file model and retire obsolete expectations."
  tests/test_create.py: "Verify create under the local-file model and retire obsolete expectations."
  tests/test_done_marker_emission.py: "Verify done marker emission under the local-file model and retire obsolete expectations."
  tests/test_dream_validate_drift.py: "Verify dream validate drift under the local-file model and retire obsolete expectations."
  tests/test_dream_worker_templates.py: "Verify dream worker templates under the local-file model and retire obsolete expectations."
  tests/test_edge_distribution.py: "Verify edge distribution under the local-file model and retire obsolete expectations."
  tests/test_env_isolation.py: "Verify env isolation under the local-file model and retire obsolete expectations."
  tests/test_git.py: "Remove git tests for the retired command or implementation."
  tests/test_init.py: "Verify init under the local-file model and retire obsolete expectations."
  tests/test_launch.py: "Verify launch under the local-file model and retire obsolete expectations."
  tests/test_launch_restart.py: "Verify launch restart under the local-file model and retire obsolete expectations."
  tests/test_launch_script.py: "Verify launch script under the local-file model and retire obsolete expectations."
  tests/test_layout_contexts.py: "Verify layout contexts under the local-file model and retire obsolete expectations."
  tests/test_log_retention.py: "Verify log retention under the local-file model and retire obsolete expectations."
  tests/test_logfile.py: "Verify logfile under the local-file model and retire obsolete expectations."
  tests/test_mark.py: "Verify mark under the local-file model and retire obsolete expectations."
  tests/test_megalaunch.py: "Verify megalaunch under the local-file model and retire obsolete expectations."
  tests/test_notification_messages.py: "Verify notification messages under the local-file model and retire obsolete expectations."
  tests/test_open_pr.py: "Verify open pr under the local-file model and retire obsolete expectations."
  tests/test_open_pr_command.py: "Remove open pr command tests for the retired command or implementation."
  tests/test_oscompat.py: "Verify oscompat under the local-file model and retire obsolete expectations."
  tests/test_owner.py: "Verify owner under the local-file model and retire obsolete expectations."
  tests/test_packaging.py: "Verify packaging under the local-file model and retire obsolete expectations."
  tests/test_paths.py: "Verify paths under the local-file model and retire obsolete expectations."
  tests/test_period_state.py: "Verify period state under the local-file model and retire obsolete expectations."
  tests/test_primitives.py: "Verify primitives under the local-file model and retire obsolete expectations."
  tests/test_publish_state.py: "Remove publish state tests for the retired command or implementation."
  tests/test_recurring.py: "Verify recurring under the local-file model and retire obsolete expectations."
  tests/test_recurring_activity.py: "Verify recurring activity under the local-file model and retire obsolete expectations."
  tests/test_recurring_autofix.py: "Verify recurring autofix under the local-file model and retire obsolete expectations."
  tests/test_recurring_clone.py: "Verify recurring clone under the local-file model and retire obsolete expectations."
  tests/test_recurring_shims.py: "Verify recurring shims under the local-file model and retire obsolete expectations."
  tests/test_recurring_state.py: "Verify recurring state under the local-file model and retire obsolete expectations."
  tests/test_repl_supervisor.py: "Verify repl supervisor under the local-file model and retire obsolete expectations."
  tests/test_repl_supervisor_nt.py: "Verify repl supervisor nt under the local-file model and retire obsolete expectations."
  tests/test_retire.py: "Verify retire under the local-file model and retire obsolete expectations."
  tests/test_retire_worklist.py: "Remove retire worklist tests for the retired command or implementation."
  tests/test_retro_skill_template.py: "Verify retro skill template under the local-file model and retire obsolete expectations."
  tests/test_review_conflict.py: "Remove review conflict tests for the retired command or implementation."
  tests/test_runner.py: "Verify runner under the local-file model and retire obsolete expectations."
  tests/test_secret.py: "Verify secret under the local-file model and retire obsolete expectations."
  tests/test_seed_local_config.py: "Keep clone seeding beside the optional sandbox procedure."
  tests/test_skill_manager.py: "Verify skill manager under the local-file model and retire obsolete expectations."
  tests/test_skill_update.py: "Verify skill update under the local-file model and retire obsolete expectations."
  tests/test_smoke.py: "Verify smoke under the local-file model and retire obsolete expectations."
  tests/test_status.py: "Verify status under the local-file model and retire obsolete expectations."
  tests/test_telemetry.py: "Verify telemetry under the local-file model and retire obsolete expectations."
  tests/test_ticket.py: "Verify ticket under the local-file model and retire obsolete expectations."
  tests/test_trim_log.py: "Verify trim log under the local-file model and retire obsolete expectations."
  tests/test_uninstall.py: "Verify uninstall under the local-file model and retire obsolete expectations."
  tests/test_upstream_coga.py: "Verify upstream coga under the local-file model and retire obsolete expectations."
  tests/test_validate.py: "Verify validate under the local-file model and retire obsolete expectations."
  tests/test_views.py: "Verify views under the local-file model and retire obsolete expectations."
  tests/test_workspace_discovery.py: "Verify workspace discovery under the local-file model and retire obsolete expectations."
  docs/contexts/coga-dev/testing/SKILL.md: Update the test harness guidance for the local-file model.
  docs/contexts/coga-dev/testing/agent-trials/SKILL.md: Describe how to handle private trial artifacts with plain Git.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/pr-publication/preparation/SKILL.md: Document how the PR step retains evidence across ticket and audit-log commits.
  src/coga/resources/templates/coga/recurring/phone-home/ticket.md: Describe the recurring job's atomic local reservation.
review:
  reviewer: codex
  kind: self
  status: passed
  head: d8848841067e9c7cb9369107bf3d2b0177ee169b
  base: cea3f2980fdbb82997149d67d91198e845f1d761
  detail: Direct Codex review against the recorded base, in a separate peer-review session from the Codex implementation. Reviewed lifecycle, launch dispatch, legacy snapshots and Git failure paths, then committed the PR evidence correction and documentation updates. Linux verification passed. The owner confirmed that skill management should continue invoking gh skill from src/coga/skill_manager.py. Approved this head with that exception recorded in the ticket. Windows and macOS verification is deferred to release. Separate uncommitted parser edits were preserved and excluded from the reviewed tree.
checks:
- command: cd /tmp/coga-v103-verified-tip && PYTHONPATH=/tmp/coga-v103-verified-tip/src /home/n/Code/coga/.venv/bin/python -m pytest
  status: passed
  head: d8848841067e9c7cb9369107bf3d2b0177ee169b
  base: cea3f2980fdbb82997149d67d91198e845f1d761
  detail: Pop!_OS 24.04 LTS, Python 3.12.12. 3150 passed and 29 skipped in 168.12 seconds.
- command: cd /tmp/coga-v103-verified-tip && env -u SLACK_WEBHOOK_URL PYTHONPATH=/tmp/coga-v103-verified-tip/src /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json
  status: passed
  head: d8848841067e9c7cb9369107bf3d2b0177ee169b
  base: cea3f2980fdbb82997149d67d91198e845f1d761
  detail: Repository validation returned zero errors and 112 warnings.
- command: cd /tmp/coga-v103-verified-tip/tests/fixtures/seeded-repo && env -u SLACK_WEBHOOK_URL PYTHONPATH=/tmp/coga-v103-verified-tip/src /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json
  status: passed
  head: d8848841067e9c7cb9369107bf3d2b0177ee169b
  base: cea3f2980fdbb82997149d67d91198e845f1d761
  detail: Seeded fixture validation returned zero errors and zero warnings.
- command: git diff --check cea3f2980fdbb82997149d67d91198e845f1d761 d8848841067e9c7cb9369107bf3d2b0177ee169b
  status: passed
  head: d8848841067e9c7cb9369107bf3d2b0177ee169b
  base: cea3f2980fdbb82997149d67d91198e845f1d761
  detail: No whitespace errors.
```
