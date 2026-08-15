---
slug: autoclose-skips-annotated-pr-lines
title: Autoclose skips annotated PR lines
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

`_PR_LINE_RE` in `src/coga/autoclose.py` is anchored to `$`, so a `## Dev`
`pr:` line carrying any trailing annotation after the URL parses as "no PR" and
the ticket is skipped — silently, since the sweep still prints `no tickets
bumped` and exits 0. Stop anchoring to `$` (or strip the trailing annotation) so
the URL is the capture, matching `_BRANCH_LINE_RE` / `_WORKTREE_LINE_RE`, which
already tolerate exactly this.

## Context

### The regex

`src/coga/autoclose.py:53`:

```python
_PR_LINE_RE = re.compile(r"^\s*(?:-\s*)?pr:\s*(\S+)\s*$", re.MULTILINE)
```

The comment directly above it (`:48-52`) already reasons about this failure
mode for the `- ` list-prefix case — "a bulleted `pr:` line is invisible to the
sweep, so a merged final-step ticket is silently skipped and left stranded
`in_progress`" — and then the same sentence applies verbatim to a trailing
annotation, which the `$` anchor still rejects.

The siblings at `:61` and `:65` capture `(.+?)` and normalize afterwards:

```python
_BRANCH_LINE_RE = re.compile(r"^\s*(?:-\s*)?branch:\s*(.+?)\s*$", re.MULTILINE)
_WORKTREE_LINE_RE = re.compile(r"^\s*(?:-\s*)?worktree:\s*(.+?)\s*$", re.MULTILINE)
```

### Live casualty

In the `admin` repo, `xero-reconcile-reminder` (final step 4/4, PR #55 merged
2026-06-10) sat stranded `in_progress` from that merge until Zach hand-closed it
on 2026-07-31, because its line read:

```
- pr: <url> (no CI configured on the repo — …)
```

That ticket has since been closed and deleted, so this defect has no
outstanding victim — it is the regex, not a stranded ticket, that needs fixing.

### The documentation alternative was considered and rejected

The other available fix is to keep the `$` anchor and document "the `pr:` line
carries a bare URL and nothing else". That was written up as a separate `admin`
ticket and closed as superseded: the constraint is the odd one out (its
`branch:` / `worktree:` siblings all state an annotation rule), and fixing the
regex deletes the need for the sentence. **If this is instead resolved by
keeping the anchor**, the sentence's home is the packaged `dev/code` context —
its `pr:` bullet is the only place describing the line's shape and the only one
omitting the annotation rule its siblings state.

### Origin

Verified against the package source during the 2026-08-15 Dream run in the
`admin` repo (Phase 3 contract audit), filed from
`admin/carry-three-verified-coga-bugs-upstream`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
