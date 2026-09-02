---
slug: interview-the-owner-on-the-17-title-only-v2-stubs
title: Interview the owner on the 17 title-only v2 stubs
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: code/design-then-implement
secrets: null
---

## Description

17 of the 81 tasks in `coga/tasks/v2/` have an empty `## Description`, and every one is a title-only
stub: frontmatter, an empty `## Description`, an empty `## Context`, the placeholder blackboard,
328–714 bytes total. There is nothing in the repo to reconstruct intent from — for `model-selector`
and `add-subproject` the entire informational payload is the slug.

So this is not an editing task. The owner has chosen to be interviewed on each of the 17: recover
the real intent where it still exists, and cancel with a recorded reason where it does not. The v2
README's premise check cannot be run on these drafts until they have a description to check.

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

### Escalation

Step 1 launched by the owner runs attended, so ask directly. If no human is reachable — the
`coga launch` supervisor auto-chains agent steps — the correct action is
`coga block --task <slug> --reason "<the 17 questions>"`. Do not write descriptions unattended and
do not defer the decisions to a later step.

### Out of scope

The 8-draft premise-dead cohort and the README stale-surfaces table — both sibling tickets. These 17
are not part of that cohort.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
