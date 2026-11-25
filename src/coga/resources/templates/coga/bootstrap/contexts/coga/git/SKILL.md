---
name: coga/git
description: Work with tickets on ordinary Git branches and carry their state through the PR.
---

# Working with Git

Coga writes the ticket and the audit log in the current checkout. You can run
Coga in a directory without Git. Code workflows can explicitly run a Git script
to open a branch or PR, and a workflow's `git:` mode can run a Git hook around
each launch ([ticket-branch mode](#ticket-branch-mode)). Use ordinary `git pull`, `git push`, and `gh` to share
work, and `git branch -d` or GitHub to clean up merged branches.

## Checkout policy

Use ordinary Git branches in the checkout where the work started. If a
branch switch would disrupt work in progress, coordinate with the person using
the checkout before switching. A [recurring run](../recurring/SKILL.md#checkout-policy)
is the only Coga workflow that can use a disposable clone or linked Git worktree.
In ticket-branch mode, launch itself switches to the ticket branch and back,
so a launch from the starting branch needs a clean tree.

## Ticket Git record

Use one line per field in the blackboard's `## Dev` section. Each workflow step
updates its own fields and preserves other lines.

```text
branch: <name>
base: <branch>
remote: <name>
reviewed: <full commit OID>
pr: <full /pull/ URL>
```

`git/open-branch` records branch, base and remote. `code/peer-review` records
the final reviewed head. `git/push-and-open-pr` records the PR URL. Workflow
gates read branch and PR from this record. If a needed field is missing or
disagrees with Git or GitHub, stop and resolve the discrepancy.

## Branch to merge

Start from the intended base. In ticket-branch mode the launch hook opens the
branch before the first step. Otherwise the branch script switches to the recorded
branch or creates one from the current HEAD. Once it exists, the ticket on
that branch is the live copy. For older tickets, the recorded branch may need
its base and remote backfilled before the PR step.

On a code step, commit implementation and review changes. The PR script commits
the ticket and log before opening the PR, then records the URL, advances the
step, and pushes the handoff. A launch audit line can land locally after that
push; in ticket-branch mode the exit hook commits and pushes it. After the PR opens, whoever changes the ticket commits and pushes that
state on the branch. The owner runs the final bump before merging, then commits
and pushes `status: done` with the log so the merge carries the finished ticket
to the base. The agent-merge workflow does that in its merge script.

Before handing off code, fetch the base and rebase as appropriate. Inspect
staged, unstaged and committed work separately. Preserve unique changes on both
sides. If Git reports a conflict, a failed push, or unexpected dirt, keep local
state, report the failure, and resolve it before retrying.

## Ticket-branch mode

A workflow that declares `git: ticket-branch` makes `coga launch` run the
packaged `git/ticket-branch` hook around the whole launch. Launch itself stays
Git-free: it reads the frozen mode, runs the hook's `run.py enter` before it
reads the ticket and `run.py exit` when the launch ends, and reports their
exit codes. `--prompt-report` runs neither. Megalaunch skips these tickets,
and recurring templates must stay on `main`.

`enter` finds the ticket branch, switches to it and lets launch read the live
copy there:

- A recorded `branch:` in the current copy's `## Dev` wins. Without one,
  `enter` looks for local or fetched `coga/<slug-part>` and
  `coga/<slug-part>-<6 hex>` branches whose own ticket copy records that
  branch. It never fetches.
- With no match it creates `coga/<slug-part>` from `HEAD` (a suffixed name
  when taken) and records `branch:`, `base:` (the starting branch) and
  `remote:` (the base's upstream remote or `origin`) before the first step.
  A later `git/open-branch` step reuses that record and adds nothing.
- It refuses, before any lifecycle write, a detached `HEAD`; more than one
  matching branch; local and remote-tracking tips that have diverged; a
  recorded branch that no longer exists; a `## Dev` record with `branch:` but
  no `base:` or `remote:`; and uncommitted changes when it would switch
  branches. Run `coga sync`, or commit or stash, then launch again. Launching
  from the ticket branch itself allows uncommitted changes; `exit` commits
  them.

`exit` runs on every path once `enter` has started: a normal end, an owner
handoff, an agent failure, a timeout, a refusal and Ctrl-C. It takes the
starting branch, ticket branch, remote and slug from the state `enter` saved,
so it still publishes when the agent deleted the ticket. It runs `git add -A`
(every non-ignored change), commits `<slug>: launch handoff at <step>` (or
`(<status>)`, or `(ticket removed)`) when anything is staged, pushes with
upstream set, even from a clean tree, and switches back to the starting
branch. Because `enter` runs before classification, a launch that later
refuses (a terminal ticket, a failed agent preflight) still publishes the
checkout's changes.

On any failure, or when `HEAD` is no longer on the ticket branch, `exit`
stops where it is with local state intact and names the failed operation.
Launch exits non-zero; a launch that was already failing keeps its own code
and reports both. Recovery is manual: finish the push or switch with Git.

Both phases warn when the ticket is not tracked on the starting branch:
later launches from there cannot find it. Commit it on that branch, or
`git switch` to the ticket branch and launch from it. Launch keeps its
ordinary "not found" for a ticket missing from the current checkout.

Owner-held steps are worked through an assist (`coga launch <ref> --agent
<type>`), which goes through launch and gets both hooks. `coga bump` and
`coga mark` are not redirected; run them on the ticket branch.

## Shared audit log

Lifecycle commands append to `coga/log.md`. The scaffold sets `merge=union`
so both sides of an append conflict survive. Log compaction snapshots the log
and preserves bytes appended before its final read. An append between that
read and the atomic replacement can still be lost. Keep compaction and routine
writes apart when possible.
