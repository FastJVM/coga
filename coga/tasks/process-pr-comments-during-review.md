---
slug: process-pr-comments-during-review
title: process pr comments during review
status: in_progress
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
2. **Add a `code/address-pr-comments` skill** and wire it as `skills:` on the
   `review` step of all three `code/*` workflows.

Tickets **already** parked at `review` when this lands will not pick it up (their
workflow snapshot is frozen — see Part 2). That is an accepted limitation, not a
gap to solve here: the owner's call is that the in-flight population is small and
short-lived.

### Acceptance

- `coga launch <slug> --agent claude` starts an agent on a `review`-step ticket;
  without `--agent` it is still refused exactly as today.
- After that session, `assignee:` on disk still reads the human owner.
- A ticket created after this change reaches `review` with the skill composing
  into the assist launch's prompt.
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

- Write the skill at `coga/skills/code/address-pr-comments/SKILL.md`, plus the
  packaged copy at
  `src/coga/resources/templates/coga/bootstrap/skills/code/address-pr-comments/SKILL.md`.
  The `code/*` skills are byte-identical pairs today
  (`coga/skills/code/{design,implement,open-pr,self-qa}` vs the packaged tree).
  Shipping only one copy breaks a bootstrapped repo: the ref is wired into the
  **packaged** workflow templates, so a repo without the packaged skill raises
  `ComposeError` from `_missing_skill_message` (`compose.py:348-349`), and
  `coga validate` flags it (`validate.py:1048`).
- Wire `skills: [code/address-pr-comments]` onto the `review` step of
  `code/with-review.md`, `code/with-self-review.md`, and
  `code/design-then-implement.md` under
  `src/coga/resources/templates/coga/bootstrap/workflows/code/`. These are
  bundled-only — there is no repo-local `coga/workflows/code/` — so that is a
  single-copy edit, unlike the skill above.
- `compose.py:344` reads a step's `skills:` regardless of its `assignee:`, so
  attaching a skill to an owner-assigned step composes correctly. It only ever
  reaches an assisting agent, since a human step composes no prompt otherwise —
  which is exactly the intended audience.

**The skill must restate the limits, because wiring it deletes the prose that
carries them today.** `_step_layers` returns early once `skill_refs` is non-empty
(`compose.py:346-359`) and never reaches the inline fallback, so the moment the
`review` step gains a `skills:` entry, the must-not-merge paragraph at
`code/with-review.md:111-116` (identical in the other two workflows) stops
composing. Carry that language — may inspect, may run verification, may push
explicitly requested fixes, **must not merge / resolve / advance** — into the
skill itself. Leave the workflow paragraph in the file for human readers.

**Accepted limitation: already-parked tickets get nothing.** A ticket's `steps:`
come from the snapshot frozen into its own frontmatter (`ticket.py:213-221`) at
create (`create.py:189`) or activation (`mark.py:365-382`), and nothing refreshes
it — `_freeze_workflow_ref` is a documented no-op once `workflow:` is already a
dict. So any ticket sitting at `review` today keeps `skills: []` forever. (This
ticket's own frozen snapshot above is an example.) The owner has accepted this;
do not build a re-freeze mechanism here.

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
- A general re-freeze / snapshot-refresh mechanism for edited workflows, and any
  attempt to reach tickets already parked at `review`. Explicitly declined by the
  owner as a small, short-lived population. (A re-freeze would fix the whole class
  — every workflow `steps:` edit is invisible to in-flight tickets, including
  `assignee:` fixes and added `requires:` gates — but it needs a re-anchor rule
  for `step: N (name)` when steps are inserted, renamed, or removed. Its own
  ticket if it ever earns one.)
- Resolving GitHub threads, and merging, both of which stay with the human.
- Any change to the `open-pr` step, `coga open-pr`, or the `requires: pr` gate.
- Relaxing `megalaunch`'s independent human gate.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
