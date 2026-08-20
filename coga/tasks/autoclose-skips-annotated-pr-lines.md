---
slug: autoclose-skips-annotated-pr-lines
title: Autoclose skips annotated PR lines
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow: code/with-self-review
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

`src/coga/autoclose.py:115` (line numbers below are as of 2026-08-19; prefer the
symbol names, the file has already drifted once):

```python
_PR_LINE_RE = re.compile(r"^\s*(?:-\s*)?pr:\s*(\S+)\s*$", re.MULTILINE)
```

The comment directly above it (`:109-114`) already reasons about this failure
mode for the `- ` list-prefix case — "a bulleted `pr:` line is invisible to the
sweep, so a merged final-step ticket is silently skipped and left stranded
`in_progress`" — and then the same sentence applies verbatim to a trailing
annotation, which the `$` anchor still rejects.

The siblings at `:122` and `:127` capture `(.+?)` and normalize afterwards:

```python
_BRANCH_LINE_RE = re.compile(r"^\s*(?:-\s*)?branch:\s*(.+?)\s*$", re.MULTILINE)
_WORKTREE_LINE_RE = re.compile(r"^\s*(?:-\s*)?worktree:\s*(.+?)\s*$", re.MULTILINE)
```

`parse_branch_name` / `parse_worktree_path` (`:139`, `:163`) do the normalizing:
a leading backtick delimits the value through its matching closing backtick
(which is what makes `` branch: `name` (annotation) `` work), and an unmatched
backtick falls back to whole-line stripping. Whatever shape the `pr:` fix takes,
it should land in the same place — normalization inside `parse_pr_url`, not a
third bespoke line-regex dialect. A URL cannot contain whitespace, so dropping
the `$` anchor and keeping the `(\S+)` capture is likely sufficient on its own;
add backtick-stripping so the `` pr: `<url>` (annotation) `` shape the siblings
document also parses.

### Blast radius is wider than the sweep

`parse_pr_url` is shared infra, not an autoclose-private helper. Consumers as of
2026-08-19:

- `src/coga/step_gate.py:45` — backs the `requires: pr` bump gate. An annotated
  `pr:` line therefore also makes `coga bump` refuse to advance the PR step of
  `code/with-review` / `code/with-self-review`, reporting "no PR recorded" for a
  ticket that has one.
- `src/coga/open_pr.py:338, :533` — the idempotency check (`already`) and the
  post-write round-trip verification (`parse_pr_url(current) != url`). Note
  `open_pr.py` has its *own* `_PR_LINE_RE` at `:149` (`pr:.*$`) which already
  tolerates annotations and rewrites the **whole** line — so a re-run of
  `coga open-pr` silently discards any annotation a human added. Out of scope to
  change, but worth knowing before writing the round-trip test.
- `src/coga/branchcleanup.py:468` — branch-sweep / retire protection.
- `src/coga/pr_assist.py:82`, `src/coga/commands/launch.py:307, :1574, :1936`.

The fix is one regex, but the test plan should cover the gate and the open-pr
round-trip, not only the sweep.

### Tests

`tests/test_autoclose.py` holds the existing parser tests
(`test_parse_pr_url_finds_under_dev`, `test_parse_pr_url_returns_none_without_dev_section`)
— extend there. `tests/test_autoclose_sweep.py` and `tests/test_retire.py` cover
the sweep and retire paths.

### Doc sync

`dev/code` is the only place documenting the `pr:` line's shape, and its bullet
("the full PR URL, one line") is the odd one out — its `branch:` / `worktree:`
siblings both state the backtick-delimit-then-annotate rule. Once the regex
tolerates annotations, update that bullet to state the same rule. Per
`CLAUDE.md`, change **both** copies:

- `coga/contexts/dev/code/SKILL.md` (live repo copy)
- `src/coga/resources/templates/coga/bootstrap/contexts/dev/code/SKILL.md` (packaged)

They are byte-identical today; keep them so.

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
