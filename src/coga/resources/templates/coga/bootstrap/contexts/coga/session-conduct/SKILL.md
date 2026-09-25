---
name: coga/session-conduct
description: How a launched agent session's conduct is selected — one packaged conduct resource per prompt chosen by the invocation's launch context (attended, megalaunch, recurring) — and what each posture requires of the agent, including how a queued session releases.
---

# Session conduct

How a session executes is a property of the **invocation**, not of the task.
The composer places exactly one conduct resource immediately after the neutral
base prompt ([coga/prompt-composition](../prompt-composition/SKILL.md)). It is
selected, never stacked or appended after task layers, and the base prompt
defers to it for every instruction to ask or to block.

## Selection

`src/coga/compose.py` `SESSION_CONDUCT_RESOURCES` maps the ephemeral
`LaunchContext` passed to `compose_prompt` / `compose_prompt_report` as
`launch_context`:

| Launch context | Resource | Chosen by |
| --- | --- | --- |
| `attended` | `prompt-attended.md` | ordinary `coga launch` (including a human-typed direct period-task launch), `coga chat`, guided `coga ticket`, any recurring spelling with `--interactive`; also the default |
| `megalaunch` | `prompt-megalaunch.md` | `coga megalaunch` (`src/coga/megalaunch.py`) |
| `recurring` | `prompt-queue.md` | runner-owned recurring runs: bare sweep, `--force`, `coga run recurring-scan`, `recurring launch <name>`, a period task's agent phase, a delegated stateless bootstrap session (`recurring_runner._recurring_launch_context`) |

It is never ticket frontmatter, config, or a user flag on an ordinary launch.
An unknown context or a missing resource is a `ComposeError` at the same
preflight boundary as any missing layer, before `in_progress` or spawn.
`--prompt-report` names the selected resource on its `session_conduct` line.

## Postures

**Attended.** A human is present in the REPL. Ask and wait for decisions,
credentials or permissions. State a short plan with its tradeoff and let the
human confirm before substantive code. Use `coga block` only when the human
explicitly asks to park the ticket. Always answer a present human, even on a
`done` or `canceled` ticket; "one step, one session" means not starting the
next step, not ignoring messages.

**Queues (megalaunch and recurring).** The TTY is transport for live
streaming and interruption, not evidence of an attending human, and input the
agent lacks is unavailable. State a plan and continue; never wait for
confirmation. When a concrete decision, credential, permission, or capability
truly prevents progress, run `coga block --task <ref> --reason "..."` as the
terminal action; merely saying "blocked" or asking hangs the queue until a
liveness timeout fails the task. An ordinary step is released only by
`coga bump`, `coga mark done`, `coga block`, or an authorized
`coga mark canceled`; a final response or agent `task_complete` event does
not release it. Both point code steps that cannot create a branch under a
read-only `.git` mount to the `/tmp` clone fallback in the `code/implement`
skill.

Megalaunch adds:

- Name a blocking Coga task's exact path-qualified ref in `--reason`, so the
  drain can retry this task when that one finishes
  ([coga/megalaunch](../megalaunch/SKILL.md)).
- When the human explicitly picked a blocked task, the composed
  resolve-or-re-block preamble may be discussed with them, then
  `coga unblock --answer` and continue, or re-block. Any new unavailable input
  still takes the terminal block path.

Recurring adds the stateless-bootstrap rule: a `bootstrap/<name>` command
ticket has no lifecycle, so its declared final action (a targeted
`coga slack --task bootstrap/<name> ...` roll-up) releases the session, and
failures go into that report.

The two queue resources are deliberately complete documents rather than a
shared fragment plus tails: only one ever reaches an agent, so repetition costs
no runtime tokens and the highest-consequence policy reads as one unit.

## Not conduct

The blocker-resolution preamble is state-derived task context, independent of
conduct ([coga/prompt-composition](../prompt-composition/SKILL.md)).
`## Launch arguments` is invocation input appended after the task layers.
Neither changes which conduct resource is selected.
