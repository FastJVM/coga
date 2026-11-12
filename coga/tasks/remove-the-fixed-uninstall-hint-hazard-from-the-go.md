---
title: Remove the fixed uninstall-hint hazard from the gotchas topic
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
step: 3 (open-pr)
agent: claude
launch_generation: pending:d820f232-bf82-4694-9a84-5206b0b47891
---

## Description

Filed by Dream run recurring/dream, period 2026-W46 (run 20261112T051938Z), Phase 6 disposition. Finding from Phase 2 (ks-27, stale) and Phase 3 (ca-01, drift), held as a draft because open Retro PR #1208 already edits the target docs/contexts/coga-dev/codebase/gotchas/SKILL.md without carrying this fix; handle after #1208's review.

The 'Known open: uninstall recovery hints use POSIX syntax on Windows' bullet names v1/15 as owner. v1/15 is done and the fix landed (bd4b557b4): src/coga/commands/uninstall.py _format_tool_command(..., windows=...) renders $env:K='<literal>'; cmd via _powershell_literal() on native Windows. Delete the bullet (coga/uninstall documents both hint syntaxes).

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

branch: remove-the-fixed-uninstall-hint-hazard-from-the-go

## Handoff (implement)

- Deleted the "Known open: uninstall recovery hints use POSIX syntax on
  Windows" bullet from `docs/contexts/coga-dev/codebase/gotchas/SKILL.md`.
  Verified the fix first: `src/coga/commands/uninstall.py` has
  `_format_tool_command(..., windows=...)` using `_powershell_literal()` on
  `_native_windows()`, and `coga/uninstall` documents the PowerShell
  `$env:UV_TOOL_DIR='<path>'; uv tool uninstall coga` form. No other
  non-archive doc referenced the owner ticket.
- PR #1208 (still open) edits the same file but only appends a bullet at the
  end; the hunks do not overlap.
- Suite has 3 failures that already exist on main, unrelated to this diff: `README.md` links to the deleted
  `coga/tasks/document-the-remedy-for-a-bloated-blackboard-sibli.md`
  (`test_context_navigation_has_no_broken_links` plus both
  `test_final_package_edits_never_escape_a_mutating_cli_sweep` cases, which
  run that test). Already tracked by draft
  `make-retro-check-inbound-doc-links-before-deleting`; siblings recorded the
  same receipt.
- Use `.venv/bin/python`; the shell's `python` lacks `tomlkit`.

## Peer review

- Codex direct independent review **completed**, with no findings. Implementing
  identity is Claude, as recorded in the implement handoff; this session did
  not author the implementation. Reviewed final head `7f30ec67b0e2b211391cd594801c1fa8de82bffd`
  against base `8afa0200426bfa29d116b58ba5df07dd302858ab` after rebasing onto fetched main.
- Inspected the complete branch diff and commit log, neighbouring gotchas,
  `_uninstall_via_tool`, `_format_tool_command`, `_powershell_literal`, the
  existing platform-syntax tests, and the owning `coga/uninstall` topic.
  The change deletes only the stale eight-line bullet; fix `bd4b557b4` is an
  ancestor of main. No other standing topic/resource repeats the stale claim.
  PR #1208 remains open; its unrelated end-of-file addition does not overlap.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q` at the
  reviewed head/base: **3 failed, 4763 passed, 33 skipped in 714.01s**.
  Platform: Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic x86_64,
  Python 3.12.12 (no Python 3.11 floor run). Failures are
  `tests/test_packaging.py::test_context_navigation_has_no_broken_links` and
  both `tests/test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep`
  parameters. All report README's link to deleted
  `document-the-remedy-for-a-bloated-blackboard-sibli.md`.
- Baseline confirmed after returning to main `8afa0200426bfa29d116b58ba5df07dd302858ab`:
  `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_packaging.py::test_context_navigation_has_no_broken_links`
  produced **1 failed in 0.47s**, with that identical broken link. README,
  the affected tests, and uninstall code/docs are unchanged by this branch.
  Existing follow-up: `make-retro-check-inbound-doc-links-before-deleting`.
- `git diff --check main...HEAD` passed at the reviewed head/base. No rendered
  terminal or native Windows run applies to this local-topic deletion; no
  executable/user-facing surface changes. No fixes were needed.
- Final fetch found no main drift. Force-with-lease push completed; primary
  checkout returned clean to main before writing this handoff. The next step
  is mechanical PR opening. Recommend **deep** because the required suite is
  failed, while clearly identifying the unrelated baseline cause.

## PR

```yaml
title: Drop fixed uninstall-hint hazard from the gotchas topic
author: claude
author_evidence: Implement session ran as claude (claude-opus-5-5) under megalaunch; preserved from implement
  handoff.
head: 7f30ec67b0e2b211391cd594801c1fa8de82bffd
base: 8afa0200426bfa29d116b58ba5df07dd302858ab
depth: deep
rationale: Bounded eight-line deletion with completed independent review and no findings; deep because
  the required full suite has three failures from the existing broken README link.
implementation: Removes the stale gotchas bullet naming v1/15 as owner of POSIX-only uninstall recovery
  hints. The fix already renders PowerShell hints on native Windows; coga/uninstall owns both syntaxes.
deviations: None.
limitations: Documentation only; no behavior change. Required suite has three existing failures from README
  linking a deleted ticket, independently reproduced on main and tracked by make-retro-check-inbound-doc-links-before-deleting.
  Linux Python 3.12.12 only; native Windows and Python 3.11 were not run for this local-topic deletion.
files:
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: Delete the obsolete uninstall-hint Known open bullet.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 7f30ec67b0e2b211391cd594801c1fa8de82bffd
  base: 8afa0200426bfa29d116b58ba5df07dd302858ab
  detail: 'Direct independent review completed on the final rebased diff with no findings. Verified the
    landed fix, owning topic, existing syntax tests, and non-overlap with PR #1208; see Peer review.'
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q
  status: failed
  head: 7f30ec67b0e2b211391cd594801c1fa8de82bffd
  base: 8afa0200426bfa29d116b58ba5df07dd302858ab
  detail: 3 failed, 4763 passed, 33 skipped in 714.01s; Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic
    x86_64, Python 3.12.12. Navigation and both final-package-publication parameters fail only on the
    existing README link to deleted document-the-remedy-for-a-bloated-blackboard-sibli.md. The same navigation
    failure was reproduced on main; see Peer review.
- command: git diff --check main...HEAD
  status: passed
  head: 7f30ec67b0e2b211391cd594801c1fa8de82bffd
  base: 8afa0200426bfa29d116b58ba5df07dd302858ab
  detail: No whitespace errors.
```
