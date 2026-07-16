---
slug: v2/add-relay-skill-search-with-candidate-eval
title: Add relay skill search with candidate eval
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/codebase
- coga/current-direction
- coga/project-stage
- dev/code
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
step: 1 (implement)
---

## Description

Build `relay skill search <query>` — the discovery + candidate-evaluation
front-end that the `bootstrap/import` pass (sibling
`add-bootstrap-skill-for-importing-external-skills`) currently does by hand.
Today Relay can *install* an external skill (`relay skill install-url` +
`.relay-source.json` provenance) but has no way to *find* one; discovery is
manual web/GitHub browsing. This ticket closes that gap.

Two parts, both required:

1. **Search** — given a capability query (e.g. "pytest failure reporting"),
   query external skill sources and return candidates, each carrying the fields
   `relay skill install-url` needs (source URL/repo, ref, the path-inside-repo
   selector) plus a short excerpt of the candidate's `SKILL.md` body. Sources:
   GitHub code search (`path:SKILL.md` + terms) at minimum; optionally a known
   registry index (OpenClaw/ClawHub, VoltAgent's awesome-skills list).
2. **Eval** — score/rank each candidate for *importability* against the
   `bootstrap/import` rubric: does the SKILL.md body actually match the need;
   is it small and focused vs. a broad "do everything" skill; does it hard-code
   commands/paths/tools that wouldn't apply. Output ranked candidates each with
   an `import` / `adapt` / `skip` recommendation and a one-line reason — not a
   raw search dump.

The command *proposes*; it does not auto-install. A human (or the import pass)
picks a candidate and runs `relay skill install-url`.

## Context

This is the concrete command that "Add a skill-import pass" explicitly
**deferred** (its `## Out of scope` notes a `relay skill search`/`import` flow
as future work) and that `detect-missing-skills` would *trigger* once a gap is
detected. Dependency order: provenance/install (already shipped) → this
search+eval → optional auto-wiring into the import pass.

Prior art: OpenClaw / ClawHub ships exactly this shape — a registry with a
`clawhub install <slug>` CLI over the same `SKILL.md` format. Relay deliberately
stays git-backed and local, so "search" here is most likely GitHub code search
via the `gh` CLI (already a Relay dependency for `gh skill install`) plus
optional web search, not a bespoke hosted registry.

Key code / surfaces:

- `src/relay/commands/skill.py` — the `relay skill` Typer app; add a `search`
  subcommand here next to `install` / `install-url` / `update` / `status`.
- `src/relay/skill_manager.py` — install/provenance logic the candidates must
  be compatible with (the `.relay-source.json` `relay.skill-source.v1` fields:
  `source_url`, `selector`, `installed_ref`, digests).
- Eval rubric to mechanize (the sibling ticket will formalize this in
  `relay-os/skills/bootstrap/import/SKILL.md`, but that file is committed on an
  unmerged branch and not yet on disk — so it is inlined here to keep this
  ticket self-contained and independently launchable):
  (a) the candidate's `SKILL.md` *body* matches the query intent, not just its
  title; (b) it is small and focused, not a broad "do-everything" skill;
  (c) it does not hard-code commands/paths/tools that wouldn't transfer to this
  repo. Map the verdict to `import` / `adapt` / `skip`.

Open design questions for the interview:

- **Eval engine**: deterministic heuristic (keyword/size/command-pattern
  checks) vs. an AI judgment the agent runs vs. both? An AI judge is more
  accurate but makes `relay skill search` non-deterministic and network-bound.
- **Sources**: GitHub-only for v1, or also a registry index? Registries have no
  single stable API — decide whether to depend on one.
- **Output shape**: human table vs. `--json` for the import pass to consume.

## Out of scope

- Auto-installation / auto-wiring into the `bootstrap/import` pass — this
  command only proposes; `relay skill install-url` stays the install path
  (sibling `add-bootstrap-skill-for-importing-external-skills`).
- Capability-gap *detection* that triggers a search — owned by
  `detect-missing-skills`.

## Acceptance criteria

- [ ] `relay skill search <query>` exists as a subcommand of the `relay skill`
      app and returns candidates rather than erroring on "no search".
- [ ] Each candidate carries the fields needed to hand off to
      `relay skill install-url` (source URL, ref, selector) plus a SKILL.md
      excerpt.
- [ ] Candidates are evaluated/ranked with an explicit
      `import` / `adapt` / `skip` recommendation and a one-line reason, applying
      the `bootstrap/import` rubric (reject broad / command-baked skills).
- [ ] The command proposes only — it does not install. (Install stays
      `relay skill install-url`.)
- [ ] `relay skill search` is read-only: no install, no filesystem writes, no
      git/`gh` mutating calls. It degrades gracefully (clear error, non-zero
      exit, no crash) when `gh` is unauthenticated or offline, and caps the
      number of candidates fetched.
- [ ] The eval-engine decision (heuristic vs. AI vs. both) and the
      source/v1-scope decision are recorded in this ticket's blackboard.
- [ ] Focused tests cover the search parse + the eval ranking, with the
      network/`gh` call mocked (no live network in tests).
- [ ] `python -m pytest` and `relay validate --json` are green.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
