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
acted on and the result count when available. For the sharded scan phases, say
how many shards were launched and how many wrote a completion line. If a phase
is skipped, say why.
The blackboard remains the durable record; console progress is for the human
watching the run.

### Run order

Dream runs six phases in order. Phases 1–3 **decide** — they read the repo and
record what to change. Phases 4–6 **execute** — they make the changes. Deciding
before executing is deliberate: the knowledge scan and contract audit read the
corpus while every done ticket still exists (Phase 4 may delete the eligible
ones), so nothing is missed, and their findings steer the Retro pass.

1. **validate-drift** — deterministic repo hygiene (registered recipe).
2. **knowledge scan** — sharded corpus read; classifies every finding.
3. **contract audit** — sharded check of the contract surface against code
   reality.
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

### Decide-half scan mechanics (Phases 2 and 3)

Both decide-half scans are read-only sweeps over Coga's own corpus, and both run
the same way: **bounded shards writing durable findings to disk**, never one
subagent sweep whose result arrives only in its final message. The corpus is
larger than a subagent can hold, and a scan that stops early after delivering
nothing is indistinguishable from a clean repo. Run each scan like this:

1. **Create the scan directory.** `mktemp -d` one directory per phase and keep
   its absolute path. Both scans and the shard subagents follow
   `bootstrap/dream/scan/scan-protocol`, which defines the directory's
   `manifest.md`, `index.md`, `findings.md`, and `progress.md`. Immediately
   create all four as empty regular files before indexing or launching any
   shard. `findings.md` must exist even when every shard reports zero findings;
   absence is never a clean result.
2. **Index and shard.** Size the phase's corpus portably with
   `find <paths> -type f -name '*.md' -exec wc -c {} \;` — do not use GNU-only
   `find -printf`. Enrich those sizes with the compact routing metadata the
   phase skill names and write the full index to `index.md`. Then build the
   phase skill's ownership + evidence assignments at no more than 150 KB across
   at most 40 distinct files, keeping a task directory's Markdown together and
   never splitting a file. Append one attempt-1 shard row per assignment to
   `manifest.md`.
3. **Run the shards.** Delegate each shard to a subagent using the phase's scan
   skill, passing the scan directory's absolute path, the shard id, and that
   shard's exact paths. Shards append to the shared `findings.md` and
   `progress.md`; they do not report findings back through their final message.
4. **Reconcile before believing the result.** Compare the active leaf shard rows
   in `manifest.md` against the completion lines in `progress.md`. Every leaf
   shard must have written
   `<shard-id> complete — <N> findings`; `0 findings` is an explicit, valid
   result, and a shard with no line at all is a shard that never returned. Do
   not treat a missing line as zero findings.
5. **Retry once, then report honestly.** For any missing or `incomplete`
   assignment, append a manifest `supersede <parent> -> <children>` row plus
   smaller attempt-2 child rows and retry those leaves once. If an attempt-2
   leaf still does not complete, the phase result is `partial`: keep the scan
   directory, and record its path, the unread paths, and a `human-needed` line
   in the run summary.
6. **Merge into the blackboard.** Read `findings.md` and merge it into this
   task's `## Findings`, de-duplicating across shards — two shards may describe
   one underlying issue from different evidence; re-read a named file when you
   are unsure whether two findings are the same. Group the `extract` findings by
   the context/skill area they touch.

Delete the scan directory only after its findings are merged into the
blackboard, and only when the phase completed. Report each scan's result as
`reported` with the shard and merged finding counts, `no-op` when every active
leaf completed and the de-duplicated findings across all attempts total zero,
or `partial` when any active leaf did not complete. Superseding a shard changes
the coverage check; it never discards findings that shard already appended.

### Phase 2 — knowledge scan

Shard this phase to subagents using the `bootstrap/dream/scan/knowledge-scan`
skill, following the scan mechanics above. This decide-half scan happens before
Phase 4 so done-ticket evidence is still available.

Merge the shards' findings into this task's blackboard under `## Findings`;
Phase 4 reads that section when batching knowledge PRs.

### Phase 3 — contract audit

Shard this phase to subagents using the `bootstrap/dream/scan/contract-audit`
skill, following the scan mechanics above. This decide-half audit complements
Phase 1's deterministic repo-hygiene check.

Merge the shards' findings into this task's blackboard under `## Findings`,
alongside the Phase 2 findings; Phase 6 reads that section when routing
proposal PRs.

### Phase 4 — retro/done-ticket

Extract durable knowledge from done tickets, then delete every eligible one.
This pass processes **every eligible done ticket in a single run** — there is
no per-run ticket cap and nothing is deferred to a later run. One corpus read
with one running delta across all tickets is both cheaper than repeated capped
runs and better at de-duplicating repeated facts.

A done ticket is eligible when:

- its resolved task directory under `coga/tasks/` still exists; and
- its blackboard `## Dev` section has no real `branch:` or `worktree:` value
  (absent, empty, and placeholder values such as `(not yet created)` do not
  block Retro); and
- no open PR is adding its `## Retro` marker or deleting that resolved task
  directory.

A checkout-bearing done ticket is retirement debt, not Retro input. Do not
delegate it to `retro/done-ticket` and do not invoke `coga retire` from Dream:
leave the ticket and its `## Dev` evidence on disk so the exact human-typed
`coga retire <slug>` command remains valid. List it as deferred retirement debt
in the run summary. After retirement consumes that evidence and removes the
source ticket, the ordinary existence gate makes it disappear from Dream's
candidate set.

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

A done `recurring/<name>` ticket from this sweep is eligible like any other
when it records no feature checkout.
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
`no-op`, `reported`, `partial`, `proposed`, `direct-fixed`, `pr-opened`,
`human-needed`, the finding counts with one-line summaries, links to every PR opened and draft
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

## Dream Skill: validate-drift

Generated: 2026-08-25T04:59:02+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python -m coga.validate --json --fix`
Task: `recurring/dream`

Result: 29 issue(s): 0 direct fix, 4 PR proposal, 25 human-needed.

### PR Proposal

- `v2/autotrigger-ticket-type`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.
- `v2/measure-relay-prompt-scope-and-agent-precision`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (non-placeholder blackboard is 4213 characters); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.
- `v2/split-context-to-doc-user-accessible-and-editable`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.
- `v2/use-worktree-when-starting-a-dev-task`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.

### Human Needed

- `autoclose-skips-annotated-pr-lines`: `stuck-in-progress` (warn) - in_progress but idle for 75.3h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `detect-stranded-ticket-writes-across-checkouts`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `megalaunch-only-shows-one-page`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `migrate-recurring-templates-to-ticket-py-shims-and`: `stuck-in-progress` (warn) - in_progress but idle for 75.6h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `move-cogacontext-to-roodoc-so-its-easier-for-human`: `stuck-in-progress` (warn) - in_progress but idle for 77.3h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `reconcile-recurring-wrapper-tty-admission-guidance`: `stuck-in-progress` (warn) - in_progress but idle for 130.1h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `retire-never-removes-a-worktree-that-ran-the-tests`: `stuck-in-progress` (warn) - in_progress but idle for 154.1h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `secrets-instructions-correction`: `stuck-in-progress` (warn) - in_progress but idle for 263.0h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `service-account-scoping-single-vault-rule-conflict`: `stuck-in-progress` (warn) - in_progress but idle for 222.2h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `service-recurring-from-a-temp-control-worktree-ins`: `stuck-in-progress` (warn) - in_progress but idle for 173.2h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `v2/acceptance-criteria`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/autotrigger-ticket-type`: `missing-step` (error) - `workflow:` is set but `step:` is missing
  Remediation: The ticket's current `step:` is not in its frozen workflow. Lifecycle correction is human-only; ask the owner to relaunch, rewind, or hand-edit the step.
- `v2/clean-uncommitted-work`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/cleanup-core-commands/lifecycle-verbs-to-ticket-operations`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/cleanup-core-commands/read-report-commands-as-ticket-workflows`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/cleanup-core-commands/residual-command-surfaces`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/cleanup-core-commands/support-commands-boundary`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/cleanup-core-commands/work-orchestration-commands-to-tickets`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/document-contexts-as-prompt-payload-not-tags-princ`: `stuck-in-progress` (warn) - in_progress but idle for 823.7h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `v2/fix-windows-cli-import-crash`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/identify-blocking-issues`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/issue-inbox-slack`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/relay-design-repositories`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/split-context-to-doc-user-accessible-and-editable`: `missing-step` (error) - `workflow:` is set but `step:` is missing
  Remediation: The ticket's current `step:` is not in its frozen workflow. Lifecycle correction is human-only; ask the owner to relaunch, rewind, or hand-edit the step.
- `v2/use-worktree-when-starting-a-dev-task`: `missing-step` (error) - `workflow:` is set but `step:` is missing
  Remediation: The ticket's current `step:` is not in its frozen workflow. Lifecycle correction is human-only; ask the owner to relaunch, rewind, or hand-edit the step.

## Run Progress

- Phase 1 validate-drift: **reported** — `coga run validate-drift` → 29 issues (0 direct-fix, 4 PR-proposal, 25 human-needed). Section below. (Recipe ran twice due to an operator retry; duplicate section removed from this blackboard.)
- Phase 2 knowledge scan: 15 shards launched over a 215-file / 1447 KB corpus (coga/tasks, coga/contexts, coga/skills, coga/workflows). Scan dir recorded in Findings section when merged.
- Phase 3 contract audit: pending.

## Phase 4 eligibility (computed pre-delegation)

Open PRs at scan time: **#708** (`coga/skill-update`, edits 11 `coga/skills/google-agents-cli-*` files) and
**#709** (`implement-branch-gate`, edits `coga/contexts/dev/code/SKILL.md`, `coga/skills/code/implement/SKILL.md`,
their packaged twins, 3 packaged `code/*` workflows, `src/coga/step_gate.py`, `tests/test_commands.py`).
Neither PR touches any `coga/tasks/` candidate directory, so no candidate is gated.

**Phase 6 overlap constraint** (record now, apply at disposition): any `stale`/`drift` finding targeting
`coga/contexts/dev/code/SKILL.md` or `coga/skills/code/implement/SKILL.md` must NOT get its own PR — PR #709
already edits those files; note the overlap and defer to that PR's review. Same for the
`coga/skills/google-agents-cli-*/SKILL.md` files under PR #708.

### Eligible for Retro (8) — no real `branch:`/`worktree:` in `## Dev`, directory present, no gating PR

Period tickets (carry nothing durable → direct-delete, no PR, no marker):
- `recurring/autoclose-merged`
- `recurring/blocker-reminders`
- `recurring/branch-sweep`
- `recurring/digest`
- `recurring/resolve-conflicts`
- `recurring/skill-update`

Ordinary done tickets (Retro reads for durable knowledge, then deletes):
- `retire-decide-the-fate-of-two-premise-dead-v2-drafts-whos`
- `retire-recurring-can-only-be-launched-by-owner`

### Deferred retirement debt (11) — checkout-bearing done tickets, NOT Retro input

Each records a real `branch:` + `worktree:` in `## Dev`; left on disk so the human-typed `coga retire <slug>`
stays valid. Dream does not invoke `coga retire`.

- `autoclose-should-name-the-retire-follow-up` (autoclose-retire-hint)
- `dream-phases-2-3-cannot-complete-scan-subagents-re` (dream-scan-shards)
- `put-build-back` (restore-coga-build)
- `read-the-recurring-serviced-period-from-the-log-dr` (fix/recurring-log-reverse-pass)
- `recurring-last-serviced-period-compares-as-a-strin` (codex/validate-recurring-periods)
- `recurring-recipe-question` (deduce-ticket-script)
- `refuse-recurring-runs-from-a-non-control-branch` (fix/recurring-control-branch-gate)
- `remove-coga-build-and-project` (remove-build-project)
- `remove-legacy-config-compatibility-shims` (remove-legacy-config-shims)
- `review-slack-channels` (route-important-failures)
- `validate-drift-classifier-misses-17-emitted-kinds` (codex/validate-drift-kinds)

## Findings

Index of what Dream saw. Full finding text for this run is kept at
`/tmp/claude-1000/-home-n-Code-claude-coga/c229fbd2-d626-4ffa-bdbe-98a273bc49a2/scratchpad/phase2-findings.md`
(Phase 6 reads it when authoring proposal PRs). Durable homes are the PRs and draft tickets, not this section.

**Phase 2 — knowledge scan: `reported`.** 15/15 leaf shards complete on first attempt, no retries.
78 raw findings; **73 after de-duplication** (5 cross-shard duplicates merged, noted inline).

### `extract` (10) — done-ticket knowledge for Phase 4, grouped by area

**area: bootstrap/retro/done-ticket**
- `dream-phases-2-3-cannot-complete-scan-subagents-re` — Retro's durable on-disk progress-log hedge is still a per-run instruction, not skill contract. It is the only reason Phase 4 survived the W34 run.
- `retire-decide-the-fate-of-two-premise-dead-v2-drafts-whos` — an orphaned `retire-<slug>` shell whose source Dream already direct-deleted has no documented disposition. Has happened twice; correct answer is close the shell as already satisfied, do not `git restore`.

**area: coga/codebase**
- `dream-phases-2-3-cannot-complete-scan-subagents-re` — a skill added on a feature branch is invisible in that checkout's gitignored `.agent-skills/` view; agents keep re-deriving this.
- `move-cogacontext-to-roodoc-so-its-easier-for-human` — repo-layout experiments must run with git sync off or in a throwaway clone; the "then revert" recipe cannot be followed as written.

**area: coga/architecture**
- `put-build-back` — `coga launch --agent <type>` propagates the override across *directly consecutive* agent steps without rewriting ticket frontmatter.

**area: coga/cli**
- `remove-legacy-config-compatibility-shims` — the alias-collision "fail loud, not silent" rule has one undocumented exemption; loud failure aborted a cross-repo `coga recurring --all` sweep from a legacy checkout.

**area: coga/recurring**
- `recurring-last-serviced-period-compares-as-a-strin` — seeding a serviced record is the supported way to suppress a new template's first firing.
- `retire-recurring-can-only-be-launched-by-owner` — retire stop conditions treat "already retired" as a wrong slug.

**area: recurring-system**
- `recurring/blocker-reminders` — the `## Blocker reminders` watermark is a permanent dedup key, not a cooldown: reminders fire exactly once per blocker. Confirmed in `src/coga/blocker_reminders.py`.
- `recurring/skill-update` — `coga skill update --pr` fails with a stale lease after every merge+delete of the previous period's branch.

> Note: the last two are **period tickets**. Phase 4's body says period tickets carry nothing durable and are direct-deleted — but these two shards found real durable knowledge in their blackboards, and `coga/contexts/coga/recurring` explicitly says a wrapper run that discovers a gotcha is worth extracting. See the `stale` finding on that contradiction below; it is routed to Phase 6, and Phase 4 must extract these two before deleting.

### `stale` (33 after merge) — a context/skill contradicting repo reality

**coga/contexts/coga/secrets/SKILL.md** (3 — one PR)
- omits the `env:VAR` reference form `parse_inline_secrets` supports (`src/coga/config.py:1360`).
- says the SA is "scoped to a single vault" while the same section tells operators to accrue vaults by trust level.
- claims the SA token makes "every `op://` ref" resolve; config values are not `op://`-aware at all.

**coga/contexts/coga/sync/SKILL.md** (3 — one PR)
- overstates which status rules stay armed during a human rewind (vs `_STATUS_PROGRESS`).
- live-notification inventory is no longer exhaustive — three `post()` sites missing.
- the `coga create` / `coga ticket` silent-surface bullet is garbled mid-sentence and does not parse.

**coga/contexts/coga/architecture/SKILL.md** (2)
- the canonical `requires:` gate section still describes `pr` as the only token (vs `STEP_GATES`, `src/coga/step_gate.py`).
- implies ticket `secrets:` bounds worker capability, but `build_launch_env()` inherits the SA token.

**coga/contexts/coga/current-direction/SKILL.md** (2)
- still describes Dream's scan as a single full-corpus read — the design this very run replaced.
- claims only one Slack idea is parked; `v2/issue-inbox-slack.md` is a second live parked draft.

**coga/contexts/coga/recurring/SKILL.md** (1)
- `## Gotchas` still sanctions a `script -qec` pty recipe no agent harness can run.

**coga/contexts/marketing/** (5 — merged from 6; shard-07 and shard-12 both found the deleted-tickets claim)
- `plan` says two shelved tickets are "not deleted" — both are gone *(merged: shard-07 + shard-12)*, and its shelved proof-post machinery lives in tracked repo files the plan never names.
- `plan`'s claim discipline points at a "5x" bet that is not in `docs/vision.md` and never was.
- `plan` scores "Discord joins" while its own phase 0 leaves the community home undecided.
- `positioning` still calls the A/B fork undecided after `plan` pinned fork A.

**Agent instruction files** (2)
- `CLAUDE.md` + `AGENTS.md` both advertise an `architecture` "locking" section that context does not have.
- `CLAUDE.md` still documents the pre-`.[test]` install contract.

**Vendored / skills layout** (7)
- `coga/recurring/skill-update/ticket.md` asserts `.coga-source.json` provenance no installed skill has.
- `coga/contexts/coga/codebase` documents a namespaced `skills/<ns>/<name>/` layout the seven flat `google-agents-cli-*` packs do not follow.
- `anthropic/skill-creator/SKILL.md` declares a flat frontmatter `name` that is not its resolvable ref.
- `anthropic/skill-creator/ATTRIBUTION.md` points at a ticket that no longer exists.
- `google-agents-cli-workflow/SKILL.md` tells the agent to reinstall the pack, bypassing the vendored copies.
- `browser/dochub` defers load-bearing recipes to a memory store this repo does not have.
- `browser/playwright` — `references/cli.md` sets `$PWCLI` to a nonexistent path; `references/workflows.md` names a different artifact dir than its own SKILL.md.

**Code workflow** (3)
- `coga/skills/code/design` tells the agent to write into `ticket.md`, which bare-file tickets do not have.
- `coga/contexts/dev/code` presents retire's worktree removal as the normal outcome when it almost never fires. **[overlaps open PR #709 — defer]**
- `coga/workflows/_template.md` lists three of the four valid `assignee:` role tokens (omits `other-agent`).

**Templates / seeded fixture** (2)
- `coga/contexts/_template` teaches a size rule 15 of 20 real contexts violate.
- `example/coga/coga.toml` seeds a Slack opt-in that halts recurring runs.

**Dream's own contradiction** (1)
- Dream Phase 4 tells Retro period tickets "carry nothing durable"; `coga/contexts/coga/recurring` says read their blackboard first. Present in all three copies of the Dream template.

**v2 parking-area drafts, premise-dead or self-contradicting** (9)
- `browser/dom-backed` defers a runner decision to an "active test track" with no trace in the repo.
- `v2/README.md` known-stale table omits `script:`, which 15 of its own drafts still carry.
- `v2/README.md` rename table maps `relay-os/…` → `coga/…`, but `workflows/code/*` lives only in the package.
- `v2/README.md` calls the area "drafts" though a quarter is paused/canceled/in_progress.
- `v2/audit-rules-md-usage-across-relay-and-decide-wheth` — premise-dead, `rules.md` no longer exists.
- `v2/document-workflow-less-concept-capture-drafts-as-s` — premise-dead, architecture already documents it.
- `v2/skill-update-aborts-on-uncommitted-log-file` — primary fix already landed.
- `v2/autotrigger-ticket-type` — every cross-reference in it is dead.
- `v2/dev-loop-git-hygiene`, `v2/relay-design-repositories`, `v2/add-relay-skill-search-with-candidate-eval`, `v2/split-context-to-doc` — each settled the other way by shipped precedent.

### `gap` (12 after merge) — repeated pattern with nothing to carry it

- **Ticket specs must cite symbols, not line numbers** — three tickets each hand-wrote the caveat. Target live + packaged `code/design/SKILL.md`. *(merged: shard-03 + shard-05)*
- **No vendored-skill provenance** — no skill under `coga/skills/` carries `.coga-source.json`, so `coga skill update --all` walks nothing, though the weekly job claims it does. *(merged: shard-13 + shard-14 + shard-15)*
- **No context carries the rules for writing to a ticket blackboard** — three recurring-area tickets each corrupted a blackboard a different way.
- **`code/implement` never verifies the `## Dev` write reached the control branch** — the exact gap `launch-ignores-the-recorded-worktree-stranding-bla` documents. **[overlaps open PR #709 — defer]**
- **Isolated checkouts lose `coga.local.toml`** and no durable doc says so. **[overlaps open PR #709 — defer]**
- **`code/implement` parks adjacent bugs on a blackboard Retro then deletes** — no step carries them out.
- **No convention for where a ticket's superseded design goes** — three tickets, three different headings.
- **The cold "Evaluator review" of a design spec** is a repeated ad-hoc ritual with no skill.
- **The ticket interview never asks what "done" means** — two tickets asked for it.
- **A design parked at an owner gate decays**, and only the rebase case is written down.
- **No durable doc covers running Coga headless** — three v2 drafts each rebuild the same runbook.
- **No comms-writing skill** — the writing process is smeared through `marketing/plan`.
- **Packaged repos ship recurring templates without the `coga/recurring` context** (35 KB of the system's whole contract).
- **Dream's own `gap` findings are parked as v2 drafts and then decay there** — five in one shard alone; the v2 README records two cancelled premise-dead drafts that "were themselves Dream `gap` findings originally". Also: `coga validate` is permanently red and every error comes from the v2 parking area, so a green validate is not achievable in this repo.
- **18 of 75 v2 drafts have an empty `## Description`** — the README's premise check cannot be run on them.
- **The v2 premise-check table covers only the pre-rename cohort**; parked drafts cite a "Wave 1 / RC release-gate" plan no durable doc carries.

### `drift` (1, from Phase 2)
- `README.md` still promises the launch experiment `marketing/plan` superseded on 2026-08-19.

