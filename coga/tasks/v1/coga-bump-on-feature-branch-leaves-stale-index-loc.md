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
step: 6 (open-pr)
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

## Dev

pr: https://github.com/FastJVM/coga/pull/1194
branch: coga/v1-coga-bump-on-feature-branch-leaves-stale-inde-5a3760


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

## Owner dispositions (implement session, 2026-11-10)

Taken live with the owner before implementation, resolving the evaluator's
must-fix findings:

1. Terminal-probe race: **pending-marker guard.** When `cli.main` defers the
   done marker it writes `<sentinel>.pending` holding its PID; both
   supervisors skip the terminal-status backstop while that file exists and
   the PID is alive. Add a final-transition test with a delayed boundary.
2. Sync hint scope: **restrict to provably safe states.** Command only when
   every dirty Coga-root path is a regular file that is unstaged-only
   (index == HEAD) with working blob *and mode* equal to control, or
   untracked and equal to control. Anything staged, mode-different,
   non-regular, or deleted is listed for manual reconciliation; no command.
3. Object writes: use `git._blob_id` (no `-w`), not `_hash_blob`.
4. Rendering: anchor with `git -C <root>` and absolute removal paths;
   POSIX via `shlex`, native Windows via PowerShell literal quoting.
   Native Windows full-suite receipt still required before merge.

## Implementation handoff (implement step, 2026-11-10)

What changed (all on the feature branch):

- `git._git_env()` forces `GIT_OPTIONAL_LOCKS=0` after any overlay; module
  docstring gains the "No optional locks" invariant.
- Direct git subprocess callers now pass `env=git._git_env()`:
  `launch._align_recorded_assist_checkout` ancestry check (`merge-base`),
  `recurring_runner` (`remote get-url`, `_path_has_local_changes` status,
  `_ref_has_path`, `_show_path`), `branchsweep` (`_verbatim_patch_ids`,
  `_git`), `branchcleanup._git` (keeps `LC_ALL=C`), `validate._git_output`,
  `open_pr._run` and `skill_manager.run_subprocess` (git argv only; they
  also run `gh`). `launch._checkout_refusal_message` only *prints* argv.
  **Deliberately left alone:** `dream_validate_drift` (dream's own
  commit/push script, outside the end-of-command boundary, deliberate index
  writes), `recurring_activity` / `retire_worklist` / `commands/update` /
  `github_preflight` (ref-only subcommands: rev-parse, log, for-each-ref,
  ls-tree, diff between refs, push --dry-run; none takes an index lock).
- Deferred done marker: `repl_supervisor.deferred_done_marker()` (a
  context manager over a `ContextVar`) wraps all of `cli.main`'s dispatch
  and boundary; `emit_done_marker` appends inside it and the last request is
  written after the sweep and log warning return, on success, SystemExit, or
  exception. Command handlers are unchanged.
- Pending guard (owner disposition 1): the same context manager writes
  `<sentinel>.pending-<pid>` for the command's lifetime when the sentinel env
  is non-empty (from boundary *entry*, not first request, so slow work
  before `emit_done_marker` is covered too). Both supervisors skip the
  terminal-status probe while `completion_pending()` finds a live PID.
  `remove_sentinel_dir()` clears the private dir on every path.
  Known limit: a SIGKILLed coga that stays an unreaped zombie still reads
  as alive on POSIX until reaped; idle/max-session backstops still apply.
- `git.feature_sync_plan()` / `FeatureSyncPlan` (disposition 2 + 3):
  porcelain v2 over the Coga roots with literal pathspecs; safe only for
  `.M` regular files (index == HEAD) and untracked regular files whose
  `_blob_id` (no `-w`) and mode equal the remote-tracking control entry.
  Everything else goes to `manual` with a reason.
- `git.stale_index_lock()` (absolute git dir), `views._warn_if_index_locked`
  and `views._hint_feature_sync` next to `_warn_if_control_ahead`; output
  unwrapped and markup-free so paths copy cleanly.
- Rendering (disposition 4): `oscompat.shell_command` / `shell_chain`
  (POSIX `&&`; PowerShell nested `if ($?) { … }`, `Remove-Item
  -LiteralPath` per file). `launch._checkout_command` now delegates to
  `shell_command`; its PowerShell bare-word rule no longer lets a leading
  `@` (splatting) through unquoted.
- Docs: `coga/checkouts/reconciliation` new "Sync a feature branch with
  control"; `coga/state-publication` feature paragraph + "Index locks";
  `coga/recurring/scheduling/inactivity` (done-signal owner) records the
  deferred write and the pending guard; `coga-dev/internals/agent-spawn`
  names the implementation. `coga/launch` does not own the done-marker
  contract, so it is unchanged.

Still required before merge: **native Windows full-suite receipt**
(platform-sensitive: supervisor + PowerShell rendering). Not run here.

Test fixture change: `tests/fixtures/authoring_cancellation.py`'s
`interrupted` variant assumed the old ordering (marker written before the
sweep, then teardown kills the hung sweep). It now releases the held marker
explicitly mid-sweep to model an external stop; the finalizer guarantees
it checks are unchanged.

Verification (Linux, git 2.43, head `d83726210c57` on base `7e342fbfa59e`):
full suite **4736 passed, 33 skipped, 0 failed**. New regression tests were
confirmed to fail with the fix reverted (optional-lock env and index stat;
deferred marker ordering). `coga validate --json`: exit 0, 107 OK, the same
ten pre-existing warnings.

Pre-existing failure fixed at the owner's request (separate commit): main's
`docs/contexts/coga-dev/internals/branch-sweep/SKILL.md` linked to
`coga/checkout-cleanup/branch-sweep#review-and-release-a-retained-local-draft`,
a section that exists only on the unmerged
`branch-sweep-never-releases-a-merged-pr-s-stale-ne` branch (`c044ed403`).
The coga-dev doc edit reached main early through a state sweep
(`0e04ded0c Sync coga state`; the pre-review publication hazard). The link
now targets the topic without the anchor. That ticket's PR may restore the
anchor once its section merges.

## Peer review

Codex **completed** an independent direct review of all 25 diff paths at
head `4ee4d7e738f1f8f30b3ef2dc530e846eee0f4d17` against base
`db1442ea32e5834ce53fe8e62ab3654be57132b4` (fresh fetched `origin/main`).
Implementation was by Claude; this fresh Codex session did not author it.
No must-fix code findings. Reviewed forced optional-lock environments,
real-index isolation, boundary exception ordering, both supervisors' live-PID
pending guards, conservative content/mode/index-state proofs, literal paths,
POSIX/PowerShell command rendering, caller-audit exclusions, tests and owners.
The branch was rebased unconditionally onto fetched main and force-pushed
with lease; the projected ticket was copied, byte-verified and restored
unstaged around the rebase. No source changes were needed.

Manual verification in disposable repos:
- Real PTY at 80x24 and 120x40: lock warning and feature-sync hint visible;
  executing the exact printed command from a nested cwd handled an apostrophe
  and square brackets in an untracked filename and left a clean checkout at
  `origin/main`.
- Final `bump` with the real terminal-status probe and a seven-second delayed
  end-of-command sweep: the boundary completed, then the sentinel was observed;
  clean completion in 7.49s and no index lock. This also exercises the final
  transition/backstop interaction beyond the five-second terminal window.
- Validation: 107 OK, ten existing warnings, zero errors. Full Linux suite:
  `PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest -q -p no:cacheprovider`
  completed: **4736 passed, 33 skipped, zero failures in 754.25s**.
  Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.12.12,
  at the head/base above. The earlier implement receipts remain historical.
- Final fetch confirmed `origin/main` still at the reviewed base; branch
  pushed at the reviewed head, `git diff --check` passed. Only this ticket
  is dirty; no source edits or additional commits were needed.
- Additional caller-audit exclusions: `config.py` and the packaged
  `seed_local_config.py` use only `ls-files`, `check-ignore`, and ref/root
  discovery (no optional index refresh); `commands/init.py` owns deliberate
  installation index writes outside session-ending publication. The other
  inspected subprocess-only modules invoke `gh`, agent CLIs or Python,
  not Git. These exclusions do not change the publication-path guarantee.

**Merge approval pending native Windows verification.** This changes process
handling and PowerShell rendering; `coga-dev/testing` requires a native Windows
full-suite receipt at the final head before merge. None has been supplied.
Asked the attending owner about an existing host or receipt. The documented
zombie-PID limitation and external idle/max-session kills remain outside the
completion-triggered teardown fix; no stronger kill-proof guarantee is claimed.

## PR

```yaml
title: Keep Coga's git calls off the index lock and defer the done marker
author: claude
author_evidence: Attended implement session run by Claude (claude-opus-5-5) under coga launch e9301af0-963e-4d01-bbf5-47659be5fc8b.
head: 4ee4d7e738f1f8f30b3ef2dc530e846eee0f4d17
base: db1442ea32e5834ce53fe8e62ab3654be57132b4
depth: deep
rationale: Changes supervisor teardown ordering, process liveness and recovery commands. Independent Codex direct code review completed without must-fix findings; native Windows full-suite verification is still required before merge.
implementation: Forces GIT_OPTIONAL_LOCKS=0 in git._git_env and routes the remaining direct git subprocess callers through it; cli.main wraps dispatch and its end-of-command boundary in repl_supervisor.deferred_done_marker, which holds the done marker until the sweep and log warning return and leaves <sentinel>.pending-<pid> so both supervisors skip the terminal-ticket probe while a coga command is alive; coga status warns about an existing index.lock and, on a feature checkout, prints a root-anchored POSIX or PowerShell sync command when every dirty Coga-root file is an unstaged or untracked regular file equal in content and mode to the remote-tracking control copy, otherwise lists the files needing manual reconciliation.
deviations: Owner dispositions of the evaluator findings (pending-marker guard, safe-state-only hint, non-writing _blob_id, anchored per-OS rendering) extend the original spec; the pending witness is written at boundary entry rather than at the first done request so slow work before emit_done_marker is also covered; launch._checkout_command now shares oscompat.shell_command, which also quotes a leading @ for PowerShell; a pre-existing broken coga-dev branch-sweep link anchor is dropped at the owner's request.
limitations: The root cause is inferred, not reproduced live. A SIGKILLed coga left as an unreaped zombie still reads as a live pending command on POSIX until reaped (idle and max-session backstops still apply). Unstaged deletions are routed to manual reconciliation even when safe. dream_validate_drift, recurring_activity, retire_worklist, commands/update and github_preflight git calls are left unchanged (ref-only or deliberate commits outside the boundary). No native Windows run.
files:
  docs/contexts/coga-dev/internals/branch-sweep/SKILL.md: Drop an anchor to a branch-sweep section that is not on main yet (pre-existing broken link, fixed at owner request).
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: Describe the deferred marker, pending witness and sentinel-dir cleanup in the supervisor internals.
  src/coga/branchcleanup.py: Run its git helper through git._git_env (keeps LC_ALL=C).
  src/coga/branchsweep.py: Run patch-id proof and git helper through git._git_env.
  src/coga/cli.py: Wrap dispatch and the end-of-command boundary in deferred_done_marker.
  src/coga/git.py: Force GIT_OPTIONAL_LOCKS=0; add FeatureSyncPlan, feature_sync_plan and stale_index_lock.
  src/coga/launch.py: Route the assist-alignment merge-base call through git._git_env; delegate command quoting to oscompat.
  src/coga/open_pr.py: Run git argv through git._git_env.
  src/coga/oscompat.py: Add shell_command and shell_chain for POSIX and PowerShell rendering.
  src/coga/recurring_runner.py: Run its direct git calls (including a status) through git._git_env.
  src/coga/repl_supervisor.py: Add deferred_done_marker, completion_pending and remove_sentinel_dir; skip the terminal probe while a command is pending.
  src/coga/repl_supervisor_nt.py: Same pending guard and sentinel-dir cleanup on Windows.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/reconciliation/SKILL.md: New "Sync a feature branch with control" section.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/inactivity/SKILL.md: Record the deferred done signal and the pending guard on the terminal backstop.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Link the sync section, mention the status lines, add the index-lock note.
  src/coga/skill_manager.py: Run git argv through git._git_env.
  src/coga/validate.py: Run its read-only git queries through git._git_env.
  src/coga/views.py: Add the index-lock warning and feature-sync hint to coga status.
  tests/conftest.py: Stub the two new status probes off the real-git harness.
  tests/fixtures/authoring_cancellation.py: Model a mid-sweep stop explicitly now that the CLI withholds its marker.
  tests/test_done_marker_emission.py: Cover marker ordering through cli.main, final bump with pending witness, sweep failure, failed command, and direct calls.
  tests/test_git.py: Cover forced optional locks, an untouched real index on a feature sweep, feature_sync_plan safe/unsafe states, no object writes, the nested-cwd command run, and stale_index_lock.
  tests/test_repl_supervisor.py: Cover completion_pending liveness and the PTY terminal backstop waiting on a live pending command.
  tests/test_repl_supervisor_nt.py: Cover the Windows supervisor's pending guard with the fake process tree.
  tests/test_views.py: Cover the status hint, omitted parts, manual listing, silence, PowerShell rendering and the lock warning.
review:
  reviewer: codex
  kind: independent
  status: pending
  head: 4ee4d7e738f1f8f30b3ef2dc530e846eee0f4d17
  base: db1442ea32e5834ce53fe8e62ab3654be57132b4
  detail: Direct review completed over all 25 diff paths with no must-fix code findings. Implementer was Claude; reviewer is this fresh Codex session. Merge approval remains pending the required native Windows full-suite receipt.
checks:
- command: .venv/bin/python -m pytest -q -p no:cacheprovider
  status: passed
  head: d83726210c57584d79c4c2f6e76af94c597ca636
  base: 7e342fbfa59e3269d32d75ff0c0cbe4d485a926b
  detail: 4736 passed, 33 skipped.
- command: .venv/bin/python -m coga.cli validate --json
  status: passed
  head: d83726210c57584d79c4c2f6e76af94c597ca636
  base: 7e342fbfa59e3269d32d75ff0c0cbe4d485a926b
  detail: Exit 0, 107 OK, ten pre-existing warnings on other tickets.
- command: native Windows python -m pytest
  status: not-run
  detail: No Windows host in this session; required before merge per coga-dev/testing.
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest -q -p no:cacheprovider
  status: passed
  head: 4ee4d7e738f1f8f30b3ef2dc530e846eee0f4d17
  base: db1442ea32e5834ce53fe8e62ab3654be57132b4
  detail: 4736 passed, 33 skipped, zero failures in 754.25s (12m34s). Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.12.12. Full suite at the rebased head.
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m coga.cli validate --json
  status: passed
  head: 4ee4d7e738f1f8f30b3ef2dc530e846eee0f4d17
  base: db1442ea32e5834ce53fe8e62ab3654be57132b4
  detail: Exit 0; 107 OK, ten existing warnings, zero errors. Pop!_OS 24.04 LTS, Python 3.12.12.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-lock-terminal-review.py
  status: passed
  head: 4ee4d7e738f1f8f30b3ef2dc530e846eee0f4d17
  base: db1442ea32e5834ce53fe8e62ab3654be57132b4
  detail: 'Real PTY at 80x24 and 120x40: status reported a present lock and printed a copyable sync command; executing it from a nested directory with an apostrophe/bracket filename left a clean scratch checkout at origin/main.'
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-lock-delayed-review.py
  status: passed
  head: 4ee4d7e738f1f8f30b3ef2dc530e846eee0f4d17
  base: db1442ea32e5834ce53fe8e62ab3654be57132b4
  detail: 'Real PTY, final bump and real terminal-status probe with a seven-second delayed sweep: boundary finished, task done, sentinel observed, exit 0 in 7.49s, no index.lock. Disposable bare-remote harness; notifications disabled.'
```

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
