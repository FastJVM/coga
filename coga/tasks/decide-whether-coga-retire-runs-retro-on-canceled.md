---
title: Decide whether coga retire runs Retro on canceled tickets
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

Docs and code disagree about retiring a canceled ticket. These docs say coga retire runs Retro (retro/done-ticket) on a canceled ticket and extracts its negative learning:
- G7 (ks-04): src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md l.3/78/161/222/438/462, and the src/coga/resources/templates/coga/bootstrap/retire/ticket.py docstring l.1/48-56.
- G17 (ks-04): src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/knowledge-scan/SKILL.md l.156 (source: canceled bullet).
- G34 (ks-04): src/coga/resources/templates/coga/recurring/dream/ticket.md l.289-290 and l.630-632. Phase 6 opens no PR for a source: canceled extract because retirement runs Retro on it.

The code does not do that: src/coga/resources/retire.md is a generic review prompt that ends in coga delete. It never delegates to retro/done-ticket.

Decision needed: restore Retro delegation for canceled tickets, or reword all three surfaces. If you reword, Dream's no-PR rule for source: canceled extract findings loses its rationale. Those findings would then have no route other than this run summary, so decide their route as well. Related parked redesign: _v2/add-a-failed-terminal-status. Its owner decision of 2026-10-14 gives canceled no agent and failed a Retro.

This run had three canceled extract findings that depend on the answer: close-the-presence-not-freshness-hole-in-the-branc, retire-canceled-tickets-without-retro, and marketing/fix-installer/add-gemini-as-an-agent-coga-can-drive.

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

branch: coga/decide-whether-coga-retire-runs-retro-on-cancele-a1e2ec
base: coga/correct-migration-claims-the-fix-stale-branch-s--4128cc
remote: origin
reviewed: ecde357318bf3b5e9bf9633e3d35e705f21737a8


## Decision (implement, 2026-11-25)

**Reword; do not restore Retro delegation.** Evidence:
- `git log -- src/coga/resources/retire.md`: 91c688048 ("Checkpoint plain Git
  workflow migration", owner commit 2026-11-21) deliberately replaced the
  Retro-launcher `retire.md` (added by 9bfb0adf5 / #1014) with the generic
  review prompt. The shipped `bootstrap/retire/ticket.md` help already says
  "creates a follow-up task to review what should be carried forward".
- Owner decision 2026-10-14 (`_v2/add-a-failed-terminal-status`, and the
  canceled `retire-canceled-tickets-without-retro`): canceled gets no Retro;
  only a future `failed` status would.

**Dream lists `source: canceled` extracts as retirement debt.** The
`retire.md` task receives the source slug and asks the agent to carry forward
durable knowledge or file follow-ups before deleting the ticket. The Dream
summary gives the operator the slug, area, and finding for prioritization.
The three findings from run `20261125T175534Z` stay on that route:
`close-the-presence-not-freshness-hole-in-the-branc`,
`retire-canceled-tickets-without-retro`, and
`marketing/fix-installer/add-gemini-as-an-agent-coga-can-drive`.

Note for `_v2/add-a-failed-terminal-status` (owner gate, not edited here): its
Proposed shape step 5 assumes `retire.md` is still the Retro launcher
("canceled" → "failed" throughout). After the plain-Git migration it is a
generic review prompt, so implementing `failed` → Retro needs a new Retro
launcher prompt (see 91c688048^:src/coga/resources/retire.md), and Retro's
`### Canceled tickets` section would become `### Failed tickets`.

## Publication dependency

The recorded base belongs to blocked task
`correct-migration-claims-the-fix-stale-branch-s-fi`. `git fetch origin` and
`git ls-remote` confirmed that its branch has no corresponding remote ref.
It contains eight commits beyond `origin/main` from three other tickets.
All seven changed paths match `origin/main` at the recorded base, so the
retirement commits can be retargeted to `main` for an independent PR. A base
change needs a fresh review receipt. The current checkout also holds four
unrelated, unstaged ticket edits which must be reconciled before the PR
script can run.

## PR

```yaml
title: Document canceled-ticket retirement and Dream routing
author: claude
author_evidence: >-
  Claude (claude-opus-5-5) wrote the implementation in launch 3c215166.
  Codex made the follow-up corrections in an independent peer-review session.
head: ecde357318bf3b5e9bf9633e3d35e705f21737a8
base: e649a9ce3b02dcc5dc67b14b7fbb2428a03c1ee3
depth: skim
rationale: >-
  The change brings shipped instructions in line with the retire command.
  The full Linux test suite and review of the canceled-ticket route passed.
implementation: >-
  Canceled-ticket retirement creates a review task from retire.md. Dream
  lists canceled-ticket extracts as retirement debt and leaves the source for
  the review task. Retro accepts eligible done tickets.
deviations: >-
  Corrected the same stale claim in extension-model and the adjacent Dream
  instruction that attributed Git checkout disposal to coga retire. Review
  uses the recorded stacked base to cover the seven paths in this change.
limitations: >-
  Native Windows and macOS and the Python 3.11 floor are deferred to release
  verification. Publication requires resolving the local-only base and the
  other ticket edits noted under Publication dependency.
files:
  src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md: "Explain why canceled retirement calls for agent judgment."
  src/coga/resources/templates/coga/bootstrap/retire/ticket.py: "Document the review task, default resource, and --no-launch."
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/knowledge-scan/SKILL.md: "Identify the retirement route for source canceled."
  src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md: "Limit accepted inputs to done tickets."
  src/coga/resources/templates/coga/recurring/dream/ticket.md: "Document the retirement review, Git cleanup, and canceled-finding summary."
  tests/test_dream_worker_templates.py: "Check that Phase 6 assigns durable knowledge to the retirement review task."
  tests/test_retro_skill_template.py: "Guard against reintroducing the canceled-ticket Retro claim."
review:
  reviewer: codex
  kind: independent
  status: passed
  head: ecde357318bf3b5e9bf9633e3d35e705f21737a8
  base: e649a9ce3b02dcc5dc67b14b7fbb2428a03c1ee3
  detail: >-
    Codex independently reviewed Claude's diff and traced the alias, command,
    resource override, deletion paths, and Dream and Retro instructions. Codex
    reviewed its own follow-up corrections and reconciled the wording assertion
    they affected. No unresolved findings on this diff. No overlap with the
    Claude implementation session.
checks:
  - command: 'PYTHONPATH="$PWD/src" .venv/bin/python -m pytest -q -p no:cacheprovider'
    status: passed
    head: ecde357318bf3b5e9bf9633e3d35e705f21737a8
    base: e649a9ce3b02dcc5dc67b14b7fbb2428a03c1ee3
    detail: "Pop!_OS 24.04 LTS (Linux), Python 3.12.12. 3258 passed, 30 skipped, 0 failed in 204.84 seconds."
  - command: .venv/bin/coga validate --json
    status: passed
    head: ecde357318bf3b5e9bf9633e3d35e705f21737a8
    base: e649a9ce3b02dcc5dc67b14b7fbb2428a03c1ee3
    detail: "Pop!_OS 24.04 LTS (Linux), Python 3.12.12. 0 errors and 82 pre-existing warnings in under one second."
  - command: git diff --check e649a9ce3b02dcc5dc67b14b7fbb2428a03c1ee3 ecde357318bf3b5e9bf9633e3d35e705f21737a8
    status: passed
    head: ecde357318bf3b5e9bf9633e3d35e705f21737a8
    base: e649a9ce3b02dcc5dc67b14b7fbb2428a03c1ee3
    detail: "Pop!_OS 24.04 LTS (Linux). Exit 0 with no findings in under one second."
```

---

## Blockers

- [ ] [2026-11-25 18:14] [agent:codex] id=20261125T181432 Resolve correct-migration-claims-the-fix-stale-branch-s-fi so its branch can serve as the remote PR base, or confirm retargeting the two reviewed retirement commits to main. Reconcile the four unrelated ticket edits in the shared checkout before publication.
