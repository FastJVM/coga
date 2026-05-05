---
schedule: "0 9 * * 1"
schedule_comment: "Every Monday at 9am"
title: "Weekly dream scan"
mode: auto
workflow: bootstrap/dream-run
assignee: claude1
owner: marc
---

## Description

Run the Dream maintenance pass for this Relay repo.

Dream is this recurring task, not a workflow, daemon, global service, plugin
registry, or standalone skill. The task scans the ticket set, calls a fixed
ordered list of known maintenance skills, writes each result to this task's
blackboard, then writes one human-reviewable run summary.

### Ordered Skill Pass

Run these known skills in this order:

| Skill | When to run | Result |
| --- | --- | --- |
| `bootstrap/dream/tasks/validate-drift` | Always. | Deterministic repo validation, safe file-presence repairs, and validation drift classification. |
| `retro/done-ticket` | When an existing done ticket lacks the `## Retro` blackboard marker for `skill: retro/done-ticket` / `status: processed` and no open PR is adding that marker. | PR-required knowledge extraction; marks the source task blackboard so Dream can clean it later. |
| `bootstrap/dream/tasks/dev/stale-branches` | When the repo is a git code repo and branch cleanup evidence is useful. | Proposal-only branch cleanup evidence. |

That table is the dispatch contract. Do not auto-discover skills, scan a
plugin folder, or invent another maintenance step during the run. If a repo
wants a different maintenance loop, make another recurring task with its own
body and ordered skill list.

For each known skill:

1. Read the skill's `## Known Skill Contract`.
2. Run the skill exactly as its contract says.
3. Keep the skill's reads, writes, and decisions inside its declared scope.
4. Let the skill write its own `## Dream Skill: <name>` section to this
   Dream run's blackboard.
5. Record one result line for the run summary:
   `no-op`, `reported`, `proposed`, `direct-fixed`, `pr-opened`, or
   `human-needed`.

One known skill failing does not permit a replacement. Record the result and
continue only with known skills whose inputs do not depend on the blocked one.

### Skill: validate-drift

Run from the repo root:

```
python relay-os/skills/bootstrap/dream/tasks/validate-drift/run.py --fix --blackboard relay-os/tasks/<this-dream-task>/blackboard.md --slack-task <this-dream-task>
```

Replace `<this-dream-task>` with this Dream run task slug. The skill runs the
same deterministic surface as `relay validate --json`, classifies every issue,
and appends `## Dream Skill: validate-drift` to this run's blackboard.

With `--fix`, the skill applies only deterministic safe repairs currently
supported by `relay validate --fix`: create missing `blackboard.md` from the
standard template and create missing `log.md` as an empty append-only file. It
does not rewrite existing files, synthesize `ticket.md`, freeze workflows,
delete locks, or change lifecycle/assignee state.

Stale-lock rule: never delete a `task.lock` from age alone. The skill reports
stale locks as `human-needed`. A human must verify that no live terminal or
agent still owns the task, then remove the lock or relaunch with `--force`.

### Skill: retro/done-ticket

Read every existing task with `status: done`.

For each done task:

1. Read `relay-os/tasks/<slug>/blackboard.md`.
2. If the blackboard has `## Retro` with `skill: retro/done-ticket` and
   `status: processed`, do not run Retro again. The ticket is processed and can
   be deleted when the cleanup gate is satisfied.
3. If the marker is absent, inspect open PRs before launching Retro. An open
   PR counts as in flight when its diff adds the same `## Retro` /
   `skill: retro/done-ticket` / `status: processed` marker to
   `relay-os/tasks/<slug>/blackboard.md`.
4. If no current marker and no open PR marker exists, run `retro/done-ticket
   <slug>` for one selected done ticket. Prefer one Retro PR per Dream run
   unless a human asks for a batch.
5. If `relay-os/tasks/<slug>/` is already gone, it is not a Retro candidate.
   For audit, use git history for the deleted `blackboard.md`; the deleted
   marker is the record that Retro processed the task before cleanup.

Absence of the marker on an existing done ticket means the task has not been
processed by Retro. Do not infer completion from branch names, stale comments,
or old Dream run notes.

### Skill: dev/stale-branches

Run `bootstrap/dream/tasks/dev/stale-branches` only when this repo is a git code
repo and branch cleanup evidence is useful. The skill is `proposal-only`: it
collects exact branch evidence and proposed commands, but it does not delete
local branches, remote branches, or remote-tracking refs.

### Higher-Judgment Scan

After the ordered skill pass, read every ticket body and blackboard. Compare
against existing contexts, skills, and workflows. Look for:

- **Context gaps** - repeated task knowledge with no matching context.
- **Skill gaps** - repeated process struggle with no skill to teach it.
- **Workflow gaps** - groups of tickets following the same ad-hoc sequence.
- **Stale content** - contexts or skills that contradict recent blackboards.

Write proposals to this task's blackboard under **Findings**:

```
### Proposal: <short title>

**Kind:** context | skill | workflow | fix | staleness
**Target:** <file path or task id>

<one paragraph describing the proposed change>

<if it is a new file, include a draft of the content>
```

### Run Summary

At the end of the Dream run, append one run-level section to this task's
blackboard:

```
## Dream Run Summary
Generated: <timestamp>

### Skill Results
| Skill | Result | Output |
| --- | --- | --- |
| validate-drift | direct-fixed | 2 files repaired; 1 stale lock human-needed |
| retro/done-ticket | pr-opened | New context PR opened for one done ticket |
| dev/stale-branches | proposed | 3 merged local branches proposed |

### Findings
<count and one-line summary of knowledge-gap proposals>

### Human Needed
<short list of decisions or review gates>
```

Skill-specific evidence can be long, but the run summary should be short enough
for a human to scan.

### Slack

The validate-drift skill posts its own one-line Slack summary when run with
`--slack-task`. For the broader Dream scan, call:

```
relay slack --task <this-dream-task> --message "<summary>"
```

Keep the message to one line, for example: `Dream scan: 3 broken refs, 2
context proposals, 1 stale lock.`
