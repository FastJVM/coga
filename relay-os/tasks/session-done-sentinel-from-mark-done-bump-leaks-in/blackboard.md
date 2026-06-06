The blackboard is a notepad to be written to often as the human and agent works through a task.

## RESOLVED — superseded by `session-done-sentinel-leaks-and-agent-stops-respon`

2026-06-05 (claude, interactive with nick).

This draft is fixed by the work on
`session-done-sentinel-leaks-and-agent-stops-respon`:

- branch `fix/session-done-sentinel-and-mute`, commit `cefd10e`.

Root cause is shared. `emit_done_marker` (`src/relay/repl_supervisor.py`)
unconditionally `print(DONE_MARKER)`-ed to stdout on every `mark done` /
`bump` / `panic`. That stray print is exactly the cross-talk this ticket
describes: when a supervised TUI parent shells out to settle a **child**
task, the printed marker gets captured and rendered back to the parent's PTY,
where the supervisor's **unscoped** byte-match reads it and tears the parent
down — even though the file channel was already session-scoped and would not
have matched.

The fix removes the success-path print entirely: the session-done signal now
travels **only** over the session-scoped sentinel file
(`$RELAY_DONE_SENTINEL`, content == the resolved task path). The supervisor
only tears down on a file whose content names *its* session, so a parent
marking a child done no longer self-teardowns. The marker is printed solely
as an OSError last resort.

This is the first option in this ticket's "Expected" list (scope the signal
to the session/task it belongs to) — already half-true via the file content,
now fully true because the unscoped stdout channel is gone on the success
path.

**No separate code change needed.** This draft can be deleted (`relay delete
session-done-sentinel-from-mark-done-bump-leaks-in`, recoverable via `git
restore`) once the fix branch lands — left to nick since it's his draft.
