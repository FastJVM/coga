---
title: Adjudicate the eight premise-dead v2 drafts
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 3 (review-design)
---

## Description

Dream 2026-08-24 named eight `v2/` drafts as premise-dead, but the evidence did
not support treating them as a flat cancellation list. Apply the v2 README's
subject and surface checks to the four remaining subjects and preserve the
four binding verdicts already reached by sibling tickets. Also account for
the README's newer required-substance and already-delivered checks.

The recommendation is **one new cancellation and three retained proposals**.
It clears **none** of the three current validation errors. Autotrigger's
subject survives; its authoring residue is not evidence for cancellation.

Cancellation is an owner decision with lifecycle effects: status, audit log,
git sync and notification. The frozen workflow sends this design to an
independent evaluator, then to the owner at `review-design`; only after that
approval may `implement` execute the approved cancellation. No cancellation
is authorized by this design-step handoff alone.

### Acceptance criteria

- [ ] All eight exact slugs have an evidence-graded verdict, with recorded
      outcomes distinguished from new recommendations and an exact reason
      for the sole proposed cancellation.
- [ ] The owner has approved the table at `review-design`. The only new
      cancellation, if approved unchanged, is
      `v2/skill-update-aborts-on-uncommitted-log-file`; its reason explicitly
      preserves the surviving ordinary-dirty-file preflight bug.
- [ ] No prior verdict is reopened: preserve the rules audit cancellation,
      both historical done outcomes, and split-context's documentation owner
      gate. Do not recreate the deleted dev-loop ticket.
- [ ] Autotrigger and skill search remain `draft`; repository design remains
      `paused`, owned by `zach`. Their bodies carry the current evidence and
      bounded follow-up below, without implementing or activating them.
- [ ] Required recovered substance is in the retained draft itself; retired
      tickets are provenance only. The canceled draft is not synthesized or
      erased. Autotrigger's blackboard remains for its own pre-activation
      authoring; this ticket does not clear its validation error.
- [ ] Only CLI commands change lifecycle fields and append to `coga/log.md`.
      No core, config, context, template or README policy changes.
- [ ] `git diff --check` and targeted validation of this ticket, skill-update
      after cancellation, repository design, and skill search pass. Report
      autotrigger's expected synthesis error and the repo-wide baseline;
      explain intervening sibling changes without fixing unrelated drafts.

### Verdict table — proposed for owner review

Evidence snapshot: 2026-09-17, `main` and local `origin/main` at
`d4c7445b7769d261c1fbaf3510625ea40486673b`. **Recorded** is a binding prior
decision; **verified** is source/command/history evidence for a new verdict;
**partial** is delivered overlap without proof of full settlement. Line
numbers are navigation aids at that revision; code symbols identify the
evidence. Keep preserves the existing disposition, including terminal ones.

| Exact task ref | Verdict / grade | Evidence and premise result | Exact cancellation reason / action |
| --- | --- | --- | --- |
| `v2/audit-rules-md-usage-across-relay-and-decide-wheth` | **cancel — recorded; already canceled** | Binding 2026-09-16 verdict at `coga/log.md:5422`; do not re-adjudicate. | No new command. Recorded reason: "Premise-dead (adjudicate-parked-and-active-tickets-whose-premise): the 'Global rules' prompt layer, coga/rules.md, paths.rules_path() and the compose.py rules layer this draft audits no longer exist anywhere in src/, coga/ or docs/ — rules.md survives only as a stale-artifact fixture in tests/test_init.py's prune test. Its 'known facts (verified)' block is wrong and there is nothing left to keep, gut, or remove." |
| `v2/document-workflow-less-concept-capture-drafts-as-s` | **keep — recorded `done`** | `coga/log.md:5427` closes it as satisfied by architecture's "Workflow gated at activation, not draft time" (`coga/contexts/coga/architecture/SKILL.md:490`). | None; preserve done, not a new cancellation. |
| `v2/split-context-to-doc-user-accessible-and-editable` | **keep — recorded, guarded `draft`** | Its Description and Context (`coga/tasks/v2/split-context-to-doc-user-accessible-and-editable.md:36`) retain relocation and the documentation owner gate; PR #826 / `23420a91` recorded the rewrite. | None; preserve the prior keep and gate. |
| `v2/dev-loop-git-hygiene-lift-sync-with-main-into-code` | **keep — recorded `done`, subsequently deleted** | `coga/log.md:4984` records both delivered changes and remaining inline-prose residue. Deletion history identifies `b73b20d0` on 2026-09-14. | None; do not recreate or re-adjudicate. |
| `v2/autotrigger-ticket-type` | **keep-with-follow-up — verified** | Subject: schedule/idle unification is unbuilt; `recurring.scan_due` (`src/coga/recurring.py:639`) and `recurring_runner.run_recurring_scan` (`src/coga/recurring_runner.py:1470`) still serve recurring schedules. Surfaces: `mark.mark_in_progress` (`src/coga/mark.py:754`) survives; six cited slugs are absent, but the four retired hazard sources are recoverable (Context below). | None. Preserve the concept; repair dependency prose with recovered substance and current lifecycle facts. Blackboard synthesis remains future authoring. |
| `v2/skill-update-aborts-on-uncommitted-log-file` | **cancel — verified obsolete primary fix, with live residue** | PR #635 / `74792cd2` fixed the log commit; PR #670 / `755e60de` removed `commands/launch_script.py::run_script_mode`. Replacement `launch_script.run_script_phase` (`src/coga/launch_script.py:180`) syncs before execution. `skill_manager._assert_no_unmerged_paths` (`src/coga/skill_manager.py:542`) still only checks unmerged files. | "Primary launcher-log fix already delivered by PR #635 (74792cd2); PR #670 (755e60de) then removed commands/launch_script.py::run_script_mode. The replacement launch_script.run_script_phase syncs its launch log before ticket.py. Surviving residue, not fixed by this cancellation: skill_manager._assert_no_unmerged_paths checks only --diff-filter=U, so an ordinary dirty tracked file that would be overwritten can still reach _checkout and fail with a raw Git error; a targeted dirty-file preflight remains follow-up work." |
| `v2/relay-design-repositories` | **keep-with-follow-up — partial delivery verified** | Subject: direction/gap/library-selection interview plus repo creation remains a proposal (`coga/tasks/v2/relay-design-repositories.md:32`). `commands.init._do_init` (`src/coga/commands/init.py:881`) requires an existing git worktree. `coga/workflows/build/onboarding.md:13` delivers an empty-repo interview, vision and starter tickets, not every requested element. Log at `coga/log.md:610` records a pause, not settlement. | None. Preserve paused state and owner `zach`; narrow to the undecided remainder and name delivered onboarding pieces. |
| `v2/add-relay-skill-search-with-candidate-eval` | **keep-with-follow-up — verified** | `coga skill --help` lists install, install-local, install-url, update, remove, status; no search. `commands.skill.app` / `install_url` (`src/coga/commands/skill.py:25,61`) and `skill_manager.SOURCE_METADATA` / `SOURCE_SCHEMA` (`src/coga/skill_manager.py:31`) survive under Coga names. Packaged `bootstrap/import` "Finding a candidate" still describes manual discovery. | None. Preserve discovery plus ranked import/adapt/skip recommendations; record current surfaces and defer engine and implementation-home choices. |

### Proposed shape

One small adjudication PR plus the approved lifecycle write; no feature build
or new follow-up tickets are required by this recommendation.

1. At implement, read the owner's verdict and recheck the live cohort on the
   control branch. The table is an allowlist, not a bulk-cancellation script.
   If intervening evidence defeats a verdict, record it and use the session's
   blocking protocol for any required new decision.
2. If approved unchanged, perform the sole cancellation from the control
   checkout before preparing cohort prose edits in the implementation checkout:
   `coga mark canceled v2/skill-update-aborts-on-uncommitted-log-file --message "<exact table reason>"`.
   Use that reason verbatim. Verify the CLI's recorded outcome; never replay
   prior transitions or synthesize this canceled draft. Naming the live bug
   in the reason is the preservation route expressly allowed by this ticket;
   it does not claim the bug is fixed or create a separate follow-up task.
3. Add a dated `### Premise review` beneath `## Context` in the three retained
   live proposals, with current evidence and remaining authoring work:
   - **Autotrigger:** preserve the concept-only scope, trigger/cardinality
     axes, OR semantics and owner questions. Explain current stable
     `recurring/<name>` identity, serviced-period ledger and orphan resume.
     Replace the "live cluster to read instead" dependency with the recovered
     background below and provenance commits; the two never-created names
     stay hypothetical. Mark old restock/mode prose as historical, without
     deciding trigger syntax, consent or migration. Leave the blackboard
     intact and record that synthesis is still due before activation.
   - **Repository design:** also narrow `## Description` to its undecided
     direction/gap interview, existing-skill/workflow selection, and creation
     from answers. Name vision capture and starter-ticket generation as
     delivered by onboarding, to reuse rather than build again. Correct the
     claim that init creates git repositories. Preserve acceptance criteria
     on generated tickets; let its own owner-led design decide whether to
     extend onboarding or retain a separate operation.
   - **Skill search:** record `src/coga/commands/skill.py`,
     `src/coga/skill_manager.py`, `.coga-source.json`, `coga.skill-source.v1`
     and the now-packaged import rubric as the current equivalents. Keep the
     inlined rubric and no-auto-install requirement. The instruction to add
     a Typer command in core is an unapproved placement proposal under today's
     microkernel rule; engine, sources, output and implementation home remain
     for the feature's own design.
4. Keep this substance in each retained draft's body so it survives this
   adjudication ticket's retirement. Preserve frontmatter and blackboards.
   Follow `code/implement` for isolation; do not run lifecycle transitions
   from a feature checkout containing unpublished cohort prose.
5. Record outcomes and exact verification commands on this blackboard. Run
   `git diff --check`, `coga validate --task <ref> --json` for this ticket and
   each of the four live refs, then `coga validate --json`. Expect the three
   baseline errors below unless documented sibling work changed them. This
   ticket uses existing commands and edits prose, so no new tests or full
   suite are needed. Finish the implement step with its normal bump.

### Out of scope

- Reopening prior verdicts; the 17 title-only stubs; the README stale-surfaces
  table and Dream routing policy.
- Synthesis of autotrigger to clear validation, or the two blackboards owned
  by `correct-the-v2-known-stale-surfaces-table-and-rout`.
- Building triggers, skill search, repository onboarding or the residual
  preflight guard; selecting those features' product decisions; activating
  or launching retained tickets; new CLI/config/context/template behavior.
- Cancellation, branches, code and PRs during this design step.

## Context

### Shared background (all three v2 triage tickets)

This ticket is one of three split out of `triage-the-v2-parking-area-empty-descriptions-prem`
(canceled 2026-09-02). Siblings: `correct-the-v2-known-stale-surfaces-table-and-rout`,
`adjudicate-the-eight-premise-dead-v2-drafts`, `interview-the-owner-on-the-17-title-only-v2-stubs`.

Origin: Dream 2026-08-24, Phase 2 knowledge scan (shards 06, 09, 11, 12), classified `gap`.
Re-verified against `main` 2026-09-02 plus an independent cold review. **Where these notes and the
original Dream findings disagree, these notes win.**

**The contract for this directory is `coga/tasks/v2/README.md`.** Its original subject/surface
questions remain the test requested here. PR #819 (`28cdbf4b`, 2026-09-17) added required-substance
recovery and already-delivered work checks. Apply the current contract without equating missing
provenance, renamed paths or an unbuilt proposal with a dead subject. Its green-validate guard
links to architecture's lifecycle rule.

**Counting `v2/` correctly.** `coga status v2 --all` reports **81 tasks** at this snapshot.
Flat `*.md` counts include the README and omit nested tickets, including the six under
`cleanup-core-commands/`; use the CLI's recursive task inventory, not Dream's older estimates.

**Validation snapshot, 2026-09-17.** `coga validate --json` exits 1 with 214 OK results,
49 warnings and **3 errors**, all `unsynthesized-draft-blackboard`: `v2/autotrigger-ticket-type`,
`v2/measure-relay-prompt-scope-and-agent-precision`, and `v2/use-worktree-when-starting-a-dev-task`.
The old four-error count predates split-context's rewrite. `validate.validate_task`
(`src/coga/validate.py:446`) checks synthesis only for drafts. The proposed cancellation is not
one of the errors and this ticket does not clear them. The two non-autotrigger syntheses belong
to `correct-the-v2-known-stale-surfaces-table-and-rout`. A green validate supplies no premise evidence.

### Four of the eight are already ruled — do not re-adjudicate them

Two sibling triage tickets reached these before this one activated; their
verdicts are in `coga/log.md` and are not reopened here.

- `audit-rules-md-usage-across-relay-and-decide-wheth` — **canceled** 2026-09-16
  by `adjudicate-parked-and-active-tickets-whose-premise` (premise-dead, reason
  in the log).
- `document-workflow-less-concept-capture-drafts-as-s` — **done** 2026-09-16 by
  the same ticket (closed as already satisfied by `coga/architecture`).
- `split-context-to-doc-user-accessible-and-editable` — **kept**, rewritten
  against current surfaces and guarded on the `redo-documentation` owner gate
  by the same ticket; it passes both README questions and must not be
  cancelled for the validate gate.
- `dev-loop-git-hygiene-lift-sync-with-main-into-code` — **done** 2026-09-12 by
  `four-parked-tickets-carry-premises-that-have-since` (already satisfied;
  evidence in its closing log line).

The remaining four (`autotrigger-ticket-type`, `skill-update-aborts-on-uncommitted-log-file`,
`relay-design-repositories`, `add-relay-skill-search-with-candidate-eval`)
are this ticket's live cohort. The old grading is retained below as historical
input; the current table and evidence supersede its stale facts and line
numbers, including the suggestion to cancel a ticket that is already done.

### Current evidence and implementation seams

- **Autotrigger:** `recurring.scan_due` / `recurring.create_template`
  (`src/coga/recurring.py`) use stable period identity and the serviced-period
  ledger. `recurring_runner.run_recurring_scan` resumes orphaned in-progress
  work. `mark.mark_in_progress` (`src/coga/mark.py`) still owns the start
  transition. Searches for `autotrigger`, `idle-eligible`, and idle/token-budget
  triggering in current source/contexts found no implementation; the token-budget
  match in config is rejection of removed megalaunch config. These findings
  establish an unbuilt subject, not an owner decision to build it. The draft
  already carries its two axes, OR semantics, concept-only scope, no-new-daemon
  constraint, and unresolved consent/file-shape questions; preserve them.
- **Recoverable autotrigger background:** resolving both file and directory
  tickets found six of seven cited slugs absent; only
  `v2/enforce-a-prompt-token-budget-in-compose` remains. Two absent names are
  explicitly planned, never-created proposals. The four retired hazard tickets
  were deleted under `relay-os/tasks/`, so searching only `coga/tasks/` history
  misses them. All four source bodies were recovered with
  `git show <deletion>^:relay-os/tasks/<slug>/ticket.md`:
  - `d7086ecd`, `detect-recurring-runs-that-mark-done-without-advan`: a domain
    cursor can stay stale despite nominal completion and repeat output. That
    concern is distinct from the scheduler's current serviced-period ledger;
    do not claim arbitrary domain-cursor advancement is enforced today.
  - `078dd705`, `recover-recurring-runs-orphaned-when-the-superviso`: resume
    stranded in-progress work at its existing step, skip done/paused work,
    and distinguish sequential retry from concurrent ownership. Its old
    no-concurrency assumption is historical, not a current guarantee.
  - `2584de1d`, `fix-recurring-templates-not-instantiated`: malformed schedules
    should fail per template without stopping healthy templates; its source
    records the fix as verified on 2026-06-17.
  - `c008c23b`, `enforce-mode-auto-for-recurring-templates`: unattended work
    must not wait for unavailable input. Its proposed mode enforcement is
    obsolete; current conduct and ticket.py dispatch are in `coga/architecture`.
  Inline this bounded background, keeping commits as provenance. These are
  historical hazards, not four new build requirements for a concept draft.
- **Skill-update:** `git show 74792cd2 -- src/coga/commands/launch_script.py`
  proves PR #635 added `git.sync_log` before subprocess execution; PR #670 /
  `755e60de` deleted that implementation. Current `launch_script.run_script_phase`
  (`src/coga/launch_script.py:180`) retains the pre-run sync.
  `skill_manager.run_skill_update_pr_flow` calls `_assert_no_unmerged_paths`,
  then `_commit_skill_updates`, which calls `_checkout` against the control
  branch (`src/coga/skill_manager.py:479,542,590`). The preflight only uses
  `--diff-filter=U`; ordinary tracked dirt that conflicts with checkout can
  pass and produce the raw error. Not every dirty file blocks checkout. This
  ticket neither fixes the residue nor authorizes stashing/committing unrelated work.
- **Repository design:** `aliases.DEFAULT_ALIASES` (`src/coga/aliases.py:59`)
  maps build to `launch coga-build`; PR #701 / `ef721d2f` restored onboarding
  while leaving project removed. `commands.init._do_init` requires an existing
  git worktree and seeds onboarding only for an empty repo. The
  `gather-and-spec` and `generate-batch` sections of
  `coga/workflows/build/onboarding.md` deliver an interview, agreed
  `product/vision` context and starter tickets. They do not require the draft's
  entire direction/gap/library-selection interview or create a repository from
  answers. Packaged `bootstrap/ticket` remains an interview precedent. The
  proposal's log/history records creation, activation and pause; no settlement
  of that remainder was found. Partial overlap warrants narrowing, not closure.
- **Skill search:** `commands.skill.app` registers no search command;
  `commands.skill.install_url` calls `skill_manager.install_url_skill`, whose
  metadata uses `SOURCE_METADATA` and `SOURCE_SCHEMA`. The import process now
  lives at `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/import/SKILL.md`;
  its manual discovery is not the proposed query/rank command. The draft's
  inlined rubric makes the retired import-ticket citation provenance only.
  `coga/current-direction`'s missing-skill decision rejects a static gap lint,
  not search. `coga/codebase`'s microkernel rule governs implementation home,
  not whether this capability request still exists.
- **Lifecycle and composition:** `commands.mark.canceled` delegates to
  `mark.mark_canceled`, preserving body/blackboard while clearing the step and
  generation, recording the reason, syncing and notifying. Use that command,
  not hand-written status or audit edits. `compose._extract_section`
  (`src/coga/compose.py`) stops at the next `##` heading; required spec content
  therefore stays beneath Description or Context.

### Historical cohort grading — retained input, not the current action list

**Confirmed dead (evidence verified — cancel is correct):**
- `audit-rules-md-usage-across-relay-and-decide-wheth` — `rules.md` survives only as a stale-artifact
  fixture in a prune test (`tests/test_init.py:1379`); the "Global rules" compose layer it audits is
  gone (`grep rules src/coga/compose.py src/coga/paths.py` is empty).
- `document-workflow-less-concept-capture-drafts-as-s` — deliverable shipped at
  `coga/contexts/coga/architecture/SKILL.md:363-400`, which names the exact validator-nagging
  problem the draft was written about.

**Subject was never built, not deleted — this is NOT the README's premise test:**
- `autotrigger-ticket-type` — the evidence offered was "every cross-reference dead" (6 of 7 named
  slugs confirmed absent). But dead cross-references make a draft harder to *act on*; they do not
  make its subject gone. Recurring is alive (`src/coga/recurring_runner.py`, three workflows under
  `coga/workflows/`), so the proposed recurring+idle trigger unification was never built.
  Re-adjudicate on the README's actual two questions.

**Cancel only if the surviving residue is named in the reason:**
- `skill-update-aborts-on-uncommitted-log-file` — the stated root cause is genuinely gone
  (`src/coga/commands/launch_script.py` and `run_script_mode` no longer exist). But its secondary
  finding is live: `_assert_no_unmerged_paths` (`src/coga/skill_manager.py:417`) still filters on
  `--diff-filter=U` only, so an ordinary dirty tracked file still walks past it into `_checkout`
  (line 488). A bare cancel silently drops a real bug — either name the residue in the cancel reason
  or open a follow-up for it.

**Asserted with no recorded evidence — re-derive before touching:**
- `dev-loop-git-hygiene`, `relay-design-repositories`, and
  `split-context-to-doc-user-accessible-and-editable` were each given a one-clause reason ("settled
  the other way", "question answered by shipped precedent") with no pointer to where that settlement
  is recorded. Find the evidence or downgrade the verdict.
- `add-relay-skill-search-with-candidate-eval` was listed as settled and **is not**. `coga skill`
  exposes install / install-local / install-url / update / remove / status — there is no `search`.
  The subject was never built, the surfaces it names are still live, and `coga/log.md` records no
  decision, cancel, or counter-ticket. It passes both of the README's questions. **Do not cancel
  this one** absent new evidence.

<!-- coga:blackboard -->

## Design handoff — 2026-09-17

- Design complete on `main`, evidence baseline `d4c7445b`. Only this ticket
  was edited. No cohort transitions, branches, code, manual commits or PRs were made.
- Table preserves four prior rulings and proposes one new cancel (skill-update)
  plus three keeps with bounded follow-up. The key new receipt is PR #635:
  the launcher bug was fixed before its implementation was deleted in #670;
  the separate ordinary-dirty-file preflight bug still survives.
- Applied the README's newly shipped four-question contract. Recovered all
  four retired autotrigger hazard bodies from pre-rename history and recorded
  the substance under Context. Onboarding only partly covers repository design;
  skill search remains unbuilt. No evidence justifies canceling either.
- Proposed implementation fits one small prose PR plus one approved CLI
  transition; no split or new feature work is needed. Next frozen step is
  `evaluate-design`, followed by the owner's approval gate. No approval inferred.

## Verification

- `git diff --check` — passed.
- `coga validate --task adjudicate-the-eight-premise-dead-v2-drafts --json` — passed.
- `coga validate --task v2/skill-update-aborts-on-uncommitted-log-file --json` — passed, still draft.
- `coga validate --task v2/relay-design-repositories --json` — passed, still paused.
- `coga validate --task v2/add-relay-skill-search-with-candidate-eval --json` — passed, still draft.
- `coga validate --task v2/autotrigger-ticket-type --json` — expected exit 1,
  only `unsynthesized-draft-blackboard`.
- `coga validate --json` — exit 1, three baseline synthesis errors named in
  Context; `coga status v2 --all` — 81 tasks.
- Source `compose._extract_section` check passed: unchanged frontmatter,
  exactly one fence, only Description/Context body regions, all four spec
  subsections and all eight verdict rows survive extraction. No tests added
  or suite run for this design-only ticket edit.

## Open Questions

1. At `review-design`, approve or change the exact skill-update cancellation
   reason and its residue-preservation route. The recommendation uses the
   expressly permitted reason-only route; if the owner wants a separately
   actionable follow-up or to retain/narrow that draft instead, record that
   decision before implementation. No cancellation has occurred.
2. Whether repository creation and explicit direction/gap/library selection
   are still wanted is unresolved by shipped onboarding. The proposed keep
   leaves that product decision with `zach` in the paused ticket's own design;
   it need not be answered to preserve the ticket in this adjudication.

## Evaluator review

Independent cold review, 2026-09-17, against `main` / local `origin/main`
`0f5e2b55`. Since the design's `d4c7445b` snapshot, only this ticket and
`coga/log.md` changed; no cohort or source drift changes the recommendation.

**Verdict: ready for owner review. No must-fix design defects found.** The
body alone defines the eight-row allowlist, exact cancellation reason,
retained-ticket edits, lifecycle ordering and verification exceptions. It is
implementable as one prose PR plus the separately approved CLI transition.
This review does not approve cancellation: the owner still decides the table
and reason-only preservation of the dirty-file preflight bug at `review-design`.

### Evidence checked

- **Prior verdicts:** the rules-audit cancellation and workflow-less draft's
  done outcome match their current frontmatter and the 2026-09-16 entries in
  `coga/log.md`. The dev-loop done entry on 2026-09-12 and deletion commit
  `b73b20d0` support leaving that absent ticket absent. Split-context's body
  retains the `redo-documentation-dir-and-merge-it-with-context-b` owner gate
  from `23420a91` / PR #826. None requires a replayed transition.
- **Sole proposed cancellation:** `git show 74792cd2 --
  src/coga/commands/launch_script.py` confirms the PR #635 pre-run log sync;
  `755e60de` deletes that implementation. Current
  `src/coga/launch_script.py::run_script_phase` still syncs before executing
  the attachment. `src/coga/skill_manager.py::run_skill_update_pr_flow`,
  `_assert_no_unmerged_paths`, `_commit_skill_updates` and `_checkout`
  confirm the distinct ordinary-dirt gap. The exact reason preserves that
  gap without claiming every dirty file prevents checkout.
- **Autotrigger:** `src/coga/recurring.py::scan_due`, `create_template`,
  `DueTask.launchable` and `_record_run`, together with
  `src/coga/recurring_runner.py::run_recurring_scan`, substantiate stable
  identity, the log ledger and orphan resume. Source search finds no idle
  trigger unification. All four cited historical bodies are recoverable at
  the specified parents (`d7086ecd`, `078dd705`, `2584de1d`, `c008c23b`);
  their contents support the proposed bounded background. Recovering it
  into the retained draft meets README question 3 without treating those
  historical hazards as four new feature requirements.
- **Other keeps:** `src/coga/commands/init.py::_do_init` requires an existing
  git worktree; `coga/workflows/build/onboarding.md`'s `gather-and-spec` and
  `generate-batch` deliver vision and starter tickets, not the entire repo
  proposal. Its pause and owner `zach` remain current. `coga skill --help`,
  `src/coga/commands/skill.py::app`, the source-metadata constants in
  `src/coga/skill_manager.py`, and packaged `bootstrap/import`'s
  `Finding a candidate` section support keeping search. Its implementation
  home properly remains undecided under `coga/codebase`'s microkernel rule.
- **Execution contract:** the frozen workflow matches packaged
  `code/design-then-implement`: evaluator, then owner approval, then implement.
  `src/coga/mark.py::mark_canceled` preserves body/blackboard, clears lifecycle
  fields and writes the reason through the audit/sync path; existing
  `tests/test_mark.py` cancellation cases cover draft eligibility.
  `src/coga/validate.py::validate_task` and
  `tests/test_validate.py::test_authoring_blackboard_error_is_draft_only`
  support the stated synthesis exception. No new core or policy work is needed.

### Optional recommendation

In skill search's planned `### Premise review`, explicitly label the
`detect-missing-skills` link as historical. Its current Context and Out of
scope still describe that ticket as a future trigger/owner, whereas
`coga/current-direction`'s `Recent decisions (missing-skill detection)`
records its closure and no programmatic handoff. This is not a prerequisite
for search and does not weaken the keep verdict; the clarification fits the
already-scoped prose edit.

### Review verification

Re-ran the exact five targeted `coga validate --task ... --json` commands
listed under `## Verification`: this ticket, skill-update, repository design
and skill search pass; autotrigger alone reports the expected
`unsynthesized-draft-blackboard`. `coga validate --json` still exits 1 with
214 OK, 49 warnings and the same three synthesis errors. `coga status v2 --all`
still reports 81 tasks. Existing lifecycle, validation and skill-preflight
tests were inspected; no tests or feature changes were made in this review.
