---
name: bootstrap/skill-update
description: Update clean imported Coga-managed skills into one reviewable PR, and surface conflicting or skipped skills as follow-up work.
script: run.py
---

# Skill Update

This skill is the maintenance pass for imported (Coga-managed) skills. It is
the script body of the `recurring/skill-update/` task. It runs
`coga skill update --all --pr`: every clean update lands in one draft PR on a
dedicated branch, while any skill that cannot be updated cleanly — a local
adaptation, a provenance conflict, a fetch failure — is left untouched and
reported so a human can follow up. Bundled (package-backed) skills are not
updated here; they ship with the coga package and refresh on
`coga init --update`.

The skill never decides *what* a conflicting skill should become. It only
applies the clean updates and records the buckets; the conflicts and skips
surface on the task blackboard as follow-up work for the human reviewing the
PR.

## Known Skill Contract

- Purpose: update clean imported skills into one reviewable PR and report the
  skills that need human follow-up.
- Runs: a `mode: script` Coga task whose workflow step references
  `bootstrap/skill-update`.
- Inputs: the installed skills under `coga-os/skills/`, their recorded
  `.coga-source.json` provenance, and (for the PR) git plus `gh` against the
  control-plane checkout.
- May change: imported skill files under `coga-os/skills/` (rewritten in place
  by `coga skill update`), committed onto the dedicated `coga/skill-update`
  branch — never the caller's branch. The clean updates are published as a
  draft PR; nothing is merged.
- Action: `pr-required`
- Idempotency: `coga skill update` only overwrites a skill whose recorded
  upstream digest changed and skips any locally-adapted skill, so a rerun with
  no upstream changes makes no commit and opens no PR.
- Stop and ask: any skill reported with a follow-up status (a conflict, a
  skipped local adaptation, or a failure) needs a human — the skill reports it
  and does not force the update. If those follow-ups are the only result and
  no PR is opened, the script exits non-zero after writing the report so the
  period task remains visible.
- Output: append `## Skill Update` to the task blackboard, bucketing every
  skill by its update status and linking the PR when one was opened.

## How to Run

From the host repo root:

```
coga launch <skill-update-task>
```

The task must be `mode: script` and its current workflow step must reference
`bootstrap/skill-update`. Coga injects `COGA_TASK_SLUG` and
`COGA_TASK_BLACKBOARD`; the script appends its result to that blackboard.

The skill runs `coga skill update --all --pr --json`, then groups the results
by their raw update status so each status (e.g. `updated`,
`skipped-local-adaptation`, a future `conflict`, `failed`) is reported in its
own bucket. It exits non-zero when the `coga skill update` command itself
failed, or when a run needs human follow-up but opened no PR to carry that
follow-up forward.

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

The script accepts:

- `--cwd <path>` — run the update from this repo directory (default: cwd).
- `--pr-title <title>` — title for the skill-update PR.
- `--no-pr` — collect and classify updates without opening a PR. Useful for a
  dry run; the default opens the PR.
