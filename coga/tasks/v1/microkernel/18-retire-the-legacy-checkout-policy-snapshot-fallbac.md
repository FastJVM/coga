---
title: Retire the legacy checkout-policy snapshot fallback
status: canceled
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
agent: claude
---

## Description

Owns retiring the legacy-snapshot fallback in src/coga/checkout_policy.py (checkout_policy.select_checkout_policy's _ROWS table plus _changed_skill/_changed_section/_lf), which selects an entry checkout for frozen workflow steps that have no checkout: key because they were frozen before the field existed. Decided by coga/tasks/decide-the-two-open-questions-left-by-the-checkout (2026-11-18). Premise: the retirement rule in coga/checkouts (Legacy snapshots) — delete the fallback only in a reviewed change after no live ticket in supported repos carries a code/docs snapshot without checkout:, or after an explicitly reviewed migration of those snapshots; never rewrite snapshots merely to delete it. Evidence at filing: this repo alone had 50 live (draft/active/in_progress/blocked/paused) code/ or docs/ workflow tickets with at least one frozen step lacking checkout:, so the condition did not hold. Before activating, re-count live legacy snapshots here and in any supported adopting repo; if the count is nonzero, choose between waiting and a reviewed migration that pins each such step to the policy the table currently selects, recording the choice. The removal must update coga/checkouts (Legacy snapshots), coga-dev/codebase (checkout_policy.py), validate's comment in _check_step_shape about absent checkout:, and the legacy cases in tests/test_checkouts.py.

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

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Re-count (implement, 2026-11-19)

Counted on origin/main 849061e43 (script: parse each `coga/tasks/**/*.md`
frontmatter; status in draft/active/in_progress/blocked/paused; workflow name
`code/*` or `docs/*`; at least one frozen step without `checkout:`).

- This repo: **49** live legacy snapshots (50 at filing). Mostly `coga/tasks/_v2/*`
  (draft/paused/in_progress), plus `v1/18`, `v1/44`, `v1/46`, `v1/49`, `v1/50`,
  `v1/05-launch-on-a-stale-feature-branch-leaves-projected`,
  `v1/microkernel/05-*`, `v1/microkernel/10-*`. Several are in_progress.
- Supported adopting repos: no topic lists them (`coga-dev/project-stage`,
  `coga-dev/current-direction` checked); not countable from here.

Condition in `coga/checkouts` "Legacy snapshots" does not hold. Nothing implemented.

## Decision needed (owner)

Wait vs. reviewed migration. The migration would rewrite the frozen
`workflow.steps` of 49 tickets (adding `checkout:` = what
`checkout_policy.select_checkout_policy` selects today, `manual` where the skill
or inline section drifted), including in_progress tickets held by other
sessions — a frontmatter field agents may not edit — and adopting repos would
need the same migration before upgrading. Options:
1. Wait: park this ticket until the count reaches zero (most `_v2` drafts may be
   canceled by triage instead).
2. Migrate: owner approves a one-off migration script (reviewed in this PR) run
   over this repo's tickets at a quiet moment, plus a statement of which adopting
   repos are supported and must be migrated/counted.

---

## Blockers

- [ ] [2026-11-19 11:14] [agent:claude] id=20261119T111458 Re-count on main 849061e43: 49 live code/docs tickets here still have frozen steps without checkout: (list on blackboard), and no topic names the supported adopting repos. Choose: (1) wait/park until the count is zero, or (2) approve a reviewed migration that rewrites those 49 frozen workflow snapshots (incl. in_progress tickets) to pin today's selected checkout, and name which adopting repos must be counted/migrated.

## Superseded in part by plain-Git (2026-11-19)

Owner re-evaluation against `v1/03-use-git-like-everyone-remove-coga-s-publication-ab`.
Likely moot: if the per-step checkout: field goes (decision 2, open question), checkout_policy.py goes entirely. Wait for that answer, then cancel or keep.
Do not implement the superseded part; re-scope after that design lands.
