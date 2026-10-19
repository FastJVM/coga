---
title: Fix the README for the V1 instrument positioning
status: done
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
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

Completed deliverable: the README is the current public presentation. The
former marketing contexts were archived on 2026-10-15. For follow-up edits,
read `coga/principles`, `README.md`, `docs/README.md`, and `coga/install` / `coga/first-task`
(`docs/contexts/coga/{install,first-task}/SKILL.md`, which replace the deleted
`docs/getting-started.md`) before editing. Keep this scoped to the README
opening and the links needed for its reader path, not a documentation rewrite.

Use megalaunch and one correction that changes later work as the concrete
proof. Distinguish a blocked task from the queue moving on to other tasks.
Coordinate exact commands with the `marketing/fix-installer/` tickets; do not invent a
second onboarding procedure or require an unpublished essay to understand
Coga. Current writing claim limits are in the
[idea-piece brief](idea-piece.md#claim-and-wording-limits). The launch ticket
owns publication timing, and PostHog implementation stays in its own ticket.

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

### Clean-install coordination

Reconcile the README's entry paths against `coga/install`, `coga/init`, and
`coga/first-task`: prerequisites and initialization precede `coga build`,
which is valid after initializing an empty repo. Keep this ticket as the
owner of the README correction; do not create a duplicate installer draft.
Use `marketing/fix-installer/run-clean-installs-and-file-issues`'s final
matrix before claiming an end-to-end verified path.

That ticket's October 1, 2026 check found two conflicting entry paths:
“Getting Started” began with `coga build` before prerequisites/init, while
“Install” later gave `uv tool install coga`, repo selection, `coga init --user`,
`coga ticket`, and `coga launch`. Its clean Linux Python 3.11.16 test found
PyPI 0.2.0 blocked at init (gh, then a resource namespace crash), while the
main wheel 0.3.2 installed, initialized, and validated. First-ticket tests
were still in progress at that date; consult the final matrix for current
results.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Production notes

### Positioning review — 2026-10-13 (owner + Claude)

Decisions live in their owners, not here: `marketing/positioning` (root
premise, `## Refinement — owner review session, 2026-10-13`, claim limits),
`marketing/strategy` (`## Where value moves`), `coga/lifecycle` (cancel and
restart on a wrong premise; rewind when the premise holds), with a linked
summary in `product/vision`. Dated competitor facts:
`docs/evidence/agent-memory-landscape-2026-10-13.md`.

README change merged as PR #1000 (branch `marketing/readme-top`): opening
with the "fix the file once" payoff, `## The problem`, Key ideas rooted in
work discovered by doing, rewritten Example, "Who it is for" before Install,
and `## First steps` split between an empty repo (`coga build`) and an
existing project (`coga ticket`). PR #1001 adds the platform line, the
`coga --version` check and the empty-repo rule on top.

Still open for this ticket:
- Proof: megalaunch carrying work forward is not shown yet; the Example shows
  only the correction-becomes-context half.
- Commands: `## First steps` is not yet checked against the `fix-installer`
  final matrix.
- Demo video: not watched; the README link and its caveat are unchanged.

## Retro

status: processed
skill: retro/done-ticket
result: knowledge-pr
title: New context: README launch checks still owed
