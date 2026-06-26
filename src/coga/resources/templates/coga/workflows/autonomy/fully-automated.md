---
name: autonomy/fully-automated
description: Agent runs an unattended low-risk task end to end and reports the verified outcome.
steps:
  - name: prerequisites-and-handoff
    assignee: agent
  - name: dry-run-or-downgrade
    assignee: agent
  - name: run-unattended
    assignee: agent
  - name: report-to-coga
    assignee: agent
---

## prerequisites-and-handoff

List the prerequisites: tools, auth scopes, write access, target reachability,
and credentials. Verify each by exercising the real action cheaply and
reversibly; a connected connector is not proof it can write. For page or UI
probes, let async content finish loading before reading the result.

If a check exposes a human-clearable gap (login, scope grant, credential),
communicate clearly, pause, and resume once it is resolved. If the capability
does not exist, fail loud and reassign to `autonomy/human-verify` or
`autonomy/human-only`, or escalate. Handle the rest yourself, and advance only
when every prerequisite is satisfied.

## dry-run-or-downgrade

With prerequisites met, dry-run the automation to confirm it runs reliably and
repeatably. If it can't run cleanly after 5 total tries, fail loud and reassign
to `autonomy/human-verify` or `autonomy/human-only`. Capability gaps belong in
the prior step; this step is about flakiness, not whether an action is possible
at all.

## run-unattended

The agent starts, performs, and completes the entire task by itself, with no
human in the loop. If it can't complete — an action errors, or the result isn't
what was intended — fail loud: stop rather than push past a half-done action,
leave things in a safe, known state, and carry the failure into the report.

## report-to-coga

Post the outcome to the shared coga notification channel — success or failure — after
verifying it actually landed. A call returning 200 is not proof the goal was
met. Include the result inline if it's compact; if it's large, post a path to
the artifact instead.
