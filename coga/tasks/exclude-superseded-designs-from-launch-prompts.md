---
title: Exclude superseded designs from launch prompts
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
launch_generation: pending:ab4149d5-0dfb-48f3-8020-02d02c7f2955
---

## Description

Keep archived ticket designs available to humans without automatically presenting their full text as current blackboard state on every launch. This addresses the surviving prompt-composition part of PR 755; its draft-synthesis-gate issue is already fixed.

This is a provisional P2 fix scope from [the triage](triage-five-review-comments-that-merged-unanswered.md). Owner verdict and archive-placement decision remain unset. Keep this draft unactivated until nicktoper accepts or revises the proposed behavior.

### Evidence and source

Original [PR 755 comment](https://github.com/FastJVM/coga/pull/755#discussion_r3937900285); source ticket: [give-a-ticket-s-superseded-design-one-documented-h](give-a-ticket-s-superseded-design-one-documented-h.md). Assessed 2026-09-18 at `4d828256d28bf772d17aa8ffa1b47d6f436ca57b`.

The partial fix `4e544d356a53b94a332c24e793ca8d6a1c833d51`, merged in `c4482fae9cb6e63e41c47dd156c08f66f2fee09c` (PR 755), excludes exact archive sections from synthesis checks and preserves them through activation. A 1,558-character archive passes that gate, unrelated scratch still fails, and all 60 abandoned-design markers still enter `compose_prompt`. Archive inclusion is verified; model confusion is a plausible consequence, not a measured incident.

### Proposed behavior and scope for owner review

Recommended minimal change: retain the existing on-disk archive and its headings, but exclude exact top-level `## Superseded designs` sections from the automatically composed blackboard. Keep a short archive pointer for deliberate reading and keep current decisions and reasons in the live body/blackboard. This avoids moving every historical ticket. The original comment's above-fence move is an alternative, not an approved requirement; if the owner chooses it, revise this draft before activation.

Inspect `src/coga/compose.py::compose_prompt_report`, `blackboard.prelaunch_blackboard_synthesis_reason_text`, and ticket section parsing. Share section recognition only where there are real common consumers; preserve unrelated blackboard content, `## Dev`, `## Blockers`, and following sections. Do not change stored history just to alter composition.

### Acceptance and focused verification

- Short and large conforming archives are absent from rendered prompts while archived bytes stay available and unchanged on disk.
- Live notes before and after the archive, machine-readable Dev/Blockers state, and current requirements still compose as intended.
- Heading boundaries are explicit: exact top-level archives are omitted, similar names or prose/code examples are not silently discarded. Cover nested historical headings and duplicate exact sections defensively.
- Draft validation and activation retain the shipped synthesis exemption and preserve the archive; unrelated authoring scratch remains subject to the existing gate.
- `--prompt-report` measures the actual composed blackboard. Test composition and draft activation in `tests/test_compose.py`, `tests/test_blackboard.py`, and `tests/test_mark.py`.
- Update the owning convention `coga/contexts/dev/code/SKILL.md`, the Layer-6 contract in `coga/contexts/coga/architecture/SKILL.md`, the PR 755 `coga/codebase` gotcha, and any affected authoring instructions. Keep each packaged twin under `src/coga/resources/templates/coga/bootstrap/` synchronized and run packaging checks.

Related [blackboard-bloat remedy](document-the-remedy-for-a-bloated-blackboard-sibli.md) offers manual archival guidance; it does not change this automatic inclusion rule and is not an equivalent fix. Coordinate shared context edits without changing that ticket's workflow.

Tradeoff: automatic launch loses historical alternatives unless the live summary preserves relevant rationale or the agent follows the archive pointer. Out of scope: bulk archive migration, deleting history, changing review ownership, or relitigating the already-fixed synthesis gate.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
