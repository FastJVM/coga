---
name: bootstrap/dream/tasks/validate-drift
description: Run Coga's deterministic validator and classify validation drift into safe remediation buckets.
---

# Validate Drift

This skill is Dream's deterministic repo-health pass. It runs the same
validation surface as:

```
python -m coga.validate --json
```

It then classifies every validator issue into one of three buckets:

- `direct-fix` - safe to repair in a small Dream PR without changing task state.
- `pr-proposal` - a file-backed fix that needs a reviewable PR after reading the target.
- `human-needed` - lifecycle, ownership, secret, or ambiguous state decision.

## Known Skill Contract

- Purpose: deterministic repo-health validation and conservative safe repair
- Runs: `coga run validate-drift` from the active Dream task
- Inputs: `coga.toml`, `coga.local.toml`, task directories, workflow refs,
  context refs, skill refs, and optional Slack webhook reachability
- May change: a missing `<!-- coga:blackboard -->` fence + blackboard region
  in a task's `ticket.md`, only when `--fix` is
  enabled by the recipe's default safe-repair pass; repaired files may be
  committed and pushed only from a non-main repair branch when
  `--commit-and-push` is passed manually
- Action: `direct-fix`
- Idempotency: `coga validate --fix` only creates missing standard files and
  leaves existing files unchanged, so reruns converge on the same repo state
- Stop and ask: invalid validator JSON, validator process failure, unsafe push
  branch, lifecycle changes, unknown ownership, or secret access
- Output: append `## Dream Skill: validate-drift` to the Dream run blackboard
  and optionally post a one-line Slack summary

## How to Run

From the host repo root:

```
coga run validate-drift
```

Run it from the active Dream task after reading this contract. The agent launch
already carries `COGA_TASK_SLUG`, `COGA_TASK_DIR`, and
`COGA_TASK_BLACKBOARD`; the recipe inherits that metadata and appends its
result directly to the Dream task blackboard. Run from a stateless bootstrap
session there is no blackboard to append to — the recipe writes its report to
stdout instead of into a packaged `bootstrap/<name>/ticket.md`.

The default safe-repair pass applies the same conservative repair set as
`coga validate --fix`: append a missing blackboard fence + region to a `ticket.md` only. To
publish those repairs from a Dream repair branch, run the recipe manually with
`--commit-and-push`; it commits only repaired files and pushes the current
branch, refusing `main`/`master` by default.

The recipe exits `0` when validation completed, even if the validator found
issues. It exits non-zero only when the validator itself failed or emitted
invalid JSON.

## Output

The skill appends a concise section to the Dream run blackboard:

```
## Dream Skill: validate-drift
```

The section includes the exact command, issue counts by bucket, and one
remediation line per issue. When the default `--fix` pass repairs files, it
also lists the applied fixes. When `--post-slack` is passed, it posts a
one-line Slack summary against the active Dream task's `COGA_TASK_SLUG`.

## Flags

The recipe accepts:

- `--cwd <path>` — run validation from this repo directory (default: cwd).
- `--no-fix` — disable the default `coga validate --fix` repair pass.
- `--post-slack` — post the one-line summary to Slack against
  `COGA_TASK_SLUG`.
- `--commit-and-push` — commit any repaired files and push the current
  non-main branch (requires the fix pass).
- `--allow-main-push` — allow `--commit-and-push` on `main`/`master`.
- `--commit-message <subject>` — commit subject when pushing
  (default: `Dream: repair validation drift`).
- `--idle-hours <hours>` — passed through to `coga validate`.
- `--max-blackboard-kb <kb>` — passed through to `coga validate`.

The classifier covers every validator kind currently emitted by
`coga validate`. Anything new is routed to `human-needed` with an
"unknown validator issue kind" remediation so the operator notices the
new kind and extends the mapping.
