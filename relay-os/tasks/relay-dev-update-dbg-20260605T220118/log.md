2026-06-05 22:01 [system] created (mode=interactive, status=active)
2026-06-05 22:01 [human:nick] started (active → in_progress) via relay launch
2026-06-05 22:01 [human:nick] launched in interactive mode (assignee=claude, agent=claude)
2026-06-05 22:06 [agent:claude] slack: Relay dev digest — May 30 → Jun 5 (6-day catch-up)

• Git-backed durability: ticket state now auto-commits & pushes, syncs cross-branch and on panic/authoring, with atomic writes for log + done-markers (#262–#264, #273, #267); failed control-branch pushes are non-fatal (#265).
• Recurring runs hardened: recover runs orphaned when the supervisor dies / laptop sleeps (#287), idle-timeout backstops + skip unattended interactive templates (#277/#278), preserve template body at scaffold (#283), --all debug launch flag (#276).
• Dream/Retro: direct-delete done tickets carrying no durable knowledge (#288, #285).
• TUI/REPL teardown fixes: sanitize terminal + fix supervised bump hint (#274), restore keyboard-input protocols on signal-teardown (#279).
• Launch safety: fail loud on missing context/skill (#269); open-pr step writes PR link into ticket.md (#270); stop overloading relay slack (#275).
• New capabilities + docs: reusable relay/gmail (#258), create-google-doc workflow (#272), positioning rewrite (#260), spool producer/consumer pattern + doc updates (#284, #280–#282, #286).
• Packaging: wheel build/packaging regressions fixed (#259, #266).
2026-06-05 22:06 [human:nick] task done
