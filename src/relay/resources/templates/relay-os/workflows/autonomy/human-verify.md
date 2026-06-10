---
name: autonomy/human-verify
description: Triage routes a task here when a machine can do it but the failure radius is high. The agent prepares everything up to the one irreversible action; the human reviews and fires it.
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

List every prerequisite the task needs — tools, auth scopes, write access, target reachability, credentials, input data. Verify each by actually exercising it: a connected connector is not proof it can write, so probe the real action (cheaply and reversibly) before assuming a prerequisite is met. When the probe is a page or UI, let async/dynamic content finish loading before reading the result — a not-yet-populated view can read as a false negative. For any gap a check reveals, split on whether a human can clear it: if a person can — a human-only login, a scope grant, a credential or fact only they can supply — communicate clearly, pause for them to resolve it, then take the task back. If nothing a human can reasonably do would clear it (the capability simply doesn't exist), don't wait or loop: fail loud and downgrade to the more protective human-only workflow, or escalate. The failure radius here is high, so surface these gaps now: far better than walking the human all the way to the brink only to discover the irreversible action can't be staged. Only advance once every prerequisite is satisfied.

## dry-run-or-downgrade

With prerequisites met, dry-run the task to confirm it runs reliably and repeatably. If it can't run cleanly after 5 total tries, fail loud and re-assign to the more protective human-only workflow. Capability gaps belong in the prior step — this step is about flakiness, not whether an action is possible at all.

## prepare-to-brink

Do everything reversible and stop at the irreversible control without touching it. If you can't reach the brink — a prep step fails or the state won't come up ready — fail loud and stop; never hand off a half-prepared or broken state for the human to fire. Otherwise, confirm the state reports ready, then hand off: what will be committed, where, the consequences, and the exact control the human will click.

## human-review

Check the prepared state against intent. If anything's wrong, send it back to prepare-to-brink — nothing commits until the human approves.

*Mistake handling:* if the review finds problems, the agent asks the human for specifics. If the human doesn't provide them, the agent restarts the workflow from the beginning.

## human-commits

The human clicks the irreversible control. The agent never does.

## report-to-relay

After the human commits, confirm the irreversible action actually landed — verify rather than assume (e.g., the message is in Sent, the file shows as shared) — then post the outcome to the shared relay Slack channel, whether it completed or was aborted. Include the result inline if it's compact; if it's large, post a path to the artifact instead.
