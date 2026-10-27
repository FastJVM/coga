---
title: Drop bundled-skill twin rows from the skill-update report
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
step: 4 (review)
agent: claude
---

## Description

In this repo every `coga/skills/<ref>` that is the live twin of a package-bundled skill (`code/open-pr`, `code/design`, `coga/show`, ...) gets a `skipped-bundled` row from `coga skill update --all` (`skill_manager._bundled_update_result(installed=True)`). These are not managed skills: they have no upstream and the updater never touches them, so 14 noise rows drowned out the 8 real ones in the weekly skill-update PR (FastJVM/coga#1098, owner comment). Change the contract so an installed bundled twin gets no row, like an uninstalled bundled ref: update `coga/skill-management` (docs + packaged twin), the skill-update recurring ticket twins, `skill_update.py` status vocabulary if `skipped-bundled` becomes unused, and the tests. `coga skill status` keeps reporting `local-override`/`package-backed`.

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

## Dev

pr: https://github.com/FastJVM/coga/pull/1127
branch: coga/drop-bundled-skill-twin-rows

## Implement handoff

- Implemented and pushed `ff410829dae6918d65d515efffadd7bc069de62b`.
  The bulk planner in `src/coga/skill_manager.py` (`update_skills`) selects
  only GitHub and URL sources, so unmanaged bundled twins emit no update row.
  Managed provenance still takes precedence when a ref overlaps a bundled skill.
- Explicit single-skill bundled updates keep their maintenance guidance, so
  `skipped-bundled` remains a used status. `status_skills` still reports
  `local-override` and `package-backed`. Updated the owning skill-management
  context and recurring ticket twins; both pairs are byte-identical.
- Regression first: the bundled-only planner, mixed managed/bundled report,
  and real recurring recipe with a twin failed as expected (3 failed, 1 passed)
  before the fix. Command: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_skill_manager.py::test_update_all_emits_no_rows_for_bundled_skills tests/test_skill_manager.py::test_update_all_reports_a_failed_gh_skill_as_followup_beside_the_updated_one tests/test_skill_update.py::test_skill_update_runs_through_generic_recipe_and_reports_no_op -q`.
- Focused verification after the fix: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_skill_manager.py tests/test_skill_update.py -q`
  — 118 passed. Full suite on the final implementation: 4,123 passed,
  10 skipped, Python 3.12.12. The peer-review receipt below supersedes that
  implementation check.
- The staged implementation tree before the full suite and the committed tree
  both equal `af95f75733706f2bbf2f9e23b6b5ee6f70c96919`. The only unstaged
  change was this ticket's working notes; no implementation bytes changed
  during testing or commit. Fetched `origin/main`, ran `git rebase FETCH_HEAD`
  (already up to date, no OID change), pushed, fetched again, and returned to
  clean current `main` before writing this handoff. Unique ticket notes were
  verified in `/tmp/coga-drop-bundled-skill-twins-ticket-before-reconcile.md`
  before clearing them for the rebase and reconciling them here.
- Actual implementer: Codex (GPT-6), without a model override, irrespective of
  the ticket's configured Claude agent. No PR opened in implementation;
  no implementation blockers or adjacent bugs found.

## Peer review

- Direct Codex (GPT-6) review **completed** on head
  `219321fc7f3d45973bb8717e44099718f241dda0`, against base
  `6beb91a464e22206ab1b0a51f1612624f47ca9cd`. Reviewed all eight changed paths
  and traced bulk selection, managed-source precedence, JSON counts, PR and
  recurring reports, explicit bundled updates, and status inventory.
  No must-fix or unresolved findings; no implementation edits were needed.
- Both the actual implementer and reviewer are Codex, so this is recorded as
  **self-review**, not independent review. Recommend **skim** for this bounded
  selection change and its explicit-update compatibility choice.
- Fetched current main and rebased the branch unconditionally. Main's added
  commits changed only this ticket and the log; the implementation bytes still
  match `ff410829dae6918d65d515efffadd7bc069de62b`. Re-ran the full suite on
  the rebased head: **4,123 passed, 10 skipped in 369.72s**, Python 3.12.12.
  Whitespace and both canonical/package twin comparisons passed. The exact
  commands and revision receipts are below. No terminal-driving check was
  needed: this changes result selection, with CLI/report paths covered by the
  suite, and does not change an interactive surface.
- Re-fetched main before and after pushing; it remained at the reviewed base.
  Pushed the rebased head with an explicit force-with-lease and returned to
  clean current `main` before writing this handoff. No PR opened; the next
  step is the mechanical `open-pr` step. No blockers.

## PR

```yaml
title: Omit bundled skill twins from bulk update reports
author: codex
author_evidence: This implement session ran in Codex (GPT-6), with no model override; the configured ticket agent was not the implementer.
head: 219321fc7f3d45973bb8717e44099718f241dda0
base: 6beb91a464e22206ab1b0a51f1612624f47ca9cd
depth: skim
rationale: Bounded bulk-selection change with a passing full suite and completed direct Codex self-review. Read the description for the retained explicit-update diagnostics; independent review was not performed because the actual implementer and reviewer are both Codex.
implementation: The bulk updater plans only GitHub and URL sources, omitting unmanaged bundled twins from JSON counts and weekly reports. Updates preserve managed-source precedence and the existing status inventory. The owning context and recurring template twins describe the change.
deviations: None. The skipped-bundled status remains because explicit single-skill updates still use it to explain repository maintenance or package upgrades.
limitations: Verified locally on Linux with Python 3.12.12; Python 3.11 and native Windows were not run. Upstream/network actions use deterministic test fixtures.
files:
  coga/recurring/skill-update/ticket.md: Describe the omission of unmanaged bundled twins from the weekly report and link the owning topic.
  docs/contexts/coga/skill-management/SKILL.md: Specify bulk omission, managed-source precedence, and explicit single-skill diagnostics.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md: Keep the shipped skill-management topic identical to its canonical copy.
  src/coga/resources/templates/coga/recurring/skill-update/ticket.md: Keep the shipped recurring ticket identical to its live copy.
  src/coga/skill_manager.py: Plan bulk updates only for GitHub and URL sources.
  src/coga/skill_update.py: Describe the bulk report's omission of unmanaged bundled skill twins.
  tests/test_skill_manager.py: Cover omitted rows and counts, untouched twins, managed-source precedence, and retained explicit diagnostics.
  tests/test_skill_update.py: Cover the recurring no-op report with an installed twin and use managed-skill statuses in report fixtures.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 219321fc7f3d45973bb8717e44099718f241dda0
  base: 6beb91a464e22206ab1b0a51f1612624f47ca9cd
  detail: Direct Codex review completed after rebase, covering all eight diff paths and the affected selection, provenance, report, explicit-update, and inventory contracts. No must-fix or unresolved findings. The implementation also ran in Codex; peer configuration does not establish independence.
checks:
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest > /tmp/coga-drop-bundled-skill-twins-peer-pytest.log 2>&1
    status: passed
    head: 219321fc7f3d45973bb8717e44099718f241dda0
    base: 6beb91a464e22206ab1b0a51f1612624f47ca9cd
    detail: 4123 passed, 10 skipped in 369.72s on Linux with Python 3.12.12. Includes packaging, twin, mixed-source report, bundled-only recurring recipe, explicit-update, and status tests. Run after rebase; no implementation bytes changed afterward.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: 219321fc7f3d45973bb8717e44099718f241dda0
    base: 6beb91a464e22206ab1b0a51f1612624f47ca9cd
    detail: No whitespace errors on the final rebased feature diff.
  - command: cmp docs/contexts/coga/skill-management/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md
    status: passed
    head: 219321fc7f3d45973bb8717e44099718f241dda0
    base: 6beb91a464e22206ab1b0a51f1612624f47ca9cd
    detail: Canonical and packaged skill-management contexts are byte-identical after rebase.
  - command: cmp coga/recurring/skill-update/ticket.md src/coga/resources/templates/coga/recurring/skill-update/ticket.md
    status: passed
    head: 219321fc7f3d45973bb8717e44099718f241dda0
    base: 6beb91a464e22206ab1b0a51f1612624f47ca9cd
    detail: Live and packaged recurring tickets are byte-identical after rebase.
  - command: coga validate --json
    status: not-run
    detail: Validation, configuration, task layout, prompt composition, and workflow semantics are unchanged; no seeded fixture update is required.
```
