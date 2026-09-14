---
title: Interview the owner on the 17 title-only v2 stubs
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

17 of the 81 tasks in `coga/tasks/v2/` have an empty `## Description`, and every one is a title-only
stub: frontmatter, an empty `## Description`, an empty `## Context`, the placeholder blackboard,
328–714 bytes total. There is nothing in the repo to reconstruct intent from — for `model-selector`
and `add-subproject` the entire informational payload is the slug.

So this is not an editing task. The owner has chosen to be interviewed on each of the 17: recover
the real intent where it still exists, and cancel with a recorded reason where it does not. The v2
README's premise check cannot be run on these drafts until they have a description to check.

### Acceptance criteria

- [ ] The owner has given a verdict — `describe` or `cancel` — for each of the 17 stubs, recorded in
      the verdict table on this ticket's blackboard, with the owner's own words for every `describe`.
- [ ] For every `describe` verdict, the stub's `## Description` in `coga/tasks/v2/<slug>.md` is
      filled from the owner's answer and the `## Context` carries the codebase facts found in the
      interview (what shipped, what it duplicates, what surface it names). Nothing in either section
      is inferred from the slug alone.
- [ ] For every `cancel` verdict, `coga mark canceled v2/<slug> --message "<reason>"` has been run
      with the reason from the table (premise dead / duplicate of `<slug>` / already shipped in
      `<commit or ticket>` / intent no longer recoverable).
- [ ] `coga/tasks/v2/README.md` and `coga/tasks/v2/cleanup-core-commands/README.md` are untouched.
- [ ] `coga status v2 --all` still reports 81 tasks (cancels change status, not count), and no stub
      in the list of 17 still has an empty `## Description` while in `status: draft`.
- [ ] `coga validate --json` shows no new ERRORs.

### Proposed shape

This is a ticket-data change, not a code change; the implement step needs no branch beyond what the
workflow requires and touches only `coga/tasks/v2/*.md`.

1. Read the verdict table on the blackboard (owner-approved at `review-design`). It is the only
   input. Outcome of the interview: **1 describe, 16 cancels.**
2. The one `describe` row (`pick-model-on-workflow-to-save-on-cost`): open
   `coga/tasks/v2/pick-model-on-workflow-to-save-on-cost.md`, replace the empty `## Description`
   with the text quoted verbatim on the blackboard ("Text for the one `describe`"), and put the
   grep findings for that stub under `## Context`. Keep frontmatter untouched; it stays
   `status: draft` with `workflow: null` — the owner explicitly does not want it pulled forward.
3. For each of the 16 `cancel` rows: `coga mark canceled v2/<slug> --message "<cancel reason
   column>"`. One command per stub, in table order; the message is the audit trail in
   `coga/log.md`. `model-selector` is canceled as `duplicate of v2/pick-model-on-workflow-to-save-on-cost`.
4. Run `coga validate --json` and `coga status v2 --all`; record both results on the blackboard.
   Expected: 81 tasks, 16 newly `canceled`, no `unsynthesized-draft-blackboard` ERROR introduced
   (the rule fires only on `status: draft`; the one described draft has a synthesized description).

### Out of scope

- The 8-draft premise-dead cohort (`adjudicate-the-eight-premise-dead-v2-drafts`) and the README
  stale-surfaces table (`correct-the-v2-known-stale-surfaces-table-and-rout`).
- Pulling any described stub forward, giving it a workflow, or launching it. A `describe` verdict
  only makes the draft premise-checkable; it does not schedule it.
- Adding a validator for title-only tickets — that is
  `title-only-tickets-have-no-convention-and-no-valid`.
- Editing `coga/tasks/v2/README.md` or the `cleanup-core-commands/` index.

## Context

### Shared background (all three v2 triage tickets)

This ticket is one of three split out of `triage-the-v2-parking-area-empty-descriptions-prem`
(canceled 2026-09-02). Siblings: `correct-the-v2-known-stale-surfaces-table-and-rout`,
`adjudicate-the-eight-premise-dead-v2-drafts`, `interview-the-owner-on-the-17-title-only-v2-stubs`.

Origin: Dream 2026-08-24, Phase 2 knowledge scan (shards 06, 09, 11, 12), classified `gap`.
Re-verified against `main` 2026-09-02 plus an independent cold review. **Where these notes and the
original Dream findings disagree, these notes win.**

**The contract for this directory is `coga/tasks/v2/README.md`.** Read it first — it defines the
two-question premise check (does the subject still exist? do the surfaces it names still resolve?)
and records the `decide-the-fate-of-two-premise-dead-v2-drafts-whos` cancellation precedent.

**Counting `v2/` correctly.** `coga status v2 --all` reports **81 tasks**. Do not count with
`ls coga/tasks/v2/*.md` — that returns 76, counting the `cleanup-core-commands/` directory as one
entry and missing its six children. The Dream scan's "~75" and "18" are both this artifact.

**`coga validate` state.** 4 ERRORs repo-wide, all `unsynthesized-draft-blackboard`, all under
`v2/`. The rule fires only on `status == "draft"` (`src/coga/validate.py:447`), so each clears by
cancelling or synthesizing. Everything else `coga validate` prints is a WARN. Two errors clear in
`correct-the-v2-known-stale-surfaces-table-and-rout`, two in
`adjudicate-the-eight-premise-dead-v2-drafts`. **A green validate is never a reason to cancel a
draft** — it is a consequence of correct verdicts, never an input to them.

### Writing a Description inferred from the slug is forbidden

That fabricates a record of what someone wanted at the time, which is the precise failure
`coga/tasks/v2/README.md:15-19` exists to prevent. If the owner has no intent left for a stub, the
correct outcome is a cancel with a recorded reason — not a plausible-sounding paragraph. Sample
titles show how little is recoverable: `docs-and-contt-block-should-be-merged`,
`remote-stale-command-line-toosl`, `generic-lib-to-use-e-g-patent-models`.

### The 17

`add-subproject`, `autoroute-agent-based-on-remaining-usage`,
`create-vault6-and-service-account-for-high-trust-s`,
`create-vault-and-service-account-for-mid-trust-sec`, `docs-and-contt-block-should-be-merged`,
`generic-lib-to-use-e-g-patent-models`, `in-general-relay-files-should-be-easier-to-access`,
`manage-security-and-pii`, `model-selector`, `pick-model-on-workflow-to-save-on-cost`,
`project-manager-split-spec-in-tickets-block`, `remote-stale-command-line-toosl`,
`script-mode-to-activate`, `simplify-command-lines`, `sync-support-files-and-bare-ticket-authoring`,
`update-all-doesn-t-copy-workflow-correctly-to-atta`, `why-ai-asks-me-to-bump-instead-of-doing-it`.

**Two files a naive glob also flags are directory indexes that must never receive a Description:**
`coga/tasks/v2/README.md` and `coga/tasks/v2/cleanup-core-commands/README.md`. The latter reads
"Launch one of the child tickets below, not this file", and its six children all have real
Descriptions. The Dream scan's count of "18" was this artifact; the real number is 17.

### Running the interview

The `design` step is the interview. Before asking about a stub, spend a moment grepping for its slug
and title across `coga/`, `src/`, and `coga/log.md` — some will have left traces that make the
owner's recall much cheaper, and a few may turn out to be already-shipped. Bring what you found to
each question rather than asking cold.

Produce a table — slug, title, what you found, the owner's answer, resulting verdict (describe /
cancel) — and get it approved at `review-design`. The `implement` step then writes the descriptions
and runs the confirmed cancels: `coga mark canceled v2/<slug> --message "<reason>"`.

`script-mode-to-activate` deserves a flag when you reach it: the `mode:`/`script:` machinery it names
is gone from core (see the stale-surfaces table, and `src/coga/ticket.py:74`), so it is a strong
premise-dead candidate — but confirm with the owner rather than assuming.

### What the pre-interview grep found (2026-09-12)

Every one of the 17 was empty from the commit that created it — `git log --follow -p` shows no
body line was ever added (rename detection chains empty stubs into unrelated files, so ignore
`--follow` output past the first creation commit). There is nothing further to recover from git.
Per-stub facts the implement step should carry into `## Context` for any `describe` verdict:

| slug | created | what still resolves today |
| --- | --- | --- |
| `add-subproject` | 2026-06-06 | No "subproject" concept in `src/`, contexts, docs, or `coga.toml`. Cold. |
| `autoroute-agent-based-on-remaining-usage` | 2026-06-09 | Folded "as superseded" into `nightly-auto-drain-run-for-ready-tickets` (`:155,:223`), which is itself `canceled`. `coga usage` (`src/coga/commands/usage.py`) exists; no routing on it anywhere in `launch.py`. |
| `create-vault6-and-service-account-for-high-trust-s` | 2026-07-20 (zach) | `coga/contexts/coga/secrets/SKILL.md:16-40` now rules **one SA, one automation vault**; trust-tiered vaults are a human taxonomy the SA is never granted, and widening scope is a migration. A second SA/vault contradicts the recorded model. |
| `create-vault-and-service-account-for-mid-trust-sec` | 2026-07-20 (zach) | Same as above. |
| `docs-and-contt-block-should-be-merged` | 2026-06-15 | Empty duplicate of `redo-documentation-dir-and-merge-it-with-context-b` (`in_progress`, `:753` classifies it so); also listed by `the-human-doc-vs-agent-context-boundary-is-decided:52`, `adjudicate-parked-and-active-tickets-whose-premise:74`, and Dream D21. |
| `generic-lib-to-use-e-g-patent-models` | 2026-05-27 | Only echo: `ship-a-shared-recurring-reminder-engine-battery` (`canceled`) named patents/admin hand-rolled sweep logic as the shared-lib case. No `patent` anywhere in `src/`. |
| `in-general-relay-files-should-be-easier-to-access` | 2026-06-15 | `move-cogacontext-to-roodoc-so-its-easier-for-human` is `done` (moved the contexts dir, added `[layout] contexts`). Possibly the same ask, already shipped. |
| `manage-security-and-pii` | 2026-05-29 | `coga/secrets` context covers secrets; `v2/document-untrusted-tool-output-verify-through-grou:47` explicitly says this stub is "about secrets/PII, not output-trust". Nothing on PII exists. |
| `model-selector` | 2026-06-09 | No `model` key in `[agents.claude]`/`[agents.codex]` (`coga/coga.toml:19-39`) or `config.py`. Same idea as the next row. |
| `pick-model-on-workflow-to-save-on-cost` | 2026-07-20 | As above — per-step model choice does not exist. Two stubs, one feature. |
| `project-manager-split-spec-in-tickets-block` | 2026-06-11 | No PM skill or workflow. `code/design` step 5 already says "split the ticket if it is too big"; `coga block` is the block half. |
| `remote-stale-command-line-toosl` | 2026-06-15 | Read as "remove stale command-line tools": `v2/cleanup-core-commands/` (six children, esp. `residual-command-surfaces`) is the live parked home for that. |
| `script-mode-to-activate` | 2026-05-31 | `mode:` frontmatter is **gone** (README stale-surfaces table; `src/coga/ticket.py`). `ticket.py` sibling is the replacement. Premise-dead candidate. |
| `simplify-command-lines` | 2026-06-11 | Same territory as `v2/cleanup-core-commands/`. |
| `sync-support-files-and-bare-ticket-authoring` | 2026-06-03 | `src/coga/authoring.py:105` `support_paths()` + commit message `"Ticket authoring — support files"` (`:126`) shipped in #491 (2026-07-01). Looks **already shipped**. |
| `update-all-doesn-t-copy-workflow-correctly-to-atta` | 2026-05-26 | `relay init --update --all` added 2026-05-22 (9a05f49a), **removed** 2026-06-26 (#461, 03fd0c37). The command the bug is against no longer exists. Premise-dead. |
| `why-ai-asks-me-to-bump-instead-of-doing-it` | 2026-06-09 | `src/coga/resources/prompt.md:17-21` now mandates "run `bump` as the *last* thing in the step". Likely shipped by the base-prompt rewrite. |

### Escalation

Step 1 launched by the owner runs attended, so ask directly. If no human is reachable — the
`coga launch` supervisor auto-chains agent steps — the correct action is
`coga block --task <slug> --reason "<the 17 questions>"`. Do not write descriptions unattended and
do not defer the decisions to a later step.

### Out of scope

The 8-draft premise-dead cohort and the README stale-surfaces table — both sibling tickets. These 17
are not part of that cohort.

<!-- coga:blackboard -->

## Evaluator review

Reviewed 2026-09-13 against checkout `29dc07f8`, from the perspective of a new
implementer. The Description, Acceptance criteria, Proposed shape, and Out of
scope were assessed before using the blackboard as the explicitly referenced
execution input.

**Verdict: ready for owner review; no must-fix findings.** The 17-row table and
the supplied Description text make this a bounded ticket-data change. The
recorded owner answers support one describe and 16 cancels. The owner gate
still approves the final wording and execution; this review does not do so.

### Must resolve before implementation

None. The model-selection scope is deliberately undecided because this task
only makes a parked draft legible. Choosing a model-selection implementation
now would exceed the stated scope.

### Verified evidence

- All 17 exact target files exist, remain `draft`, and have empty Description
  and Context sections with placeholder blackboards. The surviving
  `v2/pick-model-on-workflow-to-save-on-cost` has `workflow: null` as specified.
  Of the canceled targets, `v2/sync-support-files-and-bare-ticket-authoring`
  carries a frozen workflow and step; the other 15 have no workflow.
- `src/coga/mark.py::mark_canceled` accepts drafts, validates the prospective
  terminal state, clears `step`, preserves the body/blackboard, and appends the
  supplied reason to the global log. Existing
  `tests/test_mark.py::test_mark_canceled_from_every_non_terminal_status` and
  `test_mark_canceled_accepts_workflow_less_draft` cover both target shapes.
  The commands can run sequentially inside this parent task:
  `src/coga/repl_supervisor.py::_sentinel_signals_done` matches the target's
  identity, so canceling a different ticket does not end the parent session.
- The model facts resolve to `src/coga/config.py::AgentType` /
  `_ALLOWED_AGENT_KEYS`, `src/coga/workflow.py::WorkflowStep`, the shared
  `coga/coga.toml` agent tables, and `src/coga/commands/launch.py`. There is no
  first-class model field or per-step model routing. Use that full launch path
  when writing the surviving draft's Context.
- Cancellation evidence checked: `coga/contexts/coga/secrets/SKILL.md`,
  "The service account and its vault"; the canceled
  `coga/tasks/nightly-auto-drain-run-for-ready-tickets.md` and its explicit
  supersession decision; the related-work section of
  `coga/tasks/redo-documentation-dir-and-merge-it-with-context-b.md`; the done
  `coga/tasks/move-cogacontext-to-roodoc-so-its-easier-for-human.md` and
  `src/coga/config.py::_parse_layout`; `coga/skills/code/design/SKILL.md`, step
  5; the six-child cleanup index; `src/coga/launch_script.py::SCRIPT_ENTRY_POINT`;
  and `src/coga/resources/prompt.md`, "The loop". Commit `f08a274e` (#491)
  contains `authoring.support_paths`; commit `03fd0c37` (#461) removes the
  update/init-update surfaces. These checks support the recorded dispositions
  without deriving new intent from the titles.
- `src/coga/tasks.py::list_tasks` recurses into the six-child cleanup directory
  and excludes README indexes. `coga status v2 --all` returned **81 tasks**:
  62 draft, 11 paused, 1 in_progress, 1 done, 6 canceled. Absent unrelated
  changes, implementing this table leaves 46 draft and 22 canceled, still 81.
- The frozen workflow matches the packaged
  `src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md`:
  this evaluator hands off to owner `review-design`; branch and PR gates apply
  later. Inline Context supplies the relevant references. No core behavior,
  template, fixture, or protected README change is needed.

### Optional recommendations

1. **Refresh the validation baseline.** "Shared background" says four ERRORs,
   but `coga validate --json` currently exits 1 with **five ERRORs and 28 WARNs**.
   The fifth is `broken-skill` on `recurring/digest`, referencing the removed
   `coga/digest/flush` skill. The four `unsynthesized-draft-blackboard` errors
   remain on `v2/autotrigger-ticket-type`,
   `v2/measure-relay-prompt-scope-and-agent-precision`,
   `v2/split-context-to-doc-user-accessible-and-editable`, and
   `v2/use-worktree-when-starting-a-dev-task`. Compare error identities before
   and after implementation, rather than treating exit 1 as a regression or
   relying on the old count. None belongs to these 17 stubs.
2. **Clarify the write scope.** The body-only ambiguity was "touches only
   `coga/tasks/v2/*.md`" versus the same Proposed shape's required global audit
   writes and parent-blackboard results. Read the glob as the target-content
   scope, with CLI-managed audit/lifecycle writes and this ticket's handoff
   notes explicitly allowed. `mark_canceled` also publishes cancellation
   evidence to control immediately, including from a feature branch; see
   `tests/test_mark.py::test_mark_canceled_on_feature_lands_union_evidence_on_control`.
   The later PR gate therefore does not make the 16 cancellations one atomic
   PR change. The prior owner verdict gate supplies the intended approval.
3. **Narrow the #6 grep claim if updating the supporting notes.** "No `patent`
   anywhere in `src/`" is literally false: `config.Config.extensions` and
   `_parse_extensions` include patent examples, and packaged skill prose also
   mentions patents. There is also a parked retry at
   `coga/tasks/v2/ship-a-shared-recurring-reminder-engine-battery.md`, separate
   from the canceled root ticket. These are not recovered intent for
   `generic-lib-to-use-e-g-patent-models`; its owner-confirmed cancellation
   reason remains "intent no longer recoverable".

### Verification and handoff

- `coga status v2 --all` — exit 0; the baseline above.
- `coga validate --json` — exit 1; the five pre-existing ERRORs listed above.
- `coga validate --task interview-the-owner-on-the-17-title-only-v2-stubs --json`
  — exit 0, no issues.
- Source, relevant existing tests, and historical commits were inspected;
  pytest was not run for this prose-only evaluation. Only this review section
  was authored. Ticket intent/frontmatter, all 17 targets, and both README
  indexes were left untouched before the required workflow handoff.

## Design step — 2026-09-12 → 2026-09-13

**Status: interview complete; spec final.** The 17 questions went out via `coga block` on
2026-09-12 (megalaunch session, input unavailable). The owner answered on 2026-09-13 through
`coga unblock` (see Blockers below) and, in the attended relaunch the same day, settled the one
open point: #10 is **described from the owner's own words**, not kept title-only. The verdict
table below is the deliverable of `review-design` and the only input the implement step reads.
Owner may still edit the #10 wording at `review-design`.

Net result: **1 describe, 16 cancels.** Everything not depending on the answers was done on
2026-09-12: spec skeleton under `## Description`, per-stub grep findings under `## Context`
("What the pre-interview grep found").

## Verdict table (owner-approved 2026-09-13)

| # | slug | found | owner's answer | verdict | cancel reason (`--message`) |
| --- | --- | --- | --- | --- | --- |
| 1 | `add-subproject` | nothing anywhere | accept lean | cancel | intent no longer recoverable |
| 2 | `autoroute-agent-based-on-remaining-usage` | superseded by canceled `nightly-auto-drain-run-for-ready-tickets` | accept lean | cancel | premise dead: folded into nightly-auto-drain-run-for-ready-tickets, itself canceled |
| 3 | `create-vault6-and-service-account-for-high-trust-s` | contradicts `coga/secrets` one-SA/one-vault rule | accept lean | cancel | premise dead: coga/secrets rules one SA, one automation vault; trust-tiered vaults are human-only |
| 4 | `create-vault-and-service-account-for-mid-trust-sec` | same | accept lean | cancel | premise dead: coga/secrets rules one SA, one automation vault; trust-tiered vaults are human-only |
| 5 | `docs-and-contt-block-should-be-merged` | duplicate of live `redo-documentation-dir-and-merge-it-with-context-b` | accept lean (duplicate) | cancel | duplicate of redo-documentation-dir-and-merge-it-with-context-b |
| 6 | `generic-lib-to-use-e-g-patent-models` | only echo is canceled reminder-engine ticket | accept lean | cancel | intent no longer recoverable |
| 7 | `in-general-relay-files-should-be-easier-to-access` | `move-cogacontext-to-roodoc-so-its-easier-for-human` done | accept lean (shipped) | cancel | already shipped in move-cogacontext-to-roodoc-so-its-easier-for-human |
| 8 | `manage-security-and-pii` | secrets covered by `coga/secrets`; PII never specified | accept lean | cancel | intent no longer recoverable; secrets half covered by coga/secrets context |
| 9 | `model-selector` | twin of #10 | accept lean (duplicate of 10) | cancel | duplicate of v2/pick-model-on-workflow-to-save-on-cost |
| 10 | `pick-model-on-workflow-to-save-on-cost` | feature absent; no `model` key in `[agents.*]` | "it is a v2 item — leave it in v2/ as the surviving model-selection stub, do not cancel and do not pull it forward; no per-step/agent/ticket decision yet." Describe from these words (confirmed attended 2026-09-13). | **describe** | — |
| 11 | `project-manager-split-spec-in-tickets-block` | design step already splits; `coga block` exists | accept lean | cancel | premise dead: code/design step 5 already splits oversized tickets and coga block covers the block half |
| 12 | `remote-stale-command-line-toosl` | covered by `v2/cleanup-core-commands/` | accept lean | cancel | duplicate of v2/cleanup-core-commands/ |
| 13 | `script-mode-to-activate` | `mode:` frontmatter gone | accept lean | cancel | premise dead: mode:/script: frontmatter removed; ticket.py sibling replaced it |
| 14 | `simplify-command-lines` | covered by `v2/cleanup-core-commands/` | accept lean | cancel | duplicate of v2/cleanup-core-commands/ |
| 15 | `sync-support-files-and-bare-ticket-authoring` | shipped in #491 | accept lean (shipped #491) | cancel | already shipped in #491 (authoring.support_paths) |
| 16 | `update-all-doesn-t-copy-workflow-correctly-to-atta` | `init --update --all` removed in #461 | accept lean (premise-dead, #461) | cancel | premise dead: relay init --update --all removed in #461 |
| 17 | `why-ai-asks-me-to-bump-instead-of-doing-it` | base prompt mandates bump-last | accept lean (shipped) | cancel | already shipped in the base-prompt rewrite (prompt.md mandates bump as last act) |

### Text for the one `describe` (#10) — implement step writes this verbatim

`## Description` of `coga/tasks/v2/pick-model-on-workflow-to-save-on-cost.md`:

> Pick the model per workflow to save on cost. This is the surviving model-selection stub
> (`model-selector` was canceled as its duplicate). It stays a v2 item: not canceled, not pulled
> forward. Whether the choice lives per workflow step, per agent in `[agents.*]`, or per ticket is
> not yet decided — that is the first question whoever pulls this forward must answer.

`## Context`: the grep facts from the table row — no `model` key exists in `[agents.claude]` /
`[agents.codex]` (`coga/coga.toml:19-39`) or in `src/coga/config.py`; `launch.py` does no model
routing; `model-selector` (created 2026-06-09) was the other half, canceled as duplicate.

## Open Questions

None outstanding. All 17 answered 2026-09-13 (16 via `coga unblock`, #10 wording confirmed in the
attended relaunch). The owner may still edit the #10 Description text at `review-design`.

## Blockers

- [x] [2026-09-12 22:10] [agent:claude] id=20260912T221018 Interview needed: a describe/cancel verdict per stub (full questions + grep findings in the ticket blackboard 'Open Questions'). Agent leans in brackets; a 'describe' needs your own words. 1 add-subproject [nothing exists; cancel unless recalled]. 2 autoroute-agent-based-on-remaining-usage [folded into nightly-auto-drain, itself canceled; cancel or still wanted?]. 3+4 create-vault6/create-vault…-trust (zach) [coga/secrets now rules one SA one vault; cancel as decided-against?]. 5 docs-and-contt-block-should-be-merged [duplicate of live redo-documentation-dir; cancel?]. 6 generic-lib-to-use-e-g-patent-models [no trace; what was the lib, or cancel?]. 7 in-general-relay-files-should-be-easier-to-access [move-cogacontext shipped; whole ask, or more?]. 8 manage-security-and-pii [secrets covered; was PII a real ask?]. 9+10 model-selector / pick-model-on-workflow-to-save-on-cost [same feature; keep pick-model, cancel model-selector? what is selected per: step, agent, ticket?]. 11 project-manager-split-spec-in-tickets-block [design step already splits; distinct PM skill or cancel?]. 12 remote-stale-command-line-toosl [read as 'remove stale CLI tools' = cleanup-core-commands; cancel?]. 13 script-mode-to-activate [mode: gone; cancel premise-dead?]. 14 simplify-command-lines [cleanup-core-commands; cancel?]. 15 sync-support-files-and-bare-ticket-authoring [shipped in #491 authoring.support_paths; cancel?]. 16 update-all-doesn-t-copy-workflow-correctly-to-atta [init --update --all removed in #461; cancel premise-dead?]. 17 why-ai-asks-me-to-bump-instead-of-doing-it [base prompt now mandates bump-last; cancel as shipped, or still happening?]
  resolved: [2026-09-13 15:44] [human:nicktoper] Owner verdicts (2026-09-13, via bootstrap/orient): accept the agent lean on every stub except #10. Cancel 1 add-subproject, 2 autoroute-agent-based-on-remaining-usage, 3 create-vault6-…-high-trust-s, 4 create-vault-…-mid-trust-sec, 5 docs-and-contt-block-should-be-merged (duplicate), 6 generic-lib-to-use-e-g-patent-models, 7 in-general-relay-files-should-be-easier-to-access (shipped), 8 manage-security-and-pii, 9 model-selector (duplicate of 10), 11 project-manager-split-spec-in-tickets-block, 12 remote-stale-command-line-toosl, 13 script-mode-to-activate, 14 simplify-command-lines, 15 sync-support-files-and-bare-ticket-authoring (shipped #491), 16 update-all-doesn-t-copy-workflow-correctly-to-atta (premise-dead, #461), 17 why-ai-asks-me-to-bump-instead-of-doing-it (shipped). KEEP 10 pick-model-on-workflow-to-save-on-cost: owner says it is a v2 item — leave it in v2/ as the surviving model-selection stub, do not cancel and do not pull it forward; no per-step/agent/ticket decision yet.
