---
title: Run recurring agent templates off the control branch
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
step: 2 (evaluate-design)
---

## Description

The hard remainder of "recurring should run from anywhere". Two sibling tickets
cover the easy cases: `service-recurring-from-a-temp-control-worktree-ins`
services the `--all` child's deterministic templates from a created temp
worktree, and `reuse-the-existing-control-worktree-for-recurring` runs the
single-repo sweep from a control worktree that already exists.

What neither covers: running an **agent-backed** recurring template — `dream`,
and the delegating `resolve-conflicts` — when the operator is off the control
branch and **no worktree holds control**, so a checkout has to be created for
the session to run in.

This is not a small extension of the sibling designs. An attended agent session
is long-lived, writes files, creates its own worktrees, and records paths that
outlive the run, so the temp-and-delete shape that is correct for a
seconds-long deterministic sweep breaks in specific, known ways (below). The
design step's job is to decide whether a created checkout for agent sessions is
worth having at all, and if so, what shape it takes — a *persistent* control
worktree being the leading candidate over a throwaway one.

Both siblings have landed. Launch this only after `stop-using-worktrees` has
also merged: it removes linked worktrees from ordinary ticket work, which
changes two of the three known breaks below, so the design has to be written
against that code rather than today's.

If the conclusion is "do not build", that is a complete and successful outcome
for this step, not a failure to finish it. Write the recommendation and its
reasoning into `## Description` and on the blackboard, then run `coga bump` as
normal — the `code/design` skill has no close-unbuilt affordance and will
otherwise push toward `implement`. Do not stop without bumping; the owner
cancels the ticket at the `review-design` gate.

### Design outcome (2026-10-02): do not build

**Recommendation: close this ticket unbuilt.** Coga should not create a
checkout, throwaway or persistent, to run agent-backed recurring templates
when the operator is off control and no worktree holds control. Since
`stop-using-worktrees` merged (`e122d774`, PR #896), any linked worktree that
holds the control branch, whoever made it, makes every ordinary ticket launch
in the operator's own checkout refuse. That conflict outweighs the small gap
this ticket would close.

Reasoning, checked against code on `main` as of 2026-10-02:

1. **The gap is narrow, and attended by construction.** Ten templates now
   ship in `coga/recurring/`. Seven carry `ticket.py` (`autoclose-merged`,
   `blocker-reminders`, `branch-sweep`, `phone-home`, `skill-update`,
   `upstream-coga`, `usage-report`); the `--all` temp-worktree path already
   serves them. Three are agent-backed: `dream`, plus the delegating
   `resolve-conflicts` and `address-pr-comments`. Agent and delegated launches
   need a TTY (`coga/recurring/scheduling`, `coga/recurring/delegation`), so
   the case only arises when a human is at the terminal. That human gets a
   refusal (`recurring_runner._refuse_non_control_branch`) naming
   `git switch <control>` as a remedy.
2. **Being off control is now short-lived.** Under `dev/checkouts`, every
   code step starts and ends on `main`, and `coga launch`
   (`git.prepare_control_checkout` plus the return half) moves the invoking
   checkout back to `main` around each session. Between steps the operator's
   checkout is on control, and a sweep or `coga dream` there needs no relay.
   What remains is "the human is on a feature branch by hand", and
   `git switch main` is the obvious remedy for that.
3. **A persistent control worktree now fights ordinary ticket work.**
   `git.prepare_control_checkout` refuses when `worktree_holding_branch(root,
   control)` returns a different checkout ("`main` is checked out in another
   worktree … `git worktree remove <path>`"). A Coga-kept control worktree
   would therefore make every `coga launch <ticket>` from the operator's
   primary checkout refuse, and would stop `git switch main`. The old leading
   option is no longer a candidate, whoever owns it.
4. **A throwaway created checkout has one break left, and it got worse.**
   Re-verified against merged code:
   - Break #1 (the feature worktree lands inside the temp parent) **is gone**.
     `code/implement` makes the branch in the launch checkout with
     `git branch` / `git switch` and forbids a linked worktree. The branch is
     a shared ref, so it outlives the checkout once pushed.
   - Break #2 (a temp `worktree:` path is recorded) **is gone**.
     `step_gate._has_branch_linkage` needs only `branch:`. `worktree:` is
     written only by the sandbox clone fallback. `open_pr._checkout_mode`
     needs only that the invoking checkout is on control, and pushes the
     branch by name.
   - Break #3 (lock duration) **still holds and is worse**. For the whole
     session, often hours, the created checkout holds `main`. During that
     time the operator cannot `git switch main`, and every ticket launch from
     their checkout refuses through `prepare_control_checkout`. A seconds-long
     sweep can afford that lock; an attended agent session cannot.
   On top of that, the created checkout would need `.agent-skills/` and the
   ignored `.claude/skills/coga` / `.codex/skills/coga` discovery links.
   `dev/checkouts` notes that those links do *not* self-heal.
5. **The "operator creates it by hand" branch is already shipped** (sibling 2,
   relay), and it inherits conflict 3. So the honest remedy is
   `git switch <control>`, not a new artifact.

What a created checkout would change if built anyway: the agent would scan the
control tip rather than the operator's tree, the same as the relay case. That
answer does not change, and it was never the blocker.

### Acceptance criteria

- [ ] Owner accepts or rejects the do-not-build recommendation at
      `review-design`. On acceptance, the ticket is canceled with no code
      change.
- [ ] The follow-up in *Open Questions* (the relay refusal recommending
      `git worktree add`, which now conflicts with `prepare_control_checkout`)
      is either filed as its own ticket or explicitly declined. It is not
      folded in here unless the owner retargets this ticket.

### Proposed shape

None. No checkout is created and no code changes. If the owner retargets this
ticket to the follow-up instead of canceling, its shape is: in
`recurring_runner._refuse_non_control_branch`, change both `absence` messages
(no holder; unusable holder) so `git switch <control>` is the primary remedy
and creating a control worktree is either dropped or carries a warning that it
blocks ticket launches. Mirror that in `coga/internals/recurring-control` and
its packaged twin, and update the tests that assert the refusal text.

### Out of scope

- Any Coga-created checkout for agent sessions, throwaway or persistent.
- Removing the existing-control-worktree relay (sibling 2). It stays as a
  supported path for operators who choose that layout.
- Everything already listed under *Not this ticket* below.

## Context

Cite symbols, not line numbers. `5243dfd5` (`delegate:` field, 2026-08-26)
moved ~306 lines in `recurring_runner.py` and invalidated the line citations in
this work's first draft.

### Known breaks in the throwaway-worktree shape

These were established failures as of 2026-09-09. `stop-using-worktrees`
(see *Dependency* below) is expected to remove #1 and may shrink or remove #2;
#3 stands regardless. Re-verify each against merged code. A design that keeps
the throwaway shape must answer whichever survive.

1. **The agent's own worktree lands inside the directory cleanup deletes.**
   `coga/skills/code/implement/SKILL.md` instructs `git worktree add
   ../coga-<branch-name> -b <branch-name> main`. From
   `/tmp/coga-recurring-X/checkout`, `../coga-<branch>` resolves inside the temp
   parent that the sibling's `finally` `rmtree`s. A Dream run that opens a
   ticket, branches, and implements would have its feature checkout destroyed by
   cleanup. This is the shipped skill's default instruction, not a hypothetical.
   *Expected to go away:* `stop-using-worktrees` makes `code/implement` branch
   in the launch checkout with no linked worktree, so the feature branch would
   live in the created checkout itself. Confirm; note the branch then outlives
   the checkout only as a ref, which is fine once pushed.

2. **`worktree:` gets recorded pointing at a temp path.** `src/coga/open_pr.py`
   reads it back via `parse_worktree_path` and requires that checkout to exist,
   be on the branch, be clean and ahead of main — and additionally refuses when
   `not same_git_checkout(cfg.repo_root, worktree)` or `is_linked_worktree(...)`,
   a fifth interaction with checkout identity. After cleanup it does not exist.
   Relatedly the `implement` step's `requires: branch` gate
   (`src/coga/step_gate.py`, `_has_branch_linkage`) demands *both* `branch:` and
   `worktree:`, and parses only blackboard text — it never stats the recorded
   path. A bump from a different checkout therefore reads a different
   `ticket.md` and can pass or fail on a stale `## Dev` block; the gate never
   notices the worktree is gone, and `open-pr` is where that surfaces.
   *Depends on:* `stop-using-worktrees` decides whether `worktree:` is kept,
   dropped, or made optional in `dev/dev-record`, and reworks
   `open_pr._checkout_mode`. Re-read `_has_branch_linkage` and `open_pr` after
   it merges; if neither requires a surviving recorded checkout, this break is
   gone.

3. **Lock duration is wrong by an order of magnitude.** Checking the control
   branch out *is* the concurrency lock in the sibling's design, and that is
   correct for a sweep measured in seconds. For an agent session it means no
   other checkout of `main` anywhere on the machine — including the operator's
   own `git switch main` in another terminal — for `COGA_REPL_IDLE_TIMEOUT`
   (15 min default) plus `max_session`, potentially hours.

A **persistent** control worktree removes the data-loss path, the recording
path, and the cleanup-on-signal problem in one move, at the cost of a durable
directory to manage. It was the leading option while breaks #1 and #2 stood;
if `stop-using-worktrees` removes them, a throwaway created checkout may be
viable again and the comparison must be redone rather than assumed. Evaluate
both — and name its owner
explicitly, because that is the whole decision: *who creates it, where, when,
and who removes it.* If the answer is "the operator creates it once, by hand",
this ticket collapses into sibling 2's already-shipped case plus a
documentation line, and closure is the honest outcome. If the answer is "Coga
creates and keeps it", that is a new durable on-disk artifact in a system whose
principles favor legible, git-backed state — argue for it on those terms rather
than filing it under "a directory to manage".

### Scope check the design must perform first

The payoff here is two templates out of seven. Five carry `ticket.py`
(`autoclose-merged`, `blocker-reminders`, `branch-sweep`, `digest`,
`skill-update`) and are served by the siblings. Only `dream` and
`resolve-conflicts` are agent-backed. If the sibling ticket
`reuse-the-existing-control-worktree-for-recurring` admits agent templates into
an existing control worktree, the remaining gap is "agent template, off
control, and no control worktree exists" — which may be rare enough not to
justify the machinery. **Say so if that is the conclusion**; recommending this
ticket be closed unbuilt is a valid design outcome.

Sibling state as of 2026-09-25: both siblings are `done`.

- `service-recurring-from-a-temp-control-worktree-ins` landed as `e44e7c29`
  (PR #749). The shipped code is considerably richer than that ticket's
  Proposed Shape (ownership markers, stale-worktree reaping,
  process-group-aware cleanup that retains rather than unlinks under a live
  child, run-log preservation, and `_control_worktree_agent_refusal` in
  `recurring_runner`, which refuses agent phases in that mode). Read the code,
  not that ticket's design section.
- `reuse-the-existing-control-worktree-for-recurring` landed as `eb725dfa3`
  (PR #846). It **does** admit agent templates and `delegate:` templates into an
  existing control worktree (stdio and TTY inherited; see
  `coga/internals/recurring-control`), and ships `config.LOCAL_CONFIG_ENV`
  (`COGA_LOCAL_CONFIG`). So the remaining gap is exactly "agent template, off
  control, no control worktree exists".

### Dependency: `stop-using-worktrees`

Owner direction (2026-09-25): ordinary ticket work stops using linked
worktrees; Coga-internal recurring/Dream worktrees stay. That is ticket
`stop-using-worktrees` (`in_progress` at `review` as of 2026-09-25), whose
description keeps `coga/internals/recurring-temp-worktrees` explicitly out of
scope. Its effect here: an agent session inside a created control checkout
would branch and commit in that checkout, not in a sibling `../coga-<branch>`,
and must end back on `main` — which is exactly the control branch the created
checkout holds. Check that its "start clean on `main`, end on `main`" rule
composes with a created checkout (fast-forward to `origin/main` inside a
worktree that owns `main`), and whether its "dirty or on another ticket's
branch → stop and ask/block" rule fires spuriously there.

### Delegating templates

`resolve-conflicts` is a `delegate:` template as of `5243dfd5`: the sweep
performs the delegated launch in the operator's own terminal, with its own
TTY-admission rules and a `coga/log.md` slack-sentinel completion path.

Sibling 2 *has* analyzed this for the reuse case and concluded `delegate:`
templates work unchanged, because the relay inherits stdio so the TTY survives.
Do not redo that reasoning. The narrower open question this design owns is
whether it still holds when the checkout is one Coga created rather than one the
operator already owns.

### What the agent sees

An agent session inside a control checkout scans the control tip, not the
operator's dirty feature-branch tree. Sibling 2 already settled this for the
reuse case and calls it intended. The remaining question is narrower — whether a
*created* checkout changes that answer (probably not). Whatever the choice,
state it: it changes what the feature *means*, not just how it is built.

### Worktree hygiene facts

- `coga.local.toml`, `.coga/`, and `.agent-skills/` are all gitignored
  (`coga/.gitignore`), so a fresh checkout lacks them.
  - `coga.local.toml`: sibling 1 seeds a copy at 0600, or `load_config` raises
    before anything runs. That is not the only option — sibling 2 adds
    `config.LOCAL_CONFIG_ENV` / `local_config_path(root)` and a
    `COGA_LOCAL_CONFIG` env handoff that reads the operator checkout's file with
    no copy at all. For a *persistent* worktree the env handoff is arguably
    better: it writes no gitignored file into a durable operator-owned tree.
    Weigh both.
  - `.agent-skills/` is rebuilt by `src/coga/commands/launch.py`
    (`_refresh_agent_skills_for_launch` → `refresh_agent_skill_view`) and
    self-heals. The sibling's note arguing it "is not needed" reasons from
    recipes not reading the merged skill view; that reasoning is void here,
    because this path runs agent sessions.
  - `.coga/` has a partial shipped answer, not a blank one:
    `_persist_control_worktree_run_logs` / `_copy_control_worktree_run_log` copy
    `.coga/recurring-runs/*.md` out of the temp checkout into the operator's
    durable workspace before teardown, and retain the whole worktree if that
    transfer fails. Extend that decision; don't re-open it from scratch.
- Keeping a created worktree out of `--all` is marker-based, not location-based.
  `src/coga/workspace_discovery.py` defines `CONTROL_WORKTREE_DIR_PREFIX`
  (`coga-recurring-`) and `CONTROL_WORKTREE_OWNER_FILE`
  (`.coga-recurring-owner.json`); `_is_control_worktree_parent` and
  `_is_within_control_worktree` exclude such trees *wherever they live*, even
  when the explicit scan root is that parent. So a persistent control worktree
  may sit next to the repo and stay invisible to `discover_coga_repos` — which
  removes one standing objection to persistence.
- The checkout must have the control branch checked **out**, not `--detach`:
  `git.sync_log` refuses on a detached HEAD and `_sync_recurring_create_paths`
  skips the local commit there, so the serviced-period ledger line would never
  reach control and every sweep would re-fire the period.

### Context to read and update

The old monolithic `coga/contexts/coga/recurring/SKILL.md` was split into
focused topics under `docs/contexts/`. They are cited, not attached; read them
fresh, since they may move again before launch:

- `coga/internals/recurring-control`
  (`docs/contexts/coga/internals/recurring-control/SKILL.md`) — where recurring
  runs may start: the control-branch requirement and off-branch relay (formerly
  `## Recurring runs start on the control branch`). The contract in question.
- `coga/internals/recurring-temp-worktrees`
  (`docs/contexts/coga/internals/recurring-temp-worktrees/SKILL.md`) — how an
  `--all` child services an off-branch checkout from a temporary worktree
  (formerly `## An --all child services an off-branch checkout from a temporary
  worktree`, added by sibling 1, `e44e7c29`). This is where the current
  created-worktree contract lives, and the topic a design here extends or
  contradicts.
- `coga/internals/recurring-admission` for per-child refresh and period
  leases, and `coga/recurring/delegation` / `coga/recurring/scheduling` for TTY
  admission of delegated and agent launches (formerly the `delegate:` gotcha).

Any behavior change rewrites the affected topic in the same PR, per the repo's
context-in-the-same-PR rule. These topics now **do** have packaged twins under
`src/coga/resources/templates/coga/bootstrap/contexts/coga/`, byte-checked by
`tests/test_packaging.py`; keep both copies in sync.

### Not this ticket

- The `--all` path (`service-recurring-from-a-temp-control-worktree-ins`).
- Reusing an existing control worktree
  (`reuse-the-existing-control-worktree-for-recurring`).
- The diverged-control case. That keeps failing loud.
- Running recurring from a separate clone or install pointed at another repo.
- Moving the operator's own checkout (stash → switch → run → switch back → pop).
  Rejected with full reasoning in
  `service-recurring-from-a-temp-control-worktree-ins`; not an open question.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

---

## Design notes (2026-10-02, design step)

- Outcome: **do not build**. Full reasoning is in `## Description` →
  *Design outcome*. Expect the owner to cancel at `review-design`.
- New fact since the ticket was written: `git.prepare_control_checkout` (the
  launch boundary from `stop-using-worktrees`) refuses when control is checked
  out in another worktree. Any persistent control worktree therefore blocks
  ordinary ticket launches from the primary checkout, and a throwaway one
  blocks them for the length of the session.
- Template census has drifted from `## Context`. There are now 10 templates:
  7 `ticket.py` and 3 agent-backed (`dream`, plus `resolve-conflicts` and
  `address-pr-comments` via `delegate:`). `digest` no longer exists.
- Breaks #1 and #2 are confirmed gone against merged code; #3 stands and is
  worse (see Description).

## Open Questions

- The relay's refusal (`recurring_runner._refuse_non_control_branch`, both
  `absence` branches) and `coga/internals/recurring-control` still tell the
  operator to `git worktree add ../<repo>-<control> <control>`. Following that
  advice now makes every `coga launch <ticket>` from the primary checkout
  refuse via `git.prepare_control_checkout`. Should this be filed as a small
  follow-up ticket (lead with `git switch <control>`, or warn about the
  conflict), should this ticket be retargeted to it, or should it be left
  alone?

---

## Blockers

- [x] [2026-09-09 12:03] [agent:nick] id=20260909T120328 Blocked on sibling `reuse-the-existing-control-worktree-for-recurring` merging first. Its branch `recurring-control-worktree` (a8c12607) is unmerged with no PR open, and its `COGA_LOCAL_CONFIG` / `local_config_path` seam is still in peer-review. That seam, plus its 'agent templates are admitted' and 'delegate: works unchanged' conclusions, are load-bearing for this ticket's ## Context and for its likely close-unbuilt outcome. Unblock once that branch lands, then re-verify ## Context against the merged code before launching design.
  resolved: [2026-09-25 11:19] [human:nicktoper] Sibling reuse-the-existing-control-worktree-for-recurring merged as eb725dfa3 (PR #846); ## Context re-verified and updated 2026-09-25.

- [x] [2026-09-25 11:19] [agent:claude] id=20260925T111958 Wait for stop-using-worktrees to merge. It removes linked worktrees from ordinary ticket work and decides the fate of the worktree: field, which changes known breaks #1 and #2 in ## Context. Unblock once it lands, re-verify those two breaks against merged code, then launch design.
  resolved: [2026-10-02 11:07] [human:nicktoper] stop-using-worktrees merged as e122d774 (PR #896). Re-verified: break #1 gone (code/implement branches in the launch checkout, no ../coga-<branch>); break #2 largely gone (branch gate needs only branch:; worktree: only for the read-only-git sandbox clone fallback). open_pr._checkout_mode to be re-checked in design.


---

## Blocker reminders

- 8cf614ca1bd7 last_reminded: 2026-09-11 10:00

- a18bb9968178 last_reminded: 2026-09-28 08:36
