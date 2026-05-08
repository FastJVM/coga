---
name: bootstrap/dream/tasks/validate-drift
description: Run Relay's deterministic validator and classify validation drift into safe remediation buckets.
script: run.py
---

# Validate Drift

This skill is Dream's deterministic repo-health pass. It runs the same
validation surface as:

```
python -m relay.validate --json
```

It then classifies every validator issue into one of three buckets:

- `direct-fix` - safe to repair in a small Dream PR without changing task state.
- `pr-proposal` - a file-backed fix that needs a reviewable PR after reading the target.
- `human-needed` - lifecycle, ownership, lock, secret, or ambiguous state decision.

## Known Skill Contract

- Purpose: deterministic repo-health validation and conservative safe repair
- Runs: a `mode: script` Relay task whose workflow step references
  `bootstrap/dream/tasks/validate-drift`
- Inputs: `relay.toml`, `relay.local.toml`, task directories, workflow refs,
  context refs, skill refs, lock files, and optional Slack webhook reachability
- May change: missing `blackboard.md` and `log.md` files only when `--fix` is
  enabled by the script's default safe-repair pass; repaired files may be
  committed and pushed only from a non-main repair branch when
  `--commit-and-push` is passed manually
- Action: `direct-fix`
- Idempotency: `relay validate --fix` only creates missing standard files and
  leaves existing files unchanged, so reruns converge on the same repo state
- Stop and ask: invalid validator JSON, validator process failure, unsafe push
  branch, stale locks, lifecycle changes, unknown ownership, or secret access
- Output: append `## Dream Skill: validate-drift` to the Dream run blackboard
  and optionally post a one-line Slack summary

## How to Run

From the host repo root:

```
relay launch <validate-drift-child-task>
```

The child task must be `mode: script` and its current workflow step must
reference `bootstrap/dream/tasks/validate-drift`. Relay injects
`RELAY_TASK_SLUG`, `RELAY_TASK_DIR`, and `RELAY_TASK_BLACKBOARD`; the script
uses that metadata to append its result to the child task blackboard.

The default safe-repair pass applies the same conservative repair set as
`relay validate --fix`: create missing `blackboard.md` and `log.md` only. To
publish those repairs from a Dream repair branch, run the script manually with
`--commit-and-push`; it commits only repaired files and pushes the current
branch, refusing `main`/`master` by default.

The skill exits `0` when validation completed, even if the validator found
issues. It exits non-zero only when the validator itself failed or emitted
invalid JSON.

## Output

The skill appends a concise section to the Dream run blackboard:

```
## Dream Skill: validate-drift
```

The section includes the exact command, issue counts by bucket, and one
remediation line per issue. When `--fix` repairs files, it also lists the
applied fixes. When `--slack-task` is provided, it posts a one-line Slack
summary against that task.

## Safety

Stale locks are never deleted from age alone. A stale-lock issue is classified
as `human-needed`; a human must verify no live terminal or agent owns the task
before removing `task.lock` or relaunching with `--force`.
