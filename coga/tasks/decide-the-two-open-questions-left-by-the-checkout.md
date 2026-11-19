---
title: Decide the two open questions left by the checkout-policy declaration ticket
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 2 (peer-review)
agent: claude
launch_generation: ca0366d0-c852-4973-b5b5-b3bb6ff71284
---

## Description

Filed by Dream recurring/dream, period 2026-W47 (run 20261118T170921Z), Phase 6 disposition of Phase 4 Retro follow-ups. Retro of done ticket v1/microkernel/02-declare-each-workflow-step-s-checkout-policy-in-th (direct-deleted 2026-11-18; history in git) reported two open questions it raised but never filed: (1) should `coga validate` warn when a workflow step declares `requires: branch` together with `checkout: control` or `checkout: manual`; (2) who retires the legacy-snapshot fallback for checkout policy and when. Read the deleted ticket from git history (git log --diff-filter=D -- 'coga/tasks/v1/microkernel/02-*') and the coga/workflows and coga/launch topics, decide each, and implement or record the decision in the owning topic.

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
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

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

branch: coga/decide-checkout-open-questions

## Decisions

- **Q1 — no `coga validate` lint for `requires: branch` + `checkout: control|manual`.**
  `checkout:` is entry policy and `requires:` a completion gate; `coga/checkouts`
  already declares them independent ("a `manual` step that `requires: branch`
  still needs its `branch:` before bump"), the seeded fixture's
  `tests/fixtures/seeded-repo/coga/workflows/code/with-review.md` `implement` step
  pairs `requires: branch` with `checkout: manual` on purpose, and the bump gate
  (`src/coga/step_gate.py`, `_has_branch_linkage`) already refuses loudly, naming
  `branch:` under `## Dev`. A warning would nag a declared, authoritative choice
  and validate has no definition-lint surface; project-stage (no premature
  generality) argues against adding one. Recorded in `coga/checkouts` next to
  the independence sentence.
- **Q2 — the retirement is owned by a filed draft ticket:**
  `coga/tasks/v1/microkernel/retire-the-legacy-checkout-policy-snapshot-fallbac.md`
  (draft, `code/with-review`, owner nicktoper; published on main as 201999f62).
  "When" stays the existing `coga/checkouts` "Legacy snapshots" rule (no live
  code/docs snapshot without `checkout:` in supported repos, or a reviewed
  migration). Evidence at filing: 50 live code/docs tickets in this repo still
  carry such snapshots, so the condition does not hold today; the draft says to
  re-count and choose wait vs. reviewed migration. `coga-dev/codebase`
  (`checkout_policy.py` entry) now names that ticket as the owner. Not recorded
  in the shipped topic because adopting repos cannot see this repo's tickets.

## Handoff (implement)

Commit 6bcaac1bb on `coga/decide-checkout-open-questions` (pushed), on top of
origin/main 5c6cb9641. Docs-only: two topic edits. No code or fixture change.
Next: peer-review, then open-pr.

## PR

```yaml
title: Record checkout-policy lint and fallback-retirement decisions
author: claude (Claude Code, model claude-opus-5-5), implement step
head: 6bcaac1bb3ab144d43ff1d1a9650711d379a5df9
base: 5c6cb96411d134fc5c95fe70df70177a97f4ea75
review_depth: light
review_depth_rationale: Two-sentence docs change recording decisions; no behavior change.
implementation: >-
  coga/checkouts states validate deliberately does not warn on requires: branch with
  checkout: control|manual and why; coga-dev/codebase names the draft ticket that owns
  retiring the legacy-snapshot table. The follow-up draft ticket itself was published
  directly to main by coga create (not in this diff).
deviations: none
limitations: >-
  Retirement timing is not dated; it remains evidence-gated by the coga/checkouts rule.
files:
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: >-
    Record the Q1 decision (no cross-field lint) beside the roles/gates independence rule.
  docs/contexts/coga-dev/codebase/SKILL.md: >-
    Point the checkout_policy.py legacy-table mention at its retirement-owning draft ticket.
review: not yet run; peer-review is the next workflow step.
checks:
  - command: .venv/bin/python -m pytest -q -x -p no:cacheprovider
    result: 5004 passed, 33 skipped (802s); run on the working tree whose content equals commit 6bcaac1bb
  - command: .venv/bin/python -m coga.cli validate --json
    result: 105 ok, 17 warnings, 0 errors
```

The blackboard is a notepad to be written to often as the human and agent works through a task.
