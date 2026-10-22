---
title: 06 Collapse state publication into one user topic
status: in_progress
owner: nicktoper
contexts:
- coga/knowledge
- coga-dev/packaging
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
step: 2 (peer-review)
agent: claude
launch_generation: pending:dab14b02-401c-4038-a73b-7643905d0a59
---

## Description

Make coga/state-publication the single user owner (absorbing sweep's strict recipe and recovery), move sweep and authoring internals to coga-dev, and shorten coga/sync to a map. See `coga/tasks/blocks/README.md`.

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

### Scope and acceptance

Read `coga/tasks/blocks/README.md` first: it holds the test, the rules every
ticket in this group follows, and the audit rows for these topics. The audit
verdicts are recommendations; re-check each against current main and record
any disagreement on the blackboard for the owner before departing from it.

Done when: `coga/state-publication` is the single user topic for Coga-state publication (roots, eligibility, the pre-review hazard, the strict `coga run publish-state` recipe, recovery), `state-publication/authoring` and `state-publication/sweep` are deleted, and `coga/sync` is a short map; both copies of every touched topic are byte-identical;
no link in `docs/`, `src/`, `tests/`, `coga/` (outside old tickets and the
log), `README.md` or `AGENTS.md` points at a removed topic or anchor; any new
coga-dev page is listed in `docs/contexts/coga-dev/internals/SKILL.md`;
`.venv/bin/python -m pytest` and `coga validate --json` pass.

### Specifics

- `authoring`'s three user facts (one guarded publish; a Git-destination
  change refuses; edits are kept on failure) go into
  `bootstrap/skills/coga/ticket/finalize/SKILL.md` (live + packaged) or
  `state-publication`.
- Internals → existing `coga-dev/internals/state-publication`.
- Repoint links from `sandboxes`, `checkouts`, `checkouts/manual`,
  `extension-model`, `sync`, `architecture`, and the comments in
  `src/coga/cli.py` and `src/coga/publish_state.py`.
- `sync`'s "Design rule for new features" and the 2026-10-01 decision →
  `coga-dev/patterns`.


<!-- coga:blackboard -->

## Dev

branch: blocks-06-collapse-state-publication

## Handoff (implement)

Done on `blocks-06-collapse-state-publication` (pushed, one commit `042e0d10b`).

- `coga/state-publication` (both copies) is the single user owner: roots, eligibility, "When Coga publishes" (lifecycle commands, sweep, launch, guided authoring's three facts, manual edits), control vs feature checkouts, pre-review hazard, "Strict publication on demand", "Recovering a failed publication". Dated 2026-10-07 framing dropped from the user topic.
- `state-publication/authoring` and `/sweep` deleted (both copies; dropped from `REQUIRED_BOOTSTRAP_CONTEXT_REFS`). Their internals (sweep skips/selection, recipe wiring, finalization) and the 2026-10-07 decision are in `coga-dev/internals/state-publication`, already listed in the internals index (no new coga-dev page).
- `coga/sync` is a map: two-layer summary, failure stance, owner table, optional coga-dev links. Design rule + 2026-10-01 decision moved to `coga-dev/patterns` (description updated).
- Finalize skill (live + packaged) states the three authoring facts and links `coga/state-publication#when-coga-publishes`.
- Repointed: checkouts, checkouts/manual, sandboxes, extension-model, architecture, configuration, docs/README.md, coga-dev codebase/internals/git-refresh/publish, `cli.py` and `publish_state.py` comments. Remaining `coga/sync` mentions are general "sync layer" references and stay valid.
- On main: draft ticket `state-sync-published-unmerged-recurring-templates` attached `coga/state-publication/sweep` (validate error); repointed to `coga/state-publication` (it already had it, so the duplicate was dropped).

Audit disagreement: none.

### Pre-existing failures on main (not caused here)

`tests/test_packaging.py` fails 3 tests identically with and without this change (verified by stashing): 13 live/packaged context twins drifted and `coga/code` missing its canonical copy. Cause: tickets 01/02 (PRs #1080, #1081) had live `docs/contexts/` edits swept onto main before their packaged twins merged (the pre-review hazard). For `checkouts`, `sandboxes`, `architecture` I applied only my link edits to the packaged copies so as not to carry those tickets' content; those three still differ until #1081/#1080 land. Everything this ticket wrote is byte-identical across twins. Expect the open-pr step to need a rebase after those PRs merge.

## PR

```yaml
title: Collapse state publication into one user topic
author:
  agent: claude (claude-opus-5-5), coga megalaunch implement step
head: 042e0d10b4803d25176a89aa5956200202e6b7e6
base: bb5450faf1fca22e74002df317dae20e097540e4
review_depth: skim
review_depth_rationale: docs-only restructuring plus two code comments and one removed test list entry pair; no behavior change
files:
  docs/contexts/coga/state-publication/SKILL.md (+ packaged): absorbs sweep recipe/recovery, authoring facts, sync control/feature bullets
  docs/contexts/coga/state-publication/{authoring,sweep}/SKILL.md (+ packaged): deleted
  docs/contexts/coga/sync/SKILL.md (+ packaged): shortened to a map
  docs/contexts/coga-dev/internals/state-publication/SKILL.md: receives sweep, recipe wiring, finalization internals, 2026-10-07 decision
  docs/contexts/coga-dev/patterns/SKILL.md: receives sync design rule and 2026-10-01 decision
  coga/skills/coga/ticket/finalize/SKILL.md (+ packaged): three authoring facts, repointed link
  checkouts, checkouts/manual, sandboxes, extension-model, architecture, configuration (+ packaged), docs/README.md, coga-dev codebase/internals/git-refresh/publish: link repoints
  src/coga/cli.py, src/coga/publish_state.py: comment repoints
  tests/test_packaging.py: drop deleted refs from REQUIRED_BOOTSTRAP_CONTEXT_REFS
review: not run yet (implement step); no code review has happened
checks:
  - command: .venv/bin/python -m pytest -q
    result: 3 failed, 3952 passed, 7 skipped (tree identical to commit, before rebase onto bb5450faf which only touched this ticket)
    note: the 3 test_packaging failures reproduce on main without this change (see above)
  - command: .venv/bin/python -m pytest -q tests/test_packaging.py tests/test_paths.py tests/test_layout_contexts.py tests/test_publish_state.py
    result: 3 failed, 83 passed at head 042e0d10b (same 3 pre-existing)
  - command: .venv/bin/coga validate --json
    result: one error (draft ticket attaching removed sweep topic) fixed on main; remaining issues are warnings
```

## Plan

- `coga/state-publication` absorbs sweep's user facts (when the sweep runs, strict recipe, recovery), authoring's three facts, and sync's control/feature bullets.
- Sweep and authoring internals, dated owner decisions -> `coga-dev/internals/state-publication`; sync's design rule + 2026-10-01 decision -> `coga-dev/patterns`.
- `coga/sync` becomes a short map; repoint links.
