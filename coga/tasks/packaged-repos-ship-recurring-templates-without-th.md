---
slug: packaged-repos-ship-recurring-templates-without-th
title: Packaged repos ship recurring templates without the coga recurring context
status: in_progress
owner: nicktoper
human: nicktoper
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

`coga/contexts/coga/recurring/SKILL.md` is ~35 KB carrying the recurring system's whole contract:
template directory shape, `schedule:` / `workflow:` / `state_keys:` frontmatter, the control-branch
and `owner` gates, the serviced-period ledger in `coga/log.md`, the `ticket.py` deduction rule, and
promotion rules. It is **not** in the packaged bootstrap contexts
(`src/coga/resources/templates/coga/bootstrap/contexts/coga/`), while the recurring *templates*
themselves are packaged.

So a fresh `coga init` repo gets working recurring templates and none of the knowledge explaining
them. Decide whether to package the context, or to split a smaller operator-facing subset.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shard-08), classified `gap`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: package-recurring-context
worktree: /home/n/Code/claude/coga-package-recurring-context

## Decision

Package `coga/contexts/coga/recurring/SKILL.md` **verbatim** into
`src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md`,
rather than splitting a smaller operator-facing subset. Confirmed with the
human 2026-09-02.

Evidence gathered before deciding:

- **No subsetting precedent.** All 9 contexts already packaged (architecture,
  codebase, extension-model, important, launch-internals, patterns,
  period-task, principles, sync) are byte-identical to their live copies.
  A trimmed subset would be the repo's first intentional live/packaged
  divergence, so it could not be parity-tested and would drift.
- **Size is not disqualifying.** `architecture` and `sync` are 59,407 and
  59,220 bytes — both larger than recurring's 47,219.
- **A dangling reference exists today.** The already-packaged
  `patterns/SKILL.md` points readers at `coga/recurring` (its "The consumer is
  a recurring ticket" section and its closing cross-reference). In a fresh
  `coga init` repo that ref resolved to nothing.
- **No prompt-bloat cost.** Contexts resolve on demand via
  `resolve_context_ref` (local-first, bundled fallback); `coga/recurring` is
  composed only when a ticket attaches it, not into every prompt.
- **No packaging-config change needed.** `pyproject.toml` force-includes the
  whole `bootstrap/` tree, so a new context directory ships automatically.

Accepted tradeoff: fresh repos also receive the deep internal paragraphs
(delegate lease/generation, control-branch compare-and-set, autofix loop) and
`src/coga/*.py` filenames. This matches what `codebase` and `launch-internals`
already ship verbatim, so it is consistent with the established convention.

## Changes

Two files on `package-recurring-context`:

1. **`src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md`**
   (new) — byte-identical copy of the live context, 47,219 bytes.
2. **`tests/test_packaging.py`** — added `coga/recurring` to both
   `EXPECTED_BOOTSTRAP_RESOURCES` (it ships in the wheel) and
   `IDENTICAL_LIVE_PACKAGED_PAIRS` (it stays byte-identical to the live copy,
   so future edits to either side must be mirrored).

No `pyproject.toml` change: the `bootstrap/` tree is force-included wholesale.
No `example/` fixture change: contexts are package-backed and resolved on
demand, not scaffolded into a repo by `coga init`.

## Verification

- `python -m pytest` — **2203 passed** (Python 3.12 venv; the repo's own
  `.venv` lacks `pip`, which fails `test_wheel_includes_bootstrap_batteries`
  for environmental reasons unrelated to this change).
- `pip wheel` build inspected: the wheel now contains
  `coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md`
  alongside the other 10 bootstrap contexts.
- `bootstrap_context_path(None, "coga/recurring")` resolves to the packaged
  47,219-byte file — the fresh-repo path that previously resolved to nothing.

## Adjacent finding (follow-up ticket, not fixed here)

Three already-packaged bootstrap contexts have **no** packaging-test coverage —
they are in neither `EXPECTED_BOOTSTRAP_RESOURCES` nor
`IDENTICAL_LIVE_PACKAGED_PAIRS`:

- `coga/launch-internals` and `coga/period-task` — both have live copies that
  are currently byte-identical, so both could take a parity pair today.
- `coga/cli` — packaged with **no live copy** under `coga/contexts/coga/`, so
  it can take a ship-list entry but not a parity pair. Worth deciding whether
  that packaged-only context is intentional.

Neither list is generated from the tree, so a context can be added to (or
dropped from) `bootstrap/contexts/` without any test noticing. A follow-up
could derive the ship list from the directory walk instead of hand-maintaining
it. Out of scope for this ticket.
