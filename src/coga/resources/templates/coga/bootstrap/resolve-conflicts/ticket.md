---
title: Resolve PR conflicts
assignee: claude
secrets: null
---

## Description

Command ticket for the `resolve-conflicts` verb. It updates open pull-request
branches onto `origin/main`, resolves conflicts with agent judgment, verifies
the rebased result, and force-pushes only through an explicit lease.

`coga resolve-conflicts` is a default alias for
`coga launch bootstrap/resolve-conflicts`. Pass one PR number or URL to scope
the run, for example `coga resolve-conflicts 631`; omit it to sweep every open
PR. The optional selector arrives in the composed prompt's
`## Launch arguments` JSON array.

This target is stateless: do not create a task per run, edit this ticket, write
results to any ticket blackboard, or run `coga bump` / `coga mark`. Print the
per-PR report, post its roll-up through `coga slack`, then exit the agent
session.

### Scope and accepted limitation

The target set is **open PRs only**. With no selector, enumerate it with
`gh pr list --state open`; with one selector, resolve that PR with
`gh pr view` and require it to be open. Do not enumerate worktrees, ticket
`branch:` lines, or branches that lack an open PR. The superseded
`rebase-stale-worktrees` task covered pre-PR branches; that coverage is
intentionally dropped.

Read the `## Launch arguments` JSON array exactly when the section is present;
an absent section means the launch had no positional arguments:

- no section (equivalent to `[]`) means all open PRs.
- `[PR]` means only that PR number or URL.
- Any other arity is invalid: print
  `usage: coga resolve-conflicts [PR]`, make no changes, and stop the run.

Only update PRs targeting `main`. Report a PR with another base as
`conflict` with the base named; do not retarget or rebase it.

### Run order

1. **Preflight and enumerate.** Start from the repository root. Confirm
   `git` and `gh` can read the repository, then run `git fetch origin main`.
   Query PR metadata including number, URL, base ref, head ref, head
   OID, head repository, fork status, and maintainer-writeability. In sweep
   mode, use `gh pr list --state open`; in single mode, use `gh pr view`.
   Process PRs sequentially and keep the observed head OID for the push lease.
2. **Select a safe worktree.** Inspect `git worktree list --porcelain`.
   Never rebase the `main` checkout. If the PR branch already has a worktree,
   use it only when it is clean, has no merge/rebase/cherry-pick in progress,
   and its HEAD exactly matches the observed PR head OID. Otherwise report
   `skipped-dirty`; never stash, reset, or overwrite that work. When no
   worktree owns the branch, fetch `refs/pull/<number>/head`, confirm the
   fetched OID still matches the observed head OID, and create a temporary
   detached worktree at that OID. Remove only worktrees created by this run.
3. **Check freshness.** In the selected worktree, run
   `git merge-base --is-ancestor origin/main HEAD`. If it succeeds, report
   `up-to-date` and do not push. Otherwise record the original head OID and
   run `git rebase origin/main`.
4. **Resolve with judgment.** On conflicts, read the branch commits and diff,
   the relevant changes on `main`, and both sides of every conflicted file.
   Preserve and re-apply the PR's intent on top of current `main`; do not
   choose `ours` or `theirs` blindly. Stage resolved files and continue the
   rebase (use a non-interactive editor). Semantic conflicts are in scope, but
   confidence is mandatory: if intent is ambiguous or a safe result cannot be
   established, run `git rebase --abort`, restore the worktree as described
   below, and report `conflict` with the files and reason.
5. **Verify before push.** Re-read the complete
   `git diff origin/main...HEAD` and confirm it still implements only the
   PR's intended change. If the changed paths include anything under `src/`
   or `tests/`, run `python -m pytest`. A failed or unavailable required
   test is `verify-failed`: do not push, and restore the original worktree
   state. Diff review and this conditional test are a mandatory gate; never
   force-push first and verify afterward.
6. **Push with the observed lease.** Resolve the writable remote for the PR's
   actual head repository. `origin` is valid only for a same-repository PR;
   never push a fork branch into a same-named base-repository branch. Immediately
   before pushing, fetch the remote head again and require it to equal the
   observed head OID. Then push the rebased HEAD to that exact head ref with
   `git push --force-with-lease=refs/heads/<head-ref>:<observed-head-oid>
   <remote> HEAD:refs/heads/<head-ref>`. If no writable head remote can be
   established, the head moved, or the lease/push fails, do not weaken or
   retry the lease: restore local state and report `conflict` with the reason.
   A successful push is `rebased-pushed`.

### Restore and cleanup

A PR that is not successfully pushed must be left as it was found. While a
rebase is active, use `git rebase --abort`. If a rebase completed in an
existing worktree but verification or push then failed, restore its recorded,
original OID only because the worktree was proven clean before the run. For a
temporary detached worktree, remove it through `git worktree remove` and then
remove its now-empty temporary parent. Never delete a pre-existing worktree or
branch. Never touch, rebase, or push `main`.

### Report

Print exactly one concise stdout line per selected PR as soon as its outcome is
known:

`PR #<number> <head-ref> — <status> — <detail>`

Use these status tokens exactly:

- `rebased-pushed`
- `up-to-date`
- `conflict`
- `skipped-dirty`
- `verify-failed`

After all PRs, post one compact count roll-up (and the PR numbers needing human
attention) with the command below. This must be the final action: a successful
bootstrap-target FYI also signals the stateless launch supervisor that the
command is complete.

`coga slack --task bootstrap/resolve-conflicts --message "<one-line roll-up>"`

A Slack failure is a command failure and must be surfaced. Do not persist the
per-PR lines or roll-up in this command ticket or in any other task file.
