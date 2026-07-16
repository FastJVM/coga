---
slug: recurring/dream
title: Dream
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/period-task
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
script: null
step: 1 (execute)
---

## Description

Run the Dream cleanup pass for this Coga repo.

Dream is Coga's generic cleanup pass. It runs in two halves. The **decide**
half reads the whole repo while it is still intact and classifies every
housekeeping repair and knowledge change worth making. The **execute** half
turns those decisions into reviewable PRs, tracked draft tickets, and safe
repairs. Every Dream finding ends in a durable artifact — a PR, a draft
ticket, or a recorded marker — never only in this task's blackboard, which a
later Dream run retires along with the task.

Dream is not REM. Repo/user-specific recurring maintenance belongs in a
separate REM task under `coga/recurring/`, with its own cadence, skill
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

The two script workers (Phases 1 and 5) each run as a child script
task whose one workflow step references the worker skill — Dream-owned scripts
are skills attached to Coga tasks, never standalone execution units. Before
launching a worker, read its `## Known Skill Contract`, keep its reads and
writes inside its declared scope, let it write its own `## Dream Skill: <name>`
section to the child task blackboard, then summarize that child result here.

### Phase 1 — validate-drift

Launch a child script task whose current workflow step references
`bootstrap/dream/tasks/validate-drift`. The skill runs the same deterministic
surface as `coga validate --json`, classifies every issue, and appends
`## Dream Skill: validate-drift` to the child task's blackboard.

The skill's default safe-repair pass applies only deterministic repairs
currently supported by `coga validate --fix`: append a missing blackboard fence
+ rendered region to a `ticket.md` that lacks one. The single-file format keeps
state in `ticket.md`'s blackboard region — there is no sibling `blackboard.md`
or `log.md`, and append-only history goes to the repo-global `coga/log.md`. It
does not rewrite existing files, synthesize `ticket.md`, freeze workflows, or
change lifecycle/assignee state.

### Phase 2 — knowledge scan

Delegate this phase to a subagent using the
`bootstrap/dream/scan/knowledge-scan` skill. This decide-half scan happens
before Phase 4 so done-ticket evidence is still available.

Write the returned findings to this task's blackboard under `## Findings`;
Phase 4 reads that section when batching knowledge PRs.

### Phase 3 — contract audit

Delegate this phase to a subagent using the
`bootstrap/dream/scan/contract-audit` skill. This decide-half audit complements
Phase 1's deterministic repo-hygiene check.

Write the returned findings to this task's blackboard under `## Findings`,
alongside the Phase 2 findings; Phase 6 reads that section when routing
proposal PRs.

### Phase 4 — retro/done-ticket

Extract durable knowledge from done tickets, then delete every one of them.
This pass processes **every eligible done ticket in a single run** — there is
no per-run ticket cap and nothing is deferred to a later run. One corpus read
with one running delta across all tickets is both cheaper than repeated capped
runs and better at de-duplicating repeated facts.

A done ticket is eligible when:

- its resolved task directory under `coga/tasks/` still exists; and
- no open PR is adding its `## Retro` marker or deleting that resolved task
  directory.

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
`coga delete <slug>` (a working-tree `git rm` plus a direct
`Ticket: <slug> — deleted` commit), with no PR and no marker. Recovery is via
`git restore`. Retro never leaves a processed done ticket on disk and never
opens a marker-only PR.

A done `recurring/<name>` ticket from this sweep is eligible like any other.
Period tickets carry nothing durable (their output is the notification post or
PR they already produced), so Retro direct-deletes them via `coga delete
recurring/<name>` — no PR or marker — while leaving the recurring template's
`last_serviced_period` untouched. If a completed period ticket survives into a
later firing, the recurring scanner deletes it before creating that period's
fresh task. The previous Dream run is removed by that scanner fallback before
this Dream task is created, so Dream never sees or deletes its own predecessor.

Summarize each knowledge PR — and the directly-deleted no-knowledge tickets —
in this run's blackboard.

### Phase 5 — cleanup-orphan-markers

Recovery path for done tickets whose blackboard carries a processed Retro
marker from a knowledge PR but whose task directory was not deleted by that
PR. Phase 4 knowledge PRs delete the source directory in the same PR, so this
pass should usually find nothing. A no-durable-knowledge ticket is direct-deleted
by Phase 4 in the run and never carries a `## Retro` marker, so it can never be a
candidate here; the gate still excludes any `result: no-new-durable-knowledge`
marker left behind by an older run.

Launch a child script task whose current workflow step references
`bootstrap/dream/tasks/cleanup-orphan-markers`. The skill detects cleanup
candidates and gates deletion through `bootstrap/delete-task`. That delete
skill ships, but until its cleanup PR-dispatch wiring is finished the worker
reports `human-needed` and deletes nothing.

For each candidate, cleanup must open a PR that deletes only the resolved task
directory under `coga/tasks/`. The deletion goes in the PR, not the working
tree, so a human can review it before merge. Cleanup gate:

- the marker is present in the task directory's `ticket.md` blackboard region;
- the marker does not have `result: no-new-durable-knowledge`;
- no open PR is currently editing that task directory;
- the exact task slug is known; do not use prefix matching for deletion;
- the PR deletes only that resolved task directory;
- the PR body states that git history is the audit trail.

Result line: `pr-opened` when the PR is opened. If any gate is unclear, write
`human-needed` instead of opening the PR. Do not auto-merge.

### Phase 6 — disposition + run summary

Every Phase 2 and Phase 3 finding gets a durable home. The `## Findings`
blackboard section is an index of what Dream saw, not where decisions go to
rest — this task is retired and its blackboard with it.

Route each finding by class:

- `extract` — already handled by Phase 4 (a knowledge PR, or — when the ticket
  carried nothing durable — a direct `coga delete`).
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
- `gap` — create a tracked draft ticket with
  `coga create "<title>" --workflow code/with-review`. A gap needs human
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

`coga slack --task <this-dream-task> --message "<summary>"`

Keep the message to one line, for example:
`Dream: validate-drift clean, 2 knowledge PRs, 1 stale-fix PR, 1 gap ticket.`

Run `coga mark done <this-dream-task>` once the blackboard is up to date and
the Slack summary is posted. That is the last action — **do not delete this
task.** The run's durable artifacts — every PR, draft ticket, and the Slack
summary — carry the findings, so this `done` task and its blackboard are
disposable, but Dream does not delete itself mid-run. It sits on disk as a
done `recurring/dream` ticket; at the next firing, the recurring scanner deletes
that prior-period artifact and creates a fresh Dream task from this template.
Git history preserves the completed run.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Phase Results

### 1. validate-drift

- Child task: `dream-validate-drift-w29` (`status: done`).
- Command: `/home/n/.local/share/uv/tools/coga/bin/python -m coga.validate --json --fix`.
- Result: `reported` — 31 remaining issues, all `human-needed`; 0 direct fixes and 0 PR proposals. No files were repaired.
- The validator surfaced 8 stale `in_progress` tickets, 6 unfrozen draft workflows, 6 unsynthesized draft blackboards, 5 orphan `mode` fields, 4 unknown legacy assignees, and 3 missing workflow steps (some tickets appear in multiple groups). The complete issue list is in the child blackboard.

### 2. knowledge scan

- Result: `reported` — 5 findings from 169 tickets, 19 contexts, and 127 skill/workflow files: 2 `extract`, 3 `stale`, 0 `gap`.

## Findings

### Document the no-PR product-code boundary

- Class: `extract`
- Target: `stop-direct-body-tickets-from-stranding-committed` → `coga/skills/direct/body/SKILL.md`
- `direct/body` has no PR/push step and must not land committed product changes. The done ticket established that `coga mark done` refuses when product paths exist outside Coga state, points work toward a `code/*` workflow, permits `--force` only as an explicit exception, and has a worktree-local guard limitation. The current skill omits this boundary.

### Preserve the installed-versus-source skew diagnostic

- Class: `extract`
- Target: `warn-on-launch-when-the-installed-coga-predates-th` → `coga/contexts/coga/codebase/SKILL.md`
- Launch and validation now perform a warn-only version-skew check comparing the installed package mtime with the latest committed `src/coga` change, while skipping true editable source even from another checkout. The check may emit harmless clock-skew warnings and misses uncommitted edits; the codebase context does not preserve that interpretation.

### Remove the obsolete REPL completion protocol

- Class: `stale`
- Target: `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`
- The CLI context tells manual/API sessions to continue after `coga bump` and to emit a literal `<<<COGA_SESSION_DONE_…>>>` line. Current prompt and architecture contracts say manual/API sessions stop after bump, while supervised launches terminate through the session-scoped `$COGA_DONE_SENTINEL` side-channel written by lifecycle commands; PTY output is not the completion channel.

### Refresh the launch roadmap

- Class: `stale`
- Target: `coga/contexts/coga/roadmap/SKILL.md`
- The roadmap describes a mid-June board: already-finished autonomy-triage, single-file-task, blocker, and megalaunch work remains framed as future launch gates; several named tickets no longer exist; and removed budget-guard direction remains. Its sequencing conflicts with current task state and `coga/current-direction`.

### Correct the CLI validation guarantee

- Class: `stale`
- Target: `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`
- The validation section claims every Coga-owned task mutation, including raw creation, immediately runs task-scoped validation. `coga create` does not perform that check. Draft ticket `validate-tickets-at-create-time` already records the code-versus-context decision as a durable follow-up.

### Anonymous telemetry still appears in architecture

- Class: `drift`
- Target: `coga/contexts/coga/architecture/SKILL.md:399` and packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md:377`
- The contracts claim an install identity and hosted telemetry sink, but Coga rejected telemetry and implements no telemetry config or sender. Sources of truth: `src/coga/config.py` and `coga/principles`.

### Packaged architecture documents removed secret-catalog semantics

- Class: `drift`
- Target: `src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md:117`
- The packaged copy says absent/null injects all configured secrets and lists name `[secrets]` keys. Code accepts only inline `NAME: env:...|op://...` mappings and absent/null/empty injects nothing. Source of truth: `parse_inline_secrets` and `select_launch_secrets` in `src/coga/config.py`.

### Architecture live/package copies have unmerged contract changes

- Class: `drift`
- Target: `coga/contexts/coga/architecture/SKILL.md:117` and packaged twin
- The twins diverge across secret semantics, prompt composition, unknown-config enforcement, and the shared spawn path without documented intentional variance. Sources of truth: `src/coga/config.py`, `src/coga/compose.py`, and `spawn_agent_session`.

### Period-task live/package copies diverge

- Class: `drift`
- Target: `coga/contexts/coga/period-task/SKILL.md:3` and packaged twin
- The packaged copy retains older “scaffolder” language and a different task-path explanation. No intentional divergence is documented; `_create_at_slug` in `src/coga/recurring.py` is the source of truth.

### Digest skill describes the retired in-ticket spool

- Class: `drift`
- Target: `coga/skills/coga/digest/flush/SKILL.md:12`
- It says records live in the recurring ticket blackboard and that consumption empties the section. Code reads `recurring/digest/spool.md`, retains an anchor, and advances `consumed_through`; the packaged skill twin matches code.

### Digest template retains an obsolete spool record

- Class: `drift`
- Target: `coga/recurring/digest/ticket.md:48,65`
- The prose correctly names sibling `spool.md`, but the ticket still contains an ignored `## Spool (pending)` record. Sources of truth: `digest_spool_path` and `coga/recurring/digest/spool.md`.

### Sync contract hard-codes origin/main

- Class: `drift`
- Target: `coga/contexts/coga/sync/SKILL.md:294,360`
- The contract says state writes go to `origin/main`; implementation uses `cfg.git_remote` and `cfg.git_control_branch` in `src/coga/git.py`.

### Branch-sweep contracts hard-code remote and control branch

- Class: `drift`
- Target: `coga/skills/coga/branch-sweep/sweep/SKILL.md:14` and `coga/recurring/branch-sweep/ticket.md:27`
- They promise enumeration/deletion on `origin` and exclusion of `main`; `src/coga/branchsweep.py` uses the configured remote and control branch.

### Branch-sweep template declares a nonexistent execution field

- Class: `drift`
- Target: `coga/recurring/branch-sweep/ticket.md:9`
- `autonomy: auto` is ignored by recurring creation, while architecture says no ticket autonomy field exists. Sources of truth: `_create_at_slug` and `coga/architecture`.

### Dev context says Coga does not parse branch/pr fields

- Class: `drift`
- Target: `coga/contexts/dev/code/SKILL.md:68`
- Current autoclose, branch-sweep, and open-PR code parses blackboard `branch:` / `pr:` fields. Sources of truth: `src/coga/autoclose.py`, `src/coga/branchsweep.py`, and packaged `code/open-pr`.

### implement-and-pr claims a workflow it no longer owns

- Class: `drift`
- Target: `coga/skills/code/implement-and-pr/SKILL.md:3,54`
- `code/with-review` uses `code/implement`, peer review, and script-backed `code/open-pr`; message-less bumps are silent. Sources of truth: the live workflow and `coga/sync`.

### Recurring starter names missing and obsolete machinery

- Class: `drift`
- Target: `coga/recurring/_template/ticket.md:9,30`
- `scripts/cron.sh` does not exist, and assignees now name agent types or humans rather than per-user nicknames. Sources of truth: the artifact tree and `Config.agent_type`.

### Migration guide tells users to delete the generated skill view

- Class: `drift`
- Target: `docs/migrating-to-coga.md:81`
- `coga/.agent-skills/` is the current generated local-plus-bundled view wired into Claude and Codex, not a Relay-era leftover. Sources of truth: `_link_skills_for_agents` and `coga/codebase`.

### CLI extension audit lists removed and already-shipped commands

- Class: `drift`
- Target: `docs/cli-extension-audit.md:81,112,171`
- There is no `panic` command, while `skill-update` and `autoclose` are already default aliases. Sources of truth: `_BUILTIN_COMMANDS` and `_DEFAULT_ALIASES` in `src/coga/cli.py`.

### Market thesis presents shipped reliability work as missing

- Class: `drift`
- Target: `docs/market-thesis.md:17,259,280`
- Slack HTTP checks, recurring, supervisor watchdogs, and atomic writes are implemented but remain described as blockers. Sources of truth: Slack notification, recurring, supervisor, and atomic-I/O modules.

### Vision uses retired task/log/mode/panic terminology

- Class: `drift`
- Target: `docs/vision.md:118,135,149,165`
- Tasks no longer each have a log, execution is deduced rather than selected by auto/script mode, `panic` became `block`, and no `Create-suggest` artifact exists. Sources of truth: current log, block, launch, and CLI code.

### Codebase context names a removed update path

- Class: `drift`
- Target: `coga/contexts/coga/codebase/SKILL.md:63`
- It says managed skills install during “init/update,” but `init --update` was removed and only fresh init calls `install_venv`. Sources of truth: `src/coga/cli.py` and `src/coga/commands/init.py`.

### Secret-probe skill points at a missing finished task

- Class: `drift`
- Target: `coga/skills/test/secret-probe/SKILL.md:9`
- The temporary skill still points to `manually-test-auth-paths-gh-git-detection-secret-r`, but that task no longer exists. Source of truth: the current task artifact tree.

### 3. contract audit

- Result: `reported` — 18 `drift` findings across living contracts; 0 files changed by the audit.
