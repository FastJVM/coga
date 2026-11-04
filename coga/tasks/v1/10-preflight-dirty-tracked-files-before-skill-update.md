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
step: 4 (review)
agent: claude
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

pr: https://github.com/FastJVM/coga/pull/1168
branch: coga/v1-10-preflight-dirty-skill-update

## Implementation and decisions

Claude implemented the preflight in original commit `c12ce8fbb` (now
`f13175a99` after reconciliation). Codex's peer-review fixes are
`6b07ece3b` and `30a730532`. The final head is committed and pushed; no PR has
been opened in this step.

- The handler rejects `--pr` without `--all`, then preflights before
  `update_skills`. The existing unmerged-path check runs first, with its
  message unchanged; the PR flow's only production caller is this handler.
- The dirty tracked set is the union of the unstaged diff and the cached
  diff against HEAD, both with `--no-renames -z`. A single `git diff HEAD`
  misses a staged edit when the working file was subsequently restored to
  HEAD. Intersect that union with HEAD/control differences.
- Refuse every tracked edit or nonignored untracked file under `skills_root`,
  even on control, to avoid sweeping the user's skill edits into the update.
  Also refuse committed skills-tree drift before updates can dirty that tree.
  Skills-tree drift needs a control checkout or merge, rather than a stash.
- Untracked paths use the conservative exact-path intersection with all
  HEAD/control differences. This includes the requested added-on-control
  case. Directory/file ancestor collisions and ignored files remain outside
  this targeted tracked-file fix; this is not a complete checkout simulator.
- Harmless work outside the skills tree is allowed, including staged and
  partially staged edits. `git commit --only -- <skills_root>` leaves that
  index state out of the PR. Real-Git round-trip tests prove that HEAD,
  index, unstaged changes, untracked bytes and the caller's skills survive.
- Refusal before a no-op update is intentional. Detached-HEAD return and the
  shared-branch overwrite policy in sibling
  `v1/11-skill-update-rebuilds-its-branch-and-discards-hand-pushed-commits`
  remain out of scope. That sibling is still draft, with no branch changes
  to reconcile; this review does change `_commit_skill_updates`' commit argv.

## Peer review

**Direct Codex review completed** on head
`30a730532ef4214d0955f505935513daa46ff209`, base
`45a92ac8660f15e8112e29871787f76d6150c9b6`. No unresolved must-fix findings.
The initial review of Claude's implementation was independent. Codex authored
and then re-reviewed the corrections, so the final PR receipt records
self-review rather than claiming the final patch is fully independently reviewed.

Findings fixed:

1. A staged edit hidden by a later working-tree restoration bypassed the
   preflight and still caused Git's raw overwrite refusal after updates.
   Separate index/worktree diffs now catch it, including under the skills tree.
2. The unrestricted commit absorbed harmless staged edits. Returning removed
   fully staged work from the caller's branch; partially staged work could
   make the return checkout fail. Restricting the commit to the skills path
   preserves both forms, with real-Git regressions.
3. The new byte-preservation regression inherited Git's CRLF conversion.
   A system-config probe reproduced three false failures; both new Git
   fixtures now set `core.autocrlf=false`, following the testing topic.

Verification: the final full suite passed **4466 tests, 10 skipped** on
Linux/Python 3.12.12. The three CRLF-environment round-trip cases passed too.
An actual CLI subprocess printed the path and remedy, exited 2, and left the
branch, index/worktree and skill bytes unchanged. This change exposes plain
stderr, with no interactive terminal or rendered Slack surface to exercise.
Exact final-revision commands and receipts are under `## PR`.

Historical verification: new regressions first reproduced five failures
before the two functional fixes; the CRLF probe then reproduced three fixture
failures before its correction. A focused run placed inside this checkout's
ignored `.coga/` directory caused one packaging fixture failure; rerunning
outside the checkout passed all 168 focused tests. An earlier full run was
interrupted to correct the fixture; only the completed final run above counts.

Launch-log investigation: `launch._run_initial_script` calls
`launch_script.run_script_chain`; `run_script_phase` appends the script launch
line and calls `git.sync_log` before spawning `ticket.py`. The skill-update
script then invokes the recipe, which invokes `skill update --all --pr`.
Publication commits the append to control. However,
`git._fast_forward_control_locked` advances the control ref/holder and leaves
an invoking feature checkout's log dirty. Thus an off-control script can still
receive this clean refusal (also if publication fails). Repairing that launch
behavior is outside this ticket.

Freshness and handoff: rebased onto current main before the final review and
full run, fetched again after testing (main remained `45a92ac86`), pushed with
`--force-with-lease`, and returned this clean checkout to current main. The
handoff and preparation record are written on control, never committed to the
feature branch. Next step is mechanical PR publication.

Control handoff validation: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task v1/10-preflight-dirty-tracked-files-before-skill-update --json` returned `ok_count: 1`, no fixes and no issues.

## PR

```yaml
title: Preflight skill-update PR checkout and preserve staged work
author: claude/codex
author_evidence: Claude authored the implementation (original c12ce8fbb, rebased to f13175a99), as recorded
  by the implement session. Codex authored review fixes 6b07ece3b and the fixture correction 30a730532
  in this peer-review session.
head: 30a730532ef4214d0955f505935513daa46ff209
base: 45a92ac8660f15e8112e29871787f76d6150c9b6
depth: deep
rationale: Inspect the Git refusal and index-preservation rules, including the deliberately conservative
  skills-tree guard. The full Linux suite and real-Git regressions pass; Codex independently reviewed
  the Claude implementation but self-reviewed its own final fixes.
implementation: Runs the PR preflight before update_skills, retaining the unchanged unmerged-path refusal.
  It checks staged and unstaged tracked changes separately against HEAD/control differences, checks untracked
  paths, and refuses existing skills-tree work or branch drift. The PR commit uses --only with the skills
  path so unrelated staged work survives the round trip.
deviations: Uses the union of index and working-tree diffs instead of git diff HEAD because staged edits
  can cancel out in the latter. Restricts the commit path to fix the discovered staged-work loss and return-checkout
  failure. Untracked matching remains the conservative exact-path intersection with all HEAD/control differences.
  Preflight also refuses no-op runs, as the ticket accepts.
limitations: Detached-HEAD return is unchanged. Untracked checks cover exact-path collisions and nonignored
  skills-tree files, not ignored files or directory/file ancestor collisions. Script launch publishes
  its audit append to control but can leave it dirty in a feature checkout, so an off-control job can
  still receive a clean refusal. Linux/Python 3.12.12 only; no native Windows or Python 3.11 run. Final
  Codex fixes have self-review rather than a second independent review.
files:
  src/coga/skill_manager.py: Add the read-only preflight and NUL-delimited path helper; move the existing
    conflict check; restrict the update commit to the skills tree to preserve unrelated staged work.
  src/coga/commands/skill.py: Validate --pr/--all and invoke preflight before update_skills writes anything.
  tests/test_skill_manager.py: Cover real-Git overwrite refusal, harmless edits, hidden staged changes,
    untracked collisions, skills-tree dirt/drift, CLI ordering, and index/worktree preservation through
    commit and return; update exact-argv fakes and isolate line endings.
  tests/test_skill_update.py: Give the no-op --pr recipe a committed Git fixture with deterministic line
    endings, since even no-op updates now preflight.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md: Document the new
    refusal/remedy and preservation of harmless staged and unstaged work in the package owner.
  docs/contexts/coga/skill-management/SKILL.md: Keep the inventoried live topic byte-identical to its
    package owner.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 30a730532ef4214d0955f505935513daa46ff209
  base: 45a92ac8660f15e8112e29871787f76d6150c9b6
  detail: Direct review completed on the final head/base with no unresolved must-fix findings. The initial
    review was independent of Claude. Codex then fixed the missed staged edits and unrestricted commit,
    corrected the CRLF-sensitive fixture, and re-reviewed the resulting six-file diff; the final receipt
    is conservatively self-review.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=/home/n/Code/coga-review-v1-10-full
  status: passed
  head: 30a730532ef4214d0955f505935513daa46ff209
  base: 45a92ac8660f15e8112e29871787f76d6150c9b6
  detail: 4466 passed, 10 skipped in 632.53s on Linux with Python 3.12.12. Includes the real-Git round-trip,
    CLI refusal, recipe and packaging tests.
- command: GIT_CONFIG_SYSTEM=/tmp/coga-v1-10-crlf.gitconfig PYTHONPATH=/home/n/Code/coga/src .venv/bin/python
    -m pytest -q -p no:cacheprovider --basetemp=/home/n/Code/coga-review-v1-10-crlf tests/test_skill_manager.py
    -k 'preserves_harmless_edits'
  status: passed
  head: 30a730532ef4214d0955f505935513daa46ff209
  base: 45a92ac8660f15e8112e29871787f76d6150c9b6
  detail: 3 passed, 105 deselected. The supplied system Git config enables core.autocrlf=true; the fixture
    correctly overrides it. This is a configuration probe on Linux, not native Windows coverage.
- command: .venv/bin/python /tmp/coga-v1-10-manual-check.py
  status: passed
  head: 30a730532ef4214d0955f505935513daa46ff209
  base: 45a92ac8660f15e8112e29871787f76d6150c9b6
  detail: 'Real subprocess CLI in a temporary Git repo: a hidden staged edit produced exit 2, named notes.md,
    and printed the commit/stash remedy. Branch, index/worktree status and skill bytes were unchanged.
    Git state publication was disabled in this isolated fixture; plain stderr was inspected.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 30a730532ef4214d0955f505935513daa46ff209
  base: 45a92ac8660f15e8112e29871787f76d6150c9b6
  detail: No whitespace errors on the final feature checkout before returning to main.
```
