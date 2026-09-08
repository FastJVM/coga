---
slug: scrub-the-service-account-token-from-the-launch-ch
title: Scrub the service-account token from the launch child environment
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/secrets
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

`config.build_launch_env()` starts from the full parent environment and removes
only the source variables a ticket's `env:VAR` references name. Unless a ticket
happens to name `OP_SERVICE_ACCOUNT_TOKEN` as an `env:` source, the token is
inherited by the child, and no call site removes it afterwards. A launched
agent, `ticket.py` phase, or recipe can therefore run `op read` against the
whole automation vault even when its ticket declares one secret — or none.

That contradicts what `coga/architecture` and `coga/secrets` say a ticket's
`secrets:` list means. Make the declaration real for the service-account path:
Coga resolves the ticket's declared `op://` refs using the token, then removes
the inherited token before spawning the child.

Settled in `service-account-scoping-single-vault-rule-conflict` (decision 2,
2026-09-08) and deliberately split out of it, because that ticket is a doc
decision and this is a code change with real blast radius.

## Context

**Where the behavior lives.** `build_launch_env()` at `src/coga/config.py:1509`.
Its body is five lines: copy `os.environ`, `env.pop()` each `env:`-referenced
source, `env.update(select_launch_secrets(...))`. The scrub loop only knows
about names a ticket wrote down, which is why the token survives.

Note the signature takes `base_env: Mapping[str, str] | None = None` and only
falls back to `os.environ` when it is `None` (`config.py:1522`). The scrub must
apply to whatever env is actually in use, not to `os.environ` specifically.

**Every call site** (verified 2026-09-08 — all pass through this one function,
so a fix inside it covers them all; confirm none re-adds the token afterwards):

- `src/coga/commands/launch.py:1326, 1356, 1619, 1835`
- `src/coga/megalaunch.py:2051`
- `src/coga/launch_script.py:134, 267` — the headless `ticket.py` path. Easy to
  miss and just as exposed as the agent path.

**Scope the claim honestly.** `build_launch_env` copies the entire parent
environment; this ticket removes one variable from it. Do **not** read this as a
mandate to build an allowlist environment — the child still inherits everything
else, and `coga/architecture` deliberately says the declaration is not a
sandbox. The goal is narrower: the service-account token specifically stops
being ambient.

**The destination-alias subtlety is already documented and must not regress.**
Per `coga/secrets`, the *final alias set* decides the outcome:
`TASK_OP_TOKEN: env:OP_SERVICE_ACCOUNT_TOKEN` removes the well-known name and
prevents auto-authentication, while declaring `OP_SERVICE_ACCOUNT_TOKEN` as a
destination restores or replaces it. A ticket that deliberately declares the
well-known name as a destination is asking for the token and must keep getting
it. Scrub the *inherited* value, not a declared one.

**Removing the token is not a logout.** An inherited personal `op` session,
desktop-app integration, or other ambient credential can still authenticate the
child and may carry broader access than the service account. This change bounds
the service-account path only.

**Docs to update** (not attached as contexts — read them from disk; attaching
`coga/architecture` in full would dominate the composed prompt for one
paragraph):

- `coga/contexts/coga/architecture/SKILL.md` — the "This is a declaration, not
  a sandbox" paragraph under *Identity and capability boundaries*. Its packaged
  twin is `src/coga/resources/templates/coga/**bootstrap**/contexts/coga/architecture/SKILL.md`
  (note the `bootstrap/` segment) and must stay in sync.
- `coga/contexts/coga/secrets/SKILL.md` — repo-local, **no** packaged twin. Its
  "Scoping bounds the grant, not the process" section states the current
  inherit-the-token behavior explicitly and has to change with the code.

**The open design question — answer it before writing the scrub.** Which nested
in-session paths actually need the token once the child no longer inherits it?

Known candidates: `coga secret get` (`src/coga/commands/secret.py`), invoked by
agents and by `ticket.py` phases, and any `op://` ref a headless script resolves
at runtime. Slack is **not** a candidate: per `coga/secrets` only
`[notification.slack].webhook` and `important_webhook` resolve `env:` refs,
`op://` is not understood in config at all, and those resolve from
`SLACK_WEBHOOK_URL` — an ordinary env var this change does not touch.

If the answer is "the known candidates need a narrower mechanism", that is an
architecture call, not an implementation detail. Record the answer on the
blackboard; if it turns out to need a real design decision rather than a
verification, stop and raise it with the owner instead of settling it inside
the `implement` step.

**Out of scope.** Vault-to-token routing, per-reference credential selection,
allowlist environments, and process isolation. The repo runs one service
account against one automation vault; this ticket does not change that model.

**Verification — two halves, don't conflate them.**

- *Automated (CI-safe):* call `build_launch_env` with an injected `base_env`
  containing a fake `OP_SERVICE_ACCOUNT_TOKEN` and assert it is absent from the
  result, plus the regression case where a ticket declares that name as a
  destination and it survives. No real credential needed.
- *Manual:* in a clean environment where a real `OP_SERVICE_ACCOUNT_TOKEN` is
  the only credential, confirm a launched child with no declared secrets cannot
  `op read` the automation vault. A personal `op` login reads everything and
  gives a false pass, so this cannot run in CI.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
