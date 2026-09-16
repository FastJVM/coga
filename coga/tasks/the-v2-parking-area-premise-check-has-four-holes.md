---
title: The v2 parking-area premise check has four holes
status: in_progress
owner: nicktoper
agent: claude
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
step: 2 (peer-review)
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

**Dream 2026-W38 evidence (finding F-22, hole 4).** The guard "A green `coga validate` is never a reason to cancel a draft — it is a consequence of correct verdicts, never an input to them" is carried verbatim by eight tickets (`adjudicate-the-eight-premise-dead-v2-drafts`, `interview-the-owner-on-the-17-title-only-v2-stubs`, `adjudicate-parked-and-active-tickets-whose-premise`, `correct-the-v2-known-stale-surfaces-table-and-rout`, `record-or-clear-the-standing-repo-wide-coga-valida`, `title-only-tickets-have-no-convention-and-no-valid`, this ticket, and the canceled `triage-the-v2-parking-area-empty-descriptions-prem`) and by no context: grepping `coga/contexts`, `coga/skills`, `src/coga/resources/templates`, `docs`, and `coga/tasks/v2/README.md` for "green validate", "never a reason to cancel", or "consequence of correct verdicts" returns nothing. Since Dream deletes done tickets, the only durable statements sit on the path to deletion. Add the sentence to the premise-check section of `coga/tasks/v2/README.md` and, because the guard binds any draft, to the ticket-lifecycle section of `coga/contexts/coga/architecture/SKILL.md` and its packaged twin.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: v2-premise-holes
worktree: /home/n/Code/claude/coga-v2-premise-holes

## Plan (implement step)

Surfaces touched, one owner per fact:

- `coga/tasks/v2/README.md` — premise check grows from two questions to
  four (dangling citations; already delivered), the inline-the-substance rule,
  the green-validate guard stated once for every v2 verdict (title-only
  section now points at it instead of repeating it), and a "who runs the
  check while a draft sits" paragraph pointing at Dream.
- `coga/contexts/coga/architecture/SKILL.md` + packaged twin — the general
  form of the green-validate guard in "Two state machines per ticket", since
  a verdict is a lifecycle write and the incentive is not v2-specific.
- Hole 1 mechanism: Dream's knowledge scan already owns every ticket under
  `coga/tasks/` in-shard, so the standing re-validation is a new finding class
  `premise` in `bootstrap/dream/scan/knowledge-scan` (run the README's four
  questions over every `coga/tasks/v2/` draft the shard owns) plus a Phase 6
  route in the Dream template: one `brief-for-human` adjudication draft per
  run listing every unowned `premise` finding with its failed question and
  evidence; owned findings report "already ticketed as". Dream files no
  cancellation itself — verdicts stay the author's, and Dream's contract
  already says it never changes lifecycle state or edits another ticket.
- Rejected: a recurring grep-against-the-table ticket. Two of the four
  motivating cases (`fcntl.flock` in `src/coga/git.py`; prose already carried
  by a context) are invisible to a grep of the known-stale table, and a new
  recurring template + schedule is more machinery for less coverage.
- Test: extend `tests/test_dream_worker_templates.py` with a template-text
  test for the `premise` class and its Phase 6 route, in the suite's style.

Out of scope (owned by siblings): the known-stale table row fixes and the
`gap` routing note (`correct-the-v2-known-stale-surfaces-table-and-rout`),
the verdicts themselves (`adjudicate-parked-and-active-tickets-whose-premise`),
stubs outside `v2/` (`title-only-tickets-have-no-convention-and-no-valid`).

## Implement — what landed (commit `59f3fb56` on `v2-premise-holes`)

- `coga/tasks/v2/README.md`: premise check is now four questions (subject,
  surfaces, citations, delivered) with the git-history recovery recipe for a
  dangling citation, the "carry the substance in its own body" rule, the
  `mark done --message "delivered by …"` verdict for a shipped deliverable
  (done so Retro retires it; cancel stays for a deliverable that never
  landed), a `### The green-validate guard` section stated once (the
  title-only section now points at it), and `### Who runs the check while a
  draft sits` naming Dream. The "nothing re-validates it while it sits"
  sentence at the top was updated to match.
- `coga/contexts/coga/architecture/SKILL.md` + packaged twin: the general
  guard in "Two state machines per ticket" ("A terminal transition is a
  verdict about the ticket, never a repair of the validator's output …").
- `coga/contexts/coga/roadmap/SKILL.md`: its own "nothing re-validates it"
  sentence updated to name Dream's pass and the two new failure kinds.
- `bootstrap/dream/scan/knowledge-scan/SKILL.md` (packaged only; no live
  twin exists): `## Parked drafts: the standing premise pass` + the `premise`
  class (`target: v2/<slug>`, `question: subject|surfaces|citations|delivered`,
  `owner:`), title-only stubs excluded (Phase 1 `empty-description` owns
  them), owner search by exact slug across open tickets.
- `bootstrap/dream/scan/scan-protocol/SKILL.md`: class vocabulary gains
  `premise`.
- `coga/recurring/dream/ticket.md` + packaged twin: Phase 2 keeps the
  `premise` lines through the merge; Phase 6 gains the `premise` route — one
  `brief-for-human` adjudication draft per run
  (`Premise check <period>: <N> parked drafts need a verdict`), owned drafts
  reported as already ticketed, Dream never cancels/closes/edits; run summary
  lists the draft with its member count.
- Test: `tests/test_dream_worker_templates.py::test_dream_re_validates_parked_drafts_every_run`
  (template-text style of its neighbours; also pins that the guard sentence
  appears exactly once in the README and once in architecture).

Verification: `python -m pytest` → 2562 passed (venv Python 3.12; the shell's
default `python` is 3.9 and refuses to import coga). `coga validate --json` on
`example/` → 4 OK, 0 issues. Branch rebased on fresh `origin/main` (no new
commits). No push, no PR.

## Decisions for the reviewer

- Hole-1 owner is the knowledge scan, not a new recurring grep ticket: two of
  the four motivating cases need judgment a grep of the known-stale table
  cannot give. Cost: one more question per parked draft per shard (76 drafts,
  README is small evidence). If that proves too heavy, the fallback is a
  dedicated Dream phase over `coga/tasks/v2/` only; the finding shape and
  Phase 6 route would not change.
- Dream files a question, not a verdict: consistent with its existing
  contract ("does not change lifecycle, workflow, or assignee state", "never
  files under `coga/tasks/v2/`", "does not edit another ticket").
- Delivered verdict is `mark done`, premise-dead is `mark canceled`: Phase 6
  leaves canceled tickets on disk indefinitely, so `done` is what lets Retro
  retire a draft whose outcome actually exists.

## Adjacent observations (not fixed here)

- A bare `SLACK_WEBHOOK_URL` in the shell environment makes
  `coga validate --json` exit non-zero on the example fixture before
  validating anything ("Bare `SLACK_WEBHOOK_URL` is no longer supported");
  `env -u SLACK_WEBHOOK_URL` works around it. Behaviour is by design
  (`config.py` fails loud), but it surprises a validate run.
- Canceled parked drafts accumulate: Phase 6 says Dream leaves a canceled
  ticket on disk and Retro refuses non-done tickets, so every premise-dead
  cancellation the new pass produces is a permanent file. Nothing retires
  them today; worth a ticket if the count grows.
