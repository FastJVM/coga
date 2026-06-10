The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap notes

- Human clarified intent: add a Relay option so Claude Code and Codex can be launched with their permission/approval prompts bypassed, but only when a specific ticket opts into that behavior.
- Local CLI help checked on 2026-06-09:
  - `codex --help` exposes `--dangerously-bypass-approvals-and-sandbox` and `--ask-for-approval never`.
  - `claude --help` exposes `--dangerously-skip-permissions`, `--allow-dangerously-skip-permissions`, and `--permission-mode bypassPermissions`.
- Proposed ticket shape: keep dangerous argv in local config, add a per-ticket frontmatter opt-in, and have `relay launch` append the configured argv only for opted-in interactive/auto agent launches.
- Narrow contexts to attach: `relay/architecture` for canonical frontmatter/config semantics and `relay/codebase` for source layout/tests.

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
