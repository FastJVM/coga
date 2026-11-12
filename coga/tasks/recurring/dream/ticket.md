---
title: Dream
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: ef3ecf66-e00b-49e0-89cc-431528f93eb7
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

### Known corpus limitation

Both scans currently exclude package-backed `bootstrap/skills/**`.
The knowledge scan owns tickets and `coga/workflows/**`; the contract
audit adds recurring templates, `README.md`, `docs/*.md`,
`CLAUDE.md`/`AGENTS.md` and treats `coga/tasks/` as history. Correcting
this limitation requires a corpus decision for both scans.

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

Generated: 2026-11-12T05:15:12+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python -m coga.validate --json --fix`
Task: `recurring/dream`

Result: 12 issue(s): 0 direct fix, 0 PR proposal, 12 human-needed.

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
- `v1/01-webhook-for-slack-is-public`: `stuck-in-progress` (warn) - in_progress but idle for 78.0h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `v1/14-interactive-coga-launch-on-native-windows`: `large-blackboard` (warn) - blackboard region is 49.3 KiB (warning threshold 32.0 KiB); it is included in launch prompts. Consider summarizing old notes.
  Remediation: Ask the owner to choose the `coga/blackboard` remedy. For done tickets, use Dream's Retro/retirement route instead of slimming; recurring writer state needs its owner's decision. For live tickets, promote a file-form task to directory form (a task that already has `<slug>/ticket.md` keeps its directory), move dated evidence into sibling attachments, move abandoned designs into the single `## Superseded designs` section (it does not count toward the size), move material several tickets cite into an unattached context, and leave the current handoff, worklist and verification on the blackboard with a pointer to each. Keep `## Dev` and `## Blockers` in place under the `coga/blackboard` contract; CLI readers do not follow attachment links for that state. Move, do not delete. Publish ticket and attachment edits through `coga/state-publication`; use direct owner editing or a `brief-for-human` draft with no branch or PR requirement.
- `v1/18-handle-gh-not-being-installed-by-default`: `stuck-in-progress` (warn) - in_progress but idle for 173.4h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `v1/20-ask-which-agents-to-enable-during-coga-init`: `large-blackboard` (warn) - blackboard region is 36.8 KiB (warning threshold 32.0 KiB); it is included in launch prompts. Consider summarizing old notes.
  Remediation: Ask the owner to choose the `coga/blackboard` remedy. For done tickets, use Dream's Retro/retirement route instead of slimming; recurring writer state needs its owner's decision. For live tickets, promote a file-form task to directory form (a task that already has `<slug>/ticket.md` keeps its directory), move dated evidence into sibling attachments, move abandoned designs into the single `## Superseded designs` section (it does not count toward the size), move material several tickets cite into an unattached context, and leave the current handoff, worklist and verification on the blackboard with a pointer to each. Keep `## Dev` and `## Blockers` in place under the `coga/blackboard` contract; CLI readers do not follow attachment links for that state. Move, do not delete. Publish ticket and attachment edits through `coga/state-publication`; use direct owner editing or a `brief-for-human` draft with no branch or PR requirement.
- `v1/42-idea-piece`: `unfrozen-workflow` (warn) - workflow 'draft-for-human' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v1/package-definitions/02-repo-cutover-to-package-owned-definitions`: `large-blackboard` (warn) - blackboard region is 40.0 KiB (warning threshold 32.0 KiB); it is included in launch prompts. Consider summarizing old notes.
  Remediation: Ask the owner to choose the `coga/blackboard` remedy. For done tickets, use Dream's Retro/retirement route instead of slimming; recurring writer state needs its owner's decision. For live tickets, promote a file-form task to directory form (a task that already has `<slug>/ticket.md` keeps its directory), move dated evidence into sibling attachments, move abandoned designs into the single `## Superseded designs` section (it does not count toward the size), move material several tickets cite into an unattached context, and leave the current handoff, worklist and verification on the blackboard with a pointer to each. Keep `## Dev` and `## Blockers` in place under the `coga/blackboard` contract; CLI readers do not follow attachment links for that state. Move, do not delete. Publish ticket and attachment edits through `coga/state-publication`; use direct owner editing or a `brief-for-human` draft with no branch or PR requirement.
- `v1/pr-are-only-when-ready-for-review`: `unfrozen-workflow` (warn) - workflow 'docs/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.

## Run progress

- Period: 2026-W46. Run id `20261112T051938Z`. Repo identity: coga-source (no Rule A exclusion).
- Preflight: git-common-dir ok, remote ok (origin/main, defaults — `coga/coga.toml` has no `[git]`), gh ok.
- Phase 1: validate-drift — 12 human-needed, 0 direct-fix, 0 PR proposal (see section above).
- Human approved full-protocol scan cost (~37 shards).
- Phase 2 knowledge scan: 29 shards (ks-01..ks-29). Phase 3 contract audit: 8 shards (ca-01..ca-08) + ca-00 ownership check run inline (`_ownership_problems()` → 0).
- Corpus note: package `bootstrap/skills/**` excluded per this template's "Known corpus limitation" even though both scan skills say to include it in coga-source — recorded as a drift finding (self-contradiction).
- All `coga/recurring/*/ticket.md` carry `coga:recurring-state` → state carriers, not audited.
- Phase 4 eligibility (computed with `autoclose.parse_branch_names` + `retire_worklist` helpers + `git ls-remote`): 52 done tickets eligible; 1 done with live checkout (`v1/14-interactive-coga-launch-on-native-windows`, local branch `coga/v1-14-interactive-coga-launch-on-native-windows-e8b518`) → retirement debt; 41 canceled → retirement debt. No open PR (#1195–#1199) touches `coga/tasks/`.

## Findings

Phase 2 knowledge scan: 29/29 shards complete, 31 findings (15 extract, 16 stale, 0 gap). De-dup: ks-22 "Dream Known corpus limitation" also covers the orchestrator's own corpus-note observation (merged, one finding).

### Phase 2 — extract (grouped by area)

#### Record why Coga does not install agent CLIs (audience decision)

- shard: ks-15
- class: extract
- target: v1/19-install-link-for-claude-code-yields-the-desktop-ap
- area: coga-dev/current-direction
- source: done

The done ticket's `## Production notes` records an owner decision (Zach, 2026-11-04) not to act: Coga targets people who already use agentic coding tools, so users who need to be led through installing `claude` or `codex` are not an audience Coga serves, and Coga does not own getting an agent CLI onto a fresh machine (the `https://claude.ai/install.sh` vs no-`curl | sh` question was left unruled because it no longer blocks anything). `docs/contexts/coga-dev/current-direction/SKILL.md` ("Init offers selected missing supporting CLIs") states only that agent CLI installation offers and links were removed 2026-11-05, and `coga/init` says "Coga never installs one or says where to get one", but neither states the audience rationale or what would reopen it. Add one sentence to that current-direction bullet: agent CLI installation is out of scope because Coga's audience already runs an agent CLI (owner decision 2026-11-04); reopening needs an owner reversal on audience. The ticket has no `## Dev` section, so no live checkout.

#### Codex sessions that never submit a turn write no rollout, so "rollout not found" unknowns can be legitimate

- shard: ks-18
- class: extract
- target: v1/35-recheck-codex-usage-completeness-after-the-session
- area: coga-dev/internals/activity-capture
- source: done

The ticket closed as already-satisfied (no `## Dev` checkout recorded) with a verified behavior the capture topic does not state: Codex creates a thread/rollout (and a `~/.codex/history.jsonl` entry) only once a turn is submitted. A Codex launch that exits before that — an argument-parse failure (`exit_code: 2` in under 0.4s), a process that never initialised (no `logs_2.sqlite` rows), or, inferred from version boundaries, a human accepting Codex's startup update prompt and exiting 0 — leaves no rollout, so `usage_status: unknown` with reason `codex rollout not found for cwd` is the correct record, not a matcher miss. The ticket also records the diagnosis recipe used to tell the two apart without reading transcript content: parse only first-line `session_meta` of every rollout under the root, match meta ts/mtime against the window ±120s, attribute each hit to its owning launch by `session_id` in `coga/log.md`, and check `history.jsonl` for submitted prompts in the window. Add a short paragraph under "Provider matching" → Codex in `docs/contexts/coga-dev/internals/activity-capture/SKILL.md` stating that a never-submitted Codex session yields a legitimate unknown, and the metadata-only triage steps for distinguishing it from a filter rejection.

#### Record that Claude transcript lookup ignores CLAUDE_CONFIG_DIR

- shard: ks-21
- class: extract
- target: v1/honor-codex-home-when-locating-codex-rollouts
- area: coga-dev/internals/activity-capture
- source: done

The ticket's implement handoff recorded an unfiled follow-up: the Claude transcript root in `usage` is hard-coded to `~/.claude/projects/<cwd-name>/` (`src/coga/usage.py:811`, `Path.home() / ".claude" / "projects"`) and ignores Claude Code's `CLAUDE_CONFIG_DIR` override, the Claude analogue of the `CODEX_HOME` gap this ticket fixed. Neither `docs/contexts/coga-dev/internals/activity-capture/SKILL.md` (which now states the CODEX_HOME rule at lines 133-139) nor `coga/usage` states the Claude limitation, so a user with `CLAUDE_CONFIG_DIR` set would see every Claude session recorded `unknown` with no documented cause. Add one sentence to the Claude paragraph of activity-capture (and, if user-facing, beside the Codex sentence in `coga/usage`) naming the limitation as unsupported until fixed. Branch `coga/v1-honor-codex-home-when-locating-codex-rollouts-5b4cd1` is gone locally and on origin; no worktree recorded.

#### Windows batch transport cannot repair a reparsing npm cmd-shim (`&`/`^` in its directory)

- shard: ks-13
- class: extract
- target: v1/14-interactive-coga-launch-on-native-windows
- area: coga-dev/internals/agent-spawn
- source: done+checkout

The ticket's phase-2 box run (Implement — phase 2, session 1) measured a limit of the native Windows `.cmd`/`.bat` batch transport that `docs/contexts/coga-dev/internals/agent-spawn/SKILL.md` (the batch-transport paragraph after "A `.cmd`/`.bat` CLI always gets the pointer") does not state: the transport is lossless only up to the shim. npm's cmd-shim uses an unquoted `SET dp0=%~dp0`, which splits when the shim's own install directory contains `&` (or `^`), and a direct shim that embeds its literal directory in batch source fails the same way (`?\ was unexpected at this time`). Coga cannot repair a shim that re-parses its own path; the fake shims in `tests/test_repl_supervisor_nt.py` therefore use quoted `%~dp0` and the npm-shaped directory omits only `&`/`^`. Add one sentence to the batch-transport paragraph naming this as a known limit so a future failure with an `&` install path is not chased as a transport bug. Branch `coga/v1-14-interactive-coga-launch-on-native-windows-e8b518` still exists locally (remote head gone).

#### Pytest basetemp must sit outside the checkout

- shard: ks-07
- class: extract
- target: v1/26-make-the-readme-install-section-the-only-install-p
- area: coga-dev/testing
- source: done

The done v1/26 ticket's peer-review receipt records a verified test gotcha: a `--basetemp` inside the checkout lets the "missing repo" tests walk up and discover the checkout's real `coga.toml`, so they stop testing the no-repo case. The fix is a basetemp outside the checkout (the receipt used `--basetemp=/home/n/Code/.coga-pytest-...`). `docs/contexts/coga-dev/testing/SKILL.md` says only to pass `--basetemp` on a roomy volume (around line 66), and doesn't say it has to be outside the checkout. Add that requirement and the reason to the same bullet. Branch `coga/v1-26-retire-install-topic` is gone locally and on origin, and the `## Dev` section records no worktree.

#### Record the native-Windows limits of the package-publication control regressions

- shard: ks-08
- class: extract
- target: v1/package-definitions/02-repo-cutover-to-package-owned-definitions
- area: coga-dev/testing
- source: done

The done cutover ticket (branch `coga/v1-package-definitions-02-repo-cutover-to-packag-b5fd8f` gone locally and on origin; no worktree recorded) measured on native Windows (Server 2025, Python 3.11) that the three publication regressions in `tests/test_git.py` (`test_stage_b_first_deletion_and_carrier_publish_against_stage_a_control` and both `test_final_package_edits_never_escape_a_mutating_cli_sweep` cases) pass their publication assertions but fail inside `_check_package_control`: the nested clone plus `--basetemp={tmp_path/<label>-fixtures}` puts the control tree's own wheel-copy tests beyond Windows MAX_PATH, and the pinned historical Stage A control carries LF/CRLF-sensitive packaging/carrier fixtures that cannot be fixed by later Windows patches (the pinned checkout is deliberately not rewritten). Current `tests/test_git.py:4195` still nests the control clone and its basetemp under pytest's `tmp_path` with no Windows shortening (contrast `tests/test_usage.py::_repo_dir`, which uses a shallow `tempfile.mkdtemp` on Windows for exactly this reason). The ticket closed with that acceptance item unchecked, and `coga-dev/testing`'s "Package-owned definitions" paragraph says nothing about it. Add a short known-limitation note there (or a "Known open" bullet in `coga-dev/codebase/gotchas`): nested control-tree checks need a shallow temp root on native Windows, and the Stage A transition proof is Linux-receipted only, so a Windows full-suite receipt must account for these three cases explicitly.

#### Windows autouse conftest fixture routes agent fakes into the Windows spawn path

- shard: ks-13
- class: extract
- target: v1/14-interactive-coga-launch-on-native-windows
- area: coga-dev/testing
- source: done+checkout

The ticket's native suite runs found ~95+31 orchestration tests that faked `shutil.which`, `subprocess.run`, or `launch.run_with_done_marker` silently resolved and ran the real installed `claude.exe` on Windows, because the Windows planner resolves against the child PATH/PATHEXT and spawns through `ProcessTree`. The fix is the autouse fixture `tests/conftest.py::_windows_agent_spawn_follows_test_fakes` (keeps the bare CLI name while one of those seams is faked, routes the no-console ungated spawn through a faked `subprocess.run`, and exempts `test_repl_supervisor_nt.py`, which owns the real contract). `docs/contexts/coga-dev/testing/SKILL.md`'s Windows test-writing bullets (around "Native Windows fixtures use UTF-8 and LF explicitly" / "All Windows exclusions use `conftest.windows_skip`") do not mention it. Add a bullet: a test that models an agent must fake one of those three seams (or the real CLI runs natively); a new fake seam needs the fixture extended. Branch `coga/v1-14-interactive-coga-launch-on-native-windows-e8b518` still exists locally.

#### Cross-repo tickets break branch/PR gates — host the ticket in the repo that receives the edits

- shard: ks-22
- class: extract
- target: pr-are-only-when-ready-for-review
- area: coga/checkouts
- source: canceled

The canceled ticket's evaluator review recorded a verified gotcha no topic states: a ticket whose edits and PR live in another repository cannot run a branch-gated workflow (e.g. `docs/with-review`) from the Coga checkout. `coga launch` reserves the branch in the checkout that hosts the ticket and writes `branch:` into `## Dev` itself (`checkouts.insert_branch_line`, src/coga/checkouts.py:646), so a hand-recorded foreign branch collides; later steps re-check out the recorded branch in the hosting repo (fails, or `git diff main...HEAD` diffs the wrong repo); `open-pr` targets the hosting repo; autoclose judges branch disposal in the hosting repo. Durable rule: file the ticket in the repo whose checkout receives the edits, or use a manual/direct flow with no `requires:` gates. Add a short bullet to `src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md` (or `coga/tickets` per `coga/knowledge`). The ticket's own disposition (duplicate of a magicator ticket) is not durable.

#### Writer quiescence evidence: sandboxed process listing is not host-wide

- shard: ks-02
- class: extract
- target: commit-journal/activate-trim-log-in-this-repo-after-retention-mer
- area: coga/edge-code
- source: done

The done trim-log activation ticket (PR #1191 merged; branch `coga/commit-journal-activate-trim-log-in-this-repo-af-fb9f3f` gone locally and on origin, no worktree recorded) verified a limit that the packaged upgrade procedure does not state. Its design-phase writer inventory found that `/proc`/`ps` inspection from inside the agent's sandbox exposed only the sandbox's process namespace, user crontab was unreadable, and so no absence claim could cover cron, other users, remote hosts, agent-app schedulers or other clones; the owner had to name the participating writer (`~/.local/bin/coga`) and the excluded clones explicitly. Step 2 ("Quiesce affected launches and sweeps") of `src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/edge-code-upgrades.md` suggests `ps -eo pid,ppid,args` as the evidence source without that caveat. Add one sentence there: a process listing taken from a sandboxed agent session is not host-wide evidence; when the session cannot see the host's processes and schedulers, the owner records the participating/excluded writer inventory and stop authority, and an observed editable install version is not upgrade evidence (record the reviewed wheel's revision and SHA-256, as step 4 already requires).

#### Host .gitignore managed block is written only by fresh init (Gemini design evaluation)

- shard: ks-04
- class: extract
- target: marketing/fix-installer/add-gemini-as-an-agent-coga-can-drive
- area: coga/init
- source: canceled

The canceled Gemini-agent ticket (canceled 2026-11-06, "no need") recorded a verified Coga behavior that no topic states: `commands/update.py::ensure_host_gitignore` is called only from `commands/init.py::_do_init` (fresh init). Clone setup (`_setup_initialized_clone`), launch's `_refresh_agent_skills_for_launch`, and wheel upgrades never refresh the host `.gitignore` coga-managed block, so any change to `_HOST_GITIGNORE_BODY` (e.g. a new agent skill-link namespace) never reaches existing repos or their clones, and newly generated links would show as untracked (the evaluator reproduced 29 untracked links with `git check-ignore` exit 1). `coga/init` step 6 says init "adds a coga-managed block to the host `.gitignore`" but not that nothing else maintains it; add one sentence there (and the coga-dev note that a body change needs an explicit migration path). Secondary reusable fact worth a line in the owning agent-config/launch topic if desired: Gemini CLI 0.66.0 scans only `.gemini/skills/` root and immediate children at `process.cwd()` (no ancestor walk), so Coga's single nested `skills/coga` view link is not discoverable by it; the integration was declined as "no need", reopening only on a renewed owner request.

#### PR preparation: write prose values as YAML block scalars

- shard: ks-06
- class: extract
- target: v1/13-repair-ci-and-resume-with-release-focused-triggers
- area: coga/pr-publication
- source: done
- owner: local

Ticket v1/13 (status done; its `## Dev` branch `coga/v1-13-repair-ci-and-resume-with-release-focused--a448a8` is gone locally and on origin) recorded three consecutive `coga open-pr` refusals on 2026-11-06 from its `## PR` mapping: a plain-scalar `detail:` containing `: ` ("9 warnings (all unrelated tickets: unfrozen-workflow, ...)") failed YAML parsing ("mapping values are not allowed here"), then `review must be a mapping`, then `depth must be merge, skim, or deep`. `coga/pr-publication/preparation` (`src/coga/resources/templates/coga/bootstrap/contexts/coga/pr-publication/preparation/SKILL.md`) documents the allowed values and says malformed YAML refuses with a repair message, but its example uses only plain scalars and gives no authoring guard. Add one sentence after the example: write any free-text value (`rationale`, `implementation`, `deviations`, `limitations`, `author_evidence`, each `detail`) as a folded block scalar (`>-`) or quoted string, because a plain scalar containing `: ` or a leading `[`/`{` is invalid YAML and `coga open-pr` refuses; `review` is always a nested mapping, never a string. Ticket v1/23's `## PR` shows the working `>-` form.

#### How to attribute a `[git] sync failed` line to the session sandbox that caused it

- shard: ks-10
- class: extract
- target: v1/06-fix-coga-git-sync-failures-that-leave-main-diverge
- area: coga/sandboxes
- source: done

v1/06 (status done; recorded branch `coga/v1-06-fix-coga-git-sync-failures-that-leave-main-1212e6` is gone locally and on origin, no `worktree:`) landed its decisions in `coga-dev/internals/state-publication` and `coga/sandboxes`, but the reusable *diagnostic method* from its "Findings" stayed only on the ticket. `coga/sandboxes` ("Codex sandbox grant") now says to diagnose from the enclosing session's sandbox but not how. Add to the package topic `src/coga/resources/templates/coga/bootstrap/contexts/coga/sandboxes/SKILL.md`: (1) match each failure line to its enclosing session in `coga/log.md` — the preceding `launched (… agent=X)` line and that session's usage record `"cli":"X"`; the actor label (`[agent:claude]`, `[human:…]`) is not evidence of which harness ran the command when Codex's daemon dropped `COGA_*`; (2) read the effective Codex policy from the session file, `~/.codex/sessions/<date>/*.jsonl` → `turn_context.sandbox_policy` (`type`, `network_access`, `writable_roots`), which reflects every layer including `/etc/codex/requirements.toml`; (3) the first failing operation tells the cause: `_publish_locked` builds on the remote-tracking ref without fetching, so read-only `.git` fails at `git hash-object` before any network call, while writable `.git` with network off fails at push/fetch (`Could not resolve host`). Keep it to a short bullet list under the existing log-symptom bullet.

#### macOS baseline tool facts measured while scoping the "what macOS ships" ticket

- shard: ks-14
- class: extract
- target: v1/16-find-out-what-macos-actually-ships
- area: coga/testing (macOS test machines: `coga/skills/coga/testing/fresh-vm`)
- source: done

The ticket was closed `done` on activation (log 2026-11-04 09:00) without its deliverable — `macos-walk-findings.md` in ticket 29 has no "Tool availability by machine state" section — but its blackboard evaluator review records reusable measured facts that no context or skill holds (grep for `3.9.6`, `EXTERNALLY-MANAGED`, `pip3` stub finds nothing in `docs/contexts`, `coga/skills`, the package contexts, or README): (1) on a CLT-installed Mac (macOS 26.4.1 arm64) `/usr/bin/python3 -V` is Python 3.9.6, `/usr/bin/pip3` is the same 118928-byte xcode-select stub as `/usr/bin/python3`, and the CLT 3.9 stdlib carries no `EXTERNALLY-MANAGED` marker; (2) on a developer workstation `python3`/`pip3`/`git` commonly resolve to Anaconda/Homebrew rather than Apple's copies, so any macOS tool observation must record the absolute resolved path and provider and probe `/usr/bin/python3 -m pip` explicitly; (3) the repo holds three independent bare-macOS VM baselines (ticket 29's walk guest, `competition-testing/test-compound-engineering`, `competition-testing/test-kiro`) plus one fresh EC2 Mac host, all without CLT, where `git`/`python3` are stubs that trigger the CLT prompt; (4) whether pip on the CLT 3.9 can bootstrap uv cannot be settled read-only and remains open; no source observes a Migration Assistant machine. Add these, dated and sourced, to the macOS guidance in `coga/skills/coga/testing/fresh-vm/SKILL.md` (or the coga-dev testing topic's clean-install area), marking (4) as an open question rather than a fact. No `## Dev` section is recorded, so no checkout is live.

#### Kiro trial lessons not yet in hands-on-trial (version pinning, cost burn, verify before calling fabrication)

- shard: ks-03
- class: extract
- target: competition-testing/test-kiro
- area: competition-testing/hands-on-trial
- source: done

`status: done`, no `## Dev` section (no branch/worktree). The blackboard holds three reusable trial-method facts that `coga/skills/competition-testing/hands-on-trial/SKILL.md` does not state: (1) record the tool's version at the start of every lap, because auto-update can turn lap 2 into a different product than lap 1 (Kiro CLI shipped V2 by default on fresh install while specs only exist in V3); (2) when the tool meters usage, record the balance before lap 1 and the burn per lap — Kiro's 34 of 50 free credits for one lap was the only cost comparison across the four trials, and it showed the free tier covers one lap, not three; (3) before logging that a tool fabricated a result (e.g. "tests pass" on a VM without the runtime), check the project directory for the artifacts — Kiro carries its own bundled Node runtime, and the session's first "fabricated" conclusion had to be retracted. Also worth one line: the trialled surface (CLI vs IDE) should match the sibling trials' surface so the experience comparison holds. Add these under `## Setup`/`## Laps` of hands-on-trial; the competitor findings themselves stay out of the repo.

#### Preserve the owner's public-claim wording limits from the canceled idea-piece brief

- shard: ks-19
- class: extract
- target: v1/42-idea-piece
- area: skills/marketing/write-post
- source: canceled

The canceled brief's "Claim and wording limits" section is the last surviving copy of owner positioning decisions (2026-10-13 and 2026-10-15) carried over from a retired positioning context: do not position Coga as an audit/governance/compliance tool; avoid novelty/priority words ("first", "only", "new", "unique") and the slogans "knowledge compounds", "learn once", "multiplayer", "company brain", "human at the center", "human-centered", "human-in-the-loop", "progressive disclosure"; corrections persist through reviewed file edits, not automatic learning; human review is chosen per PR, not forced per ticket; code is "cheap enough to throw away", not free; keep setup/self-support/execution limits visible and promise no managed autonomy; competitor claims need dated verified support. `coga/skills/marketing/write-post/SKILL.md` Step 6 only says "Apply the selected brief's source limits" and names private quotations, invented results and productivity multipliers; a grep of contexts, skills and package templates finds none of the wording bans (e.g. "company brain", "human-in-the-loop", "governance") anywhere else. Retiring the ticket would drop these decisions, so Retro should land them in the write-post skill's claim-check step (or the topic that owns public positioning, per `coga/knowledge`).

### Phase 2 — stale

#### current-direction names a nonexistent `code/agent-merge` workflow

- shard: ks-07
- class: stale
- target: docs/contexts/coga-dev/current-direction/SKILL.md
- area: coga-dev/current-direction

The "Thin tickets are designed before they are built" entry (line ~94) says to use "`code/agent-merge` when the owner has opted out of the PR gate and audits after the merge", and that "All three have the other agent review the code". No such workflow exists. `src/coga/resources/templates/coga/bootstrap/workflows/code/` contains only `design-then-implement.md`, `with-review.md` and `with-self-review.md`, and `coga/workflows/` has no `code/` directory. Grepping `src/`, `coga/coga.toml` and `docs/contexts` for `agent-merge` finds only this line. Either remove the `code/agent-merge` clause and say "both" instead of "all three", or restore the workflow if it was dropped by mistake. The linked `coga/workflows` topic owns the contract.

#### state-publication "no deferred-publication state" contradicts the pending-publication record

- shard: ks-10
- class: stale
- target: docs/contexts/coga-dev/internals/state-publication/SKILL.md
- area: coga-dev/internals/state-publication

The "Scratch files and sandboxed publication" section (added by `3ee1653b2`, v1/06) says a sandboxed publication failure keeps the write dirty and "There is deliberately no deferred-publication state." But `src/coga/git.py` has kept one since `22a1a4985` (2026-11-05): `_PENDING_FILE = .coga/pending-publication.json`, a "per-checkout record of prepared ticket expectations whose publication has not landed", written by `publish(..., remember=True)` (used by `sync_task_state` when given a fresh `prepared` ticket) on a retryable failure (`state: pending`) or refusal (`state: rejected`), and reused by the supervisor retry and the sweep (`_pending_expectations`). `coga-dev/internals/git-regressions` already documents it. Narrow the sentence to what v1/06 actually decided (no supervisor-side deferred retry queue or deferred-publication mechanism beyond dirty files and the remembered prepared-ticket expectations) and link git-regressions' remembered-retries paragraph, so a sandboxed lifecycle failure is described as leaving both the dirty ticket and its pending expectation.

#### publish leaf omits `remember` / `prepared` from the documented signatures

- shard: ks-10
- class: stale
- target: docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md
- area: coga-dev/internals/state-publication

"`publish` and its wrappers" spells out the full signatures `git.publish(cfg, paths, message, *, expect=None, guard=None, fast_forward=True, require_paths=(), log_mutation=None)` and `sync_task_state(cfg, task_path, *, message, expect=None, strict=False, command=None)`. Current `src/coga/git.py` has `publish(..., log_mutation=None, remember: bool = False)` (line ~513) and `sync_task_state(..., command=None, prepared: PreparedTicket | None = None)` (line ~241, passing `remember=prepared is not None and prepared.fresh`), both added in `22a1a4985`. The leaf, which claims to own the primitive step by step, never mentions remembered prepared expectations or `.coga/pending-publication.json`. Add both parameters to the signatures and one sentence in step 1/step 3 that a prepared lifecycle publish records its expectation for retry/sweep reuse, linking `coga-dev/internals/git-regressions` (which owns the detail) rather than restating it.

#### write-post points at a canceled ticket and a renumbered one

- shard: ks-07
- class: stale
- target: coga/skills/marketing/write-post/SKILL.md
- area: marketing/write-post

The intro says "For the V1 idea piece those choices live in `v1/42-idea-piece`; publication sequencing lives in `v1/44-build-the-launch-plan`", and the Entry condition section says "The V1 idea-piece ticket owns its editorial decisions directly". Both references are out of date. `coga/tasks/v1/42-idea-piece.md` is now `status: canceled`. No `v1/44-build-the-launch-plan` exists: the launch plan was parked at `coga/tasks/_v2/marketing/build-the-launch-plan.md` on 2026-11-04 (see `v1/43-publish-coga-1-0-as-the-final-v1-step.md` lines 34 and 118, and `v1/README.md` line 90). The `v1/44-` slot now belongs to `v1/44-verify-the-macos-full-suite-procedure-on-the-ec`. Remove the V1-specific ticket pointers and keep the generic rule that the selected post's ticket owns the brief and its named launch ticket owns publication. Alternatively, name the parked `_v2/marketing/build-the-launch-plan` as not live.

#### coga/workflows claims `coga init` seeds workflows into the repo

- shard: ks-06
- class: stale
- target: src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md
- area: coga/workflows
- owner: local

The opening paragraph says "`coga init` seeds some workflows into the repo, including `direct/body`, which runs the ticket body's ordered phases." Current init copies only reviewed scaffolds: `src/coga/commands/update.py` `FRESH_SCAFFOLDS` (used by `copy_fresh_templates`, called from `src/coga/commands/init.py`) lists `workflows/_template.md` as the only workflows entry, and its comment states reusable definitions including workflows "are never on it: they resolve from the installed package". The package scaffold dir `src/coga/resources/templates/coga/workflows/` holds only `_template.md`; `direct/body` ships at `bootstrap/workflows/direct/body.md` and resolves from the package. Replace the sentence with: shipped workflows (including `direct/body`, which runs the ticket body's ordered phases) resolve from the package's `bootstrap/workflows/`; `coga init` copies only the ignored `workflows/_template.md` authoring starter, and a local file of the same ref is a deliberate override.

#### blackboard-io's "Writer races" still says lifecycle writes can overwrite a concurrent blackboard edit

- shard: ks-08
- class: stale
- target: docs/contexts/coga-dev/internals/blackboard-io/SKILL.md
- area: coga-dev/internals

The last paragraph of "Writer races" says "`git.write_ticket` serializes but does not reread, and `coga mark active` loads the `Ticket` before the lock, so a blackboard update landing in between can be overwritten by the old body." Current code closes that race for prepared lifecycle writes: `git.write_ticket(cfg, ticket, path, *, prepared=...)` (`src/coga/git.py:208-235`) re-reads the file under `state_lock` and raises `TicketChangedError` ("changed after this command read it; nothing was written") when the bytes differ from `prepared.local`, and `coga mark active` (`src/coga/commands/mark.py:70-87`) obtains `prepared` via `_load` → `commands/common.prepare_lifecycle_ticket` and passes it through, bailing on `TicketChangedError`. The same `prepared=` path is used by `bump`, `block`, `unblock` and `owner` (`prepare_lifecycle_ticket` docstring). Rewrite the paragraph: lifecycle commands write through prepared ticket transactions that refuse rather than overwrite an intervening edit (link `coga/state-publication` "Prepared ticket transactions", which owns the contract); only a `write_ticket` call without `prepared` keeps the serialize-without-reread behavior, and name any remaining unprepared callers if they exist.

#### agent-config describes a nonexistent `_configure_agent_tables` init path

- shard: ks-16
- class: stale
- target: docs/contexts/coga-dev/internals/agent-config/SKILL.md
- area: coga-dev/internals/agent-config
- owner: v1/20-ask-which-agents-to-enable-during-coga-init

The "The default agent" section says interactive `coga init` "writes no `default_agent` key at all: it comments out the `[agents.*]` table of every supported agent whose CLI it did not find (`commands/init.py` `_configure_agent_tables`), which leaves declaration order to name the default". Current code contradicts this: `_configure_agent_tables` exists nowhere in `src/` or `tests/` (grep), and `src/coga/commands/init.py` instead runs `_offer_agent_cli` (asks when exactly one agent CLI resolves and it is not the template default) followed by `_write_default_agent`, which writes a top-level `default_agent = "<type>"` into the new `coga.toml` and repoints delivered tickets via `_stamp_agent_into_delivered_tickets` (lines ~590-700, 1350-1411). The package `coga/init` topic correctly describes the shipped behavior, so the dev topic now contradicts both code and its user-facing sibling. The paragraph appears to describe the in-flight redesign of open ticket `v1/20-ask-which-agents-to-enable-during-coga-init` (status in_progress, step review) landed ahead of its code; restore the paragraph to describe `_offer_agent_cli`/`_write_default_agent` until that ticket's implementation merges, and have that ticket's PR update it in the same change.

#### activity-capture calls the log publish path "union-safe" though log.md is no longer a union path

- shard: ks-18
- class: stale
- target: docs/contexts/coga-dev/internals/activity-capture/SKILL.md
- area: coga-dev/internals (usage capture / state publication)

The "Capture point and gates" bullet says teardown publishes the log "through `git.sync_log` (its union-safe path)". Current reality: the shipped `src/coga/resources/templates/coga/.gitattributes` sets `/log.md -merge` (only `**/retires.md` stays `merge=union`), `git.sync_log` (src/coga/git.py:290) is a plain `publish(cfg, [path], ..., require_paths=[path])`, and the log lands through the event-aware `log_publication.reconcile` path that `coga-dev/internals/spool-merge` ("The audit log is no longer a union path"; "This generic union contract does not apply to logs") owns. Replace "its union-safe path" with a reference to the event-aware log publication in spool-merge ("How `publish` lands the audit log").

#### checkouts says committed `coga/tasks/` attachments stay in a branch diff, but publication adopts them to control

- shard: ks-14
- class: stale
- target: src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md
- area: coga/checkouts

The `## Stranded ticket writes` section ends "`ticket.py` and attachments under `coga/tasks/` can be implementation work and stay in the diff." Current code does not keep them on the branch: on a non-control checkout `_publish_locked` in `src/coga/git.py` sets `adopt_only = _routine_state_areas(cfg, root)` (the whole configured task directory plus the log), and `_candidates` adopts every committed branch path in that area whose control blob the checkout derived from (an edited existing attachment, or a new file absent at the merge base), so the next sweeping command (e.g. the `coga bump` ending `implement`) publishes it to control. `coga/state-publication`'s **Committed-state boundary** already says exactly this ("clean committed files stay with the branch except for the configured task directory and log"). Consequences the sentence hides: `github_preflight.check_branch_contains_control` then sees the path changed on both control and the branch and refuses with "Overlapping paths", and a branch whose only change is task-dir state is refused by `coga open-pr` as Coga-state-only (`is_coga_state_path`). Reword the sentence to say such files are not stranded-write violations but are published to control as routine state at the next sweep, never reach the PR diff, and that a ticket whose sole deliverable lives under `coga/tasks/` therefore cannot complete a branch/PR workflow — put a reviewable deliverable outside the Coga roots or use a no-PR workflow such as `draft-for-human`. (Surfaced by the evaluator review on done ticket `v1/16-find-out-what-macos-actually-ships`, `##### Workflow fit`; code re-verified at `src/coga/git.py` lines ~616 and 885-920 and `src/coga/github_preflight.py` lines 181-190, 316-334.)

#### Notification internals caller inventory omits the repo-local usage-report post

- shard: ks-17
- class: stale
- target: docs/contexts/coga-dev/internals/notifications/SKILL.md
- area: coga-dev/internals/notifications

The "Who calls `post` or `notify`" section's Live list enumerates every `notification.post` caller (it already includes the edge `coga_edge/phone_home.py` `_receipt`), but omits `coga/recurring/usage-report/ticket.py`, which imports `coga.notification.post` and calls `post(cfg, text, owner=..., important=True, fatal=False)` (line 35). It is also the only current `important=True` live post outside the script-failure path, which the topic mentions only in prose under the accounting rule. Add the usage-report `ticket.py` to the Live list (noting `important=True, fatal=False`) so a grep-driven producer edit does not miss it. All other named symbols, preflight callers (bump.py, mark.py done/canceled, launch.py `_run_initial_script`, launch_script.py `run_script_phase`, autoclose.py `_preflight_recipe_notifications`), `OUTCOME_EVENT_KINDS`, the 5-second timeout and `SLACK_TRANSPORT_ERRORS = (OSError, ValueError)` were verified current.

#### branch-sweep/sweep workflow still describes a period task and period blackboard

- shard: ks-15
- class: stale
- target: src/coga/resources/templates/coga/bootstrap/workflows/branch-sweep/sweep.md
- area: coga/recurring (branch-sweep)

The workflow body says "`coga launch` runs the period task's reserved `ticket.py`" and "The run's report lands on this period task's blackboard." Current reality: `src/coga/resources/templates/coga/recurring/branch-sweep/ticket.md` is `scope: clone` ("no shared period task ... The reserved `ticket.py` is the whole run"; step 8: "A clone-scoped run has no period blackboard, so the report is kept in the clone's `.coga/recurring-clone/branch-sweep.log` and in the sweep's run record"), its `ticket.py` runs `run_recipe(load_config(), "branch-sweep", [])` and bumps only when a legacy `COGA_TASK_SLUG` exists, and the template's frontmatter no longer names this workflow at all (no `workflow:` key; the only remaining references are the packaging lists `tests/test_packaging.py:117` and `tests/required_package_resources.txt:108`). Rewrite the `## sweep` paragraph to say the clone runner runs the template's `ticket.py` through the `branch-sweep` recipe with no period task, the report goes to `.coga/recurring-clone/branch-sweep.log` and the run record (a period blackboard only for a pre-clone-scope shared run), and add the `retires.md` owner-entry disposal step; or, if the workflow is retained only for pre-clone-scope compatibility, say so and link `coga/recurring/scheduling` for scope rather than restating the sweep (the `coga/branch-sweep/sweep` skill and `coga/checkout-cleanup/branch-sweep` own those rules).

#### coga-dev/internals/state-publication says cancellation's done sentinel precedes the child CLI sweep; `deferred_done_marker` now holds it until after

- shard: ks-28
- class: stale
- target: docs/contexts/coga-dev/internals/state-publication/SKILL.md
- area: coga-dev/internals/state-publication

The "Guided-authoring finalization" cancellation paragraph (~line 164) states that `commands.mark.canceled` "publishes the transition, then emits the done sentinel before the child CLI's exit sweep. The PTY supervisor can interrupt that sweep", and the following paragraph frames the regression fixtures around "interrupting only the child sweep". That was true when `publish-sibling-ticket-handoffs-during-targeted-au` (done, PR #1138) was written, but current code inverts it: `src/coga/cli.py:616-620` wraps dispatch and the end-of-command sweep in `repl_supervisor.deferred_done_marker()`, and `emit_done_marker` inside it only appends to a deferred list (`src/coga/repl_supervisor.py:903-913,941-965`), writing the sentinel after `_sweep_coga_state` and `_warn_unpublished_log_lines` return, while `<sentinel>.pending-<pid>` keeps the terminal-ticket backstop from tearing the session down mid-publication. The sibling dev topic `coga-dev/internals/agent-spawn` "The supervisor" already describes the deferred ordering, so the two dev topics now contradict each other. Rewrite the state-publication paragraph to say the child CLI's sweep completes before the done sentinel is written (so a supervisor `done` teardown no longer interrupts it under `cli.main`), keep the still-true points (the outer finalizer and outer sweep, a finished child sweep can publish an invalid sibling before finalization rejects it, no rollback), and re-check whether `tests/fixtures/authoring_cancellation.py`'s "interrupted child sweep" cases still describe a reachable path or are now a legacy-shape guard.

#### gotchas still lists the fixed Windows uninstall-hint bug as "Known open"

- shard: ks-27
- class: stale
- target: docs/contexts/coga-dev/codebase/gotchas/SKILL.md
- area: coga-dev/codebase

The "Known open: uninstall recovery hints use POSIX syntax on Windows" bullet says `commands/uninstall.py::_uninstall_via_tool` displays env overrides as `VAR=value` (`shlex.quote`) prefixes that cmd/PowerShell cannot paste, and that the fix is owned by `v1/15-uninstall-recovery-hints-use-posix-env-syntax-on-w`. That ticket is now `status: done` and the fix landed (commit `bd4b557b4` "Render uv uninstall recovery hints in PowerShell on Windows"): `src/coga/commands/uninstall.py` now has `_format_tool_command(..., windows=...)` which renders `$env:K='<literal>'; cmd` via `_powershell_literal()` on native Windows (`_native_windows()`), keeping `shlex.quote` only for POSIX. Delete the bullet (the `coga/uninstall` topic already documents both hint syntaxes per the ticket's handoff).

#### docs/with-review still mandates live↔packaged twin edits after the package-definition cutover

- shard: ks-29
- class: stale
- target: src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md
- area: workflows/docs

The workflow's frontmatter description ("peer-reviewed for prose, accuracy, and repo↔packaged sync"), implement step 4 ("Keep shipped copies in sync … has both a live copy under `coga/` and a packaged copy under `src/coga/resources/templates/coga/`, edit **both** in the same commit"), and the peer-review "Cross-copy sync" bullet ("confirm both were updated … This is the most common docs-only miss") describe the retired twin model. Current reality: every shipped definition has one committed owner under `src/coga/resources/` (`docs/contexts/coga-dev/packaging/SKILL.md` "This repo has completed its cutover … There are no forwarding files or symlink mirrors"); `tests/test_packaging.py::test_package_definitions_have_no_unapproved_live_counterparts` fails on "even a byte-identical, unapproved live copy" (line 264/275), and this repo has no `coga/contexts/` at all. In an adopting repo the packaged copy is not in the checkout, and a local copy of the same ref is a deliberate local-first override (`coga/context-layout`, `coga/prompt-composition` line 91), so "edit both" is impossible there and would be wrong here. Replace the twin-sync instruction and check with: edit the single owner (package file in the Coga source repo; the repo's own file otherwise), do not create a live counterpart, and in the Coga source repo run `tests/test_packaging.py` when packaged resources change. Update the description's "repo↔packaged sync" phrase to match.

#### coga/important omits agent-unavailable template skips from its important-alert list

- shard: ks-24
- class: stale
- target: src/coga/resources/templates/coga/bootstrap/contexts/coga/important/SKILL.md
- area: coga/notifications

The topic's "Raising an alert" list says Coga routes "recurring template parse errors" (plus script failures, unadvanced state, period contradictions, watchdog timeouts) to important, and the producer inventory it links (`coga/notifications/producers/SKILL.md`, row "Template parse failures in a recurring scan") says the same. Current code posts that alert for more than parse errors: `recurring_runner.py::_broadcast_scan` builds `skipped = scan.errors + [(name, reason) for name, _last_fire, reason in scan.agent_refusals]` and posts "recurring scan skipped N template(s)" with `important=True`. `DueScan.agent_refusals` (`recurring.py`, filled on `AgentUnavailableError` and on agent templates dropped for lack of a TTY / `agent_unavailable_reason`) means a headless sweep that skips an agent-assignee recurring template also raises an important post. Update the important topic's list (and the producers table row in the same PR) to say "recurring templates the scan skipped — parse errors and agent templates refused because no agent can run (e.g. no TTY)", or, if that routing is unintended, file it as a code issue instead.

#### Dream template's "Known corpus limitation" misstates both scans' corpora

- shard: ks-22
- class: stale
- target: src/coga/resources/templates/coga/recurring/dream/ticket.md
- area: bootstrap/dream

The `### Known corpus limitation` paragraph says "Both scans currently exclude package-backed `bootstrap/skills/**`. The knowledge scan owns tickets and `coga/workflows/**`; the contract audit adds recurring templates, `README.md`, `docs/*.md`...". That contradicts the package's own scan skill and actual run behavior: `bootstrap/skills/bootstrap/dream/scan/knowledge-scan/SKILL.md` ("Shard partition", Knowledge evidence) tells the knowledge scan to read every context `SKILL.md`, `coga/skills/**`, and in the source repo `src/coga/resources/templates/coga/bootstrap/{contexts,skills,workflows}/**` plus `templates/coga/recurring/**` — i.e. it lists `bootstrap/skills/**` as in-corpus rather than excluded, and it owns contexts and recurring templates, not just tickets and workflows. This run's `knowledge-scan/index.md` confirms reality: 51 `bootstrap/contexts/` and 12 `templates/coga/recurring/` entries, 0 `bootstrap/skills/` entries. Fix one side so they agree: either rewrite the limitation paragraph to state the real corpora (knowledge scan: tickets, contexts, repo skills, workflows, and in the source repo package contexts/workflows/recurring; package `bootstrap/skills/**` excluded by Dream's indexing) or, if the exclusion is the intended decision, drop `skills` from the knowledge-scan skill's package corpus glob so the skill and the dispatch template stop disagreeing.


### Phase 3 — contract audit (drift)

9/9 shards complete (ca-00 ownership check inline: 0), 16 findings; 9 duplicate a Phase 2 stale finding on the same target and claim (marked `dup-of`), 7 new.

#### coga-dev/codebase "Twins" rule contradicts single-owner packaging

- shard: ca-01
- class: drift
- target: docs/contexts/coga-dev/codebase/SKILL.md
- area: coga-dev/codebase

Line 103-104 says "Canonical topics and their packaged copies must stay byte-identical; see coga-dev/packaging." That is the retired twin model. Code reality: `tests/test_packaging.py` (`_discover_live_packaged_twins`, ownership problems) rejects every unapproved live counterpart of a package definition "even byte-identical files" (coga-dev/packaging lines 72-75, AGENTS.md); shipped user topics have one owner under `src/coga/resources/templates/coga/bootstrap/contexts/`, coga-dev topics are local-only and never packaged, and only physical scaffolds outside `INTENTIONALLY_DIVERGENT_TWINS` are asserted byte-equal (test_packaging.py ~line 330). Replace the bullet with the one-owner rule (package owns shipped definitions; a live copy is a reviewed override; scaffolds are the only byte-equal pairs) and link coga-dev/packaging.

#### gotchas "Known open" uninstall POSIX-hint hazard is already fixed

- shard: ca-01
- class: drift
- dup-of: Phase 2 ks-27 finding (same target/claim; route once)
- target: docs/contexts/coga-dev/codebase/gotchas/SKILL.md
- area: coga-dev/codebase

Lines 149-156 describe as "Known open" that `commands/uninstall.py::_uninstall_via_tool` shows env overrides only as POSIX `VAR=value` prefixes that cmd/PowerShell cannot paste, with the fix "owned by" `v1/15-uninstall-recovery-hints-use-posix-env-syntax-on-w`. Code reality: `src/coga/commands/uninstall.py::_format_tool_command` (line ~385) now takes `windows=` and emits PowerShell `$env:VAR='value'; cmd` assignments on Windows, using `shlex.quote` only on POSIX; the owning ticket `coga/tasks/v1/15-uninstall-recovery-hints-use-posix-env-syntax-on-w.md` is `status: done`. Remove the bullet (or reduce it to the durable rule that pasteable hints must be platform-specific).

#### current-direction names nonexistent workflow `code/agent-merge`

- shard: ca-01
- class: drift
- dup-of: Phase 2 ks-07 finding (same target/claim; route once)
- target: docs/contexts/coga-dev/current-direction/SKILL.md
- area: coga-dev/current-direction

Lines 91-97 ("Thin tickets are designed before they are built") list `code/agent-merge` as a third reviewed workflow "when the owner has opted out of the PR gate", and say "All three have the other agent review the code". No such workflow exists: `src/coga/resources/templates/coga/bootstrap/workflows/code/` holds only `design-then-implement.md`, `with-review.md`, `with-self-review.md`, there is no `coga/workflows/` override, and no other living file in `src/` or `docs/contexts/` mentions `agent-merge`. Source of truth: the packaged workflow directory and `coga/workflows` context. Drop the `code/agent-merge` clause and say "both" (or add the workflow if the decision is still intended).

#### agent-config describes a removed init mechanism (`_configure_agent_tables`)

- shard: ca-01
- class: drift
- dup-of: Phase 2 ks-16 finding (same target/claim; route once)
- target: docs/contexts/coga-dev/internals/agent-config/SKILL.md
- area: coga-dev/internals

Lines 59-62 say "Interactive `coga init` writes no `default_agent` key at all: it comments out the `[agents.*]` table of every supported agent whose CLI it did not find (`commands/init.py` `_configure_agent_tables`), which leaves declaration order to name the default". Code reality: no `_configure_agent_tables` exists anywhere in `src/coga/`. `src/coga/commands/init.py` now has `_offer_agent_cli` (when exactly one supported agent CLI is installed and it is not the template default, asks to make it the default), `_write_default_agent` (writes a top-level `default_agent = "<name>"` key into coga.toml), and `_stamp_agent_into_delivered_tickets` (rewrites delivered onboarding tickets' `agent: claude` to the new default) — so line 57-58's "onboarding tickets pin `agent: claude`, which outranks the default" also needs the restamp caveat. Source of truth: `src/coga/commands/init.py` lines ~579-700 and the `coga/init` context (current-direction line 121-123 already describes "init may offer an already-installed CLI as the default").

#### marketing/write-post names a launch-plan ticket slug that no longer exists

- shard: ca-06
- class: drift
- dup-of: Phase 2 ks-07 finding (same target/claim; route once)
- target: coga/skills/marketing/write-post/SKILL.md
- area: skills/marketing

Line 118 says "publication sequencing lives in `v1/44-build-the-launch-plan`", but no such ticket exists: `v1/44` is now `coga/tasks/v1/44-verify-the-macos-full-suite-procedure-on-the-ec.md`, and the launch-plan ticket lives at `coga/tasks/_v2/marketing/build-the-launch-plan.md` (status `in_progress`). On-disk task tree is the source of truth; repoint the reference to `_v2/marketing/build-the-launch-plan` (or name it generically as "the named launch ticket", as Step 8 and the closing paragraph already do). Related: lines 116-117 and 130 cite `v1/42-idea-piece` as owning the V1 idea piece's editorial decisions, but that ticket is `status: canceled` (owner deferred it, log 2026-11-04 "I'll write it afterwards"), so the skill's worked example points at a canceled ticket.

#### docs/with-review still tells agents to keep live and packaged copies in sync

- shard: ca-08
- class: drift
- dup-of: Phase 2 ks-29 finding (same target/claim; route once)
- target: src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md
- area: workflows/docs

The workflow's frontmatter description (line 3, "repo↔packaged sync"), implement step 4 (lines 89-92, "edit **both** in the same commit") and the peer-review "Cross-copy sync" bullet (lines 132-135, "confirm both were updated ... the most common docs-only miss") assume a shipped context or template has both a live copy under `coga/` and a packaged copy under `src/coga/resources/templates/coga/`. That contradicts the completed package-definition cutover: the package is the one committed owner of every shipped definition, and `tests/test_packaging.py` (`_discover_live_packaged_twins` / `_ownership_problems`, documented in `docs/contexts/coga-dev/packaging/SKILL.md` lines 72-97 and AGENTS.md "Project Structure") rejects every unapproved live counterpart, even a byte-identical one. Following the instruction would create a live copy that the test suite fails, and in a client repo no packaged copy exists to sync. Source of truth: `tests/test_packaging.py` plus `coga-dev/packaging`. Replace the sync guidance with "edit the package owner; a same-ref local copy is a deliberate reviewed override" (per `coga/knowledge`/packaging rules).

#### Dream "Known corpus limitation" contradicts both scan skills' source-repo corpus

- shard: ca-07
- class: drift
- dup-of: Phase 2 ks-22 finding (same target/claim; route once)
- target: src/coga/resources/templates/coga/recurring/dream/ticket.md
- area: bootstrap/dream

`recurring/dream/ticket.md` lines 236-241 (`### Known corpus limitation`) state "Both scans currently exclude package-backed `bootstrap/skills/**`" and that correcting it "requires a corpus decision for both scans". The scan skills that own the corpus say the opposite: `bootstrap/dream/scan/contract-audit` SKILL.md (Shard partition, **skills** group) says "In the Coga source repo also the package's `bootstrap/skills/**/SKILL.md`", and `bootstrap/dream/scan/knowledge-scan` SKILL.md (lines 55-58) says in the source repo "also read `src/coga/resources/templates/coga/bootstrap/{contexts,skills,workflows}/**`". This run's contract-audit `index.md` contains zero `bootstrap/skills` paths, i.e. Dream followed the ticket's limitation rather than the skill. Either delete the limitation paragraph (the corpus decision has been made in the scan skills) or revert the skills; the two surfaces must agree, with the scan skills as the stated corpus owners.

#### docs/README.md points the native Windows boundary at the wrong coga/launch section

- shard: ca-08
- class: drift
- target: docs/README.md
- area: docs index

docs/README.md lines 14-16 say "The native Windows boundary is in [coga/launch](…/coga/launch/SKILL.md#phases-and-routing)". The `## Phases and routing` section of `src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md` (lines 78-97) says nothing about Windows; the native Windows rules (agent owns the console, `--idle-timeout` exits 2 and names `--max-session`, CreateProcess/cmd.exe command-length refusals) live under `## Options and exits` (lines 143-153), with the preflight ordering reference at line 102 in `## Agent preflight order`. Source of truth: the coga/launch topic's headings. Retarget the link to `#options-and-exits`.

#### coga/workflows claims `coga init` seeds workflows (including `direct/body`) into the repo

- shard: ca-05
- class: drift
- dup-of: Phase 2 ks-06 finding (same target/claim; route once)
- target: src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md
- area: coga/workflows
- owner: local

Lines 10-12 say "`coga init` seeds some workflows into the repo, including `direct/body`". Code reality contradicts this: `copy_fresh_templates` (`src/coga/commands/update.py:92`) copies only `FRESH_SCAFFOLDS` (`update.py:63-74`), whose only workflow entry is the ignored authoring starter `workflows/_template.md`; `direct/body` ships only at `src/coga/resources/templates/coga/bootstrap/workflows/direct/body.md` and resolves from the package. The owning topic `coga/init` (lines 42-48) states "No reusable definition is copied: contexts, skills, workflows ... resolve from the installed package". Fix: replace the sentence with "Shipped workflows, including `direct/body` (which runs the ticket body's ordered phases), resolve from the package; `coga init` copies only the ignored `workflows/_template.md` starter."

#### publish leaf's quoted signatures omit `remember` and `prepared`

- shard: ca-02
- class: drift
- dup-of: Phase 2 ks-10 finding (same target/claim; route once)
- target: docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md
- area: coga-dev/internals/state-publication

Lines 12-13 quote `git.publish(cfg, paths, message, *, expect=None, guard=None, fast_forward=True, require_paths=(), log_mutation=None)` and lines 63-64 quote `sync_task_state(cfg, task_path, *, message, expect=None, strict=False, command=None)` as the full signatures. Code reality (`src/coga/git.py:503-514`, `:241-250`): `publish` also takes `remember: bool = False` (a prepared lifecycle transaction records retryable/refused expectations in the checkout's pending-expectation file so the supervisor retry and sweep reuse them), and `sync_task_state` also takes `prepared: PreparedTicket | None = None` (publishes a prepared transaction whose control bytes become the ticket's expectation). The leaf documents neither parameter nor the remembered-expectation behavior; add them to the quoted signatures with a one-line pointer to `coga/state-publication#prepared-ticket-transactions`, which owns the user contract.

#### extension-model routes `delete-task` to coga/checkouts, which does not own it

- shard: ca-03
- class: drift
- target: src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md
- area: coga/extension-model

Line 126-128 says "`open-pr` and `delete-task` take a task ref; see [PR publication] and [coga/checkouts](../checkouts/SKILL.md)", pairing `delete-task` with `coga/checkouts`. `coga/checkouts/SKILL.md` (and its leaves) never mention `delete-task` or `coga delete`; the recipe's contract lives in `coga/checkout-cleanup/SKILL.md` § "`coga delete <slug>`" (line 146-157, "`coga run delete-task <slug>` does the same removal without syncing"), which `coga/cli` also names as the `delete` owner. Source of truth: checkout-cleanup/SKILL.md and cli/SKILL.md line 33. Fix: point the `delete-task` link at `../checkout-cleanup/SKILL.md#coga-delete-slug`.

#### phone-home runbook runs a `recurring/phone-home/ticket.py` a fresh init never creates

- shard: ca-07
- class: drift
- target: src/coga/resources/templates/coga/recurring/phone-home/operations.md
- area: recurring/phone-home

`recurring/phone-home/operations.md` line 128 tells the owner, in the clean installed-wheel proof scratch repo made by `coga init`, to "run `/tmp/coga-telemetry-release/bin/python recurring/phone-home/ticket.py` from `coga/`" for a later snapshot. Code reality: `coga init` copies only `FRESH_SCAFFOLDS` (`src/coga/commands/update.py`), which excludes recurring definitions and their scripts, and the only repo file phone-home itself creates is the state carrier `coga/recurring/phone-home/ticket.md` (`coga_edge.phone_home._parent_state` -> `recurring_state.ensure_parent_state`, which writes the carrier ticket only). The package-backed `ticket.py` shim is copied into the period task, not into `coga/recurring/phone-home/`, so that path does not exist in the scratch repo. Repoint the step at something that exists for a package-backed definition, e.g. `/tmp/coga-telemetry-release/bin/python -m coga_edge.phone_home` from `coga/` (the module's `__main__` runs `main()`), or `coga recurring launch phone-home --rerun` if a named rerun is intended.

#### testing topic cites removed `_strip_runtime_state` helper

- shard: ca-02
- class: drift
- target: docs/contexts/coga-dev/testing/SKILL.md
- area: coga-dev/testing

Line 129-130 ("Do not pin to live dogfooded state") tells authors to "Strip runtime fields (see `_strip_runtime_state` in `tests/test_autoclose_sweep.py`)". No symbol `_strip_runtime_state` exists anywhere under `tests/` or `src/` today (grep returns nothing; `git log -S` shows it was last touched/removed in 5102c3be4 "test: enforce package-owned definitions after repo cutover", after the package-definition cutover stopped tests reading live `coga/` definitions). Source of truth: the test tree. Replace the example with a current one or drop the parenthetical, keeping the rule itself (tests read package-owned definitions, so the guidance may now apply mainly to live state such as blackboards/log).

#### Two oversized checkout topics lack the required `Size exception:` sentence

- shard: ca-03
- class: drift
- target: src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md; src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/launch-boundary/SKILL.md
- area: coga/checkouts

`coga/knowledge` (knowledge/SKILL.md lines 126-132) says a topic over 200 lines, 10,000 bytes, or 2,500 tokens is reviewed for a split, and any exception "needs a recorded reason, written in the oversized topic itself as one closing `Size exception:` sentence". On disk `coga/checkouts/SKILL.md` is 203 lines / 11,735 bytes (~2,934 tokens) and `coga/checkouts/launch-boundary/SKILL.md` is 10,977 bytes (~2,744 tokens); neither contains a `Size exception:` sentence (grep count 0), whereas `coga/init/SKILL.md` (12,022 bytes) carries one. Source of truth: the size policy in knowledge/SKILL.md and `wc -c`/`wc -l` on the files. Fix: either split further (e.g. move "Stranded ticket writes" or the step-entry table out of checkouts/SKILL.md) or append the closing `Size exception:` reason to each.

#### branch-sweep/sweep workflow still describes a period task and period blackboard

- shard: ca-07
- class: drift
- dup-of: Phase 2 ks-15 finding (same target/claim; route once)
- target: src/coga/resources/templates/coga/bootstrap/workflows/branch-sweep/sweep.md
- area: recurring/branch-sweep

`bootstrap/workflows/branch-sweep/sweep.md` lines 13-14 say "`coga launch` runs the period task's reserved `ticket.py`" and lines 25-26 say "The run's report lands on this period task's blackboard." The packaged template it serves (`recurring/branch-sweep/ticket.md`) is now `scope: clone` with no `workflow:` field: a run "creates no period task and has no period blackboard", and the `## Branch Sweep` report is kept in the clone's `.coga/recurring-clone/branch-sweep.log` and the run record (template lines 79-82, 115-121; `src/coga/recurring_clone.py` `_STATE_DIR`/`.log` path; `branchsweep.py` ~line 1326). Only a pre-clone-scope Coga still runs it as a period task (see the `recurring/branch-sweep/ticket.py` comment). Update the workflow prose to describe the clone-scoped run (report to the clone-local log and run record, no period task), or mark it explicitly as the legacy period-task lifecycle kept for older installs; the template and `coga.recurring_clone` are the source of truth.

#### design-then-implement tells the owner to rewind with `coga bump --to design`, but `--to` takes a step number

- shard: ca-07
- class: drift
- target: src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md
- area: workflows/code

`bootstrap/workflows/code/design-then-implement.md` line 54 (the `## review-design` section) says: "rewind with `coga bump <slug> --to design` instead of bumping". `coga bump --to` is declared `to_step: int | None` in `src/coga/commands/bump.py` (line 51) with help "rewind to an earlier 1-based workflow step number", so `--to design` is rejected by Typer as a non-integer. The `design` step is step 1 of this workflow, so the correct instruction is `coga bump <slug> --to 1` (or name the step and give its number).


## Phase 4 setup

- Run dir: `/tmp/claude-1000/-home-n-Code-coga/bc8b3814-b11c-4800-9198-327b301e0a3e/scratchpad/dream-retro.tRYOwx` (evidence/ read-only snapshot, progress.md).
- Isolated linked worktree: `<run dir>/checkout`, temp branch `dream-retro-20261112T051938Z` from fresh `origin/main` @ be6f1aff4. Write probe ok; `coga.local.toml` ordinary-copied (gitignored).
- 52 eligible slugs delegated to one `retro/done-ticket` subagent.
- Phase 4 result: **pr-opened** — `complete — 9 PRs, 39 direct deletes, 52 tickets`. Verified after fetch: all 39 deletes absent from `origin/main`; all 9 PR heads pushed; isolated checkout had no commits ahead and only landed deletions. Worktree + temp branch `dream-retro-20261112T051938Z` (5f7da44d7, ancestor of origin/main) removed; run dir deleted. Local `codex/retro-*` PR branches remain (pushed; branch-sweep's job).
  - #1200 codex-claude-capture-unknowns — v1/35, v1/honor-codex-home…
  - #1201 pytest-temp-roots — v1/26, v1/filter-by-user-for-megalaunch, v1/package-definitions/02
  - #1202 macos-tool-baseline — v1/16, v1/re-run-the-macos-install-walk-from-source
  - #1203 hands-on-trial-method — competition-testing/test-kiro
  - #1204 agent-cli-audience — v1/19
  - #1205 pr-preparation-yaml — v1/13
  - #1206 sync-failure-attribution — v1/06
  - #1207 sandboxed-quiescence-evidence — commit-journal/activate-trim-log…
  - #1208 skill-update-detached-head — v1/10
  - Direct-deleted (39, no durable knowledge): 7 recurring periods (address-pr-comments, autoclose-merged, blocker-reminders, phone-home, resolve-conflicts, skill-update, usage-report) + 32 others (see git log on main).
