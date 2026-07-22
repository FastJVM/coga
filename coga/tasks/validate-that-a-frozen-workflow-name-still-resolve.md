---
slug: validate-that-a-frozen-workflow-name-still-resolve
title: Validate that a frozen workflow.name still resolves
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

`coga validate` never checks that a ticket's frozen `workflow.name` still
resolves to a workflow file. Add that check, so deleting or renaming a workflow
surfaces the tickets it strands instead of degrading them silently at launch.

Two rules, both **errors**, both scoped to live tickets with a frozen
`workflow`. For the status set, reuse the `active-no-workflow` set verbatim —
`{"active", "in_progress", "blocked", "paused"}` (`src/coga/validate.py:884`).
Take it from that constant rather than re-typing it, so the two checks can't
drift apart. `blocked` is included deliberately: a blocked ticket gets
unblocked and launched, and strands identically. A `done` ticket is finished
and immutable; leave it alone.

The severity matches `active-no-workflow` because in every case below the
ticket composes a placeholder instead of its step instructions.

1. **Unloadable workflow.** `Workflow.load(resolve_workflow_path(cfg, name))`
   must succeed. Note `resolve_workflow_path` (`src/coga/paths.py:32`) returns a
   `Path` **unconditionally** — it never returns `None`, and falls back to the
   local path so the caller's `Workflow.load` raises a not-found error naming
   the conventional location. So the predicate is "the load raises", not "the
   resolver returned nothing". Phrase it as a load attempt, not an `is None`
   check that can never fire.

   Match compose's own gate rather than narrowing to a deleted file: `compose`
   catches a bare `except Exception` (`src/coga/compose.py:355`), so a
   *malformed* workflow (bad frontmatter, empty `steps:`) degrades to the same
   `*Workflow definition not found; using frozen snapshot only.*` placeholder
   (`src/coga/compose.py:360`) as a deleted one. Both should be flagged.

2. **Step with no instructions.** For a frozen step with an **empty `skills:`
   list**, `wf.inline_instructions.get(step_name)` must be non-empty. A step
   with no skills draws its instructions solely from that inline prose;
   otherwise it composes `*No instructions attached to this step.*`
   (`src/coga/compose.py:376`) and the agent launches with no idea what the
   step is for.

   Test for **non-empty instructions, not a present heading.**
   `_parse_inline_sections` (`src/coga/workflow.py:145`) stores
   `body[start:end].strip()`, so a heading with nothing under it maps to `""`,
   and compose's gate is `if inline:` (`src/coga/compose.py:364`) — falsy for
   `""`. A present-but-empty `## <step-name>` therefore strips instructions
   while satisfying a naive heading-exists check. Reusing
   `inline_instructions` also inherits its matching rules; do not
   re-implement heading matching (note it is case-**sensitive**, unlike the
   neighbouring `_extract_section` at `src/coga/compose.py:302`).

Rule 2's `skills:`-empty condition is the whole subtlety and must not be
dropped: a step whose instructions come from `skills:` refs legitimately has no
`## <step-name>` section, so an unconditional heading check would fire on most
steps in the repo. Only the skill-less steps depend on the heading. Note also
that rule 2 can fire while rule 1 passes — the workflow file is present, but a
step was renamed or its prose removed after the ticket froze.

### Decided: the blast radius is intended, not a side effect

`error` severity here reaches well past `coga validate` output, and that was
weighed and accepted — do not soften it on discovery. `_check_refs` runs inside
`_check_one_task`, which `assert_task_valid` also reaches
(`src/coga/validate.py:317`), and that function **raises** on any error. It
gates `src/coga/bump.py:110`, `src/coga/create.py:235`,
`src/coga/authoring.py:123`, `src/coga/commands/bump.py:102`, and all six
`mark` transitions (`src/coga/mark.py:137,194,443,469,498,542`).

Consequence: the moment a workflow file is deleted, every ticket frozen on it
becomes un-`bump`-able and un-`mark paused`-able — those commands hard-fail
rather than degrade. `mark done` / `mark canceled` / `mark blocked` still work,
since the post-edit status falls outside the live set. Recovery is a human
editing the frozen `workflow.name` by hand.

That is the intended stance: deleting a workflow that live tickets are frozen
on should stop the line, the same way `active-no-workflow` does. The
`mark paused` asymmetry is a known, accepted wart. If implementing this makes
the cost look worse than it does here, raise it with the owner rather than
downgrading to `warn` — the severity is the point of the ticket.

Scope note: rule 2 compares the *frozen* step names against the *current*
workflow file. Broader frozen-vs-current drift (steps added, removed, or
reordered; `assignee` or `requires` changed) is a real question but is out of
scope here — this ticket only covers the two cases that strip instructions from
a composed prompt.

## Context

Found while reviewing PR #627 (`remove-autonomy-triage`), which deleted the
`autonomy/*` workflows. Three live tickets were still frozen on them, and
nothing flagged it — `coga validate --json` output was byte-identical before
and after the deletion.

Why it degrades silently: `Workflow.freeze()` (`src/coga/workflow.py:84`)
snapshots only each step's `name` / `skills` / `assignee` / `requires`. The
inline `## <step-name>` prose is **not** frozen — `compose._step_layers`
(`src/coga/compose.py:326`) re-resolves the workflow file by name at launch and
falls back to `*Workflow definition not found; using frozen snapshot only.*`
(`src/coga/compose.py:360`) when it is missing. So a deleted workflow silently
strips step instructions from every frozen ticket pointing at it.

`_check_refs` (`src/coga/validate.py:739`) already walks the frozen workflow: its
`isinstance(wf, dict)` branch resolves each step's `skills:` refs (767-787) and
warns on an unfrozen (string) workflow (788-797). It never checks
`workflow.name` itself. And `resolve_workflow_path` (`src/coga/paths.py:32`) has
no alias or rename map, so a rename is indistinguishable from a deletion for an
already-frozen ticket.

The three stranded tickets were migrated by hand in PR #627; this ticket is
about catching the next one at validate time rather than at launch.

A live example of rule 2's blast radius: `code/with-review` declares a
`peer-review` step with no `skills:`, so its entire instruction set is the
`## peer-review` section of the workflow file. Renaming that heading would leave
every ticket already frozen on `code/with-review` composing an empty peer-review
step, with `resolve_workflow_path` still succeeding.

Note there is **no `_check_frozen_workflow` function**, despite the name being an
easy guess for the walk described above — don't waste a grep on it. Note also
that `_check_refs` has no `skills:`-empty branch today: line 772 is
`for ref_name in step.get("skills", []) or []:`, which simply iterates zero
times. Rule 2 therefore needs a new `if not step.get("skills"):` branch, not a
tweak to an existing one. `inline_instructions` is parsed by `Workflow.load`
(`src/coga/workflow.py:71`), so one load serves both rules.

Placement is worth a moment's thought rather than defaulting to `_check_refs`:
that function is deliberately status-blind (it reports `broken-context` /
`broken-skill` on `done` tickets too), so a status conditional there cuts
against the grain. `_check_workflow_shape` (`src/coga/validate.py:850`) is the
status-aware function and already owns `active-no-workflow`.

Regression test to beat: the bug's signature was that `coga validate --json` was
byte-identical before and after the workflow deletion. A test that freezes a
ticket on a workflow, deletes the file, and asserts a new error appears in the
JSON output covers rule 1; the same shape with an emptied `##` section covers
rule 2.

The existing fixture is already a rule-2 violation, so no new fixture is needed:
`tests/test_validate.py:39` writes a `code/with-review.md` with an **empty body**
whose two steps (`implement`, `pr`) both declare no `skills:`. Create an `active`
ticket on it and rule 2 fires. Only two tests create non-draft tickets on that
fixture (`tests/test_validate.py:523` and `:1195`) and neither asserts a clean
report, so neither should break — verify that rather than assuming it.

**Both rules pass against every live ticket in this repo today**, so the check
ships green and needs no ticket migration. That also means the regression tests
are the only proof it works — don't go hunting for a stranded ticket to confirm
against.

Docs to update in the same PR (per CLAUDE.md: behavior change → update the
matching context or source doc):

- `src/coga/validate.py:18-29` — the module docstring's "Checks (whole-repo)" list.
- `coga/contexts/coga/architecture/SKILL.md:240-248` — the paragraph listing the
  workflow invariants validate enforces — **and** its packaged mirror at
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md:238-246`.
  That pair is *not* in `IDENTICAL_LIVE_PACKAGED_PAIRS`
  (`tests/test_packaging.py:89`), so nothing fails the build if you skip it.

### Working notes for editing coga's own source

The `coga/codebase` context was deliberately **not** attached — at 13.1 KiB it
was ~41% of this ticket's composed prompt. These are the five facts from it that
this ticket actually needs; read the full context only if you need more:

- `src/coga/validate.py` owns the checks; `tests/` is pytest.
- **Run the suite with an explicit 3.11+ interpreter** — coga needs `tomllib`,
  and the ambient `python3` on these machines is often 3.9 (confirmed on this
  one). Use `PYTHONPATH=$PWD/src python3.12 -m pytest` rather than trusting
  `python3` or a stale `.coga/.venv`. `PYTHONPATH` must be **absolute** — the
  script-launch subprocess tests run from a different cwd.
- **Scope validation with `coga validate --task <slug>`.** A repo-wide
  `coga validate` reports pre-existing unrelated drift and drowns the signal.
- **Tests must not pin to live dogfooded state.** Coga dogfoods itself, so files
  under `coga/` mutate as the repo is used. Assert structure, not hardcoded
  values; strip runtime-mutated fields. This one is directly on point — the
  regression tests here must build their own fixture workflow and ticket, not
  assert against whatever live tickets happen to exist.
- Keep live `coga/` and packaged
  `src/coga/resources/templates/coga/` copies in sync (see the docs list above).

Known risk — installed-vs-source skew. `resolve_workflow_path` falls back to the
**installed package's** `bootstrap/workflows/` (`src/coga/paths.py:41-45`). This
very ticket is frozen on `code/with-review`, which exists only under
`src/coga/resources/templates/coga/bootstrap/workflows/` with no repo-local
copy. So a stale installed wheel could make rule 1 report a spurious error and
exit non-zero. See the skew note at `coga/contexts/coga/codebase/SKILL.md:175-191`.
Decide whether that is acceptable or whether bundled-resolved workflows warrant
a softer severity.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
