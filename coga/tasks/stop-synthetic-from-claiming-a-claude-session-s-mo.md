---
title: Stop <synthetic> from claiming a Claude session's model
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
step: 2 (peer-review)
agent: claude
---

## Description

In `usage._parse_claude_session`, model attribution is last-model-wins (`model = _first_str(message.get("model"), obj.get("model")) or model`), so a trailing assistant line with Claude Code's placeholder model `<synthetic>` overwrites the session's real model. Those records then show up as `<synthetic>` in `coga usage --by model` and in the weekly usage-report per-model split (13 of ~580 records in this repo, 5 of them real sessions with millions of tokens). Done: model attribution skips `"<synthetic>"` (a session with only synthetic lines keeps `<synthetic>`), with a test in `tests/test_usage.py` that shows a trailing synthetic line no longer claims the session. `python -m pytest` passes.

## Context

- Code: `src/coga/usage.py` plus `usage._parse_claude_session`, in the
  `kind == "assistant"` branch where `model` is reassigned per line. Keep the
  token sums as they are; only the model choice changes. Codex parsing in the
  same module (`usage._parse_codex_rollout`) is unaffected.
- Cited rather than attached: `coga/internals/activity-capture`
  (`docs/contexts/coga/internals/activity-capture/SKILL.md`), "Provider matching
  — never by file mtime", owns Claude transcript attribution. Update this
  contract and its packaged twin with the fix.
- `<synthetic>` is Claude Code's placeholder model on synthetic assistant
  messages; it appears only on Claude transcripts.
- Out of scope: re-attributing existing `<synthetic>` records already in
  `coga/log.md` (the log is append-only), and sessions that switch between
  real models mid-session (still last-model-wins; a separate problem).
- Split out of the canceled
  `define-the-api-equivalent-cost-proxy-and-price-tab` ticket, whose dollar
  pricing was dropped when `agent-usage-report` shipped as token-count only.

<!-- coga:blackboard -->

## Dev

branch: fix/claude-synthetic-model

## Implementation — 2026-09-28

- Human approved the focused approach. Pushed commit `81f4fe80d` on the branch
  above, containing `origin/main` through `f7490d1bf`; returned the launch
  checkout to clean, fast-forwarded `main` before writing this handoff.
- `src/coga/usage.py` plus `usage._parse_claude_session` now uses
  `<synthetic>` only until a real model is seen. Later real models still win;
  all four token sums and Codex parsing retain their existing behavior.
- `tests/test_usage.py` plus
  `test_parse_claude_transcript_prefers_real_model` covers trailing synthetic,
  synthetic-only, leading synthetic, and real-model-switch transcripts, with
  token-total assertions that include every assistant line.
- Updated `coga/internals/activity-capture` and its byte-identical packaged
  twin. No task-layout, prompt, workflow, or validation behavior changed, so
  the example fixture needed no update.

## Verification

- Before the fix:
  `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_usage.py -k prefers_real_model`
  → 2 failed, 2 passed, 18 deselected. Both failures reproduced a trailing
  `<synthetic>` overwriting a real model.
- After the fix:
  `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_usage.py`
  → 22 passed.
- Full suite:
  `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest`
  → 3054 passed, both before and after the initial rebase (final full run:
  189.65 seconds, commit `1621cdac4`).
- Subsequent rebases incorporated only another ticket's lifecycle records.
  `git diff --exit-code 1621cdac4 HEAD -- src tests docs` confirmed the final
  code, tests, and documentation match the full-suite-tested commit.
  `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_usage.py tests/test_packaging.py`
  → 45 passed on the final commit.
- `git diff --check` passed; the activity-capture twin `cmp` passed.

## Handoff

Ready for peer review; no blockers or adjacent bugs found. No PR opened.
Historical log records and per-model token splitting remain outside this
ticket's scope.
