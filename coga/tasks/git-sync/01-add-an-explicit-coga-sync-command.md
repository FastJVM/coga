---
title: Add an explicit coga sync command
status: canceled
owner: nicktoper
contexts:
- coga-dev/principles
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
agent: claude
---

## Description

First ticket of the `git-sync/` project. Add a new `coga sync` command
(it does not exist today) that implements the project's publication model.
Humans and agents both call it, and it must be safe to run repeatedly and
from any checkout.

`coga sync` commits the Coga state, fetches main, lands that state on main,
rebases the current branch onto main, and, if the branch was pushed before,
force-pushes it with `--force-with-lease`. Today's implicit publication (the
end-of-command sweep and per-command `sync_task_state`) **stays in place**
during this ticket. Ticket 02 removes it, so both paths must coexist safely
until then. Nothing calls `coga sync` automatically in this ticket.

Why: the implicit sweep (`git.sync_coga_state`) publishes whatever is dirty
whenever a sweeping command exits. That includes definition edits, which
breaks the fork/override workflow planned in
`v1/microkernel/12-make-packaged-behavior-discoverable-and-editable`. Its
eligibility, held-for-merge and plumbing-publish machinery also makes
`src/coga/git.py` (about 3.8k lines) a steady source of sync bugs. One
explicit, porcelain-shaped primitive lets 02 remove the implicit path and
03 cut `git.py` down.

Done means: a merged PR adding `coga sync`, with tests for control and
feature checkouts, and an updated `coga/sync` topic that describes it as the
publication primitive.

### Acceptance criteria

Command and placement
- [ ] `coga sync` is a built-in Typer command registered in
      `cli._LAZY_COMMANDS` as `"sync": ("coga.commands.sync", "sync", {})`.
      It takes no options or arguments, and `coga --help` lists it.
- [ ] `commands/sync.py` is a thin head. It loads config, calls
      `coga.sync.run_sync(cfg)` and maps the result to an exit code. All
      behavior lives in a new focused module, `src/coga/sync.py`.
- [ ] `sync` is **not** in `cli._SWEEPING_COMMANDS`. A test asserts that
      `cli._should_sweep_coga_state(["sync"])` is `False`.
- [ ] `coga-dev/microkernel` records the placement claim in "The kernel tier
      and its edges". The claim is the package-private transaction: sync holds
      `git.state_lock` across commit, land and rebase, and it coexists with
      `PUBLISHED_REF` provenance. `sync` is not added to "Open command
      placements".

Membership
- [ ] The paths sync commits and lands are exactly `git.coga_root_paths(cfg)`
      (Coga root plus contexts root), restricted to unignored files.
      Sync never commits or lands anything outside them.

Control checkout (HEAD is `[git].control_branch`)
- [ ] Dirty Coga state (modified, new, deleted) is committed on local main
      with subject `Sync coga state`. Then sync lands on `<remote>/<main>` a
      single commit with the same subject, parented on the freshly fetched
      remote tip. Local main ends at that tip plus any local non-state
      commits, rebased. Non-state commits are never pushed.
- [ ] Uncommitted changes outside the Coga roots survive the run.
      Content survives, but their staged/unstaged split is not guaranteed.

Feature checkout (HEAD is any other branch)
- [ ] Dirty Coga state is committed on the branch as `Sync coga state`.
      All Coga-root changes on the branch since its merge-base with
      `<remote>/<main>` land on main as one `Sync coga state` commit. This
      includes changes committed earlier by hand, by agents, or by this
      command. Knowledge files are included: sync does **not** apply the
      held-for-merge rule.
- [ ] The branch is then rebased onto the landed commit. Commits that touched
      only Coga roots drop out as empty. Mixed commits keep their non-state
      hunks. Afterwards `git diff --quiet <landed> HEAD -- <roots>` succeeds,
      so the branch carries no Coga-state diff against main.
- [ ] Code changes, committed or uncommitted, stay on the branch and are
      never pushed to main.
- [ ] Sync force-pushes with
      `--force-with-lease=refs/heads/<branch>:<old>` only when
      `refs/remotes/<remote>/<branch>` existed before the run, the rebase
      changed HEAD, and `<old>` (that remote-tracking oid) was an ancestor
      of the pre-rebase HEAD. If `<old>` is not an ancestor, sync does not
      push and reports that the remote branch has commits the local branch
      lacks. Sync never pushes a branch with no remote-tracking ref.
- [ ] Sync does not move the local `main` ref from a feature checkout. Launch
      checkout preparation already fast-forwards it.

Detached HEAD
- [ ] Sync commits and lands state the same way and rebases the detached
      HEAD. It pushes no branch.

Idempotence
- [ ] A second `coga sync` run right after a successful one creates no commit,
      pushes nothing, and exits 0. A test asserts that no commits or refs
      change on either side.
- [ ] If the remote tip already has this checkout's state, sync pushes no
      landing commit (empty result tree diff) and says so.

Conflicts and merging while landing
- [ ] Landing merges per path, three-way. The base for path `p` is
      `PUBLISHED_REF:p` when that ref records `p`, otherwise `merge-base:p`.
      The other two sides are ours (HEAD after the state commit) and theirs
      (the remote tip). If one side is unchanged from base, the other side
      wins. If both sides are equal, the result is that shared value. If both
      sides changed:
      - the log (`paths.log_path`) goes through `log_publication.reconcile`;
      - tickets go through `git.merge_ticket_bytes`;
      - paths with `merge=union` (`git check-attr merge`) go through
        `git._merge_union_bytes`;
      - other paths go through `git merge-file -p` three-way.
      Modify/delete and mode conflicts are conflicts.
- [ ] Any conflict aborts landing before anything is pushed. stderr lists
      each conflicted path, sync exits 1, and the `Sync coga state` commit
      stays on the current branch. Rerunning after the user reconciles the
      file, or after the other side changes, retries cleanly.
- [ ] A test covers concurrent `coga/log.md` appends from two clones. Both
      clones' events end up on main and no events are duplicated.

Push failure and retry
- [ ] A non-fast-forward rejection of the landing push triggers a refetch and
      a rebuild of the landing commit, up to 3 attempts in total. Only after
      that does sync exit 1.
- [ ] Any other fetch or push failure exits 1 immediately, with no retry.
      Examples are network or DNS errors, auth failures, a protected branch,
      and a rejecting hook. stderr says three things: the Git error
      (summarized by `git.summarize_git_failure`); that the Coga state is
      committed locally on `<branch>` as `<oid>` and nothing was lost; and
      that rerunning `coga sync` retries. Sync does not rebase the branch
      when landing failed.
- [ ] Until the next successful `coga sync`, the implicit path may still
      publish that local state commit. On control, the sweep's
      `_candidates` treats it as hand-committed state. On a feature
      checkout, it publishes routine task and log state only. A test shows
      that a following ordinary sweep neither errors nor duplicates content.

Rebase conflicts on the current branch
- [ ] When a rebase step stops with unmerged paths that are all under the
      Coga roots, sync resolves them to the onto side (main already holds the
      merged state). Use `git checkout --ours` or `git rm` for deletions, then
      `git add`. Sync continues with `GIT_EDITOR=true git rebase --continue`,
      or `git rebase --skip` when the resolution leaves the commit empty.
- [ ] If any unmerged path is outside the roots, sync runs
      `git rebase --abort` and exits 1. It reports that Coga state **was**
      published, that the branch was not rebased, and that the user should
      rebase by hand. Uncommitted changes are restored by the abort or
      autostash.
- [ ] When the rebase finishes but `--autostash` cannot reapply, sync exits 1.
      It names the stash entry Git kept and tells the user to run
      `git stash pop` after resolving.

Preconditions (exit 2, nothing changed)
- [ ] Sync refuses when a rebase, merge, cherry-pick, revert or bisect is in
      progress (`git._operation_in_progress`), when the checkout has no
      merge-base with the remote tip, or when the cwd is not a Git checkout.
- [ ] With `[git].enabled = false`, sync prints one line saying Git
      publication is disabled and exits 0. No commit is made.
- [ ] With Git enabled but no remote configured, local `main` is control.
      Sync lands with `git update-ref refs/heads/<main> <new> <old>`, a
      compare-and-swap, instead of pushing. It refuses with exit 1 when another
      worktree has local main checked out
      (`git.worktree_holding_branch`). On a control checkout, the state
      commit itself is the landing.

Output and exit contract
- [ ] stdout prints one line per stage outcome: commit, land, rebase,
      branch push. Each line names the short oid or says "nothing to do".
      Failures go to stderr with the `coga sync:` prefix and name the stage.
      Exit codes: 0 means every applicable stage completed; 1 means a stage
      failed and work is retained; 2 means refused before changing anything.

Locking and coexistence
- [ ] The whole run holds `git.state_lock(cfg)`. A concurrent
      `append_log` in the same checkout waits instead of interleaving.
- [ ] After a successful land, sync records the landed blobs in
      `PUBLISHED_REF` through `git._record_published`. It also clears those
      paths from `.coga/pending-publication.json` through `git._clear_pending`
      and `_save_pending`, so the implicit path treats them as published. A
      test runs a sweeping command (`coga slack` or `bump`) after
      `coga sync` and asserts it publishes nothing extra and is not refused.

Commits
- [ ] Both the branch-local commit and the landing commit use the subject
      `Sync coga state`. Sync makes the branch-local commit with
      `git commit --no-verify` and the landing commit with `commit-tree`, so
      neither runs hooks, which matches today's plumbing publication.
      `coga/recurring/scheduling/inactivity` and
      `recurring_activity` need no change.

Topics
- [ ] `coga/sync`
      (`src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`)
      is rewritten:
      - Its Git layer describes `coga sync` as the publication primitive.
      - It states that this deliberately reverses the old invariant that
        publication happens "without committing on a local branch, stashing,
        or rebasing".
      - It says implicit publication still runs until `git-sync/02` and that
        `coga sync` ignores held-for-merge.
      - It links a new owner leaf, `coga/sync/command` (`sync/command/SKILL.md`),
        which owns the user contract: stages, conflicts, retry and exit codes.
- [ ] `coga/cli` lists `sync` under "Tickets and state" with a link to
      `coga/sync`.
- [ ] `coga-dev/internals/state-publication` gains a short section on
      `coga.sync` that points to the user leaf, `coga-dev/codebase` lists
      `sync.py` and `commands/sync.py`, and `coga-dev/microkernel` changes as
      described above.
- [ ] The new leaf ships: add
      `src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/command/SKILL.md`
      to `tests/required_package_resources.txt`, and add `coga/sync/command`
      to `REQUIRED_BOOTSTRAP_CONTEXT_REFS` in `tests/test_packaging.py`
      beside `coga/sync`. `coga validate --json` stays clean.

Tests and verification
- [ ] A new `tests/test_sync.py` uses real local bare remotes and covers:
      - control checkout: dirty state with local code edits, code edits
        preserved;
      - feature checkout: dirty state, earlier hand-committed state, a mixed
        code-and-state commit, and an uncommitted code edit;
      - a previously pushed branch force-pushed with lease, plus a
        lease-mismatch refusal;
      - idempotence;
      - a state conflict, exit 1 with nothing pushed;
      - a non-fast-forward retry;
      - a protected main simulated by a `pre-receive` hook that rejects,
        exit 1 then retry success after the hook is removed;
      - a rebase conflict outside the roots, aborted;
      - a rebase conflict inside the roots, auto-resolved;
      - concurrent log appends;
      - detached HEAD;
      - `[git].enabled = false`;
      - coexistence with the sweep.
- [ ] `python -m pytest` passes, and the PR records receipts per
      `coga-dev/testing`.

### Proposed shape

1. **`src/coga/sync.py`** (new). Public API:
   `run_sync(cfg: Config) -> SyncResult`, where `SyncResult` is a dataclass
   with per-stage outcomes plus `exit_code`. Raise or return
   `SyncError(stage, message, retained)` for failures. The order of work,
   all under `git.state_lock(cfg)`:
   1. *Preflight*: `git.toplevel`, `cfg.git_enabled`,
      `git._operation_in_progress`, `git.symbolic_head`, and
      `git.remote_configured`.
   2. *Commit*: `git add -A -- <roots>`. If the index differs from HEAD
      under roots, run `git commit --no-verify -m "Sync coga state" --
      <roots>`. The pathspec form leaves staged non-root changes staged and
      uncommitted.
   3. *Fetch*: run `git fetch <remote> <main>`. It reuses
      `git._fetch_control`, which updates `refs/remotes/<remote>/<main>`.
      Call the fetched tip `T`.
   4. *Land*, done by `_build_landing(root, base, head, tip)`:
      - Take `base = merge-base(T, HEAD)`. Changed paths are the
        `git diff --name-only -z --no-renames base HEAD -- <roots>`.
      - Merge each path per the acceptance rule. `PUBLISHED_REF` overrides
        `base` per path.
      - Write the results into a scratch index seeded with `read-tree T`.
        `git._scratch_dir` and `git._scratch_index` already exist.
      - Run `write-tree`. If the tree equals `T^{tree}`, there is nothing to
        land.
      - Otherwise run `commit-tree -p T -m "Sync coga state"` and push
        `<commit>:refs/heads/<main>` without force.
      - On a non-fast-forward rejection, go back to step 3, up to 3 attempts.
        Match the rejection text under `LC_ALL=C`, as `git._MESSAGE_LOCALE`
        does elsewhere.
      - For the no-remote case, use `update-ref` CAS instead of the push.
   5. *Record*: `git._record_published` for the landed paths, then clear
      their pending expectations.
   6. *Rebase*: run
      `git rebase --autostash --empty=drop --no-update-refs <landed>`.
      Resolve root-only conflicts in a loop, as the acceptance criteria
      specify. Skip this step when HEAD already contains `<landed>` and HEAD
      has no root diff against it.
   7. *Branch push*: apply the lease rule from the acceptance criteria.
2. **`src/coga/commands/sync.py`** (new): a Typer function `sync()`.
   It loads config (`ConfigError` → exit 2), runs `run_sync`, echoes the
   stage lines and raises `typer.Exit(code)`.
3. **`src/coga/cli.py`**: one `_LAZY_COMMANDS` entry. Leave the sweep sets
   unchanged, since `sync` is not in the allowlist.
4. **Topics** as listed in the acceptance criteria. Update `coga/sync` and
   its new `command` leaf first, so the tests encode the documented
   contract.
5. **Tests**: `tests/test_sync.py`. Reuse the bare-remote fixture
   patterns from `tests/test_publish_state.py` (`_git`, `_onboarded_repo`)
   and `tests/test_checkouts.py`.

Keep `sync.py` independent of `git.publish`, `_publish_locked`,
`_candidates`, `_guard` and `sync_coga_state`. Ticket 03 deletes those, and
`sync.py` must survive it. Reuse only the small helpers that 03 will keep:
`run_git`/`_run`, `toplevel`, `symbolic_head`, `remote_configured`,
`_fetch_control`, `state_lock`, `_operation_in_progress`,
`worktree_holding_branch`, `summarize_git_failure`, the scratch-index
helpers, `merge_ticket_bytes`, `_merge_union_bytes`,
`log_publication.reconcile`, `coga_root_paths`, and the
`PUBLISHED_REF`/pending helpers needed only for coexistence.

### Out of scope

- Removing or converting any implicit publication path. The sweep,
  `sync_task_state`, `sync_log`, launch boundary syncs and the held-for-merge
  rule all stay (ticket 02).
- Having launch, megalaunch, recurring or the supervisor call `coga sync`,
  and changing the base prompt or step skills to tell agents to run it
  (ticket 02).
- Removing `coga run publish-state` or the `Ticket: …`/`Log: …` commit
  subjects. Revisiting inactivity classification (ticket 02).
- Deleting dead `git.py` code (ticket 03).
- Pushing a branch that has never been pushed, opening PRs, or publishing
  code in any other way.
- `--dry-run`, `--json`, a custom `--message`, and path-limited syncs.
- Cross-clone admission-claim atomicity for `launch_generation`. The owner
  rejected an exception for it.
- Related tickets: `fix-git-sync-failure` is already `canceled`;
  `hold-dirty-context-edits-on-feature-checkouts-unti` and
  `correct-state-publication-internals-for-pending-pu` are `done`. None
  needs action here. Ticket 02 reverses the held-for-merge decision recorded
  by the second one.

## Context

### Placement under the microkernel rule

Sync is a Typer command, not a `runner.RECIPES` entry or an alias. See
`docs/contexts/coga-dev/microkernel/SKILL.md`, "The microkernel rule".

- **Not an alias**: it has real logic.
- **Not a recipe**: `runner.run_reported` appends a `## Recipe Failure`
  section to the inherited task blackboard (`COGA_TASK_BLACKBOARD`) on a
  non-zero exit. For sync, that would dirty the very ticket it just failed to
  publish. `coga run` is also in `cli._SWEEPING_COMMANDS`, so a recipe would
  need a sweep exemption like `publish-state`. Sync is also the user-facing
  verb humans type, not a repository-independent automation contract.
- **Core under rule (b)**: sync's contract names a package-private
  transaction. It holds `git.state_lock`, the same lock `logfile.append_log`
  and `git.write_ticket` take, across commit, land and rebase. During
  coexistence it also maintains `git.PUBLISHED_REF` provenance and
  `.coga/pending-publication.json`. An edge script using only the CLI and
  files cannot hold that lock.
- **Core under rule (a)**: ticket 02 adds the second real consumer of
  `sync.run_sync` (the launch supervisor, megalaunch and recurring runner at
  session end). By the end of the project, sync is the main consumer of
  what remains in `git.py`.

### Existing machinery (cite symbols; ranges drift)

- `src/coga/git.py`:
  - `sync_coga_state()` is the sweep. `cli._sweep_coga_state` calls it
    after commands in `cli._SWEEPING_COMMANDS`.
  - `publish()` → `_publish_locked()` is the plumbing publish. It never
    commits on HEAD and holds knowledge on a feature checkout through
    `_publishes_from_feature()`.
  - `coga_root_paths()` is the single membership definition, which sync
    reuses.
  - `PUBLISHED_REF = "refs/worktree/coga/published"` stores, per worktree,
    the blobs last published. `_write_published()` and `_record_published()`
    write it, and `_candidates()`/`_provenance()` read it.
  - `_PENDING_FILE` with `_load_pending`, `_save_pending` and
    `_clear_pending` holds prepared lifecycle expectations.
  - `merge_ticket_bytes()` is the frontmatter-aware three-way ticket merge.
  - `_merge_union_bytes()` is the union merge.
  - `RETRY_WITHOUT_SWEEP_EXIT_CODE` (75) does not apply to `sync`, which is
    not swept anyway.
- `src/coga/log_publication.py`: `reconcile(cfg, root, rev, source, *,
  source_base=..., head=...)` merges the audit log.
  `coga/.gitattributes` marks `/log.md -merge`, so a plain three-way merge
  of the log is wrong. Spool-merge internals
  (`docs/contexts/coga-dev/internals/spool-merge/SKILL.md`, "How `publish`
  lands the audit log") own the rule. `**/retires.md` is `merge=union`.
- `src/coga/publish_state.py`: `run_publish_state_recipe` is the strict
  `coga run publish-state` recipe. It stays untouched here.
- `src/coga/cli.py`: `_LAZY_COMMANDS` registers commands lazily.
  `_should_sweep_coga_state()` is an allowlist, so a new command is unswept
  by default.
- `src/coga/launch.py` calls `git.sync_coga_state` with messages
  `"Sync coga state before launch"` and `"... before checkout return"`. These
  coexist untouched.
- Commit-subject classification: `src/coga/recurring_activity.py`'s prefix
  regex and `coga/recurring/scheduling/inactivity`. A `Sync coga state`
  prefix counts as machine activity, so sync keeps it and no rule changes.
- `coga/coga.toml`'s `[git]` comment block ("Git sync") documents that a
  push that cannot reach a protected control branch must not block a
  transition. That remains true of lifecycle commands. `coga sync` itself
  fails loud with exit 1 and keeps the local commit, and rerunning is the
  retry. Do not edit `coga.toml`; ticket 02 rewrites that comment.
- This repo sets `[layout] contexts = "docs/contexts"`, so the contexts
  root is outside `coga/` and `coga_root_paths` returns two roots. Tests
  should cover the relocated layout; `tests/test_layout_contexts.py` has
  fixtures.

### Known interactions

- PR-preparation receipts (`coga/pr-publication/preparation`, `## PR`
  head/base OIDs) go stale when sync rebases a branch. That is expected:
  re-preparing is the remedy. Nothing in 01 runs sync automatically.
- `git rebase --empty=drop` is explicit because the default differs across
  Git versions and interactive mode. Linux dev Git is 2.43. Use no Git
  feature newer than what the existing code already requires; per-path
  merging avoids `git merge-tree --write-tree`.

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
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
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

## Design notes (design step, 2026-11-17)

Spec is under `## Description` (acceptance criteria, proposed shape, out of
scope) and `## Context` (placement, cited machinery). Key decisions and why:

- **Typer command, not a recipe/alias.** `runner.run_reported` writes a
  `## Recipe Failure` section into the inherited ticket blackboard on
  failure, which would re-dirty the state sync just failed to publish; and
  `coga run` is swept. Core claim: the `git.state_lock` transaction (rule b)
  plus 02's supervisor as second consumer (rule a).
- **Own small implementation in `src/coga/sync.py`, not a wrapper over
  `git.publish`.** Wrapping publish would keep `_publish_locked`/`_candidates`
  alive and fight 03. Reuse only helpers 03 keeps (merge helpers, log
  reconcile, lock, fetch, scratch index).
- **Commit on the branch first, then land a separate commit on main, then
  rebase.** Committing first lets the rebase drop pure-state commits as
  empty instead of autostash popping state onto main's copy. Landing is a
  per-path three-way merge onto the fetched tip (commit-tree + plain push),
  not a push of the branch commit, so code never reaches main.
- **Per-path merge, not `git merge-tree --write-tree`.** The log is
  `-merge` and needs `log_publication.reconcile`; tickets get
  `merge_ticket_bytes`; avoids a Git ≥2.38 dependency.
- **Coexistence via `PUBLISHED_REF` as per-path merge base.** The implicit
  plumbing path publishes working bytes the branch never committed; without
  that base, a later sync would see a false overlap conflict on every ticket
  the sweep already landed. Sync also writes `PUBLISHED_REF` and clears
  pending expectations so the sweep sees its landed paths as published.
- **Lease = the stale remote-tracking oid, not a fresh fetch of the branch**,
  so a teammate's push to the branch makes the lease fail instead of being
  overwritten.
- **Subject stays `Sync coga state`** → inactivity rules unchanged in 01.

## Open Questions

1. **Committed knowledge on a feature branch goes to main pre-review.** Per
   the owner decision, sync lands *every* Coga-root change on the branch,
   including contexts. In this repo the contexts root is `docs/contexts`, and
   AGENTS.md says to update the owning topic "in the same PR". After a sync,
   a PR's topic edits are already on main and vanish from the PR diff
   (rebase drops them), so reviewers never see them in review. Confirm this
   is intended, or say whether sync should carry only the task directory,
   the log and recurring runtime state from *committed* branch changes
   (dirty knowledge still landing). The spec currently follows the decision
   literally.
2. **For 02 (flag, not blocking 01):** once lifecycle commands stop making
   `Ticket: <slug> — …` commits, nearly every control commit becomes
   `Sync coga state`, which `recurring_activity` classifies as machine
   activity, so every repo would look inactive. 02 needs a new human-activity
   signal or subject scheme.
3. **Hooks:** the spec bypasses `pre-commit` (`--no-verify`, commit-tree) for
   parity with today's plumbing publication. Confirm, or should a repo's
   commit hooks gate state commits?
4. **Never-pushed branches:** the spec never pushes a branch without a
   remote-tracking ref. Confirm that sync should not start publishing code.
5. **`[git].enabled = false` exits 0** (nothing to publish to), mirroring
   `coga run publish-state`. Confirm, or should an explicit `coga sync`
   fail loud (exit 1)?

## Evaluator review

**Needs revision before implementation.** The ticket has the required body
sections, the frozen workflow routes evaluation and owner review through
control, and the shared-lock transaction supports the built-in placement
under `coga-dev/microkernel`. The bare-remote fixtures in
`tests/test_publish_state.py` and relocated layout in
`tests/test_layout_contexts.py` fit the requested verification.

### Must fix

1. **The proposed rebase can succeed while reintroducing state.** Reproduced
   on Git 2.43 using Proposed shape step 6. Start with state A. On feature,
   commit A → B alongside code, then revert the state to A. Independently
   land B on main. Step 4 sees no net feature state change and lands nothing.
   Both picks replay without a conflict, leaving state A on feature and B on
   main. Define how every replayed commit excludes root changes, including
   clean picks, and how sync enforces the final root-tree equality before
   pushing. Add this case to the mixed-commit test. Also make the rebase's
   treatment of merge commits explicit. Plain rebase can drop code added
   only in a merge resolution.

2. **Keep the audit log within its existing transaction and retention rules.**
   The generic unchanged-side shortcuts in “Conflicts and merging while
   landing” can publish a one-sided truncation without invoking
   `log_publication.reconcile`. Its `_reconcile` compares the source with
   pre-edit HEAD and source-base events and rejects unreceipted truncation.
   The spool-merge topic's “How publish lands the audit log” explicitly
   forbids using a `PUBLISHED_REF` blob as the log source base. It also
   describes a pending `log_transaction` receipt that fences ordinary
   publication. Specify the dedicated log path, inputs, and receipt check
   before mutation. Test one-sided truncation and a pending receipt as well
   as two-clone append.

3. **Resolve preflight ordering and missing control.** “Preconditions” promises
   exit 2 without changes for unrelated histories, but Proposed shape
   commits before fetching and checking ancestry. Specify which changes a
   preflight fetch may make to tracking refs and check ancestry before
   staging or committing. `git._fetch_control` suppresses a missing remote
   branch and can leave a stale tracking ref in place. Require a verified
   tip and define behavior for a deleted remote control branch, an unborn
   HEAD, and missing local control in a remote-less repo. Reconcile the
   diagnostic contract with a fetch failure before any local state commit.

4. **Define what provenance proves and how recording failures recover.**
   `git._write_published` stores blobs at mode 100644 and removes entries
   for deletions. It cannot distinguish a published deletion from absent
   provenance or supply a historical file mode for a three-way merge.
   Also, selecting only merge-base → HEAD paths misses a deliberate return
   to merge-base bytes after an implicit sweep published different working
   bytes. Specify how candidates and bases distinguish that edit from a
   checkout merely behind main. `git._record_published` catches failures and
   only emits a note. State when pending expectations may be cleared and how
   a rerun repairs failed bookkeeping after main has advanced.

5. **Give branch push its own partial-success contract.** The push failure
   criteria promise that sync has not rebased and rerunning retries. After a
   lease rejection or transport failure at the branch-push stage, main may
   already hold the state and HEAD is already rebased. A rerun may have no
   HEAD change, or the old tracking tip may no longer be its ancestor. Specify
   the diagnostic, exit code, and safe recovery for this stage separately
   from a failed landing. Assert both refs and retained code in the
   lease-mismatch test.

6. **Resolve the review boundary in the ticket body.** The stated scope
   publishes relocated `docs/contexts` edits before review. That removes
   those edits from the feature diff, even when AGENTS.md requires updating
   the owning topic in the same PR as its behavior change. The blackboard
   already flags this decision. Record the owner's disposition and how a
   maintainer should preserve same-PR review when that is required. Scope
   the blanket language in `coga/state-publication` and the “Invariants”
   section of `coga-dev/internals/state-publication` to implicit publication
   where needed, and link the explicit command contract from those surfaces.

### Optional

- Specify whether the branch-local commit should bypass every hook or just
  verification hooks. `git commit --no-verify` still runs hooks such as
  `prepare-commit-msg` and `post-commit`, so the proposed invocation needs
  a different mechanism if the existing “neither runs hooks” criterion is
  retained.
- Exercise a remote-less linked worktree and a non-default control branch
  alongside the relocated-context case. These cover the CAS and branch
  lookup contracts independently of the usual origin/main fixture.
