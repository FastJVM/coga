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
only the source variables a ticket's `env:VAR` references name. It never removes
`OP_SERVICE_ACCOUNT_TOKEN`, and no later call site does either. A launched agent
or recipe can therefore run `op read` against the whole automation vault even
when its ticket declares one secret — or none.

That contradicts what `coga/architecture` and `coga/secrets` say a ticket's
`secrets:` list means. Make the declaration real for the service-account path:
Coga resolves the ticket's declared `op://` refs using the token, then removes
the raw token before spawning the child, so the child sees only the resolved
destination aliases.

Settled in `service-account-scoping-single-vault-rule-conflict` (decision 2,
2026-09-08) and deliberately split out of it, because that ticket is a doc
decision and this is a code change with real blast radius.

## Context

**Where the behavior lives.** `build_launch_env()` at `src/coga/config.py:1509`.
Its body is five lines: copy `os.environ`, `env.pop()` each `env:`-referenced
source, `env.update(select_launch_secrets(...))`. The scrub loop only knows
about names a ticket wrote down, which is why the token survives. Confirm no
call site compensates — check the `coga launch` spawn path, megalaunch, and the
recurring recipe runner.

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
the service-account path only. Say so in the docs rather than claiming
confinement Coga does not have — `coga/architecture`'s "This is a declaration,
not a sandbox" paragraph is the wording to update, and it has a packaged twin at
`src/coga/resources/templates/coga/contexts/coga/architecture/SKILL.md` that
must stay in sync. `coga/contexts/coga/secrets/SKILL.md` is repo-local with no
twin.

**The open design question this ticket has to answer.** Nested Coga commands run
inside a launched session — `coga slack`, `coga bump`, notification posts — may
themselves need credentials that today resolve through the inherited token. If
the child no longer has it, decide explicitly: do those paths resolve their
secrets in the parent before spawn, re-resolve through a narrower mechanism, or
does the notification webhook's `env:` indirection already cover every case?
Answer this before writing the scrub, because getting it wrong takes Slack dark
from inside every launched session.

**Out of scope.** Vault-to-token routing, per-reference credential selection,
and process isolation. The repo runs one service account against one automation
vault; this ticket does not change that model.

**Verify like the docs tell operators to.** A clean environment where
`OP_SERVICE_ACCOUNT_TOKEN` is the only credential — a personal `op` login reads
everything and gives a false pass. A test proving a child with no declared
secrets cannot `op read` the automation vault is the acceptance signal.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
