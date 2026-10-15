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
step: 3 (review-design)
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

## Evaluator review

Cold review, 2026-10-14. **Not ready for implementation until the must-fix items below are resolved.** The vendor-neutral config/argv change is coherent and fits shared launch infrastructure; the warning needs a more precise observation contract. No ticket-body, config, code, branch, or PR changes were made in this step.

### Must fix before implementation

1. **`termination_kind != "done"` does not prove the sentinel was never signalled.** In `src/coga/repl_supervisor.py`, `run_with_done_marker` records `term_kind="done"` on a matching sentinel, but `_classify_exit` deliberately returns `"crash"` if teardown races a different fatal signal. `tests/test_repl_supervisor.py::test_classify_exit_surfaces_real_crash_after_stop` explicitly covers this. `spawn_agent_session` returns only the classified outcome through `AgentSessionResult`, losing that distinction. The proposed helper would therefore warn even for a session that signalled done, violating the acceptance criterion. Resolve whether to carry an independent matching-sentinel observation through the result (including a final observation before sentinel cleanup), or explicitly narrow the criterion to a heuristic about termination. Preserve crash/timeout exit classification and chaining either way; add a regression for done-signal followed by crash. Warning wording must describe missing env and human attribution as possible consequences, not established facts: a ticket can also be changed by a human or another session.

2. **Define a safe post-session ticket observation point and unavailable-ticket behavior.** The proposed insertion immediately after “agent exited” precedes `_CheckoutBoundary.settle` / `reload` in `src/coga/commands/launch.py`. That return publishes and refreshes state and can re-resolve the ref; an earlier read need not see an advance published from another checkout or a relocated contexts/layout state. More directly, the existing chain deliberately handles `target_removed` and `not ref.ticket_path.exists()` as clean terminal cases. An unconditional new `read_ticket` before those guards can raise on a supported deletion and change the exit result, contrary to “advisory only.” Specify how the detector uses refreshed state when available, what it does when return refuses or the ticket is missing/unreadable, and retain warning coverage before timeout/nonzero exits. Add integration cases for removed/unreadable state and an advance visible only after return, alongside the ordinary unsignalled advance. Evidence: `_CheckoutBoundary.settle` / `reload`, the post-spawn chain in `commands/launch.py`, and `docs/contexts/dev/checkouts/launch-boundary/SKILL.md`; existing return behavior is exercised by `test_launch_returns_a_feature_branch_handoff_before_the_next_step` and `test_launch_returns_the_checkout_after_a_failed_session`.

3. **Make the manual-verification fallback executable under the cited sandbox constraint.** The acceptance criterion allows nested-Codex/sandbox limits to prevent the full launch check but then requires a PTY probe invoking the same nested Codex CLI. `docs/contexts/coga/testing/SKILL.md`, “Restricted sandboxes,” says not to launch another Codex CLI from a Codex session's shell tools and records that `--no-daemon` and escalation did not resolve the observed nesting failure. Permit an implementer under that constraint to record the exact built argv and automated evidence and hand both real-TUI checks to the owner's host shell. Specify the owner receipt needed before accepting the fix. This changes the verification handoff, not the recorded design reproduction or the intended runtime remedy.

### Recommendations and owner decisions

- **Use the actual validated-string pattern.** `_parse_agents` currently assigns `name_flag` directly without a type check; `session_id_flag`, `discussion`, and `analyze` have explicit checks. Follow one of those for `launch_args`, and add it to `_ALLOWED_AGENT_KEYS`. The acceptance criterion already requires rejection of non-strings; Proposed shape's “exactly like name_flag” is misleading. Cover an explicit local empty string clearing the shared flag as well as quoted multi-token splitting.
- **Complete the documentation touchpoints.** In addition to the named agents/testing updates, `docs/contexts/coga/internals/agent-spawn/SKILL.md`, “Per-caller parameters,” specifies the old complete argv shape, and testing's “Codex sandbox grant” says launch spawns plain `codex <prompt>`. Update those summaries and their packaged twins to refer to the new configured argv; keep the remedy owned by `coga/agents`. All three topics have bootstrap packaged twins. Config's intentionally divergent twin exemption is present as claimed.
- **Record owner dispositions for Open Questions 1–3.** Template-only defaults and no bump-time vendor sniffing are consistent with the current scope; existing repositories will need an explicit config addition. Decide who applies the required live `coga/coga.toml` line before implementation. Do not infer an exception to the base prompt's config-edit prohibition from Proposed shape.

### Evidence and review scope

The ticket's Description subsections are correctly nested and compose; the frozen `code/design-then-implement` workflow matches the packaged definition and correctly hands this review to an owner gate. No contexts are attached; the body identifies the relevant config, agents, testing, and spawn sources. `build_agent_command` has the two stated argv paths, while `recurring_autofix.build_analyze_command` builds its own argv. `completion_identity` and `_assert_supervised_step_is_current` have the stated env gates. The design's real-TUI reproduction is author-provided evidence; it was not rerun in this evaluator session.

Verification: `PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest -q tests/test_repl_supervisor.py::test_classify_exit_surfaces_real_crash_after_stop tests/test_launch.py::test_launch_returns_a_feature_branch_handoff_before_the_next_step tests/test_launch.py::test_launch_returns_the_checkout_after_a_failed_session tests/test_config.py::test_agent_session_id_flag_must_be_string` → **4 passed in 2.25s**, Python 3.12.12. These verify existing contracts, not an implementation of this design. Full-suite and manual runtime verification remain implementation/review work.
