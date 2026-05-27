The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

**Overall:** Solid ticket. An implementing agent can start without back-and-forth. The five numbered steps map cleanly to concrete edits, the scaffolder file is named, the sync rule is called out, and out-of-scope is explicit. Title is rough ("permant"), but content is good.

**Workflow fit (`code/with-review`):** Right call. There is a real code change in `src/relay/recurring.py`, a test, and shipped-context edits that warrant human PR review. Not too big — three files plus one new context plus tests. Not too small for review either, because the auto-attach behavior is a contract change for every existing/future recurring task.

**Context attachment (`relay/recurring`):** Correct. The ticket modifies that context directly and depends on the scaffold contract documented there. Nothing critical is missing from `## Context` — the slug-derivation rule, sync-rule reminder, and the `scaffold_template` location are all carried in.

**Scope / step #3 tension:** I don't see real tension. Step 3 is a *minor* trim to the same context (move the per-run procedure to `relay/period-task`, keep author framing). It belongs in this PR — leaving `relay/recurring` duplicating the new context's content would defeat the de-duplication the ticket exists to do. The five steps are one coherent unit.

**Assumptions to question:**

1. **Packaged-context path is wrong.** The ticket says "packaged copy under `src/relay/resources/templates/relay-os/contexts/`" — but that directory holds only `_template/`. Live contexts ship from `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/`. An agent following the ticket literally will create a file in the wrong place. Fix the path before handing this off.
2. **Scaffolder passthrough is verified — minor cleanup.** Line 275 of `recurring.py` does `contexts=list(template.frontmatter.get("contexts") or [])`, and `scaffold_task` accepts it. So appending `relay/period-task` there (with idempotency check) is a 2-line change. The ticket's "wherever the period task's `contexts:` is composed" hedge is unnecessary — point straight at line 275.
3. **"Append on every scaffold" vs opt-in:** Ticket commits to always-append, idempotent. Reasonable default — the convention applies to every period task by definition — but worth one sentence justifying it over an opt-out flag.
4. **`_rem` mention in step 4** is vague ("update the `_rem` template comments similarly"). Agent should be told whether `_rem` actually contains the rule today; otherwise it's a fishing expedition.
5. **No mention of `recurring/dream`**, which is also workflow-less and might hand-roll the same paragraph. Worth one line confirming it's checked or explicitly out of scope.

## Dev

branch: feat/period-task-context
worktree: /home/n/Code/claude/relay-period-task-ctx
pr: https://github.com/FastJVM/relay/pull/231

## Implement notes

- Scaffolder (`src/relay/recurring.py`): appended `"relay/period-task"`
  to the `contexts` list passed to `scaffold_task`, with an
  `if "relay/period-task" not in contexts` idempotency check.
- New context: `relay-os/contexts/relay/period-task/SKILL.md` and its
  packaged twin under
  `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/period-task/SKILL.md`.
  The packaged copy had to be added with `git add -f` because
  `src/relay/resources/templates/relay-os/.gitignore` ignores
  `bootstrap/` (it's the gitignore shipped *into* generated repos, not
  meant to apply to the source tree — the existing four contexts there
  were force-added the same way).
- Trimmed `relay-os/contexts/relay/recurring/SKILL.md` — kept the
  author-facing "state lives in the recurring task's blackboard"
  framing, dropped the per-run read/update procedure, pointed at the
  new context.
- `relay-os/recurring/relay-dev-update/ticket.md`: collapsed Step 1
  ("State lives in this recurring task's own persistent blackboard…")
  and Step 5 ("Update the … blackboard — `relay-os/recurring/…` —")
  to just name the parent recurring task's blackboard generically.
  Steps still name `last_commit` and the `### Dev Update State`
  section — only the path-teaching prose was dropped.
- Tests: added `_seed_period_task_context` helper in
  `tests/test_recurring.py` (every fixture now seeds a stub
  `relay/period-task` context so `scaffold_task`'s context resolver
  doesn't reject the auto-appended ref). Same one-line stub added to
  `tests/test_create.py`'s `repo` fixture (its `repo_with_shim`
  variant covers `test_recurring_scaffolds_and_broadcasts`). New
  tests: `test_scaffold_auto_attaches_period_task_context` and
  `test_scaffold_does_not_duplicate_explicit_period_task_context`.
- `python -m pytest`: 425 passed, 1 skipped.
- `relay validate --json` against the worktree (with `bootstrap/`
  copied in from the primary checkout — `relay-os/bootstrap/` is
  gitignored and absent from a fresh worktree): 34 ok, 0 errors,
  same warning set as `main`.

Committed on `feat/period-task-context` (commit 18da579). No push, no
PR yet — that's `code/open-pr`'s job.
