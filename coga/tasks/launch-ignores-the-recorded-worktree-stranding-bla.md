---
slug: launch-ignores-the-recorded-worktree-stranding-bla
title: Launch ignores the recorded worktree, stranding blackboard writes
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
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
step: 1 (design)
---

## Description

`coga launch` never chooses where a step's agent runs — the child inherits the
supervisor's cwd — while the shipped `code/implement` skill tells that agent to
`cd` into the feature worktree. Read literally the skill is consistent (it says
to return to the primary checkout before writing `## Dev` and before `coga
bump`), but nothing verifies the agent came back. When it doesn't, implement's
blackboard writes land on the feature branch and the next step respawns in the
primary checkout and cannot see them, so `open-pr` fails with "No usable
`branch:` recorded" even though implement did record it.

This is therefore an **enforcement/compliance** bug — an unverified instruction,
not a contradiction between `launch` and the skill. Any fix has to say what
makes the write and the read agree on one checkout.

**Mechanism confirmed by local reproduction (2026-08-19, design step; commands
on the blackboard).** The write side is the agent's file edit, which lands in
whichever checkout's `coga/tasks/<slug>.md` the agent touches; the sync side is
`commands/bump.py` → `git.sync_task_state(cfg, ref.path)`, which syncs the copy
in the checkout `coga bump` runs from. Three characterized cases:

1. `## Dev` written in the primary checkout, bump from primary (what the skill
   asks for): correct, lands on control.
2. `## Dev` written in the worktree's ticket copy, bump from primary (the
   deviation): **bump succeeds silently**, syncs a ticket that never saw the
   write, the `## Dev` block sits uncommitted in the worktree copy, and the next
   step's `coga open-pr` fails with the exact production error ("No usable
   `branch:` recorded under `## Dev`…").
3. `## Dev` written in the worktree copy, bump from the worktree:
   `sync_task_state`'s feature-branch path commits the task dir on the feature
   branch and lands the same files on control — fully correct today.

Stranding therefore requires a *split*: the blackboard write in one checkout and
the bump in another. Nothing fails loudly at the moment of divergence; the
failure surfaces one step later, in a fresh session, with a misleading message.

## Acceptance Criteria

- [ ] `src/coga/step_gate.py` registers a new completion-gate token `dev` whose
  predicate is truthy only when the blackboard has a usable `branch:` (present,
  not a `(placeholder)`) **and** a usable `worktree:` line, via
  `parse_branch_name` / `parse_worktree_path` from `coga.autoclose` (lazily
  imported, like the `pr` gate). `publish_current_branch` stays `False`.
- [ ] The gate's remediation message teaches the stranded-write failure: if
  `## Dev` was written from inside the feature checkout, it landed in that
  checkout's ticket copy; record `branch:`/`worktree:` in the ticket copy of
  the checkout `coga bump` runs from (or re-run bump from the checkout that
  has the write — case 3 above is legal).
- [ ] The three packaged code workflows
  (`src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md`,
  `with-review.md`, `with-self-review.md`) declare `requires: dev` on their
  `implement` step, with a body sentence documenting the gate in the same style
  as the existing `requires: pr` prose. (The live repo has no
  `coga/workflows/code/` copies to mirror — verified.)
- [ ] `coga bump` off a step declaring `requires: dev` fails loudly when the
  ticket copy it reads lacks usable `branch:`/`worktree:` lines, and advances
  when they are present. Rewinds (`--to`/`--backward`) stay ungated (existing
  behavior at `commands/bump.py:154`).
- [ ] `coga/skills/code/implement/SKILL.md` **and** its packaged copy state
  that the `## Dev` write must land in the same checkout `coga bump` will run
  from, and that bump enforces this via `requires: dev`.
- [ ] `coga/contexts/dev/code/SKILL.md` **and** its packaged copy mention the
  implement-step gate where they document `requires: pr`.
- [ ] `example/coga/workflows/code/with-review.md` declares `requires: dev` on
  its `implement` step so the seeded smoke path exercises the gate; smoke tests
  that bump past implement are updated to record `## Dev` first.
- [ ] Tests mirror the existing `requires: pr` gate tests in
  `tests/test_commands.py` (blocked with no `## Dev`; blocked on placeholder
  `branch: (pending)`; blocked when `branch:` is present but `worktree:` is
  missing; passes with both usable; rewind ignores the gate).
- [ ] `python -m pytest` passes and `coga validate --json` is clean against the
  example fixture.

## Proposed Shape

Selected fix: **candidate (d)** — a fail-loud completion gate, implemented
through the existing `requires:` machinery rather than new bump logic. The
enforcement point already exists and is already sound for this purpose:
`commands/bump.py:154-163` evaluates the gate against
`read_blackboard(ref.ticket_path)` — the ticket copy of the checkout bump runs
from — which is *by construction* the same copy `sync_task_state` will sync
moments later. Gate-checked copy == synced copy, so a passing gate proves the
write and the sync agree on one checkout, which is exactly what the Description
demands. Both compliant flows pass (cases 1 and 3); only the split (case 2)
is refused, in-session, while the implement agent is still alive to fix it.

Order of work:

1. `src/coga/step_gate.py` — add `_has_dev_linkage(blackboard_text)` (lazy
   import from `coga.autoclose`; branch usable per the same rule `open_pr.py:315`
   applies, i.e. non-empty and not `startswith("(")`; worktree non-empty) and
   register `"dev": StepGate(check=_has_dev_linkage, remediation=..., )`.
   ~15 lines; `workflow.py` and `validate` accept the token automatically via
   `known_gate_tokens()`.
2. `tests/test_commands.py` — mirror the `requires: pr` gate tests (see the
   existing `_set_step_requires` helper and the block at `tests/test_commands.py:476`).
3. Packaged workflow templates — `requires: dev` on `implement` + one prose
   paragraph each, styled after the existing `requires: pr` paragraphs.
4. Skill + context doc edits, live and packaged copies in the same PR
   (CLAUDE.md sync rule).
5. `example/coga/workflows/code/with-review.md` + affected smoke/fixture tests.

No changes to `bump.py`, `launch.py`, spawn infra, or `sync_task_state`.
Existing tickets keep their frozen workflows and are unaffected; the gate
applies to tickets created after the template change.

What (d) gives up, for the record: it does not *prevent* the stranded duplicate
copy in the worktree (an uncommitted one is later surfaced by `open-pr`'s
cleanliness gate at `open_pr.py:373-383`; a committed one can still seed a
`ticket.md` merge conflict on the PR — residual, follow-up recommended on the
blackboard); it gates only the machine-readable `branch:`/`worktree:` linkage,
not free-form blackboard prose stranded the same way; and it relies on the
agent acting on a loud in-session refusal rather than making the split
impossible.

## Out of Scope

- **(a) Placement:** making `coga launch` place agents in the recorded
  worktree, or threading `cwd=` through `spawn_agent_session` /
  `run_with_done_marker`. It inverts the `dev/code` checkout boundary for every
  step and breaks the `open-pr` control-checkout requirement and the
  single-checkout assist. Prior thinking lives in the two `v2/` draft
  placeholders (not edited here, per the ticket Context).
- **(b)** Removing or weakening the skill's cd-into-the-worktree instruction —
  that would be another unverified instruction, the same bug class.
- **(c)** Sync-side reconciliation: `bump` discovering and merging divergent
  ticket copies across checkouts. Spun out as a follow-up draft ticket (see
  blackboard); it also cannot see independent `/tmp` fallback clones, so it
  cannot replace the gate.
- Retrofitting `requires: dev` onto existing tickets' frozen `workflow:`
  snapshots (human-owned field).
- Hardening against a *committed* stranded duplicate causing a `ticket.md` PR
  merge conflict (residual noted above; folded into the follow-up draft).
- Gating any blackboard content beyond the `branch:`/`worktree:` linkage.

## Context

Citations below were verified against the source on 2026-08-14; an earlier draft
of this ticket cited wrong lines, so trust these and re-check before relying on
any line number quoted elsewhere.

- Write side — nobody chooses the cwd: `spawn_agent_session` calls
  `run_with_done_marker(cmd, env, ...)` at `commands/launch.py:2052`, and
  `repl_supervisor.py:202` takes **no `cwd` parameter at all**. There is no
  `os.chdir` anywhere in `src/coga/`. The child inherits the supervisor's cwd by
  omission. A fix at this layer means threading `cwd=` through shared spawn
  infra — a signature change, not a one-line edit.
- `launch` **does** already read `worktree:`, contrary to earlier notes:
  `_recorded_single_checkout_assist_branch` (`commands/launch.py:1555-1586`)
  calls `parse_worktree_path` and requires `same_git_checkout(cfg.repo_root,
  worktree)` before authorizing the single-checkout PR assist. The accurate
  claim is narrow: launch reads `worktree:` to *authorize* the assist path, and
  never to *place* the child process.
- Read side: the `worktree:` read is `open_pr.py:321` (error at `:324`); the
  observed `branch:` failure is `open_pr.py:315`. `parse_worktree_path` is
  *defined* in `autoclose.py:101` but consumed by `branchcleanup.py:133`,
  `open_pr.py:321` and `:589`, `commands/retire.py:280`, and
  `commands/launch.py:1573`. `branchsweep.py` does not read the line — it
  enumerates live worktrees from Git. That consumer list is the blast radius of
  any change to what `worktree:` means.
- The `cd` is mandated, not optional: `code/implement/SKILL.md:68` ("Implement
  in the worktree"), recorded per `:34`, with `:32` and `:88` telling the agent
  to return to the primary checkout before the `## Dev` write and before `coga
  bump`. Nothing verifies it — no worktree check in `validate.py` or `bump.py`.
- `git.py:sync_task_state` (`:382`, docstring `:403-412`) already lands
  feature-branch task state on control via working-tree-free plumbing, and it is
  not gated. The real gap is downstream: `bump.py:130` syncs `ref.path` — the
  ticket dir of *the checkout bump ran from*. An agent that writes `## Dev` in
  the worktree and then returns to primary before bumping makes bump faithfully
  sync a `ticket.md` that never saw the write.
- Evidence lives outside this repo and is not inspectable from here: two
  occurrences on 2026-08-08 across the `FastJVM/admin` and
  `accounting/xero-reconcile` workspaces — the `open-pr` failure above, then a
  `ticket.md` merge conflict on their PR #90 (not a PR in this repo), the same
  divergence surfacing from the other side. The reproduction has to be
  constructed locally.
- Adjacent but not covering: `v2/reintroduce-per-launch-worktree-isolation`
  (scoped to the per-launch worktrees removed in PR #547, not the
  agent-created one `code/implement` mandates today) and
  `v2/use-worktree-when-starting-a-dev-task` (placement + litter). **Both are
  placeholders — unrefined idea capture, both still `status: draft`, neither
  approved or scheduled.** Read them for prior thinking only. This ticket is the
  live one on `worktree:`; do not treat either as a committed design, a
  constraint on the fix, or a reason to narrow scope, and do not edit them.
- The contract this violates is the attached `dev/code` context — read its
  checkout-boundary, retire, and `## Dev` grammar sections; all three constrain
  the fix.
- **First reproduce, then choose.** Because the skill read literally does not
  strand anything, the `design` step must first characterize the actual
  deviation — which write landed in which checkout — before selecting a fix.
  Don't design against an unconfirmed mechanism.
- Design is genuinely open. Candidates, with what is already known against each:
  (a) `launch` places the agent in `worktree:` — but this inverts the `dev/code`
  contract for *every* step, not just implement: `ticket.md`, `coga/log.md`,
  `bump`, `slack`, `block` would all default to the feature checkout, and the
  workflow's own `open-pr` section requires the control checkout. (a) fixes
  implement by breaking open-pr; carry that objection.
  (b) `code/implement` stops mandating the `cd` and edits the worktree from the
  primary checkout.
  (c) make the write and the sync agree on one checkout (note `sync_task_state`
  is already ungated — the gap is `bump.py:130` syncing the cwd's ticket dir).
  (d) a `bump`/`validate` guard that fails loudly on divergence.
  Say what each gives up, don't just pick.
- **Converge on one fix.** The option set above is more than one ticket's worth
  of work — (a) is a signature change on shared spawn infra, (d) is an afternoon.
  Design picks exactly one; spin the rest out as follow-up tickets. Out of scope:
  implementing more than the selected option.
- Must not break the deliberate single-checkout assist layout (`launch.py:469-530`
  and `:1555`), where the primary checkout *is* the recorded worktree and launch
  publishes to the PR branch.
- Repo conventions live in `CLAUDE.md`; read the `coga/codebase` context before
  editing `src/coga/` (microkernel rule, source layout, test expectations), and
  the `coga/sync` context for `sync_task_state`'s full contract. Neither is
  attached — both are large and the pointer is enough.
- If the fix touches shipped OS files (`coga/skills/code/implement/SKILL.md`,
  workflows, contexts), mirror the change into the packaged copy under
  `src/coga/resources/templates/coga/` in the same PR.
- Chicken-and-egg to expect: this ticket's own `implement` step runs through the
  exact path being fixed, so the implementing agent may strand its own
  blackboard writes. Write `## Dev` from the primary checkout only, push the
  branch, and confirm `git show <control-branch>:coga/tasks/<slug>.md` contains
  the `branch:` line before bumping into `open-pr`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design step (2026-08-19)

### Reproduction — mechanism confirmed

Scratch workspace: bare origin + clone seeded from `example/coga`, ticket
created with `coga create --workflow code/with-review`, status hand-set to
`in_progress` (launch normally does this), all commands run from current
source (`PYTHONPATH=src`). Two variants, mirroring the candidate mechanisms:

- **Variant A (the deviation):** `git worktree add ../wt -b feat main`, source
  change committed on `feat`, `## Dev` (branch:/worktree:) written into
  *`../wt/coga/tasks/<slug>.md`*, then `coga bump` from the **primary**
  checkout. Result: bump advanced to step 2 and synced cleanly; primary's and
  origin/main's ticket both **lack** the `branch:` line; the `## Dev` block
  sits uncommitted in the worktree copy; `coga open-pr <slug>` then fails with
  exactly the production error: "No usable `branch:` recorded under `## Dev`
  on the blackboard. The implement step must create the feature branch…" —
  misleading, since implement did record it. Nothing failed loudly at any
  earlier point.
- **Variant B:** same worktree-side `## Dev` write, but `coga bump` run from
  **inside the worktree**. Result: fully correct — `sync_task_state`'s
  feature-branch path committed the ticket (with `## Dev`) on `feat` *and*
  landed it on control; origin/main and the primary checkout both show the
  `branch:` line and the step advance. So bump-from-worktree is already legal;
  only the *split* (write in one checkout, bump in another) strands.

Key code facts anchoring the fix:

- Gate site `commands/bump.py:154-163` evaluates `requires:` against
  `read_blackboard(ref.ticket_path)` — the same checkout-local copy
  `git.sync_task_state(cfg, ref.path)` syncs at `bump.py:130`. Gate-checked
  copy == synced copy, by construction. Forward bumps only; rewinds ungated.
- `step_gate.py` is an explicit tiny registry built for this ("any future step
  can gate on a recorded artifact by declaring `requires: <token>`"); the `pr`
  token is the model, including the lazy `coga.autoclose` import pattern.
- Parsers: `parse_branch_name` (`autoclose.py:139`), `parse_worktree_path`
  (`autoclose.py:163`); open-pr's usability rule for branch is "present and
  not `startswith('(')`" (`open_pr.py:315`).
- An uncommitted stranded duplicate in the worktree is later caught by
  open-pr's cleanliness gate (`open_pr.py:373-383` — "has uncommitted
  changes… commit or stash"); a *committed* one is the PR-merge-conflict
  residual (the 2026-08-08 PR #90 evidence shape).
- Live repo has no `coga/workflows/code/` — the code workflows exist only in
  the packaged bootstrap templates, so the `requires: dev` frontmatter change
  lands there (plus the `example/` fixture copy). Skills and the dev/code
  context exist in both live and packaged copies and must stay in sync.

### Decision — candidate (d), as a `requires: dev` step gate

(a) launch-places-agent rejected: inverts the dev/code checkout boundary for
every step, breaks open-pr's control-checkout requirement and the
single-checkout assist, and needs a `cwd=` signature change through shared
spawn infra. (b) drop-the-cd rejected: another unverified instruction — the
same bug class this ticket exists to close. (c) sync-side reconciliation
rejected for now: in the failure mode the primary copy has no `worktree:`
pointer to follow (the pointer itself is what got stranded), `git worktree
list` cannot see independent `/tmp` fallback clones, and merging divergent
free-form markdown needs semantics nobody has asked for. (d) wins: ~15 lines
in an existing registry, refuses the bump in-session while the implement agent
can still fix it, and both compliant flows (variants 1 and B) pass unchanged.

### Follow-up

- Created draft `detect-stranded-ticket-writes-across-checkouts` capturing
  candidate (c) plus the committed-duplicate PR-conflict residual.
- Candidate (a)-shaped placement thinking already lives in the two `v2/` draft
  placeholders named in the ticket Context; no new ticket, and they were not
  edited.

## Open Questions

- **Token name:** `dev` (matches the `## Dev` section it checks) vs `branch`.
  Spec says `dev`; trivial to rename in review-design.
- **Data check only?** The gate checks that `branch:`/`worktree:` parse as
  usable; it does *not* check the worktree exists on disk. Proposal: keep it a
  pure data check (gate philosophy per `step_gate.py` docstring; existence is
  environment-dependent and open-pr already verifies it). OK?
- **Example fixture ripple:** adding `requires: dev` to
  `example/coga/workflows/code/with-review.md` means smoke tests that bump
  past implement must first record `## Dev`. Accept that test churn, or leave
  the fixture ungated? Spec assumes: accept it, so the smoke path stays
  representative.
- **Retrofit:** existing in-flight code tickets keep their frozen ungated
  workflows. Proposal: no retrofit — frozen `workflow:` is human-owned; hand
  edit per ticket only if a human wants the guard on a live task.
