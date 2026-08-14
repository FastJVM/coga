---
slug: retire-never-removes-a-worktree-that-ran-the-tests
title: Retire never removes a worktree that ran the tests
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
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
step: 1 (design)
---

## Description

`coga retire` promises to dispose of a finished ticket's feature checkout, and
the `dev/code` context tells agents to rely on that ("You do not remove your own
feature checkout. `coga retire` does"). In practice that half of retire almost
never fires: it refuses any checkout holding tracked, untracked, **or ignored**
state, and every code ticket's own workflow runs `python -m pytest`, which
leaves `.pytest_cache/` and `__pycache__/` behind. The refusal is not an edge
case — it is the normal outcome for a code ticket.

The knock-on is that the branch stays pinned by the surviving worktree, so
`branch-sweep` can only report it as `skipped-worktree-pinned`, and neither
cleanup path can ever finish. Worktrees and branches accumulate until a human
notices and clears them by hand.

Decide how to close the gap without weakening the no-data-loss contract. Four
directions, in rough order of how much judgment they hand to Coga:

1. **Stop generating the junk.** Run the workflow's tests with caches outside
   the checkout (`-p no:cacheprovider`, `PYTHONPYCACHEPREFIX`, or equivalent).
   The gate keeps its exact current meaning — anything ignored is still
   precious — and the fix lands in the `code/*` skills rather than in retire.
   Weakness: it only covers the tooling we remember to redirect, and says
   nothing about a checkout where someone ran something else.
2. **Report and offer.** Keep the refusal, but when the only state is ignored,
   say so distinctly and print the explicit opt-in (`coga retire
   --force-checkout <slug>`, or the `git worktree remove --force` line). The
   human keeps the judgment; retire stops silently no-opping.
3. **Classify by disposability.** Treat a known regenerable set
   (`.pytest_cache/`, `__pycache__/`, `.ruff_cache/`, `.mypy_cache/`) as
   removable and keep refusing on anything else. Cheap and it fixes the actual
   observed case. Weakness: retire begins deciding which of the operator's
   ignored files matter, and the list is Python-specific in a tool that is not.
4. **Distinguish ignored-unique from ignored-regenerable generally.** The
   honest version of (3), but there is no reliable general signal for it —
   probably not worth the machinery.

(1) and (2) compose and neither requires Coga to judge the operator's files;
that is the pairing to beat.

Whatever ships, the `dev/code` context's "who retires the checkout" section
must match the real behavior in the same PR — right now it documents a cleanup
that does not happen.

## Context

Found on 2026-08-14 auditing seven leftover worktrees under `~/Code/claude/`.
Both `coga retire` runs that day refused removal with the same message:

```
Worktree cleanup: '/home/n/Code/claude/coga-recurring-owner-gate' contains
tracked, untracked, or ignored local state ('!! .pytest_cache/.gitignore',
... and 157 more) — left in place.
```

Every entry in both refusals was `.pytest_cache/` or `__pycache__/`. The
worktrees were otherwise clean — the only non-cache ignored file across all of
them was a `coga/coga.local.toml` byte-identical to the primary checkout's.

Code anchors:

- the gate: `src/coga/branchcleanup.py:208`
- the status probe it reads: `_worktree_local_state`,
  `src/coga/branchcleanup.py:306` (`git status --porcelain=v1
  --untracked-files=all --ignored`)
- why it is stricter than git: `src/coga/branchcleanup.py:26` and `:309` —
  `git worktree remove` without `--force` deletes ignored files, so retire has
  to ask for them explicitly. That reasoning is sound and should survive
  whatever fix ships.
- the promise this breaks: `coga/contexts/dev/code/SKILL.md`, "Who retires the
  checkout"
- the downstream report: `src/coga/branchsweep.py:24` and `:138` (worktree-pinned
  branches are preserved and reported, never swept)

Sibling ticket: `autoclose-should-name-the-retire-follow-up` covers the other
half of the same accumulation problem — nothing points at `coga retire` after an
automatic close.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
