---
name: bootstrap/dream/tasks/validate-drift
description: Run Relay's deterministic validator and classify validation drift into safe remediation buckets.
script: run.py
---

# Validate Drift

This worker is Dream's deterministic repo-health pass. It runs the same
validation surface as:

```
python -m relay.validate --json
```

It then classifies every validator issue into one of three buckets:

- `direct-fix` - safe to repair in a small Dream PR without changing task state.
- `pr-proposal` - a file-backed fix that needs a reviewable PR after reading the target.
- `human-needed` - lifecycle, ownership, lock, secret, or ambiguous state decision.

## How to Run

From the host repo root:

```
python relay-os/skills/bootstrap/dream/tasks/validate-drift/run.py --blackboard relay-os/tasks/<dream-run-task>/blackboard.md
```

Replace `<dream-run-task>` with the current Dream run task slug.

The worker exits `0` when validation completed, even if the validator found
issues. It exits non-zero only when the validator itself failed or emitted
invalid JSON.

## Output

The worker appends a concise section to the Dream run blackboard:

```
## Dream Worker: validate-drift
```

The section includes the exact command, issue counts by bucket, and one
remediation line per issue.

## Safety

Stale locks are never deleted from age alone. A stale-lock issue is classified
as `human-needed`; a human must verify no live terminal or agent owns the task
before removing `task.lock` or relaunching with `--force`.
