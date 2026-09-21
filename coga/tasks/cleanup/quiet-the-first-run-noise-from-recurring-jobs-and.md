---
title: Quiet the first-run noise from recurring jobs and managed skills
status: in_progress
owner: nicktoper
agent: claude
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
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 4 (open-pr)
---

## Description

Make the first minute in a new repo quiet without concealing configured work.
The owner chose **opt-in Google skills and a compact recurring summary** in
this design session. Retain the shipped recurring templates and their schedules;
replace their per-template status table with a summary and an explicit route to
the full view. The tradeoff is one extra command to inspect schedules, and an
explicit install before using a Google agent skill.

The September 2 audit found automatic skill downloads, Gmail/calendar dependency
installation, and six recurring rows saying "due — not created". Investigation
of the current source confirms the seven Google skill downloads and the footer,
but the Gmail/calendar pip-install path is already gone. Do not recreate or
redesign dependency installation to solve a historical finding.

### Acceptance criteria

- [ ] Fresh `coga init` in both an empty and an existing project makes no
  external skill-install calls, downloads no Google agent skills, and runs no
  pip/dependency installation. It retains bundled capabilities, ordinary
  scaffolding, and agent skill wiring. It emits no optional-install failure or
  skipped-install noise for skills the user never requested.
- [ ] Google skills remain available through the existing explicit command,
  e.g. `coga skill install google/agents-cli google-agents-cli-workflow`.
  Existing installed skills are preserved. `coga skill update --all` continues
  updating installed managed skills and does not install missing Google packs.
- [ ] With six valid, never-instantiated templates, status shows one footer
  line equivalent to `Recurring: 6 templates · 6 due — coga recurring list`,
  including when there are no ordinary tasks. Do not print six healthy template
  rows or wait for a first run before acknowledging the templates.
- [ ] Counts derive from the existing template view: total includes every
  returned template, due uses `TemplateStatus.due`, and errors are counted
  separately. A stale done instance counts as due; a serviced period whose task
  was reaped does not. Due is template-period state, not a count of launchable
  tasks or a promise that all execution prerequisites are satisfied.
- [ ] Errors are never reduced to a count alone: include each affected template
  name and its diagnostic below the summary, sorted by name. An unreadable
  instance reported as `instance_status == "unknown"` also gets a named warning.
  These exceptions may take multiple lines; healthy templates stay summarized.
- [ ] No templates means no footer. Preserve existing footer scope and focused
  view behavior (including unrelated directories, top-level `--no-recurse`,
  `--dirs`, and `--blocked`). Apply the compact footer wherever the current
  footer renders, including a recurring directory view. Instantiated recurring
  tasks remain ordinary rows with unchanged filtering and terminal-state rules.
- [ ] `coga recurring list` retains full per-template detail. Status remains
  read-only and offline, with no new saved first-run state or scheduling logic.
- [ ] Command contracts, source-layout explanations, recurring skill-update
  instructions, and Dream scan instructions agree with the new behavior.
  Packaged/live twins remain byte-identical wherever both exist.

### Proposed shape

1. In `src/coga/commands/init.py`, remove `_do_init()`'s call to
   `_install_managed_skills_or_exit()` and its managed-install summary output.
   Remove the now-unused install wrappers, reporting helpers, and imports.
   The explicit install/update implementation in `src/coga/skill_manager.py`
   stays in place; `src/coga/commands/skill.py`, `install()`, already exposes
   the desired opt-in route. Document that route in the command contract;
   do not add a new flag, opt-out switch, or init interview.
2. Remove the unused init manifest `src/coga/resources/managed-skills.toml`
   and init-only machinery in `src/coga/managed_skills.py`, after rechecking
   consumers. `reconcile_managed_skills()` currently has only test callers;
   do not retain it as speculative infrastructure. Adjust packaging assertions
   and resource documentation that name the removed manifest/module. Preserve
   generic install/update code and tests that exercise the explicit commands.
3. Fix the manifest's instructional consumers in the same change. In the
   packaged `bootstrap/dream/scan/contract-audit` and `knowledge-scan` skills,
   identify GitHub-managed upstream trees through the installed SKILL.md
   `metadata.github-repo` predicate used by `skill_manager.gh_skill_repo()`.
   Exclude those trees before scanning; keep locally adapted URL imports such
   as `clarity` in scope. Do not replace the manifest with another hardcoded
   Google-name list. Update any live twins if present.
4. In `src/coga/views.py`, replace `_print_recurring_templates()`'s healthy-row
   table with the count summary and diagnostic exceptions above. Continue
   receiving `list_templates()` output from `render_status()` through the
   existing `_covers_recurring()` gate. Reuse `TemplateStatus.due`; do not
   rescan execution history, infer readiness from repo age, or change the
   recurring scheduler. Keep `commands/status.py` a thin command head.
5. Update the command owner at
   `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`
   (init, status, and skill-install sections). Update
   `coga/contexts/coga/codebase/SKILL.md` and its packaged twin to remove the
   automatic-install model. Update `coga/recurring/skill-update/ticket.md` and
   its packaged twin to describe explicit installation followed by updates of
   installed skills. Check related architecture prose for stale automatic-init
   claims; docs should summarize/link to the contract, not duplicate it.
6. Replace init manifest-install tests with tests that reject attempted
   external installs during real fresh scaffolding, covering empty/existing
   projects and absent `gh`. Retain coverage of bundled resolution and skill
   wiring. Update status assertions and add count/diagnostic cases for no
   templates, fresh templates, live instances, stale done, reaped serviced
   periods, template errors, and unknown instances. Preserve full-list tests.
   Use mocked command/network boundaries; tests must not fetch Google skills.

Implementation verification: run `python -m pytest tests/test_init.py
 tests/test_commands.py tests/test_recurring.py tests/test_skill_manager.py
 tests/test_packaging.py` (as one command), then `python -m pytest` and
`coga validate --json`. Recheck test filenames in the implementation checkout;
remove obsolete manifest-only tests rather than retaining dead production code
for them. Record exact commands and any pre-existing validation failures.

### Out of scope

- Removing recurring templates, changing cadence or launch eligibility, or
  introducing activation toggles and persistent first-run markers.
- Changing `coga recurring list`, task-row filtering, or the scheduler's state
  semantics.
- Removing already-installed Google packs or bundled Gmail/calendar/browser
  capabilities; changing explicit skill-install/update protocols.
- Dependency management redesign, new plugin systems, migrations, or config
  edits to this repository's `coga.toml` / `coga.local.toml`.

## Context

Source: `marketing/phase-0-audit`, September 2, 2026, check 2 rows g and k,
triaged by the owner September 3. The historical finding motivated this work;
current source, rather than the old skill count/dependency description, defines
what needs changing.

Verified implementation relationships:

- `src/coga/commands/init.py`, `_do_init()`, invokes
  `_install_managed_skills_or_exit()`, which calls
  `src/coga/managed_skills.py`, `install_managed_skills()`. That function loads
  `load_managed_skill_manifest()` and installs each missing manifest entry.
  The current manifest contains seven optional `google/agents-cli` refs.
- `src/coga/commands/skill.py`, `install()`, calls
  `src/coga/skill_manager.py`, `install_github_skill()`, with the explicit
  source and selector. In the same module, `update_skills()` enumerates
  installed skills and uses `gh_skill_repo()` for GitHub provenance; it does
  not read the init manifest or restore absent packs.
- `src/coga/commands/status.py`, `status()`, delegates to
  `src/coga/views.py`, `render_status()`. That renderer calls
  `src/coga/recurring.py`, `list_templates()`, when `_covers_recurring()`
  permits it, then passes the result to `_print_recurring_templates()`.
  The footer no longer lives in the command module named by the old audit.
- `src/coga/recurring.py`, `TemplateStatus.due`, already distinguishes stale
  done instances from reaped serviced periods. `list_templates()` returns
  template-load errors through `error` and unreadable instance state through
  `instance_status == "unknown"`; the summary must preserve those signals.
- `tests/test_commands.py`,
  `test_status_shows_templates_even_without_instantiated_tasks()`,
  `test_status_renders_recurring_tasks_as_normal_rows()`, and
  `test_status_hides_templates_footer_outside_recurring_scope()` pin today's
  footer and task relationships. `tests/test_recurring.py`,
  `test_recurring_list_reports_reaped_serviced_period_as_ran()`, pins the
  full-list behavior that must remain intact.

`coga/principles` requires observable failures and offline read-only commands.
`coga/architecture`'s "Where a fact lives: docs vs contexts" makes `coga/cli`
the command contract owner. `coga/codebase` governs minimal core and packaged
parity. The change is one coherent PR: default installation, status rendering,
and their directly affected tests/contracts.

<!-- coga:blackboard -->

## Design handoff

- Owner selected "opt-in skills, compact recurring summary" in this session.
  Retain all shipped recurring jobs; expose template/due counts and named
  errors, with `coga recurring list` for detail. Accepted tradeoff: an extra
  command for schedules and an explicit install for Google packs.
- Investigation found the Gmail/calendar pip-install complaint is historical;
  current init still installs seven Google packs. Footer implementation moved
  to `views.py`; the spec cites current symbols.
- Manifest removal also affects Dream's scan exclusions. Preserve the
  upstream-tree exclusion through GitHub install metadata while retaining
  locally adapted URL skills in the scan corpus.
- Design only: no source code, branch, or PR created. Existing dirty
  `coga/log.md` was present before this work and was not manually edited.
- Design checks: `git diff --check` passed; `Ticket.parse()` and section
  assertions passed with `PYTHONPATH=src python` (plain Python did not resolve
  the source package). No runtime tests needed for this spec-only step.
- Spec lives under Description/Context so the implementation launch receives
  it. Next gate is owner `review-design`; implementation has not begun.

## Open Questions

None. The owner resolved the product choice; the proposed shape is ready for
review-design.

## Review-design

- Reviewed the proposed scope and spot-checked the current footer,
  `TemplateStatus`, GitHub provenance predicate, and fact-ownership rule.
  No must-fix design findings; no spec changes needed.
- Owner explicitly approved advancing to implementation in the attended session.
  No source changes or runtime tests in this review; the existing dirty
  `coga/log.md` was left untouched.

## Dev

pr: https://github.com/FastJVM/coga/pull/852
branch: quiet-first-run
worktree: /home/n/Code/codex/coga
Single-checkout layout: the primary checkout on the feature branch; no linked
worktree was created.

## Implement

- Commit `Quiet first-run noise: opt-in skill installs, compact recurring
  footer` on `quiet-first-run`, rebased onto `origin/main` (only task/log
  state had landed since branching).
- Init: `_do_init()` no longer calls the managed-skill installer; the
  summary/note printers and their imports are gone. Deleted
  `src/coga/managed_skills.py`, `src/coga/resources/managed-skills.toml`, and
  `tests/test_managed_skills.py` outright — init was the sole production
  caller and `reconcile_managed_skills()` had only test callers. Consequence
  accepted per design: the rate-limit / no-access / SAML classification of
  `gh` failures went with the module; `coga skill install` surfaces `gh`'s
  own error.
- Status: `views._print_recurring_templates()` prints
  `Recurring: N templates · M due[ · K errors] — coga recurring list`, then
  `error: <name> — <diag>` and `warning: <name> — instance <slug> is
  unreadable (status unknown)` lines sorted by name. Counts use
  `TemplateStatus.due`; errors are excluded from due. `firing_stamp` import
  dropped from views.
- Dream scan skills (`contract-audit`, `knowledge-scan`): exclusion predicate
  is now `metadata.github-repo` in `SKILL.md` frontmatter (the
  `gh_skill_repo()` test); the manifest and the "seven trees / 286,169 bytes"
  figures are gone, `clarity` explicitly stays in scope. Verified the
  predicate matches exactly the seven `google-agents-cli-*` dirs in this repo.
- Contracts: `coga/cli` (init installs no skills + explicit install route;
  status footer spec; `coga skill` opening), `coga/codebase` and
  `coga/architecture` (+ packaged twins, byte-identical), `skill-update`
  template (+ twin), `docs/getting-started.md`, `dependencies.py` `gh`
  rationale, docstrings in `resources/__init__.py` / `coga/__init__.py`.
- Tests: `test_fresh_init_installs_nothing[empty|existing]` runs a real init
  from packaged templates on a `PATH` holding only `git`, spies
  `subprocess.run`, and fails on any installer argv or on
  `install_github_skill`/`install_url_skill` being reached. Rollback test now
  injects its failure at `_stamp_user_into_delivered_tickets`. Footer cases:
  CLI-level (fresh ×6, errors, no templates, live instance) in
  `tests/test_commands.py`; renderer-level (stale done, reaped serviced,
  unknown instance, singular nouns) in `tests/test_views.py` — the unknown
  case is not reachable end-to-end because an unreadable ticket fails the
  main task listing first. `test_recurring_views_render_malformed_period_as_error`
  now asserts the named status line.
- Environment note: the ambient `python3` is 3.9 and `python3.12` lacks
  `tomlkit`; tests ran in a scratch venv (`uv venv --python 3.12` +
  `uv pip install -e ".[test]" pip`) with `PYTHONPATH=$PWD/src`.
- Verification (exact commands, from the checkout root, `$PY` = that venv):
  - `PYTHONPATH=$PWD/src $PY -m pytest tests/test_init.py tests/test_commands.py tests/test_recurring.py tests/test_skill_manager.py tests/test_packaging.py tests/test_views.py -q`
    → 718 passed.
  - `PYTHONPATH=$PWD/src $PY -m pytest -q` → 2640 passed in 184s.
  - `PYTHONPATH=$PWD/src $PY -m coga.cli validate --json` → exit 0, same
    issue list as `main` (4 pre-existing `error`s in unrelated tickets:
    `clean-up-all-the-working-trees`, `v2/autotrigger-ticket-type`,
    `v2/measure-relay-prompt-scope-and-agent-precision`,
    `v2/use-worktree-when-starting-a-dev-task`, plus empty-description warns).
  - `git diff --check` clean; live `coga status` shows
    `Recurring: 6 templates · 2 due — coga recurring list`.
- Not done here: no push, no PR (open-pr step). Existing dirty `coga/log.md`
  was left for `coga bump` to sync.
