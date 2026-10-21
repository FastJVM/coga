---
title: File post-merge obligations before open-pr because merge-triggered closure
  is unconditional
status: done
owner: nicktoper
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
agent: claude
---

## Description

Filed by Dream 2026-W43 (recurring/dream, Phase 6; Phase 2 knowledge-scan shard ks-20, gap). Target: docs/contexts/coga/workflows/SKILL.md (code/with-review closure) plus the code/open-pr and code/address-pr-comments skills. Pattern: three independent done tickets closed with unfinished, recorded obligations no open ticket owns: marketing/fix-installer/release-0-4-1-so-new-context-files-publish was auto-bumped done on merge of PR #998 although its Done criteria require 0.4.1 on PyPI (TestPyPI dry run, pre-tag gate, owner publication, post-PyPI clean-install + attended coga build check all still owed; origin has only tag v0.4.0); marketing/readme-top was marked done with a 'Still open' list (megalaunch proof, First steps vs the fix-installer matrix, demo-video check); marketing/fix-installer/add-an-attended-coga-build-step-to-the-clean-insta left the macOS walk without a build passthrough. Retro W43 preserved these as known gaps in PRs #1058, #1059 and #1046, but no topic says what happens to obligations the merge does not discharge. Proposed rule: any obligation the merge does not discharge must be filed as its own draft before open-pr (or the work kept off code/with-review), because autoclose-merged closure is unconditional. Note open Retro PR #1055 also edits coga/workflows; sequence after it.

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
implementation and evidence, never placeholders; coga/internals/pr-publication/
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

## Dev

pr: https://github.com/FastJVM/coga/pull/1070
branch: post-merge-obligations

## Plan (agreed with owner 2026-10-20)

Docs/skills only: add the rule to coga/workflows "Code review gate", a pre-check in code/open-pr, and a flag-before-merge note in code/address-pr-comments (each with packaged twin). No mechanical gate: autoclose stays unconditional. PR #1055 touches a different hunk of coga/workflows; proceeding without waiting.

## Handoff (implement, 2026-10-20)

Commit `01035ced3` on `post-merge-obligations` (pushed; rebased on origin/main `aef654ea4`).

- `coga/workflows` "Code review gate": new `### Obligations the merge does not discharge` subsection. It states that autoclose closure is unconditional (`autoclose._candidate` + merged check, never reads Done criteria) and says to file un-discharged obligations as drafts before `coga open-pr`, or keep the work off merge-closed workflows. The same goes for manual `coga mark done`. W43's three tickets are the worked case.
- `code/open-pr`: new step 2 pre-check (steps renumbered 1–4; the "guard in step N" reference updated) plus an acceptance bullet.
- `code/address-pr-comments`: flag such obligations to the human before merge and file a draft only with their agreement.
- Packaged twins byte-identical (test_packaging passes).
- PR #1055 edits a different hunk of coga/workflows (around line 36): no textual conflict expected, but whoever merges second should recheck the twin.
- Pre-rebase, two unrelated test failures (missing untracked CLAUDE.md; usage_report import allowlist) reproduced on main. Main fixed both; the full suite on the rebased head passes.

## Peer review

Completed direct, independent review by Codex on 2026-10-20; no must-fix
findings. The implement handoff records Claude as the author; this Codex
session made no implementation edits and did not start a nested reviewer.
Reviewed head `ea25137d4801cb20edda39d58bfb32b17c55e853` against base
`793bc026fd55727cbb02a4d2d6b19fa11cbb17a7`.

- Rebased unconditionally onto fetched main before reviewing and testing.
  `git range-diff` confirms the implementation patch is unchanged from
  `01035ced3`; pushed the new head with an explicit force-with-lease.
- Checked the closure claim against `autoclose._candidate`, `_on_final_step`,
  and `_try_bump_one`, and the worked examples against the live tickets and
  Retro PR patches. Reviewed the pre-publication pre-check, escalation,
  owner-controlled review assist, renumbered references, and all three
  byte-identical packaged twins.
- Composed the changed skills from the frozen workflow at `aef654ea4`:
  attended and megalaunch open-pr, plus attended review. All three include
  the new obligation guidance; the review assist still forbids bumping and
  requires owner agreement before filing. Only in-memory step selection
  changed. No terminal, pager, or Slack rendering changed, so a TTY exercise
  is inapplicable.
- Required full suite on Python 3.12.12: 3,808 passed, 7 skipped. Scoped
  validation: one valid ticket, no issues. Exact commands and revision
  receipts are under `## PR`. No Python 3.11 run; this diff changes prose only.
- Reviewed the workflows topic for splitting after it crossed the byte-size
  guidance. Keep this bounded addition beside the Code review gate here:
  separating its closure rule from that gate would add navigation without
  removing unrelated material.
- Final freshness fetch reached `89c92b650f3452f27ccd95ae5603d8538c73c552`.
  Its changes since the reviewed base are only unrelated generated ticket/log
  state, which the publication contract permits; neither the six reviewed
  paths nor this ticket changed. The head/base receipts remain current.
- PR #1055 remains open and changes a separate Definition format hunk in
  workflows and its twin. No must-fix interaction found. This docs/skills
  ticket has no additional obligation that its merge leaves unfinished;
  backfilling the historical release/platform work is outside the agreed scope.

## PR

```yaml
title: File post-merge obligations as drafts before open-pr
author: claude
author_evidence: The implement handoff records Claude Opus 5.5 (claude-opus-5-5) under coga launch as the author of 01035ced3. This independent Codex review session rebased that unchanged patch and made no implementation edits.
head: ea25137d4801cb20edda39d58bfb32b17c55e853
base: 793bc026fd55727cbb02a4d2d6b19fa11cbb17a7
depth: skim
rationale: Bounded docs/skills change with completed independent review, a green full suite, and pre-change frozen-workflow composition checks. Skim the new rule and its procedural enforcement tradeoff.
implementation: States in coga/workflows that merge-triggered autoclose is unconditional and that obligations the merge does not discharge must be filed as drafts before open-pr; adds the matching pre-check to code/open-pr and a flag-before-merge note to code/address-pr-comments.
deviations: None. Owner approved a procedural rule over a mechanical autoclose gate.
limitations: Not enforced mechanically; an agent can still skip the pre-check. Autoclose behavior is unchanged. Tests ran on Python 3.12.12, not 3.11; no runtime code changed. No TTY exercise was needed because no interactive or rendered terminal surface changed.
files:
  docs/contexts/coga/workflows/SKILL.md: Owns the new rule and the W43 worked case.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: Packaged twin of the workflows topic.
  coga/skills/code/open-pr/SKILL.md: Pre-check step and acceptance bullet before running coga open-pr.
  src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md: Packaged twin of code/open-pr.
  coga/skills/code/address-pr-comments/SKILL.md: Flag un-discharged obligations before the owner merges.
  src/coga/resources/templates/coga/bootstrap/skills/code/address-pr-comments/SKILL.md: Packaged twin of code/address-pr-comments.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: ea25137d4801cb20edda39d58bfb32b17c55e853
  base: 793bc026fd55727cbb02a4d2d6b19fa11cbb17a7
  detail: Direct independent review completed on the rebased head with no must-fix findings. Checked the closure implementation, obligation guidance, owner gate, worked examples, packaged twins, and compatibility with the existing frozen workflow. No nested review tool was invoked.
checks:
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest
    status: passed
    head: ea25137d4801cb20edda39d58bfb32b17c55e853
    base: 793bc026fd55727cbb02a4d2d6b19fa11cbb17a7
    detail: 3808 passed, 7 skipped in 450.12 seconds on Python 3.12.12, including packaging and composition tests.
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-post-merge-review-470d3d57/check_composition.py
    status: passed
    head: ea25137d4801cb20edda39d58bfb32b17c55e853
    base: 793bc026fd55727cbb02a4d2d6b19fa11cbb17a7
    detail: Three read-only compositions using this ticket's pre-change frozen workflow from aef654ea4 passed. Inspected attended and megalaunch open-pr guidance and attended review guidance; owner agreement and the no-bump rule remain present.
  - command: coga validate --task file-post-merge-obligations-before-open-pr-because --json
    status: passed
    head: ea25137d4801cb20edda39d58bfb32b17c55e853
    base: 793bc026fd55727cbb02a4d2d6b19fa11cbb17a7
    detail: One valid ticket, no issues or fixes.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: ea25137d4801cb20edda39d58bfb32b17c55e853
    base: 793bc026fd55727cbb02a4d2d6b19fa11cbb17a7
    detail: No whitespace errors in the six-file branch diff.
```
