---
title: Remove implicit publication and sync at session end
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
launch_generation: 24118624-c454-475f-87cd-981075bbd490
---

## Description

Second ticket of the `git-sync/` project; depends on
`git-sync/01-add-an-explicit-coga-sync-command` being merged. Switch Coga to
explicit publication. Remove the end-of-command sweep and every per-command
or per-transition publication. Make launched and unattended sessions run
`coga sync` at session end, so no work is stranded when no human is present.

Done means: a merged PR in which no command publishes implicitly; the
`coga launch` supervisor, megalaunch and recurring runners sync at session
end; tests cover these behaviors; and the topics, base prompt and step skills
describe the explicit model.

## Context

### What the design step must resolve

Every guarantee the implicit publication provides today has to be re-homed
or deliberately dropped:

- **Session end.** `bump`, `block` and `mark` end a launched session, so the
  agent cannot sync afterwards. The supervisor (`coga launch`, megalaunch,
  recurring runner) owns the end-of-session `coga sync`. Specify what happens
  when the supervisor crashes before syncing, and how the next launch
  recovers stranded state.
- **Pre-launch sync.** `launch.py` currently calls the sweep ("Sync coga state
  before launch"). Decide whether launch only pulls now.
- **Launch audit lines** in `coga/log.md`, and **notifications**: decide
  whether they fire on the local write or on publication.
- **Megalaunch/recurring chaining across clones**: no admission-claim
  exception (see the project decisions). Confirm that chaining still works
  when state lands only at session end.
- **Recurring inactivity rules** that key off `Sync coga state` commits
  (`coga/recurring/scheduling/inactivity`).

### Callers to remove or convert

Grep for `sync_coga_state`, `sync_task_state` and `git.publish`; the
inventory is part of the design. As of this writing, callers include `cli.py`
(the post-command sweep hook), `launch.py`, `megalaunch.py`, `bump.py`,
`mark.py`, `commands/{create,delete,owner,unblock,recurring}.py`,
`branchsweep.py`, `recurring_runner.py`, `recurring_autofix.py`,
`blocker_reminders.py`, `checkouts.py`, `github_preflight.py`,
`notification/__init__.py`, and the bundled `bootstrap/retire/ticket.py`.

### Surfaces to update in the same PR (cited, not attached)

- `coga/state-publication`:
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md`
- `coga/checkouts` and its children, especially `reconciliation`, under
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/`
- Launch-boundary text under `coga/checkouts/launch-boundary`
- The base prompt's "Reconcile before publishing" section, `prompt-ticket.md`
  in `src/coga/resources/`, and any step skills that assume implicit
  publication
- `coga-dev/internals/state-publication`

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
