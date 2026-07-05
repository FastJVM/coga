---
slug: write-real-coga-documentation-command-reference-gu
title: Write real Coga product documentation
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: codex
assignee: codex
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
step: 1 (implement)
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
