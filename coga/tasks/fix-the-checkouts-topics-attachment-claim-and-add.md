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
step: 4 (review)
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

pr: https://github.com/FastJVM/coga/pull/1219
branch: fix-checkouts-attachment-claim-size-exceptions

## Implementation

Claude implemented the two topic corrections and fixed the same stale claim
in `code/open-pr`, as required by the knowledge sync rule. Size exceptions
were chosen because detailed procedures already live in leaves and the
remaining lifecycle/recovery contracts benefit from staying together.

## Peer review

Codex completed a direct, independent review of Claude's implementation.
Reviewed final head `34117676a871257d4fd470c85ed3bd946b6ae334` against
base `7fad5e7a250634d74c1d18ff4832166dcdb5e4ea`; no must-fix findings
and no review fixes needed. Read all three changed files, the owning
`coga/state-publication` committed-state boundary, `coga/knowledge` size
policy, and `git._publish_locked`, `_candidates`, and `_routine_state_areas`.
The existing committed-state regression covers the sibling `ticket.py` too.
Both closing size-exception sentences satisfy the policy. No remaining stale
claim was found in the searched live source, docs, skills, or tests; archives
were excluded.

Rebased both implementation commits onto fetched main before review and tests,
then fetched again before publication: main remained at the reviewed base.
Pushed the rebased branch with `--force-with-lease` and manually returned this
checkout to clean `main` before writing this handoff. No PR exists yet; the
next step runs the mechanical `coga open-pr` command.

Full-suite receipt on the final head: `.venv/bin/python -m pytest -q -p
no:cacheprovider` → 3 failed, 4763 passed, 33 skipped in 719.02s. Environment:
Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic x86_64, Python 3.12.12.
All three failures are the known README link to deleted ticket
`document-the-remedy-for-a-bloated-blackboard-sibli`: navigation plus both
`test_final_package_edits_never_escape_a_mutating_cli_sweep` parameters.
Implement had reproduced them on main `6dc3745d0`; README, affected tests,
and publication code are unchanged from that base to this reviewed base.
Already tracked by `make-retro-check-inbound-doc-links-before-deleting`
and recorded on `decide-the-dream-scans-corpus-and-fix-the-known-co`.
`git diff --check origin/main...HEAD` passed. No new tests are warranted for
these prose corrections. Terminal rendering and native Windows checks are
inapplicable because no runtime, executable template, or platform behavior
changed. Python 3.11 was not exercised; the receipt uses 3.12.12.
Control-side handoff validation also passed with no issues:
`coga validate --task fix-the-checkouts-topics-attachment-claim-and-add --json`
on main `7fad5e7a250634d74c1d18ff4832166dcdb5e4ea`.

PRs #1199 and #1197 remain open and edit these checkout topics; reconcile
with whichever lands first. The failed suite requires a `deep` recommendation
although this independent review found no defect in the current diff.

## PR

```yaml
title: Correct checkouts attachment claim and add size exceptions
author: claude
author_evidence: Implement handoff identifies Claude Code (claude-opus-5-5); both implementation commits carry Claude Opus 5.5 coauthor trailers. Codex performed the separate peer-review session.
head: 34117676a871257d4fd470c85ed3bd946b6ae334
base: 7fad5e7a250634d74c1d18ff4832166dcdb5e4ea
depth: deep
rationale: Bounded documentation correction with completed independent review and no must-fix findings; the full suite still has three existing broken-README-link failures, requiring deep.
implementation: Corrects the ticket.py and task-attachment publication claim in coga/checkouts and code/open-pr, links the owning committed-state boundary, and adds closing Size exception sentences to checkouts and checkouts/launch-boundary.
deviations: Also corrects skills/code/open-pr/SKILL.md because it restated the stale claim; the ticket named only the checkouts topics.
limitations: PRs 1199 and 1197 remain open on the same topics and may require reconciliation when either merges. Size exceptions were chosen over splitting. No runtime or platform behavior changed, so terminal and native Windows checks are inapplicable; Python 3.11 was not exercised.
files:
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: Correct the attachment claim with a state-publication link and add the closing Size exception sentence.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/launch-boundary/SKILL.md: Add the closing Size exception sentence required by coga/knowledge.
  src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md: Correct the same stale attachment claim in dirty-clone recovery and retain the pointer to checkouts.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 34117676a871257d4fd470c85ed3bd946b6ae334
  base: 7fad5e7a250634d74c1d18ff4832166dcdb5e4ea
  detail: Direct independent Codex review completed on the final rebased diff; checked all changed files against publication code and owning topics, with no must-fix findings. No fixes or commits followed review.
checks:
  - command: coga validate --task fix-the-checkouts-topics-attachment-claim-and-add --json
    status: passed
    head: 7fad5e7a250634d74c1d18ff4832166dcdb5e4ea
    base: 7fad5e7a250634d74c1d18ff4832166dcdb5e4ea
    detail: Control-side live-ticket validation returned ok_count 1 and no issues; this checks handoff structure, not feature code.
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider
    status: failed
    head: 34117676a871257d4fd470c85ed3bd946b6ae334
    base: 7fad5e7a250634d74c1d18ff4832166dcdb5e4ea
    detail: 3 failed, 4763 passed, 33 skipped in 719.02s on Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic x86_64, Python 3.12.12. All failures trace to README linking deleted document-the-remedy-for-a-bloated-blackboard-sibli.md (navigation and both final-package-publication parameters). Implement reproduced these on main 6dc3745d0; relevant baseline files remain unchanged.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: 34117676a871257d4fd470c85ed3bd946b6ae334
    base: 7fad5e7a250634d74c1d18ff4832166dcdb5e4ea
    detail: No whitespace errors in the final branch diff.
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider
    status: failed
    head: 498ca088fa0930c6f7603ae5be467e1c5ce896b7
    base: 6dc3745d03f231e59591d9c18a74cead8338b882
    detail: Historical implement receipt before rebase; 3 failed, 4763 passed, 33 skipped in 688.32s on Linux x86_64, Python 3.12.12. Same three failures reproduced on that main baseline. Superseded for current-head verification by the peer-review run above.
```
