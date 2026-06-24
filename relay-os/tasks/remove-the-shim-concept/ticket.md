---
slug: remove-the-shim-concept
title: Remove the shim concept
status: in_progress
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 1 (design)
---

## Description

**Remove the "shim" concept from Relay entirely** — don't rename it. The
stateless launch-targets under `relay-os/bootstrap/<name>/` (orient, ticket,
project) are just **tickets**; describe and name them as such. **Delete the
"tier-2 shim"** idea from the extension model — there is no separate launcher
category. After this, the model is the three existing homes — **kernel,
tickets, external-tools** — with **aliases as sugar** (not a home). This is the
foundation for the broader "move things out of core into tickets" program and
must land before `move-read-views` and the extraction tickets. **Behavior does
not change here** — this is a model + vocabulary cleanup, not a command move.

## Context

The plan evolved: Nico first asked to rename "shim" → "alias," but `alias`
already means the argv-rewrite sugar (a distinct concept), and on reflection
"shim" shouldn't exist at all — these things are tickets. So we **delete the
concept** rather than rename it.

**Taxonomy is unchanged — just purified.** Keep `extension-model`'s three homes
(kernel / tickets / external-tools) and alias-as-sugar. "shim" and "tier-2
shim" were non-conforming extras: a bootstrap launch-target is a *ticket*; a
read-view "script shim" is a *ticket* (tickets-as-scripts); "tier-2 shim" was a
proposed fourth mechanism that shouldn't exist (ticket-authoring is just a
ticket — implemented for real by `move-ticket-authoring-out-of-core`).

**`design` step output (for `review-design`, get Nico's sign-off):** the
reworded `extension-model` / `architecture` / `cli-extension-audit` passages
(this is the model *contract*) plus the full rename inventory.

**Carve-outs — these "shim" uses are NOT the concept; plain English or leave:**
- Install symlink (`~/.local/bin/relay`) → "symlink"/"wrapper":
  `src/relay/commands/uninstall.py`, `init.py` (`_relay_shim`,
  `_try_install_shim`).
- Import-compat layer → "compatibility layer": `src/relay/slack.py:1`.
- Deprecation sense → keep "shim" / "deprecation stub":
  `relay-os/contexts/relay/project-stage/SKILL.md:28`.
- `skill-shim` historical field name (`src/relay/commands/launch.py:516`,
  tests) → leave.

**The two docs that contrast shim-vs-alias** (`extension-model/SKILL.md`,
`docs/cli-extension-audit.md`) become *ticket*-vs-alias — reword, don't
blind-replace.

**Worklist — the default `grep` HIDES files.** The live `relay-os/bootstrap/`
tree is gitignored, so use a gitignore-blind sweep:
`/usr/bin/grep -rIl "shim" . | grep -v "/.git/" | grep -v "/.venv/" | grep -v "/.relay/" | grep -v "/.pytest_cache/" | grep -v "relay-os/tasks/"`
(~37 files). Sync all three copies: live top-level, live `relay-os/bootstrap/`
(gitignored), and packaged `src/relay/resources/templates/relay-os/bootstrap/`.
Code identifiers are in scope (`DISCUSSION_BOOTSTRAP_SHIMS` → `…TICKETS`,
`shim_ticket`, …). Keep `python -m pytest` green.

**Related:** PR 425 is being closed (its `ticket.py` extraction premise is
redone as `move-ticket-authoring-out-of-core`). This ticket only removes the
concept; it moves no command.

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
