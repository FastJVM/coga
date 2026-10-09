---
title: Keep multiline audit messages on one log line
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
launch_generation: 4d6e9d37-8534-44fc-9bd2-9b85ab5dfd41
---

## Description

Ensure logfile.append_log writes exactly one physical, parseable audit line per event even when a message contains LF, CRLF, bare CR, or multiline Git stderr. Keep diagnostic content legible and preserve the exact-byte return contract.

Decided encoding: `append_log` encodes centrally (callers do not sanitize). It escapes existing backslashes first, then writes line breaks as the literal two-character text `\n` / `\r`, so the encoding is unambiguous and decodable and a literal backslash in the message is never confused with a real newline. Other control characters (tabs, ANSI) are out of scope and pass through unchanged.

Decided legacy policy: do not rewrite the append-only log. Existing malformed lines stay; log readers treat an untagged line that does not start with a timestamp as a continuation of the preceding event (or otherwise tolerate it without misparsing or crashing). The retraction guarantee applies only to events written after this change — already-malformed historical events need not retract cleanly.

Done when regression cases cover multiline sync errors (LF, CRLF, bare CR, and literal backslash sequences), the task-log readers and the other log parsers listed under Context reading both new-encoded and legacy malformed lines, and retract_log_lines removing the whole new event without orphan continuations or deleting another task's event. The one-line-per-event rule and the legacy-line policy are documented in `coga/internals/spool-merge` in the same PR. This ticket fixes event encoding, not the underlying Git failures.

## Context

### Report relayed by the owner — 2026-10-07

Another AI counted 585 out-of-format log lines and reports that multiline entries still occur in October. Its example is `sync failed: {exc}` carrying complete Git stderr (a producer is in `mark.py`). Reproduced locally at authoring (2026-10-08): 588 of 7,967 lines in `coga/log.md` did not start with a timestamp.

Intake source inspection confirms `logfile.append_log` interpolates message bytes directly despite promising one line per event. `logfile.retract_log_lines` filters physical lines by the `[ref]` task tag, so untagged continuation lines survive retraction.

### Log parsers that must tolerate both encodings

Besides logfile.py's own readers (`task_log_lines`, the activity maps, and both `iter_log_messages` functions):

- `usage._LOG_LINE_RE` and the usage-record reader in `usage.py`.
- `recurring_runner._CONTROL_LOG_ENTRY_RE` and the serviced-period ledger scan in `recurring_runner.py`, which reads the union-merged log.
- `github_preflight.py`, which reads the repo-global `log.md` alongside the branch sweep.

### Documentation owner

No topic currently owns the log line grammar; it is only spelled out in the logfile.py docstring and in `coga/usage` (`docs/contexts/coga/usage/SKILL.md`, which has a packaged twin — keep the twins byte-identical if you touch it). Put the one-line-per-event rule and the legacy policy in `coga/internals/spool-merge` (`docs/contexts/coga/internals/spool-merge/SKILL.md`), which owns the append-only invariants, and check whether it has a packaged twin.

### Cited topics

Read coga/internals/spool-merge (`docs/contexts/coga/internals/spool-merge/SKILL.md`) for union/append-only merging, and the strict-rollback paragraph of coga/internals/state-publication (`docs/contexts/coga/internals/state-publication/SKILL.md`). Both are cited, not attached. Inspect them before changing the encoding. Start with logfile.py and its tests.

### Coordination

Coordinate with fix-coga-git-sync-failures-that-leave-main-diverge, which owns the failures themselves, and prevent-duplicate-session-usage-records-from-infla, which owns usage deduplication.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: `one-line-audit-events`

Plan: `append_log` escapes `\` → `\\`, LF → `\n`, CR → `\r`; a shared
`logfile.decode_log_message` inverts it. Readers split physical lines on LF
only (not `str.splitlines`, which also breaks on VT/FF/U+2028…), decode
messages, and skip legacy continuation lines (`task_log_lines` keeps them
attached to their event for `coga show`). `retract_log_lines` matches the
parsed `[ref]` tag (not a substring) and drops continuation lines that follow
a retracted event.

## Implement handoff

Commit `32b0184` on `one-line-audit-events` (pushed; no PR yet).

- `logfile.append_log` encodes centrally via `encode_log_message`
  (`\` → `\\` first, then LF → `\n`, CR → `\r`); the return value is still
  the exact appended bytes. `decode_log_message` inverts it and leaves other
  backslash sequences alone. `log_lines` splits on LF only.
- Readers: `iter_log_messages` and `iter_log_messages_reverse` yield decoded
  messages. The activity maps and `task_log_lines` skip legacy continuation
  lines, and `task_log_lines` keeps them with the event they follow (for
  `coga show`; lines stay encoded). `usage.load_records` decodes first and
  falls back to the raw text. Against the real log, 7 of 1,105 legacy usage
  lines differ only in free-text `request`/`outcome` under decoding, and all
  1,105 still load. `recurring_runner._read_control_ledger` and its diff
  path decode and use `log_lines`.
- `retract_log_lines` now matches the parsed `[ref]` field, not a substring.
  The old code deleted any peer line that mentioned `[ref]` in its message.
  It also drops continuation lines that follow a removed event.
- `github_preflight.py` only compares path names (`is_coga_state_path`) and
  never parses log content, so it needed no change.
- Docs: added "One event per log line" (rule + legacy policy) to
  `coga/internals/spool-merge`, plus a decode note in `coga/usage`. Both
  packaged bootstrap twins were updated to stay byte-identical.
- Left unchanged: `recurring._watchdog_pauses` reads with universal newlines
  and an anchored `paused|created` regex, so it already tolerates both forms.
  `task_ref` and `actor` are not encoded; they are slugs or role names. Not
  addressed: the Git failures themselves
  (fix-coga-git-sync-failures-that-leave-main-diverge).

## PR

```yaml
title: Keep multiline audit messages on one log line
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5); see implement handoff.
head: 32b0184791837284bebe7521cdee0d595ea455f2
base: cd7d1b21e1ddfe0d5c65a37aac1d1cdd0ad54efa
depth: deep
rationale: Changes the on-disk audit-log encoding and every log reader, including the recurring serviced-period ledger and retraction; no code review has run yet.
implementation: append_log escapes backslash, LF and CR; readers split on LF, decode messages, and tolerate legacy continuation lines; retraction matches the ref field and drops continuations of removed events.
deviations: None from the decided encoding and legacy policy.
limitations: Decoding can alter free text of legacy lines holding literal \\, \n or \r (7 of 1,105 usage records, request/outcome only; usage reader falls back to raw when decoded JSON fails). task_ref/actor are not encoded. Other control characters pass through by decision.
files:
  docs/contexts/coga/internals/spool-merge/SKILL.md: Own the one-line-per-event rule and legacy-line policy.
  docs/contexts/coga/usage/SKILL.md: Note that usage records are decoded with raw fallback.
  src/coga/logfile.py: Central encoding/decoding, LF-only splitting, legacy-tolerant readers, field-matched retraction.
  src/coga/recurring_runner.py: Control-ledger parsers decode messages and split on LF only.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/spool-merge/SKILL.md: Packaged twin of the spool-merge topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md: Packaged twin of the usage topic.
  src/coga/usage.py: Decode-first usage record parsing with raw fallback for legacy lines.
  tests/test_logfile.py: Regression cases for LF/CRLF/CR/backslash encoding, legacy continuations, and retraction.
  tests/test_recurring.py: Control ledger reads encoded and legacy multiline events without faking a period.
  tests/test_usage.py: Encoded and legacy backslash usage records round-trip.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Implement step; code review belongs to the later workflow step.
checks:
  - command: python -m pytest
    status: passed
    head: 32b0184791837284bebe7521cdee0d595ea455f2
    base: cd7d1b21e1ddfe0d5c65a37aac1d1cdd0ad54efa
    detail: 3538 passed (run on the working tree, which is identical to the committed tree; the rebase was a no-op).
  - command: python -m pytest tests/test_packaging.py
    status: passed
    head: 32b0184791837284bebe7521cdee0d595ea455f2
    base: cd7d1b21e1ddfe0d5c65a37aac1d1cdd0ad54efa
    detail: 23 passed; twins byte-identical.
```
