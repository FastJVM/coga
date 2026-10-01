---
title: Dedupe Claude transcript usage by message id
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

Claude session token counts in `coga/log.md` are inflated: about 1.6× across
this repo's transcripts, and up to ~1.9× for a single session.
`usage._parse_claude_session` adds `message.usage.*` from every `assistant`
line in the transcript. However, Claude Code writes one JSONL line per content
block (thinking, text, tool_use), and every line from the same API response
repeats that response's full `usage` with the same `message.id`. On
2026-10-01 a real transcript in this repo gave 947,189 tokens with the naive
sum and 504,005 after deduplicating by `message.id`, a 1.88× overcount. Both
`coga usage` and the weekly usage report (last week: 780.9M tokens, 97% of it
cache reads) show the inflated number, so the owner questioned the total.
Across all 69 Claude transcripts for this repo on 2026-10-01, the naive sum
was 564M tokens and the deduplicated sum was 346M.

Done means: a Claude session's tokens count each API message once, keyed by
`message.id`. A test in `tests/test_usage.py` uses a transcript fixture with
several content-block lines that share one `message.id` and identical usage,
and asserts that the usage is counted once. A line with no `message.id` still
counts on its own, as it does today. The record schema is unchanged, and the
owning topic says that usage is counted once per message.

## Context

- The fix is in `usage._parse_claude_session` in `src/coga/usage.py`, in the
  `if kind == "assistant":` accumulation loop. Keep a per-`message.id` usage
  and sum those values at the end, or skip any id already seen. Pick the
  approach that stays correct if a later line for the same id carries larger
  `output_tokens`. For streaming, the final line for an id has the complete
  count, so "last one per id wins" is safer than "first one wins". Confirm
  this against a real transcript under `~/.claude/projects/<cwd-hash>/` before
  choosing. A 2026-10-01 survey found 1,577 repeated lines for the same id
  across 69 transcripts, all carrying identical usage, so both rules agree
  today. Use last-wins anyway. Deduplicate *after* the window filter, so that
  when an id's lines straddle the window boundary, only the in-window lines
  count.
- Model attribution, the `<synthetic>` handling, the window filter
  (`_inside_window`), and the human/agent turn and text extraction in the same
  loop must not change behavior. Only the token sums change.
- **The Codex path is out of scope.** `_parse_codex_rollout` reads the
  rollout's `last_token_usage`/`total_token_usage` and already subtracts
  cached-read tokens from input. It is not affected.
- **Historical records are out of scope** (owner decision). Already-written
  `coga/log.md` lines stay as they are. Do not add a recount or migration.
- The owning contract is `coga/internals/activity-capture`
  (`docs/contexts/coga/internals/activity-capture/SKILL.md`, cited rather than
  attached because this ticket edits it). In its Claude matching/token-counting
  section, the current text says the parser "sums `message.usage.*` over
  `assistant` lines". Update that text to say each `message.id` is counted once.
  It has a byte-identical packaged twin at
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/activity-capture/SKILL.md`,
  which `tests/test_packaging.py` enforces, so edit both.
  `coga/usage` (`docs/contexts/coga/usage/SKILL.md` plus its twin) is the
  read-side topic. Its "a session's tokens go to its last model" caveat says
  `_parse_claude_session` "sums usage across every assistant line". Edit that
  line in both copies to say each message is counted once.
- Existing fixtures in `tests/test_usage.py` have no `message.id`, so the
  no-id fallback keeps them passing unchanged.
- A sibling ticket, `usage-report-name-the-human-split-per-agent-show-c`,
  reworks the weekly report text and should land after this fix.

<!-- coga:blackboard -->

## Dev
branch: fix/claude-usage-dedupe

## Implementation plan

Owner approved last-wins usage per message ID after window filtering; lines
without IDs count individually. Keep model and activity extraction unchanged.
Add regression coverage before the fix and update both owning topics and twins.

Read-only transcript check on 2026-10-01: 69 transcripts under
`~/.claude/projects/-home-n-Code-codex-coga/`, 1,580 repeated message-ID lines,
all with identical usage. Example: `00360668-53cc-4cd6-beb3-870fef24deea.jsonl`,
message `msg_011CembykCtB5QFoP8v5rvxT`. Last-wins also accommodates later
streaming lines with complete output counts; real samples do not distinguish
first from last today.

## Implement handoff

Implemented and pushed `403fca7e3` on `fix/claude-usage-dedupe`.
`src/coga/usage.py` / `_parse_claude_session` retains the last usage per
message ID after the existing window filter, then sums those values. Lines
without a nonempty string ID use their line index as an independent key.
Model attribution and activity extraction still visit every eligible line.
The record schema, Codex parser, and historical log records are unchanged.

Updated the activity-capture contract and usage caveat with byte-identical
packaged twins. Regression fixtures cover identical thinking/text/tool blocks,
later larger output counts, distinct messages, two ID-less lines, synthetic
model attribution, activity extraction, and duplicates across both window edges.

Verification:
- Before the fix: `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_usage.py -k 'counts_last_usage_per_message or deduplicates_after_window_filter' -q`
  failed all three new cases with inflated counts, as expected.
- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_usage.py tests/test_packaging.py -q`
  passed 48 tests before the full run and again after rebasing.
- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest`: 3,163 passed in 262.89s.
- `git diff --check`: clean.

Rebased onto `origin/main` at `9b6615195`; incoming changes were only Coga
ticket/log state. Pushed the branch, then returned to clean, fast-forwarded
`main` before this handoff. No PR opened. No unresolved implementation issues
or adjacent bugs found. Next step is peer review.
