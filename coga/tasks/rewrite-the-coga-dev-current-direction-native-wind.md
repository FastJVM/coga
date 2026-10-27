---
title: Rewrite the coga-dev current-direction native Windows entry after the core
  port
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
launch_generation: pending:f7cdd097-12e0-4f17-a4bc-50b4aee1a96c
---

## Description

Filed by Dream 2026-W44 (Phase 6; knowledge-scan ks-06, ks-08; contract-audit ca-03). Target: docs/contexts/coga-dev/current-direction/SKILL.md (local-only, no packaged twin).

1. Lines ~109-113 say native Windows stays unsupported because src/coga/git.py imports fcntl at module top so every command fails. That code is gone: the lock moved to src/coga/oscompat.py (fcntl only under os.name == 'posix', msvcrt otherwise); windows-native/01-core-port-cli-and-test-suite-pass-on-native-window is done (PR #1093). Rewrite the entry to the current posture (non-interactive commands and deterministic work run natively; interactive agent sessions refuse until windows-native/03-interactive-coga-launch-on-native-windows lands; the user-facing claim stays owned by coga/install and coga/launch) and drop the fcntl rationale.
2. Lines ~137-138 say Retro W43 kept README launch checks as known gaps in PRs #1058, #1059 and #1046; #1058 and #1059 closed unmerged, only #1046 merged. Correct the sentence.

Why a draft, not a Dream PR: open PR #1096 (make-every-code-workflow-review-with-the-other-age) also edits this file (a different hunk near line 80); Dream does not open a competing proposal on the same path. Land after #1096 merges or rebase onto it.

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

branch: coga/rewrite-current-direction-native-windows

## Implement handoff

- Actual implementing agent: Codex, despite the ticket's configured
  `agent: claude`. No code review ran in the implement step; the completed
  review is recorded below.
- Updated the local `coga-dev/current-direction` Windows entry and its
  update date. The entry now summarizes the landed native core port,
  non-interactive commands and deterministic work, and the remaining agent
  session refusal. It links to the owning `coga/install` and `coga/launch`
  contracts and removes the obsolete `fcntl` rationale. No packaged twin,
  fixture or runtime change is needed.
- PR #1096 merged as `5ccecf9d8f8b49c20c5baebd1baf4107c00f575d`
  and is an ancestor of the feature branch, satisfying the ordering ask.
- Item 2 is already satisfied by `5738ca6468de56540b060f8ef86656575a9c19b0`
  (`Retro marker: marketing/readme-top`): the current sentence says only
  PR #1046 merged and #1058/#1059 closed unmerged. GitHub metadata confirmed
  all three outcomes; that correction is preserved without a redundant edit.
- PR #1093 merged on 2026-10-23. The current install and launch topics already
  describe native deterministic work and refusal of agent sessions pending
  `windows-native/03-interactive-coga-launch-on-native-windows`.
- Pushed `663c4f0b0b53b346ea66624785cfd8180ee78faf` to the recorded branch
  after rebasing onto `fbba20518ac88e4af4f84e184a172d3a92d00270` and rerunning
  the full suite. Incoming changes were ticket/log updates only. Final fetch
  found no further movement; the checkout returned to clean, current `main`
  before writing this handoff. No PR has been opened.
- No unresolved implementation questions or adjacent product bugs found.
  The final reviewed revision and refreshed preparation record are below.

## Verification history

The pre-rebase tested revision was
`44fcf860cc773b7d74f62e0c89e7216da62a5365`, based on
`23cea35cd65bdb442cb7cc1f32c7b42dfed7494a`. Tests ran before committing;
the staged tested tree and that commit's tree were both
`cf4fb7f282c88c0c840f75c4c468a271c0838f2a`, confirming identical content.

- `env PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest`
  exited 1: **1413 passed, 10 skipped, 2708 errors in 204.09s**. `/tmp`
  exhausted its inode limit (1,048,543 used of 1,048,576), causing fixture
  setup errors and preventing new sandbox commands from starting. With
  approval, removed only this run's `/tmp/pytest-of-n/pytest-92` scratch
  directory and moved subsequent test scratch space to the main filesystem.
- `env TMPDIR=/home/n/.codex/coga-current-direction-tests.bwtAo3 PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -x --tb=short`
  exited 0 on the same pre-rebase content: **4121 passed, 10 skipped in
  474.35s**. No source change was needed to resolve the environmental failure.

- The implement step also reran the same full-suite command on
  `663c4f0b0b53b346ea66624785cfd8180ee78faf`, based on
  `fbba20518ac88e4af4f84e184a172d3a92d00270`: **4121 passed, 10 skipped in
  489.13s**. Its whitespace check also passed.

These implementation results are historical. Current review and check receipts
cover the subsequently rebased head below.

## Peer review

- **Completed, 2026-10-27:** Codex directly reviewed the final one-file diff
  at head `3053555a6933aa286301828dfd299257acb5998c`, base
  `492924ed72d2e56f2889b4b134d2c6421c3a9ab4`. This is **self-review**:
  the actual implementer was also Codex. The fresh review session and the
  configured Claude identity do not establish independent authorship.
- **No must-fix findings.** The Windows summary matches the owning install
  and launch topics and the native platform gates in `launch.py`; `git.py`
  delegates locking to the guarded imports in `oscompat.py`. Both topic links
  resolve, including the launch anchor. The obsolete rationale is absent.
  This local-only context needs no packaged twin, fixture or runtime edit.
- Rechecked GitHub metadata: #1093 and #1096 merged, and their merge commits
  are ancestors of this branch. #1046 merged; #1058 and #1059 closed unmerged.
  The existing Retro correction from `5738ca646` is preserved. The interactive
  Windows task remains at its owner-held review-design gate.
- Rebased onto current main before review; incoming changes were this ticket
  and the log only. `git range-diff` confirms the implementation patch is
  unchanged. The required full suite passed on the final head: **4121 passed,
  10 skipped in 472.37s**, Linux/Python 3.12.12. Whitespace checks passed.
  No interactive surface changed, so no terminal exercise was applicable;
  native Windows and Python 3.11 were not exercised.
- Final fetch found no further movement. Pushed the final head with an explicit
  lease and returned to clean, current `main` before writing this handoff.
  Recommendation: **skim**, with the self-review and platform limits disclosed.
  No PR has been opened; the next step can publish from the prepared record.

## PR

```yaml
title: Update native Windows direction after the core port
author: codex
author_evidence: >-
  Codex implemented this change in the earlier implement session, overriding
  the ticket's configured Claude identity; see Implement handoff.
head: 3053555a6933aa286301828dfd299257acb5998c
base: 492924ed72d2e56f2889b4b134d2c6421c3a9ab4
depth: skim
rationale: >-
  Bounded documentation correction checked against the owning contracts and
  merged history, with no must-fix findings and a passing full suite after
  reconciliation. Skim the wording and disclosed limits: review was by Codex,
  the same actual agent identity as the implementer, so it is self-review.
implementation: >-
  Replaces the obsolete unsupported-Windows and fcntl explanation with the
  landed core-port posture, retains the interactive-session dependency and
  WSL qualification, links both owning user topics, and updates the topic date.
deviations: >-
  Item 2 was already corrected on main by 5738ca6468de56540b060f8ef86656575a9c19b0;
  its wording is preserved. No runtime, fixture or packaged-copy changes.
limitations: >-
  Verification ran on Linux with Python 3.12.12. Native Windows and Python 3.11
  were not exercised in this session; this change summarizes existing contracts.
  No independent review was performed: both the actual implementer and this
  fresh direct reviewer were Codex. No interactive surface changed.
files:
  docs/contexts/coga-dev/current-direction/SKILL.md: >-
    Correct the stale native Windows direction and update its date, keeping
    detailed support contracts owned by coga/install and coga/launch.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 3053555a6933aa286301828dfd299257acb5998c
  base: 492924ed72d2e56f2889b4b134d2c6421c3a9ab4
  detail: >-
    Direct review completed on the final rebased diff with no must-fix findings.
    Checked both owning user contracts, their links, native platform guards,
    the merged prerequisite and the already-landed Retro correction. Actual
    author and reviewer are both Codex; this is self-review, not independent review.
checks:
  - command: env TMPDIR=/home/n/.codex/coga-current-direction-peer.7gRAbR PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -x --tb=short
    status: passed
    head: 3053555a6933aa286301828dfd299257acb5998c
    base: 492924ed72d2e56f2889b4b134d2c6421c3a9ab4
    detail: >-
      4121 passed, 10 skipped in 472.37s on the final committed head after
      reconciliation. Linux/Python 3.12.12; working tree remained clean.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: 3053555a6933aa286301828dfd299257acb5998c
    base: 492924ed72d2e56f2889b4b134d2c6421c3a9ab4
    detail: Exit 0; no whitespace errors in the one-file feature diff.
  - command: coga validate --json
    status: not-run
    detail: >-
      Documentation-only correction; no config, workflow, task-model or
      validation behavior changed, so standalone validation is not required.
```
