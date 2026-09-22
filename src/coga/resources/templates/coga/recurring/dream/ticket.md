---
schedule: "0 9 * * 1"
schedule_comment: "Every Monday at 9am — Coga's generic ticket cleanup pass"
title: "Dream"
# Dream runs interactively: it writes live console progress, delegates to
# subagents, and exercises agent judgment. A weekly `coga recurring` run
# creates and launches the Dream task when its schedule is due; `coga dream`
# (alias for `coga recurring launch dream`) creates and launches it now.
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

Both decide-half scans are read-only sweeps over this repo's own corpus — which
is Coga's in the Coga source repo and the client's own knowledge, never the
installed Coga OS files, in a client repo — and both run the same way: **bounded shards writing durable findings to disk**, never one
subagent sweep whose result arrives only in its final message. The corpus is
larger than a subagent can hold, and a scan that stops early after delivering
nothing is indistinguishable from a clean repo. Run each scan like this:

0. **Decide the repo identity once per run**, before the first scan directory
   exists: this checkout is the Coga source repo when
   `src/coga/resources/templates/coga/` is a directory under the checkout
   root, and a client repo otherwise — the test the protocol's "Repo identity"
   section owns. Keep the verdict for both phases; no shard and no later phase
   re-derives it. In a client repo also run the protocol's Rule A block once,
   under the interpreter that backs the active `coga`, and keep its owned-path
   list; a non-zero exit is a failed run of both scans (`partial`, with the
   block's stderr and a `human-needed` line in the run summary), never an
   empty owned set.
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
   phase skill names and write the full index to `index.md`, with
   `repo-identity: client | coga-source` as its first line. In a client repo,
   subtract the Rule A owned-path list from the corpus **as you write the
   index** — this is the only place the exclusion happens, so no shard needs a
   filter — and write `excluded-coga-owned: <N>` as the second line so the
   decision is auditable. In the Coga source repo apply no exclusion: the index
   gains the identity line and its corpus paths are unchanged. Then build the
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
`premise` finding's `target:`, `question:`, and `owner:` lines, and every
`owner: coga` line on any class, through the merge — Phase 6 routes on them. The `premise` class is this scan's standing
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

Pass `## Findings` to Retro as it stands, `owner: coga` lines included, and
tell the subagent in the delegation prompt: a finding marked `owner: coga` is
knowledge whose source of truth is the Coga package, not this repo, and Retro
must not write that fact into a local context or skill — Phase 6 routes it
upstream. Everything else the same ticket holds is extracted as usual, so a
ticket that teaches one local fact and one Coga-owned fact contributes the
local one and still gets deleted like any processed done ticket. The
`retro/done-ticket` skill carries the matching rule; the prompt line is what
makes it fire. In the Coga source repo no finding carries the mark and the
handoff is unchanged.

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

**Coga-owned findings go upstream, whatever their class.** Before routing by
class, take every Phase 2 and Phase 3 finding that carries `owner: coga` — a
client-owned file making a claim only Coga's implementation can settle, per
the scan protocol's Rule B — and append it to `<checkout-root>/coga/upstream-coga.md`.
They are **not** routed to a proposal PR, a draft ticket, or a local knowledge
edit: the repo that owns the code is the Coga source repo, and its
`recurring/upstream-coga` job sweeps this file from every configured client
checkout and files real tickets there. Nothing here reaches into that repo.
Create the file when it is missing, with exactly this header:

```markdown
  # Upstream Coga findings

  Findings about Coga itself that this repo's Dream runs could not settle
  locally. Append-only: entries are added in order and never reordered,
  rewritten, or removed. The Coga source repo's `recurring/upstream-coga` job
  sweeps this file and files a ticket per entry.
```

Then append one entry per finding, in finding order, in exactly this shape
(shown indented so the example heading cannot end this `## Description`
section — write the real header and entries flush left):

```markdown
  ## <title>

  - id: 2026-09-09-phase-6-names-a-dead-recipe
  - repo: multiply
  - date: 2026-09-09
  - class: drift
  - target: coga/recurring/dream/ticket.md
  - evidence: coga/contexts/multiply/developer-flow/SKILL.md:44

  <one paragraph: the claim, why only Coga can settle it, and what the client
  file says>
```

`id` is `<YYYY-MM-DD>-<slug-of-title>`, suffixed `-2`, `-3`, … when that id is
already in the file. `repo` is this repo's name, `date` is the run date,
`class` and `target` are the finding's, and `evidence` is the in-corpus client
path and line the conclusion came from. The file is **append-only**: never
reorder, rewrite, or remove an entry, because the sweep keeps a per-checkout
cursor by id and treats a vanished id as a broken file. Record the entries
appended as `upstream-captured` in the run summary with their count. In the
Coga source repo no `owner: coga` finding arises — every Coga-owned file is in
this repo's own corpus — and this route does nothing.

Route each remaining Phase 2 and Phase 3 finding by class:

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
`human-needed`, `upstream-captured`, the finding counts with one-line
summaries, the number of entries appended to `coga/upstream-coga.md` (zero in
the Coga source repo), links to every PR
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

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. A run reads
it at the start to pick up where the last run left off, and updates it at the
end with whatever the next run needs.

Dream's per-period task is disposable after it is marked done, but Dream does
not delete itself mid-run. Dream keeps no durable state here — every finding
ends in a PR, a draft ticket, or a recorded marker instead. `coga recurring`
keeps Dream's serviced-period record in the repo-global `coga/log.md`;
`log.md` keeps append-only human history.
