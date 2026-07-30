---
slug: allow-comments-on-the-pr-while-open-pr-steps
title: allow comments on the PR while open pr steps
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow: code/with-review
secrets: null
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
   `review` step of all `code/*` workflows.

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
- **The skill must not bump.** `review` is the final step of `code/with-review`,
  so the ticket stays in `review` and the existing `autoclose-merged` sweep marks
  it `done` after the human merges. This is an explicit exception to the base
  prompt's "always end a step with `coga bump`" rule — say so in the skill, or an
  agent will bump or `coga mark done` out of habit. Report back with
  `coga slack --task <id> --message "<one line>"` instead.

### Part 1 — the launch gate

`_refuse_human_handoff_launch` (`src/coga/commands/launch.py:1232`) bails
whenever `assignee:` is not in `cfg.agents`. It is called twice — `launch.py:257`
(before activation) and `launch.py:276` (after). `agent_override` is passed in but
only interpolated into the *error message*; it does not open the gate. Separately,
`_read` (`launch.py:174`) applies the override to `frontmatter["assignee"]` only
when the target `is_bootstrap`, so a real task never picks it up. Once the gate
lets the launch through, `launch_assignee = agent_override or assignee`
(`launch.py:286`) already resolves the agent type correctly.

Required properties of the change:

- The override must be **explicit** — never inferred, never defaulted. Without
  `--agent`, a human-owned step is still refused exactly as today.
- The override must be **ephemeral**. `_read` mutates an in-memory `Ticket`;
  make sure that mutation cannot reach disk. After the session, `assignee:` must
  still read the human owner.
- The launch banner must say it is assisting on a human-owned step, so the
  unusual launch is visible in the transcript.

**Tradeoff, accepted deliberately by the owner:** this relaxation is *global* —
any human-owned step on any workflow becomes agent-launchable with an explicit
`--agent`. The narrower alternative (a per-step `agent_assist: true` opt-in in the
workflow) was considered and rejected in favour of the smaller diff. The three
properties above are the mitigations; keep them.

Tests belong in `tests/test_launch.py`: permitted with an explicit `--agent`,
still refused without one, and `assignee:` unchanged on disk afterwards.

### Part 2 — the skill and the workflow wiring

- New skill at `coga/skills/code/address-pr-comments/SKILL.md`.
- Wire it as `skills:` on the `review` step of `code/with-review`,
  `code/with-self-review`, and `code/design-then-implement`, all under
  `src/coga/resources/templates/coga/bootstrap/workflows/code/`. These `code/*`
  workflows are bundled batteries only — there is no repo-local `coga/workflows/code/`
  copy to keep in sync (unlike most shipped assets; see CLAUDE.md).
- `compose.py:344` reads the current step's `skills:` regardless of its
  `assignee:`, so skills on an owner step compose correctly once the launch is
  permitted.
- The prose already describes the intended behaviour and disagrees with the code:
  `code/with-review.md:112-116` says an agent launched during `review` "may inspect
  the PR, run verification, prepare or push explicitly requested fixes, and report a
  recommendation" but "must not merge … unless the human explicitly says to". Treat
  that as the authority for what the skill may do, and update it to name the command.
- **Reading comments:** `gh` is already a hard dependency (`src/coga/open_pr.py`,
  `src/coga/autoclose.py`). Unresolved review threads need `gh api graphql` —
  `gh pr view --comments` returns issue comments and misses per-line thread
  resolution state. The PR URL is on the ticket as `pr:` under `## Dev` (see the
  attached `dev/code` context); the branch is `branch:` in the same block.

### Out of scope

- Automatic/recurring triggering (a sweep that polls open PRs and launches on its
  own) — considered and rejected for now.
- Resolving GitHub threads, and merging, both of which stay with the human.
- Any change to the `open-pr` step, `coga open-pr`, or the `requires: pr` gate.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
