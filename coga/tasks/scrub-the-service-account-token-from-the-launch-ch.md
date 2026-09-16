---
title: Scrub the service-account token from the launch child environment
status: blocked
owner: nicktoper
agent: claude
contexts:
- coga/secrets
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
step: 2 (peer-review)
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
  twin is at
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md`
  — note the `bootstrap/` segment, which is easy to drop — and must stay in sync.
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

## Dev

branch: scrub-sa-token
worktree: /home/n/Code/claude/coga-scrub-sa-token

## Design question — answered (verification, not a design decision)

Which nested in-session paths need the token once the child no longer inherits
it? **None.** Evidence (2026-09-15):

- The only in-package `op://` resolver is `config.select_launch_secrets`. Its
  callers are `config.build_launch_env` and `commands/secret.py` (`coga secret
  get`). Nothing else in `src/coga/` shells out to `op`.
- Every `build_launch_env` call runs in the *parent* (`commands/launch.py`
  ×4, `megalaunch.py`, `launch_script.py` ×2), which keeps its own
  `os.environ`. Megalaunch and the REPL supervisor spawn the agent directly
  with the built env (`megalaunch._PreparedAgentLaunch.env`,
  `repl_supervisor` `subprocess.run(cmd, env=...)`), not a nested `coga
  launch`, so no second resolution ever happens from a scrubbed env. The
  supervisor's per-step re-mint (`launch.py`, the `build_launch_env` before
  the step spawn) also runs in the parent.
- `coga secret get` is defined by the `coga/cli` context as "a human-facing
  query, not something agents call". Inside a child it now fails without
  another `op` session — that is the scoping working, not a regression.
- No recurring `ticket.py` (`coga/recurring/*/ticket.py`) or recipe touches
  `op` or `OP_SERVICE_ACCOUNT_TOKEN`.
- Slack: unaffected, as the ticket already notes (`SLACK_WEBHOOK_URL` env
  ref, not `op://`).

So no narrower mechanism is needed; the scrub lives entirely inside
`build_launch_env`.

## What changed

- `src/coga/config.py`: new `SERVICE_ACCOUNT_TOKEN_VAR` constant;
  `build_launch_env` now resolves declared secrets *first* (parent still holds
  the token for `op read`), then `env.pop(OP_SERVICE_ACCOUNT_TOKEN)`, then
  `env.update(resolved)`. Because `update` runs after the pop, a ticket
  declaring `OP_SERVICE_ACCOUNT_TOKEN` as a destination alias still gets it
  (inherited value scrubbed, declared value kept). Applies to whatever
  `base_env` is in use, not only `os.environ`.
- `tests/test_config.py`: six `build_launch_env` tests — no-secrets scrub with
  injected `base_env`; scrub after `op://` resolution (fake `op read`); the
  `os.environ` default path (parent env untouched); token declared as
  destination survives; `OP_SERVICE_ACCOUNT_TOKEN: env:OTHER_TOKEN` replaces;
  `TASK_OP_TOKEN: env:OP_SERVICE_ACCOUNT_TOKEN` stays scrubbed. Three of them
  fail on the old code (checked via stash).
- Docs: `coga/contexts/coga/architecture/SKILL.md` "declaration, not a
  sandbox" paragraph + packaged twin under `bootstrap/` (byte-identical);
  `coga/contexts/coga/secrets/SKILL.md` "Scoping bounds the grant" section and
  the following `op` auto-auth paragraph (now also names the `coga secret get`
  in-child consequence).

## Verification

- Full suite in the feature worktree: `python -m pytest` → 2501 passed
  (`.venv/bin/python` 3.12; miniconda default is 3.9 and refuses to import
  coga — use the repo venv).
- `tests/test_packaging.py` passes (twins in sync).
- Manual half (clean env, real `OP_SERVICE_ACCOUNT_TOKEN` only, launched child
  with no declared secrets cannot `op read`) **not run** here — needs a real
  token and a shell without a personal `op` session; left for the owner /
  review step.

## Decisions

- Scrub placed inside `build_launch_env` rather than at call sites: one
  function, seven callers, and the ticket's own audit says none re-adds the
  variable (re-confirmed: `apply_task_env` / `build_supervised_step_env` only
  add `COGA_*` keys).
- Kept the "not a logout" caveat prominent in both docs; the change bounds the
  SA path only.

---

## Peer review

2026-09-15: `codex review --base main` **returned**, exit 0, from the recorded
feature worktree. Result: **no actionable regressions**; the reviewer reported
519 targeted tests passing. Its subprocess check used a fake `op` executable
and fake token to confirm parent-side resolution, rejection in the scrubbed
child, and success with an explicit token destination. No must-fix findings,
so no follow-up code commit was needed. No terminal, pager, prompt, or rendered
notification surface changed.

Independently re-audited all seven builder callers and subsequent environment
updates: none re-adds the token. The nested `coga secret get` consequence agrees
with the packaged CLI context's human-facing-query contract; no recurring
`ticket.py` or recipe needs ambient service-account authentication.

Ran `git fetch origin main` then `git rebase FETCH_HEAD` in the feature
worktree. Rebase was clean onto `e1b2fefa`; branch HEAD is now `cc222a6f`, one
commit ahead. All five implementation/docs/test files are unchanged from the
reviewed `ce3b270c`. `git diff --check origin/main...HEAD` and the architecture
live/packaged `cmp` passed. The feature worktree is clean and committed.

Full verification from the feature worktree:
`PYTHONPATH=/home/n/Code/claude/coga-scrub-sa-token/src /home/n/Code/claude/coga/.venv/bin/python -m pytest`
returned **2501 passed in 185.89s**, including packaging/twin checks.

`PYTHONPATH=/home/n/Code/claude/coga-scrub-sa-token/src
/home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --task
scrub-the-service-account-token-from-the-launch-ch --json` from the primary
checkout returned `ok_count: 1`, no issues.

**Manual check remains required.** `op` is installed, but this session has no
`OP_SERVICE_ACCOUNT_TOKEN` (presence checked without reading/logging a value).
No real-credential check was run. The owner must verify on this branch, with
personal/desktop authentication absent and a real SA token as the only parent
credential, that the parent can read a known automation-vault ref and a child
launched with no declared secrets cannot read that same ref. Record outcomes,
not token or secret values. Fake-token tests do not satisfy this check.

The pending live verification is the only remaining blocker. On resolution,
record its outcome here, update the PR test-plan line below, refresh/rebase and
retest against current `main`, then bump once from the primary checkout. This
session stops with `coga block`, leaving the task at peer-review.


---

## PR

Launches inherit `OP_SERVICE_ACCOUNT_TOKEN` even when a ticket declares no
secrets. Resolve declared references in the parent, remove the inherited token
from child environments, then add resolved aliases so explicitly declared
token destinations still work. Other inherited credentials remain outside
this service-account-specific boundary.

Update the architecture and secrets contexts, keep the packaged architecture
twin identical, and add regressions for injected/default environments and token
alias behavior.

Test plan: `PYTHONPATH=/home/n/Code/claude/coga-scrub-sa-token/src /home/n/Code/claude/coga/.venv/bin/python -m pytest` — 2501 passed; task-scoped validation — no issues; `codex review --base main` returned no actionable findings. Required live 1Password service-account-only check remains pending and blocks peer-review completion.

---

## Blockers

- [ ] [2026-09-15 22:00] [agent:codex] id=20260915T220015 Run and record the required live 1Password check on branch scrub-sa-token (cc222a6f): with a real OP_SERVICE_ACCOUNT_TOKEN as the only credential and no personal or desktop authentication, the parent can read a known automation-vault ref and a launched child with no declared secrets cannot read that same ref. This session has no token. Native review returned no actionable findings and all 2501 tests passed; the PR body is prepared.

---

## Blocker reminders

- 292ad8b9a72a last_reminded: 2026-09-16 10:58
