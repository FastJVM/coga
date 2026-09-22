---
name: coga/first-task
description: A short walk from a first draft ticket to a merged PR, with the readiness checks to run and links to the topics that own each step.
---

# Your first task

This walk assumes Coga is installed ([coga/install](../install/SKILL.md)) and
the repo is initialized with your name set ([coga/init](../init/SKILL.md)).
Each step links to the topic that owns its contract.

## 0. Check readiness

```sh
coga validate            # repo and task structure; non-zero exit on errors
coga validate --json     # the same, machine-readable
coga status              # the task triage view
```

Run `coga validate` again after any config, workflow, or ticket change. It
warns when `user` is unset. Network probes are opt-in:
`coga validate --check-github` checks git and `gh` auth readiness, and
`--check-slack` checks the Slack webhook
([coga/notifications](../notifications/SKILL.md)). Neither combines with
`--task`.

On an empty repo, `init` seeded an onboarding ticket. `coga build` is a
default alias for `launch coga-build`: one question, an agent-led chat, a
short vision, then a batch of starter tickets. Use `coga build --agent
codex` for Codex. It dispatches through `coga launch`, so it needs an
initialized repo. There is no separate `coga setup`.

## 1. Create a draft

A ticket is one unit of work: a markdown file under `coga/tasks/`
([coga/tickets](../tickets/SKILL.md)). Either scaffold one:

```sh
coga create "Add a health-check endpoint" --workflow code/with-review
```

then fill in `## Description` and `## Context`, or let an agent interview
you into one with `coga ticket "Add a health-check endpoint"`. To plan a
batch, talk it through in `coga chat` and let the session create the drafts.
Drafts are cheap and need no workflow yet, but a ticket cannot be activated
without one ([coga/workflows](../workflows/SKILL.md)).

## 2. Launch it

```sh
coga launch add-a-health-check-endpoint --prompt-report   # inspect, don't launch
coga launch add-a-health-check-endpoint
```

`--prompt-report` shows the composed layers and their token counts
([coga/prompt-composition](../prompt-composition/SKILL.md)). A real launch
treats typing `coga launch` as the approval signal for a draft or paused
ticket, but it activates in two phases (`src/coga/commands/launch.py`
`_prepare_auto_activate` / `_commit_auto_activate`). Activation is first
prepared in memory, so the prompt sees the activated ticket. The durable
write is deferred until every refusing preflight has passed: interactive
TTY, agent CLI on `PATH`, prompt composition, secret resolution, and git
push access. Only then is activation written and the ticket flipped to
`in_progress`. A refused launch leaves the ticket unchanged and posts no
"started" notice. Details: [coga/launch](../launch/SKILL.md).

The session is attended: you watch and talk to the agent. It does the step's
work, records findings on the blackboard
([coga/blackboard](../blackboard/SKILL.md)), and finishes with `coga bump`.
For a multi-step workflow such as `code/with-review`, the supervisor then
starts the next agent step, rotating to the peer agent for review
([coga/agents](../agents/SKILL.md)).

## 3. Review and merge

The final `review` step is a human gate with an open PR. Review and merge it
on GitHub, then run `coga bump <task>`; bumping the final step marks the
ticket `done`. A repo that schedules the `autoclose-merged` recurring sweep
also closes merged tickets on its next run, but that is opt-in
([coga/recurring](../recurring/SKILL.md)). To decline the work instead, use
`coga mark canceled <task> --message "<reason>"`, which stays distinct from
completed work. States and gates: [coga/lifecycle](../lifecycle/SKILL.md).

`coga show <task>` prints the whole ticket, history included.

## What you touched

- **Ticket**: the durable unit of work, in files rather than a session.
- **Workflow**: ordered steps, frozen into the ticket when it activates.
- **Blackboard**: scratch memory that survives torn-down sessions.
- **Composition**: each prompt is rebuilt from files on disk at launch.
- **Correction loop**: when an agent is misled, fix and commit the context
  or workflow that misled it; the next launch composes the fix
  ([coga/principles](../principles/SKILL.md)).
