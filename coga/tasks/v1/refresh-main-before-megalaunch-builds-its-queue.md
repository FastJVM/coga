---
title: Refresh main before megalaunch builds its queue
status: in_progress
owner: nicktoper
contexts:
- coga/megalaunch
- coga/sync
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
launch_generation: pending:e14f9bbd-d3a1-4aca-a8ff-f6fa81197bbe
---

## Description

`coga megalaunch` builds its picker list and queue from the local `coga/tasks/` without refreshing the control checkout first. `coga launch` calls `git.refresh(cfg)` (`src/coga/launch.py`), and so does the recurring runner, but `src/coga/commands/megalaunch.py` goes straight from `load_config` to `_resolve_selection` / `launchable_candidates`, and `run_megalaunch` builds its queue from the same files.

Incident, 2026-11-03 ~10:01 PST, `coga megalaunch --pick` in ~/Code/coga: local `main` was at 14f93052e (Nov 2 15:31), while control had moved on through Nov 2 22:13. The picker offered five tickets as launchable from that state; control had four of them already in_progress (steps 4–6) and had deleted v1/04. All five failed: four at the first activation write with 'control copy changed since this checkout last saw it', and v1/05 on its existing megalaunch claim. No state was damaged; the guard did its job. But the run wasted the pick, and the error told the human to run `git checkout origin/main -- <ticket>` and redo edits that never needed redoing.

### Fix

- At the start of `coga megalaunch` (sweep, `--pick`, and `--relaunch`), call `git.refresh(cfg)` before resolving the selection or reading any ticket. If it returns False, stop with a nonzero exit and the reason refresh already printed; do not pick or launch from the stale copy. A feature/detached checkout keeps refresh's existing behavior (fetch only, returns True).
- Git-disabled, non-Git and no-remote repos stay soft-skips, as refresh already handles.
- Update `docs/contexts/coga/megalaunch/SKILL.md` (and its packaged twin) to state the refresh-first rule.
- Regression test with real Git: a peer advances a ticket's status/step on control, the local checkout is behind on main, and megalaunch's candidate list and queue reflect control's state, not the stale local one.

### Relation to other tickets

v1/07 (lifecycle writes read control's ticket before modifying it) reconciles each write against freshly fetched control, but keeps megalaunch's exact-byte proofs unchanged and excludes moving the checkout to current main, so it does not fix the stale picker. v1/06 covers sync failures that leave main diverged. This ticket covers only the missing refresh at megalaunch entry.

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

branch: coga/v1-refresh-main-before-megalaunch

## Notes

- Entry: no prepared checkout; this checkout was on stale `coga/chat-0b453101cbae`
  (behind main, no unique commits; dirty paths all identical to origin/main).
  Switched with `git switch -m main` (merge preserved content), ff to origin/main.

## Handoff (implement)

- `src/coga/commands/megalaunch.py` (`megalaunch`): after config/agent
  validation, calls `git.refresh(cfg)` before `_resolve_selection`; on False
  prints a one-line red notice and exits 1 (refresh already printed the cause).
  Reloads config after refresh, mirroring `launch.py`'s post-refresh reload.
- Tests (`tests/test_megalaunch.py`): `_peer_advances_control_behind_local`
  helper (real Git peer clone advances one ticket to done and another to its
  owner step); `test_megalaunch_pick_offers_control_state_not_stale_checkout`,
  `test_megalaunch_queue_reflects_control_state_not_stale_checkout[sweep|relaunch]`,
  `test_megalaunch_stops_when_refresh_cannot_level_control`. All four fail with
  the refresh call disabled.
- Docs: new "Refresh first" section in `coga/megalaunch`; `coga/checkouts`
  "Which checkout you invoke Coga from" bullet updated. Twins copied byte-identical.
- Adjacent observation, not fixed (out of scope per ticket): today's
  megalaunch ran in a checkout left on `coga/chat-0b453101cbae` (a stale chat
  branch, behind main). refresh treats that as a feature checkout (fetch only),
  so this fix would not have refreshed it. Possible follow-up: megalaunch could
  refuse or warn when not on the control branch.

## Peer review

- Completed an independent direct Codex review of head `7b58e175c6b218ee244f19aa72db52e35f0a6ee9` against
  base `78d6c065669155aec7bd100ebb97554eeb3db6e7`. Claude Opus 5.5 implemented the change; Codex reviewed it
  in this fresh session and made no implementation edits. No must-fix findings.
- Reviewed all six diff paths, refresh-before-read ordering, failure handling,
  configuration reload, real-Git status/step regressions, and the existing
  feature/detached and soft-skip contracts. Both packaged topics match their
  canonical copies byte-for-byte.
- Rebased onto current main, including recurring-job state and its retire
  worklist, and re-reviewed the resulting diff. The implementation patch was
  unchanged. The final full-suite run passed: 4310 passed, 10 skipped in
  783.20s on Linux/Python 3.12.12; exact commands and revisions are below.
- Drove the actual picker in real PTYs at 100x24 and 60x10 from stale control
  checkouts. Only the owner-held step-2 ticket appeared; the completed ticket
  disappeared. Space/Enter produced a human-gate skip with no launch, and
  Space/q canceled cleanly in the narrow terminal. A diverged control checkout
  printed the refresh reason and exited 1 before the picker, preserving HEAD
  and ticket bytes. Disposable fixtures disabled Slack and spawned no agents.
- Pushed the final branch with `--force-with-lease` and returned this checkout
  to clean current main before writing the handoff. The next step is the
  mechanical PR publication; the preparation below recommends `skim` and
  records the intended feature/detached-checkout limitation.

## PR

```yaml
title: Refresh control before megalaunch builds its queue
author: claude
author_evidence: The implement handoff records Claude Opus 5.5; the implementation commit
  also carries the Claude Opus 5.5 co-author trailer. Codex performed this fresh peer-review
  session and authored no implementation changes.
head: 7b58e175c6b218ee244f19aa72db52e35f0a6ee9
base: 78d6c065669155aec7bd100ebb97554eeb3db6e7
depth: skim
rationale: Bounded command-entry change reuses the existing Git refresh contract. Independent
  direct review, real-Git regressions, the full suite and real-terminal checks verify the
  change. Read the feature/detached-checkout limitation before merging.
implementation: Megalaunch refreshes control before sweep, picker or saved-selection ticket
  reads, reloads configuration, and stops with exit 1 when refresh returns False. Real-Git
  tests cover peer status/step changes across pick, sweep and relaunch; both owning guidance
  topics and their packaged twins are updated.
deviations: None. The configuration reload follows the existing launch pattern. The checkouts
  guidance is aligned with the new megalaunch rule.
limitations: Feature and detached checkouts retain fetch-only behavior and queue from their
  own files, as requested. Verification ran on Linux/Python 3.12.12; Python 3.11 and Windows
  were not run. Terminal fixtures disabled Slack and did not spawn an agent.
files:
  src/coga/commands/megalaunch.py: Refresh before selection and queue reads, stop on failure,
    and reload configuration.
  tests/test_megalaunch.py: Real-Git regressions for pick, sweep and relaunch, plus the failed-refresh
    short circuit.
  docs/contexts/coga/megalaunch/SKILL.md: Own the refresh-first rule and its existing soft-skip
    and feature-checkout limits.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md: Ship the
    byte-identical megalaunch topic.
  docs/contexts/coga/checkouts/SKILL.md: Align invoking-checkout guidance and link the owning
    refresh-first contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: Ship the byte-identical
    checkout guidance.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 7b58e175c6b218ee244f19aa72db52e35f0a6ee9
  base: 78d6c065669155aec7bd100ebb97554eeb3db6e7
  detail: Direct review completed after the final rebase. Inspected all six diff paths, command
    ordering, the shared refresh contract, regression coverage, and canonical/package pairs.
    No must-fix findings or implementation edits; the final patch is unchanged by rebase.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q -p no:cacheprovider
  status: passed
  head: 7b58e175c6b218ee244f19aa72db52e35f0a6ee9
  base: 78d6c065669155aec7bd100ebb97554eeb3db6e7
  detail: 4310 passed, 10 skipped in 783.20s (13:03), on Linux/Python 3.12.12 after the final
    rebase.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-refresh-peer-review-wu4yjvf_/run.py
    final-wide 24 100
  status: passed
  head: 7b58e175c6b218ee244f19aa72db52e35f0a6ee9
  base: 78d6c065669155aec7bd100ebb97554eeb3db6e7
  detail: Real PTY, 100 columns by 24 rows, with a bare remote and peer checkout advancing
    two tickets. Only the in_progress owner-held step appeared; the done ticket was absent.
    Space and Enter selected it; the run skipped the human gate, launched zero agents, and
    exited 0.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-refresh-peer-review-wu4yjvf_/run.py
    final-narrow 10 60
  status: passed
  head: 7b58e175c6b218ee244f19aa72db52e35f0a6ee9
  base: 78d6c065669155aec7bd100ebb97554eeb3db6e7
  detail: Real PTY, 60 columns by 10 rows, starting behind the same peer transitions. The
    refreshed row, cursor and checkbox remained visible; Space toggled and q canceled with
    exit 0. Long fields truncated within their cells.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-refresh-peer-review-wu4yjvf_/run.py
    final-failure 24 100
  status: passed
  head: 7b58e175c6b218ee244f19aa72db52e35f0a6ee9
  base: 78d6c065669155aec7bd100ebb97554eeb3db6e7
  detail: 'Real PTY with diverged main and an unpublished code commit. Exit 1 was expected
    and observed: the refresh reason and no-work notice appeared before any picker. Local
    HEAD and ticket bytes were preserved.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 7b58e175c6b218ee244f19aa72db52e35f0a6ee9
  base: 78d6c065669155aec7bd100ebb97554eeb3db6e7
  detail: No whitespace errors.
```
