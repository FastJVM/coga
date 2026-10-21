---
name: coga/state-publication
description: Which Coga files publish to control, eligibility, and avoiding publication before review; authoring and sweep recovery live in its leaves.
---

# Publishing Coga state

Coga state becomes durable on the configured control branch.

Leaves: [authoring](authoring/SKILL.md), [sweep and recovery](sweep/SKILL.md).

## The Coga roots

Owner decision (2026-10-07): everything in the Coga root and the configured
contexts root publishes automatically — tickets, the log, recurring
templates, skills, workflows, shared `coga.toml`, `context.md`, and contexts.
There is no separate knowledge PR for files inside these roots; the accepted
tradeoff is that instruction edits there land directly, and Git history is
the visible record and the correction mechanism.

The roots are the configured Coga directory and contexts directory, with a
nested root counted once. When a launch moves the contexts root, its return
publishes the old-path deletions, new files, and config together.

**Eligible** means a regular file Git does not ignore. Every consumer asks Git
(`status`, `ls-files --exclude-standard`), so `coga.local.toml`, `.coga/` run
records, generated agent-skill views, caches, and other ignored artifacts stay
local and are never force-added. Untracked symlinks discovered through a
directory pathspec are skipped; explicitly named or tracked symlinks and paths
with symlinked ancestors are refused before reading their working bytes. Root
membership and Git path conversion are lexical: a directory link never adds
its target to the publication scope. Checkout cleanup rejects the same links.
Submodules are refused, including a dirty, staged, or
removed gitlink; a directory is never published as a submodule deletion.
Source
outside the roots, including the packaged copies under `src/`, is ordinary
code: it reaches control only through a branch and reviewed PR.

**Pre-review state publication hazard.** The sweep and authoring finalizer run
from whichever checkout invoked them. A feature checkout's *dirty* files in
the roots — ticket prose, log, recurring template (including `ticket.py`),
context, skill, or workflow — land on control before review. Committed ones
on a feature branch stay with the branch unless they are routine state, so
commit an edit you want reviewed before running a sweeping Coga command in
that checkout. Checkout practice is `coga/checkouts`.

Never `git add` `coga/tasks/**` or `coga/log.md` into a PR; `coga open-pr`
excludes that state from its cleanliness gate and refuses a branch whose only
commits are Coga state.
