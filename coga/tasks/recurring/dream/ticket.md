---
title: Dream
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 5ba8c09e-726e-4b73-a358-bf27617ffef9
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
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
4. **Reconcile before believing the result.** Reconcile only at the barrier,
   once every shard subagent you launched for this attempt has returned; a
   shard that goes idle after writing its completion line has finished, and a
   mid-flight read of `progress.md` cannot tell that apart from a shard that
   has not written yet. Compare the active leaf shard rows in `manifest.md`
   against the **set of distinct shard ids** that wrote
   `<shard-id> complete — <N> findings` to `progress.md`. Count distinct shard
   ids, never completion lines: `progress.md` is append-only and shared, a
   shard can append its line twice, and a duplicate can make the line total
   reach the leaf count while a leaf is genuinely missing. `0 findings` is an
   explicit, valid result, and a shard with no line at all is a shard that
   never returned. Do not treat a missing line as zero findings.
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

Generated: 2026-09-08T23:51:33+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python3 -m coga.validate --json --fix`
Task: `recurring/dream`

Result: 32 issue(s): 0 direct fix, 5 PR proposal, 27 human-needed.

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

- `adjudicate-the-eight-premise-dead-v2-drafts`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r`: `stuck-in-progress` (warn) - in_progress but idle for 125.3h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `correct-the-v2-known-stale-surfaces-table-and-rout`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `detect-stranded-ticket-writes-across-checkouts`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `guard-the-browser-dochub-and-playwright-live-vs-pa`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `interview-the-owner-on-the-17-title-only-v2-stubs`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `marketing/build-the-launch-plan`: `stuck-in-progress` (warn) - in_progress but idle for 99.9h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `marketing/phase-0-audit`: `stuck-in-progress` (warn) - in_progress but idle for 138.9h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `parse-agents-rejects-cogalocaltoml`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `reuse-the-existing-control-worktree-for-recurring`: `stuck-in-progress` (warn) - in_progress but idle for 315.6h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `run-recurring-agent-templates-off-the-control-bran`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `stop-syncing-task-state-onto-the-feature-branch`: `unfrozen-workflow` (warn) - workflow 'code/with-self-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `the-ticket-interview-never-asks-what-done-means`: `stuck-in-progress` (warn) - in_progress but idle for 147.0h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `ticket-specs-should-cite-symbols-not-line-numbers`: `stuck-in-progress` (warn) - in_progress but idle for 147.0h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
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
- `v2/document-contexts-as-prompt-payload-not-tags-princ`: `stuck-in-progress` (warn) - in_progress but idle for 1178.6h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `v2/fix-windows-cli-import-crash`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/identify-blocking-issues`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/issue-inbox-slack`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/relay-design-repositories`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `validate-that-committed-skill-scripts-with-a-sheba`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.


## Findings

Merged from Phase 2 (knowledge scan, 23 shards, 101 raw blocks) and de-duplicated.
Two shards retracted a finding each (ks-02 on `code/*` workflows — they live in the
packaged bootstrap battery; ks-23 on a blanket `relay`→`coga` rename sweep — the
`v2/README.md` known-stale table already governs it and forbids the sweep); both
retracted originals and their retraction blocks are excluded. Phase 3 findings are
merged below this section under `### Contract audit (Phase 3)`.

### extract — durable knowledge in done tickets (Phase 4 input)

Grouped by the context/skill area each touches.

**coga/architecture**

- E1 `no-skill-exists-for-the-cold-evaluator-review-of-a` — **live skills compose into older frozen workflow snapshots.** Workflow *steps* freeze per ticket but step *skills* and inline workflow prose stay live, so editing a shared step skill silently rewrites the prompts of already-frozen tickets. Rule: a shared step skill must say "the next frozen step", never a step name, and must consume any new blackboard section conditionally. Only `code/design/SKILL.md` embodies the fix today, unexplained.
- E2 `put-build-back` — **`--agent` override propagates across consecutive agent steps.** `coga launch <slug> --agent <type>` follows directly consecutive frozen `agent`-role steps without rewriting ticket state; a role change or human assist ends it (`commands/launch.py` `consecutive_agent_override`). Architecture's assist paragraph says "for that launch only", which reads as the opposite. Found the hard way: `coga build --agent codex` routed step two back to an unavailable Claude (P1).
- E3 `launch-activates-before-preflight` — **a slug rename orphans the audit trail.** `coga/log.md` is append-only and tagged by task ref, so a rename leaves all prior history under the old tag and `coga show` reconstructs nothing. Record the prior slug in the ticket body; grep it when reconstructing.
- E4 `bumppy-requires-exactly-two-agents` — **validate-before-write for lifecycle mutations.** `assert_task_valid`'s "leaves the ticket on disk for correction" contract holds only for content-keyed checks; a config-keyed error check (`unresolvable-step-assignee`) leaves a mutated ticket nothing on disk can fix. `mark.py:197,339` use the `ticket_override` prospective-validate idiom; `mark_active` (:780), `mark_in_progress` (:835), `mark_blocked` (:957), `mark_paused` (:1042) still write-then-validate. Already parked as item 2 of the still-`draft` `dream-2026-w36-extract-backlog-18-findings-phase-4`.

**coga/codebase**

- E5 `select-session-conduct-instead-of-appending-a-cont` (+ the same defect filed independently by ks-02) — **`coga launch --prompt-report` is not read-only.** `_should_sweep_coga_state` classifies any `coga launch` argv as state-sweeping and the report handler refreshes the generated skill view, so the diagnostic published three live doc edits to `origin/main` as `d698cd03`. The codebase context names only `status`/`show`/`validate`/`usage` as read-only, while architecture and current-direction actively recommend `--prompt-report`. Call `compose.compose_prompt_report` directly, or run the CLI report only in a disposable checkout.
- E6 `megalaunch-only-shows-one-page` — **pytest from a feature worktree silently tests the primary checkout.** The editable `.pth` names the primary checkout's `src`, so `python -m pytest` in a feature worktree imports unchanged source ("My first run 'failed the fix' that way"). The context documents absolute `PYTHONPATH` only as recovery from a *broken* `.pth`; it should be the default way to run the suite from a feature checkout.
- E7 `launch-ignores-the-recorded-worktree-stranding-bla` — **this repo has no `coga/workflows/code/`, so `code/*` resolves from the packaged bootstrap copy.** Editing `templates/coga/bootstrap/workflows/code/*.md` changes what Coga itself freezes into its own future tickets, not just downstream repos. The twin-sync rule covers byte-identity but not the packaged-only-is-live case.
- E8 `refuse-recurring-runs-from-a-non-control-branch` — **branch identity must use `git branch --show-current`.** `git rev-parse --abbrev-ref HEAD` returns `heads/<name>` when a tag shadows the branch name, misidentifying the control branch; also fail closed when the git probe itself errors. Survives only as a code comment at `branchcleanup.py:872-874`; three call sites still use the shadowable spelling (`branchsweep.py:375`, `open_pr.py:352,651`).
- E9 `megalaunch-activates-picks-before-preflight` — **the prepare/commit seam in `mark.py`.** `prepare_active` is the pure preparation boundary; `mark_active` is the durable wrapper. The exception ladder divides along it (`WorkflowMissing`/`WorkflowError`/`RequiredExtensionMissing`/`BlackboardNeedsSynthesis` prepare-side; `TaskValidationError` post-write). Two constraints: megalaunch re-reads the ticket between activation and launch so a prepared `Ticket` cannot cross that boundary, and the dependency drain activates *before* resolving blockers on purpose. `prepare_active` appears in no context or skill.

**coga/sync**

- E10 `move-cogacontext-to-roodoc-so-its-easier-for-human` — **a repo-mutating verification experiment cannot be "change, run, revert".** Every CLI command fires `sync_coga_state` at its dispatch boundary, so the first invocation after the mutation committed and pushed it (`e93307ac`) and the pull-back relocated the primary checkout too. There is no local-only window. Rule: run such experiments with `[git] enabled = false` in `coga.local.toml` or in a throwaway clone. "throwaway clone" appears nowhere in contexts or skills.

**coga/launch-internals**

- E11 `launch-activates-before-preflight` — **the deferred-activation invariant has two deliberate exceptions.** The `ticket.py` script path activates before agent-only preflights (a deterministic phase genuinely is work starting), and `recurring_runner.py`'s forced run `mark_active`s a period ticket before preflight (`recurring_runner.py:4590`). Stated unqualified today, so both live call sites read as bugs.

**coga/recurring**

- E12 `remove-legacy-config-compatibility-shims` — **the `init` / `recurring --all` config-error escape hatch.** `cli.main` discards the repo's alias map and dispatches with `DEFAULT_ALIASES` only for `coga init` and a cross-repo `coga recurring --all` (`cli.py:338-356`); every other command exits 2 on the same `ConfigError`. The recurring context documents the *target*-selection exemption but never that the parent's own broken config is survivable.

**coga/cli** (packaged-only context)

- E13 `put-build-back` — **`coga build` was removed (PR #691) then deliberately restored (`ef721d2f`, PR #701); only `coga project` stayed removed.** The still-present done removal ticket asserts no references remain, which is false for the `build` half. Nothing records the reversal, so a future cleanup would delete the survivors again. Owner's reason in `coga/log.md`: "we want the build back with the skills; it was useful."

**bootstrap/import**

- E14 `no-comms-writing-skill-the-process-is-smeared-thro` — **skill-import mechanics.** (a) `coga skill install` is not an import path — it shells out to `gh skill install`, writes no `.coga-source.json`, and leaves `coga skill status` at `delegated (github)` with no dirty detection. (b) Pruning is the normal case, not an exception. (c) `locally-adapted (url)` after a prune is expected, not failure. (d) `install-url` auto-commits the unpruned tree as "Sync coga state" before you can prune, so the sequence needs a squash. The ticket's own premise — that `gh skill` refuses only on multi-skill archives — was disproved: it refuses non-interactively regardless.

**bootstrap/ticket**

- E15 `no-comms-writing-skill-the-process-is-smeared-thro` — **do not attach a context you are editing.** When the ticket's job is to edit a context, name its path in the body and leave it off `contexts:` — files being edited are read, not composed (~22.9 KiB/step saved here). The naive instinct points the wrong way because the task is *about* that context.

**code/open-pr**

- E16 `reconcile-recurring-wrapper-tty-admission-guidance` — **a step must not be bumped while the review it ordered is still in flight.** PR #723 was opened, advanced and merged as `5243dfd5` while `codex review --base origin/main` was still running; the review then returned six actionable regressions including two P1 stale-period races, costing a 19-commit follow-up (PR #725) and sixteen review rounds after the code was already on `main`. Nothing states the rule today. Record the recovery shape too: keep the owner review gate open and authorize a separate follow-up PR from current `main` rather than rewinding.

**architecture — Retro adjacent-bug preservation / known failure modes**

- E17 `carry-adjacent-bugs-out-of-a-blackboard-before-ret` + `give-a-ticket-s-superseded-design-one-documented-h` (merged — same bug from two angles) — **an unresolved adjacent bug is parked in four blackboards and half-fixed.** `tests/test_notification_messages.py` builds its fixture with `_make_task(..., force_directory=True)` (:386) but constructs `TaskRef(..., file_form=True)` (:394), so `test_recurring_create_is_silent` raises `IsADirectoryError` at `recurring.py:85`. Four done tickets each call it "worth its own ticket" and no follow-up exists. Critically, `give-a-ticket-s...` *claims* the fixture was repaired in `4012c5e9`; only half reached `main` in `c4482fae` — the `file_form=True` was left. So the corpus contains a claimed fix, which is why each rediscovery looks new. Only `file_form=True` → `file_form=False` remains. Phase 4 deleting any of those four tickets destroys a source.

### stale — a context or skill contradicts current repo reality

- S1 `coga/contexts/coga/launch-internals/SKILL.md` — justifies non-default attachment as "~19 KiB of prompt"; the file is 29,083 bytes (~28.4 KiB). Prefer a qualitative statement so the figure cannot rot again.
- S2 `coga/contexts/coga/codebase/SKILL.md` + `CLAUDE.md` — **`coga digest`'s "unsettled classification" note is stale**: `runner.py` registers `"digest": run_digest_recipe` (PR #650, `2a26d9df`), which is exception 2 by the context's own rule and the `open-pr` precedent. Only `megalaunch` (no `RECIPES` entry) is genuinely open.
- S3 `coga/contexts/coga/extension-model/SKILL.md` — same digest error from the other side. What actually remains open is narrower: `coga digest` is still a Typer command (`cli.py:91`) rather than an `[aliases]` rewrite to `coga run digest`, the treatment `open-pr` and `delete-task` got.
- S4 `coga/contexts/coga/codebase/SKILL.md` (merged with the ks-19 URL-placement finding) — **the skills-tree taxonomy is wrong in three ways**: it omits the repo-authored `marketing/` namespace; it defines the flat shape as "declared in `managed-skills.toml`" when `coga/skills/clarity/` is a fourth kind — `install-url`-placed, carrying `.coga-source.json` with an `include` allowlist and `local_adaptation_notes`, absent from `managed-skills.toml`; and it closes with "resolution reads the directory path in all three cases". Redefine the flat shape by the `.coga-source.json` marker and add the URL-installed placement and its refresh posture.
- S5 `coga/contexts/marketing/positioning/SKILL.md` — tells comms to use "human-minutes per shipped task" **by name**, while `marketing/plan`'s claim discipline forbids any measured time result in posts 1-3 and `launch-history` shelves the ledger apparatus. Both attach to every post ticket and positioning wins on conflict, so a post-1 agent gets an instruction and a gate that stops it. Scope the sentence to the shelved proof-post regime or add human-minutes to the plan's exemption list.
- S6 `coga/contexts/coga/extension-model/SKILL.md` + `coga/contexts/coga/codebase/SKILL.md` + `CLAUDE.md` + `AGENTS.md` (merged ks-04/ks-22) — **all four defer the microkernel's one open question to an "active command-cleanup design" that is entirely parked**: `v2/cleanup-core-commands/` is five drafts plus one paused ticket, in the directory whose README defines its contents as not on the execution path. That README also states an owner direction ("the only command presumed irreducibly core is `create`") contradicting the shipped kernel table. Say plainly it is deferred to a parked design, or pull the one ticket forward. All four copies must change together.
- S7 `coga/contexts/coga/sync/SKILL.md` — lists `bootstrap` among the root-layout sweep pathspecs; `_ROOT_LAYOUT_COGA_PATHS` (`git.py:144`) does not include it, and `coga/codebase` sanctions repo-authored `coga/bootstrap/` content — so a root-layout repo's bootstrap ticket sits dirty forever. Drop it from the list or add it to the code.
- S8 `coga/contexts/coga/sync/SKILL.md` — names the declared-period-state warning as *the* known best-effort exception to fail-loud important delivery; there are now two. `launch_script.py:417-438` passes `fatal=False` under strict assist so a failing `important_webhook` is swallowed to keep the child exit authoritative.
- S9 `coga/contexts/coga/sync/SKILL.md` — the three cadence surfaces are presented as an exhaustive partition but omit `branch-sweep`, `skill-update`, and `resolve-conflicts` (three of seven templates). Their silence is defensible but undocumented, which matters because the context's own design rule tells authors to justify silence.
- S10 `coga/contexts/dev/code/SKILL.md` — teaches only the separate-worktree layout that `code/open-pr` now calls "the legacy layout". The first-class single-checkout layout (`worktree:` names the primary checkout; `open_pr.py` `_checkout_mode`, `_single_checkout_publishable_paths`) is documented in sync and launch-internals but not in the context attached to every code ticket. `code/implement` step 3 still says `git worktree add` unconditionally.
- S11 `coga/contexts/coga/usage/SKILL.md` — names a bare `launch.py`; there is no `src/coga/launch.py`. The launch supervisor is `commands/launch.py`, spelled correctly everywhere else.
- S12 `coga/skills/_template/SKILL.md` (+ enforced packaged twin) — instructs "never a slash-qualified path" for `name:`, while every repo-authored skill uses the Coga ref (`code/implement`, `marketing/write-post`, `bootstrap/dream/scan/*`) and `coga/codebase` names the namespaced form as the convention "established by the authoring template". A new skill copied from the template starts on the exception path. Also worth noting: `anthropic/skill-creator`'s `quick_validate.py` rejects Coga's namespaced frontmatter, which is expected and documented nowhere.
- S13 `coga/tasks/_template/ticket.md` (+ enforced packaged twin) — tells authors "the agent reads the composed prompt at launch time, not this body". `compose.py` lifts `## Description` and `## Context` into the prompt (`ref="ticket.md##Description"`) precisely so "the agent reads the ticket as written". Every new ticket is seeded from this sentence.
- S14 `coga/contexts/coga/recurring/SKILL.md` — states `ticket.py` dispatch as binary and absolute ("no prompt is composed and no agent starts"), but `launch_script.py` returns `chain=True` when a script exits 0 with the step unchanged, and `recurring_runner.py` carries the hybrid notion explicitly. The commonest authoring mistake — exit 0 without closing the step — is the one the completion-contract bullet omits, and it turns a "headless" template into an agent launch an unattended sweep reports as `unfinished`.
- S15 `coga/contexts/coga/recurring/SKILL.md` — the autofix loop's premise ("the blackboard is where a `ticket.py` phase and an agent session both already write what they found") is false for the shipped templates: the 2026-09-02 run-log shows `branch-sweep`, `autoclose-merged`, `digest`, and `blocker-reminders` wrote only the seeded placeholder. Only `skill-update` wrote a report, and it was the sole template the analyst faulted.
- S16 `coga/contexts/coga/recurring/SKILL.md` — the "exit non-zero for visibility" idiom taught by the `skill-update` template collides with the sweep's stop-on-failure rule. On 2026-09-08 one routine `clarity` digest conflict made `skill-update` exit 1 and the four templates behind it (`autoclose-merged`, `digest`, `blocker-reminders`, `dream`) never ran and were never named. The code fix is tracked; the knowledge defect is not — the stop-on-failure bullet should say later admitted templates are abandoned *and go unreported*.
- S17 `coga/skills/coga/branch-sweep/sweep/SKILL.md` (+ packaged twin, + `coga/recurring/branch-sweep/ticket.md` + its twin) — all say deletion happens "only when a merged PR exists for that exact tip". The code has a second path: `local_branch_landed` → plain `git branch -d` whenever the tip is reachable from the control branch, no PR required. The sibling workflow `coga/workflows/branch-sweep/sweep.md` already words it correctly, so three shipped copies disagree with the fourth and with the code.
- S18 `coga/recurring/skill-update/ticket.md` — `clarity`'s `.coga-source.json` claims its `include` allowlist makes `coga skill update` re-apply the pruning; nothing reads the key (`_url_metadata` never writes it), and the recorded `installed_tree_digest` is the *unpruned* upstream digest, so the weekly job classifies `clarity` as `skipped-local-adaptation` forever — a silent permanent skip the template describes as a human-resolvable exception, not a steady state.
- S19 `coga/contexts/coga/codebase/SKILL.md` — the skill-dependency rule names `requirements.txt`; no such file exists under `coga/skills/`, while all seven managed packs declare `metadata.requires.bins`/`install` in upstream frontmatter that Coga deliberately ignores. Name both forms.
- S20-S24 **premise-dead / overtaken parked drafts** (each needs a lifecycle verdict, not a context edit): `v2/use-worktree-when-starting-a-dev-task` (its premise shipped in `dev/code`, and its proposal — worktrees *inside* the primary checkout — now contradicts the shipped convention); `v2/cleanup-core-commands/launch-decomposition` (design cites `commands/launch.py` at 1,179 lines; it is 3,900 today and the script module moved to `src/coga/launch_script.py`); `v2/pass-secrets-to-skills-with-per-skill-scope` (the `[secrets]` bulk-inject model it is entirely about now fails loud at `config.py:288-297`; residue worth preserving in the cancellation: per-*skill* rather than per-ticket scope); `v2/debug-surface-for-recurring-tasks-streamed-output` (built on the `mode:` field, which appears zero times in the recurring context, and depends on a ticket that does not exist); `v2/wire-recurring-sweep-into-system-cron` (asserts `relay-os/scripts/cron.sh` ships; no `cron.sh` exists anywhere). The last two are outside the cohort of `adjudicate-the-eight-premise-dead-v2-drafts`.
- S25 `coga/tasks/vendored-skills-carry-no-coga-source-json-so-coga.md` (merged ks-19/ks-26 ×3) — this `active` ticket's premise has been overtaken from three directions: `.coga-source.json` now exists (`coga/skills/clarity/`), the skill-update template was rewritten with gh delegation in PR #743 (`8ad3ae3b`) after the ticket's last edit, and its "the twin is not in `IDENTICAL_LIVE_PACKAGED_PAIRS`" warning is false since twins are derived. Its remaining residue is one line: name `ATTRIBUTION.md` / `NOTICE.txt` as the hand-vendored provenance substitute. Leaving it `active` advertises merged work.

### drift — a contract claim contradicts code, artifacts, or a twin

- D1 `coga/contexts/coga/architecture/SKILL.md` — the Dream known-limitation ("packaged `bootstrap/skills/**` sit outside the surface the *contract audit* reads") attributes to one phase a blind spot both scans share: `knowledge-scan` declares the identical corpus. Confirmed empirically this run — the Phase 2 index contains zero `bootstrap/skills` entries while 30 Markdown files live there. Neither decide-half scan can ever report against Dream's own skills.
- D2 `bootstrap/dream/scan/knowledge-scan/SKILL.md` — the "both sides of the comparison in each shard" rule is unsatisfiable at the protocol's budget and was not met this run: 6 of 23 shards own zero ticket paths because a single large context (`architecture`, 74 KB) consumes most of a 150 KB shard. Either allow range-reading a large context against a ticket set, or acknowledge knowledge-only shards as a legitimate kind restricted to `stale`/`drift`.
- D3 `bootstrap/dream/scan/{knowledge-scan,contract-audit}/SKILL.md` — the corpus includes installer-managed upstream skills Coga cannot durably edit: the seven `google-agents-cli-*` trees are 286,169 bytes / 34 files, 61% of all Markdown under `coga/skills/` and ~2 shard budgets, which this run spent shards on. Any `stale` finding there is reverted at the next refresh and no `extract` can target it. Exclude `managed-skills.toml`-declared refs from the scanned corpus.
- D4 `coga/recurring/dream/ticket.md` (+ packaged twin) — the Console Progress line calls the blackboard "the durable record" while the same body twice says the opposite ("never only in this task's blackboard, which a later Dream run retires"). Reword to keep "durable" for PRs, draft tickets, and markers.
- D5 `coga/contexts/coga/extension-model/SKILL.md` — the kernel table omits `block` and `unblock`, which `coga/architecture` lists as core state-machine commands and which are registered at `cli.py:86-87`. Two shipped contexts give contradictory answers.
- D6 `coga/skills/coga/autoclose/sweep/SKILL.md` — presents the retire follow-up as durable ("remains valid until a human retires it"), but its only recurring caller writes to a period blackboard the recurring context calls scratch and the next firing deletes. The two files are individually accurate and jointly wrong.
- D7 `coga/recurring/blocker-reminders/ticket.md` — claims its scan covers "recurring period tasks" with `status: blocked`, but a period task that calls `coga block` is rewritten to `paused`, so it drops out of the only surface that would remind anyone. Evidence on disk: `recurring/resolve-conflicts` sat paused carrying blocker `20260819T135355` from 2026-08-19 until a 2026-09-03 run improvised an escape hatch.
- D8 `coga/contexts/coga/codebase/SKILL.md` — the vendored `google-agents-cli-workflow` pack twice tells the reading agent to run `uvx google-agents-cli setup` / `agents-cli setup --skip-auth`, which inside this repo would rewrite git-tracked, PR-reviewed files out of band and bypass the weekly `coga skill update --all --pr` job. The file is upstream-owned and gh-managed so the correction cannot be a local edit; nothing on the Coga side carries the counter-instruction. (Filed twice, ks-25/ks-26 — merged.)
- D9 `coga/tasks/fix-the-autofix-analyst.md` (+ ks-08 self-correction) — the ticket is `done` and shipped **none** of the three defects it scoped: `recurring_autofix.py:665` still reads `detail = (result.stderr or result.stdout or "").strip()`, no `stdin=subprocess.DEVNULL` anywhere, and `_analyze_agent` (:361) still goes straight to `default_agent()` with no `[autofix]` table in `config.py`. What shipped (PR #724) was an unrelated Claude auth fallback. A partial record exists as backlog item 8 of the still-`draft` `dream-2026-w36-extract-backlog-18-findings-phase-4`, undrained for a Dream cycle; the third defect is missing even there. Needs one real ticket carrying all three, not another backlog line.
- D10 `coga/tasks/marketing/phase-0-audit/ticket.md` — `marketing/plan` lists the audit as "complete input to this plan; do not rerun it" and has absorbed its output, but the ticket is still `in_progress` at step 2, so its `report-to-coga` step never runs and Dream's done sweep will never reap it.
- D11 `coga/tasks/marketing/phase-0-audit/narrative-candidates.md` — **confidentiality exposure.** `FastJVM/coga` is public. This tracked file opens with the owner's ruling that magicator/xpllm/admin material "must not be quoted" and then quotes exactly that: ten verbatim `coga/log.md` lines with slugs, dates and block reasons from those private repos, plus two admin-repo entries sitting beside a trademark serial, Xero reconciles and payroll/tax questions. It has no consumer left (`marketing/post-async-megalaunch` was rescoped; the plan now says the only publishable narrative evidence is Coga-on-Coga). Two sections still assert "eight strong ones with no confidentiality concern", contradicting the header. Owner decision needed: delete (and possibly purge from history) or reduce to the non-quoting summary table.
- D12-D17 **stale premises inside live/active tickets** (each is a ticket-body correction, not a context edit): `guard-the-browser-dochub-and-playwright-live-vs-pa` and `the-ticket-interview-never-asks-what-done-means` both instruct edits to `IDENTICAL_LIVE_PACKAGED_PAIRS` as a manual allowlist, which `test_packaging.py:206` now derives ("there is no list to register a new twin in"); `validate-that-committed-skill-scripts-with-a-sheba`'s 2026-09-01 survey (14 files, 3 violations) is now 19 and 5, and two new violations are vendored `clarity` scripts whose mode bit is not actually broken for their documented use; `v2/file-locking-for-concurrent-task-mutation`'s "no mutual-exclusion primitive exists" is falsified by the `fcntl.flock` in `src/coga/git.py:92,221,231`; `v2/audit-rules-md-usage-across-relay-and-decide-wheth` audits a "Global rules" prompt layer, `rules.md`, and `compose.py:186` behavior that no longer exist anywhere; `no-rule-says-ticket-context-must-cite-symbols-not` treats as open a design question its sibling already answered on an unmerged branch (`design-cite-symbols`, parked at peer-review since 2026-09-02).
- D18-D21 **parked v2 drafts whose deliverable already shipped or is being decided live**: `v2/split-context-to-doc-user-accessible-and-editable` (the larger question is live and past design in `redo-documentation-dir-and-merge-it-with-context-b`); `v2/overload-ticket-locally-easily` (both halves landed in architecture + extension-model; residue is one sentence — `coga ticket` injects a hardcoded `bootstrap/ticket` ref an alias cannot redirect); `v2/document-workflow-less-concept-capture-drafts-as-s` (architecture now covers it at lines 427-462); `v2/docs-and-contt-block-should-be-merged` (empty duplicate of the live docs ticket, already classified as such by that ticket).
- D22 `coga/tasks/v2/implement-accepted-ticket-interview-improvements.md` — routes the implementer to the "Ranked changes" section of `improve-prompt-for-relay-ticket`'s blackboard; that ticket is gone from disk, so the quoted wording it defers to is unreachable except through git history, which the draft never says.

### gap — a repeated pattern with no context, skill, or workflow to carry it

- G1 `coga/contexts/coga/architecture/SKILL.md` — **ticket supersession is prose-only.** Seven v2 tickets each invent their own shape; `CANONICAL_TICKET_KEYS` has no `supersedes`/`superseded_by` and `lifecycle.py:12` has no superseded terminal, so a superseded ticket sits at `paused`/`draft` and keeps surfacing as live work.
- G2 `coga/contexts/coga/architecture/SKILL.md` — **ticket-to-ticket dependency ordering has no mechanism.** `v2/identify-blocking-issues` asks for it; `v2/op-service-account-auth-to-skip-op-read-prompt` already hand-implements it with a `### Blocks` section. The `blocked` status is a runtime blocker-ask, not a declared prerequisite, so ordering recorded in prose is invisible to `coga status`, blocker sweeps, and launch selection.
- G3 `coga/contexts/coga/architecture/SKILL.md` — **no command reassigns `owner:`/`human:`.** Fifteen tickets still carry `owner: zach`, several paused with `assignee: nicktoper`; the fields are canonical and not agent-editable, so hand-editing is the only path and drift is the default.
- G4 `coga/contexts/coga/architecture/SKILL.md` — **"this context is too big to attach — read it directly" is re-invented per ticket.** Three tickets each wrote the same paragraph about the same files (`recurring` 54 KB, `sync` 67 KB, `architecture` 74 KB — a two-context ticket can spend >100 KB of prompt). Nothing in the prompt-composition section names a threshold or blesses the workaround; the only related item is the parked `v2/enforce-a-prompt-token-budget-in-compose`.
- G5 `coga/contexts/coga/architecture/SKILL.md` — **21 tickets have a literally empty `## Description` and `## Context`.** `validate.py` never checks that the body says anything. Titles like `remote stale command line toosl` are unrecoverable by anyone but the author. Either add a validator warning or document title-only capture as supported with an explicit expiry.
- G6 `coga/contexts/coga/codebase/SKILL.md` — **nothing exercises Python 3.11, the declared floor.** `pyproject.toml:10` says `>=3.11`; `.github/workflows/` has only `release.yml` with no pytest step, and the context tells you to run `python3.12`. The cost is recorded: `coga init` crashed on every 3.11 interpreter (`MultiplexedPath.joinpath`) across five call sites, invisible because "3.12 happens to work". `src/coga/commands/__init__.py` leaves the same footgun latent.
- G7 `coga/contexts/coga/codebase/SKILL.md` — **the two packaged-context distribution paths are undocumented.** `paths.resolve_context_path` falls back to `bootstrap/contexts/` only, while `templates/coga/contexts/**` is init-seeded and never a runtime fallback. Already shipped a defect: the bundled `bootstrap/browser-automation/ticket.md` attaches `browser/api-first`, which exists only under the init-seeded tree, so that bootstrap ticket cannot compose from bundled resources alone.
- G8 `coga/contexts/coga/codebase/SKILL.md` — **repo-wide `coga validate` has a standing non-zero baseline** (four `unsynthesized-draft-blackboard` errors on `v2/` drafts) that independent tickets keep re-deriving by hand. The one ticket scheduled to clear it is `canceled`. Record the baseline and its four slugs beside the `--task` bullet, and state they must not be auto-fixed under an unrelated ticket.
- G9 `coga/contexts/coga/codebase/SKILL.md` — **`coga/cli` is the only shipped context with no live copy**, so the derived twin test does not cover it and it is invisible to anyone treating `coga/contexts/` as canonical — yet three live contexts route readers to it and tickets edit it. Flagged once before as an adjacent finding; the decision was never made.
- G10 `coga/contexts/coga/codebase/SKILL.md` — **the local-adaptation guard covers url sources only.** `installed_digest` is computed only when `source_type == "url"` (`skill_manager.py:180-184`); every entry in `managed-skills.toml` is `github`, and `_update_gh_backed_skills` delegates to `gh skill update` with no digest comparison. A local edit to any `google-agents-cli-*` file is silently overwritable, while the same edit to a url-sourced skill raises a conflict.
- G11 `coga/contexts/coga/codebase/SKILL.md` — **nothing records why seven ADK packs live in this repo.** ~250 KB of GCP/ADK guidance materialized into `coga/.agent-skills/`, one self-described as "always active", while no ticket, context, or job in the repo does ADK work. The presumable reason — dogfooding the managed-skill path against a real remote — is written nowhere, so a future cleanup could delete the only end-to-end test of that path.
- G12 `coga/contexts/coga/sync/SKILL.md` — **no context states which branch is canonical for machine-generated Coga state.** The mechanisms are documented exhaustively; the policy the owner settled on 2026-08-25 lives only in a draft ticket body. The cost is visible: `detect-stranded-ticket-writes-across-checkouts` built its whole divergence discriminator on a "verified code fact" that the launch-end pull-back contradicts.
- G13 `coga/contexts/coga/recurring/SKILL.md` (or `codebase`) — **no knowledge names the durability property of a recipe's report blackboard.** Under a recurring template `blackboard_from_env` resolves to `coga/tasks/recurring/<name>/ticket.md`, which the next firing deletes. Four shipped recipes append through it; three are fine because their durable output is a PR, autoclose's retire follow-up was not. The existing note covers only *which repo*, never which task or for how long.
- G14 `coga/contexts/coga/recurring/SKILL.md` — **a failing recipe's detail reaches no durable surface.** The rule exists only in a source docstring (`run_skill_update_recipe`), which names the debt itself: six other recipes "all exit non-zero to stderr alone… do not paste a seventh copy, generalize it instead." No ticket owns the generalization; two independently filed tickets show the cost.
- G15 `coga/contexts/coga/period-task/SKILL.md` (+ packaged twin) — **the context is auto-attached to every period task but written end-to-end for an agent**, while five of seven shipped templates carry `ticket.py` and never spawn one. Nothing says the recipe performs that bookkeeping in code and no reader of this context exists for those firings.
- G16 `coga/skills/code/design/SKILL.md` — **ticket specs keep pinning line numbers that rot before implement runs.** Two done tickets were nearly derailed by it (one spec's `_launch` had grown ~790 lines; a cold evaluator listed nine stale citations, one pointing at the wrong module). `code/design` says nothing about citation form. Note `ticket-specs-should-cite-symbols-not-line-numbers` is in_progress and may already own this.
- G17 `code/implement` + `code/design` — **the split-a-ticket mechanic is still undefined** after two Dream runs surfaced it. `implement:146` says "stop and split the ticket on the blackboard" and `design:52` says "recommend a split"; neither defines the sibling slug convention, the blackboard heading, the cross-link form, or sequenced-vs-co-equal. The parked draft's other half (adjacent-finding preservation) has since fully shipped in `retro/done-ticket`.
- G18 `coga/skills/browser/dochub/SKILL.md` — **no "why the browser, not the API" answer**, which `browser/api-first` requires of every real-SaaS-UI ticket. DocHub is the repo's one committed automation target and the file contains no occurrence of "API"; nothing in the corpus records the check. Compounds three "GAP — unavailable" blocks in the same file where per-site learning was lost.
- G19-G22 `coga/tasks/v2/README.md` — four holes in the parking-area contract, all evidenced this run: **(a)** nothing re-validates parked drafts while they sit (the only sweep was a one-off; this run alone found several more premise-dead); **(b)** no rule for dangling cross-ticket references, the rot Coga's own machinery manufactures on a schedule since Phase 4 deletes the tickets drafts cite; **(c)** no question for "some other change already shipped this", the commonest outcome here (D18-D21); **(d)** the guard "a green validate is never a reason to cancel a draft" is carried verbatim by three tickets — one already `canceled`, two `draft` — and by no context, skill, or workflow, so the durable statement can be deleted while the incentive persists.
- G23 `coga/tasks/v2/README.md` — **title-only stubs outside `v2/` have no governing contract.** Three sit at the `coga/tasks/` root (`add-an-agent-picker-for-recurring`, `remov-digest-in-recurring`, `make-sure-repo-clietn-don-t-edit-coga`) where they read as current work in `coga status`; `validate.py:459` stays silent on an untouched placeholder. Generalize the README's dated-artifact contract or rule root-level capture out.

### Contract audit (Phase 3)

10 leaf shards, all complete; 5 findings. Three independently re-derive Phase 2
findings from contract-side evidence and are merged into them rather than counted
twice: ca-01 → **S1** (`launch-internals` "~19 KiB" vs 29,083 bytes, and its
packaged twin carries the same stale number), ca-02 → **S4** (the `coga/skills/`
shape enumeration omits `marketing/` and mis-defines the flat shape as
"declared in `managed-skills.toml`"), ca-06 → **S12** (`skills/_template`
forbids the slash-qualified `name:` that eight repo-authored skills use; the
packaged twin is byte-identical, so it is a content bug in both copies, not
divergence). Two are new:

- C1 `docs/reference.md:7` — claims "`coga --version` prints the Coga package and vendored CLI versions". `_print_version_and_exit` (`src/coga/cli.py:45-53`) resolves only `importlib.metadata.version("coga")` and emits one line, `coga <pkg>`; no vendored CLI is probed. Drop the clause or restore the output.
- C2 `docs/README.md:20` — routes "aliases" to `docs/operations.md`, which has no alias section: the word appears twice in passing inside the recurring section and the `[aliases]` table is never explained. `docs/reference.md` owns `## Aliases` (line 516). Repoint the index entry.

**Copy divergence: clean.** ca-10 derived `IDENTICAL_LIVE_PACKAGED_PAIRS` from
the packaged tree as the skill directs, confirmed both sides of every pair are
tracked, and `cmp`'d each — zero diverged pairs, which is what a green
`tests/test_packaging.py` predicts.

## Dream Skill: cleanup-orphan-markers

Generated: 2026-09-09T00:16:37+00:00
Task: `recurring/dream`

Result: no-op. No cleanup-eligible processed done tickets still have task directories.

### Corrections to the findings above

The Phase 6 PR authors re-verified every finding against the tree before
writing, and six of the scan's claims were wrong or overstated. The PRs carry
the corrected text; these entries are corrected here so the index does not
outlive the truth.

- **S18 was wrong in its second half, and the reality is worse.** `clarity` is
  not parked in a permanent conflict. The recorded `installed_tree_digest`
  currently *equals* the on-disk tree digest, so `locally_adapted` is false and
  no follow-up guard fires at all; meanwhile `source_tree_digest` records the
  digest of the *pruned* tree rather than any upstream tree, so the
  "upstream unchanged" test can never be true and the next run falls into
  `_replace_skill_tree` — a silent un-prune that restores `commands/`, `evals/`,
  `samples/`, `site/` and drops the `include` key, landing under the weekly PR's
  *updated* heading with no follow-up line. The permanent-conflict shape belongs
  to the metadata as it stood before commit `274e264c`, which is what this run's
  own sweep report (`clarity: conflict (url)`) reflects. PR #775 documents both
  states.
- **D7 was overstated.** `_pause_unfinished` in `recurring_runner.py` returns
  early when the block was *script-recorded*, so a `ticket.py` phase that calls
  `coga block` leaves the period `blocked` and is scanned normally. The gap is
  real but scoped to **agent** period tasks. The evidence dates are 2026-08-13/14,
  not 08-19, and the escape hatch was an explicit `coga megalaunch` pick, not a
  status filter flipped to `paused`.
- **S13's stated exception was wrong.** The region below the blackboard fence
  *is* composed — as its own `blackboard` layer. The real exception is that
  `_extract_section` lifts only `## Description` and `## Context`, so any other
  `##` heading above the fence is dropped.
- **S2/S3 mischaracterized the precedent.** `open-pr` and `delete-task` did not
  receive an `[aliases]` rewrite; `coga/coga.toml`'s `[aliases]` holds only
  `chat`, `build`, `pick`, `claude`, `codex`. They have no Typer command and no
  alias — they are reachable only as `coga run <name>`. That is the shape
  `digest` has not yet been given.
- **E9's megalaunch constraint was imprecise.** Megalaunch does not re-read the
  ticket between activation and launch; it prepares on a throwaway copy
  (`_prepare_for_launch` → `prepare_active`), preflights off that prospective
  view, commits only after every refusal passes, then recaptures the ticket
  bytes and refuses if they moved. The intended invariant survives: a
  prepared-but-uncommitted `Ticket` never becomes the durable revision.
- **E10's framing needed one narrowing.** `coga validate` does *not* fire the
  dispatch-boundary sweep — it is on the read-only exclusion list. The
  conclusion still holds, because the mutation stays dirty and rides along on
  the next mutating command, possibly a scheduled sweep or another terminal.

Two findings were also strengthened by verification rather than corrected: the
architecture PR found **four** prospective-validate call sites, not two, and the
branch-sweep PR established that the ancestry check runs *first* in
`delete_local_branch` (so `pr_merged` is never read on that path) and that
ancestry never authorizes a *remote* delete.

## Dream Run Summary

Generated: 2026-09-09 (period `2026-09-08`, task `recurring/dream`).

| # | Phase | Result | Detail |
|---|---|---|---|
| 1 | validate-drift | `reported` | 32 issues: 0 direct-fix, 5 PR-proposal, 27 human-needed. No repairs applied. |
| 2 | knowledge scan | `reported` | 23/23 leaf shards complete, 0 incomplete. 101 raw blocks → 72 merged entries (17 extract, 25 stale, 22 drift, 23 gap). |
| 3 | contract audit | `reported` | 10/10 leaf shards complete. 5 findings: 3 re-derived Phase 2 findings from contract-side evidence, 2 new. Copy divergence clean — zero diverged twin pairs. |
| 4 | retro/done-ticket | `direct-fixed` | 7 eligible tickets, all direct-deleted on the control branch. 0 knowledge PRs — none carried durable knowledge. |
| 5 | cleanup-orphan-markers | `no-op` | No processed Retro marker survives on a still-present task directory. |
| 6 | disposition | `pr-opened` + `proposed` | 13 proposal PRs opened, 18 tracked draft tickets created. |

### Phase 4 detail

Of 41 done tickets on disk, **34 carry a recorded feature checkout** and are
therefore retirement debt, not Retro input — left untouched so the human-typed
`coga retire <slug>` stays valid. The 7 eligible were the six `recurring/*`
period tickets from this sweep plus
`service-account-scoping-single-vault-rule-conflict`, whose knowledge had
already shipped into `coga/contexts/coga/secrets/SKILL.md` with its one deferred
item carried by an existing ticket. All seven were direct-deleted with
`coga delete --keep-control-checkout` from an isolated linked worktree; the
diff against the pre-Phase-4 tip is exactly those 7 artifacts (12 files) and
nothing else. Worktree, temporary branch, copied `coga.local.toml` and the
evidence snapshot were all removed and verified gone.

### PRs opened (all `pr-required` — none auto-merged)

| PR | Scope | Findings |
|---|---|---|
| #763 | `docs/reference.md`, `docs/README.md` | C1, C2 |
| #764 | `coga/launch-internals` + twin | S1/ca-01, E11 |
| #765 | `marketing/positioning` | S5 |
| #766 | branch-sweep skill + recurring template (2 twin pairs) | S17 |
| #767 | `coga/sync` + twin | S7, S8, S9, E10 |
| #768 | skill `_template` + ticket `_template` (2 twin pairs) | S12/ca-06, S13 |
| #769 | `coga/architecture` + twin | E1, E2, E3, E4, D1 |
| #770 | Dream scan skills + Dream template twin | D2, D3, D4 |
| #771 | `dev/code`, `code/implement`, `code/open-pr` (3 twin pairs) | S10, E16 |
| #772 | `bootstrap/import`, `bootstrap/ticket` (packaged-only) | E14, E15 |
| #773 | `coga/codebase`, `coga/extension-model`, `CLAUDE.md`, `AGENTS.md` | S2, S3, S4/ca-02, S6, S19, E5, E6, E7, E8, E9, D5, D8 |
| #774 | `coga/recurring`, autoclose sweep skill, blocker-reminders template (3 twin pairs) | S14, S15, S16, E12, D6, D7 |
| #775 | `coga/recurring/skill-update` template + twin | S18 |

### Draft tickets created (18, all `code/with-review`)

Gaps and lifecycle decisions that need human design judgment. Each carries a
written `## Description` and `## Context` — a title-only ticket is the exact
defect one of these findings names.

`ticket-relationships-and-ownership-have-no-mechani` (G1-G3) ·
`document-when-to-attach-a-large-context-versus-cit` (G4) ·
`title-only-tickets-have-no-convention-and-no-valid` (G5, G23) ·
`nothing-exercises-python-3-11-the-declared-floor` (G6) ·
`record-or-clear-the-standing-repo-wide-coga-valida` (G8) ·
`document-how-packaged-contexts-reach-a-repo-and-se` (G7, G9) ·
`installer-managed-skills-the-local-adaptation-guar` (G10, G11) ·
`state-which-branch-is-canonical-for-machine-genera` (G12) ·
`define-the-recipe-reporting-contract-report-durabi` (G13, G14) ·
`the-period-task-context-never-covers-the-determini` (G15) ·
`define-the-split-a-ticket-mechanic-shared-by-code` (G17) ·
`record-dochub-s-why-not-the-api-answer-that-browse` (G18) ·
`the-v2-parking-area-premise-check-has-four-holes` (G19-G22) ·
`the-autofix-analyst-ticket-closed-without-shipping` (D9) ·
`test-recurring-create-is-silent-fixture-fix-is-hal` (E17) ·
`adjudicate-parked-and-active-tickets-whose-premise` (S20-S25, D12-D22) ·
`narrative-candidates-md-publishes-log-text-the-own` (D11) ·
`phase-0-audit-is-complete-per-the-plan-but-still-i` (D10)

G16 (ticket specs pinning line numbers) was deliberately **not** ticketed: the
in_progress sibling `ticket-specs-should-cite-symbols-not-line-numbers` already
owns that change, on the unmerged branch `design-cite-symbols`. Filing a second
ticket would have duplicated live work.

### human-needed

1. **`narrative-candidates.md` publishes material the owner ruled confidential**
   in a public repo — ten verbatim `coga/log.md` lines with slugs, dates and
   block reasons from three private repos, plus two admin entries beside a
   trademark serial and payroll/tax questions. Dream deliberately opened **no
   PR** here: deleting the file and purging it from history are different
   decisions with different costs, and a PR diff would quote the material again.
   Ticketed; the decision is the owner's.
2. **34 done tickets are deferred retirement debt** awaiting human-typed
   `coga retire <slug>`. Their durable knowledge is what Phase 6's PRs carry —
   the extract findings E1-E17 all originate in these tickets, and because they
   are not Retro-eligible, Phase 4 could not route them. Routing them into
   proposal PRs instead is the deviation this run made from the body's "extract
   → already handled by Phase 4" line, taken so no verified durable fact is lost
   when retirement removes its source.
3. **Phase 1's 27 human-needed validator issues** stand: 6 `stuck-in-progress`
   tasks (one idle 1,178h), 15 `unfrozen-workflow` warnings, 6
   `unknown-assignee` warnings. Each is a lifecycle or ownership decision Dream
   must not make silently.
4. **The repo-wide `coga validate` baseline is still 4 errors** on the same four
   `v2/` drafts. Unchanged by this run; ticketed.
5. **Environment gap seen by every PR author:**
   `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries` fails on
   this machine because the ambient interpreter cannot import `hatchling`
   (PEP 668 blocks installing it). It fails identically on unmodified
   `origin/main`. Every twin-parity assertion — the check these PRs actually
   need — passes. Worth fixing so a red suite stops being ambiguous.

### Scan directories

Both were reconciled, merged, and removed: knowledge scan
`/tmp/dream-knowledge-Dam6`, contract audit `/tmp/dream-contract-sVMA`. No
`partial` phase, so nothing was retained for a human.
