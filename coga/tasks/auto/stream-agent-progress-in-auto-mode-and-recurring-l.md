---
slug: auto/stream-agent-progress-in-auto-mode-and-recurring-l
title: Stream agent progress in auto-mode and recurring launches
status: in_progress
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/codebase
- coga/architecture
- coga/recurring
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Auto-mode launches (and anything scheduled via `relay recurring`) produce
**no console output for the duration of the agent run**, even though the
operator is often watching the terminal. The Dream prompt is the loudest
symptom — its body explicitly asks the agent to "Write short progress
updates to the console before and after each major phase" — but the
contract is silently violated for every `mode: auto` ticket.

## Root cause

`relay.toml` invokes the agent as `claude -p <prompt>` in auto mode
(`relay-os/relay.toml:11`). From `claude --help`:

> `-p, --print` — Print response and exit (useful for pipes).

Default `--output-format=text` collects the full response and prints it
once at the end. Any "console progress" the agent writes mid-run is
buffered inside the agent process and never reaches the terminal until
the run completes. `codex exec` (the other configured auto agent) has
the same shape.

`relay launch` inherits stdio when spawning (`src/relay/commands/launch.py:266`),
so this is not a relay-side capture issue — it's that the agent itself
emits nothing until exit.

Secondary, smaller issue: relay's own `typer.echo` lines aren't flushed,
so even the "Launch: composing prompt / command / agent exited" banner
disappears when stdout is piped or redirected (CI, log files).

## Why it matters

- Dream is unwatchable. Operator stares at a blank terminal for the
  full run; if it dies mid-skill they can't tell where it died from the
  console alone.
- Recurring tasks created via `relay recurring check` inherit the
  same auto-mode launch path and the same silence.
- Violates the principle that every artifact be legible without
  running the system — here the live run is illegible.

## Approaches (pick one, or layer)

1. **Stream the agent's structured output.** Change `agents.claude.auto`
   to `-p --output-format=stream-json --include-partial-messages --verbose`
   and grow a small relay-side consumer that pretty-prints turn / tool
   events to the terminal. Highest fidelity, biggest change. Need
   equivalent for `codex exec`.
2. **Pass through stderr-only progress.** If the agent CLIs route any
   "thinking" or tool-call lines to stderr in `-p` mode, that's enough
   life signal to ship. Cheap if true; need to verify.
3. **In-prompt Slack pings.** Have Dream (and any other watchable
   recurring task) call `relay slack --task <id> --message "<phase>"`
   between phases. No relay change; trades terminal noise for Slack
   noise.
4. **Document `tail -F blackboard.md` as the live view.** Only works if
   the agent actually writes to the blackboard between phases. Cheap
   band-aid, doesn't solve CI.
5. **Flush typer.echo / `PYTHONUNBUFFERED=1`.** Orthogonal but trivial;
   fixes the launch banner disappearing under pipes. Worth shipping
   independently.

Recommendation: ship (5) immediately as a freebie, then pick (1) for
the real fix. (3) is a viable interim if (1) is too far out.

## Out of scope

- Interactive-mode launches (already streaming, by definition of TTY).
- Script-mode launches (no agent; their own logging story).
- Changing the Dream skill list / behavior — this ticket is purely
  about making auto-mode runs watchable.

## Context

Discovered while diagnosing why `relay dream` "blocks" with no output.
The previous `relay dream` run left a `dream` ticket stuck at
`in_progress` with an empty blackboard; no live process exists for it.
See chat history 2026-05-17.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap session notes (2026-06-10)

- Nick wants this ticket to live under `relay-os/tasks/auto/`, but task
  discovery (`list_tasks()` in `src/relay/tasks.py`) only sees direct
  children of `tasks/`, so moving it now would orphan it from the CLI.
- Decision: drafted a separate ticket,
  `support-task-subdirectories-in-task-discovery`, which extends
  discovery to one-level subdirs and performs the `git mv` of this
  ticket into `tasks/auto/` in the same PR. Nick will execute that
  ticket next; this one stays at top level until it ships.
- Slug-prefix grouping (e.g. `auto-…` names) was explicitly rejected.
- This ticket's own bootstrap interview (workflow, contexts, scope) is
  not finished yet — still a bare draft with only the description from
  create time. Open question carried over: is auto-mode merely silent
  (stream stdout) or actually broken (fix launches)? Nick said "right
  now auto is not working" — clarify before filling the ticket.
