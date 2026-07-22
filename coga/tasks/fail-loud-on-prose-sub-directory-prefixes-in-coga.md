---
slug: fail-loud-on-prose-sub-directory-prefixes-in-coga
title: Fail loud on prose sub-directory prefixes in coga create
status: active
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Observed in the 2026-07-20 recurring sweep (demo-hackathon Dream run): an agent
ran `coga create "Populate the base repo context stub (coga/context.md)"` and,
because `/` means sub-directory, got a mangled on-disk path — a directory
literally named `coga/tasks/Populate the base repo context stub (coga/` with
the ticket leaf `context-md.md` inside. The agent noticed and repaired it by
hand, but junk briefly landed on disk and cost a cleanup loop.

`_normalize_create_dir` (src/coga/create.py) already rejects `..`, empty
segments, `_`-prefixed segments, and task-nesting — but accepts any other
string, including prose with spaces and parentheses, as a directory prefix.

Fix: validate each prefix segment is slug-like (letters, digits, `.`, `_`
between chars, `-`; no whitespace or other punctuation). A prose segment
almost always means the *title* contained a literal `/`; the error must say so
and give both remedies — drop the slash and `mv` afterwards, or pass a
slug-like directory prefix. Update the packaged `coga/cli` context's
`coga create` paragraph (which currently documents the silent-path behavior)
in the same change.

## Context

Shipped in PR #621 (`claude/create-prefix-guard`), merged to `main`
2026-07-21. How it was resolved:

- `_DIR_SEGMENT_RE = ^[A-Za-z0-9][A-Za-z0-9._-]*$` in `src/coga/create.py`,
  checked per segment in `_normalize_create_dir` after the existing
  `..`/`_`-prefix guards. The error names the offending component and gives
  both remedies (drop the slash + `mv`, or pass a slug-like prefix). It
  surfaces through the existing `except (TaskValidationError, ValueError)` →
  `_bail` path in `commands/create.py`, so a prose prefix exits 2 and nothing
  lands on disk.
- Machine creators are unaffected: recurring/retire/dream land nested slugs
  via `slug_override` (fixed slug-like values), never via `directory`. Only
  the human/agent-facing `coga create --dir` path is guarded.
- The packaged `coga/cli` context's `coga create` paragraph was updated in the
  same change — it previously documented the silent-path behavior this ticket
  removed.
- Coverage in `tests/test_create.py`: prose component rejected with nothing
  written (unit + CLI level), slug-like components (`v2.1/sub-dir_x`) still
  accepted.

<!-- coga:blackboard -->

## Dev

- branch: claude/create-prefix-guard
- pr: https://github.com/FastJVM/coga/pull/621 (merged 2026-07-21)

## Already satisfied

Closed without a new branch: every item in the description is on `main` as of
PR #621. Verified in this session — `_DIR_SEGMENT_RE` at
`src/coga/create.py:30` and the per-segment check at `src/coga/create.py:266`;
`coga/cli` context paragraph updated; `tests/test_create.py` covers both the
rejection and the still-accepted slug-like case. Full suite at implementation
time: 1373 passed, 1 skipped.
