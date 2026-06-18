---
title: relay init must ship reusable workflows + code skills into new repos
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/architecture
- relay/codebase
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
step: 5 (review)
---

## Description

`relay init` should give a fresh repo the reusable Relay process library needed
for the normal code loop. Today the package resources already ship canonical
contexts and several core skills through the gitignored `bootstrap/` umbrella,
but the reusable code workflows and their `code/*` skills still live only in
this source checkout's git-tracked `relay-os/`. A new repo can therefore resolve
`relay/architecture`, `bootstrap/ticket`, and other bundled batteries, but it
cannot run `code/with-review`, `code/design-then-implement`, or
`dev/with-self-review` without hand-copying workflow and skill files.

The fix should make those reusable workflows package-backed, update-carried,
offline, inspectable, and locally overridable. Do not broad-copy every live
workflow into user space on update: top-level `relay-os/workflows/` is where a
repo's own playbooks belong. Package-owned reusable workflows should instead
use the same local-first fallback shape that contexts and skills already use:
local files override bundled files, and bundled files are refreshed under
`bootstrap/`.

## Acceptance Criteria

- A fresh `relay init` can create or activate tickets using these workflow refs
  without manual file copying: `code/with-review`,
  `code/design-then-implement`, `dev/with-self-review`,
  `docs/create-google-doc`, `dream/validate-drift`,
  `dream/cleanup-orphan-markers`, and `digest/post`.
- The fresh repo also contains every bundled skill those workflows require:
  `code/design`, `code/implement`, `code/implement-and-pr`,
  `code/open-pr`, `code/self-qa`, and `relay/digest/flush`. Those skills are
  visible through the generated `.agent-skills` view.
- Workflow loading is local-first: `relay-os/workflows/<ref>.md` wins when it
  exists; otherwise Relay falls back to
  `relay-os/bootstrap/workflows/<ref>.md`. Error messages and validation
  helpers report both checked paths, matching context and skill diagnostics.
- Guided authoring and diagnostic prompt surfaces that enumerate workflow
  options check both local `relay-os/workflows/` and bundled
  `relay-os/bootstrap/workflows/`, so `relay ticket` can recommend packaged
  workflows without copying them into user space.
- `relay init --update` refreshes the new bundled workflow and skill copies via
  the existing bootstrap mirror, and refreshes `recurring/digest/ticket.md`
  without overwriting that recurring template's per-repo `blackboard.md` or
  `log.md`.
- Existing top-level user workflows and skills are not wiped or overwritten by
  this change. A repo that deliberately copied `workflows/code/with-review.md`
  keeps that local override.
- The source checkout has a drift guard that compares the curated live files
  under `relay-os/` with the packaged copies under
  `src/relay/resources/templates/relay-os/bootstrap/`, so future edits fail
  tests if only one side changes.
- Tests cover fresh init, `init --update`, workflow fallback and local override
  behavior, package/wheel inclusion, and the curated live-vs-packaged parity
  check.
- The Relay architecture/codebase context text is updated so agents know that
  package-backed workflows now live under `bootstrap/workflows/` and resolve
  behind local `workflows/`.

## Proposed Shape

Add bundled workflow resolution rather than expanding the existing top-level
workflow update allowlist:

1. In `src/relay/paths.py`, add `bootstrap_workflow_path()`,
   `resolve_workflow_path()`, and `workflow_resolution_paths()`, mirroring the
   existing skill/context helpers.
2. Replace direct `Workflow.load(workflow_path(...))` call sites with the
   resolver wherever a workflow ref is frozen or loaded: `src/relay/create.py`,
   `src/relay/mark.py`, `src/relay/commands/bump.py`,
   `src/relay/compose.py`, and `src/relay/retrofit.py`. Inline step
   composition should use the resolved path when available and keep the current
   frozen-snapshot fallback when a workflow definition has disappeared.
3. Leave `workflow_path()` in place for the local authoring path and for
   messages that need to name the local override location.
4. Update workflow-related CLI/help/validation wording that currently points
   only at `relay-os/workflows/` so missing-workflow remedies and diagnostics
   name both local and bundled checked locations.

Package the curated reusable batteries under the existing bootstrap mirror:

1. Copy the reusable workflow files into
   `src/relay/resources/templates/relay-os/bootstrap/workflows/`:
   `code/{with-review,design-then-implement}.md`,
   `dev/with-self-review.md`, `docs/create-google-doc.md`,
   `dream/{validate-drift,cleanup-orphan-markers}.md`, and
   `digest/post.md`.
2. Copy `relay-os/skills/code/{design,implement,implement-and-pr,open-pr,self-qa}/`
   into
   `src/relay/resources/templates/relay-os/bootstrap/skills/code/`.
3. Ship the digest workflow as a complete battery, not a dangling workflow:
   copy `relay-os/skills/relay/digest/flush/` into
   `src/relay/resources/templates/relay-os/bootstrap/skills/relay/digest/flush/`,
   copy `relay-os/recurring/digest/` into the template tree, and add
   `recurring/digest/ticket.md` to `VENDORED_RECURRING_TEMPLATES` so
   `--update` restores the ticket body while preserving per-repo digest state.
4. Keep the already-shipped top-level workflow templates (`_template.md`,
   `browser/build-automation.md`, `autonomy/*`, `init/setup`,
   `direct/body`, `skill-update/run`, `autoclose-merged/sweep`) where they are.
   Do not move the browser example in this PR.

Use tests as the drift lock:

1. Extend `tests/test_init.py`'s fake package fixtures and expectations so
   fresh init and `init --update` materialize `bootstrap/workflows/...`,
   `bootstrap/skills/code/...`, `bootstrap/skills/relay/digest/flush/...`, and
   `recurring/digest/ticket.md`.
2. Add focused workflow-resolution tests showing that `relay create`/activation
   accepts a workflow found only under `bootstrap/workflows/`, and that a local
   `workflows/<ref>.md` overrides a bundled workflow with the same ref.
3. Extend `tests/test_packaging.py` so the wheel must contain representative
   bundled workflow and skill files. The existing bootstrap force-include should
   ship them, but the test should prove it.
4. Add a small parity test with an explicit curated mapping from live source
   files to packaged bootstrap files. Include the `code` workflows, `dev`,
   `docs`, the two Dream worker workflows, the digest workflow/skill, and the
   five `skills/code` entries. This is a test-local curation list, not a runtime
   manifest.
5. Run at least `python -m pytest tests/test_init.py tests/test_packaging.py`
   plus the new workflow-resolution/parity tests, then run
   `relay validate --task relay-cli-shipping --json`.

Update the behavioral docs in the same PR:

1. In `relay-os/contexts/relay/architecture/SKILL.md`, describe bundled
   workflows as package-backed batteries under `relay-os/bootstrap/workflows/`,
   resolved after local `relay-os/workflows/`.
2. Mirror that shipped architecture context change in
   `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/architecture/SKILL.md`.
3. In `relay-os/contexts/relay/codebase/SKILL.md`, update the layout/testing
   guidance to mention authoring packaged bootstrap workflows and skills under
   `src/relay/resources/templates/relay-os/bootstrap/`.
4. Update the packaged and materialized `bootstrap/ticket` and
   `eval/ticket-diagnostic` skills so their workflow-discovery instructions
   treat `relay-os/workflows/` as local overrides and
   `relay-os/bootstrap/workflows/` as bundled fallbacks.

## Out of Scope

- Do not ship source- or company-specific contexts such as
  `relay/codebase`, `relay/current-direction`, `relay/project-stage`,
  `relay/recurring`, or `marketing/*`.
- Do not rename the `workflow` primitive to `playbook`; that is tracked by a
  separate ticket.
- Do not ship internal or stale workflow files in this PR:
  `build/dry-run.md`, `test/relaunch-chain.md`, and
  `dream/skill-update.md`. The last one references a non-existent
  `bootstrap/dream/tasks/skill-update` skill and should not be exported until
  that Dream phase exists again.
- Do not replace the managed-skill installer with a manifest for these core
  code skills. The code loop must work offline from the Relay package.
- Do not overwrite user-authored top-level workflow or skill trees on update;
  bundled files are fallbacks unless a repo deliberately overrides them.
