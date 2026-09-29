---
title: Dream
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 2031332c-45b3-43e7-b0be-b8aa8e199628
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
agent capability preflight, validate-drift, knowledge scan, contract audit, Retro pass,
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

### Agent capability preflight

Run this once, from Dream's checkout, before Phase 1. The execute half
fetches, pushes, opens PRs, and syncs ticket state. An agent sandbox that
cannot do those fails each of them in turn, after the decide half has already
spent the run, so check the capabilities first. Read `[git].remote` and
`[git].control_branch` from the shared `coga.toml` (defaults `origin` and
`main`), then check:

1. **The Git common dir is writable.** Resolve
   `git rev-parse --path-format=absolute --git-common-dir`, create a uniquely
   named probe file in that directory (for example
   `mktemp "<common-dir>/coga-dream-preflight.XXXXXX"`), then remove it. A
   permission-bit check does not count, and the probe never uses a Git lock
   name.
2. **The remote is reachable.**
   `git ls-remote <configured-remote> <configured-control-branch>` succeeds.
3. **The GitHub CLI is authenticated.** `gh auth status` succeeds.

Print one console line with the result, for example
`preflight: git-common-dir ok, remote ok, gh ok`. If any check fails, the
preflight fails before Phase 1: do not start Phase 1 or any later phase. Name
the missing capability and the failing command's error, and point at the
agent sandbox grant recipe in the `coga/testing` topic, under
`## Restricted sandboxes`. Then escalate per this prompt's Session conduct
layer: attended, ask the human and wait; unattended, run
`coga block --task <this-dream-task> --reason "<missing capability>; see the
coga/testing Restricted sandboxes recipe"`. A sandbox grant takes effect only
in a new agent session, so after fixing it the human relaunches Dream. An
agent with ordinary machine access passes all three checks unchanged.

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
   Start every shard subagent with a **fresh context**: the delegation message
   is self-contained and the subagent inherits none of this conversation
   (codex: `spawn_agent` with `fork_turns: "none"`; its default forks the
   whole history and spends the shard's budget before it reads a file). Run
   the shards in **waves** no larger than the agent's concurrent-subagent
   limit (codex: 3), and let each wave join — every subagent in it has
   returned — before launching the next. A wave's join only frees slots:
   manifest rows not launched yet are pending, not missing, and never retry
   candidates.
4. **Reconcile before believing the result.** A subagent has *returned* when
   its final answer has been delivered to you. Reconcile only at the barrier,
   once per attempt, after every wave of that attempt has joined and every
   shard subagent you launched for it has returned; a
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
   smaller attempt-2 child rows and retry those leaves once, in waves as in
   step 3. If an attempt-2
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
every eligible slug. Start it with a fresh context and a self-contained
delegation message, as for the scan shards (codex: `fork_turns: "none"`).
Fetch the configured remote control branch first and base
the checkout's unique temporary branch on that fresh tip. Use native
`isolation: worktree` when the agent supports it; otherwise create a temporary
linked checkout with `git worktree add` at `<run-dir>/checkout`, inside the
temporary run directory above, which is already writable to this session.
Before delegating, check write access there by creating and removing a
uniquely named probe file in the new checkout; if that fails, preserve the
paths and escalate as the preflight does. An agent without native isolation
(codex) starts the subagent in Dream's cwd, so the delegation message names
the checkout's absolute path and tells the subagent to run every shell command
with that path as its working directory. If
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

Retro hands PR FYIs back as `pr` receipts in `progress.md` and never runs
`coga slack` in the isolated checkout (skill step 12). After it returns, Dream
posts each FYI from its own checkout with
`coga slack --task <this-dream-task>`, so the audit line lands through Dream's
ordinary state sync.

Every processed done ticket is deleted: a ticket that contributed durable
knowledge is deleted in its theme's knowledge PR, which also records its
`## Retro` marker; a ticket carrying nothing durable is direct-deleted with
`coga delete <slug> --keep-control-checkout` from a linked worktree or ordinary
`coga delete <slug>` from an independent clone. Both land the removal on the
remote control branch without mutating the operator's checkout, with no PR and
no marker. Recovery is via `git restore`. Retro never leaves a processed done
ticket on disk and never opens a marker-only PR.

After the subagent returns, fetch the remote control branch and verify:

- every PR branch is pushed;
- every direct delete is present on the remote control branch;
- the isolated checkout holds nothing unlanded, by the check the
  `retro/done-ticket` skill's **Isolation boundary** defines.

Then remove the copied `coga.local.toml` and explicitly remove the linked
worktree and its temporary branch, or delete the exact independent-clone
directory. After recording the verified outcome on Dream's blackboard, delete
the temporary run directory (snapshot and progress file) too. Agent-native
cleanup is not guaranteed after a mutating run.

If durability or cleanup cannot be verified — or Phase 4 is `partial` — do
not delete anything: preserve the run directory, the isolated checkout, and
its temporary branch, because they may hold the only copy of the work. Record
under `### Stranded Retro work` on this task's blackboard the temporary branch,
the checkout or clone path, the run directory, the commits it holds
(`git log --oneline <remote>/<control-branch>..<branch>`), the unlanded paths
(`git diff --stat <remote>/<control-branch>...<branch>` plus uncommitted
changes), and the exact commands a human runs to land and then remove them.
This run then ends blocked, never `done` — see the closing rule under
`### Slack`.

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

If Phase 4 preserved any path under `### Stranded Retro work`, the run is not
done: its work is stranded where no downstream consumer can see it. Say so in
the Slack summary, then end the run with
`coga block --task <this-dream-task> --reason "Retro work stranded on <branch> at <checkout path>; land it, then remove both — see ### Stranded Retro work"`
instead of `coga mark done`. In an attended session, first show the human the
stranded record and ask whether they will land it now; once they have, verify
it against the fetched remote control branch, remove the preserved paths, and
close normally. If they do not, this block is the answer the ticket needs:
it is what makes the sweep count the run as a problem.

Otherwise, run `coga mark done <this-dream-task>` once the blackboard is up to
date and the Slack summary is posted. That is the last action — **do not
delete this task.** The run's durable artifacts — every PR, draft ticket, and the Slack
summary — carry the findings, so this `done` task and its blackboard are
disposable, but Dream does not delete itself mid-run. It sits on disk as a
done `recurring/dream` ticket; at the next firing, the recurring scanner deletes
that prior-period artifact and creates a fresh Dream task from this template.
Git history preserves the completed run.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dream Skill: validate-drift

Generated: 2026-09-29T16:06:48+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python -m coga.validate --json --fix`
Task: `recurring/dream`

Result: 43 issue(s): 0 direct fix, 1 PR proposal, 42 human-needed.

### PR Proposal

- `reconcile-recurring-wrapper-tty-admission-guidance`: `large-blackboard` (warn) - blackboard region is 54.0 KiB (warning threshold 32.0 KiB); it is included in launch prompts. Consider summarizing old notes.
  Remediation: Propose the `coga/blackboard` bloated-blackboard remedy: promote a file-form task to directory form (a task that already has `<slug>/ticket.md` keeps its directory), move dated evidence into sibling attachments and superseded material into an unattached context, and leave the current handoff, worklist and verification on the blackboard. Keep `## Dev` and `## Blockers` in place under the `coga/blackboard` contract; CLI readers do not follow attachment links for that state. Move, do not delete.

### Human Needed

- `autoclose-should-be-script-only`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `autofix/name-cross-repo-retire-follow-ups-with-the-repo-th`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `autofix/treat-non-requestexception-slack-send-errors-as-de`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `cleanup/publish-coga-1-0-to-pypi`: `stuck-in-progress` (warn) - in_progress but idle for 325.9h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `dream-should-be-able-to-use-codex-instead-of-claud`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `fix-git-sync-failure`: `unfrozen-workflow` (warn) - workflow 'code/with-self-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `implement-the-include-allowlist-that-url-skill-upd`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `improve-pr-check`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `invert-command-line-to-have-actions-passed-last-or`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `make-every-code-workflow-review-with-the-other-age`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `marketing/build-the-launch-plan`: `stuck-in-progress` (warn) - in_progress but idle for 94.4h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `marketing/idea-piece`: `unfrozen-workflow` (warn) - workflow 'draft-for-human' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `marketing/readme-top`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `parse-agents-rejects-cogalocaltoml`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `recurring-unblock-launch`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `stop-with-all-the-worktreees-its-super-noisy-and-u`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `ticket-sync-fails-with-read-only-git-inside-agent`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
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
- `v2/document-contexts-as-prompt-payload-not-tags-princ`: `stuck-in-progress` (warn) - in_progress but idle for 1674.9h
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
- `where-have-code-review-disappeared`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.

## Run log (2026-W40)

- Preflight: git-common-dir ok, remote ok, gh ok. repo-identity: coga-source (no Rule A exclusion).
- Phase 1 validate-drift: reported — 43 issues (0 direct-fix, 1 pr-proposal, 42 human-needed).
- Phase 2 knowledge scan dir: /tmp/tmp.2WO6zW2aK2 (36 shards). Phase 3 contract audit dir: /tmp/tmp.fDawIchohQ (7 shards).
  Excluded: this Dream task's own ticket; `google-agents-cli-*` (github-repo managed).
- Phase 2 knowledge scan: reported — 36/36 shards complete, 94 raw findings.
- Phase 3 contract audit: reported — 7/7 shards complete, 10 raw drift findings (copy-divergence shard: pytest tests/test_packaging.py green, 0 divergent pairs).

## Findings

Merged 92 findings (Phase 2: 94 raw from 36 shards; Phase 3: 10 raw from 7 shards; 12 duplicates folded). Full text preserved in the Dream scratch copies until Phase 6 routes each.

### extract (24)

- `simplify-ticket-format` — Record that an ephemeral --agent override does not move other-agent's peer resolution (source: done+checkout; area: coga/agents) [ks-32]
- `exclude-superseded-designs-from-launch-prompts` — Blocker parsing is not archive- or fence-aware (historical checkbox examples gate launch) (source: done+checkout; area: coga/blackboard) [ks-13]
- `validate-that-committed-skill-scripts-with-a-sheba` — `non-executable-script` validate check is undocumented in any context since the #875 docs restructure (source: done+checkout; area: coga/cli) [ks-07]
- `add-an-agent-picker-for-recurring` — Record the typer optional-value flag gotcha from the agent-picker ticket (source: done+checkout; area: coga/codebase) [ks-24]
- `persist-autoclose-retire-follow-ups` — Tag-shadowed branch names also bite `for-each-ref %(refname:short)` (source: done+checkout; area: coga/codebase/gotchas) [ks-23]
- `nothing-exercises-python-3-11-the-declared-floor` — Record the Python 3.11 resource-package gotcha and what a 3.12-only green run proves (source: canceled; area: coga/codebase/gotchas) [ks-18]
- `the-v2-parking-area-premise-check-has-four-holes` — coga/dream topic omits Dream's standing premise pass over parked v2 drafts (source: done+checkout; area: coga/dream) [ks-03]
- `make-dream-run-correctly-under-codex` — Codex subagent mechanics and the owner-search budget pressure observed in real Dream runs (source: done+checkout; area: coga/dream) [ks-04]
- `attribute-headless-recurring-completions-to-system` — Carry the unresolved strict-assist audit-publication observation out of attribute-headless-recurring-completions-to-system (source: done+checkout; area: coga/internals/assist-publication) [ks-22]
- `phase-0-audit-is-complete-per-the-plan-but-still-i` — Contexts that link a live ticket by path break when Retro reaps it (source: canceled; area: coga/knowledge) [ks-17]
- `make-dream-run-correctly-under-codex` — Launch-time `--agent` override is lost in completion attribution (unresolved adjacent bug) (source: done+checkout; area: coga/launch) [ks-04]
- `cleanup/handle-a-bare-slack-webhook-url-during-empty-repo` — Init's bare SLACK_WEBHOOK_URL tolerance was dropped from the notifications contract (source: done+checkout; area: coga/notifications) [ks-19]
- `redo-documentation-dir-and-merge-it-with-context-b` — Link-topology rule for bundled topics is unowned (source: done+checkout; area: coga/packaging) [ks-08]
- `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` — coga.resources must stay a regular package; 3.11 regressions are invisible on 3.12 dev envs (source: done+checkout; area: coga/packaging (with a line in coga/testing)) [ks-29]
- `digest-can-clobber-recurring-last-serviced-period` — Parent-blackboard state writers must preserve lines they do not own (source: canceled; area: coga/period-task) [ks-24]
- `make-sure-repo-clietn-don-t-edit-coga` — A `##` line inside a code fence in `## Description` truncates the composed section (source: done+checkout; area: coga/prompt-composition) [ks-17]
- `recurring-task-to-manage-all-open-pr-and-address-c` — Shipped recurring templates must leave owner/agent empty so installs inherit repo routing (source: done+checkout; area: coga/recurring/templates) [ks-21]
- `agent-usage-report` — Document how a copied ticket.py reaches its template's other siblings (source: done+checkout; area: coga/recurring/templates) [ks-24]
- `v2/skill-update-aborts-on-uncommitted-log-file` — Canceled skill-update abort ticket leaves a verified dirty-tree gotcha recorded nowhere durable (source: canceled; area: coga/skill-management) [ks-34]
- `simplify-git-sync` — Record why state publication never commits locally, stashes, or rebases (source: done+checkout; area: coga/sync (internals/state-publication, internals/git-refresh)) [ks-06]
- `four-parked-tickets-carry-premises-that-have-since` — Verdict-application mechanics for batch premise adjudication (four-parked-tickets) (source: done+checkout; area: coga/tasks/v2 README (verdict application) / coga/workflows requires-pr gate) [ks-05]
- `reuse-the-existing-control-worktree-for-recurring` — Testing gotcha: every coga module shares one `subprocess`, so patching `run` wholesale swallows git probes (source: done+checkout; area: coga/testing) [ks-20]
- `define-the-api-equivalent-cost-proxy-and-price-tab` — Record the measured pricing facts a future price table would need (source: canceled; area: coga/usage) [ks-18]
- `agent-usage-report` — Record that usage.rollup's until bound is inclusive, and the weekly usage-report consumer (source: done+checkout; area: coga/usage) [ks-24]

### stale (26)

- `coga/skills/anthropic/skill-creator/ATTRIBUTION.md` — skill-creator ATTRIBUTION cites the removed managed-skills.toml registry (area: skills) [ks-04,ks-21]
- `coga/skills/code/self-qa/SKILL.md` — code/self-qa gotcha overstates the state sweep ("every uncommitted coga/ file") (area: coga/sync (code skills)) [ks-09]
- `docs/contexts/coga/dream/SKILL.md` — Retro's adjacent-bug preservation rule was dropped from the contexts by the docs restructure (area: coga/dream) [ks-04]
- `coga/skills/code/implement/SKILL.md` — code/implement claims "any python works" for seed_local_config.py, but it imports tomllib at module top (area: code/implement) [ks-07]
- `docs/contexts/coga/testing/SKILL.md` — coga/testing "known red baseline" bullet is stale — repo-wide validate is now green (area: coga/testing) [ks-09,ks-33,ks-28]
- `coga/tasks/v2/README.md` — v2 README's title-only expiry rule and "batch precedent" contradict the 2026-09-20 park-v2 direction (area: coga/roadmap (deferred work / v2 parking)) [ks-05]
- `docs/contexts/dev/checkouts/SKILL.md` — dev/checkouts End procedure cannot prove a merge=union log.md was published (area: dev/checkouts) [ks-11]
- `docs/contexts/coga/notifications/producers/SKILL.md` — Producer inventory omits the recurring period-contradiction important alert (area: coga/notifications) [ks-19]
- `docs/contexts/marketing/map/SKILL.md, docs/contexts/marketing/plan/SKILL.md` — marketing/map and marketing/plan link the deleted fix-installer parent ticket (area: marketing) [ks-15,ca-03]
- `docs/contexts/coga/telemetry/operations/SKILL.md` — telemetry/operations still addresses the live wheel proof to PR #880's review (area: coga/telemetry) [ks-16]
- `docs/contexts/coga/workflows/SKILL.md` — coga/workflows says the `branch` gate needs `worktree:`, but the gate only checks the branch (area: coga/workflows) [ks-18,ca-03]
- `coga/recurring/usage-report/ticket.md` — usage-report schedule_comment still names the removed 9am digest (area: coga/recurring) [ks-24,ca-06]
- `docs/contexts/coga/skill-management/SKILL.md` — skill-management spells the per-skill gh argv without the load-bearing `--all` (area: coga/skill-management) [ks-22,ks-29]
- `coga/skills/coga/autoclose/sweep/SKILL.md` — autoclose sweep skill cites a dev/code section that no longer exists (area: coga/autoclose) [ks-21,ca-04]
- `docs/contexts/coga/notifications/failures/SKILL.md` — Failures context says no caller passes record_failure=False, but phone-home does (area: coga/notifications) [ks-19]
- `docs/contexts/coga/important/SKILL.md` — This repo's usage-report routes a weekly FYI to coga-important against the context's bar (area: coga/notifications) [ks-19]
- `src/coga/resources/prompt-queue.md, src/coga/resources/prompt-megalaunch.md` — Queue conduct prompts still trigger the /tmp fallback on "cannot create a linked worktree" (area: coga/session-conduct) [ks-14]
- `coga/skills/coga/blockers/remind/SKILL.md` — Blocker-reminders skill says no ticket owns the paused-period blind spot; an open PR now does (area: coga/blockers) [ks-23]
- `docs/contexts/coga/cli/SKILL.md` — coga/cli lists `claude`/`codex` as default aliases, but they are commented-out opt-ins (area: coga/cli) [ks-31,ca-01]
- `docs/contexts/coga/recurring/autofix/SKILL.md` — Autofix context implies named recurring launches record failed create syncs; they do not (area: coga/recurring) [ks-27]
- `docs/contexts/coga/workflows/SKILL.md` — coga/workflows misstates which workflows the package ships and init seeds (area: coga/workflows) [ks-32,ca-03]
- `docs/contexts/coga/uninstall/SKILL.md` — coga/uninstall has no removal path for the preferred `uv tool install coga` (area: coga/install, coga/uninstall) [ks-29]
- `docs/contexts/coga/internals/recurring-temp-worktrees/SKILL.md` — Temp control worktree context gives a removed detached-HEAD refusal as its rationale (area: coga/internals) [ks-27]
- `docs/contexts/coga/current-direction/SKILL.md` — current-direction still calls PostHog telemetry unshipped after it landed (area: coga/current-direction) [ks-32]
- `docs/contexts/coga/roadmap/SKILL.md` — coga/roadmap names a done ticket among "the open tickets" the v2-parking follow-up must re-scope (area: coga/roadmap) [ks-31,ks-34,ca-02]
- `coga/tasks/premise-check-2026-w39-25-parked-drafts-need-a-ver.md` — Open adjudication draft's F49 verdict for `support-commands-boundary` rests on an extension-model section that no longer exists (area: coga/extension-model) [ks-36]

### drift (3)

- `coga/skills/coga/recurring/verify/SKILL.md` — recurring/verify quotes an error message Coga never emits (area: skills/coga/recurring) [ca-05]
- `README.md` — README Getting Started launches a nonexistent `init` target (area: docs) [ca-06]
- `docs/contexts/dev/code/SKILL.md` — dev/code points schema-conversion rules at coga/sync instead of their owner (area: dev/code) [ca-03]

### gap (4)

- `src/coga/branchsweep.py (merged_pr_verdict) / coga/skills/coga/branch-sweep/sweep/SKILL.md` — Rebased-copy branches accumulate every sweep with no owner for the fix or the manual clearance (area: coga/branch-sweep) [ks-23]
- `docs/contexts/coga/sync/SKILL.md` — Sandboxed agents' state publication fails on read-only .git; no topic says so (area: coga/sync; owner: ticket-sync-fails-with-read-only-git-inside-agent) [ks-14]
- `docs/contexts/coga/skill-management/SKILL.md (URL-backed provenance rules) / src/coga/skill_manager.py::hash_skill_tree` — Git-ignored agent-tooling files inside a URL skill read as local adaptation (clarity false follow-up) (area: coga/skill-management) [ks-23]
- `docs/contexts/coga/lifecycle/SKILL.md` — Canceling or superseding a ticket never repairs the tickets that point at it (area: coga/lifecycle; owner: repair-ticket-referents-when-a-referent-is-renamed) [ks-30]

### premise (35)

- `v2/add-relay-skill-search-with-candidate-eval` — Skill-search draft still names relay-era surfaces on main (area: coga/skill-management; owner: adjudicate-the-eight-premise-dead-v2-drafts; question: surfaces) [ks-35]
- `v2/acceptance-criteria` — Parked `v2/acceptance-criteria` is already delivered by its own named successor, which is `done` (area: coga/tickets (ticket interview); question: delivered) [ks-36]
- `v2/issue-inbox-slack` — `v2/issue-inbox-slack` still names the replaced `relay panic` surface; blocker-reason half already shipped (area: coga/notifications; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: surfaces) [ks-36]
- `v2/relay-design-repositories` — `v2/relay-design-repositories` is partly delivered by the onboarding workflow and still names `relay design`/`relay init` (area: coga/init (onboarding); owner: adjudicate-the-eight-premise-dead-v2-drafts; question: delivered) [ks-36]
- `v2/measure-relay-prompt-scope-and-agent-precision` — Parked prompt-scope/precision draft: half of its remaining part-2 criterion is delivered by `coga usage` (area: coga/usage; question: delivered) [ks-34]
- `v2/split-context-to-doc-user-accessible-and-editable` — split-context draft's pull-forward guard names a gate that has since closed (area: coga/prompt-composition; owner: adjudicate-the-eight-premise-dead-v2-drafts; question: surfaces) [ks-35]
- `v2/implement-accepted-ticket-interview-improvements` — Parked interview-improvements draft still delegates its prompt wording to a retired ticket's git history (area: bootstrap/ticket; question: citations) [ks-34]
- `v2/capture-report-series-google-drive-folder-ids-in-a` — `v2/capture-report-series-google-drive-folder-ids-in-a` outlived the report series it was written for (area: docs (Google Drive); owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: subject) [ks-36]
- `v2/op-service-account-auth-to-skip-op-read-prompt` — `v2/op-service-account-auth-to-skip-op-read-prompt` is already answered by the `coga/secrets` context (area: coga/secrets; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: delivered) [ks-36]
- `v2/compose-strips-skill-md-and-context-frontmatter-be` — `v2/compose-strips-skill-md-and-context-frontmatter-be` names the removed rules layer, `src/relay/` paths, and stale line numbers (area: coga/prompt-composition; question: surfaces) [ks-36]
- `v2/absorb-compound-engineering-leaf-skills-as-a-coga` — Parked CE-absorption study rests on the managed-skill manifest that PR #852 deleted (area: coga/skill-management; question: surfaces) [ks-34]
- `v2/rename-workflow-primitive-to-playbook` — Playbook-rename draft's blast-radius plan still names dead pre-rename surfaces (area: coga/workflows; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: surfaces) [ks-34]
- `v2/launch-tasks-in-container-or-vm` — Container/VM launch draft still preserves dead `feed`/`panic`/lockfile primitives (area: coga/launch; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: surfaces) [ks-35]
- `v2/cleanup-core-commands/lifecycle-verbs-to-ticket-operations` — Lifecycle-verbs cleanup draft's design question is settled by extension-model with the opposite verdict (area: coga/extension-model; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: delivered) [ks-35]
- `v2/validate-tickets-on-hand-edit-gap-outside-relay-co` — Hand-edit validation draft is written against relay-era surfaces, and launch already fails loud on a malformed ticket (area: coga/lifecycle; question: surfaces) [ks-35]
- `v2/add-a-first-class-relay-config-directory-for-machi` — `v2/add-a-first-class-relay-config-directory-for-machi` builds on the removed `mode: script` env-var set and predates the 1Password secrets model (area: coga/secrets, coga/configuration; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: surfaces) [ks-36]
- `v2/use-slack-as-a-sync-channel-for-tickets` — Slack-as-sync draft's premise ("no multi-machine story") and its blocking dependency are both gone (area: coga/sync; question: surfaces) [ks-34]
- `v2/fix-windows-cli-import-crash` — `v2/fix-windows-cli-import-crash`: tier-1 surface list is incomplete — `coga.git` has a top-level `import fcntl` (area: coga/codebase (platform support); owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: surfaces) [ks-36]
- `v2/validate-skill-md-frontmatter-conformance-not-just` — SKILL.md conformance draft still names relay-era paths and the removed skill `script:` field (area: coga/skill-management; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: surfaces) [ks-35]
- `v2/add-dev-testing-setup-skill` — `v2/add-dev-testing-setup-skill` names a deleted consumer skill and a vanished checkout; its "no CI" discovery note is false (area: dev (testing contract); owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: surfaces) [ks-36]
- `v2/cleanup-core-commands/work-orchestration-commands-to-tickets` — Work-orchestration cleanup draft still scopes the removed `coga digest` (area: coga/extension-model; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: surfaces) [ks-34]
- `v2/cleanup-core-commands/residual-command-surfaces` — Residual-command-surfaces draft: alias/init/delete/recurring classification delivered; `ticket` and `skill *` still open per extension-model (area: coga/extension-model; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: delivered) [ks-34]
- `v2/autotrigger-ticket-type` — `v2/autotrigger-ticket-type` models recurring as "a fresh task instance per fire", contradicting the stable `recurring/<name>` period-task model (area: coga/recurring; owner: adjudicate-the-eight-premise-dead-v2-drafts; question: surfaces) [ks-36]
- `v2/op-secret-dependency-init-enforcement` — `op`-at-init draft's baseline (init hard-requires `gh`) is gone (area: coga/secrets; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: surfaces) [ks-34]
- `v2/reintroduce-per-launch-worktree-isolation` — Per-launch worktree draft's motivating hazard is now serialized by `git.state_lock`, and the `coga/sync` limitation it cites no longer exists (area: coga/launch-internals; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: delivered) [ks-34]
- `v2/document-contexts-as-prompt-payload-not-tags-princ` — Contexts-as-payload draft is delivered by coga/knowledge "Attach or cite" and has sat in_progress since July (area: coga/knowledge; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: delivered) [ks-35]
- `v2/log-timestamps-need-seconds-and-timezone-for-unamb` — Log-timestamp draft: core ask live, reconcile half already delivered, all paths relay-era (area: coga/lifecycle; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: surfaces) [ks-35]
- `v2/minimal-ci-run-pytest-on-prs-and-tags` — Minimal-CI draft's opening premise ("no `.github/workflows/`") is false and its citations are relay-era (area: coga/testing; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: surfaces) [ks-35]
- `v2/onboarding-v2-first-run-experience-after-removing` — Onboarding-v2 draft assumes `coga build` is removed, but it was restored and is live (area: coga/first-task; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: subject) [ks-35]
- `v2/clean-uncommitted-work` — clean-uncommitted-work is delivered for `coga/` state by the sync exit sweep (area: coga/sync; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: delivered) [ks-35]
- `v2/use-worktree-when-starting-a-dev-task` — `v2/use-worktree-when-starting-a-dev-task` is now premise-dead: `dev/checkouts` abolished linked worktrees for ticket work (area: dev/checkouts; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: subject) [ks-36]
- `v2/cleanup-core-commands/launch-decomposition` — Parked launch-decomposition draft names moved and deleted surfaces (area: coga/launch, coga/extension-model; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: surfaces) [ks-36]
- `v2/identify-blocking-issues` — `identify-blocking-issues` is framed on the deleted `project` command, and its dependency-field ask was ruled against (area: coga/lifecycle; question: subject) [ks-34]
- `v2/coga-recurring-ack` — `coga recurring ack` draft: the reminder harness has now landed and deliberately ships no ack writer (area: coga/recurring; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: surfaces) [ks-34]
- `v2/register-a-real-domain-for-relay` — Domain draft pairs itself with Wave 1 launch-gate tickets that no longer exist (area: marketing/plan; owner: premise-check-2026-w39-25-parked-drafts-need-a-ver; question: surfaces) [ks-34]


## Phase 4 — Retro (result: pr-opened)

11 eligible done tickets (118 other done tickets carry a real `## Dev` checkout = retirement debt, left for `coga retire`).
- Knowledge PR https://github.com/FastJVM/coga/pull/920 "New context: another clone's primary checkout never leaves the autoclose worklist" — deletes `clean-up-all-the-working-trees`, `recurring/autoclose-merged`; edits dev/checkout-cleanup (+twin). Carries an unresolved adjacent bug (standalone-clone worklist entries re-post forever) → needs a follow-up ticket (Phase 6).
- Direct-deleted (verified gone on origin/main): correct-two-stale-marketing-map-catalogue-rows-aft, recurring/{address-pr-comments,blocker-reminders,branch-sweep,phone-home,resolve-conflicts,skill-update,upstream-coga,usage-report}.
- Verified: PR branch pushed, deletes landed, checkout had nothing unlanded; worktree, temp branch, local-config copy and run dir removed.

## Dream Skill: cleanup-orphan-markers

Generated: 2026-09-29T16:37:08+00:00
Task: `recurring/dream`

Result: no-op. No cleanup-eligible processed done tickets still have task directories.

## Dream Run Summary

Generated: 2026-09-29T16:42:31Z — period 2026-W40, repo-identity coga-source. Preflight: git-common-dir ok, remote ok, gh ok.

| Phase | Result | Detail |
| --- | --- | --- |
| 1 validate-drift | reported | 43 issues: 0 direct-fix, 1 pr-proposal, 42 human-needed |
| 2 knowledge scan | reported | 36/36 shards; 94 raw → merged with Phase 3 into 92 findings |
| 3 contract audit | reported | 7/7 shards; 10 raw drift (9 dup of Phase 2); packaging twins green |
| 4 retro/done-ticket | pr-opened | 11 eligible: 1 knowledge PR (#920, 2 tickets), 9 direct deletes |
| 5 cleanup-orphan-markers | no-op | no orphaned processed markers |
| 6 disposition | proposed | 9 proposal PRs, 11 draft tickets, 0 upstream-captured |

**Findings (92):** 24 extract (19 done+checkout → retirement debt, 5 canceled → PRs/drafts), 26 stale + 3 unique drift, 4 gap, 35 premise.

**Proposal PRs (pr-required, not merged):**
- #920 New context: another clone's primary checkout never leaves the autoclose worklist (Phase 4 Retro)
- #921 Restore Retro's adjacent-bug rule in coga/dream — ks-04
- #922 Repoint contexts and skills at references that moved or were deleted — marketing map/plan, autoclose sweep citation, skill-creator ATTRIBUTION (ks-15/ks-21/ks-04, ca-03/ca-04)
- #923 Drop the cleared repo-wide validate baseline from coga/testing — ks-09/28/33
- #924 Record the usage-record facts a future price table needs — canceled `define-the-api-equivalent-cost-proxy-and-price-tab`
- #925 Record two verified gotchas from canceled tickets — `nothing-exercises-python-3-11-the-declared-floor`, `digest-can-clobber-recurring-last-serviced-period`
- #926 Refresh direction topics (current-direction, roadmap, telemetry/operations) — ks-32/31/34/16, ca-02
- #927 Correct the CLI index's default aliases and the README first-run command — ks-31, ca-01, ca-06
- #928 Correct three stale recurring-job claims (usage-report schedule_comment, autofix scope, temp-worktree rationale) — ks-24/27, ca-06
- #929 Fix a stale sandbox-fallback trigger and a phantom error quote in agent instructions — ks-14, ca-05

**Draft tickets created:**
- Overlap with open PRs (finding not carried by that PR): `apply-three-dream-w40-skill-and-context-correction` (#909: self-qa, dev/code link, implement python), `apply-three-dream-w40-workflow-and-v2-readme-corre` (#912: workflows ×2, v2 README expiry), `apply-three-dream-w40-notification-and-skill-manag` (#914: producers, skill-management --all, canceled `v2/skill-update-aborts-on-uncommitted-log-file` extract), `name-phone-home-as-the-record-failure-false-caller` (#911), `record-that-contexts-linking-tickets-by-path-break` (#918; canceled `phase-0-audit-is-complete-per-the-plan-but-still-i` extract)
- Human choice: `decide-whether-the-weekly-usage-report-belongs-on` (coga/important vs usage-report), `uninstall-has-no-removal-path-for-the-preferred-uv`
- Gaps: `branch-sweep-never-clears-rebased-copy-branches`, `url-skill-digest-counts-git-ignored-agent-tooling`
- Retro adjacent bug (PR #920): `autoclose-re-posts-another-clone-s-primary-checkou`
- Premise adjudication: `premise-check-2026-w40-8-parked-drafts-need-a-verd` (8 drafts + correction to W39 F49 for `support-commands-boundary`)

**Already ticketed / covered:**
- validate-drift: empty-description → `validate-drift-empty-description-23-title-only-tic` (24 members now; 17 v2 stubs are an already-decided class per `coga/roadmap` "park v2", tag `validate-drift: empty-description`; new non-v2 since filing: autoclose-should-be-script-only, autofix/name-cross-repo-retire-follow-ups-with-the-repo-th, autofix/treat-non-requestexception-slack-send-errors-as-de, improve-pr-check, recurring-unblock-launch, stop-with-all-the-worktreees-its-super-noisy-and-u)
- validate-drift: unfrozen-workflow → `validate-drift-unfrozen-workflow-11-hand-authored` (15 members; new: dream-should-be-able-to-use-codex-instead-of-claud, implement-the-include-allowlist-that-url-skill-upd, make-every-code-workflow-review-with-the-other-age, marketing/idea-piece, marketing/readme-top, ticket-sync-fails-with-read-only-git-inside-agent, where-have-code-review-disappeared)
- validate-drift: stuck-in-progress → `validate-drift-stuck-in-progress-11-in-progress-ti` (3 members, none new)
- dev/checkouts union-log End procedure → PR #909; blockers/remind "no ticket owns" → PR #914
- read-only .git state publication gap → `ticket-sync-fails-with-read-only-git-inside-agent`; cancel/supersede referent repair gap → `repair-ticket-referents-when-a-referent-is-renamed` (its target should be retargeted at coga-side surfaces)
- 27 premise findings → `premise-check-2026-w39-25-parked-drafts-need-a-ver` / `adjudicate-the-eight-premise-dead-v2-drafts`

**Phase 1 pr-proposal:** `large-blackboard` on `reconcile-recurring-wrapper-tty-admission-guidance` (54 KiB) — a done ticket with a real `## Dev` checkout; its retirement (`coga retire`) removes it and clears the warning, so no restructuring PR was opened.

**Machine-local validator issues:** none.

**Retirement debt (118 done tickets with a real `## Dev` checkout; `coga retire <slug>` is the consumer).** Extracts each retirement unlocks: `the-v2-parking-area-premise-check-has-four-holes` (coga/dream premise pass), `make-dream-run-correctly-under-codex` (codex subagent mechanics; --agent override lost in completion attribution — adjacent bug), `four-parked-tickets-carry-premises-that-have-since` (verdict-application mechanics), `redo-documentation-dir-and-merge-it-with-context-b` (bundled-topic link topology), `validate-that-committed-skill-scripts-with-a-sheba` (non-executable-script check undocumented), `simplify-git-sync` (why publication never commits locally/stashes/rebases), `persist-autoclose-retire-follow-ups` (tag-shadowed for-each-ref names), `recurring-task-to-manage-all-open-pr-and-address-c` (shipped templates leave owner/agent empty), `add-an-agent-picker-for-recurring` (typer optional-value flag), `attribute-headless-recurring-completions-to-system` (strict-assist audit publication), `exclude-superseded-designs-from-launch-prompts` (blocker parsing not fence-aware), `reuse-the-existing-control-worktree-for-recurring` (shared subprocess patching gotcha), `agent-usage-report` (ticket.py sibling access; usage.rollup until inclusive), `cleanup/handle-a-bare-slack-webhook-url-during-empty-repo` (init bare SLACK_WEBHOOK_URL tolerance), `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` (coga.resources regular package), `make-sure-repo-clietn-don-t-edit-coga` (`##` inside a fence truncates Description), `simplify-ticket-format` (--agent override vs peer resolution).
Full list: `a-slack-repo-without-important-webhook-can-abort-t`, `activation-does-not-resolve-step-1-s-assignee-role`, `add-an-agent-picker-for-recurring`, `adjudicate-parked-and-active-tickets-whose-premise`, `agent-usage-report`, `allow-description-and-owner-on-create`, `apply-12-context-and-skill-corrections-blocked-by`, `attribute-headless-recurring-completions-to-system`, `autoclose-preserved-checkout-remedies`, `autoclose-should-name-the-retire-follow-up`, `autoclose-should-name-unanswered-review-threads-on`, `autofix/keep-cross-clone-retire-follow-ups-from-being-disc`, `autofix/make-dream-block-instead-of-done-when-its-retro-ch`, `autofix/report-per-skill-outcomes-from-gh-skill-update-in`, `autofix/stop-one-failing-ticket-py-from-starving-the-rest`, `automerge/fix-let-a-lot-of-open-craps`, `branch-sweep-strands-squash-merged-branches-whose`, `bumppy-requires-exactly-two-agents`, `carry-adjacent-bugs-out-of-a-blackboard-before-ret`, `cleanup/add-a-debug-mode-to-init-for-vendoring-from-source`, `cleanup/add-contributing-docs-issue-templates-and-a-repo-d`, `cleanup/detect-the-current-git-branch-instead-of-hard-codi`, `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r`, `cleanup/handle-a-bare-slack-webhook-url-during-empty-repo`, `cleanup/quiet-the-first-run-noise-from-recurring-jobs-and`, `cleanup/yank-the-pypi-0-0-1-placeholder-and-document-the-f`, `cloning-a-coga-repo-has-no-setup-path`, `coga-build-fails-after-init-on-a-github-scaffolded`, `correct-the-v2-known-stale-surfaces-table-and-rout`, `define-the-recipe-reporting-contract-report-durabi`, `detect-stranded-ticket-writes-across-checkouts`, `document-how-packaged-contexts-reach-a-repo-and-se`, `document-how-to-recover-a-retired-ticket-s-body-fr`, `document-the-remedy-for-a-bloated-blackboard-sibli`, `document-the-ticket-blackboard-writer-s-contract`, `document-when-to-attach-a-large-context-versus-cit`, `dream-2026-w36-extract-backlog-18-findings-phase-4`, `dream-2026-w38-extract-backlog-4-findings-phase-4`, `dream-findings-have-three-routing-holes-that-lose`, `dream-phases-2-3-cannot-complete-scan-subagents-re`, `dream-reconciliation-must-count-distinct-shard-ids`, `exclude-superseded-designs-from-launch-prompts`, `fix-the-autofix-analyst`, `four-docs-cite-positioning-context-sections-that-w`, `four-parked-tickets-carry-premises-that-have-since`, `give-a-ticket-s-superseded-design-one-documented-h`, `give-the-three-kinds-of-work-taxonomy-an-owning-do`, `installer-managed-skills-the-local-adaptation-guar`, `isolated-checkouts-nothing-says-what-a-fresh-workt`, `keep-agent-edits-to-contexts-and-skills-off-the-co`, `launch-activates-before-preflight`, `launch-ignores-the-recorded-worktree-stranding-bla`, `live-and-packaged-twin-pairs-are-edited-together-b`, `make-dream-run-correctly-under-codex`, `make-sure-repo-clietn-don-t-edit-coga`, `marketing/add-telemetry`, `megalaunch-activates-picks-before-preflight`, `megalaunch-only-shows-one-page`, `migrate-recurring-templates-to-ticket-py-shims-and`, `move-cogacontext-to-roodoc-so-its-easier-for-human`, `narrative-candidates-md-publishes-log-text-the-own`, `no-comms-writing-skill-the-process-is-smeared-thro`, `no-context-records-the-ci-posture-publish-only-rel`, `no-rule-says-ticket-context-must-cite-symbols-not`, `no-skill-exists-for-the-cold-evaluator-review-of-a`, `packaged-code-workflows-never-name-coga-retire-as`, `packaged-repos-ship-recurring-templates-without-th`, `persist-autoclose-retire-follow-ups`, `preserve-edits-during-released-claim-recovery`, `put-build-back`, `read-the-recurring-serviced-period-from-the-log-dr`, `reconcile-recurring-wrapper-tty-admission-guidance`, `record-dochub-s-why-not-the-api-answer-that-browse`, `record-four-repeated-dev-loop-verification-gotchas`, `record-or-clear-the-standing-repo-wide-coga-valida`, `recurring-context-never-mentions-the-packaged-twin`, `recurring-last-serviced-period-compares-as-a-strin`, `recurring-recipe-question`, `recurring-sweep-aborts-and-orphans-a-deleted-done`, `recurring-sweep-wedges-on-the-ticket-py-it-copies`, `recurring-task-to-manage-all-open-pr-and-address-c`, `redo-documentation-dir-and-merge-it-with-context-b`, `refresh-recurring-ledger-before-first-create-sync`, `refuse-recurring-runs-from-a-non-control-branch`, `reject-context-artifacts-that-escape-the-checkout`, `remov-digest-in-recurring`, `remove-coga-build-and-project`, `remove-legacy-config-compatibility-shims`, `retire-never-removes-a-worktree-that-ran-the-tests`, `reuse-the-existing-control-worktree-for-recurring`, `review-slack-channels`, `rewrite-coga-base-prompt-and-agent-mode-block`, `run-the-landed-branch-sweep-daily-from-autoclose`, `select-session-conduct-instead-of-appending-a-cont`, `service-recurring-from-a-temp-control-worktree-ins`, `settle-whether-megalaunch-is-the-only-unclassified`, `simplify-git-sync`, `simplify-ticket-format`, `state-which-branch-is-canonical-for-machine-genera`, `stop-recurring-on-inactive-repo`, `stop-syncing-task-state-onto-the-feature-branch`, `stop-using-worktrees`, `sync-context-omits-preflight-post-from-the-notific`, `the-autofix-analyst-ticket-closed-without-shipping`, `the-human-doc-vs-agent-context-boundary-is-decided`, `the-period-task-context-never-covers-the-determini`, `the-retro-done-ticket-skill-should-verify-a-done-t`, `the-ticket-interview-never-asks-what-done-means`, `the-v2-parking-area-premise-check-has-four-holes`, `ticket-relationships-and-ownership-have-no-mechani`, `ticket-specs-should-cite-symbols-not-line-numbers`, `title-only-tickets-have-no-convention-and-no-valid`, `unblock-rewind`, `v2/propagate-local-coga-config-into-worktrees`, `v2/ship-a-shared-recurring-reminder-engine-battery`, `validate-drift-classifier-misses-17-emitted-kinds`, `validate-that-committed-skill-scripts-with-a-sheba`, `vendored-skills-carry-no-coga-source-json-so-coga`.

**Human-needed / review gates:** review and merge PRs #920–#929; triage the 11 new drafts; owner verdicts in the W40 and W39 premise drafts.
