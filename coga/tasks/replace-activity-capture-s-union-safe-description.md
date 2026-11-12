---
title: Replace activity-capture's union-safe description of log publication
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
---

## Description

Filed by Dream run recurring/dream, period 2026-W46 (run 20261112T051938Z), Phase 6 disposition. Finding from Phase 2 (ks-18, stale), held as a draft because open Retro PR #1200 already edits the target docs/contexts/coga-dev/internals/activity-capture/SKILL.md without carrying this fix; handle after #1200's review.

The 'Capture point and gates' bullet says teardown publishes the log 'through git.sync_log (its union-safe path)'. The shipped src/coga/resources/templates/coga/.gitattributes sets /log.md -merge (only **/retires.md stays merge=union); git.sync_log is a plain publish(..., require_paths=[path]); the log lands through the event-aware log_publication.reconcile path owned by coga-dev/internals/spool-merge ('The audit log is no longer a union path'). Replace the phrase with a link to that section.

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

branch: replace-activity-capture-s-union-safe-description

## Handoff (implement)

- Changed `docs/contexts/coga-dev/internals/activity-capture/SKILL.md`
  ("Capture point and gates" bullet): dropped "(its union-safe path)"; now says
  the log is not a union path and lands through the event-aware publisher,
  linking `../spool-merge/SKILL.md#mergeunion-files` (the "`merge=union` files"
  section that states "The audit log is no longer a union path").
- PR #1200 (still open) edits the same file but not this bullet; no textual
  overlap expected.
- Pre-existing failures on origin/main fc756a9cd (reproduced there, unrelated):
  `tests/test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep[dirty-package]`,
  `[committed-package]`, and
  `tests/test_packaging.py::test_context_navigation_has_no_broken_links`
  (README.md links missing `coga/tasks/document-the-remedy-for-a-bloated-blackboard-sibli.md`).
- Env note: system `python` lacks `tomlkit`; tests ran with `.venv/bin/python`.

## Peer review

- Codex direct independent review **completed**; implementation was by Claude
  (implement handoff and commit co-author evidence). No must-fix findings.
- Covered final head `a0b3158ce63a6df9bad80a3188944b43bc601a0d` against base
  `59c86aaa37d1cf214d34527b5657190af51a51c4` after rebasing onto fetched main.
  Verified the wording against `git.sync_log`, the event-aware publisher,
  shipped `.gitattributes`, and the owning spool-merge topic; all links and
  anchors in the changed topic resolve. PR #1200 is still open and edits
  separate paragraphs without overlap.
- Full Linux suite: 4763 passed, 33 skipped, 3 failed in 708.88s on
  Pop!_OS 24.04 LTS, Python 3.12.12. All failures trace to the existing
  missing README ticket link documented in the implement handoff, including
  both nested publication checks. Exact receipts are below.
- No interactive terminal, rendering, or native Windows check is applicable:
  only local developer-topic prose changed. No code, fixture, or new test needed.
- Rebasing needed no conflict resolution or review fixes. Pushed with
  `git push --force-with-lease origin replace-activity-capture-s-union-safe-description`.
  Final fetch confirmed main unchanged; returned the checkout to clean main
  before writing this handoff. Next step is mechanical PR publication.

## PR

```yaml
title: Drop union-safe wording for activity-capture log publication
author: claude
author_evidence: Implement handoff identifies Claude Opus 5.5; the implementation commit retains its Claude
  Opus 5.5 co-author trailer. Codex performed this fresh peer-review session.
head: a0b3158ce63a6df9bad80a3188944b43bc601a0d
base: 59c86aaa37d1cf214d34527b5657190af51a51c4
depth: deep
rationale: Bounded documentation correction with completed independent review and passing page-link validation.
  Deep is required because the full suite and repository-wide navigation check have existing failures;
  no must-fix finding concerns this diff.
implementation: Replaces the stale union-safe claim with a brief description of event-aware log publication
  and a link to the owning spool-merge section.
deviations: None.
limitations: Full suite remains red due to the pre-existing missing README ticket link. No runtime behavior
  changed; interactive and native Windows checks do not apply to this documentation-only diff.
files:
  docs/contexts/coga-dev/internals/activity-capture/SKILL.md: Corrects the stale union-safe description
    and links to the owning event-aware publication contract.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: a0b3158ce63a6df9bad80a3188944b43bc601a0d
  base: 59c86aaa37d1cf214d34527b5657190af51a51c4
  detail: 'Direct review completed on the final rebased diff; no must-fix findings. Checked sync_log,
    the shared publisher and log_publication.reconcile, shipped Git attributes, and the linked contract.
    PR #1200 remains open and edits separate paragraphs with no overlap. No runtime or rendered UI surface
    changed.'
checks:
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest -q
  status: failed
  head: a0b3158ce63a6df9bad80a3188944b43bc601a0d
  base: 59c86aaa37d1cf214d34527b5657190af51a51c4
  detail: 'Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.12.12: 4763 passed, 33 skipped,
    3 failed in 708.88s. Failures: tests/test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep[dirty-package],
    [committed-package], and tests/test_packaging.py::test_context_navigation_has_no_broken_links. All
    three trace to the existing missing README ticket link document-the-remedy-for-a-bloated-blackboard-sibli.md;
    identical to the implement baseline reproduced on fc756a9cd. Only task/log state changed on main since
    that baseline.'
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest -q tests/test_packaging.py::test_context_navigation_has_no_broken_links
  status: failed
  head: a0b3158ce63a6df9bad80a3188944b43bc601a0d
  base: 59c86aaa37d1cf214d34527b5657190af51a51c4
  detail: 1 failed in 0.65s; only problem is the existing missing README ticket link, not the changed
    activity-capture page.
- command: 'PYTHONPATH=/home/n/Code/coga/src:/home/n/Code/coga/tests .venv/bin/python -c ''from pathlib
    import Path; from test_packaging import _context_link_problems; problems = _context_link_problems(Path("/home/n/Code/coga/docs/contexts/coga-dev/internals/activity-capture/SKILL.md"));
    assert not problems, problems; print("Activity-capture links and anchors: passed")'''
  status: passed
  head: a0b3158ce63a6df9bad80a3188944b43bc601a0d
  base: 59c86aaa37d1cf214d34527b5657190af51a51c4
  detail: All links and heading anchors in the changed activity-capture topic resolve, including spool-merge#mergeunion-files.
- command: git diff --check main...HEAD
  status: passed
  head: a0b3158ce63a6df9bad80a3188944b43bc601a0d
  base: 59c86aaa37d1cf214d34527b5657190af51a51c4
  detail: No whitespace errors.
```
