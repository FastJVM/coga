---
title: init-questions
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

On a fresh `relay init`, create a launch-ready `relay-setup` ticket (and
ship the `init/setup` workflow it runs). When the new user launches it, the
agent interviews them about the repo, then turns the answers plus a repo
scan into durable relay-os artifacts — contexts, rules, workflows,
recurring tasks, possibly skills — reviewed by the owner before anything
counts as final. So every future agent starts already knowing the project
instead of starting from zero.

The process itself — the four interview questions, the generation ground
rules, the follow-up open-questions interview, and the review loop — lives
in `relay-os/workflows/init/setup.md` (live + packaged copies in sync),
not here.

## Context

We found we were missing an easy opportunity for a new user to build reusable artifacts from installation — without it, relay-os starts empty and every future agent starts from zero. This fills that gap.

Design change (2026-06-12): an earlier cut asked the four questions
directly inside `relay init`. That's out — init must stay free of
additions: no prompts, no interview. The relay-setup task now ships as a
static packaged template (same mechanism as `tasks/browser-automation/`),
so init's only change is more files in the template copy, and the
interview became the first workflow step at launch (which also fixes the
template's placeholder `owner`/`human` from relay.local.toml). A second
change from the full-process prototype (see blackboard): a
`resolve-open-questions` agent step between generation and human review,
because the open-questions list otherwise rots on the blackboard waiting
for the human to notice it.

Design points validated by a pre-implementation dry run (2026-06-11; full
eval, scorecard, and Zach's recorded interview answers are on the
blackboard; fixtures kept at `~/Desktop/admin-init-test` and
`~/Desktop/admin-fresh` so the identical test can be replayed against the
real implementation):

- The interview captures intent; the scan captures the operation. Answers
  alone preserved about a third of ground-truth facts at partial
  fidelity; the scan recovered all of them, including scheduled work the
  human forgot to mention. Treat the scan step as load-bearing.
- The setup ticket should emit an **open-questions list** as a
  first-class output alongside the artifacts. On the empty-repo path it
  is the main deliverable — that path produces a starter relay-os, not a
  complete one.
- Conflict precedence: repo docs win on facts, interview answers win on
  intent. This resolved all four answer/doc conflicts in the dry run
  correctly.
- Generation must stub-and-ask rather than fabricate. Both dry-run
  agents did this unprompted (zero invented facts); make it an explicit
  requirement, not luck.
- Interview refinements worth adopting: probe enumerables ("a few
  year-end processes" → "list them"); ask *where* referenced documents
  live so the scan can ingest them; ask for anchor dates on cadences
  cron can't express (bi-weekly payroll broke both legs' schedules).
- The scan must degrade gracefully to answers-only: real ops repos can
  be nearly empty outside relay-os.
