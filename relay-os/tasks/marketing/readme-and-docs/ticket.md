---
title: README + vision.md editorial pass
status: active
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts:
- marketing/positioning
- relay/principles
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
step: "1 (design)"
---

## Description

An editorial pass over Relay's two public-facing docs — `README.md` and
`docs/vision.md`. Two goals: (1) the new-user **Getting Started** section in the
README — the shortest path from nothing to a running agent (install the CLI,
create a project, `relay init --user`, `relay build`, `relay launch`); and (2)
fix the concrete stale/wrong items below and tighten readability,
without changing what Relay *is* or re-pitching it. Scope is exactly these two
files — `docs/design.md`, `market-thesis.md`, `competition/*` are out of scope.
**Win:** a newcomer follows Getting Started start-to-finish to a launchable
ticket, and both files are correct and consistent with `relay/principles`.

## Context

- Preserve Relay's voice and canonical claims — `relay/principles` is canon when
  the README/vision narrative diverges from it; this corrects drift, it does not
  re-pitch.
- Ground every command description in real behavior (`relay --help`, the
  `relay/architecture` context) — don't invent. The Getting Started happy path
  was run end-to-end on a throwaway repo and works as written.
- Onboarding enablers (shipped): `relay build` (replaced the relay-setup
  interview), the `relay setup` → `relay build` rename, `relay init --user`, init
  auto-seeding the onboarding ticket + surfacing `relay build`, and `relay launch`
  activating a draft. Still open (`marketing/relay-ticket-creates`): `relay ticket`
  gains create-or-edit (create a ticket and author it, or edit an existing one)
  while `relay create` stays as the quick-stub path. So the README describes
  today's behavior — `relay create` makes a draft stub; `relay ticket` runs the
  guided authoring.
- Sibling CLI-bug tickets (out of scope here — document current behavior, don't
  fix the code): `marketing/relay-init-git-inits-a-fresh-dir` (init's silent
  no-git skip) and `marketing/quiet-relay-init-managed-skill-failures` (noisy
  optional-skill failures on older `gh`).

## Acceptance Criteria

- A newcomer copy-pastes Getting Started top-to-bottom and reaches a launchable
  ticket — every command correct, including `--user`. (Flow verified end-to-end.)
- One source of install truth in the README — no duplicated install commands.
- `relay digest` and `relay validate` each have a reference entry; the README
  states the license (AGPL-3.0).
- `## External CLI Tools` accurately describes the `gh` / `gh skill` requirement
  (available in recent `gh` as a preview) — no "once those commands land," and no
  stale "hand-edit `user =` / run `relay ticket` first" steps.
- `docs/vision.md`: correct repo URL, no "six-command" claim, no `[FILL IN]`
  placeholder.
- Nothing re-pitches the product; voice stays consistent with `relay/principles`.
- Lands as a PR.

## Proposed Shape

**README.md — top-of-file structure:**
1. `# Relay` + intro — tightened (the dense ~35-line intro trimmed, framing intact).
2. **`## Getting Started`** (new) — fresh-directory happy path: install once
   (`git clone` source + `pip install -e .`), then per project `mkdir` + `git
   init` + `relay init --user <name>` + `relay build` + `relay launch <slug>`;
   a short "what you end up with" + pointers (`relay chat`, `relay ticket`,
   `relay status`, `relay --help`).
3. Install handling — Getting Started *replaces* the standalone `## Install`; the
   operator-only nuance (vendored `.relay/` copy, multi-repo "one relay-os/ per
   repo") folds in as a short note or trims to a reference block (see Open Questions).
4. `## External CLI Tools` — delete the stale first-steps lines (hand-edit
   `user =`, `relay ticket "First task"`); fix the `gh skill` line to say it's
   available in recent `gh` as a preview, and that managed skills are optional
   (a fresh init on older `gh` just skips them).
5. `## Commands` — add `### relay digest` and `### relay validate` (with flags) in
   the one-screen-per-command style.
6. **`## License`** (new) — AGPL-3.0.

**docs/vision.md — surgical fixes:**
7. Repo URL (~L14): `relay-dev/relay` → `FastJVM/relay`.
8. "six-command CLI" (~L22) → non-numeric ("a small CLI"); edit that line only —
   "six" recurs innocently elsewhere ("six months"), so don't find-replace it.
9. `[FILL IN WITH REAL NUMBERS]` (~L246) → honest directional **~3x** (PR
   throughput / task units / cost); no fabricated metrics table; be upfront exact
   figures aren't published; reuse the team-composition framing already in the doc.

## Out of Scope

- `docs/design.md`, `docs/market-thesis.md`, `docs/competition/*`.
- Splitting the CLI reference into a separate file (cuts against "one obvious file").
- Code fixes for the silent no-git skip and the noisy skill failures — their own
  tickets; here we only document current behavior accurately.
- Changing `relay ticket` / `relay create` behavior — that's
  `marketing/relay-ticket-creates`; this pass documents today's behavior.
- The one-line installer.

## Open Questions

- Does Getting Started fully replace `## Install`, or sit above a trimmed Install
  reference — and where does the operator nuance (vendored copy, multi-repo) live?
- Final phrasing of the ~3x claim (owner call).
- Should the README pre-empt the "optional skills skipped" noise, or leave that
  entirely to `quiet-relay-init-managed-skill-failures`? (Lean: CLI ticket's job.)
