---
slug: recurring/dream
title: Dream
status: in_progress
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

## Run notes

- Phase 1 (validate-drift): done — 23 issues, all human-needed, 0 direct fixes. Recipe ran twice (double invocation); duplicate section removed.
- Phase 2 (knowledge-scan) and Phase 3 (contract-audit): delegated to read-only subagents, running.
- Phase 4 prep: 15 done tickets on disk; open PRs #678 (coga/skill-update) and #677 (codex/address-pr-comments) touch no coga/tasks/ path and add no Retro markers, so all 15 are eligible.
  - Ordinary: always-accept-coga-ticket, bump-can-mark-done-too, document-megalaunch-drain-order, recurring-bugs/branch-sweep-leaves-worktree-pinned-merged-branche, recurring-bugs/dream-recipes-write-reports-into-packaged-bootstra, remove-run-py/delete-the-script-seam, remove-run-py/port-hard-consumers-onto-the-generic-runner, retire-a-finished-ticket-s-linked-worktree-and-mak, scrub-coga-task-in-the-pytest-autouse-guard-so-fix, write-real-coga-documentation-command-reference-gu
  - Recurring period tickets (direct-delete, no marker): recurring/autoclose-merged, recurring/blocker-reminders, recurring/branch-sweep, recurring/digest, recurring/skill-update

## Findings

### Phase 2 — knowledge scan

#### `extract` — group: dev/code (checkout lifecycle)

**F1 — Durable-checkout rule: /tmp worktrees are a data-loss pattern** — `extract` — source tickets `write-real-coga-documentation-command-reference-gu`, `retire-a-finished-ticket-s-linked-worktree-and-mak`, `recurring-bugs/branch-sweep-leaves-worktree-pinned-merged-branche`; target `coga/contexts/dev/code/SKILL.md` (`## Checkout boundary`) + packaged twin.
Three done tickets independently paid for the same missing rule. The docs ticket's first implement pass was unrecoverable — the `/tmp/coga-real-docs` worktree was wiped by a reboot and the branch existed in no ref, forcing a full human-decided rewind and redo. The retire ticket's recorded worktree and branch were likewise gone at relaunch, and the branch-sweep probe found 18 prunable worktrees (mostly `/tmp`) invisibly pinning branches. `dev/code` says only "a path outside the primary checkout", and the `code/implement` fallback clone recipe itself uses `mktemp -d /tmp/...`. Draft addition to `## Checkout boundary`: *"A `/tmp` checkout survives only until the next reboot. For work that may span sessions, either use a durable sibling path (e.g. `../coga-<branch>`) or push the branch to the remote before ending the session — an unpushed branch whose only checkout is under `/tmp` is one reboot away from unrecoverable. A wiped `/tmp` worktree also keeps pinning its branch until `git worktree prune`."*

#### `extract` — group: coga/codebase (dev-loop gotchas)

**F2 — Coga commands inside a feature worktree publish `coga/` edits to `main` before the PR exists** — `extract` — source ticket `remove-run-py/port-hard-consumers-onto-the-generic-runner`; target `coga/contexts/coga/codebase/SKILL.md` (`## Sandbox and cross-machine dev loop`).
Running `coga validate` / `coga run` from inside the feature worktree tripped the automatic control-branch sync, which committed the branch's in-flight `coga/` context and skill edits and pushed them to `origin/main` as `3779d340` before the PR existed — leaving `main`'s contexts describing behavior `main`'s code didn't yet have, and those files missing from the PR diff. Draft bullet: *"State-changing (and even validating) coga commands run from a feature worktree will sweep any dirty `coga/` context/skill edits onto the control branch immediately — publishing your doc half before your code half merges. Keep in-flight `coga/` edits committed on the feature branch (not dirty in the working tree) before running coga commands there, or expect them to reach `main` out-of-band and drop out of the PR diff."*

**F3 — Megalaunch from a stale checkout replays already-merged tickets** — `extract` — source ticket `remove-run-py/delete-the-script-seam`; target `coga/contexts/coga/codebase/SKILL.md` (or `dev/code` `## Checkout boundary`).
Megalaunch re-picked the ticket eight minutes after its PR merged, because the invoking checkout sat on a feature branch 75 commits behind `origin/main`: the composed prompt was built from a stale ticket copy and stale source still containing the deleted seam. Draft bullet: *"Run `coga megalaunch` (and launches generally) only from a control checkout freshly synced to `origin/<control>`. A checkout parked behind `main` composes prompts from stale ticket copies and can re-dispatch work that already merged; the state-regression guard protects the control branch, not your session's wasted run."*

#### `stale`

**F4 — Live and packaged task `_template` carry the removed `autonomy:` field and pre-rename `[secrets]`/relay prose** — `stale` — files `coga/tasks/_template/ticket.md` and `src/coga/resources/templates/coga/tasks/_template/ticket.md`.
Both templates open with `autonomy: interactive`, but `coga/architecture` states "There is no `autonomy:` field". The live copy additionally documents `secrets:` as keys from `[secrets]` in relay.local.toml with legacy blanket-inject semantics — three contradictions of the current model (no central `[secrets]` catalog, `null` injects nothing, the file is `coga.local.toml`), plus `relay create`/`relay ticket`/`relay.toml` naming. Fix: strip `autonomy:`, rewrite the secrets comment to the inline `- NAME: op://…` / `env:VAR` list shape, and s/relay/coga/ in both copies.

**F5 — `coga/recurring` wrapper Gotcha contradicts the `recurring/resolve-conflicts` template on TTY admission** — `stale` — files `coga/contexts/coga/recurring/SKILL.md` (Gotchas, ~lines 371–387) and `coga/recurring/resolve-conflicts/ticket.md`.
The context tells a wrapper agent to run the delegated agent-backed command under a fake pty (`script -qec ... /dev/null`) and confirm success via `coga/log.md`; the template says the opposite ("Recurring's outer agent supervisor remains responsible for TTY admission"). The 2026-W33 run followed the template, judged the pty workaround a design bypass, and terminally blocked (blocker `20260813T094004`) — the delegated sweep never ran. One of the two must win; the blocked run's blackboard leans structural, so the proposal PR should flag that half may deserve a draft ticket.

**F6 — Packaged `docs/with-review` workflow still instructs the removed `coga panic`** — `stale` — file `src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md` (5 occurrences: lines 50, 62, 90, 117, 145).
The blocked-handoff surface is `coga block` / `coga unblock` everywhere else; an agent following this workflow will invoke a nonexistent command exactly when stuck. Overlap: draft ticket `docs-with-review-coga-panic` (2026-08-05) already tracks this — the stale-fix PR should close that draft rather than duplicate it.

**F7 — `coga/secrets` single-vault rule contradicts its own trust-tier guidance** — `stale`, already tracked, do not open a parallel PR — file `coga/contexts/coga/secrets/SKILL.md`.
"SA … scoped to a single vault" and "secrets will accrue in vaults named by their trust level" cannot both hold; hit live 2026-08-11. Active ticket `service-account-scoping-single-vault-rule-conflict` (workflow `draft-for-human`) owns the design decision. Note the overlap and defer.

**F8 — The `v2/` parking area systematically references `relay`/`relay-os` paths that no longer resolve** — `stale` — directory `coga/tasks/v2/` (most non-empty drafts).
Pre-rename paths (`src/relay/`, `relay-os/contexts/...`, `relay launch`) and dead mechanisms (`mode: script`, `relay panic`, `[secrets]` bulk-inject) pervade the parked drafts. Draft `decide-the-fate-of-two-premise-dead-v2-drafts-whos` already calls the v2-wide sweep "a broader cleanup question"; route by folding into that existing draft's scope rather than a new artifact.

#### Phase 2 notes (unclassified)

- Untracked `__pycache__/recipe.cpython-312.pyc` leftovers in `coga/skills/code/open-pr/`, `coga/skills/coga/autoclose/sweep/`, `coga/skills/coga/blockers/remind/` — residue of the deleted `recipe.py` seam; pure hygiene.
- Most done tickets already extracted their knowledge in their own PRs; apart from F1–F3 they are direct-delete candidates.
- Phase 4 batching hint: F1's three source tickets + `write-real-…` = one dev/code checkout-lifecycle knowledge PR (4 source tickets); F2+F3's two `remove-run-py` tickets = a second codebase-dev-loop PR; the rest are direct-delete.

### Phase 3 — contract audit

**F9 — Shipped task template carries the removed `autonomy:` field** — `drift` — `coga/tasks/_template/ticket.md:5` and packaged copy `src/coga/resources/templates/coga/tasks/_template/ticket.md:5`.
Both copies ship `autonomy: interactive`, but the field was removed (`src/coga/config.py:463` — "Removed with the autonomy rework (#503): launches are interactive-only"); no code reads it, it is not in `_RESERVED_TICKET_FIELD_NAMES`, and `coga validate` warns on tickets copied from the template. Source of truth: code reality + architecture context.

**F10 — Shipped task template documents the removed `[secrets]` catalog and inverted `null` semantics** — `drift` — `coga/tasks/_template/ticket.md:13-15` and packaged copy, same lines.
The `secrets:` comment teaches "omit or `null` = legacy blanket-inject all secrets", but `parse_inline_secrets` (`src/coga/config.py:1166`) treats absent/`null`/`[]` identically as no secrets, there is no `[secrets]` catalog, and a `[secrets]` table in `coga.local.toml` raises a migration ConfigError (`src/coga/config.py:233-240`). Source of truth: `src/coga/config.py`.

**F11 — Live task template diverged from packaged copy — pre-rename `relay` spellings** — `drift` — `coga/tasks/_template/ticket.md:13,18-19` vs packaged copy.
Live copy says "relay.local.toml", "relay.toml", "`relay create` / `relay ticket`"; the packaged counterpart already uses `coga` spellings. All other live/packaged pairs are byte-identical apart from runtime state, so the divergence is undocumented. Source of truth: packaged template + Relay→Coga rename.

Phase 3 note: F9–F11 all target the same `_template` pair as Phase 2's F4 — route as one combined proposal PR. Audit otherwise found the contract surface in good sync (recipe registry, aliases, flags, validator kinds, notification tiers all check out).
