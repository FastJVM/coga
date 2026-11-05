---
title: Mention coga build in the install flow
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
step: 1 (implement)
agent: claude
launch_generation: c526e129-ccff-4a11-a74e-85ea0070809f
---

## Description

The `coga/install` page ends its install path without naming the next
command. Its `## Verify` section stops at "continue with
[coga/first-task]", so a reader who installs from that page is never told
that `coga build` is their next step. (The page mentions `coga build`
only under Prerequisites, as the command that offers to install a missing
agent CLI.) Add the next step there, split by repo state, matching
what `coga init` prints:

- **Otherwise empty Git repo:** `coga build` (or `coga build --agent <other>`
  for the other agent CLI).
- **Repo that already has files:** `coga ticket "<title>"`, not `coga build`.

Done when `coga/install`'s `## Verify` section (or the sentence that hands
off from it) says the next step comes after `coga init`, names
`coga build` for the empty-repo case and `coga ticket "<title>"` for the
existing-repo case, keeps the link to `coga/first-task`, leaves the page with
one next-step hand-off rather than two overlapping ones, and the packaged copy and its legacy live twin are
byte-identical. No code change.

## Context

### Files to edit (cited, not attached)

- Package owner:
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md`.
- Legacy live twin: `docs/contexts/coga/install/SKILL.md`. It is
  byte-identical to the package copy today, and `tests/test_packaging.py`
  requires them to stay identical. Edit both in the same commit (see
  AGENTS.md), then run `python -m pytest tests/test_packaging.py`.
- Current `## Verify` text ends: "These commands check the CLI installation,
  not agent authentication or a completed first task; continue with
  [coga/first-task](../first-task/SKILL.md)." The change belongs at that
  hand-off.
- A second hand-off sits at the end of `## Upgrading and removing`: "Next:
  adopt Coga into a repository with [coga/init], then walk a first ticket
  with [coga/first-task]." Put the build/ticket split in one place only. Either
  write it at the Verify hand-off and leave the "Next:" line as a pointer, or
  fold it into the "Next:" line and trim Verify. The reviewer must not find
  two overlapping next-step paragraphs.

### Facts to match, not restate

- `coga init` already prints this split. In `init` (the next-steps block at
  the end of the init command), an empty repo gets "Run `coga build` … or
  `coga build --agent <other>`", where `<other>` is whichever agent is not the
  configured default, and a filled repo gets
  "Run `coga ticket "<title>"` to author your first task". `coga/init`
  (`src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md`,
  "printed next steps") documents the same. The install page must agree with
  both.
- `coga/init` owns what "empty" means: nothing but `.git`, `.DS_Store`,
  and a short starter README, LICENSE or `.gitattributes`. Link to it
  instead of defining "empty" again on the install page (`coga/knowledge`:
  one owner per fact).
- `coga/first-task` already explains what `coga build` does (onboarding
  chat, vision, starter batch). Keep the install page to one or two
  sentences naming the command, and leave the explanation to first-task.
- Installing never modifies a repo; `coga init` does. The next step comes
  after `coga init`, so the sentence should say "after `coga init`" rather
  than suggest `coga build` straight after `uv tool install`.

### Scope and known tension

- Edit only `coga/install`. The README already names `coga build` for the
  empty-repo case in its "Choose how to begin" block, and
  `v1/23-scan-for-an-existing-repo-during-install` owns the README's
  existing-repo line (`coga chat` → `coga ticket "<title>"`). Do not touch
  the README here.
- Zach decided on 2026-10-17 to delete `coga/install` in favour of the
  README, and `v1/26-make-the-readme-install-section-the-only-install-p`
  owns that removal. The owner chose on 2026-11-04 to fix this page anyway
  while it still ships. Keep the edit small so v1/26 can drop or carry it
  over cheaply.
- Order versus v1/23 is not enforced. If this lands first, the install page
  says `coga ticket "<title>"` for existing repos while the README still says
  `coga chat` until v1/23 merges. That short gap is accepted. Both tickets
  touch `coga/install` only if v1/23 finds a prerequisite contradiction,
  which would be in a different section, so a rebase is enough.

### History

- Nico flagged the missing `coga build` in the review on 2026-10-19.
- Self-QA on `v1/29-test-and-fix-install-on-macos-and-windows` removed
  `coga build` from the README install block on 2026-10-18, because it
  told every reader to run it, including existing repos. Zach on 2026-10-21:
  `coga build` belongs to the new-repo case only.
- The ticket originally targeted the README. On 2026-11-04 it was rescoped
  to `coga/install`, because the README now covers the new-repo case and
  v1/23 covers the existing-repo one.

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

Previous ref: `marketing/fix-installer/mention-coga-build-in-the-install-flow` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: coga/v1-24-mention-coga-build-install

## Plan (implement)

- Put the build/ticket split at `coga/install` `## Verify` hand-off (after
  `coga init`), link `coga/init#fresh-repo` for "empty", keep first-task link.
- Remove the duplicate "Next:" line under `## Upgrading and removing` so the
  page has one next-step hand-off; its `coga/init` link moves into Verify.
- Edit package owner and `docs/contexts/coga/install/SKILL.md` twin together.
