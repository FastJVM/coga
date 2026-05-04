---
name: bootstrap/dream
description: Scan the Relay repo for knowledge gaps, broken references, stale locks, and workflow patterns. Propose concrete fixes on the blackboard and summarize in Slack.
---

# Dream

Dream is the repo's recurring maintenance orchestrator. It discovers enabled
workers, runs each worker within its declared contract, then summarizes what
happened for a human reviewer. Do not turn Dream into one large cleanup script:
each maintenance concern lives in its own worker under `tasks/`.

The current shipped template lives at `relay-os/skills/bootstrap/dream/`. When
Dream moves to the project-owned namespace, the same contract applies with the
orchestrator at `relay-os/skills/dream/orchestrate/SKILL.md` and workers under
`relay-os/skills/dream/tasks/`.

## Step 1 - Discover enabled workers

Treat every `SKILL.md` under this Dream root's `tasks/` directory as an enabled
worker. In the current template that means:

```
relay-os/skills/bootstrap/dream/tasks/**/SKILL.md
```

After the namespace move, the same discovery rule becomes:

```
relay-os/skills/dream/tasks/**/SKILL.md
```

Project authors enable a worker by adding its `SKILL.md`; they disable one by
removing or moving that file. There is no hidden registry, service, database, or
cache. Skip `_template` scaffolds. Run `tasks/validate-drift` first when present
so deterministic repo health is visible before higher-judgment workers. Run the
remaining workers in path order unless a worker's own contract says it must be
run only after another worker.

Before dispatching a worker, read its `SKILL.md`. If it does not contain the
required `## Worker Contract` section, do not run it. Record the malformed
worker as `human-needed` in the run summary so the convention fails loud.

## Worker Contract

Every Dream worker is an ordinary SKILL.md file. Keep standard frontmatter
small: `name`, `description`, and optional `script` when `mode: script` or a
direct runner needs one. Worker-specific metadata belongs in the body under:

```
## Worker Contract

- Scope: <relay-core | dev/code | project-specific domain>
- Unit: <one repo pass | one done ticket | one branch inventory | ...>
- Inputs: <files, commands, APIs, or task state the worker may read>
- May change: <none | exact files/refs the worker may edit>
- Action: <report-only | proposal-only | pr-required | direct-fix>
- Risk: <low | review | destructive>
- Idempotency: <marker or proof that a unit was already handled>
- Stop and ask: <conditions that require human review before continuing>
- Output: <blackboard section, PR link, created ticket, or no-op result>
```

Use these action values consistently:

- `report-only` - read state and write a result to the Dream run blackboard.
- `proposal-only` - write evidence and proposed commands/edits, but do not
  mutate the repo or external systems.
- `pr-required` - make durable file changes only on a branch and open a PR.
- `direct-fix` - may make the narrow deterministic change named by the worker.

Destructive behavior is never implicit. Deleting task directories, deleting
git refs, removing locks, changing lifecycle state, or touching secrets requires
exact evidence and human review by default. A worker may declare direct
destructive behavior only when the rule is deterministic, narrow, and named in
`May change`; otherwise use `proposal-only` or `pr-required`.

Each worker must also define its idempotency proof. Examples: a PR body marker
for a done-ticket retro, a deterministic validation command whose safe fixes are
idempotent, or "no repo mutation; rerun regenerates the same proposal."

## Step 2 - Dispatch workers independently

For each enabled worker:

1. Read the worker's `## Worker Contract`.
2. Run the worker exactly as its `How to Run` or `script:` contract says.
3. Keep the worker's reads, writes, and decisions inside its declared scope.
4. Let the worker write its own `## Dream Worker: <name>` section to this
   Dream run's blackboard.
5. Record one result line for the run summary:
   `no-op`, `reported`, `proposed`, `direct-fixed`, `pr-opened`, or
   `human-needed`.

One worker failing does not give you permission to improvise another worker's
behavior. If a worker stops for human review, record that result and continue
only with workers whose inputs do not depend on the blocked one.

## Built-in worker - validate-drift

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
proposal with exact evidence; it is `proposal-only` and does not delete
branches.

## Step 3 - Scan for knowledge gaps

After worker dispatch, do the higher-judgment Dream scan yourself. Read every
ticket (its body and blackboard). Compare against existing contexts, skills,
and workflows. Look for:

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
- **Stale content** - a context or skill that contradicts what's in recent
  blackboards. Propose the specific edit (show old vs. new).

## Step 4 - Write proposals to the blackboard

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

## Step 5 - Write one run summary

At the end of the Dream run, append one run-level section to your task
blackboard:

```
## Dream Run Summary
Generated: <timestamp>

### Worker Results
| Worker | Result | Output |
| --- | --- | --- |
| validate-drift | direct-fixed | 2 files repaired; 1 stale lock human-needed |
| dev/stale-branches | proposed | 3 merged local branches proposed |

### Findings
<count and one-line summary of knowledge-gap proposals>

### Human Needed
<short list of decisions or review gates>
```

Do not scatter run status across unrelated sections. Worker-specific evidence
can be long, but the run summary should be short enough for a human to scan.

## Step 6 - Summarize for Slack

The validate-drift worker posts its own one-line Slack summary when run with
`--slack-task`. For the broader Dream scan, call `relay slack --task
<your-task-id> --message "<summary>"`. One line. Example: `Dream scan:
3 broken refs, 2 context proposals, 1 stale lock.`

## Step 7 - Don't take action outside a worker contract

Your default role is to propose, not to edit files directly outside of your own
blackboard. A worker may edit only when its contract explicitly allows it and
the action stays inside `May change`. The human decides what to accept.
