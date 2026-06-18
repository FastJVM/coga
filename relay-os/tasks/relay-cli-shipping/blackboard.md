The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design notes (step 1, design)

Investigated the real trees and resolution code. Decisive facts:

- Workflows resolve from ONE root (`paths.py:workflow_path` → `workflows/<name>.md`);
  no `bootstrap/` fallback. Skills/contexts DO have bootstrap fallback.
- Fresh `relay init` copies the whole packaged template tree wholesale
  (`copy_fresh_templates`), so adding files under packaged `workflows/` or
  `bootstrap/` ships them to new repos for free. The `VENDORED_*` lists only
  affect `--update` of existing non-source repos and overwrite wholesale.
- Curation settled by reference-tracing (see ticket "Design findings"): ship
  `code/{design-then-implement,with-review}` + `dev/with-self-review` +
  `skills/code/`; exclude digest/dream/build/test/docs as repo-specific or
  relay-internal.

Spec (Description/AC/Proposed Shape/Out of Scope) written into ticket.md.

## Open Questions

1. **Workflow delivery channel — confirm the recommended split.** The spec
   ships `skills/code` through bootstrap (single source, drift-free, no new
   code) but ships the workflows as plain `workflows/` template files locked by
   a parity test — because workflow resolution has no bootstrap fallback today.
   The fuller alternative (add `bootstrap/workflows/` resolution so workflows
   ride the same vendoring) is cleaner long-term but touches `workflow_path`,
   `retrofit.py` freezing, and `create.py`/`mark.py` validation. Recommended:
   take the smaller split now, file the bootstrap-workflows change as its own
   ticket. OK to defer?

2. **Update-carry for the workflows.** Recommended: fresh-init-only — do NOT
   add the curated workflows to `VENDORED_WORKFLOW_TEMPLATES`, so a user's
   edited `code/with-review` survives `relay init --update` (workflows are
   user-owned playbooks). Cost: existing repos won't gain these workflows on
   update; they'd copy them or re-init. The task title says "into new repos,"
   which fits fresh-only. Accept, or do you want existing repos force-updated
   too (accepting clobber of local edits)?

3. **`docs/create-google-doc` and `implement-and-pr`.** (a) `create-google-doc`
   is excluded as Google-Drive-MCP domain-specific — but it's arguably reusable
   for any Google-using repo. Keep excluded? (b) `skills/code/implement-and-pr`
   is not referenced by any shipped workflow. Recommended: ship the whole
   `skills/code/` dir anyway (coherent, it's a legit reusable skill) rather
   than cherry-pick the four referenced ones. OK?
