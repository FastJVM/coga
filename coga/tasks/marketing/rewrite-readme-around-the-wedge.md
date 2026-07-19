---
slug: marketing/rewrite-readme-around-the-wedge
title: Rewrite README around the wedge
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- marketing/plan
- marketing/positioning
skills: []
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 3 (open-pr)
---

## Description

Rewrite `README.md` (the "what") around the wedge, and create the missing
"how" docs. Supersedes the deleted `marketing/readme-and-docs` ticket
(taken over from zach 2026-07-14).

**The wedge:** you already run several agent sessions in parallel as terminal
tabs — Coga turns tabs into an operation (each session gets a ticket, a
blackboard that survives crashes, a blocker queue for the questions it hits,
and a log of what shipped). Megalaunch is the scheduler on top: when a task
blocks, it parks the question and moves to the next ticket — you stop being
the CPU and become the I/O device answering batched interrupts. Slogan
already in hand: **"Agents do. Humans think."** — backed by "check our math"
(everything auditable in the public repo).

README structure (top to bottom):

1. One-liner + "Agents do. Humans think."
2. The wedge paragraph (tabs → operation; pilot → air-traffic-control).
3. Demo gif slot (see `marketing/add-killer-demo`).
4. The bet, framed as a bet — "two people, output of ten" per
   `docs/vision.md`, explicitly not a measured multiplier.
5. "Measured on itself" block: honest numbers only (no multiplier — line
   throughput claims don't survive scrutiny; categorical facts do: machine-
   initiated work, peer review universal, 31 workstreams/wk at peak, the
   half-time story), linking a resurrected `docs/velocity-report.md`; later,
   the 20-min/day table from `marketing/launch-20-minutes-a-day`.
6. What it replaces (Notion/Linear → markdown tickets; Zapier → scheduled
   skills; ops coordinator → script tasks + megalaunch; wiki → contexts;
   Slack-as-memory → blackboards).
7. The correction loop, *shown* as a ~4-line shell demo.
8. Primitives in six lines; who it's for / not for (filter fast).
9. "vs X" section: plain Claude Code (ephemeral, forgets, you're the
   scheduler), Backlog.md (storage, no loop), Symphony (same skeleton, human
   out of the loop, their cloud), CompanyOS (owned markdown, no state machine
   or gated loop), autonomy platforms (sell "no human between stages" —
   there's no such thing as full autonomy; it's a function of spec +
   evaluability, and the spec/judgment work lands back on you).
10. Install compressed (uv/pip one-liners; hash-mode troubleshooting moves to
    getting-started); `coga init` → `coga build` first-run.
11. Docs map: why → `docs/vision.md`; how → `docs/getting-started.md` +
    `docs/cli.md` (those two live in ticket
    `write-real-coga-documentation-command-reference-gu` — do not duplicate).
12. Key values (trimmed from current README) + AGPL line.

Claim discipline: no productivity multiplier anywhere; the 5x stays in
vision.md as the stated bet; every number in the README must be recomputable
from this repo.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: marketing/rewrite-readme-wedge
worktree: /home/n/Code/codex/coga-rewrite-readme-wedge

## Implement notes

- Scope confirmed docs-only: rewrite `README.md` and resurrect the evidence-oriented
  `docs/velocity-report.md`. The separately ticketed `docs/getting-started.md` and
  `docs/cli.md` are linked but not duplicated here.
- Claim rule: keep the two-people/output-of-ten statement explicitly labeled as
  the bet; only categorical, repo-auditable observations enter the measured block.
- Implemented and committed `README.md` plus `docs/velocity-report.md` at
  `0ff4ee17` (`Rewrite README around the agent-operations wedge`). The feature
  worktree is clean; nothing was pushed.
- Verification: `git diff --cached --check` passed before commit; the embedded
  velocity-report recomputation prints `(31, (2026, 27))`; task-scoped
  `coga validate --json` reports 1 valid task plus only the clone-local
  `missing-user` warning.
- Local-link audit passes for this ticket's owned files. The only absent targets
  are `docs/getting-started.md` and `docs/cli.md`, intentionally owned by sibling
  ticket `write-real-coga-documentation-command-reference-gu` (PR #608) and
  required by this ticket as forward links. Rebase after #608 merges before PR
  publication so those links resolve on the combined branch.

## Peer review

- Reviewed the complete docs diff against `main` and spot-checked `coga build`,
  megalaunch sequencing, ledger actor labels, the six primitives, and local links
  against the implementation and canonical contexts.
- Corrected one must-fix evidence claim: agent-authored workflow transitions do
  not prove that agents initiated task selection. README and velocity report now
  accurately describe agent-operated work selected by a human or scheduler and
  distinguish `agent:*`, `system`, `human:*`, and `megalaunch` ledger actors.
- Fix committed on the feature branch at `fc08ae07` (`peer-review: correct
  agent-operation claim`). `git diff --check` passes. Pure prose change, so no
  pytest run was needed.
- The only unresolved links remain the explicitly forward-linked
  `docs/getting-started.md` and `docs/cli.md` from sibling PR #608; publication
  still requires rebasing after that PR lands, as recorded above.
