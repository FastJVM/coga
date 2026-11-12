---
title: Make Retro check inbound doc links before deleting a done ticket
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
launch_generation: pending:8738122c-6667-4a78-8d3e-55cee359dfdd
---

## Description

Filed by Dream run recurring/dream, period 2026-W46 (run 20261112T051938Z), Phase 6 — a gap found in the run itself, not by a scan shard.

Dream Phase 4 Retro direct-deleted the done ticket document-the-remedy-for-a-bloated-blackboard-sibli (no unextracted durable knowledge), but the root README.md cites it by a blob/main link as its worked example. tests/test_packaging.py::test_context_navigation_has_no_broken_links then failed on main. Fixed for now by PR #1214, which repoints the link to the last commit containing the ticket (dc6832e0b).

Root cause: retro/done-ticket (src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md) and the Dream template's Phase 4 eligibility check open PRs and live checkouts, but not durable inbound references (README.md, docs/*.md, contexts, skills) to coga/tasks/<slug> on blob/main. Decide the rule: e.g. before deleting, grep tracked docs for the task path and either rewrite the link to a commit permalink in the same change (knowledge PR or a small PR next to the direct delete) or skip the ticket and report it. Also consider whether coga delete itself should warn on inbound blob/main links.

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

branch: make-retro-check-inbound-doc-links-before-deleting

## Decision

- Rule owner: `retro/done-ticket`, new `### Inbound references`. Before
  choosing a source's deletion path, Retro runs
  `git grep -n -F -e '<tasks-root>/<slug>' -- . ':!<tasks-root>' ':!<coga-os>/log.md'`
  in the isolated checkout and inspects each hit. Prefix-sharing slugs,
  same-path fixture trees, and links from other live tickets are not
  references. It repoints each real reference to a permalink at the full OID of
  the fresh control tip (that tip still contains the task).
  - Knowledge-bearing source: the repoint goes in its knowledge PR. Repointed
    files do not count toward the 3-knowledge-file limit, and the PR body lists
    them under `Repointed references`.
  - No-knowledge source with references: no direct delete, because
    `coga delete` publishes only the task and the log, and doc edits need
    review. It goes into one run-level reference-pin PR
    (`codex/retro-pin-references`, "Pin links to deleted tickets"), with no
    marker. Progress receipt: `pr pin-references — <url> — <slugs>`.
  - Self-review re-runs the search on each branch, and on the tree before each
    direct delete.
- Rejected: "skip the ticket and report it". That breaks Retro's invariant that
  no processed done ticket stays on disk, and Dream would re-pick the ticket
  every run.
- `coga delete`/`coga retire` warning: not in this change, because it grows
  the shared core path and retire's deterministic delete needs its own
  decision. Filed as draft `warn-when-coga-delete-or-coga-retire-leaves-a-live`.

## Handoff (implement → peer-review)

- Changed: the Retro skill (new section, plus the contract, Scope, steps
  5/9/10/11, progress line, PR body, and intro); Dream Phase 4 (a summary
  paragraph that links to the skill); `retire.md` (an exception clause); tests
  in `tests/test_retro_skill_template.py` (new test, plus one assertion that
  followed the reworded "Do not" line) and `tests/test_dream_worker_templates.py`
  (new test). No fixture change: these are prompt templates only.
- Known red on main, not caused by this change: README.md still links the
  deleted `document-the-remedy-for-a-bloated-blackboard-sibli` on blob/main.
  This fails `test_packaging.py::test_context_navigation_has_no_broken_links`,
  plus two `test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep`
  cases that run that test in a subprocess. PR #1214 (OPEN) fixes it.

## PR

```yaml
title: Repoint inbound task links before Retro deletes a ticket
author:
  agent: claude
  model: claude-opus-5-5
head: 2e62cf0e1ba5a9705db8e8cbf549735e21923a63
base: 79cd556d60d7cbd09e6c972ed4e09c1e23cb3063
review_depth: light
review_depth_rationale: Prompt/template text plus string-assertion tests; no Python behavior change. The risk is rule wording and consistency with Dream and retire.
implementation: >-
  Retro now searches tracked files for each source task's path before it
  deletes. It repoints each live-tree reference to a full-OID commit permalink:
  in the knowledge PR for a knowledge-bearing source, or in a single
  reference-pin PR for a referenced source with no durable knowledge, which no
  longer takes the direct delete. Dream Phase 4 and retire.md summarize the rule
  and link to the skill.
deviations: []
limitations:
  - coga delete / coga retire are not guarded; follow-up draft warn-when-coga-delete-or-coga-retire-leaves-a-live.
files:
  src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md: owner of the new Inbound references rule and the matching contract/steps/progress/PR-body edits
  src/coga/resources/templates/coga/recurring/dream/ticket.md: Phase 4 summary pointing to the rule, since its eligibility gates do not cover it
  src/coga/resources/retire.md: retire's restatement of Retro's direct delete gains the reference-pin exception
  tests/test_retro_skill_template.py: regression test for the rule; one assertion updated for the reworded Do-not line
  tests/test_dream_worker_templates.py: test that Dream defers the rule to the skill
checks:
  - command: .venv/bin/python -m pytest -q
    tree: identical to head 2e62cf0e1 (committed with no further edits; rebase was a no-op)
    result: 3 failed, 4765 passed, 33 skipped
    failures: pre-existing README blob/main link to a deleted ticket (test_packaging navigation + 2 test_git subprocess cases); fixed by open PR #1214
  - command: .venv/bin/python -m pytest -q tests/test_retro_skill_template.py tests/test_dream_worker_templates.py tests/test_retire.py tests/test_packaging.py
    result: 1 failed (same navigation test), 101 passed
review:
  code_review: not run yet; peer-review is the next workflow step
```

## Plan

- Rule lives in `retro/done-ticket` (owner of deletion): before choosing a
  source's deletion path, `git grep` tracked files (outside the task root and
  `coga/log.md`) for the task path; repoint every live reference to a
  full-OID commit permalink in a PR. Knowledge-bearing → same knowledge PR;
  no-durable-knowledge with references → not direct-deleted, leaves in one
  run-level reference-pin PR. Dream Phase 4 summarizes and links.
- `coga delete`/`coga retire` warning: not in this change (core growth);
  file a follow-up draft.
