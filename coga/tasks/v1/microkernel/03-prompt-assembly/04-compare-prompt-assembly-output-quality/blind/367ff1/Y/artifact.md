# Pair 367ff1, output Y (design)

## Ticket after the design step (full)

````markdown
---
title: Warn when coga delete or coga retire leaves a live link to the deleted ticket
status: in_progress
owner: nicktoper
agent: codex
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 2 (evaluate-design)
---

## Description

Deleting a ticket can break durable navigation: ordinary `coga delete` and the deterministic done-ticket path of `coga retire` currently remove it without checking inbound references. Retro already inspects and repairs references, but these paths bypass that procedure. Add an advisory check to the shared deletion primitive so operators see potential breakage before removal.

### Acceptance criteria

- [ ] Before removing a valid resolved ticket, `run_delete_task()` searches tracked working-tree text for the target's Git-root-relative artifact path and final slug component (without `.md`). Cover file and directory forms, nested task refs, configured task roots, and invocation below the Git root. The leaf search catches links such as `../tasks/example.md` and `../example/ticket.md` that omit the full root prefix.
- [ ] Exclude the entire configured ordinary-task root, the configured repo-global log file, and `docs/archive/**` from the search. Use literal, anchored path exclusions so spaces or Git pathspec metacharacters in configured paths do not broaden the scan. Untracked and binary files are outside the scan. Read restrictions remain exclusions, not permission to inspect archives.
- [ ] On matches, emit an advisory warning to stderr **before** filesystem removal. Identify the target and each matching source file and line number, describe matches as possible inbound references, state that deletion is proceeding without repair, and advise checking durable links and replacing live-tree targets with commit permalinks. Do not describe a literal match as proof of a broken link: existing permalinks, longer slugs and fixture paths can match too. Avoid dumping full matching lines; file/line locations suffice.
- [ ] Matches neither refuse deletion nor prompt for confirmation. Preserve the existing success report returned by `run_delete_task()`, stdout, exit codes, publication scope, and recovery via Git. No new force flag. No matches produce no inbound-reference warning.
- [ ] Git-disabled operation, absence of a Git worktree, missing Git, or a failed scan emits a concise stderr warning that the check was skipped or could not complete; deletion still follows its existing filesystem/error contract. Distinguish grep exit 1 (no matches) from errors. No traceback or claim that the target has no references after an incomplete scan.
- [ ] `coga delete`, `coga run delete-task`, and done-ticket `coga retire` each expose the shared warning once. Retire continues to delete deterministically, without an agent, link rewriting, or a reference-pin PR. Its canceled-ticket Retro route keeps its current reference-repair procedure.
- [ ] Other existing callers, including recurring replacement and promotion, inherit this advisory behavior without changing their transactions or treating a warning as `DeleteTaskError`. The checkout-local spawn-admission barrier still covers removal, and existing refusal checks remain effective.
- [ ] Add real-Git regression coverage for matching and clean cases, tracked working-tree edits, both task shapes, relative links, configured/nested paths, excluded task/log/archive matches, untracked/binary files, and unavailable/failed scans. Exercise all three public routes and verify stderr, unchanged stdout, successful removal, and unchanged non-target files. Retain the admission-barrier regression and recurring behavior coverage.
- [ ] In the implementation PR, document the shared advisory contract in the packaged `coga/lifecycle` topic; update `bootstrap/delete-task` and `bootstrap/retire` contracts to summarize and link to it. Reconcile related summaries in `retire.md` and `coga/knowledge`, without duplicating the specification or changing Retro's stronger procedure. Record required Linux verification; native checks are deferred to release.

### Proposed shape

1. Keep the check in `src/coga/delete_task.py`, invoked by `run_delete_task()` after validating the ticket and before `unlink()` / `rmtree()`. Keep helpers private to this module and emit diagnostics there so callers that ignore the returned report still expose warnings. Preserve locking and `DeleteTaskError` translation. This is shared task IO with real consumers in the delete command, fixed recipe, packaged retire script, and recurring operations; it satisfies `coga-dev/microkernel` without adding a command or registry entry.
2. Resolve the actual Git root with `git.toplevel()` and derive search patterns from `TaskRef.path` and the leaf of `TaskRef.id_slug`, rather than assuming `coga/tasks/` or reconstructing a path from the CLI argument. Use `git grep` with fixed-string patterns, line numbers, binary exclusion, and explicit exclusions, run from the Git root against tracked working-tree contents. Prefer structured/NUL-delimited output for reliable filenames. Run subprocess argv directly, never through a shell. A scan invocation/result helper may live here; no new general Git-search subsystem is needed. `git.run_git()` treats every nonzero status as failure, so handle grep's no-match status explicitly.
3. Keep the heuristic deliberately conservative: no Markdown parser, URL resolver or automatic classification of permalinks. Search candidates are advisory because semantic filtering belongs to the operator or Retro. The fixed archive exclusion preserves this repository's restriction; the feature is not a general interpreter for arbitrary repository search policies. Document the scan boundary and incomplete-check behavior.
4. Keep `commands/delete.delete()`, `run_delete_task_recipe()` and retire's `_delete_done_task()` as callers of the same primitive. The retire script needs no independent scanner or repoint logic. Automatic rewriting would require choosing a historical commit and publishing unrelated documentation edits for review; it would expand retire beyond its deterministic removal contract. Operators who want prevention must repair links in reviewed work before invoking deletion; this warning alone does not guarantee navigation remains intact.
5. Extend `tests/test_commands.py` for the primitive/CLI/recipe and `tests/test_retire.py` for done-ticket integration. Use temporary repositories and local tracked fixtures, not live task contents. Run focused regressions, package-resource checks and the full Linux suite per `coga-dev/testing`; update template assertions only where the documented contract changes.

### Out of scope

Refusing or delaying deletion on reference matches; interactive confirmation or override flags; automatic permalink generation, link rewriting or PR creation; changing canceled-ticket Retro; scanning untracked files or restricted archives; complete reference detection (encoded URLs, arbitrary aliases and computed paths); changing recurring replacement semantics, checkout disposal, publication or notification behavior.

## Context

- `src/coga/delete_task.py`, `run_delete_task()`, owns the locked filesystem removal and returns a success report; `run_delete_task_recipe()` resolves its one argument and writes that report to stdout. `src/coga/commands/delete.py`, `delete()`, calls the same primitive and then publishes only the target and configured log.
- `src/coga/resources/templates/coga/bootstrap/retire/ticket.py`, `retire()`, performs checkout cleanup before dispatching done tickets to `_delete_done_task()`, which calls `run_delete_task()` and publishes the removal. Canceled tickets instead get a generated Retro task. The done path is not implemented by `src/coga/resources/retire.md`; that file is the canceled-task prose template rendered by `_retire_body()`.
- `src/coga/recurring.py` calls `run_delete_task()` from `create_template()` for completed-run replacement and from `promote_task()` after writing the recurring template. The warning must not become a new refusal in these paths.
- `src/coga/tasks.py`, `TaskRef.path`, `TaskRef.ticket_path` and `TaskRef.id_slug`, distinguish artifact paths and nested refs; `src/coga/paths.py`, `log_path()`, supplies the configured log exclusion. `src/coga/git.py`, `toplevel()` and `run_git()`, supply root discovery and the existing Git error conventions.
- Required reading, cited rather than attached: `coga-dev/microkernel` at `docs/contexts/coga-dev/microkernel/SKILL.md` (The microkernel rule); `coga/lifecycle` at `src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md` (shared lifecycle contract); and `coga/knowledge` at the sibling `knowledge/SKILL.md` (one owner per fact and narrative links).
- Required procedure/contract reading: `src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md`, Inbound references, owns the semantic review and reference-pin PR procedure; `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/delete-task/SKILL.md`, Known Skill Contract, owns the recipe invocation; `src/coga/resources/templates/coga/bootstrap/retire/ticket.md`, Steps, owns retire. Update the package owners, not local forwarding copies.
- Verification guidance is cited rather than attached: `docs/contexts/coga-dev/testing/SKILL.md`, Verification tiers and receipts, and `docs/contexts/coga-dev/packaging/SKILL.md` for package-resource ownership.


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

## Design handoff

Recommended advisory warning rather than refusal: fixed-string matches include historical permalinks and unrelated fixture paths, and recurring callers reuse deletion during replacement. Retire inherits the check without automatic rewriting; reviewed link repair stays with the operator/Retro. These are design recommendations for evaluator and owner review, not owner-approved decisions.

Starting checkout: clean `main`, no ticket branch or PR record; fetched configured local origin and confirmed HEAD equals `origin/main` at `0352757`. No implementation branch, code edits or PR created. Investigation read current package owners and source only; no archive contents accessed.

Verification: `coga validate --task warn-when-coga-delete-or-coga-retire-leaves-a-live --json` passed (one task, zero issues); `git diff --check` passed. Re-fetched origin before handoff: no intervening changes (`HEAD...origin/main` = `0 0`). Only this ticket changed; no runtime tests needed for a design-only step.

## Open Questions

None requiring additional input for this proposed scope. The owner can accept or revise the warning-versus-refusal and no-auto-repoint recommendations at review-design.

````

## Change to the ticket

```diff
diff --git a/coga/tasks/warn-when-coga-delete-or-coga-retire-leaves-a-live.md b/coga/tasks/warn-when-coga-delete-or-coga-retire-leaves-a-live.md
index 696fe0c..bf23205 100644
--- a/coga/tasks/warn-when-coga-delete-or-coga-retire-leaves-a-live.md
+++ b/coga/tasks/warn-when-coga-delete-or-coga-retire-leaves-a-live.md
@@ -1,6 +1,6 @@
 ---
 title: Warn when coga delete or coga retire leaves a live link to the deleted ticket
-status: active
+status: in_progress
 owner: nicktoper
 agent: codex
 workflow:
@@ -42,15 +42,48 @@ workflow:
     - code/address-pr-comments
     assignee: owner
     checkout: reuse-required
-step: 1 (design)
+step: 2 (evaluate-design)
 ---
 
 ## Description
 
-Follow-up from make-retro-check-inbound-doc-links-before-deleting. That ticket made retro/done-ticket search tracked files for a source task's path and repoint live-tree references (blob/<control-branch> URLs, relative links) to a commit permalink before deleting. Two delete paths still bypass that rule. coga retire deletes a done ticket deterministically, without Retro (src/coga/resources/retire.md), and an ordinary human coga delete has the same gap (src/coga/commands/delete.py plus delete_task.run_delete_task). Either can break navigation on main the way the README link to document-the-remedy-for-a-bloated-blackboard-sibli did (fixed by PR #1214). Decide whether delete_task should run git grep -F for the task path, excluding the task root and log.md, and warn or refuse before deleting. That would add core behavior to a shared path with two consumers (coga delete and the delete-task recipe), so check the microkernel rule. Also decide whether coga retire should repoint the links itself.
+Deleting a ticket can break durable navigation: ordinary `coga delete` and the deterministic done-ticket path of `coga retire` currently remove it without checking inbound references. Retro already inspects and repairs references, but these paths bypass that procedure. Add an advisory check to the shared deletion primitive so operators see potential breakage before removal.
+
+### Acceptance criteria
+
+- [ ] Before removing a valid resolved ticket, `run_delete_task()` searches tracked working-tree text for the target's Git-root-relative artifact path and final slug component (without `.md`). Cover file and directory forms, nested task refs, configured task roots, and invocation below the Git root. The leaf search catches links such as `../tasks/example.md` and `../example/ticket.md` that omit the full root prefix.
+- [ ] Exclude the entire configured ordinary-task root, the configured repo-global log file, and `docs/archive/**` from the search. Use literal, anchored path exclusions so spaces or Git pathspec metacharacters in configured paths do not broaden the scan. Untracked and binary files are outside the scan. Read restrictions remain exclusions, not permission to inspect archives.
+- [ ] On matches, emit an advisory warning to stderr **before** filesystem removal. Identify the target and each matching source file and line number, describe matches as possible inbound references, state that deletion is proceeding without repair, and advise checking durable links and replacing live-tree targets with commit permalinks. Do not describe a literal match as proof of a broken link: existing permalinks, longer slugs and fixture paths can match too. Avoid dumping full matching lines; file/line locations suffice.
+- [ ] Matches neither refuse deletion nor prompt for confirmation. Preserve the existing success report returned by `run_delete_task()`, stdout, exit codes, publication scope, and recovery via Git. No new force flag. No matches produce no inbound-reference warning.
+- [ ] Git-disabled operation, absence of a Git worktree, missing Git, or a failed scan emits a concise stderr warning that the check was skipped or could not complete; deletion still follows its existing filesystem/error contract. Distinguish grep exit 1 (no matches) from errors. No traceback or claim that the target has no references after an incomplete scan.
+- [ ] `coga delete`, `coga run delete-task`, and done-ticket `coga retire` each expose the shared warning once. Retire continues to delete deterministically, without an agent, link rewriting, or a reference-pin PR. Its canceled-ticket Retro route keeps its current reference-repair procedure.
+- [ ] Other existing callers, including recurring replacement and promotion, inherit this advisory behavior without changing their transactions or treating a warning as `DeleteTaskError`. The checkout-local spawn-admission barrier still covers removal, and existing refusal checks remain effective.
+- [ ] Add real-Git regression coverage for matching and clean cases, tracked working-tree edits, both task shapes, relative links, configured/nested paths, excluded task/log/archive matches, untracked/binary files, and unavailable/failed scans. Exercise all three public routes and verify stderr, unchanged stdout, successful removal, and unchanged non-target files. Retain the admission-barrier regression and recurring behavior coverage.
+- [ ] In the implementation PR, document the shared advisory contract in the packaged `coga/lifecycle` topic; update `bootstrap/delete-task` and `bootstrap/retire` contracts to summarize and link to it. Reconcile related summaries in `retire.md` and `coga/knowledge`, without duplicating the specification or changing Retro's stronger procedure. Record required Linux verification; native checks are deferred to release.
+
+### Proposed shape
+
+1. Keep the check in `src/coga/delete_task.py`, invoked by `run_delete_task()` after validating the ticket and before `unlink()` / `rmtree()`. Keep helpers private to this module and emit diagnostics there so callers that ignore the returned report still expose warnings. Preserve locking and `DeleteTaskError` translation. This is shared task IO with real consumers in the delete command, fixed recipe, packaged retire script, and recurring operations; it satisfies `coga-dev/microkernel` without adding a command or registry entry.
+2. Resolve the actual Git root with `git.toplevel()` and derive search patterns from `TaskRef.path` and the leaf of `TaskRef.id_slug`, rather than assuming `coga/tasks/` or reconstructing a path from the CLI argument. Use `git grep` with fixed-string patterns, line numbers, binary exclusion, and explicit exclusions, run from the Git root against tracked working-tree contents. Prefer structured/NUL-delimited output for reliable filenames. Run subprocess argv directly, never through a shell. A scan invocation/result helper may live here; no new general Git-search subsystem is needed. `git.run_git()` treats every nonzero status as failure, so handle grep's no-match status explicitly.
+3. Keep the heuristic deliberately conservative: no Markdown parser, URL resolver or automatic classification of permalinks. Search candidates are advisory because semantic filtering belongs to the operator or Retro. The fixed archive exclusion preserves this repository's restriction; the feature is not a general interpreter for arbitrary repository search policies. Document the scan boundary and incomplete-check behavior.
+4. Keep `commands/delete.delete()`, `run_delete_task_recipe()` and retire's `_delete_done_task()` as callers of the same primitive. The retire script needs no independent scanner or repoint logic. Automatic rewriting would require choosing a historical commit and publishing unrelated documentation edits for review; it would expand retire beyond its deterministic removal contract. Operators who want prevention must repair links in reviewed work before invoking deletion; this warning alone does not guarantee navigation remains intact.
+5. Extend `tests/test_commands.py` for the primitive/CLI/recipe and `tests/test_retire.py` for done-ticket integration. Use temporary repositories and local tracked fixtures, not live task contents. Run focused regressions, package-resource checks and the full Linux suite per `coga-dev/testing`; update template assertions only where the documented contract changes.
+
+### Out of scope
+
+Refusing or delaying deletion on reference matches; interactive confirmation or override flags; automatic permalink generation, link rewriting or PR creation; changing canceled-ticket Retro; scanning untracked files or restricted archives; complete reference detection (encoded URLs, arbitrary aliases and computed paths); changing recurring replacement semantics, checkout disposal, publication or notification behavior.
 
 ## Context
 
+- `src/coga/delete_task.py`, `run_delete_task()`, owns the locked filesystem removal and returns a success report; `run_delete_task_recipe()` resolves its one argument and writes that report to stdout. `src/coga/commands/delete.py`, `delete()`, calls the same primitive and then publishes only the target and configured log.
+- `src/coga/resources/templates/coga/bootstrap/retire/ticket.py`, `retire()`, performs checkout cleanup before dispatching done tickets to `_delete_done_task()`, which calls `run_delete_task()` and publishes the removal. Canceled tickets instead get a generated Retro task. The done path is not implemented by `src/coga/resources/retire.md`; that file is the canceled-task prose template rendered by `_retire_body()`.
+- `src/coga/recurring.py` calls `run_delete_task()` from `create_template()` for completed-run replacement and from `promote_task()` after writing the recurring template. The warning must not become a new refusal in these paths.
+- `src/coga/tasks.py`, `TaskRef.path`, `TaskRef.ticket_path` and `TaskRef.id_slug`, distinguish artifact paths and nested refs; `src/coga/paths.py`, `log_path()`, supplies the configured log exclusion. `src/coga/git.py`, `toplevel()` and `run_git()`, supply root discovery and the existing Git error conventions.
+- Required reading, cited rather than attached: `coga-dev/microkernel` at `docs/contexts/coga-dev/microkernel/SKILL.md` (The microkernel rule); `coga/lifecycle` at `src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md` (shared lifecycle contract); and `coga/knowledge` at the sibling `knowledge/SKILL.md` (one owner per fact and narrative links).
+- Required procedure/contract reading: `src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md`, Inbound references, owns the semantic review and reference-pin PR procedure; `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/delete-task/SKILL.md`, Known Skill Contract, owns the recipe invocation; `src/coga/resources/templates/coga/bootstrap/retire/ticket.md`, Steps, owns retire. Update the package owners, not local forwarding copies.
+- Verification guidance is cited rather than attached: `docs/contexts/coga-dev/testing/SKILL.md`, Verification tiers and receipts, and `docs/contexts/coga-dev/packaging/SKILL.md` for package-resource ownership.
+
+
 <!-- Ticket guide — keep this comment when filling in or updating the ticket.
 It documents field shapes; these are examples, not values to copy into every
 ticket. Omit optional fields and sections until needed. Editing rules come
@@ -137,4 +170,14 @@ ordinary ticket.
 
 <!-- coga:blackboard -->
 
-The blackboard is a notepad to be written to often as the human and agent works through a task.
+## Design handoff
+
+Recommended advisory warning rather than refusal: fixed-string matches include historical permalinks and unrelated fixture paths, and recurring callers reuse deletion during replacement. Retire inherits the check without automatic rewriting; reviewed link repair stays with the operator/Retro. These are design recommendations for evaluator and owner review, not owner-approved decisions.
+
+Starting checkout: clean `main`, no ticket branch or PR record; fetched configured local origin and confirmed HEAD equals `origin/main` at `0352757`. No implementation branch, code edits or PR created. Investigation read current package owners and source only; no archive contents accessed.
+
+Verification: `coga validate --task warn-when-coga-delete-or-coga-retire-leaves-a-live --json` passed (one task, zero issues); `git diff --check` passed. Re-fetched origin before handoff: no intervening changes (`HEAD...origin/main` = `0 0`). Only this ticket changed; no runtime tests needed for a design-only step.
+
+## Open Questions
+
+None requiring additional input for this proposed scope. The owner can accept or revise the warning-versus-refusal and no-auto-repoint recommendations at review-design.
```
