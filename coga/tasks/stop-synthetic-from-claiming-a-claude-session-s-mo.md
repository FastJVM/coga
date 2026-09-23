---
title: Stop <synthetic> from claiming a Claude session's model
status: draft
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
---

## Description

In `usage._parse_claude_session`, model attribution is last-model-wins (`model = _first_str(message.get("model"), obj.get("model")) or model`), so a trailing assistant line with Claude Code's placeholder model `<synthetic>` overwrites the session's real model. Those records then show up as `<synthetic>` in `coga usage --by model` and in the weekly usage-report per-model split (13 of ~580 records in this repo, 5 of them real sessions with millions of tokens). Done: model attribution skips `"<synthetic>"` (a session with only synthetic lines keeps `<synthetic>`), with a test in `tests/test_usage.py` that shows a trailing synthetic line no longer claims the session. `python -m pytest` passes.

## Context

- Code: `usage._parse_claude_session`, in the `kind == "assistant"` branch where
  `model` is reassigned per line. Keep the token sums as they are; only the
  model choice changes. Codex (`usage._parse_codex_rollout`) is unaffected.
- `<synthetic>` is Claude Code's placeholder model on synthetic assistant
  messages; it appears only on Claude transcripts.
- Out of scope: re-attributing existing `<synthetic>` records already in
  `coga/log.md` (the log is append-only), and sessions that switch between
  real models mid-session (still last-model-wins; a separate problem).
- Split out of the canceled
  `define-the-api-equivalent-cost-proxy-and-price-tab` ticket, whose dollar
  pricing was dropped when `agent-usage-report` shipped as token-count only.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
