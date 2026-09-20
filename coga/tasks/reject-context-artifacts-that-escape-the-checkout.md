---
title: Reject context artifacts that escape the checkout
status: in_progress
owner: nicktoper
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
step: 1 (implement)
agent: claude
---

## Description

Reject context artifacts whose symlink targets cannot be reproduced from the same checkout. The configured contexts root is already checked, but a tracked `<contexts-root>/team/style/SKILL.md` symlink can still resolve outside it into machine-local prose.

This is a provisional P2 fix scope from [the triage](triage-five-review-comments-that-merged-unanswered.md). Owner verdict is unset; keep the draft unactivated.

### Evidence and source

Original [PR 704 comment](https://github.com/FastJVM/coga/pull/704#discussion_r3834289315); source ticket: [move-cogacontext-to-roodoc-so-its-easier-for-human](move-cogacontext-to-roodoc-so-its-easier-for-human.md). Assessed 2026-09-18 at `4d828256d28bf772d17aa8ffa1b47d6f436ca57b`.

A local-Git probe committed an external-target `SKILL.md` symlink under a configured relocated root. Config loading, task validation and composition accepted it and the external marker entered the prompt. Removing only the external file still allowed config loading, while context resolution disappeared and composition failed. Root-component rejection tests therefore do not cover the artifact concern.

### Expected behavior and scope

Inspect `config._require_trackable_context_entry`, `resolve_layout_contexts_path`, `paths.resolve_context_path`, `validate.validate_task`, and `compose.compose_prompt_report` in `src/coga/`. Enforce reproducible actual context resolution, including symlink chains and symlinked ancestor directories beneath a valid root. Invalid existing local artifacts must fail loudly before a bundled fallback can hide them.

Proposed policy: reject escaping, dangling, cyclic, ignored, or otherwise unpublishable context targets. Preserve an internal symlink only if its complete target chain belongs to this checkout and is guaranteed to travel with the context through the normal state-publication path. If that proof needs excessive machinery, reject artifact symlinks with an actionable error instead; the owner can choose that narrower rule at this draft's scope review. Do not impose a new symlink policy on skills or ordinary attachments.

The original reproduction concerns relocated roots. Apply the artifact invariant to default roots too if they resolve the same unsafe file; keep the public behavior and test coverage explicit. Preserve ordinary local-first bundled resolution for genuinely absent local refs.

### Acceptance and focused verification

- A tracked external `SKILL.md` symlink and a chained escape fail clearly before prompt composition.
- A dangling or cyclic local artifact does not silently disappear into bundled fallback.
- Check ignored/unpublished in-checkout targets and a symlinked context ancestor directory. Cover allowed reproducible internal links only if retained by the approved policy.
- A second clone either composes the same approved context bytes or consistently rejects the invalid artifact; do not rely only on the root validator.
- Extend `tests/test_config.py`, `tests/test_layout_contexts.py`, and focused resolver/composer/validation coverage. Keep ordinary file, trackable marker, ignored scaffold and bundled-only cases working.
- Update the owning relocatable-context/artifact contract in `coga/contexts/coga/architecture/SKILL.md`, the PR 704 gotcha in `coga/codebase`, and their packaged twins; run packaging checks.

Tradeoff: repositories using local external context links will need tracked copies or an approved internal layout. Out of scope: moving the contexts tree, the broader documentation redesign, or any live config edits during triage.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
