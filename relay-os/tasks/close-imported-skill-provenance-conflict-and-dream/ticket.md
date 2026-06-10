---
title: Close imported-skill provenance and conflict gaps
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/codebase
- relay/project-stage
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

Close three remaining gaps in Relay's imported-skill update machinery — the
CLI/metadata/conflict layer. The bulk of the `relay skill` surface
(install/status/update/--all/--pr, provenance read/write, tree hashing)
already shipped in PR #143 and follow-ups; this ticket finishes the parts of
the original `add-imported-skill-update-check` spec that #143 left partial.

The fourth gap from the audit — the Dream skill-update maintenance phase — is
split into its own ticket (`add-dream-skill-update-maintenance-phase`), since it is
template/worker-skill authoring rather than code+tests on the CLI surface.

The three gaps:

1. **Provenance metadata (partial).** `_url_metadata()` in
   `src/relay/skill_manager.py` writes source/selector/ref/digests/dates but
   has no `local_adaptation_notes` field. Add it (init empty) and preserve
   it across `relay skill update` so a human's note is never silently wiped.

2. **Dirty-overwrite refusal (missing).** `install_url_skill` overwrites an
   existing skill via `gh skill install --from-local` with no guard. Before
   overwriting, compare the current tree digest against the recorded
   `installed_tree_digest`; if they differ (locally adapted), refuse with a
   clear error unless a new `--force` flag is passed. Add `--force` to the
   **`install-url` command only** — it is the only install path with a Relay
   `installed_tree_digest` to compare against (the `gh`-backed `install` and
   `install-local` paths have no Relay digest, so a dirty guard is meaningless
   there). `--force` performs the overwrite and rewrites
   `installed_tree_digest` to the freshly installed tree; it does **not**
   attempt to preserve `local_adaptation_notes` (a forced overwrite discards
   the adaptation, so the note is reset to empty — preserving it would
   mis-describe the new tree).

3. **Real conflict report (partial).** `_update_url_skill_dir` skips a
   locally-adapted skill as `skipped-local-adaptation` *before* fetching
   upstream, so it can never distinguish benign local-only edits from a true
   conflict. Change it to still fetch upstream when locally adapted: if
   upstream is unchanged keep `skipped-local-adaptation`; if upstream also
   changed, return a new `conflict` status carrying both refs/digests in
   `details`. Surface `conflict` as its own section in `render_update_pr_body`.
   For vocabulary consistency, `_status_url_skill` (which has a parallel
   `locally-adapted` early-return) must use the same rule under `--check`:
   locally-adapted + upstream-changed reports `conflict`, not just
   `locally-adapted`. `status` and `update` must not report different
   vocabularies for the same on-disk state.

## Context

This is a follow-on to the draft `add-imported-skill-update-check`; that
ticket's task body holds the original full operating model. A deep audit of
the shipped #143 implementation produced the gap list above — requirements
1 (plain dirs), 4 (`status` states), 5 (`update <name>`), and 6
(`update --all` one-diff) are already SATISFIED and out of scope here.

Key files:
- `src/relay/skill_manager.py` — `_url_metadata`, `install_url_skill`,
  `_update_url_skill_dir`, `_status_url_skill`, `render_update_pr_body`.
- `src/relay/commands/skill.py` — the `install*` / `update` Typer commands.
- `tests/test_skill_manager.py` — extend for the conflict path, dirty-
  overwrite refusal, and notes-preservation.

Design defaults already chosen: flag name `--force` (not `--upgrade`);
`local_adaptation_notes` is hand-edited in `.relay-source.json` (no `--note`
flag), keeping the CLI surface small per `relay/project-stage`.

Out of scope: the already-satisfied requirements above; any rework of the
GitHub-backed (`gh skill`) path, which owns its own metadata.

## Acceptance Criteria

- `_url_metadata()` writes `local_adaptation_notes` (empty by default), and
  `relay skill update` preserves an existing note across a clean update.
- `relay skill install-url` refuses to overwrite a locally-adapted skill
  without `--force`, and succeeds with `--force` (resetting the digest/note as
  specified in gap 2).
- `relay skill update` returns the new `conflict` status (exact string
  `conflict`) when a skill is both locally adapted and upstream-changed;
  `skipped-local-adaptation` when locally adapted but upstream unchanged.
- `relay skill status --check` reports the same `conflict` vocabulary for the
  same on-disk state.
- `render_update_pr_body` renders a dedicated conflict section.
- New tests in `tests/test_skill_manager.py` cover: conflict path, dirty-
  overwrite refusal, notes-preservation, and the PR-body conflict section
  (mirror the existing `test_pr_body_lists_skipped_local_adaptations` shape).
- `python -m pytest` and `relay validate --json` are green.
