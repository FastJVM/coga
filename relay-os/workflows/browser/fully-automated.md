---
name: browser/fully-automated
description: Triage assigned this because a machine can do the task reliably and the failure radius is small or nonexistent. The agent runs it unattended end to end and reports the result to the team.
steps:
  - name: prerequisites-and-handoff
    assignee: agent
  - name: dry-run-or-downgrade
    assignee: agent
  - name: run-unattended
    assignee: agent
  - name: report-to-relay
    assignee: agent
---

## prerequisites-and-handoff

List every prerequisite the automation needs — tools, auth scopes, write access, target reachability, credentials. Verify each by actually exercising it: a connected connector is not proof it can write, so probe the real action (cheaply and reversibly) before assuming a prerequisite is met. When the probe is a page or UI, let async/dynamic content finish loading before reading the result — a not-yet-populated view can read as a false negative. For any gap a check reveals, split on whether a human can clear it: if a person can — a human-only login, a scope grant, a credential only they can issue — communicate clearly, pause, and take the task back once it's resolved. If nothing a human can reasonably do would clear it (the capability simply doesn't exist), don't wait or loop: fail loud and re-assign to a more protective workflow, or escalate. Handle everything else yourself. Only advance once every prerequisite is satisfied.

## dry-run-or-downgrade

With prerequisites met, dry-run the automation to confirm it runs reliably and repeatably. If it can't run cleanly after 5 total tries, fail loud and re-assign to a more protective workflow (human-verify or human-only). Capability gaps belong in the prior step — this step is about flakiness, not whether an action is possible at all.

## run-unattended

The agent starts, performs, and completes the entire task by itself, with no human in the loop. If it can't complete — an action errors, or the result isn't what was intended — fail loud: stop rather than push past a half-done action, leave things in a safe, known state, and carry the failure into the report.

## report-to-relay

Post the outcome to the shared relay Slack channel — success or failure — after verifying it actually landed (a call returning 200 is not proof the goal was met). Include the result inline if it's compact; if it's large, post a path to the artifact instead.
