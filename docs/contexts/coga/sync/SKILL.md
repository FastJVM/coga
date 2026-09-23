---
name: coga/sync
description: Overview of Coga's two sync layers (live notifications for humans, git publication of control and feature-checkout state) with links to the child topics that hold the detail; attaching this topic does not load those children.
---

# Sync layers — notifications and git

Agents work asynchronously; the people approving and unblocking them do not.
Two layers keep both sides honest. The markdown on disk is always the write;
each layer only reports or publishes it.

- **Notifications** tell humans what changed, live, via the configured
  channel (Slack today). Only outcomes, urgent exceptions, and explicit FYIs
  post; routine lifecycle churn stays in `coga/log.md` and git.
- **Git** makes task state durable and shared. Coga publishes `coga/tasks/**`,
  `coga/log.md`, and `coga/recurring/**` onto the control branch
  (`origin/main` by default) without committing on a local branch, stashing,
  or rebasing.

Both layers treat a failed announcement or push of a durable write alike:
surface the miss, keep the file as written, and never let it undo the
transition.

## Control versus feature checkouts

- A **control checkout** (HEAD is the control branch) stays clean and level:
  each publish fast-forwards it.
- A **feature or detached checkout** publishes the same way but keeps its
  published ticket and log dirty by design. Do not `git add` Coga state into
  a PR. `coga status` warns when control is ahead of the local copy.
- The end-of-command sweep publishes every dirty task, log, and recurring
  path from **whichever checkout you ran the command in** — including a hand
  edit to ticket prose or a recurring template on a feature branch. Contexts,
  skills, workflows, and config are never swept; only a `coga ticket`
  interview publishes the contexts and skills it touched.

## Where the detail lives

| Question | Topic |
| --- | --- |
| Which events post, where, and how to configure the channel | [`coga/notifications`](../notifications/SKILL.md) |
| Which producers post on which surface | [`coga/notifications/producers`](../notifications/producers/SKILL.md) |
| What happens when a post fails; preflight; redaction | [`coga/notifications/failures`](../notifications/failures/SKILL.md) |
| The action-needed channel and its bar | [`coga/important`](../important/SKILL.md) |
| `publish`, the sweep, strict versus best-effort paths | [`coga/internals/state-publication`](../internals/state-publication/SKILL.md) |
| Why a publish is refused; stale generations; schema conversions | [`coga/internals/git-regressions`](../internals/git-regressions/SKILL.md) |
| `refresh`, fast-forward, staleness and stranded writes | [`coga/internals/git-refresh`](../internals/git-refresh/SKILL.md) |
| Append-only files, `merge=union`, and concurrent writers | [`coga/internals/spool-merge`](../internals/spool-merge/SKILL.md) |
| Composing new cross-run state without hidden queues | [`coga/patterns`](../patterns/SKILL.md) |
| Session usage records carried by the log | [`coga/usage`](../usage/SKILL.md) |

There is no daily digest (removed, #786); every notification posts live or
not at all.

## Design rule for new features

A command that changes state others need to know about reaches both layers:

1. Make the three notification decisions — surface, destination, preflight
   policy — described in `coga/notifications`.
2. Publish its task through `git.sync_task_state` at the logic boundary where
   the write, validation, log append, and notification post have all
   finalized (`coga/internals/state-publication`). The end-of-command sweep
   is a backstop with a generic message, not a substitute for the readable,
   individually attributed publish.
3. Echo the local outcome to stdout before posting, so it stays visible
   above any notification error.

Never bypass both layers when the team needs awareness; never post chatter
that is not an outcome, urgent exception, or explicit FYI.
