---
title: Publish sibling ticket handoffs during targeted authoring
status: draft
owner: nicktoper
workflow: code/with-review
---

## Description

Targeted `coga ticket <slug>` authoring can detect edits to another ticket
but omit them from its guarded validation and publication, leaving their
durability to a later best-effort sweep. Include tickets authored during the
interview in the finalization boundary and investigate why the observed
cancellation handoff escaped the later sweep. Done means a targeted interview
that updates a sibling publishes the valid changes together, validates all
selected tickets before publishing any part of the finalizer's transaction,
and a cancellation/teardown regression proves the handoff is published or the
command reports retained state explicitly. Preserve the existing lifecycle,
checkout, and human-gate rules; this work does not authorize executing the
sibling ticket's workflow.

## Context

### Incident and recovery

On 2026-10-28, the attended interview for
`show-which-agents-are-available-on-the-machine-dur` wrote a human-approved
handoff under `## Open Questions` in
`marketing/fix-installer/ask-which-agents-to-enable-during-coga-init`, then ran
`coga mark canceled` on the duplicate. The successor was at its owner design
review; the handoff raised wording about agents outside built-in discovery,
without changing the approved requirements or resolving design findings.

The cancellation reached control in `3831c8502`, and the session usage record
in `2b0e4e4d5` reported exit code 0 and exit kind `done`. The next interview
found the successor's 11-line handoff still dirty on `main` and absent from
`origin/main`. The prior agent transcript shows the cancellation command
returning a running tool-session ID rather than a completed exit before
the agent session ended; this is timing evidence, not proof of the whole
failure mechanism. Both affected tickets validated after cancellation.

The human requested investigation and repair. The handoff was preserved,
then published with `coga run publish-state` requiring its absolute path.
Commit `d294c0956` contains the recovered note; the working tree was verified
clean and the successor matched `origin/main`. Do not replay cancellation
or modify the successor's workflow to recover this incident.

### Confirmed gap and remaining uncertainty

- In `src/coga/authoring.py`, `changed_authoring_paths` detects the sibling
  change, but `finalize_authored`'s `TaskRef` branch selects only the named
  target for `authored_refs` and `task_sync_paths`. `support_paths` excludes
  the whole tasks tree, so it cannot carry the sibling. The `BootstrapRef`
  path instead uses `authored_task_refs` to discover authored tickets.
- Deterministic reproduction: in a disposable configured repo, create two
  valid tickets, snapshot with `snapshot_authoring_state`, change only the
  second ticket, and call `finalize_authored` with the first ticket's
  `TaskRef`. A spy on `git.publish` observes **zero calls**, although
  `changed_authoring_paths` includes the second ticket. This reproduces the
  finalizer omission independently of any concurrent process.
- A complete isolated `python -m coga.cli ticket duplicate --agent codex`
  run with a stub agent that edits a sibling, invokes `mark canceled`, and
  waits did publish the sibling and exit cleanly. The ordinary sweep can
  therefore mask the omission. The exact reason the live sweep missed the
  note remains unproven; retain this distinction and reproduce the relevant
  timing/refusal path before claiming the incident's full cause is fixed.
- Inspect `commands.ticket._run_authoring_session`,
  `commands.mark.canceled`, `launch.spawn_agent_session`,
  `repl_supervisor.run_with_done_marker`, and `cli._sweep_coga_state` for the
  cancellation-to-finalization boundary. The done marker is emitted before
  the child CLI's final sweep; supervisor teardown signals the process group.
  Preserve intentional withholding after validation/publication refusal.

### Scope and verification

Cite `coga/state-publication`
(`docs/contexts/coga/state-publication/SKILL.md`) rather than attach it; read
"When Coga publishes" and "Strict publication on demand". Guided authoring
owns a guarded publish of authored state, and publication refusal retains
edits with a nonzero result. Update this owner and its packaged twin if the
contract changes. Cite `coga-dev/internals/state-publication`
(`docs/contexts/coga-dev/internals/state-publication/SKILL.md`), sections
"The end-of-command sweep" and "Guided-authoring finalization", for the
implementation explanation and update it with the fix. For teardown, cite
`coga-dev/internals/agent-spawn`
(`docs/contexts/coga-dev/internals/agent-spawn/SKILL.md`), section "The
supervisor", rather than attach it: a `done` outcome describes how the agent
was stopped, not proof that the child CLI finished its sweep. Update that
owner if supervisor behavior changes.

The no-partial-publication guarantee applies to the finalizer's own
transaction. Earlier lifecycle commands and their sweeps can already have
published state; an authorized cancellation must not be rolled back. Test an
invalid authored sibling followed by cancellation and record which writes
precede finalization, without claiming the finalizer prevented earlier
publication. A broader change to sweep isolation or supervisor design needs
a separate design decision if the investigation proves it necessary.

Extend `tests/test_authoring.py` and appropriate command/supervisor coverage
for an unchanged or canceled target plus an edited sibling, an invalid
authored sibling, and canceled-session teardown. Consider new/deleted tickets,
attachments, and file-to-directory promotion when adjusting selection.
Snapshot-based selection must not silently absorb unrelated pre-existing
edits into the authored transaction. Use isolated local Git remotes and stub
agents; do not require Slack, real agent credentials, or network services.
Record exact commands and results and keep the fixture-interpreter fix in
`fix-release-env-fixture-interpreter-symlink-in-fre` separate.
Shared `code/open-pr` prompt cleanup is also out of scope; its historical
recovery narrative is a separate maintenance candidate.

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
