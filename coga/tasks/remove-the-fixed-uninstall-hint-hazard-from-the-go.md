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
step: 2 (peer-review)
agent: claude
launch_generation: e5bb8611-b44d-4e97-9106-cd9cac35b996
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

## PR

```yaml
title: Drop fixed uninstall-hint hazard from the gotchas topic
author: claude
author_evidence: Implement session ran as claude (claude-opus-5-5) under megalaunch.
head: 4193ca024b9e33e0e20c18fafd18c3574e5696a9
base: 08033154298c2f99dbb04c0a271547912ec62776
depth: skim
rationale: Eight-line deletion of a stale "Known open" bullet in a local-only dev topic; the fix it described landed in bd4b557b4.
implementation: Removes the gotchas bullet that named v1/15 as owner of the POSIX-only uninstall recovery hint; the code now renders PowerShell hints on native Windows and coga/uninstall documents both syntaxes.
deviations: None.
limitations: Docs-only; no behavior change. The suite still has 3 failures already on main from a README link to a deleted ticket (tracked by make-retro-check-inbound-doc-links-before-deleting).
files:
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: Delete the stale uninstall-hint "Known open" bullet.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Code review has not run yet; the peer-review step follows.
checks:
  - command: .venv/bin/python -m pytest -q
    status: failed
    head: 4193ca024b9e33e0e20c18fafd18c3574e5696a9
    base: 08033154298c2f99dbb04c0a271547912ec62776
    detail: '3 failed, 4763 passed, 33 skipped in 671.88s; Pop!_OS 24.04 LTS, Linux 7.2.15, Python 3.12.12. All 3 failures already exist on main: test_context_navigation_has_no_broken_links and both test_final_package_edits_never_escape_a_mutating_cli_sweep cases, from the README link to deleted document-the-remedy-for-a-bloated-blackboard-sibli.md.'
```
