# Production prompt builders and transports

Revision: see `sources.json` for full source/blob pins. This inventory was
checked by searching `src/coga`, `src/coga_edge` and packaged Python attachments
for prompt composition and agent-spawn calls. Scripts that call launch reuse
the following paths; they are not independent assemblers.

| Surface | Builder / caller | Transport and boundary |
| --- | --- | --- |
| Ordinary workflow step, including inline and skilled steps | `compose.compose_prompt_report`, `compose_prompt`, `_step_layers`; `launch._LaunchInvocation` preflight and step loop, `_prepare_step_checkout` | `spawn_agent_session` uses preflighted bytes when supplied, otherwise composes; UTF-8 temp file, interactive agent argv, PTY/supervisor. Checkout notice is caller-observed. Completion is a sentinel written by lifecycle commands, never prompt text |
| Stateless agent procedure | Same compose API with `BootstrapRef`; ordinary launch | Omits ticket loop; same interactive transport. Procedure supplies completion; no invented task lifecycle |
| Guided authoring, empty/new/existing target | `commands.ticket._authoring_ticket`, `_run_authoring_session`; `spawn_agent_session` | Ephemeral projection removes step, replaces skills with `bootstrap/ticket`, disables blocker preamble. Discussion-template argv plus kickoff token; no task secret injection; no execution supervisor chain. A `TaskRef` still receives `prompt-ticket.md`, the contradictory baseline |
| Direct chat (`bootstrap/orient`) | Same compose API, discussion-bootstrap branch in launch | Discussion-template argv, no kickoff interview; chat guard and generated checkout notice include branch preparation command. No task loop. Aliases are routing, not a distinct builder |
| Owner assist | Same compose/spawn under launch's explicit owner-held override | Interactive PTY; recorded-checkout assists validate PR head and propagate scoped assist identity. Same prompt builder; capability/checkout checks stay executor-owned |
| Megalaunch | `megalaunch._preflight_agent_launch` calls `compose_prompt` prospectively; `spawn_agent_session(composed_prompt=...)` | Interactive PTY despite queued conduct. Exact preflighted prompt crosses guarded admission; launch claim stays outside assembly. No supplied checkout notice means manual checkout rules |
| Recurring period agent, direct interactive recurring, delegated stateless procedure | `recurring_runner` chooses `_recurring_launch_context`, invokes launch / `launch_with_before_spawn`; shared compose/spawn | Interactive PTY; `--interactive` selects attended, runner dispatch selects recurring queue. Period lease and delegation admission stay outside assembly. Stateful period and stateless target have different completion contracts |
| Script phase and script-to-agent handoff | `launch_script.run_script_phase`, script chain classification, then shared launch if agent remains | `[sys.executable, ticket.py, *args]`, subprocess without any prompt or agent preflight. Nonzero/terminal/owner handoff stops; unchanged open step can proceed to agent using reloaded state |
| Noninteractive autofix, post-sweep and `coga run autofix-analyze` | `recurring_autofix.build_prompt`, `analyze_record`, `build_analyze_command`, `parse_analysis`; `run_autofix` catches analyst failures | Independent text builder; `subprocess.run`, DEVNULL stdin, captured stdout/stderr, deadline. Built-ins `claude -p {prompt}` / `codex exec {prompt}`; configured `analyze` wins; unknown CLI without template refuses loudly. No positional interactive fallback, PTY, launch marker, lifecycle or mutation authority |
| Prompt report / preflight / inspection | `compose_prompt_report` from launch reporting and validation paths; `compose_prompt` during preflight | Reporting is not another instruction builder. CLI report refreshes ignored skill view; the fixtures instead use the read-only API |

`spawn_agent_session` adds positional arguments as `_agent_args_prompt_suffix`
and a unique last `coga-launch:` line; neither is part of the compose report.
`build_agent_command` selects positional versus discussion-template argv and
session/name flags. Linux oversized interactive prompts use `_argv_prompt`'s
file pointer above 120,000 bytes. Windows uses `_plan_windows_agent_command`
and `repl_supervisor_nt`'s serialized-command budget, including batch wrappers.
Those are delivery adapters, not content assemblers. Autofix has its own
record/open-ticket bounds for argv; do not silently replace its one-shot
contract with the interactive file-pointer mechanism.

Other relevant owners are `coga/prompt-composition` (layer order, resolution,
authoring projection), `coga/recurring/autofix` (loop, parse failure and sweep
exit), and `coga/script-tickets` (classifier and handoff). Their full paths and
snapshots appear in `sources.json`. No production owner is changed by these
experimental attachments.
