---
slug: make-open-pr-metadata-tolerate-annotated-branch-an
title: Make open-pr metadata tolerate annotated branch and worktree values
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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
step: 4 (review)
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

## Dev
pr: https://github.com/FastJVM/coga/pull/600
branch: `fix/annotated-dev-metadata`
worktree: `/home/n/Code/codex/coga-annotated-dev-metadata`

## Implementation notes

- Preserve the whole remainder for bare metadata so worktree paths with spaces remain valid.
- For a value beginning with a backtick, use the next backtick as the delimiter; if none exists, retain the existing whole-remainder fallback.
- Keep the live and packaged `dev/code`, `code/implement`, and `code/open-pr` guidance synchronized.

## Progress

- Added failing parser and deterministic open-PR regressions reproducing annotated quoted metadata.
- Implemented closing-backtick delimiting in both parsers, with placeholder validation after extraction.
- Updated the canonical and packaged guidance plus actionable open-PR failure hints.
- `tests/test_autoclose.py` and `tests/test_open_pr.py`: 50 passed.
- Full suite: 1330 passed, 1 skipped because Hatchling was absent from the base interpreter; `tests/test_packaging.py` then passed 3/3 using the cached Hatchling test dependencies.
- `coga validate --task make-open-pr-metadata-tolerate-annotated-branch-an --json`: 1 task OK, no issues.
- No example fixture change is needed: task layout, prompt composition mechanics, and workflow semantics are unchanged.

## Implement handoff

- Commit: `05af81678c69ad11c404f6993cfb5524abac1f1b` (`Tolerate annotated open-pr metadata`).
- Rebased cleanly onto `origin/main` at `6e151639964f14603cc6b656f409a5beee5f65f9`; branch is 0 behind / 1 ahead and the worktree is clean.
- Post-rebase full suite: 1330 passed, 1 environment skip; packaging suite separately passed 3/3 with cached Hatchling dependencies.
- Nothing pushed and no PR opened; the branch is ready for peer review.

## Dream Skill: validate-drift

Generated: 2026-07-18T22:33:49+00:00
Command: `coga validate --json --fix`
Task: `make-open-pr-metadata-tolerate-annotated-branch-an`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Peer review

- `codex review --base main`: no actionable findings.
- Rebased cleanly onto `origin/main` at `2299d2a5`; reviewed commit is `2f99268794bccb5c0e2150a6d9e693ed8f032b01`.
- Post-rebase full suite: 1330 passed, 1 environment skip; `tests/test_packaging.py` separately passed 3/3 with cached Hatchling dependencies.
- `coga validate --task make-open-pr-metadata-tolerate-annotated-branch-an --json`: 1 task OK, no issues.
- Branch is clean, 0 behind / 1 ahead of `origin/main`; no peer-review fix commit was needed.

## PR

### Summary

- Parse backtick-delimited `branch:` and `worktree:` values without absorbing trailing repository annotations, while preserving whole-line handling for bare values and unmatched backticks.
- Add parser and deterministic open-PR regressions, synchronize live and packaged metadata guidance, and make annotation-related failure hints actionable.

### Test plan

`PYTHONPATH="$PWD/src" python3.12 -m pytest` (1330 passed, 1 skipped); `tests/test_packaging.py` with cached Hatchling dependencies (3 passed).

## Dream Skill: validate-drift

Generated: 2026-07-18T22:38:00+00:00
Command: `coga validate --json --fix`
Task: `make-open-pr-metadata-tolerate-annotated-branch-an`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-18T22:43:01+00:00
Command: `coga validate --json --fix`
Task: `make-open-pr-metadata-tolerate-annotated-branch-an`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-18T22:47:16+00:00
Command: `coga validate --json --fix`
Task: `make-open-pr-metadata-tolerate-annotated-branch-an`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-18T22:49:22+00:00
Command: `coga validate --json --fix`
Task: `make-open-pr-metadata-tolerate-annotated-branch-an`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.
