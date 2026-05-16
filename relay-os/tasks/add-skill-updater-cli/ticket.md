---
title: Add skill updater CLI
status: draft
mode: interactive
owner: nick
human: nick
agent: nick
assignee: nick
contexts:
- relay/architecture
- relay/principles
- relay/codebase
- relay/current-direction
- relay/project-stage
- dev/code
skills: []
workflow: null
---

## Description

Add the `relay skill update` CLI surface for imported/adapted skills.

This is the updater implementation slice of
`add-imported-skill-update-check`. The broader ticket owns the full
metadata/install/Dream integration story; this ticket should produce the
updater engine and command behavior that Dream can call.

## Context

Relay skills stay as plain directories under `relay-os/skills/`. Imported
skills need explicit update mechanics so upstream changes can be reviewed
without silently overwriting local adaptations.

The updater should consume the imported-skill provenance metadata defined by
the metadata/import work. If that metadata has not landed yet, add the minimal
reader/fixture shape needed to make the updater testable, but keep the full
installer UX out of this ticket.

## Proposed command surface

- `relay skill update <name>` updates one imported skill.
- `relay skill update --all` updates every imported skill with usable
  provenance metadata.
- `relay skill update ... --json` emits a structured summary for Dream or
  other automation.

## Required behavior

- Fetch or materialize the upstream skill source into a temporary location.
- Compare upstream contents with the installed provenance ref/digest.
- Detect local adaptations by comparing the installed tree against the recorded
  installed digest/ref.
- If upstream changed and the local skill is clean, replace the installed skill
  directory with the upstream version and refresh provenance metadata.
- If upstream changed and the local skill has local adaptations, do not
  overwrite. Skip that skill and report the conflicting paths/refs.
- If provenance is missing, incomplete, or the source cannot be fetched, report
  that explicitly.
- `--all` should keep processing independent skills and finish with a complete
  summary: updated, unchanged, skipped/conflicting, and failed.
- All changes remain normal git-visible file edits; there is no background
  sync service and no opaque package cache.

## Acceptance criteria

- [ ] `relay skill update <name>` updates one clean imported skill from its
      recorded upstream source.
- [ ] `relay skill update --all` walks all imported skills with metadata and
      updates all clean ones in a single working-tree diff.
- [ ] Locally adapted skills are skipped, not overwritten, with enough evidence
      for a human to resolve the conflict.
- [ ] Missing/incomplete provenance and source fetch failures are reported
      explicitly.
- [ ] `--json` returns a stable summary that Dream can put into a blackboard or
      PR body.
- [ ] Tests cover one unchanged skill, one clean update, one local adaptation,
      one provenance/fetch failure, and the `--all` summary.

## Out of scope

- Building the full `relay skill install` UX.
- Opening the Dream PR itself. Dream should call this command and use the
  summary; PR creation belongs in the Dream maintenance integration.
