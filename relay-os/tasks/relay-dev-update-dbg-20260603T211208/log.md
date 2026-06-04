2026-06-03 21:12 [system] created (mode=interactive, status=active)
2026-06-03 21:31 [human:nick] started (active → in_progress) via relay launch
2026-06-03 21:31 [human:nick] launched in interactive mode (assignee=claude, agent=claude)
2026-06-03 21:32 [agent:claude] slack: Relay dev pulse — 3 PRs since last update, all hardening recurring-launch robustness:
• Unattended recurring sweeps no longer hang (#277, #278): a mode:interactive template reached without a TTY is now skipped + reported as a scan error instead of spawning a driverless REPL that blocked every later due task. Added an idle-timeout backstop, now armed on the bare sweep too and threaded as an explicit --idle-timeout param.
• Keyboard no longer goes dead after an interactive launch (#279): REPL signal-teardown restores the kitty keyboard protocol + xterm modifyOtherKeys on SIGTERM/SIGKILL, not just mouse/alt-screen.
2026-06-03 21:32 [human:nick] task done
