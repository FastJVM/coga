---
slug: fix-automatically-pr-conflict-and-a-command-to-bat
title: fix automatically PR conflict and a command to batch fix them
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/codebase
- coga/principles
- dev/code
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

Ship a launchable command that resolves conflicts across the repo's open
PRs in one pass, and land the launch-side arg channel that lets it target a
single PR.

The command is authored as a **command ticket** under `coga/bootstrap/`
(the seam the `commands-as-tickets-open-pr-pilot` pilot landed — **merged to
main as PR #625, commit `9965e95e`**: local-first
`coga/bootstrap/<name>/ticket.md` resolution + `[aliases]`), so a ticket plus
one alias line mints a new `coga` verb with zero core-Python change. It is
launched in place each time, not instantiated per run.

Behavior:

- `coga resolve-conflicts` — enumerate every open PR (`gh pr list --state
  open`), and for each one that is conflicted against `main`, rebase it,
  resolve the conflicts with **full agent judgment** (read both sides,
  understand intent, re-apply the branch's change on top of main's), verify
  with `python -m pytest` when the diff touches `src/` or `tests/`, and
  `git push --force-with-lease`. This is deliberately more aggressive than
  the mechanical-only posture below it — the agent may resolve semantic
  conflicts, so verification before push is the safety net.
- `coga resolve-conflicts <PR>` — scope to a single PR. This requires the
  **arg channel for agent launches** (see below), which does not exist yet.

Because full agent judgment needs an agent (not a script), the command is an
**agent** launch. Today `coga launch` fails loud when an agent launch is
given trailing args (`launch_script.py` writes `COGA_ARG_1..N` for *script*
launches only; #625 explicitly deferred composing args into agent prompts
"until a second use case exists"). **This ticket is that second use case:**
extend `launch` to compose trailing args into the agent prompt so
`coga resolve-conflicts 631` works. This agent-prompt composition is the one
genuinely unbuilt piece — the bootstrap resolution and the script arg
channel are already live on main.

This **supersedes** the `rebase-stale-worktrees` recurring task. That task
already walks live branches and rebases them mechanically; the new command
is the PR-scoped, judgment-capable successor. Delete
`coga/recurring/rebase-stale-worktrees/` and move its weekly cron intent
onto the new command (a scheduled `coga resolve-conflicts` if a schedule is
still wanted — confirm with owner at review).

The per-run summary goes to **stdout + Slack** (one line per PR, then a
`coga slack` roll-up). Nothing durable is written to disk — this fits the
stateless command-ticket model and avoids the new command writing other
tickets' files.

## Acceptance Criteria

- [ ] `coga/bootstrap/resolve-conflicts/ticket.md` exists as a stateless
  command ticket (no `status`/`workflow`; body documents the verb) and
  `coga resolve-conflicts` runs it via a default alias
  (`launch bootstrap/resolve-conflicts`).
- [ ] Running it with no args sweeps all open PRs: for each conflicted-vs-main
  PR it rebases, resolves conflicts with agent judgment, runs `pytest` when
  the diff touches `src/`/`tests/`, and `git push --force-with-lease`. A PR
  it cannot safely resolve is reported, never force-pushed.
- [ ] Verification gates the push: a rebase whose `pytest` fails is left
  unpushed and reported `verify-failed`, matching `rebase-stale-worktrees`'
  posture.
- [ ] `coga launch <agent-target> <ARG...>` composes trailing args into the
  agent prompt (the deferred half of the `commands-as-tickets` arg channel);
  `coga resolve-conflicts 631` scopes the run to PR 631. The `COGA_*` env
  reservation and the existing script-launch `COGA_ARG_*` behavior are
  untouched.
- [ ] Per-run summary prints one line per PR to stdout and posts a one-line
  roll-up via `coga slack`; nothing is written to any ticket blackboard.
- [ ] `coga/recurring/rebase-stale-worktrees/` is deleted and any reference
  to it (docs, cron config) is updated or removed.
- [ ] Live + packaged copies stay in sync where touched (the arg-channel docs
  in `coga/architecture`, `coga/codebase`, and `docs/reference.md`; the new
  command ticket under both `coga/bootstrap/` and, if it should ship as a
  battery, `src/coga/resources/templates/coga/bootstrap/`).
- [ ] `python -m pytest` green; `coga validate` clean.

## Context

**Reuse the pilot's seam — don't rebuild it.** `commands-as-tickets-open-pr-pilot`
(**merged, PR #625, commit `9965e95e`**) landed: local-first
`coga/bootstrap/<name>/ticket.md` resolution (over the package resource), the
`COGA_ARG_1..N` + `COGA_ARGC` env channel for **script** launches, and
`open-pr` as the first shipped command ticket + default alias. All of this is
on `main` now — no coordination or waiting needed. Read that ticket's
blackboard and PR before starting — it is the template for authoring
`resolve-conflicts` and it documents exactly where the agent-arg channel was
deferred (`launch()` in `src/coga/commands/launch.py`; the script channel
lives in `src/coga/commands/launch_script.py`, and agent launch with trailing
args currently fails loud *before* the TTY gate). The only unbuilt piece this
ticket needs from that seam is composing args into the **agent** prompt.

**Sequence the work: seam → command → deletion.** The three deliverables are
separable and should land as distinct commits in that order: (1) the core
`launch` change that composes trailing args into an agent prompt, with its own
tests; (2) the `resolve-conflicts` command ticket that consumes it; (3)
deleting `rebase-stale-worktrees` and settling its cron. Deliverable (1) is a
generic kernel seam every future agent-arg use case inherits — treat it as the
load-bearing part, not an afterthought of the command.

**Supersession is NOT a strict superset — decide the coverage gap before
deleting.** `rebase-stale-worktrees` enumerates from **live branches**
(worktrees + `branch:` under non-terminal tickets). The new command
enumerates from **open PRs** (`gh pr list`). A stale in-flight branch with
**no PR yet** (a ticket still before its `open-pr` step) is swept by the old
task but invisible to the new one. Before deleting, either (a) have
`resolve-conflicts` also enumerate live pre-PR branches, or (b) explicitly
accept and document that pre-PR branches are no longer auto-rebased. This is
an owner decision flagged for the review step — see Open Questions.

**The behavior already half-exists.** `coga/recurring/rebase-stale-worktrees/ticket.md`
enumerates live branches (worktrees + `branch:` under non-terminal tickets),
`git fetch`es, tests staleness with `git merge-base --is-ancestor`, rebases
onto `origin/main`, resolves *trivial mechanical* conflicts only, verifies
(pytest when `src/`/`tests/` touched), and `git push --force-with-lease` for
branches with an upstream. Lift its run-order and its report vocabulary
(`rebased-pushed`, `up-to-date`, `conflict`, `skipped-dirty`,
`verify-failed`) into the new command — the two differences are: (a) the new
command enumerates from **open PRs** (`gh pr list`) not from live branches,
and (b) it may resolve **semantic** conflicts with agent judgment, not just
mechanical ones. Then delete `rebase-stale-worktrees`.

**Safety posture.** Force-pushing a PR branch is outward-facing and hard to
reverse. The chosen posture is full agent judgment *with* mandatory
verification before push and explicit per-PR reporting; a PR the agent
can't confidently resolve is aborted (`git rebase --abort`, worktree left as
found) and reported for a human, never force-pushed. There is no dry-run
flag in this scope — the verification gate and abort-on-doubt rule are the
safety net. (`--dry-run` was considered and set aside; revisit if the sweep
proves too eager in practice.)

**Workflow note.** Runs `code/with-review` (implement → peer-review →
open-pr → review). This ticket deletes a recurring task and changes core
`launch`; the owner chose to see the approach at PR time rather than gate a
separate design step. The peer-review step is the last judgment gate before
the PR.

## Out of Scope

- A `--dry-run` / plan-only mode (deferred; abort-on-doubt + verify-before-push
  is the safety mechanism instead).
- Writing conflict-resolution outcomes onto originating tickets' blackboards
  (rejected — the command stays stateless; summary is stdout + Slack only).
- Keeping `rebase-stale-worktrees` alongside the new command (rejected — the
  new command supersedes it; two things force-pushing the same branch is the
  hazard being removed).
- Composing trailing args into *script* prompts (already shipped by #625) —
  this ticket adds only the **agent**-launch arg composition.
- Re-litigating the `commands-as-tickets` seam (local-first resolution, the
  alias mechanism, the `requires: pr` gate) — reuse it as-is.

<!-- coga:blackboard -->

## Open Questions (for owner at review)

1. **Coverage gap on delete.** New command sweeps open PRs; old task swept
   live branches incl. pre-PR ones. Have `resolve-conflicts` also enumerate
   live pre-PR branches, or accept that pre-PR branches are no longer
   auto-rebased? (Evaluator #6.)
2. **Sweep default.** No-arg `coga resolve-conflicts` resolves *semantic*
   conflicts and force-pushes across *all* open PRs (~20 live branches at last
   count). Should the default be single-PR (opt-in `--all` sweep) rather than
   sweep-by-default? Verify-before-push + abort-on-doubt is the safety net
   either way. (Evaluator #6.)
3. **Cron fate.** `rebase-stale-worktrees` runs `0 8 * * 1`. On delete, does
   the weekly schedule transfer to a scheduled `coga resolve-conflicts` or get
   dropped? Decide before deletion so there's no coverage window with neither.
4. **Workflow.** `code/with-review` has no design gate; this is the riskiest
   ticket in the series (kernel seam + mass force-push + deleting a scheduled
   task). Keep with-review, or switch to `code/design-then-implement` to lock
   the safety posture before it's coded? (Owner already leaned with-review;
   re-confirm.)

## Evaluator review

**1. Description clarity — mostly yes, with one stale fact that will mislead**

- A cold agent can start: the Description states the two deliverables, the Behavior bullets are concrete (`gh pr list`, force-with-lease, verify gate), and ## Context points at the pilot as the authoring template. Good.
- But it repeatedly says the pilot is "in review" / "PR #625, in review" and "the arg channel... does not exist yet" / "coordinate if #625 has not merged." **This is already stale.** #625 merged to main (commit `9965e95e`), and the seams are live: `launch.py` already has the variadic `args`, `COGA_ARG_1..N`+`COGA_ARGC`, and the agent-launch fail-loud (launch.py:322-331); `resolve_bootstrap`/`bootstrap_resolution_paths` are on main. A picking-up agent reading "coordinate if not merged" may wait or hunt for an unmerged branch that no longer matters. Fix the tense: the prerequisite is satisfied; the only thing genuinely missing is the deferred *agent-prompt* arg composition.

**2. Workflow fit — the one real mismatch: no design gate for the riskiest ticket in the series**

- `code/with-review` is implement → peer-review → open-pr → review. Its only judgment gate (peer-review) fires *after* the code is written.
- The pilot this builds on used `code/design-then-implement` (design → review-design → …) for arguably lower-stakes work. This successor is riskier: it (a) changes a core kernel seam (`launch` agent-arg composition), (b) authors a command that force-pushes to **every open PR** with **semantic** conflict resolution, and (c) deletes a scheduled recurring task. That is exactly the shape that benefits from a design gate to lock the safety posture and the supersession decision *before* implementation.
- The Workflow note acknowledges the owner deliberately chose to see the approach at PR time. That's a legitimate owner call, but flag it: with-review means the delete-vs-supersede gap (see #6) and the arg-channel semantics get their first human look only at the PR, when they're already coded.

**3. Contexts — relevant, one notable omission**

- `coga/architecture`, `coga/codebase`, `dev/code` are all on-point for a kernel `launch` edit plus command-ticket authoring.
- Missing: **`coga/principles`**. The pilot attached it, and this ticket touches the microkernel/stateless-command-ticket model and the correction loop (force-pushing outward, statelessness) — the non-negotiables are directly in play. Worth adding (it's ~2.7k tokens, far cheaper than architecture).
- Nothing else critical missing; the Slack roll-up is covered by the existing `coga slack` command (confirmed present).

**4. Context size — drop `coga/architecture`; it is not justified here**

- Confirmed: architecture is 40,980 bytes (~10.2k tok, 55% of the prompt), paid on every step of a 4-step workflow. codebase is 13,424 bytes.
- This ticket needs exactly two facts from architecture: local-first `coga/bootstrap/<name>/ticket.md` resolution, and the `launch` arg-channel seam. **Both are already restated in this ticket's ## Context** and in the pilot's Proposed Shape. The full context adds ~9.5k tokens of primitives/planes/locking that this work doesn't touch.
- The one apparent reason to keep it — "update the arg-channel docs in `coga/architecture`" — does **not** require composing it into the prompt. The agent Reads/Edits that file directly when it reaches the docs step; a composed context is for *reasoning input*, not for *files you'll edit*.
- **Recommendation: drop `coga/architecture` from `contexts:`.** Keep the two load-bearing sentences in ## Context. Keep `coga/codebase` and add `coga/principles`. Net prompt roughly halves.

**5. Scope — it bundles genuinely separable work; call it two-PRs-worth**

- Three distinct deliverables: (a) author the `resolve-conflicts` command ticket, (b) a **core kernel change** to compose trailing args into agent prompts, (c) delete `rebase-stale-worktrees` + migrate its cron intent.
- (b) is not command-authoring — it's a shared `launch` seam that every future agent-arg use case inherits, and it's the hard prerequisite for `resolve-conflicts <PR>`. It deserves its own commit at minimum, arguably its own ticket. The "second use case" framing is why they're coupled, so keeping them together is defensible — but the ticket should sequence it explicitly: **seam first (kernel + tests), then the command that consumes it, then the deletion.** As written the acceptance criteria interleave them.

**6. Assumptions to question before launch**

- **The #625 dependency is real but already satisfied — the ticket says the opposite.** As in #1: correct this or the agent wastes a step. The *genuinely* unbuilt piece is only the agent-prompt composition.
- **Supersession is not a strict superset — deleting `rebase-stale-worktrees` leaves a coverage gap.** Old task enumerates from **live branches** (worktrees + `branch:` under non-terminal tickets); new command enumerates from **open PRs** (`gh pr list`). A stale in-flight branch with **no PR yet** is rebased by the old task but invisible to the new one. Either enumerate both sets, or explicitly accept and document that pre-PR branches are no longer swept. Decide before delete.
- **Blast radius of the sweep.** ~20 live branches, almost all conflicting and several likely superseded. A no-arg `coga resolve-conflicts` that resolves **semantic** conflicts and force-pushes across *all* open PRs at once is large, outward-facing, hard-to-reverse. Consider whether the *default* should be single-PR (opt-in sweep). Worth an explicit owner decision.
- **Cron migration is under-specified.** If the recurring task is deleted in the same PR, the `0 8 * * 1` schedule either transfers to a scheduled `coga resolve-conflicts` or is dropped — decide before deletion so there's no window with neither.
- Minor: verify `coga slack` posts the way the ticket assumes (one-line roll-up).
