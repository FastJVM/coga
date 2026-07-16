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

Treat the primary repo checkout as the Coga control-plane checkout.
Keep it on `main` when possible. Do code changes in a feature worktree
outside the primary checkout, then return to the primary checkout for
blackboard updates, `coga bump`, `coga slack`, and `coga block`.

This keeps task-state edits (`ticket.md`, plus the repo-global `coga/log.md`)
from mixing with source changes on a feature branch. If task-state
changes need to be committed, commit them separately from the code PR.

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
- **`worktree:`** — the moment you create the feature worktree. Use a
  path outside the primary checkout so it does not appear as an
  untracked directory in the control-plane checkout.
- **`pr:`** — the full PR URL, one line. In workflows whose PR step is
  the `code/open-pr` **script** (e.g. `code/with-review`,
  `code/with-self-review`, `code/design-then-implement`), you do **not** write
  this line by hand: the script reads `branch:` / `worktree:`, pushes, opens the
  PR, and writes `pr:` back itself. Your job in the preceding agent step is to
  make sure `branch:` and `worktree:` are recorded and the branch is committed —
  the script fails loud (and the step does not advance) if they are missing or
  there is nothing to PR. In a hand-run flow, write `pr:` yourself as soon as
  `gh pr create` returns the URL.

Update in place, don't append. If you rebase onto a renamed branch
or create a fresh worktree or PR, overwrite the existing line. The
blackboard records *current* state, not history (that's the global `coga/log.md`'s
job).

## Why a section, not frontmatter

YAML frontmatter is reserved for canonical task state (`status`, `step`,
`assignee`, `workflow`). Branch and PR linkage remains legible working state
under `## Dev`. Several focused Coga consumers deliberately parse those lines:
the `code/open-pr` runner writes `pr:`, autoclose reads PR linkage, and branch
sweep protects recorded branches. That does not make them frontmatter fields or
general config; each consumer reads the narrow blackboard convention it needs.

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
