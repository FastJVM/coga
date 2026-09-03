---
slug: reuse-the-existing-control-worktree-for-recurring
title: Run single-repo recurring from the control worktree that already exists
status: in_progress
owner: nicktoper
human: nick
agent: claude
assignee: codex
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
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
secrets: null
step: 2 (peer-review)
---

## Description

Bare `coga recurring` and `coga recurring launch <name>` hard-refuse
(`return 2`) when the checkout is not on the configured control branch, so
`coga dream` from a feature branch is a dead stop that only a manual
`git switch main` clears. The refusal names no remedy beyond "go switch
branches yourself".

In the layout Coga recommends, a linked worktree **already has the control
branch checked out**. That checkout is exactly what the run needs, and the
command can find it without creating anything: `git._worktree_holding_branch`
already locates the worktree holding a given branch.

Run the single-repo sweep from that existing control worktree instead of
refusing. No worktree is created, nothing is deleted, the operator's checkout
is never touched, and no lock is held beyond what an ordinary on-control run
holds today. When no such worktree exists, keep today's refusal — but name the
absence as the reason and give the remedy.

Done looks like: with a linked worktree on `main` present, `coga dream` typed
from a feature branch with a dirty tree creates and launches its period task,
the serviced-period ledger line reaches `<remote>/<control-branch>`, and the
operator's checkout is byte-identical afterwards — same branch, same `HEAD`,
same `git status --porcelain --untracked-files=all --ignored`, no new stash
entry.

## Context

Cite symbols, not line numbers. `5243dfd5` (`delegate:` field, 2026-08-26)
moved ~306 lines in `recurring_runner.py` on the day this ticket was drafted
and invalidated every line citation in its first draft.

### The refusal being changed

Both single-repo entry points `return 2` via `_refuse_non_control_branch` in
`src/coga/recurring_runner.py`:

- `run_recurring_scan` — guarded by `not require_fresh_control`, so this is the
  *non*-`--all` path. `--interactive` goes through this function too, so it
  refuses as well.
- `run_recurring_named` — unconditional. `coga dream` resolves through
  `src/coga/aliases.py` (`"dream": "recurring launch dream"`) straight into it.

The message names the current branch and says to `git switch main`. It exempts
only `git_enabled = false` and confirmed non-git workspaces.

Note for the implementer: the sibling ticket
`service-recurring-from-a-temp-control-worktree-ins` claims in its Out of Scope
that these entry points "keep today's best-effort behavior off the control
branch (they scan the working tree they are in)". That is false — they refuse
outright. The likely source of the error is `_refuse_non_control_branch`'s own
docstring, which says "reachability and freshness remain best-effort for
interactive runs"; that is about *freshness*, not the branch.

### Why this is the right first move

The gate itself is correct — the scan reads working-tree templates and period
tasks and writes period state, so running from a stale feature branch could
re-fire runs the control branch already serviced. The defect is that the only
recovery is a human running `git checkout` by hand.

An existing control worktree needs none of the machinery a *created* one does:
no temp directory, no cleanup on SIGINT/SIGTERM/SIGKILL, no stranded-worktree
reaping, no seeding of gitignored files, no new concurrency lock, and no
question about what happens to uncommitted work at teardown. It is an ordinary
on-control run that happens to start in a different directory, so every
existing sync, ledger, and push path applies unmodified.

It is also the case the created-worktree designs *cannot* serve:
`git worktree add <tmp> <control>` fails when a worktree already holds the
control branch, because git refuses to check one branch out twice. So a
create-only design is absent in exactly the well-configured layout, while this
one covers it.

### Relationship to the two sibling tickets

- `service-recurring-from-a-temp-control-worktree-ins` (`in_progress`,
  `review-design`) covers the `--all` child by *creating* a temp worktree. This
  ticket must not build a second worktree helper, but it also must not wait on
  that one: reusing an existing worktree needs none of its machinery. If a
  shared "find or make a control checkout" seam falls out naturally, good; if
  not, ship this without one.
- `run-recurring-agent-templates-off-the-control-bran` (draft) covers the hard
  remainder — agent sessions in a *created* checkout, with the worktree
  lifetime, `worktree:` recording, and lock-duration problems as its subject.

### Scope of the behavior change

The design decision the implementer must make explicit: does the run merely
*start from* the control worktree (child process with `cwd` there), or does it
need anything else re-pointed? A period task launched from that checkout reads
the control tip's templates and period tasks, not the operator's dirty feature
tree — which is the intended semantics, but say so, because it changes what a
`dream` run sees.

Also decide what an agent-backed template does here. Unlike a created temp
worktree, an existing control worktree is durable and operator-owned, so an
agent session inside it does not hit the data-loss and cleanup problems — but
it does occupy a checkout the operator may be using. Either admit agent
templates (and say what happens if that worktree is dirty) or restrict this
ticket to `ticket.py` templates and leave agents to the sibling draft. Do not
leave it implicit.

`resolve-conflicts` is a `delegate:` template as of `5243dfd5`, where the sweep
performs the delegated launch in the operator's own terminal with its own
TTY-admission rules and a `coga/log.md` slack-sentinel completion path. Say
what happens to a delegating template in this mode.

### Context to read and update

`coga/contexts/coga/recurring/SKILL.md` is deliberately **not attached** — at
~9.2k tokens it was 70% of the composed prompt for a handful of facts. Read it
directly. The section `## Recurring runs start on the control branch` states
the contract this ticket changes ("Every launching entry point requires the
configured control branch… There is deliberately no override") and must be
rewritten in the same PR, per the repo's context-in-the-same-PR rule. There is
no packaged duplicate to sync — it is one file. The `delegate:` gotcha near the
end of the same file is the only place TTY admission for delegated launches is
explained.

### Not this ticket

- Creating a worktree when none holds control. That is
  `run-recurring-agent-templates-off-the-control-bran`.
- The `--all` path and its parent summary — the other sibling owns those.
- The diverged-control case (control branch checked out but its local commits
  cannot rebase onto the fetched tip). That keeps failing loud.
- Running recurring from a separate clone or install pointed at another repo.
- Moving the operator's own checkout (stash → switch → run → switch back → pop).
  Rejected with full reasoning in
  `service-recurring-from-a-temp-control-worktree-ins`; not an open question.

<!-- coga:blackboard -->

## Orientation (implement, session 1)

Symbols confirmed in `src/coga/recurring_runner.py`:

- `run_recurring_scan` — `if not require_fresh_control and _refuse_non_control_branch(cfg): return 2`
- `run_recurring_named` — `if _refuse_non_control_branch(cfg): return 2`
- `_refuse_non_control_branch` is *also* called from `src/coga/commands/launch.py`
  (two sites, for `coga launch recurring/<name>`). That spelling is out of scope,
  so the function itself must keep its current behavior for that caller.
- `_run_repo_recurring` is the existing precedent for re-dispatch: it already runs
  `[sys.executable, "-m", "coga.cli", "run", "recurring-scan", ...]` with `cwd=` set
  elsewhere and inherited stdio. The `--all` parent does this per repo today.
- `git._worktree_holding_branch(root, branch)` exists but folds listing failure into
  the `_WORKTREES_UNKNOWN` sentinel *and writes a "not fast-forwarded" stderr note*
  that would be wrong in this context.

### Chosen shape: relay, not re-point

The run **starts from** the control worktree — a child `coga` process with `cwd`
there — rather than re-pointing `cfg.repo_root` in-process. Consequences, stated
because they change what a `dream` run sees:

- The child reads templates, period tasks, and `coga/log.md` from the *control
  worktree's* tree, i.e. the control tip, not the operator's dirty feature tree.
  That is the intended semantics.
- Every existing sync / ledger / push path applies unmodified, because the child
  is an ordinary on-control run. No second worktree helper is built.
- Recursion is impossible in one hop, and is additionally guarded by an env
  sentinel the child carries.

### Decisions the ticket demanded be explicit

- **Agent-backed templates are admitted.** The relay is `subprocess.run` with
  inherited stdio, so the TTY survives and `_interactive_stdio_has_tty()` is true
  in the child exactly as in an on-control run. The control worktree is durable
  and operator-owned, so there is no temp-worktree data-loss or cleanup problem.
  A **dirty** control worktree is not gated: today's on-control sweep runs in a
  dirty primary checkout without complaint, and this mode is the same run in a
  different directory. Adding a cleanliness gate here would be a new restriction,
  not a preserved one.
- **`delegate:` templates work unchanged.** The child *is* the sweep, its stdio is
  the operator's own terminal (inherited through the relay), so the delegated
  launch keeps its TTY admission, and its `coga/log.md` slack-sentinel completion
  path writes the control worktree's log — which is the control branch's log, i.e.
  the correct one.

### Blocker found: the relayed child cannot load machine-local config

`coga.local.toml` is gitignored (`coga/.gitignore:6`). A linked worktree created by
plain `git worktree add` therefore does **not** have one — verified against this
repo's own three linked worktrees, none of which carries `coga/coga.local.toml`.

`load_config(require_user=True)` *hard-errors* with "No `user` set in
coga.local.toml" in that case, so a naive relay is dead on arrival in exactly the
layout this ticket exists to serve. Options weighed under `## Open question`.

## Dev

branch: recurring-control-worktree
worktree: /home/n/Code/codex/coga-recurring-control-worktree

## Open question — resolved

Human chose the **env handoff**: the relay exports `COGA_LOCAL_CONFIG` pointing at
the operator checkout's own `coga.local.toml`, and `load_config` honors it when
set. Nothing is written anywhere, the operator's checkout stays byte-identical,
and it is semantically right — `user`, agent paths, and webhooks describe the
machine and the operator, not the checkout. Rejected: refusing without the file
(leaves the headline scenario needing a manual symlink) and copying it in (writes
a gitignored file into a durable operator-owned checkout, which the ticket rules
out).

## What landed

Commit `0491ed51` on `recurring-control-worktree`.

**`src/coga/recurring_runner.py`** — `_relay_off_control_single_repo_run` is the
new branch precondition for both single-repo entry points. It returns `None`
(proceed here), the relayed child's exit code, or `2` for the refusal that
still stands. Supporting pieces:

- `_existing_control_worktree` — the lookup. Returns None for "already on
  control", exempt/unreadable workspace, relayed child, no such worktree, the
  current root itself, or a worktree with no `coga.toml`. **Every git
  inspection failure collapses to None on purpose** so `_refuse_non_control_branch`
  re-probes and owns the error text — a broken probe can never be misread as
  "no worktree holds control".
- `_relay_to_control_worktree` — `subprocess.run([sys.executable, "-m",
  "coga.cli", *argv], cwd=..., env=...)` with inherited stdio, the same spelling
  `_run_repo_recurring` already uses for `--all`. `cwd` mirrors where the Coga
  OS dir sits relative to the checkout, so a monorepo subdir layout lands in the
  matching subdir.
- `_recurring_scan_relay_argv` — `run recurring-scan` + flags.
  `--require-fresh-control` deliberately absent; a relay only happens off the
  `--all` path.
- `_CONTROL_RELAY_ENV = "COGA_RECURRING_CONTROL_RELAY"` caps the hop at one.
- `_refuse_non_control_branch` gains `no_control_worktree=False`, which only
  appends the absence + `git worktree add` remedy. `commands/launch.py`'s two
  call sites leave it off, so `coga launch recurring/<name>` never promises a
  relay it does not implement. Its docstring's "best-effort" line — the one the
  ticket flagged as the source of the sibling's wrong claim — now says
  explicitly that only *freshness* is best-effort, never the branch.

**`src/coga/config.py`** — `LOCAL_CONFIG_ENV` / `local_config_path(root)`.
`coga.local.toml` is read from `COGA_LOCAL_CONFIG` when set, else the
checkout's own copy. `commands/init.py` still *writes* to the checkout path;
only reading is redirectable.

**`src/coga/git.py`** — `worktree_holding_branch` is the public lookup that
raises `GitError` on a failed listing; `_worktree_holding_branch` becomes a thin
wrapper keeping the `_WORKTREES_UNKNOWN` sentinel and stderr note for the
ref-update caller. No second worktree helper was built, per the ticket.

**`coga/contexts/coga/recurring/SKILL.md`** — `## Recurring runs start on the
control branch` rewritten: the requirement is now "runs happen *on* control",
with the relay, its five consequences (control-tip reads, agent admission and
the un-gated dirty worktree, delegation, the `coga.local.toml` handoff, one
hop), and the narrowed refusal. Two later paragraphs adjusted for the same
shift. No packaged duplicate exists — confirmed, it is one file.

### Verification

- `python -m pytest` — **19 failed, 2053 passed**. The same 19 fail on
  unmodified `main` (**19 failed, 2040 passed**); failure sets diffed identical
  per module (`test_launch.py` 7/7 on both). All 19 are pre-existing
  environment failures — `test_packaging` wants a built wheel, the
  `test_launch_script` / `test_smoke` / `test_recurring_shims` ones subprocess
  the separately-installed `coga`. **+13 net passing** = the new tests.
- Real end-to-end, not just mocks: from this feature worktree (which genuinely
  has no `coga.local.toml`), `load_config` with `COGA_LOCAL_CONFIG` set
  resolved `user = 'nicktoper'`, `_existing_control_worktree` found
  `/home/n/Code/codex/coga`, and `_relay_to_control_worktree` with a read-only
  `["recurring", "list"]` argv spawned a working child that printed the real
  template table and exited 0.
- `coga validate --json` — unchanged output (pre-existing draft-blackboard
  findings only). Validation behavior was not touched.

### New tests

`tests/test_recurring.py`: relay for bare/`--force` scan and for the named
launch (argv, `cwd == control/coga`, both env vars); child exit code forwarded;
operator checkout byte-identical (branch, `HEAD`, `status --porcelain
--untracked-files=all --ignored`, empty stash list) across a relay from a dirty
tree; sentinel blocks a second hop; refusal names the absence; a control
worktree with no `coga.toml` is skipped; the `coga launch` spelling keeps the
plain message. `tests/test_config.py`: env override honored and, unset, the
checkout copy still wins. `tests/test_git.py`: `worktree_holding_branch` finds /
returns None / raises.

Test-harness note worth keeping: `recurring_cmd.subprocess` **is** the shared
`subprocess` module, so patching its `run` wholesale also swallows
`git._toplevel` and the worktree listing this path depends on. `_intercept_relay`
intercepts only `-m coga.cli` spawns and delegates everything else to the real
`subprocess.run`. Also, `git worktree add <p> main` must come *after* the
primary checkout leaves `main` — git refuses to check one branch out twice,
which is exactly why a create-a-worktree design cannot serve this layout.

### For the peer reviewer

- `COGA_LOCAL_CONFIG` is a new core-config seam. It was the human's call
  (alternatives weighed under `## Open question — resolved`). The sibling
  `service-recurring-from-a-temp-control-worktree-ins` faces the same gitignored-
  file problem in a *created* worktree and can reuse it instead of seeding.
- Out of scope and untouched, as the ticket directs: the `--all` path, worktree
  *creation*, the diverged-control case, and `coga launch recurring/<name>`.
