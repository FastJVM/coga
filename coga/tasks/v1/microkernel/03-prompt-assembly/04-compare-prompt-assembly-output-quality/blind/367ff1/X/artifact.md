# Pair 367ff1, output X (design)

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

Deleting a ticket can leave a README, context, skill, or code comment pointing
at a path that no longer exists on the control branch. Retro already checks
inbound references and repoints real live-tree links in a reviewed PR, but
ordinary `coga delete` and deterministic retirement of done tickets bypass
that process. Add a visible, advisory warning to the shared deletion path.
Deletion still proceeds: literal matches are candidates, not proof of a broken
link, and deterministic deletion must not acquire an interactive gate.

### Acceptance criteria

- [ ] Before filesystem removal, `coga delete`, `coga run delete-task`, and
  the done-ticket path of `coga retire` emit a warning to stderr when tracked
  working-tree files outside the configured tasks root and configured global
  log mention the target's Git-root-relative path or its final slug component.
  Cover directory-form and file-form tickets, nested slugs, custom Coga roots,
  invocation from a subdirectory, and linked worktrees. Search terms are
  literal, passed as argv (never shell interpolation); paths use Git's `/`
  spelling. For directory form search its directory path; for file form search
  the actual `.md` path; also search the leaf slug without `.md` in both cases.
- [ ] The warning identifies the resolved ticket and each matching file and
  line number, explains that deletion can leave broken live-tree references,
  and tells the operator to inspect candidates and repair real references in
  a reviewed change using a commit permalink that still contains the ticket.
  Call matches “possible inbound references”; do not claim to parse or prove
  link validity. Existing permalinks, longer slugs sharing the leaf, and
  fixture references may therefore produce false positives. Document that
  limitation explicitly rather than adding a Markdown/URL parser.
- [ ] A successful scan with no matches is silent. Warning output precedes
  removal, leaves existing success stdout unchanged, adds no confirmation or
  refusal, and changes neither exit status nor publication scope. The recipe
  still removes only working-tree state; delete and retire still publish the
  removal as before. No doc, link, branch, or ticket body is rewritten by
  this feature.
- [ ] Without a Git worktree or executable Git, or when the scan fails, emit
  a concise stderr warning that reference checking was unavailable and
  continue with the existing deletion behavior. Git grep exit 1 means no
  matches, not a failure; other unsuccessful exits are reported as unchecked.
  The scan is local and needs no fetch, remote, GitHub URL, or enabled state
  publication; `[git].enabled = false` does not suppress a usable local scan.
- [ ] Same-path recurring replacement does not scan or warn: it recreates
  the ticket at the same path. Promotion, which removes the old path, retains
  the default warning. Preserve the existing spawn-admission barrier and
  `DeleteTaskError` handling for actual removal failures.
- [ ] Tests exercise all three user entry paths, both ticket forms, exclusions,
  literal matching, the relative-link leaf case, unchanged success stdout,
  warning-before-removal, scan failure/no-Git behavior, and recurring
  replacement suppression versus promotion. Run focused regressions followed
  by the full Linux suite per `coga-dev/testing`; record native checks as
  deferred to release.
- [ ] Update the shipped deletion contract and retire's command ticket in the
  same implementation PR. Keep the lifecycle/knowledge summaries and Retro
  guidance consistent, with one owner for the warning contract and links
  from other surfaces.

### Proposed shape

1. Add a small private scanner/formatter beside `run_delete_task()` in
   `src/coga/delete_task.py`. Use `git.toplevel()` to anchor the checkout,
   configured path helpers for the tasks root/log, and a subprocess argv for
   `git grep -n -F` with two `-e` terms over tracked working-tree files.
   Exclude the entire configured tasks root and global log with literal,
   root-anchored pathspecs. Do not search only HEAD: an edited tracked doc
   must be inspected as it stands at deletion time. Deduplicate matching
   lines and keep deterministic file/line ordering. Untracked files are
   outside this bounded check.
2. Extend `run_delete_task()` with a keyword-only `warn_references: bool =
   True` (or an equivalently explicit name). After validating the target
   exists and before `rmtree`/`unlink`, run the check and emit diagnostics to
   stderr under the existing state-lock scope. Keep its string return
   contract intact. Scanner failures must not escape as removal failures or
   tracebacks. Have `recurring.create_template()` pass false only at its
   same-path completed-period replacement call; `promote_task()` keeps the
   default because its source disappears.
3. Keep `commands.delete.delete()`, `run_delete_task_recipe()`, and the
   packaged retire script's `_delete_done_task()` on that one shared path.
   Their existing calls inherit the warning without another scanner or new
   CLI flag. Retire remains deterministic and does not repoint links itself:
   its deletion publication carries only the task and log, whereas repairs
   to docs require a reviewed PR. Canceled retirement keeps using Retro's
   existing reference repair procedure.
4. The shared check belongs in core under `coga-dev/microkernel`: the CLI
   delete head, the fixed `delete-task` recipe, and the packaged retire edge
   script consume the same deletion implementation. It is shared task IO,
   not a new command head or recipe. Keep scanner helpers private to that
   module; do not introduce an extension mechanism.
5. Extend `tests/test_commands.py`, `tests/test_retire.py`, and
   `tests/test_recurring.py` with synthetic tracked files and subprocess
   failure cases. Preserve existing deletion/publication and barrier tests.
   Own the shared warning specification in the packaged
   `skills/bootstrap/delete-task/SKILL.md`; retire's `bootstrap/retire/ticket.md`
   summarizes and links to it. Check `coga/lifecycle`, `coga/knowledge`, and
   `retro/done-ticket` for stale claims that deletion is unchecked. Change
   `resources/retire.md` only if its canceled-retirement prose needs alignment;
   it is not the deterministic done-ticket implementation.

### Out of scope

Automatic link repointing, refusing deletion on matches, a force/confirmation
flag, a Markdown or URL resolver, repository-wide link validation, references
in untracked files or other clones, and a guarantee against concurrent edits
or newly published references. This warning does not replace Retro's
human/agent inspection and reference-pin PR. No change to checkout disposal,
recurring scheduling, or deletion publication transactions.

## Context

Cited rather than attached: read `coga-dev/microkernel` (Microkernel rule),
`coga/knowledge` (Where knowledge lives and sync rule), `coga/lifecycle`
(terminal status conventions), and `coga-dev/testing` (Verification tiers and
receipts) at their indexed locations in `docs/README.md` before implementation.

- `src/coga/delete_task.py`, `run_delete_task()` validates and removes the
  resolved ticket under `git.state_lock()`; `run_delete_task_recipe()` invokes
  it and writes its report to stdout. `src/coga/runner.py`, `RECIPES`, maps
  `delete-task` to that recipe wrapper.
- `src/coga/commands/delete.py`, `delete()`, calls `run_delete_task()` before
  `git.publish()` with the task path and configured log. Its
  `--keep-control-checkout` option changes publication, not deletion scanning.
- `src/coga/resources/templates/coga/bootstrap/retire/ticket.py`, `retire()`,
  disposes of the checkout and discharges the worklist before calling
  `_delete_done_task()` for done tickets. That helper calls `run_delete_task()`
  and publishes the deletion. The sibling `ticket.md` owns this contract.
  `src/coga/resources/retire.md` instead renders the canceled-ticket Retro
  task through `_retire_body()`.
- `src/coga/recurring.py`, `create_template()`, calls `run_delete_task()` to
  replace an existing completed period at the same slug, then `_create_at_slug()`
  recreates it; `promote_task()` calls deletion after writing a recurring
  template at a different location. These two callers need different warning
  policy because only replacement preserves the referenced path.
- `src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md`,
  “Inbound references”, owns the existing inspected-reference/permalink repair
  procedure and separate reference-pin PR. Its leaf search explains why
  searching only the full task path misses relative Markdown links. Its
  exclusions deliberately omit references from transient tickets.

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

Investigated the shared removal path and every production caller. Proposed an
advisory <arm-word> warning, preserving deletion behavior; automatic repair stays
in reviewed changes. Discovered same-path recurring replacement and promotion
as additional callers: suppress only replacement. The actual done-retire
implementation is the packaged bootstrap script, not `resources/retire.md`.

Started on clean `main`, equal to fetched `origin/main`; no feature branch or
PR exists for this design-only step. No implementation files changed. Searches
and reads excluded `docs/archive/**`.

Verification: `coga validate --task
warn-when-coga-delete-or-coga-retire-leaves-a-live --json` passed (1 ticket,
no issues). Re-fetched main before handoff; no remote drift.
`git diff --check` passed after removing a trailing blank line. No code tests
run for this design-only ticket edit.

## Open Questions

None requiring unavailable input. The evaluator and owner should assess the
explicit tradeoff: advisory literal matching tolerates false positives and
still permits broken links, while refusing would make safe permalink mentions
and unrelated slug matches prevent deterministic retirement.

````

## Change to the ticket

```diff
diff --git a/coga/tasks/warn-when-coga-delete-or-coga-retire-leaves-a-live.md b/coga/tasks/warn-when-coga-delete-or-coga-retire-leaves-a-live.md
index 696fe0c..1510b2e 100644
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
@@ -42,15 +42,146 @@ workflow:
     - code/address-pr-comments
     assignee: owner
     checkout: reuse-required
-step: 1 (design)
+step: 2 (evaluate-design)
 ---
 
 ## Description
 
-Follow-up from make-retro-check-inbound-doc-links-before-deleting. That ticket made retro/done-ticket search tracked files for a source task's path and repoint live-tree references (blob/<control-branch> URLs, relative links) to a commit permalink before deleting. Two delete paths still bypass that rule. coga retire deletes a done ticket deterministically, without Retro (src/coga/resources/retire.md), and an ordinary human coga delete has the same gap (src/coga/commands/delete.py plus delete_task.run_delete_task). Either can break navigation on main the way the README link to document-the-remedy-for-a-bloated-blackboard-sibli did (fixed by PR #1214). Decide whether delete_task should run git grep -F for the task path, excluding the task root and log.md, and warn or refuse before deleting. That would add core behavior to a shared path with two consumers (coga delete and the delete-task recipe), so check the microkernel rule. Also decide whether coga retire should repoint the links itself.
+Deleting a ticket can leave a README, context, skill, or code comment pointing
+at a path that no longer exists on the control branch. Retro already checks
+inbound references and repoints real live-tree links in a reviewed PR, but
+ordinary `coga delete` and deterministic retirement of done tickets bypass
+that process. Add a visible, advisory warning to the shared deletion path.
+Deletion still proceeds: literal matches are candidates, not proof of a broken
+link, and deterministic deletion must not acquire an interactive gate.
+
+### Acceptance criteria
+
+- [ ] Before filesystem removal, `coga delete`, `coga run delete-task`, and
+  the done-ticket path of `coga retire` emit a warning to stderr when tracked
+  working-tree files outside the configured tasks root and configured global
+  log mention the target's Git-root-relative path or its final slug component.
+  Cover directory-form and file-form tickets, nested slugs, custom Coga roots,
+  invocation from a subdirectory, and linked worktrees. Search terms are
+  literal, passed as argv (never shell interpolation); paths use Git's `/`
+  spelling. For directory form search its directory path; for file form search
+  the actual `.md` path; also search the leaf slug without `.md` in both cases.
+- [ ] The warning identifies the resolved ticket and each matching file and
+  line number, explains that deletion can leave broken live-tree references,
+  and tells the operator to inspect candidates and repair real references in
+  a reviewed change using a commit permalink that still contains the ticket.
+  Call matches “possible inbound references”; do not claim to parse or prove
+  link validity. Existing permalinks, longer slugs sharing the leaf, and
+  fixture references may therefore produce false positives. Document that
+  limitation explicitly rather than adding a Markdown/URL parser.
+- [ ] A successful scan with no matches is silent. Warning output precedes
+  removal, leaves existing success stdout unchanged, adds no confirmation or
+  refusal, and changes neither exit status nor publication scope. The recipe
+  still removes only working-tree state; delete and retire still publish the
+  removal as before. No doc, link, branch, or ticket body is rewritten by
+  this feature.
+- [ ] Without a Git worktree or executable Git, or when the scan fails, emit
+  a concise stderr warning that reference checking was unavailable and
+  continue with the existing deletion behavior. Git grep exit 1 means no
+  matches, not a failure; other unsuccessful exits are reported as unchecked.
+  The scan is local and needs no fetch, remote, GitHub URL, or enabled state
+  publication; `[git].enabled = false` does not suppress a usable local scan.
+- [ ] Same-path recurring replacement does not scan or warn: it recreates
+  the ticket at the same path. Promotion, which removes the old path, retains
+  the default warning. Preserve the existing spawn-admission barrier and
+  `DeleteTaskError` handling for actual removal failures.
+- [ ] Tests exercise all three user entry paths, both ticket forms, exclusions,
+  literal matching, the relative-link leaf case, unchanged success stdout,
+  warning-before-removal, scan failure/no-Git behavior, and recurring
+  replacement suppression versus promotion. Run focused regressions followed
+  by the full Linux suite per `coga-dev/testing`; record native checks as
+  deferred to release.
+- [ ] Update the shipped deletion contract and retire's command ticket in the
+  same implementation PR. Keep the lifecycle/knowledge summaries and Retro
+  guidance consistent, with one owner for the warning contract and links
+  from other surfaces.
+
+### Proposed shape
+
+1. Add a small private scanner/formatter beside `run_delete_task()` in
+   `src/coga/delete_task.py`. Use `git.toplevel()` to anchor the checkout,
+   configured path helpers for the tasks root/log, and a subprocess argv for
+   `git grep -n -F` with two `-e` terms over tracked working-tree files.
+   Exclude the entire configured tasks root and global log with literal,
+   root-anchored pathspecs. Do not search only HEAD: an edited tracked doc
+   must be inspected as it stands at deletion time. Deduplicate matching
+   lines and keep deterministic file/line ordering. Untracked files are
+   outside this bounded check.
+2. Extend `run_delete_task()` with a keyword-only `warn_references: bool =
+   True` (or an equivalently explicit name). After validating the target
+   exists and before `rmtree`/`unlink`, run the check and emit diagnostics to
+   stderr under the existing state-lock scope. Keep its string return
+   contract intact. Scanner failures must not escape as removal failures or
+   tracebacks. Have `recurring.create_template()` pass false only at its
+   same-path completed-period replacement call; `promote_task()` keeps the
+   default because its source disappears.
+3. Keep `commands.delete.delete()`, `run_delete_task_recipe()`, and the
+   packaged retire script's `_delete_done_task()` on that one shared path.
+   Their existing calls inherit the warning without another scanner or new
+   CLI flag. Retire remains deterministic and does not repoint links itself:
+   its deletion publication carries only the task and log, whereas repairs
+   to docs require a reviewed PR. Canceled retirement keeps using Retro's
+   existing reference repair procedure.
+4. The shared check belongs in core under `coga-dev/microkernel`: the CLI
+   delete head, the fixed `delete-task` recipe, and the packaged retire edge
+   script consume the same deletion implementation. It is shared task IO,
+   not a new command head or recipe. Keep scanner helpers private to that
+   module; do not introduce an extension mechanism.
+5. Extend `tests/test_commands.py`, `tests/test_retire.py`, and
+   `tests/test_recurring.py` with synthetic tracked files and subprocess
+   failure cases. Preserve existing deletion/publication and barrier tests.
+   Own the shared warning specification in the packaged
+   `skills/bootstrap/delete-task/SKILL.md`; retire's `bootstrap/retire/ticket.md`
+   summarizes and links to it. Check `coga/lifecycle`, `coga/knowledge`, and
+   `retro/done-ticket` for stale claims that deletion is unchecked. Change
+   `resources/retire.md` only if its canceled-retirement prose needs alignment;
+   it is not the deterministic done-ticket implementation.
+
+### Out of scope
+
+Automatic link repointing, refusing deletion on matches, a force/confirmation
+flag, a Markdown or URL resolver, repository-wide link validation, references
+in untracked files or other clones, and a guarantee against concurrent edits
+or newly published references. This warning does not replace Retro's
+human/agent inspection and reference-pin PR. No change to checkout disposal,
+recurring scheduling, or deletion publication transactions.
 
 ## Context
 
+Cited rather than attached: read `coga-dev/microkernel` (Microkernel rule),
+`coga/knowledge` (Where knowledge lives and sync rule), `coga/lifecycle`
+(terminal status conventions), and `coga-dev/testing` (Verification tiers and
+receipts) at their indexed locations in `docs/README.md` before implementation.
+
+- `src/coga/delete_task.py`, `run_delete_task()` validates and removes the
+  resolved ticket under `git.state_lock()`; `run_delete_task_recipe()` invokes
+  it and writes its report to stdout. `src/coga/runner.py`, `RECIPES`, maps
+  `delete-task` to that recipe wrapper.
+- `src/coga/commands/delete.py`, `delete()`, calls `run_delete_task()` before
+  `git.publish()` with the task path and configured log. Its
+  `--keep-control-checkout` option changes publication, not deletion scanning.
+- `src/coga/resources/templates/coga/bootstrap/retire/ticket.py`, `retire()`,
+  disposes of the checkout and discharges the worklist before calling
+  `_delete_done_task()` for done tickets. That helper calls `run_delete_task()`
+  and publishes the deletion. The sibling `ticket.md` owns this contract.
+  `src/coga/resources/retire.md` instead renders the canceled-ticket Retro
+  task through `_retire_body()`.
+- `src/coga/recurring.py`, `create_template()`, calls `run_delete_task()` to
+  replace an existing completed period at the same slug, then `_create_at_slug()`
+  recreates it; `promote_task()` calls deletion after writing a recurring
+  template at a different location. These two callers need different warning
+  policy because only replacement preserves the referenced path.
+- `src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md`,
+  “Inbound references”, owns the existing inspected-reference/permalink repair
+  procedure and separate reference-pin PR. Its leaf search explains why
+  searching only the full task path misses relative Markdown links. Its
+  exclusions deliberately omit references from transient tickets.
+
 <!-- Ticket guide — keep this comment when filling in or updating the ticket.
 It documents field shapes; these are examples, not values to copy into every
 ticket. Omit optional fields and sections until needed. Editing rules come
@@ -137,4 +268,27 @@ ordinary ticket.
 
 <!-- coga:blackboard -->
 
-The blackboard is a notepad to be written to often as the human and agent works through a task.
+## Design handoff
+
+Investigated the shared removal path and every production caller. Proposed an
+advisory <arm-word> warning, preserving deletion behavior; automatic repair stays
+in reviewed changes. Discovered same-path recurring replacement and promotion
+as additional callers: suppress only replacement. The actual done-retire
+implementation is the packaged bootstrap script, not `resources/retire.md`.
+
+Started on clean `main`, equal to fetched `origin/main`; no feature branch or
+PR exists for this design-only step. No implementation files changed. Searches
+and reads excluded `docs/archive/**`.
+
+Verification: `coga validate --task
+warn-when-coga-delete-or-coga-retire-leaves-a-live --json` passed (1 ticket,
+no issues). Re-fetched main before handoff; no remote drift.
+`git diff --check` passed after removing a trailing blank line. No code tests
+run for this design-only ticket edit.
+
+## Open Questions
+
+None requiring unavailable input. The evaluator and owner should assess the
+explicit tradeoff: advisory literal matching tolerates false positives and
+still permits broken links, while refusing would make safe permalink mentions
+and unrelated slug matches prevent deterministic retirement.
```
