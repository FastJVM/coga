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
fix the concrete stale/wrong items in the Context below and tighten readability,
without changing what Relay *is* or re-pitching it. Scope is exactly these two
files — `docs/design.md`, `market-thesis.md`, `competition/*` are out of scope.
**Win:** a newcomer follows Getting Started start-to-finish to a launchable
ticket, and both files are correct and consistent with `relay/principles`.

## Context

Preserve Relay's voice and canonical claims — `relay/principles` is canon when
the README/vision narrative diverges from it; this corrects drift, it does not
re-pitch.

**Getting Started (new README section)**
- The flow to teach (fresh-directory path): install the CLI (`git clone` source
  + `pip install -e .`), then `mkdir` a new dir + `git init`, `relay init --user
  <name>`, `relay build` (one scripted question + agent-led chat → first batch of
  draft tickets), `relay launch <slug>`. Ground every command in real behavior
  (`relay --help`, `relay/architecture`) — don't invent.
- Intended shape (pending Nicolas): one `## Getting Started` section that
  *replaces* the separate `## Install` — not two install sections. Install's
  reference nuance (vendored `.relay/` copy, the multi-repo "one relay-os/ per
  repo" operator pattern) either folds in or moves to a trimmed reference below.
- Onboarding enablers (shipped): `relay build` (replaced the relay-setup
  interview), the `relay setup` → `relay build` rename, `relay init --user`, init
  auto-seeding the onboarding ticket + surfacing `relay build`, `relay launch`
  activating a draft. Still open: `relay ticket` create-and-build
  (`marketing/relay-ticket-creates`); `relay init` does **not** `git init` an
  empty dir — silent skip (`marketing/relay-init-git-inits-a-fresh-dir`).

**README.md — objective fixes**
- Missing reference entries for `relay digest` and `relay validate` (the Commands
  section claims "one entry per command"; these two have none).
- No License section — repo is AGPL-3.0 (`LICENSE`); README never states it.
- Install copy (Nicolas's review): use a placeholder path, not hardcoded
  `~/work/admin`/`~/work/code`; drop the `pip install -e .` "puts relay on your
  PATH" gloss (engineers know editable installs); keep "not on PyPI yet" but
  state it plainly. Bug: current `relay init <path>` examples omit the
  now-required `--user` and error as written.

**docs/vision.md — objective fixes**
- Wrong repo URL (~line 14): `github.com/relay-dev/relay` → `github.com/FastJVM/relay`.
- Stale "six-command CLI" claim (~line 22; actual ~18). Reframe non-numerically
  ("a small CLI"). **Edit line 22 surgically** — "six" recurs innocently
  elsewhere ("six months"); do NOT find-replace "six".
- Unfilled `[FILL IN WITH REAL NUMBERS]` placeholder (~line 246). Owner figure
  (2026-06-08): ~**3x more productive** (PR throughput / task units / cost), but
  the data is confidential and hard to extract precisely. Write as an honest
  *directional* claim — not a fabricated metrics table; be upfront that exact
  figures aren't published. Reuse the team-composition framing already in the
  doc; don't invent precise metrics.

**Editorial (judgment)**
- Tighten the dense ~35-line README intro; fix any other stale flags/cross-refs
  found while editing. Keep the principles-driven framing. Out of scope:
  splitting the CLI reference into a separate file (cuts against "one obvious
  file") — README stays the single reference.
