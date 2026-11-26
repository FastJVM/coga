---
title: Run a workflow step script that publishes only the current ticket to main
status: in_progress
owner: nicktoper
contexts:
- coga/git
- coga/workflows
- coga/launch
- coga/lifecycle
- coga-dev/principles
workflow:
  name: code/with-review
  enter: git/ticket-enter
  exit: git/ticket-exit
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
  - name: push-and-open-pr
    skills: []
    assignee: agent
    requires: pr
    run: git/push-and-open-pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (peer-review)
agent: claude
---

## Description

Owner design (2026-11-25, attended orient session): replace the closed `git:` launch mode with a workflow-declared step script, fold branching into it, and have it publish only the current ticket's state to main.

### Problems

1. **Ticket state lags on main.** In ticket-branch mode the ticket's live copy is on its `coga/*` branch and reaches main only at merge. `let-dream-retro-handle-period-tickets-that-were-ne` was `draft` on `origin/main` while its branch had it `in_progress` at step 4, so `coga status`, teammates and Dream on main read stale state.
2. **Other tickets block the push step.** `git/push-and-open-pr/run.py` (`dirty = ... - set(paths)`, ~line 375) exempts only the launched ticket and `coga/log.md`. Any other ticket's uncommitted blackboard edit in the shared checkout fails it with "Commit your work first: <other tickets>". The operator's workaround (`git add -u && git commit`) swept seven unrelated tickets into that PR (commit `529257375`).

### Design

Owner revision (2026-11-25, attended implement session) replaces the earlier
enter/exit-around-every-step design.

- **Kernel: two workflow-declared step scripts.** A workflow names any two
  skill refs: `enter: git/ticket-enter` and `exit: git/ticket-exit`. The
  kernel runs the `enter` skill's `run.py` when a step starts (the first step
  of a launch and each step the supervisor chains), and the `exit` skill's
  `run.py` on every step change (`coga bump`, including the owner's final
  bump to `done`, `coga mark done`, and `coga mark canceled` / `coga block`,
  which also end the session). A code session always ends on a step change,
  so `exit` is where the session's work is published. The kernel stays
  Git-free: it only runs the named scripts. The closed `GIT_MODES` map
  (`src/coga/workflow.py`) and the whole-launch hook (`src/coga/launch.py`
  `_LaunchHookGuard`, `src/coga/launch_script.py` `run_launch_hook`) go.
  Megalaunch runs these tickets like any other.
- **`git/ticket-enter`:** switch to the ticket's recorded branch, or create it
  from the current HEAD and record `branch`/`base`/`remote` under `## Dev`.
  After switching, write the base's copy of the ticket into the working tree
  (the branch holds the branch-point copy). This replaces the `open-branch`
  step and the `git/ticket-branch` hook.
- **`git/ticket-exit`:**
  1. On the ticket branch, commit everything except `coga/tasks/**` and
     `coga/log.md` and push the branch. Ticket state never lands on the code
     branch, so the PR merge never conflicts on a ticket.
  2. Switch back to the base: save the live ticket bytes, restore the ticket
     and log to `HEAD`, switch, write them back. If another modified file
     blocks the switch, fail loudly naming it.
  3. Publish only the current ticket and its log lines: fetch, build a commit
     on `<remote>/<base>` with a temporary index holding that ticket file and
     `coga/log.md` as the base's log plus this ticket's local lines not on it,
     and push it with `git push <remote> <oid>:<base>`; fast-forward the local
     base when possible. Other tickets' files and any unpushed local base
     commits are never published.
  Stop at the first Git failure, including a rejected push (no retry), with
  Git's message and local state intact. Manual catch-up is `coga sync <ticket>`
  (separate ticket), which runs `exit` by hand; the next `exit` also
  republishes the whole ticket file.
- **One session per checkout** is assumed (true in practice); `enter` does not
  guard against a concurrent launch switching the same checkout.
- **Scripts that bump** (`git/push-and-open-pr`, `code/merge-pr`) make the
  bump their last action, since `exit` switches the checkout to the
  base. `push-and-open-pr` pushes the code branch and opens or reuses the PR
  only; it no longer commits the ticket or log, and its dirty check ignores
  `coga/tasks/**` and `coga/log.md`. `code/merge-pr` drops its ticket-state
  commit the same way.
- **Workflows:** `code/*` packaged workflows declare
  `enter: git/ticket-enter` / `exit: git/ticket-exit` and drop the `open-branch` step.
  `docs/with-review` moves to the same pair. Workflows that declare no step
  scripts (`direct/body`, recurring templates) are unchanged.
- **Rebase onto the base: `git/ticket-enter` `run.py rebase`.** On the branch
  the live ticket is always modified (every `exit` commits a newer copy to the
  base), so a plain rebase refuses. The command copies the live ticket to
  `$TMPDIR`, runs `git checkout -- <ticket>`, `git rebase <remote>/<base>`,
  then copies the saved ticket back over the file. No `--autostash` and no
  merge of the ticket (owner: autostash lost code before). It stops at the
  first error with the saved copy kept in `$TMPDIR`. `code/implement`
  points at it.
- **Branch commit content:** `git add -A` minus `coga/tasks/**` and
  `coga/log.md`; untracked junk is handled with `.gitignore`.

### Migration

Live tickets are migrated, not kept on a legacy hook. A one-shot
migration script rewrites each live ticket's frozen `git: ticket-branch` to
`enter: git/ticket-enter` / `exit: git/ticket-exit`, publishes its
branch's live ticket copy to the base, and commits `coga/tasks/**` on that
branch back to its merge-base version so the branch carries no ticket
changes. Frozen steps and step numbering stay as they are (an
already-passed `open-branch` step remains in those snapshots). Once no live
ticket uses it, `git: ticket-branch` and the `git/ticket-branch` hook are
removed; `coga validate` reports any left.

### Contracts to update in the same PR

`coga/git` (Branch to merge, Ticket-branch mode), `coga/workflows`,
`coga/launch`, `coga/lifecycle` (bump, mark and block run the `exit`
script), `code/implement` (rebase through `git/ticket-enter` `run.py rebase`), and the v1/03 owner
decisions this reverses: C3's ticket commit and "the final bump on the branch
... reaches main with the PR merge". Align the README with
`coga-dev/principles`.

### Done when

- After any step change (bump, mark, block), `coga status` on a fresh clone of
  the base shows the ticket's current status and step.
- A PR opened by `code/with-review` contains no `coga/tasks/` paths.
- An `exit` publishes only the current ticket, and an uncommitted edit to
  another ticket does not block `push-and-open-pr`.
- Every live `git: ticket-branch` ticket is migrated and still launches.
- `python -m pytest` and `tests/test_packaging.py` pass.

## Context

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
        - name: open-branch
          run: git/open-branch               # Local-first skill directory containing run.py.
          assignee: agent
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (open-branch)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
A workflow run: selects a script for its step. A sibling ticket.py supplies the default script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

The recurring runner writes delegate on materialized period tickets. It
names the parent template's frozen bootstrap/<name> target.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev records branch:, base:, remote:, reviewed: (the commit OID),
and pr: (the full /pull/ URL). Write one field per line and omit unknown
values. coga/git owns the fields and the workflow that writes them.

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

### Codebase map (2026-11-25, read in the first implement session)

- `src/coga/workflow.py`: `GIT_MODES` / `DEFAULT_GIT_MODE` (closed `git:` map,
  ~line 50), `Workflow.git`, `Workflow.load` validates `git`, `Workflow.freeze`
  writes `git` after `name`, `git_mode()` reads frozen/draft mode. Replace with
  `enter:` / `exit:` skill refs (parse, freeze, accessor).
- `src/coga/launch_script.py`: `prepare_launch_hook` (copies the hook skill
  into `<tmp>/launch-hook/<ref>` so exit runs the same code after a branch
  switch) and `run_launch_hook` (subprocess `run.py <phase>`, task + tmp env,
  strips `COGA_SUPERVISED`, sentinel, expected-step vars, no secrets). Reuse
  for the new step scripts.
- `src/coga/launch.py`: `_LaunchHookGuard` (~line 368) wraps the whole chain;
  its `enter` re-reads config/ticket after the switch and refuses a mode
  mismatch; `_launch_hook_guard()` (~line 614) builds it from `git_mode`. Per
  the new design `enter` runs per step (first step + each chained step), so
  the call moves into the step chain.
- Lifecycle writers that must run `exit`: `src/coga/commands/bump.py` `bump`
  (calls `coga.bump.advance_step`, or `coga.mark.mark_done` on the final
  step), `src/coga/commands/mark.py` `done` (and canceled),
  `src/coga/mark.py` `mark_done` / `mark_canceled` / `mark_blocked`,
  `src/coga/commands/block.py` `block`. Bump already checks
  `COGA_SUPERVISED` in several places (supervised-session rules).
- `src/coga/validate.py` `_check_frozen_git_mode` (~line 1188): reports an
  unregistered frozen `git:`; adapt to the new fields and report leftover
  `git: ticket-branch` after migration.
- `src/coga/recurring.py` `assert_template_git_mode` (~line 262): templates
  must stay on `main`; keep the equivalent rule (no `enter`/`exit` on
  recurring templates until the recurring ticket lands).
- `src/coga_edge/megalaunch.py` ~line 1086: skips non-`main` modes with
  `skipped-unlaunchable`. Owner: megalaunch must run these tickets, so it
  calls the same per-step enter/exit.
- `bootstrap/skills/git/ticket-branch/run.py`: enter logic to reuse for
  `git/ticket-enter` (recorded-branch lookup, `candidates()` discovery,
  `refuse_diverged`, `record_new_branch`, `fresh_branch_name`). Its `exit_`
  (`git add -A`, commit, push, switch back) is what `git/ticket-exit` replaces.
- `bootstrap/skills/git/push-and-open-pr/run.py` `run()`: `commit_state` twice
  (before push and after bump) and `dirty = changed_paths - {ticket, log}`.
  Drop both commits, widen the dirty filter, make `bump` the last action.
- `bootstrap/skills/code/merge-pr/run.py` line ~74: `commit_state(cwd, paths)`
  to drop. `coga_edge/git_workflow.py` owns `commit_state`, `changed_paths`.
- Packaged workflows with `git: ticket-branch` + `open-branch` step:
  `bootstrap/workflows/code/{with-review,with-self-review,agent-merge,design-then-implement}.md`;
  `docs/with-review.md` has `open-branch` without `git:`.
- Tests: `tests/test_ticket_branch.py`, `tests/test_open_pr.py`,
  `tests/test_mark.py`, `tests/test_packaging.py`,
  `tests/required_package_resources.txt` (new skill files must be listed).
- Docs: `bootstrap/contexts/coga/{git,launch,workflows,lifecycle}/SKILL.md`,
  `docs/contexts/coga-dev/{current-direction,microkernel}/SKILL.md`,
  `coga/tasks/v1/03-use-git-like-everyone-remove-coga-s-publication-ab.md`.

<!-- coga:blackboard -->
## Dev

branch: coga/run-a-workflow-step-script-that-publishes-only-t
base: main
remote: origin


Design and migration decisions (2026-11-25) are in the ticket body.

## Open (owner, 2026-11-25)

- Manual publish is `coga sync <ticket>`, which calls the `exit` script by
  hand: filed as draft `add-coga-sync-to-run-a-ticket-s-exit-script-manual`.
- Removing `in_progress` (eval point 3, owner chose it; `done` stays): filed as
  its own draft ticket `remove-the-in-progress-status`, out of this scope.
- Eval points 10-12 settled in the body (rebase command, `git add -A` scope,
  workflows without step scripts). Recurring needs its own enter/exit pair for
  its disposable clone/worktree: separate ticket.

## Implementation plan (next session starts here)

Design is settled in the body (owner, attended, 2026-11-25). Slices, each
green before the next:

1. DONE (session 2). `Workflow.enter`/`.exit` (`src/coga/workflow.py`
   `STEP_SCRIPT_KEYS`, `step_script()`), frozen after `name`; `git:` +
   step scripts together is a load error. Validation
   `_check_frozen_step_scripts` (`src/coga/validate.py`); recurring templates
   with step scripts refused (`assert_template_git_mode`, validate).
   `GIT_MODES` / the old hook still in place for this session (slice 5 removes).
2. DONE (session 2). Owner decision (attended, 2026-11-25): `exit` runs in
   the lifecycle commands, not the supervisor. `src/coga/step_scripts.py`:
   - `run_exit_after_transition` after the local write in `commands/bump.py`
     (advance, rewind, final bump -> done, once), `commands/mark.py` done and
     canceled, `commands/block.py`. Runs before `emit_done_marker`; a failure
     reports, keeps the write, and exits with the script's code after the
     marker. `mark active`/`paused` and `unblock` run nothing.
   - `run_enter_before_step`: `launch_script.run_script_chain` (only steps
     with a script), `launch._supervise_steps` before each agent session
     (reloads cfg + ticket after), megalaunch `_run_ticket_chain` loop.
     Failure refuses the step.
   - Each run copies the skill into a nested tmp scope via
     `prepare_launch_hook` and runs `run.py` with no argument
     (`run_launch_hook` now takes `phase=None`).
   - Tradeoff accepted: a session ending without a step change (crash,
     Ctrl-C, timeout) runs no `exit`; next `enter` must accept "already on
     the branch, dirty". Recovery: `coga sync` (draft).
   - Tests: `tests/test_step_scripts.py` (17, fake recorder skills).
3. DONE (session 2). `src/coga_edge/ticket_git.py` (shared plumbing:
   `switch_carrying`, `publish_ticket` temp-index commit + `<oid>:<base>`
   push, `merged_log`, `fast_forward_base`); skills
   `bootstrap/skills/git/ticket-enter/{SKILL.md,run.py}` (no arg = enter,
   `rebase`) and `git/ticket-exit/{SKILL.md,run.py}`. Choices made:
   - enter: recorded branch or create; no branch-copy discovery any more
     (branches never carry the ticket). Already on the branch = no-op
     (resume after a session ended without exit).
   - exit with no `## Dev` branch on the base (owner step before any launch)
     only publishes; on any third branch it refuses.
   - Directory-form tasks publish the whole task dir minus nested tasks.
   - `rebase` keeps saved copies in `$COGA_TASK_DATA_DIR/rebase-saved/`
     (falls back to `$TMPDIR`), not `$TMPDIR` as the body says: TMPDIR is
     purged when the launch ends, which would lose the copy on a conflict.
   - A failed exit writes `<task data dir>/step-exit-failed`
     (`step_scripts.EXIT_FAILED_FILE`); `_harness_stop_reason`,
     `run_script_chain` and megalaunch `_chain_stop_result` stop on it; the
     next successful exit removes it.
   - Fast-forward of local base is skipped with a warning when it has
     unpushed commits.
   - Tests: `tests/test_ticket_enter_exit.py` (7, bare remote).
4. DONE (session 2). `push-and-open-pr`: no `commit_state`, no post-bump
   push, dirty check ignores `<coga root>/tasks/**`, bump is last. `merge-pr`:
   no state commit; push, verify, wait checks, merge, then final bump last.
   `ticket-exit` pushes the branch only when local and remote-tracking tips
   differ (a host that auto-deletes merged branches must not get it back).
   `code/{with-review,with-self-review,agent-merge,design-then-implement}` and
   `docs/with-review` declare the enter/exit pair, drop the `open-branch`
   step (its `## open-branch` section stays for frozen snapshots), and the
   `## review` sections say the final bump publishes. `code/implement` step 3
   points at `git/ticket-enter/run.py rebase`. Tests updated in
   `test_open_pr.py` (other ticket's dirt does not block; no ticket path in
   the PR), `test_bootstrap_workflow_review_sections.py`.
5. DONE (session 3). Owner chose (attended, 2026-11-26) to migrate the older
   snapshots too, not keep a legacy ticket commit in the PR scripts.
   `src/coga_edge/migrate_step_scripts.py`
   (`python -m coga_edge.migrate_step_scripts [--apply] [--path T]`): for a
   non-terminal ticket with an `open-branch` step, `git: ticket-branch`, or
   a definition declaring step scripts the snapshot lacks, adds
   `enter`/`exit`, drops `git: ticket-branch`, removes `open-branch` and
   renumbers `step`. Report-only by default; `--apply` = one temp-index
   commit on `<remote>/<base>`. Findings: no recorded branch carries ticket
   state (all remote branches gone or PR closed/merged; the three local-only
   ones touch only code), so the "reset branch tasks to merge-base" part was
   unnecessary and is not built; the script names no branch work. Dry run on
   origin/main 42f4d94fe: 68 tickets. Removed `GIT_MODES`, `git_mode`,
   `_LaunchHookGuard`, `git/ticket-branch`, `tests/test_ticket_branch.py`;
   a non-main `git:` is a load error / validate bad-shape / launch refusal /
   megalaunch skip pointing at coga/git (the kernel may not name
   `coga_edge`). `git: main` still loads as a no-op. This ticket and the
   three side drafts were migrated in place with `--path`.
6. DONE (session 3). coga/git (rewritten), workflows (`## Step scripts`),
   launch, lifecycle, first-task, pr-publication/preparation, code/open-pr,
   code/implement, `resources/ticket.md` example, coga-dev
   current-direction (amendment records the v1/03 reversals), microkernel,
   codebase; README "Use tools plainly".
7. DONE (session 3). Full suite and packaging green on f608f903f; `## PR`
   below.

Side tickets filed (drafts): `remove-the-in-progress-status`,
`add-coga-sync-to-run-a-ticket-s-exit-script-manual`,
`give-recurring-runs-their-own-enter-and-exit-step`.

Session 3 cleanup: the old hook's local-only "launch handoff" commit
22be2e3a2 had put this ticket, the three drafts and log lines on the branch
(never pushed). Rebuilt the code commit on 42f4d94fe without it; the branch
diff now has no `coga/tasks/**` or `coga/log.md` path. The drafts were
published to main on their own, and the old hook's
`$TMPDIR/git-ticket-branch.json` state was removed so this session's end
runs no old exit.

After merge (owner): run `python -m coga_edge.migrate_step_scripts`, review
the report, then `--apply`. Do not apply before merge: main's current code
ignores `enter`/`exit`, so a migrated draft launched from main would
implement without a branch.

## PR

```yaml
title: Run workflow enter/exit step scripts; publish only the current ticket to the base
author: claude
author_evidence: >-
  Implement sessions 2-3 of this ticket ran Claude (claude-opus-5-5) in an
  attended launch; the owner approved the plan and the migration scope.
head: f608f903f24b2d6bea5fd6911969c029214033ac
base: 42f4d94feca4cef02c6e6e565f4ae0ee6d34fe89
depth: deep
rationale: >-
  Changes how every branch ticket publishes state (new lifecycle-command
  side effect, pushes to the base from exit, removed launch mode) and ships a
  ticket migration; no independent review yet (peer-review is the next step).
implementation: >-
  Workflows may declare `enter:`/`exit:` step scripts. Launch, the script
  chain and megalaunch run `enter` before each step; bump, mark
  done/canceled and block run `exit` once after the write, and a failed exit
  keeps the write, exits non-zero and stops the chain. `git/ticket-enter`
  switches to or creates the ticket branch carrying the live ticket and log,
  with `run.py rebase`; `git/ticket-exit` commits code without ticket state,
  pushes the branch, returns to the base and publishes only this ticket and
  its log lines via a temp-index commit. push-and-open-pr and merge-pr no
  longer commit ticket state and bump last. The `git:` launch mode and its
  hook are removed; `coga_edge.migrate_step_scripts` rewrites in-flight
  tickets.
deviations: >-
  `rebase` keeps saved copies in $COGA_TASK_DATA_DIR, not $TMPDIR (purged at
  launch end). A failed exit writes a `step-exit-failed` record that stops
  the chain. Exit pushes the branch only when the remote lacks its tip. The
  migration does not edit branches (none carries ticket state). v1/03's owner
  decisions are reversed in coga-dev/current-direction rather than by editing
  that in-review ticket's body.
limitations: >-
  A session ending without a step change runs no exit (manual publish is
  draft add-coga-sync-...). Recurring runs cannot use step scripts (draft
  give-recurring-...). The base migration must be applied after merge.
files:
  README.md: Principle now says code rides the PR and ticket state is published to the base.
  docs/contexts/coga-dev/codebase/SKILL.md: Lists the step-script skills, ticket_git and the migration.
  docs/contexts/coga-dev/current-direction/SKILL.md: Owner amendment replacing the git mode; records the v1/03 reversals.
  docs/contexts/coga-dev/microkernel/SKILL.md: Step scripts stay Git-free in the kernel.
  src/coga/commands/block.py: Runs exit after the block write.
  src/coga/commands/bump.py: Runs exit after advance, rewind and final bump.
  src/coga/commands/mark.py: Runs exit after done and canceled.
  src/coga/launch.py: Enter before each supervised step; failed-exit stop; refuses a leftover git mode; hook guard removed.
  src/coga/launch_script.py: Script chain runs enter and stops on a failed exit; hook runner takes no phase.
  src/coga/recurring.py: Templates refuse step scripts.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: Walkthrough uses enter/exit publication.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/git/SKILL.md: Rewritten contract for branch step scripts.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: Step-script call points in the chain.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md: Lifecycle commands run exit.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/pr-publication/preparation/SKILL.md: PRs carry no ticket state.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: New Step scripts section; frozen-snapshot rules.
  src/coga/resources/templates/coga/bootstrap/skills/code/implement/SKILL.md: Branch comes from enter; commit without ticket state; rebase command.
  src/coga/resources/templates/coga/bootstrap/skills/code/merge-pr/run.py: No ticket commit; final bump last.
  src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md: Older agent PR step commits code only.
  src/coga/resources/templates/coga/bootstrap/skills/git/push-and-open-pr/run.py: No ticket commit; other tickets' dirt ignored; bump last.
  src/coga/resources/templates/coga/bootstrap/skills/git/ticket-branch/SKILL.md: Removed launch hook.
  src/coga/resources/templates/coga/bootstrap/skills/git/ticket-branch/run.py: Removed launch hook.
  src/coga/resources/templates/coga/bootstrap/skills/git/ticket-enter/SKILL.md: New enter script contract.
  src/coga/resources/templates/coga/bootstrap/skills/git/ticket-enter/run.py: Enter and rebase.
  src/coga/resources/templates/coga/bootstrap/skills/git/ticket-exit/SKILL.md: New exit script contract.
  src/coga/resources/templates/coga/bootstrap/skills/git/ticket-exit/run.py: Commit code, push, return, publish the ticket.
  src/coga/resources/templates/coga/bootstrap/workflows/code/agent-merge.md: Declares enter/exit; drops open-branch.
  src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md: Declares enter/exit; drops open-branch.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md: Declares enter/exit; drops open-branch.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-self-review.md: Declares enter/exit; drops open-branch.
  src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md: Declares enter/exit; drops open-branch.
  src/coga/resources/ticket.md: Frozen example shows enter/exit.
  src/coga/step_scripts.py: Runs enter/exit and records a failed exit.
  src/coga/validate.py: Checks frozen step scripts; reports a leftover git mode.
  src/coga/workflow.py: Parses and freezes enter/exit; git mode removed.
  src/coga_edge/megalaunch.py: Runs enter per step; stops on a failed exit; skips a leftover git mode.
  src/coga_edge/migrate_step_scripts.py: One-time ticket migration.
  src/coga_edge/ticket_git.py: Shared plumbing for the step scripts.
  tests/required_package_resources.txt: New skill files; removed hook files.
  tests/test_bootstrap_workflow_review_sections.py: Review sections name exit publication.
  tests/test_code_implement_skill.py: Pins the new implement contract.
  tests/test_compose.py: Step numbers after open-branch removal.
  tests/test_dream_worker_templates.py: Pins the new lifecycle sentence.
  tests/test_migrate_step_scripts.py: Migration rewrite, report, apply and path modes.
  tests/test_open_pr.py: No ticket path in the PR; other ticket's dirt does not block.
  tests/test_packaging.py: Canonical script set.
  tests/test_step_scripts.py: Call points, failures, removed git mode.
  tests/test_ticket_branch.py: Removed with the hook.
  tests/test_ticket_enter_exit.py: Enter/exit against a bare remote.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Independent peer review is the next workflow step.
checks:
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider
    status: passed
    head: f608f903f24b2d6bea5fd6911969c029214033ac
    base: 42f4d94feca4cef02c6e6e565f4ae0ee6d34fe89
    detail: 3243 passed, 29 skipped.
  - command: .venv/bin/python -m pytest -q tests/test_packaging.py
    status: passed
    head: f608f903f24b2d6bea5fd6911969c029214033ac
    base: 42f4d94feca4cef02c6e6e565f4ae0ee6d34fe89
    detail: 43 passed.
  - command: .venv/bin/python -m coga_edge.migrate_step_scripts
    status: passed
    head: f608f903f24b2d6bea5fd6911969c029214033ac
    base: 42f4d94feca4cef02c6e6e565f4ae0ee6d34fe89
    detail: Report-only dry run against origin/main lists 68 tickets; nothing pushed.
```

## Implementation notes

- Switching branch->main with a dirty ticket would refuse (main has newer
  ticket commits): save live ticket bytes, restore to HEAD, switch, write back.
- `enter` after switching to the branch must write main's ticket copy into the
  working tree (the branch holds the branch-point copy). Leaves ticket dirty on
  the branch; hence `run.py rebase`.

