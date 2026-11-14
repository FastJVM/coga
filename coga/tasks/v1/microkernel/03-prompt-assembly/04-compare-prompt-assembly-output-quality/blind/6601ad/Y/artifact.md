# Pair 6601ad, output Y (design)

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

Deleting a ticket can leave README, topic, skill, or code references pointing
at a path that no longer exists on the control branch. Retro already searches
for and reviews those references, but ordinary `coga delete`, the `delete-task`
recipe, and deterministic retirement of done tickets bypass that procedure.
Add a visible advisory diagnostic to their shared deletion path. Preserve
unattended deletion and existing exit/publication contracts; this is a warning,
not a proof that a link is broken or a refusal gate.

### Acceptance criteria

- [ ] Before filesystem removal, `coga delete`, `coga run delete-task`, and
  done-ticket `coga retire` report <arm-word> inbound references on stderr.
  Each diagnostic identifies the deleted task and referring repo-relative
  file and line, says deletion will continue, and advises inspecting live
  references and pinning them to a commit containing the ticket before
  deleting (or restoring the ticket and repairing afterward).
- [ ] Search tracked working-tree files with literal matching for both the
  resolved task's Git-root-relative removal path and its final slug component
  without `.md`. This catches control-branch URLs, full paths, and relative
  file/directory links, including nested task slugs. Resolve paths from config
  and `TaskRef`, never by assuming `coga/tasks` or the invocation directory.
- [ ] Exclude the configured tasks root (all transient tickets), configured
  global log file, and `docs/archive/**` before reading file contents. Scan
  from the actual Git root, including files outside a nested Coga workspace.
  Do not read untracked/ignored files or follow symlinks out of the tree.
  Duplicate pattern matches on one source line produce one diagnostic entry.
- [ ] Describe hits as *possible references*: longer slugs, fixture text, and
  existing commit permalinks can match and require human inspection. No
  Markdown parser or semantic link classifier is required. No claim that a
  quiet search proves deletion safe; untracked content, excluded trees, and
  other checkouts are outside this check.
- [ ] A successful scan with no matches is quiet. Disabled Git, missing Git,
  a non-Git workspace, or a failed scan produces one concise stderr warning
  that references were not checked, and deletion still proceeds. A grep exit
  of 1 means no matches; other failures must not masquerade as a clean scan.
  Expected scan failures never escape as tracebacks or `DeleteTaskError`.
- [ ] Existing stdout deletion reports, success/error exit codes, task-shape
  safety, checkout lock, publication boundaries, and retire checkout refusal
  stay intact. No confirmation, force flag, Slack notification, link edit,
  new task, or Retro agent is added for done-ticket retirement.
- [ ] Recurring same-path replacement does not warn about links to the path it
  immediately recreates. Ordinary removal, including recurring promotion,
  uses the shared warning behavior. Cover this exception explicitly rather
  than relying on a caller discarding the deletion report.
- [ ] Regression tests cover all three command routes, both ticket shapes,
  nested/custom workspace paths, working-tree edits to tracked references,
  exclusions, false positives, no matches, scan errors/unavailable Git, and
  the recurring replacement exception. Verify warning emission occurs while
  the target still exists and that deletion/publication outcomes remain the
  existing ones.
- [ ] Update the owning shared deletion topic and dependent shipped surfaces
  in the implementation PR; keep Retro's stronger search-and-repair duty.
  Record Linux checks under `coga-dev/testing`; native checks defer to release.

### Proposed shape

1. Extend `src/coga/delete_task.py`, `run_delete_task()`, with a small private
   advisory scan invoked after validating the target and before unlink/rmtree
   under the existing `git.state_lock`. Keep the returned stdout report
   unchanged; emit diagnostics to stderr so callers that ignore the return
   value cannot silently discard warnings. Use argument-vector subprocesses,
   literal Git pathspecs, and stable non-color output; distinguish grep's
   no-match status from failure. Discover the Git root through existing Git
   infrastructure and construct the two literal search patterns from the
   resolved target. Exclude restricted paths in the command, not by filtering
   already-read matches. Do not dynamically parse agent instructions.
2. Add a narrowly named keyword-only suppression for same-path replacement
   (for example `warn_inbound=True`), and opt out only at the replacement
   call in `src/coga/recurring.py`, `create_template()`. Leave `promote_task()` on the default.
   Do not add a CLI opt-out or a configuration setting.
3. Keep `src/coga/commands/delete.py`, `delete()`, and the recipe adapter
   `run_delete_task_recipe()` thin. The packaged retire script's
   `_delete_done_task()` already calls the same function; it inherits the
   diagnostic and retains its deterministic deletion/publication procedure.
   Retire will not repoint links: literal matches cannot safely determine
   intent, and doc edits need a reviewable change alongside deletion. An
   operator who needs prevention must inspect and repair before invocation;
   this advisory command cannot pause for that work.
4. The scan belongs with shared task deletion: `delete()`,
   `run_delete_task_recipe()`, and retire's `_delete_done_task()` consume that
   exact shared symbol, with recurring removal as another consumer. This
   meets the microkernel shared-infrastructure rule, and the registered
   `delete-task` recipe already has a co-versioned argv/report/exit contract.
   Do not introduce a new command, recipe, plugin, or general link checker.
5. Put the shared advisory contract in the packaged
   `coga/checkout-cleanup` topic's `coga delete` section. Summarize and link it
   from `bootstrap/delete-task` and `bootstrap/retire`; adjust the retire
   resource, lifecycle/knowledge summaries, and Retro text only where their
   descriptions would otherwise contradict the new warning. The stronger
   Retro procedure still owns classification and permalink repair, while
   core reports candidates only. Add regressions primarily in
   `tests/test_commands.py` and `tests/test_retire.py`, with recurring and
   package-template assertions where affected.

### Out of scope

Automatic reference repair; refusal on matches; changing done-versus-canceled
retirement; changing Retro's PR procedure; checking external repos, remote
pages, or untracked files; parsing arbitrary repo search policies; introducing
configuration for scan exclusions; exhaustive URL/Markdown validation; changing
publication semantics or the generic state sweep.

## Context

- `src/coga/delete_task.py`, `run_delete_task()`, holds `git.state_lock`,
  validates `TaskRef.ticket_path`, and chooses `rmtree` for `ticket.md` versus
  `unlink` for file-form tickets. `run_delete_task_recipe()` resolves one
  argument and prints that function's report without publishing.
- `src/coga/commands/delete.py`, `delete()`, calls `run_delete_task()` then
  publishes only the resolved task path and `paths.log_path(cfg)` through
  `git.publish()`. Therefore reference edits cannot be assumed to land
  atomically with a human delete.
- `src/coga/resources/templates/coga/bootstrap/retire/ticket.py`,
  `retire()`, routes done tickets to `_delete_done_task()` after cleanup;
  `_delete_done_task()` calls `run_delete_task()` then `git.publish()`.
  The contract owner is its sibling `ticket.md`; `src/coga/resources/retire.md`
  is the generated canceled-ticket agent task body, not the deterministic
  done-ticket implementation.
- `src/coga/recurring.py`, `create_template()` and `promote_task()`, call
  `run_delete_task()` during serviced period replacement and promotion
  respectively; distinguish recreation from permanent removal
  when adding the diagnostic. `src/coga/tasks.py`, `TaskRef.ticket_path` and
  `TaskRef.id_slug`, supply resolved identity rather than the user's prefix.
- Cited rather than attached: read `coga-dev/microkernel` at
  `docs/contexts/coga-dev/microkernel/SKILL.md`, “The microkernel rule” and
  “The kernel tier and its edges”, for the shared-symbol and recipe boundary.
- Cited rather than attached: read `coga/checkout-cleanup` at
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/SKILL.md`,
  “coga delete”, for the owning deletion contract, and `coga/knowledge` at
  the sibling `knowledge/SKILL.md`, “Where knowledge lives” and “Narrative
  links, never restates”, for ownership and dependent-surface updates.
- Read the packaged `retro/done-ticket/SKILL.md` under
  `src/coga/resources/templates/coga/bootstrap/skills/`, “Inbound references”.
  Its procedure searches both full path and leaf, excludes tickets/log and
  restricted trees, classifies matches, and pins real references in a PR.
- Cited rather than attached: read `coga-dev/testing` at
  `docs/contexts/coga-dev/testing/SKILL.md`, “Verification tiers and receipts”.

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

Inspected clean `main` at `b23d6db94a64b5153a9448091e110d0c6f259ef7`;
no task feature branch or PR is recorded, so no branch PR merge check applies.
The configured origin is a local bare trial remote; fetched and fast-forward
check passed before design. No implementation code, branch, or PR created.

Proposal: advisory <arm-word> warnings on stderr from shared deletion, never a
refusal or automatic rewrite. Retire inherits that behavior without an agent.
Literal false positives are an explicit tradeoff; excluded archives and failed
scans never become claims of safety. Same-path recurring replacement opts out.
The design is for evaluator and owner review, not self-approved.

Verification: `coga validate --task
warn-when-coga-delete-or-coga-retire-leaves-a-live --json` returned one OK,
zero issues. Design-only ticket edit; implementation tests belong to the
implementation step.

## Open Questions

None requiring unavailable input for this design step. Warning policy and
retire's lack of automatic repair are concrete proposals for the owner gate.

````

## Change to the ticket

```diff
diff --git a/coga/tasks/warn-when-coga-delete-or-coga-retire-leaves-a-live.md b/coga/tasks/warn-when-coga-delete-or-coga-retire-leaves-a-live.md
index 696fe0c..829d43a 100644
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
@@ -42,15 +42,149 @@ workflow:
     - code/address-pr-comments
     assignee: owner
     checkout: reuse-required
-step: 1 (design)
+step: 2 (evaluate-design)
 ---
 
 ## Description
 
-Follow-up from make-retro-check-inbound-doc-links-before-deleting. That ticket made retro/done-ticket search tracked files for a source task's path and repoint live-tree references (blob/<control-branch> URLs, relative links) to a commit permalink before deleting. Two delete paths still bypass that rule. coga retire deletes a done ticket deterministically, without Retro (src/coga/resources/retire.md), and an ordinary human coga delete has the same gap (src/coga/commands/delete.py plus delete_task.run_delete_task). Either can break navigation on main the way the README link to document-the-remedy-for-a-bloated-blackboard-sibli did (fixed by PR #1214). Decide whether delete_task should run git grep -F for the task path, excluding the task root and log.md, and warn or refuse before deleting. That would add core behavior to a shared path with two consumers (coga delete and the delete-task recipe), so check the microkernel rule. Also decide whether coga retire should repoint the links itself.
+Deleting a ticket can leave README, topic, skill, or code references pointing
+at a path that no longer exists on the control branch. Retro already searches
+for and reviews those references, but ordinary `coga delete`, the `delete-task`
+recipe, and deterministic retirement of done tickets bypass that procedure.
+Add a visible advisory diagnostic to their shared deletion path. Preserve
+unattended deletion and existing exit/publication contracts; this is a warning,
+not a proof that a link is broken or a refusal gate.
+
+### Acceptance criteria
+
+- [ ] Before filesystem removal, `coga delete`, `coga run delete-task`, and
+  done-ticket `coga retire` report <arm-word> inbound references on stderr.
+  Each diagnostic identifies the deleted task and referring repo-relative
+  file and line, says deletion will continue, and advises inspecting live
+  references and pinning them to a commit containing the ticket before
+  deleting (or restoring the ticket and repairing afterward).
+- [ ] Search tracked working-tree files with literal matching for both the
+  resolved task's Git-root-relative removal path and its final slug component
+  without `.md`. This catches control-branch URLs, full paths, and relative
+  file/directory links, including nested task slugs. Resolve paths from config
+  and `TaskRef`, never by assuming `coga/tasks` or the invocation directory.
+- [ ] Exclude the configured tasks root (all transient tickets), configured
+  global log file, and `docs/archive/**` before reading file contents. Scan
+  from the actual Git root, including files outside a nested Coga workspace.
+  Do not read untracked/ignored files or follow symlinks out of the tree.
+  Duplicate pattern matches on one source line produce one diagnostic entry.
+- [ ] Describe hits as *possible references*: longer slugs, fixture text, and
+  existing commit permalinks can match and require human inspection. No
+  Markdown parser or semantic link classifier is required. No claim that a
+  quiet search proves deletion safe; untracked content, excluded trees, and
+  other checkouts are outside this check.
+- [ ] A successful scan with no matches is quiet. Disabled Git, missing Git,
+  a non-Git workspace, or a failed scan produces one concise stderr warning
+  that references were not checked, and deletion still proceeds. A grep exit
+  of 1 means no matches; other failures must not masquerade as a clean scan.
+  Expected scan failures never escape as tracebacks or `DeleteTaskError`.
+- [ ] Existing stdout deletion reports, success/error exit codes, task-shape
+  safety, checkout lock, publication boundaries, and retire checkout refusal
+  stay intact. No confirmation, force flag, Slack notification, link edit,
+  new task, or Retro agent is added for done-ticket retirement.
+- [ ] Recurring same-path replacement does not warn about links to the path it
+  immediately recreates. Ordinary removal, including recurring promotion,
+  uses the shared warning behavior. Cover this exception explicitly rather
+  than relying on a caller discarding the deletion report.
+- [ ] Regression tests cover all three command routes, both ticket shapes,
+  nested/custom workspace paths, working-tree edits to tracked references,
+  exclusions, false positives, no matches, scan errors/unavailable Git, and
+  the recurring replacement exception. Verify warning emission occurs while
+  the target still exists and that deletion/publication outcomes remain the
+  existing ones.
+- [ ] Update the owning shared deletion topic and dependent shipped surfaces
+  in the implementation PR; keep Retro's stronger search-and-repair duty.
+  Record Linux checks under `coga-dev/testing`; native checks defer to release.
+
+### Proposed shape
+
+1. Extend `src/coga/delete_task.py`, `run_delete_task()`, with a small private
+   advisory scan invoked after validating the target and before unlink/rmtree
+   under the existing `git.state_lock`. Keep the returned stdout report
+   unchanged; emit diagnostics to stderr so callers that ignore the return
+   value cannot silently discard warnings. Use argument-vector subprocesses,
+   literal Git pathspecs, and stable non-color output; distinguish grep's
+   no-match status from failure. Discover the Git root through existing Git
+   infrastructure and construct the two literal search patterns from the
+   resolved target. Exclude restricted paths in the command, not by filtering
+   already-read matches. Do not dynamically parse agent instructions.
+2. Add a narrowly named keyword-only suppression for same-path replacement
+   (for example `warn_inbound=True`), and opt out only at the replacement
+   call in `src/coga/recurring.py`, `create_template()`. Leave `promote_task()` on the default.
+   Do not add a CLI opt-out or a configuration setting.
+3. Keep `src/coga/commands/delete.py`, `delete()`, and the recipe adapter
+   `run_delete_task_recipe()` thin. The packaged retire script's
+   `_delete_done_task()` already calls the same function; it inherits the
+   diagnostic and retains its deterministic deletion/publication procedure.
+   Retire will not repoint links: literal matches cannot safely determine
+   intent, and doc edits need a reviewable change alongside deletion. An
+   operator who needs prevention must inspect and repair before invocation;
+   this advisory command cannot pause for that work.
+4. The scan belongs with shared task deletion: `delete()`,
+   `run_delete_task_recipe()`, and retire's `_delete_done_task()` consume that
+   exact shared symbol, with recurring removal as another consumer. This
+   meets the microkernel shared-infrastructure rule, and the registered
+   `delete-task` recipe already has a co-versioned argv/report/exit contract.
+   Do not introduce a new command, recipe, plugin, or general link checker.
+5. Put the shared advisory contract in the packaged
+   `coga/checkout-cleanup` topic's `coga delete` section. Summarize and link it
+   from `bootstrap/delete-task` and `bootstrap/retire`; adjust the retire
+   resource, lifecycle/knowledge summaries, and Retro text only where their
+   descriptions would otherwise contradict the new warning. The stronger
+   Retro procedure still owns classification and permalink repair, while
+   core reports candidates only. Add regressions primarily in
+   `tests/test_commands.py` and `tests/test_retire.py`, with recurring and
+   package-template assertions where affected.
+
+### Out of scope
+
+Automatic reference repair; refusal on matches; changing done-versus-canceled
+retirement; changing Retro's PR procedure; checking external repos, remote
+pages, or untracked files; parsing arbitrary repo search policies; introducing
+configuration for scan exclusions; exhaustive URL/Markdown validation; changing
+publication semantics or the generic state sweep.
 
 ## Context
 
+- `src/coga/delete_task.py`, `run_delete_task()`, holds `git.state_lock`,
+  validates `TaskRef.ticket_path`, and chooses `rmtree` for `ticket.md` versus
+  `unlink` for file-form tickets. `run_delete_task_recipe()` resolves one
+  argument and prints that function's report without publishing.
+- `src/coga/commands/delete.py`, `delete()`, calls `run_delete_task()` then
+  publishes only the resolved task path and `paths.log_path(cfg)` through
+  `git.publish()`. Therefore reference edits cannot be assumed to land
+  atomically with a human delete.
+- `src/coga/resources/templates/coga/bootstrap/retire/ticket.py`,
+  `retire()`, routes done tickets to `_delete_done_task()` after cleanup;
+  `_delete_done_task()` calls `run_delete_task()` then `git.publish()`.
+  The contract owner is its sibling `ticket.md`; `src/coga/resources/retire.md`
+  is the generated canceled-ticket agent task body, not the deterministic
+  done-ticket implementation.
+- `src/coga/recurring.py`, `create_template()` and `promote_task()`, call
+  `run_delete_task()` during serviced period replacement and promotion
+  respectively; distinguish recreation from permanent removal
+  when adding the diagnostic. `src/coga/tasks.py`, `TaskRef.ticket_path` and
+  `TaskRef.id_slug`, supply resolved identity rather than the user's prefix.
+- Cited rather than attached: read `coga-dev/microkernel` at
+  `docs/contexts/coga-dev/microkernel/SKILL.md`, “The microkernel rule” and
+  “The kernel tier and its edges”, for the shared-symbol and recipe boundary.
+- Cited rather than attached: read `coga/checkout-cleanup` at
+  `src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/SKILL.md`,
+  “coga delete”, for the owning deletion contract, and `coga/knowledge` at
+  the sibling `knowledge/SKILL.md`, “Where knowledge lives” and “Narrative
+  links, never restates”, for ownership and dependent-surface updates.
+- Read the packaged `retro/done-ticket/SKILL.md` under
+  `src/coga/resources/templates/coga/bootstrap/skills/`, “Inbound references”.
+  Its procedure searches both full path and leaf, excludes tickets/log and
+  restricted trees, classifies matches, and pins real references in a PR.
+- Cited rather than attached: read `coga-dev/testing` at
+  `docs/contexts/coga-dev/testing/SKILL.md`, “Verification tiers and receipts”.
+
 <!-- Ticket guide — keep this comment when filling in or updating the ticket.
 It documents field shapes; these are examples, not values to copy into every
 ticket. Omit optional fields and sections until needed. Editing rules come
@@ -137,4 +271,25 @@ ordinary ticket.
 
 <!-- coga:blackboard -->
 
-The blackboard is a notepad to be written to often as the human and agent works through a task.
+## Design handoff
+
+Inspected clean `main` at `b23d6db94a64b5153a9448091e110d0c6f259ef7`;
+no task feature branch or PR is recorded, so no branch PR merge check applies.
+The configured origin is a local bare trial remote; fetched and fast-forward
+check passed before design. No implementation code, branch, or PR created.
+
+Proposal: advisory <arm-word> warnings on stderr from shared deletion, never a
+refusal or automatic rewrite. Retire inherits that behavior without an agent.
+Literal false positives are an explicit tradeoff; excluded archives and failed
+scans never become claims of safety. Same-path recurring replacement opts out.
+The design is for evaluator and owner review, not self-approved.
+
+Verification: `coga validate --task
+warn-when-coga-delete-or-coga-retire-leaves-a-live --json` returned one OK,
+zero issues. Design-only ticket edit; implementation tests belong to the
+implementation step.
+
+## Open Questions
+
+None requiring unavailable input for this design step. Warning policy and
+retire's lack of automatic repair are concrete proposals for the owner gate.
```
