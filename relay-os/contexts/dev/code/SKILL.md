---
name: dev/code
description: Conventions for code-style tickets — how to record the git branch and PR on the ticket so the link is explicit and machine-readable. Attach this context on any ticket whose workflow produces a branch and PR.
---

# Code-task conventions

Code-style tickets produce a git branch and (usually) a pull request.
The link from ticket → branch → PR has historically been implicit,
inferred from "the branch is named after the slug." That convention
breaks every time it bends — a PR bundles two tickets, an agent picks
a different branch name, the slug is truncated. Anything that wants
to follow the link (auto-bump on merge, retro generation, status
views, code review tools) is forced to guess.

The fix is small and explicit: the agent records the branch and PR
on the ticket's blackboard in a known shape. Anything that needs the
link reads it directly.

## Checkout boundary

Treat the primary repo checkout as the Relay control-plane checkout.
Keep it on `main` when possible. Do code changes in a **dedicated git
worktree** — run `relay worktree create <slug>`, which puts it at the
deterministic path `<git-toplevel>/worktree/<slug>` on its own branch —
then return to the primary checkout for blackboard updates, `relay bump`,
`relay slack`, and `relay panic`. A worktree per task means concurrent
tasks never collide on one working tree.

This keeps task-state edits (`ticket.md`, plus the repo-global `relay-os/log.md`)
from mixing with source changes on a feature branch. If task-state
changes need to be committed, commit them separately from the code PR.

`worktree/` is gitignored at the toplevel, so a worktree never shows up
as untracked clutter in the control-plane checkout. **Hazard:** that same
ignore means a `git clean -fdx` in the primary checkout would delete an
in-flight worktree's uncommitted work — never `git clean -x` the
control-plane checkout while a worktree is live. Tear a worktree down with
`relay worktree remove <slug>`, which refuses a dirty tree and never uses
`--force`.

## The `## Dev` blackboard section

Every code-style ticket gets a `## Dev` section near the top of its
blackboard, with named lines. Three are canonical:

```
## Dev
branch: <branch-name>
worktree: <path-to-feature-worktree>
pr: <pr-url>
```

When to write each:

- **`branch:`** — the moment you create the branch. Don't wait until
  the PR is open. If you crash or hand off mid-step, the next agent
  needs to know which branch your work is on.
- **`worktree:`** — the moment you create the feature worktree. Run
  `relay worktree create <slug>` to put it at the deterministic
  `<git-toplevel>/worktree/<slug>` path (gitignored, so it stays out of
  the control-plane checkout), and record that path here.
- **`pr:`** — as soon as `gh pr create` returns the URL. One line,
  the full URL.

Update in place, don't append. If you rebase onto a renamed branch
or create a fresh worktree or PR, overwrite the existing line. The
blackboard records *current* state, not history (that's the global `relay-os/log.md`'s
job).

## Why a section, not frontmatter

YAML frontmatter is for fields the relay CLI reads (`status`, `step`,
`assignee`, `workflow`). Putting `branch:` / `pr:` there would imply
relay-the-CLI parses them, which it doesn't (yet). The blackboard is
the right home: human- and agent-readable plain text, and any tool
that wants the link can grep for `branch:` / `pr:` under `## Dev`
without a config plumbing change.

If a future feature needs first-class linkage (e.g. an auto-bump
hook firing off PR merge), it can either continue grepping the
blackboard or graduate the fields to frontmatter. The convention
here is forward-compatible with both.

## Multi-ticket PRs

A single PR sometimes covers two related tickets — a draft ticket
plus a code change, two small refactors that share a branch, etc.
In that case, every covered ticket records the same `branch:` and
`pr:` lines on its own blackboard. The link goes ticket → PR, not
PR → ticket; one PR can have many tickets pointing at it.

## What this context does not cover

- **Commit message style.** Use the repo's existing convention
  (`git log` for examples).
- **Branch naming.** No requirement to match the slug. Pick something
  short and descriptive; the blackboard makes the link explicit
  regardless.
- **PR description shape.** That belongs to the workflow step's
  skill, not to this context.

This context is narrow on purpose: just the link from ticket to
branch to PR. Extend in a separate context if more dev-task
conventions need a home.
