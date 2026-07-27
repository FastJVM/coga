---
slug: recurring/dream
title: Dream
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/period-task
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
script: null
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
acted on and the result count when available. If a phase is skipped, say why.
The blackboard remains the durable record; console progress is for the human
watching the run.

### Run order

Dream runs six phases in order. Phases 1–3 **decide** — they read the repo and
record what to change. Phases 4–6 **execute** — they make the changes. Deciding
before executing is deliberate: the knowledge scan and contract audit read the
corpus while every done ticket still exists (Phase 4 deletes them all), so
nothing is missed, and their findings steer the Retro pass.

1. **validate-drift** — deterministic repo hygiene (registered recipe).
2. **knowledge scan** — one full-corpus read; classifies every finding.
3. **contract audit** — checks the contract surface against code reality.
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
directly to this task's blackboard. Do not create child script tasks.

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

### Phase 2 — knowledge scan

Delegate this phase to a subagent using the
`bootstrap/dream/scan/knowledge-scan` skill. This decide-half scan happens
before Phase 4 so done-ticket evidence is still available.

Write the returned findings to this task's blackboard under `## Findings`;
Phase 4 reads that section when batching knowledge PRs.

### Phase 3 — contract audit

Delegate this phase to a subagent using the
`bootstrap/dream/scan/contract-audit` skill. This decide-half audit complements
Phase 1's deterministic repo-hygiene check.

Write the returned findings to this task's blackboard under `## Findings`,
alongside the Phase 2 findings; Phase 6 reads that section when routing
proposal PRs.

### Phase 4 — retro/done-ticket

Extract durable knowledge from done tickets, then delete every one of them.
This pass processes **every eligible done ticket in a single run** — there is
no per-run ticket cap and nothing is deferred to a later run. One corpus read
with one running delta across all tickets is both cheaper than repeated capped
runs and better at de-duplicating repeated facts.

A done ticket is eligible when:

- its resolved task directory under `coga/tasks/` still exists; and
- no open PR is adding its `## Retro` marker or deleting that resolved task
  directory.

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

A done `recurring/<name>` ticket from this sweep is eligible like any other.
Period tickets carry nothing durable (their output is the notification post or
PR they already produced), so Retro direct-deletes them via `coga delete
recurring/<name>` — no PR or marker — while leaving the recurring template's
`last_serviced_period` untouched. If a completed period ticket survives into a
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
gates deletion through `bootstrap/delete-task`. That delete skill ships, but
until its cleanup PR-dispatch wiring is finished the recipe reports
`human-needed` and deletes nothing.

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
`no-op`, `reported`, `proposed`, `direct-fixed`, `pr-opened`, `human-needed`,
the finding counts with one-line summaries, links to every PR opened and draft
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

Generated: 2026-07-27T21:37:11+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python -m coga.validate --json --fix`
Task: `recurring/dream`

Applied fixes: 1.

- `v2/coga-recurring-ack`: `blackboard-fence` - added blackboard fence + region (`/home/n/Code/claude/coga/coga/tasks/v2/coga-recurring-ack.md`)

Result: 24 issue(s): 0 direct fix, 0 PR proposal, 24 human-needed.

### Human Needed

- `important-alerts-the-task-owner-drop-important-rec`: `stuck-in-progress` (warn) - in_progress but idle for 240.2h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `recurring-bugs/dream-recipes-write-reports-into-packaged-bootstra`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `retire-coga-important-support-second-webhook`: `stuck-in-progress` (warn) - in_progress but idle for 267.2h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `rewrite-coga-base-prompt-and-agent-mode-block`: `unfrozen-workflow` (warn) - workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/acceptance-criteria`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/autotrigger-ticket-type`: `missing-step` (error) - `workflow:` is set but `step:` is missing
  Remediation: The ticket's current `step:` is not in its frozen workflow. Lifecycle correction is human-only; ask the owner to relaunch, rewind, or hand-edit the step.
- `v2/autotrigger-ticket-type`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Unknown validator issue kind. Ask a human before changing repo state.
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
- `v2/document-contexts-as-prompt-payload-not-tags-princ`: `stuck-in-progress` (warn) - in_progress but idle for 144.4h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.
- `v2/fix-windows-cli-import-crash`: `unfrozen-workflow` (warn) - workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/identify-blocking-issues`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/issue-inbox-slack`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/measure-relay-prompt-scope-and-agent-precision`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (non-placeholder blackboard is 4213 characters); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Unknown validator issue kind. Ask a human before changing repo state.
- `v2/relay-design-repositories`: `unknown-assignee` (warn) - assignee 'nicktoper' is neither a known agent type nor one of this ticket's role-field values
  Remediation: Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next.
- `v2/split-context-to-doc-user-accessible-and-editable`: `missing-step` (error) - `workflow:` is set but `step:` is missing
  Remediation: The ticket's current `step:` is not in its frozen workflow. Lifecycle correction is human-only; ask the owner to relaunch, rewind, or hand-edit the step.
- `v2/split-context-to-doc-user-accessible-and-editable`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Unknown validator issue kind. Ask a human before changing repo state.
- `v2/use-worktree-when-starting-a-dev-task`: `missing-step` (error) - `workflow:` is set but `step:` is missing
  Remediation: The ticket's current `step:` is not in its frozen workflow. Lifecycle correction is human-only; ask the owner to relaunch, rewind, or hand-edit the step.
- `v2/use-worktree-when-starting-a-dev-task`: `unsynthesized-draft-blackboard` (error) - draft blackboard has pre-launch authoring notes (authoring section(s): ## Evaluator review); synthesize durable content into the ticket body or move intentional launch notes under `## Production notes` before activation
  Remediation: Unknown validator issue kind. Ask a human before changing repo state.
- `write-real-coga-documentation-command-reference-gu`: `stuck-in-progress` (warn) - in_progress but idle for 192.7h
  Remediation: Ask the owner whether the task should be relaunched, blocked, paused, or bumped. The skill should not change lifecycle state silently.

## Findings

Phase 2 (knowledge scan) and Phase 3 (contract audit) findings. Phase 4 batches
the `extract` findings into knowledge PRs; Phase 6 routes `stale`, `drift`, and
`gap`.

### Phase 2 — knowledge scan (14 findings: 5 extract, 7 stale, 2 gap)

#### `extract` — grouped by target area

**Area: `coga/codebase`**

**F1. A design step's "zero drift / rebases clean" claim expires; re-verify at implement time** — class `extract`; target `coga/contexts/coga/codebase/SKILL.md` (+ packaged twin); source ticket `agree-the-core-vs-skills-move-list-then-execute`.
The design step measured merge-base drift and recorded "rebases onto main with no conflicts expected" as settled fact. By implement time `main` had advanced 417 commits with real overlap; the rebase took four conflicts. The durable lesson is the two gaps auto-merge could not close, both about git renames vs. fresh copies: (a) `main`'s `TERMINAL_STATUSES` fix reached the *live* skill copy through a rename auto-merge, but the *packaged* copy was created fresh in the same move commit and silently kept the old `== "done"` test — a regression that would have deleted branches recorded on canceled tickets; (b) a new-on-main test imported a symbol the branch had moved. Rule: when a branch relocates code, git history follows only the renamed path, so a second copy created fresh in that commit never receives `main`'s later fixes. Re-diff every live↔packaged pair by hand after a rebase, and treat a design-step drift measurement as a snapshot, never a precondition.

**F2. Test fixtures must not depend on GNU-only shell flags** — class `extract`; target `coga/contexts/coga/codebase/SKILL.md` (+ packaged twin); source ticket `ship-a-shared-recurring-reminder-engine-battery` (canceled).
`tests/test_launch_script.py::test_script_launch_preserves_cancellation_made_by_script` fails on macOS because its fixture script uses GNU-only `sed -i` (`sed: invalid command code v`). Triaged as "pre-existing, unrelated" — the same recurring verification tax the context already names one bullet above, arriving through a different cause. Belongs beside the "Tests must not pin to live dogfooded state" bullet.

**Area: `coga/sync`**

**F3. Calming a known-benign git failure: gate on the up-front-detectable cause, and skip only the remote step** — class `extract`; target `coga/contexts/coga/sync/SKILL.md` (+ packaged twin); source ticket `install/short-notice-instead-of-raw-git-error-when-sync-ha`.
Three findings about where fail-loud may be relaxed. (a) Calm only the case positively detectable *before* the operation (`git remote get-url` non-zero); a configured-but-unreachable remote is not knowable up front and must stay loud. (b) The obvious implementation — copying the sibling `_control_branch_present` early-return — is too broad: it also suppressed the feature-branch *local* commit, which never contacts the remote; a launch-script test caught it (script aborted, exit 7, dirty tree). Correct scope is "commit always, skip only the push." (c) Peer review found that early-return had also dropped the state-regression guard on the false rationale that "with no remote there is nothing for a stale checkout to bury" — a sibling worktree lands state on the *shared local* control branch with no remote involved, and a stale `in_progress` copy buried a terminal `done` ticket. The guard must resolve its base locally (`refs/heads/<control>`) instead of fetching the remote tip.

**Area: `code/open-pr` skill**

**F4. `coga open-pr` refuses when the primary control checkout is parked on another ticket's branch** — class `extract`; target `coga/skills/code/open-pr/SKILL.md` + packaged twin; source tickets `remove-run-py/add-coga-run-generic-runner-and-migrate-recurring` and `ship-a-shared-recurring-reminder-engine-battery`.
Hit twice on the same day. First: `coga open-pr` refused because the primary checkout sat on an unrelated ticket's branch carrying uncommitted drift; remedy was stash → move to `main` → open-pr → restore. Second: it could not run at all and the PR was opened by hand. The skill tells the agent to return to the primary control checkout but assumes it is on the control branch — it never says what to do when a *sibling ticket* owns it. Recurs in a multi-worktree dogfooding repo.

**Area: `coga/recurring`**

**F5. An agent-delegating recurring wrapper needs a pty, and its own stdout is not a success signal** — class `extract`; target `coga/contexts/coga/recurring/SKILL.md` `## Gotchas`; source done period task `recurring/resolve-conflicts`.
Two operational facts from the 2026-07-27 run exist nowhere else: (a) `coga launch` refuses an agent launch without a TTY on *both* stdin and stdout, and an agent's tool shell supplies neither — the delegation must run under `script -qec` bounded with `timeout`; (b) the delegated launch is torn down by the done sentinel seconds after it posts its roll-up and the captured pty output is ANSI noise, so the wrapper's stdout is not a usable success signal — confirm through the `slack:` line for `bootstrap/<verb>` in `coga/log.md`. The agent in that run first mis-read the teardown as a premature kill and had to correct itself.

#### `stale`

**F6. `coga/architecture` still describes Dream as orchestrating child script tasks** — class `stale`; target `coga/contexts/coga/architecture/SKILL.md` and `src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md` (byte-identical; both must change).
Line ~139: "The parent task orchestrates child script tasks over worker skills." Line ~704: "Each known script skill writes its own `## Dream Skill: <name>` section to its child task blackboard." PR #650 removed child script tasks entirely — Dream phases 1 and 5 invoke `coga run …` directly from the parent and the recipes inherit the parent's `COGA_TASK_*`. Lines ~656–661 of the same file already say this correctly, so the file contradicts itself.

**F7. `coga/patterns` describes the spool consumer as a script step** — class `stale`; target `coga/contexts/coga/patterns/SKILL.md` line ~75 + packaged twin.
"A script step runs a skill whose `script:` reads unconsumed records, acts on them, drains the spool, and exits." The canonical instance it names — the daily digest — is now a registered recipe: the template declares `recipe: digest`, the runner executes `coga run digest` headlessly, and `coga/skills/coga/digest/flush/SKILL.md` carries no `script:`.

**F8. `coga/principles` receipt #2 names a `mode:` field that no longer exists** — class `stale`; target `coga/contexts/coga/principles/SKILL.md` line ~64 + packaged twin.
"the two modes — `agent` for agent judgment and `script` for deterministic Python — route work to the right substance." `coga/architecture` states flatly that there is no `mode:` ticket field, and there are now three substances, not two. This is a packaged canonical context shipped to every repo, so the wrong vocabulary propagates.

**F9. The live `code/implement` skill override is 26 lines behind its packaged twin** — class `stale`; target `coga/skills/code/implement/SKILL.md`.
The packaged copy gained a "Read-only Git fallback" section (independent `git clone --no-hardlinks` under `/tmp` when `git worktree add` fails on a read-only `.git`, repoint origin, record as `worktree:`, escalate with a specific capability) plus an updated Definition-of-Done line. The live copy has neither. Skill resolution is local-first, so this repo's agents load the stale version and never learn the fallback. Every other live/packaged skill pair in the repo is byte-identical; this is the only diverged one.

**F10. The `rebase-stale-worktrees` recurring template outlived its replacement and still fires** — class `stale`; target `coga/recurring/rebase-stale-worktrees/` (delete) + `coga/contexts/coga/recurring/SKILL.md` `## Gotchas`.
PR #633 shipped `resolve-conflicts` as the deliberate replacement and deleted the packaged template; the live copy was never removed. Both carry `schedule: "0 8 * * 1"` — the same slot — and the replacement's body reads "The **removed** `rebase-stale-worktrees` task…". Not dormant: `coga/log.md` shows it created and launched at 2026-07-27 14:22, running a full six-minute agent session immediately before `resolve-conflicts` ran the same slot. Also the first real instance of the gap parked as v2 draft `document-recurring-template-live-vs-packaged-sync`.

**F11. The packaged `digest` recurring template ships a hardcoded personal owner** — class `stale`; target `src/coga/resources/templates/coga/recurring/digest/ticket.md`.
Ships `owner: nick` / `assignee: claude` in the wheel — the only recurring template with either field set. Every repo that installs Coga and enables the digest gets a period task owned by a person who is not its operator, driving Slack owner mentions and megalaunch's operator filter. The documented contract is that `assignee` defaults to the repo's configured default agent and the owner comes from repo config when the template omits it, so drop both lines rather than parameterize.

**F12. Two v2 drafts are premise-dead and would generate wrong work** — class `stale`; target `coga/tasks/v2/document-parent-orchestrates-child-script-tasks-pa.md`, `coga/tasks/v2/document-interactive-recurring-sweep-hazard-in-rel.md`.
Both are prior Dream gap findings whose subject no longer exists. The first asks to document child `mode: script` tasks as the canonical housekeeping pattern — the exact shape PR #650 deleted. The second is entirely about the `mode:` frontmatter field; the field is gone and `coga/recurring` now documents the surviving true constraint. Anyone picking either up would write prose describing a removed design.

#### `gap`

**F13. The pytest autouse guard does not scrub `COGA_TASK_*`, so fixture reports were written into four live ticket blackboards** — class `gap`; target `tests/conftest.py` (`_clear_supervised_session_env`); needs a tracked ticket.
Twenty-plus `## Dream Skill: validate-drift` sections are appended across four live tickets (`make-sure-we-can-drop-new-recurring-tickets` ×9, `install/short-notice-…` ×4, `agree-the-core-vs-skills-move-list-then-execute` ×2, `ship-a-shared-recurring-reminder-engine-battery` ×3), each reporting `` `x`: `missing-file` - created log.md `` and ``committed and pushed `repair-branch` ``. There is no task `x`, Coga has no per-task `log.md` (`validate.py:361`), and `--fix` classifies `missing-file` as `human-needed` and creates nothing. That text is verbatim test-fixture data from `tests/test_dream_validate_drift.py:341–352` and `:322`: a pytest run inside a `coga launch` session inherited `COGA_TASK_BLACKBOARD` and the recipe under test appended its fixture report to the live outer ticket. `coga/codebase` already prescribes the remedy — "Clear every launch-owned metadata variable in the autouse environment guard" — but the guard clears only `COGA_DONE_SENTINEL`, `COGA_SUPERVISED`, `COGA_EXPECTED_TASK`, `COGA_EXPECTED_STEP`. `COGA_TASK_*` is absent and only 2 of 10 tests in that module opt out per-test. Needs: the full `COGA_TASK_*` / `COGA_SKILL_*` / `COGA_REPO_ROOT` / `COGA_COGA_OS_ROOT` set added to the autouse guard with a regression test; a defence-in-depth check that a report writer refuses a blackboard path outside `coga/tasks/`; and removal of the polluted sections from surviving non-done tickets. Related: `recurring-bugs/dream-recipes-write-reports-into-packaged-bootstra` flags this as its loose end #2 and asks for it to be split out.

**F14. Nothing retires a finished ticket's linked worktree, so branch-sweep can never delete those branches** — class `gap`; target needs a tracked ticket; knowledge home `coga/contexts/dev/code/SKILL.md` `## Checkout boundary`.
`dev/code` tells every code ticket to create a feature worktree and record it under `## Dev`, but nothing removes it — Coga never runs `git worktree remove`. `branchsweep.sweep_branches` skips only `_current_branch(root)`, so a branch held by a *linked* worktree is not recognized as live and falls through to `delete_local_branch`, where `git branch -d/-D` refuses ("checked out at …"); the failure is noted and the sweep still exits 0. This repo carries 17 worktrees and 25 non-main branches, and the 2026-07-27 `rebase-stale-worktrees` run reported "17 live branches, all stale, 16 already-merged squash residue" one hour after `branch-sweep` ran clean and exited 0.

### Phase 3 — contract audit (11 findings, all `drift`)

Spot-verified against source before recording: `src/coga/commands/open_pr.py` and
`src/coga/open_pr.py` are both absent; `DEFAULT_ALIASES` ships eight entries
including `open-pr` and `resolve-conflicts`; `important_recipient` appears only in
`config.py` (no notification consumer); no `automerge` command is registered;
`coga/contexts/dev/code/SKILL.md` is missing the packaged copy's 8-line read-only-Git
paragraph; `coga/bootstrap/resolve-conflicts/ticket.md` exists; the live
`coga/recurring/rebase-stale-worktrees/` has no packaged twin.

**D1. `coga/codebase` points `open-pr` at two source files that do not exist** — target `coga/contexts/coga/codebase/SKILL.md:57-58` (with `:87-90`).
The microkernel rule cites `coga open-pr` as an in-core command implementation ("`commands/open_pr.py` → `open_pr.py`") and line 88 asserts "PR #585 later turned `open-pr` into a real command implementation, so the same test now places it in core under exception 2." Neither file exists. PR #625 deleted both and moved the implementation to the packaged command ticket `src/coga/resources/templates/coga/bootstrap/open-pr/{ticket.md,run.py,recipe.py}`, fronted by `src/coga/aliases.py:66`. Source of truth: `src/coga/aliases.py:59-68` plus the absent files. Also contradicted inside the repo by `coga/contexts/coga/extension-model/SKILL.md` and `docs/reference.md:229-232`.

**D2. `CLAUDE.md` / `AGENTS.md` microkernel rule names `coga open-pr` as core Python** — target `CLAUDE.md:19` and `AGENTS.md:19` (byte-identical).
Both list "commands such as `coga digest`, `coga megalaunch`, and `coga open-pr`" as the second admissible kind of code in `src/coga/`. Two lines later the same section states the actual rule — "a launch-target command is an argv rewrite in `[aliases]`… not a Typer command with logic" — which is exactly what `open-pr` now is. `digest` and `megalaunch` remain correct examples. The example makes the instruction file argue against its own rule.

**D3. The bundled `coga/cli` command reference still documents the retired `coga automerge`** — target `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md:431-449` and `:995-996`.
Carries a full `## coga automerge` section and recommends it under "Catching up tickets after a teammate merged a PR". No such command exists — `BUILTIN_COMMANDS`, `DEFAULT_ALIASES`, and `cli.py:86-114` register none; the behavior lives only in the `autoclose` recipe, and `docs/cli-extension-audit.md:155` records the retirement. `coga/architecture/SKILL.md:622` names this file as "the command reference", so agents are handed a command that exits 2. The same section is also missing entries for `coga digest`, `coga usage`, `coga open-pr`, `coga resolve-conflicts`. Scope note: no live twin — sits in the package-backed blind spot `architecture/SKILL.md:673-676` already flags.

**D4. `important_recipient` is documented as active triage routing but nothing consumes it** — target `docs/operations.md:58-59` (same claim in `coga/coga.toml:62-68` and `src/coga/resources/templates/coga/coga.toml:83-89`).
The key is parsed (`config.py:95,816,919-940` → `Config.slack_important_recipient`) and never read again; `notification/slack.py` never substitutes it, so an `--important` post still mentions the ticket owner. The repo already knows this — `coga/contexts/coga/sync/SKILL.md:249-252` and `coga/contexts/coga/important/SKILL.md:31-37` both say not to treat the key as active routing until the wiring lands. The docs and config comments are the half that never got updated.

**D5. Live/packaged copy pair diverged: `dev/code` is missing the read-only-Git fallback** — target `coga/contexts/dev/code/SKILL.md:26`.
PR #597 added the read-only-`.git` sandbox fallback to the packaged copy only; the live copy is missing that 8-line paragraph. Context resolution is local-first, so this repo's agents load the stale text while fresh installs get the current one — the exact failure `CLAUDE.md:23` and `docs/development.md:84-88` warn about. Every other live/packaged context pair is byte-identical. Source of truth: the packaged copy and commit `6e848921`. **Shares a root commit with F9 (`coga/skills/code/implement/SKILL.md`) — repair both in one PR.**

**D6. `docs/development.md` claims the repo carries no `coga/bootstrap/` dogfood copy** — target `docs/development.md:93-94`.
States "`coga init` deliberately skips `bootstrap/`, and this repo carries no `coga/bootstrap/` dogfood copy." True after PR #526, but PR #633 re-added `coga/bootstrap/resolve-conflicts/ticket.md`, currently byte-identical to its packaged counterpart and shadowing it through the local-first `resolve_bootstrap` path (`tasks.py:302-312`). So a second copy does exist and must be kept in sync — and it is precisely the un-annotated mirror `coga/contexts/coga/codebase/SKILL.md:135-145` says not to create. Source of truth: the file on disk plus commit `c11b162c`.

**D7. `docs/cli-extension-audit.md` calls `digest/post` and `autoclose-merged/sweep` script steps** — target `docs/cli-extension-audit.md:143` and `:180`.
Neither is a script step any more. Both recurring templates declare `recipe:`, the recurring runner dispatches them through `coga run` (`runner.RECIPES`: `digest` → `run_digest_recipe`, `autoclose` → `run_autoclose_recipe`), and both workflow bodies open with "Recipe-backed recurring task." Their skills carry no `script:` frontmatter, so `current_step_is_script` cannot select them. The doc's central argument still holds; the mechanism it cites as evidence has changed.

**D8. `docs/reference.md` alias table lists two aliases no install ships** — target `docs/reference.md:375-390`.
The table includes `coga claude` and `coga codex`. Neither is available in a fresh repo: `DEFAULT_ALIASES` ships exactly eight (`chat`, `dream`, `build`, `skill-update`, `autoclose`, `pick`, `open-pr`, `resolve-conflicts`) and the packaged `coga.toml` ships `claude`/`codex` commented out. They exist only in this repo's dogfood `coga/coga.toml`. The framing is also inverted: the packaged `coga.toml` defines only `chat`, `build`, `pick`, `dream`; the other four come from Python defaults, so a reader opening `coga.toml` will not find most of the listed aliases.

**D9. The bundled `coga/cli` alias section lists 4 of the 8 shipped default aliases** — target `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md:935-955`.
States "`chat`, `build`, `dream`, and `pick` are also registered as built-in default aliases". `DEFAULT_ALIASES` now registers eight; the four omitted (`skill-update`, `autoclose`, `open-pr`, `resolve-conflicts`) are exactly the ones a reader could not discover from `coga.toml`. `docs/cli-extension-audit.md:172` already records "**`DEFAULT_ALIASES` ships eight**", so the two contract surfaces disagree. Same package-backed scope caveat as D3.

**D10. `current-direction` names the playbook-rename ticket by a slug that no longer resolves** — target `coga/contexts/coga/current-direction/SKILL.md:50-51`.
Says "Ticket: `rename-workflow-primitive-to-playbook` (draft, `code/design-then-implement`)". The ticket moved to `coga/tasks/v2/` and its frontmatter records `slug: v2/rename-workflow-primitive-to-playbook`. `tasks.py:272-299` resolves against the path-qualified `id_slug` ("A nested task's bare leaf does not resolve"), so `coga show rename-workflow-primitive-to-playbook` fails. The move also changes the implied status — `coga/contexts/coga/roadmap/SKILL.md` defines `coga/tasks/v2/` as "the durable parking area for work not on the current execution path", while current-direction presents the rename as live direction.

**D11. Broken cross-reference anchor in `docs/operations.md`** — target `docs/operations.md:27`.
The link `[reference](reference.md#coga-slack---task-task---message-text)` matches no heading. The target heading at `docs/reference.md:327` generates `#coga-slack---task-target---message-text` — the link says `task` where the heading says `TARGET`. Minor, but a dead reference on the main operations page.

**Audit coverage (checked clean, no finding):** all `coga run` recipe names against `runner.RECIPES`; every documented flag on `init`/`create`/`ticket`/`project`/`launch`/`megalaunch`/`mark`/`bump`/`block`/`unblock`/`status`/`show`/`validate`/`usage`/`slack`/`digest`/`delete`/`retire`/`skill`/`secret`/`recurring` against the Typer signatures; `mark` transition tables against `commands/mark.py:44-47`; status values against `lifecycle.VALID_STATUSES`; the `COGA_TASK_*` set against `task_env.py`; symbol references into `spool.py`, `git.py`, `views.py`, `usage.py`, `authoring.py`, `autoclose.py`, `branchsweep.py`; the `validate-drift` flag list against `dream_validate_drift.py:528-563`; the bundled workflow inventory; and the remaining ~20 live/packaged file pairs.

## Phase 4 — retro/done-ticket

All 13 eligible done tickets processed in one delegated run inside an isolated
linked worktree (`dream-retro-2026-W31`, based on a freshly fetched `origin/main`).
Corpus loaded once, one running delta across the whole run, partitioned into 5
coherent PR batches. No "Stop and ask" gate tripped. Per-PR limits respected
throughout (max 1 source ticket of 5 allowed; max 2 knowledge files of 3; 0 new
context/skill files of 1; one theme each).

### Knowledge PRs (5) — all `pr-required`, unmerged, MERGEABLE/CLEAN

- **#654** https://github.com/FastJVM/coga/pull/654 — *New context: rebases silently skip a freshly created live/packaged twin*. Theme: traps when editing Coga's own code that report success while leaving the repo wrong. Edits `coga/contexts/coga/codebase/SKILL.md`. Deletes `agree-the-core-vs-skills-move-list-then-execute`. Carries F1 (rename-vs-fresh-copy rebase trap, the `TERMINAL_STATUSES` near-regression, re-diff every pair by hand), F1's second half (a recorded "rebases clean" expires — 417 commits, four conflicts), and F2 (portable fixture shell scripts). F2 was verified against the current tree at `tests/test_launch_script.py:211`; its canceled source ticket `ship-a-shared-recurring-reminder-engine-battery` was correctly left untouched.
- **#655** https://github.com/FastJVM/coga/pull/655 — *New context: no configured remote is a sync soft-skip that still commits locally*. Theme: where fail-loud may be relaxed in the git sync layer. Edits `coga/contexts/coga/sync/SKILL.md` + packaged twin. Deletes `install/short-notice-instead-of-raw-git-error-when-sync-ha`. Carries all three parts of F3. Also corrects a stale claim in the same file: "no remote" was listed among the *loud* non-fatal sync misses; it is now the calm path, so the entry now reads "a configured-but-unreachable remote".
- **#656** https://github.com/FastJVM/coga/pull/656 — *New skill: coga open-pr refuses a control checkout parked on another ticket's branch*. Edits `coga/skills/code/open-pr/SKILL.md` + packaged twin. Deletes `remove-run-py/add-coga-run-generic-runner-and-migrate-recurring`. Carries F4 in step 2 of `## Order of operations` plus a one-liner in `## If coga open-pr fails`.
- **#657** https://github.com/FastJVM/coga/pull/657 — *New context: recurring wrappers that delegate to an agent command need a pty*. Edits `coga/contexts/coga/recurring/SKILL.md`. Deletes `recurring/resolve-conflicts`. Carries F5 in `## Gotchas`. **Also amends `## Dream is the recurring janitor`**, which asserted flatly that period tasks "carry nothing durable" — this ticket is the counterexample and would have been deleted unread on that rule. Text now says *normally* and tells Retro to read the blackboard rather than direct-delete on class alone. **Reviewers: this edits the Dream contract itself.**
- **#658** https://github.com/FastJVM/coga/pull/658 — *New skill: fall back to a direct branch-diff review when /code-review cannot be invoked*. Edits `coga/skills/code/self-qa/SKILL.md` + packaged twin. **Deletes no source ticket, deliberately** — its source (`install/short-notice-…`) is deleted in #655; bundling an unrelated skill edit there would have broken PR coherence. Not one of the F1–F5 priors; found by Retro's own corpus read. Records that `/code-review` is user-invocation-only in this harness (a launched agent cannot trigger it) and that a green suite is not the review step — two tickets shipped full-green `pytest` and still had must-fix bugs, because the defect was in a rationale no test asserted on.

**Correction to the F1/F2/F5 priors:** `coga/contexts/coga/codebase/SKILL.md` and
`coga/contexts/coga/recurring/SKILL.md` have **no packaged twin** — the packaged
`bootstrap/contexts/coga/` set is only architecture, cli, important, patterns,
period-task, principles, sync. #654 and #657 are single-copy edits by design.

### Direct-deleted — no PR, no `## Retro` marker (9)

Six period tickets carrying nothing durable: `recurring/autoclose-merged`,
`recurring/blocker-reminders`, `recurring/branch-sweep`, `recurring/digest`,
`recurring/rebase-stale-worktrees`, `recurring/skill-update`.

Three non-recurring tickets whose knowledge was already covered:
`dream-cleanup-orphan-markers-w30` (a no-op cleanup report);
`stop-trimming-blackboard-but-refuse-to-launch-befo` (the first-launch
blackboard-synthesis guard is already in `coga/contexts/coga/architecture/SKILL.md`);
`make-sure-we-can-drop-new-recurring-tickets` (`coga/contexts/coga/recurring/SKILL.md`
already documents the promote flow, frontmatter transform, refusals, and static
schedule validation — its one residual contribution rode into #658).

### Verification (independent, by this Dream run)

- All 5 PR branches confirmed pushed and present on `origin`.
- All 9 direct deletes confirmed absent from `origin/main` via `git cat-file -e`.
- No recurring template `ticket.md` changed between the pre-run tip and `origin/main`;
  `last_serviced_period: 2026-W31` intact. (The one `coga/recurring/` diff is a
  `digest/spool.md` append from a concurrent session, not Retro.)
- Isolated worktree clean; copied `coga.local.toml` removed; worktree removed;
  temp branch `dream-retro-2026-W31` deleted; evidence snapshot deleted.
- Primary checkout never mutated by the Retro run.

### Concurrency note

`origin/main` advanced past the `1ea51aa6` base before and during the run (other
Coga sessions landing state commits). None of those commits touched the 13 slugs
or the 5 knowledge files, so each PR was branched off the then-current
`origin/main` rather than the stale base. All five PR bases are current.

Separately: the primary checkout's staged `coga/tasks/` → `coga/tasks/v2/` renames
that were present at Dream's session start were **committed** by a concurrent
session (`bce4e209 Reassign remaining v1 tickets to codex`), not lost. The local
`main` ref is now 9 commits behind `origin/main` — that is the expected result of
`--keep-control-checkout`; refreshing it is the operator's call.

## Dream Skill: cleanup-orphan-markers

Generated: 2026-07-27T22:15:59+00:00
Task: `recurring/dream`

Result: no-op. No cleanup-eligible processed done tickets still have task directories.

## Phase 6 — disposition

Every Phase 2 and Phase 3 finding routed to a durable home. 5 `extract` handled
by Phase 4; 7 `stale` + 11 `drift` → 8 proposal PRs (2 deferred to a Phase 4 PR
to avoid a conflicting edit); 2 `gap` + 1 lifecycle decision → 3 tracked draft
tickets.

| Finding | Class | Disposition |
|---|---|---|
| F1, F2 | extract | PR #654 |
| F3 | extract | PR #655 |
| F4 | extract | PR #656 |
| F5 | extract | PR #657 |
| F9, D5 | stale, drift | PR #659 — resync diverged live/packaged copies |
| F6, F7, F8 | stale | PR #660 — contexts describing removed primitives |
| D2 | drift | PR #661 — microkernel rule's `open-pr` example |
| F10 (template half) | stale | PR #662 — delete `rebase-stale-worktrees` |
| F11 | stale | PR #663 — packaged digest hardcoded owner |
| D3, D9 | drift | PR #664 — bundled CLI reference |
| D4, D6, D7, D8, D11 | drift | PR #665 — `docs/` drift sweep |
| D10 | drift | PR #666 — `current-direction` stale slug |
| D1 | drift | **deferred** — overlaps PR #654 |
| F10 (Gotchas half) | stale | **deferred** — overlaps PR #657 |
| F13 | gap | draft `scrub-coga-task-in-the-pytest-autouse-guard-so-fix` |
| F14 | gap | draft `retire-a-finished-ticket-s-linked-worktree-and-mak` |
| F12 | stale | draft `decide-the-fate-of-two-premise-dead-v2-drafts-whos` |

### Deferred overlaps (per the Dream contract — do not open a conflicting PR)

- **D1** (`coga/contexts/coga/codebase/SKILL.md:57-58` and `:87-90` still name the
  deleted `commands/open_pr.py` / `open_pr.py` and claim PR #585 made `open-pr` a
  core command) overlaps **PR #654**, which already edits that file. Flagged in
  PR #661's body for #654's reviewer.
- **F10's second half** (a `## Gotchas` bullet in `coga/contexts/coga/recurring/SKILL.md`
  stating that Coga-shipped recurring templates have a packaged twin to create,
  edit, and **delete** in lockstep) overlaps **PR #657**, which already edits that
  file. Flagged in PR #662's body for #657's reviewer.

### Left to a human, not routed to a PR

`important_recipient`'s overstated claim also appears in the comments of
`coga/coga.toml:62-68` and `src/coga/resources/templates/coga/coga.toml:83-89`.
Dream is prohibited from touching `coga.toml`, so those two comment blocks are
untouched and still overstate the key. Noted in PR #665's body.

### F12 routing note

F12 is class `stale` but its target is two draft tickets, not a context or skill,
and cancelling a draft is a lifecycle change that is human-only. It was routed to
a tracked draft ticket rather than a proposal PR so the judgment survives this
task's retirement.

## Dream Run Summary

Generated: 2026-07-27T22:40Z · period `2026-W31` · task `recurring/dream`

| Phase | Result | Detail |
|---|---|---|
| 1. validate-drift | `direct-fixed` + `human-needed` | 24 issues; 1 fix applied; 24 human-needed |
| 2. knowledge scan | `reported` | 14 findings — 5 extract, 7 stale, 2 gap |
| 3. contract audit | `reported` | 11 findings — all drift |
| 4. retro/done-ticket | `pr-opened` | 13 tickets processed; 5 knowledge PRs; 9 direct deletes |
| 5. cleanup-orphan-markers | `no-op` | no orphaned markers |
| 6. disposition | `pr-opened` | 8 proposal PRs; 3 draft tickets; 2 deferred |

**Findings: 25 total** (14 knowledge scan + 11 contract audit). Every one has a
durable home; none rests only in this blackboard.

**PRs opened — 13, all MERGEABLE/CLEAN, none auto-merged (all `pr-required`):**

Phase 4 knowledge PRs — [#654](https://github.com/FastJVM/coga/pull/654) live/packaged rebase trap · [#655](https://github.com/FastJVM/coga/pull/655) no-remote sync soft-skip · [#656](https://github.com/FastJVM/coga/pull/656) open-pr parked-checkout refusal · [#657](https://github.com/FastJVM/coga/pull/657) recurring agent delegation needs a pty · [#658](https://github.com/FastJVM/coga/pull/658) self-qa review fallback

Phase 6 proposal PRs — [#659](https://github.com/FastJVM/coga/pull/659) resync diverged copies · [#660](https://github.com/FastJVM/coga/pull/660) contexts describing removed primitives · [#661](https://github.com/FastJVM/coga/pull/661) microkernel `open-pr` example · [#662](https://github.com/FastJVM/coga/pull/662) delete `rebase-stale-worktrees` · [#663](https://github.com/FastJVM/coga/pull/663) packaged digest owner · [#664](https://github.com/FastJVM/coga/pull/664) bundled CLI reference · [#665](https://github.com/FastJVM/coga/pull/665) `docs/` drift · [#666](https://github.com/FastJVM/coga/pull/666) `current-direction` slug

**Draft tickets created — 3:** `scrub-coga-task-in-the-pytest-autouse-guard-so-fix`,
`retire-a-finished-ticket-s-linked-worktree-and-mak`,
`decide-the-fate-of-two-premise-dead-v2-drafts-whos`.

**Tickets deleted — 13:** 4 in knowledge PRs (pending merge), 9 direct-deleted and
already on `origin/main`.

### `human-needed` and review gates

1. **24 validate-drift issues need an owner decision** — 4 `stuck-in-progress`
   (idle 144–267h), 7 `unfrozen-workflow`, 5 `unknown-assignee` (`nicktoper` is
   not a known agent type), 3 `missing-step` (errors), 4
   `unsynthesized-draft-blackboard` (errors). All are lifecycle/ownership calls
   Dream must not make silently. Full list in `## Dream Skill: validate-drift`.
2. **PR #657 edits the Dream contract itself** — it amends
   `coga/contexts/coga/recurring/SKILL.md`'s claim that period tasks "carry
   nothing durable", because `recurring/resolve-conflicts` was a live
   counterexample that would have been direct-deleted unread. Worth a careful read.
3. **Two deferred findings (D1, F10-Gotchas)** need folding into #654 and #657 at
   review, or a follow-up PR.
4. **`important_recipient` comments in both `coga.toml` files** still overstate the
   key; Dream cannot edit those files.
5. **13 open PRs is a large review queue.** #659 and #663 are near-mechanical and
   safe to land first.

### Run health notes

- `origin/main` advanced concurrently throughout (other Coga sessions landing
  state commits). All PR branches were based on the then-current tip; all are CLEAN.
- The operator's staged `coga/tasks/` → `coga/tasks/v2/` renames present at session
  start were committed by a concurrent session (`bce4e209`), not lost.
- Both isolated checkouts (`retro-wt`, `dispo-wt`), their temporary branches, the
  copied `coga.local.toml` files, and the evidence snapshot were all removed.
  The primary checkout is in sync with `origin/main`.
