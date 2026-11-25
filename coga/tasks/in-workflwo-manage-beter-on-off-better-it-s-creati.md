---
title: Add a Git mode field to workflow files
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: open-branch
    skills: []
    assignee: agent
    requires: branch
    run: git/open-branch
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
contexts:
- coga-dev/principles
step: 8 (review)
agent: claude
---

## Description

Today Git is handled by workflow steps. `git/open-branch` switches the
checkout to the ticket's branch and records it under `## Dev`, and the
launch ends wherever the last step left the checkout. After a launch, the
user is left on the ticket branch. If they return to the starting branch
and launch the ticket again, Coga reads that branch's stale copy of the
ticket, or finds none, instead of the live copy on the ticket branch.
Nothing commits or publishes the work at launch exit, so state left between
steps can stay only in a working tree.

Add a top-level `git:` field to workflow definitions that selects the Git
mode for the whole launch. `main` (the default, also used when the field
is omitted) does no Git work in launch, which is today's behavior.
`ticket-branch` runs packaged edge scripts around every launch of the
ticket. At start, they find or create the ticket's branch, switch to it and
let launch read the live ticket there. At exit, they commit every change,
push and switch back to the starting branch. The kernel stays Git-agnostic.
It reads the frozen mode, maps it to a hook script ref and runs that
script, the same way it runs a step's `run:` script. All Git commands live
in the edge script.

Owner decisions taken in the design session (2026-11-24):
- Use generic launch hooks with Git at the edge, not Git logic in
  `launch.py`. This amends the in-force "Plain Git, orthogonal to the
  kernel" direction for this one launch-boundary publication.
- An omitted field means `main`, and `main` is a no-op. Existing workflows
  and frozen snapshots keep today's behavior.
- The exit commit includes every non-ignored change on the ticket branch.
- If the ticket exists only on the ticket branch and not on the starting
  branch, warn the user, because that is likely a bug.
- If Git fails at exit, stop on the ticket branch with local state intact,
  name the failed operation and exit non-zero. Never retry or recover
  automatically.

Owner decisions taken at `review-design` (2026-11-25):
- A ticket missing from the starting branch is a Git problem, not a launch
  problem. Launch resolves the ticket from the current checkout as today
  and fails with the ordinary "not found" when it is absent. The edge
  warning (ticket only on its branch) is how the user learns to commit it
  on the starting branch. No cross-branch search, no special recovery.
- Every ambiguous or inconsistent Git state stops the launch with a clear
  message and the user fixes it by hand. Enter never backfills or guesses.
- Enter refuses to switch branches with uncommitted changes and points the
  user to `coga sync` (the `add-the-coga-sync-git-helper` ticket), or
  commit/stash. Without a switch (launching from the ticket branch itself)
  uncommitted changes are allowed and the exit commit picks them up.
- Owner-held steps are worked through an assist (`coga launch <ref>
  --agent`), which goes through launch and gets both hooks. No Git check is
  added to `coga bump`/`coga mark`.
- All four shipped code workflows, including `code/agent-merge`, declare
  `git: ticket-branch`.

### Acceptance criteria

- [ ] `Workflow.load` accepts an optional top-level `git:` whose value is
      `main` or `ticket-branch`, and rejects any other value with a
      `WorkflowError` that names the path and the valid modes.
- [ ] `Workflow.freeze()` writes `git: ticket-branch` into the snapshot
      only when the mode is not `main`. Snapshots of workflows that omit
      the field, or declare `main`, stay byte-identical to today's.
- [ ] A frozen snapshot without `git:` behaves as `main`. `coga validate`
      reports a frozen `git:` value outside the registry as a `bad-shape`
      error.
- [ ] In `main` mode, `coga launch` runs no Git command it does not run
      today. The existing launch tests pass unchanged.
- [ ] In `ticket-branch` mode, the first launch from `main` creates the
      ticket branch from `HEAD`, switches to it and records `branch:`,
      `base:` and `remote:` under `## Dev` before the first step runs.
- [ ] A second `coga launch` from `main` switches to the same branch,
      including one with an older random-suffix name, and runs the step
      recorded in the branch copy of the ticket, not the stale `main` copy.
      A test commits a `main` copy at an earlier step and asserts that the
      launched step comes from the branch.
- [ ] Launch reads the mode from the copy it resolved. If, after enter, the
      live copy on the ticket branch selects a different mode, launch bails
      before classification with a message naming both modes; the exit
      hook still runs.
- [ ] At launch exit, on every path after enter started (normal end,
      owner handoff, agent failure, timeout, `LaunchBail`, Ctrl-C, including
      Ctrl-C during a script step or between `git switch` and the end of
      enter), the exit hook runs `git add -A`. It commits if anything is staged, pushes
      the branch to its recorded remote with upstream set and switches back
      to the starting branch. A clean tree still pushes any unpushed
      commits.
- [ ] If any exit Git operation fails, or `HEAD` is no longer on the ticket
      branch, the checkout stays where it is. Launch prints the failed
      operation and exits non-zero. If the launch was already failing,
      whether by a returned non-zero `LaunchResult` or an exception such as
      `SystemExit(130)`, its original exit code is kept and both failures
      are reported. Tests pair an exit-hook failure with an agent failure,
      a timeout and Ctrl-C.
- [ ] Exit takes `start`, `branch`, `remote` and `slug` from the enter
      state file, not from the ticket, so it still commits and pushes when
      the agent deleted the ticket. The commit message is
      `<slug>: launch handoff at <step>`, `<slug>: launch handoff (<status>)`
      when no step is current, or `<slug>: launch handoff (ticket removed)`.
- [ ] Enter and exit print a warning when the ticket path is not tracked in
      the starting branch's `HEAD`: "ticket exists only on its branch;
      commit it on `<start>` so later launches can find it". The warning
      does not fail the launch.
- [ ] Enter refuses with a clear message, before any lifecycle write, when
      `HEAD` is detached; when more than one distinct branch matches the
      ticket; when a branch's local and remote-tracking tips have diverged;
      when the recorded `branch:` no longer exists; when the `## Dev`
      record has `branch:` without `base:` or `remote:`; or when it would
      switch branches with uncommitted changes. The dirty-tree message
      names the files and says to run `coga sync` or commit/stash first.
      Launching from the ticket branch itself (no switch) with uncommitted
      changes is allowed.
- [ ] `--prompt-report` runs no hook. Megalaunch skips a `ticket-branch`
      ticket with an explicit reason. `coga validate` reports a recurring
      template whose workflow declares `git: ticket-branch` as `bad-shape`,
      and the recurring runner refuses such a template before creating,
      reactivating or preparing a period, leaving the period and its
      serviced record untouched. Delegated periods use the fixed one-step
      workflow and are always `main`.
- [ ] One end-to-end scenario: `design` launch from `main`, owner
      `review-design` through an assist, then `open-branch`/`implement`,
      all resuming from `main` on the same ticket branch.
- [ ] `git/open-branch` and `git/push-and-open-pr` still work in both
      modes. In `ticket-branch` mode, `open-branch` reuses the recorded
      branch and adds no fields. The `requires: branch`/`pr` gates and the
      owner `review-design`/`review` gates are unchanged.
- [ ] The shipped `code/with-review`, `code/with-self-review`,
      `code/design-then-implement` and `code/agent-merge` declare
      `git: ticket-branch`. Topics are updated in
      the same PR: `coga/workflows`, `coga/git`, `coga/launch`,
      `coga-dev/current-direction` and `coga-dev/microkernel`.
- [ ] Tests run against a local bare remote. They cover a first launch, a
      resume from `main`, an exit with dirty and with clean trees, a push
      failure (remote removed) and the ticket-only-on-branch warning. The
      Linux tier of `coga-dev/testing` passes and receipts are recorded on
      the blackboard.

### Proposed shape

1. **Workflow field and freeze** (`src/coga/workflow.py`).
   - Add a module registry `GIT_MODES: dict[str, str | None] =
     {"main": None, "ticket-branch": "git/ticket-branch"}`. Each mode
     maps to its hook skill ref, or `None` for no hook. Future modes add
     an entry here and a packaged skill.
   - Add `git: str = "main"` to `Workflow`. Parse it in `Workflow.load`
     next to `name`/`steps` and validate it against `GIT_MODES`.
   - `Workflow.freeze()` emits `"git"` after `"name"` only when it is not
     `"main"`.
   - Add a helper `git_mode(workflow: dict | str | None, cfg) -> str`
     that reads a frozen mapping's `git` (default `"main"`). For a draft's
     string reference it loads the definition, matching how
     `launch_script.script_entry_point()` freezes a draft reference to
     find its first step.
2. **Validation** (`src/coga/validate.py`). Next to the frozen-step
   checks that `_check_step_run` belongs to, check a frozen `git:` value
   against `GIT_MODES` and emit `bad-shape` (error). Also check that the
   mode's hook script resolves through `launch_script.resolve_step_script()`.
   Report a recurring template whose workflow declares `git: ticket-branch`
   as `bad-shape`.
3. **Launch hooks** (`src/coga/launch.py`, `_launch()`).
   - Inside the existing `ExitStack`, after `run_state.launch_tmp_scope`
     is entered and before `invocation._classify_target`, resolve the mode
     with `git_mode(read_ticket(ref).workflow, cfg)`. Skip this for
     `prompt_report`, `BootstrapRef` and delegated periods (those have
     already returned from `_prepare_target`).
   - If the mode maps to a hook ref, resolve its `run.py` with
     `resolve_step_script()` once and copy that skill directory into the
     launch `$TMPDIR`, so exit runs the same code even if a local override
     changes or disappears on the branch switch.
   - Enter the exit guard *before* running enter: a context manager (not
     `stack.callback`, which sees no exception state) whose `__exit__`
     observes both an unwinding exception and the returned `LaunchResult`.
     It runs `run.py exit` only if the enter state file exists, reports an
     exit-hook failure, and keeps the first non-zero code (an existing
     `SystemExit`/`LaunchBail` code wins; otherwise the hook's failure
     makes the launch non-zero). It is entered after the tmp scope, so it
     runs while `$TMPDIR` still exists.
   - Run `run.py enter` as a subprocess. Give it the ticket env
     (`COGA_TASK_TICKET`, `COGA_TASK_SLUG`) and the launch tmp env
     (`run_state.apply_tmp_env`), but no secrets. A non-zero exit bails
     before classification, so no activation, log or lifecycle write
     happens; the guard still runs exit if enter got as far as writing
     its state.
   - After enter, re-read the mode from the switched checkout's copy. If
     it differs from the mode that selected the hook, bail with both
     values.
   - `_classify_target` then reads the ticket from the switched checkout,
     which is the live copy. No other launch phase changes. Enter runs
     before classification, so a launch that classification later refuses
     (terminal ticket, agent preflight failure) still commits and pushes
     the checkout's changes at exit; document this in `coga/launch` and
     `coga/git` and cover it with a regression test.
   - Put the Git-free hook runner in a small helper in `launch_script.py`
     (for example `run_launch_hook(cfg, ref, script, phase, tmp_scope) ->
     int`). Megalaunch can then refuse `ticket-branch` tickets through
     `git_mode()` in `_candidate_result`/`_launch_chain` in
     `src/coga_edge/megalaunch.py`. The recurring runner checks the
     template's workflow mode in `run_recurring_scan` and
     `run_recurring_named` before `create_named`, reactivation or period
     preparation.
4. **Edge script** `src/coga/resources/templates/coga/bootstrap/skills/git/ticket-branch/`
   with `SKILL.md` and `run.py`, importing only shared core infra
   (`coga.blackboard.read_dev_fields`/`set_dev_fields`,
   `coga.taskfile.read_blackboard`/`replace_blackboard`).
   - `enter`:
     1. Read the starting branch (`git branch --show-current`) and refuse
        a detached `HEAD`.
     2. Find the ticket branch. If the current copy's `## Dev` has
        `branch:`, use it; refuse if that branch exists neither locally
        nor as a remote-tracking ref, or if `base:`/`remote:` is missing.
        Otherwise check local and remote-tracking refs named
        `coga/<slug-part>` or `coga/<slug-part>-<6 hex>`, and accept a
        candidate only if `git show <ref>:<ticket relpath>` has a `## Dev
        branch:` equal to that branch. Ticket paths are relative to the
        Git top level, as in `git/push-and-open-pr/run.py`. Use the same
        `<slug-part>` rule as `fresh_branch_name()` in
        `git/open-branch/run.py`. Candidates are grouped by branch name;
        the local ref is used when present.
     3. Refuse if more than one branch name matches, or if a branch's
        local and remote-tracking tips have diverged (neither is an
        ancestor of the other).
     4. Write `{"start", "branch", "remote", "slug"}` to
        `$TMPDIR/git-ticket-branch.json` *before* any switch, so an
        interrupt after the switch still lets exit return.
     5. If the target branch differs from `start`: refuse uncommitted
        changes, naming the files (reuse
        `coga_edge.git_workflow.changed_paths`) and pointing to `coga sync`
        or commit/stash. Then switch, creating a local tracking branch when
        only the remote exists. If start is already the ticket branch,
        do not switch and allow uncommitted changes.
     6. If none is found, create `coga/<slug-part>` from `HEAD` (falling
        back to the suffixed `fresh_branch_name()` when that name is
        taken) and record `branch`/`base`/`remote` like `open-branch`.
        `base` is the starting branch, and `remote` is the base's upstream
        remote or `origin`. The same dirty-tree refusal applies.
     7. Warn if the ticket path is absent from `<start>`'s `HEAD`
        (`git cat-file -e <start>:<path>`).
     Move the slug and branch-name helpers out of `git/open-branch/run.py`
     into `src/coga_edge/git_workflow.py` and import them from both
     scripts. Do not copy them.
   - `exit`:
     1. Read the state file and refuse if `HEAD` is not on the recorded
        ticket branch.
     2. Run `git add -A`, then commit if `git diff --cached --quiet` fails.
        Message: `<slug>: launch handoff at <step>`, or
        `(<status>)` / `(ticket removed)` as in the acceptance criteria.
     3. Run `git push -u <remote> <branch>`.
     4. Run `git switch <start>` unless `start == branch`.
     5. Warn if the ticket is absent on `<start>`.
     Stop at the first failure with `ticket-branch: <operation> failed`
     and exit non-zero.
5. **Shipped workflows.** Add `git: ticket-branch` to the frontmatter of
   `bootstrap/workflows/code/with-review.md`, `with-self-review.md`,
   `design-then-implement.md` and `agent-merge.md`. In `agent-merge`, the
   exit after `code/merge-pr` pushes any late audit commit to the merged
   branch and returns to a `main` that needs a pull (`coga sync`); those
   late lines stay on the branch, as late audit lines do today. Keep their `open-branch` steps. Those steps
   are no-ops on an already recorded branch and keep the `requires: branch`
   gate for old snapshots. Update the authoring starter `workflows/_template.md`
   to show the optional field.
6. **Docs, in the same PR.**
   - `coga/workflows` "Definition format" and "Frozen snapshot, live
     content": the field, its default, freezing and the omitted-means-main
     rule.
   - `coga/git`: a new "Ticket-branch mode" section. Update "Checkout
     policy" and "Branch to merge" (the exit commit and push replace the
     note that a launch audit line can land after the PR push in this
     mode). Owner-held steps are worked through an assist
     (`coga launch <ref> --agent`), which gets both hooks. A ticket
     missing from the starting branch is fixed with Git (commit it there,
     or `git switch` to the ticket branch and launch from it).
   - `coga/launch` "The step chain": enter before classification and exit
     after the chain, on every path.
   - `coga-dev/current-direction`: amend "Plain Git" to allow the
     launch-boundary hook.
   - `coga-dev/microkernel` "Git workflow scripts": add the hook.
   - The ticket template guide's frozen example
     (`bootstrap/tickets` template): show the optional `git:`.
   - Add `git/ticket-branch` to `tests/required_package_resources.txt`.

### Out of scope

- Any Git logic in `src/coga/` (launch, bump, mark). `coga bump` and
  `coga mark` run from the starting branch are not redirected to the
  ticket branch and get no warning; owner steps go through an assist.
- Finding a ticket that is absent from the current checkout. Launch keeps
  today's "not found"; the edge warning is the prevention.
- Running `ticket-branch` tickets under megalaunch or recurring. They are
  refused there, and supporting them is a follow-up.
- Implementing `coga sync` (the `add-the-coga-sync-git-helper` ticket; the
  refusal message only names it) and pulling or fast-forwarding the
  starting branch at exit.
- Fetching before enter. A branch that exists only on a remote is found
  only through refs already fetched.
- Removing `git/open-branch` steps from shipped workflows, rewriting
  existing frozen snapshots or deleting merged branches.
- Modes beyond `main` and `ticket-branch`.

## Context

- `src/coga/workflow.py`: `Workflow.load()` parses frontmatter `name`,
  `description` and `steps`. `Workflow.freeze()` produces the mapping that
  `create.py` (`fm["workflow"] = wf.freeze()`) and `mark.py` (activation
  of a draft reference) write into the ticket. `validate.py` also calls
  `workflow.freeze()["steps"]`. The new key must therefore be added in
  `freeze()`, or it never reaches a ticket.
- `src/coga/launch_script.py`: `resolve_step_script(cfg, run)` resolves a
  skill ref's `run.py` local-first, falling back to bootstrap. Reuse it
  for the hook ref. `script_entry_point()` shows how a draft's string
  `workflow` is loaded and frozen to read its first step. Mirror that in
  `git_mode()`. `run_script_phase()` builds the step env with
  `build_launch_env` (secrets). The hook must not get secrets.
- `src/coga/launch.py`: `_launch()` runs `_prepare_target`, then, inside
  an `ExitStack` that first enters `run_state.launch_tmp_scope`, runs
  `_classify_target` → `_run_initial_script` → `_prepare_agent` →
  `_supervise_steps`. `_classify_target` is the first read of the ticket
  (`self.ref.ticket_path.read_bytes()`) that drives activation and
  routing, so enter must complete before it. `_supervise_steps` re-reads
  the ticket each iteration through `self._read`, so the switched checkout
  is used for the whole chain.
- `src/coga_edge/megalaunch.py`: `_launch_chain()` runs its own chain
  through `spawn_agent_session`/`run_script_phase`, not `_launch()`, so it
  needs an explicit refusal. `recurring_runner` calls
  `launch_with_before_spawn` and `launch_recurring_period`, which reach
  `_launch()` in a disposable clone. Refuse there instead of switching
  branches.
- `src/coga/resources/templates/coga/bootstrap/skills/git/open-branch/run.py`:
  `fresh_branch_name()` builds `coga/<slug-part>-<hex6>`, and `main()`
  records `branch`/`base`/`remote` through `set_dev_fields` and refuses
  live/derived disagreement. The new enter logic reuses this naming and
  recording rule.
- `src/coga/step_gate.py`: the `branch`/`pr` gates read `## Dev` through
  `read_dev_fields`. Enter writes the same record, so the gates are
  unaffected.
- `git/push-and-open-pr` commits the ticket and log path-limited, pushes
  and bumps. In `ticket-branch` mode, the exit hook then commits whatever
  remains, such as a later launch audit line, and pushes again.
- `coga-dev/current-direction` "Plain Git, orthogonal to the kernel
  (2026-11-19)" and `v1/03-use-git-like-everyone-...` set the stance this
  design amends: launch had no Git knowledge and no automatic publication.
  Keep the kernel side to "read mode, run mapped script".
- Tests to extend: `tests/test_launch.py` (hook ordering, exit on every
  path, `main` no-op), `tests/test_launch_script.py` (hook runner),
  `tests/test_validate.py` (frozen `git:`), `tests/test_megalaunch.py`
  (refusal), `tests/test_open_pr.py`/new `tests/test_ticket_branch.py`
  (bare-remote Git scenarios), and `tests/test_packaging.py` and
  `tests/required_package_resources.txt` (new packaged skill).

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

<!-- coga:blackboard -->
## Dev

pr: https://github.com/FastJVM/coga/pull/1291
reviewed: 9c9d892eff4bbdb32b65ba43bbb56167efb56699
branch: coga/in-workflwo-manage-beter-on-off-better-it-s-crea-2155af
base: main
remote: origin


## PR

```yaml
title: Add a launch Git mode field to workflows
author: claude
author_evidence: Claude Opus 5.5 produced the implementation in the attended implement session on
  2026-11-25 (d6f122035). Codex authored the separate peer-review correction commit (9c9d892ef).
head: 9c9d892eff4bbdb32b65ba43bbb56167efb56699
base: 7c78e19203a3a20eff9202ae625ba3a7c6f0aaeb
depth: deep
rationale: The change affects launch control flow and automatically commits and pushes all non-ignored
  work in the four shipped code workflows.
implementation: The frozen mode selects a packaged launch hook. Enter finds or creates the ticket
  branch and launch reads the same ticket there. Exit publishes the handoff and returns to the starting
  branch. Review fixes include every fetched ref in discovered-branch divergence checks, complete
  a new branch's record after an interrupt during enter, and keep the earlier exit status if the exit
  hook itself is interrupted or cannot start.
deviations: The owner approved one shared recurring preflight in create_template. The hook owns its
  state file and treats missing state as a no-op. The state also carries base for warnings when launched
  from the ticket branch. The frozen-field example lives in coga/workflows because the bootstrap ticket
  guide has no frozen example. The review uses the existing merge base. The newer fetched origin/main
  commit abc35abd0 adds only ticket state and overlaps an untracked local ticket.
limitations: Native Windows and macOS suites are deferred to release. Enter uses already fetched refs.
  A stale local branch behind the remote can fail its push, leaving the operator on the ticket branch
  for manual recovery.
files:
  docs/contexts/coga-dev/current-direction/SKILL.md: Records the approved launch-boundary amendment.
  docs/contexts/coga-dev/microkernel/SKILL.md: Identifies the kernel dispatch and the edge ownership
    of Git commands.
  src/coga/launch.py: Wraps the chain in a hook guard and preserves ticket identity and the original
    launch status.
  src/coga/launch_script.py: Copies and runs the same resolved hook for both phases.
  src/coga/recurring.py: Refuses the unsupported Git mode before recurring period changes.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/git/SKILL.md: Defines branch discovery,
    interrupted enter and exit publication.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: Documents launch hook
    ordering and failure handling.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: Documents the workflow
    field and freeze compatibility.
  src/coga/resources/templates/coga/bootstrap/skills/git/open-branch/run.py: Uses the shared branch-name
    helper.
  src/coga/resources/templates/coga/bootstrap/skills/git/ticket-branch/SKILL.md: Describes the packaged
    launch hook.
  src/coga/resources/templates/coga/bootstrap/skills/git/ticket-branch/run.py: Implements branch selection,
    checkout, publication and return.
  src/coga/resources/templates/coga/bootstrap/workflows/code/agent-merge.md: Enables ticket-branch
    mode for the agent merge workflow.
  src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md: Enables ticket-branch
    mode for the design workflow.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md: Enables ticket-branch
    mode for peer-reviewed work.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-self-review.md: Enables ticket-branch
    mode for self-reviewed work.
  src/coga/resources/templates/coga/workflows/_template.md: Shows the optional Git mode declaration.
  src/coga/validate.py: Checks frozen modes and hook resolution and reports unsupported recurring
    templates.
  src/coga/workflow.py: Parses, freezes and resolves the Git mode.
  src/coga_edge/git_workflow.py: Shares ticket branch naming across both Git scripts.
  src/coga_edge/megalaunch.py: Reports an explicit skip for ticket-branch workflows.
  tests/required_package_resources.txt: Requires the packaged hook and skill.
  tests/test_packaging.py: Checks the hook's canonical package path.
  tests/test_ticket_branch.py: Exercises local bare-remote launches, failure paths and runner admission.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 9c9d892eff4bbdb32b65ba43bbb56167efb56699
  base: 7c78e19203a3a20eff9202ae625ba3a7c6f0aaeb
  detail: Codex reviewed the complete diff, traced launch and alternate runner entry points, and reproduced
    two handoff failures with local bare remotes. This session was independent of Claude's original
    implementation. Codex wrote and verified its own follow-up corrections. A process-group SIGINT
    during git switch returned 130, published the Git record and restored main. A script-mode PR launch
    with stub gh published the PR pointer and final audit line, then returned to main.
checks:
- command: PYTHONPATH=$PWD/src TERM=dumb .venv/bin/python -m pytest -p no:randomly --basetemp /tmp/coga-peer-full-yapvl2ls/fixtures
  status: passed
  head: 9c9d892eff4bbdb32b65ba43bbb56167efb56699
  base: 7c78e19203a3a20eff9202ae625ba3a7c6f0aaeb
  detail: Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.12.12. 3233 passed, 29 skipped,
    0 failed in 195.70s. Inherited COGA_* and temporary-directory overrides were cleared.
- command: PYTHONPATH=$PWD/src TERM=dumb "$scratch/venv/bin/python" -m pytest -p no:randomly tests/test_ticket_branch.py
    --basetemp "$scratch/fixtures"
  status: passed
  head: 9c9d892eff4bbdb32b65ba43bbb56167efb56699
  base: 7c78e19203a3a20eff9202ae625ba3a7c6f0aaeb
  detail: Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.11.15. 37 passed, 0 skipped,
    0 failed in 16.04s. A disposable system-temp venv installed .[test]. Inherited COGA_* and temporary-directory
    overrides were cleared.
- command: PYTHONPATH=$PWD/src TERM=dumb .venv/bin/python -m coga.cli validate --json
  status: passed
  head: 9c9d892eff4bbdb32b65ba43bbb56167efb56699
  base: 7c78e19203a3a20eff9202ae625ba3a7c6f0aaeb
  detail: Pop!_OS 24.04 LTS, Python 3.12.12. Exit 0 with 97 valid tickets, 84 warnings and no errors.
    Inherited COGA_* variables were cleared.
- command: git diff --check 7c78e19203a3a20eff9202ae625ba3a7c6f0aaeb..9c9d892eff4bbdb32b65ba43bbb56167efb56699
  status: passed
  head: 9c9d892eff4bbdb32b65ba43bbb56167efb56699
  base: 7c78e19203a3a20eff9202ae625ba3a7c6f0aaeb
  detail: Exit 0 with no whitespace errors.
- command: Native Windows and macOS full suites
  status: not-run
  detail: Deferred to release under coga-dev/testing.
```

## Implement handoff (2026-11-25)

- Implementation committed at d6f122035 on the ticket branch; not pushed
  (push-and-open-pr publishes). Peer review should read
  `launch._LaunchHookGuard.__exit__` (code preservation) and
  `git/ticket-branch/run.py` enter candidate logic first.
- Test-run note: inside a Coga launch the inherited `COGA_*` env and
  `TMPDIR` under the repo break unrelated tests; run pytest with `COGA_*`
  unset and `--basetemp` under the system temp dir.
- README/principles not edited: "Helpers for those tools are workflow
  steps" still reads true (the hook is declared by the workflow and lives
  at the edge), but the owner may want the principles wording revisited.

## Open Questions

Resolved at `review-design` (2026-11-25, owner, attended assist):
1. `code/agent-merge` declares `git: ticket-branch` too: one branch per
   ticket in every case, easier to track.
2. No Git warning in `coga bump`/`coga mark`; owner steps go through an
   assist, which gets the hooks.
3. Exit commit message `<slug>: launch handoff at <step>` with
   `(<status>)` / `(ticket removed)` fallbacks — proposed by the assist;
   owner may still revise.

## Review-design dispositions (2026-11-25)

Evaluator must-fix findings, all resolved in `## Description`:
1. Ticket lookup/mode: missing ticket on the starting branch is a Git
   problem; launch keeps "not found"; the edge warning prevents it. Mode
   mismatch between copies bails after enter, exit still runs.
2. Result/interrupt: exit guard is a context manager entered before enter,
   keeps the first non-zero code; enter writes its state file before
   switching.
3. Candidates: refuse every ambiguity (multiple names, diverged tips,
   missing recorded branch, incomplete `## Dev`); no backfill. Exit reads
   its inputs from the state file.
4. Recurring: `validate` rejects `ticket-branch` in recurring templates;
   runner refuses before any period change. Delegated periods are `main`.
5. Dirty tree: refuse only when switching, pointing to `coga sync`; no
   switch = allowed. Owner gates via assist. `add-the-coga-sync-git-helper`
   ticket updated with the on-`main` use case.
Optional recommendations: both accepted (preflight publishing documented
and tested; hook skill copied to `$TMPDIR` at enter; helpers moved to
`coga_edge/git_workflow.py`).

## Design notes

- 2026-11-24 design session (attended, owner nicktoper): chose generic
  hooks with edge Git, omitted field = `main` = no-op, exit commits
  everything (`git add -A`), a warning (not a failure) when the ticket
  exists only on its branch, and fail loud on Git errors at exit. These
  decisions are recorded under `## Description`.
- Branch discovery does not depend on the starting branch's copy having
  `## Dev`. It accepts `coga/<slug-part>[-hex6]` refs whose own ticket
  copy records that branch, so existing random-suffix branches are found
  too.

## Evaluator review

**Verdict.** Resolve the launch and handoff contracts below before
implementation. The specification sections compose correctly, and the
frozen workflow field and fixed dispatch to Git scripts at the edge fit
the proposed scope.

### Must resolve before implementation

1. **Define how launch finds the ticket and selects its mode.**
   `src/coga/launch.py::_LaunchInvocation._prepare_target` calls
   `resolve_target` and reads the current ticket before the hook point.
   `src/coga/tasks.py::resolve_task` searches only the current checkout.
   In a disposable Git repo, an untracked draft resolved before the first
   switch, then disappeared from `main` after it was committed on its
   branch. The next resolution failed before any hook could warn or
   discover the branch. Choose whether to require a committed starting
   copy for resume and document the manual recovery, or specify how to
   find a missing ticket before normal resolution. Also specify what
   happens when the starting copy selects `ticket-branch` but the live
   snapshot omits it, or when a stale draft reference resolves to a
   different mode. The current proposal selects using one copy and routes
   using the other while promising old snapshots retain their behavior.

2. **Preserve the launch result and define the interrupt boundary.**
   `ExitStack.callback` receives no exception state. A disposable Python
   probe confirmed that raising from the callback replaces an unwinding
   `SystemExit(130)`. In `src/coga/launch.py`, `_launch_error_boundary`
   translates exit exceptions after cleanup, `_prepare_agent` installs
   signal handlers after the initial script path, and some paths return a
   nonzero `LaunchResult`. Specify cleanup that observes both returned
   results and exceptions and preserves the first nonzero code. Test an
   exit-hook failure paired with an agent failure, timeout and Ctrl-C,
   including interruption during a script step. Specify how Ctrl-C between
   `git switch` and writing the enter state is handled so a changed
   checkout has a clear recovery path.

3. **Define candidate identity, precedence and exit inputs.**
   After a successful push, one logical branch normally has both a local
   ref and a remote-tracking ref. Specify deduplication, which ref wins
   when the tips differ, and how a stale or missing recorded branch and
   competing remote-only matches are handled. Compare ticket paths
   relative to the Git top level, as `git/push-and-open-pr/run.py::run`
   does. Discovery currently accepts a ticket with only `branch:`, yet
   exit needs `remote:` even when an owner handoff bypasses `open-branch`.
   Define whether enter backfills or refuses incomplete Git records and
   when it captures the validated remote. `_supervise_steps` treats an
   agent-deleted ticket as a clean terminal path. Specify the exit commit
   label fallback and preserve the inputs needed to push in that case.

4. **Place recurring refusal before period changes.**
   `src/coga/recurring_runner.py::run_recurring_scan` can reactivate or
   prepare a period before `_launch_created`, and `run_recurring_named`
   calls `create_named` first. A delegated period's workflow lives on the
   carrier, while `_run_delegated_task` passes its bootstrap target to
   `launch_with_before_spawn`. A check at the proposed hook point misses
   that carrier. Define where both repo-scoped templates and existing
   periods are refused, including manual launches of a delegated carrier,
   and whether a skip leaves the period and its serviced record untouched.

5. **Specify the owner-to-agent handoff and same-branch dirt rule.**
   The acceptance criterion refuses dirt when switching to an existing
   branch, while proposed enter step 3 says to refuse dirt for any existing
   branch. The shipped `code/design-then-implement` workflow hands off at
   `review-design`, and `src/coga/bump.py::advance_step` writes the ticket
   and log in the current checkout. An owner who switches to the ticket
   branch, edits and bumps leaves an expected dirty tree. State whether
   they can launch there immediately or must commit first, and document
   the steps for resuming from `main`. Verify design through owner review
   and the subsequent `open-branch`/`implement` handoff as one scenario.

### Optional recommendations

- Make preflight behavior explicit in `coga/launch` and `coga/git`. The
  proposed placement allows a newly created branch to carry and publish
  existing checkout changes even when classification subsequently refuses
  a terminal ticket or an agent preflight fails. A regression test would
  record the intended interaction with the approved `git add -A` policy.
- Specify whether exit uses the same executable as enter if a local hook
  override changes or disappears on branch switch.
  `src/coga/launch_script.py::resolve_step_script` prefers local paths.
  Reuse `src/coga_edge/git_workflow.py::changed_paths` for dirty-path
  diagnostics and consider placing the shared branch naming helpers there.

## Superseded designs

### 2027-03-22 — Restore the starting branch after `open-branch`

Superseded by: a workflow-level choice of direct work on `main` or managed
ticket-branch work, including commit and push at handoff in branch mode.

Reason: the owner wants each workflow to declare where it runs and what
happens to its changes at launch exit. The earlier draft scoped the design
to returning from the existing `open-branch` flow. Both approaches need
the next launch or owner handoff to recover the live ticket state.
