The blackboard is a notepad to be written to often as the human and agent works through a task.

## Run notes — debug dev-update (2026-06-05)

State read from parent `relay-os/recurring/relay-dev-update/blackboard.md`:
- last_commit: 29dc3c1 (2026-05-30 "Make relay status read-only #254")
- origin/main HEAD: a3f250f (this debug ticket's in_progress commit, 2026-06-05)

Range 29dc3c1..origin/main = **158 commits**, but ~32 are real merged PRs;
the rest is ticket-lifecycle churn. This is a **6-day catch-up** — the daily
digest's high-water mark hasn't moved since 5/30 (the 5/31 run recorded #256
but did not advance last_commit). New SHA to record: a3f250f.

### Drafted digest (themed)

Relay dev digest — May 30 → Jun 5 (6-day catch-up)

• Git-backed durability: ticket state now auto-commits & pushes, syncs
  cross-branch and on panic/authoring, with atomic writes for log +
  done-markers (#262–#264, #273, #267); failed control-branch pushes are
  non-fatal (#265).
• Recurring runs hardened: recover runs orphaned when the supervisor dies /
  laptop sleeps (#287), idle-timeout backstops + skip unattended interactive
  templates (#277/#278), preserve template body at scaffold (#283), `--all`
  debug launch flag (#276).
• Dream/Retro: direct-delete done tickets carrying no durable knowledge
  (#288, #285).
• TUI/REPL teardown fixes: sanitize terminal + fix supervised bump hint
  (#274), restore keyboard-input protocols on signal-teardown (#279).
• Launch safety: fail loud on missing context/skill (#269); open-pr step
  writes PR link into ticket.md (#270); stop overloading relay slack (#275).
• New capabilities + docs: reusable relay/gmail search+attachments (#258),
  create-google-doc workflow (#272), positioning rewrite (#260), spool
  producer/consumer pattern + context/codebase doc updates (#284, #280–#282,
  #286).
• Packaging: wheel build/packaging regressions fixed (#259, #266).

### Open decision
Debug run over a 6-day range — confirm with human whether to actually post to
the team Slack channel or just record state.
