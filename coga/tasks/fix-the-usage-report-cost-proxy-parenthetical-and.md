---
title: Fix the usage-report cost-proxy parenthetical and delivery-miss comment after
  PR 1102
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
step: 2 (peer-review)
agent: claude
---

## Description

Filed by Dream 2026-W44 (Phase 6; knowledge-scan ks-17). Targets: coga/skills/coga/usage-report/post/SKILL.md (~line 54-55, no twin) and the comment at coga/recurring/usage-report/ticket.py ~line 29.

Retro PR #1102 already corrects the skill's claim that a delivery miss lands in log.md (it reaches stderr only: the shim passes no task_path and slack.py writes its 'post failed' audit line only with one). Two related fixes are not in #1102 and touch the same skill file, so Dream did not open a competing PR:
1. The skill's out-of-scope note says an API-equivalent-value line 'is a follow-up once the cost proxy lands', but define-the-api-equivalent-cost-proxy-and-price-tab was canceled (coga/log.md:6209, no consumer needs dollar pricing). Suggested: '(an API-equivalent-value line would need the set-aside cost proxy revived; see coga-dev/internals/usage-pricing)'.
2. ticket.py's comment still says the miss is 'already loud on stderr and in log.md'. Suggested: 'a delivery miss is reported on stderr only (no task_path, so no log.md audit line)'. (Alternatively change behavior: pass task_path so the audit line is written.)
Land after #1102 merges.

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

branch: coga/fix-usage-report-cost-proxy-comment

## Implementation handoff

- Prerequisite [PR #1102](https://github.com/FastJVM/coga/pull/1102) merged
  2026-10-26; its merge commit `1de719527856d99b8f15cf22717998a4f5cae5a1`
  is included in the branch.
- Commit `cac80a0bfca33cf5fe422e3404d613b504f00804` corrects the cost-proxy parenthetical,
  links the standing usage-pricing topic, and corrects the delivery-miss comment.
  The skill's stale statement that the comment is wrong was removed as part
  of the same correction.
- Chose the requested comment correction: no `task_path` was added, and
  notification or bump behavior did not change. Both edited surfaces are
  repo-local with no packaged twins. No new regression tests, fixture changes,
  or context contract edits are needed for this prose/comment-only change.
- Full suite passed on Linux/Python 3.12.12: 4,121 passed, 10 native-Windows
  cases skipped. The two edited files' SHA-256 hashes were unchanged across
  the run; the precommit staged tree and committed tree both equal
  `5e46827b1b867875678fe12557e9a78092f62710`. The committed shim AST also matches
  the base, and the new relative pricing link resolves.
- Reconciled with `origin/main` at `b090307a60c529d614da0f8866df3baf4e15d0af`;
  `git rebase FETCH_HEAD` was already up to date, so no revision or test
  receipt changed. Pushed the recorded branch and returned to clean,
  fast-forwarded `main` before writing this handoff.
- No unresolved implementation findings. No PR opened or code review performed;
  the next workflow step owns peer review and should refresh the PR receipts
  after any changes.

## PR

```yaml
title: Correct usage-report pricing and delivery comments
author: codex
author_evidence: >-
  The actual implementing session used Codex (GPT-6), not the ticket's
  configured claude agent. No implementation or review was delegated.
head: cac80a0bfca33cf5fe422e3404d613b504f00804
base: b090307a60c529d614da0f8866df3baf4e15d0af
depth: deep
rationale: >-
  Two small prose/comment corrections with passing checks. Advisory depth
  remains deep until the required peer-review step supplies a review receipt.
implementation: >-
  Describe an API-equivalent-value line as requiring revival of the set-aside
  cost proxy and link the usage-pricing topic. Explain that delivery misses
  reach stderr only because the shim supplies no task_path. Remove the skill's
  now-stale claim that the shim comment says otherwise.
deviations: None; selected the ticket's wording correction and preserved runtime behavior.
limitations: >-
  Independent review has not run in this implement step. Verification used
  Linux and Python 3.12.12; native Windows and Python 3.11 were not exercised.
files:
  coga/skills/coga/usage-report/post/SKILL.md: >-
    Correct the cost-proxy status, link its standing topic, and remove the
    statement made obsolete by the corrected shim comment.
  coga/recurring/usage-report/ticket.py: >-
    Correct the comment to explain stderr-only failure reporting without
    changing the post call or the subsequent bump.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: The subsequent peer-review workflow step owns code review.
checks:
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest
    status: passed
    head: cac80a0bfca33cf5fe422e3404d613b504f00804
    base: b090307a60c529d614da0f8866df3baf4e15d0af
    detail: >-
      4121 passed, 10 skipped in 373.44s on Linux/Python 3.12.12.
      Skips: 2 Windows job-object integration cases, 5 native PowerShell 5.1
      cases, and 3 native Windows Job Object recovery cases.
      Tests ran before commit; unchanged file hashes and identical staged
      and committed tree 5e46827b1b867875678fe12557e9a78092f62710 tie this receipt
      to the committed revision.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: cac80a0bfca33cf5fe422e3404d613b504f00804
    base: b090307a60c529d614da0f8866df3baf4e15d0af
    detail: No whitespace errors in the committed two-file diff.
  - command: "python -c 'import ast, subprocess; from pathlib import Path; p = \"coga/recurring/usage-report/ticket.py\"; assert ast.dump(ast.parse(subprocess.check_output([\"git\", \"show\", f\"origin/main:{p}\"], text=True))) == ast.dump(ast.parse(Path(p).read_text())); assert (Path(\"coga/skills/coga/usage-report/post\") / \"../../../../../docs/contexts/coga-dev/internals/usage-pricing/SKILL.md\").resolve().is_file(); print(\"PASS: shim AST unchanged and pricing link resolves\")'"
    status: passed
    head: cac80a0bfca33cf5fe422e3404d613b504f00804
    base: b090307a60c529d614da0f8866df3baf4e15d0af
    detail: The shim AST is unchanged from the base and the pricing link resolves.
  - command: coga validate --json
    status: not-run
    detail: No configuration, workflow, task-model, or validation behavior changed.
```
