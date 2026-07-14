---
slug: document-cross-machine-sandbox-dev-loop-friction-i
title: Document cross-machine/sandbox dev-loop friction in coga/codebase
status: done
owner: nick
human: nick
agent: claude
assignee: nick
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
---

## Description

Across roughly 15 code-ticket blackboards, the same cross-machine / sandbox
dev-loop frictions get re-discovered each time. Capture them once in the
`relay/codebase` context (`relay-os/contexts/relay/codebase/SKILL.md`, as a new
block) so future agents don't have to rederive them:

- (a) The checked-in `.venv` is Python 3.9, but Relay needs 3.11+ (it imports
  `tomllib`). Run the suite as
  `PYTHONPATH=<worktree>/src python3.12 -m pytest` instead of the venv python.
- (b) `codex review --base main` fails in-sandbox (the app-server is read-only)
  and must be rerun unsandboxed.
- (c) `relay validate` / `relay draft` fail when `.git` can't create
  `index.lock` inside a restricted sandbox.
- (d) Repo-wide `relay validate` reports pre-existing unrelated drift, so
  `relay validate --task <slug>` is the meaningful per-ticket check.

This is a doc task for a human to design and place the wording.

## Context

<!-- coga:blackboard -->

## Findings (orientation)

- **The task is written in "relay" naming; this repo is "coga".** No
  `relay-os/`, no `relay/` contexts, no `relay` CLI exist. The intended target
  is `coga/contexts/coga/codebase/SKILL.md`. Translation: `relay validate` →
  `coga validate`; `relay draft` → `coga create` (`coga draft` is the
  deprecated alias). Treating this as a coga repo, pending human confirmation.
- **`codebase` is repo-local only** — not a packaged bootstrap context (the
  packaged set is architecture/cli/patterns/period-task/principles/sync). So
  only `coga/contexts/coga/codebase/SKILL.md` needs editing; no template-tree
  sync required.
- **Friction (a) is already partly documented.** The "Daily commands" section
  already states "Use a 3.11+ interpreter. coga needs `tomllib`" and gives the
  `PYTHONPATH=$PWD/src <venv python> -m pytest` workaround for a broken `.pth`.
  The task's (a) is a sharper framing (the checked-in `.venv` itself is 3.9).
  Plan: fold (a) into that section rather than duplicate.
- **Frictions (b),(c),(d) are genuinely new.** None of sandbox `codex review`,
  `index.lock`, or `--task` scoping are covered. `coga validate --task <slug>`
  exists (verified in `src/coga/commands/validate.py`), so (d) maps cleanly.

## Plan (proposed, awaiting human sign-off)

Add a new `## Sandbox and cross-machine dev loop` section for (b),(c),(d) and
fold (a) into the existing "Daily commands" venv discussion. Wording is the
human's to design.

## Dev

- branch: `docs-sandbox-dev-loop-friction`
- worktree: `/home/n/Code/claude/coga-sandbox-friction-docs`
- commit: `6e94e72c` — edits `coga/contexts/coga/codebase/SKILL.md` only
  (repo-local context; no packaged-template sync needed).
- changes: (1) sharpened the "Daily commands" interpreter bullet to fold in
  friction (a) with accurate framing; (2) added a `## Sandbox and cross-machine
  dev loop` section covering (b) codex review read-only in-sandbox, (c) git
  `index.lock` failures, (d) `coga validate --task <slug>` scoping.
- tests: `PYTHONPATH=$PWD/src python3.12 -m pytest` → 913 passed, 1 skipped.
- pr: https://github.com/FastJVM/coga/pull/472

## Peer review

- Native review: sandboxed `codex review --base main` failed with the known
  read-only app-server error; reran unsandboxed from the feature worktree.
- Review finding: the first draft incorrectly said `coga validate` touches
  `.git/index.lock`. The validator is read-only by default and task-scoped
  validation should remain the sandbox-friendly check.
- Fix commit: `9974b032` (`peer-review: narrow git-sync sandbox note`) narrows
  the `index.lock` warning to state-changing git-sync transitions such as
  `coga create`, `coga bump`, and `coga mark ...`.
- Verification after fix:
  - `git diff --check`
  - `PYTHONPATH=$PWD/src python3.12 -m coga.cli validate --task document-cross-machine-sandbox-dev-loop-friction-i --json` -> ok_count 1, no issues
  - `PYTHONPATH=$PWD/src python3.12 -m pytest` -> 913 passed, 1 skipped, 1 pytest-cache warning because `.pytest_cache` was read-only

## Correction to friction (a)

Verified on this checkout: there is **no `.coga/.venv`** present and it is
**not committed**, so "the checked-in `.venv` is Python 3.9" is not literally
true for coga. What is true: the ambient `python3` is 3.9.12 (no `tomllib`)
and `python3.12` is available. Durable framing: don't trust the default
`python3`; name a 3.11+ interpreter explicitly (covers a stale/missing venv
too). Human confirmed: fold (a) into Daily commands; new section for (b/c/d).

## Usage

{"agent":"claude","cache_creation_input_tokens":89250,"cache_read_input_tokens":340878,"cli":"claude","input_tokens":16337,"model":"claude-opus-4-8","output_tokens":8416,"provider":"anthropic","schema":1,"session_id":"39deb049-6fb3-4b4b-8a3d-32aacb1cdbe5","slug":"document-cross-machine-sandbox-dev-loop-friction-i","step":"implement","title":"Document cross-machine/sandbox dev-loop friction in coga/codebase","ts":"2026-06-30T05:11:00.381535Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":676480,"cli":"codex","input_tokens":171139,"model":"gpt-5.5","output_tokens":5500,"provider":"openai","schema":1,"session_id":"019f16f0-1852-75d2-9ea3-663483462423","slug":"document-cross-machine-sandbox-dev-loop-friction-i","step":"peer-review","title":"Document cross-machine/sandbox dev-loop friction in coga/codebase","ts":"2026-06-30T05:25:28.788594Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":92303,"cache_read_input_tokens":427007,"cli":"claude","input_tokens":14830,"model":"claude-opus-4-8","output_tokens":5966,"provider":"anthropic","schema":1,"session_id":"202cea6a-15b6-4003-bcdb-833ebacab0e3","slug":"document-cross-machine-sandbox-dev-loop-friction-i","step":"open-pr","title":"Document cross-machine/sandbox dev-loop friction in coga/codebase","ts":"2026-06-30T05:26:30.656280Z","usage_status":"ok"}
