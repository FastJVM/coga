---
title: Make Dream workers skills only
status: active
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: claude1
contexts:
- relay/architecture
- relay/principles
- relay/cli
- relay/codebase
workflow:
  name: code/with-review
  steps:
  - name: implement
    skill: code/implement
  - name: open-pr
    skill: code/open-pr
  - name: review
    assignee: owner
step: 2 (open-pr)
---

## Description

Convert every Dream worker into a plain Relay skill. No bespoke
Python under `src/relay/resources/dream/`, no `relay.commands.dream`
imports of `worker.main()`, no "Dream worker" as its own concept
distinct from a skill.

Why: per the dream-5 architectural correction, "scripts are skills,
never standalone." Today some Dream workers exist as ad-hoc Python
files that Dream discovers and calls; that's a side-channel around
Relay's task/skill machinery. Lifting them to skills makes them
launchable through normal `mode: script` tasks, gives them
blackboards and logs, and removes the parallel execution path.

## Workers In Scope

- `validate-drift` — repo validation + conservative safe repair.
- `cleanup-orphan-markers` — recovery for done tickets whose
  blackboard already has the processed Retro marker but whose task
  directory still exists.

If implementation reveals other shadow-workers in the codebase, list
them in the blackboard and decide per-worker whether they belong in
this ticket or a follow-up.

## Required Shape Per Worker

- Lives at `relay-os/skills/<path>/SKILL.md` (or
  `bootstrap/skills/...`, whichever matches the shipping bootstrap
  tree).
- `SKILL.md` has the standard frontmatter (`name`, `description`)
  plus optional `script: <filename>` for the executable entry point.
- Script reads task metadata from the env vars Relay injects in
  `mode: script` runs (task dir, blackboard path, slug). No
  `--blackboard` argument plumbing.
- Detection / repair logic for the worker is unchanged in spirit.
  Specifically for `cleanup-orphan-markers`:
  - exact `status: done`;
  - a `## Retro` block containing both
    `skill: retro/done-ticket` and `status: processed`;
  - exact slug match, no prefix matching;
  - no open PR already touching `relay-os/tasks/<slug>/`;
  - deletion goes through the public delete surface (whatever the
    sibling ticket `move-relay-delete-into-a-skill` lands), inside
    the cleanup PR worktree — never silently from the running tree.

## Acceptance Criteria

- `validate-drift` and `cleanup-orphan-markers` exist as skills with
  the shape above.
- A `mode: script` Relay task whose one workflow step references
  the worker skill runs the worker end-to-end and writes its
  summary to the child task's blackboard.
- `relay.commands.dream` (and any sibling Dream module) does not
  import worker `main()` functions or call them in-process. Grep
  proves it. The "Dream orchestrates by launching child tasks"
  story holds.
- Tests cover:
  - skill discovery + script-mode invocation;
  - script-mode metadata env vars present and consumed;
  - cleanup uses the sibling ticket's delete-skill surface, not a
    private helper;
  - docs / context wording: "Dream-owned scripts are skills attached
    to Relay tasks; they are never standalone execution units."
- `relay/architecture` context picks up that one-line rule.

## Out Of Scope

- Replacing `relay dream` itself with a recurring task + alias —
  that's the sibling ticket
  `compose-dream-as-recurring-plus-alias`.
- Adding new workers beyond what already exists. Inventory only.
- Auto-deletion without a reviewable PR. Cleanup still opens a PR.

## Context

Sibling tickets in this split:

- `move-relay-delete-into-a-skill` — provides the skill-based
  delete surface this ticket's `cleanup-orphan-markers` worker
  depends on.
- `compose-dream-as-recurring-plus-alias` — assembles these
  skill-shaped workers into the runnable Dream pass.

Background: `relay-os/tasks/dream-5/ticket.md` is the combined
parent. That body has the most detail on each worker's correct
shape — read it before coding.
