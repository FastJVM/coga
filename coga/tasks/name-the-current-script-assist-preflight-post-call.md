---
title: Name the current script-assist preflight_post caller in the notifications failures
  topic
status: done
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
agent: claude
---

## Description

Filed by Dream 2026-W43 (recurring/dream, Phase 6; Phase 3 contract-audit shard ca-02, drift). Target: docs/contexts/coga/notifications/failures/SKILL.md and its packaged twin src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/failures/SKILL.md. The preflight_post callers list says 'launch.py _launch — the script-assist setup path', but in src/coga/launch.py the preflight_post(self.cfg) call now lives in _LaunchInvocation._run_initial_script (the initial-script phase _launch coordinates). Fix: name _LaunchInvocation._run_initial_script in both twins, byte-identical. Filed as a draft instead of a proposal PR because open Retro PR #1050 (Slack configuration refusals) edits the same section without carrying this fix; land it after #1050 is reviewed to avoid a conflict.

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
pr: https://github.com/FastJVM/coga/pull/1072
branch: docs-preflight-post-caller

## Handoff (implement)
- Changed the `preflight_post` callers list in `coga/notifications/failures` (both twins, byte-identical): `launch.py` `_launch` -> `launch.py` `_LaunchInvocation._run_initial_script`, noting it is the initial-script phase `_launch` coordinates (`_launch` passes `invocation._run_initial_script` as a phase).
- PR #1050 is still OPEN. Its hunk in this file is `@@ -19,6 +19,13` (top of file); this change is at line ~67, so no text conflict is expected. Ticket asked to land after #1050 is reviewed; open-pr/owner should honor that ordering at merge time.
- No adjacent bugs found.

## Peer review

- Codex completed a direct, independent review on 2026-10-20 in launch
  `a215b83d-db31-4ef2-a21b-8d9be493e74c`. Claude authored the implementation,
  as recorded above and in the commit's co-author trailer; this Codex session
  made no implementation edits. No nested reviewer was invoked.
- Reviewed final head `da6105143715ab1a6fbf2dcbd6e560e35b1ff799` against base
  `6583d275e9ba07e1b2d3a68afd9a5c51a3673048`, after fetching main and rebasing.
  No findings or required fixes. `launch.py` `_LaunchInvocation._run_initial_script`
  contains `preflight_post(self.cfg)` before assist lifecycle writes, and
  `_launch` includes that method in its phase sequence. Both topic copies
  identify the correct caller and remain byte-identical.
- `.venv/bin/python -m pytest` completed on that head/base with **3808 passed,
  7 skipped** in 455.24s under Python 3.12.12, including all 22 packaging
  tests. `git diff --check origin/main...HEAD` and the twin `cmp` passed.
  No interactive terminal or Slack-rendering check applies to this prose-only
  change; no config, workflow, or task-model change requires fixture validation.
- The final fetch confirmed main was unchanged. Force-pushed the rebased
  branch with an explicit lease on its previous remote head; it is one commit
  ahead of main. Loaded control's ticket before writing this handoff. The
  checkout stays on the feature branch for the launcher's return to main
  (`COGA_LAUNCH_RETURNS_CHECKOUT=1`).
- PR #1050 remains open. Its current head
  `4658651e6e31eb56af5a6f4581b4327056d6398e` has a completed automated Codex
  review with no findings; no submitted human review is recorded. Its topic
  hunk is separate from this correction. Preserve the ticket's requested
  landing order after #1050 is reviewed; the owner decides when to merge.

## PR
```yaml
title: Name _LaunchInvocation._run_initial_script as the script-assist preflight_post caller
author: claude
author_evidence: Implement session ran Claude Code (claude-opus-5-5), attended launch f13d35ed-f2dd-48f1-9dc8-702fd672b735.
head: da6105143715ab1a6fbf2dcbd6e560e35b1ff799
base: 6583d275e9ba07e1b2d3a68afd9a5c51a3673048
depth: skim
rationale: >-
  Bounded documentation correction with completed independent review and a
  passing full suite on the final rebased head. Skim the landing-order note
  for PR #1050; runtime behavior is unchanged.
implementation: Renames the script-assist preflight_post caller in the notifications/failures topic and its packaged twin to the method that now holds the call.
deviations: None.
limitations: >-
  Honor the ticket's request to land after PR #1050 is reviewed. That PR remains
  open with a completed automated Codex review on its current head and no
  submitted human review; its hunk in this topic is separate. No interactive
  terminal or Slack-rendering check applies to this prose-only correction.
files:
  docs/contexts/coga/notifications/failures/SKILL.md: Name the current preflight_post caller in the canonical topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/failures/SKILL.md: Keep the packaged bootstrap twin byte-identical.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: da6105143715ab1a6fbf2dcbd6e560e35b1ff799
  base: 6583d275e9ba07e1b2d3a68afd9a5c51a3673048
  detail: >-
    Direct Codex review completed in a fresh peer-review session after rebase,
    independently of Claude's implementation. No findings. Inspected both
    changed topics, the actual preflight_post call, and the phase coordinator.
checks:
  - command: .venv/bin/python -m pytest
    status: passed
    head: da6105143715ab1a6fbf2dcbd6e560e35b1ff799
    base: 6583d275e9ba07e1b2d3a68afd9a5c51a3673048
    detail: 3808 passed, 7 skipped in 455.24s under Python 3.12.12, including all 22 packaging tests, on the committed final head.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: da6105143715ab1a6fbf2dcbd6e560e35b1ff799
    base: 6583d275e9ba07e1b2d3a68afd9a5c51a3673048
    detail: No whitespace errors in the final branch diff.
  - command: cmp docs/contexts/coga/notifications/failures/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/failures/SKILL.md
    status: passed
    head: da6105143715ab1a6fbf2dcbd6e560e35b1ff799
    base: 6583d275e9ba07e1b2d3a68afd9a5c51a3673048
    detail: Canonical and packaged topics are byte-identical after rebase.
```
