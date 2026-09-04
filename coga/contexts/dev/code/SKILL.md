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

When an agent sandbox mounts the primary checkout's `.git` metadata read-only,
`git worktree add` cannot create its branch lock. In that case an independent
`git clone --no-hardlinks` under `/tmp`, repointed to the real remote and
freshened from the control branch, is the accepted feature checkout. Record its
repo path in `worktree:` exactly like a linked worktree. This keeps source and
Git metadata writable without broadening the sandbox or moving control-plane
ticket writes onto the feature branch.

This keeps task-state edits (`ticket.md`, plus the repo-global `coga/log.md`)
from mixing with source changes on a feature branch. If task-state
changes need to be committed, commit them separately from the code PR.

### Keep the feature checkout durable

A `/tmp` checkout survives only until the next reboot, and the sandbox fallback
above puts one there by design. For work that may span sessions, either place
the feature checkout on a durable sibling path (`../coga-<branch>`) or push the
branch to the remote before ending the session. **An unpushed branch whose only
checkout is under `/tmp` is one reboot away from unrecoverable** — the docs
rewrite lost an entire implement pass exactly this way. The branch existed in no
local, packed, or remote ref, so the only recovery was a human-decided rewind to
step 1 and a full redo from current `main`.

A wiped `/tmp` worktree is not harmless once the work itself is safe, either.
Its registration outlives the directory and keeps pinning its branch until
`git worktree prune` runs, so merged branches accumulate invisibly — one probe
of this repo found 18 prunable worktrees, each pinning a branch that
`branch-sweep` then could not delete. That is why `coga run branch-sweep` prunes
repo-wide before it enumerates.

### Who retires the checkout

You do not remove your own feature checkout. `coga retire` does, at the
lifecycle event where the ticket still exists and its `## Dev` lines are still
readable. Retire removes the recorded worktree *first* — a branch still checked
out in a linked worktree cannot be deleted at all — and then prunes the branch.
Leave `worktree:` recorded and accurate; that line is what retire acts on.

Retire only removes a checkout Git identifies as a **linked worktree of the same
repository** that still holds the recorded branch. It also refuses cleanup when
another non-terminal ticket in any Coga workspace in the same Git checkout
records the branch/worktree, while any PR for that head remains open, or when
the branch has neither landed on the control branch nor retained the exact head
of its recorded merged PR. Remote deletion verifies that exact head again and
uses a force-with-lease, so a reused branch is never deleted on stale PR state.

Before removal, retire checks tracked, untracked, **and ignored** files. Tracked
and untracked state always preserves the checkout. So does ignored state — with
one carve-out: the regenerable tool caches `__pycache__/`, `.pytest_cache/`,
`.ruff_cache/` and `.mypy_cache/` are derived from files already in the repo and
reappear on the next tool run, so retire deletes them along with the checkout and
says how many went. Without that carve-out retire refused on every code ticket,
because every code ticket runs its tests in the feature worktree. Machine-local
config — `coga.local.toml`, `.env`, `.venv/`, `.coga/` — is ignored but not
regenerable, and still preserves the checkout.

These survive and are reported for manual disposal:

- an independent fallback clone (the `/tmp` sandbox path above) — it is a
  separate repository, not a linked worktree;
- the checkout currently running `coga retire`, a stale path now holding
  another branch, a checkout shared with another live ticket (including one in
  a sibling Coga workspace), or a branch still used by an open PR;
- a worktree with tracked or untracked local state, or with ignored state
  outside the regenerable caches above (machine-local config such as
  `coga.local.toml`, `.env`, `.venv/`, `.coga/`), or a locked one. For the
  ignored-only case retire prints the explicit opt-in —
  `git worktree remove --force '<path>'` — and records it in the retro task it
  creates, so the note outlives the scrollback. It never offers that line over
  tracked or untracked state, where forcing would destroy real work;
- a recorded path that is already gone. Retire reports the stale registration
  rather than pruning it; `coga run branch-sweep` prunes repo-wide and reports
  any branch still pinned by a live worktree as `skipped-worktree-pinned`.

## The `## Dev` blackboard section

Every code-style ticket gets a `## Dev` section near the top of its
blackboard, with named lines. Three are canonical:

```
## Dev
branch: <branch-name>
worktree: <path-to-feature-worktree>
pr: <pr-url>
```

`branch:`, `worktree:`, and `pr:` are machine-readable fields. A bare
`branch:` / `worktree:` value consumes the whole remainder of its line, which
keeps worktree paths containing spaces valid; a bare `pr:` value ends at the
first whitespace, since a URL never contains any. Keep arbitrary prose out of a
bare value. When a repository annotation is useful, either backtick-delimit the
value before the annotation:

```
branch: `feature/name` (Magicator repo)
worktree: `/tmp/path with spaces` (Magicator repo)
pr: `https://github.com/acme/repo/pull/7` (Magicator repo)
```

or put the annotation on a separate line:

```
branch: feature/name
worktree: /tmp/path with spaces
pr: https://github.com/acme/repo/pull/7
Repository note: Magicator repo
```

When to write each:

- **`branch:`** — the moment you create the branch. Don't wait until
  the PR is open. If you crash or hand off mid-step, the next agent
  needs to know which branch your work is on.
- **`worktree:`** — the moment you create the feature worktree. Use a
  path outside the primary checkout so it does not appear as an
  untracked directory in the control-plane checkout.

  Both `branch:` and `worktree:` must be written into the ticket copy of the
  checkout `coga bump` will run from. In the workflows above the implement step
  declares `requires: branch`, so `coga bump` refuses to advance until it reads
  both lines in *that* copy. Writing `## Dev` from inside the feature checkout
  and then bumping from the primary checkout strands the write on the feature
  branch: bump syncs a ticket that never saw it, and `coga open-pr` fails a step
  later with "No usable `branch:` recorded" even though implement did record it.
  Either write the lines in the checkout you bump from, or run `coga bump` from
  the checkout that has the write. The gate checks presence, not freshness — on
  a retried implement, confirm the recorded lines describe the current attempt.
- **`pr:`** — the full PR URL, one line. A trailing annotation after the URL
  is fine (`pr: <url> (no CI configured on the repo)`) — and unlike the two
  fields above, `pr:` needs no backticks around the value to make one safe,
  because a bare `pr:` value ends at the first whitespace. The value must still
  contain `/pull/<number>`: a placeholder like `pr: (not opened yet)` or any
  other link reads as no PR at all. In workflows whose PR step uses
  `code/open-pr` (e.g. `code/with-review`, `code/with-self-review`,
  `code/design-then-implement`), you do **not** write this line by hand: the
  `code/open-pr` agent step runs `coga open-pr <slug>` from the primary control
  checkout; the command reads `branch:` / `worktree:`, pushes the recorded
  feature branch by name, opens the PR, and writes `pr:` back itself. Your job in
  the preceding steps is to make sure `branch:` and `worktree:` are recorded and
  the branch is committed — `coga open-pr` fails loud if they are missing or
  there is nothing to PR, and that step declares `requires: pr` so `coga bump`
  refuses to advance until `pr:` is recorded. In a hand-run flow, write `pr:`
  yourself as soon as `gh pr create` returns the URL.

Update in place, don't append. If you rebase onto a renamed branch
or create a fresh worktree or PR, overwrite the existing line. The
blackboard records *current* state, not history (that's the global `coga/log.md`'s
job).

## Why a section, not frontmatter

YAML frontmatter is reserved for canonical task state (`status`, `step`,
`assignee`, `workflow`). Branch and PR linkage remains legible working state
under `## Dev`. Several focused Coga consumers deliberately parse those lines:
the `code/open-pr` runner writes `pr:`, autoclose reads PR linkage and reports
the `coga retire` follow-up for the `branch:` / `worktree:` a closed ticket
leaves behind, and branch sweep protects recorded branches. That does not make them frontmatter fields or
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
