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
step: 4 (review)
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

pr: https://github.com/FastJVM/coga/pull/979
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

## Peer review

Codex peer-review session rebased the feature branch onto `9ddcd7498ac5448b33be695b89ebbc59a7b76979` and
corrected one must-fix issue: the moved text retained the obsolete claim that
Python logic and inability to use an alias justify core placement. It now
summarizes the reviewed/co-versioned contract in `coga/extension-model`, with
a regression assertion. Original implementation was Claude; this correction
was Codex.

`codex review --base main` **returned** on final head `a8bf85ba0b9376679aac7594a57b7b14f421391a`,
base `9ddcd7498ac5448b33be695b89ebbc59a7b76979`, with no actionable regressions. This was a
separate review process, independent of the implementing conversation (the
small Codex correction received same-tool-family review). The sandboxed
invocation could not initialize its app server; the permitted unsandboxed
retry completed. Its 86 focused composition/packaging tests passed.

Full check: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest`
— 3408 passed in 384.22s (0:06:24), Python 3.12.12. The initial ambient
`python -m pytest` failed collection with 33 missing-dependency errors
(`tomlkit`); the complete venv run supersedes that environment failure.

Fresh-init smoke: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python
/tmp/verify-coga-prompt-boundary.py` passed. The relocated section is absent
from the fresh repo's full prompt, and present in this repo's `repo_context`
layer. Correction to the implement handoff: the fresh active design-step
prompt does contain a `src/coga/git.py` citation example from `code/design`;
base/conduct/repo-context layers contain no such path. That generic example
is outside this ticket's base/conduct scope and imposes no source-tree rule.

Read all five base/conduct/blocker resources: the remaining instructions
operate Coga in any repository; the implement handoff's keep rationales hold.
No interactive UI changed; composed text was inspected directly. No terminal
rendering check applies. `git diff --check` and the changed topic's twin
comparison passed. Final branch committed and pushed with force-with-lease;
returned to clean `main` before this handoff. No unresolved findings.

## PR

```yaml
title: Move Coga-development rules out of the shipped base prompt
author: claude
author_evidence: Implement session ran Claude Code (claude-opus-5-5) under megalaunch. Codex peer-review
  session corrected the moved summary to match the current extension-model contract; original implementation
  remains Claude-authored.
head: a8bf85ba0b9376679aac7594a57b7b14f421391a
base: 9ddcd7498ac5448b33be695b89ebbc59a7b76979
depth: skim
rationale: Bounded prompt relocation with no runtime code changes. A separate Codex review returned on
  the final diff, the full suite and fresh-init composition smoke passed. Skim the corrected microkernel
  wording and the intentional repo/template divergence.
implementation: 'Deletes the "Keep Coga small and legible" section from prompt.md, restates it as repo
  context in coga/context.md, marks that file an intentionally divergent twin of the init stub, and adds
  tests keeping Coga-source references out of the packaged prompt layers. The moved summary now follows
  the owning extension-model contract: Python logic alone does not justify a core command.'
deviations: Also updated the coga/codebase/gotchas topic (both twins) so the owning topic records the
  new boundary. Peer review corrected the inherited, outdated command-placement criterion instead of copying
  it unchanged.
limitations: Repo-level prompt overrides remain out of scope. A generic source-citation example in the
  bundled code/design skill still mentions src/coga/git.py; it is not a Coga-development rule in a packaged
  base/conduct layer. Tests ran on Python 3.12.12, not Python 3.11. No terminal UI behavior changed, so
  terminal interaction checks were inapplicable.
files:
  src/coga/resources/prompt.md: Remove the Coga-only section from the shipped base prompt.
  coga/context.md: Carry the section as this repo's context, replacing the init stub.
  tests/test_packaging.py: Declare coga/context.md an intentionally divergent twin of the stub.
  tests/test_compose.py: Guard the packaged layers against Coga-source rules; pin the rule in this repo's
    context; invert the old presence assertions.
  docs/contexts/coga/codebase/gotchas/SKILL.md: Record where Coga-source rules belong.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/gotchas/SKILL.md: Packaged twin of
    the gotchas edit.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: a8bf85ba0b9376679aac7594a57b7b14f421391a
  base: 9ddcd7498ac5448b33be695b89ebbc59a7b76979
  detail: A separate codex review --base main process returned with no actionable regressions after the
    rebase and wording correction. It reviewed the committed diff without the implementing conversation;
    its focused venv run passed 86 composition/packaging tests. The root Codex session made the wording
    fix, so that correction also received same-tool-family review.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest
  status: passed
  head: a8bf85ba0b9376679aac7594a57b7b14f421391a
  base: 9ddcd7498ac5448b33be695b89ebbc59a7b76979
  detail: 3408 passed in 384.22s (0:06:24); Python 3.12.12.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/verify-coga-prompt-boundary.py
  status: passed
  head: a8bf85ba0b9376679aac7594a57b7b14f421391a
  base: 9ddcd7498ac5448b33be695b89ebbc59a7b76979
  detail: Initialized a fresh Git/Coga repo with code/design-then-implement; no moved section in its composed
    prompt and no src/coga/ in its base/conduct/repo-context layers. Coga repo_context explicitly contains
    the section and source boundary. Script and fresh repo are temporary verification artifacts.
- command: git diff --check && cmp docs/contexts/coga/codebase/gotchas/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/gotchas/SKILL.md
  status: passed
  head: a8bf85ba0b9376679aac7594a57b7b14f421391a
  base: 9ddcd7498ac5448b33be695b89ebbc59a7b76979
  detail: No whitespace errors; canonical and packaged gotchas twins remain byte-identical after rebase.
```
