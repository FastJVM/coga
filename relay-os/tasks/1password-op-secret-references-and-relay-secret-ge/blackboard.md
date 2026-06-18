The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: op-secret-references
worktree: ../relay-op-secrets
pr: https://github.com/FastJVM/relay/pull/396

## Plan (implement step)

Matches the ticket's pinned "Proposed Shape". No second resolver — CLI and launch
share `select_launch_secrets`.

1. **`SecretValue`** gains `op_ref: str | None = None`. `_resolve_secrets` adds an
   `op://` prefix branch that stores the reference **without** resolving it
   (`value=None`, `op_ref=value`). No subprocess at config-load time, so loading
   config never prompts 1Password. `env:`/literal provenance unchanged.
2. **`select_launch_secrets`**:
   - blanket (`declared is None`): unchanged — keeps `value is not None`, so
     `op://` (value None at load) is naturally skipped → legacy blanket never
     prompts op.
   - least-privilege (explicit list): for an `op://` key, resolve live via
     `op read <ref>` (`subprocess.run(..., check=False)`), strip exactly one
     trailing newline, raise `SecretError` (naming key + ref, never the value) on
     missing `op` binary or non-zero exit.
3. **Fail-loud**: both `launch.py` and `launch_script.py` already catch
   `SecretError` from `build_launch_env` and `_bail` before spawning → op
   failures fail loud for free.
4. **`relay secret get <key>`**: new thin `commands/secret.py`, Typer group
   registered in `cli.py` + added to `_BUILTIN_COMMANDS`. Calls
   `select_launch_secrets(cfg, [key])`, echoes the value, never logs/posts it.
5. **`validate`**: no change to live behavior — an `op://` secret is neither
   undeclared nor env-unset (`missing` is env-only), so `_check_secrets`
   emits nothing and never shells out to `op`. Add a clarifying comment.

### Tests (mirror tests/test_config.py + test_launch.py style; mock subprocess.run)
- config: `op://` value loads with op_ref set, value None, missing False.
- blanket mode does NOT resolve op (no subprocess called).
- least-privilege resolves op via mocked `op read` (strips trailing newline).
- missing `op` binary (FileNotFoundError) → SecretError naming key+ref.
- non-zero `op read` → SecretError naming key+ref, not value.
- `relay secret get` success + failure (via CliRunner).
- launch fails loud before spawn when op read fails.

## Status: implement done — ready for bump

Implemented exactly the pinned shape:
- `config.py`: `SecretValue.op_ref`; `_resolve_secrets` op:// branch (deferred,
  no subprocess at load); `_resolve_op_reference(key, ref)` runs `op read`,
  strips one trailing newline, raises `SecretError` naming key+ref (never value)
  on missing binary / non-zero; `select_launch_secrets` resolves op only in the
  explicit-list branch (blanket skips via `value is None`).
- `commands/secret.py` + `cli.py`: `relay secret get <key>` reuses
  `select_launch_secrets(cfg, [key])` — no second resolver.
- `validate.py`: doc-only clarification; op secrets emit no issue, no live op.
- Docs: added `relay secret get` section to bootstrap `relay/cli` context
  (force-added; tracked template path).

Tests: 161 targeted pass; new config/launch/secret coverage for all acceptance
cases. `relay validate --json` on example fixture: ok, 0 errors.

### Pre-existing failures (NOT mine — confirmed on base commit c027263)
`tests/test_autoclose_sweep.py::test_autoclose_live_and_packaged_copies_stay_in_sync`
and `::test_autoclose_recurring_template_creates_idempotently` fail because they
hardcode `last_serviced_period: 2026-06-11` but today is 2026-06-17. Date-driven,
unrelated to secrets. Left untouched per implement-skill scope.

### Note on test mocking
`relay.config` and `relay.commands.launch` share one `subprocess` module object,
so patching both `.subprocess.run` collides — launch tests use a single
argv-dispatching mock on `relay.config.subprocess.run`.

## Peer review (codex)

Reviewed from feature worktree `/home/n/Code/claude/relay-op-secrets` on branch
`op-secret-references` against `main`.

- Required native review: `codex review --base main`. First sandboxed attempt
  failed before review with `failed to initialize in-process app-server client:
  Read-only file system`; reran outside the sandbox and it completed with: "No
  diff-scoped correctness issues were found in the new op:// secret resolution,
  launch integration, or `relay secret get` command."
- Must-fix findings: none. No code changes and no peer-review commit needed.
- Verification: `python -m pytest` in the feature worktree reported `2 failed,
  792 passed, 1 skipped`. The two failures are the already-recorded unrelated
  autoclose date/template-state failures:
  `tests/test_autoclose_sweep.py::test_autoclose_live_and_packaged_copies_stay_in_sync`
  and
  `tests/test_autoclose_sweep.py::test_autoclose_recurring_template_creates_idempotently`.

## Retro

status: processed
skill: retro/done-ticket
result: knowledge-pr
title: Refresh relay/cli context (relay build, validate --check-github)
