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
step: 1 (implement)
agent: claude
launch_generation: ecf7b539-6b30-44f2-a2a1-4c5228e898ad
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
