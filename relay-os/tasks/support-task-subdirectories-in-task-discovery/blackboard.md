The blackboard is a notepad to be written to often as the human and agent works through a task.

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
