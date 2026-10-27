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
step: 3 (open-pr)
agent: claude
launch_generation: 987665cb-238b-46d8-a843-8b1759e215e1
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

pr: https://github.com/FastJVM/coga/pull/1124
branch: coga/fix-usage-report-cost-proxy-comment

## Implementation handoff

- Prerequisite [PR #1102](https://github.com/FastJVM/coga/pull/1102) merged;
  its merge commit `1de719527856d99b8f15cf22717998a4f5cae5a1` is an ancestor
  of the reviewed branch.
- Codex (GPT-6) implemented the corrections in `cac80a0bfca33cf5fe422e3404d613b504f00804`,
  despite the ticket's configured `claude` agent. No work was delegated.
  Peer review rebased that commit to `0e28c59364d7ea0599759a5dfaa1b5a096044dfa`.
- Selected the requested wording correction. The skill links the set-aside
  pricing topic and drops its now-stale claim that the shim comment is wrong.
  No `task_path` was added; notification and bump behavior are unchanged.
  Both edited surfaces are repo-local, with no packaged twins.
- The implementation suite passed with 4,121 tests and 10 native Windows
  skips. The fresh verification below supersedes that earlier receipt.

## Peer review

- Direct Codex review **completed**, with no must-fix findings or edits, at
  head `0e28c59364d7ea0599759a5dfaa1b5a096044dfa` against base
  `a7388098da04aa0683d04a446d8e4b29f6d9f82e`. This is recorded as self-review:
  the implementing session also used Codex. The configured peer and this
  fresh session do not establish independent authorship.
- Reviewed both changed files, the standing usage-pricing topic, the owner's
  cancellation in `coga/log.md:6209`, the notification contract and backend,
  and existing usage-report coverage. The link resolves; the shim supplies
  no `task_path`, so `SlackChannel.send` reports a delivery miss on stderr
  without a failure audit line. The shim AST is unchanged from the base.
- No rendered terminal or Slack surface changes: only skill prose and a
  Python comment changed. No live Slack send or new regression test was
  needed. Existing usage-report tests, including failed-delivery completion,
  passed in the full suite.
- Rebased onto freshly fetched `origin/main`, with no conflicts. Full suite
  on the rebased head: **4,121 passed, 10 skipped in 381.77s**, on
  Linux/Python 3.12.12. Skips: 2 Windows job-object integration cases,
  5 native PowerShell 5.1 cases, and 3 native Windows Job Object recovery
  cases. Native Windows and Python 3.11 were not exercised.
- The fetch before push confirmed main unchanged. Pushed the rebased branch
  with an explicit force-with-lease and returned to `main`. A later handoff
  fetch added only audit-log commit `fdcc2cc01628e01e4ecc7fcd08bed367c010aa6f`;
  preserved this handoff, fast-forwarded main, and restored it. The reviewed
  two-file diff and its merge base are unchanged. No PR exists yet;
  `open-pr` is the next step.
- Recommendation: **skim**. The two-file correction is bounded, all required
  checks passed, and self-review is disclosed. No unresolved findings.

## PR

```yaml
title: Correct usage-report pricing and delivery comments
author: codex
author_evidence: >-
  The implementing session used Codex (GPT-6), despite the ticket's configured
  claude agent. No work was delegated. The peer-review session also used Codex.
head: 0e28c59364d7ea0599759a5dfaa1b5a096044dfa
base: a7388098da04aa0683d04a446d8e4b29f6d9f82e
depth: skim
rationale: >-
  Two bounded prose/comment corrections with no executable change. Direct
  Codex self-review completed without findings, the full suite passed on the
  rebased head, and the pricing link and unchanged shim AST were verified.
  Read the description for the self-review and platform limitations.
implementation: >-
  Describe an API-equivalent-value line as requiring revival of the set-aside
  cost proxy and link the usage-pricing topic. Explain that delivery misses
  reach stderr only because the shim supplies no task_path. Remove the skill's
  now-stale claim that the shim comment says otherwise.
deviations: None; selected the ticket's wording correction and preserved runtime behavior.
limitations: >-
  Review is self-review because both implementation and review used Codex;
  independent review was not performed. Verification used Linux and Python
  3.12.12; native Windows and Python 3.11 were not exercised. No live Slack or
  terminal check was needed because message text and runtime behavior did not
  change; the full suite covers existing delivery and completion behavior.
files:
  coga/skills/coga/usage-report/post/SKILL.md: >-
    Correct the cost-proxy status, link its standing topic, and remove the
    statement made obsolete by the corrected shim comment.
  coga/recurring/usage-report/ticket.py: >-
    Correct the comment to explain stderr-only failure reporting without
    changing the post call or the subsequent bump.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 0e28c59364d7ea0599759a5dfaa1b5a096044dfa
  base: a7388098da04aa0683d04a446d8e4b29f6d9f82e
  detail: >-
    Direct review completed in this fresh peer-review session with no must-fix
    findings or edits. Reviewed the complete two-file diff, pricing topic and
    cancellation evidence, notification implementation and contract, and
    existing usage-report tests. Codex also implemented the change, so this
    receipt does not claim independent review.
checks:
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest
    status: passed
    head: 0e28c59364d7ea0599759a5dfaa1b5a096044dfa
    base: a7388098da04aa0683d04a446d8e4b29f6d9f82e
    detail: >-
      4121 passed, 10 skipped in 381.77s on Linux/Python 3.12.12 after rebase.
      Skips: 2 Windows job-object integration cases, 5 native PowerShell 5.1
      cases, and 3 native Windows Job Object recovery cases. The working tree
      remained clean and HEAD unchanged throughout verification.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: 0e28c59364d7ea0599759a5dfaa1b5a096044dfa
    base: a7388098da04aa0683d04a446d8e4b29f6d9f82e
    detail: No whitespace errors in the committed two-file diff.
  - command: |
      .venv/bin/python - <<'PY'
      import ast
      import subprocess
      from pathlib import Path

      shim = Path('coga/recurring/usage-report/ticket.py')
      base = subprocess.check_output(['git', 'show', f'origin/main:{shim}'], text=True)
      assert ast.dump(ast.parse(base)) == ast.dump(ast.parse(shim.read_text()))
      skill = Path('coga/skills/coga/usage-report/post/SKILL.md')
      link = '../../../../../docs/contexts/coga-dev/internals/usage-pricing/SKILL.md'
      assert f']({link})' in skill.read_text()
      assert (skill.parent / link).resolve().is_file()
      for root in ('src/coga/resources/templates/coga',):
          assert not any('usage-report' in p.parts for p in Path(root).rglob('*'))
      print('PASS: shim AST unchanged; pricing link resolves; no packaged usage-report twins')
      PY
    status: passed
    head: 0e28c59364d7ea0599759a5dfaa1b5a096044dfa
    base: a7388098da04aa0683d04a446d8e4b29f6d9f82e
    detail: The shim AST is unchanged, the pricing link resolves, and neither file has a packaged twin.
  - command: coga validate --json
    status: not-run
    detail: No configuration, workflow, task-model, or validation behavior changed.
```
