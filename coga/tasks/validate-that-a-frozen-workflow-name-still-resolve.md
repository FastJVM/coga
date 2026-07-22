---
slug: validate-that-a-frozen-workflow-name-still-resolve
title: Validate that a frozen workflow.name still resolves
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - dev/code
skills: []
workflow: code/with-review
secrets: null
script: null
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

`_check_frozen_workflow` (`src/coga/validate.py:750-780`) resolves step
`skills:` refs and warns on an unfrozen (string) workflow, but never checks
`workflow.name` itself. `resolve_workflow_path` (`src/coga/paths.py:32`) is a
pure path lookup with no alias or rename map, so a rename is indistinguishable
from a deletion for an already-frozen ticket.

The three stranded tickets were migrated by hand in PR #627; this ticket is
about catching the next one at validate time rather than at launch.

A live example of rule 2's blast radius: `code/with-review` declares a
`peer-review` step with no `skills:`, so its entire instruction set is the
`## peer-review` section of the workflow file. Renaming that heading would leave
every ticket already frozen on `code/with-review` composing an empty peer-review
step, with `resolve_workflow_path` still succeeding.

**There is no `_check_frozen_workflow` function** — an earlier draft of this
ticket named one and it does not exist; don't grep for it. The frozen-workflow
walk lives in `_check_refs` (`src/coga/validate.py:739`), whose
`isinstance(wf, dict)` branch is lines 767-787 and whose `unfrozen-workflow`
warn is 788-797. Note it has no `skills:`-empty branch today — line 772 is
`for ref_name in step.get("skills", []) or []:`, which simply iterates zero
times — so rule 2 needs a new `if not step.get("skills"):` branch, not a tweak
to an existing one. `inline_instructions` is parsed by `Workflow.load`
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

## Evaluator review

Cold read by an independent session, verbatim. Corrections have been folded into
the body above; the open decisions are still open.

---

## Verdict

The ticket's *reasoning* is sound and the failure mode it describes is real — I reproduced the degradation path end to end. But three of its code citations are wrong or misleading in ways that will cost the implementing agent time, and it omits the single biggest consequence of the change (it isn't confined to `coga validate`). Fix those before launch; the rest is in good shape.

## Technical claims — what's wrong

**`_check_frozen_workflow` does not exist.** The ticket names it three times (lines 72, 87, and implicitly in the Context) and cites `src/coga/validate.py:750-780`. A repo-wide grep for that identifier returns nothing. The function actually meant is `_check_refs` at `src/coga/validate.py:739`; its frozen-workflow branch is lines 767-787 and the unfrozen-string warn is 788-797. The cited 750-780 range straddles the `broken-context` message and the skills loops. Both the name and the range need correcting — an agent that greps the name finds nothing and has to re-derive the entry point.

**`resolve_workflow_path` never signals a miss.** `src/coga/paths.py:32-46` returns a `Path` unconditionally, and its docstring says so explicitly: *"Unlike those resolvers this returns a `Path` rather than `None` when neither exists."* Rule 1's phrasing ("`resolve_workflow_path` must find a file for `workflow.name`") and the Context's parenthetical at line 89-90 ("Rule 1 needs `Workflow.load` (or just `resolve_workflow_path`) rather than a path check alone") both invite the wrong code — a `is None` check that can never fire. The parenthetical is also backwards: a path check alone (`.is_file()`) *is* sufficient for rule 1; `Workflow.load` is needed for **rule 2**, because that's what parses the headings.

**"rule 2 needs exactly the `skills:`-empty branch it is already looking at" — there is no such branch.** `src/coga/validate.py:772` is `for ref_name in step.get("skills", []) or []:`; an empty list just iterates zero times. Rule 2 requires a new `if not step.get("skills"):` branch. Minor, but it makes the work sound smaller than it is.

**Rule 2's predicate as written is too weak and will miss a real case.** `_parse_inline_sections` (`src/coga/workflow.py:145-160`) stores `body[start:end].strip()`, so a heading with no prose under it maps to `""`. Compose's gate is `if inline:` (`src/coga/compose.py:364-365`), which is falsy for `""`. So a *present but empty* `## peer-review` heading composes `*No instructions attached to this step.*` while satisfying the ticket's stated rule ("the resolved workflow must contain a matching `## <step-name>` section"). Implement the check as `not Workflow.load(...).inline_instructions.get(step_name)` so validate and compose agree by construction. Also: `_parse_inline_sections` matches step names **case-sensitively** (`if heading in step_names`) whereas the neighbouring `_extract_section` (`src/coga/compose.py:302-311`) is case-insensitive — reuse `inline_instructions`, don't re-implement heading matching.

**Rule 1's predicate is probably "`Workflow.load` fails", not "file missing".** `src/coga/compose.py:355` catches a bare `except Exception:`, so a *malformed* workflow file (bad frontmatter, empty `steps:`) degrades to the same `*Workflow definition not found...*` placeholder as a deleted one. If the stated goal is "flag every case where the ticket composes a placeholder," rule 1 must fire on any `WorkflowError`, not only a missing file. The ticket's deleted-or-renamed framing misses this. Cheap to include, but it changes both the predicate and the error message, so decide before implementing.

**Minor citation drift:** `src/coga/compose.py:352` is `return []` (the no-workflow-name early return), not the inline branch it's cited for — the meaningful anchors are :349 (comment) and :364-365 (the gate). The `*No instructions attached to this step.*` literal is at :376, not :375.

## Technical claims that check out

`Workflow.freeze` (`src/coga/workflow.py:84-97`) snapshots only `name`/`skills`/`assignee`/`requires` — no prose. Correct. `inline_instructions` is parsed by `Workflow.load` at `src/coga/workflow.py:71` — exactly right. The `*Workflow definition not found...*` literal at `src/coga/compose.py:360` — right. The `code/with-review` example is verified: `peer-review` declares no `skills:` (`src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md:9-10`) and its whole instruction set is the `## peer-review` section at :44. PR #627 is verified: commit `9d3ea027` deleted `.../templates/coga/workflows/autonomy/{fully-automated,human-verify}.md` and carries a "Migrate live tickets off deleted autonomy/* workflows" commit.

## The consequence the ticket doesn't mention

The Description frames this as "`coga validate` never checks…". But `_check_refs` runs inside `_check_one_task`, which is also reached by `validate_task_dir` → `assert_task_valid` (`src/coga/validate.py:317-333`), and `assert_task_valid` **raises** on any error. Its callers: `src/coga/bump.py:110`, `src/coga/create.py:235`, `src/coga/authoring.py:123`, `src/coga/mark.py:137,194,443,469,498,542`, `src/coga/commands/bump.py:102`.

So the moment a workflow file is deleted, every stranded ticket becomes un-`bump`-able and un-`mark paused`-able — those commands hard-fail rather than degrading. That may be the intent, but it is a far larger behavior change than "add a check to validate," and it should be a stated decision (error vs. warn) rather than something discovered mid-implementation.

The escape hatches also come out asymmetric under the ticket's chosen status set: `coga mark done` / `mark canceled` / `mark blocked` still work (the post-edit status falls outside `{active, in_progress, paused}`), but `coga mark paused` does not. That asymmetry is arbitrary and worth designing away.

## Status scoping contradicts its own stated precedent

The ticket scopes to `active` / `in_progress` / `paused` and claims "the severity matches `active-no-workflow`." But `active-no-workflow` fires on `{"active", "in_progress", "blocked", "paused"}` (`src/coga/validate.py:884`). `blocked` is dropped with no explanation; a blocked ticket gets unblocked and launched and strands identically. Either include it or say why not — simplest consistent rule is to reuse the set at validate.py:884 verbatim.

Relatedly, the "natural home" claim deserves pushback: `_check_refs` is currently status-blind (it reports `broken-context`/`broken-skill` on `done` tickets too). Adding the first status conditional there is against the grain. `_check_workflow_shape` (`src/coga/validate.py:850`) is the status-aware function and already owns `active-no-workflow`. Worth at least considering.

## Missing surface: docs and contexts

Per CLAUDE.md ("if behavior changes, update the matching context or source doc in the same PR"), two places enumerate what `coga validate` enforces about workflows and will go stale:

- `src/coga/validate.py:18-29` — the module docstring's "Checks (whole-repo)" list.
- `coga/contexts/coga/architecture/SKILL.md:240-248` — the paragraph spelling out the workflow invariants validate enforces — plus its packaged mirror at `src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md:238-246`.

That live/packaged pair is *not* in `IDENTICAL_LIVE_PACKAGED_PAIRS` (`tests/test_packaging.py:89-106`), so nothing will fail the build if it's skipped — which is precisely why it belongs in the ticket. The ticket mentions no doc work at all.

## Testing — two facts the ticket could have handed over

The "byte-identical validate output" regression framing is good and directly testable. Two things I confirmed that would have saved the implementer a lap:

- The shared fixture at `tests/test_validate.py:39-49` writes a `code/with-review.md` whose body is **empty** and whose two steps (`implement`, `pr`) both declare no `skills:`. That is a ready-made rule-2 violation — create an `active` ticket on it and the check fires, no new fixture needed. Only two tests currently create non-draft tickets on that fixture (`tests/test_validate.py:523` and `:1195`) and neither asserts a clean report, so no existing test breaks.
- I ran both rules against every live ticket in this repo: **zero violations of either rule today.** The check ships green and needs no migration — but that also means the regression tests are the only proof it works. Worth stating so nobody hunts for stranded tickets.

## One risk worth a line in the ticket

Rule 1 resolves through `resolve_workflow_path`'s bundled fallback (`src/coga/paths.py:41-45`), i.e. against the **installed package's** `bootstrap/workflows/`. This very ticket is frozen on `code/with-review`, which exists *only* under `src/coga/resources/templates/coga/bootstrap/workflows/` — there is no `coga/workflows/code/with-review.md`. So the new check's verdict depends on the installed wheel's vintage; see the installed-versus-source skew note at `coga/contexts/coga/codebase/SKILL.md:175-191`. A stale install could produce a spurious dangling-workflow **error** and a non-zero exit. Decide whether that's acceptable or whether bundled-resolved workflows warrant a softer severity.

## Workflow fit

`code/with-review` fits. Real source change, testable behavior delta, and non-trivial blast radius across `bump`/`mark`/`create` — a peer-review pass before the PR is earned. No change recommended.

## Contexts

`dev/code` (4.9 KiB) — correct and necessary. The workflow produces a branch and PR, and this context defines the `## Dev` blackboard shape that the `open-pr` step's `requires: pr` gate reads.

`coga/codebase` (13.1 KiB, ~41% of the total prompt) — over the flag line and the one concrete trim candidate. It does earn part of its keep: the "Tests must not pin to live dogfooded state" gotcha (`coga/contexts/coga/codebase/SKILL.md:231-241`) is directly on point for a validate regression test, and the `coga validate --task <slug>` scoping advice (:211-214) is the right verification command. But everything the implementer actually needs from it is about six lines — `validate.py` owns the checks, run `python3.12 -m pytest`, scope with `--task`, don't pin tests to live dogfooded state, keep live/packaged template pairs in sync. Copy those into `## Context` and drop the context: ~3,300 tokens, 40% of the prompt, for no loss.

Nothing important is missing. `coga/architecture` is the tempting add since it owns freezing/locking, but at 37.9 KiB it would dominate the prompt — and the ticket has already inlined the relevant freeze semantics into `## Context` (lines 64-70), which is the right call.

## Scope

Reasonable: one function, two rules, two tests. The explicit out-of-scope note on broader frozen-vs-current drift (lines 51-55) is good and should stay. The only thing that could inflate it is the `assert_task_valid` blast-radius question — if the answer is "warn instead of error," that stays in scope; if it becomes "introduce a severity that validate reports but `assert_task_valid` ignores," that is a separate ticket.

## Assumptions to settle before launch

1. Error or warn, given `assert_task_valid` raises and gates `bump`/`mark`/`create`?
2. Why is `blocked` excluded when the cited precedent includes it?
3. Rule 1: missing file only, or any `Workflow.load` failure (matching compose's bare `except Exception`)?
4. Rule 2: heading present, or non-empty instructions (matching compose's `if inline:`)?
5. Is a spurious error from installed-vs-source workflow skew acceptable?
