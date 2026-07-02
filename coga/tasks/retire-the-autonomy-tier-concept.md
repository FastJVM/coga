---
slug: retire-the-autonomy-tier-concept
title: retire the autonomy tier concept
status: active
mode: llm
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

The **autonomy-tier / triage** concept is retired. Remove it from the repo:
the 3-question triage test, the four named tiers (`human-only`,
`assist-only`, `human-verify`, `fully-automated`), the `autonomy/triage`
context, the `autonomy/*` tier workflows, the bootstrap/ticket interview step
that runs the triage, and the doc passages that teach the concept — across
both the live `coga/` tree and the packaged `src/coga/resources/templates/`
copies.

Done looks like: no context, workflow, skill, or doc still presents the
autonomy-tier framework as live guidance; `coga validate` passes; the test
suite passes; nothing references the deleted files.

## Context

**CRITICAL — two different "autonomy" things; only one is retired.**

- RETIRED: the *autonomy tier / triage* concept (advisory 4-tier
  classification + 3-question test).
- KEEP (do **not** touch): everything about *how a task launches* — a script
  launch (runs a skill) vs an agent session. That is active plumbing: the
  `autonomy:` field (`interactive` / `auto` in the repo today), the `autonomy`
  column in `src/coga/commands/status.py` (lines 32, 171, 295, 299, 307),
  `Ticket.autonomy`, `is_script_launch`, and `_effective_autonomy` / the
  auto-ban in `src/coga/recurring.py` (line ~513). Leave them alone. Grep hits
  for the bare word "autonomy" in code are almost all launch plumbing, not the
  tier. The only "autonomy" being retired is the advisory *tier/triage*
  vocabulary.

Touchpoints to remove/update (each has a packaged mirror under
`src/coga/resources/templates/coga/...` — keep them in sync per CLAUDE.md):

- Context: `coga/contexts/autonomy/triage/SKILL.md` — delete (and packaged
  copy). This is the tier framework itself.
- Workflows: `coga/workflows/autonomy/{human-only,assist-only,human-verify,
  fully-automated}.md` (and packaged copies). These are named after the
  tiers. Decide with the reviewer whether to delete outright or keep any as a
  plain workflow shape divorced from the tier vocabulary — default: delete.
  First grep for any ticket with `workflow: autonomy/...` in its frontmatter;
  a live ticket pointing at one blocks deletion until repointed.
- Bootstrap skill: `coga/bootstrap/skills/bootstrap/ticket/SKILL.md` (and
  packaged copy) — remove interview step 3 (the autonomy triage) and the
  "Autonomy tier" block in the step-7 summary template; renumber remaining
  steps.
- Docs: `docs/vision.md`, `docs/market-thesis.md`,
  `coga/contexts/coga/architecture/SKILL.md`,
  `coga/contexts/coga/roadmap/SKILL.md` (and packaged
  `coga/bootstrap/contexts/coga/architecture/SKILL.md`) — excise or rewrite
  the tier passages. Judgment call per doc; preserve unrelated content.
- Sweep `coga/tasks/**` and `example/coga/**` for stale references, but do
  not rewrite historical/log-like task bodies unless they present the concept
  as current guidance.

Verify: `grep -rn "autonomy/triage\|autonomy tier\|human-verify\|assist-only\|
fully-automated" .` returns nothing live after the change (ignoring
`coga/log.md`); run `coga validate` and `python -m pytest`; check
`tests/test_config.py`, `tests/test_create.py`, `tests/test_smoke.py` for
fixtures that assumed the tier/workflows exist.

Note: `mode-autonomy-split` tickets exist under `coga/tasks/` — if the tier
was meant to fold into the `mode` field rather than vanish, confirm intent
with the owner before deleting, since that changes "retire" to "migrate".

<!-- coga:blackboard -->
## Production notes

This blackboard is for active-work handoff notes. Authoring scratch was cleared at activation; durable requirements belong in the ticket body.
