---
title: 'Harness loop: relay launch continues through agent steps until blocked'
status: active
mode: interactive
owner: nick
assignee: claude1
workflow: code/with-review
step: 1 (implement)
contexts:
  - relay/codebase
  - relay/cli
  - relay/architecture
  - relay/principles
---

## Description

Today, one `relay launch` covers exactly one workflow step: agent
runs, calls `relay bump`, exits. To do step N+1 someone has to
relaunch. Fine for workflows where every step needs a human gate
between, but wrong for chains of agent-only steps (e.g.
`implement → self-review → open-pr`) where the human has no role
mid-chain.

Want: `relay launch` continues through agent-driven steps in fresh
processes, stopping only when the work *actually* needs someone
else (or itself).

## Why fresh-process per step (not same-process continuing)

The other shape — keep the agent process alive across steps — was
considered and rejected. Two reasons:

1. **Context overload.** A single agent context that walks
   implement → self-review → open-pr accumulates the entire repo
   read and diff history before getting to PR-writing. Relay's
   architecture deliberately puts state on disk (blackboard, ticket,
   log) so an agent can be killed and replaced with no loss. That
   property is wasted if we keep the process alive.
2. **Per-step prompt composition is the model.** Each step's skill
   is loaded into the prompt at compose time; advancing past it has
   no defined semantics if the agent stays running.

So: bump-and-exit. The harness re-composes a fresh prompt with the
new step's skill + the now-updated blackboard + the now-updated
ticket body, spawns a fresh agent process, waits, repeat.

## Stop conditions

The loop continues iff *all* of the following are true after a
bump:

1. Ticket `status == "active"` (not done, not paused).
2. Next step has a `skill:` field (a missing skill = pure human
   step, e.g. `review` in `code/with-review`).
3. Next step's `assignee` matches the just-finished step's
   `assignee` — i.e. no handoff happened. Determined deterministically
   from the workflow's per-step assignee field
   (see prerequisite ticket).
4. The previous run exited cleanly (not via `relay panic`).

If any condition fails, the harness stops and prints the reason to
the user. Cases:

- (1) → "task is done" / "task is paused".
- (2) → "next step has no skill — handoff to human".
- (3) → "next step assignee changed: claude1 → nick".
- (4) → already handled by panic (Slack + lock release); harness just
  stops.

## Fix sketch

In `src/relay/commands/launch.py`, the existing single-launch flow
becomes a loop:

```python
while True:
    compose_and_run_agent(ticket, ref)   # blocks until agent exits
    ticket = read_ticket(ref)            # re-read post-bump state
    if ticket.status != "active": break
    next_step = ticket.current_step()
    if not next_step.get("skill"): break
    if next_step.get("assignee") != prev_assignee: break
    if panic_was_called(ref): break
    prev_assignee = next_step["assignee"] or ticket.assignee
```

Detecting "panic was called" is the only non-obvious bit — could be
done via the agent process's exit code (panic exits non-zero), or
by reading the latest log entry, or by checking lock state. Exit
code is cleanest if `relay panic` already non-zeroes the parent
agent (which it should once the panic ticket lands —
`make-relay-panic-exit-non-zero`).

Apply the TTY check from the fail-loud-on-non-tty ticket *outside*
the loop (one check at entry covers all iterations).

## Tests

- Workflow with two consecutive agent steps + same assignee →
  agent process spawned twice, ticket ends on third step (human).
- Workflow with assignee change between steps → loop stops at the
  change, ticket frontmatter reflects the new assignee.
- Agent panics mid-loop → loop stops, lock released, exit non-zero.
- `mode: auto` and `mode: script` tickets behave correctly under
  the loop (auto = same loop semantics, script = no agent so no
  loop — single execution and out).

## Out of scope

- Cross-task chaining (this is intra-task only — one ticket's
  workflow steps).
- Switching agent identity mid-loop. If step N+1's assignee is a
  different agent type, the loop stops; the new agent gets relaunched
  by a human or scheduler. Auto-switching agents is a separable
  concern.

## Open questions

- Should the harness also stop on a heuristic like "we've looped 5
  times, sanity check"? Probably not for v1 — workflows are short by
  design. Revisit if it becomes an issue.
- What's the right console output between iterations? At minimum, a
  banner "→ entering step N (name)" before each compose+spawn so the
  human watching sees progress.
