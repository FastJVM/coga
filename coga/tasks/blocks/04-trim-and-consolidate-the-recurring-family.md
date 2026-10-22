---
title: 04 Trim and consolidate the recurring family
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
launch_generation: pending:0a2f1671-bc5c-41b5-b588-64040eab3474
---

## Description

Apply the audit verdicts to coga/recurring, period-task and their leaves, merging scheduling/ledger and scheduling/failures into scheduling. See `coga/tasks/blocks/README.md`.

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

Done when: the recurring rows in the README table are applied, `scheduling/ledger` and `scheduling/failures` are merged into `scheduling`, and the serviced-period ledger is stated once (in `scheduling`) with the other topics linking; both copies of every touched topic are byte-identical;
no link in `docs/`, `src/`, `tests/`, `coga/` (outside old tickets and the
log), `README.md` or `AGENTS.md` points at a removed topic or anchor; any new
coga-dev page is listed in `docs/contexts/coga-dev/internals/SKILL.md`;
`.venv/bin/python -m pytest` and `coga validate --json` pass.

### Specifics

- `period-task` is auto-attached to every period prompt by `recurring.py`;
  every line removed there is saved on every recurring run.
- Commands: one owner for the recurring command list (`scheduling`
  Variants or `recurring`), the other links; flag detail is `--help`'s.
- New coga-dev pages: `internals/recurring-autofix`,
  `internals/recurring-clone`. Existing: `recurring-admission`.
- The old-install skew paragraph in `scheduling` moves to `coga/install`
  troubleshooting (ticket 09 also edits `install`; reconcile).
- Ticket 01 adds the `idle_days` comment to `coga.toml`; link to it.


<!-- coga:blackboard -->

## Dev

branch: coga/blocks-04-recurring-trim


## Handoff (implement, 2026-10-21)

Commit `5a314ff19` on `coga/blocks-04-recurring-trim` (pushed). No PR yet.

What changed, per audit row (both twins byte-identical for every touched shipped topic):
- `recurring/scheduling/ledger` + `recurring/scheduling/failures` merged into
  `recurring/scheduling` (sections "Periods and the serviced-period ledger",
  "Admission and unfinished runs", "Failures and exit code"); both leaves
  deleted in both trees and dropped from `REQUIRED_BOOTSTRAP_CONTEXT_REFS`.
  `scheduling` now **owns the serviced-period ledger**; `recurring`,
  `period-task`, `templates`, `install` link to its anchor.
- **Command list owner: `scheduling` "Variants"** (behavior); `recurring`'s
  command table replaced by one sentence + link; flags → `--help`.
- `scheduling`: clone deadline/truncation details/Windows job object → new
  `coga-dev/internals/recurring-clone` (user summary kept); skew paragraph →
  `coga/install` "CLI older than the templates it sweeps"; private names dropped
  (`_order_for_launch`, `recurring.create_template`, `scan_clone_due`,
  `RETRY_WITHOUT_SWEEP_EXIT_CODE`, `_record_abandoned_due`). `upstream-coga`
  line was already gone on canonical (ticket 02).
- Ledger backward-read/union-merge/`format_serviced_log` → `recurring-admission`
  "Reading the serviced-period ledger".
- `inactivity`: `_read_inactivity_fields`, ledger pre-pass, `is_machine_commit`
  → `recurring-admission` "Inactivity gate ordering"; now names the
  `[recurring] idle_days` key as commented in the shipped `coga.toml`
  (ticket 01, PR #1080 adds that comment; text-only reference because the
  coga.toml path differs per repo and links are test-checked) plus link to
  `configuration`.
- `autofix`: fd-tee, `parse_analysis`/`demote_headings`, codex stdin, auth
  retry detail → new `coga-dev/internals/recurring-autofix`; known-gap
  sentence about named-launch create-sync dropped (already owned by draft
  `report-failed-create-syncs-from-named-recurring-la`).
- `delegation`: "Why delegate" alternatives + Implementation names →
  `recurring-admission` "Why delegation rather than a nested launch"; generation
  guards summarized + link.
- `templates`: PR #857 / test pin / "Shipped templates in the Coga source repo"
  → `coga-dev/packaging`; "Weekly usage battery" deleted (phone-home ticket and
  `coga/edge-code` own it; no inbound anchor links); gains the fence-aware
  Python blackboard API from `period-task`.
- `period-task` (auto-attached): private name, ledger restatement, Python API
  and digest-writer anecdote removed (anecdote → `coga-dev/codebase/gotchas`).
  70 → 60 lines.
- New coga-dev pages listed in `coga-dev/internals/SKILL.md` and in
  `recurring`'s Internals line. `docs/README.md` and `architecture` map updated.

Decisions / for the owner:
- `scheduling` is now 188 lines / ~2,860 tokens, over the 2,500-token review
  line. Recorded exception: the ticket requires the merge; the family shrank
  (233 → 188 lines for the three files). A future split would re-create the
  leaves this ticket removed, so not done.
- Auth-retry kept as one user line in `autofix` (operators see the announced
  retry); full conditions in coga-dev.

Verification: see `## PR` checks. Pre-existing failure, not caused here:
`test_live_and_packaged_copies_stay_identical` fails on main because tickets
02/03's canonical edits (checkout-cleanup, checkouts, lifecycle, cli, code,
knowledge, …) were swept to main ahead of their packaged twins (PR #1081 et
al.). None of the drifted pairs is in this ticket's family.

Reconcile notes: PR #1081 (ticket 02) edits the packaged
`scheduling` and `scheduling/failures` twins; this branch rewrites/deletes
them, so whichever merges second resolves by taking this branch's content
(02's edits are already reflected). Ticket 09 also edits `install`.

## PR

```yaml
title: Trim the recurring topics and merge the scheduling leaves
author: claude (claude-opus-5-5), implement step, megalaunch queue session
head: 5a314ff1917747d94ed464435a089e0a719e5a77
base: 383d634618da7bb65809ea213382305f6361216d
review_depth: skim
review_depth_rationale: Documentation-only restructuring of shipped context topics plus one test list edit; no Python behavior change. Reviewer should check that no user-needed fact was lost from the moved paragraphs and that links/anchors resolve.
implementation: Merge scheduling/ledger and scheduling/failures into scheduling; trim recurring, period-task, templates, delegation, autofix, inactivity per the blocks audit; move internals to coga-dev (new internals/recurring-clone, internals/recurring-autofix; recurring-admission, packaging, codebase/gotchas extended); skew paragraph to coga/install.
deviations: Auth-retry kept as one user-facing line in autofix; scheduling exceeds the 2,500-token review line by design (ticket-mandated merge).
limitations: Inactivity names the coga.toml idle_days comment that PR #1080 adds; text is accurate only after #1080 merges.
files:
  docs/contexts/coga/recurring/scheduling/SKILL.md: absorbs ledger and failures; owns ledger and command variants; clone internals and skew paragraph out
  docs/contexts/coga/recurring/scheduling/ledger/SKILL.md: deleted (merged)
  docs/contexts/coga/recurring/scheduling/failures/SKILL.md: deleted (merged; known gaps already ticketed)
  docs/contexts/coga/recurring/SKILL.md: command table and source-file list out; leaf map updated
  docs/contexts/coga/recurring/scheduling/inactivity/SKILL.md: private names out; idle_days pointer
  docs/contexts/coga/recurring/autofix/SKILL.md: spawn/parse internals out; known-gap sentence dropped
  docs/contexts/coga/recurring/delegation/SKILL.md: rejected alternatives and implementation names out
  docs/contexts/coga/recurring/templates/SKILL.md: PR/test history, Coga-repo section, phone-home section out; gains blackboard API
  docs/contexts/coga/period-task/SKILL.md: auto-attached; anecdote, API, ledger restatement, private name out
  docs/contexts/coga/install/SKILL.md: gains CLI-older-than-templates troubleshooting
  docs/contexts/coga/architecture/SKILL.md: topic map wording
  src/coga/resources/templates/coga/bootstrap/contexts/coga/**: byte-identical twins of the above
  docs/contexts/coga-dev/internals/recurring-clone/SKILL.md: new; clone run internals
  docs/contexts/coga-dev/internals/recurring-autofix/SKILL.md: new; analyst internals
  docs/contexts/coga-dev/internals/recurring-admission/SKILL.md: ledger read, inactivity ordering, delegation rationale
  docs/contexts/coga-dev/internals/SKILL.md: lists the new pages
  docs/contexts/coga-dev/packaging/SKILL.md: shipped recurring template rules
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: digest-writer anecdote
  docs/README.md: index without removed leaves
  tests/test_packaging.py: drop the two merged refs from REQUIRED_BOOTSTRAP_CONTEXT_REFS
review: not run (implement step; peer-review is next)
checks:
  - command: .venv/bin/python -m pytest -q
    head: 5a314ff1917747d94ed464435a089e0a719e5a77
    result: 3 failed, 3952 passed, 7 skipped
    note: The 3 failures (test_live_and_packaged_copies_stay_identical, test_context_distribution_is_complete, test_context_navigation_has_no_broken_links) fail identically on origin/main 383d63461 (tests/test_packaging.py, 3 failed 27 passed in a clean worktree); causes are tickets 02/03 drift (coga/code, checkout-cleanup, ...), none in this family.
  - command: coga validate --json
    head: 5a314ff1917747d94ed464435a089e0a719e5a77
    result: exit 0, 47 warnings (pre-existing stale/idle tickets), no errors
```
