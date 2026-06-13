---
title: Dream
status: done
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
ticket, or a recorded marker — never only in this task's blackboard, which a
later Dream run retires along with the task.

Dream is not REM. Repo/user-specific recurring maintenance belongs in a
separate REM task under `relay-os/recurring/`, with its own cadence, skill
order, and output conventions.

### Console Progress

Write short progress updates to the console before and after each phase:
validate-drift, knowledge scan, contract audit, skill-update, Retro pass,
cleanup-orphan-markers, disposition, and the final status mark. Include the
command or file path being
acted on and the result count when available. If a phase is skipped, say why.
The blackboard remains the durable record; console progress is for the human
watching the run.

### Run order

Dream runs seven phases in order. Phases 1–3 **decide** — they read the repo and
record what to change. Phases 4–7 **execute** — they make the changes. Deciding
before executing is deliberate: the knowledge scan and contract audit read the
corpus while every done ticket still exists (Phase 5 deletes them all), so
nothing is missed, and their findings steer the Retro pass.

1. **validate-drift** — deterministic repo hygiene (script worker).
2. **knowledge scan** — one full-corpus read; classifies every finding.
3. **contract audit** — checks the contract surface against code reality.
4. **skill-update** — update clean imported skills into one PR (script worker).
5. **retro/done-ticket** — extracts durable knowledge from every eligible done
   ticket in one pass.
6. **cleanup-orphan-markers** — delete-only orphan cleanup (script worker).
7. **disposition + run summary** — routes every finding to a durable home.

This body is the dispatch contract. Do not auto-discover skills, scan a plugin
folder, or invent another maintenance phase during the run. Adding or removing
a Dream phase is a normal change to this template. A phase failing does not
permit a replacement: record the result and continue only with later phases
whose inputs do not depend on the blocked one. If a repo wants a different
maintenance loop, make another task with its own body and ordered phase list.

The three script workers (Phases 1, 4, and 6) each run as a child `mode: script`
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

Delegate this phase to a subagent using the
`bootstrap/dream/scan/knowledge-scan` skill. This decide-half scan happens
before Phase 5 so done-ticket evidence is still available.

Write the returned findings to this task's blackboard under `## Findings`;
Phase 5 reads that section when batching knowledge PRs.

### Phase 3 — contract audit

Delegate this phase to a subagent using the
`bootstrap/dream/scan/contract-audit` skill. This decide-half audit complements
Phase 1's deterministic repo-hygiene check.

Write the returned findings to this task's blackboard under `## Findings`,
alongside the Phase 2 findings; Phase 7 reads that section when routing
proposal PRs.

### Phase 4 — skill-update

Launch a child `mode: script` task whose current workflow step references
`bootstrap/dream/tasks/skill-update`. The skill runs
`relay skill update --all --pr`: every clean imported-skill update lands in one
draft PR on the dedicated `relay/skill-update` branch, and it appends
`## Dream Skill: skill-update` to the child task's blackboard, bucketing each
skill by its update status.

Bundled (package-backed) skills are not touched here — they refresh with the
relay package on `relay init --update`. Only imported skills under
`relay-os/skills/` are updated, and only when their recorded upstream digest
changed. A skill that cannot be updated cleanly — a local adaptation, a
provenance conflict, a fetch failure — is left untouched and reported under the
worker's follow-up bucket. When no imported skill changed, the worker opens no
PR. Treat any follow-up skill as a `human-needed` result and surface it in the
Phase 7 run summary; this skill never decides what a conflicting skill should
become.

### Phase 5 — retro/done-ticket

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
is deleted in its theme's knowledge PR, which also records its `## Retro`
marker; a ticket carrying nothing durable is direct-deleted with
`relay delete <slug>` (a working-tree `git rm` plus a direct
`Ticket: <slug> — deleted` commit), with no PR and no marker. Recovery is via
`git restore`. Retro never leaves a processed done ticket on disk and never
opens a marker-only PR.

A done `recurring-<name>-<period>` ticket is an eligible done ticket like any
other — this is how recurring period tickets get cleaned up. The recurring
command does not delete real done period tasks; a finished period task sits on
disk as `status: done` until a Dream run sweeps it here. Period tickets carry
nothing durable (their output is the Slack post or PR they already produced),
so Retro finds no new knowledge in them and **direct-deletes** them via
`relay delete <slug>` — no PR, no marker — leaving the recurring template's
period-ledger line in `relay-os/recurring/<name>/log.md` untouched so the
period is not re-scaffolded. This includes the **previous Dream run's own**
`recurring-dream-<period>` ticket: Dream does not delete itself mid-run, so the
last finished Dream period ticket is one of the done tickets this pass deletes.

Summarize each knowledge PR — and the directly-deleted no-knowledge tickets —
in this run's blackboard.

### Phase 6 — cleanup-orphan-markers

Recovery path for done tickets whose blackboard carries a processed Retro
marker from a knowledge PR but whose task directory was not deleted by that
PR. Phase 5 knowledge PRs delete the source directory in the same PR, so this
pass should usually find nothing. A no-durable-knowledge ticket is direct-deleted
by Phase 5 in the run and never carries a `## Retro` marker, so it can never be a
candidate here; the gate still excludes any `result: no-new-durable-knowledge`
marker left behind by an older run.

Launch a child `mode: script` task whose current workflow step references
`bootstrap/dream/tasks/cleanup-orphan-markers`. The skill detects cleanup
candidates and gates deletion through `bootstrap/delete-task`. That delete
skill ships, but until its cleanup PR-dispatch wiring is finished the worker
reports `human-needed` and deletes nothing.

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

### Phase 7 — disposition + run summary

Every Phase 2 and Phase 3 finding gets a durable home. The `## Findings`
blackboard section is an index of what Dream saw, not where decisions go to
rest — this task is retired and its blackboard with it.

Route each finding by class:

- `extract` — already handled by Phase 5 (a knowledge PR, or — when the ticket
  carried nothing durable — a direct `relay delete`).
- `stale` — open a proposal PR that edits the named context or skill to match
  reality. The PR is `pr-required`: a human reviews and merges it; Dream never
  auto-merges and never edits a context or skill directly on `main`. If a
  stale fix would touch a context or skill that a Phase 5 PR already edits, do
  not open a conflicting PR — note the overlap on the finding and leave it for
  that PR's review.
- `drift` — open a proposal PR that fixes the named contract: correct the doc
  to match code, repoint or remove a dead reference, or resync a diverged
  packaged/live copy pair. Like `stale`, the PR is `pr-required` and Dream
  never auto-merges. If the fix overlaps a context or skill a Phase 5
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
the Slack summary is posted. That is the last action — **do not delete this
task.** The run's durable artifacts — every PR, draft ticket, and the Slack
summary — carry the findings, so this `done` task and its blackboard are
disposable, but Dream does not delete itself mid-run. It sits on disk as a
done `recurring-dream-<period>` ticket and is cleaned up by the **next** Dream
run's Phase 5 retro pass, exactly like every other done recurring period
ticket. Dream is the single deleter of done recurring tickets; it just never
turns that deleter on itself in the same run.

## Context
