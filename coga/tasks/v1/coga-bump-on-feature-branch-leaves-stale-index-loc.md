---
title: coga bump on feature branch leaves stale index.lock and blocks syncing with
  main
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
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
step: 1 (design)
agent: claude
---

## Description

A `coga bump` run from a **feature-branch** checkout published the ticket and
log to `origin/main` correctly, but left the checkout broken in two ways:

1. A stale, empty `.git/index.lock` that no process owned. Every later git
   write failed. `git stash create` exited 1 with no message, and
   `git merge origin/main` printed only `fatal: stash failed`. The silent stash
   failure made it look like a coga dirty-state problem instead of a lock
   problem.
2. The published ticket and log edits stayed dirty (` M`) in the feature
   checkout, byte-identical to `origin/main`. That dirt blocks
   `git merge`/`git rebase` of `origin/main` until someone runs
   `git checkout -- <paths>` by hand.

Find which coga publication path leaves `index.lock` behind and fix it. Likely
candidates are the feature-branch publication plumbing or the
advance-local-control step, possibly when the process is killed or races an
agent session teardown. Then remove the manual sync burden from item 2.

Done when:

- The root cause of the stale lock is identified, with a regression test. No
  publication path can exit (normally, on error, or on signal/teardown) while
  leaving a coga-created `index.lock`.
- One of these holds: coga restores published-and-identical files in a
  feature checkout after publishing, or `coga/checkouts/reconciliation`
  documents the exact one-command way to sync a feature branch with control
  and `coga status` points at it when that dirt is present. The design step
  chooses between them.

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

### Evidence (observed in another repo, 2026-11-10)

- coga 0.4.1, git 2.43.0, Linux. A Codex agent (`launch_args = "--no-daemon"`)
  ran `coga bump` at the end of an attended implement step, from a
  `coga/<slug>-<hex>` feature branch. Control got the ticket commit at 15:16:36
  and the log commit at 15:16:39.
- `.git/index.lock`: 0 bytes, mtime 15:16:38.435. That is inside the publish
  window and equal to the session's `ended_at` in the log usage record. So
  the lock was created during publication, at the moment the agent session
  ended. Afterwards no git process and no coga process had the repo as cwd
  (`pgrep -x git`, `lsof`).
- Afterwards, the feature checkout had ` M coga/log.md` and ` M coga/tasks/<slug>.md`,
  both identical to `origin/main` (`git diff --quiet origin/main -- <paths>`).
- Running `coga create` from the same feature checkout reproduced item 2
  immediately: it published to control, left `coga/log.md` dirty, and left the
  new ticket untracked locally. So any feature-branch coga command makes the
  next `git merge origin/main` need a manual restore.

Manual recovery used: confirm no owning process and `rm .git/index.lock`;
check that the dirty coga files equal control, then `git checkout -- <paths>`;
`git merge --no-edit origin/main`. Use merge, not rebase, so the already-pushed
branch doesn't need a force-push.

### Where to look

- Publication code: `src/coga/git.py` and the state-publication/sync modules
  it calls. Look for any git invocation that writes the **checkout's** index
  (`git add`, `read-tree`, `checkout`, `update-index`, `stash`) during a
  feature-branch publish. A lock in the checkout's `.git` means coga touched
  the real index, not a temporary `GIT_INDEX_FILE`. Check whether that
  subprocess can be killed mid-write: the supervisor tearing down the agent
  at bump, a SIGTERM/SIGHUP to the process group, or a timeout.
- `coga/state-publication` (cited, not attached;
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md`):
  read "Control versus feature checkouts", "Strict publication on demand", and
  "Recovering a failed publication". Update it in the same PR if behaviour
  changes.
- `coga/checkouts/reconciliation` (cited, not attached;
  `.../contexts/coga/checkouts/reconciliation/SKILL.md`): edit it if the design
  picks the documentation route.
- Related history: `v1/06-fix-coga-git-sync-failures-that-leave-main-diverge`
  (done) covered divergence of local main, not stale locks or feature-checkout
  dirt.

### Out of scope

- Automatically deleting an `index.lock` that coga did not create. Another
  git process may own it. At most, detect it and report a clear message.


<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
