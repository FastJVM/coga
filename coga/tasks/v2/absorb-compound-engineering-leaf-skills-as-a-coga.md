---
title: Absorb Compound Engineering leaf skills as a Coga method library
status: draft
owner: nicktoper
workflow: null
---

## Description

Study, then decide, whether Coga should absorb Compound Engineering's leaf skills (ce-brainstorm, ce-plan, ce-code-review, ce-simplify-code, ce-debug, ce-doc-review, ce-pov, ce-strategy, ce-prototype, ce-polish) through the existing managed-skill manifest and a workflow that uses them as step skills — while explicitly not absorbing CE's loop layer (lfg, ce-work's run controller, ce-compound, ce-compound-refresh, ce-sweep), which duplicates the ticket lifecycle or contradicts memory-via-PR. Parked: this is a design study to be picked up later, not an approved implementation. The competitive finding behind it (2026-09-16): CE is a method library that runs inside the agent (35 skills, 14 hosts, MIT, no telemetry); Coga is a runtime that runs outside the agent and spawns it. Where Coga leads CE it is all runtime (ticket lifecycle, enforced per-step human ownership, blocker parks and the queue continues, scheduling, deterministic context delivery, mid-task rewind); where CE leads it is everything that is not the runtime (vendor breadth, method breadth, non-code and front-of-loop skills, install path, audience). ce-work's Return-to-Caller mode is designed to hand its remaining gates to an outer orchestrator, i.e. to something like Coga. Absorbing the leaves fills the acknowledged method-breadth gap without touching what is distinctive; absorbing the loop would make Coga a worse CE.

## Context

Dated 2026-09-16. Read as a record of what was wanted then; re-check every
surface named below against `main` before pulling forward (see
`coga/tasks/v2/README.md`).

### What to study before deciding

1. **Fit of each leaf skill under Codex as well as Claude.** CE leaves assume
   Claude Code conventions in places (slash commands, subagent calls). List
   which of the ten need a `local_adaptation_notes` entry and how much.
2. **Path and config collisions.** CE reads `.compound-engineering/config.yaml`
   and defaults artifacts to `docs/plans/` and `docs/solutions/`. Decide
   whether to adapt paths per skill or leave them and accept a second artifact
   root.
3. **Learning capture.** `ce-compound` writes `<root>/solutions/` directly with
   no approval gate; `ce-compound-refresh` recommends branch+PR on the default
   branch but offers "commit directly". Both cut across `coga/principles` §4.
   The candidate rule: learnings go to the ticket blackboard; Dream / retro
   proposes the PR. Confirm that no absorbed leaf skill invokes `ce-compound`
   internally.
4. **Manifest vs vendoring.** Candidate: entries in
   `src/coga/resources/managed-skills.toml` (`source_type = "github"`,
   `source = "EveryInc/compound-engineering-plugin"`, `required = false`),
   not copies under `bootstrap/skills/`. Vendoring would put the packaging
   twin test (`tests/test_packaging.py`) on the hook for every upstream drift.
   Check that `gh skill install` can select a single skill from that
   multi-skill repo and that `coga skill update --all` reports `conflict`
   correctly once a leaf is locally adapted.
5. **One workflow that uses them.** Candidate `workflows/code/ce.md`:
   `brainstorm (owner)` → `plan (agent, ce-plan)` → `implement (agent,
   code/implement, requires: branch)` → `simplify (agent, ce-simplify-code)`
   → `peer-review (other-agent, ce-code-review)` → `open-pr (requires: pr)`
   → `review (owner)`. Check against the shared-skill authoring rule in
   `coga/workflows` (refer to "the next frozen step", never a step by
   name).
6. **What it costs.** Upkeep of adaptations, CE's taste in the leaves
   colliding with Coga contexts (the context composes earlier and wins), and
   the public concession that method breadth is not Coga's thing — which the
   market thesis already makes.
7. **What it is not.** Not a replacement for `code/*` skills, not a new core
   Python surface, not a plugin API. Zero core changes expected beyond the
   manifest and a workflow file.

### Evidence

- Source-pinned CE comparisons already in the repo: `docs/evidence/adoption-trial.md`,
  `docs/evidence/build-vs-adopt.md` (lists "Coga runs CE" under combinations worth
  considering), `docs/evidence/continuity-comparison.md`,
  `docs/evidence/research-work-comparison.md`, `docs/evidence/research-replacement-trial.md`.
- CE upstream inspected 2026-09-16: README (host list, 35-skill inventory,
  MIT), `skills/lfg/SKILL.md` (single request; stops on an unproducible work
  source, a non-complete child, or an invalidated decision; asks the human only
  through `ce-brainstorm`), `skills/ce-work/SKILL.md` (Return-to-Caller mode:
  "the invoking workflow … owns its remaining gates"; `status: blocked`
  result with `run_id` and `blockers`), `skills/ce-compound/SKILL.md`
  (writes `<root>/solutions/`, no approval described),
  `skills/ce-compound-refresh/references/commit.md` (PR recommended, direct
  commit offered).
- Coga seams: `coga skill install <owner/repo> [skill]`, `coga skill update
  --all` with digest-based `local-adaptation` / `conflict` statuses, `include`
  allowlists, local-first `resolve_skill_path`; all documented in `coga/skill-management`.

### Decision owed when pulled forward

Absorb the leaves via the manifest plus one workflow; do not absorb the loop;
or record why not. Either verdict should also settle the pitch line — "Coga
runs CE" versus positioning against it.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
