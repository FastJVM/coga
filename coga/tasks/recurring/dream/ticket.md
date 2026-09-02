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
period_generation: a3cf4cb5-62f7-4299-9eb4-83aaf33cc0a6
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
Period tickets *normally* carry nothing durable — their output is the
notification post or PR they already produced — so Retro normally direct-deletes
them via `coga delete recurring/<name>` — no PR or marker — while leaving the
recurring template's serviced-period record untouched. Normally, not always: a
wrapper run that hit a reusable gotcha writes it to its own blackboard (see
`## Gotchas`), and that is worth extracting into a knowledge PR before the
delete. Read the period ticket's blackboard and decide on what is actually
there; never direct-delete on the ticket's class alone. Keep it cheap — the
common case really is "nothing durable", so direct-delete as soon as the
blackboard shows none. If a completed period ticket survives into a
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

Generated: 2026-09-02T19:00:13+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python3 -m coga.validate --json --fix`
Task: `recurring/dream`

Result: 27 issue(s): 0 direct fix, 5 PR proposal, 22 human-needed.

### PR Proposal

- `reconcile-recurring-wrapper-tty-admission-guidance`: `large-blackboard` (warn) - blackboard region is 54.0 KiB (warning threshold 32.0 KiB); it is included in launch prompts. Consider summarizing old notes.
  Remediation: Propose a reviewed blackboard condensation that preserves current decisions and blockers before removing detail.
- `v2/autotrigger-ticket-type`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.
- `v2/measure-relay-prompt-scope-and-agent-precision`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (non-placeholder blackboard is 4213 characters); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.
- `v2/split-context-to-doc-user-accessible-and-editable`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.
- `v2/use-worktree-when-starting-a-dev-task`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.

### Human Needed

- `detect-stranded-ticket-writes-across-checkouts`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `parse-agents-rejects-cogalocaltoml`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `retire-never-removes-a-worktree-that-ran-the-tests`: `stuck-in-progress` (warn) - in_progress but idle for 360.1h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `reuse-the-existing-control-worktree-for-recurring`: `stuck-in-progress` (warn) - in_progress but idle for 166.8h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `run-recurring-agent-templates-off-the-control-bran`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `secrets-instructions-correction`: `stuck-in-progress` (warn) - in_progress but idle for 469.1h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `service-account-scoping-single-vault-rule-conflict`: `stuck-in-progress` (warn) - in_progress but idle for 428.3h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `service-recurring-from-a-temp-control-worktree-ins`: `stuck-in-progress` (warn) - in_progress but idle for 379.2h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `stop-syncing-task-state-onto-the-feature-branch`: `unfrozen-workflow` (warn) - workflow 'code/with-self-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `the-ticket-interview-never-asks-what-done-means`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/acceptance-criteria`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
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
- `v2/document-contexts-as-prompt-payload-not-tags-princ`: `stuck-in-progress` (warn) - in_progress but idle for 1029.8h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `v2/fix-windows-cli-import-crash`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/identify-blocking-issues`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/issue-inbox-slack`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/relay-design-repositories`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.

## Dream Run Notes — 2026-W36

Serviced period read from `coga/log.md`: `created recurring/dream for 2026-W36`
(2026-09-02 11:55). Repo root `/home/n/Code/claude/coga`, control branch `main`,
remote `origin` → `https://github.com/FastJVM/coga/`.

### Phase 1 — validate-drift: `reported`

`coga run validate-drift` → 27 issues (0 direct-fix, 5 pr-proposal, 22
human-needed). Full classification in `## Dream Skill: validate-drift` above.
The fix pass repaired nothing (no missing blackboard fences).

### Phase 2/3 scan mechanics

- Knowledge scan directory: `/tmp/dream-ks-Poha8f` — 15 shards (`ks-01`…`ks-15`),
  242 corpus files (155 tickets + 87 knowledge files, 1.74 MB) each owned exactly
  once, every shard inside the 150 KB / 40 file budget.
- Contract audit directory: `/tmp/dream-ca-6o1Ife` — 8 shards (`ca-01`…`ca-08`),
  69-file living contract surface (22 contexts, 23 skills, 8 recurring template
  files, 13 docs, README/CLAUDE.md/AGENTS.md) each owned exactly once.

### Phase 4 — Retro eligibility (computed before delegation)

Scanned every `status: done` task under `coga/tasks/` for a real `## Dev`
`branch:`/`worktree:` value and checked both open PRs (#735, #736) for marker
or deletion overlap. Neither open PR touches any candidate.

**Eligible (7)** — done, directory present, no feature checkout recorded:

- `retire-autoclose-skips-annotated-pr-lines` (done retire task; its
  `## Retro run` note documents a *different* ticket's Retro pass, so it is not
  a marker on itself)
- `recurring/autoclose-merged`
- `recurring/blocker-reminders`
- `recurring/branch-sweep`
- `recurring/digest`
- `recurring/resolve-conflicts`
- `recurring/skill-update`

**Deferred retirement debt (21)** — `status: done` but the blackboard `## Dev`
records a real branch and worktree, so these are retirement debt, not Retro
input. Left on disk untouched so the human-typed `coga retire <slug>` stays
valid: `autoclose-should-name-the-retire-follow-up`,
`bumppy-requires-exactly-two-agents`,
`dream-phases-2-3-cannot-complete-scan-subagents-re`,
`fix-the-autofix-analyst`, `launch-ignores-the-recorded-worktree-stranding-bla`,
`megalaunch-only-shows-one-page`,
`migrate-recurring-templates-to-ticket-py-shims-and`,
`move-cogacontext-to-roodoc-so-its-easier-for-human`, `put-build-back`,
`read-the-recurring-serviced-period-from-the-log-dr`,
`reconcile-recurring-wrapper-tty-admission-guidance`,
`recurring-last-serviced-period-compares-as-a-strin`,
`recurring-recipe-question`, `refuse-recurring-runs-from-a-non-control-branch`,
`remove-coga-build-and-project`, `remove-legacy-config-compatibility-shims`,
`review-slack-channels`, `rewrite-coga-base-prompt-and-agent-mode-block`,
`select-session-conduct-instead-of-appending-a-cont`, `unblock-rewind`,
`validate-drift-classifier-misses-17-emitted-kinds`.

**Not Retro input:** `status: canceled` tasks. `retro/done-ticket` stops and asks
when any passed task is not `status: done`, so the 7 canceled tickets
(`digest-can-clobber-recurring-last-serviced-period`,
`nightly-auto-drain-run-for-ready-tickets`, `parse-agents-rejects-cogalocaltoml`,
`ship-a-shared-recurring-reminder-engine-battery`,
`v2/document-interactive-recurring-sweep-hazard-in-rel`,
`v2/document-parent-orchestrates-child-script-tasks-pa`,
`v2/move-some-alerts-to-coga-important-instead-of-coga`) are out of scope for
this phase.

## Findings

Merged from Phase 2 (`/tmp/dream-ks-Poha8f`, 15/15 shards complete) and Phase 3
(`/tmp/dream-ca-6o1Ife`). 54 raw Phase-2 blocks → 51 distinct findings after
de-duplication: 18 `extract`, 23 `stale`, 10 `gap`.

Two blocks were dropped as non-findings:
- `ks-02` filed "Packaged digest recurring template declares a workflow that is
  not packaged" and then **retracted it in a later block**. The retraction is
  correct: `digest/post.md` is packaged under
  `src/coga/resources/templates/coga/bootstrap/workflows/digest/post.md` (the
  bundled-fallback tree resolved by `coga.paths.workflow_path`), and
  `tests/test_packaging.py` registers that twin explicitly. No action.
- `ks-13` and `ks-11` independently reported the same `coga/scripts/cron.sh`
  defect; merged into one finding below.

### Blocking structural result — Phase 4 cannot consume any `extract` finding

**All 18 `extract` findings name a source ticket that is retirement debt or
canceled.** None is in Phase 4's eligible set (see the eligibility section
above). The Dream body assumes `extract` findings are "already handled by
Phase 4"; this run they cannot be, because every knowledge-bearing done ticket
in the corpus records a real `## Dev` checkout and is therefore deferred to
`coga retire`, not delegated to Retro.

The knowledge itself is not at risk — those tickets stay on disk. The *findings*
are, because this blackboard is deleted at the next firing. Phase 6 therefore
routes the whole `extract` backlog to a tracked draft ticket rather than letting
it die here, and files the routing hole itself as a `gap`.

### `extract` — grouped by the context/skill area they touch

**coga/codebase** (5)
1. `autoclose-should-name-the-retire-follow-up` — peer review's microkernel
   refinement: do not promote a helper to core while its existing duplicate
   consumers stay unmigrated. `append_report` exists as three byte-identical
   private copies (`skill_update.py`, `dream_validate_drift.py`,
   `dream_cleanup_orphan_markers.py`); the rule is "consolidate the real
   consumers, don't add a fifth".
2. `bumppy-requires-exactly-two-agents` — validate-before-write for lifecycle
   mutations: build a prospective `Ticket`, validate via
   `assert_task_valid(..., ticket_override=...)`, then commit. Three writers
   converted (`mark.py:193`, `:334`, `bump.py:178`); `mark_active`,
   `mark_in_progress`, `mark_blocked`, `mark_paused` still write-then-validate.
3. `select-session-conduct-instead-of-appending-a-cont` — `coga launch
   --prompt-report` reads as a report but runs under the mutating `launch`
   command and is swept, so it publishes working-tree edits. The codebase
   context's "read-only commands are safe" list invites exactly the wrong
   inference.
4. `megalaunch-only-shows-one-page` — silent twin of the documented editable-
   install failure: inside a feature worktree a bare `python -m pytest` imports
   the *primary* checkout's source. `PYTHONPATH=$PWD/src` is the default
   invocation, not a repair.
5. `rewrite-coga-base-prompt-and-agent-mode-block` — authoring rules for
   `src/coga/resources/prompt*.md`: an abridged restatement inside a prompt
   resource is often the only version an agent sees, and a guard split across
   two resources can be deleted wholesale in one commit with tests still green.

**coga/recurring** (3)
6. `recurring-last-serviced-period-compares-as-a-strin` — how to suppress a new
   template's first firing (record a real ledger line for the period; a
   placeholder token is rejected, not silently accepted).
7. `migrate-recurring-templates-to-ticket-py-shims-and` — why a `ticket.py`-
   backed step keeps `assignee: agent`: the assignee vocabulary is deliberately
   role-only, and a script role would reintroduce the rejected `mode:` field.
8. `fix-the-autofix-analyst` — two of the ticket's three specified defects are
   still live in `src/coga/recurring_autofix.py`: `detail = (result.stderr or
   result.stdout or "")` hides the real cause, and the analyst subprocess passes
   no `stdin`, so piped bytes graft onto the prompt.

**dev/code** (2)
9. `launch-ignores-the-recorded-worktree-stranding-bla` — `coga launch` never
   chooses the agent's working directory: `run_with_done_marker` takes no `cwd`
   and there is no `os.chdir` in `src/coga/`. `worktree:` authorizes the
   single-checkout assist; it does not place anything.
10. `launch-ignores-the-recorded-worktree-stranding-bla` — the `requires: branch`
    gate is cheaply satisfiable by hand-copying the lines, and `open-pr`'s
    "commit or stash them" remediation steers an agent into committing the
    stranded duplicate onto the feature branch, manufacturing a `ticket.md`
    merge conflict.

**coga/architecture** (1)
11. `put-build-back` — a `--agent` override now propagates across *directly
    consecutive* frozen agent steps and stops at a role change or human assist
    (`launch.py`, `consecutive_agent_override`). Architecture still describes it
    as "for that launch only".

**coga/extension-model** (1)
12. `remove-legacy-config-compatibility-shims` — alias-validation failure modes:
    a built-in collision is a hard `ConfigError` at dispatch, except `coga init`
    and the cross-repo `coga recurring --all` parent, which discard the invalid
    map; an `uninstall` alias is warned-and-ignored.

**coga/period-task + coga/codebase gotchas** (1)
13. `ship-a-shared-recurring-reminder-engine-battery` (canceled) — cross-run
    state writers must use the fence-aware `coga.blackboard` / `coga.taskfile`
    API. A hand-rolled whole-file regex mistakes body prose for state; a bare
    append destroys a fence on a file that ends at one, breaking every
    blackboard reader at once.

**coga/sync** (1)
14. `move-cogacontext-to-roodoc-so-its-easier-for-human` — an experiment that
    mutates tracked repo state and is exercised *through Coga commands*
    publishes itself: the catch-all `sync_coga_state` sweep committed and pushed
    the relocation on the first `coga validate`. There is no window in which
    such an experiment is only local; run it with `[git] enabled = false` or in
    a throwaway clone.

**coga/project-stage** (1)
15. `put-build-back` — two more delete-then-restore cycles for the
    bias-toward-deletion precedent list (`coga build` #691→#701; the `remove-run-py`
    epic's #670 reversed by the `ticket.py` seam), plus the partial-revert
    procedure both produced.

**bootstrap/retro** (1)
16. `dream-phases-2-3-cannot-complete-scan-subagents-re` — Phase 4 is the one
    Dream phase with no on-disk progress contract. The scan protocol
    generalized the hedge for Phases 2–3 only; Retro, the *destructive* phase,
    still delivers all-or-nothing through a final message.

**code/with-review workflow** (1)
17. `reconcile-recurring-wrapper-tty-admission-guidance` — the workflow never
    says the peer review must have *returned and been read* before `coga bump`.
    PR #723 was opened, advanced and merged while its review was still running;
    the review then returned six actionable regressions in merged code,
    including two P1 lifecycle races.

**code/self-qa** (1)
18. `megalaunch-only-shows-one-page` — no rule covers surfaces automated tests
    structurally cannot reach. The `--pick` TTY loop was uncovered by a green
    suite and the bug was found by eye; a recorded manual sweep with exact
    conditions should be a gate, and an undrivable terminal a blocker.

### `stale` — a context, skill, or template contradicts repo reality

**coga/contexts/coga/architecture/SKILL.md** (2)
19. The step-gate section still presents `pr` as the whole gate registry and
    closes with "both `pr` policies". `step_gate.py` registers two tokens —
    `branch` (`_has_branch_linkage`) alongside `pr` — and `dev/code` plus
    `code/implement` already cite `requires: branch`.
20. The prompt-composition section concludes "the agent reads the ticket as
    written". Composition carries exactly `## Description`, `## Context`, and
    the blackboard; `_extract_section` stops at the next `##`, so every other
    body section is silently dropped.

**coga/skills/code/design/SKILL.md** (1)
21. `code/design` writes `## Acceptance Criteria`, `## Proposed Shape`, and
    `## Out of Scope` as sibling sections that never reach the implement agent's
    prompt — the same root cause as #20, from the authoring side.

**coga/contexts/coga/extension-model/SKILL.md** (2)
22. It inlines ~450 words of lease/publication/snapshot detail that
    `coga/launch-internals` owns, and never references that context — not in the
    body and not in its does-NOT-cover list.
23. Its kernel derivation and command-classification table exclude commands core
    actually keeps (`digest`, `megalaunch`, and the dozen-plus verbs
    `cli.py` registers), contradicting `coga/codebase` and CLAUDE.md.

**coga/contexts/coga/sync/SKILL.md** (2)
24. The live-producer pointers name `commands/block.py`, `commands/bump.py`, and
    `commands/launch.py`; those modules now only call `preflight_post`. The
    actual deliveries are `src/coga/bump.py:250` and `src/coga/mark.py:986`.
25. It omits the `slack_response.py` boundary: the `live`/`revoked`/`unreachable`
    classification behind the `slack-revoked` and `slack-misconfigured` issue
    kinds, and — more importantly — `redact_slack_webhook_credentials`, which
    exists because a webhook URL is a bearer token and coga writes failure
    strings to the git-tracked `coga/log.md`.

**coga/contexts/coga/period-task/SKILL.md** (2)
26. It enumerates four period-key shapes; `src/coga/recurring.py` emits five
    (`YYYYMMDDTHHMM` for schedules outside the four buckets). This is the context
    auto-attached to every firing.
27. Step 3 offers "`coga mark done` for a workflow-less ticket" — a state the
    code forbids: every period task is created with a workflow, and activation
    refuses a workflow-less ticket.

**coga/contexts/coga/codebase/SKILL.md** (1)
28. Its skill inventory presents two categories (repo-authored namespaced;
    `coga skill install` flat). `anthropic/skill-creator/` is a third shape —
    hand-vendored under a namespace, absent from `managed-skills.toml`, carrying
    its own attribution and licence.

**coga/contexts/coga/secrets/SKILL.md** (1)
29. It frames vault/SA scoping as the boundary bounding automation reach, and
    never states what architecture does: `build_launch_env()` never scrubs
    `OP_SERVICE_ACCOUNT_TOKEN`, so a launched agent reaches every vault the SA
    can, regardless of the ticket's `secrets:` declaration.

**coga/contexts/coga/roadmap/SKILL.md** (1)
30. `## Current sequence` item 4 presents the workflow-to-playbook rename as live
    ordering guidance; its only ticket is a `draft` in the v2 parking area whose
    body is entirely pre-rename (`relay/architecture`, `src/relay/*`). The same
    context's own deferred-work section says v2 items are pulled forward only by
    explicit decision. `Last updated: 2026-07-15`.

**coga/contexts/coga/current-direction/SKILL.md** (1)
31. Its `Last updated` stamp is 32 days behind its own content, and nothing
    bumps it.

**Packaged `coga/cli` context** (2) — `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`
32. It offers `coga/scripts/cron.sh` as the optional scheduler entry point. No
    `cron.sh` and no `coga/scripts/` exists in the checkout or the wheel.
    (Reported independently by `ks-13` and `ks-11`; merged.) This also strands
    the parked draft `v2/wire-recurring-sweep-into-system-cron`, whose whole
    deliverable is scheduling that file.
33. It has no section for `coga usage` or `coga digest`, both registered in
    `cli.py`. This is the only shipped `coga/*` context with **no live twin**, so
    the "update both copies" habit never fires for it.

**Recurring templates** (1)
34. `coga/recurring/skill-update/ticket.md` and its packaged twin open by
    asserting imported skills carry `.coga-source.json` provenance and instruct
    the run to walk skills with recorded provenance. Zero such files exist, so
    the weekly run's stated scan set is empty. Owned by the open draft
    `vendored-skills-carry-no-coga-source-json-so-coga`.

**Skills — frontmatter and vendored packs** (2)
35. `coga/skills/anthropic/skill-creator/SKILL.md` carries upstream's bare
    `name: skill-creator`, which is exactly what its own `ATTRIBUTION.md`
    forbids. `browser/dochub` and `browser/playwright` likewise carry bare
    quoted names instead of their `browser/` prefix.
36. `coga/skills/google-agents-cli-workflow/SKILL.md` tells the agent to install
    or refresh the pack with `uvx google-agents-cli setup` / `agents-cli setup
    --skip-auth`. In this repo those packs are managed by `coga skill install`
    / `coga skill update` and refreshed by `recurring/skill-update`; following
    the vendored instruction writes an unmanaged second copy outside the PR
    loop. **Overlaps open PR #736**, which edits this file — defer, do not open
    a conflicting PR.

**Shipped `code/*` workflows** (1)
37. All three packaged `code/*` workflows carry long agent-directed inline `##`
    step bodies for steps that declare `skills:`. `_step_layers` returns early
    when a step has skills, so no launched agent has ever read them. The
    `## implement` body is byte-identical across two files and differs by one
    word in the third — three unenforced copies of a rule whose purpose is to
    make the stranded-write failure loud.

**Stale *tickets* (not contract surface — routed differently)** (4)
38. `v2/dream-recurring-persist-done-stop-inline-delete` — a detailed spec whose
    four load-bearing assumptions all inverted (flat `recurring-<name>-<period>`
    slugs, no dedupe, `tasks/recurring/` grouping "out of scope"). Reads as
    authoritative to whoever unpauses it.
39. `v2/automerge-ticket` — its `## Evaluator review` explicitly *verified* that
    `code/` is not packaged and needs no dual-copy sync. The layout is now
    exactly inverted. The verification is what makes it dangerous.
40. `v2/dev-loop-git-hygiene-lift-sync-with-main-into-code` — both halves of its
    `## Acceptance` already shipped (`code/implement` step 8; `branch-sweep`).
41. `verify-the-pr-review-comment-loop-once-the-review` — blocked on a
    precondition ("once the review queue drains") that is now satisfied.

### `gap` — a repeated pattern with no context, skill, or workflow to carry it

42. **`coga.local.toml` in isolated checkouts** — `dev/code` "Checkout boundary"
    and `code/implement` both instruct the agent to create a linked worktree or
    `/tmp` clone, and neither mentions that `coga/coga.local.toml` is gitignored,
    so the next mutating Coga command exits 2. Confirmed by two tickets that hit
    it as a dead end, plus three places that already work around it ad hoc.
    Target: `coga/contexts/dev/code/SKILL.md`.
43. **What a fresh linked worktree lacks** — three tickets in the
    "run recurring from somewhere else" family each re-derived the same facts,
    one as a mid-implementation blocker: the three gitignored paths and which
    self-heal, the one-checkout-per-branch rule, and the detached-HEAD publish
    refusal. Target: `coga/contexts/coga/codebase/SKILL.md`.
44. **CI posture** — three tickets each re-derived it and all three are now
    wrong. `.github/workflows/release.yml` exists but is publish-only; there is
    no PR/push test job, so the local suite plus `coga validate` are the whole
    release gate. Target: `coga/contexts/coga/codebase/SKILL.md`.
45. **Live/packaged twin rule for recurring templates** — all seven templates
    have packaged twins, `IDENTICAL_LIVE_PACKAGED_PAIRS` enforces only some, and
    `coga/recurring` never mentions the twin at all. Three tickets circle it.
    Target: `coga/contexts/coga/recurring/SKILL.md`.
46. **`preflight_post`** — `coga/sync`'s "Design rule for new features" lists
    cadence, destination, post-after-write ordering and `sync_task_state`, but
    not the preflight that makes misconfiguration crash *before* the state
    write. Five call sites. The omission is invisible in any repo whose webhook
    resolves. Target: `coga/contexts/coga/sync/SKILL.md`.
47. **Cite symbols, not line numbers** — grepping contexts, skills and workflows
    for "line number" returns nothing, while `bootstrap/ticket` owns `## Context`
    authoring. A cold evaluator tabulated nine stale citations in one ticket and
    called it blocking; the follow-up ticket pinned twenty more anyway.
    Target: `bootstrap/ticket` SKILL.
48. **Dream refiles gaps it already ticketed** — nothing tells a shard to check
    for an existing owner before classifying a `gap`. Four drafts show the cycle,
    including two filed by different runs for the identical gap. Target:
    `bootstrap/dream/scan/knowledge-scan` SKILL.
49. **Phase 1 `human-needed` issues have no durable home** — `coga/log.md` shows
    W33 23, W34 23, W35 29, W36 22: four runs, no trend, no ticket, no marker.
    Two of the stuck tickets have been reported by every run since W34. Needs a
    routing rule (one draft per systematic class, or a hygiene ledger outside the
    period blackboard). Target: Dream body Phase 6 + `validate-drift` skill.
50. **Dream `gap` tickets get parked in `coga/tasks/v2/` and decay** — no context
    states they must not be. Target: `coga/tasks/v2/README.md` + Dream Phase 6.
51. **The human-doc vs agent-context boundary** is re-opened by every new ticket
    and recorded nowhere. Target: `coga/contexts/coga/architecture/SKILL.md`.

### `drift` — Phase 3 contract audit

8/8 shards complete, 13 raw blocks → 6 new distinct findings. `ca-03` (sync,
dev/code, marketing, browser contexts), `ca-06` (recurring templates + copy
divergence) and `ca-07` (README, CLAUDE.md, AGENTS.md, `docs/reference.md` and
the operational docs) each returned an explicit **0 findings** — those surfaces
audit clean.

Dropped as non-findings:
- `ca-01` and `ca-02` both reported that three live contexts point at a
  `coga/cli` context absent from `coga/contexts/`. **`ca-02` then retracted it,
  correctly**: `paths.resolve_context_path` falls back to the packaged
  `bootstrap/contexts/<ref>/SKILL.md`, and the 65 KB `coga/cli` seed is tracked
  there. The same bundled fallback covers the `code/*` workflows that are
  likewise absent from `coga/workflows/`. Neither is drift. (Contrast finding 52
  below, which is a genuinely missing *file*, not an unresolved ref.)
- `ca-05` filed an evidence addendum to its own skill-creator finding; folded in.

Three Phase-3 findings duplicate Phase-2 findings from different evidence and are
merged rather than listed twice: the bare skill `name:` frontmatter (Phase 2 #35,
now with `ca-04`/`ca-05`'s code proof that `paths.resolve_skill_path` builds
`skills_root / ref / "SKILL.md"`, so the advertised name is unciteable, and that
`browser/playwright`'s packaged twin carries the same bare name); and
`current-direction`'s stale `Last updated` stamp (Phase 2 #31).

**New drift:**

52. **`coga/contexts/coga/architecture/SKILL.md` — the reserved frontmatter key
    list matches neither code constant.** This is load-bearing:
    `src/coga/config.py:678` raises "collides with the canonical ticket
    frontmatter key ... See the `coga/architecture` context for the reserved
    set", naming this list as the source of truth. Two defects. `period_generation`
    is in `ticket.CANONICAL_TICKET_KEYS` and `validate.OPTIONAL_TASK_KEYS` but
    missing from both the context list and `config._RESERVED_TICKET_FIELD_NAMES`
    — so `[ticket.fields.period_generation]` is accepted today and would collide
    with the runner-written key on any recurring period task. Conversely `slug`
    is listed as reserved in the context but is absent from
    `_RESERVED_TICKET_FIELD_NAMES`, so `[ticket.fields.slug]` loads without error
    despite `slug` being in `validate.REQUIRED_TASK_KEYS`.
53. **`coga/contexts/coga/architecture/SKILL.md` — the launch env-var contract
    lists seven members and says "two are conditional".** `task_env.TASK_ENV_KEYS`
    has ten: the seven plus `COGA_ASSIST_AGENT`, `COGA_ASSIST_BRANCH`,
    `COGA_ASSIST_PR`. All three are really exported (`commands/launch.py:3004`,
    `launch_script.py:279`) and read back by in-session state commands
    (`pr_assist.py`, `cli.py:229`). `grep -rn COGA_ASSIST coga/contexts/coga/*/SKILL.md`
    is empty — including `coga/launch-internals`, where architecture defers the
    strict-assist invariants. Ten members, five conditional.
54. **`coga/contexts/coga/period-task/SKILL.md` — calls the unadvanced-state-key
    alert "a Slack FYI".** `mark.py:602` posts it with `important=True`, and
    `coga/important` independently names "unadvanced recurring state" as a
    coga-important event. The two contexts disagree; period-task is wrong.
55. **`docs/concepts.md` — the documented prompt-layer order no longer matches
    `compose_prompt`.** The doc places the ticket's inline `## Context` before
    skills (code emits it after) and the blackboard before the task description
    (code emits description first, blackboard last). `compose.py:272` records the
    contiguous-ticket ordering as a deliberate change (#427). The follow-on
    sentence "Only the blackboard (layer 6) carries state forward" cites a layer
    number that no longer corresponds to the blackboard.
56. **`coga/skills/_template/SKILL.md` — names `coga run` as the only home for
    deterministic headless behavior.** The microkernel rule in `coga/codebase`
    and CLAUDE.md now sanctions two edges: a fixed `runner.RECIPES` entry for
    behavior needing a repo-independent argv/stdout/exit contract, and the
    reserved sibling `ticket.py` for a ticket-owned headless phase. The
    `ticket.py` route is how every recurring job in this repo actually runs, and
    the starter template points a new author at only one of the two.
57. **Skill frontmatter `name:` is unqualified in three vendored packs** (merged
    with Phase 2 #35): `anthropic/skill-creator` (`name: skill-creator`, which its
    own `ATTRIBUTION.md` explicitly forbids), `browser/playwright`
    (`name: "playwright"`, and its packaged twin carries the same bare name, so a
    fix must touch both), and `browser/dochub` (`name: "dochub"`). Coga resolves
    skills by path, so each advertises a name no ticket can cite. PR #736 does not
    touch any of these three, so the fix is conflict-free.

### Phase 4 — retro/done-ticket: `direct-fixed` (7 direct deletes, 0 knowledge PRs)

Delegated as one subagent run of `retro/done-ticket` with all seven eligible
slugs, in a dedicated linked worktree at `/tmp/coga-dream-retro-247403`
(branch `dream-w36-retro-1788376680`, based on the fetched `origin/main` tip
`39fdef32`). The caller's gitignored `coga.local.toml` was ordinary-copied in at
mode 0600 and never staged. Evidence snapshot: `/tmp/dream-retro-snap-bSyo7t`
(read-only ordinary copies of the seven resolved artifacts including sibling
`ticket.py` files, `coga/log.md`, the live `contexts/` and `skills/` corpus, and
this task's `## Findings`).

Every one of the seven carried **no new durable knowledge**, so all seven were
direct-deleted with `coga delete <slug> --keep-control-checkout`. No knowledge
PR, no `## Retro` marker, no `## Pruned` bookkeeping. Recovery is `git restore`.

Independently verified after a fresh fetch — not taken from the subagent's report:

- `origin/main` advanced `39fdef32` → `38858dd9` across exactly seven
  `Ticket: <slug> — deleted` commits.
- All seven paths are absent from `origin/main`.
- `git diff --name-only 39fdef32 38858dd9` touches **only** `coga/tasks/` paths —
  nothing else was modified.
- `coga/recurring/` still holds all seven templates, and `coga/log.md` on
  `origin/main` still carries the `created recurring/dream for 2026-W36`
  serviced-period line.
- The Dream task itself (`coga/tasks/recurring/dream/ticket.md`) is untouched.

Deleted: `retire-autoclose-skips-annotated-pr-lines`,
`recurring/autoclose-merged`, `recurring/blocker-reminders`,
`recurring/branch-sweep`, `recurring/digest`, `recurring/resolve-conflicts`,
`recurring/skill-update`.

This is the expected shape for period tickets — their output was the
notification post each already produced — and it is corroborated by Phase 2
finding zero `extract` findings against any of the seven.

## Dream Skill: cleanup-orphan-markers

Generated: 2026-09-02T19:24:04+00:00
Task: `recurring/dream`

Result: no-op. No cleanup-eligible processed done tickets still have task directories.

## Dream Run Summary

Generated 2026-09-02 (period **2026-W36**). Repo `FastJVM/coga`, control branch
`main`.

| # | Phase | Result | Detail |
|---|---|---|---|
| 1 | validate-drift | `reported` | 27 issues: 0 direct-fix, 5 pr-proposal, 22 human-needed. Fix pass repaired nothing. |
| 2 | knowledge scan | `reported` | 15/15 shards complete, 0 incomplete. 242 corpus files, 1.74 MB. 54 raw blocks → 51 distinct findings. |
| 3 | contract audit | `reported` | 8/8 shards complete, 0 incomplete. 69-file contract surface. 13 raw blocks → 6 new distinct findings. |
| 4 | retro/done-ticket | `direct-fixed` | 7 eligible tickets, all no-durable-knowledge → 7 direct deletes on `origin/main`. 0 knowledge PRs. |
| 5 | cleanup-orphan-markers | `no-op` | No processed done ticket still has a task directory. |
| 6 | disposition | `pr-opened` + `proposed` | 10 proposal PRs, 9 tracked draft tickets, 1 deferred for PR overlap. |

**Findings: 57 distinct** — 18 `extract`, 23 `stale`, 10 `gap`, 6 `drift`.
Three raw blocks were dropped as self-retracted or duplicate (see `## Findings`);
catching those is why shards write retractions rather than silently correcting.

### PRs opened — all `pr-required`, none auto-merged

| PR | Subject |
|---|---|
| #737 | period-task: five period-key shapes, no workflow-less finish path, important alert not FYI |
| #738 | sync: correct the notification producer list; record the Slack classification + webhook-redaction boundary |
| #739 | extension-model: delegate launch-internals detail; reconcile the kernel rule with `coga/codebase` |
| #740 | path-qualify three skill frontmatter names; name both deterministic edges in the skill template |
| #741 | codebase: admit the hand-vendored skill shape; secrets: record the `OP_SERVICE_ACCOUNT_TOKEN` trust boundary |
| #742 | roadmap: stop citing a parked pre-rename ticket; fix two stale currency stamps |
| #743 | skill-update template: stop asserting `.coga-source.json` provenance no skill carries |
| #744 | architecture: step-gate registry, composition constraint, reserved frontmatter keys, launch env vars |
| #745 | cut agent instructions from `code/*` workflow step bodies that never compose |
| #746 | document `coga usage` and `coga digest`; drop a nonexistent `cron.sh`; fix the concepts prompt-layer order |

Verified after the fact: every branch is pushed, every enforced live/packaged twin
pair touched by a PR is still byte-identical, and no PR edits a file another PR edits.

### Draft tickets created (`code/with-review`)

- `isolated-checkouts-nothing-says-what-a-fresh-workt`
- `no-context-records-the-ci-posture-publish-only-rel`
- `recurring-context-never-mentions-the-packaged-twin`
- `sync-context-omits-preflight-post-from-the-notific`
- `no-rule-says-ticket-context-must-cite-symbols-not`
- `dream-findings-have-three-routing-holes-that-lose`
- `the-human-doc-vs-agent-context-boundary-is-decided`
- `dream-2026-w36-extract-backlog-18-findings-phase-4`
- `four-parked-tickets-carry-premises-that-have-since`

### `human-needed` — decisions this run could not make

1. **Phase 1's 22 `human-needed` validator issues have no route out of this
   blackboard.** They are: 11 `unfrozen-workflow`, 6 `stuck-in-progress`, 5
   `unknown-assignee: 'nicktoper'`. Four consecutive runs have reported the same
   classes with no downward trend (W33 23, W34 23, W35 29, W36 22), and two of the
   stuck tickets have been idle since before W34. Ticketed as
   `dream-findings-have-three-routing-holes-that-lose`, but the underlying
   lifecycle decisions are the owner's.
2. **21 done tickets are outstanding retirement debt.** Each records a real `## Dev`
   branch and worktree, so Retro must not touch them and `coga retire <slug>` stays
   the human-typed path. They are listed in full in the Phase 4 eligibility section
   above. This is also why Phase 4 had no knowledge to extract.
3. **All 18 `extract` findings are orphaned by that debt.** Phase 6's `extract` route
   assumes Phase 4 handled them; Phase 4 structurally could not. Carried into
   `dream-2026-w36-extract-backlog-18-findings-phase-4` so they survive this
   blackboard, but whether to land them as knowledge PRs or let `coga retire` consume
   them is a human call.
4. **Two code-side gaps found but not fixed** (documentation-only PRs by design):
   `config._RESERVED_TICKET_FIELD_NAMES` omits `period_generation` (so
   `[ticket.fields.period_generation]` is accepted and would collide with the
   runner-written key on any period task) and omits `slug` (so
   `[ticket.fields.slug]` loads despite `slug` being required). Flagged in PR #744.
5. **One finding deferred for overlap.** `coga/skills/google-agents-cli-workflow/SKILL.md`
   tells agents to refresh the pack with `uvx google-agents-cli setup`, bypassing
   `coga skill install`/`update` and the `recurring/skill-update` PR loop. Open PR
   **#736** already edits that file, so per the Dream body no conflicting PR was
   opened — it goes to that PR's review.

### Notes for the operator

- `coga/tasks/triage-the-v2-parking-area-empty-descriptions-prem.md` was being edited
  by a concurrent session throughout this run (an evaluator review written into its
  blackboard). Dream did not touch it, but the `coga create` calls in Phase 6 fired
  the ordinary `sync_coga_state` sweep, which will have published that in-progress
  edit along with the new tickets. That is normal Coga behavior, not data loss — and
  it is the same hazard `extract` finding 14 describes.
- This task's own blackboard now trips the `large-blackboard` warning. Expected: the
  recurring scanner deletes this task before creating the 2026-W37 Dream.
- Scan directories `/tmp/dream-ks-Poha8f` and `/tmp/dream-ca-6o1Ife` were deleted
  after their findings merged. The Phase 4 worktree, its temporary branch, the copied
  `coga.local.toml` and the evidence snapshot were all removed and verified gone. The
  ten PR worktrees were removed; their branches are kept because the PRs need them.
