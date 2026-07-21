---
slug: make-open-pr-metadata-tolerate-annotated-branch-an
title: Make open-pr metadata tolerate annotated branch and worktree values
status: done
owner: nicktoper
human: nicktoper
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

## Dev
pr: https://github.com/FastJVM/coga/pull/600
(merged on origin/main; the ticket was completed by a parallel checkout —
see `## Already satisfied` below)

## Already satisfied

The full change already landed on `origin/main` as PR #600, "Tolerate
annotated open-pr metadata" (commit `36fb9d9f`). Origin's history even shows
this very ticket slug progressing through its workflow there
(`Ticket: make-open-pr-metadata-tolerate-annotated-branch-an — step 4
(review)`); this local checkout's `main` and ticket state were simply stale.
Per-acceptance-item evidence, all verified in `FETCH_HEAD` (= origin/main):

- Annotated backtick branch parsing: `src/coga/autoclose.py`
  `parse_branch_name()` delimits a leading backtick through the matching
  close; covered by `test_parse_branch_name_backtick_wrapped_with_annotation`
  and `..._unclosed_backtick_falls_back_to_bare_form` in
  `tests/test_autoclose.py`.
- Worktree paths with spaces, bare and annotated:
  `test_parse_worktree_path_bare_form_preserves_spaces`,
  `..._backtick_wrapped_with_annotation`, `..._unclosed_backtick_falls_back`,
  and the placeholder check runs on the extracted value
  (`..._annotated_placeholder_is_none`).
- Bare / list-prefixed / backtick-only compatibility: existing forms all
  covered in the same test module.
- open-pr recipe works with annotated quoted metadata:
  `tests/test_open_pr.py::test_open_pr_uses_annotated_quoted_dev_metadata`.
- Guidance: `coga/contexts/dev/code/SKILL.md` (canonical) calls
  `branch:`/`worktree:` machine-readable and shows both annotation forms;
  packaged bootstrap copy and the implement/open-pr skills (live + packaged)
  updated too; `src/coga/open_pr.py` failure hints name the backtick fix for
  both branch and worktree.

Session cleanup: I had independently implemented the same fix on a
`open-pr-annotated-metadata` branch/worktree before discovering PR #600 during
the pre-handoff freshen; the duplicate branch and worktree were deleted,
nothing pushed.

Note for the owner: local `main` here has diverged from `origin/main`
(~3 local-only state commits vs ~37 on origin, including this ticket's own
origin-side progression to step 4) — a rebase replays conflicting `coga/log.md`
state commits. The control-plane checkout needs a manual sync; out of scope for
this session.

Note: the ticket context mentions a duplicated `recipe.py` in the bootstrap
tree; that is stale — the recipe now lives in `src/coga/open_pr.py`
(core package only), and the bootstrap open-pr skill dir holds just SKILL.md.

## Dream Skill: validate-drift

Generated: 2026-07-21T01:14:21+00:00
Command: `coga validate --json --fix`
Task: `make-open-pr-metadata-tolerate-annotated-branch-an`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.
