Run the Dream cleanup pass for this Relay repo.

Dream is Relay's generic cleanup pass. It scans every ticket, runs the fixed
Relay housekeeping skills, proposes cleanup, writes each result to this task's
blackboard, then writes one human-reviewable run summary.

Dream is not REM. Repo/user-specific recurring maintenance belongs in a
separate REM task under `relay-os/recurring/`, with its own cadence, skill
order, and output conventions.

### Console Progress

Write short progress updates to the console before and after each major phase:
validate-drift, done-ticket classification, Retro handoff, cleanup proposal,
higher-judgment scan, Slack, and final bump. Include the command or file path
being acted on and the result count when available. If a phase is skipped,
say why. The blackboard remains the durable record; console progress is for
the human watching the run.

### Ordered Skill Pass

Run these known skills in this order:

| Skill | When to run | Result |
| --- | --- | --- |
| `bootstrap/dream/tasks/validate-drift` | Always. | Deterministic repo validation, safe file-presence repairs, and validation drift classification. |
| `retro/done-ticket` | When an existing done ticket lacks the `## Retro` blackboard marker for `skill: retro/done-ticket` / `status: processed` and no open PR is adding that marker or deleting that task directory. | PR-required knowledge extraction; records the marker in PR history and deletes the source task directory in the same PR. |
| `bootstrap/dream/tasks/cleanup-orphan-markers` | Always. | Deterministic detection and PR-required deletion of done tickets whose blackboard already carries the processed Retro marker but whose task directory still exists. |

That table is the dispatch contract. Do not auto-discover skills, scan a
plugin folder, or invent another maintenance step during the run. If a repo
wants a different maintenance loop, make another task with its own body and
ordered skill list.

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

`python relay-os/skills/bootstrap/dream/tasks/validate-drift/run.py --fix --blackboard relay-os/tasks/<this-dream-task>/blackboard.md --slack-task <this-dream-task>`

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
   `status: processed`, do not run Retro again. The ticket is processed; if no
   open PR already deletes it, it is eligible for the cleanup gate below.
3. If the marker is absent, inspect open PRs before launching Retro. An open
   PR counts as in flight when its diff adds the same `## Retro` /
   `skill: retro/done-ticket` / `status: processed` marker to
   `relay-os/tasks/<slug>/blackboard.md` or deletes
   `relay-os/tasks/<slug>/`.
4. If no current marker and no open PR marker exists, run `retro/done-ticket
   <slug>` for one selected done ticket. Prefer one Retro PR per Dream run
   unless a human asks for a batch. Run Retro in a subagent. The full ticket
   evidence (`ticket.md`, `blackboard.md`, `log.md`, plus every context and
   skill file) would otherwise bloat the main Dream context. The subagent
   must open a PR that records the marker and deletes the source task directory
   in that same PR, then return only the PR URL and a one-line result; the raw
   evidence stays inside the subagent.
5. If `relay-os/tasks/<slug>/` is already gone, it is not a Retro candidate.
   For audit, use git history for the deleted `blackboard.md`; the deleted
   marker is the record that Retro processed the task before cleanup.

Absence of the marker on an existing done ticket means the task has not been
processed by Retro unless an open PR is already deleting that exact task
directory. Do not infer completion from branch names, stale comments, or old
Dream run notes.

### Skill: cleanup-orphan-markers

Run from the repo root:

`python relay-os/skills/bootstrap/dream/tasks/cleanup-orphan-markers/run.py --open-prs --blackboard relay-os/tasks/<this-dream-task>/blackboard.md --slack-task <this-dream-task>`

Replace `<this-dream-task>` with this Dream run task slug. The script enforces
the cleanup gate deterministically and opens a delete-only PR for each
orphan-marker ticket. Detection rules — no LLM judgment:

- exact `status: done` in ticket frontmatter;
- a `## Retro` block in the blackboard containing both
  `skill: retro/done-ticket` and `status: processed`;
- exact slug match (no prefix matching);
- no open PR already touching `relay-os/tasks/<slug>/`.

The deletion lives in the PR (not the working tree) so the human reviews or
edits before merge. Result line for the Dream summary: `pr-opened` when at
least one PR is opened, `no-op` when no candidates exist, `human-needed` when
the script reports an error. Do not auto-merge.

Drop `--open-prs` for a dry-run that only reports candidates to the
blackboard.

### Higher-Judgment Scan

After the ordered skill pass, delegate this step to a subagent. The scan reads
every ticket body and blackboard and compares them against existing contexts,
skills, and workflows. The subagent should return only the findings list; the
raw ticket and blackboard contents stay inside the subagent.

Look for:

- context gaps: repeated task knowledge with no matching context;
- skill gaps: repeated process struggle with no skill to teach it;
- workflow gaps: groups of tickets following the same ad-hoc sequence;
- stale content: contexts or skills that contradict recent blackboards.

Write proposals to this task's blackboard under `Findings`. Each proposal
should include a short title, kind, target file or task, one paragraph
describing the proposed change, and draft content when a new file is proposed.

### Run Summary

At the end of the Dream run, append one top-level `Dream Run Summary` section
to this task's blackboard. Include the generation time, a skill result table,
finding counts with one-line summaries, and any human-needed decisions or
review gates. Keep the run summary short enough for a human to scan.

### Slack

The validate-drift skill posts its own one-line Slack summary when run with
`--slack-task`. For the broader Dream scan, call:

`relay slack --task <this-dream-task> --message "<summary>"`

Keep the message to one line, for example:
`Dream scan: 3 broken refs, 2 context proposals, 1 stale lock.`

Run `relay bump <this-dream-task>` as the last action after the blackboard is
up to date.
