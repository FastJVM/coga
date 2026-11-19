---
title: Maintain ticket blackboards
status: in_progress
owner: nicktoper
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
    checkout: reuse-required
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 2 (self-qa)
agent: claude
---

## Description

Filed by Dream in 2026-W46 (run 20261112T051938Z) as `validate-drift: large-blackboard`. The initial report identified a 36.8 KiB blackboard on `v1/20-ask-which-agents-to-enable-during-coga-init`. That ticket is now done. It is the example that exposed the missing maintenance process.

### Detect oversized blackboards

Add a dedicated recurring task, independent of Dream. Use the existing `large-blackboard` findings from `coga validate --json` to report the affected tickets, their sizes, and the current 32 KiB threshold. The alert is informational. Oversized blackboards can be exceptional, and an alert does not create a mandatory review or block work.

### Remove stale notes during normal ticket work

Add a blackboard cleanup instruction to the agent workflow. Whenever the agent loads or resumes a ticket, it checks the blackboard as part of reading it and removes notes that clearly no longer help the work. This is a light pass during normal ticket work and requires no separate review step. Age is a cue to check usefulness. Keep current decisions and rationale, active blockers, the worklist, and verification evidence still needed for handoff. Obsolete notes can be deleted directly. Update the owning `coga/blackboard` topic and the agent instructions that apply the policy.

### Completion

Deliver both behaviors in this ticket.

- Run the dedicated recurring task against a fixture with a blackboard above the threshold and one below it. Verify that only the oversized blackboard is reported, with its ticket ref, measured size, and threshold.
- Verify that the normal agent prompt includes the cleanup instruction when loading or resuming a ticket. Walk through a sample blackboard containing obsolete notes and information still needed for handoff, and confirm the instruction supports removing the former and retaining the latter. Update the owning blackboard topic alongside the prompt.
- Use fixtures for verification and leave the completed agent-selection ticket as the original example.

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
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
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

branch: coga/maintain-ticket-blackboards

## Handoff (implement, 2026-11-19)

Implemented on `coga/maintain-ticket-blackboards` (commit `0089457`, pushed). No PR yet.

- **Detection.** Bundled script-backed recurring job `blackboard-size` (`src/coga/resources/templates/coga/recurring/blackboard-size/{ticket.md,ticket.py}`, workflow `bootstrap/workflows/blackboard-size/run.md`, Mondays 08:00). Its edge `ticket.py` imports only shared core infra (`runner.run_entry`, `blackboard.append_blackboard_report`, `notification.post`, `task_env.blackboard_from_env`). It subprocesses `coga validate --json`, keeps `large-blackboard` findings and writes `## Oversized blackboards` (ref, size, threshold) to the period blackboard. When something is flagged it posts one non-important FYI with `fatal=False`. It always bumps, and nothing is filed or blocked. Not in `runner.RECIPES` (microkernel: single consumer).
- **Decision: size and threshold are parsed from the finding message.** The validate JSON `Issue` has no structured size fields. `test_reads_size_and_threshold_from_the_validator_warning` pins `blackboard.blackboard_size_warning`'s format, and an unreadable finding raises rather than being dropped. Adding structured fields to `validate.Issue` would be the cleaner core change if wanted.
- **Selection.** Added to `commands/update.FRESH_RECURRING_SELECTION` (owner review decides that default list; flag in PR) and to this repo's `coga/recurring/jobs.toml`. Lazy state carrier approved in `tests/test_packaging.py`.
- **Cleanup.** `src/coga/resources/prompt-ticket.md`, loop step 1: delete clearly obsolete notes on load/resume. Age is only a cue. Keep decisions+reasons, open blockers, worklist and handoff verification. Never delete `## Dev`/`## Blockers`/`## Blocker reminders`/`## PR`/`## Superseded designs`. If unsure, keep the note. Owning topic `coga/blackboard` gains "Stale-note cleanup", and "Size and its remedy" names the job. `coga/notifications/producers` lists the FYI.
- **Walkthrough (completion criterion 2).** Sample blackboard: (a) "Plan: try approach X" after X was replaced and nothing relies on its rationale, (b) "tests running…" status, (c) a ruled-out dead end, (d) "Decision: parse message because Issue lacks fields", (e) an open `## Blockers` ask, (f) the remaining worklist, (g) the full-suite receipt the PR record needs. The instruction deletes (a)-(c) as superseded plan, stale status and dead end. It keeps (d) as decision+reason, (e) as open blocker and CLI section, (f) as worklist, and (g) as handoff verification. This handoff applied it: the finished `## Plan` was replaced.
- **Verification.** Live-repo dry render flags `recurring/dream` 39.5 KiB, `v1/14-…` 49.3 KiB, and `v1/20-ask-which-agents-to-enable-during-coga-init` 36.8 KiB (the original example, left untouched).
- **Follow-up for owner / retro (not done here).** Dream's validate-drift still classifies `large-blackboard` as human-needed (`dream_validate_drift.py`), so live oversized tickets can be reported twice. Decide whether Dream should defer to this job. Also, the shell's `python`/`coga` (uv tool) lacks `tomlkit` for tests; use `.venv/bin/python`.

## PR

```yaml
title: Report oversized blackboards weekly and prune stale notes on read
author: claude
author_evidence: >-
  Implement session ran as Claude Opus 5.5 (claude-opus-5-5) in a megalaunch queue.
head: 008945777714511550555ca7037892e1c6c2539c
base: 052daf10b64a631ef5a85c721adda00113224a8c
depth: deep
rationale: >-
  Adds a new bundled recurring job selected by default for fresh repos (owner
  review decides that list) and changes the shipped ticket-loop prompt that
  every agent session composes; no review has run yet.
implementation: >-
  New package-owned recurring template blackboard-size with an edge ticket.py
  that reports coga validate --json large-blackboard findings (ref, size,
  threshold) to the period blackboard and as one non-fatal FYI, then bumps.
  Ticket-loop step 1 now instructs a light stale-note cleanup on load or
  resume; coga/blackboard owns the policy in a new Stale-note cleanup section.
deviations: >-
  None from the ticket. Size and threshold are parsed from the finding message
  because the validate JSON has no structured size fields; a test pins the format.
limitations: >-
  Dream validate-drift still files large-blackboard as human-needed, so a live
  oversized ticket can surface in both places. The cleanup pass is prompt
  guidance; its judgment was checked by walkthrough, not automated.
files:
  coga/recurring/jobs.toml: Select the new bundled job in this repo.
  src/coga/commands/update.py: Add blackboard-size to the fresh-repo recurring selection.
  src/coga/resources/prompt-ticket.md: Instruct the stale-note cleanup pass when loading or resuming a ticket.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: >-
    Own the stale-note cleanup policy and name the size report job.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/producers/SKILL.md: >-
    Inventory the new job's informational FYI.
  src/coga/resources/templates/coga/bootstrap/workflows/blackboard-size/run.md: One-step workflow for the script-backed period.
  src/coga/resources/templates/coga/recurring/blackboard-size/ticket.md: Template contract and schedule for the size report.
  src/coga/resources/templates/coga/recurring/blackboard-size/ticket.py: Edge script that reads validate findings and reports them.
  tests/required_package_resources.txt: Require the new package owners.
  tests/test_packaging.py: >-
    Approve the lazy state carrier and run the new job in the installed-wheel smoke.
  tests/test_recurring_state.py: Include the new job in the bundled catalog.
  tests/test_blackboard_size.py: >-
    End-to-end fixture run (one blackboard above and one below threshold),
    message-format pin, and prompt/topic cleanup-clause checks.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: >-
    Implement step; the workflow's self-qa step reviews next.
checks:
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider -x
    status: passed
    head: 008945777714511550555ca7037892e1c6c2539c
    base: 052daf10b64a631ef5a85c721adda00113224a8c
    detail: >-
      5011 passed, 33 skipped in 794.52s. Run on the working tree that was
      committed unchanged as the head (git status clean after commit; rebase was a no-op).
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_blackboard_size.py tests/test_layout_contexts.py
    status: passed
    head: 008945777714511550555ca7037892e1c6c2539c
    base: 052daf10b64a631ef5a85c721adda00113224a8c
    detail: 35 passed.
```
