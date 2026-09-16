---
title: Ticket relationships and ownership have no mechanism
status: blocked
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

Three related ticket-model gaps, all found by Dream's knowledge scan with
evidence from tickets that hand-rolled a workaround. They share one question —
what relationships between tickets, and between a ticket and a person, does the
model carry? — so they are scoped together and may still split into siblings.

**1. Supersession is prose-only.** Seven `v2/` tickets annotate supersession by
hand and each invents its own shape: `v2/acceptance-criteria` uses a bold
"**Superseded by `<slug>` (2026-09-01).** … Do not work this ticket" paragraph
in `## Context`; `v2/cleanup-core-commands/work-orchestration-commands-to-tickets`
buries "The dedicated removal ticket supersedes the project-planning portion of
this work" mid-`## Description` without naming the successor;
`v2/dream-recurring-persist-done-stop-inline-delete`,
`v2/auto-persist-dirty-launch-worktrees-to-pushed-bran`,
`v2/use-worktree-when-starting-a-dev-task` and
`v2/cleanup-core-commands/launch-decomposition` each differ again. Nothing in the
model supports it: `CANONICAL_TICKET_KEYS` in `src/coga/ticket.py` has no
`supersedes`/`superseded_by`, and `src/coga/lifecycle.py` allows only
draft/active/in_progress/blocked/paused/done/canceled — no superseded terminal.
So a superseded ticket sits at `paused` or `draft` and keeps surfacing in
queues, blocker sweeps and launch candidates as live work.

**2. Ticket-to-ticket dependency ordering has no mechanism.**
`v2/identify-blocking-issues` asks for it directly ("possibly another field in
the ticket labelled 'dependencies'"), and
`v2/op-service-account-auth-to-skip-op-read-prompt` already implements it by
hand with a `### Blocks` section naming a successor that "**cannot be done
until this ticket ships**". `CANONICAL_TICKET_KEYS` has no dependency field, and
`blocked` is a runtime blocker-ask mechanism (`coga block` / `coga unblock` on
open questions), not a declared prerequisite between tickets — so an ordering
constraint recorded in prose is invisible to `coga status`, blocker sweeps and
launch selection.

**3. No command reassigns `owner:` / `human:`.** `v2/acceptance-criteria`
records the problem in its own body: taken over on 2026-09-01, "the
`owner:`/`human:` frontmatter still reads `zach` — there is no CLI command to
reassign it, and those fields are not agent-editable, so a human needs to change
them by hand". Fifteen tickets under `coga/tasks/` still carry `owner: zach`,
several paused with `assignee: nicktoper`, so the frontmatter and the body
disagree. `src/coga/commands/` has no assign module, which makes hand-editing
the only path and drift the default.

## Context

Each part has two honest outcomes and the design step should pick per part:
add the mechanism (a frontmatter field, a lifecycle transition, a command), or
document the convention so readers and tooling can rely on one spelling and
stop trusting what the model does not carry.

The natural home for a documented convention is
`coga/contexts/coga/architecture/SKILL.md` (with its enforced packaged twin);
a mechanism touches `src/coga/ticket.py`, `src/coga/lifecycle.py`,
`src/coga/validate.py` and possibly a new command.

Note: `document-design-pivot-in-blackboard-convention` was canceled, but it
covered a different shape — a design pivot inside one ticket — so that
cancellation does not close part 1.

**Code facts (implement step, 2026-09-15).** Part 2 already has a mechanism
the description missed: `src/coga/megalaunch.py` `_finished_blocker_dependency`
plus `_reason_names_task` read an exact path-qualified task slug out of an open
blocker ask, and `_drain_satisfied_blockers` relaunches the dependent once that
ticket is `done` or retired — a blocked ticket is therefore visible to `coga
status --blocked`, `src/coga/blocker_reminders.py`, and launch selection. What
was missing was one documented spelling, not a field. For part 3,
`src/coga/git.py` `TicketRoutingState` includes `owner`, which is why a live
`in_progress` session must not have its owner changed underneath it.

**Dream 2026-W38 evidence (finding F-25, part 1 — supersession).** Verified against source: `CANONICAL_TICKET_KEYS` in `src/coga/ticket.py` has no `supersedes`/`superseded_by` key, `src/coga/lifecycle.py` has no `superseded` state, and `grep -rni supersed coga/contexts coga/skills` finds only `coga/contexts/dev/code/SKILL.md` "Design pivots and superseded plans", which governs a superseded design *inside one ticket*. Current carriers each invent a shape: `coga/tasks/v2/acceptance-criteria.md` (paused) opens `## Context` with a bold "Superseded by `the-ticket-interview-never-asks-what-done-means` (2026-09-01)" line; `v2/cleanup-core-commands/work-orchestration-commands-to-tickets.md` buries "The dedicated removal ticket supersedes …" mid-Description without naming the successor; `nightly-auto-drain-run-for-ready-tickets.md` records the supersession only from the successor's side while `v2/autoroute-agent-based-on-remaining-usage` says nothing. Refresh this ticket's example slugs: three of the six it cites (`dream-recurring-persist-done-stop-inline-delete`, `auto-persist-dirty-launch-worktrees-to-pushed-bran`, `use-worktree-when-starting-a-dev-task`) no longer exist under `coga/tasks/` at those paths (the first two live under `v2/`, the third is `v2/use-worktree-when-starting-a-dev-task`). Proposed minimum: one documented spelling in the ticket-lifecycle section of `coga/contexts/coga/architecture/SKILL.md` (a bold "Superseded by `<slug>` (<date>)" first paragraph of `## Context` plus the terminal status the superseded ticket takes), or a `superseded_by` key that `coga status`/launch selection treat as terminal.

<!-- coga:blackboard -->

## Plan (implement step, 2026-09-15)

The workflow (`code/with-review`) has no design step, so implement picks per
part, following the ticket's own framing: mechanism or documented convention.

- **Part 1 — supersession: document, no new mechanism.** `coga mark canceled
  <slug> --message "Superseded by <path-qualified-slug>"` already provides
  everything a `superseded` terminal would: terminal (drops out of `coga
  status`, blocker sweeps, megalaunch candidates), reason required and
  audit-logged, `step:` cleared, body untouched. Adding a `superseded_by` key
  or a new status would touch `lifecycle.py`, `validate.py`, `mark.py`, views,
  launch refusals, and every packaged workflow for a relationship that
  cancellation-with-reason already carries. Convention: the cancellation
  reason begins `Superseded by <exact slug>`; when readers of the file need the
  pointer too, `## Context` opens with the same bold line. Owner of the fact:
  `coga/architecture` (new `## Ticket relationships` section); `coga/cli`
  "Pick which command" gets the entry.
- **Part 2 — dependencies: document the existing mechanism.** A blocker ask
  whose reason names the prerequisite's exact path-qualified slug *is* the
  declared dependency: `megalaunch._finished_blocker_dependency` /
  `_reason_names_task` already read it and the dependency drain retries the
  dependent once the prerequisite is `done` or retired (see `### Megalaunch
  dependency drain`). The ticket's claim that ordering is "invisible to `coga
  status`, blocker sweeps and launch selection" is stale — a blocked ticket is
  visible on all three. No `dependencies:` field: it would be a second, unread
  copy of the same fact. The successor-side `### Blocks` prose in
  `v2/op-service-account-auth-to-skip-op-read-prompt` stays a human pointer.
- **Part 3 — owner reassignment: build `coga owner <slug> <name>`.** Hand
  editing `owner:` skips validation, the audit line, and the guarded control
  sync, which is why fifteen tickets drifted. The transaction (barrier write →
  `assert_task_valid` → `append_log` → `git.sync_task_state` under
  `ticket_state_guard`) is package-private, so this is a genuine command under
  the microkernel rule, not an alias. Rules: any non-terminal status except
  `in_progress` (pause first — a live session's routing lease compares
  `owner`, see `git.TicketRoutingState`); terminal records refuse; same owner
  is a no-op error; name must be non-empty. No Slack post (routine, like
  `mark paused`). Named `owner` so the verb mirrors the frontmatter field the
  way `mark <state>` mirrors `status`, and to avoid reviving "assign".

Out of scope, noted for retro: migrating the seven hand-annotated `v2/`
supersession tickets and the fifteen `owner: zach` tickets is a human
decision per ticket; the new command and convention make it a one-liner each.

## Implemented (commit 8e3680b2 on `ticket-relationships`)

- `src/coga/commands/owner.py` — new `coga owner <slug> <name>`; registered in
  `src/coga/cli.py` (command + `_SWEEPING_COMMANDS`) and
  `src/coga/aliases.py` `BUILTIN_COMMANDS`.
- `tests/test_owner.py` — 13 tests mirroring `tests/test_mark.py`: every
  allowed status, step/body preserved, workflow-less draft, refusals
  (in_progress, done/canceled, same owner, blank name, unknown task), plus one
  `git_repo` test proving the reassignment and audit line land on control.
- `coga/contexts/coga/architecture/SKILL.md` + packaged twin — new
  `## Ticket relationships` section (ownership / dependency / supersession),
  `coga owner` added to the one-writer list, prospective-validation list, and
  the `human` → `owner` bullet.
- `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md` —
  `## coga owner` section and three "Pick which command" entries.
- `docs/reference.md` — one-line pointer.
- Ticket `## Context`: refreshed the three stale example slugs to their `v2/`
  paths and added the code facts for parts 2 and 3.

Verification: `python -m pytest` → 2508 passed; `coga validate --json` on
`example/` → 0 issues; on the live repo → 29 pre-existing warnings/errors, none
on this ticket. Rebased on `origin/main` (no new commits). Not pushed.

For peer review: the one judgment call worth challenging is refusing
`in_progress` instead of clearing `launch_generation` the way `mark paused`
does — I chose the refusal because an owner change does not end the session,
so clearing the claim would lie about a child that is still running.

## Peer review

`codex review --base main` **returned**, exit 0, on 2026-09-15 against
commit `8e3680b2` in the recorded feature checkout. It found two P1 bugs and
one P2 policy problem. Its 380 focused tests passed; additional real-Git and
CLI probes reproduced all three uncovered failures. This is a failed review,
not approval to advance.

1. **P1 — stale control publication loses newer state.**
   `src/coga/commands/owner.py` `owner` passes only the ordinary
   `git.ticket_state_guard` to `git.sync_task_state`. A feature checkout with
   a paused ticket can overwrite control's later `in_progress` or `blocked`
   state and blackboard while returning success. Independently reproduced:
   publish a paused ticket, check out a feature branch, publish
   `in_progress` from a competing clone, then run `owner` from the stale
   feature checkout; control becomes `paused` with the new owner. Lease the
   pre-change control revision and prevent a refused publication from being
   retried by the generic CLI sweep without that lease.
2. **P1 — the local write barrier does not compare its input.**
   `owner` caches the ticket before validation and calls
   `git.write_ticket_under_barrier` without a `mutation_snapshot`. An
   intervening lifecycle write is overwritten. The review probe published
   an `in_progress` launch with a claim and new notes during validation;
   reassignment restored `paused`, removed the claim and notes, and returned
   success. Capture the initial ticket bytes and compare them under the
   barrier; preserve concurrent edits on refusal and cover this with a
   deterministic regression.
3. **P2 — pause-first reassignment strands an owner gate.**
   An ordinary `assignee: owner` handoff remains `in_progress` after the
   agent session ends. Following the new error's `mark paused` then `owner`
   advice leaves that gate paused: `bump` refuses because it requires
   `in_progress`, and ordinary `launch` refuses an owner step. Requiring an
   unnecessary assisting agent or rewinding completed work is not a usable
   handoff. The assumption that every `in_progress` ticket has a running
   agent is false; conversely, an owner step can have a live assisting agent.

**Design decision required before fixes:** choose the policy for reassigning
an `in_progress` owner-held gate while retaining its progressable state,
including what happens to a live assisting session whose routing lease would
be invalidated. The step explicitly requires escalation when findings imply
a design rethink, and this queue cannot obtain a new answer interactively.
No product fixes were made. The required `git fetch origin main` and
`git rebase FETCH_HEAD` completed; the clean feature branch now holds
`4e4a4faf`, one commit ahead of `origin/main` (the same implementation,
with only control ticket/log updates relative to the reviewed `8e3680b2`).
After resolution, implement the three
fixes together, update the owning contexts and packaged twins, rerun review
and regressions, freshen the branch, and author `## PR` before advancing.

Verification so far: `git diff --check main...HEAD` passed;
`coga validate --task ticket-relationships-and-ownership-have-no-mechani --json`
returned one valid ticket and no issues. Real-PTY smoke of
`PYTHONPATH=/home/n/Code/claude/coga-ticket-relationships/src
/home/n/Code/claude/coga/.venv/bin/python -m coga.cli owner --help` rendered
the usage, arguments and refusal policy cleanly at the default 80-column
terminal. No raw-terminal loop, pager or Slack renderer changed. The ambient
`python` lacks `tomlkit`; use the existing repo venv with an absolute
`PYTHONPATH` to test the feature source.

Full suite, run before and again after the required rebase:
`PYTHONPATH=/home/n/Code/claude/coga-ticket-relationships/src
/home/n/Code/claude/coga/.venv/bin/python -m pytest` — **2508 passed** in
187.07s before rebase and **2508 passed** in 172.52s after rebase. Both runs
had one non-failing warning that the sandbox cannot write the worktree's
pytest cache. The branch remains clean; no fix commit, push, PR, or bump.

## Dev

branch: ticket-relationships
worktree: /home/n/Code/claude/coga-ticket-relationships

---

## Blockers

- [ ] [2026-09-15 22:52] [agent:codex] id=20260915T225238 Choose how coga owner should reassign an in_progress owner-held gate without stranding it, including how to handle a live assisting agent (stop first or invalidate its routing lease). The current pause-first policy prevents normal bump/launch. See Peer review on the blackboard for the returned review and two P1 state-loss races.

---

## Blocker reminders

- d137baf1e3d7 last_reminded: 2026-09-16 10:58
