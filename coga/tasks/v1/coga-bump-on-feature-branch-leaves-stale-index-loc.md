---
title: coga bump on feature branch leaves stale index.lock and blocks syncing with
  main
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
step: 3 (review-design)
agent: claude
---

## Description

A `coga bump` run from a **feature-branch** checkout published the ticket and
log to `origin/main` correctly, but left the checkout broken in two ways:

1. A stale, empty `.git/index.lock` that no process owned. Every later git
   write failed. `git stash create` exited 1 with no message, and
   `git merge origin/main` printed only `fatal: stash failed`. The silent stash
   failure made it look like a coga dirty-state problem instead of a lock
   problem.
2. The published ticket and log edits stayed dirty (` M`) in the feature
   checkout, byte-identical to `origin/main`. That dirt blocks
   `git merge`/`git rebase` of `origin/main` until someone runs
   `git checkout -- <paths>` by hand.

Find which coga publication path leaves `index.lock` behind and fix it. Likely
candidates are the feature-branch publication plumbing or the
advance-local-control step, possibly when the process is killed or races an
agent session teardown. Then remove the manual sync burden from item 2.

Done when:

- The root cause of the stale lock is identified, with a regression test. No
  publication path can exit (normally, on error, or on signal/teardown) while
  leaving a coga-created `index.lock`.
- One of these holds: coga restores published-and-identical files in a
  feature checkout after publishing, or `coga/checkouts/reconciliation`
  documents the exact one-command way to sync a feature branch with control
  and `coga status` points at it when that dirt is present. The design step
  chooses between them.

**Design choice (owner-confirmed in the design session): the
documentation + `coga status` route.** A feature checkout keeps its
published ticket and log dirty on purpose. Launch projects the current
control ticket onto feature branches, and `coga/state-publication`
("Control versus feature checkouts") says so. Automatically restoring
those files to HEAD would make later commands in that checkout read a stale
ticket. The owner also chose to have `coga status` report a present
`index.lock`.

### Root cause

This was inferred from the code and the evidence timings, not reproduced
live. The chain:

1. `coga bump` (and `mark done`, `mark canceled`, `block`) calls
   `emit_done_marker()` (`src/coga/repl_supervisor.py`) *inside* the command
   handler (`src/coga/commands/bump.py`, `bump()`).
   `cli.main()` (`src/coga/cli.py`) only afterwards runs the end-of-command
   boundary: `_sweep_coga_state()` → `git.sync_coga_state()`, then
   `_warn_unpublished_log_lines()`. So coga's own git work keeps running
   after the supervisor has been told to tear the session down.
2. The supervisor (`run_with_done_marker()`, `_trigger_term()` in
   `src/coga/repl_supervisor.py`) polls the sentinel every 0.25 s. It sends
   `SIGTERM` to the agent's process group and escalates to `SIGKILL` after
   `_KILL_GRACE_SECONDS` (2 s). An agent CLI may also kill its tool
   subprocesses outright on shutdown. The `coga bump` process is a
   descendant of the agent, so it and its git children die mid-sweep.
3. The sweep's candidate selection runs `git status` against the
   **checkout's real index** (`git._candidates()` → `_dirty_paths()`).
   `git status` opportunistically refreshes the index and writes it under
   `<git-dir>/index.lock` unless `GIT_OPTIONAL_LOCKS=0`. `git._git_env()`
   does not set that variable. Git removes its lock on
   SIGTERM/SIGINT/SIGHUP/SIGPIPE, but **SIGKILL leaves the 0-byte lock**.
   That matches the evidence: a 0-byte lock whose mtime equals the session's
   `ended_at`. The ticket landed at :36, before the marker. The log commit at
   :39 came from the supervisor's own teardown publication, which uses
   scratch indexes and tolerates a stale lock (status just skips its
   optional write), so nothing noticed.

Publication's deliberate index writes (`_build_tree()`,
`_write_published()`) already use a scratch `GIT_INDEX_FILE`. The
real-index writes in `_stage_landed()` (`git add` / `update-index`) and the
`read-tree -m -u` in `_realign_control()` / `_apply_preparation()` run only
when this checkout holds the control branch, so they cannot be what fires
on a feature branch.

### Acceptance criteria

- [ ] Every git subprocess coga starts through `git._git_env()` (that is,
      `git.run_git()` / `git._run()`) runs with `GIT_OPTIONAL_LOCKS=0`. This
      is forced: a value already in the environment is overridden.
- [ ] Other in-package git callers that can run during a supervised
      session and touch a checkout either route through `git._git_env()` or
      set `GIT_OPTIONAL_LOCKS=0` themselves. At minimum this covers the
      `subprocess` git calls in `src/coga/launch.py` (the checkout snapshot
      that runs `git status --short --branch`), `src/coga/branchcleanup.py`,
      and `src/coga/validate.py`. The implementer lists any caller
      deliberately left alone, with the reason, on the blackboard.
- [ ] `emit_done_marker()` no longer signals the supervisor before the
      end-of-command boundary when it is called under `cli.main()`. The
      marker is written only after `_sweep_coga_state()` and
      `_warn_unpublished_log_lines()` have both returned, on every path where
      the command requested it: a normal return, a `SystemExit`, or another
      exception that propagates after the request. Outside `cli.main()` (a
      direct library or test call) it still writes immediately.
- [ ] Regression tests in `tests/test_git.py` (or a new focused module):
  - (a) Use a real temporary repo with a bare remote, a feature-branch
        checkout, a dirty ticket, and a stat-dirty tracked file (touched so
        its mtime is newer than the index entry). Run
        `git.sync_coga_state()` from the feature checkout. Assert that every
        recorded git call ran with `GIT_OPTIONAL_LOCKS=0` and that the real
        index file was not rewritten (its mtime and inode are unchanged). The
        test must fail on current `main`. See Proposed shape, step 6.
  - (b) Through `cli.main()` with `COGA_DONE_SENTINEL` set and a monkeypatched
        `git.sync_coga_state` and `cli._warn_unpublished_log_lines` that
        record call order: running `coga bump` on a ticket at a non-final
        step writes the sentinel only after both have run. A test that the
        marker is still written when the sweep raises. The test must fail on
        current `main`.
  - (c) The existing supervisor/bump tests in `tests/test_repl_supervisor.py`
        and the bump tests still pass, with no added teardown hang.
- [ ] `coga status` (`src/coga/views.py`, beside `_warn_if_control_ahead()`)
      prints, to stderr in yellow, one **feature-sync hint** when HEAD is not
      the control branch and every dirty or untracked file under
      `git.coga_root_paths(cfg)` is byte-identical (clean-filtered blob id)
      to the local `refs/remotes/<remote>/<control>` copy. The hint gives the
      exact command with shell-quoted paths, and omits the parts that have
      no paths:
      `git checkout -- <tracked…> && rm -- <untracked…> && git merge --no-edit <remote>/<control>`.
      It also names the reconciliation section. When some dirty Coga-root
      files differ from control, it prints no command. Instead it names the
      differing files and says to publish them first
      (`coga run publish-state`) or reconcile per the section. It prints
      nothing on a control checkout, with no dirt, with git disabled, or when
      the remote-tracking ref is absent. No network, fail-open to silence on
      `GitError`, the same posture as `stale_coga_task_rels()`.
- [ ] `coga status` prints one stderr warning when
      `<absolute-git-dir>/index.lock` exists (per-worktree git dir for a
      linked worktree). It names the path and says: confirm no git process
      is using this checkout, then remove it. Coga never deletes it.
- [ ] Tests for both status lines in `tests/test_views.py` /
      `tests/test_status.py`. Cover these cases: all-identical (command
      printed, including an untracked identical ticket), one-differs (no
      command), a control checkout (silent), and a present lock (warning).
      The `conftest.py` autouse stub of `stale_coga_task_rels` shows the
      pattern for keeping other status tests quiet.
- [ ] Docs, updated in the same PR:
  - `coga/checkouts/reconciliation`: a new `## Sync a feature branch with
    control` section. It states that published Coga state stays dirty in a
    feature checkout by design, gives the exact command above, and gives the
    precondition (every dirty Coga-root path equals control, which
    `coga status` checks). It says why `git merge --autostash` is not enough
    (an identical untracked ticket still blocks the merge), recommends merge
    over rebase for an already-pushed branch, and says what to do when files
    differ.
  - `coga/state-publication`, "Control versus feature checkouts": replace
    "`coga status` warns when control is ahead of the local copy" with a
    sentence linking to the new reconciliation section and the status hint.
    Add a short note that coga's git calls run without optional index locks
    and that session-ending commands signal the supervisor only after their
    end-of-command publication.
  - `coga/launch` (or whichever topic owns the done-marker contract; find
    it with `grep -rn "COGA_DONE_SENTINEL\|done marker"` under
    `src/coga/resources/templates/coga/bootstrap/contexts`): record that the
    marker is emitted after the end-of-command boundary.
- [ ] `python -m pytest` passes. `coga validate --json` is clean.

### Proposed shape

1. **`src/coga/git.py`, `_git_env()`**: set
   `env["GIT_OPTIONAL_LOCKS"] = "0"` after copying `os.environ` and before
   applying `extra`. Update the module docstring's invariants with one line:
   coga never takes Git's optional index lock.
2. **Other git callers**: route the `launch.py` checkout-snapshot argv,
   `branchcleanup.py`'s runner, and `validate.py`'s runner through
   `git._git_env()` (pass `env=`), or add the variable locally where
   importing `git` would create a cycle.
3. **Deferred done marker** (`src/coga/repl_supervisor.py`, `src/coga/cli.py`):
   - Add a module-level `ContextVar` in `repl_supervisor`, for example
     `_deferred_done: ContextVar[list[str] | None]`, default `None`.
   - `emit_done_marker(session_id)`: if the var holds a list, append the
     marker and return. Otherwise behave as today.
   - Add `flush_deferred_done_marker()`, which writes the last requested
     marker through the existing sentinel-write path.
   - In `cli.main()`, set the var to `[]` next to `withheld_token`. In the
     outer `finally`, after `_warn_unpublished_log_lines()`, call the flush
     in its own `try/finally` so a failing warning cannot suppress it, then
     reset the token.
   - Commands keep calling `emit_done_marker()` exactly where they do now,
     so no command handler changes.
4. **Status lines** (`src/coga/git.py` + `src/coga/views.py`):
   - Add `git.feature_sync_plan(cfg) -> FeatureSyncPlan | None`, a frozen
     dataclass with `tracked: list[str]`, `untracked: list[str]`,
     `differing: list[str]`, and `target: str` (`<remote>/<control>`).
   - Use `git status --porcelain=v2 -z --untracked-files=all -- <roots>` for
     dirty and untracked paths (optional locks are now off).
   - Compare `_hash_blob(root, working_bytes, rel)` with
     `_blob_oid(root, remote_ref, rel)`. A deleted path counts as identical
     only when control also lacks it.
   - Return `None` on a control checkout, when there is no dirt, or on
     `GitError`.
   - Add `git.stale_index_lock(cfg) -> Path | None`, using
     `_scratch_dir(root) / "index.lock"` (the absolute git dir).
   - In `views.render_status()`, call two new warning helpers next to
     `_warn_if_control_ahead()`. Build the command with `shlex.quote`.
5. **Docs** as listed in the acceptance criteria. Edit the package copies
   under `src/coga/resources/templates/coga/bootstrap/contexts/coga/`.
6. **Tests** as listed. For (a), the simplest robust form is a structural
   assertion: monkeypatch `git._run` to record `(argv, env)` for every call
   made by a feature-branch `git.publish()`. Assert that every call has
   `GIT_OPTIONAL_LOCKS == "0"` in its effective env, and that every argv
   whose subcommand writes an index (`status`, `add`, `update-index`,
   `read-tree`, `rm`, `checkout`, `stash`, `merge`) either carries
   `GIT_INDEX_FILE` or is `status`/`diff` with optional locks off. Add a
   real-git check as well: after a feature-branch publish with a touched
   (stat-dirty) file, the index mtime is unchanged. That proves the real
   index was not rewritten.

### Out of scope (design)

- Deleting any `index.lock`, coga-created or not. Detection and reporting
  only.
- Automatically restoring, committing, or merging published files in a
  feature checkout (the rejected route), and any new `coga` command for
  syncing. The microkernel rule would put one at the edge anyway.
- Changing `_KILL_GRACE_SECONDS`, the supervisor's signal escalation, or how
  agent CLIs kill their tool subprocesses.
- Making the deliberate control-checkout real-index writes (`_stage_landed`,
  `read-tree -m -u`) SIGKILL-proof. Nothing can make a lock-holding write
  survive SIGKILL. The deferred marker removes coga's own teardown race for
  them, and an external kill (a human Ctrl-C escalated to SIGKILL, the
  idle/max-session timeout) is not addressed.
- Cleaning up leftover scratch-index files (`coga-git-index-*`) in the git
  dir.

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

### Evidence (observed in another repo, 2026-11-10)

- coga 0.4.1, git 2.43.0, Linux. A Codex agent (`launch_args = "--no-daemon"`)
  ran `coga bump` at the end of an attended implement step, from a
  `coga/<slug>-<hex>` feature branch. Control got the ticket commit at 15:16:36
  and the log commit at 15:16:39.
- `.git/index.lock`: 0 bytes, mtime 15:16:38.435. That is inside the publish
  window and equal to the session's `ended_at` in the log usage record. So
  the lock was created during publication, at the moment the agent session
  ended. Afterwards no git process and no coga process had the repo as cwd
  (`pgrep -x git`, `lsof`).
- Afterwards, the feature checkout had ` M coga/log.md` and ` M coga/tasks/<slug>.md`,
  both identical to `origin/main` (`git diff --quiet origin/main -- <paths>`).
- Running `coga create` from the same feature checkout reproduced item 2
  immediately: it published to control, left `coga/log.md` dirty, and left the
  new ticket untracked locally. So any feature-branch coga command makes the
  next `git merge origin/main` need a manual restore.

Manual recovery used: confirm no owning process and `rm .git/index.lock`;
check that the dirty coga files equal control, then `git checkout -- <paths>`;
`git merge --no-edit origin/main`. Use merge, not rebase, so the already-pushed
branch doesn't need a force-push.

### Where to look

- Publication code: `src/coga/git.py` and the state-publication/sync modules
  it calls. Look for any git invocation that writes the **checkout's** index
  (`git add`, `read-tree`, `checkout`, `update-index`, `stash`) during a
  feature-branch publish. A lock in the checkout's `.git` means coga touched
  the real index, not a temporary `GIT_INDEX_FILE`. Check whether that
  subprocess can be killed mid-write: the supervisor tearing down the agent
  at bump, a SIGTERM/SIGHUP to the process group, or a timeout.
- `coga/state-publication` (cited, not attached;
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md`):
  read "Control versus feature checkouts", "Strict publication on demand", and
  "Recovering a failed publication". Update it in the same PR if behaviour
  changes.
- `coga/checkouts/reconciliation` (cited, not attached;
  `.../contexts/coga/checkouts/reconciliation/SKILL.md`): edit it if the design
  picks the documentation route.
- Related history: `v1/06-fix-coga-git-sync-failures-that-leave-main-diverge`
  (done) covered divergence of local main, not stale locks or feature-checkout
  dirt.

### Out of scope

- Automatically deleting an `index.lock` that coga did not create. Another
  git process may own it. At most, detect it and report a clear message.


<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design notes (design step, 2026-11-10)

- Spec is under `## Description` (Root cause / Acceptance criteria /
  Proposed shape / Out of scope (design)).
- Owner decisions taken live in the attended design session:
  (1) the documentation + `coga status` hint route, not auto-restore;
  (2) `coga status` also warns about a present `index.lock`.
- I checked on git 2.43 in a scratch repo:
  `git merge --autostash --no-edit origin/main` cleans up identical
  tracked dirt, but an untracked ticket identical to control still aborts
  the merge ("untracked working tree files would be overwritten"). That is
  why the sync command needs `rm -- <untracked>` and is a `&&` chain, not a
  single git command.
- The root cause is inferred, not reproduced live. The evidence's lock
  mtime equals `ended_at`, and the ticket commit (:36) precedes the lock
  (:38.4), which fits a kill during the post-marker sweep. Whether the kill
  came from our 2 s SIGKILL escalation or from Codex killing its tool
  subprocesses is unknown. The fix covers both.

## Open Questions

- Teardown latency: deferring the done marker means a supervised session
  stays up until the end-of-command sweep finishes (normally one fetch and
  push, a few seconds; longer offline, bounded by git's own timeouts). Is
  that acceptable? The alternative is to skip the sweep entirely in a
  supervised session (`COGA_SUPERVISED`), because the supervisor publishes
  after the child exits anyway. That is faster, but it changes the
  documented "every mutating command sweeps" contract.
- Should the feature-sync hint also appear in launch's end-of-session
  output for feature-branch steps (implement / address-pr-comments)? The
  spec limits it to `coga status`, as the ticket asked.

## Evaluator review

2026-11-10 — **Not ready for implementation until the must-fix findings are
resolved or explicitly dispositioned at owner review.** Reviewed cold against
fetched `origin/main` at `fba00b9bfd9ec4b2f6643872633a6366365a06c8`.
The ticket's requirements are in the composed Description/Context regions;
its frozen workflow correctly hands this review to the owner. The selected
documentation/status route preserves the existing feature-checkout contract,
and the optional-lock mitigation addresses a verified real-index write.

### Must fix before implementation

1. **P1 — Deferring the sentinel does not cover Coga's other completion
   trigger.** `src/coga/launch.py::_terminal_status_probe` observes a published
   `done`/`canceled` ticket and returns terminal after five stable seconds.
   Both `repl_supervisor.py::run_with_done_marker` and
   `repl_supervisor_nt.py::run` act on that callback independently of the
   sentinel. A final bump or terminal mark can publish its ticket, then spend
   more than five seconds in the remaining command/publication boundary and
   still be killed before the deferred marker. `git._run` supplies no
   subprocess timeout; the blackboard's claim that Git bounds this delay is
   not an established guarantee. Optional-lock suppression protects the
   feature index, but this still exposes deliberate index writes in a control
   checkout (including a separate control worktree advanced by publication).
   Resolve the claimed guarantee: coordinate completion with this backstop,
   or explicitly retain and document this race as a narrower scope decision.
   Reconcile the opening “No publication path ... on signal/teardown” promise
   with the explicit external-kill exclusions. Add a final-transition test
   with a delayed boundary and the terminal probe active; the specified
   non-final bump test cannot exercise this path. Existing evidence:
   `tests/test_launch.py::test_terminal_status_probe_waits_for_publication_and_caches_blobs`
   and the terminal-ticket tests in both supervisor modules.

2. **P1 — Blob equality is insufficient proof for the destructive sync
   hint, and the command does not handle all selected index states.**
   `git checkout -- <path>` restores from the index, not HEAD. In a scratch
   repo, a staged deletion whose working path and control path are both
   absent satisfies the proposed equality rule, but that command exits 1
   with “pathspec ... did not match”; the merge never runs. A mode-only
   executable-bit change also satisfies the blob check, but the command
   removes that unpublished change. Publication explicitly preserves modes
   and distinct staged drafts (`coga/state-publication`, “Control versus
   feature checkouts”; `src/coga/git.py::_stage_landed`,
   `_plan_preparation`, `_regular_working_file`, `_tree_entry`). Define the
   supported index states and prove modes/type as well as content before
   recommending cleanup. Either restrict the shortcut to provably safe
   unstaged regular-file states and route the rest to reconciliation, or
   specify restoration of staged additions/deletions/renames without losing
   unique staged content. Do not simply switch to a forced HEAD restore.
   Require tests for staged deletion, a distinct staged draft, and a
   mode-only change, alongside the proposed identical-untracked test.

3. **P2 — The proposed status probe writes Git objects.**
   `src/coga/git.py::_hash_blob` runs `hash-object -w`; a scratch probe
   confirmed that previously absent working bytes become a stored object.
   This violates the read-only status contract and can silently suppress the
   differing-files warning when the object store is read-only. Use the
   already-existing `_blob_id`, which applies the same clean filters without
   `-w`, and test that differing-file diagnostics require no object writes.

4. **P2 — Make the recovery command valid for its invocation directory and
   supported shell.** The plan returns Git-root-relative paths but prints
   commands relative to the user's cwd; `coga status` can run below the Git
   root. Establish the root explicitly in the hint/docs or anchor every
   operation. `shlex.quote`, POSIX `rm --`, and the proposed chain also do
   not supply the native Windows PowerShell recovery contract. Existing
   diagnostics in `src/coga/launch.py::_checkout_refusal_message` name the
   root and shell, and `_checkout_command` has a PowerShell quoting test.
   Specify supported shell rendering, literal Git path handling, and tests
   for a nested cwd and paths containing spaces/apostrophes. This work is
   platform-sensitive under `coga-dev/testing`, “Verification tiers and
   receipts”: retain the required native Windows full-suite receipt before
   merge, in addition to Linux verification.

### Optional recommendations

- Audit actual subprocesses rather than the named launch “snapshot”:
  `launch._checkout_refusal_message` only prints the `git status --short
  --branch` argv. Actual bypasses include
  `recurring_runner._path_has_local_changes`, `branchsweep._git`, and
  `launch._align_recorded_assist_checkout`. The broad caller-audit acceptance
  criterion already permits fixing these; correct the misleading example.
- For the structural regression, inspect the environment passed to
  `subprocess.run`: `_run` receives an optional overlay and constructs the
  effective environment internally. Force optional locks off after overlays
  if the invariant is intended to hold for explicit `env=` values too.
- The user-facing done-signal owner is
  `coga/recurring/scheduling/inactivity`, “Session completion and liveness”;
  `coga-dev/internals/agent-spawn`, “The supervisor”, owns its implementation
  description. Update those owners and link from launch/publication. Keeping
  the new hint limited to status is consistent with the selected scope.

### Verification and handoff

- Scratch real-Git probes confirmed that current feature-branch
  `sync_coga_state` performs a real-index `status` call and changes the
  index inode and mtime with optional locks enabled. Repeating publication
  with `GIT_OPTIONAL_LOCKS=0` preserved both. This verifies the vulnerable
  path and mitigation, not the exact kill source in the reported incident.
  An isolated `cli.main` probe also observed the sentinel already present
  during both the sweep and exit warning. The deletion, mode, and object
  write probes above used disposable repositories only.
- Targeted existing tests: **24 passed**, 719 deselected. Exact command:
  `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_git.py tests/test_launch.py tests/test_repl_supervisor.py tests/test_repl_supervisor_nt.py tests/test_views.py -k 'terminal_status_probe or terminal_ticket_stops or prepare_refuses_staged_content or publish_then_prepare_preserves_distinct_staged_renames or staged_union_log_draft or checkout_command_quotes_powershell_literals or render_status_warns_when_control_ref_ahead'`.
  The first attempt with ambient `python` could not set up tests because
  `tomlkit` was missing; the repository venv supplied the successful receipt.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate
  --json` exited 0: 107 OK, ten pre-existing warnings on other tickets,
  no errors and no finding for this ticket. No full-suite or native Windows
  receipt is claimed for this design-only review.
- No ticket-body, frontmatter, source, test, branch, or PR changes were made.
  Owner review should resolve the four findings and the existing latency
  question before advancing to implementation.
