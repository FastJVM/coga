---
title: where have code review disappeared?
status: draft
owner: nicktoper
agent: claude
workflow: code/with-review
contexts:
  - coga/launch
---

## Description

The peer code review by the other agent has stopped happening. The owner saw
this under both `coga launch` and `coga megalaunch`. When the implementing
agent runs `coga bump` at the end of `implement`, the agent session just
exits. The supervisor doesn't start the peer agent (claude → codex, or the
reverse) as a fresh process for the `peer-review` step, so the review never
runs. Megalaunch also appears to advance only one step per ticket and not
chain through the workflow's agent steps. Find out why the chain stops, fix
it, and pin it with a regression test.

Second part: audit every workflow (bundled ones under
`src/coga/resources/templates/coga/bootstrap/workflows/`; repo-local
`coga/workflows/` holds no `code/` or `docs/` workflows today, but check it too)
and make sure every code-producing workflow runs its
review with the other agent (`assignee: other-agent`), or document why one
intentionally doesn't.

Done when a `code/with-review` ticket launched with `coga launch` goes from
`implement` → bump → a fresh peer-agent process on `peer-review` → bump → the
main agent on `open-pr`, with no manual relaunch. Megalaunch must chain the
same way, up to its 8-step cap. A test must fail on today's behavior and pass
after the fix. The workflow audit's result must be recorded on the blackboard,
and any workflow changed to use `other-agent` must have its packaged twin and
live copy kept in sync.

## Context

**Expected contract** (from `coga/launch`, attached, section "The step
chain"): after a clean exit, the supervisor rereads the ticket and continues
when the task is still `in_progress`, the step advanced, and the next operator
is an agent. `agent` and `other-agent` rotate CLIs. The observed behavior
breaks this. Megalaunch (`docs/contexts/coga/megalaunch/SKILL.md`, cited not
attached) says a task chains through at most 8 agent steps per run, and an
exit that changes neither step nor status is `failed`.

**Code to start from:**
- `repl_supervisor.run_with_done_marker` and `repl_supervisor._classify_exit`:
  the PTY watcher and done-sentinel release that decide how a session ended.
  Check whether a bump-triggered exit is classified as a clean, progressing
  exit.
- `megalaunch._chain_stop_result`: the decision to stop or continue after an
  agent step. The `coga launch` chain decision is the `while True:` chain
  loop inside `commands.launch._launch` (the block commented "Agent launches
  chain across consecutive agent-owned steps"). Compare the two.
- `bump.resolve_other_agent` / `bump.resolve_main_agent`: turn the step's role
  token into a concrete agent. `coga/coga.toml` defines exactly two agents
  (`claude`, `codex`), so `other-agent` should infer the peer.
- Recent commits that touched this path are good places to bisect:
  `Simplify git sync (#848)`, `Scrub 1Password auth from launched task
  environments (#879)`, `Detect stranded ticket writes across checkouts
  (#850)`, and `Preserve edits during released claim recovery (#842)`. A
  sync change that makes the supervisor reread a stale ticket copy, and so
  see "no progress", would produce exactly this symptom.

**Lead for the audit, found while authoring:** `code/with-self-review` routes
implement → self-qa → pr to `assignee: agent` and the final `review` to
`owner`, so it never involves the other agent by design. The ticket on the current branch
(`run-the-landed-branch-sweep-daily-from-autoclose`) uses it. Some "missing
review" may come from tickets being authored with that workflow, not only from
the chain bug. Decide with the owner whether `with-self-review` should stay as
a deliberate lighter option or gain an `other-agent` step. Also check which
workflow `bootstrap/ticket` steers toward. Current bundled step owners:
`code/with-review` and `docs/with-review` run `peer-review` as other-agent;
`code/design-then-implement` runs only `evaluate-design` as other-agent and
has no code review after `implement`; `code/with-self-review` has no
other-agent step.

**Dogfooding caveat:** this ticket runs on `code/with-review`, the path it is
fixing. Expect to relaunch `peer-review` by hand (`coga launch <slug>`) if the
chain still breaks.

**Twins:** bundled `code/*` and `docs/*` workflows currently have no live
copy under `coga/workflows/`, so there is no twin to sync. If a live copy
exists by the time you edit, keep both byte-identical (`tests/test_packaging.py`). If the chain contract itself changes, update
`docs/contexts/coga/launch/SKILL.md` in the same PR.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

**Clarity.** Yes — an agent with no prior context could start. Symptom, expected contract, and starting code are concrete; the dogfooding caveat is a good touch.

**Done criteria.** The chain half is reviewer-checkable (explicit step sequence, megalaunch 8-step cap, fail-then-pass test). The audit half is softer: "or document why one intentionally doesn't" doesn't say *where* (workflow file? blackboard?), and "Decide with the owner" is an owner gate the `code/with-review` workflow doesn't have before `open-pr`.

**Workflow fit.** `code/with-review` fits the chain fix. The audit's "decide with the owner" has no matching owner step until final review — the agent will either stall or decide unilaterally.

**Contexts.** `coga/launch` is the right attachment ("The step chain" section exists, L86). Citing `coga/megalaunch` is fine — the ticket copies the two facts it needs (8-step cap, no-progress exit = `failed`). Nothing needs attaching instead. `coga/packaging` is missing but the twin rule is adequately summarized. Missing pointer: which topic/skill actually steers ticket authors toward a workflow (`bootstrap/ticket`) — named but not cited by path.

**Scope.** Bundles two tickets. The chain bug is a bounded code fix with a regression test. The workflow audit is a policy decision (whether `with-self-review` stays a lighter option) needing owner input. Recommend splitting the audit into its own ticket blocked on/after this one; that also removes the owner-decision gate from a `with-review` run.

**Citations** (verified): `repl_supervisor.run_with_done_marker` (L228), `_classify_exit` (L652), `megalaunch._chain_stop_result` (L1968), `bump.resolve_main_agent`/`resolve_other_agent` (L90/L147), `max_steps_per_task: int = 8` — all accurate. All four bisect commits (#848, #850, #842, #879) exist. Issues:
- "the `coga launch` chain decision lives in the launch command path" is vague — it's the chain loop in `src/coga/commands/launch.py` (~L1507–1780); name it.
- **Wrong:** ticket says `code/with-self-review` routes "every step to `assignee: agent` (implement → self-qa → pr → review)". `review` is `assignee: owner`. Conclusion (no other-agent step) still holds, but the stated fact is wrong.
- **Misleading:** the audit says check repo-local workflows under `coga/workflows/`, and the Twins note implies `code/*` has live copies. `coga/workflows/` has no `code/` or `docs/` dirs and no `other-agent` step at all; a `code/*` change touches only the packaged copy (no twin pair to sync).

**Assumptions to question before launch.**
- Has the bug actually been reproduced? It could be (a) stale ticket reread (the #848 sync theory), (b) `_classify_exit` misclassifying a bump-exit, or (c) simply tickets authored on `with-self-review` — the lead already hints at (c). First step should confirm with a recent run record under `.coga/` which one it is.
- "Megalaunch advances one step per ticket" may be a separate cause from the launch chain; don't assume one fix covers both.
- If the root cause is config (both CLIs resolve to the same agent), the fix is in `bump`, not the supervisor.

**Prompt size (~4524 tok).** No layer exceeds 40%. Largest: `ticket_context` `coga/launch` 1525 (34%) and `base_prompt` 1500 (33%) — acceptable. `task_context` (743) could shed the full bundled step-owner list if the audit is split out.
