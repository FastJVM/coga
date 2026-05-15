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
higher-judgment scan, Slack, and final status mark. Include the command or file path
being acted on and the result count when available. If a phase is skipped,
say why. The blackboard remains the durable record; console progress is for
the human watching the run.

### Ordered Skill Pass

Run these known skills in this order:

| Skill | When to run | Result |
| --- | --- | --- |
| `bootstrap/dream/tasks/validate-drift` | Always. | Deterministic repo validation, safe file-presence repairs, and validation drift classification. |
| `retro/done-ticket` | When an existing done ticket lacks the `## Retro` blackboard marker for `skill: retro/done-ticket` / `status: processed` and no open PR is adding that marker or deleting that task directory. | Knowledge extraction; opens a PR only when new durable knowledge exists. If no new durable knowledge exists, records a `no-new-durable-knowledge` marker directly and opens no PR. |
| `bootstrap/dream/tasks/cleanup-orphan-markers` | When an existing done ticket already has the processed Retro marker from a knowledge PR, but its task directory still exists. | PR-required delete-only cleanup through the public `bootstrap/delete-task` skill; reports `human-needed` until that skill is installed. `no-new-durable-knowledge` markers are terminal no-ops, not cleanup candidates. |

That table is the dispatch contract. Do not auto-discover skills, scan a
plugin folder, or invent another maintenance step during the run. If a repo
wants a different maintenance loop, make another task with its own body and
ordered skill list.

For each known skill:

1. Read the skill's `## Known Skill Contract`.
2. For executable Dream-owned skills, scaffold and launch a child
   `mode: script` task whose workflow step references the skill.
   Dream-owned scripts are skills attached to Relay tasks; they are never
   standalone execution units.
3. Keep the skill's reads, writes, and decisions inside its declared scope.
4. Let the skill write its own `## Dream Skill: <name>` section to this
   child task blackboard, then summarize that child result in this Dream run's
   blackboard.
5. Record one result line for the run summary:
   `no-op`, `reported`, `proposed`, `direct-fixed`, `pr-opened`, or
   `human-needed`.

One known skill failing does not permit a replacement. Record the result and
continue only with known skills whose inputs do not depend on the blocked one.

### Skill: validate-drift

Launch a child `mode: script` task whose current workflow step references
`bootstrap/dream/tasks/validate-drift`. The skill runs the same deterministic
surface as `relay validate --json`, classifies every issue, and appends
`## Dream Skill: validate-drift` to the child task's blackboard.

The skill's default safe-repair pass applies only deterministic repairs
currently supported by `relay validate --fix`: create missing `blackboard.md`
from the standard template and create missing `log.md` as an empty append-only
file. It does not rewrite existing files, synthesize `ticket.md`, freeze
workflows, or change lifecycle/assignee state.

### Skill: retro/done-ticket

Read every existing task with `status: done`.

For each done task:

1. Read `relay-os/tasks/<slug>/blackboard.md`.
2. If the blackboard has `## Retro` with `skill: retro/done-ticket` and
   `status: processed`, do not run Retro again. If that Retro block also has
   `result: no-new-durable-knowledge`, the ticket is intentionally left in
   place and is not eligible for cleanup. Otherwise, if no open PR already
   deletes it, it is eligible for the cleanup gate below.
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
   must either open a PR when it found new durable knowledge, or record a
   `no-new-durable-knowledge` marker directly and return a one-line no-op
   result. It must not open a marker-only or delete-only PR; the raw evidence
   stays inside the subagent.
5. If `relay-os/tasks/<slug>/` is already gone, it is not a Retro candidate.
   For audit, use git history for the deleted `blackboard.md`; the deleted
   marker is the record that Retro processed the task before cleanup.

Absence of the marker on an existing done ticket means the task has not been
processed by Retro unless an open PR is already deleting that exact task
directory. Do not infer completion from branch names, stale comments, or old
Dream run notes.

### Skill: cleanup-orphan-markers

Recovery path for done tickets whose blackboard carries a processed Retro
marker from a knowledge PR but whose task directory was not deleted by that
Retro PR. New Retro PRs delete the source task directory in the same PR, so
this pass should usually find nothing. Retro blocks with
`result: no-new-durable-knowledge` are terminal no-ops and must be ignored by
this cleanup gate.

Launch a child `mode: script` task whose current workflow step references
`bootstrap/dream/tasks/cleanup-orphan-markers`. The skill detects cleanup
candidates and gates deletion through `bootstrap/delete-task`. Until that
delete skill exists, it reports `human-needed` and does not delete anything.

For each such ticket, cleanup must open a PR that deletes only
`relay-os/tasks/<slug>/`. The deletion goes in the PR (not the working tree
directly) so the human can review or edit it before merge. Cleanup gate:

- the marker is present in `relay-os/tasks/<slug>/blackboard.md`;
- the marker does not have `result: no-new-durable-knowledge`;
- no open PR is currently editing that task directory;
- the exact task slug is known; do not use prefix matching for deletion;
- the PR deletes only `relay-os/tasks/<slug>/`;
- the PR body states that git history is the audit trail.

Result line: `pr-opened` when the PR is opened. If any gate is unclear, write
`human-needed` in the Dream run summary instead of opening the PR. Do not
auto-merge.

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

Child script tasks write their durable result to their own blackboard; the
parent Dream run sends the broader one-line summary. Call:

`relay slack --task <this-dream-task> --message "<summary>"`

Keep the message to one line, for example:
`Dream scan: 3 broken refs, 2 context proposals.`

Run `relay mark done <this-dream-task>` as the last action after the blackboard is
up to date.
