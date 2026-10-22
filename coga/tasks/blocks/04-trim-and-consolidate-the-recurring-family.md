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

## Implementation

Claude's original implementation was `5a314ff19`, rebased as `e0dbc7de4`.
Scheduling now owns the serviced-period ledger and recurring command variants;
the ledger/failures leaves were removed and their user contracts merged.
Period-task retains the state-lifetime and completion rules, linking to
templates for the Python blackboard API. Developer details live in the new
recurring-clone and recurring-autofix topics, recurring-admission, packaging,
and codebase/gotchas. The old-install troubleshooting paragraph lives in install.

Recorded audit deviations: one user-facing auth-retry summary remains because
operators see the retry; its mechanics are local developer knowledge.
Scheduling remains over the topic-size review threshold after the required
merge, while the three-topic family shrank. Splitting it back would recreate
the removed leaves; retain this exception for the owner to review.

## Peer review

Completed direct Codex review of final head `7abf37635690f7b6f53a9468b6180459d4ebf4ed` against
base `bb322aa4225b22d0e4a12bf877b07ca7cb3f0bfd`. The implement handoff identifies Claude
(claude-opus-5-5) as the original implementer. This was independent review of
that implementation; Codex authored and self-reviewed commit `7abf37635`.
No nested review CLI or subagent ran.

Fixed findings:
- The condensed clone-output paragraph incorrectly promised the final tail on
  the console. `recurring_clone._run_clone_script` retains it in the local log
  and run record. Corrected that distinction and kept exact output/deadline
  limits only in `coga-dev/internals/recurring-clone`.
- Install troubleshooting generalized one old clone-scope incompatibility to
  every unknown future template key. Narrowed the claim to the established
  clone-scope case.
- Added the requested direct link to the shipped configuration for `idle_days`.
  Its comments are in prerequisite PR #1080, still open. Rebuilt the PR record
  with valid compact identities, structured receipts and all 30 exact paths;
  the implement record's free-form author/review and wildcard file path would
  not satisfy publication preparation.

Reviewed the audit rows, ledger and command ownership, period-state retention,
headless/delegation gates, clone completion/output, inactivity admission,
autofix parsing/auth retry, and moved authoring/package contracts against the
relevant source. All nine surviving topic pairs are byte-identical; both
deleted leaves are absent in both trees. No live link points to those removed
topics or their removed anchors, excluding old tickets, log and archive.
Both new developer topics are indexed. No terminal or rendered Slack exercise
applies because this diff changes neither UI code nor message formats.

Verification on the head/base above:
- `PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest -q`:
  **3 failed, 3952 passed, 7 skipped in 348.08s (0:05:48)**, Python 3.12.12. These are the existing
  packaging twin, distribution and navigation failures. An earlier exploratory
  run was interrupted before the final committed run; only the completed final
  run supplies this receipt.
- `PYTHONPATH=/home/n/Code/claude/coga/src coga validate --json`:
  **151 OK, 0 errors, 0 fixes, 47 warnings**, exit 0.
- `git diff --check origin/main...HEAD`: passed.
- The change-specific twin/reference audit passed. A pristine main clone at
  `bb322aa4225b22d0e4a12bf877b07ca7cb3f0bfd` separately reproduced the three packaging
  failures (**3 failed, 27 passed**, `tests/test_packaging.py`).

Readiness is withheld for prerequisites, not an unfinished review:
- **blocks/02-delete-the-code-topic-and-remove-coga-repo-only**, PR #1081,
  repairs the twelve remaining unrelated twin mismatches and the leftover
  `coga/code` package/registration/links. The required green suite cannot be
  claimed before this lands.
- **blocks/01-self-document-coga-toml-and-split-the-agents-to**, PR #1080,
  supplies the linked `idle_days` comments. Its source was inspected at
  `b4a503632c87eb832f1dbe8e1dc17485e9cda212`; current main lacks them.

After both land, rebase this branch, retain the merged scheduling topic and
deleted leaves through PR #1081's overlap, rerun the suite and validation,
re-review the resulting head and refresh these receipts before bumping.
Ticket 09 also edits install; reconcile that overlap if it lands meanwhile.
The final fetch still had main at the reviewed base. The branch was pushed
with `--force-with-lease` and has two commits ahead of main. This manual
checkout was returned to clean, current `main` before writing this handoff.
No PR has been opened for this branch.

## PR

```yaml
title: Trim the recurring topics and merge the scheduling leaves
author: claude
head: 7abf37635690f7b6f53a9468b6180459d4ebf4ed
base: bb322aa4225b22d0e4a12bf877b07ca7cb3f0bfd
implementation: Merge scheduling/ledger and scheduling/failures into scheduling, which owns the serviced-period
  ledger and command variants. Trim recurring, period-task, templates, delegation, autofix and inactivity per the
  audit; relocate internals to indexed local developer topics, template packaging rules to packaging, the digest-writer
  incident to gotchas, and old-install troubleshooting to install. Correct clone output retention, narrow the old-install
  compatibility claim, and link the shipped configuration. Runtime behavior is unchanged.
deviations: Retain one operator-facing auth-retry summary in autofix. Keep scheduling above the topic-size review
  threshold to preserve the ticket-mandated merge; splitting it back would recreate the removed leaves. Exact clone
  runtime/output limits now live only in recurring-clone.
limitations: 'PR #1081 (blocks/02-delete-the-code-topic-and-remove-coga-repo-only) must repair existing main packaging
  drift before the mandatory suite can pass. PR #1080 (blocks/01-self-document-coga-toml-and-split-the-agents-to)
  supplies the referenced idle_days comments. Both were still open at review. No terminal or rendered Slack exercise
  applies: no UI code or message format changes. Verification used Python 3.12.12, not a new Python 3.11 compatibility
  run.'
files:
  docs/README.md: index without removed leaves
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: digest-writer anecdote
  docs/contexts/coga-dev/internals/SKILL.md: lists the new pages
  docs/contexts/coga-dev/internals/recurring-admission/SKILL.md: ledger read, inactivity ordering, delegation rationale
  docs/contexts/coga-dev/internals/recurring-autofix/SKILL.md: new; analyst internals
  docs/contexts/coga-dev/internals/recurring-clone/SKILL.md: new; clone run internals
  docs/contexts/coga-dev/packaging/SKILL.md: shipped recurring template rules
  docs/contexts/coga/architecture/SKILL.md: topic map wording
  docs/contexts/coga/install/SKILL.md: gains CLI-older-than-templates troubleshooting; peer review limits the compatibility
    claim to the known clone-scope case
  docs/contexts/coga/period-task/SKILL.md: auto-attached; anecdote, API, ledger restatement, private name out
  docs/contexts/coga/recurring/SKILL.md: command table and source-file list out; leaf map updated
  docs/contexts/coga/recurring/autofix/SKILL.md: spawn/parse internals out; known-gap sentence dropped
  docs/contexts/coga/recurring/delegation/SKILL.md: rejected alternatives and implementation names out
  docs/contexts/coga/recurring/scheduling/SKILL.md: absorbs ledger and failures; owns ledger and command variants;
    clone internals and skew paragraph out; peer review corrects console-versus-log output retention and removes
    duplicated implementation limits
  docs/contexts/coga/recurring/scheduling/failures/SKILL.md: deleted (merged; known gaps already ticketed)
  docs/contexts/coga/recurring/scheduling/inactivity/SKILL.md: private names out; idle_days pointer; peer review
    adds the requested link to the shipped configuration
  docs/contexts/coga/recurring/scheduling/ledger/SKILL.md: deleted (merged)
  docs/contexts/coga/recurring/templates/SKILL.md: PR/test history, Coga-repo section, phone-home section out; gains
    blackboard API
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: 'Packaged twin: topic map wording'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: 'Packaged twin: gains CLI-older-than-templates
    troubleshooting; peer review limits the compatibility claim to the known clone-scope case'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/period-task/SKILL.md: 'Packaged twin: auto-attached;
    anecdote, API, ledger restatement, private name out'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md: 'Packaged twin: command table and
    source-file list out; leaf map updated'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md: 'Packaged twin: spawn/parse
    internals out; known-gap sentence dropped'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/delegation/SKILL.md: 'Packaged twin: rejected
    alternatives and implementation names out'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: 'Packaged twin: absorbs
    ledger and failures; owns ledger and command variants; clone internals and skew paragraph out; peer review corrects
    console-versus-log output retention and removes duplicated implementation limits'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/failures/SKILL.md: 'Packaged twin:
    deleted (merged; known gaps already ticketed)'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/inactivity/SKILL.md: 'Packaged
    twin: private names out; idle_days pointer; peer review adds the requested link to the shipped configuration'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/ledger/SKILL.md: 'Packaged twin:
    deleted (merged)'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md: 'Packaged twin: PR/test
    history, Coga-repo section, phone-home section out; gains blackboard API'
  tests/test_packaging.py: drop the two merged refs from REQUIRED_BOOTSTRAP_CONTEXT_REFS
review:
  reviewer: codex
  kind: independent
  status: failed
  head: 7abf37635690f7b6f53a9468b6180459d4ebf4ed
  base: bb322aa4225b22d0e4a12bf877b07ca7cb3f0bfd
  detail: Direct review completed on the final diff. Independent review of the Claude implementation; Codex applied
    and self-reviewed the follow-up corrections. The merge, retained user contracts, relocated implementation details,
    both twins, deleted references and indexes were inspected. Readiness remains withheld for the two unmerged prerequisites
    and failed mandatory suite; no other unresolved change-specific finding. No nested review CLI or subagent was
    used.
checks:
- command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest -q
  status: failed
  head: 7abf37635690f7b6f53a9468b6180459d4ebf4ed
  base: bb322aa4225b22d0e4a12bf877b07ca7cb3f0bfd
  detail: 'Python 3.12.12: 3 failed, 3952 passed, 7 skipped in 348.08s (0:05:48). Failures: test_live_and_packaged_copies_stay_identical,
    test_context_distribution_is_complete, test_context_navigation_has_no_broken_links. All are existing main drift;
    twelve remaining mismatched pairs and the leftover coga/code package/registration/links are covered by PR #1081.
    This completed run began after the final correction commit.'
- command: PYTHONPATH=/home/n/Code/claude/coga/src coga validate --json
  status: passed
  head: 7abf37635690f7b6f53a9468b6180459d4ebf4ed
  base: bb322aa4225b22d0e4a12bf877b07ca7cb3f0bfd
  detail: 'Exit 0: 151 OK, 0 errors, 0 fixes, 47 warnings for existing ticket state.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 7abf37635690f7b6f53a9468b6180459d4ebf4ed
  base: bb322aa4225b22d0e4a12bf877b07ca7cb3f0bfd
  detail: No whitespace errors.
- command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python /tmp/coga-blocks04-peer-audit.py
  status: passed
  head: 7abf37635690f7b6f53a9468b6180459d4ebf4ed
  base: bb322aa4225b22d0e4a12bf877b07ca7cb3f0bfd
  detail: 'Change-specific audit: all nine surviving canonical/package topic pairs are byte-identical; both removed
    topics are absent in both trees. Searches and resolved navigation found no live references to the removed recurring
    topics or removed anchors outside excluded old tickets/log/archive. Both new developer topics are indexed. Existing
    unrelated navigation and distribution errors remain disclosed by the failed suite.'
- command: PYTHONPATH=/tmp/coga-blocks04-peer-main-bb322aa42/src /home/n/Code/claude/coga/.venv/bin/python -m pytest
    -q tests/test_packaging.py --tb=short
  status: failed
  head: bb322aa4225b22d0e4a12bf877b07ca7cb3f0bfd
  base: bb322aa4225b22d0e4a12bf877b07ca7cb3f0bfd
  detail: 'Baseline-only evidence from a pristine clone of main, not verification of the feature head: 3 failed,
    27 passed in 11.45s. Reproduced the same three packaging test names before the final feature test run.'
author_evidence: The implement handoff records Claude (claude-opus-5-5) as the implementer of original commit 5a314ff19,
  now rebased as e0dbc7de4. Codex independently reviewed that implementation in this session and authored the documentation
  corrections in 7abf37635; those corrections were self-reviewed.
depth: deep
rationale: 'The documentation restructuring is bounded, but acceptance remains blocked: the required full suite
  has three pre-existing packaging failures covered by open PR #1081, and the linked idle_days comments belong to
  still-open prerequisite PR #1080. Complete those dependencies and refresh review/check receipts before advancing.'
```

---

## Blockers

- [ ] [2026-10-21 17:38] [agent:codex] id=20261021T173852 Merge PR #1081 for blocks/02-delete-the-code-topic-and-remove-coga-repo-only to repair the three required packaging-test failures, and PR #1080 for blocks/01-self-document-coga-toml-and-split-the-agents-to to supply the linked idle_days comments. Then rebase the pushed branch, rerun pytest and validation, and refresh the final review receipts before bumping. Direct review and documentation fixes are complete; validation passes.
