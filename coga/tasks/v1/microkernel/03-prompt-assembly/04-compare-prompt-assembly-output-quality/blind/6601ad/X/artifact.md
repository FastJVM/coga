# Pair 6601ad, output X (design)

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

Deleting a ticket can break durable navigation to it. Retro already inspects
inbound references and repoints live links in a reviewed PR, but ordinary
`coga delete`, the `delete-task` recipe, and deterministic retirement of done
tickets remove the source without that inspection. Add an advisory diagnostic
before permanent deletion so an operator sees the potential damage.

Proposed decision for design review: **warn and continue**, rather than refuse
or rewrite links. A literal search cannot establish whether every mention is
a live link, and making it a gate would block valid deletion on historical
mentions. Done-ticket retire remains deterministic and uses the same warning;
it does not run Retro or edit referring documents. Link repair belongs in a
reviewed change that pins references and deletes the source together, as Retro
already does. This safeguard makes risk visible; it does not guarantee that
deleting a ticket preserves navigation.

### Acceptance criteria

- [ ] Before filesystem removal, `coga delete <ref>`, `coga run delete-task
  <ref>`, and the done-ticket path of `coga retire <ref>` emit the same
  advisory warning to stderr when eligible tracked working-tree files contain
  <arm-word> references. The warning identifies the deleted ticket, reports
  referring file paths and line numbers, says these are possible inbound
  references, and says deletion will continue and links may need pinning in a
  reviewed change. It must not claim that every match is a broken link.
- [ ] Search from the Git top level, using fixed strings for both the resolved
  ticket's repository-relative path and its final slug component without
  `.md`. For a directory ticket search its directory path (which also matches
  links to sibling attachments); for a file ticket search the `.md` path.
  The leaf term catches relative links omitting the full configured task root.
  Use tracked working-tree contents, including unstaged edits, not only HEAD
  or index contents. No network access or repository-wide link parser is added.
- [ ] Exclude the configured tasks tree, the configured log file, and
  `docs/archive/**` from <arm-word> content searches. The tasks exclusion is
  the whole transient tasks tree, not merely the deleted ticket. Resolve
  configured paths against the Git root; invocation from a subdirectory,
  nested task slugs, nondefault workspace paths, and both ticket forms work.
  Do not inspect untracked files. Results are deterministic and duplicate
  matches from the two search terms appear only once per referring line.
- [ ] A <arm-word> match alone never changes the existing success status or
  deletion/publication behavior. Preserve the existing stdout deletion report
  and `run_delete_task()` string return contract. No referring file is modified,
  no PR or agent is started, and no confirmation or force flag is introduced.
- [ ] A successful search with no matches is quiet. With Git disabled, Git
  unavailable, no Git work tree, or a search error, deletion remains available
  and stderr explicitly says the reference check was skipped or failed; do not
  report these cases as a successful zero-match scan. Distinguish `git grep`
  exit 1 (no matches) from execution failures. Invalid deletion targets retain
  their existing refusal behavior and are checked before attempting a scan.
- [ ] Permanent removal through recurring promotion receives the default
  diagnostic too. Same-path replacement of a completed recurring period skips
  the reference diagnostic: the path is recreated as part of that operation.
  It retains the shared deletion implementation and its lock/error handling.
- [ ] The deletion's checkout-local spawn-admission barrier and existing
  `DeleteTaskError` handling remain intact. The warning is emitted before
  unlink/rmtree, including when filesystem removal subsequently fails.
- [ ] Regression coverage exercises relative links and control-branch URLs,
  file and directory tickets (including attachment links), exclusions, quiet
  zero-match behavior, scan failure/disabled Git, working-tree edits, configured
  paths, and stderr/stdout separation. Integration coverage proves the CLI,
  recipe, and deterministic retire paths surface the warning and still delete;
  recurring replacement is quiet while promotion retains the default check.
- [ ] Update the packaged owning deletion contract and retire contract in the
  implementation PR; reconcile their summaries and the knowledge-placement
  warning. Record the heuristic's false positives (including commit permalinks,
  longer slugs, fixture mentions, and prose) and blind spots rather than
  promising complete link validation. Run the required Linux verification per
  `coga-dev/testing`; native verification is deferred to release.

### Proposed shape

1. Keep the guard with `src/coga/delete_task.py`, `run_delete_task()`, so
   callers cannot accidentally omit it. Add a small private <arm-word>-search
   and diagnostic helper there, not a new general link-checking subsystem.
   Run the check after target validation and before removal inside the existing
   state-lock scope. Capture Git's status/output explicitly so exit 1 is not
   confused with a failed scan. Invoke Git with an argv list and literal,
   root-anchored exclusion paths; handle spaces and pathspec metacharacters.
2. Add a keyword-only opt-out such as `check_references=False` solely for
   `src/coga/recurring.py`, `create_template()`'s same-path completed-period
   replacement. Default to checking for every other caller, including
   `promote_task()`. Keep warning output separate from the returned deletion
   report so existing callers and stdout contracts stay stable.
3. Let `src/coga/commands/delete.py`, `delete()`, and the packaged retire
   script's `_delete_done_task()` inherit the check through their existing
   calls. Do not duplicate search or repair logic in the command heads.
4. Add focused deletion regression tests and extend the existing command,
   runner, retire, and recurring coverage as appropriate. Use temporary Git
   fixture repositories; never search this repository's restricted archive to
   test the scanner. After focused checks, run the full Linux suite and
   ticket-scoped validation, recording exact commands and receipts.
5. Put the shared behavioral contract in packaged `coga/checkout-cleanup`
   under `coga delete`; make `bootstrap/delete-task` summarize and link to it.
   Update packaged `bootstrap/retire/ticket.md` step 5 to link to that contract
   and explicitly retain deterministic deletion without automatic repointing.
   In packaged `coga/knowledge`, reconcile the retirement paragraph with
   Retro's existing reference-pin behavior and the advisory deletion check.
   Inspect `resources/retire.md` and the Retro skill for dependent summaries;
   their canceled-ticket reference repair procedure remains authoritative.

### Out of scope

Automatic reference edits, commit selection or permalink generation, new PRs
or agents during done retirement, refusal/force policy, parsing Markdown or
GitHub URL semantics, searching Git history/untracked files/restricted archives,
a configurable search-policy framework, changing checkout cleanup or publication
transactions, and cleanup of all existing ticket links. The check observes this
checkout only; it does not establish remote-main freshness or serialize edits
in other checkouts.

## Context

### Code relationships and required reading

- `src/coga/delete_task.py`, `run_delete_task()`, validates the resolved
  ticket and holds `git.state_lock()` while removing the file or directory.
  `run_delete_task_recipe()` resolves one argument and prints the returned
  report. `src/coga/commands/delete.py`, `delete()`, calls that same removal
  function, then separately publishes only the task path and log. Therefore
  repairing a referring document inside this primitive would not make its
  publication atomic with the deletion.
- `src/coga/resources/templates/coga/bootstrap/retire/ticket.py`,
  `retire()` dispatches done tickets to `_delete_done_task()`, which calls
  `run_delete_task()` and publishes the removal. The similarly named
  `src/coga/resources/retire.md` is the canceled-ticket Retro shell, not the
  deterministic done-ticket implementation. The command's behavior owner is
  `src/coga/resources/templates/coga/bootstrap/retire/ticket.md`.
- `src/coga/recurring.py`, `create_template()` deletes a stale completed
  period through `run_delete_task()` immediately before `_create_at_slug()`
  recreates it. `promote_task()` calls the same deletion function after
  constructing a recurring template at a different path. Only the former
  qualifies for the same-path diagnostic opt-out.
- `src/coga/git.py`, `toplevel()` resolves the Git root; `run_git()` treats
  every nonzero status as `GitError`, so a direct grep call must account for
  its normal no-match status rather than silently treating all failures as
  absence. Reuse appropriate shared infrastructure without expanding Git's
  public API solely for this private diagnostic.
- Read `docs/contexts/coga-dev/microkernel/SKILL.md`, especially “The
  microkernel rule” and “The kernel tier and its edges” (cited, not attached).
  This is shared task-IO behavior used by the delete head, fixed recipe, and
  shipped retire script; the recipe is already an accepted co-versioned core
  contract. The diagnostic belongs in that existing shared path. Deterministic
  retire orchestration remains at the edge; no edge implementation is imported
  into core.
- Read `src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md`,
  “Inbound references” (cited, not attached): it owns inspection and reviewed
  repointing, distinguishes commit permalinks from live references, and
  excludes transient tasks and the log. The new advisory intentionally uses
  <arm-word> search without pretending to perform that agent judgment.
- Read `src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/SKILL.md`,
  “coga delete”, and the `bootstrap/delete-task` skill at
  `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/delete-task/SKILL.md`
  (cited, not attached), before updating their contract and summary. Read
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md`,
  “Where knowledge lives” and “Narrative links, never restates”, for ownership
  and dependent-summary reconciliation.
- Tests already cover these consumers in `tests/test_commands.py`,
  `tests/test_runner.py`, `tests/test_retire.py`, and `tests/test_recurring.py`.
  Read `docs/contexts/coga-dev/testing/SKILL.md`, “Verification tiers and
  receipts”, before implementation verification (cited, not attached).

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

Investigated at `ebdf2d2461762ccbde7c3dcec14ed26cb509b1a5` on clean
`main`, equal to freshly fetched `origin/main`. No branch or PR is recorded
for this design task. No implementation was attempted.

Proposed advisory <arm-word> search, warn-and-continue, no automatic retire
repointing. Literal matches are deliberately conservative; the warning does
not prove a live link. Found additional recurring callers: suppress the check
only for same-path period replacement, retain it for promotion. The full spec
and source relationships are above the fence in composed sections.

## Open Questions

None unresolved for producing an implementable proposal. The evaluator and
owner should review warn-versus-refuse and the conservative <arm-word>-search
tradeoff before implementation; these are proposed decisions, not approval.

Verification: `coga validate --task warn-when-coga-delete-or-coga-retire-leaves-a-live --json` passed (`ok_count: 1`, no issues). `git diff --check` passed after whitespace cleanup. Final fetch confirmed `origin/main` unchanged at the investigation revision. Ticket-only design change; implementation tests were not run.

````

## Change to the ticket

```diff
diff --git a/coga/tasks/warn-when-coga-delete-or-coga-retire-leaves-a-live.md b/coga/tasks/warn-when-coga-delete-or-coga-retire-leaves-a-live.md
index 696fe0c..c2f7f65 100644
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
@@ -42,15 +42,171 @@ workflow:
     - code/address-pr-comments
     assignee: owner
     checkout: reuse-required
-step: 1 (design)
+step: 2 (evaluate-design)
 ---
 
 ## Description
 
-Follow-up from make-retro-check-inbound-doc-links-before-deleting. That ticket made retro/done-ticket search tracked files for a source task's path and repoint live-tree references (blob/<control-branch> URLs, relative links) to a commit permalink before deleting. Two delete paths still bypass that rule. coga retire deletes a done ticket deterministically, without Retro (src/coga/resources/retire.md), and an ordinary human coga delete has the same gap (src/coga/commands/delete.py plus delete_task.run_delete_task). Either can break navigation on main the way the README link to document-the-remedy-for-a-bloated-blackboard-sibli did (fixed by PR #1214). Decide whether delete_task should run git grep -F for the task path, excluding the task root and log.md, and warn or refuse before deleting. That would add core behavior to a shared path with two consumers (coga delete and the delete-task recipe), so check the microkernel rule. Also decide whether coga retire should repoint the links itself.
+Deleting a ticket can break durable navigation to it. Retro already inspects
+inbound references and repoints live links in a reviewed PR, but ordinary
+`coga delete`, the `delete-task` recipe, and deterministic retirement of done
+tickets remove the source without that inspection. Add an advisory diagnostic
+before permanent deletion so an operator sees the potential damage.
+
+Proposed decision for design review: **warn and continue**, rather than refuse
+or rewrite links. A literal search cannot establish whether every mention is
+a live link, and making it a gate would block valid deletion on historical
+mentions. Done-ticket retire remains deterministic and uses the same warning;
+it does not run Retro or edit referring documents. Link repair belongs in a
+reviewed change that pins references and deletes the source together, as Retro
+already does. This safeguard makes risk visible; it does not guarantee that
+deleting a ticket preserves navigation.
+
+### Acceptance criteria
+
+- [ ] Before filesystem removal, `coga delete <ref>`, `coga run delete-task
+  <ref>`, and the done-ticket path of `coga retire <ref>` emit the same
+  advisory warning to stderr when eligible tracked working-tree files contain
+  <arm-word> references. The warning identifies the deleted ticket, reports
+  referring file paths and line numbers, says these are possible inbound
+  references, and says deletion will continue and links may need pinning in a
+  reviewed change. It must not claim that every match is a broken link.
+- [ ] Search from the Git top level, using fixed strings for both the resolved
+  ticket's repository-relative path and its final slug component without
+  `.md`. For a directory ticket search its directory path (which also matches
+  links to sibling attachments); for a file ticket search the `.md` path.
+  The leaf term catches relative links omitting the full configured task root.
+  Use tracked working-tree contents, including unstaged edits, not only HEAD
+  or index contents. No network access or repository-wide link parser is added.
+- [ ] Exclude the configured tasks tree, the configured log file, and
+  `docs/archive/**` from <arm-word> content searches. The tasks exclusion is
+  the whole transient tasks tree, not merely the deleted ticket. Resolve
+  configured paths against the Git root; invocation from a subdirectory,
+  nested task slugs, nondefault workspace paths, and both ticket forms work.
+  Do not inspect untracked files. Results are deterministic and duplicate
+  matches from the two search terms appear only once per referring line.
+- [ ] A <arm-word> match alone never changes the existing success status or
+  deletion/publication behavior. Preserve the existing stdout deletion report
+  and `run_delete_task()` string return contract. No referring file is modified,
+  no PR or agent is started, and no confirmation or force flag is introduced.
+- [ ] A successful search with no matches is quiet. With Git disabled, Git
+  unavailable, no Git work tree, or a search error, deletion remains available
+  and stderr explicitly says the reference check was skipped or failed; do not
+  report these cases as a successful zero-match scan. Distinguish `git grep`
+  exit 1 (no matches) from execution failures. Invalid deletion targets retain
+  their existing refusal behavior and are checked before attempting a scan.
+- [ ] Permanent removal through recurring promotion receives the default
+  diagnostic too. Same-path replacement of a completed recurring period skips
+  the reference diagnostic: the path is recreated as part of that operation.
+  It retains the shared deletion implementation and its lock/error handling.
+- [ ] The deletion's checkout-local spawn-admission barrier and existing
+  `DeleteTaskError` handling remain intact. The warning is emitted before
+  unlink/rmtree, including when filesystem removal subsequently fails.
+- [ ] Regression coverage exercises relative links and control-branch URLs,
+  file and directory tickets (including attachment links), exclusions, quiet
+  zero-match behavior, scan failure/disabled Git, working-tree edits, configured
+  paths, and stderr/stdout separation. Integration coverage proves the CLI,
+  recipe, and deterministic retire paths surface the warning and still delete;
+  recurring replacement is quiet while promotion retains the default check.
+- [ ] Update the packaged owning deletion contract and retire contract in the
+  implementation PR; reconcile their summaries and the knowledge-placement
+  warning. Record the heuristic's false positives (including commit permalinks,
+  longer slugs, fixture mentions, and prose) and blind spots rather than
+  promising complete link validation. Run the required Linux verification per
+  `coga-dev/testing`; native verification is deferred to release.
+
+### Proposed shape
+
+1. Keep the guard with `src/coga/delete_task.py`, `run_delete_task()`, so
+   callers cannot accidentally omit it. Add a small private <arm-word>-search
+   and diagnostic helper there, not a new general link-checking subsystem.
+   Run the check after target validation and before removal inside the existing
+   state-lock scope. Capture Git's status/output explicitly so exit 1 is not
+   confused with a failed scan. Invoke Git with an argv list and literal,
+   root-anchored exclusion paths; handle spaces and pathspec metacharacters.
+2. Add a keyword-only opt-out such as `check_references=False` solely for
+   `src/coga/recurring.py`, `create_template()`'s same-path completed-period
+   replacement. Default to checking for every other caller, including
+   `promote_task()`. Keep warning output separate from the returned deletion
+   report so existing callers and stdout contracts stay stable.
+3. Let `src/coga/commands/delete.py`, `delete()`, and the packaged retire
+   script's `_delete_done_task()` inherit the check through their existing
+   calls. Do not duplicate search or repair logic in the command heads.
+4. Add focused deletion regression tests and extend the existing command,
+   runner, retire, and recurring coverage as appropriate. Use temporary Git
+   fixture repositories; never search this repository's restricted archive to
+   test the scanner. After focused checks, run the full Linux suite and
+   ticket-scoped validation, recording exact commands and receipts.
+5. Put the shared behavioral contract in packaged `coga/checkout-cleanup`
+   under `coga delete`; make `bootstrap/delete-task` summarize and link to it.
+   Update packaged `bootstrap/retire/ticket.md` step 5 to link to that contract
+   and explicitly retain deterministic deletion without automatic repointing.
+   In packaged `coga/knowledge`, reconcile the retirement paragraph with
+   Retro's existing reference-pin behavior and the advisory deletion check.
+   Inspect `resources/retire.md` and the Retro skill for dependent summaries;
+   their canceled-ticket reference repair procedure remains authoritative.
+
+### Out of scope
+
+Automatic reference edits, commit selection or permalink generation, new PRs
+or agents during done retirement, refusal/force policy, parsing Markdown or
+GitHub URL semantics, searching Git history/untracked files/restricted archives,
+a configurable search-policy framework, changing checkout cleanup or publication
+transactions, and cleanup of all existing ticket links. The check observes this
+checkout only; it does not establish remote-main freshness or serialize edits
+in other checkouts.
 
 ## Context
 
+### Code relationships and required reading
+
+- `src/coga/delete_task.py`, `run_delete_task()`, validates the resolved
+  ticket and holds `git.state_lock()` while removing the file or directory.
+  `run_delete_task_recipe()` resolves one argument and prints the returned
+  report. `src/coga/commands/delete.py`, `delete()`, calls that same removal
+  function, then separately publishes only the task path and log. Therefore
+  repairing a referring document inside this primitive would not make its
+  publication atomic with the deletion.
+- `src/coga/resources/templates/coga/bootstrap/retire/ticket.py`,
+  `retire()` dispatches done tickets to `_delete_done_task()`, which calls
+  `run_delete_task()` and publishes the removal. The similarly named
+  `src/coga/resources/retire.md` is the canceled-ticket Retro shell, not the
+  deterministic done-ticket implementation. The command's behavior owner is
+  `src/coga/resources/templates/coga/bootstrap/retire/ticket.md`.
+- `src/coga/recurring.py`, `create_template()` deletes a stale completed
+  period through `run_delete_task()` immediately before `_create_at_slug()`
+  recreates it. `promote_task()` calls the same deletion function after
+  constructing a recurring template at a different path. Only the former
+  qualifies for the same-path diagnostic opt-out.
+- `src/coga/git.py`, `toplevel()` resolves the Git root; `run_git()` treats
+  every nonzero status as `GitError`, so a direct grep call must account for
+  its normal no-match status rather than silently treating all failures as
+  absence. Reuse appropriate shared infrastructure without expanding Git's
+  public API solely for this private diagnostic.
+- Read `docs/contexts/coga-dev/microkernel/SKILL.md`, especially “The
+  microkernel rule” and “The kernel tier and its edges” (cited, not attached).
+  This is shared task-IO behavior used by the delete head, fixed recipe, and
+  shipped retire script; the recipe is already an accepted co-versioned core
+  contract. The diagnostic belongs in that existing shared path. Deterministic
+  retire orchestration remains at the edge; no edge implementation is imported
+  into core.
+- Read `src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md`,
+  “Inbound references” (cited, not attached): it owns inspection and reviewed
+  repointing, distinguishes commit permalinks from live references, and
+  excludes transient tasks and the log. The new advisory intentionally uses
+  <arm-word> search without pretending to perform that agent judgment.
+- Read `src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/SKILL.md`,
+  “coga delete”, and the `bootstrap/delete-task` skill at
+  `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/delete-task/SKILL.md`
+  (cited, not attached), before updating their contract and summary. Read
+  `src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md`,
+  “Where knowledge lives” and “Narrative links, never restates”, for ownership
+  and dependent-summary reconciliation.
+- Tests already cover these consumers in `tests/test_commands.py`,
+  `tests/test_runner.py`, `tests/test_retire.py`, and `tests/test_recurring.py`.
+  Read `docs/contexts/coga-dev/testing/SKILL.md`, “Verification tiers and
+  receipts”, before implementation verification (cited, not attached).
+
 <!-- Ticket guide — keep this comment when filling in or updating the ticket.
 It documents field shapes; these are examples, not values to copy into every
 ticket. Omit optional fields and sections until needed. Editing rules come
@@ -137,4 +293,22 @@ ordinary ticket.
 
 <!-- coga:blackboard -->
 
-The blackboard is a notepad to be written to often as the human and agent works through a task.
+## Design handoff
+
+Investigated at `ebdf2d2461762ccbde7c3dcec14ed26cb509b1a5` on clean
+`main`, equal to freshly fetched `origin/main`. No branch or PR is recorded
+for this design task. No implementation was attempted.
+
+Proposed advisory <arm-word> search, warn-and-continue, no automatic retire
+repointing. Literal matches are deliberately conservative; the warning does
+not prove a live link. Found additional recurring callers: suppress the check
+only for same-path period replacement, retain it for promotion. The full spec
+and source relationships are above the fence in composed sections.
+
+## Open Questions
+
+None unresolved for producing an implementable proposal. The evaluator and
+owner should review warn-versus-refuse and the conservative <arm-word>-search
+tradeoff before implementation; these are proposed decisions, not approval.
+
+Verification: `coga validate --task warn-when-coga-delete-or-coga-retire-leaves-a-live --json` passed (`ok_count: 1`, no issues). `git diff --check` passed after whitespace cleanup. Final fetch confirmed `origin/main` unchanged at the investigation revision. Ticket-only design change; implementation tests were not run.
```
