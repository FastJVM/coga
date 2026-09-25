---
name: coga/internals/agent-spawn
description: The single shared agent-spawn path (`spawn_agent_session`) — its compose/prompt-file/argv/audit/spawn/teardown order, per-caller parameters, large-prompt file delivery, the PTY supervisor's done sentinel and exit classification, and the missing-file versus missing-CLI split.
---

# Shared agent spawn

Every command that starts an agent goes through
`src/coga/commands/launch.py` `spawn_agent_session`: "spawn one agent once".
Callers are `coga launch`'s step supervisor, megalaunch, recurring
delegation, and `coga ticket` authoring. Do not hand-roll compose→spawn in a
new command; add the difference as a parameter. A forked copy once lost the
PTY watcher and REPLs stopped releasing on the sentinel.

## Order inside one call

1. `apply_task_env` rewrites `COGA_TASK_*`; inherited `COGA_ASSIST_*` values
   are dropped and re-minted only for a proven recorded assist
   ([human assist](../human-assist/SKILL.md)).
2. Compose the prompt, or use a caller's preflighted `composed_prompt`
   bytes (megalaunch), then append `prompt_suffix` (launch arguments only).
3. Write the prompt file; build argv with `build_agent_command`.
4. `validate_before_spawn` guard; append the launch audit (unless deferred
   into the spawn gate) and, with `commit_log`, publish it at once. `coga
   launch` always sets `commit_log`, so a code step's start check
   ([dev/checkouts](../../../dev/checkouts/SKILL.md)) finds a clean tree;
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
authority to it.
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
  (`coga/session-conduct`); `commit_log` publishes the audit immediately
  (bootstrap targets).

Otherwise argv is `<cli> [name_flag title] [session_id_flag uuid] <prompt>`.

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
(`128 + signal` for any signal Coga did not send). After a Coga teardown the
terminal's input modes are reset. A stateless bootstrap target has no
lifecycle: its final `coga slack --task bootstrap/<name>` FYI is the
completion signal, attributed to its explicit agent or the configured
default; an invalid explicit agent refuses that FYI before posting.

## Missing files versus missing CLI

Compose, prompt-file write, and audit happen before exec, so a
`FileNotFoundError` from this call usually means a vanished skill, context,
or prompt destination. Callers catch `repl_supervisor.AgentCliNotFound` for
the install-the-CLI remedy and report every other one through
`missing_launch_file_message`, naming the path. On the PTY path a missing
binary appears as the child's exit 127, not as that exception.
