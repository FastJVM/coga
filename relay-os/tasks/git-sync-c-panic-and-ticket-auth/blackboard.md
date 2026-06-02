The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: git-sync-c
worktree: ../relay-git-sync-c (based on origin/main, which has A #262 + B #263)
pr: (pending — open-pr step)
commit: 8417a76

## Scope expanded (final, committed in 8417a76)
The ticket-authoring half was generalized beyond my first cut (7a1abe3):
- New `git.sync_paths(cfg, anchor, paths, *, message)` multi-path helper;
  `sync_task_state` delegates to it. `_commit_paths`/`_overlay_paths` stage
  exactly the selected pathspecs (add if present, `rm --cached` if removed).
- `relay ticket` authoring now snapshots tasks/contexts/skills before the
  session, diffs after, and syncs EVERY authored task (incl. a brand-new task
  created from a title) plus changed support files — my first cut only synced
  a pre-resolved ref, missing the title→new-task case.
- conftest `_stub_git` had to also stub `sync_paths` (it only stubbed
  `sync_task_state`); without it, 3 existing test_ticket.py tests broke
  (authoring shelled out to real git on a non-git tmp path → faked subprocess
  TypeError). Fixed + added a git_repo test for the new-task authoring sync.

## Implement step: DONE
Wired `git.sync_task_state` into both deferred sites:
- `commands/panic.py` — after the Slack post / echo, before `emit_done_marker`
  so the commit lands before teardown. Message `Ticket: <slug> — panic`.
- `commands/ticket.py` (`_run_authoring_session`) — last statement of the
  success path, after validation + workflow gate. Message `... — authored`.
  Note: ticket.py:157 always appends a launch-log line, so a no-edit session
  still syncs that record (not a true no-op); the genuine nothing-staged no-op
  is covered by the helper unit test.

BUG FIX (human approved including in C): `git.py::_build_overlay_tree`
`git rm -r` → `git rm -rf` on the throwaway temp index. Without `-f`, cross-
branch land crashed whenever the task already existed on main and the feature
HEAD had changed it — the common panic-from-a-worktree case. Verified the fix
lands the blocker on main without sweeping uncommitted code.

Tests (tests/test_git.py, +214 lines, reuse the `git_repo` harness):
- CLI panic syncs blocker to origin (same-branch).
- CLI panic from feature branch lands blocker on main, leaves uncommitted code.
- helper-level regression: cross-branch re-land of an already-on-main task.
- CLI ticket authoring syncs the agent's external edits.
- CLI ticket authoring records the session even without ticket edits.

Context updated (CLAUDE.md rule): both copies of relay/sync SKILL.md
(live + packaged template) move panic + ticket authoring from "Deferred" to
the synced surface.

Verification:
- `pytest tests/test_git.py` → 27 passed; full suite → 512 passed, 1 FAIL.
- The 1 failure is `test_packaging.py::test_package_force_includes_relay_resources`
  — PRE-EXISTING on origin/main (force-include removed by #259, test left
  stale). I touched neither pyproject.toml nor that test. FOLLOW-UP candidate,
  not part of C.
- `relay validate --json` on example fixture → clean. Example fixture needs no
  update (no task-layout / prompt / workflow change).

Run with the relay venv python + PYTHONPATH=src pointing at the worktree
(editable install resolves `relay` to the PRIMARY checkout otherwise).

## Peer-review step: in progress

Ran required review command from `../relay-git-sync-c`:
- `codex review --base origin/main`

Review returned two P2 findings, both on the `relay ticket` authoring path:
- Support files created by the authoring skill (`relay-os/contexts/...` or
  `relay-os/skills/...`) are not pushed by `git.sync_task_state(ref.path)`.
  Local validation/prompt composition can pass, while another checkout sees
  only the ticket edit and misses the referenced context/skill file.
- Bare `relay ticket` launches the stateless `bootstrap/ticket` shim, so
  `ref` is a `BootstrapRef` and the current sync block does not run. In that
  empty-interview flow the child agent may run `relay draft` and then edit the
  new task directly; relay currently syncs only the raw draft creation, not the
  filled ticket after the authoring session returns.

Scope tension: both findings are real product gaps, but fixing them is broader
than C's written constraint ("C adds no new git mechanism, only two call
sites" and task-dir scoped sync). The support-file fix needs a non-task-dir
sync path or broader authoring transaction. The bare `relay ticket` fix needs
post-session discovery of which task(s) the child created/edited, then
validation + sync of those tasks without sweeping unrelated concurrent edits.

Verification this session:
- `PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest tests/test_git.py`
  -> 27 passed (pytest cache warning only because the sibling worktree is
  read-only under the sandbox).
- `PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/relay-git-sync-c-pycache
  /home/n/Code/relay/.venv/bin/python -m pytest -p no:cacheprovider`
  -> 511 passed, 1 skipped, 1 failed. Failure is still
  `tests/test_packaging.py::test_package_force_includes_relay_resources`
  (`KeyError: 'force-include'`), matching the implement note as unrelated to
  this diff.

Decision needed with human before editing: either keep C scoped and file these
as follow-up authoring-sync tickets, or expand C into a broader authoring
transaction/sync-path change.

## BUG found in merged git.py (B / #263) — blocks C's panic site
Cross-branch land (`_build_overlay_tree`) runs `git rm -r --cached
--ignore-unmatch` against a throwaway temp index. When the task ALREADY exists
on main (normal — created earlier) AND `_commit_task_dir` just committed the
change to the feature HEAD, `git rm --cached`'s safety check ("staged content
differs from both file and HEAD") REFUSES → cross-branch sync crashes with
typer.Exit(1). B's existing test misses it because there the task was never
previously committed to main, so `--ignore-unmatch` makes the rm a no-op.

This is exactly C's riskiest path: `relay panic` from a feature worktree on an
existing ticket. Same-branch panic (on main) is unaffected.

Fix (tested, verified): `git rm -rf --cached ...` — the temp index is throwaway
and immediately rewritten, so the safety guard is meaningless there. One word
(`-r` → `-rf`). DECISION PENDING with human: include in C vs follow-up ticket.

## Resolution: base branch (was a question)
Both A (#262 same-branch helper) and B (#263 cross-branch land) are MERGED to
origin/main. Local main was just stale. C bases off origin/main and inherits
the cross-branch helper — so panic/ticket sync also lands on main from a
feature branch. The earlier A-vs-B dilemma is moot.


## Findings (session 1, implement step)

C wires `git.sync_task_state` into two bespoke call sites that A's clean-site
pass deliberately skipped: `relay panic` and `relay ticket` authoring.

### Dependency state
- `src/relay/git.py` does NOT exist on `main`. It is introduced by ticket A
  (branch `git-sync-a`, in_progress, NOT merged) and extended by B
  (branch `git-sync-b`, NOT merged — adds the cross-branch land-on-main path).
- A's helper API: `git.sync_task_state(cfg, task_path, *, message=...)`.
  Same-branch only: no-ops with a warning on a feature branch; on the control
  branch it `git add`s ONLY the task dir, commits if staged, pushes.
  Empty-edit case already handled (nothing staged → clean no-op).
- A also adds `[git]` config (`git_enabled`/`git_remote`/`git_control_branch`)
  and a test fixture (`tests/conftest.py` git-repo fixture + `tests/test_git.py`).
- => C cannot branch off `main` (no git.py). It must base on A or B.

### The two call sites
1. `commands/panic.py` — after `post(...)`/`emit_done_marker`, before `sys.exit(1)`.
   RISK: panic often fires from inside a feature worktree with uncommitted
   CODE. A's helper already scopes `git add` to the task dir only (never -A),
   so the code tree is safe. On a feature branch it no-ops (A) or lands on main
   (B) — either way scoped to `relay-os/tasks/<slug>/`.
2. `commands/ticket.py:~204` — after the subprocess returns AND the re-read +
   validation + workflow check pass. The agent edits ticket.md/blackboard
   externally; relay must commit them itself. Empty-edit case → helper no-ops.

### Plan
- Base branch on `git-sync-a` (or `b` — see decision below).
- panic.py: add `from relay import git`; call `sync_task_state` after the post,
  before `emit_done_marker`/exit, message `Ticket: <slug> — panic`.
- ticket.py: add import; call `sync_task_state` as the last statement of the
  success path, message `Ticket: <slug> — authored`.
- Extend `tests/conftest.py` fixture + `tests/test_git.py` to cover both sites.
- Run `python -m pytest` and `relay validate --json`.
