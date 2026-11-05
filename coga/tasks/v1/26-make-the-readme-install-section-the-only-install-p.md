---
title: Retire the coga/install topic
status: draft
owner: zach
contexts:
  - coga-dev/principles
  - coga/knowledge
workflow: code/with-review
---

## Description

Delete the `coga/install` topic so the README "Get started" section is the
only install path, as the owner decided on 2026-10-17. The README link to the
topic is already gone (the owner's README rewrite, 2026-11-03/04). What remains
is the topic itself, the links that still point at it, and the facts only it
holds.

1. Triage the orphan facts listed under Context. For each one, either move it
   to the topic that owns the surrounding behavior, or record that it already
   lives there or is deliberately dropped. Follow `coga/knowledge` for where a
   fact goes. Do not create a new catch-all install page under another name.
2. Delete `docs/contexts/coga/install/SKILL.md` and its packaged twin, and
   update the packaging bookkeeping that names them.
3. Repoint or remove every inbound link and mention, so nothing links to the
   deleted topic.
4. Close the README's one remaining gap. Add one plain line saying what to do
   when `coga --version` fails after `uv tool install coga` because the uv tool
   bin directory isn't on PATH (for example `uv tool update-shell`, then open a
   new terminal). Check that wording against current uv before writing it.

Done when: `coga/install` and its twin are gone; `grep -rn "coga/install"`
finds no live link or mention outside `docs/archive/`, `coga/tasks/` and
`coga/log.md`, which are history and are left alone; each
orphan fact is either in a named owning topic or recorded on the blackboard as
dropped, with a reason; the README covers the coga PATH case; and
`python -m pytest` plus `coga validate --json` pass.

## Context

### Why

- Owner decision, 2026-10-17: delete `coga/install` in favour of install
  instructions in the README.
- Zach, 2026-10-21: there should be no separate install page at all. Having to
  click into other pages to work out how to install coga is where it gets
  confusing.
- Walk, 2026-10-15: the page explains prerequisites instead of supplying them,
  and it reads as written for agents while the README reads as written for
  humans.
- `v1/29-test-and-fix-install-on-macos-and-windows` is closing and states on
  its blackboard that this ticket owns the topic's removal.
- `v1/33-review-all-doc`, the documentation acceptance pass, is in progress.
  It removed the README link but left retirement and re-homing to this ticket,
  and its final acceptance rechecks the result. Reconcile with its branch or
  merged state before you edit the same pages.

### Orphan facts to triage

From the 2026-10-17 owner-decision section on v1/29's ticket. These are
candidates, not commitments. Read the current
`docs/contexts/coga/install/SKILL.md` for the exact wording, because it may
hold more than this list:

- The macOS Command Line Tools trap, including the headless `softwareupdate`
  route, and that the CLT ships Python 3.9. The README now covers the basic
  `xcode-select --install` path.
- Why the floor is Python 3.11: config loading uses `tomllib`, and what an
  older interpreter fails with.
- Why native Windows does not run. The topic's explanation (`coga.git`
  importing `fcntl` at module top) is stale: `fcntl` now appears only in
  `coga.oscompat` and `coga.repl_supervisor`. `coga/launch` ("Phases and
  routing") already owns the Windows boundary, so this is likely "already
  owned". Do not carry the stale explanation forward.
- The Python <3.11 failure detail: the yanked `coga==0.0.1` that an old
  interpreter resolves to, `uv tool install --python 3.11`, and that an older
  venv does not help.
- The `--require-hashes` install failure and its two workarounds.
- The pipx, venv and pip install alternatives. Rehome them or drop them on
  purpose; the README now offers only uv.
- Which external CLIs are checked when, and that `coga init` enforces only
  `git`. `coga.dependencies` is the code source of truth.
- Upgrade and removal commands for each installer, including the upgrade
  note that bundled batteries need no per-repo refresh. `coga/uninstall` owns
  removal.
- "Verify": `coga --version` prints `unknown` without package metadata, and
  there is one CLI with no per-repo version.
- "CLI older than the templates it sweeps" (a lagging editable install in
  clone scope). This probably belongs to `coga/recurring/scheduling`.
- "Audit retention adoption" (`coga_edge.trim_log --install`). This is likely
  already owned by `coga/edge-code` and `coga/configuration`.

### Where it is referenced (as of 2026-11-04)

- Topics: `docs/README.md` and the `coga/init`, `coga/first-task`, `coga/cli`,
  `coga/uninstall`, `coga/recurring/scheduling` and
  `coga-dev/current-direction` topics. Edit the package copy under
  `src/coga/resources/templates/coga/bootstrap/contexts/` for user topics and
  mirror any legacy live copy (see AGENTS.md). In `coga/uninstall`, the link
  explains what counts as a uv-tool install, so the replacement has to carry
  that meaning rather than just dropping the link.
- Packaged skills: `coga/testing/clean-install`,
  `coga/testing/clean-install/macos-aws` (two links, one to the
  `#macos-check-git-before-init` anchor) and
  `coga/testing/clean-install/windows-aws` under
  `src/coga/resources/templates/coga/bootstrap/skills/`, each with a live
  copy in `coga/skills/` to mirror. Whatever replaces the anchor must still
  give the same check.
- `tests/test_packaging.py`: `"coga/install"` appears in the required
  bootstrap context refs list (`REQUIRED_BOOTSTRAP_CONTEXT_REFS`).
- `tests/legacy_removal_inventory.txt`: the
  `docs/contexts/coga/install/SKILL.md` ↔ package-twin row.
- `coga.dependencies` module docstring names the `coga/install` topic as the
  human-facing description of the dependency set.
- Open tickets under `coga/tasks/` (including
  `coga/tasks/context-audiences/README.md`) also mention it. They are not code, so
  leave them, but note on the blackboard any whose premise this changes.

`coga/knowledge` is attached because triaging the orphan facts is the core job.
`coga-dev/packaging` (`docs/contexts/coga-dev/packaging/SKILL.md`) is cited,
not attached. Read its sections on twins and the legacy inventory before
editing the bookkeeping.

### README PATH gap

The README's only PATH line covers `uv` itself, so a reader whose
`coga --version` fails after `uv tool install coga` is told nothing. In the
Kiro trial on 2026-10-30, Kiro's installer printed "Installation complete!"
above the PATH step that made the tool runnable. Keep the fix to a line or two
in the README, in keeping with `coga-dev/principles`. Do not add a page.

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

Previous ref: `marketing/fix-installer/make-the-readme-install-section-the-only-install-p` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
