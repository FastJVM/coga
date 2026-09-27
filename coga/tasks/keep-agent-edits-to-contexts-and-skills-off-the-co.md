---
title: Keep agent edits to contexts and skills off the control branch without a merge
status: in_progress
owner: nicktoper
contexts:
- coga/internals/state-publication
- coga/principles
- coga/script-tickets
- coga/testing
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
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
step: 2 (evaluate-design)
agent: claude
---

## Description

Keep automatic Coga publication from putting context and skill edits onto the
control branch before human review. The original report described a sweep of
the whole Coga tree; that premise is stale. The current sweep already publishes
only tasks, log, and recurring state. The remaining gap is guided ticket
authoring: its finalizer publishes context and skill changes made during the
agent interview directly to control.

Retain the existing state-only sweep and remove support files from guided
authoring publication. Keep detecting those edits so the finalizer can list
them visibly and tell the operator to carry them through a branch and reviewed
PR. The owner accepted this scope and tradeoff in the attended design session:
knowledge changes remain local until explicitly reviewed rather than being
automatically committed for cleanliness. Ordinary manual knowledge edits also
remain normal Git review work; documentation must make that responsibility
explicit.

### Acceptance criteria

- [ ] `sync_coga_state()` continues publishing task, log, and recurring state
  only. Contexts, skills, workflows, and config remain excluded regardless of
  session metadata or checkout branch. No new lifecycle refusal is added.
- [ ] `finalize_authored()` publishes authored task paths only, preserving
  existing validation, file-to-directory conversion, deleted-ticket handling,
  and bootstrap task discovery. It never includes context or skill changes
  in its `git.publish()` call, including additions, edits, and deletions.
- [ ] Changed contexts and skills are retained on disk as authored (including
  intended deletions), with a deterministic stderr notice listing affected
  paths and explaining that Coga did not publish them and that a branch plus
  human-reviewed PR is required. A relocated `[layout] contexts` root is
  included. No notice is emitted for support files unchanged by the interview.
- [ ] Support-only interviews emit the notice without calling `git.publish()`.
  Mixed task/support interviews still publish tasks. The notice is visible
  even if task validation or publication subsequently fails; it does not
  convert those failures into success or claim the task was published.
- [ ] The behavior is identical with or without `COGA_TASK_*` metadata in the
  parent process: a human invoking an agent interview is not permission to
  publish the agent's knowledge edits. No actor-detection heuristic is added.
- [ ] Real-Git regression coverage proves a launched-session context/skill
  edit cannot reach control through the sweep while task/log changes do.
  Cover nested and root layouts and relocated contexts; include control and
  feature checkouts across the cases. Assert control-tree contents as well
  as preservation of local edits, rather than only mocking publication.
- [ ] Authoring tests cover new, edited, and deleted support files, relocated
  contexts, support-only and mixed interviews, and a parent without launch
  metadata. At least one real-Git case runs finalization followed by the
  sweep and proves knowledge stays off control while the authored task lands.
- [ ] Update the owning state-publication topic, the sync overview, and the
  principle-4 receipt in the same implementation PR. Update the finalize
  skill's summary to link to the owning contract. Keep all affected packaged
  twins byte-identical; check other authoring guidance for stale promises.
- [ ] Record exact verification commands and counts: focused authoring/Git
  tests, packaging checks, the full suite, and task-scoped validation under
  an absolute checkout `PYTHONPATH`.

### Proposed shape

1. In `src/coga/authoring.py`, keep `snapshot_authoring_state()`,
   `changed_authoring_paths()`, and `support_paths()` detecting interview
   changes. In `finalize_authored()`, use the support list for the stderr
   notice before validation, and remove its extension of task publication
   paths. Keep the existing task validation and publication sequence.
   Retain helpers where useful; rename misleading sync-oriented descriptions
   or remove newly unreachable support-only commit-message handling as needed.
2. Leave `src/coga/git.py`, `publish()` and its provenance guards unchanged.
   `sync_coga_state()` already implements candidate (a) for the sweep. Add
   regression coverage rather than restoring the removed broad pathspecs.
3. Adapt the support-publication expectations in `tests/test_authoring.py`
   to task-only publication plus notices. Extend the existing sweep coverage
   in `tests/test_git.py` using the real-Git fixtures and explicit launch
   metadata set inside the test (the test fixture clears inherited metadata).
   Add the finalization-plus-sweep integration case there or alongside the
   authoring tests, reusing fixtures rather than building a new harness.
4. Make `docs/contexts/coga/internals/state-publication/SKILL.md` the owner
   of the new finalizer behavior and its visibility contract. Remove the
   interview exception from `docs/contexts/coga/sync/SKILL.md`; revise the
   receipt in `docs/contexts/coga/principles/SKILL.md` to describe both the
   automatic publication boundary and Dream's reviewed proposals. Update
   `coga/skills/coga/ticket/finalize/SKILL.md` and the corresponding files
   under `src/coga/resources/templates/coga/bootstrap/`.

Candidate (b), human-only knowledge sweeping, is rejected: a parent CLI can
lack launch metadata while its interview child authored the changes, and a
later human command could sweep earlier agent edits. Candidate (c), refusing
bump/done/block while knowledge is dirty, adds lifecycle coupling without
closing the independent authoring finalizer. Candidate (a), already implemented
for the sweep, extends naturally to finalization with explicit feedback.

### Out of scope

- No automatic branching, commits of review work, PR creation, merges,
  actor provenance database, configuration switches, or new commands.
- No changes to task/log/recurring publication, including recurring template
  scripts and task attachments. These are existing operational-state policy;
  this ticket does not claim to gate every behavior-affecting file.
- No global restriction in `git.publish()`, launch classification change,
  completion gate, or repeated whole-repository warning on every command.
- No Git permission boundary against an agent explicitly invoking Git or
  editing a control checkout. This change closes the identified automatic
  Coga publication paths; branch discipline and human merge policy still
  govern review. Local prompt composition continues reading local files.
- No change to the nonzero interview exit path; it already skips finalization
  and surfaces the agent failure. The ordinary sweep remains state-only.

## Context

- `src/coga/git.py`, `sync_coga_state()` builds paths from `tasks_dir()`,
  `log_path()`, and `recurring_dir()`, finds dirty paths, then passes them to
  `publish()`. The old `_coga_state_pathspecs` and `_ROOT_LAYOUT_COGA_PATHS`
  symbols no longer exist. `sync_task_state()` separately publishes the
  requested task and log; neither needs a new knowledge filter.
- `src/coga/authoring.py`, `authoring_sync_roots()` resolves the configured
  contexts root as well as tasks and skills. `snapshot_authoring_state()`
  captures hashes before the interview; `changed_authoring_paths()` compares
  them afterward and includes deletions. `support_paths()` selects contexts
  and skills from that set. `finalize_authored()` currently appends this
  support list to task paths before calling `git.publish()`.
- `src/coga/commands/ticket.py`, `_run_authoring_session()` snapshots before
  `spawn_agent_session()` and calls `finalize_authored()` in the parent only
  after a successful child exit. Child launch metadata is not a reliable
  classifier of what this parent may publish.
- `tests/test_git.py`,
  `test_sweep_publishes_only_task_log_and_recurring_state()` already proves
  exclusion of a new context and edited workflow, but does not explicitly
  simulate launch metadata or exercise authoring finalization.
- `tests/test_authoring.py`,
  `test_finalize_authored_syncs_task_and_support_paths()`,
  `test_finalize_authored_syncs_relocated_contexts_dir()`,
  `test_finalize_authored_syncs_support_only_from_bootstrap_interview()`, and
  `test_finalize_authored_syncs_deleted_support_only_with_live_anchor()`
  currently expect support files in mocked publish calls; those expectations
  must change with the contract.
- `coga/internals/state-publication` owns publication behavior, `coga/sync`
  summarizes it, and `coga/principles` §4 supplies the review requirement.
  No publish guard change is planned. If implementation requires one, attach
  and read `coga/internals/git-regressions` before changing that boundary.

<!-- coga:blackboard -->

## Design handoff — 2026-09-26

Investigated the current source and corrected the stale broad-sweep premise.
The remaining gap is `authoring.finalize_authored()` publishing interview
support files. The attending owner answered “ok” to retaining the state-only
sweep and closing that gap with local retention plus visible PR guidance.
The spec above records the chosen scope, alternatives, and limitations.
No code, branch, or PR was created in this design step.

Verification: `PYTHONPATH="$PWD/src" .venv/bin/python -m coga.cli validate
--task keep-agent-edits-to-contexts-and-skills-off-the-co --json` returned
`ok_count: 1`, no issues. `git diff --check` passed. The initial ambient
`python -m coga.cli` attempt lacked `tomlkit`; using the checkout venv resolved
that environment issue. No runtime tests were run for this spec-only step.

## Open Questions

None outstanding from the attended design discussion. Independent evaluation
and the frozen owner review-design gate remain required; this spec is not
self-approved.
