---
title: Publish log lines that commands leave uncommitted
status: active
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
    skills: []
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
---

## Description

Some Coga log writes land in `coga/log.md` without being published by the
command that wrote them, so `main` can sit with a dirty log until a later
command's sweep picks it up, or indefinitely if none runs, and a dirty log
blocks fast-forwards and launches. Inventory every log write, classify each as
(a) published by its own command, (b) a documented deliberate deferral to a
later publish, or (c) stranded, and fix every stranded path so it publishes or
reports the failure.

Done when every log write either is published before its command exits,
prints a warning naming the retained line, or is a deferral documented in
`coga/state-publication`; each formerly stranded path has a test proving the
fix; and `python -m pytest` passes. Also decide, and record why, whether a
long-running attended session (`coga ticket`, `coga chat`) should publish its
start line immediately rather than leave it dirty for the whole session.

## Context

Split from `fix-the-commit-git-journal` (deleted); siblings
`commit-journal/coalesce-coga-state-commits` (which depends on this ticket's
inventory and lands after it) and `commit-journal/trim-the-audit-log`.

### The motivating case is a deferral, not proof of a bug

During this ticket's authoring on 2026-10-23, `git status` showed
`M coga/log.md` holding `[fix-the-commit-git-journal] [human:nicktoper] ticket
authoring launched`. `coga ticket` writes that line through
`spawn_agent_session` without `commit_log`, so nothing publishes it until a
later sync; here the first `coga create` run inside the session published it.
This is the attended-session question in the Description, not a confirmed
stranding.

### Prior work

The done ticket `surface-a-chat-end-log-line-that-was-written-but-n` fixed a
`coga chat` usage line written at session end on 2026-10-08 and never
published; it sat dirty for two weeks until `coga recurring --all` refused to
fast-forward over it. That fix covers chat teardown.

### Where to look

- Writers: `logfile.append_log` callers across about 15 modules (`bump`,
  `create`, `launch`, `launch_script`, `mark`, `recurring`,
  `recurring_runner`, `usage`, `commands/{init,owner,slack,unblock}`,
  `notification/slack`, `git`, `logfile`); search the whole `src/` tree.
- Publish paths: `git.sync_log` (log alone), `git.sync_task_state` (ticket
  plus log), and the CLI end-of-command sweep (`cli._should_sweep_coga_state`
  then `git.sync_coga_state`). Most commands sweep at exit, so likely
  stranding paths are the exceptions:
  - commands in `cli._NON_SWEEPING_COMMANDS` (`status`, `show`,
    `validate`, `usage`, `init`, `uninstall`) and the `run publish-state` /
    `prepare-checkout` exemptions;
  - every `git.state_sweep_withheld.set(True)` site (for example
    `commands/ticket` on `AuthoringError`, which leaves the launch line
    unpublished by design);
  - refused checkout returns.
- Failure records: `git.record_sync_failure` and the "sync refused" /
  "refresh failed" lines are written *because* a publish failed. They count
  as satisfied by the existing failure report; do not try to publish a
  failure record in a retry loop.

### Topic (cited, not attached; read first, update in the same PR)

`coga/state-publication` (`docs/contexts/coga/state-publication/SKILL.md`)
owns when each command publishes ("When Coga publishes") and how a stranded
log tail is recovered ("A stranded log tail blocking catch-up"). The
deliberate-deferral list this ticket produces belongs there.

Out of scope: `Read-only file system` sync failures inside agent sandboxes
(owned by `fix-coga-git-sync-failures-that-leave-main-diverge`).

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
