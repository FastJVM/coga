---
title: Pass secrets to skills with per-skill scope
status: draft
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: claude1
contexts: []
skills:
- bootstrap/ticket
workflow: null
---

## Description

Today every secret in `relay.local.toml` `[secrets]` gets bulk-injected
as env vars into every launch — agent (`src/relay/commands/launch.py:217`)
and script (`src/relay/commands/launch_script.py:63`). A skill that only
needs Brex sees the GitHub token, the Stripe key, and everything else.

We want a way to declare which secrets a skill needs and inject only
those. Brex skill gets Brex creds; GitHub PR-review skill gets the
GitHub token; nothing else leaks.

## Open questions

- **Where is the scope declared?** Skill frontmatter (`secrets:
  [brex_token]`) is the obvious spot — co-located with the skill that
  needs them, fails loud if the secret isn't in `relay.local.toml`.
  Alternative: workflow step config. Skill-level feels right because
  the skill is the unit that knows what it calls.
- **Agent-mode vs script-mode.** Script mode is the easy case —
  the runner reads the skill, sees `secrets: [...]`, builds a scoped
  env. Agent mode is harder: the agent process is general-purpose and
  may invoke many tools across the session. Options:
  - Inject the union of all step-skill secrets at launch (still
    coarser than script mode but narrower than today).
  - Run a secrets broker the agent calls per-tool — overkill for v1.
- **Composition with ticket contexts.** Contexts don't currently
  declare secrets. If a context implies needing creds (e.g. a
  Brex domain context), do we let contexts declare too, or keep it
  skill-only? Skill-only is cleaner.
- **Failure mode.** Missing required secret → loud failure at
  launch time, before the agent or script starts. Matches relay's
  fail-loud principle.

## Context

- `src/relay/config.py:262` — `_resolve_secrets` reads
  `[secrets]` and resolves `env:VAR` refs.
- `src/relay/commands/launch.py:217` — bulk-injects all secrets into
  the agent process env.
- `src/relay/commands/launch_script.py:63` — same for script mode.
- `docs/spec.md:110-115` — current `[secrets]` example.
- Today's contract is "skills see every secret"; this ticket changes
  that to "skills see only what they declare."
