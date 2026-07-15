---
slug: make-open-pr-metadata-tolerate-annotated-branch-an
title: Make open-pr metadata tolerate annotated branch and worktree values
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Coga's deterministic `code/open-pr` step reads `branch:` and `worktree:` from
the ticket blackboard. The current parsers consume the entire remainder of the
line and then strip backticks only from the ends. A natural handoff such as:

```text
branch: `test/sliced-getfield-constantclass` (Magicator repo)
worktree: `/home/n/Code/magicator-sliced-getfield-cc` (Magicator repo)
```

therefore turns the explanatory suffix into part of the branch or filesystem
path. `open-pr` then fails even though the recorded branch and worktree exist.
This is especially common when a Coga task in one repository owns feature work
in another repository.

Make backtick-wrapped metadata genuinely delimited: when the value begins with
a backtick, parse through the matching closing backtick and ignore trailing
prose. Preserve the existing contract for bare values, including legitimate
worktree paths containing spaces. A value that opens with a backtick but has
no closing backtick falls back to the current bare-value handling (whole
remainder, edge-stripped) — don't error on it.

Update the implement/open-PR guidance to call `branch:` and `worktree:`
machine-readable fields and show how to put repository annotations either
after a backtick-delimited value or on a separate line. The canonical home of
the `branch:`/`worktree:` convention is `coga/contexts/dev/code/SKILL.md` —
update it there, not only in the `code/implement` and `code/open-pr` skills
that defer to it. Improve the missing worktree/branch failure hint if useful
so an ambiguous inline annotation is easy to recognize.

Acceptance criteria:

- `parse_branch_name()` returns `feature/name` for both
  `branch: feature/name` and `branch: \`feature/name\` (other repo)`.
- `parse_worktree_path()` returns `/tmp/path with spaces` for both a bare value
  and `worktree: \`/tmp/path with spaces\` (other repo)`.
- Existing bare, list-prefixed, and backtick-only forms remain compatible.
- The deterministic open-PR recipe successfully uses annotated, quoted branch
  and worktree metadata rather than reporting a nonexistent worktree.
- Parser and open-PR regression tests cover the failure, and the relevant Coga
  test suite passes.

Out of scope: guessing whether arbitrary unquoted trailing words are prose or
part of a legitimate path. Such annotations must use backtick delimiters or a
separate line.

## Context

Observed in `/home/n/Code/xpllm` on task
`dacapo/fix-sunflow-slicecompiler-constantclass-constantcp`: the real clean
worktree `/home/n/Code/coga-test-sliced-getfield-cc` existed, but the recorded
value ended in ` (magicator repo)`, causing `code/open-pr` to exit 2 before
push or PR creation.

Code pointers: the parsers are `parse_branch_name()` and
`parse_worktree_path()` in `src/coga/autoclose.py` (~lines 75 and 94); both
capture to end-of-line and edge-strip backticks, which is the bug. The open-pr
recipe imports them, so fixing the parsers fixes the recipe. Regression tests
belong in `tests/test_autoclose.py` and `tests/test_open_pr.py`. Ordering
trap: `parse_worktree_path()`'s `startswith("(")` placeholder check must apply
to the extracted value, not the raw remainder of the line.

Sync reminder: the guidance files exist both live (`coga/skills/code/…`,
`coga/contexts/dev/code/`) and packaged
(`src/coga/resources/templates/coga/bootstrap/…`) — edit both copies, and note
`recipe.py` itself is duplicated in the bootstrap tree if its error hints
change. The parser fix in `src/coga/autoclose.py` is core-package-only.

Note (2026-07-14): PR #547 removed *per-launch* worktree isolation but
explicitly kept the feature-branch `## Dev` worktree convention this ticket
targets — the ticket is not obsoleted by it.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
