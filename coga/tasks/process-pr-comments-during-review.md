---
slug: process-pr-comments-during-review
title: process pr comments during review
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

When a `code/*` workflow reaches its human-owned `review` step, the ticket is
parked and there is no way to hand work back to an agent: `coga bump` has
rewritten `assignee:` to the human owner, and `coga launch <slug>` is hard-
refused as a human handoff. The owner reviews by leaving comments on the GitHub
PR, so those comments currently have to be re-typed into a new ticket or applied
by hand.

Make it possible, on demand, to relaunch an agent on an already-open PR so it
reads the unresolved review comments, applies the fixes, pushes to the PR
branch, and replies on each thread — leaving the merge decision with the human.

Two parts:

1. **Relax the human-handoff launch gate** so an explicit `--agent <type>`
   override launches an agent on a human-owned step. The override is ephemeral:
   `assignee:` on disk is unchanged.
2. **Add a `code/address-pr-comments` skill**, and deliver it to the `review`
   step of all three `code/*` workflows both as a step `skills:` ref (for new
   tickets) and via the live-composed inline `## review` prose (for tickets
   already parked at `review`).

### Acceptance

- `coga launch <slug> --agent claude` starts an agent on a `review`-step ticket;
  without `--agent` it is still refused exactly as today.
- After that session, `assignee:` on disk still reads the human owner.
- A ticket **already** parked at `review` before this change picks up the new
  instructions on its next assist launch.
- `python -m pytest` green, including the inverted gate test named below.

## Context

### Shape of the feature (decided with the owner during authoring)

- **Trigger is on demand.** The owner runs `coga launch <slug> --agent claude`
  once they have finished commenting. No new workflow step (comments usually
  arrive *after* a step would have run) and no recurring sweep that polls PRs
  and launches by itself.
- **Authority of the assisting agent:** apply the must-fix comments on the
  recorded branch, run `python -m pytest`, commit and push to the PR branch, and
  reply to each thread saying what it did. It must **not** merge, **not** resolve
  GitHub threads, and **not** advance the ticket.
- **The skill must not bump.** `review` is the final step of all three `code/*`
  workflows, so the ticket stays in `review` and the existing `autoclose-merged`
  sweep marks it `done` after the human merges (`autoclose.py:223-234` requires
  `status in {active, in_progress}` *and* the final step, so this is sound). This
  is an explicit exception to the base prompt's "always end a step with
  `coga bump`" rule — say so in the skill, or an agent will bump or
  `coga mark done` out of habit.
- **Session termination.** The assist launch is attended by definition — the
  human just typed the command. The session ends when they end it; do **not**
  reach for `coga slack` as a terminator, because it emits the done marker only
  for bootstrap refs (`src/coga/commands/slack.py:74-75`) and is explicitly
  non-terminal for ordinary tasks. A useful free property to keep as an
  acceptance check: because the assist changes neither step nor status,
  `_harness_stop_reason` returns "still on …; stopping" (`launch.py:1173-1174`),
  so the supervisor will not loop.

### Part 1 — the launch gate

`_refuse_human_handoff_launch` (`src/coga/commands/launch.py:1232`) bails
whenever `assignee:` is not in `cfg.agents`. It is called twice — `launch.py:257`
(before activation) and `launch.py:276` (after). `agent_override` is passed in but
only interpolated into the *error message*; it does not open the gate. Separately,
`_read` (`launch.py:174-179`) applies the override to `frontmatter["assignee"]`
only when the target `is_bootstrap`, so a real task never picks it up. Once the
gate lets the launch through, `launch_assignee = agent_override or assignee`
(`launch.py:286`, mirrored in the chain loop at `launch.py:401-403` for the first
step only) already resolves the agent type correctly.

Required properties of the change:

- The override must be **explicit** — never inferred, never defaulted. Without
  `--agent`, a human-owned step is still refused exactly as today.
- The override must be **ephemeral**. `_read` mutates an in-memory `Ticket`;
  make sure that mutation cannot reach disk. After the session, `assignee:` must
  still read the human owner.
- The launch banner must say it is assisting on a human-owned step, so the
  unusual launch is visible in the transcript.

**An existing test asserts the current behaviour and must be inverted, not
worked around.** `test_launch_agent_override_does_not_bypass_human_handoff`
(`tests/test_launch.py:2826-2850`) asserts exit code 2 and
`Cannot launch fix-retry-logic with --agent 'codex'`. Its *name* encodes today's
refusal as a deliberate invariant — this ticket is the decision to change that
invariant, so rewrite the test rather than treating the red as a signal to stop.
Add coverage for: permitted with an explicit `--agent`, still refused without
one, and `assignee:` unchanged on disk afterwards.

**Known wrinkle, decide during implement:** in-session commands re-read
`assignee:` from disk, so `coga slack` derives its audit actor as
`f"agent:{ticket.assignee}"` (`src/coga/commands/slack.py:56`) and an assisting
agent's FYI lands in `coga/log.md` as `agent:<human>`. That is a direct
consequence of the ephemerality requirement. Either thread the effective launch
agent through, or accept it knowingly — don't discover it in production.

**`megalaunch` is deliberately untouched.** It enforces its own independent human
gate (`megalaunch.py:836-841`, `skipped-human-gate`), which this change does not
relax — a sweep grabbing human-owned steps would be bad. But its docstring
(`megalaunch.py:162-168`) claims `--agent` has "the same semantics as
`coga launch --agent`", which becomes false. Fix that docstring in this PR.

**Tradeoff, accepted deliberately by the owner:** this relaxation is *global* —
any human-owned step on any workflow becomes agent-launchable with an explicit
`--agent`. The narrower alternative (a per-step `agent_assist: true` opt-in in the
workflow) was considered and rejected in favour of the smaller diff. The three
properties above are the mitigations; keep them.

### Part 2 — the skill and the workflow wiring

**The frozen-snapshot problem, and why delivery is two-pronged.** A ticket's
`steps:` come from the workflow snapshot frozen into its own frontmatter
(`ticket.py:213-221`), and freezing happens once — at create (`create.py:189`) or
at activation (`mark.py:365-382`). Editing a workflow template's `steps:` therefore
does **nothing** for a ticket already parked at `review`, which is the motivating
scenario. Inline step prose is different: `compose.py:360-365` loads the workflow
file **live** from disk every launch. So:

- Write the canonical skill at `coga/skills/code/address-pr-comments/SKILL.md`
  and wire it as `skills:` on the `review` step of the three `code/*` workflows —
  this serves tickets created after the change.
- **Also** extend each workflow's inline `## review` prose with a short version
  plus the must-not-merge / must-not-advance language, so tickets already parked
  at `review` pick it up on their next assist launch.

(This ticket's own frozen snapshot above shows the problem concretely: its
`review` step reads `skills: []` and will keep reading that after the change
lands. The inline prose is the only path that reaches it.)

**Adding `skills:` silently replaces the inline prose for new tickets.**
`_step_layers` returns early once `skill_refs` is non-empty (`compose.py:346-359`)
and never reaches the inline fallback. So the skill must carry the "must not
merge / must not advance" language itself; it cannot defer to the workflow prose
that today lives at `code/with-review.md:111-116` (the same paragraph appears in
`with-self-review.md` and `design-then-implement.md`). Treat that paragraph as the
authority for what the skill may do, and keep both copies saying the same thing.

**The skill needs two copies.** Unlike the `code/*` workflows — which are bundled
batteries with no repo-local `coga/workflows/code/` — the `code/*` *skills* are
byte-identical pairs: `coga/skills/code/{design,implement,open-pr,self-qa}` and
`src/coga/resources/templates/coga/bootstrap/skills/code/*`. Since the ref is
being wired into the **packaged** workflow templates, a bootstrapped repo without
the packaged skill copy would raise `ComposeError` from `_missing_skill_message`
(`compose.py:348-349`), and `coga validate` flags it too (`validate.py:1048`).
Ship both copies.

**Reading comments:** `gh` is already a hard dependency (`src/coga/open_pr.py`,
`src/coga/autoclose.py`). Unresolved review threads need `gh api graphql` —
`gh pr view --comments` returns issue comments and misses per-line thread
resolution state. The PR URL is on the ticket as `pr:` under `## Dev` (see the
attached `dev/code` context); the branch is `branch:` in the same block.

**Microkernel rule (CLAUDE.md).** Part 1 edits shared launch machinery, which is
fine. Part 2 is markdown only. The `gh api graphql` invocation belongs **in the
skill text**, not in a new `src/coga/` helper module — a single-consumer GraphQL
helper in core is exactly what the rule forbids.

### Out of scope

- Automatic/recurring triggering (a sweep that polls open PRs and launches on its
  own) — considered and rejected for now.
- A general re-freeze / snapshot-refresh mechanism for edited workflows. It would
  fix this class of problem for every future workflow edit, but it is a second
  feature; the inline-prose path covers this ticket's need. Worth its own ticket.
- Resolving GitHub threads, and merging, both of which stay with the human.
- Any change to the `open-pr` step, `coga open-pr`, or the `requires: pr` gate.
- Relaxing `megalaunch`'s independent human gate.

<!-- coga:blackboard -->

## Evaluator review

## Verified wrong or incomplete

**The skill will not compose for any ticket that already exists.** `current_step()` reads the workflow snapshot frozen into the ticket's own frontmatter (`/home/n/Code/codex/coga/src/coga/ticket.py:213-221`), and freezing happens once — at create (`/home/n/Code/codex/coga/src/coga/create.py:189`) or at activation (`/home/n/Code/codex/coga/src/coga/mark.py:365-382`). Editing the workflow template file changes nothing for a ticket already parked at `review` — which is the entire motivating scenario. The ticket's Part 2 is written as if wiring `skills:` into the three workflow files is sufficient; it is not. This needs an explicit answer (re-freeze path, a documented "edit the frozen `steps:` by hand" fallback, or accept that the feature only applies to tickets created after the change). Note the irony: this ticket's own `code/with-review` run will freeze *before* the edit lands, so it cannot dogfood itself without manual intervention.

**The new skill needs two copies, not one.** The ticket says the skill goes at `coga/skills/code/address-pr-comments/SKILL.md` and explicitly waves off sync ("there is no repo-local `coga/workflows/code/` copy to keep in sync"). That claim is true *for workflows* and false *for skills*: `coga/skills/code/{design,implement,open-pr,self-qa}` and `src/coga/resources/templates/coga/bootstrap/skills/code/*` are byte-identical pairs (verified with `diff -q`). Since the ref is being wired into the **packaged** workflow templates, a bootstrapped repo with no local copy would hit `ComposeError` from `_missing_skill_message` at `/home/n/Code/codex/coga/src/coga/compose.py:348-349`, and `coga validate` flags it too (`/home/n/Code/codex/coga/src/coga/validate.py:1048`). Add the packaged copy.

**An existing test asserts the opposite of Part 1 and the ticket doesn't say to change it.** `test_launch_agent_override_does_not_bypass_human_handoff` at `/home/n/Code/codex/coga/tests/test_launch.py:2826-2850` asserts exit code 2 and the message `Cannot launch fix-retry-logic with --agent 'codex'`. Its name encodes the current behaviour as a deliberate decision. The ticket lists tests to *add* but never says this one must be inverted or deleted; an agent will hit a red test whose name reads like a design invariant and may reasonably stop. Say so explicitly.

**`coga slack` will not end the session.** The ticket prescribes `coga slack --task <id> --message "<one line>"` as the report-back in place of `coga bump`. But `coga slack` emits the done marker only for bootstrap refs — `/home/n/Code/codex/coga/src/coga/commands/slack.py:74-75`, with the comment "Ordinary task FYIs remain non-terminal; their workflow still ends through bump/mark/block." So a supervised assist session that deliberately never bumps has no clean terminator and will sit until `/exit` or the idle timeout. The skill needs an explicit exit instruction, or the plan needs a real terminator.

**Adding `skills:` silently *replaces* the inline `## review` prose.** `_step_layers` returns early on `skill_refs` (`/home/n/Code/codex/coga/src/coga/compose.py:346-359`) and never reaches the inline-section fallback. The ticket treats `with-review.md:112-116` as "the authority" the skill should honour, but once `skills:` exists on that step, that prose stops composing entirely. The skill must carry the "must not merge / must not advance" language itself, not defer to it. (Minor: the cited range is actually 111-116, and all three workflows carry the same paragraph — `with-self-review.md` and `design-then-implement.md` too.)

**megalaunch's documented parity claim becomes false.** `/home/n/Code/codex/coga/src/coga/megalaunch.py:162-168` states that `--agent` has "the same semantics as `coga launch --agent`: … a human-assigned ticket is not converted into an agent step (still a human gate)". megalaunch enforces that with its own independent gate at `megalaunch.py:836-841` (`skipped-human-gate`), which the ticket's change does not touch. That's probably the right outcome — a sweep grabbing human-owned steps would be bad — but the divergence is now undocumented and that docstring is wrong. The ticket doesn't mention megalaunch at all.

**Audit-trail wrinkle from ephemerality.** In-session commands re-read `assignee:` from disk. `coga slack` derives its log actor as `f"agent:{ticket.assignee}"` (`/home/n/Code/codex/coga/src/coga/commands/slack.py:56`), so the assisting agent's report lands in `coga/log.md` as `agent:nick`. Deliberate ephemerality buys this; worth an explicit decision rather than a surprise.

## Claims that check out

`_refuse_human_handoff_launch` is at `launch.py:1232` and bails when `assignee not in cfg.agents`; called at `launch.py:257` and `:276`; `agent_override` reaches it only for the error string. `_read` at `launch.py:174-179` gates the override on `is_bootstrap`. `launch_assignee = agent_override or assignee` at `launch.py:286`, mirrored in the chain loop at `launch.py:401-403` (first step only). `coga bump` does rewrite `assignee:` to the resolved `owner` (`/home/n/Code/codex/coga/src/coga/bump.py:50-71`, `:105-108`). `compose.py:344` reads step `skills:` with no regard to step `assignee:`. `review` is genuinely the final step in all three `code/*` workflows, and `autoclose._candidate` requires `status in {active, in_progress}` and final step (`/home/n/Code/codex/coga/src/coga/autoclose.py:223-234`) — so "don't bump, let autoclose finish it" is sound. There is no repo-local `coga/workflows/code/`. `gh` is a hard dep in `open_pr.py` and `autoclose.py`. `coga slack --task/--message` exists.

One nice property the ticket doesn't claim but gets for free: after an assist session that changes neither step nor status, `_harness_stop_reason` returns "still on …; stopping" (`launch.py:1173-1174`), so the supervisor won't loop. Worth recording as an acceptance check.

## Description clarity, workflow fit, scope

The Description is unusually good — a cold agent can start from it. Two snags. The **slug and title are actively misleading**: `allow-comments-on-the-pr-while-open-pr-steps` reads as work on the `open-pr` step, which the ticket then lists as out of scope. Rename before launch. And the Description names the deliverables but no acceptance criteria; the `## Context` has them scattered in prose.

`code/with-review` fits: two-file-ish Python change plus a new markdown asset, real peer-review value on the gate relaxation, and it ends at a human PR review. No mismatch.

Scope is at the upper edge of one ticket but defensible — Part 1 is small and Part 2 is a single markdown file plus three one-line workflow edits. The parts are genuinely coupled (Part 2 is unreachable without Part 1). Splitting would create a ticket that can't be demonstrated. Keep it together, but the frozen-workflow and packaged-skill items above add real work that isn't currently costed.

## Contexts

`dev/code` is the right context and the only one needed for the `## Dev` / `branch:` / `pr:` fact. But it is the largest single layer at 7.2 KiB, and roughly half of it (the `coga retire` cleanup rules, branch-sweep interaction, multi-ticket PRs) is irrelevant here. The ticket's `## Context` already restates the one fact it needs ("The PR URL is on the ticket as `pr:` under `## Dev` … the branch is `branch:` in the same block") — so the attachment is arguably redundant. That said, the assisting skill this ticket *creates* will need the `## Dev` convention at runtime, so keeping the context attached is defensible.

What's **missing** is a context or `## Context` note pointing at the microkernel rule in CLAUDE.md. Part 1 touches `src/coga/commands/launch.py`, which is fine (shared launch machinery, existing command), and Part 2 is pure markdown — so there's no violation — but an agent tempted to add a helper module for GraphQL comment-fetching would be creating exactly the single-consumer core code the rule forbids. State that the `gh api graphql` invocation belongs *in the skill text*, not in a new `src/coga/` module.

## Prompt size — proportional read

Nothing crosses the 40% line, so no layer is a mandated trim. Shares of the 22.3 KiB total: `ticket_context` (dev/code) 32.7%, `base_prompt` 31.8%, `task_context` 19.7%, `mode_prompt` 9.0%, everything else under 5%. This is a healthy distribution.

One caveat on the numbers themselves: the breakdown has **no `workflow_skill` layer**, because the ticket is still an unfrozen draft (`current_step()` returns `None` for a bare-string `workflow:`). At real launch, step 1 pulls in `code/implement` (7.1 KiB, ~1.8k tokens), taking the actual first-step prompt to roughly 29.4 KiB / ~7.5k tokens and dropping `dev/code` to about 25%. Still fine. `code/open-pr` at step 3 is heavier (8.9 KiB) but that step composes without `dev/code`-scale duplication. No trim needed.
