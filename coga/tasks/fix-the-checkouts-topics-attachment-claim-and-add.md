---
title: Fix the checkouts topics' attachment claim and add their size exceptions
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
---

## Description

Filed by Dream run recurring/dream, period 2026-W46 (run 20261112T051938Z), Phase 6 disposition. Findings from Phase 2 (ks-14, stale) and Phase 3 (ca-03, drift), held as a draft because open PRs #1199 and #1197 already edit src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md (and #1199 edits checkouts/launch-boundary/SKILL.md) without carrying these fixes; handle after their review.

1. stale (ks-14): the 'Stranded ticket writes' section ends 'ticket.py and attachments under coga/tasks/ can be implementation work and stay in the diff.' Current code adopts them to control: on a non-control checkout _publish_locked in src/coga/git.py sets adopt_only = _routine_state_areas(cfg, root) (task directory plus log) and _candidates adopts committed branch paths there, so the next sweeping command publishes them. coga/state-publication's Committed-state boundary already says so. Correct the sentence and link that section.
2. drift (ca-03): coga/knowledge's size policy requires a closing 'Size exception:' sentence in any topic over 200 lines / 10,000 bytes / 2,500 tokens. checkouts/SKILL.md (203 lines, 11,735 bytes) and checkouts/launch-boundary/SKILL.md (10,977 bytes) lack one. Either split further or append the reason.

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

branch: fix-checkouts-attachment-claim-size-exceptions

## Handoff (implement → peer-review)

Pushed `fix-checkouts-attachment-claim-size-exceptions` (2 commits on
merge-base 6dc3745d0, current origin/main). Docs-only change:

- Item 1 (ks-14): `coga/checkouts` "Stranded ticket writes" no longer says
  `ticket.py`/attachments under `coga/tasks/` stay in the diff. It now says a
  sweep on the feature checkout adopts their committed copies to control,
  links `coga/state-publication#control-versus-feature-checkouts`
  (Committed-state boundary, the owner), and routes those edits to the live
  task in the primary checkout. Code basis: `git._publish_locked` sets
  `adopt_only = git._routine_state_areas(cfg, root)` off control and
  `git._candidates` adopts committed paths only within those areas.
- Same stale claim was restated in `skills/code/open-pr/SKILL.md`
  (dirty-clone recovery bullet, which links the section); fixed in the same
  PR per AGENTS.md (owner and summarizing surface change together).
- Item 2 (ca-03): chose a closing `Size exception:` sentence over a split for
  `checkouts/SKILL.md` (now 213 lines, ~12.3 KB) and
  `checkouts/launch-boundary/SKILL.md` (174 lines, ~11.2 KB). The procedures
  already live in leaves; the remaining parent text is the lifecycle map, and
  launch-boundary keeps recovery next to the conditions it re-proves.
- Open PRs #1199 and #1197 touch `checkouts/SKILL.md` (and #1199
  `launch-boundary/SKILL.md`); they were still open at implement time, so
  whichever lands second needs a small rebase. My hunks are at the end of
  each file.
- Known, unrelated: full suite has 3 failures that reproduce identically on
  origin/main 6dc3745d0, all from README.md linking the deleted ticket
  `coga/tasks/document-the-remedy-for-a-bloated-blackboard-sibli.md`
  (`test_packaging::test_context_navigation_has_no_broken_links` and both
  `test_git::test_final_package_edits_never_escape_a_mutating_cli_sweep`
  params, which run that check in a subprocess). Already recorded on
  `decide-the-dream-scans-corpus-and-fix-the-known-co`; root cause tracked by
  draft `make-retro-check-inbound-doc-links-before-deleting`.

## PR

```yaml
title: Correct checkouts attachment claim and add size exceptions
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5) under megalaunch; both commits authored in this session.
head: 498ca088fa0930c6f7603ae5be467e1c5ce896b7
base: 6dc3745d03f231e59591d9c18a74cead8338b882
depth: deep
rationale: Docs-only wording change, but the full-suite receipt is failed (3 pre-existing main failures from a broken README link), which forces deep; reviewers only need to read the two changed paragraphs and two closing sentences.
implementation: Replaces the stale stay-in-the-diff claim for ticket.py and task attachments in coga/checkouts and code/open-pr with the committed-state boundary link and routes those edits to the live task; appends Size exception sentences to checkouts and checkouts/launch-boundary.
deviations: Also edits skills/code/open-pr/SKILL.md, which restated the same stale claim; the ticket named only the checkouts topic.
limitations: Open PRs 1199 and 1197 edit the same checkouts files and will need a rebase against whichever merges second. Size exceptions chosen over a split.
files:
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: Correct the attachment claim with a state-publication link and add the closing Size exception sentence.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/launch-boundary/SKILL.md: Add the closing Size exception sentence required by coga/knowledge.
  src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md: Drop the same stale attachment claim from the dirty-clone recovery bullet.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Implement step; independent peer review is the next workflow step.
checks:
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider
    status: failed
    head: 498ca088fa0930c6f7603ae5be467e1c5ce896b7
    base: 6dc3745d03f231e59591d9c18a74cead8338b882
    detail: 3 failed, 4763 passed, 33 skipped in 688.32s (Linux x86_64, Python 3.12.12, pytest 9.1.1). All 3 reproduce unchanged on origin/main 6dc3745d0 (README link to deleted ticket document-the-remedy-for-a-bloated-blackboard-sibli.md); none touch the changed files.
```
