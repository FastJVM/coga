---
slug: recurring/skill-update
title: Skill update
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/period-task
skills: []
workflow:
  name: skill-update/run
  steps:
  - name: update
    skills:
    - bootstrap/skill-update
    assignee: agent
secrets: null
---

## Description

Update every clean imported (Coga-managed) skill in one reviewable PR.

Imported skills live as plain directories under `coga/skills/` with
`.coga-source.json` provenance. Once a week this ticket fires on its schedule
and its recipe runs `coga skill update --all --pr`, which:

1. walks every imported skill with recorded provenance,
2. rewrites in place each skill whose upstream digest changed and whose local
   copy is unmodified,
3. commits the clean updates onto the dedicated `coga/skill-update` branch
   and opens (or updates) one draft PR, and
4. appends a `## Skill Update` report to this period task's blackboard,
   bucketing every skill by raw update status.

Local adaptations are never overwritten: a skill whose local copy diverged, a
provenance conflict, or a fetch failure is left untouched and listed under the
report's follow-up heading for a human to resolve. Bundled (package-backed)
skills are not touched here — they refresh when the coga package is upgraded.

A week with no upstream changes is a quiet no-op: nothing is committed and no
PR is opened. A week with only follow-up statuses is intentionally loud: after
writing the `## Skill Update` report, the recipe exits non-zero so this period
task remains visible until a human resolves or parks it.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Skill Update

Generated: 2026-08-25T04:56:46+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python -m coga.cli skill update --all --json --pr --pr-title 'Update Coga-managed skills'`
Task: `recurring/skill-update`

Result: 15 skill(s): 1 updated, 0 need follow-up, 14 skipped.
PR: https://github.com/FastJVM/coga/pull/708

### Updated

- `gh-managed`: `delegated` (github) - delegated GitHub-backed skill updates to gh skill

### Skipped

- `bootstrap/delete-task`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/scan/contract-audit`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/scan/knowledge-scan`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/scan/scan-protocol`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/tasks/cleanup-orphan-markers`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/tasks/validate-drift`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/import`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/skill-update`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/ticket`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `browser/build-automation`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/calendar-reminder`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/gmail`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/google-calendar`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `retro/done-ticket`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`

### Run notes

- First attempt failed (exit 2): `git push` rejected with `! [rejected] coga/skill-update -> coga/skill-update (stale info)`.
  PR #678 merged and its remote branch was deleted, but the local
  `refs/remotes/origin/coga/skill-update` tracking ref still pointed at the old
  SHA, so the force-with-lease push saw a lease it could not satisfy.
  `git fetch --prune origin` cleared it and the rerun succeeded. This will
  recur every period after a merge+delete unless `coga skill update --pr`
  prunes (or fetches) the branch ref before pushing — worth a follow-up ticket.
- This period task directory has no `ticket.py`, so the run fired as an agent
  phase rather than headless. The template at
  `coga/recurring/skill-update/ticket.py` does have it; this instance was
  created before the template gained the file. Next period instantiates cleanly.
