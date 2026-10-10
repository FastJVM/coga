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
step: 3 (open-pr)
agent: claude
launch_generation: fd38580c-e547-4b51-8b98-e6ae576aaa53
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

Implemented: new headers include `v1` before `[ref]`; only marked messages
are decoded, while legacy messages stay raw. `append_log` escapes `\` → `\\`, LF → `\n`, CR → `\r`; a shared
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

## Peer review

Completed 2026-10-09. Final head `55e6a6d75fbc403f68c93d765cb75427e0d551a0` against base `c2f089bb44b713e99dc3669c8e93504346885c78`.
`codex review --base main` **returned** on this final committed revision with
no actionable findings. The review ran as a separate Codex tool process;
recorded conservatively as self-review because Codex implemented the fixes.
Claude remains the original implementing identity; Codex is a co-author.

Both earlier P2 findings are fixed with regressions: unmarked legacy JSON is
parsed raw (including `C:\temp\file` without real newlines), and
`scripts/human_minutes.py` decodes v1 quoted usage records correctly.
The owner's approved header is implemented across logfile, usage, recurring
ledger/diff parsing, the metrics script, watchdog pause detection, and telemetry.
Historical audit bytes are untouched. The initial complete suite found a missed
telemetry reader and an init exact-byte expectation (3541 passed, 2 failed in
290.08s); both were fixed. Telemetry also handles decoded multiline FYIs.

Final verification: `PYTHONPATH=$PWD/src .venv/bin/python -m pytest` →
**3566 passed in 321.67s (0:05:21)**, Python 3.12.12. Packaging twins are included.
`git diff --check main...HEAD` passed. Python 3.11 was not run.
Earlier focused checks returned 299 passed in 14.20s; the final full run
supersedes them. A read-only comparison found all 1,116 real legacy usage
records equal to raw JSON parsing. The first review in this session returned
no actionable findings but overlapped fixes; it is superseded by the final
review receipt above. Initial sandboxed review could not initialize its
app-server on a read-only filesystem; the required review returned after an
approved unsandboxed retry.

PTY verification of the actual `coga show` renderer at 80/120 columns on the
final head: v1 marker and escaped diagnostics remain legible; legacy
continuations stay with alpha; beta events and continuations are excluded.
Existing Rich bracket-tag consumption predates this change. No pager, raw
terminal loop, or Slack rendering changed.

Started on clean main, fetched/fast-forwarded; unconditionally fetched and
rebased the feature branch before final verification. Branch committed and
force-with-lease pushed; returned to clean main before this handoff.
`github_preflight.py` only classifies paths and requires no message-parser
change. Git failure recovery and usage deduplication remain with their named
tickets; neither is a prerequisite for this approved format change.

## PR

```yaml
title: Keep multiline audit messages on one log line
author: claude+codex
author_evidence: Claude implemented the original change; Codex implemented the owner-approved v1 discriminator
  and peer-review fixes in this session.
head: 55e6a6d75fbc403f68c93d765cb75427e0d551a0
base: c2f089bb44b713e99dc3669c8e93504346885c78
depth: deep
rationale: The versioned audit grammar affects usage, recurring admission, watchdog provenance, telemetry,
  and rollback. Final tests and Codex review passed, but inspect this cross-consumer format migration.
  Review is conservatively recorded as self-review because Codex also implemented fixes.
implementation: append_log centrally escapes backslash, LF, and CR and writes v1 before the ref. Readers
  decode only v1 messages and preserve unmarked legacy messages. Retraction matches the ref field and
  preserves peer events. All discovered anchored readers accept both formats.
deviations: Owner approved the v1 discriminator on 2026-10-08 after the first review found legacy JSON
  corruption and a missing metrics consumer. Also migrated watchdog and telemetry readers discovered during
  verification; updated the init exact-byte expectation.
limitations: Historical log bytes are unchanged; malformed historical events need not retract cleanly.
  Tabs and ANSI pass through by design. Python 3.11 was not tested (verification used Python 3.12.12).
  Older Coga readers do not understand v1 headers. Git failure recovery and usage deduplication remain
  separate tickets.
files:
  docs/contexts/coga/internals/spool-merge/SKILL.md: Own the v1 line grammar, central escaping, raw legacy
    messages, and continuation/retraction policy.
  docs/contexts/coga/telemetry/SKILL.md: Link the shared audit decoding contract and document multiline
    FYI suffixes.
  docs/contexts/coga/usage/SKILL.md: Describe version-aware JSON parsing without a parse-success heuristic.
  scripts/human_minutes.py: Read v1 and legacy envelopes, decode only v1 messages, and split on LF.
  src/coga/logfile.py: Encode one physical event line with a v1 header; preserve legacy text; update activity/history
    readers and field-matched retraction.
  src/coga/recurring.py: Accept v1 headers when reconstructing watchdog pause provenance.
  src/coga/recurring_runner.py: Read both envelope versions in control-ledger scans and incremental diff
    parsing.
  src/coga/usage.py: Decode only marked usage records so valid legacy JSON stays exact.
  src/coga_edge/phone_home.py: Count movement from both envelope versions and handle decoded multiline
    FYIs.
  tests/test_human_minutes_script.py: Regress dropped quoted usage records and legacy backslash corruption.
  tests/test_init.py: Expect the version marker in the exact onboarding audit line.
  tests/test_logfile.py: Cover LF/CRLF/CR/backslashes, exact append bytes, both reader versions, continuations,
    and whole-event retraction.
  tests/test_recurring.py: Cover versioned ledger messages and both watchdog envelope formats.
  tests/test_telemetry.py: Exercise movement grammar in both formats and versioned multiline FYIs.
  tests/test_usage.py: Regress legacy paths with literal backslashes and encoded quoted/newline outcomes.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/spool-merge/SKILL.md: Byte-identical
    packaged twin of coga/internals/spool-merge.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/telemetry/SKILL.md: Byte-identical packaged
    twin of coga/telemetry.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md: Byte-identical packaged twin
    of coga/usage.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 55e6a6d75fbc403f68c93d765cb75427e0d551a0
  base: c2f089bb44b713e99dc3669c8e93504346885c78
  detail: 'codex review --base main returned (exit 0) on the final committed revision with no actionable
    findings. Reviewer checks: 299 log/usage/telemetry/metrics/init tests, 480 recurring tests, and 467
    packaging/mark/launch/git tests passed. It ran in a separate review tool process; independence is
    not claimed for the Codex-authored fixes.'
checks:
- command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest
  status: passed
  head: 55e6a6d75fbc403f68c93d765cb75427e0d551a0
  base: c2f089bb44b713e99dc3669c8e93504346885c78
  detail: 3566 passed in 321.67s (0:05:21) on Python 3.12.12, including packaging twin checks.
- command: git diff --check main...HEAD
  status: passed
  head: 55e6a6d75fbc403f68c93d765cb75427e0d551a0
  base: c2f089bb44b713e99dc3669c8e93504346885c78
  detail: No whitespace errors.
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=$PWD/src .venv/bin/python /tmp/audit_render.py
  status: passed
  head: 55e6a6d75fbc403f68c93d765cb75427e0d551a0
  base: c2f089bb44b713e99dc3669c8e93504346885c78
  detail: Temporary isolated fixture ran coga.views.render_show in a PTY at widths 80 and 120. v1 diagnostics
    and escaped CR/LF/backslashes were legible; legacy alpha continuation stayed attached; beta event/continuation
    were excluded. Existing Rich tag consumption predates this change.
```

---

## Blockers

- [x] [2026-10-08 21:55] [agent:codex] id=20261008T215527 Approve a versioned audit header for new events: YYYY-MM-DD HH:MM v1 [ref] [actor] <escaped-message>, with unmarked legacy messages read raw and historical bytes unchanged, or specify another unambiguous discriminator. Returned Codex review found legacy JSON backslash corruption and dropped records in scripts/human_minutes.py; both need format-aware readers. Full suite: 3538 passed. Findings, proposal, and exact receipts are on the blackboard; branch 17808f2d2 is pushed.
  resolved: [2026-10-08 22:38] [human:nicktoper] Owner approved the versioned audit header: new events are written as 'YYYY-MM-DD HH:MM v1 [ref] [actor] <escaped-message>'; only v1-marked messages are unescaped, unmarked legacy lines are read raw (legacy continuation tolerance stays), historical bytes unchanged. Update every anchored reader together (logfile, usage, recurring_runner, scripts/human_minutes.py), the spool-merge topic and twins, and tests; fix both Codex P2 findings with regressions.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `keep-multiline-audit-messages-on-one-log-line`
Recorded: 2026-10-10T01:16:51+00:00

    [open-pr] origin/main advanced only through non-overlapping Coga task/log state; branch is safe to publish
    PR presentation: use one complete fenced yaml mapping under ## PR.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `keep-multiline-audit-messages-on-one-log-line`
Recorded: 2026-10-10T01:16:58+00:00

    [open-pr] origin/main advanced only through non-overlapping Coga task/log state; branch is safe to publish
    PR presentation: use one complete fenced yaml mapping under ## PR.
