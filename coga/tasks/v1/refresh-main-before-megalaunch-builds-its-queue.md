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
step: 1 (implement)
agent: claude
launch_generation: 3cdcca1c-1b87-4ae1-925c-b1b89c42b6b8
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
