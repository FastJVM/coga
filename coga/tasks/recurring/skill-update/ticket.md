---
slug: recurring/skill-update
title: Skill update
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/period-task
skills: []
period_generation: 6fbd8073-dc2a-47ab-a506-7037d152f4e9
workflow:
  name: skill-update/run
  steps:
  - name: update
    skills:
    - bootstrap/skill-update
    assignee: agent
secrets: null
step: 1 (update)
---

## Description

Update every clean remotely managed GitHub/URL skill in one reviewable PR.

Imported skills live as plain directories under `coga/skills/`. GitHub-backed
installs are tracked by `gh skill`'s own metadata. URL-installed skills instead
carry Coga's `.coga-source.json` provenance with `source_type = "url"`.
`coga skill install-local` is a third supported installation path: `gh skill`
records `local-path`, but its updater skips that directory because it has no
GitHub source metadata, and Coga's URL updater does not consume it. Hand-vendored
packs likewise have no managed update source. A freshly initialized repo
attempts to install the optional GitHub refs declared in `managed-skills.toml`,
but installation may be skipped or fail and operators may add any source shape
later. Once a week this ticket fires on its schedule and its `ticket.py` runs
`coga skill update --all --pr`, which:

1. delegates the installed GitHub-backed skills to `gh skill update --dir
   coga/skills --all`, then walks in Coga's own code every skill carrying
   `.coga-source.json` with `source_type = "url"`; local-backed and
   hand-vendored directories are outside both updater paths,
2. for URL-backed skills, rewrites in place only when the upstream digest
   changed and the local copy is unmodified; the delegated GitHub updater
   follows its own stored-tree-SHA policy,
3. commits the clean updates onto the dedicated `coga/skill-update` branch
   and opens (or updates) one draft PR, and
4. appends a `## Skill Update` report to this period task's blackboard,
   bucketing every result emitted by the GitHub, URL, and bundled paths.

Local-edit protection applies to URL-backed skills: a diverged local copy,
provenance conflict, or fetch failure is left untouched and listed under the
report's follow-up heading for a human to resolve. GitHub-backed directories
are upstream-owned by `gh skill update`; when its recorded tree SHA differs
from upstream, re-downloading can overwrite local modifications before the
draft PR is opened. That PR reviews the resulting upstream update; it does not
recover overwritten edits. Do not keep local adaptations in those directories.
Local-backed installs are pinned until an operator reviews their source and
reinstalls explicitly. They currently produce no per-skill update result, so
the weekly report neither lists nor verifies them; omission is not evidence
that their source or installed bytes are current. Hand-vendored directories
have the same unmanaged update posture.
Bundled (package-backed) skills are not touched here — they refresh when the
coga package is upgraded.

A week with no upstream changes is a quiet no-op: nothing is committed and no
PR is opened. A week with only follow-up statuses is intentionally loud: after
writing the `## Skill Update` report, `ticket.py` exits non-zero so this period
task remains visible until a human resolves or parks it.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
