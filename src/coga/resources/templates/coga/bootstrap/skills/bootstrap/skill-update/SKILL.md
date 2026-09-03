---
name: bootstrap/skill-update
description: Update clean imported Coga-managed skills into one reviewable PR, and surface conflicting or skipped skills as follow-up work.
---

# Skill Update

This skill documents the skill-update run behind the
`recurring/skill-update/` task, whose `ticket.py` calls
`coga.skill_update.run_skill_update_recipe` directly — no agent, no composed
prompt. The run performs `coga skill update --all --pr`: GitHub-backed skills
are delegated to `gh skill update`, while URL-backed skills use Coga's digest
and provenance checks. Updates land in one draft PR on a dedicated branch.
URL-backed local adaptations and provenance conflicts are left untouched and
reported; GitHub-backed directories follow `gh skill`'s stored-tree-SHA policy
and can be overwritten before that PR is opened. Bundled (package-backed)
skills are not updated here; they ship with the coga package and refresh when
the package is upgraded.

The skill never decides *what* a conflicting skill should become. It only
applies the clean updates and records the buckets; the conflicts and skips
surface on the task blackboard as follow-up work for the human reviewing the
PR.

## Known Skill Contract

- Purpose: update clean imported skills into one reviewable PR and report the
  skills that need human follow-up.
- Runs: the period task's `ticket.py` in its inherited task context; the
  same behavior is available by hand as `coga run skill-update`.
- Inputs: the installed skills under `coga/skills/`; `gh skill`'s own metadata
  for GitHub-backed installs; Coga `.coga-source.json` provenance for
  URL-backed installs; and (for the PR) git plus `gh` against the control-plane
  checkout. Hand-vendored and bundled skills have no managed source here and
  are not updated by this run.
- May change: imported skill files under `coga/skills/` (rewritten in place
  by `coga skill update`), committed onto the dedicated `coga/skill-update`
  branch — never the caller's branch. The clean updates are published as a
  draft PR; nothing is merged.
- Action: `pr-required`
- Idempotency: URL-backed updates overwrite only when the upstream digest
  changed and the local tree still matches its recorded installed digest.
  GitHub-backed updates rely on `gh skill`'s stored tree SHA. With no upstream
  changes the combined run makes no commit and opens no PR; unlike the URL
  path, the delegated GitHub path does not promise to preserve local edits when
  upstream changed.
- Stop and ask: a URL-backed conflict or skipped local adaptation, or a failure
  from either updater, needs a human — the skill reports it and does not force
  the URL update. If those follow-ups are the only result and no PR is opened,
  `ticket.py` exits non-zero after writing the report so the period task
  remains visible. Do not keep local adaptations in GitHub-backed directories:
  the draft PR can review a resulting overwrite but cannot recover it.
- Output: append `## Skill Update` to the task blackboard, bucketing every
  skill by its update status and linking the PR when one was opened. A run that
  fails before it classifies anything appends the same section carrying a
  `### Failed` block with the command and its stderr, so a hard failure is as
  legible in the run record as a follow-up — the recurring sweep discards a
  task's stderr, so a diagnostic written only there is lost.

## How to Run

From the host repo root:

```
coga run skill-update
```

Coga injects `COGA_TASK_SLUG` and `COGA_TASK_BLACKBOARD`; the run appends
its result to that blackboard. `coga launch` supplies those variables from the
instantiated period task before it runs `ticket.py`. A stateless bootstrap target has no
blackboard, so run from one the recipe writes its report to stdout rather than
into a packaged `bootstrap/<name>/ticket.md`.

The skill runs `coga skill update --all --pr --json`, then groups the results
by their raw update status so each status (e.g. `updated`, URL-backed
`skipped-local-adaptation` / `conflict`, or `failed`) is reported in its own
bucket. It exits non-zero when the `coga skill update` command itself failed,
or when a run needs human follow-up but opened no PR to carry that follow-up
forward.

## Output

The skill appends a section to the task blackboard:

```
## Skill Update
```

The section includes the exact command, a one-line result summary
(updated / follow-up / skipped counts), the PR link when one was opened, and
one line per skill grouped by update status. Statuses other than a clean update
or a benign no-op are surfaced under a follow-up heading so conflicts and
skipped skills are not lost.

## Flags

The recipe accepts:

- `--cwd <path>` — run the update from this repo directory (default: cwd).
- `--pr-title <title>` — title for the skill-update PR.
- `--no-pr` — collect and classify updates without opening a PR. Useful for a
  dry run; the default opens the PR.
