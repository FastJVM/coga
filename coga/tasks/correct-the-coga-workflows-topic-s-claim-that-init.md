---
title: Correct the coga workflows topic's claim that init seeds workflows
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
  - name: peer-review
    skills:
    - code/peer-review
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
agent: claude
launch_generation: pending:4e8120b9-82c0-4db7-aeaa-d94576c6c71e
---

## Description

Filed by Dream run recurring/dream, period 2026-W46 (run 20261112T051938Z), Phase 6 disposition. Finding from Phase 2 (ks-06, stale) and Phase 3 (ca-05, drift), held as a draft because open PR #1197 (Add bundled code/agent-merge workflow) already edits the target src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md without carrying this fix; handle after #1197's review.

The opening paragraph says 'coga init seeds some workflows into the repo, including direct/body'. Current init copies only reviewed scaffolds: src/coga/commands/update.py FRESH_SCAFFOLDS (used by copy_fresh_templates from commands/init.py) lists workflows/_template.md as the only workflows entry, and its comment says reusable definitions resolve from the installed package. direct/body ships at bootstrap/workflows/direct/body.md. Replace the sentence: shipped workflows (including direct/body) resolve from the package's bootstrap/workflows/; coga init copies only the ignored workflow authoring template.

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

## Dev

branch: fix-workflows-topic-init-claim

## Handoff (implement)

Changed only the opening paragraph of
`src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md`:
shipped workflows, including `direct/body`, resolve from the package's
`bootstrap/workflows/`; `coga init` copies only the ignored
`workflows/_template.md` starter. Verified against
`src/coga/commands/update.py` `FRESH_SCAFFOLDS` (the only workflows entry is
`workflows/_template.md`; its comment says reusable definitions resolve from
the installed package). No other surface repeats the old claim (grep of
docs/contexts, package resources, README). No code or fixture change.

PR #1197 is still open and also edits this file. If it merges first, rebase
this branch; the conflict is limited to this one paragraph.

Pre-existing failure, not from this change:
`tests/test_packaging.py::test_context_navigation_has_no_broken_links` fails on
origin/main 8ab0f010e. The README links to
`coga/tasks/document-the-remedy-for-a-bloated-blackboard-sibli.md`, which was
deleted in 61388855a. The two
`test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep`
cases run that packaging test in a subprocess, so they fail for the same
reason. Related follow-up:
`coga/tasks/make-retro-check-inbound-doc-links-before-deleting.md`. That
ticket fixes the retro process. The broken README link itself still needs a
fix.

## PR

```yaml
title: Correct coga/workflows claim that init seeds workflows
author: claude (Claude Code, claude-opus-5-5)
head: 42bcd1729944f15127a444e1ff069b6b3b312e0d
base: 8ab0f010ede0c723d5b3eed20870be9318f45fd2
review_depth: light
review_depth_rationale: one-paragraph documentation correction in a shipped topic, verified against update.FRESH_SCAFFOLDS; no behavior change
implementation: Replaced the sentence claiming coga init seeds workflows (including direct/body) with the package-resolution fact and the init template-only copy.
deviations: none
limitations: Overlaps PR #1197's edits to the same file; a rebase may be needed after #1197 merges.
files:
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: corrected the stale claim about init seeding workflows
checks:
  - command: .venv/bin/python -m pytest -q
    tree: d8a7a7eaf (pre-rebase; the rebase onto 8ab0f010e changed only this ticket file under coga/tasks, and the source tree is identical)
    result: 3 failed, 4763 passed, 33 skipped
    failures: test_packaging::test_context_navigation_has_no_broken_links plus two test_git sweep cases that run it in a subprocess; pre-existing README link to a deleted ticket, also present on origin/main
  - command: .venv/bin/python -m pytest -q tests/test_packaging.py tests/test_git.py
    tree: 42bcd1729
    result: 3 failed, 389 passed, 1 skipped (same three pre-existing failures)
review: not yet run; peer-review is the next workflow step
```

