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

## Run State

- Period: `2026-W30` (from `coga/recurring/dream/ticket.md`).
- Scope: the six ordered phases in this ticket; no extra maintenance phases.
- Started: 2026-07-23.

## Findings

### Knowledge scan — coga/codebase

- Title: Scrub inherited launch metadata in subprocess tests
- Class: `extract`
- Target: `coga/contexts/coga/codebase/SKILL.md`
- Source tickets: `allow-open-pr-when-the-recorded-worktree-is-the-pr`,
  `build-an-order-for-megqlaunch`,
  `fix-automatically-pr-conflict-and-a-command-to-bat`,
  `make-ticket-script-form-works`,
  `validate-that-a-frozen-workflow-name-still-resolve`
- Multiple done tickets independently found that subprocess tests inherited
  live `COGA_TASK_*` / `COGA_SKILL_*` metadata and redirected fixture workers
  into the outer task's blackboard. Add the durable isolation rule: scrub or
  explicitly replace launch metadata before subprocess tests, preferably in
  the autouse environment guard.

### Knowledge scan — coga/extension-model

- Title: Document command tickets as the shipped stateless extension surface
- Class: `extract`
- Target: `coga/contexts/coga/extension-model/SKILL.md`
- Source tickets: `commands-as-tickets-open-pr-pilot`,
  `fix-automatically-pr-conflict-and-a-command-to-bat`
- The completed command-ticket work supersedes the context's claim that
  Coga-authored stateless extensions have no implementation. Document
  local-first bootstrap command tickets, alias-backed verbs, no per-invocation
  lifecycle, script `COGA_ARG_*` delivery, and structured launch arguments for
  agent-backed commands.

### Knowledge scan — coga/architecture

- Title: Correct the workflow-freeze guarantee
- Class: `stale`
- Target: `coga/contexts/coga/architecture/SKILL.md`
- The statement that in-flight tickets are unaffected by later workflow edits
  contradicts `remove-autonomy-triage` and
  `validate-that-a-frozen-workflow-name-still-resolve`: frozen frontmatter
  retains step metadata, but skill-less step prose is reloaded from the current
  workflow definition. State that deleting, renaming, or emptying that
  definition can degrade composition and now causes validation errors for live
  tickets.

### Contract audit — packaged architecture migration inventory

- Title: Packaged architecture migration inventory lags live contract
- Class: `drift`
- Target: `src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md:220`
- The packaged twin lists only `[assignees]`; `src/coga/config.py:231-240` and
  `:462-489` also implement tailored errors for local `[secrets]` and removed
  agent keys, matching the live architecture context.

### Contract audit — read-only Git fallback

- Title: Read-only Git fallback missing from live code contracts
- Class: `drift`
- Targets: `coga/contexts/dev/code/SKILL.md:20`,
  `coga/skills/code/implement/SKILL.md:27`
- Their packaged twins specify the independent `/tmp`
  `git clone --no-hardlinks` fallback, and the Dream contract relies on it.
  The live/packaged divergence is undocumented despite the twin-sync rule in
  `AGENTS.md`.

### Contract audit — bump status gate

- Title: `bump` falsely described as status-agnostic
- Class: `drift`
- Target: `coga/contexts/coga/architecture/SKILL.md:290`
- `src/coga/commands/bump.py:84-85` refuses every status except
  `in_progress`, agreeing with the same context's contradictory statement at
  lines 293-294.

### Contract audit — launch-time parameters

- Title: Launch-time parameters still documented as forbidden
- Class: `drift`
- Targets: `coga/contexts/coga/extension-model/SKILL.md:128-140`,
  `docs/cli-extension-audit.md:227-231`
- `src/coga/commands/launch.py:96-100,322-333` implements trailing script
  arguments as `COGA_ARG_1..N` / `COGA_ARGC`, and `src/coga/aliases.py:52-55`
  shows `open-pr` consuming that channel.
- Disposition overlap: merged Retro PR #637 owns the extension-model target;
  merged proposal PR #640 owns only the non-overlapping CLI-audit target. A
  cross-PR review note was posted on #637.

### Contract audit — default aliases

- Title: Default-alias inventory and implementation references are obsolete
- Class: `drift`
- Targets: `coga/contexts/coga/extension-model/SKILL.md:183`,
  `docs/cli-extension-audit.md:21-28,121-124,168-170,238-240`
- `src/coga/aliases.py:14-39,56-64` now owns built-ins and ships seven aliases,
  adding `pick` and `open-pr`; the audit still points to removed `cli.py`
  symbols and counts five. This overlaps the bootstrap-inventory finding.
- Disposition overlap: merged Retro PR #637 owns the extension-model target;
  merged proposal PR #640 owns the CLI-audit and bootstrap-inventory targets.

### Contract audit — bootstrap ticket inventory

- Title: Bootstrap-ticket inventory omits live command targets
- Class: `drift`
- Target: `docs/cli-extension-audit.md:102-105`
- Packaged artifacts include `bootstrap/browser-automation/ticket.md` and
  `bootstrap/open-pr/ticket.md` in addition to the four listed. Browser
  automation remains an unaliased stateless launch target, contradicting the
  audit's claim that no unaliased passthrough remains.

### Contract audit — create notification

- Title: `coga create` falsely documented as posting Slack
- Class: `drift`
- Targets: `docs/cli-extension-audit.md:71`,
  `coga/contexts/coga/current-direction/SKILL.md:215-219`
- `src/coga/commands/create.py:1-5,59-62` explicitly defines raw creation as
  Slack-silent.

### Contract audit — watchers

- Title: Watchers simultaneously documented as removed and implemented
- Class: `drift`
- Targets: `coga/contexts/coga/project-stage/SKILL.md:50`,
  `coga/contexts/coga/current-direction/SKILL.md:230-232`
- `src/coga/ticket.py:168-172` parses watchers and
  `src/coga/notification/slack.py:30-49` renders mapped watcher mentions;
  current-direction itself records their reintroduction at lines 200-205.

### Contract audit — compatibility posture

- Title: “No backwards-compat hacks” contradicts shipped compatibility paths
- Class: `drift`
- Target: `coga/contexts/coga/project-stage/SKILL.md:26-35`
- `src/coga/config.py:793-795,875-890` retains deprecated `[slack]` and
  bare-env fallbacks, while `src/coga/aliases.py:67-91` soft-migrates the
  legacy `create` alias.

### Contract audit — important recipient

- Title: Important-recipient configuration still described as pending
- Class: `drift`
- Targets: `coga/contexts/coga/important/SKILL.md:32-35,69-71`
- `src/coga/config.py:919-942` resolves
  `[notification.slack].important_recipient`, and
  `coga/contexts/coga/sync/SKILL.md:238-258` documents the shipped behavior.

### Contract audit — period cleanup timing

- Title: Period-task cleanup timing is wrong
- Class: `drift`
- Target: `coga/contexts/coga/period-task/SKILL.md:9-14`
- Completed period tasks remain `status: done` until Dream deletes them or a
  later recurring scan replaces them, as specified by
  `coga/contexts/coga/recurring/SKILL.md:299-310` and implemented around
  `src/coga/recurring_runner.py:1773-1779`.

### Contract audit — canceled digest outcomes

- Title: Canceled outcomes omitted from digest contracts
- Class: `drift`
- Targets: `coga/contexts/coga/sync/SKILL.md:204-210`,
  `coga/skills/coga/digest/flush/SKILL.md:12-26`,
  `coga/recurring/digest/ticket.md:21-42`
- `src/coga/notification/__init__.py:80,203-218,277-296` accepts, spools, and
  renders `canceled` records alongside done/error outcomes.

### Contract audit — workflow snapshot timing

- Title: Workflow snapshots still described as creation-only
- Class: `drift`
- Targets: `docs/vision.md:127`, `docs/market-thesis.md:313`
- `src/coga/mark.py:360-378` freezes a bare workflow reference at activation,
  and `docs/concepts.md:116-120` states the current creation-or-activation
  rule.

### Contract audit — lock claim

- Title: Vision still claims local locks
- Class: `drift`
- Target: `docs/vision.md:236`
- The live architecture explicitly rejects filesystem mutexes, while
  `docs/concepts.md:148-151` identifies task status as the concurrency signal.

### Contract audit — shipped trust layer

- Title: Market thesis says the already-shipped trust layer is missing
- Class: `drift`
- Targets: `docs/market-thesis.md:305,358`
- The same document records supervised liveness, recurring execution, checked
  notifications, and atomic writes as built at lines 279-298; implementations
  include `src/coga/repl_supervisor.py`, `src/coga/atomicio.py`, and
  `src/coga/notification/slack.py`.

## Phase Results

### Phase 1 — validate-drift

- Child task: `dream-validate-drift-w30` (`dream/validate-drift`), completed.
- Command: `/home/n/.local/share/uv/tools/coga/bin/python -m coga.validate --json --fix`.
- Result: `human-needed`; 27 issues, 0 direct fixes, 0 PR proposals.
- Breakdown: 6 `stuck-in-progress`, 8 `unfrozen-workflow`, 5
  `unknown-assignee`, 3 `missing-step`, and 5
  `unsynthesized-draft-blackboard`.
- No files were repaired. Lifecycle, ownership, routing, and draft synthesis
  decisions remain explicitly human-owned; full remediation lines are in the
  child task blackboard.

### Phase 2 — knowledge scan

- Result: `reported`; 3 findings from a complete corpus read (2 `extract`, 1
  `stale`, 0 `gap`).
- Corpus: 155 canonical task tickets plus 6 task-tree support/template
  artifacts, 21 local contexts, 22 local skills, 9 local workflows, and their
  effective packaged counterparts.
- Candidate gaps already had durable tickets, so no new gap survived
  deduplication.

### Phase 3 — contract audit

- Result: `reported`; 15 `drift` findings from 64 living contract files.
- Corpus: 20 contexts, 21 skills, 7 recurring templates, 13 `docs/*.md`
  documents, and 3 top-level documentation/instruction files. Frozen task
  artifacts were excluded.
- Findings include 3 undocumented divergent twin files (grouped into 2
  findings) and 13 code/artifact-versus-prose contradictions.

### Phase 4 — Retro

- Result: `pr-opened` + `direct-fixed`; all 56 eligible done tasks received
  exactly one disposition.
- [PR #636 — New context: isolate subprocess tests from launch
  metadata](https://github.com/FastJVM/coga/pull/636) updates
  `coga/contexts/coga/codebase/SKILL.md` and deletes
  `allow-open-pr-when-the-recorded-worktree-is-the-pr`.
- [PR #637 — New context: stateless commands are local-first command
  tickets](https://github.com/FastJVM/coga/pull/637) updates
  `coga/contexts/coga/extension-model/SKILL.md` and deletes
  `commands-as-tickets-open-pr-pilot`.
- Both PRs opened clean and mergeable, stayed within the Retro batch limits,
  and had pushed heads. Their source `## Retro` markers are preserved in
  branch history before the source paths disappear at the PR tips. Both PR
  Slack FYIs posted. A human merged both during this run.
- The other 54 no-new-knowledge tasks were direct-deleted on `origin/main`
  as 54 exact `Ticket: <slug> — deleted` commits (58 artifact files):
  `add-a-status-canceled-for-ticket`,
  `append-queue-execution-guidance-to-recurring-agent`,
  `bug-if-not-on-megalaunch-don-t-block-ask`,
  `build-an-order-for-megqlaunch`,
  `check-we-can-extend-coga-recurring`,
  `clean-up-workflows-and-make-sure-they-re-in-bootst`,
  `coga-important/add-coga-slack-important`,
  `coga-important/add-toml-property-for-notification-recipient`,
  `coga-important/context`, `coga-important/support-second-webhook`,
  `distill-git-conflict-errors-and-stop-compounding-d`,
  `dream-cleanup-orphan-markers-w29`, `dream-validate-drift-w30`,
  `fail-loud-on-prose-sub-directory-prefixes-in-coga`,
  `fail-validation-for-unsynthesized-draft-blackboard`,
  `fix-automatically-pr-conflict-and-a-command-to-bat`,
  `handle-better-delete-branches-autcommit`,
  `improve-prompt-for-relay-ticket`,
  `install/actionable-hint-when-recurring-template-references`,
  `install/add-migration-errors-for-removed-config-keys`,
  `install/cut-release-to-realign-pypi-with-main`,
  `install/decide-whether-gh-stays-required-at-init`,
  `install/gh-auth-hint-on-managed-skill-rate-limit`,
  `install/harden-packaging-and-install-before-launch`,
  `install/improve-reinit-already-exists-message`,
  `install/init-next-steps-should-mention-agent-cli-requireme`,
  `install/retest-ssh-https-and-init-reclone-on-fresh-machine`,
  `install/vendor-cli-from-installed-package-not-git-clone`,
  `install/warn-loud-when-init-commit-is-skipped`,
  `log-md-coga-chat-too-so-we-have-a-full-view-of-the`,
  `make-open-pr-metadata-tolerate-annotated-branch-an`,
  `make-ticket-script-form-works`,
  `marketing/rewrite-readme-around-the-wedge`,
  `metrics-human-minutes-script`,
  `move-browser-automation-entry-point-out-of-seeded`,
  `move-open-pr-gate-from-launch-into-bump-make-open`,
  `move-open-pr-recipe-into-the-code-open-pr-skill-ke`,
  `move-per-session-usage-records-from-ticket-blackbo`,
  `on-resize-update-stauts-and-pick`,
  `recurring-bugs/coga-usage-cannot-locate-claude-transcript-or-sess`,
  `recurring-bugs/recurring-all-diverges-two-checkouts-of-one-remote`,
  `recurring-bugs/recurring-all-sweeps-throwaway-coga-scratch-clones`,
  `recurring-bugs/recurring-dream-launch-mis-points-coga-task-env-at`,
  `recurring-bugs/recurring-scan-should-skip-and-report-an-unloadabl`,
  `recurring-bugs/retro-and-delete-branch-switch-the-primary-checkou`,
  `recurring/autoclose-merged`, `recurring/branch-sweep`,
  `recurring/digest`, `recurring/skill-update`,
  `redact-slack-webhook-credentials-from-request-fail`,
  `remove-autonomy-triage`,
  `validate-that-a-frozen-workflow-name-still-resolve`,
  `validate-tickets-at-create-time`, and
  `why-browser-autoamtion-as-a-ticket`.
- Remote verification at Retro handoff: `origin/main` was
  `b86ad68eb8d1a7e172363d34d78f10f7e409a8b5`, exactly 54 delete commits
  beyond the fetched base, and all 54 direct-delete paths were absent. The two
  source paths were subsequently removed when PRs #636 and #637 merged.
- Cleanup verified: copied `coga.local.toml`, linked checkout, temporary
  branch, and evidence snapshot were removed after durability checks.

### Phase 5 — cleanup-orphan-markers

- Child task: `dream-cleanup-orphan-markers-w30`
  (`dream/cleanup-orphan-markers`), completed.
- Result: `no-op`; no cleanup-eligible processed done ticket still has a task
  directory, so no delete-only cleanup PR or human decision was needed.

### Phase 6 — disposition

- Result: `pr-opened`; all 18 findings have a durable disposition. No `gap`
  survived deduplication, so no draft ticket was created.
- Extract — launch-metadata test isolation:
  [PR #636](https://github.com/FastJVM/coga/pull/636), merged.
- Extract — stateless command tickets:
  [PR #637](https://github.com/FastJVM/coga/pull/637), merged.
- Stale workflow-freeze guarantee and contract-audit findings for the packaged
  migration inventory, bump gate, and period cleanup timing:
  [PR #638](https://github.com/FastJVM/coga/pull/638), merged.
- Read-only Git fallback:
  [PR #639](https://github.com/FastJVM/coga/pull/639), explicitly closed
  without merge by the human reviewer. The PR remains the durable review
  record; Dream did not reopen it.
- Launch parameters, default aliases, bootstrap-ticket inventory, and the CLI
  audit's create-notification claim:
  [PR #640](https://github.com/FastJVM/coga/pull/640), merged. The overlapping
  extension-model portions were handled by PR #637; a cross-PR review note was
  posted there.
- Watchers, bounded compatibility paths, and the current-direction
  create-notification claim:
  [PR #641](https://github.com/FastJVM/coga/pull/641), merged.
- Important-recipient and canceled-digest contracts:
  [PR #642](https://github.com/FastJVM/coga/pull/642), open and clean.
- Workflow snapshot timing, status-as-signal coordination, and the shipped
  trust substrate:
  [PR #643](https://github.com/FastJVM/coga/pull/643), open and clean.
- All six proposal branches were pushed. The isolated disposition checkout,
  temporary branch, and PR-body files were removed after verification.
- Final scoped validation: `coga validate --json --task recurring/dream`
  reported 1 task OK and 0 issues; the installed CLI emitted a non-blocking
  source-version-skew warning.

## Dream Run Summary

Generated: `2026-07-23T23:34:25Z`

| Phase | Result | Count / summary |
|---|---|---|
| validate-drift | `reported`; `human-needed` | 27 lifecycle/ownership issues; 0 safe fixes |
| knowledge scan | `reported` | 3 findings: 2 extract, 1 stale |
| contract audit | `reported` | 15 drift findings |
| Retro | `pr-opened`; `direct-fixed` | 2 knowledge PRs; 54 direct deletes |
| cleanup-orphan-markers | `no-op` | 0 candidates |
| disposition | `pr-opened` | 6 proposal PRs; 0 gap tickets |

Finding totals:

- `extract`: 2 — both knowledge PRs merged.
- `stale`: 1 — routed to merged PR #638.
- `drift`: 15 — routed across PRs #638–#643; three merged, two remain open,
  and #639 was closed without merge by its human reviewer.
- `gap`: 0 — no draft ticket created.

PRs opened:
[PR #636](https://github.com/FastJVM/coga/pull/636),
[PR #637](https://github.com/FastJVM/coga/pull/637),
[PR #638](https://github.com/FastJVM/coga/pull/638),
[PR #639](https://github.com/FastJVM/coga/pull/639),
[PR #640](https://github.com/FastJVM/coga/pull/640),
[PR #641](https://github.com/FastJVM/coga/pull/641),
[PR #642](https://github.com/FastJVM/coga/pull/642), and
[PR #643](https://github.com/FastJVM/coga/pull/643).

Human gates: triage the 27 validate-drift reports; review PRs #642 and #643.
PR #639 records the human decision to close the fallback proposal without
merge.
