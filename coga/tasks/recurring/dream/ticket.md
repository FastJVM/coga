---
slug: recurring/dream
title: Dream
status: done
mode: agent
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

1. **validate-drift** — deterministic repo hygiene (script worker).
2. **knowledge scan** — one full-corpus read; classifies every finding.
3. **contract audit** — checks the contract surface against code reality.
4. **retro/done-ticket** — extracts durable knowledge from every eligible done
   ticket in one pass.
5. **cleanup-orphan-markers** — delete-only orphan cleanup (script worker).
6. **disposition + run summary** — routes every finding to a durable home.

This body is the dispatch contract. Do not auto-discover skills, scan a plugin
folder, or invent another maintenance phase during the run. Adding or removing
a Dream phase is a normal change to this template. A phase failing does not
permit a replacement: record the result and continue only with later phases
whose inputs do not depend on the blocked one. If a repo wants a different
maintenance loop, make another task with its own body and ordered phase list.

The two script workers (Phases 1 and 5) each run as a child script
task whose one workflow step references the worker skill — Dream-owned scripts
are skills attached to Coga tasks, never standalone execution units. Before
launching a worker, read its `## Known Skill Contract`, keep its reads and
writes inside its declared scope, let it write its own `## Dream Skill: <name>`
section to the child task blackboard, then summarize that child result here.

### Phase 1 — validate-drift

Launch a child script task whose current workflow step references
`bootstrap/dream/tasks/validate-drift`. The skill runs the same deterministic
surface as `coga validate --json`, classifies every issue, and appends
`## Dream Skill: validate-drift` to the child task's blackboard.

The skill's default safe-repair pass applies only deterministic repairs
currently supported by `coga validate --fix`: create missing `blackboard.md`
from the standard template and create missing `log.md` as an empty append-only
file. It does not rewrite existing files, synthesize `ticket.md`, freeze
workflows, or change lifecycle/assignee state.

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

Run `retro/done-ticket <slug> [<slug> ...]` in one subagent, passing every
eligible slug. The skill loads the context/skill corpus once, reads each
ticket, carries one running delta across the whole run, and partitions the
tickets into coherent PR batches — each PR within its hard limits (≤5 source
tickets, ≤3 knowledge files, ≤1 new context/skill file, one theme). Every
processed done ticket is deleted: a ticket that contributed durable knowledge
is deleted in its theme's knowledge PR, which also records its `## Retro`
marker; a ticket carrying nothing durable is direct-deleted with
`coga delete <slug>` (a working-tree `git rm` plus a direct
`Ticket: <slug> — deleted` commit), with no PR and no marker. Recovery is via
`git restore`. Retro never leaves a processed done ticket on disk and never
opens a marker-only PR.

A done `recurring/<name>` ticket is an eligible done ticket like any other —
this is how recurring period tickets get cleaned up. The recurring command does
not delete real done period tasks; a finished period task sits on disk as
`status: done` until a Dream run sweeps it here. Period tickets carry nothing
durable (their output is the notification post or PR they already produced),
so Retro finds no new knowledge in them and **direct-deletes** them via `coga
delete recurring/<name>` — no PR, no marker — leaving the recurring template's
`last_serviced_period` line in `coga/recurring/<name>/blackboard.md`
untouched so the period is not re-created. This includes the **previous
Dream run's own** `recurring/dream` ticket: Dream does not delete itself
mid-run, so the last finished Dream period ticket is one of the done tickets
this pass deletes.

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

Launch a child script task whose current workflow step references
`bootstrap/dream/tasks/cleanup-orphan-markers`. The skill detects cleanup
candidates and gates deletion through `bootstrap/delete-task`. That delete
skill ships, but until its cleanup PR-dispatch wiring is finished the worker
reports `human-needed` and deletes nothing.

For each candidate, cleanup must open a PR that deletes only the resolved task
directory under `coga/tasks/`. The deletion goes in the PR, not the working
tree, so a human can review it before merge. Cleanup gate:

- the marker is present in the task directory's `blackboard.md`;
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

Child script tasks write their durable result to their own blackboard; the
parent Dream run sends the broader one-line summary. Call:

`coga slack --task <this-dream-task> --message "<summary>"`

Keep the message to one line, for example:
`Dream: validate-drift clean, 2 knowledge PRs, 1 stale-fix PR, 1 gap ticket.`

Run `coga mark done <this-dream-task>` once the blackboard is up to date and
the Slack summary is posted. That is the last action — **do not delete this
task.** The run's durable artifacts — every PR, draft ticket, and the Slack
summary — carry the findings, so this `done` task and its blackboard are
disposable, but Dream does not delete itself mid-run. It sits on disk as a
done `recurring/dream` ticket and is cleaned up by the **next** Dream run's
Phase 4 retro pass, exactly like every other done recurring period ticket.
Dream is the single deleter of done recurring tickets; it just never turns that
deleter on itself in the same run.

## Context

<!-- coga:blackboard -->

## Run plan

Dream run for period 2026-W27 (parent last_serviced_period: 2026-W27).
Human chose: **full run, all 6 phases**.

Orientation (start of run):
- ~43 `status: done` tickets on disk under `coga/tasks/` → Phase 4 retro candidates.
- Open PRs: #472 (docs-sandbox-dev-loop-friction, ticket not done), #473 (coga/skill-update).
- Working tree has routine uncommitted state writes (digest spool, usage records,
  launch log line) from the recurring runs that just fired — NOT mine; branch around them.
- Phase 5 cleanup-orphan-markers worker reports human-needed by design.

Phase progress:
- [x] P1 validate-drift (script child) — child task `dream-validate-drift-w27`
- [x] P2 knowledge scan (subagent) — 16 findings
- [x] P3 contract audit (subagent) — 7 drift findings
- [x] P4 retro/done-ticket — 5 knowledge PRs (#474-#478, 8 extract), 35 direct-deletes
      (34 by subagent + 1 I caught it missed: support-task-subdirectories). All on
      LOCAL main, UNPUSHED (harness gated direct main push). PR branches pushed OK.
- [x] P5 cleanup-orphan-markers — ran detection INLINE (read-only): no processed
      ## Retro markers on local main → confirmed no-op. Did NOT create a child task
      (would push the 35-ahead main mid-run before the user's push decision).
- [~] P6 disposition + run summary (proposal PRs running; gaps+summary+push pending)

## Phase 1 — validate-drift result

Child task: `dream-validate-drift-w27` (done). `coga validate --json --fix`.
- 10 deterministic `blackboard-fence` auto-fixes were applied to the working
  tree, then **reverted by Dream**: all 10 targets are either group READMEs
  (`install/README.md`, `marketing/README.md` — not tickets) or `install/*`
  legacy tickets that are independently malformed (missing `slug`+`autonomy`,
  orphan `mode` key). Fence-on-README is a validator false-positive; fence-on-a
  -frontmatter-broken-ticket is premature (owner must repair frontmatter first).
  Deterministic, so a future `validate --fix` re-offers them; nothing lost.
- 44 `human-needed` issues (no direct-fix, no PR-proposal). Buckets:
  - **`install/*` legacy format (8 tickets + install/README):** `missing-key`
    slug/autonomy (error), orphan `mode` key, `install/README` bad-frontmatter.
  - **`marketing/README` bad-frontmatter; `marketing/auto-width-200`
    missing-step; `marketing/relay-discord` unknown-assignee 'nick'.**
  - **`v2/*`:** several missing-step (autotrigger-ticket-type,
    split-context-to-doc, use-worktree) + unknown-assignee 'nick' on 5 + one
    stuck-in-progress (add-dev-testing-setup-skill, idle 463h).
  - **stuck-in-progress (idle):** drain-pending-auto-tickets (130h),
    filter-relay-status-by-directory-group (74h), improve-prompt-for-relay-ticket
    (97h), mode-autonomy-split/1 (74h), nightly-auto-drain (111h),
    wire-autonomy-triage (337h).
  - **unfrozen-workflow:** handle-better-delete-branches-autcommit.
  These are lifecycle/ownership/frontmatter decisions the worker defers to the
  owner — surfaced to the human; not auto-fixed.

## Findings

(Phase 2 knowledge-scan + Phase 3 contract-audit populate this.)

## Phase 4 eligibility (pre-computed)

43 `status: done` tickets on disk. Open PRs #472 (contexts/coga/codebase) and
#473 (skills/google-agents-cli-*) touch NO done-ticket dir → no PR-overlap
exclusions.

Eligible for Phase 4 retro = **42** (all 43 minus `dream-validate-drift-w27`,
this run's own worker scratch — left for the next run, matching how the prior
`dream-debug-validate-drift` / `dream-debug-cleanup-orphan-markers` worker
children were left behind rather than self-deleted). No prior done
`recurring/dream` ticket exists on disk, so the self-delete carve-out is moot.

Done `recurring/*` period tickets in the set → direct-delete (no durable
knowledge): `recurring/autoclose-merged`, `recurring/digest`,
`recurring/skill-update`. Their templates under `coga/recurring/<name>/` are a
different path and stay untouched.

Git note: `anonymous-install-telemetry-opt-out-no-pii` (a delete target) has an
uncommitted usage-record append in the working tree; that record dies with the
file at deletion (disposable telemetry). `document-cross-machine-...` also has
an uncommitted usage record but is NOT done (open PR #472) → not a candidate.
Direct-deletes commit to `main` by design; knowledge PRs branch off `main`.

## Phase 4 execution plan (retro subagent, plain-git / Option A)

5 knowledge PRs (8 extract tickets), 34 direct-deletes, sum 42:
- PR1 git control-branch-mismatch soft-skip → contexts/coga/sync. [fresh-repo-...]
- PR2 config fail-loud unknown keys → contexts/coga/architecture. [fail-loud-...]
- PR3 codebase gotchas (OptionInfo / no-pin-to-dogfood / shared-subprocess) →
  contexts/coga/codebase. [fix-optioninfo, marketing/relay-build-command,
  decouple-autoclose, 1password-op-secret]. OVERLAPS open PR #472 (same file) —
  noted in PR3 body for human merge-order.
- PR4 NEW contexts/coga/usage/SKILL.md (local usage primitive, provider seam) →
  [track-usage-of-llm].
- PR5 shared agent-spawn path → contexts/coga/architecture. [finish-relay-ticket-...]
Dropped as already-covered (in bootstrap contexts / coga contexts): E2, E1-preflight,
E5, E9, E10 candidates — those tickets direct-deleted.

## OBSERVATION — coga-state sweep not firing (candidate finding)

`coga.toml` is at `coga/coga.toml` (repo_root = `coga/`), so `_coga_state_pathspecs`
should return `["coga"]` and the dispatch-`finally` `sync_coga_state` sweep SHOULD
commit dirty `coga/` files to the control branch after every sweeping command
(create/mark/launch/slack/delete/bump...). Empirically it does NOT: 6 dirty files
(digest spool/ticket, 2 usage records, log.md, dream blackboard) survived ~6
sweeping commands this session; digest spool's last commit is the #455 rename.
git is enabled (lifecycle commits land + push: origin/main==main), control branch
present. Mechanism unconfirmed — either a silent GitError-swallow in
`_dispatch_branch_sync`, a path-resolution mismatch, or a guard I didn't trace.
Net effect: Coga's "always-on sync" / convergence contract is silently not
holding in this repo → routine OS-state accumulates uncommitted. Route P6: gap
draft ticket to INVESTIGATE (don't assume bug; needs a repro + root-cause).

### F-validator-readme (drift)
Target: `src/coga/validate.py` (validator). The validator scans `README.md`
files inside task subdirectories (`coga/tasks/install/README.md`,
`coga/tasks/marketing/README.md`) as if they were tickets — emits
`bad-frontmatter` and auto-adds a spurious blackboard fence under `--fix`.
Group/doc READMEs in task dirs are not tickets. Surfaced by Phase 1.
Route: Phase 6 (drift → proposal PR, or gap if it needs design judgment).

### Phase 3 — contract audit (7 drift findings)

Strong theme: obsolete `blackboard.md`/`log.md` multi-file model lingering in
contracts after the v2 single-file (`ticket.md` + blackboard region) migration.

1. **D1 contract-audit skill "Phase 7"** — `src/coga/.../scan/contract-audit/SKILL.md:42-43`
   says Phase 7 routes drift; Dream has 6 phases (routing is Phase 6).
2. **D2 knowledge-scan skill "Phase 5" (×2)** — `.../scan/knowledge-scan/SKILL.md:10,27`
   say "Phase 5 deletes / batches PRs"; that's Phase 4. Phase 5 is cleanup-orphan-markers.
3. **D3 Dream body Phase 1 stale repair desc** — `coga/recurring/dream/ticket.md:74-79`
   claims `validate --fix` creates `blackboard.md` + `log.md`; code (validate.py
   apply_safe_fixes, create.py:202-203) appends a fence/region to `ticket.md` and
   never creates per-task `blackboard.md`/`log.md`. Same text in packaged copy.
4. **D4 Dream body Phase 4/5 blackboard.md refs** — `coga/recurring/dream/ticket.md:140,169`
   point at `coga/recurring/<name>/blackboard.md` and task-dir `blackboard.md`;
   state + Retro marker live in `ticket.md` blackboard region (recurring.py,
   cleanup-orphan-markers run.py). File footer (line 243) is already correct →
   internally inconsistent.
5. **D5 recurring `_template` + `_rem` templates** — `coga/recurring/_template/ticket.md:26-27`,
   `coga/recurring/_rem/ticket.md:23-25` describe separate `blackboard.md`/`log.md`;
   single-file now. These SEED new recurring tasks → propagate the stale model.
6. **D6 code/design skill** — `coga/skills/code/design/SKILL.md:34` puts Open Questions
   on `blackboard.md`; should be ticket's blackboard region.
7. **D7 copy divergence browser/dom-backed** — live `coga/contexts/browser/dom-backed/SKILL.md:55`
   says ticket.md blackboard region (correct); packaged
   `src/coga/resources/templates/coga/contexts/browser/dom-backed/SKILL.md:55` still
   says `blackboard.md` (stale seed). Resync packaged → live.

Excluded (expected divergence, not drift): coga.toml live-vs-packaged (real
config/webhooks vs empty seed; dropped `dream` alias); recurring
`last_serviced_period`/digest-spool runtime state lines.

NOTE: D3+D4 edit the Dream template (this task's own source) — Phase 6 routes as
`pr-required` proposal PR; never edit on main. D1/D2 edit packaged scan skills.

### Phase 2 — knowledge scan (16 findings: 10 extract, 3 stale, 3 gap)

EXTRACT (candidate knowledge-PR themes for Phase 4; re-verify vs current corpus):
- E1 git/auth conventions → `contexts/coga/sync` (+architecture pointer).
  Sources: relay-forces-https, fresh-repo-default-branch-mismatch-git-init-master,
  manually-test-auth-paths-gh-git-detection-secret-r.
- E2 `recurring --all` is a forced full run; slug-prefix gating ≠ isolation →
  `contexts/coga/recurring`. Source: make-recurring-all-a-real-full-run-drop-the-debug.
- E3 config loader fails loud on unknown keys → `contexts/coga/architecture`.
  Source: fail-loud-on-unrecognized-config-sections-instead.
- E4 Typer OptionInfo sentinel gotcha; prefer aliases over in-code cmd calls →
  `contexts/dev/code` or `coga/codebase`. Sources:
  fix-optioninfo-sentinel-crash-in-on-demand-recurri, marketing/relay-build-command.
- E5 prompt files single-source (not dual-copy); base prompt = per-run token cost →
  `contexts/coga/codebase` + architecture. Source: launch-prompt/improve-prompt-for-relay-launch.
- E6 don't pin tests to live dogfood drift (_strip_runtime_state) →
  `contexts/coga/codebase`. Sources: decouple-autoclose-sweep-test-from-baked-in-period,
  1password-op-secret-references-and-relay-secret-ge.
- E7 usage = blackboard-JSONL primitive w/ provider parser seam →
  `contexts/coga/architecture` + codebase. Source: track-usage-of-llm.
- E8 one shared agent-spawn path; launch supervisor wraps it →
  `contexts/coga/architecture`/codebase. Source: finish-relay-ticket-greet-first-land-pr-417.
- E9 imported-vs-bundled skill update model → `contexts/coga/extension-model`.
  Source: recurring/skill-update.
- E10 bullet-tolerant `pr:` line + task-discovery rules → `contexts/dev/code` +
  codebase. Sources: document-the-automerge-bare-pr-line-format-require,
  support-task-subdirectories-in-task-discovery.

STALE (→ Phase 6 proposal PRs):
- S1 telemetry described as live v1 hosted crossing but it's WONT-SHIP + principle 5
  now forbids it → edit `contexts/coga/architecture` (~341-359), `extension-model`
  (~106), `roadmap`. HIGH value.
- S2 Dream template recurring state points at blackboard.md (single-file now) →
  OVERLAPS contract-audit D4 (same file `coga/recurring/dream/ticket.md`). Merge.
- S3 roadmap status tags stale for several now-done tickets → fold into S1 roadmap PR.

GAP (→ Phase 6 draft tickets):
- G1 no install/onboarding context → draft ticket. Covers 7 sources: first-run-works
  -without-slack, relay-init-captures-name-via-user-param, marketing/relay-init-captures
  -name, marketing/relay-init-git-inits-a-fresh-dir, marketing/relay-uninstall,
  marketing/relay-build-command, marketing/relay-build-onboarding-flow. These 7 are
  retro DIRECT-DELETED in P4 (knowledge deferred to this draft ticket, NOT extracted).
- G2 reopening a done ticket would not re-resolve assignee (latent footgun) → draft ticket.
  Source: launch-must-not-re-activate-a-done-ticket.
- G3 Dream scan-filed gaps decay; re-verify premise vs source before building → draft
  ticket. Sources: decouple-autoclose..., document-the-automerge..., fix-optioninfo...



## Usage

{"agent":"claude","cache_creation_input_tokens":579593,"cache_read_input_tokens":16579062,"cli":"claude","input_tokens":16948,"model":"claude-opus-4-8","output_tokens":324877,"provider":"anthropic","schema":1,"session_id":"506037ea-cd39-4ff0-8c56-e86e1ec1e27c","slug":"recurring/dream","step":"execute","title":"Dream","ts":"2026-06-30T07:03:58.387183Z","usage_status":"ok"}
