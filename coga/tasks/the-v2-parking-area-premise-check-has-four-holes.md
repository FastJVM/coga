---
slug: the-v2-parking-area-premise-check-has-four-holes
title: The v2 parking-area premise check has four holes
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

`coga/tasks/v2/README.md` gives a two-question premise check — does the
subject still exist, and do the surfaces it names still resolve — plus a
known-stale table of renamed and removed commands and frontmatter fields. This
Dream run found four holes in that contract, each with evidence from drafts it
read this week.

**1. Nothing re-validates a parked draft while it sits.** The README names the
problem in its own words ("nothing re-validates it while it sits") but the check
fires only when a human happens to pull a draft forward. The only sweep that
ever ran it was the one-off ticket `decide-the-fate-of-two-premise-dead-v2-drafts-whos`,
which cancelled two drafts. That is demonstrably insufficient: a single 36-file
shard in this run found two more whose premises have since died —
`pass-secrets-to-skills-with-per-skill-scope` (the `[secrets]` bulk-inject model
it is entirely about now fails loud in `src/coga/config.py`) and
`file-locking-for-concurrent-task-mutation` (its "no mutual-exclusion primitive
exists" evidence is contradicted by the `fcntl.flock` pair in `src/coga/git.py`).

**2. No rule for dangling cross-ticket references** — the rot Coga's own
machinery manufactures on a schedule, since drafts routinely delegate their real
content to another ticket's body or blackboard and Dream Phase 4 deletes done
tickets. `v2/implement-accepted-ticket-interview-improvements` tells the
implementer to read the "Ranked changes" section of
`improve-prompt-for-relay-ticket`'s blackboard — a ticket that no longer exists
under `coga/tasks/`, so the exact wording for five of its six changes is
recoverable only from git history, which the draft never says.
`v2/autotrigger-ticket-type` already hit a milder version, annotated two slugs
as planned-not-created and redirected the reader to a "live recurring-hazard
cluster to read instead" — all four of those slugs are now gone too, so the
fix-up rotted the same way the original did.

**3. No question for "some other change already shipped this"** — the commonest
outcome in this run. `v2/document-workflow-less-concept-capture-drafts-as-s`
asks for architecture prose the architecture context now carries;
`v2/overload-ticket-locally-easily` asks for a local-first override note that
architecture and extension-model now both carry;
`v2/skill-for-split-into-sibling-ticket-discipline` has had half its acceptance
criterion satisfied by `retro/done-ticket/SKILL.md`. In each case the shipping
PR had no reason to know a parked draft was waiting on it.

**4. The one guard that matters is stated in no durable place.** "A green
`coga validate` is never a reason to cancel a draft — it is a consequence of
correct verdicts, never an input to them" is carried verbatim by three tickets
(`triage-the-v2-parking-area-empty-descriptions-prem`, `adjudicate-the-eight-premise-dead-v2-drafts`,
`interview-the-owner-on-the-17-title-only-v2-stubs`), each with the same
supporting observation that two of the four standing validate errors sit on the
drafts under adjudication, so ruling them dead is the cheapest route to a green
gate. The first of the three is already `canceled` and the other two are
`draft`, so the durable statement of the rule can be deleted while the incentive
it guards against persists. A grep across `coga/contexts`, `coga/skills` and the
packaged templates returns nothing.

## Context

Write 2, 3 and 4 into `coga/tasks/v2/README.md`, which already owns the
premise-check contract: a third premise question for dangling citations (and the
rule that a draft must inline the substance it depends on rather than citing
another ticket's blackboard), a fourth for already-delivered deliverables, and
the green-validate guard stated once, durably. If the guard is meant to bind
beyond `v2/`, its general form belongs in the lifecycle section of
`coga/contexts/coga/architecture/SKILL.md` as well.

Hole 1 is the one that needs a mechanism, not prose. Dream reads this corpus
every run and is the natural owner — either a standing pass over parked drafts
in Dream's disposition phase, or a small recurring ticket that greps parked
drafts against the known-stale table and files cancellations. That is a design
decision for the review step, and it would change the Dream template, so treat
it as the larger half.

Sibling tickets from this run that overlap: `adjudicate-parked-and-active-tickets-whose-premise`
(the verdicts themselves), `title-only-tickets-have-no-convention-and-no-valid`
(the stub habit outside `v2/`), and `record-or-clear-the-standing-repo-wide-coga-valida`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
