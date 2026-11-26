---
title: Restore coga-init contracts and a delete topic that siblings cite
status: blocked
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: open-branch
    skills: []
    assignee: agent
    requires: branch
    run: git/open-branch
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: push-and-open-pr
    skills: []
    assignee: agent
    requires: pr
    run: git/push-and-open-pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 3 (peer-review)
agent: claude
---

## Description

Filed by Dream recurring/dream, period 2026-W48 (run 20261125T175534Z), Phase 6 disposition of Phase 2/3 findings.

Two shipped contexts are cited as the owner of contracts they no longer hold.
- G49 (ks-11): src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md no longer states the agent-CLI requirement, the [agents.*] comment-out, the user key, or the [layout] contexts contract. These pages still delegate those contracts to coga/init: docs/contexts/coga-dev/current-direction l.149, docs/contexts/coga-dev/internals/agent-config l.63, src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration l.110, src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout l.136, src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task l.69, and src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/package-definitions-migration.md ('linked from init').
- G8 (ks-05): src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md l.35 routes coga delete to a topic that says nothing about delete.

Decision needed (where each contract lives, per coga/knowledge): restore them in coga/init, or repoint each citer to the actual owner. Add a short 'Deleting a task' paragraph where delete belongs, for example coga/tickets or coga/tickets/discovery, and route the cli row there. Acceptance: every citer resolves to text that states the contract, and tests/test_packaging.py passes.

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: open-branch
          run: git/open-branch               # Local-first skill directory containing run.py.
          assignee: agent
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (open-branch)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
A workflow run: selects a script for its step. A sibling ticket.py supplies the default script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

The recurring runner writes delegate on materialized period tickets. It
names the parent template's frozen bootstrap/<name> target.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev records branch:, base:, remote:, reviewed: (the commit OID),
and pr: (the full /pull/ URL). Write one field per line and omit unknown
values. coga/git owns the fields and the workflow that writes them.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->
## Dev

branch: coga/restore-coga-init-contracts-and-a-delete-topic-t-bb5902
base: coga/decide-whether-coga-retire-runs-retro-on-cancele-a1e2ec
remote: origin
reviewed: b4205a08f3f5254f6e26a1f9db7ef3c1f1a6c704

## Review notes

- `coga/init` owns the fresh and clone init contracts. Checked the scan, table
  rewrite, local identity and contexts relocation against `commands/init.py`,
  `config.py` and agent launch preflight. The docs describe the current
  standalone init and its failure remedies.
- `coga/tickets/discovery` owns deletion. The top-level command and registered
  recipe use the same helper. Corrected the delete and Retro skills to point
  at the local deletion contract and record publication as a separate Git step.
- Checked all six init citers, the reciprocal layout and migration links, and
  the delete links. Fourteen links resolve to the intended files and headings.
- An exploratory Python 3.11 suite run exposed a pre-existing failure in
  `test_layout_context_artifact_symlink_rejected`. Python 3.11.15 omits the
  dangling `SKILL.md` from `Path.rglob`, while Python 3.12.12 enumerates it.
  The config code and test match the recorded base. An earlier Python 3.12
  full run reproduced the documented POSIX supervisor timing failure. Its
  isolated rerun on the final head passed.
- After `git fetch origin`, the recorded base was the local commit
  `ecde357318bf3b5e9bf9633e3d35e705f21737a8` on
  `coga/decide-whether-coga-retire-runs-retro-on-cancele-a1e2ec`. `git ls-remote`
  confirmed no remote branch with that name. Its task
  `decide-whether-coga-retire-runs-retro-on-canceled` is blocked. The publisher
  requires a remote base and also refuses the five unrelated unstaged ticket
  edits in this checkout. Those edits are preserved.

## PR

```yaml
title: Restore coga-init contracts and a delete topic that siblings cite
author: claude
author_evidence: >-
  The implementation session ran on Claude Opus 5.5 (claude-opus-5-5).
  Codex authored the documentation and assertion corrections during peer review.
head: b4205a08f3f5254f6e26a1f9db7ef3c1f1a6c704
base: ecde357318bf3b5e9bf9633e3d35e705f21737a8
depth: skim
rationale: >-
  The change restores documentation contracts and updates one content
  assertion. Peer review checked the contracts against the implementation
  and followed each citation.
implementation: >-
  coga/init owns the agent CLI scan, agent table selection, missing CLI remedy,
  local identity and contexts relocation, and links the migration procedure.
  The CLI index routes delete to coga/tickets/discovery, which documents both
  entry points and their local working-tree effects.
deviations: >-
  Peer review updated the agent configuration summary and the delete and
  Retro skills to align with the owning topics. It refreshed the existing
  Retro content assertion to check the reference-pin PR rule directly.
limitations: >-
  Native Windows and macOS verification is deferred to release. The full Linux
  suite was run on Python 3.12.12. A baseline Python 3.11 issue with discovering
  dangling context symlinks is recorded in the review notes.
files:
  docs/contexts/coga-dev/internals/agent-config/SKILL.md: "Point to the agent scan contract in coga/init."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: "Route delete to the new section."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: "Restore agent CLI, user, contexts-root and migration guidance."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md: "Mention coga delete in the discovery leaf."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/discovery/SKILL.md: "Describe local deletion and Git recovery."
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/delete-task/SKILL.md: "Use the canonical delete topic for command semantics."
  src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md: "Distinguish local deletion from the enclosing Git publication step."
  tests/test_retro_skill_template.py: "Keep the content check for the reference-pin PR route."
review:
  reviewer: codex
  kind: independent
  status: passed
  head: b4205a08f3f5254f6e26a1f9db7ef3c1f1a6c704
  base: ecde357318bf3b5e9bf9633e3d35e705f21737a8
  detail: >-
    Codex reviewed the full diff against the recorded ticket base and checked
    init and both delete entry points against their code and callers. Codex
    did not participate in implementation and reviewed its own peer-review
    corrections. The focused and full Linux runs passed on the final head.
    No in-scope findings remain.
checks:
  - command: >-
      TMPDIR="$review_tmp" PYTHONPATH="$PWD/src" TERM=dumb PIP_DISABLE_PIP_VERSION_CHECK=1
      .venv/peer-review.wT1qVC/venv/bin/python -m pytest -q tests/test_packaging.py
      tests/test_layout_contexts.py tests/test_retro_skill_template.py --basetemp="$review_tmp/pytest"
    status: passed
    head: b4205a08f3f5254f6e26a1f9db7ef3c1f1a6c704
    base: ecde357318bf3b5e9bf9633e3d35e705f21737a8
    detail: "Pop!_OS 24.04 LTS (Linux), Python 3.11.15. 73 passed in 12.69s."
  - command: >-
      TMPDIR="$review_tmp" PYTHONPATH="$PWD/src" TERM=dumb PIP_DISABLE_PIP_VERSION_CHECK=1
      .venv/bin/python -m pytest -q --basetemp="$review_tmp/pytest"
    status: passed
    head: b4205a08f3f5254f6e26a1f9db7ef3c1f1a6c704
    base: ecde357318bf3b5e9bf9633e3d35e705f21737a8
    detail: "Pop!_OS 24.04 LTS (Linux), Python 3.12.12. 3258 passed, 30 skipped in 180.93s."
```

---

## Blockers

- [ ] [2026-11-25 18:30] [agent:codex] id=20261125T183024 Resolve decide-whether-coga-retire-runs-retro-on-canceled so the recorded PR base is available on origin, or approve retargeting this change. Reconcile the five unrelated unstaged ticket edits before publication.
