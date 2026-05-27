---
title: 'launch : autoquit when done or relaunch depending on mode'
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
  - name: self-qa
    skills:
    - code/self-qa
  - name: pr
    skills:
    - code/open-pr
  - name: review
    skills: []
    assignee: owner
---

## Description

Make a supervised interactive agent session actually exit when its step
is done. Today the REPL supervisor in `src/relay/repl_supervisor.py`
already watches the PTY for `DONE_MARKER`
(`<<<RELAY_SESSION_DONE_a9f3c41e>>>`) and SIGTERMs the child when it
sees it — but nothing in the system emits that marker, so the agent's
REPL just sits idle after `relay bump`. The base prompt tells the agent
to "exit cleanly" after bumping without saying how, and a Claude
Code / Codex REPL has no native way to exit itself.

Scope of this ticket: make `relay bump`, `relay mark done`, and
`relay panic` print the `DONE_MARKER` as their final stdout line. The
agent then just runs the CLI command as it already does; the supervisor
sees the marker and tears down the REPL. No agent-side knowledge of the
marker string is required.

Also in scope: **escape the kill switch in injected text.** Any prompt
shipped into the REPL by `relay launch` (base prompt, mode prompt,
ticket body, blackboard, context layers, skill bodies, …) that contains
the literal `DONE_MARKER` byte sequence will be echoed by the REPL onto
the PTY, matched by the supervisor, and SIGTERM the child before it
does any work. This ticket itself triggered the bug on first launch
because it quotes the marker in its description. The composer (or
whatever final stage hands text to the REPL) must munge any verbatim
occurrence of `DONE_MARKER` in injected text so it cannot be matched by
`relay.repl_supervisor`. A zero-width-joiner inside the string, a split
across two lines, or any equivalent transformation is fine — the only
requirement is that the supervisor's literal byte search cannot match.
The marker emitted by the *commands themselves* (`bump` / `mark done` /
`panic`) is unaffected: those go to stdout after the REPL turn ends,
not through the prompt.

Out of scope (separate follow-up ticket to be created once this ships):
teaching `relay launch` to relaunch the next workflow step in a fresh
process for interactive mode. The current interactive path explicitly
`break`s after one iteration (see `src/relay/commands/launch.py:368`);
auto-chaining is reserved for unattended runs. Stopping cleanly is the
prerequisite — chaining is the next ticket.

Done looks like: in a supervised interactive launch, after the agent
runs `relay bump`, the REPL is gone and the supervisor returns control
to its caller without the human typing `/exit`.

## Context

Relevant files:

- `src/relay/repl_supervisor.py` — defines `DONE_MARKER` and the PTY
  watcher. No change expected here; the constant is already public.
- `src/relay/commands/bump.py` — emit `DONE_MARKER` as the last stdout
  line on a successful bump.
- `src/relay/commands/mark.py` — emit `DONE_MARKER` on `mark done`
  specifically. Other `mark` transitions (active, paused, draft, …) do
  not end a session and must not emit the marker.
- `src/relay/commands/panic.py` — emit `DONE_MARKER` on a successful
  panic.
- `src/relay/resources/prompt.md` — update the "Finishing a step" /
  "What you don't do" sections so the base prompt no longer leaves
  "exit cleanly" undefined. The new line is: in supervised sessions,
  `relay bump` / `relay panic` / `relay mark done` already signal the
  supervisor to tear down your REPL; just run the command and stop.
  Don't paste any marker string yourself.
- `src/relay/compose.py` (or whichever stage hands the final composed
  prompt to the REPL — confirm by tracing `compose_prompt` callers in
  `src/relay/commands/launch.py`) — sanitize the assembled prompt so
  any verbatim `DONE_MARKER` is broken before it reaches the PTY.
  Single source of truth: import `DONE_MARKER` from
  `relay.repl_supervisor` and replace it with a deliberately-broken
  variant (e.g. insert a zero-width character, or split on `>>>`).
- `src/relay/commands/launch.py:335` — there is currently a TEMP block
  that bypasses `run_with_done_marker` entirely so this very ticket
  could be launched. Restore it to call `run_with_done_marker(cmd,
  env)` once the composer sanitizes the marker.

Design notes:

- Import `DONE_MARKER` from `relay.repl_supervisor` rather than
  duplicating the string. One source of truth.
- Print the marker on its own line at the very end of the command's
  stdout, after all other output. The supervisor only looks for the
  literal byte sequence, so flush ordering matters.
- The marker is opaque enough that it's harmless to a human running
  these commands in a normal terminal — it just shows up as a tagged
  line. Don't gate emission on a `RELAY_SUPERVISED` env var unless
  testing shows the bare marker is meaningfully disruptive; simpler is
  better.
- Be careful about non-zero exit paths: if `relay bump` errors before
  it actually advances state, do not emit the marker (the session
  isn't done; the human / agent needs to react). Only emit on the
  success path.

Out of scope:

- The auto-chain / relaunch behavior for interactive workflows. That's
  a separate ticket the human will draft once this lands.
- Any change to `mode: auto` or `mode: script` launches. Both already
  exit on their own; only the interactive PTY-wrapped path needs this.

Tests:

- Add unit coverage in `tests/` for each of the three commands: assert
  the marker is the last line of stdout on the success path and is
  absent on the error path. The supervisor itself already has its own
  test coverage for the marker watcher; no changes needed there.
- Add a composer test: feed a prompt layer containing the literal
  `DONE_MARKER` byte sequence into `compose_prompt`, assert the
  resulting prompt does not contain it. Use the imported constant —
  not a hard-coded literal — so the test follows any future rotation.

Verification:

- `python -m pytest`
- Re-launch this very ticket (`relay launch
  launch-autoquit-when-done-or-relaunch-depending-on`) after restoring
  the supervisor in `launch.py`. Since the ticket body quotes the
  marker, a successful launch that doesn't immediately die proves the
  composer is sanitizing correctly.
- Manual sanity check (optional): a supervised interactive launch of a
  scratch task where the agent runs `relay bump` should return control
  to the parent shell without `/exit`.
