---
name: bootstrap/dream/tasks/dev/stale-branches
description: Inspect local and remote git branches and write a reviewable stale-branch cleanup proposal with exact evidence.
---

# Dev Stale Branches

This is a project-specific Dream worker template for code repos. It inspects
git branch state and writes a cleanup proposal. It does not delete branches.

Branch deletion is destructive because branch refs are a human recovery surface.
The first version of this worker is proposal-only: collect evidence, classify
risk, and hand a human exact commands to review.

## Safety Rules

Protected branches are never deletion candidates:

- `main`
- `master`
- `trunk`
- `develop`
- `dev`
- `staging`
- `production`
- the current checked-out branch
- the remote default branch, for example `origin/main`
- any branch currently attached to a git worktree

Never run these commands from this worker:

```
git branch -D <branch>
git push origin --delete <branch>
git remote prune <remote>
git fetch --prune
```

`git remote prune` and `git fetch --prune` only delete local remote-tracking
refs, not server branches, but they still change git state. Include them only
as proposed commands after showing the dry-run evidence.

## Evidence Commands

Run evidence collection from the repo root. Record every command and the
relevant output in the Dream run blackboard.

Find the remote default branch:

```
git symbolic-ref --quiet --short refs/remotes/origin/HEAD
```

If that fails, use `origin/main` only if `git show-ref --verify
refs/remotes/origin/main` succeeds. Otherwise stop and ask the human for the
default branch.

Record protected and checked-out branch evidence:

```
git branch --show-current
git worktree list --porcelain
```

List local branches already merged into the default branch:

```
git branch --merged <remote-default> --format='%(refname:short)'
```

For each local deletion candidate, record exact proof:

```
git merge-base --is-ancestor <local-branch> <remote-default>
git log -1 --format='%h %cs %an %s' <local-branch>
git for-each-ref --format='%(refname:short) %(upstream:short) %(upstream:track)' refs/heads/<local-branch>
```

The `git merge-base --is-ancestor` command must exit `0`. If it exits non-zero,
the branch is not a merged-local deletion candidate.

Identify stale remote-tracking refs separately:

```
git fetch --prune --dry-run origin
```

Only classify refs shown by the dry run as stale remote-tracking refs. These
are local `refs/remotes/origin/*` entries that the remote would prune; they are
not local branches and they are not remote branch deletion requests.

Identify old topic branches separately:

```
git for-each-ref --sort=committerdate --format='%(committerdate:iso8601) %(refname:short) %(upstream:short) %(upstream:track)' refs/heads refs/remotes/origin
git log --left-right --cherry-pick --count <remote-default>...<branch>
```

Use the repo's configured stale age if one exists. If the repo has no project
policy, use 90 days as a review threshold and label that threshold as a default
in the report. Old topic branches are not deletion candidates unless they also
pass the merged-local rules above.

## Classification

Write separate sections for these categories:

### Merged Local Branches

Local `refs/heads/*` branches that are not protected, are not checked out, are
not attached to any worktree, and have exact merge evidence:

- `git branch --merged <remote-default>` listed the branch.
- `git merge-base --is-ancestor <branch> <remote-default>` exited `0`.
- The branch is absent from the protected list.

For each branch, propose but do not run:

```
git branch -d <branch>
```

### Stale Remote-Tracking Refs

Remote-tracking refs identified only by:

```
git fetch --prune --dry-run origin
```

For this category, propose but do not run:

```
git remote prune origin
```

Do not convert this category into `git push origin --delete`; that deletes a
server branch and is outside this worker's authority.

### Old Topic Branches

Branches older than the review threshold that are not proven merged. Include:

- last commit date and subject
- upstream tracking state
- ahead/behind counts from `git log --left-right --cherry-pick --count`
- owner if the repo has a documented owner convention

Do not propose a deletion command for old topic branches. Propose one of:

- ask the owner whether the branch is still needed
- create a cleanup ticket
- leave alone with a reason

## Output

Append a section to the Dream run blackboard:

```
## Dream Worker: dev/stale-branches
Generated: <timestamp>
Remote default: <remote-default>
Review threshold: <N days>

### Commands Run
<exact commands and relevant output>

### Merged Local Branches
<branch-by-branch evidence and proposed git branch -d commands>

### Stale Remote-Tracking Refs
<dry-run prune evidence and proposed git remote prune command>

### Old Topic Branches
<evidence and owner-review recommendations>

### Proposal
<copy-pasteable commands for human review, grouped by risk>
```

If there are no candidates, write a concise no-op result. Do not open a noisy
PR just to say there were no stale branches.

If there are candidates, output a proposal first. A PR is appropriate when the
repo wants reviewed documentation, cleanup tickets, or policy changes, but a PR
cannot delete git refs by itself.

## Direct Deletion

Direct deletion is not implemented in this template.

A future tightened worker may delete only local branches with all of these
properties:

- the branch is not protected
- the branch is not checked out
- the branch is not attached to any worktree
- `git branch --merged <remote-default>` lists the branch
- `git merge-base --is-ancestor <branch> <remote-default>` exits `0`
- deletion uses `git branch -d`, never `git branch -D`

Remote branch deletion must remain proposal-only unless a separate human-owned
policy explicitly authorizes it.
