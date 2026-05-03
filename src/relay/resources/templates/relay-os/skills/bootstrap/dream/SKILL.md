---
name: bootstrap/dream
description: Scan the Relay repo for knowledge gaps, broken references, stale locks, and workflow patterns. Propose concrete fixes on the blackboard and summarize in Slack.
---

# Dream

Your job is to read the entire Relay repo and surface what's missing or drifting.
Write concrete proposals, not vague recommendations.

## Step 1 — Run the validate-drift worker

Run:

```
python relay-os/skills/bootstrap/dream/tasks/validate-drift/run.py --fix --blackboard relay-os/tasks/<this-dream-task>/blackboard.md --slack-task <this-dream-task>
```

Replace `<this-dream-task>` with the slug of this Dream run. The worker runs
the same deterministic surface as `relay validate --json`, classifies every
issue, and appends a concise `## Dream Worker: validate-drift` section to this
run's blackboard. It uses three action buckets:

- `direct-fix` — safe to apply in a small Dream PR without changing task state.
- `pr-proposal` — file-backed fix that needs a reviewable PR after reading the target.
- `human-needed` — lifecycle, ownership, lock, secret, or ambiguous state decision.

With `--fix`, the worker applies only the deterministic safe repairs currently
supported by `relay validate --fix`: create missing `blackboard.md` from the
standard template and create missing `log.md` as an empty append-only file. It
does not rewrite existing files, synthesize `ticket.md`, freeze workflows,
delete locks, or change lifecycle/assignee state.

If the Dream run is already on a repair branch and the safe fixes should be
published immediately, add `--commit-and-push`. That mode commits only the
files repaired by the worker and pushes the current branch. It refuses to push
from `main`/`master` unless a human explicitly passes `--allow-main-push`.

Validator issue kinds include:

- `missing-file` — a task is missing ticket.md/blackboard.md/log.md.
- `stale-lock` — a lock file is older than the configured threshold (likely a crashed agent).
- `invalid-status` — a ticket's status value isn't one of the allowed ones.
- `unknown-assignee` — assignee is not a known human or agent nickname.
- `broken-context` / `broken-skill` — a reference points to a file that doesn't exist.
- `stuck-active` — task is `active` but `log.md` hasn't been written to in a while.

Stale-lock rule: never delete a `task.lock` from age alone. The worker reports
stale locks as `human-needed`. A human must verify that no live terminal or
agent still owns the task, then remove the lock or relaunch with `--force`.

Optional dev/code worker templates live under `tasks/dev/`. For example,
`tasks/dev/stale-branches` inspects git branches and writes a reviewable cleanup
proposal with exact evidence; it is proposal-only and does not delete branches.

## Step 2 — Scan for knowledge gaps (this is the harder part)

Read every ticket (its body and blackboard). Compare against existing contexts,
skills, and workflows. Look for:

- **Context gaps** — patterns that repeat across multiple tickets but aren't
  captured in any context. Example: three different tickets mention "429 retry
  with Retry-After" and there's no `email/retry-patterns` context. Propose the
  missing context with a one-paragraph scope.
- **Skill gaps** — workflow steps with no `skill:` reference where blackboards
  show agents repeatedly asking the same questions. Propose a skill file with
  the boilerplate answers.
- **Workflow gaps** — groups of tickets that follow the same ad-hoc sequence
  without a named workflow. Propose the workflow name, steps, and which steps
  deserve skill refs.
- **Stale content** — a context or skill that contradicts what's in recent
  blackboards. Propose the specific edit (show old vs. new).

## Step 3 — Write proposals to the blackboard

Every proposal goes in the **Findings** section of *your* task's blackboard,
with this shape:

```
### Proposal: <short title>

**Kind:** context | skill | workflow | fix | staleness
**Target:** <file path or task id>

<one paragraph describing the proposed change>

<if it's a new file, include a draft of the content>
```

No proposal is too small. A human reviews and accepts or rejects — don't
pre-filter.

## Step 4 — Summarize for Slack

The validate-drift worker posts its own one-line Slack summary when run with
`--slack-task`. For the broader Dream scan, call `relay slack --task
<your-task-id> --message "<summary>"`. One line. Example: `Dream scan:
3 broken refs, 2 context proposals, 1 stale lock.`

## Step 5 — Don't take action

Your role is to propose, not to edit files directly (outside of your own
blackboard). The human decides what to accept.
