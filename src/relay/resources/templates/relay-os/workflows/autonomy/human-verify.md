---
name: autonomy/human-verify
description: Agent prepares high-radius work to the irreversible step; human reviews and commits.
steps:
  - name: prerequisites-and-handoff
    assignee: agent
  - name: dry-run-or-downgrade
    assignee: agent
  - name: prepare-to-brink
    assignee: agent
  - name: human-review
    assignee: human
  - name: human-commits
    assignee: human
  - name: report-to-relay
    assignee: agent
---

## prerequisites-and-handoff

List the prerequisites: tools, auth scopes, write access, target reachability,
credentials, and input data. Verify each by exercising the real action cheaply
and reversibly; a connected connector is not proof it can write. For page or UI
probes, let async content finish loading before reading the result.

If a check exposes a human-clearable gap (login, scope grant, credential, or
missing fact), communicate clearly, pause, and resume once it is resolved. If
the capability does not exist, fail loud and downgrade to `autonomy/human-only`,
or escalate. The failure radius here is high, so surface gaps before walking the
human to the brink. Advance only when every prerequisite is satisfied.

## dry-run-or-downgrade

With prerequisites met, dry-run the task to confirm it runs reliably and
repeatably. If it can't run cleanly after 5 total tries, fail loud and reassign
to `autonomy/human-only`. Capability gaps belong in the prior step; this step is
about flakiness, not whether an action is possible at all.

## prepare-to-brink

Do everything reversible and stop at the irreversible control without touching
it. If you can't reach the brink — a prep step fails or the state won't come up
ready — fail loud and stop; never hand off a half-prepared or broken state for
the human to fire. Otherwise, confirm the state reports ready, then hand off:
what will be committed, where, the consequences, and the exact control the human
will click.

## human-review

Check the prepared state against intent. If anything's wrong, send it back to
prepare-to-brink; nothing commits until the human approves.

*Mistake handling:* if the review finds problems, the agent asks the human for
specifics. If the human doesn't provide them, the agent restarts the workflow
from the beginning.

## human-commits

The human clicks the irreversible control. The agent never does.

## report-to-relay

After the human commits, confirm the irreversible action actually landed; verify
rather than assume (e.g., the message is in Sent, the file shows as shared).
Then post the outcome to the shared relay Slack channel, whether it completed or
was aborted. Include the result inline if it's compact; if it's large, post a
path to the artifact instead.
