---
title: Anonymous install telemetry (opt-out, no PII)
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Give us a count of **active installs** so we can tell whether anyone is
actually running Relay after launch. Strictly no PII.

Decided shape: a single anonymized **opt-out** ping.

- Sends only: a random install ID (generated once, stored locally), the Relay
  version, and coarse OS/platform. Nothing that identifies a user, repo, path,
  ticket content, or git remote.
- **On by default**, with clear first-run disclosure and a one-line disable
  (config flag + env var). Document exactly what is sent and how to turn it off.
- Fires at most once per period (e.g. daily) per install — enough to estimate
  "active," not a background reporter. Idempotent; never blocks a command.
- Must **fail silent-for-the-user but never wrong**: a telemetry failure must
  not break or slow any `relay` command, and must not be swallowed in a way that
  hides a real bug (log it, don't crash the command).

Open design questions for the design step:

- Where the ping lands — a tiny endpoint we run vs. a hosted analytics sink.
  This is a **hosted backend**, which is the principle tension below; keep it as
  small and inspectable as possible.
- "Active" definition: distinct install IDs seen in the last N days.
- Whether to also lean on PyPI download stats as a cross-check (cheap, no infra).

## Context

This is a Wave 1 launch-gate item: post-launch we need to know if installs are
real and sticky.

Principle tension to respect (see `relay/principles`): phoning home introduces a
hosted backend, which cuts against principle 5 (own the substrate, local by
default) and the legibility ethos. The mitigations are non-negotiable: opt-out
**with** loud disclosure, fully documented payload, trivial disable, no PII, and
the agent/human can read exactly what's sent. If the design can't keep those, it
should fall back to the no-phone-home PyPI/GitHub estimate instead.

