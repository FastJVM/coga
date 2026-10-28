---
title: Stop the contexts-root sweep from publishing canonical topics without their
  packaged twins
status: draft
owner: nicktoper
contexts:
  - coga-dev/principles
workflow: code/design-then-implement
---

## Description

Coga keeps hand-maintained byte-identical twins: packaged resources under `src/coga/resources/templates/coga/` with a live counterpart in this repo (`docs/contexts/<ref>` for contexts; `coga/<path>` for skills, workflows, recurring tickets, scaffolding). Both live trees are Coga roots, so a state sweep on a feature branch (bump, `coga create`, …) publishes the live half straight to control while the packaged half travels only in the PR, and main fails `tests/test_packaging.py` until the PR merges. Observed 2026-10-21: 001aad66f (blocks/02's deletion of `docs/contexts/coga/code/` and architecture edits) and e9a88b970 (blocks/09's topic edits, from a `coga create` sweep).

Owner decision: shipped resources live **only in the wheel** and are read from it, read-only. The package tree under `src/coga/resources/` is the single committed source; repos (this one included) hold only their own overrides and real state, never copies of shipped files. That removes the drift and makes upgrades a package bump instead of a re-copy. Recurring tickets must work this way too, which needs a package fallback that does not exist today.

Rejected alternatives: excluding twin paths from the sweep, or publishing both halves together. Both treat the symptom and keep the duplication that produces drift.

Done when:
- No shipped resource is committed twice: the live copies under `docs/contexts/coga/**` and `coga/{skills,workflows,recurring}/**` that duplicate the package are deleted, and this repo resolves them from the package. The only remaining pairs are files that differ by design (see Context).
- Recurring parents shipped by the package (`autoclose-merged`, `branch-sweep`, `blocker-reminders`, `dream`, `phone-home`, `skill-update`, `address-pr-comments`, `resolve-conflicts`) are discovered and run from the wheel when the repo has no local override, and a local override still wins.
- Both an editable install and a wheel built from a fresh clone serve every fallback context, init scaffold, bundled battery, and recurring parent.
- `tests/test_packaging.py` asserts single-source (no shipped file duplicated in a live root, except the documented exceptions; `coga-dev/` never ships) instead of byte-identity, plus a regression test showing that a feature-branch sweep which edits a shipped resource cannot leave main's packaging tests red.
- Docs follow: `docs/README.md`, `AGENTS.md`, and cross-topic links point at the package paths, with `test_context_navigation_has_no_broken_links` green. `coga-dev/packaging`, `coga-dev/testing`, `coga-dev/codebase`, and the twin paragraph in `AGENTS.md` describe the new rule.

## Context

### Background

The twins are historical, not designed. `relay init` once vendored package content into each repo, and this repo dogfooded (e8fac886f). Then 340ef8033 made fallbacks resolve from the wheel. Finally #875 (5c917004d) moved the contexts root to `docs/contexts/` and hand-mirrored every user topic into the package, with byte-identity tests as the drift guard. The owner authorizes the `design` step to read `docs/archive/` for a recorded twin rationale only; if one turns up that conflicts with the decision above, raise it at `review-design` rather than deviating.

### Facts the design depends on (verified 2026-10-27)

- Skills and workflows already resolve local-first and fall back to package `bootstrap/` (`paths.resolve_skill_path`, `paths.resolve_workflow_path`). Contexts fall back to `bootstrap/contexts` when absent from the contexts root (`paths.resolve_context_path`). For these, deleting the live copies is mostly enough.
- Recurring parents have **no** package fallback: `paths.recurring_dir(cfg)` is just `cfg.repo_root / "recurring"`. Its consumers (state publication in `git`, `logfile`, `retire_worklist`, the recurring scheduler/launch) must learn to merge package parents with local ones. Recurring runs produce period tasks and per-repo state; decide where that state lives when the parent is read-only in the wheel.
- Resources are read via `files("coga.resources").joinpath("templates", "coga", …)` (`paths.py`). Under `pip install -e` that is `src/coga/` directly, so editable installs work with no build step once the package is the source.
- Some files must stay physically in a repo: `coga/.gitattributes` (git applies `merge=union` only from a real file), and the `INTENTIONALLY_DIVERGENT_TWINS` entries in `tests/test_packaging.py` (`coga/.gitignore`, `coga/coga.toml`, `coga/context.md`, `coga/log.md`, `coga/recurring/phone-home/ticket.md`), where the live copy is this repo's real state. Keep these as explicit exceptions, or justify a change.
- `coga-dev/` topics are local-only (`LOCAL_ONLY_CONTEXT_NAMESPACES`) and stay in `docs/contexts/coga-dev/`. Their relative links into `coga/*` topics must be repointed. The audience criterion is owned by `coga/context-layout` (cited; read "Context audiences").
- `coga-dev/packaging` ("Wheel packaging") warns that hatch walk + force-include collisions show up only on a pristine tree. Verify the built wheel from a fresh `git clone`/`git worktree`.

### Open for the `design` step

- Adopting repos: does `coga init` keep seeding copies (e.g. `coga/recurring/*`, `coga/workflows/*`) into new repos, or stop now that they resolve from the wheel? The owner's intent ("read only in wheel files, makes updates easier") points toward stopping. Confirm the migration story for repos that already hold seeded copies (are stale identical copies left as overrides?) at `review-design`.
- Splitting: contexts, bundled skills/workflows, and recurring/init seeds are largely independent. If the PR gets unwieldy, propose sibling tickets under a plain directory per `coga/tickets/discovery`.

### Cited, not attached

- `coga-dev/packaging` (`docs/contexts/coga-dev/packaging/SKILL.md`): will be edited. Read "Canonical copies and twins" and "Wheel packaging".
- `coga/context-layout` (`docs/contexts/coga/context-layout/SKILL.md`): "Context audiences".
- `coga/recurring` topics (`docs/contexts/coga/recurring/`): how parents, period tasks, and scheduling work today.
- Sweep mechanics, for the failure only: `git.coga_root_paths` and `git._state_areas` publish the Coga root and `cfg.contexts_root`.

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
