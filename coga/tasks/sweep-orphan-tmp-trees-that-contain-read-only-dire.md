---
title: Sweep orphan tmp trees that contain read-only directories
status: draft
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: open-branch
    skills: []
    assignee: agent
    requires: branch
    run: git/open-branch
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: push-and-open-pr
    skills: []
    assignee: agent
    requires: pr
    run: git/push-and-open-pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (open-branch)
---

## Description

Launch sweeps orphaned launch tmp areas under `coga/.coga/tmp/<token>/` with plain `shutil.rmtree` (`_remove_tree` in `src/coga/run_state.py`). When a dead launch left a read-only directory behind, the sweep fails with `[Errno 13] Permission denied` on every entry inside it, then `[Errno 39] Directory not empty` up the tree. It retries on every later launch, printing about 14 warnings each time until a human runs `chmod -R u+w` and deletes the area.

Observed 2026-11-23: a launch ran pytest with `$TMPDIR` inside its tmp area. `test_installed_wheel_init_and_*` left `company/coga/bootstrap/recurring-promote/` as `dr-xr-xr-x`, which blocked the sweep on `coga launch` and `coga chat` until the area was removed by hand.

### Requirements

- `_remove_tree` handles permission failures. When a delete fails because the parent directory is not writable, make that directory (and the entry, if it is a directory) owner-writable and retry. Only report what still fails after the retry. Never follow symlinks out of the tmp area while changing permissions.
- A remaining failure produces one concise warning per orphan area, not one line per file and ancestor.
- Add a regression test: an orphan tmp area that contains a read-only subdirectory holding files is fully removed by `sweep_orphans`, and so is the same layout found by validate's `orphan-tmp` fix.
- Find why `test_installed_wheel_init_and_*` leaves read-only copies of packaged resources (wheel install permissions, or a chmod in the test), and make the test clean up or avoid creating them.
- Update the owning topic for launch tmp/run state if its contract mentions sweep failure behavior.

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
        - name: open-branch
          run: git/open-branch               # Local-first skill directory containing run.py.
          assignee: agent
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (open-branch)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
A workflow run: selects a script for its step. A sibling ticket.py supplies the default script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

The recurring runner writes delegate on materialized period tickets. It
names the parent template's frozen bootstrap/<name> target.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev records branch:, base:, remote:, reviewed: (the commit OID),
and pr: (the full /pull/ URL). Write one field per line and omit unknown
values. coga/git owns the fields and the workflow that writes them.

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
