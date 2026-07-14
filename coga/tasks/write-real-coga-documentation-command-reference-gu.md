---
slug: write-real-coga-documentation-command-reference-gu
title: Write real Coga product documentation
status: in_progress
owner: nicktoper
human: nicktoper
agent: codex
assignee: claude
contexts:
- coga/principles
- coga/architecture
skills: []
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 2 (peer-review)
---

## Description

Stand up real Coga documentation so the README can stay minimal and the product
has a place to explain itself. The docs should teach what Coga is, how it works,
and how a new operator actually starts using it.

The highest-priority deliverable is a strong **getting started** guide. It
should take a new operator from install/init through creating, launching, and
finishing a first task, while giving enough of the mental model to understand
what just happened. After that, build the supporting docs: core concepts,
task/workflow lifecycle, command reference, Dream/REM, notifications, aliases,
and the contributor/operator details a serious user needs.

This is a rewrite and organization pass, not a copy-paste of the old README.
The voice matters: write practical, concrete, human docs. Avoid generic AI
voice, filler, breathless marketing prose, and vague "unlock productivity"
claims. Prefer specific examples, real commands, and the product's own language.

Scope this as the first coherent documentation tree, not the final perfect docs
site. The getting-started path should be complete enough for a new operator to
use. The command reference should be accurate for the current CLI. Deeper
Dream/REM and contributor material can be concise as long as it gives readers a
real place to continue.

Done = a coherent markdown docs tree that a new user and a contributor can
navigate, with the README linking out to it ("Full docs →").

## Context

- **Docs home:** prefer a normal markdown tree under `docs/` rather than a
  generated site for this first real documentation pass. A likely shape is
  `docs/README.md` or `docs/index.md`, `docs/getting-started.md`,
  `docs/concepts.md`, and `docs/reference.md`, but let the implementation pick
  the smallest navigable structure that serves the reader. Make the chosen docs
  entrypoint canonical and link to it from README.
- **Source material:** the current `README.md` holds most of the raw content —
  the `## Getting Started`, `## Commands`, `## Task lifecycle`,
  `## External CLI Tools`, `## Layout`, notifications, aliases, Dream/REM, and
  development sections. Pull from it, but treat it as material to reorganize,
  verify, and rewrite.
- **README end state:** README should keep the short hook/install/key-values
  surface and link to the new docs. Do not leave the exhaustive manual duplicated
  in README unless `improve-readme` has not landed yet and you need a temporary
  compatibility shape; in that case, coordinate the final "Full docs →" target.
- **Canonical behavior:** `coga --help` and the `src/coga/commands/` modules
  are the source of truth for command flags/behavior. Verify the reference
  against them; do not trust old README prose where they disagree.
- **Command coverage:** document the public command surface that exists at
  implementation time, including flags shown by help output. If a command is
  mostly contributor/internal-facing, say so rather than omitting it. Start the
  command reference from the current help output so the minimum command list is
  generated from the CLI rather than guessed.
- **Voice/vision:** `docs/vision.md` plus the attached `coga/principles` and
  `coga/architecture` contexts define the product, concepts, and tone. The docs
  should sound like a competent operator explaining a tool they use, not like an
  AI-generated product page. Use `coga/architecture` selectively; it is there to
  explain concepts that help users understand behavior, not to dump the whole
  internal model into public docs.
- **Depth:** keep the implementation launchable. Do not try to make every
  section exhaustive. Getting started should be complete; concepts and reference
  should be accurate; Dream/REM, notifications, aliases, and contributor details
  can be concise if they point readers to the next useful place.
- **Verification:** at minimum, verify task structure with
  `PYTHONPATH=$PWD/src python -m coga.cli validate --task write-real-coga-documentation-command-reference-gu --json`.
  During the docs audit, run `coga --help` and relevant `coga <command> --help`
  output (or the equivalent source-checkout invocation) for any command reference
  claims. Check changed markdown for broken obvious links; if there is no link
  checker available, do a manual path/link audit and record that in the PR.
- **Current terminology:** document the product as it exists when implemented.
  Do not preempt the planned `workflow` -> `playbook` rename unless that change
  has already landed.
- **Open assumptions to check at implementation time:** whether `improve-readme`
  has landed, whether the CLI surface has changed, how much notification setup
  needs provider/secrets caveats, how deep Dream/REM docs should go in this first
  pass, and whether `workflow` is still the current term.
- **Sequencing:** this can proceed in parallel with or after `improve-readme`.
  Coordinate the "Full docs →" link target so the two land consistently.

<!-- coga:blackboard -->

## Dev

- branch: codex/write-real-coga-documentation
- worktree: /tmp/coga-real-docs
- base: local `main` at ec9f6b6e; `improve-readme` has not landed there, but the local `codex/improve-readme` branch preserves the accepted short README.
- scope check: docs-only. No code behavior changes planned.

## Findings

- Correction: `codex/improve-readme` has the accepted 73-line README, but local `main` still has the long README. This branch will carry the minimal README shape plus a `Full docs ->` link so the new docs tree has one entrypoint.

## Implementation

- Replaced the long root `README.md` with a short hook/install/key-values entrypoint and `Full docs -> docs/README.md`.
- Added the docs tree in `/tmp/coga-real-docs`: `docs/README.md`, `docs/getting-started.md`, `docs/concepts.md`, `docs/reference.md`, `docs/operations.md`, and `docs/development.md`.
- Command reference was checked against `env PYTHONPATH=src python -m coga.cli --help` plus command/subcommand help for the public surface.

## Verification

- `git diff --check`
- `env PYTHONPATH=src python -m coga.cli --help`
- `env PYTHONPATH=src python -m coga.cli launch --help`
- `env PYTHONPATH=src python -m coga.cli skill --help`
- `env PYTHONPATH=src python -m coga.cli recurring --help`
- Manual local-link path audit for changed docs: README/docs entrypoints, `docs/vision.md`, and referenced Coga context files all exist.
- `env PYTHONPATH=src python -m coga.cli validate --task write-real-coga-documentation-command-reference-gu --json` -> passed with no issues.

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":3586816,"cli":"codex","input_tokens":317962,"model":"gpt-5.5","output_tokens":36334,"provider":"openai","schema":1,"session_id":"019f33a0-c2c3-73b1-9aee-ea818a5de69c","slug":"write-real-coga-documentation-command-reference-gu","step":"implement","title":"Write real Coga product documentation","ts":"2026-07-05T20:28:05.737790Z","usage_status":"ok"}
