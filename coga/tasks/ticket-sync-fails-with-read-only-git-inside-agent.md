---
title: Ticket sync fails with read-only git inside agent sandboxes
status: draft
owner: nicktoper
workflow: code/with-review
---

## Description

When an agent runs a state-changing Coga command (`coga bump`,
`coga mark`, `coga block`, `coga create`) inside its own sandbox, publishing
the task state to the control branch fails. It logs:

```
[git] sync failed: `git hash-object` failed: error: unable to create temporary file: Read-only file system
fatal: Unable to add (null) to database
```

The transition itself still happens on disk, as the sync contract requires,
but the ticket and log changes never reach `origin/main`. They sit dirty in
the checkout until some later sync outside the sandbox picks them up, or a
human pushes them by hand. The failure is frequent and ongoing:
`coga/log.md` holds 191 of these "Read-only file system" sync failures since
2026-06-09. Of the 35 that follow a logged launch line, 32 were launched with
`agent=codex`, and only 3 with `agent=claude`.

Note that the log's `[agent:<name>]` attribution names the ticket's configured
agent, not the process that ran the command. For example, the 2026-09-25 10:49
`[agent:claude] advanced` line came from a `launch_agent=codex` session. Read
the preceding `launched (...)` line to see which CLI actually ran.

Done when a state change made from inside a sandboxed agent session reaches
the control branch without a human pushing it. A regression test must cover
the path where the in-sandbox publish is refused and the state still gets
published, for example by the supervisor after the session exits. The
`coga/sync` topic must describe the chosen behavior.

## Context

**Cause, as far as known:** `git.sync_task_state` publishes without touching
the working tree, by writing blobs with `git hash-object -w --stdin` (in
`git.py`) and building the commit from them. That needs write access to
`.git/objects`. The likely culprit is Codex's default `workspace-write` sandbox:
it lets the agent edit the workspace but keeps `.git` read-only, so the very
first object write fails. Coga launches `codex` with no sandbox flags
(`[agents.codex]` in `coga/coga.toml`), and the owner's `~/.codex/config.toml`
sets no `sandbox_mode`, so the default applies. Claude Code as configured here
has no sandbox: an attended claude session wrote to `.git` (worktree, commit,
push) without error on 2026-09-25.

Confirm before designing:
- Reproduce with a codex-launched `coga bump`.
- Explain the 3 claude-launched failures. They may be codex bumps under a
  claude-configured ticket, a different sandbox, or a separate cause.
- Check whether a linked worktree's shared `.git` behaves differently from the
  primary checkout.

**Candidate directions** (pick one in implementation, and weigh them on the
blackboard):
- The `coga launch` / megalaunch supervisor runs outside the sandbox, so it
  could retry or perform the publish after each agent exit. Its exit path
  already refreshes the control checkout (see `coga/launch`, "The step
  chain"). Tradeoff: state is published at session end, not at bump time.
  That is also exactly when the supervisor rereads the ticket to decide the
  next step.
- Let the Codex sandbox write to `.git`, for example with a sandbox
  writable-roots setting in the `[agents.codex]` launch argv or the user's
  Codex config. Tradeoff: every codex session can then rewrite git history
  and refs, and it doesn't help Codex sessions not started by Coga.
- Detect the read-only case and log a clear "deferred" note, not a scary
  failure, then publish later. This only makes sense combined with one of the
  above.

**Related:** `where-have-code-review-disappeared` suspects a stale ticket
reread breaking the agent → other-agent step chain. An unpublished bump caused
by this failure may be one mechanism, so compare notes with that ticket.

**Topics:** `docs/contexts/coga/sync/SKILL.md` (cited, not attached) owns the
contract: publish `coga/tasks/**`, `coga/log.md`, and `coga/recurring/**` to
the control branch without committing on a local branch, and a failed publish
never undoes the transition. Its child topics hold the git detail. Update the
owning topic in the same PR.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
