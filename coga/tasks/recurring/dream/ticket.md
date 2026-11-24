---
title: Dream
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
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

1. **validate-drift** — deterministic repo hygiene (edge worker).
2. **knowledge scan** — sharded corpus read; classifies every finding.
3. **contract audit** — sharded check of the contract surface against code
   reality.
4. **retro/done-ticket** — extracts durable knowledge from every eligible done
   ticket in one pass.
5. **cleanup-orphan-markers** — delete-only orphan cleanup (edge worker).
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

The two deterministic phases (1 and 5) run Python workers directly from
this Dream task. Before each run, read the matching skill's
`## Known Skill Contract`, keep reads and writes inside its declared scope,
then invoke the exact command below with the Python interpreter that runs
`coga`. The worker inherits this task's `COGA_TASK_*` context, writes its
`## Dream Skill: <name>` section directly to this task's blackboard, publishes
eligible Coga state on exit, and never advances this task. An interpreter that
cannot import the worker is a failed phase, not permission to substitute
another command. Do not create child worker tasks.

### Agent capability preflight

Run this once, from Dream's checkout, before Phase 1. The execute half
uses Git and GitHub for the isolated Retro changes. Determine the remote
and base from the repository's Git and GitHub configuration, then check the
capabilities before starting the decide half.

1. **The Git common dir is writable.** Resolve
   `git rev-parse --path-format=absolute --git-common-dir`, create a uniquely
   named probe file in that directory (for example
   `mktemp "<common-dir>/coga-dream-preflight.XXXXXX"`), then remove it. A
   permission-bit check does not count, and the probe never uses a Git lock
   name.
2. **The remote is reachable.**
   `git ls-remote <configured-remote> <base>` succeeds.
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
`python -m coga_edge.validate_drift`. The worker runs the same deterministic
surface as `coga validate --json`, classifies every issue, and appends
`## Dream Skill: validate-drift` to this task's blackboard.

The skill's default safe-repair pass applies only deterministic repairs
currently supported by `coga validate --fix`: append a missing blackboard fence
+ rendered region to a `ticket.md` that lacks one. The single-file format keeps
state in `ticket.md`'s blackboard region — there is no sibling `blackboard.md`
or `log.md`, and retained history goes to the repo-global `coga/log.md`. It
does not rewrite existing files, synthesize `ticket.md`, freeze workflows, or
change lifecycle/assignee state.

The worker's three buckets are inputs to Phase 6, not results. `direct-fix`
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
Fetch the configured remote base branch first and base
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
remote base branch and branch/PR state before retrying. Without `complete`,
report the phase as `partial` with the file's contents and preserve the run
directory and isolated checkout for recovery; a final message alone does not
establish completion.

Retro hands PR FYIs back as `pr` receipts in `progress.md` and never runs
`coga slack` in the isolated checkout (skill step 12). After it returns, Dream
posts each FYI from its own checkout with
`coga slack --task <this-dream-task>`, which appends the audit line locally.

Every processed done ticket is deleted: a ticket that contributed durable
knowledge is deleted in its theme's knowledge PR, which also records its
`## Retro` marker. For an unreferenced ticket carrying no durable knowledge,
follow Retro's local deletion and explicit Git handoff. Recovery is via
`git restore`. Retro never leaves a processed done
ticket on disk and never opens a marker-only PR. Retro also searches tracked
files for durable references to each source task, such as a README or doc
link on `blob/<base>`. Before a deletion lands, it repoints each one
to a commit permalink in a PR. A no-durable-knowledge ticket with such a
reference therefore leaves in the run's reference-pin PR, not by direct
delete. The skill's **Inbound references** section owns the rule. The
eligibility gates above do not cover it.

After the subagent returns, fetch the remote base branch and verify:

- every PR branch is pushed;
- every direct delete is present on the remote base branch;
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
(`git log --oneline <remote>/<base>..<branch>`), the unlanded paths
(`git diff --stat <remote>/<base>...<branch>` plus uncommitted
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
`python -m coga_edge.cleanup_orphan_markers`. The worker detects cleanup
candidates and gates deletion through `bootstrap/delete-task`
(`coga run delete-task`). That delete surface ships, but until its cleanup
PR-dispatch wiring is finished the worker reports `human-needed` and deletes
nothing.

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
`brief-for-human` draft with no branch or PR requirement. The owner can edit locally and share changes through ordinary Git. Dream does not rewrite another ticket's blackboard.

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
  the tag line `validate-drift: <kind>` verbatim, the worker's remediation
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
entry left only in the worker's disposable blackboard bucket is unfinished.

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

The Phase 1 and 5 workers write their durable results to this Dream task's
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
it against the fetched remote base branch, remove the preserved paths, and
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


## Dream Skill: validate-drift

Generated: 2026-11-23T22:48:24+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python -m coga.validate --json --fix`
Task: `recurring/dream`

Result: 107 issue(s): 0 direct fix, 0 PR proposal, 107 human-needed.

### Human Needed

- `add-the-megalaunch-dependency-resolution-append-lo`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `add-the-megalaunch-dependency-resolution-append-lo`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `add-the-megalaunch-dependency-resolution-append-lo`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `add-the-megalaunch-dependency-resolution-append-lo`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `correct-script-tickets-on-which-supervisor-variabl`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `correct-script-tickets-on-which-supervisor-variabl`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `correct-script-tickets-on-which-supervisor-variabl`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `correct-script-tickets-on-which-supervisor-variabl`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `decide-the-two-open-questions-left-by-the-checkout`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `decide-the-two-open-questions-left-by-the-checkout`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `decide-the-two-open-questions-left-by-the-checkout`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `decide-the-two-open-questions-left-by-the-checkout`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `decide-where-the-google-helper-skills-read-their-c`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `decide-where-the-google-helper-skills-read-their-c`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `decide-where-the-google-helper-skills-read-their-c`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `decide-where-the-google-helper-skills-read-their-c`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `fix-git-sync-failure`: `unfrozen-workflow` (warn) - workflow 'code/with-self-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `fix-the-google-skills-dead-helper-invocation-paths`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `fix-the-google-skills-dead-helper-invocation-paths`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `fix-the-google-skills-dead-helper-invocation-paths`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `fix-the-google-skills-dead-helper-invocation-paths`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `fix-the-readme-windows-walk-findings-left-unowned`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `fix-the-readme-windows-walk-findings-left-unowned`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `fix-the-readme-windows-walk-findings-left-unowned`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `fix-the-readme-windows-walk-findings-left-unowned`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `fix-the-windows-aws-walk-step-and-add-the-v1-14-at`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `fix-the-windows-aws-walk-step-and-add-the-v1-14-at`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `fix-the-windows-aws-walk-step-and-add-the-v1-14-at`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `fix-the-windows-aws-walk-step-and-add-the-v1-14-at`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `implement-the-include-allowlist-that-url-skill-upd`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `maintain-ticket-blackboards`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `maintain-ticket-blackboards`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `maintain-ticket-blackboards`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `maintain-ticket-blackboards`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `marketing/research-how-agents-make-delegated-decisions-geo`: `stuck-in-progress` (warn) - in_progress but idle for 193.7h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `name-clone-scoped-recurring-scripts-among-the-scru`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `name-clone-scoped-recurring-scripts-among-the-scru`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `name-clone-scoped-recurring-scripts-among-the-scru`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `name-clone-scoped-recurring-scripts-among-the-scru`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `parse-agents-rejects-cogalocaltoml`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `refresh-the-v1-microkernel-task-readmes-after-the`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `refresh-the-v1-microkernel-task-readmes-after-the`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `refresh-the-v1-microkernel-task-readmes-after-the`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `refresh-the-v1-microkernel-task-readmes-after-the`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `stop-creating-linked-worktrees-for-coga-retire`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `stop-megalaunch-when-an-agent-fails-to-start`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `stop-megalaunch-when-an-agent-fails-to-start`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `stop-megalaunch-when-an-agent-fails-to-start`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `stop-megalaunch-when-an-agent-fails-to-start`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `ticket-sync-fails-with-read-only-git-inside-agent`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `update-the-testing-topic-known-failure-note-on-the`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `update-the-testing-topic-known-failure-note-on-the`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `update-the-testing-topic-known-failure-note-on-the`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `update-the-testing-topic-known-failure-note-on-the`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/01-urgent-roll-out-the-04b-edge-shims-on-this-repo-s-blocker`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/01-urgent-roll-out-the-04b-edge-shims-on-this-repo-s-blocker`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/01-urgent-roll-out-the-04b-edge-shims-on-this-repo-s-blocker`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/03-use-git-like-everyone-remove-coga-s-publication-ab`: `large-blackboard` (warn) - blackboard region is 45.3 KiB (warning threshold 32.0 KiB); it is included in launch prompts. Consider summarizing old notes.
  Remediation: Ask the owner to choose the `coga/blackboard` remedy. For done tickets, use Dream's Retro/retirement route instead of slimming; recurring writer state needs its owner's decision. For live tickets, promote a file-form task to directory form (a task that already has `<slug>/ticket.md` keeps its directory), move dated evidence into sibling attachments, move abandoned designs into the single `## Superseded designs` section (it does not count toward the size), move material several tickets cite into an unattached context, and leave the current handoff, worklist and verification on the blackboard with a pointer to each. Keep `## Dev` and `## Blockers` in place under the `coga/blackboard` contract; CLI readers do not follow attachment links for that state. Move, do not delete. Publish ticket and attachment edits through `coga/state-publication`; use direct owner editing or a `brief-for-human` draft with no branch or PR requirement.
- `v1/03-use-git-like-everyone-remove-coga-s-publication-ab`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/03-use-git-like-everyone-remove-coga-s-publication-ab`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/03-use-git-like-everyone-remove-coga-s-publication-ab`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/03-use-git-like-everyone-remove-coga-s-publication-ab`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/03-use-git-like-everyone-remove-coga-s-publication-ab`: `obsolete-key` (warn) - workflow step #5 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/03-use-git-like-everyone-remove-coga-s-publication-ab`: `obsolete-key` (warn) - workflow step #6 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/03-use-git-like-everyone-remove-coga-s-publication-ab`: `obsolete-key` (warn) - workflow step #7 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/04-script-or-agent-one-executor-model-and-one-launch`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/04-script-or-agent-one-executor-model-and-one-launch`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/04-script-or-agent-one-executor-model-and-one-launch`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/04-script-or-agent-one-executor-model-and-one-launch`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/04-script-or-agent-one-executor-model-and-one-launch`: `obsolete-key` (warn) - workflow step #5 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/04-script-or-agent-one-executor-model-and-one-launch`: `obsolete-key` (warn) - workflow step #6 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/04-script-or-agent-one-executor-model-and-one-launch`: `obsolete-key` (warn) - workflow step #7 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/13-move-ticket-authoring-to-a-command-ticket`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/13-move-ticket-authoring-to-a-command-ticket`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/13-move-ticket-authoring-to-a-command-ticket`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/13-move-ticket-authoring-to-a-command-ticket`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/13-move-ticket-authoring-to-a-command-ticket`: `obsolete-key` (warn) - workflow step #5 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/13-move-ticket-authoring-to-a-command-ticket`: `obsolete-key` (warn) - workflow step #6 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/13-move-ticket-authoring-to-a-command-ticket`: `obsolete-key` (warn) - workflow step #7 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/14-move-skill-management-to-command-tickets`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/14-move-skill-management-to-command-tickets`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/14-move-skill-management-to-command-tickets`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/14-move-skill-management-to-command-tickets`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/14-move-skill-management-to-command-tickets`: `obsolete-key` (warn) - workflow step #5 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/14-move-skill-management-to-command-tickets`: `obsolete-key` (warn) - workflow step #6 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/14-move-skill-management-to-command-tickets`: `obsolete-key` (warn) - workflow step #7 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/16-second-pass-move-branch-sweep-and-autofix-repl`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/16-second-pass-move-branch-sweep-and-autofix-repl`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/16-second-pass-move-branch-sweep-and-autofix-repl`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/16-second-pass-move-branch-sweep-and-autofix-repl`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/16-second-pass-move-branch-sweep-and-autofix-repl`: `obsolete-key` (warn) - workflow step #5 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/16-second-pass-move-branch-sweep-and-autofix-repl`: `obsolete-key` (warn) - workflow step #6 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/16-second-pass-move-branch-sweep-and-autofix-repl`: `obsolete-key` (warn) - workflow step #7 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/17-move-autoclose-to-the-edge`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/17-move-autoclose-to-the-edge`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/17-move-autoclose-to-the-edge`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `v1/microkernel/17-move-autoclose-to-the-edge`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `validate-drift-stuck-in-progress-in-progress-ticke`: `stuck-in-progress` (warn) - in_progress but idle for 276.6h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `validate-drift-unfrozen-workflow-canceled-tickets`: `stuck-in-progress` (warn) - in_progress but idle for 276.6h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `warn-when-coga-delete-or-coga-retire-leaves-a-live`: `obsolete-key` (warn) - workflow step #1 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `warn-when-coga-delete-or-coga-retire-leaves-a-live`: `obsolete-key` (warn) - workflow step #2 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `warn-when-coga-delete-or-coga-retire-leaves-a-live`: `obsolete-key` (warn) - workflow step #3 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `warn-when-coga-delete-or-coga-retire-leaves-a-live`: `obsolete-key` (warn) - workflow step #4 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `warn-when-coga-delete-or-coga-retire-leaves-a-live`: `obsolete-key` (warn) - workflow step #5 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `warn-when-coga-delete-or-coga-retire-leaves-a-live`: `obsolete-key` (warn) - workflow step #6 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `warn-when-coga-delete-or-coga-retire-leaves-a-live`: `obsolete-key` (warn) - workflow step #7 ignores its legacy checkout key
  Remediation: Review obsolete configuration locally. Leave frozen workflow snapshots intact.
- `warn-when-coga-delete-or-coga-retire-leaves-a-live`: `stuck-in-progress` (warn) - in_progress but idle for 137.8h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.

## Run log

- preflight: git-common-dir ok, remote ok (origin/main), gh ok.
- Phase 1 validate-drift: reported — 107 human-needed (obsolete-key 97, unfrozen-workflow 5, stuck-in-progress 4, large-blackboard 1).
- repo-identity: coga-source. Scan dir: /home/n/Code/coga/coga/.coga/dream-scans/20261123T224856Z/{knowledge-scan,contract-audit}
- Phase 2 knowledge-scan: 17 shards (ks-01..ks-17) planned; Phase 3 contract-audit: 9 shards (ca-01..ca-09; ca-09 also runs the single-source ownership check). Waves of 9.
- Phase 4 eligibility (pre-check, read-only):
  - eligible (done, no live checkout; all on origin/main identical to wt): decide-the-two-open-questions-left-by-the-checkout, name-clone-scoped-recurring-scripts-among-the-scru, update-the-testing-topic-known-failure-note-on-the, fix-the-readme-windows-walk-findings-left-unowned, maintain-ticket-blackboards, decide-where-the-google-helper-skills-read-their-c, stop-megalaunch-when-an-agent-fails-to-start, v1/01-urgent-roll-out-the-04b-edge-shims-on-this-repo-s-blocker, recurring/address-pr-comments, recurring/blackboard-size, recurring/blocker-reminders (tracked; open PR #1280 edits one line each, but no PR adds a Retro marker or deletes them).
  - retirement debt (done+checkout): refresh-the-v1-microkernel-task-readmes-after-the (local branch `refresh-v1-microkernel-readmes-after-retro`), make-retro-check-inbound-doc-links-before-deleting (branch live locally + on origin).
  - local-only done period tickets (untracked, absent on origin/main): recurring/{phone-home,resolve-conflicts,skill-update,trim-log,usage-report}. Retro reads them from the snapshot for gotchas but cannot delete them from an isolated checkout based on main; deleting untracked files has no `git restore` recovery, so Dream leaves them for the recurring scanner's next-firing fallback.
- GitHub REST core quota exhausted at ~22:56Z (reset ~23:29Z); graphql still has headroom. Scans need no gh.
- Phase 2 knowledge-scan: reported — 17/17 leaves complete (distinct ids), 29 raw findings before de-dup.
- CAUTION for Phase 6: Dream's checkout is branch coga/v1-no-weird-state-in-personal-dir-d9bd4b (PR #1280, stacked on v1/03 PR #1279), 302 files ahead of origin/main; commit 1099f14c3 (plain-Git migration: removes src/coga/{autoclose,git,open_pr,retire_worklist}.py) is NOT on main. Shards judged against this branch. Each finding must be re-verified against origin/main before routing: branch-only contradictions belong to the in-flight migration (v1/03), not to main-based proposal PRs.
- Phase 3 contract-audit: reported — 9/9 leaves complete (distinct ids), 20 raw findings; ownership check (`_ownership_problems`) printed nothing.

## Findings

49 raw findings (ks 29 + ca 20) → 38 after de-duplication. Each re-verified against origin/main (Dream checkout is the unmerged PR #1280 branch stacked on #1279).

### Valid on origin/main

- F1 stale — `src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md` (~l.46): "Retro and `coga delete` remove a ticket without repairing inbound references" — Retro's Inbound references section now repoints live-tree links to commit permalinks; only `coga delete`/`coga retire` skip it (owner of a warning: `warn-when-coga-delete-or-coga-retire-leaves-a-live`). [ks-09] area: coga/knowledge
- F2 stale — `docs/contexts/coga-dev/microkernel/SKILL.md` open-placements table names the `owner` head's cleanup ticket by the old slug `lifecycle-verbs-to-ticket-operations`; it is `v1/microkernel/15-lifecycle-verbs-to-ticket-operations`. [ks-06]
- F3 stale — `docs/contexts/coga-dev/current-direction/SKILL.md` "No branch freshness guard at bump" entry ends "Contract: coga/workflows", which says nothing about a freshness guard. (The thin-ticket half of ks-14's finding is false on main: workflows l.144 names design-then-implement.) [ks-14]
- F4 stale — `coga/tasks/v1/package-definitions/README.md` is a completed design record: links two deleted tickets (01/02), proposal tense, cutover finished per AGENTS.md. [ks-08]
- F5 stale — `coga/tasks/blocks/README.md` "Rules for every ticket" prescribes editing a live topic and its packaged twin together; the package-only cutover forbids live copies. [ks-16]
- F6 stale — `coga/tasks/v1/README.md` "only open tickets" table still lists done `v1/01-urgent-…` under Urgent. Handled with v1/01's Retro deletion (inbound reference). [ks-08]
- F7 gap — shipped `coga/prompt-composition` `## Assembler ruling` carries Coga-dev trial evidence (context-audiences rule); `coga-dev/internals/compose` records it as an unanswered open placement question; no owner ticket. [ks-16]
- F8 gap — `coga/releasing` gate lacks the `uvx --python 3.11 twine check` caution. owner: v1/14-publish-coga-1-0-as-the-final-v1-step [ks-05]
- F9 stale+gap — `coga/testing/clean-install/windows-aws` walk step / attended-run gotchas (owner: fix-the-windows-aws-walk-step-and-add-the-v1-14-at, PR #1276) and missing symlink-privilege caveat (owner: v1/07-wire-agent-skills-on-windows-without-symlink-pr). [ks-04 ×2]
- F10 gap — Google skills' `/resolved/…` helper path has no recipe. owner: fix-the-google-skills-dead-helper-invocation-paths (PR #1277). [ks-12]

### extract (area-grouped)

- coga/megalaunch — E1 `stop-megalaunch-when-an-agent-fails-to-start` (source: done): failed-agent-start stop-and-restore contract (`exec_failed`, exit 127) absent from the megalaunch topic. [ks-13] → Phase 4
- coga/pr-publication — E2 `open-prs-only-when-ready-to-merge-and-needing-huma` (source: canceled): owner decision not to add early/draft-PR guidance (packaged Coga opens PRs only at open-pr). [ks-01] → retirement debt
- retro/done-ticket — E3 `stop-creating-linked-worktrees-for-coga-retire` (source: canceled): Retro's isolated worktree is an accepted exception to the no-linked-worktrees direction (2026-10-14). [ks-09] → retirement debt
- coga-dev/internals/agent-config — E4 `marketing/fix-installer/add-gemini-as-an-agent-coga-can-drive` (source: canceled): verified Gemini CLI 0.66.0 integration limits + decision not to act. [ks-17] → retirement debt

### Branch-only residue of the plain-Git migration (true on PR #1279/#1280 branch, not on main)

Targets named in v1/03's "Docs to change" list but still stale on the branch, plus a few outside it:
B1 coga-dev/codebase/gotchas (git.py, branchcleanup/branchsweep/open_pr, publish/_git_env) [ks-16, ca-01] · B2 internals/activity-capture `git.sync_log` [ca-01] · B3 internals index omits 7 pages [ks-16, ca-01] · B4 internals/agent-spawn removed symbols (`prepare_control_checkout`, `retry_session_publication`, `before_recompose`, `_admit_held_child`, …) and missing run-state tmp scope [ca-01, ks-02] · B5 internals/compose `CheckoutNotice`/`_prepare_step_checkout` [ca-01] · B6 internals/notifications autoclose/branchsweep callers, `preflight_post` caller list [ks-12, ca-01] · B7 internals/recurring-clone "resolves through git's common dir" [ca-01] · B8 coga-dev/microkernel `autoclose.py`, `_preflight_push_auth`, `github_preflight`, `RETRY_WITHOUT_SWEEP_EXIT_CODE` [ca-01] · B9 coga/recurring/templates `retire_worklist.py`, `autoclose/sweep`, autoclose-merged/branch-sweep run_when_inactive, `run_recipe` shims [ks-08, ks-10, ca-04 ×2] · B10 code/design + bootstrap/ticket citation examples `src/coga/git.py`/`sync_task_state` [ca-06] · B11 coga/first-task `coga validate --check-github` [ca-03] · B12 recurring/resolve-conflicts template "after branch-sweep" [ca-08] · B13 coga/usage `/log.md -merge` vs scaffold `merge=union` [ca-04] · B14 recurring/dream Phase 4 helpers (`autoclose.parse_branch_names`, `retire_worklist.is_discharged`, …) and "retire disposes of the checkout" [ks-10, ca-08] · B15 coga/workflows autoclose-merged merge-triggered closure [ca-04] · B16 coga/notifications/producers autoclose/branch-sweep producers [ca-03] · B17 coga/recurring overview self-links `recurring-control`/`recurring-temp-worktrees` [ks-11, ca-03] · B18 coga/recurring/autofix `coga autoclose` alias [ks-11, ca-03] · B19 coga/sandboxes `[git] sync failed`/hash-object/control-branch [ks-01] · B20 internals/assist-publication description vs stub body [ks-01] · B21 internals/recurring-admission description vs stub body [ks-12] · B22 internals/spool-merge name/description vs body [ks-12] · B23 internals/blackboard-io `open_pr` reader (+ taskfile.py:238 comment) [ks-16] · B24 retro/done-ticket "review its audit log"/"publishes only the task and the log" — branch `coga delete` writes no log [ca-07].
Full per-finding text: scan findings.md (merged here; scan dir deleted after merge).

## Phase 4 Retro

Result: reported — `complete — 2 PRs, 9 direct deletes, 11 tickets (+5 local-only classified none)`; verified against origin/main da2da0630 (all deletes present, PR branches pushed at matching OIDs, isolated checkout clean with 0 unlanded commits). Worktree, temp branch `dream-retro-20261123T224856Z` and run dir /tmp/coga-dream-retro.WTFkZ0 removed.

- Knowledge PR: https://github.com/FastJVM/coga/pull/1281 — "New context: the terminal-backstop PTY test can fail once under full-suite load" (source: name-clone-scoped-recurring-scripts-among-the-scru; coga-dev/testing Known suite failures).
- Reference-pin PR: https://github.com/FastJVM/coga/pull/1282 — "Pin links to deleted tickets" (source: v1/01-urgent-…; removes the v1/README Urgent row, finding F6).
- Direct-deleted on main (no durable knowledge / already covered): decide-the-two-open-questions-left-by-the-checkout, update-the-testing-topic-known-failure-note-on-the, fix-the-readme-windows-walk-findings-left-unowned, maintain-ticket-blackboards, decide-where-the-google-helper-skills-read-their-c, stop-megalaunch-when-an-agent-fails-to-start (E1 already covered on main), recurring/address-pr-comments, recurring/blackboard-size, recurring/blocker-reminders.
- Local-only period tickets (phone-home, resolve-conflicts, skill-update, trim-log, usage-report): classified no durable knowledge; left for the recurring scanner's next-firing delete.
- Retirement debt (not taken by Phase 4): done+checkout refresh-the-v1-microkernel-task-readmes-after-the, make-retro-check-inbound-doc-links-before-deleting; all canceled tickets.

## Dream Skill: cleanup-orphan-markers

Generated: 2026-11-23T23:08:07+00:00
Task: `recurring/dream`

Result: no-op. No cleanup-eligible processed done tickets still have task directories.

## Dream Run Summary

Generated: 2026-11-23T23:20Z · run 20261123T224856Z · period 2026-W48 by date (no `created recurring/dream for …` ledger line exists for this run; it was launched directly at 14:48) · repo-identity: coga-source · checkout: PR #1280 feature branch.

| Phase | Result |
| --- | --- |
| preflight | ok (git-common-dir, remote, gh) |
| 1 validate-drift | reported — 107 human-needed (0 direct-fix, 0 PR proposal) |
| 2 knowledge-scan | reported — 17/17 shards, 29 raw findings |
| 3 contract-audit | reported — 9/9 shards, 20 raw findings; ownership check clean |
| 4 retro/done-ticket | pr-opened — 2 PRs, 9 direct deletes (verified on origin/main da2da0630), 5 local-only classified none |
| 5 cleanup-orphan-markers | no-op |
| 6 disposition | pr-opened 1, proposed 5 drafts, upstream-captured 0 |

Findings: 49 raw → 38 merged. 10 valid on main (F1–F10), 4 extract (E1 already covered on main; E2–E4 canceled), 24 branch-only residue of the unmerged plain-Git migration (B1–B24; the docs are accurate on main today).

PRs opened (pr-required; none auto-merged):
- https://github.com/FastJVM/coga/pull/1281 — New context: the terminal-backstop PTY test can fail once under full-suite load (Retro, source name-clone-scoped-…)
- https://github.com/FastJVM/coga/pull/1282 — Pin links to deleted tickets (Retro; v1/01 row, F6)
- https://github.com/FastJVM/coga/pull/1283 — Retire stale task-group README guidance (F4, F5)

Draft tickets created:
- `fix-stale-doc-references-left-by-the-plain-git-mig` (code/with-review) — B1–B24; overlaps PR #1279/#1280, owner v1/03.
- `correct-three-stale-doc-claims-that-pr-1279-also-e` (code/with-review) — F1 knowledge Retro-inbound claim, F2 microkernel slug, F3 current-direction freshness link; files overlap PR #1279.
- `move-the-assembler-trial-evidence-out-of-the-shipp` (code/with-review) — gap F7.
- `validate-drift-obsolete-key-frozen-workflow-steps` (brief-for-human) — `validate-drift: obsolete-key`, 97 issues / 20 tickets (branch validator only).
- `validate-drift-large-blackboard-v1-03-blackboard-o` (brief-for-human) — `validate-drift: large-blackboard`, v1/03 at 45.3 KiB.

Already ticketed:
- `validate-drift: unfrozen-workflow` (5 members, 0 new) as `validate-drift-unfrozen-workflow-canceled-tickets`.
- `validate-drift: stuck-in-progress` (4 members; new since filing: marketing/research-how-agents-make-delegated-decisions-geo, validate-drift-stuck-in-progress-in-progress-ticke, validate-drift-unfrozen-workflow-canceled-tickets, warn-when-coga-delete-or-coga-retire-leaves-a-live) as `validate-drift-stuck-in-progress-in-progress-ticke`.
- F8 releasing twine/3.11 caution as `v1/14-publish-coga-1-0-as-the-final-v1-step`.
- F9 windows-aws walk/gotchas as `fix-the-windows-aws-walk-step-and-add-the-v1-14-at` (PR #1276); symlink caveat as `v1/07-wire-agent-skills-on-windows-without-symlink-pr`.
- F10 Google helper-path recipe as `fix-the-google-skills-dead-helper-invocation-paths` (PR #1277).

Already-decided classes: none. Machine-local validator issues: none. Upstream entries appended to coga/upstream-coga.md: 0 (Coga source repo).

Retirement debt (human `coga retire <slug>`):
- done+checkout: refresh-the-v1-microkernel-task-readmes-after-the (local branch `refresh-v1-microkernel-readmes-after-retro`), make-retro-check-inbound-doc-links-before-deleting (branch live locally and on origin).
- canceled (37), with the extract findings their retirement unlocks: open-prs-only-when-ready-to-merge-and-needing-huma (E2: decision not to add early/draft-PR guidance → coga/pr-publication); stop-creating-linked-worktrees-for-coga-retire (E3: Retro's isolated worktree is an accepted exception → retro/done-ticket); marketing/fix-installer/add-gemini-as-an-agent-coga-can-drive (E4: verified Gemini CLI 0.66.0 limits + decision not to act → coga-dev/internals/agent-config). Others: adjudicate-the-eight-premise-dead-v2-drafts, close-the-presence-not-freshness-hole-in-the-branc, codex-doesn-t-exist-properly-for-agent-restart, decide-the-fate-of-the-multiply-probe-harness-work, define-the-api-equivalent-cost-proxy-and-price-tab, define-the-split-a-ticket-mechanic-shared-by-code, detect-stranded-blackboard-prose-across-checkouts, digest-can-clobber-recurring-last-serviced-period, don-t-recurr-for-inactive-repo, don-t-recurr-for-inactive-repo-2, dream-shouldn-t-touch-coga-in-coga-enabled-repo, fix-git-sync-failure, for-v1-complete-thinkpick-project, implement-the-include-allowlist-that-url-skill-upd, interview-the-owner-on-the-17-title-only-v2-stubs, nightly-auto-drain-run-for-ready-tickets, no-durable-runbook-covers-running-coga-headless, nothing-exercises-python-3-11-the-declared-floor, parse-agents-rejects-cogalocaltoml, phase-0-audit-is-complete-per-the-plan-but-still-i, premise-check-2026-w39-25-parked-drafts-need-a-ver, premise-check-2026-w40-8-parked-drafts-need-a-verd, recurring-scan-aborts-on-an-unloadable-workflow, retire-canceled-tickets-without-retro, scrub-the-service-account-token-from-the-launch-ch, ship-a-shared-recurring-reminder-engine-battery, some-recurring-tasks-are-not-launched-correctly-to, stop-with-all-the-worktreees-its-super-noisy-and-u, stop-with-all-the-worktreees-its-super-noisy-and-u-2, tell-agents-never-to-git-commit-coga-task-and-log, ticket-sync-fails-with-read-only-git-inside-agent, triage-the-v2-parking-area-empty-descriptions-prem, validate-drift-large-blackboard-live-ticket-blackb, validate-drift-unsynthesized-draft-blackboard-four.

Human-needed / review gates:
- Review PRs #1281, #1282, #1283. #1282 and the 9 direct deletes touch files that PR #1280/#1279 also edit (the three recurring period tickets lose a line on that branch → modify/delete conflicts to resolve in favor of deletion).
- Local-only done period tickets in this checkout (recurring/phone-home, resolve-conflicts, skill-update, trim-log, usage-report) carry nothing durable; left for the recurring scanner's next-firing delete.
- Scan dirs removed (both phases complete). No stranded Retro work.
