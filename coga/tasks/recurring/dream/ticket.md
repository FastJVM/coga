---
title: Dream
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: be5cee77-6481-458f-a553-466aadeadb42
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
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

The recipe's three buckets are inputs to Phase 6, not results. `direct-fix`
repairs land in the safe-repair pass; Phase 6 routes `pr-proposal` issues to
proposal PRs or covering tickets; `human-needed` issues are routed to hygiene
draft tickets, one per validator `kind`, by the Phase 6 rule below. The
`## Dream Skill: validate-drift` section is deleted with this task at the next firing, so an
issue left only there was never reported.

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
Phase 4 reads that section when batching knowledge PRs. Keep each `extract`
finding's `source:` line, each `gap` finding's `owner:` line, and each
`premise` finding's `target:`, `question:`, and `owner:` lines through the
merge — Phase 6 routes on them. The `premise` class is this scan's standing
re-validation of the parking area, where `coga/tasks/v2/README.md` exists:
the skill asks that contract's four premise questions of every parked draft
it owns, so a draft that sits there is re-checked every run instead of only
when a human pulls it forward.

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

Before delegation, create a unique writable temporary run directory outside
every checkout. Copy the live Retro inputs into its read-only `evidence/`
snapshot: every eligible resolved task artifact (the bare task
Markdown file or the complete task directory, including sibling attachments),
the repo-global `coga/log.md`, local contexts and skills, and this Dream task's
current `## Findings`. Use ordinary copies, not symlinks back to Dream's
mutable checkout. Create a writable `progress.md` alongside `evidence/`, not
inside it. Pass the snapshot path and Dream's absolute repo root to the
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
theme). It first appends a `start` line to the writable `progress.md`, before
any remote mutation, then records each classified ticket, opened PR, and landed
direct delete, and finally `complete`. Read that file when the subagent returns
or terminates, before removing any paths. A missing `pr` or `deleted` receipt
means the outcome is unknown: the remote mutation may have succeeded before
the worker stopped. Follow the skill's reconciliation checks against the fresh
remote control branch and branch/PR state before retrying. Without `complete`,
report the phase as `partial` with the file's contents and preserve the run
directory and isolated checkout for recovery; a final message alone does not
establish completion.

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
directory. After recording the verified outcome on Dream's blackboard, delete
the temporary run directory (snapshot and progress file) too. Agent-native
cleanup is not
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

Every Phase 1 `pr-proposal` or `human-needed` issue and every Phase 2 and Phase 3
finding gets a durable home. The `## Findings` and
`## Dream Skill: validate-drift` blackboard sections are an index of what Dream saw, not where decisions go to
rest — this task is retired and its blackboard with it. A finding whose only
record is this blackboard was lost, not reported.

**Filing rules for every draft ticket Dream creates.** File at the top level:
`coga create "<title>" ...` with no `/` in the title; put paths in the
description. Dream never files
under `coga/tasks/v2/` — that directory is the human's parking decision, made
after reading a draft, and a Dream draft parked there by construction decays
unread. The `--description` names the Dream run (period, phase, shard) and the
target path or validator `kind`, so a later run can find the owner by grep.
Before any `coga create`, search for an existing owner (the per-class rules say
what to search for): an open ticket — any status but `done` or `canceled` —
whose title or body already covers the finding is the owner. Create nothing for
an owned finding; report it as "already ticketed as `<slug>`" in the run
summary. Dream does not edit another ticket's body or blackboard to add
members or evidence.

Route each Phase 1 `human-needed` issue by validator `kind`, one draft ticket
per **systematic class**, never one per issue:

- Machine-local kinds — `missing-user`, `unset-secret-env`, `slack-*`,
  `github-*` — describe the operator's environment, not the committed corpus.
  They get no ticket: list them in the run summary and the Slack line.
  A config-only `unresolvable-step-assignee` issue belongs here too when its
  message and the effective agent configuration show that the remedy is a
  local `peer` setting. Do not classify it as shared drift merely because it
  names a committed ticket. A correction to a frozen role or shared workflow
  still needs the repo-state route below.
- Group the remaining `human-needed` issues that need a committed-state
  decision by `kind`. For each kind, search all statuses under `coga/tasks/`
  and the effective contexts for the exact tag line `validate-drift: <kind>`;
  also read any context decision linked from a matched completed owner.
  First check recorded decisions: a context carrying the tag must state the
  decision, rationale, and conditions or members it covers. Report current
  issues within that scope as already decided, citing the context and count;
  do not refile them just because the validator still emits the warning.
  Issues outside that scope still need an owner. A completed ticket alone is
  not a disposition, and a decision about one subset does not waive the kind.
  For the remaining issues, check for an open owner by tag or by matching its
  title and description under the filing rules above. If one covers them,
  create nothing, and report the class in the run summary as
  "already ticketed as `<slug>`" with this run's member count and the slugs
  that are new since the owner was filed. If none does, create one draft:
  `coga create "validate-drift: <kind> — <one-line class description>"
  --workflow brief-for-human --description "<...>"` whose description carries
  the tag line `validate-drift: <kind>` verbatim, the recipe's remediation
  text, this run's member slugs with their messages, and the instruction that
  `coga validate --json` is the live member list. Membership is not copied
  from run to run: the ticket is the durable record that the class needs a
  decision, the validator is the source of truth for which tickets are in it,
  and the owner ticket stays open until the class is empty or the decision is
  recorded in a context. Include that completion rule in the description:
  before closing with accepted warnings remaining, preserve the same tag,
  decision, rationale, and scope in the appropriate context, so the decision
  survives the owner's retirement and later runs can apply it. `brief-for-human`
  is the workflow because the
  decision is the human's; Dream does not change lifecycle, workflow, or
  assignee state.

**Proposal ownership.** Before opening a proposal below, check for an open
ticket owning the same target and fact, then inspect all open PRs, including
earlier runs' Phase 6 proposals (also match the source slug for an `extract`).
Report an existing owner instead of opening another proposal. Reuse a PR only
when its diff or description actually carries the finding; report its link
and create no duplicate. A shared target path alone is not coverage. If an
overlapping PR does not carry the finding, file or reuse a scoped
`code/with-review` draft under the filing rules above. Its description must
preserve the finding, source evidence, target, and overlapping PR link so it
can be handled after that PR's review. An overlap noted only on this run's
blackboard is not a disposition.

**Phase 1 PR proposals.** Read every issue in the `PR Proposal` bucket of
`## Dream Skill: validate-drift`, including its validator `kind`, target path,
message, and suggested remediation. Apply the proposal-ownership rule above to
each issue before opening anything: report the covering ticket or PR, or
preserve uncovered overlap in a scoped draft. For an unowned issue with an
evidenced correction, open a proposal PR applying that correction to the named
reference, template, or other contract. Group only coherent fixes, keep shipped
live/packaged twins in sync, and include the Dream period,
`validate-drift: <kind>`, affected paths, original messages, and validation results.
Validate each affected task with `coga validate --task <slug> --json`; for
template or shared-contract fixes, compare repo validation before and after
and account for any remaining issues. If the correction needs a human choice,
file or reuse a scoped `code/with-review` draft preserving the issue,
remediation, and specific decision needed under the filing rules above.
These are `pr-required` proposals: never apply them directly on `main` or
auto-merge them. List each issue's PR or owner draft in the run summary; an
entry left only in the recipe's disposable blackboard bucket is unfinished.

Route each Phase 2 and Phase 3 finding by class:

- `extract` — by the finding's `source:` line, which the knowledge-scan shard
  records from the source ticket's `status:` and `## Dev` section:
  - `done` — already handled by Phase 4 (a knowledge PR, or — when the ticket
    carried nothing durable — a direct `coga delete`). If Phase 4 skipped it
    because an open PR already edits that ticket, it is in flight; report the
    PR and do nothing.
  - `done+checkout` — the source ticket is retirement debt, deliberately left
    on disk so the human-typed `coga retire <slug>` stays valid. That ticket
    is the durable artifact and retirement is its consumer: `coga retire`
    runs Retro over the ticket and extracts what this finding saw. Open no PR
    and file no carrier ticket — a second copy decays while the source stays
    fresh. Instead, list the finding under the run summary's retirement-debt
    section with its slug, area, and one-line summary, so the human can order
    retirements by the knowledge they unlock. This is a standing condition
    while the retirement backlog exists; the same findings recur until the
    tickets are retired, and reporting them again each run is correct.
  - `canceled` — Retro refuses a ticket that is not `done`, so nothing else
    will ever consume it. Apply the proposal-ownership check above before
    opening anything. Open a proposal PR that edits the target context or
    skill with the durable fact when no existing proposal or overlap draft
    owns it, citing the source ticket by slug. The PR is `pr-required` like
    `stale`, and Dream leaves the canceled ticket on disk.
- `stale` — open a proposal PR that edits the named context or skill to match
  reality. The PR is `pr-required`: a human reviews and merges it; Dream never
  auto-merges and never edits a context or skill directly on `main`. Apply the
  proposal-ownership rule to existing PRs, including those opened by Phase 4.
- `drift` — open a proposal PR that fixes the named contract: correct the doc
  to match code, repoint or remove a dead reference, or resync a diverged
  packaged/live copy pair. Like `stale`, the PR is `pr-required` and Dream
  never auto-merges. Apply the same proposal-ownership rule.
- `gap` — reconcile against open tickets before creating anything. The shard
  already searched its own area and wrote `owner: <slug>` when it found one;
  Phase 6 repeats the search with the whole corpus in view, because a shard
  sees one area and the owner is often filed elsewhere. Grep `coga/tasks/`
  (bare `.md` files and every `ticket.md`, titles and bodies) for the
  finding's target path and two or three of its distinctive terms, read each
  hit's title and description, and treat an open ticket that covers the same
  gap as its owner — including a draft an earlier Dream run filed and one
  this run created moments ago for a duplicate finding from another shard.
  A `done` ticket is evidence to inspect, not an open owner. Verify its
  promised change in the current corpus or an open PR before reporting the
  gap as covered, and cite that evidence. If instead the ticket holds
  unextracted durable knowledge, reclassify as `extract` with `source:` and
  `area:` and use that route. If the promised change remains missing, keep
  the `gap` and find an open owner or file it; `status: done` alone must not
  suppress follow-up. For an owned gap, create nothing
  and report "already ticketed as `<slug>`". Otherwise create a tracked
  draft ticket with `coga create "<title>" --workflow code/with-review`
  under the filing rules above. A gap needs human design judgment about
  whether and how to add the context, skill, or workflow; a draft ticket is
  where that judgment happens, and unlike a blackboard note it survives this
  task's retirement.
- `premise` — a parked draft under `coga/tasks/v2/` failed one of the
  README's premise questions. The verdict is the author's, never Dream's:
  Dream does not cancel, close, narrow, or edit the draft, and it does not
  file under `v2/`. Reconcile first, as for `gap`: the shard wrote
  `owner: <slug>` when an open ticket already adjudicates the draft, and Phase
  6 repeats that search with the whole corpus in view — grep `coga/tasks/`
  for the draft's exact slug and read each open hit's title and description,
  including an adjudication draft an earlier run filed. For an owned draft,
  create nothing and report "already ticketed as `<slug>`". Collect every
  remaining `premise` finding of this run into **one** adjudication draft —
  never one ticket per draft —
  `coga create "Premise check <period>: <N> parked drafts need a verdict"
  --workflow brief-for-human --description "<...>"` under the filing rules
  above, whose description lists each draft by path-qualified slug with the
  question it failed and the shard's evidence, names the README's verdict
  vocabulary (cancel with evidence, including already-delivered work; narrow;
  rewrite), and repeats the README's guard that a green `coga validate` is never a reason
  to rule a draft dead. `brief-for-human` is the workflow because every
  verdict is the human's. A draft ruled on in that ticket stops appearing
  when its verdict lands; a draft the human leaves open is owned by that
  ticket until it closes, and reported as already ticketed meanwhile.

Then append one top-level `## Dream Run Summary` section to this task's
blackboard: the generation time, a phase result table using the vocabulary
`no-op`, `reported`, `partial`, `proposed`, `direct-fixed`, `pr-opened`,
`human-needed`, the finding counts with one-line summaries, links to every PR
opened and draft ticket created (the run's premise adjudication draft
included, with its member count), every `already ticketed as` line, the
already-decided classes with their context citations, reused proposal PRs,
the retirement-debt list with the `extract` findings each retirement unlocks, the
machine-local validator issues, and any `human-needed` decisions or review
gates. Keep it short enough for a human to scan.

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

Generated: 2026-09-21T18:24:52+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python3 -m coga.validate --json --fix`
Task: `recurring/dream`

Result: 50 issue(s): 0 direct fix, 5 PR proposal, 45 human-needed.

### PR Proposal

- `clean-up-all-the-working-trees`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Ticket authoring notes, ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.
- `reconcile-recurring-wrapper-tty-admission-guidance`: `large-blackboard` (warn) - blackboard region is 54.0 KiB (warning threshold 32.0 KiB); it is included in launch prompts. Consider summarizing old notes.
  Remediation: Propose a reviewed blackboard condensation that preserves current decisions and blockers before removing detail.
- `v2/autotrigger-ticket-type`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.
- `v2/measure-relay-prompt-scope-and-agent-precision`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (non-placeholder blackboard is 4213 characters); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.
- `v2/use-worktree-when-starting-a-dev-task`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.

### Human Needed

- `add-an-agent-picker-for-recurring`: `stuck-in-progress` (warn) - in_progress but idle for 253.6h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `adjudicate-the-eight-premise-dead-v2-drafts`: `stuck-in-progress` (warn) - in_progress but idle for 91.8h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `clean-up-all-the-working-trees`: `unfrozen-workflow` (warn) - workflow 'maintenance/with-approval' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `cleanup/publish-coga-1-0-to-pypi`: `stuck-in-progress` (warn) - in_progress but idle for 136.2h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `define-the-api-equivalent-cost-proxy-and-price-tab`: `stuck-in-progress` (warn) - in_progress but idle for 145.4h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `define-the-split-a-ticket-mechanic-shared-by-code`: `stuck-in-progress` (warn) - in_progress but idle for 108.9h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `dream-should-be-able-to-use-codex-instead-of-claud`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `fix-git-sync-failure`: `unfrozen-workflow` (warn) - workflow 'code/with-self-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `invert-command-line-to-have-actions-passed-last-or`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `marketing/build-the-launch-plan`: `stuck-in-progress` (warn) - in_progress but idle for 406.5h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `marketing/fix-installer`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `marketing/phase-0-audit`: `stuck-in-progress` (warn) - in_progress but idle for 263.5h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `marketing/plan/collect-public-examples-for-the-launch`: `unfrozen-workflow` (warn) - workflow 'draft-for-human' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `marketing/plan/write-the-pitch-and-narrative`: `unfrozen-workflow` (warn) - workflow 'draft-for-human' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `parse-agents-rejects-cogalocaltoml`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `phase-0-audit-is-complete-per-the-plan-but-still-i`: `stuck-in-progress` (warn) - in_progress but idle for 117.4h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `recurring-sweep-wedges-on-the-ticket-py-it-copies`: `stuck-in-progress` (warn) - in_progress but idle for 265.1h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `redo-documentation-dir-and-merge-it-with-context-b`: `stuck-in-progress` (warn) - in_progress but idle for 303.8h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `some-recurring-tasks-are-not-launched-correctly-to`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `stop-recurring-on-inactive-repo`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/add-subproject`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/autoroute-agent-based-on-remaining-usage`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
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
- `v2/create-vault-and-service-account-for-mid-trust-sec`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/create-vault6-and-service-account-for-high-trust-s`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/docs-and-contt-block-should-be-merged`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/document-contexts-as-prompt-payload-not-tags-princ`: `stuck-in-progress` (warn) - in_progress but idle for 1485.2h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `v2/fix-windows-cli-import-crash`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/generic-lib-to-use-e-g-patent-models`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/in-general-relay-files-should-be-easier-to-access`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/manage-security-and-pii`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/model-selector`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/pick-model-on-workflow-to-save-on-cost`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/project-manager-split-spec-in-tickets-block`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/remote-stale-command-line-toosl`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/script-mode-to-activate`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/simplify-command-lines`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/sync-support-files-and-bare-ticket-authoring`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/update-all-doesn-t-copy-workflow-correctly-to-atta`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `v2/why-ai-asks-me-to-bump-instead-of-doing-it`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `where-have-code-review-disappeared`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.

## Run notes (2026-W39)

- Period: 2026-W39 (log line 5987: created recurring/dream for 2026-W39). Repo root `/home/n/Code/claude/coga`, control branch `main`, remote `origin` = FastJVM/coga.
- Phase 1 validate-drift: **reported** — 50 issues (0 direct-fix, 5 pr-proposal, 45 human-needed). Kinds: `unsynthesized-draft-blackboard` ×4 + `large-blackboard` ×1 (pr-proposal); `stuck-in-progress` ×11, `unfrozen-workflow` ×12, `empty-description` ×22 (human-needed). Recipe committed its blackboard append as `76785989b Sync coga state`.
- Phase 2 knowledge scan: corpus = 234 tickets (2,521,468 B) + 81 knowledge files (914,560 B; seven managed `google-agents-cli-*` trees excluded per `managed-skills.toml`). Partitioned into 34 area shards (marketing 2, skills 2, recurring 8, sync-launch 4, dev-code 5, ticket-format 4, codebase 5, architecture 4); oversized contexts owned ranged (architecture@25000, sync@25000, recurring@25000, codebase@20000). Scan dir: `/tmp/claude-1000/-home-n-Code-claude-coga-coga/f8c5fdbd-9dee-476f-ae5e-7b988a98d033/scratchpad/dream-w39-knowledge.k1b67C`.

## Findings

Merged from the Phase 2 knowledge scan (34 shards, 80 blocks on disk, 73 after de-duplication) — Phase 3 contract-audit `drift` findings are appended below under their own subheading. Per-finding numbers `F<n>` are this run's handles. `extract` findings are grouped by `source:` then area.

### Class: extract

#### F1. Owner decision to park `coga/tasks/v2/` off the status path, and the inventory of surfaces that assume it is live

- shard: ks-23
- class: extract
- target: interview-the-owner-on-the-17-title-only-v2-stubs
- area: roadmap
- source: canceled

The ticket was canceled at `review-design` on 2026-09-20 with a recorded owner decision that is not written anywhere else: "it's a v2 but we're far from v2 at this point" — the 17 title-only stubs (and #10 `pick-model-on-workflow-to-save-on-cost`, which the owner would also have canceled) are not to be adjudicated one by one; the intended follow-up is to park `coga/tasks/v2/` somewhere `coga status` does not reach, and that follow-up is "not yet a ticket". `coga/contexts/coga/roadmap/SKILL.md:39-63` still describes v2 as the durable parking area with `coga status v2` as the authoritative list, so the direction change lives only in this canceled ticket. The ticket's `## Canceled at review-design` section also carries the verified migration inventory the future ticket needs: `tasks.list_tasks` skips `_`-prefixed directories (`src/coga/tasks.py:163,227`), so `git mv coga/tasks/v2 coga/tasks/_v2` hides all 81 in one commit, but `coga/roadmap` "Deferred work", `coga/tasks/v2/README.md`, `coga create "v2/<title>"` as the only supported bare-capture spelling (`create.py`, `ticket.py`, `validate.py`), Dream's weekly premise pass, `coga/architecture`, `coga/codebase`, `current-direction`, and `test_create`/`test_validate`/`test_megalaunch`/`test_ticket` all assume the directory is live, and the in_progress siblings `adjudicate-the-eight-premise-dead-v2-drafts` and `correct-the-v2-known-stale-surfaces-table-and-rout` will need canceling or re-scoping alongside. Two counting gotchas from the same triage family are worth one sentence beside it: `coga status v2 --all` reports 81 because discovery recurses into `cleanup-core-commands/` and excludes `README.md` indexes (`src/coga/tasks.py:125`), while `ls coga/tasks/v2/*.md` returns 76. Record the decision and inventory under the roadmap's "Deferred work" (or `coga/tasks/v2/README.md`) so the follow-up ticket can be written from a file rather than from a canceled ticket's blackboard.

#### F2. A done ticket's recorded fix can be half-applied on main — verify the exact token, not the claim

- shard: ks-05
- class: extract
- target: test-recurring-create-is-silent-fixture-fix-is-hal
- area: codebase / retro
- source: done

`coga/tasks/test-recurring-create-is-silent-fixture-fix-is-hal.md` is `status: done` with no `## Dev` checkout (its blackboard says "No branch, worktree, or PR created"; the fix merged separately as `589e141a`, PR #780). Its durable fact is a failure mode neither `coga/contexts/coga/codebase/SKILL.md` nor `retro/done-ticket` carries: a done ticket's `## Verification` recorded a fix (`give-a-ticket-s-superseded-design-one-documented-h`, commit `4012c5e9`) that reached `main` only half-applied (`c4482fae` added `force_directory=True` and a comment but left `file_form=True` on the `TaskRef`), so four later done tickets each re-diagnosed `test_recurring_create_is_silent` as "pre-existing, worth its own ticket" and none filed one — the claimed fix made every rediscovery look new. The codebase context's "Tests must not pin to live dogfooded state" bullet covers a *different* four-times-rediscovered test, and the retro skill's "Unresolved adjacent bugs" section says `status: done` does not prove adjacent bugs are fixed, but nothing says a done ticket's own fix claim is not proof either. Proposed one-bullet addition to the codebase context's testing gotchas (or the retro skill's adjacent-bugs section): when a failing test is recorded as "pre-existing" and some ticket claims to have fixed it, do not trust the claim — confirm what reached `main` with `git log -S'<exact token>' -- <test file>` and the ticket's prescribed absolute-`PYTHONPATH` invocation, and record any durable note as "half-applied, not absent", because that distinction is what stopped four readers from finishing it. The only durable record today is the fixture comment in `tests/test_notification_messages.py` (line 371 area) and the `589e141a` commit message; once Retro deletes this ticket the pattern is otherwise gone.

#### F3. Branch sweep never clears a branch whose review follow-up was rebased in a scratch checkout

- shard: ks-07
- class: extract
- target: recurring/branch-sweep
- area: coga/recurring (branch-sweep)
- source: done

The done period ticket `coga/tasks/recurring/branch-sweep/ticket.md` (no `## Dev`) recorded on 2026-09-21 a shape the sweep skill does not name: six branches with a **merged** PR — `branch-sweep-landed` (#811), `dream-w38-extract-backlog` (#812), `recurring-missing-workflow` (#814), `sweep-abandoned-record` (#813), `title-only-validator` (#815), `v2-premise-holes` (#819) — all reported "has merged PR #N at <oid>, but the ref carries commits touching <source paths>" and left in place, local and remote. Verified for #812: the recorded worktree's local ref is `1d23cb4c` (`18091d93` + `1d23cb4c`, per its reflog a rebase onto `9f0c30d8` on 2026-09-15), while the merged head `35b9b609` carries `8714fda3` + `a2659a86` — the same two commits re-applied under new SHAs — plus the follow-up commit. `git merge-base --is-ancestor 1d23cb4c 35b9b609` is false. The cause is the review step's follow-up convention: the source tickets' blackboards (`dream-2026-w38-extract-backlog-4-findings-phase-4`, `branch-sweep-strands-squash-merged-branches-whose`, `recurring-sweep-aborts-and-orphans-a-deleted-done`, `title-only-tickets-have-no-convention-and-no-valid`) all say "Addressed the requested comments on PR #N in `/tmp/coga-review-prN-20260916`" — a scratch checkout that rebased onto fresh `main` before pushing, so the recorded worktree's branch keeps a dead pre-rebase lineage whose commits touch real source paths. `coga/skills/coga/branch-sweep/sweep/SKILL.md` §4 admits only the exact tip, a *lagging* ref (ancestor of the merged head) and a ref that walked *past* it through state commits; it says nothing about the rebased-copy shape, and the earlier stranding ticket's description named that "dead lineage" shape as one "a fix must handle" while its design admitted only lag. `src/coga/branchsweep.py` / `branchcleanup.py` contain no `git cherry` / patch-id equivalence check (grep). Because the merged PR vouches for the head name but the local commits are patch-equivalent rather than ancestors, these refs will be reported every week until a human runs `git branch -D` (and `git push origin --delete`) by hand. No open ticket covers it (`clean-up-all-the-working-trees` explicitly excludes branch deletion). Record in the branch-sweep skill's §4 (live and packaged twins): a ref whose commits were rebased and re-pushed from another checkout is refused by design and needs a manual `git branch -D` after confirming the merged head carries the same patches (`git cherry <merged-head> <tip>` all `-`), or extend the verdict with a patch-id check; and add to `coga/skills/code/address-pr-comments/SKILL.md` §1 ("Remain on the recorded branch for the entire assist") that a follow-up pushed from a scratch checkout must not rebase, or must fast-forward the recorded worktree's branch to the pushed OID afterwards, otherwise the weekly sweep strands it.

#### F4. Fan-out follow-ups that each rewrite one shared context bullet conflict pairwise

- shard: ks-19
- class: extract
- target: triage-five-review-comments-that-merged-unanswered
- area: dev/code
- source: done

`triage-five-review-comments-that-merged-unanswered` (status: done, no `## Dev` section) spun out five `code/with-review` follow-ups and left the `coga/codebase` "Five bot review threads merged unanswered" bullet untouched because "all five PRs rewrite it (both the live context and the packaged `bootstrap` twin)". Its report step then measured the consequence with `git merge-tree` on 2026-09-20: each of PRs 835/838/840/842/844 merges cleanly onto `origin/main` alone, but every pair conflicts on both copies of that bullet (and PR 840 + PR 844 also conflict in `src/coga/compose.py`), so whichever merges first forces the other four to rebase and reconcile their bullet rewrite. The reusable lesson is not in `dev/code` ("Multi-ticket PRs" covers one PR for several tickets, not several PRs for one shared context passage) nor in the `coga/codebase` gotchas (grep for "merge-tree", "same bullet", "coordinate" found nothing): when a triage or audit fans out N follow-ups that must each update the same context passage and its packaged twin, either the spawning ticket owns that passage's rewrite in one PR before the follow-ups launch, or the follow-ups are serialized, or each follow-up adds its own sub-bullet rather than rewriting the shared one — otherwise the byte-identical live/packaged twin rule doubles every conflict. Suggested home: a sentence under `dev/code` "Multi-ticket PRs", or the `coga/codebase` gotcha list.

#### F5. Blocker reminders are blind to a paused recurring period task that still carries an unresolved ask

- shard: ks-12
- class: extract
- target: recurring/blocker-reminders
- area: recurring
- source: done

The done period ticket `coga/tasks/recurring/blocker-reminders/ticket.md` (no `## Dev` section, so no checkout) carries a verified operational blind spot under "What this scan does not cover": `run_blocker_reminders_recipe` filters on `status: blocked` and nothing else, but a recurring *agent* period task that calls `coga block` never stays `blocked` — the sweep rewrites it `blocked → paused` when the launch returns unfinished (`_stop_if_unfinished_after_launch` in `src/coga/recurring_runner.py` returns early only for a script-recorded block), so the unresolved ask sits on a `paused` ticket that fails the reminder filter and nobody is ever reminded. Evidence in the ticket: `recurring/resolve-conflicts` recorded a TTY-admission blocker on 2026-08-13, was paused the same minute, blocked and paused again on 2026-08-14, and the ask went unanswered until a human picked it with `coga megalaunch` on 2026-08-17. The ticket also records the design decision not to widen the filter (`paused` also means "a human deliberately parked this"). Neither knowledge surface carries this: `coga/skills/coga/blockers/remind/SKILL.md` restates the filter ("scans tasks whose frontmatter says `status: blocked`") with no caveat, and the `coga/recurring` context's "A scheduled agent run must reach `done` in one launch" bullet (lines ~773-786) says a `coga block` in a scheduled agent run is paused and "cannot use ordinary `bump` / `unblock` from that state" but never says the reminder sweep will not surface that ask (`grep -n "remind" coga/contexts/coga/recurring/SKILL.md` finds only unrelated hits at 604/937/1015). The template body `coga/recurring/blocker-reminders/ticket.md` does carry the same paragraph, so the fact is durable as a run prompt, but not as knowledge an operator reading the skill or the context would meet. Proposed home: one sentence in `coga/blockers/remind` ("a recurring agent period task paused after `coga block` is not `blocked` and is never reminded; check `paused` periods by hand") and a matching clause in the recurring context's scheduled-agent-run bullet. No open ticket owns widening the filter (grep of `coga/tasks/` for `blocker-reminders` + `paused` finds only historical/unrelated hits).

#### F6. `coga mark done` is allowed only from `active`/`in_progress`; drafts can reach a terminal state only via `mark canceled`

- shard: ks-24
- class: extract
- target: the-v2-parking-area-premise-check-has-four-holes
- area: architecture (lifecycle / "Two state machines per ticket")
- source: done+checkout

The ticket's peer review found that its first-draft README recipe (`coga mark done v2/<slug> --message "delivered by …"`) exits 2 on a `status: draft` ticket, and the implementation was changed to `mark canceled … --message "already delivered by <evidence>"` because cancel is "a transition available to drafts, including workflow-less ones". The code confirms the asymmetry: `src/coga/commands/mark.py` has `_DONE_FROM = {"active", "in_progress"}`, `_PAUSED_FROM = {"active", "in_progress"}`, `_ACTIVE_FROM = {"draft", "paused"}`, and `_CANCELED_FROM = set(CANCELABLE_STATUSES)`. `coga/contexts/coga/architecture/SKILL.md` ("Two state machines per ticket", ~L563-585) documents that `mark canceled` "accepts every non-terminal status" and that `mark active` is allowed from `draft`/`paused`, but never states the `done`/`paused` source-set restriction — a grep of `coga/contexts/` and `coga/tasks/v2/README.md` for the rule returns nothing. Add one sentence there (and the packaged twin): `mark done` and `mark paused` are accepted only from `active` or `in_progress` (exit 2 otherwise), so a `draft`, `paused`, or `blocked` ticket whose outcome already exists must be either activated first or canceled with delivery evidence; the v2 README's "already delivered" verdict relies on exactly this.

#### F7. api-first: a "No" API answer must be dated, source-linked, hedged, and carry a re-check trigger

- shard: ks-03
- class: extract
- target: record-dochub-s-why-not-the-api-answer-that-browse
- area: browser
- source: done+checkout

The done ticket (`## Dev` has real `branch: dochub-api-answer`, `worktree: /home/n/Code/claude/coga-dochub-api-answer`, `pr: #822`) learned a general api-first lesson that only landed in the site-specific skill, not in the governing context. Its `## Context` warned that "an unverified 'no API' note would be worse than the current silence"; its peer review then had to downgrade the implement step's categorical "No" because "an old reply plus unsuccessful documentation searches also cannot prove that no API exists" — the durable form became "no usable public API found for *this workflow*" with a date, the exact sources checked, the conflicting marketing claim acknowledged, and explicit re-check triggers (different workflow, new API evidence/access, check older than a year). `coga/contexts/browser/api-first/SKILL.md` (read whole) still phrases the "No" branch as only "link or note the docs page checked": it never asks for a date, a workflow-scoped rather than site-wide claim, the finding-not-proof hedge, or a re-check condition, and it does not tell a later ticket that an existing dated check in a site skill (as `coga/skills/browser/dochub/SKILL.md` now carries under "Why the browser, not the API") may be cited instead of redoing the search. Proposed addition to the `## Rule` "If no" bullet and `## How to apply` of `browser/api-first` (and its packaged twin under `src/coga/resources/templates/coga/bootstrap/contexts/browser/api-first/SKILL.md` if one exists): a "No" answer is scoped to the workflow, dated, lists the sources checked, names any conflicting claim, and states when to re-check; a site skill under `coga/skills/browser/<site>/` is the durable home for that answer and later tickets cite it rather than repeating the search.

#### F8. `coga open-pr` cannot request GitHub reviewers — the owner adds them by hand

- shard: ks-18
- class: extract
- target: allow-description-and-owner-on-create
- area: code/open-pr
- source: done+checkout

The done ticket `allow-description-and-owner-on-create` (status done; `## Dev` records `branch: create-description-owner`, a real worktree, and merged PR #783) had a reviewer other than the owner and worked around a limit that no skill states: "`coga open-pr` can't request GitHub reviewers, so the ticket owner (zach) adds him on GitHub once the PR opens; the `review` gate stays with the owner." Verified on current `main`: `src/coga/open_pr.py` builds `gh pr create` with title/body/base/head only and never passes `--reviewer` (the word appears once, in a comment), and `coga/skills/code/open-pr/SKILL.md` describes the command's push/open/record contract and its refusals but says nothing about reviewer assignment, so an agent whose ticket names a reviewer has no rule for what to do. Add one sentence to `code/open-pr` under step 2 (or the "What this skill does NOT do" list): the recipe never requests reviewers; a ticket-named reviewer is added on GitHub by the owner after `pr:` is recorded, and the `review` step stays with the owner. This is retirement debt (`done+checkout`), so Phase 6 lists it rather than Retro consuming it.

#### F9. `typer.Exit` is an `Exception` subclass, so a bare `except Exception` turns fail-loud into fail-quiet

- shard: ks-27
- class: extract
- target: review-slack-channels
- area: codebase
- source: done+checkout

The done ticket `coga/tasks/review-slack-channels.md` (`## Dev` has a real `branch: route-important-failures` and worktree; PR #696 merged) established a reusable codebase gotcha that no context states: `typer.Exit`'s MRO is `(click.exceptions.Exit, RuntimeError, Exception, BaseException, object)` (re-verified with `.venv/bin/python -c "import typer; print(typer.Exit.__mro__)"`), so any `except Exception` guard around a `post(...)`/`notify(...)` call silently swallows the `typer.Exit(1)` that `SlackChannel.webhook_for` raises for an unresolved `important_webhook` — the configuration refusal that `coga/sync` describes as the fail-loud contract. That is exactly why the declared-period-state warning (`src/coga/mark.py:502`, `except Exception as exc:  # advisory broadcast — never break completion`) is fail-quiet rather than fail-loud: `coga/contexts/coga/sync/SKILL.md:212-214` records the *outcome* ("its existing advisory guard reports that raise on stderr") but not the *mechanism*, and `coga/contexts/coga/codebase/SKILL.md` "Gotchas when editing coga's own code" (line 723 onward) has no entry for it (grep for `RuntimeError`, `click.exceptions.Exit`, `bare except` across `coga/contexts`, `coga/skills`, `coga/workflows` returns nothing). The same ticket also recorded the accepted converse: `recurring_runner._run_recipe_task` is called with no guard, so an unresolved webhook on the recipe-failure post propagates out of the scan loop and skips every remaining due task — the owner chose fail-loud there with the `coga validate` warning as the mitigation. Proposed home: one bullet in the codebase context's gotchas list saying that `typer.Exit` is caught by `except Exception`, that a broad guard around a notification call therefore converts a configuration refusal into a stderr line, and that new guards should either catch narrower exception types or be a deliberate, documented best-effort exception as `coga/sync` lists.

#### F10. Twin enforcement is one-sided: a context created on only one side is caught by nothing

- shard: ks-23
- class: extract
- target: document-the-ticket-blackboard-writer-s-contract
- area: codebase
- source: done+checkout

`coga/contexts/coga/codebase/SKILL.md` (~line 833-838) says `tests/test_packaging.py` derives twin pairs so "a new twin is covered the moment it exists and there is nothing to register". The done ticket verified the gap in that statement: the derivation walks the *packaged* tree and pairs a file only when its live counterpart already exists, so creating a new context on one side only (live-only, or packaged-only) is not a pair and fails nothing, and `EXPECTED_BOOTSTRAP_RESOURCES` (`tests/test_packaging.py:21`) is a hand-kept partial list that cannot catch it either. Verified on current `main`: that list names 6 of the 11 packaged `contexts/coga/*` (no `blackboard`, `patterns`, `period-task`, `launch-internals`, or `cli` entry), `contexts/coga/cli` exists packaged-only with no live twin, and five live contexts (`current-direction`, `project-stage`, `roadmap`, `secrets`, `usage`) have no packaged twin. Neither test reports any of these. The codebase context should say that the derived check covers an *existing* pair only — the author creating a new shipped context or skill must create both copies deliberately (the blackboard ticket's `## Implementation notes` records doing exactly that), and `EXPECTED_BOOTSTRAP_RESOURCES` is an incomplete hand-kept list that a new packaged resource should be added to or that should be derived instead (the ticket's `## Follow-ups` names this as unfiled).

#### F11. A validator kind that fires on a shape a mutating command legitimately writes must be `warn`, never `error`

- shard: ks-24
- class: extract
- target: title-only-tickets-have-no-convention-and-no-valid
- area: codebase (validate severity rule) / architecture ("Each of those writers also chooses when it validates")
- source: done+checkout

The ticket's implement decision records a general severity rule with its rationale: `empty-description` had to be a warning because `assert_task_valid` runs as the post-write check of every mutating command, and `coga create` without `--description` legitimately produces an empty body — an `error` would make `coga create` fail its own post-write validation of the ticket it just wrote. The shipped surfaces carry only the behavior, not the rule: `bootstrap/contexts/coga/cli/SKILL.md` L138-140 says `coga validate` "does not refuse creation or activation on that warning alone", and `coga/contexts/coga/architecture/SKILL.md` L643-646 explains why `assert_task_valid` errors must be keyed off ticket content, but neither states the constraint that binds any *future* kind: a check can only be `error` severity if no mutating command's legitimate output can trip it, otherwise the command's own commit-half validation refuses the write it just made. One sentence in the architecture paragraph (and packaged twin) or the `codebase` validator section, with `empty-description` as the worked example, would keep the next author from adding an `error` that breaks `coga create`.

#### F12. The draft-synthesis gate's 600-character threshold is a measured limit no context names

- shard: ks-25
- class: extract
- target: give-a-ticket-s-superseded-design-one-documented-h
- area: coga/blackboard
- source: done+checkout

The done ticket's `## Peer review` recorded the concrete limit behind the pre-launch blackboard gate: "a draft with a conforming `## Superseded designs` archive can fail the pre-launch blackboard gate once the archive reaches 600 characters, because only `## Production notes` is exempt" — the number is `PRELAUNCH_SYNTHESIS_TEXT_CHARS = 600` in `src/coga/blackboard.py`, and `coga validate` prints it as "non-placeholder blackboard is N characters" (today's baseline error on `v2/measure-relay-prompt-scope-and-agent-precision` reads 4213). `coga/contexts/coga/blackboard/SKILL.md` describes the gate only qualitatively ("Remaining authoring sections or large custom scratchpads make `coga mark active` and launch-time auto-activation refuse") and neither it, `dev/code`, nor `bootstrap/ticket` states the threshold or that it measures non-placeholder characters of the region excluding `## Production notes` and `## Superseded designs`. An author deciding how much scratch a draft may carry before activation has no number to work from. Proposed: add the constant, its unit, and the two exclusions to the "Append or rewrite in place" paragraph of `coga/blackboard` (live and packaged twin), citing `blackboard.PRELAUNCH_SYNTHESIS_TEXT_CHARS` by symbol. The ticket's `## Dev` has a real `branch:`/`worktree:`/`pr:`, so this is retirement debt for `coga retire`, not a Retro extract.

#### F13. gh skill update flattens nested refs and scans only two directory levels — recorded only as a code comment

- shard: ks-08
- class: extract
- target: autofix/report-per-skill-outcomes-from-gh-skill-update-in
- area: coga/codebase
- source: done+checkout

The done ticket (`## Dev` has real `branch: skill-update-per-skill` / `worktree:` / PR #796) verified two gh 2.92.0 behaviors that the codebase context's "Installer-managed, flat and GitHub-backed" bullet (`coga/contexts/coga/codebase/SKILL.md` ~L207-225) does not carry: (1) `gh skill update --dir d --force --all ns/x` silently deletes `d/ns/x` and reinstalls it flat at `d/x`, printing a clean `Updated ns/x` with exit 0, which is why `_update_gh_backed_skill` refuses any namespaced gh-backed ref as `failed` before calling gh (`src/coga/skill_manager.py:1153` holds the only durable note); and (2) `gh skill update --dir` scans only two directory levels (`scanInstalledSkills`), so a gh-backed skill at `coga/<a>/<b>` is invisible to bulk gh but reported `failed` ("none of the specified skills are installed") by Coga's per-skill call. Neither `coga/contexts/coga/codebase/SKILL.md` nor `bootstrap/skill-update/SKILL.md` mentions the nesting hazard (grep for `nested`, `two levels`, `ns/x` is empty); the context should add one sentence beside the flat-layout bullet so nobody re-nests a gh-backed pack to "namespace" it. The ticket's other findings (per-skill invocation, `github-repo` predicate, no `--json`, `skipped-bundled` inventory, main-red-on-test_packaging gotcha) are already in the codebase context, the skill-update skill, and `code/self-qa`.

#### F14. Rich TUI viewport gotchas from the megalaunch picker fix are unrecorded

- shard: ks-15
- class: extract
- target: megalaunch-only-shows-one-page
- area: coga/codebase
- source: done+checkout

`coga/tasks/megalaunch-only-shows-one-page.md` (status done; `## Dev` records `branch: megalaunch-picker-viewport` and `worktree: /home/zach2179/dev/coga-megalaunch-picker-viewport`, PR #722) verified four Rich-rendering facts that any of the three Rich consumers in `src/coga/` (`commands/megalaunch.py`, `views.py`, `commands/recurring.py`) can trip on, and none is in `coga/contexts/coga/codebase/SKILL.md` (grep for `no_wrap`, `first screenful`, `vertical_overflow`, `ratio_reduce`, `render_lines` returns nothing there or in any other context/skill; the only picker mention is `coga/skills/code/self-qa/SKILL.md:55`, which cites the bug as a testing lesson, not the mechanics). The facts: (1) `rich.live.Live` defaults to `vertical_overflow="ellipsis"` and `LiveRender` keeps `lines[: height - 1]` — the *first* screenful, not the last, so a taller-than-terminal render hides the bottom; (2) making wide `Table` columns `no_wrap=True, overflow="ellipsis"` alone makes the table measure wider than the terminal and Rich's last-resort `ratio_reduce` shrinks every column evenly, emptying one-cell fixed columns (the cursor marker, the `[x]` checkbox) — `width=` does not protect them; the fix is `expand=True` plus `ratio=` on the elastic columns so `ratio_distribute` absorbs the excess (`src/coga/commands/megalaunch.py:403-410` on main); (3) a `Table` costs 2 chrome lines (header + rule), and any standalone `Text` in the surrounding `Group` (hint line, indicators) wraps independently and needs its own `no_wrap`; (4) to test frame height, assert on `Console(width=, height=).render_lines(group)` *without* passing an explicit `height` option (Rich pads/crops to it and the assertion passes vacuously) and assert an exact height, not `<=`, since a wrapped row can still happen to fit. Worth a short "Rich rendering invariants" note beside the existing megalaunch entries in the codebase context (around lines 56-77) so the next TUI change does not rediscover them by eye.

#### F15. Recovery recipe after the exit-boundary sweep lands feature-branch `coga/` docs on `main`

- shard: ks-32
- class: extract
- target: select-session-conduct-instead-of-appending-a-cont
- area: coga/codebase
- source: done+checkout

`coga/contexts/coga/codebase/SKILL.md` (~lines 603–632) documents the hazard itself — a state-changing command such as `coga launch --prompt-report` run from a feature worktree sweeps in-flight `coga/` edits onto `main` — but stops at "commit onto the feature branch first". The ticket's blackboard `## Gotchas` records the verified recovery once it has already happened (`d698cd03 "Sync coga state"` pushed from the worktree): soft-reset the feature branch past the swept commit so the doc files join the feature commit, `git revert` the swept commit on `main` (`b5cb36a0`), and then verify the swept commit is no longer an ancestor of the feature branch — otherwise merging hits the revert-then-merge trap and the docs never land. The context does not mention the ancestor check or the revert-then-merge trap (grep for `revert` finds nothing), so an agent that trips the hazard has no documented way back. Status is `done` with a real `## Dev` checkout (`branch: select-session-conduct`, worktree `/home/n/Code/codex/coga-select-session-conduct`), so Retro will not touch it; this is retirement debt for `coga retire`.

#### F16. `for-each-ref %(refname:short)` has the same tag-shadow failure as `rev-parse --abbrev-ref`

- shard: ks-32
- class: extract
- target: persist-autoclose-retire-follow-ups
- area: coga/codebase
- source: done+checkout

`coga/contexts/coga/codebase/SKILL.md` (~lines 739–753) already carries the "tag shares a name with the branch → `heads/<name>`" gotcha, but only for `git rev-parse --abbrev-ref HEAD`, and it names `branchsweep._current_branch` and two `open_pr.py` call sites as the shadowable holdouts. The ticket's `## Self-QA` recorded a second, verified instance of the same git behavior: `git for-each-ref --format=%(refname:short) refs/heads/` also emits `heads/<name>` when a tag shares the branch name, which in the retire worklist would have discharged a live branch as "gone"; the fix that shipped is `--format=%(refname)` plus `removeprefix("refs/heads/")` (now a docstring at `src/coga/retire_worklist.py:213`, code-only). The context does not mention `for-each-ref`/`refname:short` at all (grep finds no hit under `coga/contexts`, `coga/skills`, or `docs`), and `src/coga/branchsweep.py:637` `_local_branches` still uses the shadowable `%(refname:short)` spelling, so a tag named like a branch makes branch-sweep's branch map key on `heads/<name>` and miss every comparison against worktree branch names. Extend that bullet to cover both spellings and list `branchsweep._local_branches` among the holdouts. Status is `done` with a real `## Dev` checkout (`branch: autoclose-retire-worklist`, worktree `/home/n/Code/claude/coga-autoclose-retire-worklist`, PR #820), so this is retirement debt for `coga retire`, not Retro.

#### F17. Ordinary-launch deferred activation is knowingly unguarded (single-writer decision)

- shard: ks-13
- class: extract
- target: launch-activates-before-preflight
- area: coga/launch-internals
- source: done+checkout

`coga/contexts/coga/launch-internals/SKILL.md` records that draft/paused activation is deferred past every refusing preflight on the agent path and that the assist path byte-compares the ticket before publishing, but it does not record the owner decision (2026-09-02, ticket `## Implementation` blackboard) that the ordinary non-assist path's prepare→commit window — held across `compose_prompt`, `build_launch_env` (`op read`), and `_preflight_push_auth` — is deliberately *unguarded*: `_commit_auto_activate` (`src/coga/commands/launch.py`) overwrites the on-disk ticket from the in-memory prepared object with no drift check, on the stated rationale that Coga is single-writer and a ticket is not edited concurrently with its own launch, matching the pre-existing blocked-resume gate; the strict assist path is the sole byte-guarded exception. The context lists the strict guarantees under concurrent writers, so a reader can wrongly infer every activation is byte-guarded; grep of the context and `coga/architecture` for "single-writer"/"lost-update" finds nothing. Two further code-comment invariants the split depends on are also worth one sentence there: nothing between `_prepare_auto_activate` and the commit re-reads the ticket from disk, and `mark_active`'s re-run of `prepare_active` is idempotent only because the second run sees `prior_status == "active"` and so skips the draft-only blackboard-synthesis and canceled checks. Ticket is `done` with a real `## Dev` (`branch: defer-launch-activation`, worktree `/home/n/Code/claude/coga-defer-launch-activation`, PR #748), so this is retirement debt for `coga retire`.

#### F18. Dream routing decisions landed as rules but their rejected alternatives and rationale live only in the done ticket

- shard: ks-08
- class: extract
- target: dream-findings-have-three-routing-holes-that-lose
- area: coga/recurring (Dream template)
- source: done+checkout

`status: done` with a real `## Dev` checkout (`branch: dream-routing-holes`, worktree `/home/n/Code/claude/coga-dream-routing-holes`, PR #799 merged — the rules are present in `coga/recurring/dream/ticket.md` L324-486 and in `bootstrap/dream/scan/knowledge-scan/SKILL.md`). What did not land is the *why*, which is the reusable part when someone next proposes cross-run Dream state: (1) a persistent hygiene ledger for validator issues was rejected because Dream's template blackboard deliberately opts out of `coga/period-task` cross-run state ("Dream keeps no durable state here", template L523) and a ledger is exactly the hidden-state shape CLAUDE.md forbids — so `coga validate --json` is the live member list and membership is never copied run to run; (2) extending Phase 4 Retro eligibility to checkout-bearing done tickets was rejected because the checkout gate exists so the human-typed `coga retire <slug>` stays valid, and letting Phase 6 open knowledge PRs for `done+checkout` sources was rejected because W36 alone had 18 and it would bypass Retro's batching/isolation — hence retirement debt is a *reported* condition, and W36's hand-filed carrier ticket was "the right emergency move, not the rule"; (3) peer review established that a `done` ticket alone never suppresses a gap (the autofix follow-up was the counterexample). The template states each rule but none of the rejected shapes; a short "Why Dream keeps no cross-run ledger" note under the recurring context's "Dream is the recurring janitor" section (`coga/contexts/coga/recurring/SKILL.md` L948) or in the template's Phase 6 preamble would stop the ledger idea from being re-proposed. Grep of both files for `ledger`/`hygiene` in Dream's sense is empty.

### Class: stale

#### F19. `coga/extension-model` and `coga/codebase` call `megalaunch` the only unclassified verb while their own evidence base lists `ticket` and `retire` as unsettled

- shard: ks-34
- class: stale
- target: coga/contexts/coga/extension-model/SKILL.md
- area: architecture

`coga/contexts/coga/extension-model/SKILL.md` states twice that `coga megalaunch` "is the one genuinely unclassified in-package implementation" (line 84) and "The one live verb still genuinely under classification is `megalaunch`" (line 270); `coga/contexts/coga/codebase/SKILL.md:113-114`, `CLAUDE.md:19`, `AGENTS.md:19`, and both packaged twins under `src/coga/resources/templates/coga/bootstrap/contexts/coga/{extension-model,codebase}/SKILL.md` repeat it. But `docs/cli-extension-audit.md` — which extension-model names as "the verb-by-verb evidence behind" the rule — records `ticket` as "thin built-in head + `coga.authoring` finalize; package home provisional ... no co-versioning invariant has yet been ratified" (line 77, again at 104 and 211-214: "its permanent package home remains provisional until the residual-command ticket records a co-versioning invariant or moves it to the edge"), and `retire` as retaining "its own task-creation and launch head pending its separate cleanup review" (line 214). Under extension-model's own decision rule a verb is kernel only via the launch closure, the fixed `coga run` table, or a reviewed co-versioning proof, and "Python logic only proves that a verb is not an alias" — yet the audit's sole justification for `show`, `status`, `usage`, `slack`, `secret`, `uninstall`, and `skill` is "built-in ... Logic, not a passthrough" or "Heavy side effects", which the context explicitly rules insufficient. So `ticket` (and by the audit's wording `retire`) are unclassified in exactly the sense the context reserves for `megalaunch`, and the read/report and support verbs have no rule-tier classification at all; the five parked drafts under `coga/tasks/v2/cleanup-core-commands/` exist precisely to supply those. Current reality: `src/coga/cli.py:76-96` registers all of these as Typer commands; `runner.RECIPES` (`src/coga/runner.py:47-54`) contains none of them. Owner of the fact is extension-model (rule + settled table); the fix is either to widen the sentence to name `ticket`/`retire` (and the unclassified read/report/support verbs) alongside `megalaunch` as deferred to the same parked design, or to record their kernel-tier reasons in the audit — and to sync `coga/codebase`, `CLAUDE.md`, `AGENTS.md`, and the packaged twins in the same PR.
Correction (same finding): `coga/current-direction` has **no** packaged twin — `find src/coga/resources/templates -path '*current-direction*' -name SKILL.md` returns nothing — so only the live file needs the edit; disregard the twin sentence above.

#### F20. `coga/codebase` pins a dated `coga validate` baseline error set that no longer matches `main`

- shard: ks-09, ks-25, ks-26 (merged)
- class: stale
- target: coga/contexts/coga/codebase/SKILL.md
- area: codebase

`coga/contexts/coga/codebase/SKILL.md` (~lines 577-586, "The repo-wide run is red by baseline") states that "As of 2026-09-16, `coga validate --json` exits 1 on exactly four errors, all `unsynthesized-draft-blackboard`, all on `v2/` drafts" and names `v2/autotrigger-ticket-type`, `v2/measure-relay-prompt-scope-and-agent-precision`, `v2/split-context-to-doc-user-accessible-and-editable`, and `v2/use-worktree-when-starting-a-dev-task`. Running `coga validate --json` on `main` at this scan still yields four `unsynthesized-draft-blackboard` errors, but the set is different: `v2/split-context-to-doc-user-accessible-and-editable` no longer errors (its blackboard was reworked in #826 `Adjudicate parked and active tickets whose premises have moved`, and it stays `status: draft`), and the root-level draft `clean-up-all-the-working-trees` — not a `v2/` draft — is now one of the four. The "all on `v2/` drafts" qualifier and the named list are therefore both wrong, and the in-progress ticket `correct-the-v2-known-stale-surfaces-table-and-rout` (PR #845, at its review step) will shrink the set again by synthesizing `measure-relay-prompt-scope-and-agent-precision` and `use-worktree-when-starting-a-dev-task`. The instruction the passage exists for ("if your verification matches that error set, report it as known baseline and do not touch those drafts") cannot be followed from a list that drifts every time a draft is adjudicated; the durable fact is the rule (the check fires only on `status == "draft"`, clears only by synthesis/adjudication, never fix it under an unrelated ticket), and the concrete slug list should either be dropped or be re-derived from a `coga validate --json` filter rather than hardcoded. Fix in the live file and its packaged twin under `src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md` if one exists (`tests/test_packaging.py` enforces byte-identity).

_Merged duplicate from ks-25 ("`coga/codebase` validate-baseline bullet no longer matches the live error set"):_ The "repo-wide run is red by baseline" bullet (added by done ticket `record-or-clear-the-standing-repo-wide-coga-valida`, PR #823) states that as of 2026-09-16 `coga validate --json` exits 1 on "exactly four errors, all `unsynthesized-draft-blackboard`, all on `v2/` drafts" and lists `v2/autotrigger-ticket-type`, `v2/measure-relay-prompt-scope-and-agent-precision`, `v2/split-context-to-doc-user-accessible-and-editable`, `v2/use-worktree-when-starting-a-dev-task`. On current `main` (2026-09-21) the run still exits 1 with four errors, but the set differs: `v2/split-context-to-doc-user-accessible-and-editable` no longer errors (its blackboard was rewritten in PR #826 `23420a916`, "Adjudicate parked and active tickets whose premises have moved", which did not update the bullet as the bullet itself requires), and a new non-`v2` draft `clean-up-all-the-working-trees` (created `b8ec2ba8e`, carries `## Ticket authoring notes` and `## Evaluator review` sections) now errors. So both the slug list and the "all on `v2/` drafts" claim are wrong. The bullet's own rule — "Any PR that clears a listed error must update this bullet's date, remaining error count, and task-ref list in the same change" — was not followed; the fix is to refresh the date, list, and the `v2/`-only wording in both the live context and its byte-identical packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md`. No open ticket owns this (the only ticket mentioning the baseline is the done one above).

_Merged duplicate from ks-26 ("codebase context's "red by baseline" validate bullet lists the wrong error set"):_ The "Sandbox and cross-machine dev loop" bullet ("The repo-wide run is red by baseline; do not clear it under an unrelated ticket") claims that as of 2026-09-16 `coga validate --json` exits 1 on exactly four `unsynthesized-draft-blackboard` errors, "all on `v2/` drafts": `v2/autotrigger-ticket-type`, `v2/measure-relay-prompt-scope-and-agent-precision`, `v2/split-context-to-doc-user-accessible-and-editable`, and `v2/use-worktree-when-starting-a-dev-task`. Running `coga validate --json` on current `main` (2026-09-21) still exits 1 with four `unsynthesized-draft-blackboard` errors, but the set is different: `v2/split-context-to-doc-user-accessible-and-editable` no longer errors (still `status: draft`, last touched by PR #826 "Adjudicate parked and active tickets whose premises have moved"), and the root draft `coga/tasks/clean-up-all-the-working-trees.md` now errors in its place — so the "all on `v2/` drafts" qualifier is also false. The bullet itself mandates that any PR clearing a listed error updates its date, count, and task-ref list, and its packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md` must stay byte-identical. Related in-flight work: `correct-the-v2-known-stale-surfaces-table-and-rout` (in_progress) reports its feature branch clears two more of these (4 → 2, leaving `clean-up-all-the-working-trees` and `v2/autotrigger-ticket-type`), but its ticket does not name the codebase bullet as a touchpoint, so the bullet should be refreshed against whichever set is live when that lands.

#### F21. `coga/codebase` still files `browser/playwright` as a hand-vendored, installer-free skill

- shard: ks-04
- class: stale
- target: coga/contexts/coga/codebase/SKILL.md
- area: codebase / skill management

The "Hand-vendored upstream skills, verbatim or adapted" bullet (`coga/contexts/coga/codebase/SKILL.md:266-273`) groups `browser/playwright/` with `anthropic/skill-creator/` and states "Neither is in `managed-skills.toml` and neither carries `.coga-source.json`: no installer placed them and none updates them." Current reality: `browser/playwright` is a package-bundled skill shipped at `src/coga/resources/templates/coga/bootstrap/skills/browser/playwright/` (alongside `dochub` and `build-automation`), the live `coga/skills/browser/playwright/` is its byte-identical twin, and `coga skill status` reports it as `local-override` (`src/coga/skill_manager.py:1293` `_local_override_result`, and `_bundled_update_result` at line 1271 explains the shadowing). The package copy is refreshed by upgrading `coga`; only the repo twin is left alone. The `recurring/skill-update` template already draws this distinction after PR #829 (`coga/recurring/skill-update/ticket.md:70-78`: "The package-backed `browser/playwright` skill ships `NOTICE.txt` ... a repo that copies it as a `local-override` carries the same file"), so the two knowledge surfaces now disagree. The done ticket `vendored-skills-carry-no-coga-source-json-so-coga` recorded this exact discrepancy in its blackboard as "Adjacent finding — deferred ... carry this finding into the retro handoff" and found no follow-up ticket; a grep of `coga/tasks/` for `local-override` still finds no open owner. Fix: move `browser/playwright` out of the hand-vendored bullet into the bundled-twin/local-override shape (or say explicitly that it is a bundled skill whose repo copy is a `local-override` carrying the same `NOTICE.txt`), keeping `anthropic/skill-creator` as the only genuinely hand-vendored example; the packaged twin of the codebase context must change identically.

#### F22. codebase context says the five unanswered review threads have no fix tickets; four now exist and the triage brief is done

- shard: ks-08, ks-19 (merged)
- class: stale
- target: coga/contexts/coga/codebase/SKILL.md
- area: coga/codebase

Under "Gotchas when editing coga's own code", the bullet "Five bot review threads merged unanswered in Aug–Sep 2026" (`coga/contexts/coga/codebase/SKILL.md` ~L902-909) states "the brief is draft `triage-five-review-comments-that-merged-unanswered`; none has a fix ticket yet." On current `main` that triage ticket is `status: done`, and four of the five threads have their own in-progress fix tickets that each cite the same assessment commit `4d828256`: PR 699 → `coga/tasks/refresh-recurring-ledger-before-first-create-sync.md` (step 4 review, PR #838 open, `fix/recurring-ledger-freshness`); PR 704 → `coga/tasks/reject-context-artifacts-that-escape-the-checkout.md`; PR 705 → `coga/tasks/attribute-headless-recurring-completions-to-system.md`; PR 747 → `coga/tasks/preserve-edits-during-released-claim-recovery.md`. The bullet should say the brief is closed and point each remaining concern at its fix ticket (or drop the per-PR sub-bullets once each fix merges, which #838's own acceptance list already promises for the 699 sub-bullet). The packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md` carries the same sentence and must move with it.

_Merged duplicate from ks-19 ("`coga/codebase` "Five bot review threads" gotcha still calls the triage a draft with no fix tickets"):_ The bullet "Five bot review threads merged unanswered in Aug–Sep 2026; their remaining concerns need triage" (`coga/contexts/coga/codebase/SKILL.md` ~line 902, byte-identical in the packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md`) says "the brief is draft `triage-five-review-comments-that-merged-unanswered`; none has a fix ticket yet", and its PR 755 sub-bullet says "the remaining ask is to keep the archive above the fence". Current reality: `coga/tasks/triage-five-review-comments-that-merged-unanswered.md` is `status: done` with owner verdicts recorded 2026-09-20 (fix on all five), and each concern has its own `code/with-review` ticket, all `status: in_progress` at the review step with an open PR — `refresh-recurring-ledger-before-first-create-sync` (PR 838), `reject-context-artifacts-that-escape-the-checkout` (PR 844, strict reject-all-symlinks policy chosen 2026-09-19), `attribute-headless-recurring-completions-to-system` (PR 835), `preserve-edits-during-released-claim-recovery` (PR 842), `exclude-superseded-designs-from-launch-prompts` (PR 840). For PR 755 the owner explicitly rejected the above-fence move; the accepted fix is to keep the archive on disk and exclude it from automatic composition with a pointer. The triage ticket's report step deliberately left the bullet alone because all five follow-up PRs rewrite it (live and packaged) and `git merge-tree` showed every pair conflicting on it, so the bullet will be corrected by whichever PR merges first and the other four must rebase; Dream should not file a sixth edit, only note that the bullet is stale until one of those five merges and the rest reconcile.

#### F23. `coga/codebase` misdescribes why pytest in a feature worktree needs PYTHONPATH

- shard: ks-18
- class: stale
- target: coga/contexts/coga/codebase/SKILL.md
- area: coga/codebase

The "Run the suite with an explicit `PYTHONPATH`" paragraph in `coga/contexts/coga/codebase/SKILL.md` (and its byte-identical packaged twin) claims that running `python -m pytest` from a feature worktree makes "`import coga` resolve to the primary checkout's unchanged package" via the editable install's `.pth`, so "the suite is simply green against source you did not edit". That mechanism is contradicted by `pyproject.toml` `[tool.pytest.ini_options] pythonpath = ["src"]` (present since #325, before the paragraph was written in #773): pytest 9.1.1 prepends `<rootdir>/src` to `sys.path` at startup, so every in-process test imports the worktree's own `coga`. Three done tickets corroborate this independently: `allow-description-and-owner-on-create` (self-QA: "pytest uses `pythonpath = ["src"]`, so the worktree code is what ran"), `isolated-checkouts-nothing-says-what-a-fresh-workt` (its "Adjacent observation, not fixed here" names exactly this contradiction and left the text alone), and `define-the-recipe-reporting-contract-report-durabi` ("a relative `PYTHONPATH` makes subprocess `ticket.py` children import the editable install on `main`"). The real hazard is narrower and lives in the ~26 test files that spawn subprocesses (`sys.executable -m coga.cli ...`, `coga`, `ticket.py` children): those inherit the environment, not pytest's `sys.path`, so without an exported absolute `PYTHONPATH` they run the `.pth` target — a mixed run where in-process assertions exercise the branch while CLI-driven ones exercise the primary checkout. The recommended command (`PYTHONPATH=$PWD/src python3.12 -m pytest`) stays correct; the paragraph should state the actual split (in-process imports follow `pythonpath = ["src"]`; subprocess children follow the `.pth` unless `PYTHONPATH` is absolute and exported) so an agent does not conclude the whole suite is testing the wrong tree, or the opposite, that the plain command is safe. Fix live and packaged twin together (`tests/test_packaging.py` enforces identity).

#### F24. `coga/codebase` still lists "launch worktrees" among what `.coga/` holds, but per-launch worktree isolation was removed in #547

- shard: ks-30
- class: stale
- target: coga/contexts/coga/codebase/SKILL.md
- area: coga/codebase

Under "Which checkout you invoke coga from" the context says (line 693–695, identical in the packaged twin `src/coga/resources/templates/coga/contexts/coga/codebase/SKILL.md`): "`.coga/` — **created on demand.** It is per-checkout runtime state, not installation: `recurring-runs/` ledgers, `megalaunch-selection.json`, launch worktrees." Nothing on `main` creates a worktree under `.coga/`. The `[launch].worktree` per-launch isolation feature was rolled back by commit `667120e8` ("Remove per-launch git worktree isolation (#547)", 2026-07-14) — `config._ALLOWED_LAUNCH_KEYS` is `{"idle_timeout", "max_session"}` (`src/coga/config.py:483`) and `commands/launch.py` has no worktree helpers — and the only worktree Coga now creates itself is the recurring runner's temporary control worktree, made with `tempfile.mkdtemp(prefix=...)` in the system temp dir (`src/coga/recurring_runner.py:1363`), whose run records are then moved back by `_persist_control_worktree_run_logs`. No `.py` under `src/coga/` references a `.coga/worktrees` path; the empty `.coga/worktrees/` directory on this machine is dated 2026-07-14, the day #547 landed. The canceled `v2/auto-persist-dirty-launch-worktrees-to-pushed-bran` ticket's Self-QA records the same removal. The sentence should list `recurring-runs/` and `megalaunch-selection.json` only (and `megalaunch.py:1032`'s docstring "(vendored CLI, worktrees)" carries the same leftover, though that is code, not a context). Reintroduction is parked in `v2/reintroduce-per-launch-worktree-isolation`, not live.

Correction to the twin path above: the packaged copy is `src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md` (line 695 carries the same sentence).

#### F25. `coga/codebase` "## Secrets" section still describes the removed `coga.local.toml` credential model

- shard: ks-30
- class: stale
- target: coga/contexts/coga/codebase/SKILL.md
- area: coga/codebase

The `## Secrets` section (lines 935–940 of the live file, identical in the packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md`) says: "per-machine paths and credentials go in `coga.local.toml` via `env:VAR_NAME` references. Secrets get injected as env vars at launch time by `coga launch`." That is the pre-rename `[secrets]` bulk-inject model the `coga/tasks/v2/README.md` known-stale table marks **Gone** and that the canceled `v2/pass-secrets-to-skills-with-per-skill-scope` draft describes as the old contract. On `main`, `config.py:297-306` rejects a `[secrets]` table in `coga.local.toml` outright ("`[secrets]` in coga.local.toml is no longer supported. Secrets are declared inline per-ticket"), `parse_inline_secrets` (`config.py:1438`) reads a ticket's `secrets:` frontmatter of `op://vault/item/field` or `env:VAR` refs, and `coga/contexts/coga/secrets/SKILL.md` states that "Config values resolve almost nothing. Exactly two fields — `[notification.slack].webhook` and `[notification.slack].important_webhook` — run an `env:VAR` reference through the shared resolver; every other string in `coga.toml` / `coga.local.toml` is taken literally, so an `env:VAR` written anywhere else is a nonfunctional configuration". A reader following the codebase section would put a credential ref in `coga.local.toml` and get a literal string. The section should point at `coga/secrets` (per-ticket `secrets:`, webhook keys as the only config-side `env:` fields) rather than restate a removed mechanism; the root `CLAUDE.md` "Configuration & Security" paragraph carries the same wording and is the other surface to fix in the same PR.

#### F26. current-direction carries a mechanical-rename artifact: "the product is literally a *coga* (baton between runners)"

- shard: ks-33
- class: stale
- target: coga/contexts/coga/current-direction/SKILL.md
- area: coga/current-direction

`coga/contexts/coga/current-direction/SKILL.md:64-65` (section "Open rename (workflow → playbook)") says "The product is literally a *coga* (baton between runners)". That sentence was written when the product was named Relay — the source draft `coga/tasks/v2/rename-workflow-primitive-to-playbook.md` reads "The product is literally a relay. A relay (race) is a baton passed between runners" — and the `relay` → `coga` rename was applied to it as find-and-replace, producing a claim that is false on its face (a "coga" is not a relay race) and strips the rationale of its meaning. The same section otherwise correctly frames the rename as parked intent. The packaged twin under `src/coga/resources/templates/coga/bootstrap/contexts/coga/current-direction/SKILL.md` must be corrected in the same change (byte-identity is enforced by `tests/test_packaging.py`). No open ticket names this sentence: `grep -rn "baton between runners" coga/tasks` returns nothing.

#### F27. Sync context's HEAD-blob claim-clear allowance does not converge an offline bump on a control-branch checkout

- shard: ks-13
- class: stale
- target: coga/contexts/coga/sync/SKILL.md
- area: coga/sync

`### The state-regression guard` (around lines 866–878) states that the catch-all sweep may clear a `launch_generation` in one shape — a session-ending transition from a checkout whose *committed `HEAD` blob* of the ticket is byte-identical to control's claimed copy — and presents this as "the retry of a `bump`/`mark` whose own scoped publication failed — an offline remote at transition time leaves the released ticket dirty, and without this allowance no later sweep could ever converge it". On the deployment the same context documents elsewhere (a primary checkout on the control branch, where `_sync_paths_on_control_branch` commits locally *before* pushing, lines ~527–530), an offline transition does not leave the ticket dirty: it leaves a local `main` commit whose `HEAD` blob is already the cleared ticket, so it can never equal control's claimed copy and the allowance is unsatisfiable exactly in the case it was written for. `coga/tasks/simplify-git-sync.md` (in_progress, PR #848 unmerged) records the live instance in its audit finding A3 — the September `coga` claim clear after an offline bump was re-offered by 18 later sweeps, "the documented 'retry of an offline bump' allowance did not fire", and ended in a human hand-commit after 24–30 h — and its keep/drop table gives the same mechanism as the cause ("the HEAD-blob allowance failed in its one incident because it depended on a local commit"). The context should either scope the allowance to the checkouts where the released ticket really stays dirty (detached/feature checkouts) or state that on a control-branch checkout the offline retry currently requires `git checkout origin/<control> -- <path>` by hand. The open PR #848 rewrites this section wholesale; if it merges the paragraph disappears with it, otherwise the claim stays wrong on `main`.

#### F28. dev/code says a committed stranded ticket duplicate surfaces as a PR merge conflict; open-pr's freshness gate refuses it first

- shard: ks-17
- class: stale
- target: coga/contexts/dev/code/SKILL.md
- area: dev/code
- owner: detect-stranded-ticket-writes-across-checkouts

The `## Dev` bullet under "Know what the gate does and does not buy" states that a hand-copied duplicate "resurfaces one step later — uncommitted, as `coga open-pr`'s 'Recorded worktree has uncommitted changes' refusal; committed, as a `ticket.md` (or `coga/log.md`) merge conflict on the PR against a control branch whose copy has since moved." On current `main` a committed duplicate never reaches the PR: `github_preflight.check_branch_contains_control` (present since #518, 2026-07-04) computes the paths changed on both sides since the merge base and returns a failing `CheckResult` for any non-identical overlap ("current branch does not contain latest <remote>/<control>. Rebase or merge before opening a PR ... Overlapping paths: coga/tasks/<slug>.md"), which `open_pr.py` wraps as `Branch ... is not safe to publish` and raises before push or `gh pr create`; `tests/test_open_pr.py::test_open_pr_rejects_overlapping_coga_state_drift` pins it. The merge conflict only appears if the operator follows that message's rebase advice — the same advice `coga/skills/code/open-pr/SKILL.md` repeats under "If `coga open-pr` fails" as "Stale branch → rebase the control branch" — and `coga/log.md` cannot conflict at all because `.gitattributes` sets `**/log.md merge=union`. The in_progress ticket `detect-stranded-ticket-writes-across-checkouts` (PR #850, open, on `review`) already rewrites this paragraph in both the live and packaged `dev/code` twins and adds a "Stranded ticket write" remediation to `code/open-pr`, so this is already ticketed; if that PR does not merge, the two sentences above still need correcting to "refused by `coga open-pr`'s freshness gate as an unsafe overlap; do not rebase — restore the merge base's copy of the ticket on the branch".

#### F29. code/self-qa still assumes the separate-checkout layout: "change into the feature worktree" and "return to the primary checkout" to bump

- shard: ks-17
- class: stale
- target: coga/skills/code/self-qa/SKILL.md
- area: dev/code

Since #771 (2026-09-09) the `dev/code` context and `code/implement` name two first-class checkout layouts, and for the single-checkout layout the context is explicit: `worktree:` names the primary checkout itself, `## Dev` lives on the feature branch, and the agent runs `coga bump` and `coga open-pr` "from that same checkout on that same branch — do not switch back to the control branch first". `code/implement` step 9 and `code/open-pr` step 2 both carry that branch ("in the single-checkout layout there is nowhere to return to — stay put"). `code/self-qa` (last edited 2026-09-14, byte-identical to its packaged twin) never mentions the layout: step 1 says unconditionally "change into the feature worktree and confirm it is on the recorded branch", and step 7 says "Finally, return to the primary checkout and run `coga bump <slug>` to advance to `pr`." Followed literally in a single-checkout ticket, step 7 means `git switch <control-branch>` before the bump, which moves the bump off the live ticket copy and is exactly the stranding direction the context warns against (the ticket copy `coga bump` syncs is the one in the checkout it runs in). The skill sits between `implement` and `open-pr` in `code/with-self-review`, so it is the one step in that workflow whose instructions contradict the layout the neighbours accept. The fix is the same one-clause conditional the sibling skills already use: "return to the primary checkout (in the single-checkout layout you are already there — stay on the feature branch)". No open ticket under `coga/tasks/` names `self-qa` together with the single-checkout layout.

#### F30. marketing/map links three clarity files the install allowlist pruned

- shard: ks-02, ks-01 (merged)
- class: stale
- target: coga/contexts/marketing/map/SKILL.md
- area: marketing

The "Writing methods" table in `coga/contexts/marketing/map/SKILL.md` has a row "Imported skill documentation and examples" linking `../../../skills/clarity/README.md`, `../../../skills/clarity/PRODUCT.md` and `../../../skills/clarity/samples/README.md`, and the catalogue header claims "no missing files or broken local links" (coverage checked 2026-09-10). None of the three paths exists: `coga/skills/clarity/` holds only `SKILL.md`, `LICENSE`, `references/` and `scripts/`, because `coga/skills/clarity/.coga-source.json` (installed 2026-09-08 by `coga skill install-url`) records an `include` allowlist and `local_adaptation_notes` that deliberately drop `README`, `PRODUCT` and `samples/` so `coga skill update` re-applies the pruning. The done ticket `no-comms-writing-skill-the-process-is-smeared-thro` planned that prune; no open ticket owns the dangling row (grep of `coga/tasks/` for `PRODUCT.md`, `clarity/README`, `samples/README` hits only that done ticket). The peer review in `phase-0-audit-is-complete-per-the-plan-but-still-i` already noted "three missing Clarity documentation links already exist on origin/main" without fixing them. Fix: delete the row (the notes say the skill body never loads those files) or repoint it to the upstream `source_url` in `.coga-source.json`, and drop the "no broken local links" claim or re-verify it.

_Merged duplicate from ks-01 ("marketing/map links clarity README, PRODUCT and samples that the prune removed"):_ The "Writing methods" table row "Imported skill documentation and examples" links `../../../skills/clarity/README.md`, `../../../skills/clarity/PRODUCT.md` and `../../../skills/clarity/samples/README.md` and describes them as "Third-party examples and skill documentation". None of the three exists on `main`: `coga/skills/clarity/` now holds only `LICENSE`, `SKILL.md`, `references/` and `scripts/`, and `.coga-source.json`'s `include` allowlist (`local_adaptation_notes`: "Pruned to the runtime skill only ... README/DESIGN/PRODUCT ... samples/ ... are excluded by that allowlist") makes `coga skill update` re-apply that pruning, so the files will not come back. `git log -- coga/skills/clarity/README.md` shows the last removal in `7966c2a23` (2026-09-14), after the map's "Coverage checked against the repo on 2026-09-10" line, and the map was last touched by #805 on 2026-09-14 without correcting this row. The row should be dropped or reduced to the `.coga-source.json` provenance pointer; the adjacent "Prose craft" row already covers what survives.

#### F31. marketing/map and marketing/distribution still call the telemetry ticket an empty concept with no policy decision

- shard: ks-02
- class: stale
- target: coga/contexts/marketing/map/SKILL.md, coga/contexts/marketing/distribution/SKILL.md
- area: marketing

`coga/contexts/marketing/map/SKILL.md` ("Distribution and audience" table) describes `coga/tasks/marketing/add-telemetry.md` as "Empty concept draft. It authorizes no instrumentation or change to distribution policy", and `coga/contexts/marketing/distribution/SKILL.md` ("Measurement and interpretation") says "The existing measurement boundary remains: no user instrumentation is authorized. The telemetry concept has no developed brief or policy decision." Current reality: `marketing/add-telemetry` ("Add PostHog phone-home telemetry for V1 product-market-fit signal") is `status: in_progress` at `step: 3 (review-design)` of `code/design-then-implement`, is 32 KB with acceptance criteria, a proposed shape and a completed design/evaluator review (log 2026-09-20 14:00–14:02), and its description records "Owner decisions, nicktoper, attended session 2026-09-20: reverse the principles #5 telemetry ban … These choices are settled." So the brief exists and the policy decision is made; only the implementation has not landed (`coga/contexts/coga/principles/SKILL.md` §5 still carries the absolute ban, which the ticket plans to amend). The ticket's "Documentation ownership and verification" section lists principles, architecture, usage, README and `docs/operations.md` as surfaces to update but not these two marketing contexts, so nothing currently scheduled fixes them. Fix: reword the map row to "in-progress design ticket; owner reversed the ban 2026-09-20" and replace distribution's "no user instrumentation is authorized … no developed brief or policy decision" with a pointer to the ticket and to `coga/principles` as the policy owner, so marketing measurement planning does not re-assert a boundary the owner has lifted.

#### F32. skill-creator ATTRIBUTION.md says skill-import generalization is untracked; the machinery and its tickets now exist

- shard: ks-03
- class: stale
- target: coga/skills/anthropic/skill-creator/ATTRIBUTION.md
- area: skills

The file's closing sentence — "Generalizing imports of this kind (update checks, attribution generation, namespacing) is not currently tracked by a ticket." — no longer matches the repo. `src/coga/skill_manager.py` and `src/coga/commands/skill.py` now implement `coga skill install` (GitHub-backed via `gh skill`), `coga skill install-url` (writes `.coga-source.json` with `installed_tree_digest`, `include` allowlist and `local_adaptation_notes`; `coga/skills/clarity/.coga-source.json` is a live instance) and `coga skill update`, driven weekly by `coga/recurring/skill-update/ticket.md`; and the import work has been ticketed repeatedly (`vendored-skills-carry-no-coga-source-json-so-coga` done, `installer-managed-skills-the-local-adaptation-guar` in_progress, `implement-the-include-allowlist-that-url-skill-upd` draft). The done ticket `vendored-skills-carry-no-coga-source-json-so-coga` records the actual decision for this skill: it stays deliberately hand-vendored "outside every updater path", with `ATTRIBUTION.md` as its human-readable attribution home and no `.coga-source.json` backfill. The refresh instructions and pinned-SHA guidance in the file are still correct; only the last paragraph is stale. Replace it with the recorded posture: this skill is intentionally unmanaged by `coga skill update` (see `coga/recurring/skill-update/ticket.md`), refresh is the manual re-copy above, and `coga skill install-url` is the managed route if that ever changes.

### Class: gap

#### F33. Nobody owns reaping linked worktrees left by tickets that ended without `coga retire`

- shard: ks-31
- class: gap
- target: coga/skills/coga/branch-sweep/sweep/SKILL.md (and coga/contexts/coga/recurring/SKILL.md)
- area: architecture
- owner: packaged-code-workflows-never-name-coga-retire-as

Two independent done tickets each scope leaked worktrees out and point at the other mechanism. `branch-sweep-strands-squash-merged-branches-whose` measured 21 linked worktrees (24 by its final re-measure) pinning branches the sweep refuses by design, and says "removing worktrees is `coga retire`'s job. Tickets that ended without retire leak both. Separate ticket." `service-recurring-from-a-temp-control-worktree-ins` scopes its reaping to its own `coga-recurring-*` prefix plus `git worktree prune` and states "Repo-wide branch and worktree hygiene remains `branch-sweep`'s job." No context, skill, or workflow settles the contradiction: `coga/skills/coga/branch-sweep/sweep/SKILL.md` and `coga/recurring/branch-sweep/ticket.md` only prune dead registrations and report live worktrees as `skipped-worktree-pinned`; `coga/contexts/coga/recurring/SKILL.md` and `coga/contexts/coga/architecture/SKILL.md` have no line naming who removes a live worktree whose ticket is already `done`. The in_progress ticket `packaged-code-workflows-never-name-coga-retire-as` attacks the root cause (packaged workflows never tell the owner to run `coga retire`, so checkout-bearing done tickets pile up) and is the closest open owner; the draft `clean-up-all-the-working-trees` is a one-time manual cleanup, not a durable rule. The durable fact to land — in the branch-sweep skill or the recurring context — is a one-sentence ownership statement: a worktree held by a `done` ticket is `coga retire`'s to remove, `branch-sweep` never removes worktrees, and a `done+checkout` ticket therefore pins its branch until retired.

#### F34. Recurring cleanup test globs the shared system tempdir and fails on stale leftovers

- shard: ks-16
- class: gap
- target: coga/contexts/coga/codebase/SKILL.md
- area: codebase

Two independent tickets hit the same full-suite failure and each re-derived the remedy from scratch. `activation-does-not-resolve-step-1-s-assignee-role` (`## Verification`) reports "a subsequent full run ... hit a transient unrelated worktree in the cleanup test's shared `/tmp` glob" and reran under a private `TMPDIR=/tmp/coga-step-one-final-tests`; `packaged-code-workflows-never-name-coga-retire-as` (`## Open PR`) reports `tests/test_recurring.py::test_control_worktree_is_removed_and_unregistered_after_the_run` failing identically on `origin/main` "caused by stale `/tmp/coga-recurring-repo-*` fixture directories left by earlier runs on this machine (the test globs the whole tempdir)" and calls it "a pre-existing test-isolation gap on `main`, not fixed here". The mechanism is verifiable: the test (`tests/test_recurring.py`, `leftovers = list(Path(tempfile.gettempdir()).glob(f"{_CONTROL_WORKTREE_PREFIX}{git_repo.root.name}-*"))`) asserts an empty match over the *machine-wide* tempdir, and every `git_repo` fixture names its root `repo` (`tests/conftest.py`, `root = tmp_path / "repo"`), so one aborted run of any control-worktree test leaves a `coga-recurring-repo-*` directory that breaks this assertion for every later run until someone deletes it by hand. `coga/contexts/coga/codebase/SKILL.md` carries a test-gotcha list (wheel build backend, `PYTHONPATH` absolute, portable fixture scripts, live-vs-packaged comparisons) but nothing about this: grep for `coga-recurring-repo`, `TMPDIR`, or the test name finds nothing in any context or skill. No open ticket owns it (grep of `coga/tasks/` for those terms hits only the two tickets above). Proposed carrier: a bullet in the codebase context's test-gotcha list naming the test, the cause (shared-tempdir glob keyed on the fixture's fixed `repo` name), and the remedy (run the suite with a private `TMPDIR`, or clear `$(python -c 'import tempfile;print(tempfile.gettempdir())')/coga-recurring-repo-*` first) — or a note that the proper fix is to point the test at `tmp_path` instead, if a code fix is preferred over documentation.

#### F35. Packaged-context reachability (init-seeded vs bootstrap-fallback vs packaged-only) is undocumented and re-derived per ticket

- shard: ks-29
- class: gap
- target: coga/contexts/coga/codebase/SKILL.md
- area: codebase
- owner: document-how-packaged-contexts-reach-a-repo-and-se

`coga/contexts/coga/codebase/SKILL.md` on `main` documents packaged contexts only as the byte-identity twin rule (grep for "packaged contexts reach", "init-seeded", "packaged-only", "coga/cli" returns nothing in the live context). Two independent tickets had to rediscover the mechanism: `packaged-repos-ship-recurring-templates-without-th` (done; body lines 118-123 flag `coga/cli` as "packaged with no live copy ... worth deciding whether that packaged-only context is intentional" and note a file can be dropped from `bootstrap/contexts/` without any test noticing) and `document-how-packaged-contexts-reach-a-repo-and-se` (in_progress, step 4 review; its verified-facts blackboard establishes that `paths.resolve_context_path` falls back to `bootstrap/contexts/` only while `templates/coga/contexts/**` is init-seeded once by `commands/update.py::copy_fresh_templates` and never read again, and that the bundled `browser-automation` ticket attached a context that existed only in the seed tree). The latter ticket owns the fix: PR #843 (`packaged-context-states`) is open and unmerged as of 2026-09-21, moving `templates/coga/contexts/browser/*` into `bootstrap/contexts/`, adding `test_bundled_bootstrap_tickets_attach_only_bootstrap_contexts`, and adding a `### How packaged contexts reach a repo` subsection plus the deliberate packaged-only `coga/cli` paragraph to both codebase twins. No new ticket is needed; Phase 6 should report "already ticketed" and the gap closes when #843 merges.

#### F36. No context or skill says how to read a retired ticket's body back from Git

- shard: ks-19
- class: gap
- target: coga/contexts/coga/architecture/SKILL.md
- area: coga/architecture

Tickets repeatedly need the body of a ticket that `coga retire` (or an older cleanup) already deleted, and each rediscovers the recipe on its own: `triage-five-review-comments-that-merged-unanswered` (done) was told "recover the source ticket from Git history if it has been retired" and used `git show 6c305673^:coga/tasks/verify-the-pr-review-comment-loop-once-the-review.md`; `the-ticket-interview-never-asks-what-done-means` (in_progress) records "the file was deleted in `ffb0a383` — it is not on disk. Recovered at design time with `git show ffb0a383^:coga/tasks/improve-prompt-for-relay-ticket.md`"; `adjudicate-parked-and-active-tickets-whose-premise` (done) notes wording "reachable only through git history" and had to recover accepted interview prompts the same way. The only written recipe is in `coga/tasks/v2/README.md` (`git log --all --diff-filter=D --name-only -- 'coga/tasks/<slug>*'` to find the deleting commit, then `git show <commit>^:<path>`), scoped to the parked-draft premise check — it is not a context or skill and does not compose into launch prompts for ordinary tickets. The closest knowledge text, `coga/contexts/coga/architecture/SKILL.md` (~line 41, "renaming a task orphans its whole prior history under the retired tag ... grep the retired tag when reconstructing the trail"), covers only the `coga/log.md` trail, not the deleted ticket file; `dev/code` "Who retires the checkout" says retire acts "at the lifecycle event where the ticket still exists" without saying where the body goes afterwards. Grep of `coga/contexts/**/SKILL.md` and repo-authored `coga/skills/**` for `git show`/`--diff-filter=D`/"recover" against tasks found no such guidance. Proposed: one sentence plus the two-command recipe beside the architecture context's retired-tag passage (or in `dev/code` next to "Who retires the checkout"), stating that a retired ticket's body and blackboard survive only as a Git blob, that `coga show <slug>` will not find it, and that the `v2/README.md` premise check should link to that owner rather than restate it. No open ticket owns this: task-title grep for retired/recover/git-history found only `preserve-edits-during-released-claim-recovery`, which is unrelated (launch admission).

#### F37. `codex review`'s own test probe always fails on missing `tomlkit`; nothing says to expect it

- shard: ks-15
- class: gap
- target: coga/contexts/coga/codebase/SKILL.md
- area: coga/codebase

At least a dozen tickets' `## Peer review` / verification notes each rediscover the same thing and re-justify it in prose: `codex review --base main` runs its own test attempt under the ambient interpreter, which lacks `tomlkit`, so its probe fails collection (`31 errors` in one record), and the agent then has to explain that the review verdict still stands and rerun the suite through the declared venv. Independent instances: `coga/tasks/exclude-superseded-designs-from-launch-prompts.md:169` ("Its attempted tests could not collect because ambient Python lacks `tomlkit`; the full suite passed separately"), `coga/tasks/preserve-edits-during-released-claim-recovery.md:106` ("Its own test attempt failed collection because its interpreter lacked `tomlkit`"), `coga/tasks/document-how-packaged-contexts-reach-a-repo-and-se.md:185`, `coga/tasks/phase-0-audit-is-complete-per-the-plan-but-still-i.md:111`, `coga/tasks/state-which-branch-is-canonical-for-machine-genera.md:173`, `coga/tasks/narrative-candidates-md-publishes-log-text-the-own.md:153`, plus `title-only-tickets…:183`, `test-recurring-create…:94`, `cleanup/handle-a-bare-slack-webhook…:128`, `ticket-relationships…:229`. `coga/contexts/coga/codebase/SKILL.md` covers two adjacent facts — the `.venv` is the test environment with `tomlkit` (line ~473) and `codex review` fails in-sandbox (line 560) — but neither it, `coga/skills/code/self-qa/SKILL.md` (which names `codex review` at line 38), nor the `code/with-review` peer-review step (`skills: []`) says that the reviewer's embedded test probe is expected to fail on `tomlkit`, that this is not a finding against the branch, and that the agent must run the suite itself via `PYTHONPATH=<checkout>/src <venv>/bin/python -m pytest` and record that command as the evidence. One bullet next to the sandbox item under the "codex review" list in `coga/codebase` (and a pointer from `code/self-qa`) would stop the per-ticket rediscovery. No open ticket found owning this (grep of `coga/tasks/` for `codex review` + `tomlkit` among non-done/canceled tickets).

#### F38. The wheel-building test also needs `pip` in the venv, not only `hatchling` — a repeated pre-existing failure nobody recorded

- shard: ks-20
- class: gap
- target: coga/contexts/coga/codebase/SKILL.md
- area: coga/codebase

`coga/contexts/coga/codebase/SKILL.md` (the "two non-obvious traps" bullets around line 415, twin in `src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md`) says `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries` shells out to `python -m pip wheel --no-build-isolation --no-deps .` and fails loud when `hatchling` is missing from the venv. It never says the same about `pip` itself, and that is the failure agents actually keep hitting: a venv created with `uv venv` (or `python -m venv --without-pip`) ships no `pip` module, so the subprocess dies with `No module named pip` before hatchling is even consulted. At least five independent tickets re-diagnosed this from scratch and each spent a verification paragraph proving it "fails identically on main": `no-context-records-the-ci-posture-publish-only-rel` (blackboard `## Verification`: "the project `.venv` has no pip ... Pre-existing and unrelated"; peer review repaired it with `python -m ensurepip` then `pip install 'hatchling>=1.18'`), `automerge/fix-let-a-lot-of-open-craps` (`## Implement handoff`: tests ran from "`uv venv .venv` + `uv pip install -e ".[test]"` (plus `pip`, which the wheel test needs)"), `launch-activates-before-preflight` (line ~401: "`No module named pip` in the venv"), `megalaunch-activates-picks-before-preflight` (line ~268, same), and `retire-never-removes-a-worktree-that-ran-the-tests` (line ~371: "`ensurepip` is available but pip is not installed"). No open ticket owns this (grep of `coga/tasks/` for `No module named pip` / `ensurepip` / `uv venv` hits only tickets whose subject is something else). Proposed carrier: extend the existing "The only wheel-building test needs a build backend in the venv" bullet in `coga/codebase` to say the test also needs `pip` importable in the interpreter running pytest, that `uv venv` does not install one, and that the one-line repair is `python -m ensurepip` (or `uv pip install pip`) before `pip install -e ".[test]"`; `docs/development.md` line ~20 could add the same one-liner to its install block so a `uv`-created venv gets pip. Keep both context copies byte-identical.

#### F39. Validating `example/coga` needs `env -u SLACK_WEBHOOK_URL`; the daily-commands list does not say so

- shard: ks-15, ks-28 (merged)
- class: gap
- target: coga/contexts/coga/codebase/SKILL.md
- area: coga/codebase

Ten tickets (grep `env -u SLACK_WEBHOOK_URL` across `coga/tasks/`) each rediscover that running `coga validate --json` against the seeded `example/coga` fixture fails when the operator's shell exports a bare `SLACK_WEBHOOK_URL`, and each writes the same workaround into its verification notes: `coga/tasks/megalaunch-only-shows-one-page.md` ("Needs `env -u SLACK_WEBHOOK_URL` — a bare value in this shell's env trips an unrelated config check"), `coga/tasks/exclude-superseded-designs-from-launch-prompts.md` ("The fixture disables notifications; unset the inherited legacy bare webhook variable rather than editing config"), `coga/tasks/reject-context-artifacts-that-escape-the-checkout.md` ("Unsetting the inherited bare webhook avoids the existing removed-environment-key guard"), plus `move-cogacontext-to-roodoc…`, `simplify-ticket-format`, `title-only-tickets…`, `the-v2-parking-area-premise-check…`, `activation-does-not-resolve-step-1…`, `validate-that-committed-skill-scripts…`, `cleanup/add-a-debug-mode-to-init…`. The guard itself is owned and explained by `coga/contexts/coga/sync/SKILL.md:414-416` (a bare exported `SLACK_WEBHOOK_URL` fails config load until `[notification.slack].webhook = "env:SLACK_WEBHOOK_URL"` is declared), so this is not a stale claim — but the operational consequence for the test fixture is absent from `coga/contexts/coga/codebase/SKILL.md`'s "Daily commands" (line ~436 lists `coga validate --json` with no mention of the env), which is where an implementing agent looks. One sentence there — "from `example/coga`, run `env -u SLACK_WEBHOOK_URL coga validate --json`; the fixture disables notifications and the config-load guard rejects a bare inherited webhook variable; do not edit the fixture's config to satisfy it" — would end the repeat. No open ticket owns it (all matching tickets are done or are the two in-progress fix tickets above, neither of which targets the docs).

_Merged duplicate from ks-28 ("`coga validate` on `example/` needs `env -u SLACK_WEBHOOK_URL` on dev shells — a repeated verification gotcha with no carrier"):_ At least ten tickets record the same verification struggle: running `coga validate --json` in `example/` fails on a dev shell that exports a bare `SLACK_WEBHOOK_URL`, because the seeded fixture's `webhook = "env:SLACK_WEBHOOK_URL"` trips the bare-env guard described in `coga/contexts/coga/sync/SKILL.md` (~line 414-416), and every ticket rediscovers the `env -u SLACK_WEBHOOK_URL coga validate --json` workaround by hand. Independent evidence: `coga/tasks/cleanup/add-a-debug-mode-to-init-for-vendoring-from-source.md` (Verification: "needs `env -u SLACK_WEBHOOK_URL` — a stray var in this shell trips the bare-webhook check"), `coga/tasks/megalaunch-only-shows-one-page.md:206` ("a bare value in this shell's env trips an ..."), `coga/tasks/simplify-ticket-format.md:765,942,1153`, plus `title-only-tickets-have-no-convention-and-no-valid`, `the-v2-parking-area-premise-check-has-four-holes`, `activation-does-not-resolve-step-1-s-assignee-role`, `reject-context-artifacts-that-escape-the-checkout`, `exclude-superseded-designs-from-launch-prompts`, `validate-that-committed-skill-scripts-with-a-sheba`, `move-cogacontext-to-roodoc-so-its-easier-for-human`. Neither `coga/contexts/coga/codebase/SKILL.md` nor `docs/development.md` mentions `SLACK_WEBHOOK_URL` at all (grep confirms), so the smoke-path instruction in CLAUDE.md ("`coga validate --json` validates repo/task structure") silently fails for anyone with the variable exported. Proposed carrier: one sentence in the codebase context's test/verification guidance (the section that owns "`coga validate --json` on `example/`") naming the guard and the `env -u` prefix, or a fixture change so `example/coga.toml` does not resolve the operator's real env var. No open ticket owns this: every ticket mentioning the variable is `done`, `in_progress` on unrelated work, or the unrelated draft `v2/let-notification-webhooks-resolve-1password-refere`.

#### F40. `code/implement` and `code/design` still instruct "split the ticket" with no defined mechanic on `main`

- shard: ks-21
- class: gap
- target: coga/skills/code/implement/SKILL.md (and coga/skills/code/design/SKILL.md)
- area: dev-code / code skills
- owner: define-the-split-a-ticket-mechanic-shared-by-code

On current `main`, `coga/skills/code/implement/SKILL.md` "Gotchas" still says only "If the work is too big for one PR, **stop and split the ticket** on the blackboard", and no `## Split` / `## Splitting a ticket` section exists in either the live or packaged `code/*` skills. Independent tickets keep inventing the linkage ad hoc: `run-recurring-agent-templates-off-the-control-bran` ("Two sibling tickets cover the easy cases"), `the-period-task-context-never-covers-the-determini` ("the sibling ticket `define-the-recipe-reporting-contract-report-durabi`. Read both before writing"), `retire-never-removes-a-worktree-that-ran-the-tests` ("shipped by the sibling ticket"), and `the-v2-parking-area-premise-check-has-four-holes` ("Sibling tickets from this run that overlap: …") — none distinguishing sequenced from co-equal or recording the split under a findable heading. This is already owned: `define-the-split-a-ticket-mechanic-shared-by-code` is `in_progress` at step 2 (peer-review) with the contract implemented as commit `c6d71231` on branch `split-ticket-contract` (worktree `/home/n/Code/claude/coga-split-ticket-contract`, not pushed, no PR) — a `## Splitting a ticket` section byte-identical in `code/implement` and `code/design` plus `tests/test_code_split_contract.py`; the overlapping parked draft `v2/skill-for-split-into-sibling-ticket-discipline` is already `canceled` on `main`. Reported for an honest count only; Phase 6 should mark it "already ticketed", not file a duplicate.

#### F41. `state_publication_barrier` is not reentrant and `sync_paths` takes it itself — no context says so

- shard: ks-06
- class: gap
- target: coga/contexts/coga/period-task/SKILL.md
- area: recurring
- owner: simplify-git-sync

Two independent tickets rediscovered the same lock trap by probing the code, and a third site works around it silently. `src/coga/git.py::state_publication_barrier` opens a fresh descriptor per acquisition and takes a blocking `flock`, so it is not reentrant, and the public publisher `git.sync_paths` acquires that barrier internally. Any writer that does the documented "read `taskfile.read_blackboard(expected_bytes=...)` / `replace_blackboard(expected_bytes=...)` under the barrier, then publish with `git.sync_paths()`" sequence deadlocks if the publish call sits inside the barrier. `coga/tasks/marketing/add-telemetry.md` (in_progress) specifies exactly that sequence in its design and its evaluator review had to prove the deadlock with a disposable subprocess (outer lock held, inner acquisition timed out after two seconds) before recommending that CAS exit its barrier before calling the publisher; `coga/tasks/simplify-git-sync.md` (in_progress, evaluator item 4) independently records "opens a separate descriptor for each acquisition; it is not reentrant" and that the redesign must define lock ownership/nesting; `src/coga/megalaunch.py` line ~1928 already carries the workaround as a code comment ("Re-entering it would deadlock, so use ... `_sync_paths_without_barrier`"). None of `coga/contexts/coga/period-task/SKILL.md`, `coga/contexts/coga/sync/SKILL.md`, `coga/contexts/coga/architecture/SKILL.md`, `coga/contexts/coga/codebase/SKILL.md`, or `coga/contexts/coga/blackboard/SKILL.md` mentions reentrancy, nesting, or the `_sync_paths_without_barrier` escape (grep for `reentran|re-entran|deadlock|_sync_paths_without_barrier` is empty across all of them). `coga/period-task` is the natural home because it is the context that tells a `ticket.py` author to write parent state through the fence-aware CAS API and then publish; one sentence there — "the barrier is a non-reentrant flock; `git.sync_paths` acquires it itself, so leave the barrier before publishing (or use the narrow `_sync_paths_without_barrier` form only when you already hold it, as `megalaunch` does)" — would have saved both evaluator probes. `simplify-git-sync` is named as owner because it is the open ticket whose body already carries this fact and whose redesign is to define lock nesting; if that ticket lands a different lock model, the documented rule should follow it.

#### F42. A done ticket's self-reported verification is not proof its scoped change reached main

- shard: ks-10, ks-10 (merged)
- class: gap
- target: src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md (packaged file is the single owner; no live twin)
- area: retro / dream

Two independent tickets record the same failure: a `status: done` ticket whose blackboard claims a fix that never (or only half) reached `main`, and every later reader — Retro, Dream, the next implementer — took the claim at face value. `coga/tasks/the-autofix-analyst-ticket-closed-without-shipping.md` (done, PR #816) documents that `fix-the-autofix-analyst` was marked done on the strength of an unrelated change (PR #724, the Claude subscription fallback) while none of the three defects its `## Description` scoped ever touched `src/coga/recurring_autofix.py`; closing it "removed the surface that would have kept the three defects visible", and the W36 backlog line that captured two of them did not drain. `coga/tasks/test-recurring-create-is-silent-fixture-fix-is-hal.md` (done) documents that `give-a-ticket-s-superseded-design-one-documented-h`'s `## Verification` claimed the fixture fix landed in `4012c5e9` when `c4482fae` carried half of it, so four later done tickets each re-recorded the failure as "pre-existing on main, worth its own ticket" and none checked the claim. The knowledge in the corpus covers only fragments: `bootstrap/dream/scan/knowledge-scan` tells the scan that a done ticket is "evidence to inspect, not an open owner" for *gap-owner* resolution, and `retro/done-ticket` says a ticket's `status: done` "says nothing about whether its adjacent bugs are fixed" and "do not ... claim one has landed" — for adjacent bugs only. Neither surface says the general rule these two tickets each had to rediscover: before Retro extracts from, deletes, or cites a done ticket as delivery evidence, compare the ticket's `## Description` acceptance scope against `main` (the named source path, test, or context) rather than against its own `## Implemented` / `## Verification` prose; a done ticket whose scoped change is absent on `main` is an unshipped ticket to report (a follow-up bug ticket, as `the-autofix-analyst-ticket-closed-without-shipping` did), not knowledge to extract or a fix to cite. No open ticket owns this (grep of `coga/tasks/` for `half-applied`, `closed without shipping`, `claimed ... landed`, `self-reported` hits only the two done tickets above). Suggested home: a short "Done is a status, not a receipt" paragraph in `retro/done-ticket`'s read-the-blackboard section, with a one-line pointer from `coga/contexts/coga/architecture` "Two state machines per ticket" (`done` is a control-plane transition and carries no proof the description shipped).



#### F43. Ticket-history recovery recipe misses tickets deleted before the `relay-os` → `coga` rename

- shard: ks-22
- class: gap
- target: coga/tasks/v2/README.md (the `git log --all --diff-filter=D --name-only -- 'coga/tasks/<slug>*'` recovery recipe; same gap in `bootstrap/ticket`'s citation guidance)
- area: ticket-format

Two independent tickets rediscovered that the task tree was `relay-os/tasks/` before commit `d0645a197` ("Rename relay to coga (full rebrand)", PR #454), so any history search scoped to `coga/tasks/` silently misses tickets deleted before the rename. `coga/tasks/adjudicate-the-eight-premise-dead-v2-drafts.md` (Context, "Recoverable autotrigger background") found six of seven cited slugs absent until it searched the old path: "The four retired hazard tickets were deleted under `relay-os/tasks/`, so searching only `coga/tasks/` history misses them. All four source bodies were recovered with `git show <deletion>^:relay-os/tasks/<slug>/ticket.md`" (commits `d7086ecd`, `078dd705`, `2584de1d`, `c008c23b`). `coga/tasks/simplify-ticket-format.md` (Context, line ~540) independently had to run its `watchers` history search "under both `coga/tasks/` and the former `relay-os/tasks/`". `coga/tasks/v2/README.md` lines 76-78 carry the only written recipe for recovering a dangling citation and it names only `'coga/tasks/<slug>*'`; `docs/migrating-to-coga.md` records the rename for operators but says nothing about history recovery, and no context or skill under `coga/contexts/`, `coga/skills/coga`, `coga/skills/code`, or `coga/skills/bootstrap` mentions `relay-os/tasks` at all (grep empty). Proposed change: extend the README recipe (and the `bootstrap/ticket` citation guidance that points to it) with one sentence — search both pathspecs, e.g. `-- 'coga/tasks/<slug>*' 'relay-os/tasks/<slug>*'`, because deletions before `d0645a197` live under the old tree. Owner search: grep of every task file for `pre-rename`/`relay-os/tasks` finds only historical mentions (`launch-activates-before-preflight` done, `four-parked-tickets-carry-premises-that-have-since` done, `no-durable-runbook-covers-running-coga-headless` canceled); no open ticket proposes fixing the recipe, and the in_progress `adjudicate-the-eight-premise-dead-v2-drafts` only inlines the recovered bodies into the autotrigger draft, not the README.

#### F44. Batch-adjudication tickets re-derive the same verdict-application mechanics every time

- shard: ks-24
- class: gap
- target: coga/tasks/v2/README.md (new "Applying a batch of verdicts" section beside "Before pulling anything forward")
- area: ticket-format / v2 parking contract

Three independent adjudication tickets each worked out, from scratch, how to actually apply a batch of premise verdicts while running under `code/with-review` (`requires: branch`, `requires: pr`): `four-parked-tickets-carry-premises-that-have-since` (done, "### Mechanics": "Verdict application is CLI state (`coga mark canceled/active/done`, `coga unblock`) on the control branch. The only PR-able work is ticket prose … `coga open-pr` treats ticket-body rewrites as publishable (`_publishable_changes`)"; and "Status is `draft`, so `coga mark done` is not allowed directly (needs `mark active` first)"), `adjudicate-parked-and-active-tickets-whose-premise` (done, "Lifecycle verdicts were applied with `coga mark` on `main` from this checkout (irreversible …); prose verdicts ride the PR", with `mark active` → `mark done` rows), and `adjudicate-the-eight-premise-dead-v2-drafts` (in_progress, "perform the sole cancellation from the control checkout before preparing cohort prose edits in the implementation checkout"). `coga/tasks/v2/README.md` owns the verdict vocabulary (cancel with reason, "already delivered by", describe-or-cancel) but says nothing about *where* each verdict is applied — lifecycle writes go to the control checkout on `main` and never ride the feature branch; only rewritten/narrowed ticket prose goes through the PR (which `open-pr` accepts as publishable); a draft that is done-by-other-means is either canceled with delivery evidence (README's current rule) or, if Retro retirement is wanted, activated first because `mark done` refuses `draft`. No context, skill, or workflow carries this (grep of `coga/contexts`, `coga/skills`, `coga/workflows` for "control checkout"/"publishable"/"mark active … mark done" in an adjudication sense returns nothing), and the open-owner grep across `coga/tasks/` for "mechanics" + "control checkout" + "adjudicat" finds only the verdict tickets themselves, none of which proposes documenting the recipe. Proposed: a short README section, and a one-line note in the code-facing `coga/cli` "Pick which command" (or `coga/architecture` lifecycle) that ticket-body-only edits satisfy `requires: pr`.

#### F45. `coga/codebase` should name the namespace-package footgun and how to get a 3.11 interpreter locally

- shard: ks-20, ks-18 (merged)
- class: gap
- target: cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r
- area: coga/codebase
- source: done+checkout
- extract_source: cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r (done+checkout)
- owner: nothing-exercises-python-3-11-the-declared-floor

The ticket (status `done`, `## Dev` records `worktree: /home/n/Code/claude/coga-resources-pkg-init`, PR #831) established two reusable facts that live today only in a Python docstring and the ticket blackboard, not in the context that owns "how to run tests and validation". (1) `src/coga/resources/__init__.py` is load-bearing: without it `coga.resources` is an implicit namespace package, `importlib.resources.files()` returns a `MultiplexedPath` whose `joinpath` takes exactly one segment on 3.11 (and has no `__fspath__`), and every multi-segment lookup — `paths.packaged_template_path`, `commands.update.packaged_template_root`, `managed_skills.managed_skill_manifest_root`, `dream_cleanup_orphan_markers` — raises `TypeError` and `coga init` dies before laying down a template; the same latent footgun applies to any future `files("coga.<pkg>")` call on a package without a marker (`commands/__init__.py` is empty and only incidentally saves it). (2) The verified way to reproduce the declared floor on these machines is `uv python install 3.11` and then an explicit `PYTHONPATH=$PWD/src <that interpreter> -m pytest`; the ambient `python` is 3.9 (conda) and the only system interpreter is 3.12, which is why the crash never reproduced locally. `coga/contexts/coga/codebase/SKILL.md` ("Use an explicit 3.11+ interpreter", ~line 501) tells the reader to use `python3.12` and says nothing about the namespace-package trap or about obtaining a 3.11 interpreter (grep for `MultiplexedPath`, `namespace package`, `uv python` finds nothing in the context, `docs/development.md`, or `code/implement`). The wider "nothing exercises 3.11" problem is already owned by the blocked ticket `nothing-exercises-python-3-11-the-declared-floor`; this extract is the narrower durable fact — one bullet under the packaging traps naming `resources/__init__.py` as a marker that must not be deleted (pointing at its docstring for the mechanism), and one line in the interpreter bullet giving `uv python install 3.11` as the local route to the floor. Apply to both context copies.

_Merged duplicate from ks-18 ("No context carries the namespace-package resource footgun or the "green 3.12 is not the floor" rule"):_ Two independent tickets hit the same undocumented fact. `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` (done, PR #831, merged as `506f0477c`) found that `src/coga/resources/` shipped no `__init__.py`, so on Python 3.11 `importlib.resources.files("coga.resources")` returns a `MultiplexedPath` whose `joinpath` takes one segment and has no `__fspath__`, crashing `coga init` at five call sites (`paths.py`, `update.py`, `managed_skills.py`, `dream_cleanup_orphan_markers.py`); 3.12 happens to accept the multi-segment call, which is why the break stayed invisible. `nothing-exercises-python-3-11-the-declared-floor` (blocked, owned here) then measured it end to end: the full suite on 3.11.15 gave 426 failed / 2229 passed against 2655 passed on 3.12.12, and it names the still-latent twin, `src/coga/commands/__init__.py` (present on `main` today, but the pattern — any new `files("coga.<pkg>")` consumer needs a package marker — is what must be remembered). `coga/contexts/coga/codebase/SKILL.md` today says only "use an explicit 3.11+ interpreter" and its "CI posture" section records that no test job exists; grep finds no `__init__.py`, `MultiplexedPath`, or "declared floor" rule in any context or skill. The open owner ticket already carries the exact context edit (committed unmerged on `ci/python311-floor` per its `## Changes`), so this is "already ticketed"; note for the owner that its blocker's stated dependency (merge PR #831) has since landed on `main` — `src/coga/resources/__init__.py` exists — so the blocked implement step can resume.

### Class: premise

#### F46. Parked draft `v2/cleanup-core-commands/lifecycle-verbs-to-ticket-operations`: its design verdict has been recorded in `coga/extension-model` with the opposite outcome

- shard: ks-34
- class: premise
- target: v2/cleanup-core-commands/lifecycle-verbs-to-ticket-operations
- area: architecture
- question: delivered

Questions 1-3 pass: `coga mark active|paused|done`, `coga bump`, `coga block`, `coga unblock` all resolve (`src/coga/cli.py:84-86,93`; `src/coga/commands/mark.py:59,115,194`), the referenced contexts and `code/design-then-implement` workflow exist (packaged under `src/coga/resources/templates/coga/bootstrap/`), and its only cross-ticket citation (`v2/cleanup-core-commands/launch-decomposition`, status `paused`, still on disk) is coordination, not required substance. Question 4 fails: the draft's first acceptance criterion — "the design step documents the minimal internal state-write substrate and separates it from user-facing lifecycle verbs", with `mark`/`bump`/`block`/`unblock` then moved or given a precise follow-up — has been answered durably in `coga/contexts/coga/extension-model/SKILL.md` since the draft was written, but with the opposite verdict: the "launch closure" section names "the `mark` (status) and `bump` (step) state-writes it advances" as kernel because launch calls them mid-flight, and "The command surface, classified" table lists `mark`, `bump`, `block`/`unblock` as kernel members, explaining that `block`/`unblock` are there "because they are core blocked-state transitions — registered in `src/coga/cli.py` and named as state-machine commands by `coga/architecture`" (`coga/contexts/coga/architecture/SKILL.md:571-612`). The draft's premise sentence "only `create` is presumed irreducibly core" is therefore contradicted by the rule the repo now treats as settled, and `docs/cli-extension-audit.md:82,86,92` records the same verbs as built-in without a pending review. The verdict is the author's: cancel as delivered-by-rule (`coga mark canceled ... --message "classification settled by coga/extension-model launch-closure rule"`), or narrow the draft in its own body to the one part the context leaves arguable — `block`/`unblock` are in the kernel table by registration and naming rather than by the launch-closure test that justifies `mark`/`bump`. No open ticket adjudicates this draft (grep of `coga/tasks/**` for the slug finds only Phase 1 validator lines in `recurring/dream/ticket.md`).

#### F47. Parked draft `v2/cleanup-core-commands/work-orchestration-commands-to-tickets`: still names the removed `coga digest` surfaces in its body

- shard: ks-34
- class: premise
- target: v2/cleanup-core-commands/work-orchestration-commands-to-tickets
- area: architecture
- question: surfaces

Question 1 passes — `coga retire`, `coga megalaunch`, and `coga slack` still resolve (`src/coga/cli.py:81,88,89`) and neither `coga/extension-model` nor `docs/cli-extension-audit.md` has settled them (`retire` "retains its own task-creation and launch head pending its separate cleanup review", audit line 214; `megalaunch` is the context's declared open case). Question 2 fails: the draft's Description scopes "digest/recurring maintenance command surfaces that still own workflow substance", its Context cites "digest/autoclose/delete behavior already has script/workflow precedent", and its third acceptance criterion requires "`megalaunch`, `slack`, and digest/recurring maintenance surfaces are classified and migrated". `coga digest` no longer exists: `remov-digest-in-recurring` (status `done`) removed the command, its `runner.RECIPES` entry, the spool, and the recurring template (commit `5b5f3e1f1` "Remove the daily digest (#786)"); `src/coga/cli.py:76-96` registers no `digest`, `src/coga/runner.py:47-54` has no digest recipe, and `coga/workflows/` has no digest template. The sibling `coga/tasks/v2/cleanup-core-commands/README.md` carries a dated "Status note (2026-09-10)" saying the digest half "is therefore moot" but "the drafts above are left as written" — the acknowledgement lives in the directory index, not in the draft's own body, which is the surface that will be read when it is pulled forward. Remaining live subject: `retire`, `megalaunch`, `slack`, and whatever recurring-maintenance heads still own substance (`coga recurring` is now a thin head over the registered `recurring-scan` recipe per audit line 93, so that portion may also be narrower than written). Verdict is the author's: narrow the Description/acceptance criteria to the live surfaces, or leave as is with the digest lines struck. No open ticket adjudicates this draft; `ticket-relationships-and-ownership-have-no-mechani` (blocked) cites it only as an example of unnamed supersession prose.

#### F48. Parked draft `v2/cleanup-core-commands/residual-command-surfaces`: most of its taxonomy has shipped in `coga/extension-model` and the audit; only `coga ticket` remains open

- shard: ks-34
- class: premise
- target: v2/cleanup-core-commands/residual-command-surfaces
- area: architecture
- question: delivered

Questions 1-3 pass: every surface it names still resolves — `init`, `ticket`, `delete`, `skill` group, `recurring` group with `launch`/`promote`/`list` (`src/coga/cli.py:76-95`, `src/coga/commands/recurring.py:114-250`), and the default aliases `chat`, `build`, `dream`, `skill-update`, `autoclose` are all still in `DEFAULT_ALIASES` (`src/coga/aliases.py:56-65`, which has since grown `pick`, `open-pr`, `resolve-conflicts`); the four files it says to read exist. Question 4 fails for most of the scope, on the acceptance criteria rather than the title: "Default aliases are documented as alias sugar, not command logic" — delivered by `coga/contexts/coga/extension-model/SKILL.md` ("Aliases are not a fourth home — they are argv sugar"; the "Alias (sugar)" row of "The command surface, classified") and by `docs/cli-extension-audit.md:103-126` classifying each default alias as a pure passthrough; "`skill *` is explicitly classified as excluded or external/tooling, with the owner direction recorded" — delivered by extension-model's "Trust boundaries straddle" section (`gh skill` acquirer is external; "a `skill` acquirer is a thin wrapper on `gh skill` — extractable later as a `gh` extension; defer until a second consumer exists"); `init` is settled as kernel ("fresh `init` (creates the `coga/` a launch needs to exist)"); `delete` is recorded as a thin head over the fixed `delete-task` recipe (audit line 84 and 206, `src/coga/runner.py` RECIPES); bare `recurring` is recorded as a thin head over the registered `recurring-scan` recipe (audit line 93, 105). What has not shipped is exactly the draft's `ticket` bullet: the audit still says `coga ticket`'s "permanent package home remains provisional until the residual-command ticket records a co-versioning invariant or moves it to the edge" (lines 77, 104, 211-214). Verdict is the author's: narrow the draft in its own body to the `coga ticket` co-versioning proof-or-migration (question 3 applies — inline the audit's stated split: `bootstrap/ticket` interview target, `coga.authoring` finalize, `commands/ticket.py` arg-to-draft coordinator calling finalize inline), or cancel with delivery evidence if the owner accepts the audit's "provisional" as the recorded status. No open ticket adjudicates this draft.

#### F49. Parked draft `v2/cleanup-core-commands/support-commands-boundary`: the `secret` half is settled by `coga/extension-model`'s "acquire outside, verify inside" rule

- shard: ks-34
- class: premise
- target: v2/cleanup-core-commands/support-commands-boundary
- area: architecture
- question: delivered

Questions 1-3 pass: `coga secret get` (`src/coga/commands/secret.py:33`) and `coga uninstall` (`src/coga/cli.py:77`) resolve; the draft correctly notes there is no top-level `coga update` (confirmed: `src/coga/commands/update.py` is "Bootstrap helpers used by `coga init`", and `coga init` carries the fresh/update/update-all modes at `src/coga/commands/init.py:350`); it cites no other ticket for substance. Question 4 fails for the `secret get` half of the scope: the first acceptance criterion asks that `secret get` be "classified under the new small-core rule" with a "documented substrate or external tooling reason". `coga/contexts/coga/extension-model/SKILL.md`, section "Trust boundaries straddle: acquire outside, verify inside", now records that classification — acquisition (`op` / `env` resolving values) is external tooling, injection into the agent env is the mid-flight kernel hook, "This ends the 'is `secret`/`skill` core?' argument", and secret values "must never flow through the legible ticket/prompt/blackboard/git machinery" — which is also the security boundary the draft's second criterion demands. The unshipped remainder is `uninstall` plus package-upgrade/refresh documentation: the audit records `uninstall` only as "built-in ... Heavy side effects" (`docs/cli-extension-audit.md:75`), a reason extension-model itself says does not choose kernel over an edge command, and extension-model mentions `uninstall` only as one of the three invocations that bypass alias validation (line 246). Verdict is the author's: narrow the draft in its own body to `uninstall` and the upgrade-docs surface, citing the shipped secret classification as provenance, or cancel if the owner rules `uninstall` as `init`'s symmetric bootstrap substrate by the same "must exist before any launch" argument. No open ticket adjudicates this draft.

#### F50. Parked `op`-at-init draft describes an init requirement model that no longer exists

- shard: ks-16
- class: premise
- target: v2/op-secret-dependency-init-enforcement
- area: cli
- question: surfaces

The draft's "Current behavior (shipped)" baseline states that `relay init` hard-requires **`git` and `gh`** and that only `op` is deferred to its point of need; the open question is whether `op` should be able to opt into the same up-front enforcement `gh` gets. That baseline is gone. `src/coga/commands/init.py`, `_check_external_dependencies`, now checks a manifest of "just `git`" and its docstring states that "`gh` and `op` are deliberately not enforced here: each is enforced at its point of need (`gh` by managed-skill installs, the open-pr step, and the autoclose sweep; `op` by a launch that resolves an `op://` secret)". So the precedent the draft leans on — init hard-failing on a missing `gh` — was itself moved to the point-of-need model the draft describes for `op`, and the proposed `[init] require_op` flag would be reintroducing up-front enforcement for one tool that the codebase has since removed for the other. The other pointers still resolve after the `src/relay/` → `src/coga/` rename (`config._resolve_op_reference`, `config.select_launch_secrets`), nothing on `main` implements `require_op` (grep of `src/coga` and `coga/contexts` finds no hit), and sibling `v2/gh-merge-requirement` still exists. The only other ticket naming this slug is `v2/op-service-account-auth-to-skip-op-read-prompt` (a sibling pointer, not an adjudication), so there is no open owner.

#### F51. `v2/use-worktree-when-starting-a-dev-task` names dead surfaces, and its cleanup half is already delivered by `coga retire`

- shard: ks-28
- class: premise
- target: v2/use-worktree-when-starting-a-dev-task
- area: codebase
- question: surfaces

The draft (`status: draft`, non-empty description) fails question 2 of `coga/tasks/v2/README.md`: its steps are written against pre-rename surfaces that no longer resolve. It tells the implementer to fall back to `relay panic` (gone — README table says use `coga block`), to hook cleanup into `relay mark done` / `relay automerge` (there is no `automerge.py`; the merge-close hook on `main` is `src/coga/autoclose.py`), and to edit `src/relay/resources/templates/relay-os/.gitignore` (now `src/coga/resources/templates/coga/.gitignore`); it also says to close the sibling `autocleanup-worktree-branche` on review, but no such file exists under `coga/tasks/v2/` today. The evidence for the author's verdict goes further than the rename: the cleanup half — the half the draft calls "the whole point", with its "must guard before `git worktree remove`" sharp edge — is already delivered on `main` by `coga retire` → `branchcleanup.remove_ticket_worktree` (`src/coga/branchcleanup.py:153`), whose module docstring carries a "Worktree safety model" that preserves dirty, untracked, ignored, or open-PR checkouts exactly as the draft demanded, and `coga/contexts/coga/codebase/SKILL.md` (~line 684-692) already documents that behaviour. Only the creation half (a deterministic slug-keyed `<repo>/worktree/<slug>` path) remains undelivered: `coga/contexts/dev/code/SKILL.md` "Checkout boundary" still says "outside the primary checkout" with no fixed location, and no `[launch]` worktree key exists in `src/coga/config.py` (the root `.gitignore` comment mentioning `[launch].worktree` refers to a key that is not there). Question 4 therefore applies to the remainder: if the draft survives, narrow it in its own body to placement only and drop the cleanup mechanism and the dead sibling reference. No open ticket adjudicates it: `correct-the-v2-known-stale-surfaces-table-and-rout` (in_progress) only synthesizes its blackboard to clear `unsynthesized-draft-blackboard`, and `adjudicate-the-eight-premise-dead-v2-drafts` cites it only in a validation snapshot.

#### F52. `v2/identify-blocking-issues`: its subject, `relay project`, was removed and stayed removed

- shard: ks-25
- class: premise
- target: v2/identify-blocking-issues
- area: coga/architecture
- owner: ticket-relationships-and-ownership-have-no-mechani
- question: subject

The draft (status `paused`, owner `zach`, non-empty description) is framed as "When relay project creates an ordered list of steps … there should be a way to identify" cross-step dependencies. There is no `project.py` under `src/coga/commands/`, and `coga/contexts/coga/project-stage/SKILL.md` records that `coga project` was removed in PR #691 and, unlike `coga build` (restored in PR #701), "stayed gone". The subject that generates the step list therefore no longer exists. The residual ask — a `dependencies`-style ticket field — has no field in the ticket model (no `depends_on`/`blocked_by` in `src/coga/`), but is already cited and scoped by the open `blocked` ticket `ticket-relationships-and-ownership-have-no-mechani`, whose `## Description` quotes this draft ("`v2/identify-blocking-issues` asks for it directly"). That ticket is the natural home for a verdict: cancel this draft as premise-dead with the field question carried there, or rewrite it without the `relay project` framing.

#### F53. Parked launch-decomposition draft names moved and deleted surfaces

- shard: ks-32
- class: premise
- target: v2/cleanup-core-commands/launch-decomposition
- area: coga/architecture
- question: surfaces

Question 1 passes: the subject, `src/coga/commands/launch.py`, still exists and is still the shared runtime for `launch`/`ticket`/`megalaunch`. Question 2 fails. The draft's inventory and source plan name `commands/launch_script.py` ("another 460 lines"), but on `main` that module is `src/coga/launch_script.py` (815 lines; `src/coga/commands/launch_script.py` does not exist) and `coga/codebase` already describes it as the classify-and-run script seam. The draft's acceptance criteria and step 5 also require updating `commands/project.py` and list `project` among the callers that must use the extracted session path, but `src/coga/commands/project.py` does not exist — `remove-coga-build-and-project` (status `done`) deleted it, which the draft's own `## Context` half-acknowledges while its criteria still bind on it. The line count the design classifies (1,179) is now 4,101, so the responsibility inventory in `## Proposed Shape` no longer describes the file. Question 4 is not the answer: none of `src/coga/agent_session.py`, `src/coga/script_session.py`, or `src/coga/launch.py` exist, so nothing has delivered the split. No open ticket adjudicates the draft — the only non-terminal hits for its slug (`the-ticket-interview-never-asks-what-done-means`, `ticket-relationships-and-ownership-have-no-mechani`) cite it as an example, and `CLAUDE.md` / `coga/codebase` explicitly defer `megalaunch`'s placement to this parked design, so the draft is load-bearing and should be rewritten against current module names rather than left as-is.

#### F54. Playbook-rename draft names dead pre-rename surfaces throughout its scope plan

- shard: ks-33
- class: premise
- target: v2/rename-workflow-primitive-to-playbook
- area: coga/architecture
- question: surfaces

The subject (the `workflow` primitive, still canonical per `coga/contexts/coga/current-direction/SKILL.md` "Open rename (workflow → playbook)") exists, but the draft's entire "Scope / blast radius" list is written against the pre-rename tree and several of its named surfaces no longer resolve on `main`: the `--workflow` flag on `relay draft` (`relay draft` is **Gone** per the v2 README table; creation is `coga create` / `coga ticket`), a `relay retrofit` one-shot migration and a `retrofit.py` source module (no `src/coga/retrofit.py` or `src/coga/commands/retrofit.py` exists; `ls src/coga/` shows no retrofit module), `relay-os/workflows/` and `src/relay/resources/templates/relay-os/workflows/` (now `coga/workflows/` and `src/coga/resources/templates/coga/...`), and `example/relay-os/` (now `example/coga/`). The module list (`workflow.py`, `compose.py`, `bump.py`, `mark.py`, `launch.py`, `launch_script.py`, `ticket.py`, `validate.py`, `config.py`, `create.py`, `paths.py`, `recurring.py`, `automerge.py`, `retrofit.py`, `retire.py`) also names `automerge.py` and `retire.py`, neither of which is a module in `src/coga/` today. `## Context` is empty, so nothing in the draft's own body re-anchors the plan. The draft is a design ticket whose design step would rebuild the plan, so the surviving substance is the motive paragraph — which `coga/current-direction` already carries. No open ticket adjudicates this draft: grepping `coga/tasks/` for its slug hits only `simplify-ticket-format` (done, frontmatter-roles discussion) and the draft itself.

#### F55. Parked `document-contexts-as-prompt-payload-not-tags-princ` was delivered by the architecture context's "Attach or cite" section

- shard: ks-30
- class: premise
- target: v2/document-contexts-as-prompt-payload-not-tags-princ
- area: coga/architecture
- question: delivered

The draft's deliverable is a heading in the architecture context's prompt-composition section carrying three bullets: attach only contexts whose body the agent must read; copy a single fact into `## Context` rather than attaching the whole context; skills attach via workflow steps, not `contexts:`. `coga/contexts/coga/architecture/SKILL.md` on `main` now has `### Attach or cite` (line 976 onward) opening with "`contexts:` is prompt payload. Every attached context is composed whole (layer 4) into every launch of every step", defining **cite** as "name its path in the ticket's `## Context`, copy the few facts the step depends on, and leave the ref off `contexts:`", and giving the attach/cite test with the `approx_tokens` measurement; the third bullet is the primitives section's standing rule that skills are "Attached to **workflow steps**, not tickets" (line 57–60). That section landed under the done ticket `document-when-to-attach-a-large-context-versus-cit`, whose body names the `### Attach or cite` subsection as its output. The draft also cites `measure-relay-prompt-scope-and-agent-precision` for the 35.8 KiB → 25 KiB evidence, but it inlines that figure, so the citation is provenance only. The in_progress ticket `redo-documentation-dir-and-merge-it-with-context-b` lists this draft merely as an "overlap input" to recheck ("do not close them during this design step"), which is not adjudication, so no `owner:` applies.

#### F56. `v2/log-timestamps-need-seconds-and-timezone-for-unamb`: half its surfaces are dead and that half is already delivered

- shard: ks-25
- class: premise
- target: v2/log-timestamps-need-seconds-and-timezone-for-unamb
- area: coga/codebase
- question: surfaces

The draft (status `draft`, non-empty description) names two surfaces. The first still resolves after the rename: `src/coga/logfile.py` `append_log` still writes `datetime.now().strftime("%Y-%m-%d %H:%M")` — minute resolution, naive local time, no offset — and `last_activity` still parses that exact format, so the core ask (seconds + timezone) is undelivered. The second surface is gone: the draft says `validate.py`'s stuck-in-progress detection "uses file **mtime**" and asks to "reconcile" it with `last_activity`; on current `main` `validate.validate_task`'s `stuck-in-progress` branch already calls `logfile.last_activity(cfg, ref.id_slug)` and compares it to `now` in the same naive-local frame, so the two notions of "last activity" no longer disagree. Every citation is a `src/relay/…` path with pinned line numbers (`logfile.py:20`, `:26-47`, `validate.py:312-323`), all of which have moved. Under README question 4, the reconciliation half has shipped and the draft should be narrowed to the timestamp-format remainder (and re-cited by symbol per the `_template` rule); no open ticket names this slug.

#### F57. Parked `add-dev-testing-setup-skill` names a deleted consumer skill and a vanished checkout, and its discovery notes predate CI

- shard: ks-30
- class: premise
- target: v2/add-dev-testing-setup-skill
- area: coga/codebase
- question: surfaces

The draft (status `paused`, non-empty description) still has a live premise — no `dev/testing-setup` skill or `dev/testing` context exists (`coga/contexts/dev/` holds only `code`, `coga/skills/` has no `dev/` tree) — but the surfaces its confirmed implement plan names no longer resolve. Plan step 3 updates consumers `code/implement`, `code/implement-and-pr`, `code/self-qa`; `coga/skills/code/` today is `address-pr-comments design implement open-pr review-design self-qa`, so `code/implement-and-pr` is gone. Its `## Dev` checkout is dangling: no local or remote branch `dev-testing-contract` (`git branch -a`) and `/home/n/Code/codex/relay-dev-testing-contract` does not exist, so any work started there is unrecoverable and the plan must restart from `main`. The `relay-os/skills/...` and `relay-os/contexts/...` paths are pre-rename (now `coga/skills/`, `coga/contexts/`). The plan's discovery finding "**no CI exists** — local commands are the only gate" is also false on `main`: `.github/workflows/release.yml` exists (publish-only, no test gate), as the done ticket `no-context-records-the-ci-posture-publish-only-rel` already records, so the contract's "CI parity" section would need to be written against a real workflow. No open ticket adjudicates this draft (grep of `coga/tasks/` for the slug hits only that done ticket).

#### F58. Parked `onboarding-v2-first-run-experience-after-removing` assumes `coga build` is gone, but it was restored

- shard: ks-30
- class: premise
- target: v2/onboarding-v2-first-run-experience-after-removing
- area: coga/current-direction
- question: subject

The draft's premise is stated in its first sentence: design first-run onboarding "now that `coga build` (the packaged `coga-build` onboarding ticket) and `coga project` are being removed as never-used entry points (see `remove-coga-build-and-project`). After that removal, `coga chat` (orient) is the single conversational door". That removal was half-reversed. `coga/contexts/coga/project-stage/SKILL.md` ("Bias toward deletion") records that "`coga build` was removed with `coga project` (PR #691) and deliberately restored three days later (PR #701, 'we want the build back with the skills; it was useful'), while `coga project` stayed gone". On `main` today the alias is live in both twins (`build = "launch coga-build"` at `coga/coga.toml:166` and `src/coga/resources/templates/coga/coga.toml:147`, plus `src/coga/aliases.py:59`), the packaged onboarding ticket exists at `src/coga/resources/templates/coga/tasks/coga-build.md`, and the `build/onboarding.md` workflow exists under both `coga/workflows/build/` and `src/coga/resources/templates/coga/workflows/build/`. So `coga chat` is not the single door and there is no post-removal gap to design for; the draft's open questions ("should onboarding live inside `bootstrap/orient`… what must a first session produce") would need rewriting as "what does `coga-build` still lack", if anything. The cited `remove-coga-build-and-project` is `done`, so it is evidence rather than an open owner, and no open ticket adjudicates this draft (slug grep hits only that done ticket).

#### F59. Parked `op-service-account-auth-to-skip-op-read-prompt` is already answered by the `coga/secrets` context

- shard: ks-30
- class: premise
- target: v2/op-service-account-auth-to-skip-op-read-prompt
- area: coga/secrets
- question: delivered

The draft asks Coga to "support resolving `op://` references via a 1Password service-account token", with a verify list of: confirm `OP_SERVICE_ACCOUNT_TOKEN` reaches the `op read` child and `build_launch_env` does not strip it; document the setup; keep a bad token fail-loud. `coga/contexts/coga/secrets/SKILL.md` on `main` already carries every item: "`config.build_launch_env()` starts from the full parent environment and scrubs only the source variables an `env:VAR` ref names. It does not special-case `OP_SERVICE_ACCOUNT_TOKEN`, so the token normally survives"; "The `op` CLI auto-uses `OP_SERVICE_ACCOUNT_TOKEN` while it remains set, so no coga code changes are normally needed for headless auth — exporting the token in the job process is enough"; the alias rule (`OP_SERVICE_ACCOUNT_TOKEN: env:OP_SERVICE_ACCOUNT_TOKEN` restores it, `TASK_OP_TOKEN: env:OP_SERVICE_ACCOUNT_TOKEN` removes it); and a setup/verification procedure under "Adding a headless secret" (create the item in the automation vault, verify with `coga secret get` in a clean env where the token is the only credential). The draft's acceptance ("an operator can export a service-account token and have `op://` references resolve with no prompt") is thus the documented default, and `config.py` has no token-specific code to add (`grep OP_SERVICE_ACCOUNT_TOKEN src/coga/config.py` is empty by design). The canceled ticket `no-durable-runbook-covers-running-coga-headless` reached the same reading ("likely premise-dead on its own terms ... which is that draft's entire ask") but, being canceled, is not an open owner. The only residue not on `main` is an automated test that the token survives `build_launch_env` (no test file mentions `OP_SERVICE_ACCOUNT_TOKEN`); if the author wants that, the draft should narrow to it. Note the sibling `v2/let-notification-webhooks-resolve-1password-refere` declares itself blocked on this draft; the block dissolves with it.

#### F60. Parked `add-a-first-class-relay-config-directory-for-machi` builds on the removed `mode: script` env-var set and predates the 1Password secrets model

- shard: ks-30
- class: premise
- target: v2/add-a-first-class-relay-config-directory-for-machi
- area: coga/secrets
- question: surfaces

The problem the draft records is still real on `main`: the interim `.secrets/` holding dir is still the only home for a service-account JSON key (`.gitignore` lines 34–36 keep the "interim home for SA keys etc." rule), and the bundled `coga/google-calendar` skill still reads `[calendar].service_account_file` from `coga.local.toml` as a path (`src/coga/resources/templates/coga/bootstrap/skills/coga/google-calendar/gcal.py:81-99`). No `COGA_CONFIG_DIR` or equivalent exists (`src/coga/task_env.py` exports only `COGA_COGA_OS_ROOT` / `COGA_REPO_ROOT` plus task vars). But the draft's delivery surfaces are pre-rename and one is gone: it wants the path exposed "in the `mode: script` env var set, alongside `RELAY_RELAY_OS_ROOT`", and the README's known-stale table records `mode:` ticket frontmatter and child `mode: script` tasks as **Gone** (the deterministic half is now a ticket's sibling `ticket.py`, and the vars are `COGA_*`); `relay init` / `relay.local.toml` / `relay-os/.config/` are rename-cohort names. It also predates the model `coga/contexts/coga/secrets/SKILL.md` now fixes — secrets are per-ticket `op://` refs resolved at launch from a single automation vault, and "`op://` is not understood in config at all" — so a rewrite has to decide whether a credential *file* belongs in a config directory at all or should instead be an `op://` document field materialized by the consuming skill. No open ticket adjudicates this draft (grep of `coga/tasks/` for the slug returns only the draft itself).

#### F61. `v2/issue-inbox-slack`: names the replaced `relay panic` surface, and the blocker-reason half has shipped

- shard: ks-25
- class: premise
- target: v2/issue-inbox-slack
- area: coga/usage
- question: surfaces

The draft (status `paused`, owner `zach`, non-empty description) asks that "panics carry the blocker reason and required action, dones carry the outcome" and that "every post links the next step: the relay command to run or a link to the ticket file". `relay panic` is in the README's known-stale table as **Replaced** by `coga block`, so the surface does not resolve as written. On current `main` the replacement already delivers part of the acceptance: `commands/block.py` posts `🛑 {blocker} blocked *{slug}* "{title}": {reason}` (the reason is mandatory, `--reason cannot be empty`), and `commands/mark.py` posts `🎉 {finisher} finished *{slug}* "{title}": {step} → done{suffix}` with any `--message` as the outcome. What is not delivered is the "next step" link — neither post names the command to run (`coga unblock …`) or a link to the ticket file; only the terminal `echo` says "(owner X needs to answer)". Per README question 4 the draft should be narrowed to that remainder and re-worded from `panic` to `block`. Owner search: only the done tickets `simplify-ticket-format` and `activation-does-not-resolve-step-1-s-assignee-role` list the slug (in migration tables); no open ticket adjudicates it.

#### F62. `v2/minimal-ci-run-pytest-on-prs-and-tags`: premise line and named surfaces no longer match `main`

- shard: ks-21
- class: premise
- target: v2/minimal-ci-run-pytest-on-prs-and-tags
- area: dev-code / coga/codebase
- question: surfaces

Q1 passes: no PR/push `pytest` job exists on `main`, so the subject is alive. Q2 fails on three counts. (a) The opening premise "There is no CI today (`.github/workflows/` does not exist)" is false: `.github/workflows/release.yml` (dated 2026-06-26 in the tree) exists and is a publish-only workflow — `release: published` / `workflow_dispatch` → `uv build`, `twine check`, PyPI/TestPyPI Trusted Publishing — which `coga/contexts/coga/codebase/SKILL.md` now records under "CI posture: publish-only release workflow, no test gate" and which names this draft as "the parked design" that would change the posture. (b) The draft cites `relay/roadmap` and `relay/codebase`; both are pre-rename names (README rename table: `relay-os/contexts/…` → `coga/contexts/…`), resolving today to `coga/roadmap` and `coga/codebase`. (c) The paired ticket `one-line-install` no longer exists anywhere under `coga/tasks/` — it was deleted in commit `f3a226ff7` (`relay-os/tasks/one-line-install/`), so "coordinate with `one-line-install`" points at nothing (provenance-only, not required substance, so not a Q3 failure). Q4 is a partial delivery worth naming in the same verdict: the draft's "optional follow-up" — "a release job that builds the wheel / publishes to PyPI on a version tag" — is exactly what `release.yml` already does, so the remainder is only the PR/push `pytest` matrix job. The done ticket `no-context-records-the-ci-posture-publish-only-rel` (branch `ci-posture`, delivered as the `coga/codebase` subsection above) explicitly chose to "Leave the three stale v2 tickets as they are", so no open ticket adjudicates this draft; `four-parked-tickets-carry-premises-that-have-since` (done) only mentions it in passing. The author's verdict is to narrow the body to the pytest-on-PR job with the corrected premise (release workflow exists; local `PYTHONPATH=$PWD/src python3.12 -m pytest` + `coga validate` is the current gate) and drop the shipped release-job follow-up, or cancel if the publish-only posture is the accepted one.

#### F63. `v2/fix-windows-cli-import-crash`: the tier-1 surface list is incomplete since `coga.git` gained a top-level `fcntl` import

- shard: ks-21
- class: premise
- target: v2/fix-windows-cli-import-crash
- area: dev-code / src/coga
- question: surfaces

Q1 passes: nothing on `main` guards any Unix-only import, no doc declares WSL the supported Windows path (grep of `docs/`, `README.md`, `coga/contexts/coga/codebase`, `coga/contexts/dev/code` for `wsl`/`windows` finds nothing relevant), so the subject — every `coga` command crashing at import on native Windows — is alive and undelivered (Q4 also passes). Q2 fails on the draft's root-cause inventory, which it dates "verified against source on 2026-07-18": it states `fcntl` "has a single use site: `repl_supervisor.py:430`" and sketches tier 1 as guarding `repl_supervisor.py` and `commands/megalaunch.py` "so import always succeeds". On current `main`, `src/coga/git.py:112` also has a top-level `import fcntl`, used by `fcntl.flock` for the local state-publication barrier lock (`git.py` ~lines 242–252); it was introduced in commit `5c91ed748` (2026-09-04, PR #747, "Megalaunch activates picked tickets before its preflight checks refuse them"), after the draft's verification date. `cli.py:13` imports `coga.git` directly and 29 modules under `src/coga/` import it, so the eager chain now breaks on `git.py` before it ever reaches `commands/block.py` → `repl_supervisor.py`. The named surfaces still resolve (`repl_supervisor.py:20` `import fcntl`, `megalaunch.py:23–24` `termios`/`tty`) but the surface set is no longer sufficient: an implementer who follows the tier-1 sketch literally ships a guard that still fails `coga --help` on Windows with `ModuleNotFoundError: No module named 'fcntl'` — from a different module — and the draft's acceptance ("`coga --help` and a non-interactive command succeed") is unreachable. The `flock` site is also different in kind from the `TIOCSWINSZ` ioctl: it is a correctness lock on every checkout's state publication, not interactive-only machinery, so it needs a portable substitute (e.g. `msvcrt.locking`) or a documented no-lock Windows mode rather than a "use WSL" error. Secondary: the draft's "there is no platform-matrix CI today" is now recorded knowledge in `coga/codebase` ("CI posture: publish-only release workflow, no test gate"). No open ticket adjudicates this draft: the only non-Dream reference is `no-context-records-the-ci-posture-publish-only-rel` (done), which cited it as one of three stale re-derivations and left it as-is. The author's verdict is to rewrite the tier-1 inventory against current `main` (three modules, two kinds of use) or cancel in favour of declaring WSL the supported path in `coga/codebase`.

#### F64. Parked `capture-report-series-google-drive-folder-ids-in-a` outlived the report series it was written for

- shard: ks-30
- class: premise
- target: v2/capture-report-series-google-drive-folder-ids-in-a
- area: docs/gdrive-mcp
- question: subject

The draft's subject is a live doc series — "the eight `*-report` tickets plus `relay-additions` and `bucket-comparison-document`" that kept re-resolving the same Drive folder IDs. None of those tickets exists under `coga/tasks/` today (`ls coga/tasks coga/tasks/v2 | grep -i 'report\|relay-additions\|bucket-comparison'` returns only this draft plus two unrelated tickets), and `git log --all --diff-filter=D --name-only` shows them retired from the pre-rename tree (`relay-os/tasks/dust-report/`, `relay-os/tasks/relay-additions/`, `relay-os/tasks/relay-additions-spec/`, …). No live ticket, context, or skill cites either folder ID (`grep -rl 1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT coga/ src/ docs/` hits only the draft), and the one Drive context on `main`, `coga/contexts/docs/gdrive-mcp/SKILL.md` (48 lines), records tool semantics only, no folder facts. The draft is self-contained — it inlines all three IDs and the My-Drive-root trap, so citations pass — and it already says the answer "may not be worth durably capturing at all"; with the series retired the recurring-wrong-answer cost that motivated it has stopped accruing, so the author's verdict is between cancel and narrowing to a marketing/docs context for any future series. No open ticket adjudicates it (slug grep returns only the draft).

#### F65. Parked container/VM launch draft names dead relay-era primitives as the model it must preserve

- shard: ks-16
- class: premise
- target: v2/launch-tasks-in-container-or-vm
- area: launch-internals
- question: surfaces

The subject (running a launched agent somewhere other than the operator's machine) still exists and nothing on `main` delivers it — `src/coga/config.py` has no `[runners.<name>]` table and no `runner =` key, and `coga launch` has no `--runner` flag. The draft fails the README's second question, though: the "rest of the relay model" it says must stay unchanged is spelled as "`bump` / `feed` / `panic` semantics", and two of those three are dead surfaces. `relay panic` is **Replaced** per the README's known-stale table (`coga block --task <slug> --reason "…"`), and `relay feed` is not in that table at all: `git log -S "def feed"` shows it was renamed to `relay slack` (commit `38ffbd742`), and today `src/coga/commands/slack.py` is a notification/channel command, not a task-feedback primitive an in-container agent would call back through. The draft's "Bump / feed / panic from inside the container" section, its "Lockfile is local to the working tree … stale local locks" concurrency premise (no per-task launch lockfile is described in `coga/launch-internals`; concurrency is gated by `in_progress` claims and the task-tree snapshot invariants there), and the `relay.toml` / `relay launch` names all need re-derivation against `coga block`, `coga bump`, and the current launch contract before any step in it can be trusted. Its citation of `token-budget-aware-idle-execution-of-low-priority` is a "see also", not required substance (the ticket no longer exists under `coga/tasks/`; only this draft and `v2/autotrigger-ticket-type` mention it). No open ticket adjudicates this draft: grepping `coga/tasks/` for the slug hits only the draft itself.

#### F66. `v2/register-a-real-domain-for-relay` pairs itself with three launch-gate tickets that no longer exist

- shard: ks-28
- class: premise
- target: v2/register-a-real-domain-for-relay
- area: marketing
- question: surfaces

The draft (`status: draft`, non-empty description, Relay-era) fails question 2 of `coga/tasks/v2/README.md`. Its subject — a real product domain — is still open (no non-GitHub product URL appears anywhere in `README.md`, `docs/*.md`, or `coga/contexts/marketing/`; the README install path is `uv tool install coga` / `pip install coga` with no landing page), so question 1 passes. But every surface it names is dead: it is framed as a "Wave 1 launch-gate item" pairing with `one-line-install`, `improve-readme-and-doc`, and `marketing/launch-relay-product-launch-comms`, and none of those exists under `coga/tasks/` today (`git log --all --diff-filter=D` shows `coga/tasks/marketing/launch-relay-product-launch-comms.md` deleted in `43c149f4`; the other two have no file and no deletion record). It also asks for "Relay" copy and the "`one-line-install` story", both pre-rename names, and the current marketing inventory already classifies it as stale: `coga/contexts/marketing/map/SKILL.md` line 103 lists it as a "Historical Relay-era proposal; stale names/dependencies need checking if the idea is selected. No domain purchase is authorized by inventory work." Question 3 is a provenance-only pairing (no required substance is delegated), and question 4 finds nothing delivered. The author's verdict is whether the domain work is still a launch gate under the current marketing plan; if so the draft needs rewriting against `coga/contexts/marketing/map` rather than the deleted Wave 1 cluster. No open ticket adjudicates it: no task file other than the draft itself mentions its slug.

#### F67. `v2/autotrigger-ticket-type` delegates the recurring half of its premise to four tickets that no longer exist

- shard: ks-11
- class: premise
- target: v2/autotrigger-ticket-type
- area: recurring
- owner: adjudicate-the-eight-premise-dead-v2-drafts
- question: citations

Questions 1 and 2 pass: the subject (a schedule/idle unification) is still unbuilt, and the one code surface the draft's "key insight" rests on survives under the rename — `mark_in_progress` is `src/coga/mark.py:754` and `coga launch` still calls it (`src/coga/commands/launch.py:1780`, `:2608`). Question 3 fails. The draft's body says "the recurring side this concept absorbs" is not in the draft but in a "live recurring-hazard cluster to read instead": `detect-recurring-runs-that-mark-done-without-advan`, `recover-recurring-runs-orphaned-when-the-superviso`, `fix-recurring-templates-not-instantiated`, `enforce-mode-auto-for-recurring-templates`; the evaluator review likewise defers the "re-stock misfires today" caveat to those three. None of the four exists under `coga/tasks/` (bare `.md` or `<slug>/ticket.md`, checked 2026-09-21), and `token-budget-aware-idle-execution-of-low-priority` — the draft's source for the `idle` trigger — is also absent; the only cited slug that resolves is `v2/enforce-a-prompt-token-budget-in-compose`, which the draft itself says is "adjacent but not this". `coga/tasks/v2/README.md` names this exact draft as the precedent for a citation fix-up that rotted the same way its original did. The required substance is what the recurring re-stock actually does and how it misfires — the draft's "recurring = re-stock after done" line is the whole recurring half of the model and currently rests on deleted tickets. The open in_progress ticket `adjudicate-the-eight-premise-dead-v2-drafts` already rules it "keep-with-follow-up — verified" and says the four retired hazard sources are recoverable from git history, so this is already ticketed; the verdict (inline the recovered substance or narrow to the one-shot/idle half) stays the author's.

#### F68. `coga recurring ack` draft names an engine API and skill that are not on main

- shard: ks-12
- class: premise
- target: v2/coga-recurring-ack
- area: recurring
- question: surfaces

The draft's `## Context` states as fact that "the reminder engine ships `read_ack` / `record_ack`" and points implementers at "the `coga/reminders` SKILL", and its `## Description` scopes the command as a wrapper over `record_ack()` and the engine's `period_for(today)`. None of those surfaces resolve on current `main`: `grep -rn "record_ack\|read_ack\|period_for" src/ coga/ tests/` hits no source file (`src/coga/reminders.py` does not exist; the only `period_for` match is the unrelated `_exact_recurring_period_for_launch` in `src/coga/commands/launch.py`), and `coga/contexts/coga/reminders` / a `coga/reminders` skill are absent. The engine the draft depends on was shipped by `ship-a-shared-recurring-reminder-engine-battery` (now `status: canceled`; its own body records PR #652 "closed unmerged on 2026-07-27") and is being re-cut by the in_progress retry `v2/ship-a-shared-recurring-reminder-engine-battery`, whose description explicitly says the first attempt's mistake was "an attempt to add more commands to Coga" — i.e. the retry may well not expose the `read_ack`/`record_ack` API this draft wraps, and the ack shapes it pins (`Acked: YYYY-MM`, `Acked: YYYY-MM-DD`) live in the downstream `FastJVM/admin` reminders, not in this repo. The draft's "Depends on the reminder engine landing" line acknowledges the dependency but the body reads its API as already present. No open ticket names the slug `coga-recurring-ack`, so it has no owner. Verdict is the author's (owner `zach`): hold until the retry lands and rewrite against whatever ack surface it actually exposes, or cancel if the retry's smaller boundary drops the CLI-verb idea.

#### F69. Live draft `recurring-scan-aborts-on-an-unloadable-workflow` was already delivered by PR #814

- shard: ks-12
- class: premise
- target: recurring-scan-aborts-on-an-unloadable-workflow
- area: recurring
- question: delivered

Not a parked `v2/` draft — it sits live at `coga/tasks/recurring-scan-aborts-on-an-unloadable-workflow.md` with `status: draft` — so this is reported for the human's adjudication rather than as a README premise pass. Its single fix ("add `WorkflowError` to that `except` tuple" in `_create_at_slug`, plus a regression test) is already on `main`: `src/coga/recurring.py:1457` reads `except (TaskValidationError, ValueError, WorkflowError) as exc:`, and `git log -S` attributes the change to commit `29b559f41` "Recurring sweep aborts and orphans a deleted done period task when a template's workflow is missing (#814)". No other task file references the slug. The draft's acceptance criterion (a bad `workflow:` lands in `scan.errors` and later templates are still created) is what #814 addressed; the author can confirm the test shape and cancel with `already delivered by #814`, or narrow it to anything #814 left out (the draft notes "whether the unattended runner catches it higher up was not checked").

#### F70. `v2/skill-update-aborts-on-uncommitted-log-file` targets a launcher path that no longer exists

- shard: ks-04
- class: premise
- target: v2/skill-update-aborts-on-uncommitted-log-file
- area: skills / launch
- owner: adjudicate-the-eight-premise-dead-v2-drafts
- question: subject

The draft asks to fix "the launcher so a script step starts against a clean-enough tree" by committing the `coga/log.md` append in `run_script_mode` (`src/coga/commands/launch_script.py:216`), mirroring `launch.py:984-991`. That subject is gone: there is no `src/coga/commands/launch_script.py` and no `run_script_mode` anywhere under `src/coga/` (`grep -rn run_script_mode src/coga` is empty), and the `mode: script` step shape it describes is in the v2 README's known-stale table. `recurring/skill-update` now runs as the reserved `ticket.py` sibling (`coga/recurring/skill-update/ticket.py` calls `run_recipe(cfg, "skill-update", [])` then `coga bump`), and the agent-launch path commits its audit append via `git.sync_log` before spawning (`src/coga/commands/launch.py:3594-3610`). The secondary residue the draft names is still live: `_assert_no_unmerged_paths` (`src/coga/skill_manager.py:542`) still filters on `--diff-filter=U` only, so an ordinary dirty tracked file can still reach `_checkout` (`skill_manager.py:571`, `git checkout -B coga/skill-update <base>`) and surface a raw git abort — any verdict should carry that residue rather than drop it. The open ticket `adjudicate-the-eight-premise-dead-v2-drafts` (status `in_progress`) already tables this draft as "cancel — verified obsolete primary fix, with live residue" citing PR #635 / #670, so this is already ticketed.

#### F71. `v2/validate-skill-md-frontmatter-conformance-not-just` names the removed skill `script:` field and relay-era paths

- shard: ks-04
- class: premise
- target: v2/validate-skill-md-frontmatter-conformance-not-just
- area: skills / validate
- question: surfaces

The draft's subject is still live: `coga validate` still checks only that skill refs resolve (`src/coga/validate.py:1065-1113` `_check_refs` emits `broken-skill`/`broken-context` on `resolve_skill_path`/`resolve_context_path` being `None`) and nothing in `validate.py` loads or inspects `SKILL.md` frontmatter; `Skill.load` (`src/coga/skill.py:23-31`) is the only parser and still raises `ValueError` on missing/non-mapping frontmatter, and `_skill_ref_for_dir` (`src/coga/skill_manager.py:1625`) is where that error is swallowed. Two of the surfaces the draft depends on do not resolve, though. (1) One acceptance bullet says to "flag the proprietary `script:` field explicitly" — a skill-frontmatter `script:` (the pre-#427 script-vs-agent deduction: "is_script_launch -> a step skill's `script:`") no longer exists: no `SKILL.md` under `coga/skills/` or the packaged bootstrap tree carries `script:`, no code under `src/coga/` reads a skill `script` key, and the v2 README's known-stale table records that the deterministic half is now the ticket's sibling `ticket.py`. That bullet is dead and should be dropped rather than modernized. (2) Every code path is relay-era: `src/relay/validate.py` (`_check_refs 533-592`), `src/relay/skill.py`, `src/relay/skill_manager.py:882-886`, `relay-os/skills/_template/SKILL.md` — all renamed per the README table, and the line numbers have moved (refs check now at 1065, swallow at 1625; the "bet" line is `coga/skills/_template/SKILL.md:9`). `relay skill lint` never existed and `coga skill` today has no `lint` subcommand. The draft is a candidate for narrowing/rewrite against current names rather than cancellation; no open ticket adjudicates it (grep of `coga/tasks/` for the slug, "frontmatter conformance", and "skill lint" finds only the draft itself and an unrelated table row in `redo-documentation-dir-and-merge-it-with-context-b`).

#### F72. Parked per-launch worktree isolation draft's stated hazard is now serialized by the publication barrier

- shard: ks-16
- class: premise
- target: v2/reintroduce-per-launch-worktree-isolation
- area: sync
- question: delivered

The draft's goal is "several agents on different tickets run from one clone without their `coga bump`/`mark` syncs contending a single `.git/index` / stash stack", and its `## Context` says the re-accepted limitation "concurrent launches in one clone share an index/stash stack" is documented in `coga/sync`. The current `coga/contexts/coga/sync/SKILL.md` no longer says that: "Within one checkout, Coga's own publishers and lifecycle ticket writes serialize on the checkout-local advisory admission/publication barrier (`git.state_publication_barrier`, an `fcntl.flock` on a per-checkout lock file …), so two Coga commands racing on the index/stash stack is not the hazard. What stays unserialized is the shared *working tree* itself: an agent session and a recurring sweep both editing one checkout's files. Run concurrent sessions from separate clones or worktrees, or sequentially". The index/stash contention the draft was written to remove has therefore been delivered by a different mechanism, and the remaining working-tree hazard is addressed on the agent side rather than in launch: the packaged `code/implement` skill now instructs the agent to `git worktree add ../coga-<branch-name> -b <branch-name> main` at step start, with `v2/propagate-local-coga-config-into-worktrees` (in review, PR #851) seeding local config into that checkout. What is *not* delivered is Coga itself creating and tearing down a worktree per launch — `_enter_launch_worktree`/`_cleanup_launch_worktree` are absent from `src/coga/commands/launch.py`, only `git.stranded_product_paths` survives from v1 — so the draft is at most narrowable to that automation, and the propagate ticket already scopes "future internal worktree automation" to it. Its five v1 failure-mode bullets and the recoverable SHAs (`fb79d3f9`, `56c46890`, `cb555c9e^`) are inlined, so citations pass; `v2/auto-persist-dirty-launch-worktrees-to-pushed-bran` is `canceled` and points back at this draft as its successor, and `launch-ignores-the-recorded-worktree-stranding-bla` (done) cites it as "prior thinking only", so no open ticket adjudicates it.

#### F73. Parked clean-uncommitted-work draft is half-delivered by the catch-all exit sweep

- shard: ks-16
- class: premise
- target: v2/clean-uncommitted-work
- area: sync
- question: delivered

The draft (one paragraph, relay-era) asks for "a reliable way to ensure other work doesn't get stranded as uncommitted" beyond the auto-commit on ticket creation. For everything under `coga/`, that exists on `main`: `coga/contexts/coga/sync/SKILL.md` describes the catch-all sweep — "`sync_coga_state` commits every dirty `coga/` path and, on any branch, lands the non-union ones on the control branch — that is its pre-existing contract", runs it as the exit sweep of every state-changing command (the codebase context notes it "still loads with `require_user=False` and can publish dirty Coga state" even after an actor failure), and lists it as one of the three Coga Git publishers that take the state publication barrier. The half that is not delivered is deliberately so: product code outside `coga/` is never auto-committed, and the written rule is the operator's pre-command commit (`dev/code`, cited from the codebase context's "pre-command commit rule"; the sync policy section says "Commit review work yourself before running a mutating Coga command"). The draft names neither scope, so it cannot be told apart from the shipped sweep without the author saying whether "other work" meant Coga state (delivered) or product code (a policy the repo has since chosen not to automate). No open ticket adjudicates it: grepping `coga/tasks/` for `clean-uncommitted-work` hits only the draft.

### Phase 2 result

- Phase 2 knowledge scan: **reported** — 34/34 leaf shards wrote a completion line (distinct ids; 0 `incomplete`, 0 supersessions), 80 finding blocks on disk merged to 73 (18 extract, 14 stale, 13 gap, 28 premise). Scan directory deleted after merge.

### Class: drift (Phase 3 contract audit)
Merged from the Phase 3 contract audit (10 shards, 22 blocks on disk, 12 after de-duplication; three blocks restate Phase 2 findings and are folded into them: ca-04 marketing/map clarity links → F30, ca-02 five-threads bullet → F22, ca-02 validate baseline → F20).

#### F74. `address-pr-comments` cluster: live `extension-model`/`sync` contexts diverged from packaged twins, no packaged recurring/bootstrap copies, no default alias, audit doc omits the template

- shard: ca-01, ca-02, ca-06, ca-09, ca-10 (merged 7 blocks)
- class: drift
- target: coga/contexts/coga/{extension-model,sync}/SKILL.md; coga/recurring/address-pr-comments/ticket.md; coga/bootstrap/address-pr-comments/ticket.md; docs/cli-extension-audit.md
- area: coga/recurring / extension-model / sync
- owner-pr: #857 (address-pr-comments-sweep) — its diff adds `DEFAULT_ALIASES["address-pr-comments"]`, the packaged `bootstrap/address-pr-comments/ticket.md` and `recurring/address-pr-comments/ticket.md`, the packaged `extension-model` and `sync` twins, `docs/cli-extension-audit.md`, and `tests/test_packaging.py`; `tests/test_packaging.py::test_live_and_packaged_copies_stay_identical` fails on `main` until it merges

_ca-01 — extension-model live/packaged twin diverged over `address-pr-comments`:_ Live `coga/contexts/coga/extension-model/SKILL.md` lines 141-143 say "`resolve-conflicts` and `address-pr-comments` are the shipped agent-backed forms; each pairs a stateless command ticket with a recurring template that only delegates to it", and the table row at line 262 lists "bootstrap targets such as `resolve-conflicts` and `address-pr-comments`". The packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md` (line 141 and line 260) names only `resolve-conflicts` in both places; `cmp` reports the pair differs at byte 8193 and `diff` shows those two hunks are the whole difference. The pair is derived by `tests/test_packaging.py` (the packaged path appears at line 59) and `coga/contexts/coga/extension-model/SKILL.md` is not in `INTENTIONALLY_DIVERGENT_TWINS` (lines 146-161 list only `coga/.gitignore`, `coga/coga.toml`, `coga/log.md`), so the byte-identity test fails. The live copy was last changed by `a5420200e` (2026-09-20, "Sync coga state") without the packaged copy; the underlying fact is also only half true for the package: `coga/bootstrap/address-pr-comments/` and `coga/recurring/address-pr-comments/ticket.md` exist in the live repo, but neither `src/coga/resources/templates/coga/bootstrap/address-pr-comments/` nor `src/coga/resources/templates/coga/recurring/address-pr-comments/` exists, so `address-pr-comments` is repo-local, not "shipped". Either the packaged twin must gain the same sentences (and the package ship the bootstrap/recurring pair) or the live wording must stop calling it shipped.

_ca-10 — Live/packaged twin drift: coga/contexts/coga/extension-model/SKILL.md:_ `cmp` reports `coga/contexts/coga/extension-model/SKILL.md` (17984 bytes) and `src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md` (17839 bytes) differ, and `.venv/bin/python -m pytest tests/test_packaging.py -q` fails on exactly this pair (`test_live_and_packaged_copies_stay_identical`: "have drifted; edit both copies together", 1 failed / 12 passed). Two hunks differ: live lines 141-143 read "`resolve-conflicts` and `address-pr-comments` are the shipped agent-backed forms; each pairs a stateless command ticket with a recurring template that only delegates to it. `open-pr` is a registered" where packaged line 141 reads "`resolve-conflicts` is the shipped agent-backed form. `open-pr` is a registered"; and the live line 262 table row "**Stateless command tickets** | package/repo bootstrap targets such as `resolve-conflicts` and `address-pr-comments`; ..." where packaged line 260 lists only `resolve-conflicts`. The live copy is newer: `git log -1` gives `a5420200e 2026-09-20 Sync coga state` for the live path versus `2a7e02908 2026-09-14 Dream 2026-W36 extract backlog: 18 findings Phase 4 could not consume (#795)` for the packaged path; commit a5420200e touched only the live tree (both live contexts plus `coga/bootstrap/address-pr-comments/ticket.md` and `coga/recurring/address-pr-comments/ticket.md`) and no `src/` file. Neither working copy is dirty, so the drift is committed on `main`. The live path is not in `INTENTIONALLY_DIVERGENT_TWINS` (that set is only `coga/.gitignore`, `coga/coga.toml`, `coga/log.md`), so per `CLAUDE.md` and the `coga/codebase` context the two copies must be byte-identical.

_ca-10 — Live/packaged twin drift: coga/contexts/coga/sync/SKILL.md:_ `cmp` reports `coga/contexts/coga/sync/SKILL.md` (89956 bytes) and `src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md` (89683 bytes) differ; `tests/test_packaging.py::test_live_and_packaged_copies_stay_identical` stops at the first drifted pair (extension-model) but this pair fails the same byte-identity rule. Three hunks differ, all in the notification-surface enumeration: live lines 130-132 add a bullet "`recurring/address-pr-comments` — the same shape on a daily cadence. The period template emits nothing; its `delegate: bootstrap/address-pr-comments` target replies on GitHub threads and posts one `coga slack` roll-up per run." that the packaged copy lacks; live lines 134-137 say "Those four complete the enumeration: `coga/recurring/` ships seven templates — `address-pr-comments`, `autoclose-merged`, `blocker-reminders`, `branch-sweep`, `dream`, `resolve-conflicts`, `skill-update`" where packaged lines 131-134 say "Those three complete the enumeration: `coga/recurring/` ships six templates" without `address-pr-comments`; live lines 141-145 say "several already do ... `resolve-conflicts` and `address-pr-comments` are silent as period templates while the bootstrap delegates they run post their roll-ups" where packaged lines 138-142 say "two already do ... `resolve-conflicts` is silent as a period template while the `bootstrap/resolve-conflicts` delegate it runs posts its roll-up". The live copy is newer: `git log -1` gives `a5420200e 2026-09-20 Sync coga state` (live) versus `046dd8dc5 2026-09-17 State which branch is canonical for machine-generated Coga state (#824)` (packaged). Neither working copy is dirty. The live path is not in `INTENTIONALLY_DIVERGENT_TWINS`, so the pair is required to be byte-identical by `tests/test_packaging.py` and the `coga/codebase` context.

_ca-02 — live `coga/sync` context diverged from its packaged twin (address-pr-comments edit swept to main without the packaged copy):_ `coga/contexts/coga/sync/SKILL.md` and its packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md` are no longer byte-identical (`cmp` differs at line 130). The live copy, lines 130-146, adds the `recurring/address-pr-comments` bullet to the silent lifecycle surface, says "`coga/recurring/` ships seven templates — `address-pr-comments`, `autoclose-merged`, ..." and "several already do ... `resolve-conflicts` and `address-pr-comments` are silent as period templates"; the packaged copy still reads "Those three complete the enumeration: `coga/recurring/` ships six templates" and "two already do ... `resolve-conflicts` is silent as a period template". The live edit reached `main` through catch-all sweep commit a5420200e "Sync coga state" (2026-09-20), which also added `coga/recurring/address-pr-comments/ticket.md` and `coga/bootstrap/address-pr-comments/ticket.md`, and no commit touched the packaged twin after 046dd8dc5 (2026-09-17). `coga/contexts/coga/sync/SKILL.md` is not in `tests/test_packaging.py::INTENTIONALLY_DIVERGENT_TWINS` (which lists only `coga/.gitignore`, `coga/coga.toml`, `coga/log.md`), so the derived-pair identity test in `tests/test_packaging.py` fails on this pair until the packaged copy is synced from live. The live copy's seven-template count is correct against disk (`ls coga/recurring/` shows seven directories); the packaged copy's six-template count is the stale side.

_ca-10 — address-pr-comments is called a shipped twin but has no packaged copy or default alias:_ Live `coga/contexts/coga/sync/SKILL.md` line 134 states "`coga/recurring/` ships seven templates — `address-pr-comments`, ..." and live `coga/contexts/coga/extension-model/SKILL.md` line 141 states "`resolve-conflicts` and `address-pr-comments` are the shipped agent-backed forms; each pairs a stateless command ticket with a recurring template" (line 29 of the same file says a command ticket's "repo-local definition wins over the packaged fallback"). `coga/contexts/coga/recurring/SKILL.md` lines 1137-1140 define what shipped means: "shipped recurring templates have a live copy at `coga/recurring/<name>/` and a packaged twin at `src/coga/resources/templates/coga/recurring/<name>/` — edit both. The packaged copy is what a fresh `coga init` writes into every new repo". On disk only the live side exists: `git ls-files` tracks `coga/bootstrap/address-pr-comments/ticket.md` and `coga/recurring/address-pr-comments/ticket.md` (both added in `a5420200e 2026-09-20 Sync coga state`), but `src/coga/resources/templates/coga/recurring/` contains only `autoclose-merged`, `blocker-reminders`, `branch-sweep`, `dream`, `resolve-conflicts`, `skill-update`, and `src/coga/resources/templates/coga/bootstrap/` contains only `browser-automation`, `contexts`, `orient`, `resolve-conflicts`, `skills`, `ticket`, `workflows` — no `address-pr-comments` directory on either packaged path, which is also why the derived `IDENTICAL_LIVE_PACKAGED_PAIRS` list has no entry for it. The same one-sided commit makes a related code-reality claim: `coga/bootstrap/address-pr-comments/ticket.md` lines 15-16 say "`coga address-pr-comments` is a default alias for `coga launch bootstrap/address-pr-comments`", but `src/coga/aliases.py` `DEFAULT_ALIASES` (last changed 5b5f3e1f1 2026-09-11) contains only `chat`, `dream`, `build`, `skill-update`, `autoclose`, `pick`, `open-pr`, `resolve-conflicts`, and neither `coga/coga.toml` `[aliases]` nor the packaged `coga.toml` defines `address-pr-comments`, so the spelling the ticket and the recurring template's Description (`coga address-pr-comments`) rely on does not dispatch. Either the packaged twins (recurring template, bootstrap ticket) and a `DEFAULT_ALIASES` entry are missing, or the two live contexts should describe `address-pr-comments` as a repo-local template/command ticket rather than a shipped one; the evidence does not decide which.

_ca-06 — CLI extension audit omits the live `address-pr-comments` recurring template and its repo-local bootstrap ticket:_ The doc's "Recurring launches" table enumerates exactly six templates (`dream`, `resolve-conflicts`, `skill-update`, `autoclose-merged`, `blocker-reminders`, `branch-sweep`) and its "Source references" line 248 states the recurring inventory as `coga/recurring/{autoclose-merged,blocker-reminders,branch-sweep,dream,resolve-conflicts,skill-update}/`. On disk and tracked in git there is a seventh, `coga/recurring/address-pr-comments/ticket.md` (schedule `0 7 * * *`, agent-backed, `delegate: bootstrap/address-pr-comments`), which is launched via the same `recurring launch <name>` mechanism and has no default alias; it delegates to a second repo-local command ticket `coga/bootstrap/address-pr-comments/ticket.md` that the doc's bootstrap-ticket table (lines 96-104) also never lists, even though mechanism 3 (line 34) explicitly covers "package-backed or repo-local tickets at `bootstrap/<name>/ticket.md`". Source of truth: `git ls-files coga/recurring/address-pr-comments coga/bootstrap` lists both files; `src/coga/resources/templates/coga/recurring/` holds only the six packaged templates, so the omission is of live repo-authored inventory, not packaged inventory. All other concrete claims in the file (the eight `DEFAULT_ALIASES` in `src/coga/aliases.py:56-65`, the ten `RECIPES` in `src/coga/runner.py:46-56`, the 21-verb `BUILTIN_COMMANDS` set, `coga recurring --interactive/--force/--agent/--all`, `megalaunch --pick/--relaunch`, `validate --fix`, `_`-prefixed skip in `src/coga/recurring.py`, `coga.autoclose.sweep_merged`, `coga.authoring`, `coga/contexts/coga/extension-model/SKILL.md`, `coga/workflows/autoclose-merged/sweep.md`, `coga/skills/coga/ticket/finalize`, `tests/test_aliases.py`) verified as accurate.

_ca-09 — address-pr-comments template names a `coga address-pr-comments` command that does not exist:_ `coga/recurring/address-pr-comments/ticket.md:19` says the template runs "the stateless `coga address-pr-comments` command", and line 52 tells an operator to "call `coga address-pr-comments [PR]` directly" for an on-demand run. No such command resolves: `src/coga/aliases.py:56-65` `DEFAULT_ALIASES` contains `chat`, `dream`, `build`, `skill-update`, `autoclose`, `pick`, `open-pr`, `resolve-conflicts` only (and `git log -S address-pr-comments -- src/coga/aliases.py` shows it was never there); the repo's `coga/coga.toml` `[aliases]` table adds `chat`, `build`, `pick`, `claude`, `codex`; and `.venv/bin/coga address-pr-comments --help` exits with `No such command 'address-pr-comments'`. The working spelling is `coga launch bootstrap/address-pr-comments [PR]` (the `delegate:` target that `coga/bootstrap/address-pr-comments/ticket.md` exists for). The bootstrap command ticket `coga/bootstrap/address-pr-comments/ticket.md:15-17` repeats the same claim ("a default alias for `coga launch bootstrap/address-pr-comments`"); fixing it means either adding the alias to `[aliases]` in `coga/coga.toml` (or `DEFAULT_ALIASES`) or rewording both files to the `coga launch bootstrap/...` spelling.

#### F75. Four docs link positioning-context sections (dated 2026-09-11..14) that were never committed anywhere

- shard: ca-06, ca-07, ca-08 (merged 4 blocks)
- class: drift
- target: docs/why-switch-to-coga.md, docs/pitch-evaluation.md, docs/build-vs-adopt.md, docs/adoption-trial.md → coga/contexts/marketing/positioning/SKILL.md
- area: marketing/positioning

_ca-06 — why-switch-to-coga.md links four positioning-context sections that do not exist:_ The doc states that "The marketing positioning principle and comparative ratings summarize this research" and links four heading anchors in `coga/contexts/marketing/positioning/SKILL.md`: `#current-owner-direction--2026-09-11`, `#competitive-positioning-and-ratings--2026-09-11` (line 32-33), `#two-linked-central-ideas--2026-09-13` (line 40, "chosen delegation and understandable ownership"), and `#message-hierarchy--2026-09-14` (line 93, "uses megalaunch to demonstrate the immediate payoff"). The tracked context (3,408 bytes, last changed 2026-09-10, commit 7a3d56431) has only three headings — `## Earlier directions to consider`, `## Source and claim limits`, `## Where the new message lands` — opens with "Fresh start, owner direction of 2026-09-10 ... The next pitch, audience, central story and tone are still to be decided", and contains none of the phrases "owner direction", "competitive positioning", "two linked central ideas" or "message hierarchy" (`grep -in` over the file returns nothing; a repo-wide grep finds those phrases only in `docs/why-switch-to-coga.md` and `docs/pitch-evaluation.md`). Neither `coga/contexts/marketing/launch-history/positioning-before-reset.md` nor any other file under `coga/contexts/marketing/` carries them either, and `git status` shows no uncommitted change to the context. The doc was committed 2026-09-16 (924412e0c) citing sections dated 09-11 to 09-14 that never landed in the context, so the claim that the positioning context holds the ratings, the two-ideas principle and the message hierarchy is unbacked and all four links are dead. All other referenced artifacts in the file (`docs/{build-vs-adopt,usage-comparison,adoption-trial,pitch-evaluation,continuity-comparison,upkeep-audit}.md` with their cited anchors, `src/coga/{megalaunch,compose}.py`, `src/coga/resources/prompt-megalaunch.md`, `coga/tasks/marketing/phase-0-audit/source-inspection-results.json`, `coga/contexts/coga/{architecture,codebase}/SKILL.md`, `coga/recurring/dream/ticket.md`) exist as named.

_ca-07 — pitch-evaluation links three positioning sections that the positioning context does not contain:_ `docs/pitch-evaluation.md` names `coga/contexts/marketing/positioning/SKILL.md` as the "maintained" owner of three statements and links section anchors that do not exist there: line 13 `#two-linked-central-ideas--2026-09-13` ("the maintained statement"), line 344 `#message-hierarchy--2026-09-14` ("the whole message hierarchy"), and line 615 `#draft-explanation-and-comparative-check--2026-09-13` ("The maintained copy is in positioning"). The positioning context at HEAD has only four headings (`# Coga positioning`, `## Earlier directions to consider`, `## Source and claim limits`, `## Where the new message lands`), and `git log --all -S` for each anchor slug matches only the docs commit `924412e0c` — none of those sections was ever committed to the context, whose last content rewrite is `7a3d56431` (2026-09-10). The doc therefore points readers at a "maintained copy" that lives nowhere on disk; either the positioning context must gain those sections or the doc must stop naming it as their owner. `docs/why-switch-to-coga.md:40` links the same `#two-linked-central-ideas` anchor (outside this shard's owned paths; same cause). Source of truth: `coga/contexts/marketing/positioning/SKILL.md` heading list at HEAD.

_ca-07 — build-vs-adopt links a positioning heading that does not exist:_ `docs/build-vs-adopt.md:28` links "the pitch candidate" to `../coga/contexts/marketing/positioning/SKILL.md#pitch-candidate-your-way-of-working-made-executable` and describes it as centering on "editable work definitions that agents execute and reviewed lessons can improve". No such heading exists: `grep -n "^#" coga/contexts/marketing/positioning/SKILL.md` yields only `# Coga positioning`, `## Earlier directions to consider`, `## Source and claim limits`, and `## Where the new message lands`, and `grep -rin "pitch candidate" coga/contexts/marketing/` matches nothing. `git log --all -S"your way of working, made executable"` shows the phrase only ever entered the repo through the docs commit `924412e0c` (2026-09-16); the positioning context was rewritten in `7a3d56431` (2026-09-10) before the doc was written and never carried that section. `docs/adoption-trial.md:113` links the same missing anchor (outside this shard's owned paths; same cause). Source of truth: `coga/contexts/marketing/positioning/SKILL.md` heading list.

_ca-08 — adoption-trial.md links a positioning-context section that does not exist:_ `docs/adoption-trial.md` ends: "The [positioning context](../coga/contexts/marketing/positioning/SKILL.md#pitch-candidate-your-way-of-working-made-executable) owns the resulting pitch candidate." The file `coga/contexts/marketing/positioning/SKILL.md` exists (3,408 bytes) but has only four headings — `# Coga positioning`, `## Earlier directions to consider`, `## Source and claim limits`, `## Where the new message lands` — and no section titled "Pitch candidate: your way of working made executable"; `grep -i 'way of working made executable'` over `coga/contexts`, `coga/skills`, `docs`, and `README.md` returns nothing, and `git log --all -S'way of working made executable'` shows the heading was never committed anywhere. The context also says at line 61 "No new pitch or campaign is approved by this inventory reset." The doc's ownership claim points at a missing artifact: either the positioning context should carry that pitch-candidate section, or the doc should repoint (e.g. to the `write-the-pitch-and-narrative` plan ticket the context links at line 58) or drop the anchor.

#### F76. Two docs link `#dream-run-summary` inside the ephemeral `recurring/dream` period ticket

- shard: ca-07, ca-09 (merged 2 blocks)
- class: drift
- target: docs/upkeep-audit.md:32, docs/usage-comparison.md:706
- area: docs / recurring dream

_ca-09 — upkeep-audit.md cites Dream evidence through a link into an ephemeral period task:_ `docs/upkeep-audit.md:32` links its primary evidence as `[Dream run summary](../coga/tasks/recurring/dream/ticket.md#dream-run-summary)`, citing the W37 (2026-09-08) run. `coga/tasks/recurring/dream/ticket.md` is the recurring period task that `docs/operations.md:164` says "is deleted at the next period"; the file on disk today is the W39 in-progress task and contains no `Dream run summary` heading (`grep -n -i "run summary"` finds only the phase-6 label at line 324), so the anchor does not resolve and the W37 summary the audit relies on is no longer reachable from that link. The durable source of truth for that run is the log (`coga/log.md:4586`, which the doc separately cites) or a frozen copy; the doc should cite one of those instead of a path that is rewritten every period.

_ca-07 — usage-comparison cites a Dream run record anchor the live recurring ticket no longer carries:_ `docs/usage-comparison.md:706` (footnote `[^5]`, cited from line 267) links the "Dream run record, September 9, 2026" to `../coga/tasks/recurring/dream/ticket.md#dream-run-summary`. `coga/tasks/recurring/dream/ticket.md` is the recurring task's live per-period instance: the current 2026-W39 ticket at HEAD has no heading matching "Dream run summary" (`grep -c "Dream run summary"` returns 0; its `##` headings are Description, Context, Dream Skill: validate-drift, Run notes (2026-W39), Findings). The `## Dream Run Summary` section the footnote refers to exists only in the superseded period's done ticket, e.g. `git show 9cb722546:coga/tasks/recurring/dream/ticket.md` line 637 (commit dated 2026-09-08, "Ticket: recurring/dream — done"). The link therefore resolves to a different Dream run every period and the cited evidence is only reachable through git history; the doc should cite the commit or an archived copy rather than the live instance path. Source of truth: `coga/tasks/recurring/dream/ticket.md` at HEAD versus `9cb722546`.

#### F77. code/open-pr says `coga open-pr` "is a launch" that regenerates `.agent-skills/`

- shard: ca-05
- class: drift
- target: coga/skills/code/open-pr/SKILL.md
- area: skills/code

Line 196-197 of `coga/skills/code/open-pr/SKILL.md` (the "Dirty checkout naming only `coga/.agent-skills/`" bullet) claims "that merged skill view is regenerated by every `coga launch`, and this command *is* a launch, so it lands in the very checkout being published." That contradicts both the same file's line 15-16 ("It is an ordinary command, not a nested launch") and the code: `coga open-pr` is the `[aliases]` rewrite to `coga run open-pr`, which `src/coga/runner.py:55` dispatches in-process to `coga.open_pr.run_open_pr_recipe`; the only callers of `coga.agent_skills.refresh_agent_skill_view` are `src/coga/commands/init.py:1426` and `src/coga/commands/launch.py:4081` (`_refresh_agent_skills_for_launch`), and `src/coga/open_pr.py` never references the skill view. The dirty `.agent-skills/` the bullet describes comes from the *outer* `coga launch` session that composed the agent, not from `coga open-pr` itself; the sentence should attribute the regeneration to that enclosing launch.

#### F78. sync context still says `coga/log.md` is the only `merge=union` file

- shard: ca-02
- class: drift
- target: coga/contexts/coga/sync/SKILL.md
- area: coga/sync

`coga/contexts/coga/sync/SKILL.md` lines 514-515 state "The one file every writer appends to is the repo-global `coga/log.md`, and it is the one file `.gitattributes` marks `merge=union`", and lines 1052-1053 restate the union set as "(union files — `log.md` — committed locally + union-merged onto the control branch ...)". Both `coga/.gitattributes` and its packaged twin `src/coga/resources/templates/coga/.gitattributes` now carry two lines: `**/log.md merge=union` and `**/retires.md merge=union`, the second added by commit fdab877fe "Persist autoclose retire follow-ups (#820)" on 2026-09-17, which introduced `coga/recurring/autoclose-merged/retires.md` (owned by `coga.retire_worklist`, referenced from `src/coga/autoclose.py:33,644`). That file is not append-only: the autoclose recipe "drops entries whose recorded worktree directory and local branch are both gone" and the commit relies on union duplicates "healing on the next reconcile" — which is exactly the rewritten-file shape the same section (lines 516-523) says "must never carry the attribute". The context's single-union-file inventory and its append-only safety argument no longer describe `.gitattributes`; the source of truth is `coga/.gitattributes` and `git.py::_union_merge_paths` (git.py:3536-3567), which asks `git check-attr` and therefore already treats `retires.md` as a union file.

#### F79. codebase context calls `v2/propagate-local-coga-config-into-worktrees` "still a draft" but it is in_progress

- shard: ca-02
- class: drift
- target: coga/contexts/coga/codebase/SKILL.md
- area: coga/codebase

`coga/contexts/coga/codebase/SKILL.md` lines 667-670 say "The command-side complement — Coga seeding its own checkouts — is `v2/propagate-local-coga-config-into-worktrees`, still a draft; other fresh checkouts still need explicit local setup." `coga/tasks/v2/propagate-local-coga-config-into-worktrees.md` is `status: in_progress` on workflow `code/with-review`, activated by commit 32e86a72f (2026-09-20) and at step 4 (review) since efe6fb93d (2026-09-20). The draft characterisation no longer matches the ticket's lifecycle state; the packaged twin under `src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md` carries the same sentence.

#### F80. skills/_template says Coga never reads a skill's `name:` field, but `coga skill install-url` does

- shard: ca-05
- class: drift
- target: coga/skills/_template/SKILL.md
- area: skills/_template

Line 14-17 of `coga/skills/_template/SKILL.md` (and its byte-identical packaged twin `src/coga/resources/templates/coga/skills/_template/SKILL.md`) states of the `name:` frontmatter field: "**Coga never reads it** — a skill's reference is derived from its directory path, both for `skills:` refs and for the generated `coga/.agent-skills` view (`agent_skills.py`)." The two named consumers are indeed path-derived (`agent_skills._skill_refs` rglobs `SKILL.md` paths; `compose.py` never touches `Skill.name`), but `coga skill install-url` reads the field and acts on it: `src/coga/skill_manager.py` `materialize_url_skill` sets `skill_ref=_validated_url_skill_ref(skill_dir)`, which loads the downloaded `SKILL.md`, requires `frontmatter["name"]` to be a string matching the Agent Skills grammar (or a slash-separated namespace of such parts, each ≤64 chars) and raises `SkillManagerError` otherwise, and `install_url_skill` then uses that value as the install destination via `_skill_target(cfg, skill_ref)`. The checked-in `coga/skills/clarity/.coga-source.json` (`"installed_ref": "clarity"`) is the artifact of that path. The blanket "never reads it" should be narrowed to reference resolution at compose/view time, and note that the URL installer uses `name:` to validate and to choose the target directory under `coga/skills/`.

#### F81. codebase context locates the PR 699 concern at a `_LEDGER_LOADED = "yes"` mark that does not exist

- shard: ca-02
- class: drift
- target: coga/contexts/coga/codebase/SKILL.md
- area: coga/codebase

`coga/contexts/coga/codebase/SKILL.md` line 911 points the PR 699 (P1) concern at "`recurring_runner.py` near the `_LEDGER_LOADED = "yes"` mark". `src/coga/recurring_runner.py:4369` defines `_LEDGER_LOADED = "\0loaded"`, and `git log -S'_LEDGER_LOADED'` shows the sentinel has carried that value since it was introduced in f55434462 (2026-08-14, #688) — no revision ever spelled it `"yes"`. An agent grepping for the quoted mark finds nothing. The identifier `_LEDGER_LOADED` is correct; only the quoted value is wrong. Packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md` carries the same text.

#### F82. codebase context cites `clarity/` as the `.coga-source.json` without an `include` key, but the key is present

- shard: ca-02
- class: drift
- target: coga/contexts/coga/codebase/SKILL.md
- area: coga/codebase

`coga/contexts/coga/codebase/SKILL.md` lines 257-262 describe "a `.coga-source.json` whose `local_adaptation_notes` describe a prune but which carries no `include` key — the updater then treats the full tree as the install and never re-prunes (`clarity/` fell into this after a refresh that ran on pre-#776 code)". `coga/skills/clarity/.coga-source.json` on disk carries an `include` allowlist (`SKILL.md`, `LICENSE`, `references`, `scripts/prose_stats.py`, `scripts/strip_markdown.py`) together with `local_adaptation_notes`; it was added by 7966c2a23 "Sync coga state" on 2026-09-14, the same day the sentence was written (c30d30ba5, #803). The unprotected shape the paragraph warns about therefore has no in-tree instance, and the parenthetical reads as if `clarity/` still exhibits it. Packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md` carries the same sentence.

### Phase 3 result

- Phase 3 contract audit: **reported** — 10/10 leaf shards wrote a completion line (distinct ids; 0 `incomplete`, 0 supersessions); 22 blocks on disk → 9 new drift findings (F74–F82) plus 3 folded into Phase 2 findings. `tests/test_packaging.py` fails on `main` today (extension-model twin) — carried by PR #857. Scan directory deleted after merge.

## Phase 4 — Retro (setup)

- Eligible done tickets (directory exists on origin/main, no real `## Dev` branch/worktree, no open PR touching them): 11 — `autofix/stop-the-digest-spool-drain-leaking-a-blank-line-e`, `recurring/address-pr-comments`, `recurring/autoclose-merged`, `recurring/blocker-reminders`, `recurring/branch-sweep`, `recurring/resolve-conflicts`, `recurring/skill-update`, `test-recurring-create-is-silent-fixture-fix-is-hal`, `triage-five-review-comments-that-merged-unanswered`, `v2/document-workflow-less-concept-capture-drafts-as-s`, `v2/overload-ticket-locally-easily`.
- Checkout-bearing done tickets (retirement debt, left on disk for `coga retire`): 74 — listed in the run summary.
- Isolation: caller-created linked worktree `/tmp/coga-dream-w39-retro` on temp branch `dream-w39/retro-115556` fast-forwarded to fresh `origin/main` (fc15f1a00); `coga.local.toml` ordinary-copied (0600). Run dir `/tmp/claude-1000/-home-n-Code-claude-coga-coga/f8c5fdbd-9dee-476f-ae5e-7b988a98d033/scratchpad/dream-w39-retro-run.tNYOFd` with read-only `evidence/` (11 task artifacts, `coga/log.md`, `coga/contexts`, `coga/skills`, this task's `## Findings`) and writable `progress.md`.

### Phase 4 result

- Phase 4 retro/done-ticket: **pr-opened** — subagent receipt `complete — 4 PRs, 7 direct deletes, 11 tickets`; every receipt verified against `origin/main` and `gh pr view` before teardown.
- Knowledge PRs (each deletes its source ticket in the same PR; live + packaged twins edited together):
  - #859 `codex/retro-recurring-branch-sweep-knowledge` — New skill note: branch sweep refuses a merged branch whose commits were rebased in another checkout (`coga/skills/coga/branch-sweep/sweep/SKILL.md` + packaged twin; source `recurring/branch-sweep`). Consumes Phase 2 F3.
  - #860 `codex/retro-recurring-blocker-reminders-knowledge` — New context: blocker reminders never fire for a paused recurring agent period (`coga/contexts/coga/recurring/SKILL.md`, `coga/skills/coga/blockers/remind/SKILL.md` + twins; source `recurring/blocker-reminders`). Consumes F5.
  - #861 `codex/retro-test-recurring-create-is-silent-fixture-fix-is-hal-knowledge` — New context: a done ticket's fix claim can be half-applied on main — verify the exact token (`coga/contexts/coga/codebase/SKILL.md` + twin; source `test-recurring-create-is-silent-fixture-fix-is-hal`). Consumes F2.
  - #862 `codex/retro-triage-five-review-comments-that-merged-unanswered-knowledge` — New context: fan-out follow-ups that rewrite one shared context bullet conflict pairwise (`coga/contexts/coga/codebase/SKILL.md` + twin; source `triage-five-review-comments-that-merged-unanswered`). Consumes F4.
- Direct-deleted (no durable knowledge; `coga delete <slug> --keep-control-checkout` from the linked worktree, landed on `origin/main` as `Ticket: <slug> — deleted`): `autofix/stop-the-digest-spool-drain-leaking-a-blank-line-e` (8d2ba7990), `recurring/address-pr-comments` (5d8cfb4ad), `recurring/autoclose-merged` (a616f78b1), `recurring/resolve-conflicts` (7ba9d2105), `recurring/skill-update` (64a8c6f15), `v2/document-workflow-less-concept-capture-drafts-as-s` (3dc24d93f), `v2/overload-ticket-locally-easily` (dbf90a9cc).
- Teardown: copied `coga.local.toml` removed, linked worktree `/tmp/coga-dream-w39-retro` removed, temp branch `dream-w39/retro-115556` deleted, run directory deleted. Primary checkout fast-forwarded to `origin/main`.

## Dream Skill: cleanup-orphan-markers

Generated: 2026-09-21T19:18:35+00:00
Task: `recurring/dream`

Result: no-op. No cleanup-eligible processed done tickets still have task directories.

## Dream Run Summary

Generated: 2026-09-21T19:35Z (UTC) — period 2026-W39, repo `FastJVM/coga`, control branch `main`.

| Phase | Result | Notes |
| --- | --- | --- |
| 1 validate-drift | reported | 50 issues: 0 direct-fix, 5 pr-proposal, 45 human-needed (3 kinds) |
| 2 knowledge scan | reported | 34/34 shards complete, 80 blocks → 73 findings (18 extract, 14 stale, 13 gap, 28 premise) |
| 3 contract audit | reported | 10/10 shards complete, 22 blocks → 9 drift findings + 3 folded into Phase 2 |
| 4 retro/done-ticket | pr-opened | 11 eligible: 4 knowledge PRs (#859 #860 #861 #862), 7 direct deletes on `main`; 74 checkout-bearing done tickets deferred as retirement debt |
| 5 cleanup-orphan-markers | no-op | no processed marker on a surviving directory |
| 6 disposition | proposed | 6 proposal PRs (#863–#868), 12 draft tickets, 12 "already ticketed"/in-flight findings, 0 machine-local validator issues |

### PRs opened this run (all `pr-required`; nothing auto-merged)
- Retro knowledge PRs: #859 branch-sweep rebased-merged-branch note (F3); #860 blocker reminders blind to paused period task (F5); #861 half-applied fix claim — verify the exact token (F2); #862 fan-out follow-ups conflict pairwise on one bullet (F4). Each deletes its source ticket.
- Proposal PRs: #863 `coga/roadmap` records the owner's v2-parking decision (F1, canceled-source extract); #864 `code/self-qa` single-checkout layout (F29); #865 `skills/_template` `name:` claim (F80); #866 docs cite the frozen Dream period commit (F76); #867 skill-creator ATTRIBUTION posture (F32); #868 `marketing/distribution` telemetry decision (F31, distribution half).

### Draft tickets created this run
- brief-for-human: `validate-drift-stuck-in-progress-11-in-progress-ti` (11 members); `validate-drift-unfrozen-workflow-11-hand-authored` (11); `validate-drift-empty-description-23-title-only-tic` (23; carries the tag line and the owner's 2026-09-20 parking decision); `premise-check-2026-w39-25-parked-drafts-need-a-ver` (25 members: F46–F51, F53–F66, F68, F69, F71–F73; F69 is a live root draft already delivered by #814).
- code/with-review (gap): `record-four-repeated-dev-loop-verification-gotchas` (F34 F37 F38 F39); `document-how-to-recover-a-retired-ticket-s-body-fr` (F36 F43); `the-retro-done-ticket-skill-should-verify-a-done-t` (F42); `add-an-applying-a-batch-of-verdicts-section-to-the` (F44).
- code/with-review (stale/drift preserved because an open PR touches the target without carrying the fix): `apply-12-context-and-skill-corrections-blocked-by` (F20 F21 F23 F24 F25 F26 F27 F77 F78 F79 F81 F82 + the validate-baseline tag line); `correct-two-stale-marketing-map-catalogue-rows-aft` (F30, F31 map half; overlap #841); `settle-whether-megalaunch-is-the-only-unclassified` (F19; overlap #857 #848); `four-docs-cite-positioning-context-sections-that-w` (F75; human choice).

### Already ticketed / in flight (nothing created)
- F52 `v2/identify-blocking-issues` → already ticketed as `ticket-relationships-and-ownership-have-no-mechani`.
- F67 `v2/autotrigger-ticket-type`, F70 `v2/skill-update-aborts-on-uncommitted-log-file` → already ticketed as `adjudicate-the-eight-premise-dead-v2-drafts`.
- F33 worktree reaping → `packaged-code-workflows-never-name-coga-retire-as` (PR #847); F35 packaged-context reachability → `document-how-packaged-contexts-reach-a-repo-and-se` (PR #843); F40 split-a-ticket mechanic → `define-the-split-a-ticket-mechanic-shared-by-code`; F41 barrier reentrancy → `simplify-git-sync` (PR #848); F45 namespace-package footgun → `nothing-exercises-python-3-11-the-declared-floor` (blocked).
- F28 dev/code stranded-duplicate claim → `detect-stranded-ticket-writes-across-checkouts` (PR #850).
- F22 codebase "five bot review threads" bullet → carried piecewise by open PRs #835 #840 #842 #844 (each rewrites its own sub-bullet).
- F74 `address-pr-comments` cluster (twin drift on `extension-model`/`sync`, missing packaged copies, missing alias, audit-doc omission) → PR #857 carries all of it; `tests/test_packaging.py` fails on `main` until it merges.

### Phase 1 pr-proposal bucket
- 4 × `unsynthesized-draft-blackboard` (`clean-up-all-the-working-trees`, `v2/autotrigger-ticket-type`, `v2/measure-relay-prompt-scope-and-agent-precision`, `v2/use-worktree-when-starting-a-dev-task`): already decided — the `coga/codebase` "repo-wide run is red by baseline; do not clear it under an unrelated ticket" bullet (PR #823) is the recorded baseline, and the v2 members fall under the owner's 2026-09-20 parking decision (PR #863). The bullet lists a stale member set (F20); its refresh plus the tag line `validate-drift: unsynthesized-draft-blackboard` is preserved in `apply-12-context-and-skill-corrections-blocked-by`. No synthesis PR opened: synthesizing an author's draft notes is the author's choice.
- 1 × `large-blackboard` (`reconcile-recurring-wrapper-tty-admission-guidance`, 54 KiB): the ticket is done with a recorded checkout — retirement debt; `coga retire` consumes and deletes it, so no condensation PR.

### Already-decided classes / machine-local issues
- No context carries a `validate-drift: <kind>` tag line yet, so no class was reported as decided by context; all three human-needed kinds got one owner draft each (above).
- Machine-local validator kinds this run: none.

### Retirement debt (74 done tickets with a recorded checkout; `coga retire <slug>` is the consumer)
Findings named after a slug are the `done+checkout` extracts that retirement unlocks — order retirements by them: `record-dochub-s-why-not-the-api-answer-that-browse` (F7), `autofix/report-per-skill-outcomes-from-gh-skill-update-in` (F13), `dream-findings-have-three-routing-holes-that-lose` (F18), `launch-activates-before-preflight` (F17), `megalaunch-only-shows-one-page` (F14), `the-v2-parking-area-premise-check-has-four-holes` (F6), `review-slack-channels` (F9), `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` (F45), `allow-description-and-owner-on-create` (F8), `title-only-tickets-have-no-convention-and-no-valid` (F11), `document-the-ticket-blackboard-writer-s-contract` (F10), `select-session-conduct-instead-of-appending-a-cont` (F15), `persist-autoclose-retire-follow-ups` (F16), `give-a-ticket-s-superseded-design-one-documented-h` (F12).
  - `a-slack-repo-without-important-webhook-can-abort-t` (branch `scan-alert-nonfatal`)
  - `activation-does-not-resolve-step-1-s-assignee-role` (branch `resolve-step-one-assignee`)
  - `adjudicate-parked-and-active-tickets-whose-premise` (branch `adjudicate-moved-premises`)
  - `allow-description-and-owner-on-create` (branch `create-description-owner`) — unlocks F8
  - `autoclose-should-name-the-retire-follow-up` (branch `autoclose-retire-hint`)
  - `autofix/report-per-skill-outcomes-from-gh-skill-update-in` (branch `skill-update-per-skill`) — unlocks F13
  - `autofix/stop-one-failing-ticket-py-from-starving-the-rest` (branch `sweep-abandoned-record`)
  - `branch-sweep-strands-squash-merged-branches-whose` (branch `branch-sweep-landed`)
  - `bumppy-requires-exactly-two-agents` (branch `agent-peers`)
  - `carry-adjacent-bugs-out-of-a-blackboard-before-ret` (branch `retro-adjacent-bugs`)
  - `cleanup/add-a-debug-mode-to-init-for-vendoring-from-source` (branch `vendor-pypi-only`)
  - `cleanup/add-contributing-docs-issue-templates-and-a-repo-d` (branch `docs/contributing`)
  - `cleanup/detect-the-current-git-branch-instead-of-hard-codi` (branch `init-control-branch`)
  - `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` (branch `resources-pkg-init`) — unlocks F45
  - `cleanup/handle-a-bare-slack-webhook-url-during-empty-repo` (branch `init-bare-slack-env`)
  - `cleanup/yank-the-pypi-0-0-1-placeholder-and-document-the-f` (branch `docs/pypi-placeholder-note`)
  - `cloning-a-coga-repo-has-no-setup-path` (branch `init-clone-setup`)
  - `define-the-recipe-reporting-contract-report-durabi` (branch `recipe-reporting-contract`)
  - `document-the-ticket-blackboard-writer-s-contract` (branch `blackboard-writer-contract`) — unlocks F10
  - `document-when-to-attach-a-large-context-versus-cit` (branch `attach-vs-cite`)
  - `dream-2026-w36-extract-backlog-18-findings-phase-4` (branch `dream-w36-extract-backlog`)
  - `dream-2026-w38-extract-backlog-4-findings-phase-4` (branch `dream-w38-extract-backlog`)
  - `dream-findings-have-three-routing-holes-that-lose` (branch `dream-routing-holes`) — unlocks F18
  - `dream-phases-2-3-cannot-complete-scan-subagents-re` (branch `dream-scan-shards`)
  - `dream-reconciliation-must-count-distinct-shard-ids` (branch `dream-reconcile-distinct-shards`)
  - `fix-the-autofix-analyst` (branch `autofix-claude-auth-fallback`)
  - `four-parked-tickets-carry-premises-that-have-since` (branch `triage-inverted-premises`)
  - `give-a-ticket-s-superseded-design-one-documented-h` (branch `docs/superseded-design-home`) — unlocks F12
  - `isolated-checkouts-nothing-says-what-a-fresh-workt` (branch `fresh-checkout-lacks`)
  - `launch-activates-before-preflight` (branch `defer-launch-activation`) — unlocks F17
  - `launch-ignores-the-recorded-worktree-stranding-bla` (branch `implement-branch-gate`)
  - `live-and-packaged-twin-pairs-are-edited-together-b` (branch `derive-twin-sync`)
  - `megalaunch-activates-picks-before-preflight` (branch `megalaunch-defer-activation`)
  - `megalaunch-only-shows-one-page` (branch `megalaunch-picker-viewport`) — unlocks F14
  - `migrate-recurring-templates-to-ticket-py-shims-and` (branch `recurring-ticket-py`)
  - `move-cogacontext-to-roodoc-so-its-easier-for-human` (branch `layout-contexts-dir`)
  - `no-comms-writing-skill-the-process-is-smeared-thro` (branch `write-post-skill`)
  - `no-context-records-the-ci-posture-publish-only-rel` (branch `ci-posture`)
  - `no-rule-says-ticket-context-must-cite-symbols-not` (branch `cite-symbols-rule`)
  - `no-skill-exists-for-the-cold-evaluator-review-of-a` (branch `cold-design-review`)
  - `packaged-repos-ship-recurring-templates-without-th` (branch `package-recurring-context`)
  - `persist-autoclose-retire-follow-ups` (branch `autoclose-retire-worklist`) — unlocks F16
  - `put-build-back` (branch `restore-coga-build`)
  - `read-the-recurring-serviced-period-from-the-log-dr` (branch `fix/recurring-log-reverse-pass`)
  - `reconcile-recurring-wrapper-tty-admission-guidance` (branch `delegate-recurring`)
  - `record-dochub-s-why-not-the-api-answer-that-browse` (branch `dochub-api-answer`) — unlocks F7
  - `record-or-clear-the-standing-repo-wide-coga-valida` (branch `validate-baseline`)
  - `recurring-context-never-mentions-the-packaged-twin` (branch `recurring-twin-note`)
  - `recurring-last-serviced-period-compares-as-a-strin` (branch `codex/validate-recurring-periods`)
  - `recurring-recipe-question` (branch `deduce-ticket-script`)
  - `recurring-sweep-aborts-and-orphans-a-deleted-done` (branch `recurring-missing-workflow`)
  - `refuse-recurring-runs-from-a-non-control-branch` (branch `fix/recurring-control-branch-gate`)
  - `remov-digest-in-recurring` (branch `remove-digest`)
  - `remove-coga-build-and-project` (branch `remove-build-project`)
  - `remove-legacy-config-compatibility-shims` (branch `remove-legacy-config-shims`)
  - `retire-never-removes-a-worktree-that-ran-the-tests` (branch `retire-cache-worktrees`)
  - `review-slack-channels` (branch `route-important-failures`) — unlocks F9
  - `rewrite-coga-base-prompt-and-agent-mode-block` (branch `codex/rewrite-launch-prompts`)
  - `select-session-conduct-instead-of-appending-a-cont` (branch `select-session-conduct`) — unlocks F15
  - `service-recurring-from-a-temp-control-worktree-ins` (branch `recurring-control-worktree`)
  - `simplify-ticket-format` (branch `simplify-ticket-format`)
  - `state-which-branch-is-canonical-for-machine-genera` (branch `sync-canonical-policy`)
  - `stop-syncing-task-state-onto-the-feature-branch` (branch `feature-branch-state-boundary`)
  - `sync-context-omits-preflight-post-from-the-notific` (branch `sync-context-preflight`)
  - `the-autofix-analyst-ticket-closed-without-shipping` (branch `autofix-analyst-fixes`)
  - `the-human-doc-vs-agent-context-boundary-is-decided` (branch `doc-context-boundary`)
  - `the-period-task-context-never-covers-the-determini` (branch `period-task-recipe-firing`)
  - `the-v2-parking-area-premise-check-has-four-holes` (branch `v2-premise-holes`) — unlocks F6
  - `ticket-specs-should-cite-symbols-not-line-numbers` (branch `design-cite-symbols`)
  - `title-only-tickets-have-no-convention-and-no-valid` (branch `title-only-validator`) — unlocks F11
  - `unblock-rewind` (branch `rewind-status-gate`)
  - `validate-drift-classifier-misses-17-emitted-kinds` (branch `codex/validate-drift-kinds`)
  - `validate-that-committed-skill-scripts-with-a-sheba` (branch `shebang-exec-check`)
  - `vendored-skills-carry-no-coga-source-json-so-coga` (branch `docs/skill-attribution`)

### Human-needed decisions / review gates
- Review and merge or reject the 10 PRs above; none auto-merges.
- The 25-draft premise adjudication and the three validate-drift class drafts need the owner's verdicts; the `empty-description` draft and PR #863 together propose recording the v2 waiver in a context.
- `four-docs-cite-positioning-context-sections-that-w` needs a decision on where the missing positioning sections live.
