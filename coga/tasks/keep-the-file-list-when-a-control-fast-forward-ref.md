---
title: Keep the file list when a control fast-forward refuses over local changes
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

During `coga recurring --all` on 2026-10-22, the multiply clone failed with `[git] note: local 'main' in /home/n/Code/multiply not fast-forwarded: error: Your local changes to the following files would be overwritten by merge:` and then nothing: the note never named the file (it was `coga/log.md`). Cause, verified: `summarize_git_failure` in `src/coga/git.py` keeps only `error:`/`fatal:`/`CONFLICT` lines, and git prints the blocking paths on the following tab-indented lines, so they are discarded. Keep those path lines (bounded, e.g. first N plus a count) so the operator can see what blocks the fast-forward without running git by hand. Add a test covering git's 'would be overwritten by merge' and 'untracked working tree files would be overwritten' outputs.

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

branch: coga/keep-control-fast-forward-paths

## Implement handoff

- Pushed commit `af0423e0fc106d70b2f684892a0c14d21c3b942d` on the recorded
  branch. Returned this manual checkout to clean, current `main` before
  writing this handoff. No PR opened; peer review is next.
- `src/coga/git.py` `summarize_git_failure` now keeps the first 10
  tab-indented paths with each overwrite-error heading and counts omitted
  paths. It deduplicates complete messages, preserving different path lists
  under the same heading. Advice/progress filtering and the unknown-error
  fallback remain intact. `fast_forward_control` uses the richer summary.
- Regression tests cover tracked/untracked real-Git refusals, unchanged local
  files and control tip, quoted paths/spaces, truncation at EOF or before a
  later error, and repeated headings with different file lists. The owning
  state-publication topic and packaged twin document the output contract.
- Before the fix, the focused command recorded below ran against uncommitted
  regression tests: 9 failed, 2 passed, 223 deselected. Both real-Git cases
  reproduced the missing `coga/log.md` path. The same selection passed after
  the fix. SHA-256 comparisons verified the committed implementation files
  matched the tested working tree.
- Main advanced only in another ticket and `coga/log.md`; rebased cleanly and
  reran the full suite on the resulting commit. Both runs passed with 3996
  passed, 7 skipped. All seven skips require Windows. No known unresolved
  implementation issue or adjacent bug was found. Independent review remains
  for the next workflow step.

## PR

```yaml
title: Keep blocking file lists in Git failure summaries
author: codex
author_evidence: >-
  Implemented by the Codex assistant in this session (coga-launch
  cdea37f1-2c2b-4096-bbe0-dbf19effc106), not the ticket's configured Claude agent.
head: af0423e0fc106d70b2f684892a0c14d21c3b942d
base: 24f3524b5c90d1b847b6d109d12ea0449bdfdf87
depth: deep
rationale: >-
  Bounded diagnostic-only change with passing regression and full-suite checks;
  independent review has not run and belongs to the next workflow step.
implementation: >-
  Keep up to 10 paths per overwrite refusal with their error heading and an
  exact omitted count. Deduplicate complete messages and preserve the existing
  actionable-error filtering and fallback. Document the operator-visible note.
deviations: None.
limitations: >-
  Verified on Linux with Python 3.12.12. Seven Windows-only checks were skipped;
  no separate Python 3.11 run was performed for this diagnostic-only change.
files:
  src/coga/git.py: Preserve bounded overwrite file lists in the shared Git failure summary.
  tests/test_git.py: Cover real-Git refusals and bounded, associated, deduplicated path lists.
  docs/contexts/coga/state-publication/SKILL.md: Document the refusal note's file-list contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Keep the shipped fallback identical to its canonical topic.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Independent code review is the next workflow step; implement does not perform self-QA.
checks:
  - command: >-
      PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_git.py
      -k 'summarize_git_failure or fast_forward_names_files' -q
    status: passed
    head: 1f031dca47097d0c0cf921faccf78ffc5e2a3296
    base: 1ee371c66af6ec2473c934b49b2b057a16f8d71c
    detail: >-
      Historical pre-rebase focused run: 11 passed, 223 deselected in 0.49s.
      Tested working-tree files were verified byte-identical to this commit.
  - command: >-
      PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest
      > /tmp/coga-control-ff-pytest.log 2>&1
    status: passed
    head: 1f031dca47097d0c0cf921faccf78ffc5e2a3296
    base: 1ee371c66af6ec2473c934b49b2b057a16f8d71c
    detail: >-
      Historical pre-rebase full run: 3996 passed, 7 skipped in 366.94s.
      Tested working-tree files were verified byte-identical to this commit.
  - command: >-
      PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest
      > /tmp/coga-control-ff-pytest-rebased.log 2>&1
    status: passed
    head: af0423e0fc106d70b2f684892a0c14d21c3b942d
    base: 24f3524b5c90d1b847b6d109d12ea0449bdfdf87
    detail: >-
      Fresh full run after rebase: 3996 passed, 7 skipped in 345.70s.
      Python 3.12.12; skips are Windows job-object and PowerShell integration.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: af0423e0fc106d70b2f684892a0c14d21c3b942d
    base: 24f3524b5c90d1b847b6d109d12ea0449bdfdf87
    detail: No whitespace errors in the committed feature diff.
  - command: >-
      cmp docs/contexts/coga/state-publication/SKILL.md
      src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md
    status: passed
    head: af0423e0fc106d70b2f684892a0c14d21c3b942d
    base: 24f3524b5c90d1b847b6d109d12ea0449bdfdf87
    detail: Canonical and packaged context are byte-identical.
  - command: coga validate --json
    status: not-run
    detail: No configuration, validation, task-model, prompt-composition, or workflow behavior changed; the seeded fixture needed no update.
```
