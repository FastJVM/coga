---
title: Add imported-skill update check
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/codebase
- relay/current-direction
- relay/project-stage
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 4 (review)
---

## Description

Add skill provenance metadata, an installer, and an updater for
imported/adapted skills.

Imported skills are useful only if humans can tell where they came from, when
upstream changed, and whether local adaptations still make sense. Relay needs a
human-readable provenance record for each imported skill, CLI surfaces to
install/check/update them, and a recurring maintenance task that updates all
clean imports in a reviewable PR.

## Context

This is related to Dream, but it is not the same as running tests. Dream or a
future recurring maintenance workflow can use this check to notice stale
imported skills.

The desired operating model:

- Imported skills stay as plain directories under `relay-os/skills/`; no opaque
  package cache or hidden service owns them.
- Each imported skill records enough metadata for update checks: source URL or
  repo, upstream path, installed ref/version, digest if available, import date,
  and local adaptation notes.
- `relay skill install <source>` copies a skill directory into place, preserves
  bundled scripts/templates, writes provenance metadata, and refuses dirty
  overwrites unless the user explicitly asks for upgrade/force behavior.
- `relay skill status` reports clean, locally modified, upstream changed,
  provenance missing, and source fetch failed states.
- `relay skill update <name>` updates one imported skill.
- `relay skill update --all` walks every imported skill with metadata and
  updates all clean imports in one working-tree diff.
- Local adaptations are never overwritten silently. If upstream changed and the
  local copy also changed, the updater skips that skill and emits a conflict
  report with the exact paths/refs involved.
- A standalone weekly recurring task (`recurring/skill-update/`, `mode:
  script`) runs the all-skill updater and creates one PR containing clean
  imported-skill updates. Conflicts and skipped skills go into the period
  task's blackboard/PR body as follow-up work. (Redirected from the original
  "Dream maintenance step" shape: many small recurring tasks are easier to
  debug and fix than one fat Dream pass, so Dream's skill-update phase is
  removed.)

## Acceptance criteria

- [ ] Imported skills have enough recorded provenance for status/update/install
      commands to read.
- [ ] `relay skill install <source>` installs a skill directory, preserves
      bundled files, writes provenance, and refuses unsafe overwrites.
- [ ] `relay skill status` reports upstream version/commit changes when
      available and distinguishes clean imports from local adaptations.
- [ ] `relay skill update <name>` updates one clean imported skill and skips
      locally adapted/conflicting skills with reviewable evidence.
- [ ] `relay skill update --all` updates all clean imported skills in one
      working-tree diff and produces a structured summary.
- [ ] Missing provenance, fetch failures, digest mismatches, and other
      supply-chain concerns are reported explicitly instead of being ignored.
- [ ] A standalone recurring task runs `relay skill update --all --pr` on a
      weekly schedule and opens one PR for clean updates; Dream no longer has
      a skill-update phase.
- [ ] The period task's blackboard report lists updated skills, unchanged
      skills, skipped/conflicting skills, and next actions.
- [ ] Focused tests/fixtures cover at least one clean imported skill, one local
      adaptation/conflict, `--all`, and the recurring template/report path.
