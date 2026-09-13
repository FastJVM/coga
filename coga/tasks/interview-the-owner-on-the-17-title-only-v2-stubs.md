---
title: Interview the owner on the 17 title-only v2 stubs
status: blocked
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
step: 1 (design)
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

1. Read the verdict table on the blackboard (filled in at `review-design`). It is the only input.
2. For each `describe` row: open `coga/tasks/v2/<slug>.md`, replace the empty `## Description` with
   the owner's answer (prose, first person is fine — it is a record of intent, not a spec), and put
   the interview's findings for that stub under `## Context`. Keep frontmatter untouched; the
   drafts stay `status: draft` with `workflow: null` so the v2 README's premise check can now be
   run on them by whoever pulls them forward.
3. For each `cancel` row: `coga mark canceled v2/<slug> --message "<reason from table>"`. One
   command per stub; the message is the audit trail in `coga/log.md`.
4. Where the owner merged two stubs into one (e.g. the two model-selection stubs), describe the
   survivor and cancel the other with `duplicate of v2/<survivor>` as the reason.
5. Run `coga validate --json` and `coga status v2 --all`; record both results on the blackboard.

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

## Design step — 2026-09-12

**Status: blocked on the interview.** Session conduct for this launch is the megalaunch queue rule
(input not already in hand is unavailable; do not ask-and-wait), so the 17 questions go out through
`coga block`. Everything that does not depend on the answers is done: the spec skeleton is under
`## Description`, and the per-stub grep findings are under `## Context` ("What the pre-interview
grep found"). The verdict table below is the deliverable of `review-design`; the implement step
reads only that table.

Leans below are the agent's read of the evidence, **not verdicts** — the owner overrides any of
them. A `describe` needs the owner's own words; nothing gets written from the slug.

## Verdict table (fill at review-design)

| slug | found | lean | owner's answer | verdict |
| --- | --- | --- | --- | --- |
| `add-subproject` | nothing anywhere | cancel unless intent recalled | | |
| `autoroute-agent-based-on-remaining-usage` | superseded by canceled `nightly-auto-drain` | cancel (superseder canceled too) or describe if still wanted | | |
| `create-vault6-and-service-account-for-high-trust-s` | contradicts `coga/secrets` one-SA/one-vault rule; owner zach | cancel as premise-dead by decision | | |
| `create-vault-and-service-account-for-mid-trust-sec` | same | cancel as premise-dead by decision | | |
| `docs-and-contt-block-should-be-merged` | duplicate of live `redo-documentation-dir-…` | cancel as duplicate | | |
| `generic-lib-to-use-e-g-patent-models` | only echo is canceled reminder-engine ticket | cancel unless intent recalled | | |
| `in-general-relay-files-should-be-easier-to-access` | `move-cogacontext-…` done | cancel as shipped, unless more was meant | | |
| `manage-security-and-pii` | secrets covered; PII not | describe if PII ask is real; else cancel | | |
| `model-selector` | feature absent; twin of next | merge into one described stub, cancel other | | |
| `pick-model-on-workflow-to-save-on-cost` | feature absent; twin of prev | (survivor candidate — it names the why) | | |
| `project-manager-split-spec-in-tickets-block` | design step already splits; block exists | cancel unless a PM role is still wanted | | |
| `remote-stale-command-line-toosl` | covered by `v2/cleanup-core-commands/` | cancel as duplicate | | |
| `script-mode-to-activate` | `mode:` gone | cancel as premise-dead | | |
| `simplify-command-lines` | covered by `v2/cleanup-core-commands/` | cancel as duplicate | | |
| `sync-support-files-and-bare-ticket-authoring` | shipped in #491 | cancel as shipped | | |
| `update-all-doesn-t-copy-workflow-correctly-to-atta` | command removed in #461 | cancel as premise-dead | | |
| `why-ai-asks-me-to-bump-instead-of-doing-it` | base prompt mandates bump-last | cancel as shipped | | |

## Open Questions

The 17 questions to the owner, each carrying what was found. Answer with a verdict per row; for
`describe`, one or two sentences in your own words is enough — they become the Description
verbatim.

1. `add-subproject` — no subproject concept exists anywhere. What was a subproject: a nested
   Coga repo, a `coga/tasks/<dir>/` namespace like `v2/`, or something else? Or cancel?
2. `autoroute-agent-based-on-remaining-usage` — was folded into `nightly-auto-drain`, which you
   later canceled. Does routing a ticket to whichever of Claude/Codex still has budget still
   matter on its own, or cancel with it?
3. `create-vault6-and-service-account-for-high-trust-s` (zach's) — `coga/secrets` now says one SA,
   one automation vault, and that trust-named vaults are human-only. Cancel as decided-against, or
   is there a second automation tier you and zach still want?
4. `create-vault-and-service-account-for-mid-trust-sec` (zach's) — same question.
5. `docs-and-contt-block-should-be-merged` — three tickets already call it an empty duplicate of
   the live `redo-documentation-dir-and-merge-it-with-context-b`. Confirm cancel as duplicate?
6. `generic-lib-to-use-e-g-patent-models` — do you remember what the "generic lib" was (a shared
   Python module the patents/admin repos would import? a bundled battery?). If not, cancel.
7. `in-general-relay-files-should-be-easier-to-access` — `move-cogacontext-to-roodoc-…` shipped
   the contexts move. Was that the whole ask, or is there more (tasks? skills? a CLI `coga show`
   gap)?
8. `manage-security-and-pii` — secrets are covered by `coga/secrets`. Was the PII half a real ask
   (e.g. rules about what agents may put in tickets/log/Slack)? If yes, one sentence on what;
   else cancel.
9. + 10. `model-selector` / `pick-model-on-workflow-to-save-on-cost` — same feature twice. Keep
   one? Proposed: keep `pick-model-on-workflow-to-save-on-cost` (it carries the why) and cancel
   `model-selector` as duplicate. What did you want selected — model per workflow step in the
   frozen workflow, per agent in `[agents.*]`, or per ticket?
11. `project-manager-split-spec-in-tickets-block` — `code/design` already says "split if too
    big" and `coga block` exists. Was this a distinct PM role/skill that turns a spec into a set
    of tickets? Describe or cancel.
12. `remote-stale-command-line-toosl` — reading this as "remove stale command-line tools", which
    `v2/cleanup-core-commands/` now owns. Cancel as covered, or did "remote" mean something else?
13. `script-mode-to-activate` — `mode:` frontmatter is gone; `ticket.py` sibling replaced it.
    Confirm cancel as premise-dead?
14. `simplify-command-lines` — also `cleanup-core-commands/` territory. Cancel as covered?
15. `sync-support-files-and-bare-ticket-authoring` — `authoring.support_paths()` shipped this in
    #491. Confirm cancel as shipped?
16. `update-all-doesn-t-copy-workflow-correctly-to-atta` — `init --update --all` was removed in
    #461. Confirm cancel as premise-dead?
17. `why-ai-asks-me-to-bump-instead-of-doing-it` — base prompt now mandates bump-as-last-act.
    Confirm cancel as shipped, or is the behavior still happening?

---

## Blockers

- [ ] [2026-09-12 22:10] [agent:claude] id=20260912T221018 Interview needed: a describe/cancel verdict per stub (full questions + grep findings in the ticket blackboard 'Open Questions'). Agent leans in brackets; a 'describe' needs your own words. 1 add-subproject [nothing exists; cancel unless recalled]. 2 autoroute-agent-based-on-remaining-usage [folded into nightly-auto-drain, itself canceled; cancel or still wanted?]. 3+4 create-vault6/create-vault…-trust (zach) [coga/secrets now rules one SA one vault; cancel as decided-against?]. 5 docs-and-contt-block-should-be-merged [duplicate of live redo-documentation-dir; cancel?]. 6 generic-lib-to-use-e-g-patent-models [no trace; what was the lib, or cancel?]. 7 in-general-relay-files-should-be-easier-to-access [move-cogacontext shipped; whole ask, or more?]. 8 manage-security-and-pii [secrets covered; was PII a real ask?]. 9+10 model-selector / pick-model-on-workflow-to-save-on-cost [same feature; keep pick-model, cancel model-selector? what is selected per: step, agent, ticket?]. 11 project-manager-split-spec-in-tickets-block [design step already splits; distinct PM skill or cancel?]. 12 remote-stale-command-line-toosl [read as 'remove stale CLI tools' = cleanup-core-commands; cancel?]. 13 script-mode-to-activate [mode: gone; cancel premise-dead?]. 14 simplify-command-lines [cleanup-core-commands; cancel?]. 15 sync-support-files-and-bare-ticket-authoring [shipped in #491 authoring.support_paths; cancel?]. 16 update-all-doesn-t-copy-workflow-correctly-to-atta [init --update --all removed in #461; cancel premise-dead?]. 17 why-ai-asks-me-to-bump-instead-of-doing-it [base prompt now mandates bump-last; cancel as shipped, or still happening?]
