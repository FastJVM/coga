---
title: Add imported-skill update check
status: draft
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: nick
contexts:
  - relay/codebase
  - relay/current-direction
  - relay/project-stage
  - dev/code
workflow:
  name: code/with-review
  steps:
    - name: implement
      skill: code/implement
    - name: open-pr
      skill: code/open-pr
    - name: review
      assignee: owner
step: 1 (implement)
---

## Description

Add skill provenance metadata, an installer, and an updater for
imported/adapted skills.

Imported skills are useful only if humans can tell where they came from, when
upstream changed, and whether local adaptations still make sense. Relay needs a
human-readable provenance record for each imported skill, CLI surfaces to
install/check/update them, and a Dream maintenance step that can update all
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
- Dream includes a known skill-update maintenance step that runs the all-skill
  updater and creates one PR containing clean imported-skill updates. Conflicts
  and skipped skills go into the Dream blackboard/PR body as follow-up work.

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
- [ ] Dream's maintenance plan includes the imported-skill update step and uses
      `relay skill update --all` to open one PR for clean updates.
- [ ] Dream's PR body or blackboard summary lists updated skills, unchanged
      skills, skipped/conflicting skills, and next actions.
- [ ] Focused tests/fixtures cover at least one clean imported skill, one local
      adaptation/conflict, `--all`, and the Dream summary/PR path.
