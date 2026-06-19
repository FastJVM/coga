---
title: 1Password op secret references and relay secret get
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/principles
- relay/architecture
- relay/codebase
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

Fast-follow after PR #382 ("Scope secret injection to declared per-task
secrets and fail loud on missing"). Relay now has ticket-level `secrets:`,
`SecretValue`, `select_launch_secrets`, and scoped launch env construction.
This ticket adds a 1Password-backed secret reference plus a human-facing query
command on top of that shared path.

Supported new reference shape:

```toml
[secrets]
stripe_key = "op://vault/item/field"
```

Relay passes the 1Password secret-reference URI verbatim to `op read`; it does
not parse vault/item/field, manage 1Password items, rotate secrets, or add a
generic provider registry.

## Acceptance Criteria

- [ ] `[secrets]` accepts `op://vault/item/field` values alongside literals and
  `env:VAR`.
- [ ] `op://` resolution reuses the shared secret-selection path used by
  launch. Do not add a second resolver only for the CLI command.
- [ ] `op://` secrets are resolved on demand: when an explicit ticket
  `secrets:` list selects the key, or when a human runs
  `relay secret get <key>`.
- [ ] Legacy absent/null `secrets:` blanket injection does not unexpectedly
  prompt 1Password for every configured `op://` value. Tasks that need an
  `op://` secret should declare that key explicitly.
- [ ] A declared `op://` secret fails loud before spawning an agent/script when
  `op` is missing, the user is not signed in, or `op read` returns non-zero.
  Error messages name the Relay secret key and reference, never the resolved
  secret value.
- [ ] Add `relay secret get <key>` as a thin Typer group/command registered in
  `src/relay/cli.py`. It loads config, resolves exactly that `[secrets]` key
  through the shared helper, prints the value only because the human explicitly
  requested it, and never logs/posts the value.
- [ ] `relay validate` does not require a real 1Password account. If it checks
  shape, it should validate the prefix/reference form only; live `op read`
  belongs to explicit launch or `relay secret get`.
- [ ] Tests mock `subprocess.run`; no test requires a real `op` binary or
  1Password account. Cover missing binary, unauthenticated/non-zero `op read`,
  successful launch selection, `relay secret get`, and "do not resolve op in
  legacy blanket mode."
- [ ] No provider registry, non-1Password provider, hosted secret broker,
  secret creation, or rotation behavior is introduced.

## Proposed Shape

- Extend `SecretValue` or add a tiny helper it calls so `_resolve_secrets`
  preserves `op://` provenance without flattening it at config-load time.
  Current `env:` provenance must keep working.
- Put prefix dispatch in the existing config/secret path. `env:` and `op://`
  are explicit branches; literals pass through.
- Resolve `op://` by running `subprocess.run(["op", "read", ref], ...)` with
  captured output and `check=False`. Strip only the trailing newline 1Password
  prints; do not otherwise transform the secret.
- Keep `src/relay/commands/secret.py` thin. The reusable behavior belongs in
  config/secret helpers so launch and the CLI command cannot diverge.


## Context

Split from `authentication-system` during review. The earlier
`add-a-way-to-query-a-declared-secret-on-demand` concept draft was deleted; this
is the replacement ticket with the shape pinned after the fail-loud secrets
base landed on `main`.

Dependency state on 2026-06-17: PR #382 is merged on `main`, and this checkout
contains `SecretValue`, `select_launch_secrets`, `build_launch_env`,
`validate._check_secrets`, and `secrets: null` in both task templates.
