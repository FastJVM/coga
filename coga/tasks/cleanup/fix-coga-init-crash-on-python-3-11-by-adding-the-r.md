---
slug: cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r
title: Fix coga init crash on Python 3.11 by adding the resources package init
status: in_progress
owner: nicktoper
human: nick
agent: claude
assignee: codex
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
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
step: 2 (peer-review)
---

## Description

`coga init` crashes on Python 3.11 — the oldest interpreter Coga supports
(`requires-python = ">=3.11"`) — with:

```
TypeError: MultiplexedPath.joinpath() takes 2 positional arguments but 3 were given
```

`src/coga/resources/` ships no `__init__.py`, so `coga.resources` is an
implicit **namespace** package. `importlib.resources.files()` returns a plain
`pathlib.Path` for a regular package but an
`importlib.resources.readers.MultiplexedPath` for a namespace one — and on
3.11 that class is `def joinpath(self, child)`, taking exactly one segment. It
only became `joinpath(*descendants)` in 3.12.

Every multi-segment resource lookup therefore raises on 3.11:

- `paths.packaged_template_path` (`paths.py:46`) — the shared helper behind
  every bootstrap skill/context/workflow resolution and prompt composition
- `commands.update.packaged_template_root` (`update.py:247`) — what `coga init`
  dies in
- `commands.update.packaged_bootstrap_skills_dir` (`update.py:261`)
- `managed_skills.managed_skill_manifest_root` (`managed_skills.py:74`)
- `dream_cleanup_orphan_markers` (`dream_cleanup_orphan_markers.py:156`)

3.12 happens to work, which is why the break stayed invisible in local
development and CI.

## Acceptance criteria

- [x] `coga.resources` is a regular package, so `files()` returns a `Path` on
      every supported interpreter.
- [x] `coga init` completes on a real Python 3.11.
- [x] A regression test fails if the package marker is removed again.
- [x] The marker is guarded as shipping in the built wheel.
- [x] Full suite passes on 3.11 and 3.12.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: resources-pkg-init
worktree: /home/n/Code/claude/coga-resources-pkg-init

## Findings

Root cause confirmed against CPython source, not inferred. Python 3.11's
`Lib/importlib/resources/readers.py` defines:

```python
def joinpath(self, child):   # 3.11 — one segment only
```

widened to `joinpath(*descendants)` in 3.12. `MultiplexedPath` also has no
`__fspath__`, so the `Path(files(...).joinpath(...))` conversions in
`paths.py` / `update.py` would fail on a directory resource regardless of
segment count — the single-arg rewrite alternative would have needed fixing
too.

Reproduced and fixed on a real CPython 3.11.15 (fetched with `uv python
install 3.11`), not simulated:

- without the fix: `coga init` → `TypeError: MultiplexedPath.joinpath() takes
  2 positional arguments but 3 were given` (from `packaged_template_root`, on
  the two-segment `templates/coga`)
- with the fix: `coga init --user tester` completes and lays down
  `coga/{coga.toml,context.md,contexts,recurring,skills,tasks,workflows,log.md}`

## Decisions

**Chose the package marker over rewriting the call sites.** The alternative —
chaining single-arg `joinpath` at each of the five call sites — touches five
modules, is easy to get wrong, does not fix the missing `__fspath__`, and
leaves the namespace-package footgun armed for the *next* call site someone
adds. One `__init__.py` fixes the class of bug at its source. No behavior
change on 3.12.

**Gave the `__init__.py` a real docstring** rather than leaving it empty like
`commands/__init__.py`. An empty file here reads as deletable cruft, and
deleting it silently reintroduces a 3.11-only crash that 3.12 CI would not
catch. The docstring says why it is load-bearing.

**Test asserts the invariant, not the symptom.** The multi-segment call
happens to succeed on 3.12, so a test that only exercises
`packaged_template_path` would pass on a 3.12 runner even with the bug
present. `test_coga_resources_is_a_regular_package` asserts
`coga.resources.__file__ is not None` and that `files()` returns a `Path` —
version-independent, and verified to fail when the marker is removed.

## Changes

- **new** `src/coga/resources/__init__.py` — the fix, with a docstring
  explaining why it must not be deleted.
- `tests/test_packaging.py` — two regression tests
  (`test_coga_resources_is_a_regular_package`,
  `test_packaged_template_path_accepts_multiple_segments`), plus
  `coga/resources/__init__.py` added to `EXPECTED_BOOTSTRAP_RESOURCES` so the
  existing wheel-build test guards that it actually ships.

No template/context sync needed: this is Python source, not a shipped Coga OS
context or template, so the `coga/` ↔ `src/coga/resources/templates/coga/`
pairing in CLAUDE.md does not apply.

## Adjacent, not fixed here

`src/coga/commands/__init__.py` is empty and `commands` is a regular package
only because of it — same latent fragility, but nothing in the codebase calls
`files("coga.commands")`, so there is no bug to fix and it stays out of this
diff.

## Verification

Commands run, all from the feature checkout unless noted:

- `pytest` on **CPython 3.11.15** — 2205 passed (re-run after the rebase)
- `pytest` on **CPython 3.12.12** — 2205 passed (re-run after the rebase)
- `coga validate --json` (primary checkout) — no issues for this ticket; the 4
  reported errors are pre-existing `unsynthesized-draft-blackboard` on
  unrelated `v2/*` drafts
- `coga init --user tester` in a throwaway git repo on 3.11 — completes, lays
  down `coga/{coga.toml,coga.local.toml,context.md,contexts,recurring,skills,tasks,workflows,log.md}`
- same `coga init` with `resources/__init__.py` removed on 3.11 — crashes as
  reported in the ticket, confirming the fix is what closes it
- `test_coga_resources_is_a_regular_package` with the marker removed — fails,
  confirming the regression test actually guards the invariant

The 3.11 interpreter was fetched with `uv python install 3.11`; the local
default `python` is 3.9 (conda) and the only system interpreter is 3.12, which
is why this never reproduced locally before.

## Note: ticket renamed mid-step

`main` advanced during this step (`fb0992a6`, `c1254655`) and moved this ticket
into the phase-0 audit triage queue: `coga/tasks/` →
`coga/tasks/cleanup/`, slug `fix-coga-init-crash-on-python-3-11-by-adding-the-r`
→ `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r`. The primary
checkout was fast-forwarded and these blackboard edits re-applied onto the new
path with the new slug preserved; no other frontmatter field changed. The
feature branch rebased onto `c1254655` without conflict — it touches only
`src/` and `tests/`.
