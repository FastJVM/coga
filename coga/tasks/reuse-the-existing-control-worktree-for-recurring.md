---
slug: reuse-the-existing-control-worktree-for-recurring
title: Run single-repo recurring from the control worktree that already exists
status: active
owner: nick
human: nick
agent: claude
assignee: nick
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
step: 1 (implement)
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
