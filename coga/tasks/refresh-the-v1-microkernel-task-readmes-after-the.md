---
title: Refresh the v1 microkernel task READMEs after the W47 Retro deletions
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
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
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
step: 1 (implement)
agent: claude
launch_generation: 06f71dfa-4aac-47fb-bf4a-771e252952db
---

## Description

Filed by Dream recurring/dream, period 2026-W47 (run 20261118T170921Z), Phase 6 disposition of Phase 4 Retro follow-ups. coga/tasks/v1/microkernel/README.md still describes refresh (01), checkout declaration (02), launch decomposition (03) and the read/report commands (06) as pending/unstarted, though those tickets are done (Phase 2 shard ks-03 stale finding: the 06 row says 'Move report policy only after a generic stateless path preserves read-only behavior' while 06 is done). coga/tasks/v1/microkernel/03-prompt-assembly/README.md links the four 01–04 tickets that Retro PR #1255 deletes, and the orphan sibling directory coga/tasks/v1/microkernel/03-prompt-assembly/03-implement-the-proven-prompt-assembly-evidence/ was left behind with no owning ticket. After #1255 and #1259 merge: update the README rows to the done state (link durable outcomes via commit permalinks, not deleted ticket paths), and decide whether the evidence directory is kept (move under a live owner or docs/archive) or deleted.

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

## Status (implement, 2026-11-18)

Precondition unmet; no branch created, no edits made.

- PR #1255 (`codex/retro-prompt-assembly-trials-knowledge`, "New context: paired
  agent-behavior trial method for prompt changes") is OPEN. It deletes the
  `03-prompt-assembly/01-…` ticket tree that `03-prompt-assembly/README.md` links.
- PR #1259 (`codex/retro-v1-microkernel-06-read-report-commands-as-ticket-workflows-knowledge`)
  is OPEN. It deletes/edits `06-read-report-commands-as-ticket-workflows.md`
  and `docs/contexts/coga-dev/microkernel/SKILL.md`.
- Doing the README refresh before they merge would conflict with both and
  could not cite their merge-commit permalinks.

Next: once both merge, relaunch; refresh `coga/tasks/v1/microkernel/README.md`
rows for 01/02/03/06 and `03-prompt-assembly/README.md` using commit
permalinks, then decide the fate of
`03-prompt-assembly/03-implement-the-proven-prompt-assembly-evidence/`.

---

## Blockers

- [ ] [2026-11-18 23:57] [agent:claude] id=20261118T235751 Waiting on PRs #1255 (retro prompt-assembly trials knowledge) and #1259 (retro 06 read/report commands knowledge) to merge; both are still OPEN. The ticket says to refresh the READMEs only after they merge (their deletions and merge commits are what the rows must cite). Unblock once both are merged.

---

## Blocker reminders

- 7b0e53102f6a last_reminded: 2026-11-19 09:03
