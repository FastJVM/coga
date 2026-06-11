The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: task-subdirs
worktree: /home/n/Code/relay-task-subdirs

## Implement plan (2026-06-10)

- `list_tasks()` (src/relay/tasks.py): one-level groups. A direct child
  of `tasks/` with `ticket.md` is a task; a child dir without one is a
  group whose direct children are scanned the same way (no deeper
  recursion). `_`-prefix skipped at both levels. Duplicate leaf slug →
  raise typed `DuplicateTaskSlugError` carrying the colliding paths.
- `relay validate` catches `DuplicateTaskSlugError` and reports the
  colliding paths as an error issue instead of crashing.
- `_authored_task_refs` (commands/ticket.py): replace `rel.parts[0]`
  slug reconstruction with containment against `list_tasks()` paths.
- `task_dir()` (paths.py): REMOVE — uncalled in src/ and tests, exported
  landmine; ticket allows "make nesting-aware or remove".
- Recurring orphan sweep (commands/recurring.py): debug runs are always
  scaffolded top-level, sweep stays top-level — confirm, no change.
- Scaffold (scaffold.py): new tasks stay top-level; slug dedup now sees
  nested slugs via list_tasks — intentional, no change.
- git.py / compose.py carry `ref.path` — safe, no change.
- `git mv` stream-agent ticket → tasks/auto/ on this branch (atomic with
  code per ticket).
- Fixture: example/relay-os has no tasks/ — add nested-task fixture.
  Check test_smoke.py expectations first.
- New tests in tests/test_tasks.py + validate duplicate-slug test in
  test_validate.py.

## Implemented (2026-06-10)

Committed as 7ab0a31 on branch `task-subdirs` (worktree
/home/n/Code/relay-task-subdirs). 638 tests pass; `relay validate
--json` against example fixture is clean (ok_count 1, no issues).

What changed:
- `list_tasks()` (src/relay/tasks.py): one-level groups. Child of
  `tasks/` with ticket.md = task; without = group whose direct children
  are scanned; `_` skipped at both levels; task dirs never recursed
  into; results sorted by slug. New typed `DuplicateTaskSlugError`
  (carries slug + colliding paths) raised on duplicate leaf names.
- `validate.run()` / `validate_task()` catch `DuplicateTaskSlugError`
  and report a `duplicate-slug` error issue with both paths instead of
  crashing. `run()` now discovers first, then passes `only=refs` to
  `apply_safe_fixes` (same set, avoids a second raise site).
- `_authored_task_refs` (commands/ticket.py): replaced `rel.parts[0]`
  reconstruction with containment against `list_tasks()` paths — the
  old code mis-attributed nested tasks to their group dir.
- `task_dir()` REMOVED from paths.py (uncalled landmine; ticket allowed
  remove). Nothing in src/ or tests imported it.
- Debug-orphan sweep (commands/recurring.py): confirmed safe —
  `scaffold_debug_run` → `_scaffold_at_slug` → `scaffold_task` always
  creates top-level; added a comment documenting the assumption.
- Scaffold: unchanged by design — new tasks always created top-level
  (grouping = manual `git mv`); slug dedup via list_tasks now sees
  nested slugs, so cross-group collisions are prevented at creation.
- `git mv relay-os/tasks/stream-agent-… → tasks/auto/` in the same
  commit (atomic per ticket).
- Fixture: added example/relay-os/tasks/auto/triage-inbound-email/
  (frozen code/with-review workflow so the example validates with zero
  warnings); smoke test now asserts the nested fixture is discovered
  and selects the scaffolded task by slug instead of `[0]`.
- New tests/test_tasks.py (discovery, `_` skipping, no-recursion,
  duplicate error, prefix resolution across groups) + two validate
  tests (nested-clean, duplicate-slug report).
- Templates under src/relay/resources/templates/relay-os/ untouched —
  behavior change is code-side only; template tasks/ content unchanged.

Merge wrinkle for reviewer: the primary checkout has live UNCOMMITTED
edits to the stream-agent ticket's blackboard.md/log.md at the OLD
top-level path. When this branch merges and main is checked out, git
will see those as edits to a deleted path — commit or stash the live
task state before merging to avoid a messy reconcile.

## Peer review (2026-06-11)

Native review command: `codex review --base main` from
`/home/n/Code/relay-task-subdirs`. The sandboxed run hit the known read-only
app-server setup failure, so the same command was rerun with escalation and
completed.

Must-fix found:
- The implementation made nested tasks discoverable, but launch-time guidance
  still taught agents to reconstruct `relay-os/tasks/<slug>/`. That would
  send agents to the wrong blackboard for grouped tasks.

Fix committed on branch `task-subdirs` as `c48e771`:
- `compose_prompt_report()` now includes `Task directory:
  relay-os/tasks/...` in the prompt header, using the resolved `TaskRef.path`.
- Updated the base prompt, live Relay contexts, packaged bootstrap contexts,
  Dream/Retro templates, and git-sync comments to describe top-level or
  one-level-grouped task directories.
- Added a compose regression test for nested task header paths.

Verification:
- `python -m pytest` from `/home/n/Code/relay-task-subdirs`: 638 passed,
  1 skipped. One pytest cache warning came from the sandbox not being able to
  write `.pytest_cache`; tests passed.
- `PYTHONPATH=/home/n/Code/relay-task-subdirs/src python -m relay.validate
  --json` from `example/relay-os`: ok_count 1, no issues.

## Bootstrap notes (2026-06-10)

Drafted during the bootstrap session for
`stream-agent-progress-in-auto-mode-and-recurring-l`. Nick wants
auto-mode tickets grouped under `relay-os/tasks/auto/`; discovery only
sees direct children of `tasks/`, so nesting needs code support first.
Slug-prefix naming was explicitly rejected. The stream-agent ticket
stays at top level until this ticket ships; the `git mv` happens in
this ticket's PR (atomically with the code change).

Evaluator findings (collision semantics, slug→path reconstruction
sites, fixture gap, move-ordering hazard) were folded into the ticket's
`## Context` after the review below was written.

## Evaluator review

**Verdict: Launchable with minor pre-flight fixes — clear, well-scoped, correctly contexted; the main gaps are an under-specified collision behavior, an ordering hazard around moving a live ticket, and two slug-reconstruction sites the ticket's checklist doesn't name.**

1. **Description clarity: good.** A cold agent gets the what (nested task dirs, one level deep), the why (grouping by area), the where (`list_tasks()` in `src/relay/tasks.py` ~line 50 — the line reference is accurate), and a concrete acceptance action (move one real ticket into `tasks/auto/`). The invariants are stated crisply: slug stays the leaf dir name, bare-slug/prefix referencing is preserved, task dirs are not recursed into, `_`-prefix skipping applies at both levels. This is above the bar for cold pickup.

2. **Workflow fit: correct.** `code/with-review` (implement → peer-review → open-pr → human review) fits a CLI behavior change with tests and a fixture touchpoint. One wrinkle: the ticket bundles a repo-content action (the `git mv` of the stream-agent ticket) into a code PR. That move is only valid *after* the code change ships — if it lands on the feature branch and the human reviews/merges later, every CLI command on `main` is blind to that ticket in the interim, and the supervisor/automerge machinery may treat it as vanished. The implement step should either do the move in the same PR knowing it merges atomically, or the ticket should say explicitly "move only after merge." Worth one sentence before launch.

3. **Contexts: relevant, one candidate missing.** `relay/codebase` is the right primary attachment (source layout, fixture-sync rule, test commands). Candidate addition: `relay/architecture` — per CLAUDE.md it defines primitives and locking, and this change touches task *identity* (slug-as-reference is an architectural invariant, and task-dir locking presumably keys off task paths). Low severity, but an agent deciding collision semantics would benefit from the architecture contract.

4. **Context-vs-ticket fact placement: handled well.** The ticket already copied the load-bearing facts out of the broad context into `## Context` (discovery location and mechanics, fixture-sync rule, template-sync rule). No reliance on the reader fishing a buried fact out of `relay/codebase/SKILL.md`. This is the right pattern.

5. **Scope: reasonable, with the right escape valve.** Core (discovery + resolution + validate + collision check + tests + fixture) is one coherent ticket. The scaffolding question (`group/slug` form in `relay draft`/`relay ticket`) is correctly marked optional with "manual `git mv` is acceptable" — that's good scope discipline. The single ticket move is a fine smoke test, not scope creep. Out-of-scope lines are explicit.

6. **Assumptions to question before launch** (I verified these against the source):
   - **Collision behavior is under-specified.** "Fail loud in discovery/validate" is ambiguous: if `list_tasks()` raises on a duplicate leaf name, *every* command breaks — including `relay validate`, which needs discovery to run in order to report the problem legibly. Decide: discovery raises a typed error (validate catches and reports it), or discovery dedups/returns and validate flags it. One sentence would settle it.
   - **Two slug→path reconstruction sites exist beyond `list_tasks`, and the ticket's checklist ("validate and any log/digest/Slack code") doesn't name either.** (a) `src/relay/commands/ticket.py:270–282` (`_authored_task_refs`) computes `slug = rel.parts[0]` and `task_path = tasks_root / slug` — for a nested task, `parts[0]` is the *group* dir, so authored-task detection silently misses or mis-attributes nested tickets. (b) `src/relay/paths.py:92` `task_dir(cfg, id_slug)` builds `tasks/<slug>` directly — it appears uncalled in `src/relay/` today, but it's exported API and a landmine; deprecate or make it nesting-aware. Also note `src/relay/commands/recurring.py:279–296` runs its own `tasks_root.iterdir()` sweep (debug-run orphan reaping) — probably fine since debug runs are always scaffolded at top level, but the implementer should confirm rather than assume. `git.py` and `compose.py` carry `ref.path`/`id_slug` correctly and look safe.
   - **Scaffold dedup misses cross-group collisions in one branch.** `src/relay/scaffold.py:113–121` dedups against `{t.slug for t in list_tasks(cfg)}` then checks `tasks_dir(cfg)/slug` existence — once nested tasks are discoverable, the slug-set check covers them, but the new-task dir is always created at top level, which is consistent with "grouping is a manual git mv." Fine, just confirm intentionally.
   - **One-level-deep: adequate for the stated use** (`tasks/auto/`), and bounding depth keeps the "subdir with ticket.md is a task, not a group" rule decidable. No evidence anything needs deeper nesting. Accept.
   - **Reserved names.** If scaffolding ever accepts a `group/slug` arg, note that `resolve_target` reserves the `bootstrap/` prefix (`src/relay/tasks.py:113–117`); a group literally named `bootstrap` would be unreachable by that arg form. Trivial, but worth a line if the optional scaffold work happens.
   - **Fixture gap.** `example/relay-os/` currently has *no* `tasks/` directory at all, so "mirror in the seeded fixture" means *adding* a nested-task fixture, not editing one — slightly more work than the ticket implies.
