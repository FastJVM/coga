---
name: coga/sync
description: Map of Coga's two sync layers (live notifications for humans, Git publication of Coga state) with links to the topics that own each; attaching this topic does not load them.
---

# Sync layers — notifications and git

Agents work asynchronously; the people approving and unblocking them do not.
Two layers keep both sides honest. The markdown on disk is always the write;
each layer only reports or publishes it.

- **Notifications** tell humans what changed, live, via the configured
  channel (Slack today). Only outcomes, urgent exceptions, and explicit FYIs
  post; routine lifecycle churn stays in `coga/log.md` and Git.
- **Git** makes Coga state durable and shared on the control branch
  (`origin/main` by default), without committing on a local branch,
  stashing, or rebasing.

Both layers treat a failed announcement or push of a durable write alike:
surface the miss, keep the file as written, and never let it undo the
transition. There is no digest: every notification posts live or not at all.

| Question | Topic |
| --- | --- |
| Which files publish, when, from which checkout; strict publication and recovery | [`coga/state-publication`](../state-publication/SKILL.md) |
| Which events post, where, how to configure the channel, and what happens when a post fails | [`coga/notifications`](../notifications/SKILL.md) |
| Which producers post on which surface | [`coga/notifications/producers`](../notifications/producers/SKILL.md) |
| The action-needed channel and its bar | [`coga/important`](../important/SKILL.md) |
| Session usage records carried by the log | [`coga/usage`](../usage/SKILL.md) |

For developing Coga, the [state publication
internals](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/state-publication/SKILL.md)
and [patterns](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/patterns/SKILL.md)
hold the implementation and the rule for adding a state-changing command.
