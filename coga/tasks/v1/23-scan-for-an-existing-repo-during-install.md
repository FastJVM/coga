---
title: Scan for an existing repo during install
status: in_progress
owner: zach
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
contexts:
- coga-dev/principles
step: 2 (peer-review)
agent: claude
---

## Description

The README's Get started section treats "no Git repo yet" as a path to walk
the user through. It isn't one: Coga only runs inside a Git repo, and outside
one it should stop. Make a Git repo a stated prerequisite, remove the
create-a-repo steps, then stop in one case and route the other two by repo
state:

- **Not in a Git repo:** stop. The README states the prerequisite and does not
  show how to create a repo. `coga init` already refuses here (see Context);
  no code change.
- **Git repo that is empty apart from starter files:** first step is
  `coga build`.
- **Git repo with existing files:** first step is `coga ticket "<title>"`,
  not `coga build` and not `coga chat`.

Done when the README's Get started section has no `mkdir`/`git init` block,
states that Coga runs inside an existing Git repo as a prerequisite (the idea,
not exact wording; it belongs with the opening "You'll need working Git…"
sentence), and its
"Choose how to begin" block sends the empty-repo case to `coga build` and the
existing-project case to `coga ticket "<title>"`, so a reader never has to work
out which case they are in beyond "is my repo empty?".

## Context

### Current state (checked 2026-11-04)

- `README.md`, Get started: after `uv tool install coga`, it says "For an
  existing project, change into its Git repository. For a new project, create
  the repository first:" and shows `mkdir myproject` / `cd myproject` /
  `git init -b main`. Remove that block and the "new project" sentence.
- The same section's "Choose how to begin" block shows `coga build` for "New,
  otherwise empty Git repo", `coga chat` for "Existing project", and
  `coga status`. Change the existing-project line to `coga ticket "<title>"`.
  Keep `coga status`. The following paragraph lists `--agent codex` forms for
  `build`, `chat`, and `ticket`; drop the `coga chat --agent codex` form so
  it lists only the commands the block shows.
- `coga init` already refuses outside a repo: `init._require_git_work_tree`
  prints "<path> is not inside a git repository — coga is git-backed. Run
  `git init` … first, then re-run `coga init`." and exits 2. That is the
  required "stop", so this ticket changes no code. If the implementer finds a
  path past install that does not refuse, record it on the blackboard rather
  than widening this ticket.
- `coga init`'s printed next steps already say `coga build` (empty repo) or
  `coga ticket "<title>"` (filled repo), as `coga/init` documents ("printed
  next steps"). The README should match that.
- What counts as "empty": init seeds the onboarding ticket only for an
  otherwise empty repo, and a short starter README, LICENSE or
  `.gitattributes` still counts as empty. Reuse that wording; don't invent a
  new definition. The README wording is looser than init's real rule; do not
  expand it.
- `coga/init`
  (`src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md`,
  cited, not attached) says starting a brand-new project means `git init`
  first, and owns the real "empty" rule. It needs no change.
- Coga still tells a user how to create a repo in one place: init's refusal
  message says "Run `git init`…". That stays; the README just stops
  presenting it as a path.

### Scope

- README only. Read `coga/install`
  (`src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md`,
  cited, not attached) for any statement that contradicts "a Git repo is a
  prerequisite". Its "macOS: check Git before init" section mentions
  `git init` only as a Git sanity check, which is fine. If it does contradict
  the prerequisite, fix the package copy and its legacy live twin
  `docs/contexts/coga/install/SKILL.md` together (see AGENTS.md).
- `coga/first-task` suggests `coga chat` for planning a *batch* of tickets.
  That is a different use and stays.
- Out of scope: any feature where Coga scans a repo to generate docs (Nico's
  separate idea); changing `coga init`'s behavior or messages.
- Sibling `v1/24-mention-coga-build-in-the-install-flow` was rescoped on
  2026-11-04 to the `coga/install` page's Verify hand-off only. It does not
  touch the README, so the two tickets don't overlap there.

### Why

- Finding 4 on `test-and-fix-install-on-macos-and-windows`: the README install
  block assumed a repo exists. This was the first dead end on the 2026-10-15
  walk-through.
- Following the `mkdir myproject && git init` block literally sends a user who
  already has a project into a throwaway directory.
- Nico (2026-10-19): having a repo is a prerequisite, not a step. Owner
  decision (2026-11-04): with no repo, Coga stops and goes no further.
- Zach (2026-10-21): an existing repo with files goes to `coga ticket`, and a
  new (empty) repo goes to `coga build`. Owner decision (2026-11-04):
  `coga ticket`, not `coga chat`, for the existing-project case.

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

Previous ref: `marketing/fix-installer/scan-for-an-existing-repo-during-install` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: coga/v1-23-repo-prerequisite

## Plan

- README-only: state the Git-repo prerequisite in the opening "You'll need
  working Git…" sentence, drop the "new project" sentence and the
  mkdir/git init block, send the existing-project case to
  `coga ticket "<title>"`, drop `coga chat --agent codex`.
- `coga/install` checked: its `git init` mention is only a Git sanity check
  in the macOS section; no contradiction, no change.

## Handoff (implement)

- Commit on `coga/v1-23-repo-prerequisite` (pushed, rebased on origin/main):
  README Get started now opens with "Coga runs inside an existing Git
  repository; outside one, `coga init` stops."; the "new project" sentence
  and `mkdir`/`git init` block are gone ("Change into your project's Git
  repository." remains); the begin block shows `coga build` (empty repo),
  `coga ticket "<title>"` (repo with existing files), `coga status`; the
  Codex paragraph lists only `build` and `ticket`.
- Verification: `.venv/bin/python -m pytest -q
  tests/test_packaging.py::test_context_navigation_has_no_broken_links`
  passed (system `python` lacks `tomlkit`; use the venv). No code touched.
- Kept: "chat and ticket interviews default to Claude" sentence (still
  accurate). No path past install found that skips the refusal.
- Follow-up candidates (out of scope): `coga/configuration` and
  `coga/first-task` still cite `coga chat --agent codex`, which is correct
  for their own uses.
