---
title: Preflight dirty tracked files before skill-update PR checkout
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
    skills:
    - code/peer-review
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
step: 1 (implement)
agent: claude
launch_generation: 870e7eca-41b2-46ae-94c6-d7b0be036ca9
---

## Description

`coga skill update --all --pr` applies updates before `skill_manager.run_skill_update_pr_flow` carries them onto the shared branch with `git checkout -B coga/skill-update <control-branch>` (`_commit_skill_updates`, `_checkout`). Its preflight `skill_manager._assert_no_unmerged_paths` checks only `git diff --name-only --diff-filter=U`, so an ordinary dirty tracked file the checkout would overwrite (for example `coga/log.md`) reaches Git, which refuses with the raw "Your local changes ... would be overwritten by checkout" error; Coga exits 2 with the applied skill updates left in the working tree. Add a targeted dirty-file preflight (fail loud, naming the paths and the remedy) before any update is applied, with a regression test. Moved out of the shipped `coga/skill-management` topic by blocks/09 (Known gaps do not ship); residue recorded when `_v2/skill-update-aborts-on-uncommitted-log-file` was canceled.

Done means:

- `coga skill update --all --pr`, run with a dirty tracked file that the
  branch switch would overwrite, exits non-zero with a Coga error before
  `update_skills` writes anything. The error lists each offending path and
  says how to fix it (commit or stash, then retry). No skill update is left
  behind in the working tree.
- A dirty tracked file that the switch would carry over safely does not
  block the run. The weekly job must keep working when an unrelated,
  harmless edit is present. When HEAD is the control branch, the check
  finds nothing to block, which is correct: Git never refuses that
  checkout. The reported failure only happens off the control branch.
- The existing unmerged-paths refusal still fires, with its message
  unchanged.
- Regression tests in `tests/test_skill_manager.py` cover the blocking case
  and the non-blocking case. Add a CLI-level test if the check runs in the
  command handler.

## Context

### Code map (as of 2026-11-04)

- `commands/skill.py` `update`: runs `update_skills` before
  `run_skill_update_pr_flow`, so the preflight cannot stay inside the PR
  flow. Add a `skill_manager` preflight and call it from the handler
  before `update_skills` when `pr and all_skills`. Move the
  "`--pr` needs `--all`" refusal above it.
- `skill_manager._assert_no_unmerged_paths` (`--diff-filter=U` only): fold
  it into the new preflight. Do not duplicate it.
- `skill_manager._commit_skill_updates`: runs `git checkout -B
  coga/skill-update <cfg.git_control_branch>` in `cfg.repo_root.parent`,
  then stages only `skills_root(cfg)`. The `finally` in the PR flow
  returns to the original branch.
- PR-flow tests in `tests/test_skill_manager.py` use exact-argv fake
  runners, which need the new git calls added. Prefer one real-git
  `tmp_path` test for the overwrite case.

### Design points for implement

- **Targeted, not "any dirty file".** Git refuses the checkout only when a
  locally modified tracked path also differs between `HEAD` and the start
  point. Block on the intersection of (a) dirty tracked paths, staged or
  unstaged, from `git diff --name-only HEAD`, and (b) `git diff --name-only
  HEAD <control-branch>`. A plain "tree must be clean" check would fail
  the weekly job for harmless edits. Record the chosen rule on the
  blackboard if it differs from this one. Use `--no-renames -z` on both
  diffs: rename detection would hide the source path, and `-z` avoids
  quoted path names. Diff paths are relative to the repo top, which
  matches `cwd`. The control branch is a local ref (`git_control_branch`,
  default `main`), so a stale local `main` widens the diff. Over-blocking
  in that case is acceptable.
- **Also block when `skills_root` itself differs between HEAD and the
  control branch.** The updates dirty files under `skills_root` *after*
  the preflight runs, so the pre-update dirty set misses them. Without
  this check, the raw Git error can still come back after updates are
  applied.
- **Untracked files:** Git also refuses when an untracked file sits at a
  path that exists in the control branch but not in HEAD. Either cover
  this (untracked paths ∩ paths added in the control branch) or record on
  the blackboard that it is out of scope, with the reason.
- Also check the return trip. The `finally` checks out the original branch,
  and that can hit the same refusal. Starting with no blocking dirty files
  plus committing only `skills_root` should keep the return trip safe;
  confirm it.
- Pre-existing edits under `skills_root(cfg)`, untracked ones included,
  get swept into the PR commit by `git add -- skills_root` and then vanish
  from the user's branch on the return checkout. Decide explicitly whether
  the preflight refuses them, and record the decision on the blackboard.
  Refusing is the default unless you find a reason not to.
- The preflight refuses even when no update would change anything,
  because it runs before the updates are known. That is accepted:
  checking afterwards is exactly the bug.
- The original trigger was the recurring job's own uncommitted
  `coga/log.md` launch append. Check whether launch now commits that
  append before `ticket.py` runs (`launch.commit_log`). If it does not,
  this fix turns the crash into a clean refusal, but the job will still
  fail whenever it runs off the control branch. Report that on the
  blackboard; fixing it is out of scope here.
- Out of scope: on a detached HEAD, `_current_git_branch` returns an
  empty name, so the `finally` never returns from `coga/skill-update`.
- Sibling ticket `v1/11-skill-update-rebuilds-its-branch-and-discards-hand-pushed-commits`
  changes the same `_commit_skill_updates` and checkout path. Expect
  textual conflicts if both are in flight. Reconcile them rather than
  rewriting the other change.

### Docs

`coga/skill-management` (`docs/contexts/coga/skill-management/SKILL.md`)
is cited, not attached. It documents `--pr` in its command section. If you
add a user-visible refusal, add one line there and in the packaged twin
under `src/coga/resources/templates/coga/bootstrap/contexts/`, which
`tests/test_packaging.py` enforces. Do not reintroduce a "Known gaps"
section; blocks/09 removed it.

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

Previous ref: `preflight-dirty-tracked-files-before-skill-update` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: coga/v1-10-preflight-dirty-skill-update
