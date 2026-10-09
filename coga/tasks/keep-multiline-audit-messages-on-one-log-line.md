---
title: Keep multiline audit messages on one log line
status: blocked
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

## Peer review

Independent `codex review --base main` **returned** on 2026-10-08 with two
P2 must-fix findings. Reviewed head `17808f2d251e2d33e8daf20fbcf9f48b687d4ea9`
against base `57ad2b6c67831f4170112f4349aec7b270bea2a9`.
The separate Codex reviewer did not implement the change; Claude remains the
implementing identity. The review process exited 0, which is not a clean
verdict: both findings remain open.

1. `src/coga/usage.py:377-383`: decode-first/raw-fallback silently changes
   valid legacy JSON. An outcome containing literal `C:\temp\file` loads
   with a tab and form-feed; decoded JSON still parses, so fallback never
   runs. The implement handoff's disclosed limitation is not owner approval
   to corrupt legacy text. Add a regression without an actual newline.
2. `scripts/human_minutes.py::parse_log`: raw `json.loads(message)` drops new
   encoded records containing quotes (e.g. `Said "done"`). The reviewer
   reproduced one loaded record before encoding and zero after it. This
   consumer needs the same format-aware parsing and regression coverage.

**Design decision needed:** authorize an explicit version marker outside
message text, proposed grammar
`YYYY-MM-DD HH:MM v1 [<ref>] [<actor>] <escaped-message>` for new events.
Legacy headers remain unmarked and are read without unescaping; historical
bytes stay untouched. Backslash/LF/CR encoding itself stays as decided.
Placing the marker before the ref makes it distinguishable from every message
written by the old grammar. Update all anchored readers (including the metrics
script), the owning topic, twins, and tests together after approval. This is
a proposal, not an implemented or approved contract. A parse-success heuristic
cannot distinguish both formats reliably. Per the current step's explicit
instruction to escalate findings implying a design rethink, block instead of
bumping. The second fix depends on the same discrimination policy.

Verification: `PYTHONPATH=$PWD/src .venv/bin/python -m pytest` returned
**3538 passed in 298.97s** on Python 3.12.12, including packaging tests.
Ambient `python -m pytest` failed collection (33 errors, missing `tomlkit`);
the complete rerun used the repository environment. The review tool also ran
`.venv/bin/python -m pytest tests/test_logfile.py tests/test_usage.py tests/test_recurring.py -q`:
**528 passed in 92.04s**. `git diff --check` passed. Python 3.11 was not run.
A PTY check of the actual `coga show` renderer at 80/120 columns confirmed
escaped new messages remain legible, old continuations accompany their task,
and peer events/continuations are excluded. Existing Rich bracket-tag handling
predates this change. No raw terminal loop, pager, or Slack surface changed.

Start check was clean `main`; fetched and fast-forwarded. Feature branch was
unconditionally rebased on fetched main before review and force-with-lease
pushed as `17808f2d2`. No code fixes were made. After checks, returned to clean
`main` at `e697cce23` (a concurrent README-only commit). A temporary unrelated
README edit was preserved and subsequently landed independently; none of it
was committed to this branch. Final review/test receipts retain their actual
head/base rather than claiming to cover the later README commit.

Coordination: inspected the two related draft tickets.
`fix-coga-git-sync-failures-that-leave-main-diverge` still owns failure recovery;
`prevent-duplicate-session-usage-records-from-infla` still owns deduplication.
Neither is a prerequisite for this format decision. `github_preflight.py`
classifies paths and does not parse log messages, so its omission is justified.
The additional metrics consumer omission is not justified and must be fixed.

## PR

```yaml
title: Keep multiline audit messages on one log line
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5); see implement handoff.
head: 17808f2d251e2d33e8daf20fbcf9f48b687d4ea9
base: 57ad2b6c67831f4170112f4349aec7b270bea2a9
depth: deep
rationale: Independent Codex review returned with two unresolved P2 findings. A format-discrimination
  decision is required before fixing legacy text corruption and the additional metrics reader; do not
  publish yet.
implementation: append_log escapes backslash, LF and CR; readers split on LF, decode messages, and tolerate
  legacy continuation lines; retraction matches the ref field and drops continuations of removed events.
deviations: Review found that decode-first parsing corrupts some valid legacy JSON and scripts/human_minutes.py
  was omitted from the encoding migration. Both remain unresolved pending the header-format decision.
limitations: No encoding discriminator currently exists. Legacy literal backslashes can become JSON control
  escapes even when decoded JSON parses successfully. scripts/human_minutes.py can silently drop newly
  encoded usage records containing quotes. Other control characters pass through by decision. Git failure
  recovery and usage deduplication remain separate tickets.
files:
  docs/contexts/coga/internals/spool-merge/SKILL.md: Own the one-line-per-event rule and legacy-line policy.
  docs/contexts/coga/usage/SKILL.md: Note that usage records are decoded with raw fallback.
  src/coga/logfile.py: Central encoding/decoding, LF-only splitting, legacy-tolerant readers, field-matched
    retraction.
  src/coga/recurring_runner.py: Control-ledger parsers decode messages and split on LF only.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/spool-merge/SKILL.md: Packaged twin
    of the spool-merge topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md: Packaged twin of the usage
    topic.
  src/coga/usage.py: Decode-first usage record parsing with raw fallback for legacy lines.
  tests/test_logfile.py: Regression cases for LF/CRLF/CR/backslash encoding, legacy continuations, and
    retraction.
  tests/test_recurring.py: Control ledger reads encoded and legacy multiline events without faking a period.
  tests/test_usage.py: Encoded and legacy backslash usage records round-trip.
review:
  reviewer: codex
  kind: independent
  status: failed
  head: 17808f2d251e2d33e8daf20fbcf9f48b687d4ea9
  base: 57ad2b6c67831f4170112f4349aec7b270bea2a9
  detail: 'codex review --base main returned (exit 0, findings present): P2 legacy JSON corruption at
    src/coga/usage.py:377-383; P2 scripts/human_minutes.py::parse_log drops newly encoded records containing
    quotes. No fixes applied because choosing an unambiguous header discriminator requires a design decision.
    Implementation remains by Claude; review ran in a separate Codex tool session.'
checks:
- command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest
  status: passed
  head: 17808f2d251e2d33e8daf20fbcf9f48b687d4ea9
  base: 57ad2b6c67831f4170112f4349aec7b270bea2a9
  detail: 3538 passed in 298.97s on Python 3.12.12, including packaging twins. No Python 3.11 verification
    performed. The initial ambient python -m pytest attempt failed collection with 33 errors because tomlkit
    was unavailable; this complete run used the correct environment.
- command: .venv/bin/python -m pytest tests/test_logfile.py tests/test_usage.py tests/test_recurring.py
    -q
  status: passed
  head: 17808f2d251e2d33e8daf20fbcf9f48b687d4ea9
  base: 57ad2b6c67831f4170112f4349aec7b270bea2a9
  detail: 528 passed in 92.04s in the independent review tool session; does not cover either reported
    regression.
- command: git diff --check
  status: passed
  head: 17808f2d251e2d33e8daf20fbcf9f48b687d4ea9
  base: 57ad2b6c67831f4170112f4349aec7b270bea2a9
  detail: No whitespace errors.
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=$PWD/src .venv/bin/python - (temporary audit fixture invoking
    coga.views.render_show in a PTY)
  status: passed
  head: 17808f2d251e2d33e8daf20fbcf9f48b687d4ea9
  base: 57ad2b6c67831f4170112f4349aec7b270bea2a9
  detail: Inspected Rich Console output at widths 80 and 120. New LF/CRLF and literal backslashes remained
    escaped and legible; legacy continuation stayed with alpha; beta event/continuation were excluded.
    Existing Rich markup handling consumes bracketed tags; that predates this diff. No raw-terminal loop
    or Slack rendering changed.
```

---

## Blockers

- [ ] [2026-10-08 21:55] [agent:codex] id=20261008T215527 Approve a versioned audit header for new events: YYYY-MM-DD HH:MM v1 [ref] [actor] <escaped-message>, with unmarked legacy messages read raw and historical bytes unchanged, or specify another unambiguous discriminator. Returned Codex review found legacy JSON backslash corruption and dropped records in scripts/human_minutes.py; both need format-aware readers. Full suite: 3538 passed. Findings, proposal, and exact receipts are on the blackboard; branch 17808f2d2 is pushed.
