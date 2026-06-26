---
slug: marketing/readme-and-docs
title: README + vision.md editorial pass
status: in_progress
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts:
- marketing/positioning
- coga/principles
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
step: 2 (review-design)
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
- One source of install truth in the README — no duplicated install commands;
  `## Development` references Getting Started for install and keeps only the
  dev-only commands (`python -m pytest`, `relay validate`).
- A one-line cross-reference distinguishes the Getting Started first-run path
  (`relay build`) from `relay ticket` (ongoing authoring); the existing
  `## Task lifecycle` and `relay ticket` boot-sequence sections are not rewritten.
- `relay digest` and `relay validate` each have a reference entry; the README
  states the license as `AGPL-3.0-or-later` (matching `pyproject.toml` and
  `docs/vision.md`).
- `## External CLI Tools` accurately describes the `gh` / `gh skill` requirement
  (available in recent `gh` as a preview) — no "once those commands land," and no
  stale "hand-edit `user =` / run `relay ticket` first" steps.
- `docs/vision.md`: correct repo URL, no "six-command" claim, no `[FILL IN]`
  placeholder, and no quantified-improvement claim (the ~3x idea is dropped as
  inventor's bias).
- Nothing re-pitches the product; voice stays consistent with `relay/principles`.
- Lands as a PR.

## Proposed Shape

**README.md — top-of-file structure:**
1. `# Relay` + intro — tightened (the dense ~35-line intro trimmed, framing intact).
2. **`## Getting Started`** (new) — fresh-directory happy path: install once
   (`git clone` source + `pip install -e .`), then per project `mkdir` + `git
   init` + `relay init --user <name>` + `relay build` + `relay launch <slug>`;
   a short "what you end up with" + pointers (`relay chat`, `relay ticket`,
   `relay status`, `relay --help`). Include a one-line cross-reference
   distinguishing this first-run greenfield path (`relay build` → onboarding
   chat → a batch of draft tickets) from `relay ticket` (ongoing task
   authoring), so the existing `## Task lifecycle` normal path and the
   `relay ticket` "usual boot sequence" stay un-rewritten but a newcomer knows
   which path is which.
3. Install handling — Getting Started *replaces* the standalone `## Install`
   outright. The operator-only nuance (vendored `.relay/` copy, "one relay-os/
   per repo" / global-vs-vendored) moves to a new short `## Operating notes`
   block (~4-5 lines) below Getting Started. Also de-duplicate `## Development`:
   drop its own `git clone` + `pip install -e .` lines, point back to Getting
   Started for install, and keep only the dev-only commands (`python -m pytest`,
   `relay validate --json`, `relay validate --fix`). Net: exactly one install
   source in the file.
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
9. `[FILL IN WITH REAL NUMBERS]` (~L246) → remove the quantified-improvement
   claim entirely (flagged as inventor's bias). Delete the `[FILL IN]` line and
   the surrounding metric claim; no number, directional or otherwise. Keep the
   team-composition framing already in the doc.

## Out of Scope

- `docs/design.md`, `docs/market-thesis.md`, `docs/competition/*`.
- Splitting the CLI reference into a separate file (cuts against "one obvious file").
- Code fixes for the silent no-git skip and the noisy skill failures — their own
  tickets; here we only document current behavior accurately.
- Changing `relay ticket` / `relay create` behavior — that's
  `marketing/relay-ticket-creates`; this pass documents today's behavior.
- The one-line installer.

## Decisions

- Getting Started fully replaces `## Install`. The operator nuance (vendored
  `.relay/` copy, one-`relay-os`-per-repo / global-vs-vendored) lives in a short
  `## Operating notes` block below Getting Started.
- The ~3x / quantified-improvement claim is dropped entirely (inventor's bias) —
  the `[FILL IN]` line is removed, with no number replacing it.
- The README does not touch the "optional skills skipped" noise — that's left to
  `quiet-relay-init-managed-skill-failures`.
- Install de-duplication includes `## Development`: it references Getting Started
  rather than repeating `git clone` + `pip install -e .`, so there is one install
  source. (Decided with zach 2026-06-20, design step.)
- The new onboarding narratives are not consolidated — Getting Started is
  additive and gets a single cross-reference line vs. `relay ticket`; the
  existing `## Task lifecycle` and `relay ticket` boot sequence are left intact.
  (Decided with zach 2026-06-20, design step.)
- License string is the precise SPDX `AGPL-3.0-or-later`, not a bare `AGPL-3.0`.

<!-- coga:blackboard -->

# Blackboard — readme-and-docs

## Design step (2026-06-20) — verification log

The ticket arrived already carrying a full spec (Description / AC / Proposed
Shape / Out of Scope / Decisions). The design step's job here was to verify
that spec against real CLI behavior, refine the gaps, and surface decisions —
not author from scratch. All claims were ground-truthed against the
`~/Desktop/relay-cli` checkout (the `relay` on PATH runs this source).

Confirmed real / accurate:

- `relay init --user <name>` — required for a fresh init (`relay init --help`).
  Seeds `tasks/relay-build/` onboarding ticket, stamps `new-user` →
  `<name>` on owner/human/assignee, prunes it on a non-empty repo
  (`src/relay/commands/init.py`, `_ONBOARDING_TICKET_DIRS = ("relay-build",)`).
- `relay build` = alias → `relay launch relay-build` (`relay.toml` `[aliases]`).
  Launches the `build/onboarding` workflow (`gather-and-spec` →
  `generate-batch`): one scripted question → agent chat → vision written to
  `contexts/product/vision/SKILL.md` + a batch of draft tickets → `relay launch
  <slug>`. So `init --user → build → launch` does land a newcomer on a
  launchable ticket — the stated Win holds.
- `relay digest` exists (flags `--quiet-empty` / `--announce-empty`); no README
  entry today. `relay validate` exists (`--json`, `--task`, `--fix`,
  `--idle-hours`, `--max-blackboard-kb`, `--check-slack`, `--check-github`);
  also no dedicated README entry.
- License = `AGPL-3.0-or-later` (`pyproject.toml`, `LICENSE` present).
- vision.md stale items at the specced lines: repo URL `relay-dev/relay` (L14),
  "six-command CLI" (L22), `[FILL IN WITH REAL NUMBERS]` (L246).
- README stale items: hand-edit `user =` / `relay ticket "First task"` block
  (L133-139); `gh skill` "once those commands land" (L100) — contradicted by
  the README's own `### relay skill` section, which treats `gh skill` as a
  shipped public preview.

## Resolved questions (answered by zach, in-session)

1. **Install duplication.** `## Development` (L772-781) also has `git clone` +
   `pip install -e .`, so "one source of install truth" was not fully covered.
   → **Decision: Dev references Getting Started**, keeps only dev-only commands.
   Folded into AC + Proposed Shape item 3.
2. **Three onboarding narratives.** Getting Started (`init→build→launch`) vs the
   existing `## Task lifecycle` path and `relay ticket` "usual boot sequence",
   both centered on `relay ticket`.
   → **Decision: light cross-reference** — one line distinguishing them; do not
   rewrite those sections. Folded into AC + Proposed Shape item 2.

No open questions remain. Spec is ready for `review-design`.

## Clean-room test of Getting Started (2026-06-20)

Ran the Getting Started happy path in an isolated clean-room (fresh `git clone`
+ a brand-new venv + `pip install -e .`, then a fresh `git init` project with a
throwaway local remote — never the real GitHub/Slack). Reusable harness lives at
`/tmp/relay-cleanroom/` (`setup.sh` rebuilds the install layer; `reset.sh` wipes
the project back to pristine for another run). Install (`relay 0.2.0`),
`relay init --user`, and the `build`/`launch` wiring (`--prompt-report`) all pass.
Four findings surfaced — flagged by whether they're in-scope **doc** edits or
sibling-ticket **code** bugs:

1. **`git init` → `master`, but relay syncs to `main` (highest impact).** Step 2's
   plain `git init` makes a `master` branch (machine default); `[git].control_branch`
   defaults to `main`, so every mutating command fails its sync but still exits 0:
   `relay create … → [git] sync failed: 'git fetch origin main' (exit 128): couldn't
   find remote ref main`. Work stays local, never reaches the remote — easy to miss.
   Dents the AC ("newcomer reaches a launchable ticket"). **Doc:** change step 2 to
   `git init -b main`. **Code (sibling):** relay should detect the repo's branch.
2. **`relay init` prints 5 managed-skill failures.** `Managed skills: failed=5,
   installed=7`; all 404 against `FastJVM/relay-skills` (repo doesn't resolve), e.g.
   `relay/gmail`, `relay/google-calendar`, `browser/playwright`. Fires for everyone,
   not just "older gh". **Doc:** the new `## External CLI Tools` line ("a fresh
   `relay init` on an older `gh` just skips them with a warning") misattributes the
   cause and undersells the noise — retarget it. **Code:** `quiet-relay-init-managed-skill-failures`.
3. **A `browser-automation` draft ships in the templates.** Every fresh init seeds
   it (+ browser contexts + a workflow) under `resources/templates/relay-os/tasks/`,
   so `relay status` shows a ticket the newcomer never authored — before `build`
   even runs. Muddies "launch your first ticket — which slug?". **Doc (optional):**
   "What you end up with" implies the drafts come from `relay build`. **Code:** remove
   the example from templates.
4. **`relay --version` errors inside the cloned source repo (low).** Natural
   post-install check while still `cd`'d in `relay/`: `'user' is missing from
   …/relay.local.toml` (a gitignored file that isn't there). Works from any
   non-`relay-os/` dir. Happy path dodges it (step 2 moves away). Minor; likely no
   doc change.
