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

1. **validate-drift** — deterministic repo hygiene (registered recipe).
2. **knowledge scan** — one full-corpus read; classifies every finding.
3. **contract audit** — checks the contract surface against code reality.
4. **retro/done-ticket** — extracts durable knowledge from every eligible done
   ticket in one pass.
5. **cleanup-orphan-markers** — delete-only orphan cleanup (registered recipe).
6. **disposition + run summary** — routes every finding to a durable home.

This body is the dispatch contract. Do not auto-discover skills, scan a plugin
folder, or invent another maintenance phase during the run. Adding or removing
a Dream phase is a normal change to this template. A phase failing does not
permit a replacement: record the result and continue only with later phases
whose inputs do not depend on the blocked one. If a repo wants a different
maintenance loop, make another task with its own body and ordered phase list.

The two deterministic phases (1 and 5) run registered recipes directly from
this Dream task. Before each run, read the matching skill's
`## Known Skill Contract`, keep reads and writes inside its declared scope,
then invoke the exact `coga run` command below. The recipe inherits this
task's `COGA_TASK_*` context and writes its `## Dream Skill: <name>` section
directly to this task's blackboard. Do not create child worker tasks.

### Phase 1 — validate-drift

Read `bootstrap/dream/tasks/validate-drift`, then run
`coga run validate-drift`. The recipe runs the same deterministic surface as
`coga validate --json`, classifies every issue, and appends
`## Dream Skill: validate-drift` to this task's blackboard.

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

Before delegation, copy the live Retro inputs into a read-only temporary
evidence snapshot: every eligible resolved task artifact (the bare task
Markdown file or the complete task directory, including sibling attachments),
the repo-global `coga/log.md`, local contexts and skills, and this Dream task's
current `## Findings`. Use ordinary copies, not symlinks back to Dream's
mutable checkout. Pass the snapshot path and Dream's absolute repo root to the
subagent so Phases 2–3 and other uncommitted evidence are not lost when the new
worktree starts from a commit.

Delegate the entire Retro pass to one subagent in a dedicated **isolated git
checkout**, running `retro/done-ticket <slug> [<slug> ...]` there and passing
every eligible slug. Fetch the configured remote control branch first and base
the checkout's unique temporary branch on that fresh tip. Use native
`isolation: worktree` when the agent supports it; otherwise create a temporary
linked checkout with `git worktree add` and tell the subagent its exact cwd. If
the managed sandbox makes the primary `.git` metadata read-only, use an
independent `git clone --no-hardlinks` under `/tmp`, repointed to the configured
real remote, instead. Do not run Retro in Dream's checkout or fall back to an
unisolated subagent. Before any Coga command, ordinary-copy the caller's
gitignored `coga.local.toml` to the same repo-relative path in the isolated
checkout; never symlink, snapshot, stage, or commit it. The skill verifies the
checkout boundary before reading evidence, loads the snapshot/corpus once,
carries one running delta, and partitions coherent PR batches within the hard
limits (≤5 source tickets, ≤3 knowledge files, ≤1 new context/skill file, one
theme).

Every processed done ticket is deleted: a ticket that contributed durable
knowledge is deleted in its theme's knowledge PR, which also records its
`## Retro` marker; a ticket carrying nothing durable is direct-deleted with
`coga delete <slug> --keep-control-checkout` from a linked worktree or ordinary
`coga delete <slug>` from an independent clone. Both land the removal on the
remote control branch without mutating the operator's checkout, with no PR and
no marker. Recovery is via `git restore`. Retro never leaves a processed done
ticket on disk and never opens a marker-only PR.

After the subagent returns, verify every PR branch is pushed, every direct
delete is present on the remote control branch, and the isolated checkout is
clean. Remove the copied `coga.local.toml`; then explicitly remove the linked
worktree and its temporary branch, or delete the exact independent-clone
directory. Delete the evidence snapshot too. Agent-native cleanup is not
guaranteed after a mutating run. If durability or cleanup cannot be verified,
preserve the paths and surface a blocker.

A done `recurring/<name>` ticket from this sweep is eligible like any other.
Period tickets carry nothing durable (their output is the notification post or
PR they already produced), so Retro direct-deletes them via `coga delete
recurring/<name>` — no PR or marker — while leaving the recurring template's
serviced-period record untouched. If a completed period ticket survives into a
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

Read `bootstrap/dream/tasks/cleanup-orphan-markers`, then run
`coga run cleanup-orphan-markers`. The recipe detects cleanup candidates and
gates deletion through `bootstrap/delete-task` (`coga run delete-task`). That
delete surface ships, but until its cleanup PR-dispatch wiring is finished the
recipe reports `human-needed` and deletes nothing.

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

The registered recipes write their durable results to this Dream task's
blackboard; the Dream run sends the broader one-line summary. Call:

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

## Run State

Period serviced: `2026-W34` (per `coga/log.md`: `created recurring/dream for 2026-W34`).

- **Phase 1 validate-drift** — done. 23 issues, all `human-needed` (0 direct-fix,
  0 pr-proposal). Recipe writes only to this blackboard; it printed nothing to
  stdout, so the first invocation looked like a no-op and was run twice. The
  duplicate `## Dream Skill: validate-drift` section was removed. Passed as a
  lead to the Phase 3 contract audit.
- **Phase 2 knowledge scan** — delegated to subagent (read-only).
- **Phase 3 contract audit** — delegated to subagent (read-only).

### Phase 4 preflight (done before delegation)

Eligible done tickets — 11. Gate: resolved dir exists on disk **and** no open PR
adds its `## Retro` marker or deletes its directory. Checked all 7 open PRs;
only #695 and #691 touch `coga/tasks/` and neither touches a done ticket.

1. `decide-the-fate-of-two-premise-dead-v2-drafts-whos`
2. `important-alerts-the-task-owner-drop-important-rec`
3. `megalaunch-does-not-set-coga-expected-task`
4. `process-pr-comments-during-review`
5. `recurring-can-only-be-launched-by-owner`
6. `retire-coga-important-support-second-webhook`
7. `recurring/autoclose-merged`
8. `recurring/blocker-reminders`
9. `recurring/branch-sweep`
10. `recurring/digest`
11. `recurring/skill-update`

All 11 verified present on `origin/main` (so each can be deleted durably —
Retro stops on an uncommitted-only task). Local `HEAD` == `origin/main` ==
`60c98639`.

Isolation: linked worktrees are writable here (probe created and removed
cleanly), so the `git clone --no-hardlinks` fallback is not needed.
Machine-local config to copy into the isolated checkout: `coga/coga.local.toml`
(config lives under the Coga OS root, not the repo root).

Evidence snapshot: 11 task artifacts + `coga/log.md` + `coga/contexts/` +
`coga/skills/` + `coga/.agent-skills/`, ordinary copies, no symlinks.
`## Findings` is appended to it once Phases 2-3 return.

### Phase 2/3 delegation — first attempt failed

Both scan subagents were spawned concurrently at ~14:26 and died silently
without returning findings (output streams froze at 14:27 and 14:31; no agent
reachable at 14:35). Neither produced a findings list. Retrying the delegation
one subagent at a time.

### Phase 2/3 — FAILED (capability unavailable)

Subagent delegation does not deliver results in this session. Three attempts:

- `knowledge-scan` (14:26) — read ~120KB of corpus, froze at 14:27, never returned.
- `contract-audit` (14:26) — read ~53KB incl. `coga/log.md`, froze at 14:31, never returned.
- `knowledge-scan-2` (14:36, retry with a tightened reading budget) — produced no
  transcript at all and returned nothing by 14:42.

Both original agents later emitted `idle_notification` / `idleReason: available`
and, when messaged directly asking for whatever findings they had, replied only
with another idle notification — no content either time.

Consequence: `## Findings` is **empty** for this run. Phases 2 and 3 are
`human-needed`. Per the body's dispatch contract ("a phase failing does not
permit a replacement"), the scans were **not** re-run inline in Dream's own
context — delegation is also what keeps the full-corpus read out of Dream's
context so Phases 4-6 stay affordable.

Phase 6 therefore has no findings to route: no `stale`/`drift` proposal PRs and
no `gap` draft tickets are created this run. That is an absence of input, not a
clean bill of health — the scans never ran.

## Phase 4 — retro/done-ticket (in progress, isolated worktree)

Delegated to one subagent in a linked worktree at
`/home/n/Code/claude/coga/.claude/worktrees/agent-a357abc7c01e0a27c`
(branch `worktree-agent-a357abc7c01e0a27c`, git-common-dir shared with the
primary checkout, so `coga delete --keep-control-checkout` is the correct delete
form). Preflight boundary proof passed; `coga/coga.local.toml` copied in at mode
600, unstaged. Evidence snapshot was made read-only before delegation.

The subagent writes a step-by-step progress log to
`scratchpad/retro-progress.log` — added as a hedge after the Phase 2/3 agents
died silently. That log, not the agent's final message, is what makes this
phase's work recoverable.

Classification (all 11 tickets, one running delta):

- **Knowledge-bearing — 1**: `process-pr-comments-during-review` → PR
  [#698](https://github.com/FastJVM/coga/pull/698) "New context: a frozen
  workflow snapshot never refreshes", branch
  `codex/retro-workflow-freeze-knowledge`. Edits the live + packaged
  `architecture` context, records the `## Retro` marker, and deletes the source
  ticket in the same PR.
- **No durable knowledge — 10** (direct-deleted, no marker, no PR): the five
  `recurring/*` period tickets (facts already covered by
  `coga/{recurring,sync,patterns}` + the `coga/*` sweep skills),
  `megalaunch-does-not-set-coga-expected-task`,
  `recurring-can-only-be-launched-by-owner`,
  `important-alerts-the-task-owner-drop-important-rec`,
  `decide-the-fate-of-two-premise-dead-v2-drafts-whos`, and
  `retire-coga-important-support-second-webhook` — each already covered by an
  existing context or skill block the subagent cited by line.

## Dream Skill: cleanup-orphan-markers

Generated: 2026-08-17T21:53:08+00:00
Task: `recurring/dream`

Result: no-op. No cleanup-eligible processed done tickets still have task directories.
