---
slug: install/short-notice-instead-of-raw-git-error-when-sync-ha
title: Short notice instead of raw git error when sync has no origin remote
status: active
owner: nicktoper
human: nicktoper
agent: codex
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
step: 1 (implement)
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
