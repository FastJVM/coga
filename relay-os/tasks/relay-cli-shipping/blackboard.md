The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: ship-bootstrap-workflows
worktree: ../relay-ship-workflows (off main @ 8067e2e)
pr: https://github.com/FastJVM/relay/pull/387

### Implementation plan (implement step, 2026-06-17)

Local-first `bootstrap/workflows/` fallback, mirroring the existing skill/context
resolution model.

1. `src/relay/paths.py`: add `bootstrap_workflow_path`, `resolve_workflow_path`
   (local → bundled → local-fallback so not-found errors name the conventional
   location), and `workflow_resolution_paths`. Export them.
2. Repoint `Workflow.load(workflow_path(...))` callsites at `resolve_workflow_path`:
   `compose.py`, `create.py`, `mark.py`, `bump.py`, `retrofit.py`.
3. Bundle source under `src/relay/resources/templates/relay-os/bootstrap/`:
   - `workflows/`: code/with-review, code/design-then-implement,
     dev/with-self-review, docs/create-google-doc, dream/cleanup-orphan-markers,
     dream/validate-drift, digest/post.
   - `skills/code/{design,implement,open-pr,self-qa}` (copied from live skills).
   - digest battery: `skills/relay/digest/flush` (+ run.py) and add
     `recurring/digest/ticket.md` to `VENDORED_RECURRING_TEMPLATES`.
   New files under templates `bootstrap/` are gitignored there → `git add -f`.
4. Prompt surfaces: `bootstrap/ticket` + `eval/ticket-diagnostic` SKILL.md mention
   `relay-os/bootstrap/workflows/` alongside `relay-os/workflows/`.
5. Tests for the fallback + example fixture if affected.

Excluded (per design): dream/skill-update (dangling skill ref), test/relaunch-chain,
build/dry-run (internal probes).

### Implementation result (committed 29f8c4c)

Done on branch `ship-bootstrap-workflows` (worktree `../relay-ship-workflows`).

- `paths.py`: added `bootstrap_workflow_path` + `resolve_workflow_path`
  (local → bundled → local-fallback). Did NOT add a `workflow_resolution_paths`
  helper — it would have been dead code (workflow not-found errors name the
  conventional `workflows/` path directly, unlike skills/contexts which use
  their resolution-paths helpers in "checked: …" messages).
- Repointed `Workflow.load(...)` callsites: compose, create, mark, bump, retrofit.
- Bundled under templates `bootstrap/workflows/`: code/with-review,
  code/design-then-implement, dev/with-self-review, docs/create-google-doc,
  dream/cleanup-orphan-markers, dream/validate-drift, digest/post.
- Bundled skills under templates `bootstrap/skills/`: code/{design,implement,
  open-pr,self-qa} and relay/digest/flush (+ run.py).
- Digest battery: packaged `recurring/digest/{ticket.md, blackboard.md (clean
  seed — NO live spool state), log.md (empty)}` and added
  `recurring/digest/ticket.md` to `VENDORED_RECURRING_TEMPLATES`.
- Prompt surfaces updated: bootstrap/ticket, eval/ticket-diagnostic, and the
  architecture (both bundled + live override) and codebase contexts.
- New bootstrap template files force-added (`git add -f`) — templates
  `.gitignore` ignores `bootstrap/`; the wheel ships them via the existing
  bootstrap force-include. Verified present in a built wheel.

Verification: full suite 777 passed / 1 skipped; packaging wheel-build test
passes (hatchling installed in a throwaway venv) with new files asserted;
`relay validate --json` clean on example fixture; bootstrap-only repo layout
resolves + freezes all 7 shipped workflows with every step skill resolving.

## Design Notes

Investigated on 2026-06-17 during the `design` step.

- Fresh init copies the packaged template tree from
  `src/relay/resources/templates/relay-os/`. `relay init --update` refreshes
  `bootstrap/` wholesale through `_copy_vendored_bootstrap()` and refreshes a
  narrow set of top-level recurring/workflow/skill templates through
  `VENDORED_*_TEMPLATES`.
- Current packaged workflows are not as sparse as the original ticket text:
  templates already include `_template`, `browser/build-automation`,
  `autonomy/*`, `init/setup`, `direct/body`, `skill-update/run`, and
  `autoclose-merged/sweep`.
- The release-blocking gap is still real: `code/*`, `dev/with-self-review`,
  `docs/create-google-doc`, the Dream child workflows, `digest/post`, and
  `skills/code/*` live only in the source checkout's `relay-os/` tree.
- Broad-copying top-level workflows on update would violate the current
  ownership split in `update.py`, where most named workflows are treated as
  repo-owned playbooks. The proposed spec instead adds a bundled
  `bootstrap/workflows/` fallback, matching the existing local-first skill and
  context model.
- `digest/post` is only safe to ship together with its dependencies:
  `relay/digest/flush` and `recurring/digest/ticket.md`. Shipping the workflow
  alone would create a fresh-install broken-skill failure.
- `dream/skill-update.md` should not ship in this PR. It references
  `bootstrap/dream/tasks/skill-update`, which is not present in the packaged or
  live bootstrap Dream task skills, and the current Dream recurring template no
  longer lists a skill-update phase.
- `test/relaunch-chain.md` and `build/dry-run.md` read as Relay-internal probes
  rather than reusable first-install workflows; the spec excludes them from the
  first shipping set.

## Open Questions

None blocking. The proposed curation is intentionally narrow: ship the core
code loop, docs workflow, Dream child workflows that have real bundled skills,
and the complete digest battery; leave internal or stale workflow files out of
the initial PR.

## Review-Design Notes

Reviewed on 2026-06-18 during the owner `review-design` step.

- The runtime shape is right: a local-first `bootstrap/workflows/` fallback
  keeps reusable process offline, inspectable, update-carried, and locally
  overridable without broad-copying repo playbooks into `relay-os/workflows/`.
- Tightened the spec to cover prompt surfaces that enumerate workflows. The
  existing `bootstrap/ticket` and `eval/ticket-diagnostic` instructions still
  teach agents to look only under `relay-os/workflows/`; implementation must
  update those to include `relay-os/bootstrap/workflows/` so packaged workflows
  are discoverable during guided authoring and ticket diagnostics.
- No blocking open questions remain after that spec correction.
