---
title: Dream
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: bfeed55d-68fd-41da-9e56-767fd5f5ccd9
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
finding's `source:` line, each `gap` finding's `owner:` line, and every
`owner: coga` line on any class, through the merge — Phase 6 routes on them.

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
into a parked (`_`-prefixed) directory such as `coga/tasks/_v2/` — parking is
the human's decision, made after reading a draft, and a Dream draft parked
there by construction decays unread. The `--description` names the Dream run (period, phase, shard) and the
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

Then append one top-level `## Dream Run Summary` section to this task's
blackboard: the generation time, a phase result table using the vocabulary
`no-op`, `reported`, `partial`, `proposed`, `direct-fixed`, `pr-opened`,
`human-needed`, `upstream-captured`, the finding counts with one-line
summaries, the number of entries appended to `coga/upstream-coga.md` (zero in
the Coga source repo), links to every PR
opened and draft ticket created, every `already ticketed as` line, the
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

Generated: 2026-10-05T18:32:29+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python -m coga.validate --json --fix`
Task: `recurring/dream`

Result: 30 issue(s): 0 direct fix, 3 PR proposal, 27 human-needed.

### PR Proposal

- `launch-locks/ticket-ownership-lock`: `large-blackboard` (warn) - blackboard region is 32.9 KiB (warning threshold 32.0 KiB); it is included in launch prompts. Consider summarizing old notes.
  Remediation: Propose the `coga/blackboard` bloated-blackboard remedy: promote a file-form task to directory form (a task that already has `<slug>/ticket.md` keeps its directory), move dated evidence into sibling attachments and superseded material into an unattached context, and leave the current handoff, worklist and verification on the blackboard. Keep `## Dev` and `## Blockers` in place under the `coga/blackboard` contract; CLI readers do not follow attachment links for that state. Move, do not delete.
- `marketing/readme-top`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (non-placeholder blackboard is 986 characters); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Propose a reviewed synthesis of durable authoring decisions into the ticket body. Preserve intentional launch-only notes under `## Production notes`; do not discard ambiguous content.
- `reconcile-recurring-wrapper-tty-admission-guidance`: `large-blackboard` (warn) - blackboard region is 54.0 KiB (warning threshold 32.0 KiB); it is included in launch prompts. Consider summarizing old notes.
  Remediation: Propose the `coga/blackboard` bloated-blackboard remedy: promote a file-form task to directory form (a task that already has `<slug>/ticket.md` keeps its directory), move dated evidence into sibling attachments and superseded material into an unattached context, and leave the current handoff, worklist and verification on the blackboard. Keep `## Dev` and `## Blockers` in place under the `coga/blackboard` contract; CLI readers do not follow attachment links for that state. Move, do not delete.

### Human Needed

- `add-an-applying-a-batch-of-verdicts-section-to-the`: `stuck-in-progress` (warn) - in_progress but idle for 165.4h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `autoclose-should-be-script-only`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `autofix/name-cross-repo-retire-follow-ups-with-the-repo-th`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `carry-the-apply-the-register-amendment-step-in-a-w`: `stuck-in-progress` (warn) - in_progress but idle for 121.6h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `dream-should-be-able-to-use-codex-instead-of-claud`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `fix-coga-git-sync-failures-that-leave-main-diverge`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `fix-git-sync-failure`: `unfrozen-workflow` (warn) - workflow 'code/with-self-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `fix-the-commit-git-journal`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `gigantic-refactor-move-recurring-recipes-out-of-co`: `stuck-in-progress` (warn) - in_progress but idle for 120.7h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `implement-the-include-allowlist-that-url-skill-upd`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `improve-pr-check`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `launch-locks/ticket-ownership-lock`: `stuck-in-progress` (warn) - in_progress but idle for 92.2h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `lifecycle-writes-read-control-s-ticket-before-modi`: `stuck-in-progress` (warn) - in_progress but idle for 167.5h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `make-every-code-workflow-review-with-the-other-age`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `marketing/1st-users`: `unfrozen-workflow` (warn) - workflow 'draft-for-human' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `marketing/build-the-launch-plan`: `stuck-in-progress` (warn) - in_progress but idle for 240.8h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `marketing/idea-piece`: `unfrozen-workflow` (warn) - workflow 'draft-for-human' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `marketing/readme-top`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `open-pr-becomes-detereminstici-mechanic-no-check`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `parse-agents-rejects-cogalocaltoml`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `recover-when-local-main-carries-hand-commits-of-co`: `stuck-in-progress` (warn) - in_progress but idle for 72.8h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `recurring-unblock-launch`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `stop-creating-linked-worktrees-for-coga-retire`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `stop-with-all-the-worktreees-its-super-noisy-and-u`: `empty-description` (warn) - `## Description` is empty — a title-only ticket whose intent is unrecoverable from the repo; write the description down, or cancel with a recorded reason when the author confirms it is lost. Do not cancel it just to clear this warning
  Remediation: A title-only ticket: only its author can say what the title meant. Ask the owner to write the description in their own words, or to cancel it with a recorded reason when the intent is lost. Do not infer a description from the slug, and never cancel a draft merely to clear this warning — a green validate is a consequence of a correct verdict, not a reason for one.
- `ticket-sync-fails-with-read-only-git-inside-agent`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `usage-report-name-the-human-split-per-agent-show-c`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `where-have-code-review-disappeared`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.

## Run notes (2026-10-05)

- preflight: git-common-dir ok, remote ok (origin/main), gh ok.
- Phase 1 validate-drift: 30 issues (0 direct-fix, 3 pr-proposal, 27 human-needed).
- repo-identity: coga-source (no Rule A exclusion).
- Phase 2 scan dir: /tmp/dream-ks.GdtVuo — 33 area shards (ks-01..ks-33), live Dream task excluded from corpus.
- Phase 3 scan dir: /tmp/dream-ca.ept1L3 — 8 shards (ca-01..ca-08; ca-08 = copy divergence).

## Findings

Merged from Phase 2 (/tmp/dream-ks.GdtVuo, 33 shards) and Phase 3 (/tmp/dream-ca.ept1L3, 8 shards). IDs K<n> = knowledge-scan block n, C1..C3 = contract audit. K15 merged into K11; K10 merged into C2.

### extract/done

- K4 [ks-03] **Releasing: pre-tag local gate and the post-upload stale-index install** — target: `cleanup/publish-coga-1-0-to-pypi`; area: coga/releasing; The 0.4.0 release (blackboard "Release execution — 2026-10-02"; the ticket has no `## Dev` section) ran and recorded a pre-publish gate that `docs/contexts/coga/releasing/SKILL.md` "Real release" does not state: before drafting the GitHub Release, run the full suite against the release checkout (`PYTHONPATH=<checkout>/src python -m pytest`), build both distributions and `twine check dist/*`, and install the built wheel into a fresh Python 3.11 venv (the `requires-python` floor) and run `coga --version`, `coga init --user tester`, and `coga validate --json` in a scratch Git repo. The context's step 4 verifies with an unpinned `pipx install coga && coga --version`; the ticket found that the first unpinned install immediately after the Trusted Publishing upload still resolved the previous version (0.2.0) from a stale index/cache, and only a new fresh environment after the index refreshed obtained 0.4.0 (`pip install --no-cache-dir --index-url https://pypi.org/simple coga`). Add both to "Real release": the pre-tag gate as a step before tagging, and a note that the post-publish check must use a fresh venv with `--no-cache-dir` (or pin `coga==<version>`) and may need a retry while the index propagates, rather than treating the old version as a failed publish.
- K16 [ks-13] **macOS harness: reusing an already-billed EC2 Mac host needs a manual substitution** — target: `marketing/fix-installer/run-clean-installs-and-file-issues`; area: coga/testing/clean-install/macos-aws; The 2026-10-01 clean-install run reused host `h-0833c01ac15e645ac` (allocated the previous day by the harness ticket, still inside its 24-hour billing minimum) with explicit owner approval instead of allocating a second host. `scripts/clean-install/aws-mac.sh provision` always calls `ec2 allocate-hosts` (line ~181) and has no switch to target an existing host, so the operator ran a temporary copy that substituted the existing host ID for the allocation; the standard `teardown <name>` then cleaned up and released the host from the new ledger. The `coga/testing/clean-install/macos-aws` runbook says to "run every walk you need on one host within its first day" but does not say that a host allocated under one provision name cannot be reused by a later provision without editing the script, nor that reuse needs separate owner approval and that the new ledger becomes the one that must record `HOST_RELEASED`. Add a short "Reusing an allocated host" note to the Cost/Teardown sections (and packaged twin), or file a harness switch.

### extract/canceled

- K19 [ks-07] **Native Windows is unsupported at import time; no context states Coga's platform support** — target: `premise-check-2026-w39-25-parked-drafts-need-a-ver`; area: coga/codebase; The canceled W39 premise-check ticket (finding F63, shard ks-21) verified a reusable platform fact that no context records: `src/coga/git.py` imports `fcntl` at module top (for the `fcntl.flock` state-publication barrier lock) and `src/coga/repl_supervisor.py` does too, and `cli.py` imports `coga.git` eagerly, so every `coga` command — including `coga --help` — fails with `ModuleNotFoundError: No module named …
- K24 [ks-17] **Record the owner's decline of a pytest CI gate in coga/testing's CI posture** — target: `nothing-exercises-python-3-11-the-declared-floor`; area: coga/testing; The canceled ticket records an owner decision not to act (2026-09-24): test verification is a Coga workflow property (the implement / self-qa / review steps), not a GitHub Actions gate, so PR #894 adding a Python 3.11/3.12 pytest matrix (`.github/workflows/tests.yml`) was closed unmerged; the port survives as commit 58630a20f. `docs/contexts/coga/testing/SKILL.md` "CI posture and receipts" still describes the …
- K34 [ks-32] **Record the declined split-a-ticket mechanic and the dropped oversized-ticket guidance** — target: `define-the-split-a-ticket-mechanic-shared-by-code`; area: coga/tickets; The ticket (canceled 2026-09-25: "Won't do: oversized work escalates to the owner instead (PR #899); #889 closed") records an owner decision not to define a split mechanic (no `code/split-ticket` skill, no `## Split` blackboard roster, no `**Split from …** / After:` cross-link convention). Follow-up commit 2ffcd4f8b then removed the oversized-ticket guidance from `code/design` and `code/implement` entirely …
- K37 [ks-30] **Record the declined base-prompt rule against agents committing Coga state** — target: `tell-agents-never-to-git-commit-coga-task-and-log`; area: coga/sync (land in coga/internals/state-publication beside "Never `git add` coga/tasks/** or coga/log.md into a PR", or coga/prompt-composition); On 2026-10-01 the owner canceled adding a base-prompt (`src/coga/resources/prompt.md`) rule telling agents never to `git add`/`git commit` `coga/tasks/**` or `coga/log.md`, after an attended orient session hand-committed ticket and log state on local `main` (mimicking Coga's own commit subjects), diverging it from origin so `coga launch` refused and the operator's `git pull --rebase` failed on the dirty log. The …

### stale

- K2 [ks-01] **checkout-cleanup omits that retire skips checkout disposal off the control branch** — target: `docs/contexts/dev/checkout-cleanup/SKILL.md`; area: dev/checkout-cleanup; The `coga retire` section says retire "first disposes of the checkout and branch under the proofs above", unconditionally. `src/coga/commands/retire.py::_cleanup_checkout` skips disposal entirely (printing `Retire: checkout cleanup skipped (run from '<control>'; current checkout is '<branch>')`) when the checkout retire runs from is not on `[git].control_branch`, and also when `[git].enabled` is false or the ticket …
- K12 [ks-06] **activity-capture omits the Codex subagent-rollout exclusion** — target: `docs/contexts/coga/internals/activity-capture/SKILL.md`; area: coga/internals/activity-capture; The Codex matching paragraph says capture claims "the one new file whose `session_meta.payload.cwd` equals the session cwd ... None or several → usage unknown." Since ticket `make-dream-run-correctly-under-codex` (PR #891), `usage._parse_codex_session` first skips any rollout whose `session_meta.payload` marks a subagent (`thread_source == "subagent"` or a non-empty `parent_thread_id`), because every codex child …
- K18 [ks-12] **marketing/plan scope list omits the owner-agreed first-user ICP and recruiting work** — target: `docs/contexts/marketing/plan/SKILL.md`; area: marketing/plan; `marketing/plan` "Scope" says "The remaining marketing work is launch execution, the idea piece, the README, the `fix-installer/` ticket group, PostHog live-wheel verification and the final V1 release" and "There is no separate audience/story/pitch pipeline". Since then the owner agreed (2026-09-29, recorded in draft `marketing/1st-users`) to audit and record a first-user ICP as a new `marketing/first-users` …
- K20 [ks-16] **codebase/gotchas says every shipped ticket.py shim calls run_recipe; phone-home's does not** — target: `docs/contexts/coga/codebase/gotchas/SKILL.md`; area: coga/codebase; The "Shipped `ticket.py` shims go through the runner" seam states shims call `run_recipe(load_config(), "<name>", [])` rather than importing the job function. That holds for autoclose-merged, blocker-reminders, branch-sweep and skill-update, but the shipped `src/coga/resources/templates/coga/recurring/phone-home/ticket.py` is the wheel-owned edge shim: it does `from coga_edge.phone_home import main` and `raise …
- K23 [ks-23] **Gotchas list of shadowable `--abbrev-ref HEAD` callers omits `git.current_branch`** — target: `docs/contexts/coga/codebase/gotchas/SKILL.md`; area: ; The hazard says `branchsweep._current_branch` and two `open_pr.py` call sites "still use the shadowable form", implying the rest of the tree is fixed. But the shared `git.current_branch` (`src/coga/git.py:1522-1524`) is `rev-parse --abbrev-ref HEAD` and is called from `git.py:332` (refresh fast-forward guard), `git.py:759`, `commands/retire.py:168`, `commands/bump.py:407`, `autoclose.py:1006`, and …
- K27 [ks-21] **coga/important still says "nothing else goes there" while the weekly usage report deliberately posts there** — target: `docs/contexts/coga/important/SKILL.md`; area: coga/important; `coga/important` says the important destination is only for notifications that need a human to act ("Nothing else goes there."). But `coga/recurring/usage-report/ticket.py` (on main and origin/main) still calls `post(cfg, text, important=True, fatal=False)`, and its `ticket.md` step 3 documents the important route. The done ticket `decide-whether-the-weekly-usage-report-belongs-on` was filed to settle this conflict. …
- K28 [ks-19] **autoclose/sweep still describes per-branch linked worktrees as the live checkout layout** — target: `coga/skills/coga/autoclose/sweep/SKILL.md`; area: coga/autoclose; The "Only from the control branch, only this clone's worktrees" paragraph says, in present tense, that "in this repo the recurring jobs run from `/home/n/Code/claude/coga`, whose `/home/n/Code/claude/coga-<branch>` worktrees are what the worklist names", and the section framing assumes closed tickets normally record a linked `worktree:`. Since `stop-using-worktrees` merged (`e122d774`, PR #896), `dev/checkouts` …
- K29 [ks-14] **extension-model classifies every built-in head except `coga owner`** — target: `docs/contexts/coga/extension-model/SKILL.md`; area: coga/extension-model; `aliases.BUILTIN_COMMANDS` and `src/coga/cli.py:87` register `coga owner <slug> <name>` (`src/coga/commands/owner.py`: the single writer of a ticket's `owner:`, "shaped like a `coga.mark` transition" — prospective validation, locked write, audit line, guarded control sync). The topic says existing command heads without a settled home are "recorded under Open command placements", and its Kernel tier names `mark`, …

### gap

- K40 [ks-29] **Sandboxed agent sessions cannot publish ticket state (read-only `.git`), and no sync topic says so** — target: `docs/contexts/coga/internals/state-publication/SKILL.md`; area: coga/sync; owner: lifecycle-writes-read-control-s-ticket-before-modi; A recurring failure with no knowledge surface: a state-changing command (`bump`/`mark`/`block`/`create`) run inside an agent sandbox fails `publish` at its first object write (`git hash-object -w` → "unable to create temporary file: Read-only file system", or `index.lock: Read-only file system`), leaving the transition dirty on disk until a later out-of-sandbox sweep or a human push. Evidence from independent …

### extract/done+checkout

- K0 [ks-01] **Retire carries a preserved checkout's reason into the retro task body; status probe is -z and fails closed** — target: `retire-never-removes-a-worktree-that-ran-the-tests`; area: dev/checkout-cleanup; The ticket (status done, `## Dev` records branch `retire-cache-worktrees` and worktree `/home/n/Code/claude/coga-retire-cache-worktrees`, now gone) shipped three durable facts that `docs/contexts/dev/checkout-cleanup/SKILL.md` does not state: (1) when retire preserves a recorded worktree, `commands/retire.py::_checkout_cleanup_section` appends a `### Checkout cleanup` section to the scaffolded `retire-<slug>` task …
- K1 [ks-02] **open-pr freshness does not treat coga/recurring/** as state drift** — target: `launch-moves-the-checkout-to-main-before-and-after`; area: coga/internals/pr-publication; The ticket's Open-PR handoff (2026-09-28) recorded that `coga open-pr` refused a branch as stale although `origin/main` had moved only through Coga state, because `github_preflight.is_coga_state_path` (verified in `src/coga/github_preflight.py`) defines "generated Coga state" as only `<coga>/tasks/**` and `<coga>/log.md`, while the state sweep (`coga/sync`, `coga/internals/state-publication`) also publishes …
- K3 [ks-03] **Testing on the 3.11 floor: 3.12 hides 3.11-only stdlib breaks (coga.resources must stay a regular package)** — target: `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r`; area: coga/testing; The ticket (PR #831; `## Dev` records branch `resources-pkg-init` and worktree `/home/n/Code/claude/coga-resources-pkg-init`) found that `coga init` crashed on Python 3.11 — the declared `requires-python` floor — while every local and dev run used 3.12, so the break was invisible. Root cause: without `src/coga/resources/__init__.py`, `coga.resources` is a namespace package, `importlib.resources.files()` returns a …
- K5 [ks-03] **Notifications: init's one-read tolerance of a bare SLACK_WEBHOOK_URL is no longer documented** — target: `cleanup/handle-a-bare-slack-webhook-url-during-empty-repo`; area: coga/notifications; PR #825 (`## Dev` records branch `init-bare-slack-env` and worktree `/home/n/Code/claude/coga-init-bare-slack-env`) made `coga init` tolerate a bare exported `SLACK_WEBHOOK_URL`: `commands/init.py::_load_scaffolded_config` pops the variable around init's single `load_config` (needed only to append the seeded `coga-build` audit line on the empty-repo path) and restores it, so both init paths exit 0 and print the …
- K6 [ks-03] **Testing: running a not-yet-installed Coga change from `main` via a source snapshot** — target: `stop-using-worktrees`; area: coga/testing; `stop-using-worktrees` (PR #896; `## Dev` records branch `stop-using-worktrees`, no worktree) changed the very checkout/open-pr contract its own next workflow step had to run, and hit a self-hosting trap the topics do not describe: the operator's installed `coga` (a uv tool install) still implemented the old contract, and the new rule returns the checkout to `main`, which removes the branch's source from the working …
- K7 [ks-04] **Record that Dream's stranded-Retro → blocked rule is prompt-enforced by design** — target: `autofix/make-dream-block-instead-of-done-when-its-retro-ch`; area: coga/dream; The ticket (PR #907, merged 2026-09-28) records an owner decision the `coga/dream` topic does not state: the rule that a run with preserved/unlanded Retro work ends `blocked` instead of `done` is enforced only at prompt level in the Dream template, and the owner explicitly declined code-level detection of Dream's temporary Retro checkouts because it would put Dream-only logic in core (microkernel rule). The sweep …
- K8 [ks-08] **Megalaunch picker one-line-per-candidate rendering invariant and Rich gotchas** — target: `megalaunch-only-shows-one-page`; area: coga/codebase/gotchas (picker rendering; coga/megalaunch links); The done ticket (PR #722 merged; `## Dev` records branch `megalaunch-picker-viewport` and worktree `/home/zach2179/dev/coga-megalaunch-picker-viewport`, so this is retirement debt) verified durable facts about the `--pick` picker in `src/coga/commands/megalaunch.py` that no context states: `_picker_window` budgets in candidates, so `_picker_view` must keep every candidate row and every chrome line (hint line, both …
- K9 [ks-10] **Record why human rewind refuses done tickets (reopen is a separate decision)** — target: `unblock-rewind`; area: coga/lifecycle; `coga/lifecycle` states that `coga bump --to/--backward` refuses terminal tickets but not why, so the refusal reads like an arbitrary gate someone may "relax". The done ticket recorded an owner decision to exclude `done`: reopening is not a gate removal because three mechanisms defend it — `mark_done` pops `step:` (nothing to count back from), `validate` forbids `step:` on a terminal ticket (status and step would …
- K11 [ks-12] **Telemetry live ingestion acceptance was owner-deferred and never performed** — target: `marketing/add-telemetry`; area: coga/telemetry; The done ticket (Dev: branch `phone-home`, worktree `/tmp/coga-phone-home`, PR #880) records an owner decision on 2026-09-22 to defer the live installed-wheel/PostHog queried-row acceptance ("assume it works for current review; owner will test later"); the first/later/disabled HogQL proof in `coga/telemetry/operations` has not been performed or passed, and only automated fake-transport verification stands. Neither …
- K13 [ks-11] **Forced recurring reactivation is durable before launch preflights, by design** — target: `launch-activates-before-preflight`; area: coga/recurring/scheduling; `launch-activates-before-preflight` (done; `## Dev` branch `defer-launch-activation`, worktree `/home/n/Code/claude/coga-defer-launch-activation`) deferred `coga launch`'s durable draft/paused activation past every refusing preflight — already stated in `coga/launch` and `coga/first-task`. Its Out of Scope recorded the deliberate exception that no context states: `recurring_runner._prepare_forced_launch` durably …
- K14 [ks-10] **Blocker reader is section- and fence-blind: archived example asks gate launch** — target: `exclude-superseded-designs-from-launch-prompts`; area: coga/blackboard; The done ticket verified (and handed to retro) a live gotcha that no context states: `src/coga/blackboard.py` `parse_blockers_text` / `open_blockers` match blocker checkbox lines anywhere in the blackboard region with no section or code-fence awareness (still true in current source: `read_blockers` parses the whole `read_blackboard` region). A fenced `- [ ] [<ts>] [human:x] id=old ...` example inside `## Superseded …
- K17 [ks-06] **Launch-time --agent override is not used for audit actor / Slack label (unresolved adjacent bug)** — target: `make-dream-run-correctly-under-codex`; area: coga/launch; The ticket's blackboard (iterations 1 and 2) records an unresolved adjacent bug with no follow-up ticket: under `coga dream --agent codex` the `slack` and `task done` log lines and the Slack label say `agent:claude` / "claude on", and agent-run `coga create` lines say `human:nicktoper`. Cause: `commands/common.py::completion_identity` (supervised branch) and `commands/slack.py` resolve the actor via …
- K21 [ks-18] **Record why notification.post has no catch-all and preflight_post has no TLS probe** — target: `autofix/treat-non-requestexception-slack-send-errors-as-de`; area: coga/notifications/failures; The ticket's implement handoff recorded two owner-level design refusals that `coga/notifications/failures` does not state: (1) `notification.post` deliberately does not wrap `channel.send` in a catch-all `except Exception` under `fatal=False`, because that would also hide real programming bugs in channels — the fix is instead to keep `slack_response.SLACK_TRANSPORT_ERRORS` covering the whole transport surface; (2) …
- K22 [ks-23] **Tag-shadowed branch gotcha also bites `for-each-ref %(refname:short)`** — target: `persist-autoclose-retire-follow-ups`; area: coga/codebase/gotchas; The ticket's self-QA verified that `git for-each-ref --format=%(refname:short)` shortens a branch that shares its name with a tag to `heads/<name>`, which would have made `retire_worklist.local_branches` read a live branch as gone and discharge its worklist line; the fix lists `%(refname)` and strips `refs/heads/` (`src/coga/retire_worklist.py:268-291`). The `coga/codebase/gotchas` hazard "Use `git branch …
- K25 [ks-19] **Shipped recurring templates must not pin `agent:`/`owner:` — periods inherit repository defaults** — target: `recurring-task-to-manage-all-open-pr-and-address-c`; area: coga/recurring; Peer review of PR #857 found that a shipped recurring template carrying an explicit `agent: claude` prevents period creation in a Codex-only repository, even with a launch override. The owner decided shipped templates leave `owner:` and `agent:` empty (with a frontmatter comment) so the minted period inherits the repository's configured owner and agent; …
- K26 [ks-23] **Why skill-update calls `gh skill update` once per skill: bulk mode hides outcomes** — target: `autofix/report-per-skill-outcomes-from-gh-skill-update-in`; area: coga/skill-management; `coga/skill-management` states that GitHub-backed skills are updated with one `gh skill update --dir coga/skills --all <ref>` call each, but not why a single bulk call is unusable — the verified gh v2.92.0 behavior the ticket recorded: `gh skill update` has no `--json`; bulk output never names up-to-date skills individually (only `All skills are up to date.`); and when one repo's ref fails to resolve it prints one …
- K30 [ks-28] **Record why knowledge publication is not gated by actor metadata or lifecycle refusals** — target: `keep-agent-edits-to-contexts-and-skills-off-the-co`; area: coga/internals/state-publication; The ticket (merged as PR #904, branch `fix-authoring-publication` still recorded in `## Dev`) records two owner-declined designs and their reasons that `coga/internals/state-publication` does not state: (b) "human-only knowledge sweeping" keyed on `COGA_TASK_*` launch metadata was rejected because the parent CLI of an agent interview can lack launch metadata while its child authored the edits, and a later human …
- K31 [ks-25] **A recurring ticket.py reaches its template siblings through $COGA_COGA_OS_ROOT/recurring/<name>** — target: `agent-usage-report`; area: coga/recurring/templates; `docs/contexts/coga/recurring/templates/SKILL.md` states that period creation "copies only the reserved `ticket.py`; other siblings stay with the template", but not how the copied shim then finds those siblings. agent-usage-report established and tested the pattern (first recurring `ticket.py` that does not delegate to a core recipe): the shim resolves `Path(os.environ["COGA_COGA_OS_ROOT"]) / "recurring/<name>"` and …
- K32 [ks-25] **coga/usage should name the weekly usage-report consumer and the half-open window recipe** — target: `agent-usage-report`; area: coga/usage; `docs/contexts/coga/usage/SKILL.md` says consumers ("report views") are separate work, but a live consumer now exists: the edge recurring job `coga/recurring/usage-report/` (Mondays 08:00, important route, `fatal=False`, `report.py` beside it, ad hoc `python coga/recurring/usage-report/report.py --since … --until …`), documented by `coga/skills/coga/usage-report/post`. The ticket also verified a reader gotcha the …
- K33 [ks-25] **Typer cannot give an option an optional value; is_flag=False/flag_value is ignored** — target: `add-an-agent-picker-for-recurring`; area: coga/codebase/gotchas; The agent-picker design verified empirically (typer 0.23.2 in the repo venv) that `typer.Option(None, "--agent", is_flag=False, flag_value=...)` still errors `Option '--agent' requires an argument`, because Typer re-derives `is_flag` from the annotation; a sentinel value such as `--agent ?` was rejected because `?` is a shell glob. That is why `coga ticket` grew a separate `--pick-agent` flag (rejected together with …
- K35 [ks-26] **browser/api-first: generalize the DocHub check's evidence standard and re-check triggers** — target: `record-dochub-s-why-not-the-api-answer-that-browse`; area: browser/api-first; `docs/contexts/browser/api-first/SKILL.md` asks only for Yes/No/Partial plus "link or note the docs page checked". The DocHub ticket's peer review established a reusable evidence standard that the context does not state: an old vendor support reply plus unsuccessful documentation searches cannot prove "no API" (the implement step's categorical "No" had to be corrected), so a negative answer should be recorded as "no …
- K36 [ks-27] **`coga validate`'s `non-executable-script` rule is documented nowhere after the context reorg** — target: `validate-that-committed-skill-scripts-with-a-sheba`; area: coga/skill-management; The done ticket (PR #800, merged as `20f6b0fcd`; `## Dev` still records branch `shebang-exec-check` and worktree `/home/n/Code/claude/coga-shebang-exec-check`) added `validate._check_shebang_executables` (`src/coga/validate.py:1386`): any regular file under the installed skills root or the packaged bootstrap skills whose first two bytes are `#!` must carry an executable bit, otherwise `coga validate` reports a …
- K38 [ks-32] **State that a group README does not compose into sibling ticket launches** — target: `prevent-parent-ticket-assumptions-during-task-spli`; area: coga/tickets; The ticket's attached owner clarification (`multiply-task-grouping-context.md`) carries one durable gotcha that did not land with PR #915: "A README does not compose into a ticket launch automatically; each ticket must identify the parts it needs." Verified: nothing under `src/coga/compose.py` or other prompt code reads `README.md` (only `tasks.py`/`dependencies.py` mention it, to exclude it from discovery). …
- K39 [ks-24] **Delegation context omits why the two alternatives to `delegate:` were rejected** — target: `reconcile-recurring-wrapper-tty-admission-guidance`; area: coga/recurring/delegation; The ticket's PR "Design choice" and Context record durable rationale that `docs/contexts/coga/recurring/delegation/SKILL.md` ("Why delegate instead of a nested launch") does not state: (1) making the delegating job deterministic (then a `recipe:`, today the template's own `ticket.py`) was rejected because it moves the template into the TTY-exempt class, so a headless sweep would create the period and only fail at …
- K41 [ks-28] **State the freshness probe's already-rebased early exit as a known stranded-write coverage limit** — target: `detect-stranded-ticket-writes-across-checkouts`; area: coga/internals/pr-publication; `github_preflight.check_branch_contains_control` still returns ok on `git merge-base --is-ancestor <control> <head>` (src/coga/github_preflight.py ~L251-265) before any overlap analysis. The ticket (PR #850, `## Dev` branch `stranded-ticket-writes`, worktree `/home/n/Code/coga-stranded-ticket-writes`) verified and the owner explicitly accepted that consequence: a branch already rebased onto control while carrying a …
- K42 [ks-25] **Manual `coga retire` of a foreign linked worktree still judges the same-named branch in the invoking clone** — target: `autoclose-re-posts-another-clone-s-primary-checkou`; area: dev/checkout-cleanup; The ticket fixed autoclose's foreign-primary path but recorded an unresolved adjacent hazard with no follow-up: `checkout_disposal.dispose_checkout` (reached from `commands/retire.py::_cleanup_checkout` and from autoclose's `_dispose_checkouts` for existing foreign-linked directories) calls `delete_branch(cfg, root, branch, ...)` against the invoking clone even after the worktree proof refuses a foreign repository, …
- K43 [ks-27] **skill-creator's `quick_validate.py` rejects Coga's namespaced `name:` — expected, not a defect** — target: `no-skill-exists-for-the-cold-evaluator-review-of-a`; area: coga/skill-management; The done ticket (PR #752; `## Dev` still records branch `cold-design-review` and worktree `/tmp/coga-cold-design-review`) recorded in `## Verification` that "the generic skill-creator quick validator rejects Coga's namespaced `code/review-design` frontmatter as non-flat; Coga's resolver, composition test, package build, and full suite validate the repository convention." The mechanism is verifiable: …

### drift (contract audit)

- C1 [ca-05] **Shipped code workflows still say the autoclose sweep never disposes of checkouts** — target: `src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md`; `design-then-implement.md` line 78, `with-review.md` line 151, and `with-self-review.md` line 76 (all under `src/coga/resources/templates/coga/bootstrap/workflows/code/`, the `## review` section) state that a done ticket's feature branch and recorded worktree "outlive the close: neither the sweep nor `coga bump` disposes of them, because destructive behavior is never implicit", leaving disposal solely to `coga retire <slug>`. Code reality contradicts this: `coga.autoclose.run_autoclose_recipe` calls `_dispose_checkouts`, which disposes of each closed ticket's recorded `branch:`/`worktree:` (and every open `retires.md` worklist entry) under the shared `coga.checkout_disposal` proofs, and …
- C2 [ca-02] **Phone-home receipt caller named as ticket.py, but the post now lives in coga_edge** (also K10/ks-12, same finding) — target: `docs/contexts/coga/notifications/failures/SKILL.md`; `docs/contexts/coga/notifications/failures/SKILL.md:90-91` names the current `record_failure=False` caller as "the `recurring/phone-home` weekly snapshot receipt (`ticket.py` `_receipt`)", and `docs/contexts/coga/notifications/producers/SKILL.md:151` lists the caller as "phone-home `ticket.py` (`fatal=False`, `record_failure=False`)" under a table whose header says "The module named is the one that calls `post(`". Since #938 (bc46823c4, "Ship edge ticket.py code upgrades with the wheel") `coga/recurring/phone-home/ticket.py` is a three-line shim that imports `coga_edge.phone_home.main`; the `_receipt` function and the `notification.post(..., fatal=False, record_failure=False)` call live in …
- C3 [ca-01] **assist-publication claims an open-pr dirt carve-out that open_pr.py no longer has** — target: `docs/contexts/coga/internals/assist-publication/SKILL.md`; Line 33-36 says the assist's single checkout keeps Coga's live task, log, and recurring state dirty by design and that "`coga open-pr` publishes the pending log append first, then leaves those paths out of its cleanliness gate; any other dirt still refuses." Code reality (`src/coga/open_pr.py`, reworked in #896 "stop using worktrees", after this page's last edit in #875) has no such behavior: `run_open_pr_recipe` first applies `_checkout_mode` (line 650), which refuses any checkout not on the control branch — so open-pr cannot run from the assist's PR feature-branch checkout at all — and the only cleanliness gate, `_check_recorded_clone` (lines ~283-330), treats every dirty path (including …
Phase 2 result: reported — 33/33 shards complete, 44 raw → 42 merged findings. Phase 3 result: reported — 8/8 shards, 3 drift findings.

## Phase 4 — Retro (2026-W41)

Result: pr-opened — 10 eligible done tickets processed (progress file reported `complete`), verified against fetched origin/main; isolated worktree, temp branch, and run dir removed.
- Knowledge PR https://github.com/FastJVM/coga/pull/953 — K4 `coga/releasing`: pre-tag local gate + stale-index post-upload install; deletes `cleanup/publish-coga-1-0-to-pypi`.
- Knowledge PR https://github.com/FastJVM/coga/pull/954 — K16 `coga/testing/clean-install/macos-aws`: EC2 Mac host reuse substitution + unpinned Python 3.11 known failure; deletes `marketing/fix-installer/run-clean-installs-and-file-issues`.
- Direct-deleted (nothing durable, landed on origin/main): recurring/address-pr-comments, autoclose-merged, blocker-reminders, branch-sweep, phone-home, resolve-conflicts, skill-update, usage-report.
- Deferred retirement debt: 139 done tickets with a real `## Dev` checkout (not Retro input; `coga retire <slug>`).

## Dream Skill: cleanup-orphan-markers

Generated: 2026-10-05T18:52:35+00:00
Task: `recurring/dream`

Result: no-op. No cleanup-eligible processed done tickets still have task directories.

## Dream Run Summary

Generated: 2026-10-05 (period 2026-W41). Repo identity: coga-source. Preflight: git-common-dir ok, remote ok, gh ok.

| Phase | Result | Notes |
|---|---|---|
| 1 validate-drift | reported | 30 issues: 0 direct-fix, 3 pr-proposal, 27 human-needed |
| 2 knowledge scan | reported | 33/33 shards, 44 raw → 42 merged findings |
| 3 contract audit | reported | 8/8 shards, 3 drift (copy-divergence shard clean) |
| 4 retro/done-ticket | pr-opened | 10 eligible: 2 knowledge PRs, 8 direct deletes; 139 checkout-bearing done tickets deferred |
| 5 cleanup-orphan-markers | no-op | no candidates |
| 6 disposition | proposed | 6 proposal PRs, 3 draft tickets, 0 upstream-captured (source repo) |

**PRs opened (all `pr-required`, not merged)**
- #953 releasing gate / stale index (Retro K4), #954 macOS harness host reuse (Retro K16)
- #955 marketing/plan first-user ICP scope (K18)
- #956 internals: assist-publication open-pr dirt gate (C3), activity-capture Codex subagent exclusion (K12)
- #957 codebase gotchas `git.current_branch` (K23), extension-model `coga owner` placement (K29; reviewer decides tier)
- #958 phone-home receipt in coga_edge (C2=K10), gotchas shim shapes (K20), coga/important usage-report exception (K27)
- #959 checkout-cleanup off-control retire skip (K2), autoclose/sweep live checkout layout (K28)
- #960 platform support / Windows (K19, canceled source), declined split-a-ticket mechanic (K34), declined no-commit base-prompt rule (K37). Review note: K37 edits `coga/sync`, which open PR #948 also edits — expect a rebase.

**Draft tickets created**
- `correct-the-code-workflows-review-section-autoclos` — C1 (overlaps PR #950 on with-review.md)
- `record-the-owner-s-decline-of-a-pytest-ci-gate-in` — K24, canceled source (overlaps PR #950 on packaged coga/testing)
- `validate-drift-blackboard-hygiene-two-oversized-bl` — Phase 1 pr-proposals: large-blackboard ×2 (launch-locks/ticket-ownership-lock, reconcile-recurring-wrapper-tty-admission-guidance), unsynthesized-draft-blackboard ×1 (marketing/readme-top)

**Already ticketed**
- validate-drift: stuck-in-progress (7 this run) — already ticketed as `validate-drift-stuck-in-progress-11-in-progress-ti`; new since filing: add-an-applying-a-batch-of-verdicts-section-to-the, carry-the-apply-the-register-amendment-step-in-a-w, gigantic-refactor-move-recurring-recipes-out-of-co, launch-locks/ticket-ownership-lock, lifecycle-writes-read-control-s-ticket-before-modi, recover-when-local-main-carries-hand-commits-of-co
- validate-drift: unfrozen-workflow (14) — already ticketed as `validate-drift-unfrozen-workflow-11-hand-authored`; 12 new since filing (see `coga validate --json`)
- validate-drift: empty-description (6) — already ticketed as `validate-drift-empty-description-23-title-only-tic`; all 6 new since filing: autofix/name-cross-repo-retire-follow-ups-with-the-repo-th, fix-the-commit-git-journal, improve-pr-check, open-pr-becomes-detereminstici-mechanic-no-check, recurring-unblock-launch, stop-with-all-the-worktreees-its-super-noisy-and-u
- gap K40 (sandboxed sessions cannot publish state) — already ticketed as `lifecycle-writes-read-control-s-ticket-before-modi` (the canceled `ticket-sync-fails-with-read-only-git-inside-agent` names it as successor)

Machine-local validator issues: none. Already-decided classes: none this run. Reused proposal PRs: none.

**Retirement debt — `extract` findings each `coga retire` unlocks** (139 checkout-bearing done tickets total)
- `retire-never-removes-a-worktree-that-ran-the-tests` — dev/checkout-cleanup: Retire carries a preserved checkout's reason into the retro task body; status probe is -z and fails closed (K0)
- `launch-moves-the-checkout-to-main-before-and-after` — coga/internals/pr-publication: open-pr freshness does not treat coga/recurring/** as state drift (K1)
- `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` — coga/testing: Testing on the 3.11 floor: 3.12 hides 3.11-only stdlib breaks (coga.resources must stay a regular package) (K3)
- `cleanup/handle-a-bare-slack-webhook-url-during-empty-repo` — coga/notifications: Notifications: init's one-read tolerance of a bare SLACK_WEBHOOK_URL is no longer documented (K5)
- `stop-using-worktrees` — coga/testing: Testing: running a not-yet-installed Coga change from `main` via a source snapshot (K6)
- `autofix/make-dream-block-instead-of-done-when-its-retro-ch` — coga/dream: Record that Dream's stranded-Retro → blocked rule is prompt-enforced by design (K7)
- `megalaunch-only-shows-one-page` — coga/codebase/gotchas (picker rendering; coga/megalaunch links): Megalaunch picker one-line-per-candidate rendering invariant and Rich gotchas (K8)
- `unblock-rewind` — coga/lifecycle: Record why human rewind refuses done tickets (reopen is a separate decision) (K9)
- `marketing/add-telemetry` — coga/telemetry: Telemetry live ingestion acceptance was owner-deferred and never performed (K11, +K15)
- `launch-activates-before-preflight` — coga/recurring/scheduling: Forced recurring reactivation is durable before launch preflights, by design (K13)
- `exclude-superseded-designs-from-launch-prompts` — coga/blackboard: Blocker reader is section- and fence-blind: archived example asks gate launch (K14)
- `make-dream-run-correctly-under-codex` — coga/launch: Launch-time --agent override is not used for audit actor / Slack label (unresolved adjacent bug) (K17)
- `autofix/treat-non-requestexception-slack-send-errors-as-de` — coga/notifications/failures: Record why notification.post has no catch-all and preflight_post has no TLS probe (K21)
- `persist-autoclose-retire-follow-ups` — coga/codebase/gotchas: Tag-shadowed branch gotcha also bites `for-each-ref %(refname:short)` (K22)
- `recurring-task-to-manage-all-open-pr-and-address-c` — coga/recurring: Shipped recurring templates must not pin `agent:`/`owner:` — periods inherit repository defaults (K25)
- `autofix/report-per-skill-outcomes-from-gh-skill-update-in` — coga/skill-management: Why skill-update calls `gh skill update` once per skill: bulk mode hides outcomes (K26)
- `keep-agent-edits-to-contexts-and-skills-off-the-co` — coga/internals/state-publication: Record why knowledge publication is not gated by actor metadata or lifecycle refusals (K30)
- `agent-usage-report` — coga/recurring/templates: A recurring ticket.py reaches its template siblings through $COGA_COGA_OS_ROOT/recurring/<name> (K31)
- `agent-usage-report` — coga/usage: coga/usage should name the weekly usage-report consumer and the half-open window recipe (K32)
- `add-an-agent-picker-for-recurring` — coga/codebase/gotchas: Typer cannot give an option an optional value; is_flag=False/flag_value is ignored (K33)
- `record-dochub-s-why-not-the-api-answer-that-browse` — browser/api-first: browser/api-first: generalize the DocHub check's evidence standard and re-check triggers (K35)
- `validate-that-committed-skill-scripts-with-a-sheba` — coga/skill-management: `coga validate`'s `non-executable-script` rule is documented nowhere after the context reorg (K36)
- `prevent-parent-ticket-assumptions-during-task-spli` — coga/tickets: State that a group README does not compose into sibling ticket launches (K38)
- `reconcile-recurring-wrapper-tty-admission-guidance` — coga/recurring/delegation: Delegation context omits why the two alternatives to `delegate:` were rejected (K39)
- `detect-stranded-ticket-writes-across-checkouts` — coga/internals/pr-publication: State the freshness probe's already-rebased early exit as a known stranded-write coverage limit (K41)
- `autoclose-re-posts-another-clone-s-primary-checkou` — dev/checkout-cleanup: Manual `coga retire` of a foreign linked worktree still judges the same-named branch in the invoking clone (K42)
- `no-skill-exists-for-the-cold-evaluator-review-of-a` — coga/skill-management: skill-creator's `quick_validate.py` rejects Coga's namespaced `name:` — expected, not a defect (K43)

Human-needed / review gates: review and merge PRs #953–#960; decide the three drafts; work down retirement debt (`coga retire <slug>`).

