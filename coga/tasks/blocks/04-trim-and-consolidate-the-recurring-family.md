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
step: 3 (open-pr)
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

pr: https://github.com/FastJVM/coga/pull/1084
branch: coga/blocks-04-recurring-trim

## Implementation

Claude's original implementation was `5a314ff19`, previously `e0dbc7de4`,
now rebased as `2aa3dc9de`.
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

Completed direct Codex review of final head `73c4649d4c2dadda2c359c25deb2da0195d54a54`
against base `67774a1b97515df64a5b04623fbd577f82899bc1`. No unresolved findings.
The implement handoff identifies Claude (claude-opus-5-5) as the original
implementer. Codex independently reviewed that implementation and self-reviewed
its corrections, rebase resolutions and template syncs. The combined review
is recorded as self-review; no nested review CLI or subagent ran.

The owner cleared the prerequisite blocker after PRs #1080 and #1081 merged;
`coga unblock` recorded the resolution. Rebased onto current main, preserving
its autofix default-context contract and ticket 09's install cleanup alongside
this ticket's consolidation. The projected ticket was backed up and restored
byte-for-byte; the unblock log entry was already published before rebase.

Fixed findings and reconciliation:
- Preserved the earlier corrections distinguishing console output from the
  final log/run-record tail, limiting the old-install claim to clone scope,
  and linking the now-landed `idle_days` configuration comments.
- The first post-rebase suite found two pre-existing failures (3985 passed,
  7 skipped, 360.78s): `test_autoclose_live_and_packaged_copies_stay_in_sync`
  and `test_live_and_packaged_copies_stay_identical`. Main's `ee50b4ba4`
  published live cleanup-template links without their packaged twins.
  The owner approved including those two syncs here; commit `73c4649d4`
  repairs them and matches the packaged link changes in PR #1083.
- Removed the stray separator after the historical PR YAML that made the
  preparation parser reject it. Refreshed actual authorship, all 32 file
  explanations and final-head receipts; the read-only PR formatter accepts
  the preparation without evidence gaps.

Reviewed audit verdicts, ledger and command ownership, period state and
completion, headless/delegation gates, clone output/limits, inactivity,
autofix parsing/auth retry and moved developer contracts against source.
All nine surviving topic pairs and both corrected recurring-template pairs
match; both deleted topics are absent in both trees. No live link points to
removed recurring topics or anchors (old tickets, log and archive excluded).
Both new developer topics are indexed. The extra generic navigation scan's
`0.2` candidate is Go code (`genai.Ptr[float32](0.2)`), not a Markdown link.
No terminal or Slack-format exercise applies: no executable UI or message
format changes.

Verification on the final head/base above (Python 3.12.12):
- `PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest -q`:
  **3987 passed, 7 skipped in 369.12s (0:06:09)**.
- `PYTHONPATH=/home/n/Code/claude/coga/src coga validate --json`:
  **156 OK, 0 errors, 0 fixes, 48 warnings**, exit 0.
- `git diff --check origin/main...HEAD`: passed.
- `PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python /tmp/coga-blocks04-peer-audit.py`:
  passed the change-specific twin/reference audit; no enforced twin drift or
  context distribution errors remain.

The final fetch still had main at the reviewed base. The branch is committed
and pushed with `--force-with-lease` at `73c4649d4`, three commits ahead
of main; only this projected ticket remains unstaged. No PR has been
opened in this step.

Recommendation: **skim** for the retained scheduling-size exception, the
operator auth-retry summary and the approved two-template scope addition.
No Python 3.11 run was performed. The open-pr step remains mechanical;
launch owns returning this checkout after the step transition.

## PR

```yaml
title: Trim the recurring topics and merge the scheduling leaves
author: claude/codex
head: 73c4649d4c2dadda2c359c25deb2da0195d54a54
base: 67774a1b97515df64a5b04623fbd577f82899bc1
implementation: Merge scheduling/ledger and scheduling/failures into scheduling, the owner of the serviced-period
  ledger and command variants. Trim the recurring family and period-task; relocate implementation details to
  indexed local developer topics, packaging rules to packaging, the digest-writer incident to gotchas, and
  old-install troubleshooting to install. Preserve main's new autofix default-context contract and ticket 09's
  install cleanup. Correct clone output retention and old-install wording, link the shipped idle_days comments,
  and synchronize the packaged autoclose and branch-sweep checkout-cleanup links with their live copies. Runtime
  behavior is unchanged.
deviations: 'Retain one operator-facing auth-retry summary in autofix. Keep scheduling above the topic-size
  review threshold to preserve the mandated merge; splitting it back would recreate the removed leaves. Exact
  clone limits live only in recurring-clone. The owner approved adding two packaged-template link syncs to
  repair main''s independently published live-template drift; these are also present in PR #1083.'
limitations: 'Tests ran on Python 3.12.12; no new Python 3.11 compatibility run. No terminal or rendered Slack
  exercise applies because executable UI and message formats are unchanged. Codex independently reviewed the
  original Claude implementation and self-reviewed its corrections and rebase resolutions; no separate reviewer
  covered those corrections. Prerequisite PRs #1080 and #1081 are merged and included.'
files:
  docs/README.md: index without removed leaves
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: digest-writer anecdote
  docs/contexts/coga-dev/internals/SKILL.md: lists the new pages
  docs/contexts/coga-dev/internals/recurring-admission/SKILL.md: ledger read, inactivity ordering, delegation
    rationale
  docs/contexts/coga-dev/internals/recurring-autofix/SKILL.md: new; analyst internals
  docs/contexts/coga-dev/internals/recurring-clone/SKILL.md: new; clone run internals
  docs/contexts/coga-dev/packaging/SKILL.md: shipped recurring template rules
  docs/contexts/coga/architecture/SKILL.md: topic map wording
  docs/contexts/coga/install/SKILL.md: gains CLI-older-than-templates troubleshooting; peer review limits the
    compatibility claim to the known clone-scope case
  docs/contexts/coga/period-task/SKILL.md: auto-attached; anecdote, API, ledger restatement, private name out
  docs/contexts/coga/recurring/SKILL.md: command table and source-file list out; leaf map updated
  docs/contexts/coga/recurring/autofix/SKILL.md: Move analyst implementation details to coga-dev and remove
    the known-gap restatement while preserving main's newly added default-context contract.
  docs/contexts/coga/recurring/delegation/SKILL.md: rejected alternatives and implementation names out
  docs/contexts/coga/recurring/scheduling/SKILL.md: absorbs ledger and failures; owns ledger and command variants;
    clone internals and skew paragraph out; peer review corrects console-versus-log output retention and removes
    duplicated implementation limits
  docs/contexts/coga/recurring/scheduling/failures/SKILL.md: deleted (merged; known gaps already ticketed)
  docs/contexts/coga/recurring/scheduling/inactivity/SKILL.md: private names out; idle_days pointer; peer review
    adds the requested link to the shipped configuration
  docs/contexts/coga/recurring/scheduling/ledger/SKILL.md: deleted (merged)
  docs/contexts/coga/recurring/templates/SKILL.md: PR/test history, Coga-repo section, phone-home section out;
    gains blackboard API
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: 'Packaged twin: topic map
    wording'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: 'Packaged twin: gains CLI-older-than-templates
    troubleshooting; peer review limits the compatibility claim to the known clone-scope case'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/period-task/SKILL.md: 'Packaged twin: auto-attached;
    anecdote, API, ledger restatement, private name out'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md: 'Packaged twin: command table
    and source-file list out; leaf map updated'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md: Packaged twin of the
    trimmed autofix topic, including the preserved default-context contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/delegation/SKILL.md: 'Packaged twin:
    rejected alternatives and implementation names out'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: 'Packaged twin:
    absorbs ledger and failures; owns ledger and command variants; clone internals and skew paragraph out;
    peer review corrects console-versus-log output retention and removes duplicated implementation limits'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/failures/SKILL.md: 'Packaged
    twin: deleted (merged; known gaps already ticketed)'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/inactivity/SKILL.md: 'Packaged
    twin: private names out; idle_days pointer; peer review adds the requested link to the shipped configuration'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/ledger/SKILL.md: 'Packaged
    twin: deleted (merged)'
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md: 'Packaged twin: PR/test
    history, Coga-repo section, phone-home section out; gains blackboard API'
  src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.md: Owner-approved synchronization of
    checkout-cleanup links with the live template already on main; repairs the required twin checks.
  src/coga/resources/templates/coga/recurring/branch-sweep/ticket.md: Owner-approved synchronization of checkout-cleanup
    links with the live template already on main; repairs the required twin checks.
  tests/test_packaging.py: drop the two merged refs from REQUIRED_BOOTSTRAP_CONTEXT_REFS
review:
  reviewer: codex
  kind: self
  status: passed
  head: 73c4649d4c2dadda2c359c25deb2da0195d54a54
  base: 67774a1b97515df64a5b04623fbd577f82899bc1
  detail: Direct review completed on this final head/base with no unresolved findings. Independent inspection
    of the Claude implementation, plus self-review of Codex corrections, conflict resolutions and the two template
    link syncs. Reviewed the audit verdicts, surviving user contracts against source, ledger and command ownership,
    moved internals, main's autofix contexts, install overlap, every changed twin, removed references and indexes.
    No nested review CLI or subagent ran.
checks:
- command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest -q
  status: passed
  head: 73c4649d4c2dadda2c359c25deb2da0195d54a54
  base: 67774a1b97515df64a5b04623fbd577f82899bc1
  detail: 'Python 3.12.12: 3987 passed, 7 skipped in 369.12s (0:06:09). Completed after the final fix commit.'
- command: PYTHONPATH=/home/n/Code/claude/coga/src coga validate --json
  status: passed
  head: 73c4649d4c2dadda2c359c25deb2da0195d54a54
  base: 67774a1b97515df64a5b04623fbd577f82899bc1
  detail: 'Exit 0: 156 OK, 0 errors, 0 fixes, 48 warnings for existing ticket state.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 73c4649d4c2dadda2c359c25deb2da0195d54a54
  base: 67774a1b97515df64a5b04623fbd577f82899bc1
  detail: No whitespace errors.
- command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python /tmp/coga-blocks04-peer-audit.py
  status: passed
  head: 73c4649d4c2dadda2c359c25deb2da0195d54a54
  base: 67774a1b97515df64a5b04623fbd577f82899bc1
  detail: All nine surviving topic pairs and both corrected template pairs are byte-identical; the two removed
    topics are absent in both trees. No enforced twin drift or context distribution errors. No removed recurring
    topic/anchor links on live surfaces (old tickets, log and archives excluded); both new developer topics
    are indexed. The generic scanner's unrelated 0.2 candidate is Go generic-call syntax in a code block, not
    a Markdown link.
author_evidence: The implement handoff identifies Claude (claude-opus-5-5) as the author of original commit
  5a314ff19, now 2aa3dc9de. Codex authored the earlier documentation corrections (7abf37635, now bbbdc1ba6),
  resolved this rebase, and authored the owner-approved template link sync in 73c4649d4.
depth: skim
rationale: 'Bounded documentation consolidation with no executable behavior change. The required full suite,
  validation and twin/reference checks passed on this head, and direct review completed. Read the size exception
  and scope addition: scheduling stays consolidated, and two packaged recurring templates are synchronized
  with existing main edits. The final combined diff includes Codex-authored corrections and is therefore disclosed
  as self-review.'
```

## Blockers

- [x] [2026-10-21 17:38] [agent:codex] id=20261021T173852 Merge PR #1081 for blocks/02-delete-the-code-topic-and-remove-coga-repo-only to repair the three required packaging-test failures, and PR #1080 for blocks/01-self-document-coga-toml-and-split-the-agents-to to supply the linked idle_days comments. Then rebase the pushed branch, rerun pytest and validation, and refresh the final review receipts before bumping. Direct review and documentation fixes are complete; validation passes.
  resolved: [2026-10-21 21:37] [human:nicktoper] Owner confirmed: clear blocker and continue. PR #1080 merged as bd8c505462d5022176a733b35bd4691b82b7c897 and PR #1081 merged as a1a3f5049b5dd2457f531a4d81b79b6a6425bb9f. Rebase the recorded branch onto current main, reconcile the overlapping documentation, rerun pytest and validation, complete direct review of the resulting head, and refresh the final receipts before bumping.
