---
title: Remove the shim concept
status: in_progress
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
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
secrets: null
step: 2 (review-design)
---

## Description

**Remove the "shim" concept from Relay entirely** — don't rename it. The
stateless launch-targets under `relay-os/bootstrap/<name>/` (orient, ticket,
project) are just **tickets**; describe and name them as such. **Delete the
"tier-2 shim"** idea from the extension model — there is no separate launcher
category. After this, the model is the three existing homes — **kernel,
tickets, external-tools** — with **aliases as sugar** (not a home). This is the
foundation for the broader "move things out of core into tickets" program and
must land before `move-read-views` and the extraction tickets. **Behavior does
not change here** — this is a model + vocabulary cleanup, not a command move.

## Context

The plan evolved: Nico first asked to rename "shim" → "alias," but `alias`
already means the argv-rewrite sugar (a distinct concept), and on reflection
"shim" shouldn't exist at all — these things are tickets. So we **delete the
concept** rather than rename it.

**Taxonomy is unchanged — just purified.** Keep `extension-model`'s three homes
(kernel / tickets / external-tools) and alias-as-sugar. "shim" and "tier-2
shim" were non-conforming extras: a bootstrap launch-target is a *ticket*; a
read-view "script shim" is a *ticket* (tickets-as-scripts); "tier-2 shim" was a
proposed fourth mechanism that shouldn't exist (ticket-authoring is just a
ticket — implemented for real by `move-ticket-authoring-out-of-core`).

**`design` step output (for `review-design`, get Nico's sign-off):** the
reworded `extension-model` / `architecture` / `cli-extension-audit` passages
(this is the model *contract*) plus the full rename inventory.

**Carve-outs — these "shim" uses are NOT the concept; plain English or leave:**
- Install symlink (`~/.local/bin/relay`) → "symlink"/"wrapper":
  `src/relay/commands/uninstall.py`, `init.py` (`_relay_shim`,
  `_try_install_shim`).
- Import-compat layer → "compatibility layer": `src/relay/slack.py:1`.
- Deprecation sense → keep "shim" / "deprecation stub":
  `relay-os/contexts/relay/project-stage/SKILL.md:28`.
- `skill-shim` historical field name (`src/relay/commands/launch.py:516`,
  tests) → leave.

**The two docs that contrast shim-vs-alias** (`extension-model/SKILL.md`,
`docs/cli-extension-audit.md`) become *ticket*-vs-alias — reword, don't
blind-replace.

**Worklist — the default `grep` HIDES files.** The live `relay-os/bootstrap/`
tree is gitignored, so use a gitignore-blind sweep:
`/usr/bin/grep -rIl "shim" . | grep -v "/.git/" | grep -v "/.venv/" | grep -v "/.relay/" | grep -v "/.pytest_cache/" | grep -v "relay-os/tasks/"`
(~37 files). Sync all three copies: live top-level, live `relay-os/bootstrap/`
(gitignored), and packaged `src/relay/resources/templates/relay-os/bootstrap/`.
Code identifiers are in scope (`DISCUSSION_BOOTSTRAP_SHIMS` → `…TICKETS`,
`shim_ticket`, …). Keep `python -m pytest` green.

**Related:** PR 425 is being closed (its `ticket.py` extraction premise is
redone as `move-ticket-authoring-out-of-core`). This ticket only removes the
concept; it moves no command.

## Acceptance Criteria

- [ ] No "shim" referring to the bootstrap launch-target / read-view concept
  remains anywhere in the worklist, **except** the four carve-outs (Out of
  Scope). Verify: the gitignore-blind sweep returns only carve-out hits.
- [ ] "tier-2 shim" and "tier-2 residue" appear nowhere as a named mechanism.
  `extension-model/SKILL.md` and `docs/cli-extension-audit.md` describe exactly
  **three homes** (kernel / tickets / external) **+ aliases as sugar** — no
  fourth launcher category.
- [ ] The "No worse Typer" guardrail is retained in `extension-model/SKILL.md`
  with its substance intact (no transient launch params; no `relay.toml` config
  DSL; branching → a skill), rephrased around the `arg → draft+workflow →
  launch` authoring shape rather than a named "tier-2 shim".
- [ ] The `extension-model` and `cli-extension-audit` contrasts read as
  *ticket*-vs-alias (not shim-vs-alias); the bootstrap launch targets are
  described and named as **bootstrap tickets** / **stateless launch targets**.
- [ ] Code identifiers renamed: `DISCUSSION_BOOTSTRAP_SHIMS` →
  `DISCUSSION_BOOTSTRAP_TICKETS` (`launch.py`); local `shim_ticket` →
  `bootstrap_ticket` (`project.py`).
- [ ] Every shared artifact is updated **identically across the three trees**
  (top-level live `relay-os/`, gitignored live `relay-os/bootstrap/`, packaged
  `src/relay/resources/templates/relay-os/bootstrap/`). Pre-existing drift in
  the `architecture` (3 copies) and `cli` (2 copies) contexts is harmonized to
  identical text.
- [ ] Carve-outs untouched (see Out of Scope).
- [ ] No behavior change: `relay launch bootstrap/<name>`, `relay chat`,
  `relay ticket`, `relay project` resolve and run exactly as before.
- [ ] `python -m pytest` green; `relay validate --json` clean.

## Proposed Shape

### Naming
- **Prose:** "shim" (the concept) → **bootstrap ticket** (noun), with
  **stateless launch target** as the descriptive gloss. `architecture/SKILL.md`
  already uses "stateless launch targets".
- **Code:** `DISCUSSION_BOOTSTRAP_SHIMS` → `DISCUSSION_BOOTSTRAP_TICKETS`;
  `shim_ticket` → `bootstrap_ticket`.

### Model-contract rewordings (the `review-design` sign-off surface)
Concrete before→after for the load-bearing lines; apply the same
shim→bootstrap-ticket reword to surrounding prose in each file.

**`relay-os/contexts/relay/extension-model/SKILL.md`**
- frontmatter `description:` — drop "or a shim" from "before adding a command,
  an alias, or a shim".
- Tickets-row table cell: `fused, pending tier-2: ticket, project, retire` →
  `fused, authoring moving to tickets: ticket, project, retire`.
- "the tier-2 shim work (`arg → draft` …)" → "ticket-authoring commands work
  (`arg → draft` …)".
- External-script home: "sibling of the tier-2 shim" → drop the tier-2
  reference; name the external-script home directly.
- **"No worse Typer" guardrail (decided — keep substance, drop the name):**
  > Do not add transient launch-time parameters, and do not let an
  > `arg → create-draft-with-workflow → launch` authoring command grow past
  > that single fixed shape. Conditionals, computed args, types, or validation
  > in `relay.toml` rebuild Typer worse and in TOML — an illegible config DSL
  > that violates the legibility non-negotiable (`relay/principles`). Branching
  > logic belongs in a skill.
- Pass 2: "read views → stateless script shims" → "stateless script tickets
  (tickets-as-scripts)"; "collapses the `arg → draft` heads … onto the
  **tier-2 shim** built there (its one new mechanism)" → "moves ticket-authoring
  (`ticket`/`project`/`retire`) into tickets via
  `move-ticket-authoring-out-of-core`; no new launcher mechanism is introduced".

**`docs/cli-extension-audit.md`**
- mechanism-3 bullet "**Launch shims / recurring launches** … (stateless
  shims)" → "**Bootstrap launch tickets / recurring launches** … (stateless
  launch targets)".
- "### Bootstrap shims" heading, the "| Shim |" table column, "Only
  `orient`, `project`, `ticket` are shims", "No un-aliased shim passthrough
  remains" → bootstrap-launch-ticket wording.
- "the **tier-2 residue**. When the **tier-2 shim** exists, `ticket` collapses
  to a shim + a mixed workflow" → "the `arg → draft` head is irreducible;
  moving authoring into a ticket (`move-ticket-authoring-out-of-core`) collapses
  `ticket` to that head + a mixed workflow with zero hand-written command
  logic".
- Guardrail mention of "the tier-2 shim stays the single fixed shape" → mirror
  the extension-model rephrasing.

**`relay-os/contexts/relay/architecture/SKILL.md`** (+ live-bootstrap + packaged)
- "**Bootstrap shims** in …" → "**Bootstrap tickets** in …"; "launch shims
  materialized under `relay-os/bootstrap/`" → "launch targets …";
  "bootstrap/discussion shims" → "bootstrap/discussion tickets". Harmonize the
  "creates"/"scaffolds" drift to "creates" (do not reintroduce "scaffold").

### Mechanical sweep (concept reword)
Source of truth for the file set — the gitignore-blind sweep (the default
`grep` hides the gitignored live bootstrap tree):

```
/usr/bin/grep -rIl "shim" . | grep -v "/.git/" | grep -v "/.venv/" \
  | grep -v "/.relay/" | grep -v "/.pytest_cache/" | grep -v "relay-os/tasks/"
```

Grouped worklist:
- **Battery contexts (sync all copies):** `architecture` (top-level + live
  bootstrap + packaged = 3 copies), `cli` (live bootstrap + packaged = 2 copies
  — there is **no** top-level `cli` copy; do not create one).
- **Project-local contexts (1 copy):** `extension-model`, `codebase`,
  `project-stage` (leave the deprecation line — carve-out).
- **Bootstrap tickets (live + packaged):** `orient/ticket.md`,
  `ticket/ticket.md`, `project/ticket.md`, `skills/bootstrap/ticket/SKILL.md`.
- **Docs:** `README.md`, `docs/design.md`, `docs/cli-extension-audit.md`
  (`docs/cli-extension-external-surface.md` is the compat-shim carve-out —
  leave).
- **Config:** `relay-os/relay.toml:145` ("bootstrap-shim launches" →
  "bootstrap-ticket launches").
- **Code comments/docstrings:** `tasks.py` (64/248/261), `ticket.py:150`,
  `launch.py` (11/73/466/548/733; **keep** the `skill-shim` field-name mention
  near 470), `project.py:59`, `show.py:36`, `update.py` (288/865), `init.py:67`
  (concept comment only — NOT the install-symlink lines).
- **Code identifiers:** `launch.py` `DISCUSSION_BOOTSTRAP_SHIMS`; `project.py`
  `shim_ticket`.
- **Tests:** reword concept strings/fixtures (`test_create.py`
  `repo_with_shim` / "Persistent launch shim", `test_git.py`, `test_launch.py`,
  `test_project.py`, `test_ticket.py`, `test_init.py` "bootstrap shim"
  strings). Leave `test_uninstall.py` and the `conftest.py` /
  `test_init.py` `_try_install_shim` symlink references. No test references the
  renamed identifiers, so the renames don't cascade.

### Order of work
1. Contract docs first (`extension-model`, `cli-extension-audit`,
   `architecture` ×3) — get the model right before the mechanical churn.
2. Mechanical sweep: bootstrap tickets, docs, `relay.toml`, code comments.
3. Code identifier renames; run `python -m pytest`.
4. Re-run the gitignore-blind sweep — confirm only carve-outs remain; then
   `relay validate --json`.

## Out of Scope

- **Carve-outs (leave exactly as-is):**
  - Install symlink (`~/.local/bin/relay`): `init.py` `_try_install_shim` /
    `_relay_shim` and lines 359/402-403/408, all of `uninstall.py`, and
    `test_uninstall.py` / `conftest.py` / `test_init.py` symlink references.
  - Import-compat layer: `src/relay/slack.py:1`.
  - Deprecation sense: `relay-os/contexts/relay/project-stage/SKILL.md:28` and
    the compat-shim language in `docs/cli-extension-external-surface.md`.
  - `skill-shim` historical field name (`launch.py` ~470, tests).
- **No behavior change and no command move.** Relocating `ticket`/`project`/
  `retire` authoring or the read-views into tickets is
  `move-ticket-authoring-out-of-core` / `move-read-views` — not this ticket.
- **`.relay/` vendored CLI** (init-managed, gitignored) and the stale
  `__pycache__/shim*.pyc` from the already-deleted `shim.py` command — not
  edited.
- **Broader "scaffold" term cleanup** beyond lines already being reworded for
  "shim".
- **Unrelated doc drift** (e.g. the `relay/cli` Aliases section listing only
  `chat` + `dream`) — separate follow-up noted in the audit.
