---
title: Dream
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 83b31e2d-c5ec-4c05-ab55-01158198fa08
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
The blackboard is this run's record of what happened; console progress is for
the human watching it happen. Neither is durable — that word belongs to the
PRs, draft tickets, and markers a finding has to end in.

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
   at most 40 distinct files, keeping a task directory's Markdown together. A
   file is never split across two owning shards; the one departure from
   whole-file ownership is the protocol's **ranged ownership** for a file over
   the 60 KB whole-read limit, which stays with a single owner and is priced at
   its declared allowance rather than its full length. Append one attempt-1
   shard row per assignment to `manifest.md`.
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

Generated: 2026-09-14T18:56:29+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python -m coga.validate --json --fix`
Task: `recurring/dream`

Result: 30 issue(s): 0 direct fix, 6 PR proposal, 24 human-needed.

### PR Proposal

- `reconcile-recurring-wrapper-tty-admission-guidance`: `large-blackboard` (warn) - blackboard region is 54.0 KiB (warning threshold 32.0 KiB); it is included in launch prompts. Consider summarizing old notes.
  Remediation: Propose a reviewed blackboard condensation that preserves current decisions and blockers before removing detail.
- `recurring/digest`: `broken-skill` (error) - step 'flush' references skill 'coga/digest/flush', but no skill file exists for it. Checked: /home/n/Code/claude/coga/coga/skills/coga/digest/flush/SKILL.md, /home/n/Code/claude/coga/src/coga/resources/templates/coga/bootstrap/skills/coga/digest/flush/SKILL.md.
  Remediation: Open a small PR after reading the task: either fix the typo in the reference or add the missing context/skill with reviewable content.
- `v2/autotrigger-ticket-type`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.
- `v2/measure-relay-prompt-scope-and-agent-precision`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (non-placeholder blackboard is 4213 characters); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.
- `v2/split-context-to-doc-user-accessible-and-editable`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.
- `v2/use-worktree-when-starting-a-dev-task`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.

### Human Needed

- `add-an-agent-picker-for-recurring`: `stuck-in-progress` (warn) - in_progress but idle for 86.1h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `adjudicate-the-eight-premise-dead-v2-drafts`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `agent-usage-report`: `stuck-in-progress` (warn) - in_progress but idle for 86.1h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r`: `stuck-in-progress` (warn) - in_progress but idle for 264.4h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `correct-the-v2-known-stale-surfaces-table-and-rout`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `detect-stranded-ticket-writes-across-checkouts`: `stuck-in-progress` (warn) - in_progress but idle for 86.1h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `make-sure-repo-clietn-don-t-edit-coga`: `stuck-in-progress` (warn) - in_progress but idle for 98.1h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `marketing/build-the-launch-plan`: `stuck-in-progress` (warn) - in_progress but idle for 239.0h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `marketing/phase-0-audit`: `stuck-in-progress` (warn) - in_progress but idle for 96.0h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `marketing/plan/collect-public-examples-for-the-launch`: `unfrozen-workflow` (warn) - workflow 'draft-for-human' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `marketing/plan/write-the-pitch-and-narrative`: `unfrozen-workflow` (warn) - workflow 'draft-for-human' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `parse-agents-rejects-cogalocaltoml`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `recurring-sweep-wedges-on-the-ticket-py-it-copies`: `stuck-in-progress` (warn) - in_progress but idle for 97.6h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `redo-documentation-dir-and-merge-it-with-context-b`: `stuck-in-progress` (warn) - in_progress but idle for 136.4h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `reuse-the-existing-control-worktree-for-recurring`: `stuck-in-progress` (warn) - in_progress but idle for 117.9h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `the-ticket-interview-never-asks-what-done-means`: `stuck-in-progress` (warn) - in_progress but idle for 286.1h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `ticket-specs-should-cite-symbols-not-line-numbers`: `stuck-in-progress` (warn) - in_progress but idle for 286.0h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
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
- `v2/document-contexts-as-prompt-payload-not-tags-princ`: `stuck-in-progress` (warn) - in_progress but idle for 1317.7h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `v2/fix-windows-cli-import-crash`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.

## Run notes (2026-W38)

- Phase 1 validate-drift: `reported` — 30 issues (0 direct-fix, 6 pr-proposal, 24 human-needed); no repairs applied. Recipe's git sync was refused because the checkout already had uncommitted edits on two unrelated tickets (`define-the-api-equivalent-cost-proxy-and-price-tab`, `validate-that-committed-skill-scripts-with-a-sheba`) — left untouched.
- Phase 2 knowledge scan: scan dir `/tmp/dream-ks-YlTD4I`; corpus 228 ticket files (2.01 MB) + 88 knowledge files (767 KB, managed `google-agents-cli-*` excluded); 32 attempt-1 shards (ks-01..ks-32), launched in batches of 8.

## Findings

Merged from Phase 2 (`/tmp/dream-ks-YlTD4I/findings.md`, 32/32 shards complete, 33 raw → 28 after de-dup) and Phase 3 (appended below once reconciled). Overlap notes name open PRs that already edit the target file.

### extract (grouped by area; Phase 4 input)

- F-01 [coga/codebase] `live-and-packaged-twin-pairs-are-edited-together-b`: `CLAUDE.md`/`AGENTS.md` are a hand-kept byte-identical twin with no test; add one sentence to the codebase context's twin bullet (edit both, `cmp` them; `test_packaging.py` never covers them).
- F-02 [coga/codebase] `cleanup/add-a-debug-mode-to-init-for-vendoring-from-source`: record the developer install model — `coga` is a uv-tool editable install whose interpreter is `$(dirname "$(readlink -f "$(command -v coga)")")/python`, `direct_url.json` names the checkout it imports; scripts that must `import coga` run under that interpreter, not ambient `python`; `.coga/` is machine-local state (`recurring-runs/`, megalaunch selection), not an installation directory (codebase context + CLAUDE.md wording).
- F-03 [coga/codebase] `allow-description-and-owner-on-create`: `create_task()` writes + logs before `assert_task_valid`; only `commands/create.py` guards a structure-breaking description (`_description_structure_problem`). Add a "Gotchas when editing coga's own code" bullet: new callers must reject level-2 headings / own-line fence themselves.
- F-04 [coga/sync] `simplify-ticket-format`: the one-PR cutover procedure for a stored-ticket schema conversion (code+data+fixtures+contexts in one PR; regression guard is not a schema barrier — quiet the dispatchers and inventory worktrees/clones/editable installs; refresh the conversion from the exact control tip at the gate; rebase rule: take control's ticket wholesale then re-apply only the mechanical conversion; never run a mutating Coga command from the converting checkout).
- F-05 [retro/done-ticket] `dream-phases-2-3-cannot-complete-scan-subagents-re`: Phase 4 needs on-disk start/done receipts per slug. **Already implemented** by open PR #795 (item 16); no new knowledge PR — Retro may still delete the source ticket if it judges the knowledge landed.

### stale

- F-06 `coga/contexts/coga/codebase/SKILL.md` ↔ packaged twin diverged (commit `74692b23 Sync coga state` swept PR #796's live-context edit onto `main` ahead of the code; `test_packaging.py` red on main). Open PR #796 carries the matching packaged copy and resolves it on merge. **Overlap → no Dream PR; human-needed: merge #796 or revert live lines 33-34/188-207.** (ks-01/18/28 merged.)
- F-07 `coga/contexts/coga/codebase/SKILL.md` ~L216-227 + packaged twin: "the `include` allowlist is inert" is false since #776 (`parse_include_allowlist`/`apply_include_allowlist` in `skill_manager.py`). Draft `implement-the-include-allowlist-that-url-skill-upd` is discharged by #776 (human: cancel). (ks-26/29 merged; ks-26's "no packaged twin" claim was wrong — the bootstrap twin exists.)
- F-08 `coga/contexts/coga/codebase/SKILL.md` + twin: closing "coga layout" paragraph says managed skills install "during init/update"; only `coga init` calls `install_managed_skills`; `reconcile_managed_skills` has no production caller. (ks-16)
- F-09 `coga/recurring/skill-update/ticket.md` + packaged twin: paragraphs "A URL install that was pruned after download is a distinct shape…" through "Implement the `include` allowlist…" describe pre-#776 behavior and contradict the earlier allowlist paragraph; cut to the one true caveat (a `.coga-source.json` with no `include` key gets no pruning protection). Overlap: PR #796 edits the same file's L24-40 (different hunk). (ks-06/26/29 merged.)
- F-10 same template, final paragraph: "a non-zero `ticket.py` … every template ordered after `skill-update` is then skipped" — fixed in `recurring_runner._launch_due_tasks` (records failure, keeps sweeping). Also: `autofix/stop-one-failing-ticket-py-from-starving-the-rest` is still `active` although shipped → human-needed. (ks-06)
- F-11 `coga/contexts/coga/recurring/SKILL.md` ~L661-664 + twin: "Exit-code contract" gotcha still says a non-zero exit stops the whole sweep, contradicting L122-128 of the same file and the code. Overlap: #792 (L982) and #795 edit this context in other hunks. (ks-07)
- F-12 `coga/recurring/autoclose-merged/ticket.md` + twin: blackboard note implies the retire follow-up section accumulates on the template; `autoclose._report_retire_followups` writes the period task's blackboard (non-durable). Reword; point at open `persist-autoclose-retire-follow-ups`. (ks-04)
- F-13 `coga/recurring/blocker-reminders/ticket.md` + twin: names `_pause_unfinished`, which does not exist; the behavior lives in `recurring_runner._stop_if_unfinished_after_launch`. (ks-07)
- F-14 `coga/contexts/marketing/map/SKILL.md`: "Source/debug installation" launch-dependency row describes a done ticket that instead deleted the vendored venv; reader path is `uv tool install coga` + `coga init`. (ks-24)
- F-15 `coga/skills/clarity/` is unpruned again (93 files, 2.3 MB incl. `site/`, PNG samples) and `.coga-source.json` lost its `include` key in the #762 refresh (which ran on pre-#776 code) while its `local_adaptation_notes` still describe the prune; `installed_tree_digest` matches the unpruned tree so `coga skill update` sees a clean install. Fix: restore `include` (SKILL.md, LICENSE, references, scripts/prose_stats.py, scripts/strip_markdown.py) and re-prune. Side effect: upstream marketing copy now enters Dream's corpus. (ks-26)
- F-16 packaged-only `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md` (~L118, 226, 271-276, 1131-1137) still documents `human`/`assignee`/`watchers` and the old promote pass-through; #784 removed them (`REJECTED_TICKET_KEYS`, derived operator). Overlap: #788 and #796 edit this file in other hunks. (ks-15)
- F-17 packaged `bootstrap/workflows/docs/with-review.md`: `review` step promises the PR-comment assist but freezes no `skills:` (`code/with-review` freezes `code/address-pr-comments`); `open-pr` hand-runs `gh pr create` without `requires: pr`. Live ticket `document-the-ticket-blackboard-writer-s-contract` (PR #798) is parked on exactly this shape. (ks-19)
- F-18 `bootstrap/orient/ticket.md` says a launch gives "a lock" and points at `docs/spec.md` (does not exist; only other mention is an error string at `src/coga/config.py:276`); `commands/init.py::AGENT_GUIDE_TEMPLATE` says canonical contexts are "composed automatically" but `compose_prompt_report` reads only `ticket.contexts`. (ks-21)
- F-19 `coga/contexts/coga/sync/SKILL.md` ~L484-488 + twin: "coga stays intentionally lock-free … share a single `.git/index`" contradicts the later admission/publication barrier section and `git.py::state_publication_barrier` (`fcntl.flock`). Overlap: #791 (L249/349/1134) and #797 (L752) edit other hunks. (ks-14)
- F-20 `coga/tasks/v2/README.md` known-stale-surfaces row misroutes `relay-os/workflows/code/*` to a nonexistent `coga/workflows/code/`; `code/*` resolve from the packaged bootstrap tree only. **Already tracked** by draft `correct-the-v2-known-stale-surfaces-table-and-rout` (whose `script:` deliverable is now moot — #784 removed `script`). (ks-31)

### gap

- F-21 `code/design` should tell the designer to cite symbols, not line numbers. **Already tracked**: `no-rule-says-ticket-context-must-cite-symbols-not` (PR #793 open). (ks-10)
- F-22 "A green `coga validate` is never a reason to cancel a draft" lives in eight tickets and no context. **Already tracked**: draft `the-v2-parking-area-premise-check-has-four-holes` (hole 4). (ks-32)
- F-23 Fresh linked worktrees lack `coga.local.toml`; nothing says so before the first mutating command. **Already tracked**: `isolated-checkouts-nothing-says-what-a-fresh-workt` (PR #789 open). (ks-13)
- F-24 No documented recovery for a bump whose strict publication failed on transport (claim-clearing dirty ticket wedges every later sweep). **Already tracked**: `detect-stranded-ticket-writes-across-checkouts` (PR #797 open: sweep converges the release + sync-context text). (ks-09)
- F-25 Ticket-to-ticket supersession has no convention or field. **Already tracked**: draft `ticket-relationships-and-ownership-have-no-mechani` (3 of its 6 cited example slugs no longer exist — refresh evidence). (ks-32)
- F-26 Splitting a ticket into siblings has no defined mechanic in `code/implement`/`code/design`. **Already tracked**: draft `define-the-split-a-ticket-mechanic-shared-by-code` (+ `v2/skill-for-split-into-sibling-ticket-discipline`). (ks-32)
- F-27 No context names the remedy for a bloated blackboard (promote to directory form, move dated evidence to sibling attachments; superseded program material to an unattached context). Two marketing tickets converged on it independently; draft paragraph for `coga/architecture` provided in the scan findings. (ks-24)
- F-28 Dream's `gap` routing creates drafts without searching for an open owner. **Already tracked**: `dream-findings-have-three-routing-holes-that-lose` (PR #799 adds the owner search). (ks-31)

### drift (Phase 3 contract audit — `/tmp/dream-ca-PpZ8Mn`, 10/10 shards complete, 13 raw → 6 new after de-dup)

Confirmed independently by the audit (merged into the Phase 2 entries above): F-06 (ca-10: copy-divergence shard; `test_packaging` 1 failed/10 passed on main; all other 60 pairs identical), F-07 (ca-04), F-09/F-10 (ca-07), F-11 (ca-02), F-13 (ca-07).

- F-29 `coga/contexts/coga/sync/SKILL.md` ~L89-94 and ~L418-422 + twin: "both recurring-error producers pass `important=True`" and the outcome-producer list omit the third producer — `recurring_runner.run_recurring_scan` (~L1640, PR #778) re-escalates every already-watchdog-paused task on each sweep with `kind="recurring-error", important=True`. (ca-03)
- F-30 `docs/cli-extension-audit.md` L76: CLI-verb table row `create` / `draft` — no `draft` verb exists (`cli.py` registers only `create`; no alias). (ca-08)
- F-31 `coga/contexts/coga/project-stage/SKILL.md` L53-55: "watchers … later reintroduced" — #784 removed `watchers` again (`REJECTED_TICKET_KEYS`). **Already tracked**: PR #795 item 15 corrects this bullet. (ca-05)
- F-32 `coga/contexts/coga/architecture/SKILL.md` ~L562-564 + twin: "`coga.mark` finalizers own the `draft`/…" — there is no `mark_draft`; `draft` is written by `coga create` via `default_status`. Overlap: #790 and #798 edit this context in other hunks. (ca-01)
- F-33 `coga/contexts/coga/sync/SKILL.md` ~L788-805 + twin: `ticket_state_guard` caller list "mark, bump, unblock — that is all of them" and "recurring child writes pass no ticket-state guard" are wrong: `open_pr._sync_pr_record`, `recurring_runner._period_lease_guard`, `megalaunch.py` (4 sites) and `commands/launch.py` also bind it. (ca-03)
- F-34 `coga/contexts/coga/sync/SKILL.md` ~L155 + twin: "runs `draft`/`mark`/`launch`/`bump`" — no `coga draft` command; the command is `coga create`. (ca-03)

- Phase 3 contract audit: `reported` — 10 shards (ca-01..ca-10, incl. one copy-divergence shard), 13 raw findings, 6 new after de-dup against Phase 2. Scan dir deleted after merge.

## Phase 4 — retro/done-ticket (2026-W38)

Isolated linked worktree `/home/n/Code/claude/coga-dream-w38-retro` (branch `dream-w38-retro` from fresh `origin/main`); read-only snapshot `/tmp/dream-retro-evidence-usNSa1`; receipts `/tmp/dream-retro-progress-w38.md`. 10 eligible done tickets processed in one run; 40 done tickets carry a real `## Dev` branch/worktree → deferred retirement debt (list in run summary).

Knowledge PRs (`pr-required`, source ticket deleted in the PR with its `## Retro` marker):
- #801 — New context: PR review threads that merge unanswered — `dev/code` context (+twin) new section (owner-gate mechanism, 7-of-38 measured miss, 2026-09-13 decision, two reading rules); `coga/codebase` context (+twin) gotcha preserving five unresolved adjacent bugs (PRs 699 P1, 704, 705, 747, 755). Source: `verify-the-pr-review-comment-loop-once-the-review`. Overlaps #787/#789/#790/#795/#796 (codebase), #789/#795 (dev/code).
- #802 — New context: the four commit subjects Coga writes for itself — `coga/sync` context (+twin): `Sync task state:`, `Ticket: <slug> — <event>`, `Sync coga state`, `Log: <slug>`. Source: `autofix/filter-coga-s-own-log-sync-commits-out-of-the-dige`. Overlaps #791/#797 (other hunks).

Direct-deleted (no durable knowledge; on `origin/main`, recovery via `git restore`): `guard-the-browser-dochub-and-playwright-live-vs-pa` (ff6d5ffa), `recurring/autoclose-merged` (42f1a7be), `recurring/blocker-reminders` (9f632edb), `recurring/branch-sweep` (548b6928), `recurring/digest` (2264587d), `recurring/resolve-conflicts` (74749574), `recurring/skill-update` (35671e46), `v2/dev-loop-git-hygiene-lift-sync-with-main-into-code` (b73b20d0).

Verified after return: all 8 deletions absent from `origin/main`; both PR branches on the remote; worktree clean on `dream-w38-retro` == `origin/main`.

## Dream Skill: cleanup-orphan-markers

Generated: 2026-09-14T20:08:45+00:00
Task: `recurring/dream`

Result: no-op. No cleanup-eligible processed done tickets still have task directories.

## Gotchas

- **Any Coga command run inside a proposal worktree fires the catch-all state sweep, and edits under `coga/` (a skill tree included) land on the control branch as `Sync coga state`.** Reproduced this run: `coga skill status --check` in `coga-dream-w38-fix` committed the clarity re-prune straight to `origin/main` (7966c2a2) before a PR existed — the same mechanism that put PR #796's context edit on `main` (F-06). In a worktree meant for a reviewable PR, edit files with plain tools and run no `coga` command until the branch is pushed; verify with `git`/`python` instead.
- A Retro evidence snapshot made read-only with `chmod -R a-w` needs `chmod -R u+w` before `rm -rf`.
- `git stash list` is shared across all linked worktrees of one `.git`; stale `autostash` entries there belong to other checkouts' failed sync rebases — do not drop them from a Dream worktree.
- The primary checkout had a pre-existing dirty ticket (`define-the-api-equivalent-cost-proxy-and-price-tab`, a published launch claim) that made every catch-all sync refuse for the whole run; per-transition scoped publication (`coga create`, `coga slack`) still landed, and the run's own task-file edits had to be committed and pushed by hand from `main`.

## Dream Run Summary

Generated: 2026-09-14T20:23:08Z — period 2026-W38.

| Phase | Result | Detail |
|---|---|---|
| 1 validate-drift | reported | 30 issues: 0 direct-fix, 6 pr-proposal, 24 human-needed; no repairs |
| 2 knowledge scan | reported | 32/32 shards complete, 33 raw → 28 merged (5 extract, 15 stale, 8 gap) |
| 3 contract audit | reported | 10/10 shards complete (incl. copy-divergence), 13 raw → 6 new drift |
| 4 retro/done-ticket | pr-opened | 10 eligible: 2 knowledge PRs (#801, #802), 8 direct deletes; 40 checkout-bearing done tickets deferred as retirement debt |
| 5 cleanup-orphan-markers | no-op | no processed-marker directories remain |
| 6 disposition | pr-opened | 7 proposal PRs, 2 draft tickets, 4 drafts given evidence, 10 findings already tracked |

Findings: 34 merged (F-01..F-34). Routing:
- **Knowledge PRs (Phase 4)**: #801 (dev/code: PR review threads that merge unanswered; codebase: five parked adjacent bugs), #802 (sync: the four commit subjects Coga writes for itself).
- **Proposal PRs (pr-required, human merges)**: #803 codebase context — honored `include` allowlist, init-only managed-skill install (F-07, F-08); #804 recurring templates skill-update/autoclose-merged/blocker-reminders (F-09, F-10, F-12, F-13); #805 small drifts in recurring, architecture, marketing/map contexts + CLI audit doc (F-11, F-32, F-14, F-30); #806 sync context — admission barrier, third recurring-error producer, guard callers, `coga create` (F-19, F-29, F-33, F-34); #807 packaged coga/cli context → derived-operator model (F-16); #808 docs/with-review freezes `code/address-pr-comments` (F-17); #809 orient ticket + agent guide + config string (F-18).
- **Draft tickets created**: `dream-2026-w38-extract-backlog-4-findings-phase-4` (carrier for F-01..F-04 — every source ticket is retirement debt, so Phase 4 could not consume them; full paragraphs in its Context); `document-the-remedy-for-a-bloated-blackboard-sibli` (F-27, draft paragraph for the architecture context in its Context).
- **Already tracked — evidence appended to the owning draft's body**: F-20 → `correct-the-v2-known-stale-surfaces-table-and-rout`; F-22 → `the-v2-parking-area-premise-check-has-four-holes`; F-25 → `ticket-relationships-and-ownership-have-no-mechani`; F-26 → `define-the-split-a-ticket-mechanic-shared-by-code`.
- **Already tracked by an open PR — no action**: F-05 and F-31 → #795; F-21 → #793; F-23 → #789; F-24 → #797; F-28 → #799.

human-needed:
1. **F-06 / `test_packaging` red on main**: `coga/contexts/coga/codebase/SKILL.md` diverged from its packaged twin via `74692b23 Sync coga state`; merge #796 (carries the matching packaged copy) or revert the live hunks at ~L33 and ~L188-207. Every open PR touching that context (#787, #789, #790, #795, #796, #801, #803) rebases over whichever lands first.
2. **F-15 clarity re-prune landed on `main` unreviewed** as `7966c2a2 Sync coga state` (83 files, −13,876 lines; restores the `include` allowlist and prunes `coga/skills/clarity/` to SKILL.md, LICENSE, references/, two scripts — `coga skill status --check` now reports it `up-to-date`). Dream's attempt to revert and re-land it as a PR was refused by the session's push permission. Review it in place (`git show --stat 7966c2a2`) or revert it.
3. Lifecycle decisions Dream does not make: `autofix/stop-one-failing-ticket-py-from-starving-the-rest` is still `active` though its fix shipped (F-10); draft `implement-the-include-allowlist-that-url-skill-upd` is discharged by #776 (F-07); `v2/skill-for-split-into-sibling-ticket-discipline` overlaps `define-the-split-a-ticket-mechanic-shared-by-code` (F-26).
4. validate-drift: 15 `stuck-in-progress` (86h–1318h idle) and 9 `unfrozen-workflow` hand-authored tickets need an owner decision; 4 `unsynthesized-draft-blackboard` errors (`v2/autotrigger-ticket-type`, `v2/measure-relay-prompt-scope-and-agent-precision`, `v2/split-context-to-doc-user-accessible-and-editable`, `v2/use-worktree-when-starting-a-dev-task`) and 1 `large-blackboard` (`reconcile-recurring-wrapper-tty-admission-guidance`, 54 KiB) were classified pr-proposal but need the author's judgment, not a Dream rewrite. The `broken-skill` error on `recurring/digest` is gone with that period ticket's deletion.
5. Pre-existing dirty ticket in the primary checkout (`define-the-api-equivalent-cost-proxy-and-price-tab`, published launch claim) blocks every catch-all sync; reconcile per the F-24 recipe or finish that ticket's session.

Deferred retirement debt (done, real `## Dev` checkout; run `coga retire <slug>`): `a-slack-repo-without-important-webhook-can-abort-t`, `activation-does-not-resolve-step-1-s-assignee-role`, `allow-description-and-owner-on-create`, `autoclose-should-name-the-retire-follow-up`, `bumppy-requires-exactly-two-agents`, `carry-adjacent-bugs-out-of-a-blackboard-before-ret`, `cleanup/add-a-debug-mode-to-init-for-vendoring-from-source`, `cleanup/detect-the-current-git-branch-instead-of-hard-codi`, `dream-phases-2-3-cannot-complete-scan-subagents-re`, `dream-reconciliation-must-count-distinct-shard-ids`, `fix-the-autofix-analyst`, `give-a-ticket-s-superseded-design-one-documented-h`, `launch-activates-before-preflight`, `launch-ignores-the-recorded-worktree-stranding-bla`, `live-and-packaged-twin-pairs-are-edited-together-b`, `megalaunch-activates-picks-before-preflight`, `megalaunch-only-shows-one-page`, `migrate-recurring-templates-to-ticket-py-shims-and`, `move-cogacontext-to-roodoc-so-its-easier-for-human`, `no-comms-writing-skill-the-process-is-smeared-thro`, `no-skill-exists-for-the-cold-evaluator-review-of-a`, `packaged-repos-ship-recurring-templates-without-th`, `put-build-back`, `read-the-recurring-serviced-period-from-the-log-dr`, `reconcile-recurring-wrapper-tty-admission-guidance`, `recurring-last-serviced-period-compares-as-a-strin`, `recurring-recipe-question`, `refuse-recurring-runs-from-a-non-control-branch`, `remov-digest-in-recurring`, `remove-coga-build-and-project`, `remove-legacy-config-compatibility-shims`, `retire-never-removes-a-worktree-that-ran-the-tests`, `review-slack-channels`, `rewrite-coga-base-prompt-and-agent-mode-block`, `select-session-conduct-instead-of-appending-a-cont`, `service-recurring-from-a-temp-control-worktree-ins`, `simplify-ticket-format`, `stop-syncing-task-state-onto-the-feature-branch`, `unblock-rewind`, `validate-drift-classifier-misses-17-emitted-kinds`.
