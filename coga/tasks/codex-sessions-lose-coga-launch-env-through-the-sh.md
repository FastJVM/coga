---
title: Codex sessions lose COGA_* launch env through the shared app-server daemon
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (evaluate-design)
agent: claude
---

## Description

Since 2026-09-25, interactive Codex sessions launched by `coga launch` / megalaunch run their shell commands without the `COGA_*` variables the supervisor sets (`COGA_SUPERVISED`, `COGA_EXPECTED_TASK`, `COGA_EXPECTED_STEP`, `COGA_DONE_SENTINEL`, `COGA_TASK_*`, and from PR #1015 `COGA_EXPECTED_AGENT`). Effects:

- `coga bump` from Codex is credited `human:<user>`. `coga/log.md` shows 61 such bumps since 2026-09-25 and none earlier; before that date Codex bumps logged `agent:codex`.
- The stale-session bump guard (`commands/bump.py`, gated on `COGA_SUPERVISED`) does not run.
- The done sentinel is never signalled, so the supervisor does not end the session on bump. Example: `add-a-failed-terminal-status` evaluate-design bumped at 17:39 on 2026-10-14, but its session ended at 17:53.

Root cause (confirmed in design, see Context): Codex 0.162.x's interactive TUI attaches to a shared, long-lived `codex app-server` daemon by default, and that daemon spawns the model's shell commands with **its own** environment, not the launching TUI's. Whatever env Coga hands the `codex` child never reaches the agent's shell. `codex --no-daemon` runs the app server in-process and restores inheritance. Disabling `daemon_auto_start` does **not** help while a daemon is already running.

### Acceptance criteria

- [x] Reproduce with a real interactive Codex launch and show which launch configuration preserves `COGA_*` in Codex's shell commands. Done in design (Context, "Reproduction"); the implementer re-runs the probe once against the built argv (last item below).
- [ ] `AgentType` gains one optional, vendor-neutral key, `launch_args` (string, `shlex`-split, default `""`). `build_agent_command` inserts its tokens immediately after `agent.cli` in **both** the positional and the discussion argv shapes. `analyze` (the one-shot autofix argv) is unaffected.
- [ ] The seeded template `src/coga/resources/templates/coga/coga.toml` sets `launch_args = "--no-daemon"` under `[agents.codex]`, with a comment explaining why. This repo's live `coga/coga.toml` gets the same line (see Open Questions: the base prompt forbids agents editing `coga.toml`, so the owner may need to apply it).
- [ ] Unit test: with `launch_args = "--no-daemon"`, `build_agent_command` yields `["codex", "--no-daemon", ..., prompt]` for a launch and `["codex", "--no-daemon", "-c", "developer_instructions=..."]` for discussion. With the key unset, argv is byte-identical to today's.
- [ ] Config test: `launch_args` parses from shared and local tables and follows the existing key-level local-over-shared merge in `_parse_agents`. A non-string value fails config load the way other string keys do.
- [ ] Fail loud: after a supervised session ends, if the ticket's step/status changed during the session while the done sentinel was **never** signalled, `coga launch` and megalaunch print a yellow stderr warning. The warning names the task, says the agent's shell probably lacked `COGA_*` (so the bump was credited to a human and the stale-step guard did not run), and points to `coga/agents`. The warning is advisory and never changes exit codes or chaining. A session that signals done, or that ends with the ticket unchanged, prints nothing new. The warning has tests for both launch and megalaunch, or for a shared helper both call.
- [ ] Docs: `docs/contexts/coga/agents/SKILL.md` adds `launch_args` to the Keys table and gets a short "Agent shells must inherit the launch env" note. The note explains the Codex daemon, the `--no-daemon` remedy, and the new warning. `docs/contexts/coga/testing/SKILL.md` "Restricted sandboxes" gets one bullet on the daemon env loss that links to `coga/agents`. Update any packaged twins of these topics too (`tests/test_packaging.py` passes).
- [ ] Verification (manual, recorded on the blackboard): with a Codex daemon running, a real `coga launch` of a throwaway Codex ticket step produces a `coga bump` credited `agent:codex`, and the session ends on bump with outcome `done`. If an attended launch cannot be driven from the implement session (nested-Codex/sandbox limits in `coga/testing`), record the PTY probe against the exact argv `build_agent_command` now emits, and leave the full launch check to the owner in review.
- [ ] `python -m pytest` and `coga validate --json` pass.

### Proposed shape

1. **`src/coga/config.py`**: add `launch_args: str = ""` to the `AgentType` dataclass, next to `name_flag`/`session_id_flag`, with a comment in the same style ("argv tokens inserted right after `cli` for every interactive spawn…"). Parse it in `_parse_agents` exactly like `name_flag` (an optional string key, merged per key).
2. **`src/coga/commands/launch.py` `build_agent_command()`**: compute `extra = shlex.split(agent.launch_args)` once and emit `[agent.cli, *extra, ...]` in both return paths. Update the docstring's "Default shape" paragraph. `spawn_agent_session` already routes every interactive spawn (launch chain, megalaunch, `coga ticket`/chat) through this builder, so no other spawn site changes. Confirm this with a grep for `agent.cli` and for argv lists built elsewhere.
3. **Template**: in `src/coga/resources/templates/coga/coga.toml` `[agents.codex]`, add `launch_args = "--no-daemon"` plus a 2–3 line comment ("Codex's shared app-server daemon runs shell commands with its own env, so `COGA_*` launch variables never reach the agent; `--no-daemon` keeps them. Remove only if your Codex predates the flag."). Mirror the line in live `coga/coga.toml`, which is an intentionally divergent twin, so no packaging-test change is needed.
4. **Fail-loud detector**: a small pure helper (suggested home: `src/coga/repl_supervisor.py` or next to the launch chain in `commands/launch.py`. Megalaunch already imports from `repl_supervisor`, which gives it its 2 consumers) along the lines of `def warn_if_unsignalled_advance(ref_path, before: tuple[status, step], after: tuple[status, step], outcome_kind: str) -> str | None`. It returns the warning text when `outcome_kind != "done"` and `(status, step)` differs. Both callers already hold the pre-spawn ticket (`spawn_ticket` in the launch chain; the per-task ticket in megalaunch). They re-read the ticket after the session returns and echo the warning. In the launch chain, place it right after `typer.echo(f"Launch: agent exited with code …")` and before the timeout/non-zero branches, so it also fires on a timeout teardown. This needs no vendor knowledge and catches any CLI that drops env.
5. **Docs** as listed in the acceptance criteria. Keep `coga/agents` the owner of the remedy; `coga/testing` only links to it.
6. **Tests**: extend the existing `build_agent_command` and agent-config tests (find them with `grep -rn build_agent_command tests/` and `grep -rn name_flag tests/`). For the detector, unit-test the helper's truth table plus one launch-chain test using the existing fake-agent/PTY harness that bumps the ticket via a path that doesn't touch the sentinel.

### Out of scope

- Fixing Codex upstream, or filing an issue (worth doing, but not this ticket).
- Correcting the 61 historical `human:` bump lines; `coga/log.md` is append-only.
- In-session detection inside `coga bump` itself, such as keying on vendor env markers like `CODEX_THREAD_ID`. That would be vendor knowledge in core and would misfire on bare, unsupervised Codex sessions. The supervisor-side check is vendor-neutral. Revisit only if the owner wants a bump-time warning (Open Questions).
- Ending the session from the supervisor when the ticket advances without a sentinel. That is a behavior change to the sentinel contract (session-scoped teardown). With env restored, the sentinel works again.
- Passing env to the daemon (for example `shell_environment_policy.set` overrides). These are per-vendor, they leak across sessions that share a daemon, and `-c` overrides don't reliably bypass the daemon.
- `analyze` / `codex exec`: already inherits env (verified).

## Context

### Reproduction (2026-10-14, codex-cli 0.162.1, Linux, daemon pid already running)

A Python `pty.fork()` driver ran the real interactive TUI as `codex [flags] "<prompt>"`, the same shape `build_agent_command` emits, from a trusted dir. The env had `COGA_PROBE=hello-<label>` and `COGA_SUPERVISED=1`, and the prompt asked Codex to run a script that writes `printenv COGA_PROBE`/`COGA_SUPERVISED` and its `CODEX_*`/`CLAUDE*` var names to a file. Driver: scratchpad `drive2.py` (not committed; trivial to recreate).

| argv | `COGA_*` in agent shell |
|---|---|
| `codex "<prompt>"` (default, attaches to running daemon) | **unset** |
| `codex --no-daemon "<prompt>"` | **present** (`hello-…`, `1`) |
| `codex --disable daemon_auto_start "<prompt>"` | unset |
| `codex -c features.daemon_auto_start=false "<prompt>"` | unset |

- In the daemon case the shell's env carries `CODEX_THREAD_ID`/`CODEX_SESSION_ID` etc. but none of the launching process's env (not even `CLAUDECODE`, which was in the driver's env). With `--no-daemon`, the full launcher env is present. So the daemon's env, not the TUI's, is what the shell sees.
- `daemon_auto_start=false` only stops the TUI from *starting* a daemon. The binary's selection reasons include `existing_daemon`, and an already-running daemon is still used. So a config-only `[features]` fix is insufficient, and no Codex config key equivalent to `--no-daemon` was found in the binary's strings.
- An earlier run with `-C <dir> -s workspace-write -a never -c projects.<dir>.trust_level=…` *did* inherit env. Some of those flags force the in-process server (the binary lists "incompatible option" as a selection reason). This was not isolated further, and it is not a reliable remedy.
- `--no-daemon` is rejected only with `--remote`, `codex agents`, `codex queue`, and `remote-control`. Coga uses none of these.
- Transcript `source: "unified_exec_startup"` appears in both modes, so it does not distinguish them.

### Code facts the implementer relies on

- `src/coga/repl_supervisor.py` `build_supervised_step_env()` mints `COGA_SUPERVISED`/`COGA_EXPECTED_TASK`/`COGA_EXPECTED_STEP`. `run_with_done_marker()` exports `COGA_DONE_SENTINEL` (`SENTINEL_ENV`) and returns a `ReplOutcome` whose `kind` is `"done"` only when the sentinel matched. That `kind` is surfaced to callers as `AgentSessionResult.termination_kind` from `commands/launch.py` `spawn_agent_session()`, which is the signal the detector keys on.
- `src/coga/commands/common.py` `completion_identity()` credits `agent:<operator>` only when `COGA_SUPERVISED` is set and `COGA_EXPECTED_TASK` resolves to the ticket path. Otherwise it falls through to `human:<current_user>`. This is the mis-credit.
- `src/coga/commands/bump.py` `_assert_supervised_step_is_current()` returns early when `COGA_SUPERVISED` is absent. This is the skipped stale guard.
- `src/coga/commands/launch.py` `build_agent_command()` is the single interactive argv builder (called from `spawn_agent_session`). It already reads per-agent `name_flag`/`session_id_flag` with `shlex.split`. `DEFAULT_DISCUSSION_TEMPLATES` is existing precedent for per-CLI built-in defaults in core, which matters for the open question on defaulting `launch_args`.
- Spawn sites: the launch chain (`commands/launch.py`, the loop that calls `build_supervised_step_env` then `spawn_agent_session`), `src/coga/megalaunch.py` (calls `build_supervised_step_env` and `spawn_agent_session`), and `src/coga/commands/ticket.py` (`spawn_agent_session`, discussion).
- `src/coga/config.py` `AgentType` holds per-agent keys. `_parse_agents` merges shared and local per key, and `docs/contexts/coga/agents/SKILL.md` "Keys" documents every key.
- `tests/test_packaging.py` `INTENTIONALLY_DIVERGENT_TWINS` already lists `coga/coga.toml`, so adding the line to the template alone keeps the test green.
- `docs/contexts/coga/testing/SKILL.md` "Restricted sandboxes" already documents Codex 0.162.1 daemon quirks (`/tmp/codex-daemon-<uid>`). The new bullet belongs there.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

coga-launch: 4634d435-cd6d-4873-b4c2-b9f2f8b52db6

## Design notes (design step, 2026-10-14)

- Reproduced with a real interactive Codex TUI under a PTY. Only `--no-daemon` preserves `COGA_*`; feature-flag disabling does not while a daemon runs. See `## Context`.
- Chose a vendor-neutral `launch_args` key and put the Codex value in config, over a hardcoded core default. That honors the ticket's "prefer config" criterion; the cost is that existing repos must add the line themselves (Open Question 1).
- Chose a supervisor-side fail-loud (ticket advanced and no sentinel) over a bump-side vendor env sniff. It is vendor-neutral and has no false positives on bare Codex sessions; the cost is that it warns only after the session ends.

## Open Questions

1. **Built-in default for existing repos?** Should `launch_args` also have a built-in default for the known `codex` CLI (`"--no-daemon"`), like `DEFAULT_DISCUSSION_TEMPLATES`, so repos initialized before this fix get it without editing `coga.toml`? Pro: every existing Codex user is fixed on upgrade. Con: vendor knowledge in core, and an older Codex without the flag would fail to start unless the user sets `launch_args = ""` locally. The spec currently uses **template only**.
2. **Who edits this repo's live `coga/coga.toml`?** The base prompt forbids agents editing `coga.toml`. Should the implement step add `launch_args = "--no-daemon"` to `coga/coga.toml` (owner grants the exception), or should the owner apply it by hand at review?
3. **Bump-time warning too?** Is the post-session supervisor warning enough for "fail loud"? Or do you also want `coga bump` to warn in-session when it is plainly inside an agent but unsupervised? The latter needs a per-agent env marker (for example a config key `session_env = "CODEX_THREAD_ID"`), and is currently out of scope.
