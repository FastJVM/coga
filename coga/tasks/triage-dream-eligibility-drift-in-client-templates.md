---
title: Triage Dream eligibility drift in client templates
status: draft
owner: nicktoper
workflow: null
---

## Description

Imported at the owner's request from [FastJVM/multiply PR #195](https://github.com/FastJVM/multiply/pull/195), replacing the proposed client-side inbox entry with a Coga-owned draft.

- upstream-id: multiply/dream-2026-w43-u3
- repo: FastJVM/multiply
- date: 2026-10-20
- class: drift
- target: client Dream Phase 4 eligibility wording versus the shipped `bootstrap/dream/scan/knowledge-scan` definition of `source: done`
- evidence: Multiply Dream 2026-W43; its local `coga/recurring/dream/ticket.md` and the knowledge-scan skill

### Original finding

Multiply's Dream template treated any real recorded `branch:` or `worktree:` value as retirement debt, even after the named checkout was gone. The knowledge-scan skill used liveness: recorded names that no longer exist do not block `source: done`. W43 reported roughly 30 extracts classified differently and 82 versus 5 eligible tickets depending on the reading. These counts are historical evidence from the client report, not a fresh census.

### Current-main verification, 2026-10-21

The reported disagreement is already resolved in Coga source. Fresh `origin/main` at `d666fc90e2b8c7c01968c66a1443520bbfeca061` has matching liveness rules in:

- `coga/recurring/dream/ticket.md`, Phase 4, and its packaged template;
- `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/knowledge-scan/SKILL.md`, the `source: done` definition.

The rule checks every recorded branch in its owning repository and the configured remote, preserves debt for existing non-primary worktree directories, and treats unknown probes as live. A primary checkout is exempt only from directory debt, not branch debt. Recorded names whose branches and worktrees are gone do not block Retro. Relevant source history includes [22e12bf57595f6cb142df64e3e126f1c0ea1adce](https://github.com/FastJVM/coga/commit/22e12bf57595f6cb142df64e3e126f1c0ea1adce), following 9bfb0adf5cdb983616c9c3496eee61199115fd76 on 2026-10-14.

Multiply's local template still contains the older presence-based wording. Do not reopen the settled eligibility semantics or implement the same upstream fix again.

### Requested triage and completion

Determine which shipped version carries the fix and how a client with a local recurring-template copy should adopt it. Check whether existing template-refresh or drift-detection work already owns that follow-up. Record the exact upgrade or refresh action and its owner, preserving intentional local customization and `coga retire`'s checkout evidence.

If the package and documented upgrade path already satisfy the finding, record that evidence and close this draft as already satisfied. Any remaining client-only repair should be explicitly routed back to Multiply; only an identified Coga distribution or upgrade-contract gap needs new Coga implementation.

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
implementation and evidence, never placeholders; coga/internals/pr-publication/
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
