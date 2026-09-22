# Context migration record — 2026-09-22

The documentation and the reusable contexts were merged into one library under
`docs/`. Ticket: `redo-documentation-dir-and-merge-it-with-context-b`. The
owner chose a single migration PR at the implement step (overriding the
design's four-prerequisite split) and approved the README's opening paragraph.
Per-section dispositions from the migration were checked for coverage before
any legacy file was deleted. This page keeps the durable result: where each
old path and ref went, what was cut, and how the cutover works.

## Configuration

This repo sets `[layout] contexts = "docs/contexts"` in the committed
`coga/coga.toml`, anchored at the checkout root. The packaged default for
other repos is unchanged: an unset `[layout]` still means `coga/contexts/`.
`coga uninstall` removes the configured directory, so here it removes
`docs/contexts/`; Git is the recovery source. Indexes, evidence, designs and
archives stay outside that directory on purpose.

## Old refs

Every old ref still resolves except the one listed as retired. Seven old refs
are now short overviews or indexes. Attaching one loads only that page, not
the topics it links to.

| Old ref | Now |
| --- | --- |
| `coga/architecture` | Overview + topic map. Details: `coga/tickets`, `coga/lifecycle`, `coga/workflows`, `coga/prompt-composition`, `coga/session-conduct`, `coga/knowledge`, `coga/configuration`, `coga/context-layout`, `coga/agents`, `coga/launch`, `coga/megalaunch`, `coga/internals/agent-spawn`, `coga/extension-model`, `coga/dream` |
| `coga/cli` (package-only before) | Command index; now also has a canonical copy. Each command's contract lives in its owning topic |
| `coga/codebase` | Source map. Details: `coga/codebase/gotchas`, `coga/testing`, `coga/packaging`, `coga/releasing`, `coga/skill-management`, `coga/extension-model` (microkernel rule), `coga/context-layout`, `dev/checkouts` |
| `coga/sync` | Overview. Details: `coga/notifications` (+ `/producers`, `/failures`), `coga/internals/{state-publication,git-regressions,git-refresh,spool-merge}` |
| `coga/recurring` | Overview. Details: `coga/recurring/{templates,scheduling,delegation,autofix}`, `coga/dream`, `coga/internals/recurring-{admission,control,temp-worktrees}` |
| `coga/launch-internals` | Index. Details: `coga/internals/{agent-spawn,human-assist,assist-publication,launch-claims,claim-recovery,pr-publication}` |
| `dev/code` | Overview. Details: `dev/{checkouts,dev-record,design-history,checkout-cleanup}` |
| `coga/usage` | Read contract; capture schema moved to `coga/internals/activity-capture` |
| `coga/blackboard`, `coga/principles`, `coga/extension-model`, `coga/period-task`, `coga/important`, `coga/patterns`, `coga/secrets`, `coga/current-direction`, `coga/project-stage`, `coga/roadmap`, `browser/*`, `docs/gdrive-mcp`, `marketing/{map,positioning,plan,distribution}` | Same ref, trimmed or rewritten in place |
| `marketing/launch-history` | **Retired.** Moved to `docs/archive/launch-programs/` (a README index, not attachable) |

New refs: `product/vision`, `coga/knowledge`, `marketing/strategy`, and every
leaf listed in [docs/README.md](README.md). A `coga/digest` topic was planned,
but digest and the spool were removed from the product (#786), so it was never
written. The notification pages carry the facts that still apply.

## Old docs paths

| Old path | Now |
| --- | --- |
| `docs/getting-started.md` | `coga/install`, `coga/init`, `coga/first-task` |
| `docs/concepts.md` | `coga/architecture`, `coga/tickets`, `coga/blackboard`, `coga/lifecycle`, `coga/workflows`, `coga/prompt-composition`, `coga/knowledge` |
| `docs/reference.md` | `coga/cli` command index |
| `docs/operations.md` | `coga/notifications`, `coga/sync`, `coga/recurring`, `coga/dream`, `coga/secrets`, `coga/first-task` (readiness) |
| `docs/development.md` | `coga/codebase`, `coga/testing`, `coga/packaging`, `dev/*`, `coga/init`, `coga/configuration` |
| `docs/releasing.md` | `coga/releasing` |
| `docs/vision.md` | `product/vision`; normative rules in `coga/principles`; history in [archive/origins.md](archive/origins.md) |
| `docs/market-thesis.md` | `marketing/strategy`; dated competitor research in [archive/market-landscape.md](archive/market-landscape.md) |
| `docs/velocity-report.md` | [evidence/velocity.md](evidence/velocity.md) (experiment status corrected to shelved) |
| `docs/{adoption-trial,build-vs-adopt,continuity-comparison,human-centered-comparison,pitch-evaluation,research-replacement-trial,research-work-comparison,upkeep-audit,usage-comparison,why-switch-to-coga}.md` | Same names under [evidence/](evidence/) |
| `docs/cli-extension-audit.md`, `docs/cli-extension-external-surface.md` | [design/cli-extension-audit.md](design/cli-extension-audit.md), [design/cli-external-surface.md](design/cli-external-surface.md) |
| `docs/migrating-to-coga.md` | [archive/relay-migration.md](archive/relay-migration.md), with the blanket rollback snippets replaced by targeted steps |
| `coga/contexts/**` | `docs/contexts/**` |

## Cuts and history

Content was removed only when another topic already owned it, when the source
showed it was false, or when it was history. History went to `archive/`:
- founding narrative → `archive/origins.md`
- superseded current-direction and stage decisions → `archive/superseded-decisions.md`
- competitor matrices → `archive/market-landscape.md`
- launch programs → `archive/launch-programs/`

Where prose disagreed with the code, the new topics follow the code.
Notable corrections:
- The Git state sweep publishes only tasks, the log and recurring files. It
  does not publish contexts (#848). The only path that publishes contexts is
  `coga ticket` authoring.
- Workflows freeze when a ticket is activated, not when it is created. Launch
  commits the activation only after its preflights pass.
- `coga init` installs no managed skills.
- `aliases.DEFAULT_ALIASES` has nine entries.
- A secret declaration does not isolate the process: only the named source
  variable is scrubbed.
- The launcher switches to a prompt file above 120,000 UTF-8 bytes
  (`_MAX_PROMPT_ARG_BYTES`).

## Distribution

- **Bootstrap fallback:** every generic topic (all of `coga/*` except the
  three posture pages, plus `dev/*` and `browser/*`) has a byte-identical copy
  at `src/coga/resources/templates/coga/bootstrap/contexts/<ref>/SKILL.md`.
- **Init-seeded:** only the scaffolds (`.gitignore`, `_template/SKILL.md`)
  under `templates/coga/contexts/`. Since the browser fallback repair, the
  browser topics ship through bootstrap instead.
- **Local-only:** `product/vision`, `coga/{current-direction,project-stage,roadmap}`,
  `docs/gdrive-mcp`, `marketing/*`.

`tests/test_packaging.py` enforces all three classes against this repo's
configured root. `REQUIRED_BOOTSTRAP_CONTEXT_REFS`,
`REQUIRED_INIT_CONTEXT_FILES` and `LOCAL_ONLY_CONTEXT_REFS` are reviewed
lists, and the suite fails if a topic is deleted from both copies.

## Cutover

1. Merge this PR (the content move and the owner's `[layout]` edit together)
   through the owner review gate.
2. Before merging, pause schedulers and finish or pause any session or
   checkout that can publish Coga state.
3. Every operating checkout takes the merged revision together with the
   matching package: an editable install of this source, or the released
   wheel that contains the new bootstrap topics.
4. Check that `load_config(...).contexts_root` resolves to `docs/contexts`,
   run `coga validate --json`, and compose a representative prompt. Then
   resume.
5. On failure, keep writers paused and revert the config and content together.
   Never restore only the old config against the removed files.

Cutover revision and package version: *recorded after merge.*
