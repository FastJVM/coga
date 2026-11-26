---
title: Stop the shipped bootstrap-import skill presenting Coga's own skills as the
  user's repo
status: in_progress
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
step: 4 (push-and-open-pr)
agent: claude
---

## Description

Filed by Dream recurring/dream, period 2026-W48 (run 20261125T175534Z), Phase 6 disposition of Phase 2/3 findings.

G40 (ks-16): src/coga/resources/templates/coga/bootstrap/skills/bootstrap/import/SKILL.md l.104/133/151-156/167 is a shipped skill. Its examples present the Coga source repo's own installed skills as 'this repo': coga/skills/clarity, the google-agents-cli-* packs, and marketing/write-post. An adopting repo has none of them, so the guidance reads as fact about the user's checkout. Rewrite them as generic examples (an install-url skill, a github-managed pack, a repo-authored skill), or move the Coga-specific notes to a coga-dev topic. Acceptance: the shipped skill names no Coga-repo-only path as the reader's repo, and tests/test_packaging.py passes.

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

branch: coga/stop-the-shipped-bootstrap-import-skill-presenti-4704ec
base: coga/restore-coga-init-contracts-and-a-delete-topic-t-bb5902
remote: origin
reviewed: ff3f1188176012f08d4107ca7a86c5298ac84406

## Implement notes

- Chose "rewrite as generic examples" over a coga-dev topic: the four spots
  only needed an illustration, and the inline `include` JSON snippet carries
  what `coga/skills/clarity/.coga-source.json` used to point at.
- Remaining "this repo" phrases (decision checklist, reject criteria,
  adaptation-notes example) address the reader's repo generically; kept.
- Out of scope, possible follow-up: the shipped dream skills
  `bootstrap/dream/scan/contract-audit/SKILL.md` l.54-56 and
  `bootstrap/dream/scan/knowledge-scan/SKILL.md` l.87-91 also cite
  `coga/skills/clarity/` and `google-agents-cli-*`. Those read as Coga-repo
  scan targets, not as claims about an adopter's checkout, so not touched.

## Publication handoff

- The recorded stacked base is the parent of the reviewed change at `b4205a08f`.
  After fetching `origin`, that base still exists only locally. The PR step
  needs the base on `origin`.
- The checkout already had unstaged changes in the audit log and seven task
  files, including this ticket. The PR script requires the other task files
  to be reconciled before publication. Their changes are preserved.

## PR

```yaml
title: Stop the shipped bootstrap-import skill presenting Coga's own skills as the user's repo
author: claude
author_evidence: >-
  The implement session ran on Claude Opus 5.5 (claude-opus-5-5).
head: ff3f1188176012f08d4107ca7a86c5298ac84406
base: b4205a08f3f5254f6e26a1f9db7ef3c1f1a6c704
depth: skim
rationale: >-
  A documentation-only change to one shipped skill. It replaces four
  Coga-repo-specific examples with placeholders and leaves the behavior
  descriptions unchanged.
implementation: >-
  The gh-managed pack example now uses coga/skills/example-cli-*/. The
  clarity worked example becomes an inline include and
  local_adaptation_notes snippet. The flat-import examples use
  name example-skill, and the namespaced authored example uses
  coga/skills/docs/write-guide/. The claim about what every import in
  this repo is has been removed.
deviations: >-
  None. The ticket allowed generic examples or a coga-dev topic, and
  generic examples were chosen.
limitations: >-
  Native Windows and macOS verification is deferred to release. The Linux
  suite ran on Python 3.12.12. The dream scan skills still cite Coga's own
  skills, which is out of scope and noted on the blackboard.
files:
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/import/SKILL.md: "Replace Coga-repo-only skill paths with generic examples."
review:
  reviewer: codex
  kind: independent
  status: passed
  head: ff3f1188176012f08d4107ca7a86c5298ac84406
  base: b4205a08f3f5254f6e26a1f9db7ef3c1f1a6c704
  detail: >-
    Codex manually reviewed the full diff against the recorded stacked base
    and checked the shipped skill against coga/skill-management, the skill
    resolver, and the import implementation. All four examples apply to an
    adopting repo and no findings remain. Claude implemented the change in a
    separate session, with no reviewer overlap.
checks:
  - command: 'PYTHONPATH="$PWD/src" .venv/bin/python -m pytest tests/test_packaging.py tests/test_skill_manager.py'
    status: passed
    head: ff3f1188176012f08d4107ca7a86c5298ac84406
    base: b4205a08f3f5254f6e26a1f9db7ef3c1f1a6c704
    detail: "176 passed in 12.64s on Pop!_OS 24.04 LTS (Linux), Python 3.12.12."
  - command: 'PYTHONPATH="$PWD/src" .venv/bin/python -m pytest'
    status: passed
    head: ff3f1188176012f08d4107ca7a86c5298ac84406
    base: b4205a08f3f5254f6e26a1f9db7ef3c1f1a6c704
    detail: "3258 passed, 30 skipped in 179.56s on Pop!_OS 24.04 LTS (Linux), Python 3.12.12."
```
