---
name: coga-dev/internals/agent-spawn
description: The `coga.launch` Python API and its internal phases, and the single shared agent-spawn path (`spawn_agent_session`) — its compose/prompt-file/argv/audit/spawn/teardown order, per-caller parameters, large-prompt file delivery, the PTY supervisor's done sentinel and exit classification, the unsignalled-advance advisory, and the missing-file versus missing-CLI split.
---

# Shared agent spawn

Every command that starts an agent goes through
`src/coga/launch.py` `spawn_agent_session`: "spawn one agent once".
Callers are `coga launch`'s step supervisor, megalaunch, recurring
delegation, and `coga ticket` authoring. Do not hand-roll compose→spawn in a
new command; add the difference as a parameter. A forked copy once lost the
PTY watcher and REPLs stopped releasing on the sentinel.

## Launch API and phases

The CLI adapter (`src/coga/commands/launch.py`) owns Typer arguments,
presentation and process exits. Python callers use `coga.launch`: ordinary
parameter defaults, `LaunchResult(kind, exit_code)` for a completed launch,
and `LaunchBail(code, reason)` for a refusal or propagated failure.
`LaunchBail` is an ordinary exception, never `SystemExit`. Progress goes
through the scoped `launch_reporting` callback (plain stdout/stderr by
default); callers can render it independently of the result. The recurring
entry point also returns its child-generation lease, and delegation retains
the actual session exit code. Signals unwind library handlers before that
public boundary translates them into `LaunchBail`; recoverable exception
handlers must not swallow termination. Internal callers must not invoke the
Typer command function.

`_launch` coordinates one `_LaunchInvocation` through five fixed phases:
target preparation, assist alignment and ticket classification, initial
script execution, agent preflight, and step supervision. Each phase can
return a completed result before the next begins. Mutable config, target,
routing and blocker state belong to that invocation; checkout return and
blocker cleanup read its latest state after synchronization. This is internal
organization, not a phase registry or extension surface; the ordering
guarantees in [coga/launch](../../../coga/launch/SKILL.md) apply across those
boundaries. Entry preparation is `git.prepare_control_checkout`
([git refresh](../git-refresh/SKILL.md)); a prepared step spawns with the
prompt composed before the switch
(`spawn_agent_session(composed_prompt=...)`). Agent preflight looks up the
CLI with `shutil.which` and resolves secrets with `build_launch_env`; an
open blocker left after a resumed session is restored by
`_reblock_unresolved_resume`; the `--agent` continuation rule is
`consecutive_agent_override`.

## Order inside one call

1. `apply_task_env` rewrites `COGA_TASK_*`; inherited `COGA_ASSIST_*` values
   are dropped and re-minted only for a proven recorded assist
   ([human assist](../../../coga/human-assist/SKILL.md)).
2. Compose the prompt, or use a caller's preflighted `composed_prompt`
   bytes (megalaunch), then append `prompt_suffix` (launch arguments only).
3. Write the prompt file; build argv with `build_agent_command`.
4. `validate_before_spawn` guard; append the launch audit (unless deferred
   into the spawn gate) and, with `commit_log`, publish it at once. `coga
   launch` always sets `commit_log`, so a code step's start check
   ([coga/checkouts](../../../coga/checkouts/SKILL.md)) finds a clean tree;
   megalaunch's deferred audit publishes with its launch admission.
   `before_recompose` (recurring: after the audit
   publishes, exit this pass so the caller reloads and recomposes);
   `before_spawn` final boundary.
5. `repl_supervisor.run_with_done_marker`, optionally with the held-child
   gate ([launch claims](../launch-claims/SKILL.md)).
6. Teardown: when the child actually started, capture usage
   (`coga/usage`; outcome `unknown` unless classified) and publish `log.md`;
   always delete the prompt file.

The step chain (per-step operator and CLI re-resolution, claude↔codex
rotation, `COGA_SUPERVISED`, respawn) wraps this call and stays launch-only.
`build_supervised_step_env` pins `COGA_SUPERVISED=1`, `COGA_EXPECTED_TASK`
(absolute task path), and `COGA_EXPECTED_STEP` per step; the spawn never
reassigns that pair, so it keeps naming the outer session for `coga bump`'s
stale-session guard and the other lifecycle commands that scope their
authority to it. Megalaunch mints the same pair. Both also pin
`COGA_EXPECTED_AGENT`, the agent nickname actually spawned (an `--agent`
override included), so `bump` and `mark done` from that session credit
`agent:<who ran>` rather than the step's routed operator. Known gap
(unresolved, no follow-up ticket): `coga slack` does not read it.
`commands/slack.py` builds its actor from `current_operator`, the routed or
default agent, so under an override (seen with `coga dream --agent codex`,
2026-09-24) it logs `[agent:claude]` and posts "claude on <slug>"; an
agent-run `coga create` in the same runs logged `[human:<user>]`, because its
actor comes from `created_by`. Only `coga launch` adds
`COGA_LAUNCH_RETURNS_CHECKOUT=1`, and only when its checkout boundary
prepared the invoking checkout. The boundary itself (publish, prepare,
return) runs in `_launch` around this call, never inside it, because
authoring and megalaunch spawn here under different admission contracts
([coga/launch](../../../coga/launch/SKILL.md)).
Secrets are minted per step from the freshly read config and ticket.

## Per-caller parameters

- `env`: launch passes `build_launch_env`; authoring passes the ambient
  environment scrubbed of 1Password CLI auth (`config.scrub_op_auth_env`),
  with no Coga secrets (`secrets_are_scoped=False` keeps usage
  redaction from matching unrelated variables).
- `discussion`: for `bootstrap/orient` and `bootstrap/ticket`, the prompt
  goes through the agent's `discussion = "...{prompt}..."` template, else the
  built-in `claude` (`--append-system-prompt`) or `codex`
  (`-c developer_instructions=`) template, else positional. It lands as
  context, so the human's first ask names the session; `name_flag` is skipped.
- `kickoff`: an extra first user turn (`coga ticket`'s greet-first token).
- `include_blocker_preamble=False` and `stateless_identity` for authoring.
- `launch_context` selects the one session-conduct layer
  (`coga/prompt-composition`); `commit_log` publishes the audit immediately
  (bootstrap targets).

Otherwise argv is
`<cli> [launch_args...] [name_flag title] [session_id_flag uuid] <prompt>`.
The agent's `launch_args` tokens (`shlex`-split, empty by default) also follow
`<cli>` in the discussion shape, so every interactive spawn carries them; the
recurring `analyze` argv does not ([agent config](../agent-config/SKILL.md)).
Codex's interactive TUI attaches by default to a shared `codex app-server`
daemon (observed in codex-cli 0.162.x) that spawns shell commands with its own
environment, so the `COGA_*` variables above never reach them; the shipped
`coga.toml` therefore sets `launch_args = "--no-daemon"` for codex. Core adds
no built-in default. Codex rejects the flag only with `--remote` and the
`agents`, `queue`, and `remote-control` subcommands, none of which Coga uses;
the one-shot `codex exec` analyze argv already inherits the environment.

## Large prompts

Linux caps one execve argument near 128 KiB. When the prompt exceeds
`_MAX_PROMPT_ARG_BYTES` (120,000 UTF-8 bytes), argv carries a pointer telling
the agent to read the prompt file in full first; the file outlives the
session.

## The supervisor

The child runs in a PTY with proxied stdio (plain `subprocess.run` when
stdout is not a TTY). PTY output is never a completion channel. `coga bump`,
`coga mark done`, `coga mark canceled`, and `coga block` call
`emit_done_marker`, which atomically writes the task's `id_slug` to
`$COGA_DONE_SENTINEL`; the supervisor polls every 0.25 s, tears down only on
a content match (slug, not path, so a bump from another checkout works), and
sends SIGTERM then SIGKILL after 2 s. Without the variable nothing is written.

`ReplOutcome.kind`: `natural` (own exit, own code), `done` (0), `timeout`
(124, idle or max-session with the exact trigger in `reason`), or `crash`
(`128 + signal` for any signal Coga did not send). `kind` is the *teardown
cause*: `timeout` means a liveness limit started the teardown, not proof
that no done signal ever arrived. How this maps to an activity record's
`outcome_status` is owned by
[activity-capture](../activity-capture/SKILL.md#record-schema-usage_schema--2).

`ReplOutcome.done_signalled`, carried to callers as
`AgentSessionResult.done_signalled`, is a separate observation. It is set
when a matching sentinel is seen while polling, during a teardown already
under way, or in one final check after the child exits and before the
sentinel is deleted (cleanup runs on every path). It never feeds exit
classification, so a done signal followed by a real crash stays a `crash`
with `done_signalled` true. The non-TTY path has no sentinel channel and
reports false (no observation). Launch and megalaunch freeze `(status, step)`
immediately before spawn. They compare it with post-session state through
`repl_supervisor.unsignalled_advance_warning` to print the
[advisory](#unsignalled-advance-advisory) below. After a Coga teardown the
terminal's input modes are reset. A stateless bootstrap target has no
lifecycle: its final `coga slack --task bootstrap/<name>` FYI is the
completion signal, attributed to its explicit agent or the configured
default; an invalid explicit agent refuses that FYI before posting.

## Unsignalled-advance advisory

If the post-session `(status, step)` differs from the pre-spawn freeze and
no matching done signal was observed, launch and megalaunch print a yellow
stderr warning naming the task and the codex `launch_args` remedy. Missing
`COGA_*` is the likely cause, but the warning says only that it *may* be: a
human or another session could also have moved the ticket, so the
observation never establishes who did. Observation limits:

- Launch reads state after its checkout return and reload, so an advance
  published from elsewhere is seen. It skips the check when the return or
  reload refuses, the target was removed, or the ticket cannot be read or
  parsed. Exempt checkouts read their current copy. Megalaunch uses its
  existing post-session read.
- A session whose unresolved blocked resume launch reblocks itself is not
  diagnosed, so the supervisor's own write is never attributed to the agent.
  Megalaunch observes before its reblock.
- The warning appears only after the session ends. It never changes exit
  codes, chaining, or result handling. Bump-time detection (sniffing vendor
  environment markers) is deliberately out of scope: it would put vendor
  knowledge in core and misfire on unsupervised sessions.

## Missing files versus missing CLI

Compose, prompt-file write, and audit happen before exec, so a
`FileNotFoundError` from this call usually means a vanished skill, context,
or prompt destination. Callers catch `repl_supervisor.AgentCliNotFound` for
the install-the-CLI remedy and report every other one through
`missing_launch_file_message`, naming the path. On the PTY path a missing
binary appears as the child's exit 127, not as that exception.

## No launch preflight for the Codex sandbox grant

A `coga launch` preflight that warns or refuses when the Git common dir is not
writable or the [Codex sandbox grant](../../../coga/sandboxes/SKILL.md#codex-sandbox-grant)
is missing was considered and left out (owner-confirmed plan, 2026-10-14). A
write probe in the launch parent proves only the parent's access, not the
child's effective sandbox; a check for the config file cannot establish child
permissions, since codex permissions also come from other config layers and
profiles; and a common-dir probe misses an external `GIT_OBJECT_DIRECTORY`.
Dream's preflight works because it runs inside the launched agent. Reopening
it needs its own capability design: where the probe runs, warn versus refuse,
effective object storage, and which alternate configurations comply.
