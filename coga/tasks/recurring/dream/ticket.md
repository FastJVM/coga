---
title: Dream
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: a33073f6-35fc-4cb0-9752-6bc7c62631f6
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
    checkout: manual
step: 1 (execute)
---

## Description

Run the Dream cleanup pass for this Coga repo.

This template owns Dream's procedure and contract. With no `workflow:`,
it runs as `direct/body`. The alias `coga dream` launches this recurring
template; the scheduler runs Dream last so it sees the periods that
the same sweep finished (see `coga/recurring/scheduling`).

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

Destructive actions must be deterministic, narrow, and explicitly named
in the invoked skill's `May change`; otherwise propose the change for
review. Missing or failed phases grant no substitute action.

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
agent sandbox grant recipe in the `coga/sandboxes` topic, under
`## Restricted sandboxes`. Then escalate per this prompt's Session conduct
layer: attended, ask the human and wait; unattended, run
`coga block --task <this-dream-task> --reason "<missing capability>; see the
coga/sandboxes Restricted sandboxes recipe"`. A sandbox grant takes effect only
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
or `log.md`, and retained history goes to the repo-global `coga/log.md`. It
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
1. **Create the scan directory** under this Coga workspace's gitignored
   `.coga/`, never under `/tmp`, `mktemp -d`, or `$TMPDIR`. Pick one run id per
   Dream run (`date -u +%Y%m%dT%H%M%SZ`). From the directory holding
   `coga.toml`, create one directory per phase, named for the phase's scan
   skill (`knowledge-scan`, `contract-audit`):
   `mkdir -p .coga/dream-scans/<run-id>`, then
   `mkdir .coga/dream-scans/<run-id>/<phase>`. Keep its absolute path.
   Temporary storage is reaped
   underneath long runs by the OS, the agent harness, or the sandbox, which
   silently empties a live scan and leaves a `partial` result pointing at
   nothing. Both scans and the shard subagents follow
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
   directory, and record its absolute path, the unread paths, and a
   `human-needed` line in the run summary. The path must still resolve when a
   human reads the summary days later; that is why it lives under `.coga/`.
6. **Merge into the blackboard.** Read `findings.md` and merge it into this
   task's `## Findings`, de-duplicating across shards — two shards may describe
   one underlying issue from different evidence; re-read a named file when you
   are unsure whether two findings are the same. Group the `extract` findings by
   the context/skill area they touch.

Delete the scan directory only after its findings are merged into the
blackboard, and only when the phase completed; nothing else removes it. Remove
the `<run-id>` directory once it is empty, so a surviving one always means a
`partial` phase a human still has to read. Report each scan's result as
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
- its blackboard `## Dev` section records no **live checkout**. Check every
  real `branch:` line (`autoclose.parse_branch_names`), not just the first.
  Use `retire_worklist.is_discharged`'s existence and ownership rule: resolve
  `worktree:` relative to this repository's root, identify its owning
  repository with `worktree_owner`, and check the branches in that repository
  (`owner_branch_remains`), not only in Dream's checkout. A primary checkout
  is exempt from directory debt, **not** from branch debt: a branch held only
  in an independent sandbox clone still blocks Retro. Also require every
  recorded branch to be absent from the configured remote
  (`git ls-remote --heads <remote> refs/heads/<branch>`). A non-primary
  worktree directory that still exists blocks Retro. A line naming a branch
  and worktree already gone — the shape autoclose leaves after deleting a
  merged ticket's branch — does not block Retro, and neither do absent, empty,
  or placeholder values such as `(not yet created)`. A probe that cannot
  answer (an unreadable branch list, an unreachable remote) counts as live; and
- no open PR is adding its `## Retro` marker or deleting that resolved task
  directory.

A done ticket with a live checkout is retirement debt, not Retro input. Do
not delegate it to `retro/done-ticket` and do not invoke `coga retire` from
Dream: leave the ticket and its `## Dev` evidence on disk so the exact
human-typed `coga retire <slug>` command remains valid. That command disposes
of the checkout and deletes the done ticket without a retro agent. A canceled
ticket is retirement debt too: Phase 4 never takes it, and `coga retire <slug>`
runs Retro on it for its cancellation reason and other negative learning. List
both kinds as deferred retirement debt in the run summary. After retirement
removes the source ticket, the ordinary existence gate makes it disappear from
Dream's candidate set.

A ticket whose directory is already gone is not a candidate; git history holds
its record. A processed `## Retro` marker on a still-present directory does not
settle the ticket — its deletion PR has not merged, so it stays eligible. Do
not infer completion from branch names, stale comments, or old Dream notes —
only the on-disk directory and open-PR state count.

The `retro/done-ticket` skill owns extraction and deletion: knowledge-bearing
tickets leave in knowledge PRs, and tickets with nothing durable may be
direct-deleted. Read recurring periods' `## Gotchas` before classifying
them; unresolved adjacent bugs or unshipped scope are durable knowledge
unless the owning corpus already preserves them.

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
ticket on disk and never opens a marker-only PR. Retro also searches tracked
files for durable references to each source task, such as a README or doc
link on `blob/<control-branch>`. Before a deletion lands, it repoints each one
to a commit permalink in a PR. A no-durable-knowledge ticket with such a
reference therefore leaves in the run's reference-pin PR, not by direct
delete. The skill's **Inbound references** section owns the rule. The
eligibility gates above do not cover it.

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
members or evidence. Wherever a rule below files a `code/with-review` draft,
first check `[agents.*]` in `coga/coga.toml` and `coga.local.toml`: in a
one-agent repo — only one agent configured, or three or more with no `peer =`
on the main agent — file it with `code/with-self-review` instead.

**Phase 1 blackboard state edits.** `large-blackboard` and
`unsynthesized-draft-blackboard` are `human-needed` owner-directed state edits,
even when an older recipe lists them in `PR Proposal`. Reroute those entries
here before applying the PR-proposal rule. Read `coga/blackboard` for the
remedy: done tickets follow Phase 4's Retro/retirement split, and a recurring
writer's own state goes to that writer's owner. Do not create slimming drafts
for done tickets. For live tickets needing cleanup or an owner decision,
apply the grouping and ownership rule below to file or reuse a
`brief-for-human` draft with no branch or PR requirement. The owner can edit
directly on control; ticket and sibling-attachment changes publish through
`coga/state-publication`. Dream does not rewrite another ticket's blackboard.

Route the remaining Phase 1 `human-needed` issues by validator `kind`, one draft ticket
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
message, and suggested remediation. Route blackboard state edits by the rule
above before handling the remaining proposals. Apply the proposal-ownership rule above to
each issue before opening anything: report the covering ticket or PR, or
preserve uncovered overlap in a scoped draft. For an unowned issue with an
evidenced correction, open a proposal PR applying that correction to the named
reference, template, or other contract. Group only coherent fixes, edit each
shipped definition at its package owner, and include the Dream period,
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
    on disk so the human-typed `coga retire <slug>` stays valid. `coga retire`
    deletes a done ticket without Retro, so this finding is the only route
    for what it saw. Apply the proposal-ownership rule above before opening
    anything. Open a proposal PR that edits the target context or skill with
    the durable fact when no existing proposal or overlap draft owns it,
    citing the source ticket by slug. The PR is `pr-required` like `stale`,
    and Dream leaves the ticket on disk. Also list the ticket under the run
    summary's retirement-debt section so the human can retire it.
  - `canceled` — the source ticket is retirement debt, deliberately left on
    disk so the human-typed `coga retire <slug>` stays valid. That ticket
    is the durable artifact and retirement is its consumer: `coga retire`
    runs Retro over the ticket and extracts what this finding saw. Open no PR
    and file no carrier ticket — a second copy decays while the source stays
    fresh. Instead, list the finding under the run summary's retirement-debt
    section with its slug, area, and one-line summary, so the human can order
    retirements by the knowledge they unlock. This is a standing condition
    while the retirement backlog exists; the same findings recur until the
    tickets are retired, and reporting them again each run is correct.
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

Generated: 2026-11-18T17:08:31+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python -m coga.validate --json --fix`
Task: `recurring/dream`

Result: 13 issue(s): 0 direct fix, 0 PR proposal, 13 human-needed.

### Human Needed

- `fix-git-sync-failure`: `unfrozen-workflow` (warn) - workflow 'code/with-self-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `implement-the-include-allowlist-that-url-skill-upd`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `parse-agents-rejects-cogalocaltoml`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `stop-creating-linked-worktrees-for-coga-retire`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `ticket-sync-fails-with-read-only-git-inside-agent`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v1/01-webhook-for-slack-is-public`: `stuck-in-progress` (warn) - in_progress but idle for 233.9h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `v1/14-interactive-coga-launch-on-native-windows`: `large-blackboard` (warn) - blackboard region is 49.3 KiB (warning threshold 32.0 KiB); it is included in launch prompts. Consider summarizing old notes.
  Remediation: Ask the owner to choose the `coga/blackboard` remedy. For done tickets, use Dream's Retro/retirement route instead of slimming; recurring writer state needs its owner's decision. For live tickets, promote a file-form task to directory form (a task that already has `<slug>/ticket.md` keeps its directory), move dated evidence into sibling attachments, move abandoned designs into the single `## Superseded designs` section (it does not count toward the size), move material several tickets cite into an unattached context, and leave the current handoff, worklist and verification on the blackboard with a pointer to each. Keep `## Dev` and `## Blockers` in place under the `coga/blackboard` contract; CLI readers do not follow attachment links for that state. Move, do not delete. Publish ticket and attachment edits through `coga/state-publication`; use direct owner editing or a `brief-for-human` draft with no branch or PR requirement.
- `v1/18-handle-gh-not-being-installed-by-default`: `stuck-in-progress` (warn) - in_progress but idle for 131.3h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `v1/20-ask-which-agents-to-enable-during-coga-init`: `large-blackboard` (warn) - blackboard region is 36.8 KiB (warning threshold 32.0 KiB); it is included in launch prompts. Consider summarizing old notes.
  Remediation: Ask the owner to choose the `coga/blackboard` remedy. For done tickets, use Dream's Retro/retirement route instead of slimming; recurring writer state needs its owner's decision. For live tickets, promote a file-form task to directory form (a task that already has `<slug>/ticket.md` keeps its directory), move dated evidence into sibling attachments, move abandoned designs into the single `## Superseded designs` section (it does not count toward the size), move material several tickets cite into an unattached context, and leave the current handoff, worklist and verification on the blackboard with a pointer to each. Keep `## Dev` and `## Blockers` in place under the `coga/blackboard` contract; CLI readers do not follow attachment links for that state. Move, do not delete. Publish ticket and attachment edits through `coga/state-publication`; use direct owner editing or a `brief-for-human` draft with no branch or PR requirement.
- `v1/42-idea-piece`: `unfrozen-workflow` (warn) - workflow 'draft-for-human' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v1/pr-are-only-when-ready-for-review`: `unfrozen-workflow` (warn) - workflow 'docs/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `validate-drift-stuck-in-progress-in-progress-ticke`: `stuck-in-progress` (warn) - in_progress but idle for 151.0h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `validate-drift-unfrozen-workflow-canceled-tickets`: `stuck-in-progress` (warn) - in_progress but idle for 150.9h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.

## Findings

Run `20261118T170921Z`, repo-identity: coga-source. Phase 2 knowledge-scan: 31/31 shards complete, 40 raw findings. Phase 3 contract-audit: 13/13 shards complete (ca-own ownership check inline: 0), 14 raw drift. Merged duplicates (same underlying issue, both shards kept below as one disposition unit):
- M1 bootstrap/import `_dispatch_branch_sync` = ks-30 + ca-08
- M2 bootstrap/import ignores `include` allowlist = ks-30 + ca-08
- M3 log-writers 32→33 sites = ks-15 + ca-02
- M4 Google skills (calendar-reminder/google-calendar/gmail) dead helper paths + rejected config tables + stopgap framing = ks-28 ×2, ks-29 ×2, ca-09 ×3
De-duplicated total: 47 (13 extract, 18 stale, 14 drift, 2 gap). No `owner: coga` findings (source repo).

- **Direct git subprocess callers must use git._git_env (optional-lock gotcha)** — shard: ks-15 · class: extract · target: v1/coga-bump-on-feature-branch-leaves-stale-index-loc · area: coga-dev/codebase/gotchas (or coga-dev/internals/state-publication) · source: done · owner: local
  The done ticket (PR #1194; branch gone locally and on origin) holds a contributor rule that today lives only in `src/coga/git.py`'s module docstring and the ticket: every Git subprocess Coga starts must run with `GIT_OPTIONAL_LOCK…
- **Record the declined Gemini agent integration and its verified CLI constraints** — shard: ks-22 · class: extract · target: marketing/fix-installer/add-gemini-as-an-agent-coga-can-drive · area: coga-dev/current-direction · source: canceled
  The owner canceled this ticket on 2026-11-06 with the reason "no need" (`coga/log.md`), after design and evaluation had finished. No topic under `docs/contexts/` or `src/coga/` mentions Gemini, so nothing records the decision or w…
- **`coga validate` never checks a bootstrap target's pinned `agent:`** — shard: ks-19 · class: extract · target: v1/20-ask-which-agents-to-enable-during-coga-init · area: coga-dev/internals/agent-config · source: done · owner: local
  The ticket's "Findings that cost real time" records, and current code confirms, that `coga validate`'s `unknown-agent` check (`validate._check_main_agent`, called from the per-task check over `list_tasks(cfg)` refs at `src/coga/va…
- **Record why the dollar-cost proxy was declined and what would reopen it** — shard: ks-26 · class: extract · target: define-the-api-equivalent-cost-proxy-and-price-tab · area: coga-dev/internals/usage-pricing · source: canceled
  The canceled ticket's verified record facts (mixed 5m/1h Claude cache-write TTLs, Codex null cache-creation meaning "no split" rather than "no charge", invisible context tiers, last-model attribution) already landed in `docs/conte…
- **Testing gotcha: patch the importing module, not the source module (init's `AGENT_CLIS` / `packaged_template_root`)** — shard: ks-19 · class: extract · target: v1/20-ask-which-agents-to-enable-during-coga-init · area: coga-dev/testing · source: done · owner: local
  The ticket records a gotcha that "will cost time otherwise", verified against current code: `src/coga/commands/init.py` does `from coga.dependencies import AGENT_CLIS` and `from coga.commands.update import packaged_template_root`,…
- **Record why requires-python has no upper bound** — shard: ks-21 · class: extract · target: v1/47-cap-requires-python-and-stop-init-leading-with-a-c · area: coga-dev/testing · source: done · owner: local
  Ticket 47 (status done, PR #1235; its `coga/v1-47-…` branch is absent locally and from `git ls-remote origin`, only a stale `remotes/origin/` tracking ref remains) recorded an owner-reviewed decision not to cap `requires-python` (…
- **Blocker ids collide for asks appended within one second** — shard: ks-08 · class: extract · target: keep-unfinished-dependency-blockers-open-in-megala · area: coga/blackboard · owner: local · source: done
  The ticket's blackboard records a verified gotcha: `blackboard._blocker_id` (src/coga/blackboard.py:469) formats only whole seconds (`%Y%m%dT%H%M%S`), so different blockers appended in the same second share an `id=`; targeted reso…
- **Cross-repo tickets: packaged branch-gated workflows cannot drive work in another repository** — shard: ks-28 · class: extract · target: v1/pr-are-only-when-ready-for-review · area: coga/checkouts · source: canceled · owner: local
  The canceled ticket's evaluator review discovered a reusable fact that no topic states: a ticket kept in one Coga workspace whose edits and PR land in a different repository misbehaves under the packaged code/docs workflows. `crea…
- **Uncommenting an init-disabled `[agents.*]` table: strip only init's `# `, not the packaged prose or `# analyze`/`# peer` examples** — shard: ks-19 · class: extract · target: v1/20-ask-which-agents-to-enable-during-coga-init · area: coga/configuration · source: done · owner: local
  The ticket's 2026-11-11 peer-review entry records an accepted limitation, verified against current code: `init._configure_agent_tables` prefixes `# ` only to the disabled table's live lines (header and keys) and leaves the package…
- **Record the recurring-reminder harness boundary the canceled engine ticket settled** — shard: ks-05 · class: extract · target: ship-a-shared-recurring-reminder-engine-battery · area: coga/notifications (or a new user topic for downstream reminder sweeps) · owner: local · source: canceled
  The ticket was canceled 2026-07-27 (log: "the engine's boundary reached too far into what individual scripts should own"; PR closed unmerged) and the smaller retry landed as `src/coga/reminders.py` (commit 894fea4b3, #853). The on…
- **Walking an unmerged branch and controlling agent detection in an install walk** — shard: ks-19 · class: extract · target: v1/20-ask-which-agents-to-enable-during-coga-init · area: coga/testing/clean-install · source: done · owner: local
  v1/20 ran its four-case init walk (none / only-claude / only-codex / both) on a macOS VM and a bare Windows 11 VM before merge, and recorded a reusable method that `coga/skills/coga/testing/clean-install/human-walk/SKILL.md` ("Fix…
- **Windows 11 client's Restricted execution policy breaks the bare uv installer, and the Server 2025 harness cannot see it** — shard: ks-20 · class: extract · target: v1/45-fix-the-readme-s-native-windows-install-steps · area: coga/testing/clean-install (windows-aws harness; human-walk) · source: done
  Ticket v1/45 is done. Its branch `coga/v1-45-fix-the-readme-s-native-windows-install-st-2006e1` is gone locally and from origin, and it records no worktree. It verified a platform gotcha that no testing knowledge states. Windows 1…
- **Windows native full-suite duration estimate understated** — shard: ks-08 · class: extract · target: keep-unfinished-dependency-blockers-open-in-megala · area: coga/testing/clean-install/windows-aws · owner: local · source: done
  The ticket (status done, `## Dev` branch `coga/keep-unfinished-dependency-blockers-open-in-mega-3a6dfd` not present locally or on origin) measured a native Windows full-suite run on the default t3.large host reaching only 58% afte…
- **Windows attended-launch harness gotchas missing from windows-aws skill** — shard: ks-11 · class: extract · target: v1/14-interactive-coga-launch-on-native-windows · area: coga/testing/clean-install/windows-aws · source: done+checkout
  The ticket is `status: done`, but its `## Dev` branch `coga/v1-14-interactive-coga-launch-on-native-windows-e8b518` still exists locally and on `origin`, so this is `done+checkout` retirement debt. Nearly all of its durable knowle…
- **Owner positioning wording limits live only in canceled v1/42-idea-piece** — shard: ks-30 · class: extract · target: v1/42-idea-piece · area: marketing/write-post (coga/skills/marketing/write-post/SKILL.md) · source: canceled
  `coga/tasks/v1/42-idea-piece.md` (status: canceled 2026-11-04, owner will write the piece after launch) holds the only copy of the `### Claim and wording limits` owner decisions (2026-10-13 and 2026-10-15) carried forward from the…
- **bootstrap/import cites removed `_dispatch_branch_sync` symbol** — shard: ks-30 · class: stale · target: src/coga/resources/templates/coga/bootstrap/skills/bootstrap/import/SKILL.md · area: bootstrap/import
  "Installing and pruning" says "`_dispatch_branch_sync` pushes when HEAD is the control branch, and from a feature branch it lands the same paths on the control branch anyway." No `_dispatch_branch_sync` exists anywhere in `src/cog…
- **bootstrap/import teaches hand-pruning and "locally-adapted is expected" though `include` allowlist exists** — shard: ks-30 · class: stale · target: src/coga/resources/templates/coga/bootstrap/skills/bootstrap/import/SKILL.md · area: bootstrap/import
  "Recording provenance" lists the `.coga-source.json` fields without `include`, and "Installing and pruning" says the selector cannot exclude siblings so you must "Delete the rest and hand-write what you dropped ... into `local_ada…
- **bootstrap/ticket calls `coga draft` "deprecated" though the command no longer exists** — shard: ks-30 · class: stale · target: src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md · area: bootstrap/ticket
  Step 1's note says "`coga create "<title>"` (the replacement for the deprecated `coga draft`) only writes the draft bytes". There is no `draft` command or alias: `coga --help` lists `create`, `ticket`, and no `draft`; `src/coga/cl…
- **code/implement promises retro/done-ticket will rescue adjacent-bug notes, but done tickets retire with no Retro** — shard: ks-28 · class: stale · target: src/coga/resources/templates/coga/bootstrap/skills/code/implement/SKILL.md · area: code/implement · owner: local
  Step 4 tells the implementer to leave a found adjacent bug only as a blackboard note because "`retro/done-ticket` owns carrying that finding into a durable context before deleting this ticket, so the blackboard is a handoff, not t…
- **git-refresh caller lists for `refresh` and `prepare_control_checkout` are incomplete** — shard: ks-16 · class: stale · target: docs/contexts/coga-dev/internals/git-refresh/SKILL.md · area: coga-dev/internals/git-refresh
  Two caller claims no longer match `src/coga/`. (1) "`prepare_control_checkout` ... Its only caller is the launch checkout boundary": `checkouts._prove_control` (src/coga/checkouts.py ~L459) also calls `git.prepare_control_checkout…
- **log-writers inventory misses megalaunch dependency-resolution append (32 vs 33 sites)** — shard: ks-15 · class: stale · target: docs/contexts/coga-dev/internals/state-publication/log-writers/SKILL.md · area: coga-dev/internals/state-publication · owner: local
  The topic claims "The startup-group implementation inventory has **32 direct call sites**" and tells writers to re-inventory all direct `append_log` calls under `src/`. `grep -rn "append_log(" src/` now finds 33: the table omits `…
- **publish leaf misstates which steps run under state_lock** — shard: ks-18 · class: stale · target: docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md · area: coga-dev/internals/state-publication · owner: local
  The `state_lock` section says "`publish` runs steps 2–5 under `git.state_lock`", implying step 1 (Candidates) is computed outside the lock. In `src/coga/git.py` `publish` takes `with state_lock(cfg):` before calling `_publish_lock…
- **Microkernel README row for 06 still describes the work as unstarted** — shard: ks-03 · class: stale · target: coga/tasks/v1/microkernel/README.md · area: coga-dev/microkernel
  The group README's table row for `06-read-report-commands-as-ticket-workflows.md` says "Rendering partly shared already. Move report policy only after a generic stateless path preserves read-only behavior". The ticket is `status: …
- **Microkernel open-placements table names superseded cleanup owners** — shard: ks-25 · class: stale · target: docs/contexts/coga-dev/microkernel/SKILL.md · area: coga-dev/microkernel
  The "Open command placements" table routes `slack` to `work-orchestration-commands-to-tickets`, `ticket` to `residual-command-surfaces`, and describes `skill *` as "excluded from the current migration push" owned by `residual-comm…
- **coga-dev/microkernel exceeds the topic size review threshold with no Size exception** — shard: ks-25 · class: stale · target: docs/contexts/coga-dev/microkernel/SKILL.md · area: coga-dev/microkernel
  `coga/knowledge` "Topic size review policy" says a topic over 200 lines, 10,000 bytes, or 2,500 tokens (ceil(chars/4)) is reviewed for a split, and any exception needs a closing `Size exception:` sentence in the topic itself. `doc…
- **coga-dev/testing calls the control_relay_started leak "open, no ticket", but an open ticket fixes it** — shard: ks-20 · class: stale · target: docs/contexts/coga-dev/testing/SKILL.md · area: coga-dev/testing
  The "Known suite failures" bullet says `control_relay_started` leaks between tests and labels it "(open, no ticket)". The leak is still real on current main: on 2026-11-18, running `tests/test_recurring.py::test_recurring_scan_rel…
- **calendar-reminder hardcodes a gcal.py path that no longer exists after the package-definition cutover** — shard: ks-29 · class: stale · target: src/coga/resources/templates/coga/bootstrap/skills/coga/calendar-reminder/SKILL.md · area: coga/calendar-reminder (google-calendar skill attachments) · owner: local
  Every call shape in the skill runs `python "$COGA_COGA_OS_ROOT/skills/coga/google-calendar/gcal.py" ...`. `task_env.py:68` sets `COGA_COGA_OS_ROOT` to `cfg.repo_root` (the workspace `coga/` dir), but bundled skills are no longer c…
- **calendar-reminder still frames itself as a stopgap until recurring ships, and ships one client's legacy event table** — shard: ks-29 · class: stale · target: src/coga/resources/templates/coga/bootstrap/skills/coga/calendar-reminder/SKILL.md · area: coga/calendar-reminder (recurring) · owner: local
  The description ("coga's native recurring-task scheduling hasn't shipped yet — the calendar event is the stopgap"), the intro, the event description template ("Temporary — delete this event once coga's recurring-task machinery lan…
- **terminal-owners says terminal transitions "make no network call"** — shard: ks-18 · class: stale · target: src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/terminal-owners/SKILL.md · area: coga/checkout-cleanup · owner: local
  "When it runs" states that `coga mark done`, `coga mark canceled` and a final-step `coga bump` "delete nothing and make no network call". The deletion half holds (`src/coga/mark.py` and `bump.py` import no `branchcleanup`/`branchs…
- **coga/first-task says the workflow freezes "when it activates", but its own example freezes at create** — shard: ks-30 · class: stale · target: src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md · area: coga/first-task
  "What you touched" says "**Workflow**: ordered steps, frozen into the ticket when it activates." Step 1 of the same walk creates the ticket with `coga create "..." --workflow code/with-review`, and `create.create_task` freezes on …
- **coga/gmail: helper invocation path `<coga>/skills/coga/gmail/gmail.py` does not exist after the package cutover** — shard: ks-28 · class: stale · target: src/coga/resources/templates/coga/bootstrap/skills/coga/gmail/SKILL.md · area: coga/gmail · owner: local
  Every command example is `python <coga>/skills/coga/gmail/gmail.py ...`, and setup says to `pip install -r requirements.txt` "from this skill's dir". The skill now ships only from the package (`src/coga/resources/templates/coga/bo…
- **coga/google-calendar: helper path under `$COGA_COGA_OS_ROOT/skills/` no longer exists, and it cites a removed `[secrets]` table** — shard: ks-28 · class: stale · target: src/coga/resources/templates/coga/bootstrap/skills/coga/google-calendar/SKILL.md · area: coga/google-calendar · owner: local
  The skill tells consumers to run `python <coga>/skills/coga/google-calendar/gcal.py ...` and to "Locate the helper via `COGA_COGA_OS_ROOT`". `task_env` sets `COGA_COGA_OS_ROOT` to the Coga workspace root (`cfg.repo_root`), but aft…
- **PR preparation leaf omits open-pr's compact-author refusal** — shard: ks-18 · class: stale · target: src/coga/resources/templates/coga/bootstrap/contexts/coga/pr-publication/preparation/SKILL.md · area: coga/pr-publication · owner: local
  `coga/pr-publication/preparation` owns the `## PR` record fields and enumerates the value constraints `coga open-pr` enforces (free-text values must be folded/quoted YAML, `depth` is exactly `merge|skim|deep`, `review.kind` values…
- **coga/secrets omits the scrubbed env for clone-scoped recurring scripts** — shard: ks-27 · class: stale · target: src/coga/resources/templates/coga/bootstrap/contexts/coga/secrets/SKILL.md · area: coga/secrets · owner: local
  The "A declaration plus an env scrub, not a sandbox" section enumerates what the 1Password-auth scrub covers ("launch ... The same scrub covers the `coga ticket` interviewer and the recurring autofix analysis call") and then says …
- **windows-aws skill shows the bare uv installer the walk no longer runs** — shard: ks-23 · class: stale · target: src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md · area: coga/testing/clean-install
  The Walk section's step 2 says the walk runs "uv's official installer (`irm https://astral.sh/uv/install.ps1 | iex`)". `scripts/clean-install/windows-walk.ps1` `Install-Uv` (line 35) actually runs it in a child process as `powersh…
- **human/run workflow says `bump` needs a launched in_progress ticket; a human can now bump an active owner step** — shard: ks-29 · class: stale · target: coga/workflows/human/run.md · area: workflows (human/run) / coga/lifecycle · owner: local
  The `execute` section ends: "Use `mark done` for this human-only path: `mark active` leaves the ticket `active`, whereas `bump` requires an `in_progress` ticket from a launch." Since d8051cf8d ("Let a human bump an active owner-he…
- **validate-drift Idempotency line misdescribes the `--fix` repair set** — shard: ca-08 · class: drift · target: src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/tasks/validate-drift/SKILL.md · area: bootstrap/dream · owner: local
  Line 33-34 says "`coga validate --fix` only creates missing standard files and leaves existing files unchanged". Code reality: `apply_safe_fixes` in `src/coga/validate.py:1884` creates no files; its only repair appends a missing b…
- **cleanup-orphan-markers skill claims slug-exact scan but code only sees top-level task directories** — shard: ks-03 · class: drift · target: src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/tasks/cleanup-orphan-markers/SKILL.md · area: bootstrap/dream/tasks/cleanup-orphan-markers
  The skill's Detection Gate and Inputs describe candidates as "task directories under `coga/tasks/`" matched by exact slug (`coga/tasks/<slug>/ticket.md`), and the open-PR gate uses `coga/tasks/<slug>/`. In `src/coga/dream_cleanup_…
- **bootstrap/import names nonexistent `_dispatch_branch_sync`** — shard: ca-08 · class: drift · target: src/coga/resources/templates/coga/bootstrap/skills/bootstrap/import/SKILL.md · area: bootstrap/import · owner: local
  Line 137 says "`_dispatch_branch_sync` pushes when HEAD is the control branch". No symbol by that name exists anywhere in `src/coga/` (grep finds only this SKILL.md). The post-command sweep is `_sweep_coga_state` in `src/coga/cli.…
- **bootstrap/import pruning guidance ignores the `include` allowlist** — shard: ca-08 · class: drift · target: src/coga/resources/templates/coga/bootstrap/skills/bootstrap/import/SKILL.md · area: bootstrap/import · owner: local
  Lines 115-132 and 143-150 say pruning an `install-url` skill is a hand deletion recorded only in `local_adaptation_notes`, that `locally-adapted (url)` is the expected status afterwards, and that `update` then needs `--force`. The…
- **bootstrap/import misdescribes `installed_ref`** — shard: ca-08 · class: drift · target: src/coga/resources/templates/coga/bootstrap/skills/bootstrap/import/SKILL.md · area: bootstrap/import · owner: local
  Line 74 describes `installed_ref` as "the ref/version installed". `install_url_skill` writes `installed_ref=skill_ref` (`src/coga/skill_manager.py:286`), which is the Coga skill ref taken from the upstream frontmatter name, such a…
- **bootstrap/import cites nonexistent `coga/skills/code/*` as locally authored trees** — shard: ca-08 · class: drift · target: src/coga/resources/templates/coga/bootstrap/skills/bootstrap/import/SKILL.md · area: bootstrap/import · owner: local
  Line 166 lists "`coga/skills/marketing/write-post/`, `coga/skills/code/*`" as the locally authored namespaced trees in this repo. `coga/skills/code/` does not exist. The `code/*` skills ship from the package at `src/coga/resources…
- **activity-capture names a removed `commands/usage.py`** — shard: ca-01 · class: drift · target: docs/contexts/coga-dev/internals/activity-capture/SKILL.md · area: coga-dev/internals
  docs/contexts/coga-dev/internals/activity-capture/SKILL.md:10-11 says "All parsing, bounding, and rollup logic lives in `src/coga/usage.py`; `launch.py` and `commands/usage.py` stay thin." `src/coga/commands/usage.py` no longer ex…
- **git-regressions cites coga-dev/current-direction for the no-compatibility-reader decision, which it does not record** — shard: ca-02 · class: drift · target: docs/contexts/coga-dev/internals/git-regressions/SKILL.md · area: coga-dev/internals · owner: local
  docs/contexts/coga-dev/internals/git-regressions/SKILL.md:163-164 says the stored-ticket "no-compatibility-reader decision is recorded in `coga-dev/current-direction`". docs/contexts/coga-dev/current-direction/SKILL.md has no ment…
- **log-writers inventory misses megalaunch's dependency-resolution append_log (33 sites, not 32)** — shard: ca-02 · class: drift · target: docs/contexts/coga-dev/internals/state-publication/log-writers/SKILL.md · area: coga-dev/internals · owner: local
  docs/contexts/coga-dev/internals/state-publication/log-writers/SKILL.md:14 claims "The startup-group implementation inventory has **32 direct call sites**" and the table (lines 18-31) is described as the complete `append_log` writ…
- **Branch-sweep template and workflow describe two deletion authorizations; the code has a third (closed-unmerged PR)** — shard: ks-02 · class: drift · target: src/coga/resources/templates/coga/recurring/branch-sweep/ticket.md · area: coga/checkout-cleanup/branch-sweep · owner: local
  Step 4 of the packaged `branch-sweep` template says the sweep "authorizes deletion two independent ways" (local tip reachable from control, or a merged PR with no open PR), and step 6 says it skips "anything unmerged with no merge…
- **script-tickets overstates which supervisor variables a ticket.py child "loses"** — shard: ca-05 · class: drift · target: src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md · area: coga/script-tickets
  `script-tickets/SKILL.md:54-58` says the script child's environment "loses `COGA_SUPERVISED`, `COGA_DONE_SENTINEL`, `COGA_EXPECTED_TASK`, `COGA_EXPECTED_STEP`, and `COGA_EXPECTED_AGENT`" unconditionally. Code reality (`src/coga/la…
- **Shipped phone-home template requires reading a local-only coga-dev topic** — shard: ca-11 · class: drift · target: src/coga/resources/templates/coga/recurring/phone-home/ticket.md · area: recurring/phone-home · owner: local
  `src/coga/resources/templates/coga/recurring/phone-home/ticket.md:117-119` defines movement counting "using the versioned/legacy decoding contract in [coga-dev/internals/spool-merge](…/docs/contexts/coga-dev/internals/spool-merge/…
- **Google helper invocation paths point at a live `coga/skills/coga/...` copy that no longer exists** — shard: ca-09 · class: drift · target: src/coga/resources/templates/coga/bootstrap/skills/coga/calendar-reminder/SKILL.md · area: skills/coga/google-capabilities · owner: local
  `coga/calendar-reminder/SKILL.md:29,141,174,196,213` invokes `python "$COGA_COGA_OS_ROOT/skills/coga/google-calendar/gcal.py"`; `coga/google-calendar/SKILL.md:71,90-91` says to locate the helper as `<coga>/skills/coga/google-calen…
- **calendar-reminder still says native recurring scheduling has not shipped and uses the flat `recurring/<name>.md` layout** — shard: ca-09 · class: drift · target: src/coga/resources/templates/coga/bootstrap/skills/coga/calendar-reminder/SKILL.md · area: skills/coga/google-capabilities · owner: local
  The skill's description (line 3: "coga's native recurring-task scheduling hasn't shipped yet") and body (lines 11-13, 68-69, 130, 145, 207, 293-302) frame the calendar event as a stopgap until recurring machinery "ships". Code rea…
- **Google capability skills configure `[calendar]`/`[gmail]` tables that Coga's config loader rejects** — shard: ca-09 · class: drift · target: src/coga/resources/templates/coga/bootstrap/skills/coga/google-calendar/SKILL.md · area: skills/coga/google-capabilities · owner: local
  `coga/google-calendar/SKILL.md:95-101,117` tells operators to put a `[calendar]` table (`service_account_file`) in `coga.local.toml`; `coga/calendar-reminder/SKILL.md:42` repeats it and `:52` says to resolve the calendar id from a…
- **recurring/verify derives script-vs-agent templates from live `coga/recurring/*/ticket.py`, missing every package-backed job** — shard: ca-09 · class: drift · target: src/coga/resources/templates/coga/bootstrap/skills/coga/recurring/verify/SKILL.md · area: skills/coga/recurring · owner: local
  `coga/recurring/verify/SKILL.md:248-254` says to "derive which templates can fire headless rather than trusting a list" with `for t in coga/recurring/[!_]*/; do [ -f "$t/ticket.py" ] && echo script || echo agent`, and the secret r…
- **No knowledge home for running Coga agent-behavior A/B trials** — shard: ks-13 · class: gap · target: docs/contexts/coga-dev/testing/SKILL.md · area: coga-dev/testing
  Two independent done tickets — `v1/microkernel/03-prompt-assembly/02-compare-current-and-candidate-prompt-assembly` and `v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality` — each rebuilt the same paired-t…
- **Third hardcoded agent list in `commands/uninstall.py` is outside v1/50's stated scope** — shard: ks-19 · class: gap · target: src/coga/commands/uninstall.py · area: coga/uninstall · owner: v1/50-make-adding-a-third-agent-one-registry-edit
  v1/20 merged the agent display names and binaries into `dependencies.AGENT_CLIS` and filed v1/50 (draft) to make adding an agent "one registry record", naming two remaining lists: `init._AGENT_SKILL_DIRS` and the packaged `[agents…


## Phase 4 — retro/done-ticket

Result: `pr-opened` — `complete — 5 PRs, 23 direct deletes, 35 tickets` (linked worktree on origin/main 7a40b520f; verified and torn down).
Eligible 35 done tickets; deferred as retirement debt: `make-retro-check-inbound-doc-links-before-deleting` (branch on origin), `v1/14-interactive-coga-launch-on-native-windows` (local branch), 41 canceled tickets.
- #1255 paired agent-behavior trial method (new `coga-dev/testing/agent-trials`) + compose limits — 03-prompt-assembly/01–04, recurring/autoclose-merged (covers gap ks-13)
- #1256 install Python pin / Restricted policy — v1/45, v1/47
- #1257 coga-dev hazards (git._git_env, blocker id collision, branch-sweep gh defaults, native suite duration) — v1/coga-bump…, keep-unfinished…, branch-sweep-never-releases…
- #1258 init agent-selection gotchas — v1/20
- #1259 microkernel report-command startup cost — v1/microkernel/06
Direct-deleted (23): correct-the-coga-workflows…, decide-the-dream-scans…, fix-the-checkouts…, remove-the-fixed-uninstall…, replace-activity-capture…, update-the-testing-topic…, hold-dirty-context-edits…, correct-state-publication…, v1/48, v1/microkernel/{01,02,03-launch-decomposition,avoid-duplicate…,normalize-signal…}, 03-prompt-assembly/record-{output-quality…,non-replacement…}, recurring/{address-pr-comments,blocker-reminders,phone-home,resolve-conflicts,skill-update,trim-log,usage-report}.
Retro follow-ups (route in Phase 6): 03-prompt-assembly/README.md + v1/microkernel/README.md stale rows; orphan `03-implement-the-proven-prompt-assembly-evidence/` dir; v1/45 deferred README should-fix items have no live owner; v1/microkernel/02 open questions (validate warn on `requires: branch` + `checkout: control|manual`; legacy-snapshot fallback retirement owner).
