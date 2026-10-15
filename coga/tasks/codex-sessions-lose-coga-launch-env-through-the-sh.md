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
step: 4 (implement)
agent: claude
---

## Description

Since 2026-09-25, interactive Codex sessions launched by `coga launch` / megalaunch run their shell commands without the `COGA_*` variables the supervisor sets (`COGA_SUPERVISED`, `COGA_EXPECTED_TASK`, `COGA_EXPECTED_STEP`, `COGA_DONE_SENTINEL`, `COGA_TASK_*`, and from PR #1015 `COGA_EXPECTED_AGENT`). Effects:

- `coga bump` from Codex is credited `human:<user>`. `coga/log.md` shows 61 such bumps since 2026-09-25 and none earlier; before that date Codex bumps logged `agent:codex`.
- The stale-session bump guard (`commands/bump.py`, gated on `COGA_SUPERVISED`) does not run.
- The done sentinel is never signalled, so the supervisor does not end the session on bump. Example: `add-a-failed-terminal-status` evaluate-design bumped at 17:39 on 2026-10-14, but its session ended at 17:53.

Root cause (confirmed in design, see Context): Codex 0.162.x's interactive TUI attaches to a shared, long-lived `codex app-server` daemon by default, and that daemon spawns the model's shell commands with **its own** environment, not the launching TUI's. Whatever env Coga hands the `codex` child never reaches the agent's shell. `codex --no-daemon` runs the app server in-process and restores inheritance. Disabling `daemon_auto_start` does **not** help while a daemon is already running.

### Acceptance criteria

- [x] Reproduce with a real interactive Codex launch and show which launch configuration preserves `COGA_*` in Codex's shell commands. Done in design (Context, "Reproduction"); verification against the implemented argv follows the manual-verification criterion below, including its host-shell fallback.
- [ ] `AgentType` gains one optional, vendor-neutral key, `launch_args` (string, `shlex`-split, default `""`). `build_agent_command` inserts its tokens immediately after `agent.cli` in **both** the positional and the discussion argv shapes. `analyze` (the one-shot autofix argv) is unaffected.
- [ ] The seeded template `src/coga/resources/templates/coga/coga.toml` sets `launch_args = "--no-daemon"` under `[agents.codex]`, with a comment explaining why. This repo's live `coga/coga.toml` gets the same line (owner approved a narrow exception allowing the implementer to add this line and its explanatory comment).
- [ ] Unit test: with `launch_args = "--no-daemon"`, `build_agent_command` yields `["codex", "--no-daemon", ..., prompt]` for a launch and `["codex", "--no-daemon", "-c", "developer_instructions=..."]` for discussion. With the key unset, argv is byte-identical to today's.
- [ ] Config test: `launch_args` parses from shared and local tables and follows the existing key-level local-over-shared merge in `_parse_agents`. A non-string value fails config load the way other validated string keys do. An explicit local empty string clears the shared value; quoted multi-token arguments retain their token boundaries.
- [ ] Fail loud: after a supervised session ends, when a readable post-session ticket has a different `(status, step)` from the immutable pre-spawn snapshot and no matching done sentinel was observed, `coga launch` and megalaunch print a yellow stderr warning. Carry sentinel observation independently of exit classification, including a final check after child exit and before sentinel cleanup. A done signal followed by a crash must suppress this warning while retaining the crash result. The warning names the task and points to `coga/agents`; it says missing `COGA_*` **may** explain the change and **could** cause human attribution and a skipped stale-step guard. Human or concurrent-session edits are also possible. Never assert who made the change from this observation alone.
- [ ] Warning observation is advisory: use refreshed state after launch's existing checkout settle/reload, before timeout/nonzero result handling. Skip detection if checkout return/reload refuses, the target is removed, or the diagnostic ticket read fails with an expected filesystem/parsing/validation error. Exempt checkouts use their current ref. Do not introduce another checkout operation or change existing exit codes, chaining, or error handling. Megalaunch observes its existing post-session state before reblocking/result handling; diagnostic failure must not replace its existing handling. Supervisor-owned reblocking must not itself be mistaken for an agent's change (see Proposed shape).
- [ ] Warning tests cover changed/unchanged state, matching/nonmatching sentinel, done-signal followed by crash, a late matching sentinel seen only after child exit, timeout/nonzero exits, checkout-refreshed advances, refused return, and removed/unreadable tickets. Exercise both callers' wiring, with a shared helper's truth table where useful.
- [ ] Docs: `docs/contexts/coga/agents/SKILL.md` owns the `launch_args` Keys entry, env-inheritance requirement, Codex daemon remedy, existing-repo config migration, and advisory warning with its observation limits. Update `docs/contexts/coga/testing/SKILL.md` Restricted sandboxes with a link to that remedy and correct its Codex sandbox grant argv summary. Update `docs/contexts/coga/internals/agent-spawn/SKILL.md` argv and sentinel-observation/result contracts. Sync all packaged twins (`tests/test_packaging.py` passes).
- [ ] Verification (manual, recorded on the blackboard): with a Codex daemon running, verify the exact implemented `build_agent_command` argv in a real interactive session and run `coga launch` on a throwaway Codex ticket step. Its `coga bump` must be credited `agent:codex`, and the session must end on bump with outcome `done`. One full launch may establish both checks if its actual argv and shell-env evidence are captured. If the implementation session cannot run nested Codex under `coga/testing` constraints, do not retry through a PTY or escalation: record the exact built argv and automated results, and hand both real-TUI checks to the owner's host shell. Keep this criterion unchecked until the owner supplies a receipt with tested revision, Codex version, running-daemon evidence, actual argv, relevant `COGA_*` values (no secrets), bump attribution, and supervisor outcome. This receipt is required before final acceptance; implementation may hand off with this explicit verification gap.
- [ ] `python -m pytest` and `coga validate --json` pass.

### Proposed shape

1. **`src/coga/config.py`**: add `launch_args: str = ""` to the `AgentType` dataclass, next to `name_flag`/`session_id_flag`, with a comment in the same style ("argv tokens inserted right after `cli` for every interactive spawn…"). Add it to `_ALLOWED_AGENT_KEYS`; parse it in `_parse_agents` using the explicit string validation pattern of `session_id_flag`, with the existing key-level merge. Unset means `""`; an explicit local `""` clears a shared flag. The owner approved template-only defaults: do not add a Codex default in core.
2. **`src/coga/commands/launch.py` `build_agent_command()`**: compute `extra = shlex.split(agent.launch_args)` once and emit `[agent.cli, *extra, ...]` in both return paths. Update the docstring's "Default shape" paragraph. `spawn_agent_session` already routes every interactive spawn (launch chain, megalaunch, `coga ticket`/chat) through this builder, so no other spawn site changes. Confirm this with a grep for `agent.cli` and for argv lists built elsewhere.
3. **Template**: in `src/coga/resources/templates/coga/coga.toml` `[agents.codex]`, add `launch_args = "--no-daemon"` plus a 2–3 line comment ("Codex's shared app-server daemon runs shell commands with its own env, so `COGA_*` launch variables never reach the agent; `--no-daemon` keeps them. Remove only if your Codex predates the flag."). The owner explicitly authorizes the implementer to add the same `launch_args` line and explanatory comment under `[agents.codex]` in live `coga/coga.toml`; this exception authorizes no other config edits. It is an intentionally divergent twin, so no packaging-test exemption change is needed.
4. **Sentinel observation**: add an independent `done_signalled` observation to `ReplOutcome` and propagate it through `AgentSessionResult`. Latch a matching sentinel when observed during polling, including during teardown, then check once more after the child has exited and before deleting its sentinel. Ensure cleanup remains reliable on exceptional paths. Do not derive this bit from `kind`, and do not let the final observation change `_classify_exit`, timeout/crash status, usage classification, or chaining. Any path without a sentinel channel reports no observation. Preserve compatibility for existing result construction sites and update test doubles explicitly.
5. **Fail-loud detector**: place shared pure comparison/wording logic in `src/coga/repl_supervisor.py` (launch and megalaunch are its two consumers). Inputs are the task label, immutable before/after `(status, step)` tuples, and `done_signalled`; unavailable post-state yields no warning. Callers own best-effort ticket IO and yellow stderr output. Freeze the before tuple after admission/start-state writes and immediately before spawning, so activation cannot trigger a warning. In launch, observe after the existing `boundary.settle` and `boundary.reload`, before timeout/nonzero branches. If return/reload refuses or removes the target, skip the diagnostic. Catch only expected read/parse/validation errors in the diagnostic path; leave downstream handling intact. In megalaunch use its post-session ticket before `_reblock_unresolved` and early result returns. Launch currently reblocks before settling; if `_reblock_unresolved_resume` actually writes a supervisor-owned state change, suppress that session's diagnostic rather than reordering lifecycle operations or attributing that write to the agent. This deliberately gives up diagnosis on those reblocked sessions. A successful read alone does not prove the agent made the change.
6. **Docs** as listed in the acceptance criteria. Keep `coga/agents` the owner of the remedy, and link from testing. Agent-spawn owns the independent observation versus outcome distinction. If documentation describes timeout as proof no done signal ever arrived, correct it: timeout classification remains the original teardown cause even when a signal arrives later.
7. **Tests**: extend existing argv/config tests for both launch shapes, unchanged defaults, local override/clear, invalid types, and quoted tokens. Add supervisor regressions for signal-then-crash and a final observation after child exit. Cover the diagnostic truth table and both caller integrations, including refreshed-only advance, failed return, missing/unreadable state, supervisor reblocking, and timeout/nonzero paths. Verify warning presence/absence and unchanged results/chaining together.

### Out of scope

- Fixing Codex upstream, or filing an issue (worth doing, but not this ticket).
- Correcting the 61 historical `human:` bump lines; `coga/log.md` is append-only.
- In-session detection inside `coga bump` itself, such as keying on vendor env markers like `CODEX_THREAD_ID`. That would be vendor knowledge in core and would misfire on bare, unsupervised Codex sessions. The supervisor-side check is vendor-neutral. The owner approved supervisor-only warnings; bump-time detection remains out of scope.
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

- `src/coga/repl_supervisor.py` `build_supervised_step_env()` mints `COGA_SUPERVISED`/`COGA_EXPECTED_TASK`/`COGA_EXPECTED_STEP`. `run_with_done_marker()` exports `COGA_DONE_SENTINEL` (`SENTINEL_ENV`) and returns a `ReplOutcome` whose `kind` is `"done"` only when the sentinel matched. That `kind` is surfaced to callers as `AgentSessionResult.termination_kind` from `commands/launch.py` `spawn_agent_session()`. A matching sentinel can still lead to a classified crash; the implementation must add an independent observation for the detector instead of keying it on this classification.
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

None. Owner approved the revised design and these decisions in the attended review:

1. **Template-only default.** No built-in Codex default in core; existing repositories must explicitly add the config value. Document that migration in `coga/agents`.
2. **Live config exception granted.** The implementer may add `launch_args = "--no-daemon"` and its explanatory comment under `[agents.codex]` in `coga/coga.toml`. This is a narrow exception to the base prompt's config-edit prohibition, not permission for other config edits.
3. **Supervisor-only warning.** No bump-time vendor sniffing. Accept that diagnosis arrives after session exit and is skipped when reliable post-state is unavailable.

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

## Owner-review preparation (2026-10-14)

- Checked the evaluator findings against `run_with_done_marker` / `_classify_exit`, launch's post-session settle/reload sequence, megalaunch's post-session handling, and the agents/testing/agent-spawn/launch-boundary topics. Revised the Description and Proposed shape for all three must-fix findings; none is rejected. These are proposed design corrections, pending owner approval, not implemented behavior.
- The design now carries independent matching-sentinel evidence, suppresses diagnosis when refreshed state is unavailable, and preserves existing lifecycle/result handling. Launch's own unresolved-resume reblocking is an additional false-positive source; suppress that diagnostic when the supervisor writes the change. Cost: no warning for those sessions or unavailable post-state.
- Added validated-string parsing, allowed-key registration, local empty-string clearing, quoted-token coverage, missing documentation touchpoints, and an executable host-shell verification handoff. No nested Codex probe was attempted. The original dated reproduction remains author-provided evidence, not a new verification receipt.
- Open Questions 1–3 still require the owner: recommend template-only default, a narrowly scoped implementation-time exception for the live Codex `launch_args` line/comment, and supervisor-only warning. Costs: existing repos need config migration; warnings arrive only after the session ends. No config exception has been granted.
- Only this ticket was edited. No implementation, config changes, or workflow transition. Await explicit owner decisions and instruction to advance this owner-held review gate.
- Verification: `git diff --check` passed; `coga validate --task codex-sessions-lose-coga-launch-env-through-the-sh --json` returned `ok_count: 1`, no issues or fixes. Implementation tests were not run for this ticket-only revision.

## Owner approval and implementation handoff

The owner replied "ok" to the explicit request to approve the revised design, the three decisions above, and advancement to implementation. All evaluator must-fix findings are resolved in the revised specification; none was rejected. The earlier owner-review preparation notes describe the pre-approval state. Implement the current Description/Proposed shape, including independent sentinel observation, advisory post-refresh detection, regression coverage, and documentation twins. Preserve the manual verification gap until the required host-shell receipt is available. The narrow live-config exception is now granted. Review-design is complete; advance once to implement and stop this session.

## Dev

branch: codex-no-daemon-launch-args

## Owner review discussion — 2026-10-14

- Later owner feedback in the evaluator conversation: crashes are rare enough that the false-positive warning in finding 1 is acceptable for now. The owner accepts the simpler termination-outcome heuristic rather than requiring separate sentinel observation solely for that case. This concerns warning accuracy, not crash recovery or durable-state guarantees. The implementation specification currently requires independent sentinel observation from the separately approved revision; reconcile that requirement with this later owner feedback before treating the extra machinery as mandatory.
- On finding 2, the owner asks why tickets are not committed immediately and notes concurrent races are rare. Explanation supplied: lifecycle transitions already attempt immediate commit/push via `advance_step` and `git.sync_task_state`; refreshing brings a different checkout up to date. Handling a deleted ticket is a separate issue from concurrent races. No new owner decision on that handling was inferred.
- This conversation discovered that control had already advanced to step 4 with an implementation branch recorded. Preserved that current state and all other-session edits; this note makes no workflow transition and performs no implementation work.
