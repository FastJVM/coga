---
slug: install/short-notice-instead-of-raw-git-error-when-sync-ha
title: Short notice instead of raw git error when sync has no origin remote
status: in_progress
owner: nicktoper
human: nicktoper
agent: codex
assignee: nicktoper
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 4 (review)
---

## Description

In a repo with no `origin` remote — exactly the state `coga init` leaves a new
user in (`git init` → `coga init`, "push when ready") — every state-changing
command prints a raw two-paragraph git fatal, twice:

```
[git] sync failed: `git push origin main` failed: fatal: 'origin' does not
appear to be a git repository
fatal: Could not read from remote repository. …
```

Sync is correctly non-fatal (the GitError handler in `src/coga/git.py` makes
the miss visible without blocking the transition), and `git.py` already prints
calm one-liners for the "git disabled" and "not a git repo" cases. "No remote
named `origin` (or the configured `git_remote`)" is just as detectable and
just as expected on first run — it should get the same short, actionable
notice (e.g. "no `origin` remote yet — state committed locally; add a remote
to sync") instead of a scary fatal dump on a new user's first ticket.

## Context

Found during `install/retest-ssh-https-and-init-reclone-on-fresh-machine`
(finding 6 on its blackboard): fresh-container onboarding, `coga create` right
after `coga init` in a local-only repo.

**Fail-loud is the governing principle here** (Coga principle #6, quoted
inline so the whole `coga/principles` context need not be attached): *surface
every failure; never silent-wrong-answers. The worst failure is confidently
producing wrong output because something silently failed. If the cost of a
check is one line and the cost of skipping it is "wrong answer and nobody
knows," always check.* This fix must therefore calm **only** the one case that
is cleanly, positively detectable up front (no remote configured) and keep
every other push failure loud.

**Detect up front, don't pattern-match stderr.** The "no remote named
`origin` (or the configured `git_remote`)" case is cleanly detectable before
the push. `_remote_branch_present` (git.py ~2012) probes
`git remote get-url <remote>` and treats a non-zero exit as "remote absent."

**Gate on the `get-url` returncode, not the whole `_remote_branch_present`
predicate.** That function returns `False` for *two* distinct cases: (a) no
remote configured (`git remote get-url` non-zero, ~git.py:2020) and (b) the
remote exists but lacks the branch (`ls-remote` exit 2). We want to calm-swallow
**only case (a)**. Case (b) — a configured remote that simply doesn't have
`main` yet — is a legitimate first push that *creates* the branch and must not
be silenced. So gate the new soft-skip specifically on the `get-url` non-zero
result, next to the existing `_control_branch_present` check, rather than
reusing the composite function. (Good news for fail-loud: a configured-but-
unreachable remote already stays loud — `ls-remote` with a returncode other
than 0/2 raises `GitError` at ~git.py:2042.)

**Touchpoints (line numbers approximate — re-anchor, don't trust literally).**
The raw fatal prints from *each* sync entry point that runs per command (that's
the "twice"). Four call sites in `src/coga/git.py` currently soft-skip via
`_control_branch_present` and are the pattern to emulate — a complete fix
covers all four:
- `sync_log` (~304)
- `sync_paths` (~375)
- `sync_coga_state` (~484)
- `refresh_coga_state_from_control` (~567)  ← the one the original note omitted

(Line numbers refreshed against the current file by the drafting review;
function names are the reliable anchor — re-anchor by name, not number.)

The raw fatal itself surfaces from the `except GitError` handlers inside those
functions. **Note: the ticket lists four soft-skip sites but does not pin which
two fire on `coga create` to produce the observed doubling — confirm the "twice"
is fully explained by this set before assuming the fix is complete.**

`src/coga/recurring_runner.py` likely does **not** need the fix:
its git handler is `_sync_control_checkout_ahead`'s `except git.GitError`
(~582, not the originally-noted ~548) and already degrades to a calm
`"[git] note: pre-scan catch-up skipped: {exc}"` line. Confirm before touching
it.

**Guardrail (the key peer-review check).** Scope the calm swallow to the
**remote-not-configured** case only. A remote that exists but is unreachable —
offline, bad URL, auth failure, protected `main` — is *not* cleanly detectable
up front and must **stay a loud `GitError`** per the module's fail-loud model.
Broadening the fix to swallow all push failures would silently hide real sync
misses.

**Repro nuance.** The fatal only fires when the local control branch exists
(so `_control_branch_present` is True) *and* the remote is missing. If `git
init` left the user on `master` while `[git].control_branch` defaults to
`main`, they get the branch-mismatch one-liner instead. Reproduce the exact
stderr first to confirm you're fixing this path, not the adjacent one.

**Done includes a test.** Per CLAUDE.md, git-sync behavior changes ship with a
regression test — extend the existing `tests/test_git*.py` surface.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/644
branch: no-remote-notice
worktree: /home/n/Code/claude/coga-no-remote-notice

## Plan (implement step)

**Goal.** Replace the raw two-paragraph `git push` fatal with a calm one-liner
when — and only when — the configured remote is not configured at all
(`git remote get-url <remote>` non-zero). Every other push failure stays loud.

**Design.**
1. New helper `_remote_configured(root, remote) -> bool` (runs `git remote
   get-url`, returns `rc == 0`). Refactor `_remote_branch_present` to reuse it
   (it already inlines the same probe) — single source of truth for the get-url
   check.
2. New calm-message helper `_no_remote_message(cfg) -> str`, mirroring
   `_control_branch_mismatch_message`'s shape (returns the core line; each site
   appends ` ({message})\n`).
3. In all four sync entry points, *after* the existing `_control_branch_present`
   check, add `if not _remote_configured(root, cfg.git_remote): <calm>; return`.
   Order matters: `_control_branch_present` first keeps the on-`master`/no-`main`
   case on the branch-mismatch one-liner (the adjacent path); the no-remote
   soft-skip fires only when the local control branch *does* exist but no remote
   is configured — exactly the repro nuance in the ticket.

**"Twice" confirmed.** `coga create` fires `sync_task_state`→`sync_paths`
(create.py:99) AND the post-command sweep `sync_coga_state` (cli.py:156). Both
are in the four-site set, so the fix covers the doubling. Message wording: since
the soft-skip early-returns (like the sibling `_control_branch_present` skip, it
does *not* reach the local commit), the notice says "saved to disk", not
"committed" — accurate to what actually happens.

**Tradeoff (noted).** Emulating the four `_control_branch_present` early-returns
means the *local* commit is also skipped in the no-remote case (state stays a
dirty working-tree file, converged on the next sync once a remote exists — disk
is source of truth per the module's failure model). This matches the sibling
pre-check's behavior and the ticket's explicit "gate next to
`_control_branch_present`" instruction, chosen over a more invasive
commit-locally-but-skip-only-the-push refactor.

**Tests.** Two existing tests simulate a push failure via `remote remove origin`
and assert the LOUD path (`test_sync_log_failure_does_not_redirty_the_log`,
`test_sync_feature_branch_nonfatal_on_push_failure`). After this change "no
origin" is the calm path, so those must switch to a configured-but-broken remote
(`remote set-url origin <nonexistent-path>`) to keep exercising loud. New
regression tests cover the calm notice for each of the four entry points +
assert a broken-but-configured remote stays loud.

**recurring_runner.py:** confirmed NOT touched — `_sync_control_checkout_ahead`
already degrades to a calm `[git] note: pre-scan catch-up skipped` line.

## Design correction (found while testing — supersedes the blanket early-return)

The initial plan (early-return next to `_control_branch_present`, per the
ticket's drafting note) is **too broad**: it also suppresses the *feature-branch
local commit*, which never contacts the remote and must still happen. Proof:
`tests/test_launch_script.py::test_script_launch_commits_log_append_before_running_script`
runs `sync_log` on a **feature branch with no remote** and asserts the log
append is *committed* before the script runs — the blanket early-return left it
dirty and the script aborted (exit 7).

**Corrected scope — skip only the remote step, keep the local commit:**
- `sync_log`: commit always; soft-skip only the control-branch `_push_control_branch`
  and the `publish_current_branch` push.
- `sync_paths` / `sync_coga_state` (via `_dispatch_branch_sync`): keep the local
  commit on control/feature branches; soft-skip only the control-branch
  landing/push. Added `push` param to `_sync_paths_on_control_branch` — when
  `False` it commits but skips the push *and* the guard's remote-tip fetch (the
  guard's regression check is moot with no remote). Detached HEAD (no durable
  local commit) soft-skips the landing.
- `refresh_coga_state_from_control`: pure remote pull with no local commit to
  preserve → early-return before the fetch (kept).

Net effect matches the ticket's own example wording: **state is committed
locally, only the push is skipped.** Message is "saved locally" (accurate for
both the committed cases and the rare detached no-commit case). Helper
`_remote_configured(root, remote)` is the single get-url probe; `_remote_branch_present`
now reuses it.

## Verification

- `python -m pytest` — 1500 passed, 1 skipped (full suite).
- Manual repro: fresh `git init` + no remote → sync emits the calm one-liner,
  no `fatal`, and the ticket **is** committed on local `main` (working tree
  clean). Configured-but-broken remote → still the loud raw fatal (guardrail
  holds).
- Updated three existing tests that simulated a push failure via `remote remove
  origin` (now the calm path) to use a configured-but-broken remote instead, so
  they keep exercising the loud path.

## Dev status: implemented, tests green, committed on branch. Ready to bump.

## Dream Skill: validate-drift

Generated: 2026-07-24T17:47:07+00:00
Command: `coga validate --json --fix`
Task: `install/short-notice-instead-of-raw-git-error-when-sync-ha`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-24T17:54:01+00:00
Command: `coga validate --json --fix`
Task: `install/short-notice-instead-of-raw-git-error-when-sync-ha`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-24T17:59:56+00:00
Command: `coga validate --json --fix`
Task: `install/short-notice-instead-of-raw-git-error-when-sync-ha`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-24T18:04:51+00:00
Command: `coga validate --json --fix`
Task: `install/short-notice-instead-of-raw-git-error-when-sync-ha`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Peer review (step 2)

`/code-review` is user-invocation-only in this harness, so the slash command
could not be triggered programmatically; the review was done directly against
the branch diff vs `main` (the step's substance — a second agent that did not
write the change). Two must-fix findings, both applied in `e0d52197`, both
covered by new regression tests that fail without the fix.

**1. The no-remote path silently dropped the state-regression guard (real bug).**
`_sync_paths_on_control_branch(push=False)` gated the guard on `push`, with the
docstring rationale that "with no remote to advance the branch, there is nothing
for a stale checkout to bury." That rationale is false: a sibling worktree lands
state on the *shared local* control branch via the plumbing overlay path — no
remote involved. Verified by test: a stale `in_progress` copy buried a terminal
`done` ticket, printing only the calm notice. The guard now resolves its base
locally (`_control_base_for_attempt` attempt 0 → `refs/heads/<control>`) rather
than fetching the remote tip (which would raise the very fatal being suppressed),
so it still refuses. A refusal surfaces as the normal loud `sync refused` before
any commit.

**2. The notice claimed a save that never happened.** It printed unconditionally
on the control-branch path, so a clean no-op sync announced "coga state saved
locally" while committing nothing — and would fire on every command a no-remote
user runs. With a remote, that same no-op is silent. Now scoped to syncs that
actually committed (`_sync_paths_on_control_branch` returns whether it committed).

**Guardrail re-verified.** The fail-loud boundary the ticket cares about holds:
missing remote → calm one-liner; configured-but-broken remote → unchanged loud
`sync failed` + raw fatal + audit-log entry.

Rebase: `git fetch origin main && git rebase FETCH_HEAD` — clean, 2 commits
ahead of `main`, 0 behind. Full suite: 1502 passed, 1 skipped.

## PR

Replace the raw two-paragraph `git push` fatal with a short, actionable notice
when — and only when — no remote is configured. This is the state `coga init`
leaves a new user in (`git init` → `coga init`, "push when ready"), so every
state-changing command greeted their first ticket with a scary fatal dump,
printed twice.

Now that case prints one calm line and the state is still committed locally:

```
[git] no 'origin' remote configured — coga state saved locally; add a remote to sync (Ticket: demo — created)
```

The doubling is gone as a side effect: the local commit now happens, so the
post-command sweep finds a clean tree and stays quiet.

Scoped deliberately to the one push failure that is cleanly knowable *up front*
(`git remote get-url <remote>` exits non-zero). Every other push failure — a
remote that is offline, misauthed, protected, or simply lacks the branch — is
not detectable in advance and stays a loud `GitError`, per the module's
fail-loud model. Only the remote step is skipped; the local commit still
happens, and the state-regression guard still runs (resolving its base locally
instead of fetching), so a stale checkout cannot bury newer state landed by a
sibling worktree.

Touches the four sync entry points that each run per command: `sync_log`,
`sync_paths`, `sync_coga_state`, `refresh_coga_state_from_control`.
`recurring_runner.py` needed no change — it already degrades to a calm line.

Test plan: `python -m pytest` (1502 passed, 1 skipped), plus a manual fresh
`git init` + `coga init` + `coga create` repro confirming one calm notice with
the ticket committed on local `main`, and a configured-but-broken remote still
producing the loud failure.
