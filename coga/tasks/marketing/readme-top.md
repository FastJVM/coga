---
title: Fix the README for the V1 instrument positioning
status: draft
owner: nicktoper
agent: claude
contexts:
  - marketing/plan
  - marketing/positioning
workflow: code/with-review
---

## Description

Fix the README's first screen for the approved V1 instrument positioning.
Explain who is in control, show the concrete behavior, and give a reader a
clear path to installation and one useful completed task. Done means the
owner-reviewed README change is merged, its claims match the product and
its links/commands agree with the verified installer/onboarding path.
The linked demo has also been reviewed and either retained as accurate,
corrected, or removed from the README.

## Context

Attach the current marketing message and plan; read `README.md`, `docs/README.md`, and `coga/install` / `coga/first-task`
(`docs/contexts/coga/{install,first-task}/SKILL.md`, which replace the deleted
`docs/getting-started.md`) before editing. Keep this scoped to the README
opening and the links needed for its reader path, not a documentation rewrite.

Use megalaunch and one correction that changes later work as the concrete
proof. Distinguish a blocked task from the queue moving on to other tasks.
Coordinate exact commands with the `marketing/fix-installer/` tickets; do not invent a
second onboarding procedure or require an unpublished essay to understand
Coga. Claim support follows marketing/positioning. The launch ticket owns
publication timing, and PostHog implementation stays in its own ticket.

### Existing video — check, not a new production prerequisite

Owner decision: fold the existing demo check into this README change. Watch
the [95-second demo](https://www.youtube.com/watch?v=iwnewxJvRPc) and check its
commands and explanation against the current product. If it is accurate and
shows the human directing work, keep it. If it is misleading, remove the
README link or make a small correction that clearly addresses the problem.
Re-record only if a short screen capture is the simplest way to demonstrate
megalaunch plus a correction affecting later work. A polished video or a new
recording is not a launch prerequisite. Record the decision and reason here;
changes on YouTube remain an owner action.

This absorbs `cleanup/check-the-demo-video-against-current-cli-names`.
Its September 3 check recorded a July 18 upload titled “Coga Asynchronous
Agentic Programming”, with no captions or description, and flagged the
removed `coga project` command as a possible accuracy issue. Nobody had yet
verified whether that command appeared in the video. Those observations are
dated; inspect the video and current behavior rather than treating the old
command comparison as a complete present-day check. The original notes remain
in `docs/archive/launch-programs/phase-0-audit/audit-history.md`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.


## Clean-install coordination — 2026-10-01

`marketing/fix-installer/run-clean-installs-and-file-issues` confirms the current README still presents two entry paths: “Getting Started” begins with `coga build` before prerequisites/init, while “Install” later gives `uv tool install coga`, repo selection, `coga init --user`, `coga ticket`, and `coga launch`. These are no longer identically titled blocks, but the ordering conflict remains. Keep this existing ticket as owner; no duplicate installer draft. Reconcile against `coga/install`, `coga/init`, and `coga/first-task`; build is valid after initializing an empty repo. Current clean Linux Python 3.11.16 test: PyPI 0.2.0 blocks at init (gh, then resource namespace crash); main wheel 0.3.2 installs/inits/validates. First-ticket tests remain in progress. Use the run ticket's final matrix before claiming an end-to-end verified path.
