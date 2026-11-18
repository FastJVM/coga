---
title: Add an explicit coga sync command
status: in_progress
owner: nicktoper
contexts:
- coga-dev/principles
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
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
step: 1 (design)
agent: claude
launch_generation: pending:dbabd0b0-5379-4fc8-9dc4-110b0dc0e900
---

## Description

First ticket of the `git-sync/` project. Add a new `coga sync` command
(it does not exist today) that implements the project's publication model
below. Humans and agents both call it. It must be safe to run repeatedly and
from any checkout.

`coga sync`: commit the Coga state directory, fetch main, push the state to
main, rebase the current branch onto main, and force-push a previously pushed
branch with `--force-with-lease`. Today's implicit publication stays in place
during this ticket. Ticket 02 removes it, so both paths must coexist safely
until then.

Done means: a merged PR adding `coga sync` with tests for control and feature
checkouts, and an updated `coga/sync` topic that describes it as the
publication primitive.

## Context

### What the design step must resolve

- **Placement under the microkernel rule** (`AGENTS.md`, cite
  `coga-dev/microkernel`): Typer command, `runner.RECIPES` entry, or alias.
  Justify why it belongs in core.
- **Uncommitted code changes** on the branch when syncing: what happens to
  them through the rebase (only Coga state is committed by sync).
- **Coga-state commits already on a feature branch**: how they get to main,
  and how they are dropped from or reconciled on the branch.
- **Protected or unreachable main**: the config comment near the control
  remote in `coga/coga.toml` covers this case. Define the failure and retry
  behavior.
- **Conflicts** while rebasing Coga state and while rebasing code, and retry
  after a failed push.
- **Commit subject**: check the `Sync coga state` prefix rules in
  `coga/recurring/scheduling/inactivity` before changing it.

### Pointers (cited, not attached)

- Edit: `coga/sync` at
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`.
- Read: `coga-dev/internals/state-publication`
  (`docs/contexts/coga-dev/internals/state-publication/SKILL.md`) and
  `coga-dev/patterns` (the rule for state-changing commands). `coga/sync`
  routes to both.
- Existing primitives to reuse or replace: `git.sync_coga_state` (the sweep),
  `git.sync_task_state`, `git.publish`, `publish_state.py`,
  `log_publication.py`.

### Project decisions (owner, 2026-11-17)

These apply to the whole `git-sync/` project (01 → 02 → 03):

- **Publication is explicit everywhere.** No command auto-publishes, including
  lifecycle transitions (`bump`, `block`, `mark`, `create`, launch audit
  lines). Their writes reach other checkouts only when `coga sync` runs, called
  by a human, an agent, or the session end.
- **`coga sync` is the only publication path.** It commits the Coga state
  directory (`coga/`, plus the contexts root if configured outside it), fetches
  main, pushes that state to main, and rebases the current branch onto main.
  When the rebased branch has already been pushed, it force-pushes
  automatically with `--force-with-lease`.
- **State goes to main from any checkout.** On a feature checkout, Coga state
  is still pushed straight to main while code stays on the branch. The current
  held-for-merge behavior is dropped.
- **No atomic-publish exception for megalaunch/recurring admission claims**
  (`launch_generation`). Tickets have an owner, so the owner rejected
  protecting cross-clone admission races with an exception.
- **End state: `src/coga/git.py` becomes trivial.**
- This deliberately reverses the current `coga/sync` invariant that Git
  publication happens "without committing on a local branch, stashing, or
  rebasing". Say so in the topics you rewrite.

Origin: the problem surfaced while designing
`v1/microkernel/05-make-packaged-behavior-discoverable-and-editable`. The
end-of-command sweep (`git.sync_coga_state`) publishes every dirty eligible
file on control, including definition edits. A fork command would therefore
publish a byte-identical override that silently stops following package
updates. `git.py` (thousands of lines) also keeps producing small sync bugs.

Related tickets that may be superseded by this project; check and cancel or
fold them as the design settles: `fix-git-sync-failure`,
`hold-dirty-context-edits-on-feature-checkouts-unti`,
`correct-state-publication-internals-for-pending-pu`.

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
