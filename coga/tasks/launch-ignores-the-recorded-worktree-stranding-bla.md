---
slug: launch-ignores-the-recorded-worktree-stranding-bla
title: Launch ignores the recorded worktree, stranding blackboard writes
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - dev/code
skills: []
workflow: code/design-then-implement
secrets: null
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
  `v2/use-worktree-when-starting-a-dev-task` (placement + litter).
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

## Evaluator review

## Verification of the ticket's factual claims

**Wrong — `commands/launch.py:928,1014` (`Path.cwd()`).** Neither line contains `Path.cwd()`. Line 928 is a `typer.secho` for "Agent exited with code {n}"; line 1014 is the `expected_assist_branch=` kwarg inside `_refresh_launch_checkout(...)`. There is exactly **one** `Path.cwd()` in the file, at `src/coga/commands/launch.py:1986`, and it is `usage_cwd` — a value captured purely for `usage_tracking.capture_session(cwd=…)` at line 2092. It has nothing to do with where the agent runs.

The *substance* of the claim survives, but the mechanism is different and should be cited differently: `spawn_agent_session` calls `run_with_done_marker(cmd, env, …)` at `src/coga/commands/launch.py:2052`, and `run_with_done_marker` (`src/coga/repl_supervisor.py:202`) takes **no `cwd` parameter at all**. There is no `os.chdir` anywhere in `src/coga/`. So the agent inherits the supervisor process's cwd by omission — nobody chooses it. That is a more accurate and more actionable framing than "cwd-determined via `Path.cwd()`", and it tells the implementer exactly where a fix would have to go (a new `cwd=` through `run_with_done_marker`, i.e. a signature change on shared infra, not a one-line edit in `launch`).

**Wrong — "`grep worktree commands/launch.py` returns nothing."** It returns 10 hits. Most importantly, `launch` *already reads the `worktree:` line*: `_recorded_single_checkout_assist_branch` at `src/coga/commands/launch.py:1555-1586` calls `parse_worktree_path`, and requires that `same_git_checkout(cfg.repo_root, worktree)` — i.e. that the checkout running `coga launch` **is** the recorded worktree — before it will authorize the single-checkout PR assist. This is not a footnote; it is directly load-bearing prior art for option (a), and a cold implementer who trusts the grep claim will "discover" it late and have to redesign. The correct claim is narrower: *launch reads `worktree:` to authorize the assist path, but never uses it to place the child process.*

**Slightly off — `open_pr.py:315`.** Line 315 is the **`branch:`** error string ("No usable `branch:` recorded…"), which matches the Description's quoted symptom but not the Context bullet's label ("Read side is `worktree:`-determined"). The `worktree:` read is at `src/coga/open_pr.py:321`, with its error at 324. Cite 321 for the worktree read and 315 for the observed failure.

**Wrong — "the same line is read by `autoclose.py`, `branchsweep.py`, `branchcleanup.py`."** `autoclose.py:101` *defines* `parse_worktree_path` and exports it; it never consumes the line itself. `branchsweep.py` does not import it at all — it enumerates live worktrees from Git (`_worktree_branches`), not from the blackboard. The actual consumers are `src/coga/branchcleanup.py:133`, `src/coga/open_pr.py:321` and `:589`, `src/coga/commands/retire.py:280`, and `src/coga/commands/launch.py:1573`. Worth fixing, because the accurate list (retire + open-pr + branch-cleanup + launch's assist gate) is the actual blast radius of any change to what `worktree:` means.

**Correct — `git.py:sync_task_state`.** Exists at `src/coga/git.py:382`, and its docstring (lines 403-412) says what the ticket says: on a feature branch it commits the task dir on that branch, *then* lands the same files on the control branch via the working-tree-free plumbing path.

But this makes the ticket's design option (c) misleading. `sync_task_state` **already** fires unconditionally in that sense — there is no gate to remove. The real gap is different: `coga bump` (`src/coga/bump.py:130`) syncs `ref.path`, the ticket dir **of the checkout it was run from**. If the agent writes `## Dev` inside the worktree copy and then obeys the skill's "return to the primary checkout" before bumping, bump faithfully syncs a `ticket.md` that never saw the write. Option (c) as phrased asks for something that exists; rewrite it as "make the *write* and the *sync* agree on one checkout" or drop it.

**Correct** — `coga/skills/code/implement/SKILL.md:68` is "4. **Implement in the worktree.**", and `:34` is the `worktree: <path>` recording line. **Correct** — no `worktree` reference anywhere in `validate.py` or `bump.py`. **Correct** — both adjacent v2 tickets exist at the cited slugs.

## Assessment

**1. Clear enough to start?** Mostly yes — the symptom, the failing command, and the four candidate fixes are legible cold. Two things will mislead a cold implementer, though. First, the citation errors above (especially the grep claim) will send them to the wrong lines and hide existing worktree handling. Second, the Description's causal story overstates the conflict: it says the skill "tells that agent to change into the feature worktree" as if that contradicts the control-plane split, but `code/implement/SKILL.md:32` already says "Then return to the primary checkout and write … `branch:` … `worktree:`", and step 9 (`:88`) says "Return to the primary checkout and run `coga bump`". Followed literally, the skill does **not** strand anything. So this is an *enforcement/compliance* bug — nothing verifies the agent came back — not a contradiction between launch and the skill. That distinction changes which of the four options is even coherent, so it belongs in the Description rather than being left for the design step to rediscover.

**2. Workflow fit.** `code/design-then-implement` is the right pick: the fix is genuinely undetermined, the options have real trade-offs, and there's a human review gate between design and implement. No mismatch. Note the workflow's own `## open-pr` section states the PR step "runs `coga open-pr <slug>` from the checkout that owns the live ticket … the primary control checkout" — which is an argument the design step needs (see 6 below).

**3. Attached context.** `dev/code` is the right and arguably the only necessary attachment — it is the contract being violated, and it documents the four other consumers of `worktree:` that any fix must not break (retire's removal semantics, branch-sweep's pinning). The `coga/codebase` pointer-not-attachment call is right. One real gap: nothing points at the **`coga/sync`** context (`src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`), which documents `sync_task_state`'s contract at length (lines 345, 434, 499, 550). Since three of the four design options turn on sync semantics, that should at least be a pointer bullet alongside the `coga/codebase` one.

**4. Prompt budget / should the fact have been copied instead?** No layer exceeds 40%: `dev/code` is 8.3 KiB of 21.3 KiB ≈ **39%**, just under the line, and `base_prompt` is 34%. I would not trim `dev/code` here even though it's the biggest layer. Normally the argument for copying a fact in is that only one paragraph of the context matters; that isn't true on this ticket. The fix could change what `worktree:` means, and `dev/code` is where the *retire* semantics (§"Who retires the checkout"), the sandbox fallback-clone case, and the `## Dev` line grammar are specified — all three constrain the design. Keeping it attached is the right call; the `## Context` bullet that paraphrases the checkout boundary is then slightly redundant and could be cut to one clause to buy back a few hundred bytes.

**5. Scope.** The *ticket* is one bug. The *option set* is not one ticket's worth of work: (a) threads a `cwd` through shared spawn infra and interacts with the assist path and with `v2/reintroduce-per-launch-worktree-isolation`; (d) is a guard in `bump`/`validate` and is maybe an afternoon. The ticket says "say what each gives up, don't just pick" — good — but it should also say explicitly that the design step must converge on **one** fix and spin the rest out as follow-up tickets, or the implement step will be handed a menu. Add that as an out-of-scope line.

**6. Assumptions to question before launch.**

- **That `launch` is the right layer at all.** Option (a) — spawn the agent in `worktree:` — inverts the `dev/code` contract for *every* step, not just `implement`. If the agent starts in the worktree, then `ticket.md`, `coga/log.md`, `coga bump`, `coga slack`, and `coga block` all default to the feature checkout, which is precisely what the contract forbids; and the `open-pr` step's own workflow text requires the control checkout. Option (a) fixes implement by breaking open-pr. The ticket presents (a) first and neutrally; it should carry that objection, because it's the strongest thing known about the option.
- **That the single-checkout assist layout doesn't collide.** `launch.py:469-530` and `1555` describe a deliberate supported layout where the primary checkout *is* the recorded worktree and launch publishes to the PR branch. Any fix has to leave that path intact. The ticket doesn't mention it exists.
- **The evidence isn't inspectable.** "Observed twice on one task (`FastJVM/admin`, `accounting/xero-reconcile`, 2026-08-08)" reads as self-contradictory (twice on one task, but two workspaces named), and "PR #90" is not a PR in this repo. A cold implementer cannot check any of it. Either name the repo/workspace for each occurrence or state plainly that the evidence lives outside this repo and the reproduction has to be constructed locally.
- **No reproduction is specified.** Given that the skill, read literally, does not produce the bug, the design step should be asked to first *reproduce or precisely characterize* the deviation (which write landed in which checkout) before choosing among fixes. Right now the ticket asks for a fix selection on an unconfirmed mechanism.
- **The self-referential warning is good and should stay** — the chicken-and-egg bullet is the most useful thing in `## Context`. Consider strengthening it to a concrete instruction: write `## Dev` from the primary checkout only, and confirm `git show <control>:coga/tasks/<slug>.md` contains the `branch:` line before bumping into `open-pr`.
