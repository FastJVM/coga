---
title: Define the split-a-ticket mechanic shared by code design and implement
status: canceled
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
---

## Description

`v2/skill-for-split-into-sibling-ticket-discipline` was raised by the Dream
W22 knowledge scan and re-raised from a different repo in Dream W31, and it is
still a parked `draft`. Half of it has since shipped without the draft being
updated: `retro/done-ticket/SKILL.md` now carries the adjacent-finding contract
end to end — an "Unresolved adjacent bugs" section, a disposition-table row, a
pre-deletion verification step, and a required report line — so a source ticket
can no longer be deleted as the only copy of an accepted adjacent finding.

The other half is untouched. `coga/skills/code/implement/SKILL.md` still says
only "If the work is too big for one PR, **stop and split the ticket** on the
blackboard", and `coga/skills/code/design/SKILL.md` only says "recommend a split
rather than writing a spec you know is oversized". Neither defines the mechanic,
and grepping the live and packaged skill trees finds no `## Split` or
`## Sequencing` heading convention anywhere.

So an agent told to split has no answer for what filename the siblings get,
which blackboard section records the split, how siblings cross-link, or how an
ordered sequence differs from a co-equal split — and every split invents its own
shape.

## Context

The fix is a short "Splitting a ticket" contract shared by `code/implement`
and `code/design`: sibling slug convention, one named blackboard heading, the
cross-link form, and the sequenced-versus-co-equal distinction. Both skills are
twin pairs — keep the live and packaged copies byte-identical.

Dispose of the parked draft as part of this: narrow
`v2/skill-for-split-into-sibling-ticket-discipline` to the split mechanic alone,
since its adjacent-finding acceptance criterion is already met, or cancel it
with a pointer to this ticket.

This also interacts with `ticket-relationships-and-ownership-have-no-mechani`
(ticket-to-ticket dependency ordering has no mechanism): an ordered split needs
a way to record the order. Decide whether the split contract adopts whatever
that ticket settles, or defines its own heading and stays prose-only.

**Dream 2026-W38 evidence (finding F-26).** `coga/skills/code/implement/SKILL.md` ("If the work is too big for one PR, **stop and split the ticket** on the blackboard") and `coga/skills/code/design/SKILL.md` ("recommend a split rather than writing a spec you know is oversized") both instruct a split without defining it; a grep of `coga/skills`, `coga/contexts`, and `src/coga/resources/templates` finds no `## Split`/`## Sequencing` heading and no sibling-slug or cross-link convention. Three independent tickets invented the linkage three ways: `run-recurring-agent-templates-off-the-control-bran` ("Two sibling tickets cover the easy cases: …"), `megalaunch-activates-picks-before-preflight` ("the same invariant violation as the sibling ticket `launch-activates-before-preflight`"), and `the-period-task-context-never-covers-the-determini` ("the sibling ticket `define-the-recipe-reporting-contract-report-durabi`. Read both before writing"), none distinguishing an ordered sequence from a co-equal split or recording it under a findable blackboard heading. `v2/skill-for-split-into-sibling-ticket-discipline` overlaps this ticket; its adjacent-finding half is already satisfied by the packaged `retro/done-ticket/SKILL.md` "Unresolved adjacent bugs" section, so fold what remains into this ticket rather than keeping both.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Plan (implement step, 2026-09-16)

- **Where the contract lives: inlined, identically, in both step skills.**
  A `## Splitting a ticket` section in `code/implement` and `code/design`,
  byte-identical, enforced by a test the way live/packaged twins are. A third
  owner (a `code/split-ticket` skill or a context) was rejected: nothing
  composes it at the moment the split decision arises, `dev/code` is opt-in
  per ticket and declares itself narrow, and no CLI prints a bundled
  non-step skill for a downstream repo's agent to read.
- **Sibling slug: whatever `coga create` makes of a title that names the
  sibling's own outcome.** No shared prefix or numbering — `slugify` truncates
  at 50 chars and the slug never changes. Siblings are created as drafts from
  the checkout you bump from, in the source ticket's directory; never
  activated by the splitting agent.
- **One heading: `## Split` on the source blackboard**, dated, marked
  `Co-equal` or `Sequenced`, one line per sibling (exact path-qualified slug +
  slice).
- **Cross-link: bold first paragraph of each sibling's `## Context`** —
  `**Split from `<source>` (<date>).** Siblings: …` plus `After: `<slug>`.`
  for a sequenced successor. Same shape as the supersession line the blocked
  `ticket-relationships-and-ownership-have-no-mechani` plan settled on, and it
  composes into the sibling's prompt and survives the source's deletion.
- **Ordering adopts the existing mechanism, no new field.** A draft cannot be
  blocked (`commands/block.py` requires active/in_progress/blocked), so the
  order is prose until the successor is activated; whoever picks up a
  successor whose `After:` ticket is not `done` runs `coga block` naming that
  exact slug, and `megalaunch._finished_blocker_dependency` retries it later.
  This is the same conclusion `ticket-relationships…` part 2 reached; the
  contract does not wait on that blocked ticket.
- **Source ticket: narrow to one PR-sized slice, or `coga mark canceled
  --message "Split into …"`** when nothing remains.
- **Parked draft:** cancel `v2/skill-for-split-into-sibling-ticket-discipline`
  with a pointer here — its adjacent-finding half shipped in
  `retro/done-ticket`, its split half ships on this branch.

## Implemented (commit c6d71231 on `split-ticket-contract`)

- `coga/skills/code/implement/SKILL.md` + packaged twin — new
  `## Splitting a ticket` section (five numbered rules: `coga create` drafts
  named for their own outcome, `## Split` heading on the source blackboard,
  `**Split from …**` cross-link opening each sibling's `## Context`,
  co-equal vs sequenced with the `After:` line and the block-at-activation
  rule, narrow-or-cancel the source); the Gotchas bullet now points at it;
  step 1 tells the implementer of a sequenced successor to block on its
  `After:` ticket before setting up a checkout.
- `coga/skills/code/design/SKILL.md` + packaged twin — the identical section;
  step 5 now splits by the contract (spec covers the slice the source keeps,
  each sibling draft carries its own; the owner can cancel a sibling in
  `review-design`) instead of merely recommending one.
- `tests/test_code_split_contract.py` — mirrors
  `tests/test_code_implement_skill.py`: the two packaged sections are
  byte-identical, the contract's load-bearing spellings are present, both
  step skills point at it. The comment there records why the section has no
  single owner file.
- Example slugs inside the contract are invented, not this repo's tickets,
  because the skill ships as a bundled battery.
- Control (`main`): `coga mark canceled v2/skill-for-split-into-sibling-ticket-discipline`
  with a `Superseded by …` reason naming this ticket and the branch.

Verification: `PYTHONPATH=<worktree>/src .venv/bin/python -m pytest` →
2564 passed; live/packaged `cmp` identical for all four skill copies;
`coga validate --json` → only pre-existing warnings/errors, none on this
ticket; `git diff --check` clean. Rebased on `origin/main` (no new
commits). Not pushed, no PR.

Not done here, for retro: the three ad-hoc "sibling ticket" links the Dream
evidence cites predate the contract and are left as they are — retro deletes
them on completion, and rewriting live tickets' prose is not this ticket's
scope. `ticket-relationships-and-ownership-have-no-mechani` stays blocked on
its own peer-review question; this contract adopts its part-2 conclusion
(blocker ask naming the exact slug) without waiting on it, so if that ticket
later lands a `## Ticket relationships` section in `coga/architecture`, the
dependency spelling there and rule 4 here should be checked for agreement.

## Dev

pr: https://github.com/FastJVM/coga/pull/889
branch: split-ticket-contract
worktree: /home/n/Code/coga

## Peer review

2026-09-23: `codex review --base main` ran in the recorded feature worktree
and **returned**: no actionable defects. Its attempted test run lacked
`tomlkit`; a separate temporary environment now contains the declared test
extra, and the full suite is running with an absolute worktree `PYTHONPATH`.

Ran `git fetch origin main` and `git rebase FETCH_HEAD` unconditionally.
Resolved the design-skill conflict in both twins by preserving main's added
step and numbering (split step 6, bump step 7) and this branch's split text.
Rebased feature commit: `b36286d6b`; worktree clean. `git diff --check` and
both live/packaged `cmp` checks pass. No terminal, pager, TTY prompt, or Slack
rendering behavior changed; reviewed the Markdown instructions directly.
`coga validate --task define-the-split-a-ticket-mechanic-shared-by-code --json`
returned one valid ticket and no issues.

Full-suite verification:
`PYTHONPATH=/home/n/Code/claude/coga-split-ticket-contract/src /tmp/coga-split-review-venv/bin/python -m pytest`
returned **2880 passed, 2 warnings in 264.20s**. Warnings concern pytest cache
writes denied in the feature worktree by the sandbox; no test failures.
The temporary environment was installed with the package's declared `[test]`
extra. Final feature worktree is clean and committed, one commit ahead of
fetched `origin/main` (`cfa3332b1`).

## PR

Define the split procedure for oversized tickets in one new skill,
`code/split-ticket`, loaded beside `code/design` / `code/implement` in the
design and implement steps of every bundled `code/*` workflow: outcome-named
sibling drafts created by `coga create` with their complete body (including
the `**Split from …** After: …` cross-link), a `## Split` roster on the source
blackboard, co-equal versus sequenced siblings via `After:` and the existing
blocker mechanism, and narrowing or canceling the source. The step skills
point to it and fall back to reading the file when a ticket's workflow froze
before it shipped.

Test plan: full suite 2904 passed; contract + packaging tests rerun after the
fallback commit (26 passed); `git diff --check` clean; `coga validate --json`
issue count unchanged from main.

## Review assist (2026-09-24)

Addressed both Codex P1 threads on #889 (replied, not resolved): contract
moved to the single `code/split-ticket` owner (91db4ab); sibling cross-links
now written via `coga create --description` so the create sync publishes
them; frozen-workflow fallback added in the step skills. Branch rebased onto
main and pushed under exact leases.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `define-the-split-a-ticket-mechanic-shared-by-code`
Recorded: 2026-09-24T05:50:17+00:00

    `coga open-pr` must run from the primary control checkout on 'main', not branch 'authoring-agent-picker'. Return to the control checkout and rerun it; the command will still push the recorded feature branch by name.
