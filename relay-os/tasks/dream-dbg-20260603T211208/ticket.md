---
title: '[debug] Dream'
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/period-task
skills: []
workflow: null
---

## Description

Run the Dream cleanup pass for this Relay repo.

Dream is Relay's generic cleanup pass. It runs in two halves. The **decide**
half reads the whole repo while it is still intact and classifies every
housekeeping repair and knowledge change worth making. The **execute** half
turns those decisions into reviewable PRs, tracked draft tickets, and safe
repairs. Every Dream finding ends in a durable artifact — a PR, a draft
ticket, or a recorded marker — never only in this task's blackboard, which is
retired along with the task.

Dream is not REM. Repo/user-specific recurring maintenance belongs in a
separate REM task under `relay-os/recurring/`, with its own cadence, skill
order, and output conventions.

### Console Progress

Write short progress updates to the console before and after each phase:
validate-drift, knowledge scan, contract audit, Retro pass,
cleanup-orphan-markers, disposition, and the final status mark. Include the
command or file path being
acted on and the result count when available. If a phase is skipped, say why.
The blackboard remains the durable record; console progress is for the human
watching the run.

### Run order

Dream runs six phases in order. Phases 1–3 **decide** — they read the repo and
record what to change. Phases 4–6 **execute** — they make the changes. Deciding
before executing is deliberate: the knowledge scan and contract audit read the
corpus while every done ticket still exists (Phase 4 deletes them all), so
nothing is missed, and their findings steer the Retro pass.

1. **validate-drift** — deterministic repo hygiene (script worker).
2. **knowledge scan** — one full-corpus read; classifies every finding.
3. **contract audit** — checks the contract surface against code reality.
4. **retro/done-ticket** — extracts durable knowledge from every eligible done
   ticket in one pass.
5. **cleanup-orphan-markers** — delete-only orphan cleanup (script worker).
6. **disposition + run summary** — routes every finding to a durable home.

This body is the dispatch contract. Do not auto-discover skills, scan a plugin
folder, or invent another maintenance phase during the run. Adding or removing
a Dream phase is a normal change to this template. A phase failing does not
permit a replacement: record the result and continue only with later phases
whose inputs do not depend on the blocked one. If a repo wants a different
maintenance loop, make another task with its own body and ordered phase list.

The two script workers (Phases 1 and 5) each run as a child `mode: script`
task whose one workflow step references the worker skill — Dream-owned scripts
are skills attached to Relay tasks, never standalone execution units. Before
launching a worker, read its `## Known Skill Contract`, keep its reads and
writes inside its declared scope, let it write its own `## Dream Skill: <name>`
section to the child task blackboard, then summarize that child result here.

### Phase 1 — validate-drift

Launch a child `mode: script` task whose current workflow step references
`bootstrap/dream/tasks/validate-drift`. The skill runs the same deterministic
surface as `relay validate --json`, classifies every issue, and appends
`## Dream Skill: validate-drift` to the child task's blackboard.

The skill's default safe-repair pass applies only deterministic repairs
currently supported by `relay validate --fix`: create missing `blackboard.md`
from the standard template and create missing `log.md` as an empty append-only
file. It does not rewrite existing files, synthesize `ticket.md`, freeze
workflows, or change lifecycle/assignee state.

### Phase 2 — knowledge scan

Delegate this phase to a subagent. It is the single full-corpus read of the
run: the subagent reads every ticket body and blackboard, and every context,
skill, and workflow file, and compares them. Running it now — in the decide
half, before Phase 4 deletes any done ticket — means no evidence is lost.

The subagent returns only a classified findings list; raw ticket and blackboard
contents stay inside the subagent. Classify each finding as exactly one of:

- `extract` — a done ticket holds durable knowledge that belongs in a context
  or skill. Record the ticket slug and the context/skill area it touches.
- `stale` — an existing context or skill contradicts current repo reality.
  Name the file and state the contradiction.
- `gap` — a repeated pattern (recurring task knowledge, repeated process
  struggle, or an ad-hoc workflow sequence) with no context, skill, or
  workflow to carry it.

Write the findings to this task's blackboard under `## Findings`: short title,
class, target file or ticket, one paragraph describing the change, and draft
content when a new file is proposed. Group the `extract` findings by the
context/skill area they touch — Phase 4 uses that grouping to batch coherent
PRs.

### Phase 3 — contract audit

Delegate this phase to a subagent. Where the knowledge scan asks what the repo
knows that no context captures, the contract audit asks the opposite: what the
contexts, skills, recurring templates, and shipped docs *claim* that the repo
no longer backs up. It is a consistency pass over Relay's explanation of
itself, and it is the decide-half complement to Phase 1: validate-drift checks
deterministic repo hygiene, the contract audit checks whether the prose still
matches the code.

The subagent reads the living contract surface — every
`relay-os/contexts/**/SKILL.md` and `relay-os/skills/**/SKILL.md`, the
`relay-os/recurring/<name>/ticket.md` templates (recurring tasks are
ticket-format directories), `README.md`, `docs/*.md`, and the agent
instruction files `CLAUDE.md` and `AGENTS.md` — and checks each concrete claim
against three sources of truth:

- **code reality** — a flag, default, command, status value, or path that
  `src/relay/` no longer implements as described.
- **referenced artifacts** — a file, skill, context, or workflow a contract
  names that does not exist on disk.
- **copy divergence** — a shipped template under `relay-os/` whose packaged
  counterpart under `src/relay/resources/templates/relay-os/` has drifted,
  where the difference is not documented as intentional.

Frozen task artifacts under `relay-os/tasks/` are historical records, not
contracts — a stale reference inside a retired ticket is not a finding. Audit
only the living contract surface.

The subagent returns only a classified findings list. Classify each finding as:

- `drift` — a contract claim contradicts code reality, names a missing
  artifact, or a live/packaged copy pair has diverged. Name the file and line,
  state the contradiction, and name the source of truth.

Write these findings to this task's blackboard under `## Findings`, alongside
the Phase 2 findings and in the same shape: short title, class, target file,
one paragraph. The audit never repairs anything itself — Phase 6 routes each
`drift` finding to a proposal PR.

### Phase 4 — retro/done-ticket

Extract durable knowledge from done tickets, then delete every one of them.
This pass processes **every eligible done ticket in a single run** — there is
no per-run ticket cap and nothing is deferred to a later run. One corpus read
with one running delta across all tickets is both cheaper than repeated capped
runs and better at de-duplicating repeated facts.

A done ticket is eligible when:

- its directory `relay-os/tasks/<slug>/` still exists; and
- no open PR is adding its `## Retro` marker or deleting
  `relay-os/tasks/<slug>/`.

A ticket whose directory is already gone is not a candidate; git history holds
its record. A processed `## Retro` marker on a still-present directory does not
settle the ticket — its deletion PR has not merged, so it stays eligible. Do
not infer completion from branch names, stale comments, or old Dream notes —
only the on-disk directory and open-PR state count.

Run `retro/done-ticket <slug> [<slug> ...]` in one subagent, passing every
eligible slug. The skill loads the context/skill corpus once, reads each
ticket, carries one running delta across the whole run, and partitions the
tickets into coherent PR batches — each PR within its hard limits (≤5 source
tickets, ≤3 knowledge files, ≤1 new context/skill file, one theme). Every
processed done ticket is deleted: a ticket that contributed durable knowledge
is deleted in its theme's knowledge PR; a ticket carrying nothing durable gets
a `no-new-durable-knowledge` marker and is deleted too — folded into a
knowledge PR's `## Pruned` section, or, when the run opens no knowledge PR at
all, in one delete-only prune PR. Retro never leaves a processed done ticket on
disk and never opens a marker-only PR.

Summarize each PR — knowledge PRs and any prune PR — in this run's blackboard.

### Phase 5 — cleanup-orphan-markers

Recovery path for done tickets whose blackboard carries a processed Retro
marker from a knowledge PR but whose task directory was not deleted by that
PR. Phase 4 PRs delete the source directory in the same PR, so this pass should
usually find nothing. A `result: no-new-durable-knowledge` ticket is Phase 4's
to delete — Phase 4 re-picks it each run until its prune PR merges — so this
cleanup gate ignores those markers.

Launch a child `mode: script` task whose current workflow step references
`bootstrap/dream/tasks/cleanup-orphan-markers`. The skill detects cleanup
candidates and gates deletion through `bootstrap/delete-task`. Until that
delete skill exists, it reports `human-needed` and deletes nothing.

For each candidate, cleanup must open a PR that deletes only
`relay-os/tasks/<slug>/`. The deletion goes in the PR, not the working tree, so
a human can review it before merge. Cleanup gate:

- the marker is present in `relay-os/tasks/<slug>/blackboard.md`;
- the marker does not have `result: no-new-durable-knowledge`;
- no open PR is currently editing that task directory;
- the exact task slug is known; do not use prefix matching for deletion;
- the PR deletes only `relay-os/tasks/<slug>/`;
- the PR body states that git history is the audit trail.

Result line: `pr-opened` when the PR is opened. If any gate is unclear, write
`human-needed` instead of opening the PR. Do not auto-merge.

### Phase 6 — disposition + run summary

Every Phase 2 and Phase 3 finding gets a durable home. The `## Findings`
blackboard section is an index of what Dream saw, not where decisions go to
rest — this task is retired and its blackboard with it.

Route each finding by class:

- `extract` — already handled by Phase 4 (a knowledge PR, or — when the ticket
  carried nothing durable — a `no-new-durable-knowledge` marker and deletion).
- `stale` — open a proposal PR that edits the named context or skill to match
  reality. The PR is `pr-required`: a human reviews and merges it; Dream never
  auto-merges and never edits a context or skill directly on `main`. If a
  stale fix would touch a context or skill that a Phase 4 PR already edits, do
  not open a conflicting PR — note the overlap on the finding and leave it for
  that PR's review.
- `drift` — open a proposal PR that fixes the named contract: correct the doc
  to match code, repoint or remove a dead reference, or resync a diverged
  packaged/live copy pair. Like `stale`, the PR is `pr-required` and Dream
  never auto-merges. If the fix overlaps a context or skill a Phase 4
  knowledge PR already edits, note the overlap and defer to that PR's review.
- `gap` — scaffold a tracked draft ticket with
  `relay create "<title>" --workflow code/with-review`. A gap needs human
  design judgment about whether and how to add the context, skill, or
  workflow; a draft ticket is where that judgment happens, and unlike a
  blackboard note it survives this task's retirement.

Then append one top-level `## Dream Run Summary` section to this task's
blackboard: the generation time, a phase result table using the vocabulary
`no-op`, `reported`, `proposed`, `direct-fixed`, `pr-opened`, `human-needed`,
the finding counts with one-line summaries, links to every PR opened and draft
ticket created, and any `human-needed` decisions or review gates. Keep it short
enough for a human to scan.

### Slack

Child script tasks write their durable result to their own blackboard; the
parent Dream run sends the broader one-line summary. Call:

`relay slack --task <this-dream-task> --message "<summary>"`

Keep the message to one line, for example:
`Dream: validate-drift clean, 2 knowledge PRs, 1 stale-fix PR, 1 gap ticket.`

Run `relay mark done <this-dream-task>` once the blackboard is up to date and
the Slack summary is posted. Then, as the very last action, run
`relay delete <this-dream-task>`: the run's durable artifacts — every PR,
draft ticket, and the Slack summary — carry the findings, so this task and its
blackboard are disposable. Deleting it here is what "retired along with the
task" means above: Dream cleans up after itself in the same run, instead of
leaving a done task for the next run's Phase 4 retro pass to prune.

## Context

