---
name: bootstrap/dream
description: Scan the Relay repo for knowledge gaps, broken references, stale locks, and workflow patterns. Propose concrete fixes on the blackboard and summarize in Slack.
---

# Dream

Dream is Relay's bootstrap maintenance feature. It runs a small set of known
maintenance skills, then summarizes what happened for a human reviewer. Do not
turn Dream into one large cleanup script, and do not treat it as a project
extension registry.

The shipped skill lives at `relay-os/skills/bootstrap/dream/SKILL.md`. Known
skills may live under `relay-os/skills/bootstrap/dream/tasks/`, but they run
only when this orchestrator names them. Adding arbitrary files under `tasks/`
does not enable them.

## Step 1 - Run the known Dream skills

Run these known skills in this order:

| Skill | When to run | Result |
| --- | --- | --- |
| `bootstrap/dream/tasks/validate-drift` | Always. | Deterministic repo validation, safe file-presence repairs, and validation drift classification. |
| `bootstrap/dream/tasks/retro-done-ticket` | When a completed task has durable knowledge to extract. Run one done ticket at a time. | Context/skill extraction PR and Slack summary. |
| `bootstrap/dream/tasks/dev/stale-branches` | When the repo is a git code repo and branch cleanup evidence is useful. | Proposal-only branch cleanup evidence. |

That list is the dispatch contract. Dream does not recursively discover skill files
and it does not offer a project-level plugin API. If a repo wants a different
maintenance loop, it can define one directly in user space, for example `rem`,
`ops/dream`, or another normal skill/workflow/recurring task. That user-space
loop owns its own dispatch rules, state, naming, and conventions; it is not
plugged into bootstrap Dream. Relay's shipped Dream remains this explicit
bootstrap feature.

## Known Skill Contract

Each known Dream skill is an ordinary SKILL.md file. Keep standard frontmatter
small: `name`, `description`, and optional `script` when a direct runner needs
one. The body must include:

```
## Known Skill Contract

- Purpose: <what maintenance question this skill answers>
- Runs: <exact command, manual instructions, or script entry point>
- Inputs: <files, commands, APIs, or task state the skill may read>
- May change: <none | exact files/refs the skill may edit>
- Action: <report-only | proposal-only | pr-required | direct-fix>
- Idempotency: <why rerunning avoids duplicate work>
- Stop and ask: <conditions that require human review before continuing>
- Output: <blackboard section, PR link, created ticket, or no-op result>
```

Use these action values consistently:

- `report-only` - read state and write a result to the Dream run blackboard.
- `proposal-only` - write evidence and proposed commands/edits, but do not
  mutate the repo or external systems.
- `pr-required` - make durable file changes only on a branch and open a PR.
- `direct-fix` - may make the narrow deterministic change named by the skill.

Destructive behavior is never implicit. Deleting task directories, deleting
git refs, removing locks, changing lifecycle state, or touching secrets requires
exact evidence and human review by default. A skill may declare direct
destructive behavior only when the rule is deterministic, narrow, and named in
`May change`; otherwise use `proposal-only` or `pr-required`.

Each known skill must also define its idempotency proof. Examples: a PR body marker
for a done-ticket retro, a deterministic validation command whose safe fixes are
idempotent, or "no repo mutation; rerun regenerates the same proposal."

## Step 2 - Dispatch the known skills

For each known skill in the dispatch table:

1. Read the skill's `## Known Skill Contract`.
2. Run the skill exactly as its contract says.
3. Keep the skill's reads, writes, and decisions inside its declared scope.
4. Let the skill write its own `## Dream Skill: <name>` section to this
   Dream run's blackboard.
5. Record one result line for the run summary:
   `no-op`, `reported`, `proposed`, `direct-fixed`, `pr-opened`, or
   `human-needed`.

One known skill failing does not give you permission to invent a replacement or
scan for new skills. If a skill stops for human review, record that result and
continue only with known skills whose inputs do not depend on the blocked one.

## Known skill - validate-drift

Run:

```
python relay-os/skills/bootstrap/dream/tasks/validate-drift/run.py --fix --blackboard relay-os/tasks/<this-dream-task>/blackboard.md --slack-task <this-dream-task>
```

Replace `<this-dream-task>` with the slug of this Dream run. The skill runs
the same deterministic surface as `relay validate --json`, classifies every
issue, and appends a concise `## Dream Skill: validate-drift` section to this
run's blackboard. It uses three action buckets:

- `direct-fix` — safe to apply in a small Dream PR without changing task state.
- `pr-proposal` — file-backed fix that needs a reviewable PR after reading the target.
- `human-needed` — lifecycle, ownership, lock, secret, or ambiguous state decision.

With `--fix`, the skill applies only the deterministic safe repairs currently
supported by `relay validate --fix`: create missing `blackboard.md` from the
standard template and create missing `log.md` as an empty append-only file. It
does not rewrite existing files, synthesize `ticket.md`, freeze workflows,
delete locks, or change lifecycle/assignee state.

If the Dream run is already on a repair branch and the safe fixes should be
published immediately, add `--commit-and-push`. That mode commits only the
files repaired by the skill and pushes the current branch. It refuses to push
from `main`/`master` unless a human explicitly passes `--allow-main-push`.

Validator issue kinds include:

- `missing-file` — a task is missing ticket.md/blackboard.md/log.md.
- `stale-lock` — a lock file is older than the configured threshold (likely a crashed agent).
- `invalid-status` — a ticket's status value isn't one of the allowed ones.
- `unknown-assignee` — assignee is not a known human or agent nickname.
- `broken-context` / `broken-skill` — a reference points to a file that doesn't exist.
- `stuck-active` — task is `active` but `log.md` hasn't been written to in a while.

Stale-lock rule: never delete a `task.lock` from age alone. The skill reports
stale locks as `human-needed`. A human must verify that no live terminal or
agent still owns the task, then remove the lock or relaunch with `--force`.

## Known skill - retro-done-ticket

For each completed task that is ready to archive, run exactly one ticket at a
time:

```
python relay-os/skills/bootstrap/dream/tasks/retro-done-ticket/run.py <done-task-slug> --commit-and-push --create-pr --blackboard relay-os/tasks/<this-dream-task>/blackboard.md --slack-task <this-dream-task>
```

Replace `<done-task-slug>` with the done task being extracted. The skill reads
that task's `ticket.md`, `blackboard.md`, and `log.md`, writes warranted
context blocks or new context files, rarely creates a skill file when process
evidence explicitly warrants it, appends a `## Dream Worker: retro-done-ticket`
report to this Dream run's blackboard, commits/pushes the extraction branch,
creates or reuses a PR, and posts a Slack FYI.

The report includes concrete context/skill artifacts, evidence highlights,
explicit notes that the source ticket and task branches were not touched, and a
PR body snippet with a durable source ref like
`abc123def456:relay-os/tasks/<done-task-slug>/`.

Non-`done` tickets are a no-op. Missing task files are errors. This skill does
not delete tickets or git branches; those are separate Dream skills.

The known `tasks/dev/stale-branches` skill inspects git branches and writes a
reviewable cleanup proposal with exact evidence. It is `proposal-only` and does
not delete branches.

## Step 3 - Scan for knowledge gaps

After known skill dispatch, do the higher-judgment Dream scan yourself. Read every
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

### Skill Results
| Skill | Result | Output |
| --- | --- | --- |
| validate-drift | direct-fixed | 2 files repaired; 1 stale lock human-needed |
| dev/stale-branches | proposed | 3 merged local branches proposed |

### Findings
<count and one-line summary of knowledge-gap proposals>

### Human Needed
<short list of decisions or review gates>
```

Do not scatter run status across unrelated sections. Skill-specific evidence
can be long, but the run summary should be short enough for a human to scan.

## Step 6 - Summarize for Slack

The validate-drift skill posts its own one-line Slack summary when run with
`--slack-task`. For the broader Dream scan, call `relay slack --task
<your-task-id> --message "<summary>"`. One line. Example: `Dream scan:
3 broken refs, 2 context proposals, 1 stale lock.`

## Step 7 - Don't take action outside a known skill contract

Your default role is to propose, not to edit files directly outside of your own
blackboard. A skill may edit only when its contract explicitly allows it and
the action stays inside `May change`. The human decides what to accept.
