The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap notes

- Human clarified intent: add a Relay option so Claude Code and Codex can be launched with their permission/approval prompts bypassed, but only when a specific ticket opts into that behavior.
- Local CLI help checked on 2026-06-09:
  - `codex --help` exposes `--dangerously-bypass-approvals-and-sandbox` and `--ask-for-approval never`.
  - `claude --help` exposes `--dangerously-skip-permissions`, `--allow-dangerously-skip-permissions`, and `--permission-mode bypassPermissions`.
- Superseded initial ticket shape: keep dangerous argv in local config, add a per-ticket frontmatter opt-in, and have `relay launch` append the configured argv only for opted-in interactive/auto agent launches.
- Narrow contexts to attach: `relay/architecture` for canonical frontmatter/config semantics and `relay/codebase` for source layout/tests.

## Revision notes

- Human clarified the product shape after the first draft: this should be a per-agent local policy for autonomous work, not a per-ticket frontmatter opt-in.
- Current ticket text asks for `[agents.<name>] skip_permissions = "auto"` plus `skip_permissions_argv = "..."` in `relay.local.toml`.
- The policy applies only to normal `mode: auto` task launches. Interactive tickets, bootstrap/discussion shims, and script tasks should keep today's behavior.
- The evaluator review below is still useful for argv placement, agent rotation, local-only dangerous config, and template/docs coverage, but its recommendation to add canonical ticket field `skip_permissions: true` is superseded.

## Evaluator review

**Verdict:** Yes, this is clear enough to launch. The core behavior is well stated in [ticket.md](/home/n/Code/relay/relay-os/tasks/skip-permissions-option/ticket.md:18): per-ticket opt-in, dangerous argv in `relay.local.toml`, no global default change, fail loud when opted in but unconfigured.

**Workflow:** `code/with-review` fits. This is a safety-sensitive launch/config change, and the workflow’s cross-agent rotation is directly relevant because the ticket requires behavior across `claude -> codex -> claude` supervised relaunches.

**Contexts:** `relay/architecture` and `relay/codebase` are relevant. `architecture` is broad, but justified because this touches canonical frontmatter, extension semantics, launch chaining, and local-file state. I would not add `relay/principles`; the relevant facts are already inlined well enough: opt-in, local-only dangerous config, fail loud.

**Main gaps to tighten before launch:**

- Name the field and config key explicitly. Example: canonical optional `skip_permissions: true` on tickets and local `[agents.<name>] skip_permissions_argv = "..."`. Leaving both unnamed invites implementation churn.
- Specify argv placement, not just “append.” The extra flags must be inserted in a CLI-valid position relative to `name_flag`, `auto`, subcommands, and the prompt payload.
- Clarify bootstrap/discussion shims. I’d assume this applies only to normal task tickets, not `relay chat` / `bootstrap/ticket`, unless explicitly opted in.
- Clarify `--agent` override behavior. I’d expect the effective launch agent’s local argv to be required and used.
- Define shape validation: boolean ticket field; local argv as either string parsed with `shlex.split` or `list[str]`, with bad types failing config load.
- Correct/extend the template-copy note: packaged Relay context copies live under `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/...`, not a plain `templates/relay-os/contexts/...` path.

**Scope:** Reasonable, not bundled. It spans config parsing, ticket schema/validation, launch command construction, docs/templates, and tests, but those are all necessary for one coherent feature.

## Implement step — plan (2026-06-10)

Code reading findings:

- `config.py::_parse_agents` reads `[agents]` from shared `relay.toml` only;
  there is no local-override merge today. New plumbing: pass
  `local.get("agents", {})` into the parser and allow partial
  `[agents.<name>]` local tables carrying ONLY `skip_permissions` /
  `skip_permissions_argv`.
- `launch.py` hard-disables `mode: auto` (bails at launch.py:224-236,
  "temporarily disabled" pending streaming). The skip-permissions live path
  is therefore dormant until the streaming ticket re-enables auto; the
  feature is still implementable and testable at the
  `build_agent_command`/policy-helper level.
- `build_agent_command` is also called from `commands/ticket.py` (discussion,
  interactive) — signature change must keep that call site working (keyword
  default).
- Tests: `tests/test_launch.py` has an established `test_build_command_*`
  style to mirror; `tests/test_config.py` for parser coverage.

Planned shape:

- `AgentType` gains `skip_permissions: str = ""` (normalized "" | "auto";
  TOML `false` normalizes to "") and `skip_permissions_argv: tuple[str, ...]`
  (from `shlex.split` of a string).
- Validation at config load: `skip_permissions` accepts only unset/false/
  "auto" (bad value/type → ConfigError); `skip_permissions_argv` must be a
  string (bad type → ConfigError). Local `[agents.<name>]` for an unknown
  agent → ConfigError; keys other than the two skip keys in a local agent
  table → ConfigError (no silent partial-override surface).
- Proposed: REJECT `skip_permissions` / `skip_permissions_argv` in shared
  `relay.toml` agents tables (fail loud) so dangerous argv can't be committed.
- Fail-loud placement for "auto"-without-argv: at LAUNCH time when the policy
  actually applies (auto-mode normal task resolving that agent), per
  acceptance criterion — not at config load, which would break every relay
  command on that machine.
- `build_agent_command(..., skip_permissions_argv=())` inserts after
  name-flag argv, before `agent.auto` argv / prompt. Launch computes
  applicability per step: normal TaskRef (not bootstrap), effective mode
  "auto", current step's effective agent has `skip_permissions == "auto"`.
  First step honors `--agent` override; chained steps use the re-read
  ticket's assignee.
- Docs/templates: README/local-config docs, `example/relay-os/relay.local.toml`,
  template `relay.local.toml` guidance comment, live + packaged
  `relay/architecture` context.

Human decisions (interactive, 2026-06-10):

- Proceed with implementation even though `mode: auto` launches are currently
  hard-disabled in launch.py — cover behavior with unit tests at the
  build_agent_command/policy level; feature goes live when auto re-enables.
- Reject `skip_permissions` / `skip_permissions_argv` in shared `relay.toml`
  `[agents.*]` tables with a loud ConfigError — the keys are local-only.

## Dev

branch: skip-permissions
worktree: /home/n/Code/relay-skip-permissions
pr: https://github.com/FastJVM/relay/pull/336

## Implement step — done (2026-06-10)

Committed on branch `skip-permissions` (b686e96), worktree
/home/n/Code/relay-skip-permissions. No push, no PR (later steps).

What changed:

- `src/relay/config.py` — `AgentType` gains `skip_permissions` ("" | "auto")
  and `skip_permissions_argv` (tuple from `shlex.split`). `_parse_agents` now
  takes the local `[agents]` table: partial local `[agents.<name>]` tables may
  carry ONLY the two skip keys (anything else → ConfigError), unknown local
  agent names → ConfigError, and either skip key in shared relay.toml →
  ConfigError. `skip_permissions` accepts only unset/false/"auto";
  `skip_permissions_argv` must be a string. "auto" with no argv is legal at
  config load (so a half-written local table doesn't brick every relay
  command) — launch is the fail-loud point.
- `src/relay/commands/launch.py` — `build_agent_command` takes
  `skip_permissions_argv`, inserted after name argv and before the
  mode-specific argv/prompt (`claude -n <t> <skip> -p <p>`,
  `codex <skip> exec <p>`). New `_skip_permissions_argv_for_launch(agent,
  mode, ref)` is the policy: returns () unless effective mode == "auto" AND
  ref is a normal TaskRef AND agent.skip_permissions == "auto"; raises
  ConfigError when policy applies but argv is empty. Wired twice: a pre-flight
  right after first-step agent resolution (fails before the in_progress flip
  and Slack broadcast) and per step inside the chain loop using
  `mode_override or ticket.mode` and that step's rotated agent.
- Tests: `tests/test_config.py` (+11) parsing/validation/shared-rejection;
  `tests/test_launch.py` (+10) command construction, policy no-ops
  (interactive/bootstrap/unconfigured), per-step rotation, fail-loud, and an
  integration test that interactive launches ignore the local policy.
- Docs/templates: README launch section, init.py LOCAL_TOML_TEMPLATE,
  example/relay-os/relay.local.toml, live + template relay.toml agents-header
  note, live + packaged `relay/architecture` context (auto-mode bullet).

Verification:

- Full suite: 649 passed (`PYTHONPATH=$PWD/src .relay/.venv python -m pytest`).
- `python -m relay.validate --json` on example fixture: no issues (matches main).
- Flags verified against installed CLIs on this machine: claude exposes
  `--dangerously-skip-permissions`, codex exposes
  `--dangerously-bypass-approvals-and-sandbox` — examples/docs use these.

Notes for self-qa:

- The live applying path is dormant: launch.py still bails on mode=auto
  ("temporarily disabled" pending streaming). Behavior is covered at the
  helper/build_agent_command level; nothing needs to change when auto
  re-enables.
- `--mode interactive` on an auto ticket correctly disables the policy
  (effective mode is what's checked); `--mode auto` is still refused by the
  temporary auto bail.

## Peer review (Codex, 2026-06-10 21:08 PDT)

- Branch/worktree reviewed: `skip-permissions` at
  `/home/n/Code/relay-skip-permissions` (clean worktree).
- Native review command: `codex review --base main`. First sandboxed attempt
  failed before findings with the known read-only app-server initialization
  error; reran escalated and got one P2 finding.
- Finding: auto launches still bail before the new skip-permissions policy is
  reachable through live `relay launch`.
- Disposition: not treated as a must-fix for this step because the implement
  plan records the explicit human decision to proceed while `mode: auto` is
  temporarily disabled and to cover the behavior at helper/command-construction
  level until streaming re-enables auto launches.
- No peer-review code changes; no new commit.
- Verification: `PYTHONPATH=/home/n/Code/relay-skip-permissions/src python -m pytest`
  from the feature worktree: 648 passed, 1 skipped.

## Open-PR step (2026-06-10)

- Pushed `skip-permissions` to origin from the feature worktree (clean tree,
  head b686e96) and opened https://github.com/FastJVM/relay/pull/336.
- `gh pr checks 336`: "no checks reported" — the repo has no CI configured on
  this branch, so there is no green/red signal to wait on.
- PR body notes the dormant auto-launch path and the recorded human decision,
  links the ticket, and carries the test plan.
