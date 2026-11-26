---
title: Run a workflow step script that publishes only the current ticket to main
status: draft
owner: nicktoper
contexts:
  - coga/git
  - coga/workflows
  - coga/launch
  - coga/lifecycle
  - coga-dev/principles
workflow:
  name: code/with-review
  git: ticket-branch
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

Owner design (2026-11-25, attended orient session): replace the closed `git:` launch mode with a workflow-declared step script, fold branching into it, and have it publish only the current ticket's state to main.

### Problems

1. **Ticket state lags on main.** In ticket-branch mode the ticket's live copy is on its `coga/*` branch and reaches main only at merge. `let-dream-retro-handle-period-tickets-that-were-ne` was `draft` on `origin/main` while its branch had it `in_progress` at step 4, so `coga status`, teammates and Dream on main read stale state.
2. **Other tickets block the push step.** `git/push-and-open-pr/run.py` (`dirty = ... - set(paths)`, ~line 375) exempts only the launched ticket and `coga/log.md`. Any other ticket's uncommitted blackboard edit in the shared checkout fails it with "Commit your work first: <other tickets>". The operator's workaround (`git add -u && git commit`) swept seven unrelated tickets into that PR (commit `529257375`).

### Design

- **Kernel: open `step-script:`.** A workflow names any skill ref: `step-script: git/ticket-state`. The kernel runs its `run.py enter` before each step and `run.py exit` after each step, and also runs `exit` after every ticket-state write made outside a launched step (`coga bump`, including the owner's final bump to `done`, `coga mark`, `coga block`, `coga unblock`). The kernel stays Git-free: it only runs the named script. The closed `GIT_MODES` map (`src/coga/workflow.py`) and the whole-launch hook (`src/coga/launch.py` `run_launch_hook`) go; a frozen `git: ticket-branch` keeps working by mapping to the legacy `git/ticket-branch` script.
- **`git/ticket-state` enter:** switch to the ticket's recorded branch, or create it from the current HEAD and record `branch`/`base`/`remote` under `## Dev`. This replaces the `open-branch` step and the `git/ticket-branch` hook.
- **`git/ticket-state` exit:** publish only the current ticket. Build a commit on the fetched `origin/<base>` with a temporary index containing that ticket file and `coga/log.md` as `origin/<base>`'s log plus the local lines naming this ticket that are not on it. Push it with `git push <remote> <oid>:<base>`. Never touch the working tree or the code branch, and never commit ticket state to the code branch. On a rejected push, fetch, rebuild and retry once, then stop simply with Git's message and local state intact. Other tickets' files are never read or published.
- **`git/push-and-open-pr`** pushes the code branch and opens or reuses the PR only. It no longer commits the ticket or log. Its dirty check ignores `coga/tasks/**` and `coga/log.md`. `code/merge-pr` drops its ticket-state commit the same way.
- **Workflows:** `code/*` packaged workflows declare `step-script: git/ticket-state` and drop the `open-branch` step. Repos whose base is protected keep today's state-on-branch behaviour by declaring the legacy script.

### Contracts to update in the same PR

`coga/git` (Branch to merge, Ticket-branch mode), `coga/workflows`, `coga/launch`, `coga/lifecycle` (bump and mark run the step script's exit), and the v1/03 owner decisions this reverses: C3's ticket commit and "the final bump on the branch ... reaches main with the PR merge". Align the README with `coga-dev/principles`.

### Done when

- After any launch, bump, mark or block, `coga status` on a fresh clone of the base shows the ticket's current status and step.
- A PR opened by `code/with-review` contains no `coga/` paths.
- Two concurrent sessions in one checkout never publish each other's ticket, and an uncommitted edit to another ticket does not block `push-and-open-pr`.
- A frozen `git: ticket-branch` ticket still launches.
- `python -m pytest` and `tests/test_packaging.py` pass.

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
