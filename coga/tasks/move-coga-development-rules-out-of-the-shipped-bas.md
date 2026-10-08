---
title: Move Coga-development rules out of the shipped base prompt
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (peer-review)
contexts:
- coga/prompt-composition
- coga/packaging
agent: claude
---

## Description

The packaged base prompt (`src/coga/resources/prompt.md`) ships a section that
only makes sense when the repo being worked on is Coga itself: "Keep Coga small
and legible" (lines 98–116, 139 words). It opens with "When changing Coga
itself, preserve its microkernel boundary" and talks about `src/coga/`,
`runner.RECIPES` and wheel-owned edge modules.

Because `prompt.md` is read only from the installed package, every user gets
this section in every launch, in repos that have nothing to do with Coga. It
costs tokens on each launch and gives an agent working on someone else's
project rules about a codebase it is not in.

Move the section to where it belongs: the Coga repo's own `coga/context.md`,
which is composed into every task prompt in this repo and is currently the
untouched `coga init` template stub. Coga's own tickets keep the rule; nobody
else receives it.

Done means:

- The "Keep Coga small and legible" section is gone from
  `src/coga/resources/prompt.md`.
- Its content is in this repo's `coga/context.md`, replacing the template stub
  text, with wording adjusted so it reads as repo context rather than a
  conditional ("When changing Coga itself…" becomes a plain statement about
  this repo).
- The rest of `prompt.md` and the session-conduct layers
  (`prompt-attended.md`, `prompt-megalaunch.md`, `prompt-queue.md`,
  `prompt-blocker-resolution.md`) have been read with one question: does this
  rule make sense in someone else's repo? Each rule that only fits the Coga
  repo is moved the same way, or the reason to keep it is written on the
  blackboard.
- A test guards the boundary: the packaged prompt layers contain no reference
  to `src/coga/` or other Coga-source paths.
- Verified by composing a prompt in a fresh `coga init` repo (section absent)
  and in this repo (section present, via `coga/context.md`).

## Context

- Evidence (2026-10-07): in a fresh `coga init` repo with coga 0.4.0, the
  composed prompt for a `code/design-then-implement` ticket contains both
  "microkernel boundary" and `src/coga/`.
- `compose._resource()` reads `prompt.md` and the conduct layers through
  `paths.read_packaged_resource`, with no repo-first lookup. Workflows, skills
  and contexts do have repo-first resolution (`resolve_workflow_path`,
  `resolve_skill_path`); the base prompt does not.
- No test currently references the section text (grep for "Keep Coga small"
  and "microkernel boundary" finds only `prompt.md`).
- First read of the rest of `prompt.md`: the loop, ticket/blackboard,
  finishing the step, blocking and boundaries sections are about operating
  Coga and apply to any repo. One phrase to reconsider: the opening "this
  team's repo-level company OS" is FastJVM's framing, not necessarily a
  user's. `coga/launch` and `coga/packaging`, which the prompt cites, ship as
  bootstrap contexts, so those references resolve for users.
- Out of scope: letting a repo override `prompt.md` and the conduct layers.
  That is `overload-base-text-prompt-etc`. This one removes repo-specific
  content so the shared base is right for everyone, with or without an
  override, and comes first.
- Keep everything in this ticket's body inside `## Description` and
  `## Context`: the composer currently drops any other level-two section.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: base-prompt-coga-rules

Plan: move the "Keep Coga small and legible" section into coga/context.md
(rewritten as repo context), mark the coga/context.md twin intentionally
divergent, add a test that packaged prompt layers carry no Coga-source paths.

## Implement handoff

Changed (branch `base-prompt-coga-rules`, commit 32d67513d, pushed):

- `src/coga/resources/prompt.md`: "Keep Coga small and legible" section removed.
- `coga/context.md`: stub replaced with a short "this repo is Coga" intro plus
  the section, reworded as a plain statement ("Preserve Coga's microkernel
  boundary") with a pointer to `coga/extension-model`.
- `tests/test_packaging.py`: `coga/context.md` added to
  `INTENTIONALLY_DIVERGENT_TWINS`. It pairs with the init stub
  `templates/coga/context.md`, which must stay a stub for fresh repos.
- `tests/test_compose.py`: new `test_packaged_prompt_layers_carry_no_coga_source_rules`
  (prompt.md, blocker preamble, every `SESSION_CONDUCT_RESOURCES` entry;
  markers `src/coga`, `coga_edge`, `runner.RECIPES`, `microkernel`,
  "When changing Coga itself") and `test_coga_repo_context_carries_the_minimal_core_boundary`.
  `test_base_prompt_teaches_exit_after_bump` now asserts the rule is absent
  from a generic repo's prompt; before, it pinned it as present.
- `coga/codebase/gotchas` (canonical + packaged twin): the prompt-resources
  gotcha now says packaged prompt layers reach every repo, so Coga-source
  rules belong in `coga/context.md`.

Review of the remaining layers (the question was "does this make sense in
someone else's repo?"):

- prompt.md loop / ticket+blackboard / finishing / blocking / boundaries: all
  about operating Coga in any repo. Kept.
- Opening "this team's repo-level company OS": kept. Coga is a repo-level
  company OS, and "this team" is whichever team installed it, so it isn't
  FastJVM-specific.
- `dev/design-history`, `coga/launch`, `coga/packaging` references: bundled
  bootstrap contexts, so they resolve for users. Kept. The deleted section
  was the only `coga/packaging` reference.
- Conduct layers (attended, megalaunch, queue) and blocker preamble: no
  Coga-source rules. The `/tmp` clone fallback points at the bundled
  `code/implement` skill, so it applies anywhere. Kept.

Verification: composed `code/design-then-implement` in a fresh `coga init`
repo, with "Keep Coga small", "microkernel boundary" and `src/coga/` all
absent. Composed this ticket in this repo, with all three present (via
`coga/context.md`).

## PR

```yaml
title: Move Coga-development rules out of the shipped base prompt
author: claude
author_evidence: Implement session ran Claude Code (claude-opus-5-5) under megalaunch.
head: 32d67513d7eda2c4409be3ac88135011e473bdc0
base: 2338765f9858f77eea537a5ca88f9bbcde064946
depth: skim
rationale: Moves one prose section from the shipped prompt into this repo's context and adds guard tests. No runtime logic changes.
implementation: Deletes the "Keep Coga small and legible" section from prompt.md, restates it as repo context in coga/context.md, marks that file an intentionally divergent twin of the init stub, and adds tests keeping Coga-source references out of the packaged prompt layers.
deviations: Also updated the coga/codebase/gotchas topic (both twins) so the owning topic records the new boundary.
limitations: Repo-level override of prompt.md stays out of scope (overload-base-text-prompt-etc).
files:
  src/coga/resources/prompt.md: Remove the Coga-only section from the shipped base prompt.
  coga/context.md: Carry the section as this repo's context, replacing the init stub.
  tests/test_packaging.py: Declare coga/context.md an intentionally divergent twin of the stub.
  tests/test_compose.py: Guard the packaged layers against Coga-source rules; pin the rule in this repo's context; invert the old presence assertions.
  docs/contexts/coga/codebase/gotchas/SKILL.md: Record where Coga-source rules belong.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/gotchas/SKILL.md: Packaged twin of the gotchas edit.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: The peer-review step comes next in the workflow and has not run yet.
checks:
  - command: python -m pytest
    status: passed
    head: 32d67513d7eda2c4409be3ac88135011e473bdc0
    base: 2338765f9858f77eea537a5ca88f9bbcde064946
    detail: 3408 passed in 347.95s, run on the committed, rebased head.
  - command: compose_prompt on a fresh coga init repo (code/design-then-implement) and on this ticket in this repo
    status: passed
    head: 32d67513d7eda2c4409be3ac88135011e473bdc0
    base: 2338765f9858f77eea537a5ca88f9bbcde064946
    detail: Fresh repo has no section or src/coga/; this repo has both.
```
