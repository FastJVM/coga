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
step: 3 (implement)
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

- [ ] `src/coga/step_gate.py` registers a new completion-gate token `branch`
  whose predicate is truthy only when the blackboard has a usable `branch:`
  **and** a usable `worktree:` line, via `parse_branch_name` /
  `parse_worktree_path` from `coga.autoclose` (lazily imported, like the `pr`
  gate). `publish_current_branch` stays `False`. The token checks **both**
  lines because `coga open-pr` rejects on either one missing — a branch-only
  gate would just move the late failure. The explicit `(placeholder)` guard is
  needed on the **branch** half only: `parse_worktree_path` already rejects a
  `(`-prefixed value (`autoclose.parse_worktree_path`), while
  `parse_branch_name` returns it verbatim. Do not write a redundant worktree
  placeholder check, or a test for it that can never fail.
- [ ] The gate's remediation message teaches the stranded-write failure: if
  `## Dev` was written from inside the feature checkout, it landed in that
  checkout's ticket copy; record `branch:`/`worktree:` in the ticket copy of
  the checkout `coga bump` runs from (or re-run bump from the checkout that
  has the write — case 3 above is legal). It must also name **both** required
  lines explicitly, and tell the agent to confirm the recorded lines describe
  *this* attempt's branch and checkout. Both are load-bearing: the generic
  prefix `gate_unmet_reason` prepends is rendered from the token name, so with
  token `branch` it reads "requires a recorded `branch` artifact … but none is
  present" even when `worktree:` is the missing field — the remediation string
  is the only place that can say otherwise. And the gate is presence-based, so
  it cannot tell a stale `## Dev` from a fresh one (see the retry hole under
  Proposed Shape).
- [ ] The three packaged code workflows
  (`src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md`,
  `with-review.md`, `with-self-review.md`) declare `requires: branch` on their
  `implement` step, with a body sentence documenting the gate in the same style
  as the existing `requires: pr` prose. (The live repo has no
  `coga/workflows/code/` copies to mirror — verified.)
- [ ] `coga bump` off a step declaring `requires: branch` fails loudly when
  the ticket copy it reads lacks usable `branch:`/`worktree:` lines, and
  advances when they are present. Rewinds (`--to`/`--backward`) stay ungated
  (existing behavior — the gate call in `commands/bump.py` is guarded on the
  forward path only).
- [ ] `coga/skills/code/implement/SKILL.md` **and** its packaged copy state
  that the `## Dev` write must land in the same checkout `coga bump` will run
  from, and that bump enforces this via `requires: branch`.
- [ ] `coga/contexts/dev/code/SKILL.md` **and** its packaged copy mention the
  implement-step gate where they document `requires: pr`.
- [ ] Tests mirror the existing `requires: pr` gate tests in
  `tests/test_commands.py` (blocked with no `## Dev`; blocked on placeholder
  `branch: (pending)`; blocked when `branch:` is present but `worktree:` is
  missing; passes with both usable; rewind ignores the gate). Add one more:
  the single-checkout assist layout, where the primary checkout *is* the
  recorded worktree, still bumps cleanly — that flow is asserted, not
  verified, by the reproduction, and `publish_current_branch=False` interacts
  with its push behavior.
- [ ] `python -m pytest` passes and `coga validate --json` is clean against the
  example fixture.

## Proposed Shape

Selected fix: **candidate (d)** — a fail-loud completion gate, implemented
through the existing `requires:` machinery rather than new bump logic. The
enforcement point already exists and is already sound for this purpose:
the forward-bump gate call in `commands/bump.py` evaluates
`step_gate.gate_unmet_reason` against `read_blackboard(ref.ticket_path)` — the
ticket copy of the checkout bump runs from — which is *by construction* the
same copy `git.sync_task_state(cfg, ref.path)` syncs moments later (both come
off the same `TaskRef`). Gate-checked copy == synced copy, so a passing gate proves the
write and the sync agree on one checkout, which is exactly what the Description
demands. Both compliant flows pass (cases 1 and 3); only the split (case 2)
is refused, in-session, while the implement agent is still alive to fix it.

Order of work:

1. `src/coga/step_gate.py` — add `_has_branch_linkage(blackboard_text)` (lazy
   import from `coga.autoclose`; branch usable per the same rule `open_pr`
   applies to `parse_branch_name`, i.e. non-empty and not `startswith("(")`;
   worktree non-empty, its placeholder guard already inside the parser) and
   register `"branch": StepGate(check=_has_branch_linkage, remediation=...)`.
   ~15 lines; `workflow.py` and `validate` accept the token automatically via
   `known_gate_tokens()`.
2. `tests/test_commands.py` — mirror the `requires: pr` gate tests (see the
   existing `_set_step_requires` helper and the `requires: pr` block beside it).
3. Packaged workflow templates — `requires: branch` on `implement` + one prose
   paragraph each, styled after the existing `requires: pr` paragraphs.
4. Skill + context doc edits, live and packaged copies in the same PR
   (CLAUDE.md sync rule).

The example fixture (`example/coga/workflows/code/with-review.md`) is
deliberately **not** gated: its `implement` step runs `infra/testing-conventions`
and does no worktree work, its `pr` step already exercises the same gate
machinery end-to-end in the smoke path, and gating it would force a `## Dev`
write through the fixture assumptions of every test that touches
`with-review`. Owner decision, 2026-08-24, on the evaluator's recommendation.

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

Two further holes, named so `implement` does not rediscover them as surprises:

- **Presence, not freshness.** `code/implement`'s SKILL tells a resumed session
  to *reuse* an existing `branch:`/`worktree:`. On a relaunch or retry, the
  primary copy already carries usable lines from the prior attempt, so the gate
  passes on those while this attempt's writes strand — the retry path is
  exactly where stranding is most likely, and the gate is blind to it. The
  remediation text (AC above) is the only mitigation: it tells the agent to
  confirm the lines describe this attempt.
- **Cheaply satisfiable.** A refused agent can hand-copy two lines into the
  primary copy and pass the gate without moving the stranded write, which then
  resurfaces as `open-pr`'s uncommitted-changes refusal or as the `ticket.md`
  merge conflict. The gate raises the cost of the wrong path and moves the
  failure in-session; it does not make the wrong path impossible.

Also note this workflow has no peer-review step, and `design-then-implement`'s
`open-pr` prose falls back to `## Description` for the PR body — which here
describes only the bug. `implement` should write a `## PR` section on the
blackboard describing the fix.

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

Citations here name **symbols, not line numbers**. An earlier draft pinned line
numbers twice; both sets had drifted within days (the 2026-08-24 evaluator found
roughly two-thirds stale, one pointing at the wrong module). Grep for the symbol.

- Write side — nobody chooses the cwd: `spawn_agent_session` calls
  `run_with_done_marker(cmd, env, ...)`, and `run_with_done_marker` in
  `src/coga/repl_supervisor.py` takes **no `cwd` parameter at all**. There is no
  `os.chdir` anywhere in `src/coga/`. The child inherits the supervisor's cwd by
  omission. A fix at that layer would mean threading `cwd=` through shared spawn
  infra — a signature change, not a one-line edit. (Out of scope; see below.)
- `launch` **does** already read `worktree:`, contrary to earlier notes:
  `_recorded_single_checkout_assist_branch` in `src/coga/commands/launch.py`
  calls `parse_worktree_path` and requires `same_git_checkout(cfg.repo_root,
  worktree)` before authorizing the single-checkout PR assist. The accurate
  claim is narrow: launch reads `worktree:` to *authorize* the assist path, and
  never to *place* the child process. That layout — primary checkout *is* the
  recorded worktree — must keep working; it gets its own gate test.
- Read side: `src/coga/open_pr.py` rejects on a missing/placeholder `branch:`
  **and**, separately, on a missing `worktree:` (and then on a `worktree:` that
  is not a directory). Both refusals are why the gate checks both lines.
  `parse_worktree_path` is defined in `src/coga/autoclose.py` and consumed by
  `branchcleanup.py`, `open_pr.py`, `commands/retire.py`, and
  `commands/launch.py`; `branchsweep.py` does *not* read the line — it
  enumerates live worktrees from Git. That consumer list is the blast radius of
  any change to what `worktree:` means. Note the asymmetry the gate depends on:
  `parse_worktree_path` rejects a `(`-prefixed placeholder itself,
  `parse_branch_name` does not.
- The `cd` is mandated, not optional: `code/implement/SKILL.md` says to
  implement in the worktree, record `## Dev`, and return to the primary checkout
  before the `## Dev` write and before `coga bump`. Nothing verifies the return
  — that is the whole bug. The same SKILL also tells a *resumed* session to
  reuse an existing `branch:`/`worktree:`, which is the source of the gate's
  freshness hole (Proposed Shape).
- `git.sync_task_state` already lands feature-branch task state on control via
  working-tree-free plumbing, and it is not gated. The gap is downstream: the
  sync call in `src/coga/bump.py` passes `ref.path` — the ticket dir of *the
  checkout bump ran from*. An agent that writes `## Dev` in the worktree and
  returns to primary before bumping makes bump faithfully sync a `ticket.md`
  that never saw the write. (`sync_task_state` itself is not being changed, so
  the `coga/sync` context is not needed for this work.)
- Workflow resolution matters for the AC: this repo has no `coga/workflows/code/`,
  so `paths.resolve_workflow_path` falls through to the packaged bootstrap
  copies. Editing the templates under `src/coga/resources/templates/coga/` is
  therefore not just shipping a change to other repos — it changes what *this*
  repo freezes into its own future code tickets. The example fixture is
  deliberately left ungated (see Proposed Shape).
- Evidence lives outside this repo and is not inspectable from here: two
  occurrences on 2026-08-08 across the `FastJVM/admin` and
  `accounting/xero-reconcile` workspaces — the `open-pr` failure above, then a
  `ticket.md` merge conflict on their PR #90 (not a PR in this repo), the same
  divergence surfacing from the other side. The design step reproduced both
  locally; see the blackboard.
- Prior thinking only, not constraints: `v2/reintroduce-per-launch-worktree-isolation`
  and `v2/use-worktree-when-starting-a-dev-task` are unrefined `status: draft`
  placeholders on agent placement. Do not treat either as committed design, and
  do not edit them.
- The contract this fix must respect is the attached `dev/code` context — its
  checkout-boundary, retire, and `## Dev` grammar sections all constrain it.
- Repo conventions live in `CLAUDE.md`. The `coga/codebase` microkernel rule is
  satisfied trivially here — the change adds ~15 lines to `step_gate.py`, an
  existing shared module with existing consumers — so that context is not
  attached. If the fix touches shipped OS files (skills, workflows, contexts),
  mirror it into the packaged copy under `src/coga/resources/templates/coga/`
  in the same PR.
- **Chicken-and-egg, still live.** This ticket's own frozen workflow is ungated
  (owner decided against retrofitting in-flight tickets), so its `implement`
  step runs through the exact unguarded path being fixed and the new gate will
  not protect it. Write `## Dev` from the primary checkout only, push the
  branch, and confirm `git show <control-branch>:coga/tasks/<slug>.md` contains
  the `branch:` line before bumping into `open-pr`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: implement-branch-gate
worktree: /home/n/Code/claude/coga-implement-branch-gate

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

## Design decisions (owner, 2026-08-24)

Answers to the design step's open questions — these are settled; implement
follows them.

- **Token name:** `branch` (not `dev`). Registered in `STEP_GATES` as
  `"branch"`; the implement step declares `requires: branch`.
- **Data check only:** yes. The gate checks that the `## Dev` lines parse as
  usable values; it does **not** stat the worktree path or touch Git. Existence
  is environment-dependent and `open_pr.py:328` already verifies it.
- **Example fixture:** accept the churn. `example/coga/workflows/code/*.md`
  gets `requires: branch` on the implement step, and any smoke test that bumps
  past implement records a `## Dev` block first, so the fixture path stays
  representative of shipped behavior.
- **Retrofit:** none. Existing in-flight code tickets keep their frozen ungated
  workflows; frozen `workflow:` is human-owned and gets hand-edited only if a
  human wants the guard on a live task. (This ticket itself is one of them — its
  own implement step stays ungated.)

### Still to confirm before implement

- **Gate scope:** `open_pr.py` requires *both* `branch:` (`:312-319`) and
  `worktree:` (`:321-327`). A `branch` gate that checks only `branch:` still
  lets a bump through that open-pr then rejects for a missing `worktree:`.
  Proposal: the `branch` token checks both lines (name follows the primary
  artifact, like `pr`), so the gate exactly covers what the next step needs.

## Evaluator review (cold, 2026-08-24)

# Cold review — `launch-ignores-the-recorded-worktree-stranding-bla`

Reviewed at step 2 (review-design), against source at `fac1d268`.

## Verdict

The ticket is **substantively strong and nearly ready** — the mechanism is real, the reproduction is convincing, and (d) is the right pick. But it should **not** launch `implement` as-is. Two blocking problems: the ticket now contradicts itself on the gate token name, and roughly two-thirds of its code citations are stale enough to send a cold agent to the wrong lines (in one case, the wrong module).

## Blocking: the ticket says two different things about the token name

`## Acceptance Criteria` and `## Proposed Shape` specify the token `dev` in six places (lines 77, 87, 95, 98, 101, 103, 130). The owner's blackboard decision (line 337) says `branch`. Nothing marks which section is authoritative. Recency argues for `branch`, but a cold agent has no way to know that, and `review-design`'s own workflow prose says "Edit the ticket directly to correct scope or approach" — so the AC and Proposed Shape should be rewritten to `branch` before bumping, not left for `implement` to reconcile.

Related, and worth reopening: **`branch` is a poor token name for a two-field check.** `step_gate.py:88-90` renders the generic prefix from the token itself:

```
f"Cannot advance: this step requires a recorded `{token}` artifact on the "
f"blackboard, but none is present. " + gate.remediation.format(slug=slug)
```

With token `branch` and a check covering both lines, a ticket that records `branch:` but omits `worktree:` is told "requires a recorded `branch` artifact … but none is present" — factually false, and misleading in exactly the way the production error already was. `dev` (the section being gated) is the honest name. If the owner keeps `branch`, the remediation string must carry the both-fields explanation explicitly, because the prefix won't.

## Blocking: stale citations

The `## Context` header claims "Citations below were verified against the source on 2026-08-14 … trust these and re-check before relying on any line number quoted elsewhere." That claim is no longer true. Three commits landed on 2026-08-21/24 (`2343a9f6`, `ddd59dd5`, `11372a0c`) after the design step ran. Current reality:

| Ticket says | Actual |
|---|---|
| `commands/bump.py:154-163` (gate site) | `src/coga/commands/bump.py:183-201` |
| `commands/bump.py:130` syncs `ref.path` | **Wrong module.** `commands/bump.py` never calls `sync_task_state`. It is `src/coga/bump.py:140` and `:148` |
| `commands/bump.py:154` (rewinds ungated) | `src/coga/commands/bump.py:190` (`if not rewind and 1 <= current_idx <= total`) |
| `autoclose.py:101` / `:139` / `:163` (parsers) | `parse_branch_name` at `src/coga/autoclose.py:195`; `parse_worktree_path` at `:213` |
| `git.py:382` `sync_task_state`, docstring `:403-412` | `src/coga/git.py:593`, docstring `:610-640` |
| `commands/launch.py:2052` `run_with_done_marker` | `src/coga/commands/launch.py:2587` |
| `commands/launch.py:1555-1586` / `:1573` assist branch | `src/coga/commands/launch.py:2090` / `:2108` |
| `open_pr.py:315` branch usability rule | check is at `src/coga/open_pr.py:313`; `:315` is inside the error string |
| `open_pr.py:373-383` cleanliness gate | `src/coga/open_pr.py:377-383` |

Citations that **do** hold: `src/coga/repl_supervisor.py:202` (`run_with_done_marker`, and it genuinely has no `cwd` parameter); `src/coga/open_pr.py:321` / `:328`; `tests/test_commands.py:476` and the `_set_step_requires` helper at `:479`; `coga/skills/code/implement/SKILL.md:32`, `:34`, `:68`; no `os.chdir` anywhere in `src/coga/`; and the owner's own 2026-08-24 refs (`open_pr.py:312-319`, `:321-327`, `:328`) are all correct. `SKILL.md:88` is stale — the "return to the primary checkout … `coga bump`" instruction is now at `:96-97`.

The two claims doing load-bearing work survive the drift: `## Context`'s "no one chooses the cwd" and the Proposed Shape's **"gate-checked copy == synced copy, by construction."** The gate reads `read_blackboard(ref.ticket_path)` and the sync writes `git.sync_task_state(cfg, ref.path)` — both off the same `TaskRef`, so the argument holds even though both line numbers moved. **Recommendation: replace every line number in `## Context` with symbol names** (`step_gate.gate_unmet_reason`, `git.sync_task_state`, `open_pr._require_recorded_branch`-region) rather than re-pinning numbers that will drift again before `implement` runs.

## Description clarity

Good enough to start from — but only in combination with `## Proposed Shape`. `## Description` is purely a bug narrative and ends on an open design prompt ("Any fix has to say what makes the write and the read agree on one checkout"), which is stale now that the fix is chosen. The three characterized cases (lines 60-70) are the single most useful thing in the ticket and are worth preserving verbatim.

One downstream consequence worth writing into the ticket: this workflow has no peer/self-review step, and `design-then-implement.md`'s own `## open-pr` prose says the PR body falls back to `## Description`. Here that means the PR will describe the bug and never the fix. Instruct `implement` to write a `## PR` section on the blackboard.

## Does (d) close the failure mode?

It closes the **reproduced** one (variant A) cleanly, and preserves variant B. But there are four holes, and only two are acknowledged.

**Acknowledged in the ticket:** it gates only the machine-readable linkage, not free-form prose (note this now includes the `## PR` section above); and it does not prevent the stranded duplicate, only relocates when it bites.

**Not acknowledged, and both worth adding to the ticket before implement:**

1. **The gate is presence-based, not freshness-based.** `coga/skills/code/implement/SKILL.md:62-67` explicitly tells a resumed session to *reuse* an existing `branch:`/`worktree:`. On any relaunch or retry of `implement`, the primary copy already carries a usable `## Dev` from the prior attempt — so the gate passes on the old lines while this attempt's writes sit stranded in the worktree. That is precisely the retry path where stranding is most likely, and (d) is blind to it.

2. **The gate is trivially satisfiable without fixing anything.** A blocked agent's cheapest move is to hand-copy the two lines into the primary copy. Gate passes; the stranded duplicate stays in the worktree and resurfaces at `src/coga/open_pr.py:377-383` ("has uncommitted changes") if uncommitted, or as the `ticket.md` merge conflict if committed. The ticket's honest framing — "it relies on the agent acting on a loud in-session refusal" — understates this: it relies on the agent acting *correctly*, and the incorrect action is easier.

Neither invalidates (d). Both belong in the "what (d) gives up" paragraph, and (1) suggests the remediation text should tell the agent to *verify the lines match this attempt's branch*, not merely that they exist.

**A precision correction for the AC:** line 78-80 asks for a usability check on both parsers. `parse_worktree_path` **already rejects placeholders** at `src/coga/autoclose.py:228-229` (`if not path or path.startswith("(")`); `parse_branch_name` does **not** (`:210` returns the value or None). So the gate needs the `startswith("(")` guard on branch only — the worktree half is redundant. Worth stating so `implement` doesn't write a duplicate check and then a test that can never fail.

## Workflow fit

`code/design-then-implement` fits and has already earned its keep — the design step reproduced the bug, corrected the ticket's own premise (this is a compliance bug, not a launch/skill contradiction), and rejected three candidates with reasons. No mismatch.

Note the ticket's own `implement` step stays ungated (frozen workflow, owner decided no retrofit), so the chicken-and-egg warning at lines 256-260 is still fully live and is the only protection. Keep it prominent.

## Contexts

`dev/code` is the right and sufficient attachment: it is the checkout-boundary contract, it is a file the ticket must edit, and it documents `requires: pr` at `coga/contexts/dev/code/SKILL.md:143` — the exact spot AC line 100 targets. (Confirmed live and packaged copies are byte-identical today.)

The unattached pointers have decayed. `coga/sync` was pointed at for "`sync_task_state`'s full contract" — but the Proposed Shape now says "No changes to … `sync_task_state`", so that pointer is dead weight and should be dropped. `coga/codebase` (microkernel rule) is nominally right but the fix adds ~15 lines to an existing module with two existing consumers, so it is trivially compliant; a one-line note in `## Context` would beat the pointer.

Nothing important is missing, but one fact should be **copied into `## Context`** rather than left for discovery: this repo has no `coga/workflows/code/`, so `paths.resolve_workflow_path` (`src/coga/paths.py:57-73`) falls through to the packaged bootstrap copies — which is *why* editing the templates changes this repo's own future tickets. The ticket states the fact but not the mechanism, and the mechanism is what makes the AC correct.

## Scope

One ticket's worth. The design correctly refused to bundle (a) and spun (c) out as a draft. Code change is ~15 lines plus five mirrored tests; the bulk is documentation mirroring, which is mechanical.

**One item I would cut:** AC line 102 — `requires: branch` on `example/coga/workflows/code/with-review.md`. That fixture's `implement` step uses `infra/testing-conventions`, not `code/implement`, and does no worktree work at all, so gating it is not "representative of shipped behavior." Its `pr` step already carries `requires: pr` and already exercises the full gate machinery end-to-end at `tests/test_smoke.py:113-126`. Adding a second gate buys no new coverage while forcing a `## Dev` write into the smoke path and touching fixture assumptions across ~14 test files that reference `with-review`. The owner accepted this churn on 2026-08-24; I would ask them to reconsider — it is the largest chunk of work in the ticket and the lowest-value.

## Assumptions to question before implement

1. **Token name `branch`** — see above; the generic message text at `step_gate.py:88-90` will lie when `worktree:` is the missing field.
2. **"Both compliant flows pass unchanged."** True for variants 1 and B as reproduced, but not verified for the single-checkout assist layout, where the primary checkout *is* the recorded worktree. It should pass trivially (the `## Dev` is in the only copy there is), but `publish_current_branch=False` interacts with that layout's push behavior and deserves an explicit test, not an assumption.
3. **"Existing tickets keep their frozen workflows and are unaffected."** Correct, and confirmed by `workflow.py:133-138` / `validate.py:784-791` accepting only registered tokens — but note the corollary the ticket does not draw: **the gate protects nothing until tickets created after this PR reach their implement step.** Every in-flight code ticket, including this one, remains exposed. Whether that is acceptable is an owner call worth making explicitly.
4. **AC line 108's test list** omits the presence-but-stale case from hole (1). If the owner agrees that hole is real, the test list needs a row, or the ticket needs a sentence conceding it.

## Prompt size

32.6 KiB / ~8.3k tokens total. **No layer exceeds 40%** — the largest is `ticket_context` (dev/code) at 9.0 KiB, 27.6%, and it is directly load-bearing since the file must be edited. Nothing to flag under the stated rule.

Qualitatively, though, there is a clear trim for the `implement` step: `## Context` (5.8 KiB, 17.8%) is now mostly *design-phase* instruction — "First reproduce, then choose", "Design is genuinely open. Candidates (a)–(d) … Say what each gives up, don't just pick", "Converge on one fix." Those are not merely stale for `implement`; they actively instruct the agent to redo work the blackboard already settled. Cutting the candidate list and the reproduce-first mandate down to a two-line summary would remove ~2 KiB and, more importantly, remove a live source of confusion. The `v2/` placeholder paragraph (lines 216-222) can shrink to one sentence for the same reason.
