---
slug: service-recurring-from-a-temp-control-worktree-ins
title: Service recurring from a temp control worktree instead of failing the repo
status: in_progress
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/architecture
- coga/cli
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 3 (implement)
---

## Description

When `coga recurring --all <path>` dispatches a repo whose checkout is not
sitting on the configured control branch, the child refuses before scanning and
the parent reports the whole repo as failed. A repo parked on a feature branch —
a workflow stopped at a human-owned step, an abandoned agent worktree — fails
every scheduled sweep until a human notices the cron output and runs
`git checkout` by hand.

Service that repo's **recipe-backed** templates from a temporary linked worktree
holding the control branch instead, and leave the operator's working tree and
current branch untouched. The temp worktree checks the control branch *out*
(it is free by definition — that is the trigger), so the run is an ordinary
control-branch run from a different directory: every existing sync, ledger, and
push path applies unmodified.

Do **not** implement this by moving the operator's checkout (stash → switch →
run → switch back → pop). That option was considered and rejected; the reasons
are recorded under `## Context` and the rejection is part of this ticket's
scope, not an open question.

## Acceptance Criteria

- An `--all` child whose checkout is off the control branch (feature branch or
  detached HEAD) and whose tree is dirty **services its recipe templates** and
  exits 0, instead of returning `git.STALE_CONTROL_EXIT_CODE`.
- The operator's checkout is byte-identical afterwards: same branch, same
  `HEAD`, same `git status --porcelain --untracked-files=all --ignored`, and
  `git stash list` unchanged. No stash entry is ever created.
- Period tasks, the template `ticket.md` cursors, and the repo-global
  `coga/log.md` `created|reused <task-ref> for <period>` ledger line all reach
  `<remote>/<control-branch>` exactly as they do from an ordinary on-control
  sweep. Re-running the sweep in the same period does **not** re-fire the
  template.
- Agent templates (no `recipe:`) are skipped in this mode regardless of TTY,
  and each is reported by name with a reason that says the run came from a
  temporary control worktree — not the misleading "an agent run requires a TTY".
- The temp worktree is removed on success, on a recipe's non-zero exit, on an
  exception, and on SIGINT/SIGTERM. A worktree stranded by SIGKILL is reaped by
  the next run before it creates its own.
- The temp worktree is never discoverable as a Coga repo by
  `discover_coga_repos` (it lives outside any plausible `--all` scan root).
- Two concurrent sweeps over the same repo cannot both service it: the second
  fails to acquire the control branch and reports that, rather than racing
  period state.
- When the temp worktree cannot be created (another worktree already holds the
  control branch, `git worktree add` fails), the run keeps today's loud refusal
  and `STALE_CONTROL_EXIT_CODE`, with a message that names both the blocker and
  the manual remedy.
- **Independently shippable:** the not-checked-out branch of
  `_sync_control_checkout_ahead` names the exact fix
  (`git -C <root> checkout <control-branch>`), the way the post-fetch branch
  already names its rebase command.
- The `--all` summary distinguishes repos serviced from a temp control worktree
  from ordinary sweeps.
- Bare `coga recurring`, `coga recurring launch <name>`, and
  `coga recurring --interactive` in a single repo behave exactly as they do
  today.
- New tests in `tests/test_recurring.py` cover each bullet above, using the
  real-git `git_repo` fixture (`tests/conftest.py:373`) so `git worktree add`
  and the control push run for real against the bare `origin`.
- `python -m pytest` passes; `coga validate --json` reports no new issues.

## Proposed Shape

### 1. Make the gate's failure distinguishable

`_sync_control_checkout_ahead` (`src/coga/recurring_runner.py:920`) currently
returns `tuple[bool, str]`, collapsing "not on the control branch" and "could
not integrate the control tip" into one falsy result. Replace the return with a
small frozen dataclass:

```python
@dataclass(frozen=True)
class _ControlCatchup:
    fresh: bool
    reason: str
    off_control_branch: bool  # True only for the pre-fetch early return
```

`off_control_branch` is set only on the early return that fires before
`_fetch_control_branch` — i.e. exactly the "branch 'x'" / "detached HEAD" case.
Two call sites update: `run_recurring_scan:590` and `run_recurring_named:884`.
While here, append the remedy to that early return's `reason`:
``Check that branch out — `git -C <root> checkout <control>` — then re-run.``

### 2. Service from a temp control worktree

In `run_recurring_scan`, when `require_fresh_control` is set, the catchup is not
fresh, `catchup.off_control_branch` is true, and `control_worktree` is **not**
already set, try the new path before returning `STALE_CONTROL_EXIT_CODE`:

```python
def _service_from_control_worktree(
    cfg: Config, *, force: bool, interactive: bool, agent_override: str | None
) -> tuple[int, None] | tuple[None, str]:
    """Run this repo's recipe templates from a temp worktree on the control
    branch. Returns (exit_code, None), or (None, why_unavailable)."""
```

Steps, in order:

1. `root = _git_toplevel(cfg.repo_root)`; run `git worktree prune` first so a
   registration stranded by a killed run (its directory already gone with
   `/tmp`) stops pinning the control branch.
2. Ensure a local control ref exists: if `git rev-parse --verify
   refs/heads/<control>` fails, `_fetch_control_branch(cfg, root)` and add the
   worktree with `-b <control> … <remote>/<control>`; otherwise add it plain.
3. `parent = Path(tempfile.mkdtemp(prefix=f"coga-recurring-{root.name}-"))`,
   checkout at `parent / "checkout"` (a fresh subpath — `git worktree add`
   refuses a pre-existing populated directory). The system temp dir is outside
   any plausible `--all` scan root, so `discover_coga_repos`
   (`src/coga/workspace_discovery.py:18`) can never pick it up.
4. `git -C <root> worktree add <checkout> <control>`. **This is the concurrency
   lock**: git refuses to check one branch out twice, so a second sweep — or an
   unrelated worktree already holding the control branch — fails here and the
   caller falls back to today's refusal, naming the holder from
   `git._worktree_holding_branch:4018`.
5. Seed the machine-local config: copy `<coga_os>/coga.local.toml` to the same
   relative path inside the checkout, `chmod 0600`. **Required** — the file is
   gitignored (`coga/.gitignore`), so a fresh worktree has no `user` and
   `load_config` raises before anything runs.
6. Dispatch the child through the existing spawner, generalized to take the
   extra flag: `_run_repo_recurring(<checkout>/<workspace-rel>, force=…,
   interactive=…, agent_override=…, control_worktree=True)`. It already builds
   `python -m coga.cli run recurring-scan --require-fresh-control …` with
   `cwd=coga_os.parent`, which is exactly right for the worktree copy.
7. `finally`: `git worktree remove --force <checkout>`,
   `shutil.rmtree(parent, ignore_errors=True)`, `git worktree prune`. Install a
   SIGTERM handler for the duration that raises, so a cron kill unwinds through
   the same `finally` (SIGINT already does via `KeyboardInterrupt`).

Print one banner before dispatch naming the temp path and the branch the
operator's checkout is actually on.

### 3. The inner run: `--control-worktree`

Add `--control-worktree` to `run_recurring_scan_recipe:728`'s argparse and
thread it to `run_recurring_scan(..., control_worktree: bool = False)`. It does
two things:

- **Recursion stop.** With it set, `run_recurring_scan` never enters
  `_service_from_control_worktree`; if the freshness gate still fails it returns
  `STALE_CONTROL_EXIT_CODE` as today.
- **Recipe-only.** The `scan_due` call (`recurring_runner.py:657`) passes
  `allow_interactive=_interactive_stdio_has_tty() and not control_worktree`.
  A throwaway worktree is the wrong place to spawn an agent REPL that composes
  prompts, edits files, and opens PRs, so agent templates are excluded whether
  or not a TTY exists.

The refusal text needs to stay honest. `create_template`
(`src/coga/recurring.py:386`, raises at :428 and :460) hardcodes "an agent run
requires a TTY…", which is false in an attended `--control-worktree` run. Give
`scan_due`/`create_template` an optional `agent_unavailable_reason: str | None`
(default `None` keeps today's message) and pass:

> serviced from a temporary control worktree because `<root>` is on `<branch>`;
> agent templates need that checkout on `<control>`.

Those land in `DueScan.errors` and are already printed and broadcast by
`_broadcast_scan:2164`, so each skipped template is named without new plumbing.

### 4. Why nothing in the sync layer changes

The temp worktree holds the control branch, so `_current_branch(root)` returns
`cfg.git_control_branch` inside it and every write takes its existing path:

- `_sync_recurring_create_paths:1139` → the `branch == cfg.git_control_branch`
  arm (`_sync_recurring_create_on_checked_out_control_branch:1502`).
- `git.sync_log:554` and `git.sync_task_state:382` → commit +
  `git._push_control_branch:3010`, whose fetch/rebase retry union-merges
  concurrent `log.md` appends. **This is the load-bearing reason for the
  control-branch shape**: on a detached HEAD `sync_log` refuses outright
  ("detached HEAD — log append not committed locally") and
  `_sync_recurring_create_paths` skips the local commit, so the serviced-period
  ledger would never reach control and every sweep would re-fire the period.
- `_run_recipe_task:748` spawns each recipe with `cwd=host_repo_root(cfg)` and
  `COGA_TASK_*` re-derived from the temp workspace, so recipes read and write
  the worktree's files and land them the ordinary way.

The local control ref advances in place (fast-forward from
`_sync_control_checkout_ahead`'s own catch-up, plus the run's commits) — the
same thing an on-control sweep does today, and it leaves the operator's next
`git checkout <control>` current rather than stale.

### 5. Reporting in the `--all` parent

`_configured_remote_identity:475` already computes `on_control_branch` per repo
for the duplicate-remote grouping. Keep that observation per workspace in
`run_recurring_all_repos:236`; a repo that was off-control at dispatch **and**
exited 0 was necessarily serviced through the temp worktree (the path is the
only way that combination can occur — an unavailable worktree still returns
`STALE_CONTROL_EXIT_CODE`). Print it per repo (`✓ <label> — serviced from a
temporary control worktree`) and as its own summary section beside the existing
unconfigured / not-owner / duplicate counts. No new exit-code protocol.

### 6. Order of work

1. `_ControlCatchup` + the remedy in the not-checked-out message (ships alone).
2. `--control-worktree` flag, recipe-only `scan_due`, honest refusal reason.
3. `_service_from_control_worktree` + `_run_repo_recurring` generalization.
4. `--all` summary section.
5. Tests.

## Out of Scope

- **The diverged-control case.** When the control branch *is* checked out but
  its local commits cannot rebase onto the fetched tip (the `fetched == True`
  arm of the same gate), the run keeps failing loud. Servicing that from a
  worktree at the remote tip would silently step around commits a human has to
  reconcile — the opposite of what that error is for. Its own ticket if wanted.
- **Agent templates.** They stay excluded from this path in every mode.
- **Single-repo runs.** Bare `coga recurring`, `coga recurring launch <name>`,
  and `--interactive` keep today's best-effort behavior off the control branch
  (they scan the working tree they are in). Only the `require_fresh_control`
  child changes.
- **A general-purpose temp-worktree helper** for other commands. Keep the
  helpers private to `recurring_runner.py` until a second consumer exists.
- **Changing `_duplicate_remote_checkouts`.** Its keeper preference (a checkout
  already on the control branch) still holds and still wins; this path only
  serves the case where no such checkout exists.
- **Global worktree GC.** Reaping is scoped to this run's own prefix plus a
  plain `git worktree prune` in the repo being serviced. Repo-wide branch and
  worktree hygiene remains `branch-sweep`'s job.

## Context

### The failure being fixed

`_sync_control_checkout_ahead` (`src/coga/recurring_runner.py:918`) returns
early when the checkout is not on the control branch:

```
configured control branch 'main' is not checked out (branch 'agent/…')
```

Because that path returns before `_fetch_control_branch`, `fetched` stays
`False`, so the "Resolve in that checkout — e.g. `git -C … rebase …`" hint is
never appended: the operator gets a diagnosis with no remedy. With
`require_fresh_control` set (every `--all` child, see
`_run_repo_recurring:558`), `run_recurring_scan` returns
`git.STALE_CONTROL_EXIT_CODE` (`recurring_runner.py:637-652`) and
`run_recurring_all_repos:236` counts the repo in its `N repo(s) failed` line.

The gate itself is correct — the scan reads working-tree templates and period
tasks and writes period state, so running it from a stale feature branch could
re-fire runs the control branch already serviced. The defect is that the only
recovery is a human noticing cron output and running `git checkout` by hand.
A repo left parked on a feature branch (e.g. a workflow stopped at a
human-owned step) fails every sweep until someone intervenes.

### Why the temp worktree is the right shape

An unattended sweep can only ever run recipe templates today:
`run_recurring_scan` calls
`scan_due(cfg, allow_interactive=_interactive_stdio_has_tty(), force=force)`
(`recurring_runner.py:657`), which reaches `create_template(...,
allow_agent=allow_interactive)` (`recurring.py:338`) and drops agent templates
when there is no TTY. Recipe tasks then run through `_run_recipe_task:748` as
plain `python -m coga.cli run <recipe>` subprocesses — deterministic, no REPL,
no agent CLI. So the set this ticket needs to serve is exactly the set that
needs no interactive checkout, and a linked worktree at the control tip is
enough to run it.

A linked worktree gives "be on the control branch, elsewhere" with no mutation
of the operator's checkout: a dirty tree is irrelevant, concurrent agent
sessions are unaffected, and a crash leaves nothing but a stale temp directory
to reap.

### Rejected: stash / switch / restore

Considered and rejected (2026-08-17). It is not merely riskier; it breaks in
this codebase specifically:

- **The window is the whole sweep, not a moment.** `recurring` launches as well
  as scans, sequentially, with a 15-minute default idle timeout per REPL
  (`COGA_REPL_IDLE_TIMEOUT`) plus `max_session`. Under `--all` the operator's
  work would sit in a stash, on a branch they did not choose, for as long as
  the sweep runs.
- **`stash pop` conflicts against the scan's own writes.** The scan writes
  `coga/tasks/**`, `coga/log.md`, and template blackboards
  (`last_serviced_period`) — precisely the paths a human is likely to have
  uncommitted edits in. An unattended job would leave conflict markers inside a
  ticket plus a half-applied stash: the silent-wrong-answer failure mode
  principle 6 forbids.
- **It races Coga's own sessions.** Git has no worktree-level lock, and
  `coga launch` already rechecks the active branch and sampled HEAD immediately
  before every fast-forward *because* a concurrent checkout switch is a known
  hazard. A scheduler performing that switch would attack an invariant the rest
  of the system defends.
- **Ordinary git sharp edges:** plain `git stash` skips untracked files (`-u`)
  and ignored ones (`-a`, which would sweep `node_modules` / `.venv` / `.env`);
  `git checkout <control>` fails outright when the control branch is already
  checked out in another linked worktree — the layout Coga recommends — so the
  auto-switch would break on exactly the well-configured repos; mid-rebase,
  mid-merge, and mid-bisect states cannot switch at all; submodules do not
  follow.
- **No crash safety.** A cron timeout, reboot, or SIGKILL between stash and pop
  strands the work in a stash entry the operator never created.

### Rejected: a detached worktree at the remote tip

The original sketch was `git worktree add --detach <tmp> <remote>/<control>`,
which never touches a local ref. Rejected at design time (2026-08-17, owner
confirmed) because Coga's git layer deliberately refuses to publish from a
detached HEAD, and the serviced-period ledger depends on that publication:

- `git.sync_log:554` prints "detached HEAD — log append not committed locally"
  and returns `False`.
- `_sync_recurring_create_paths:1139` skips the local commit (`if branch !=
  "HEAD"`), and the cross-branch overlay deliberately never carries
  `coga/log.md` (it is `merge=union`; the overlay replaces files wholesale).

So the period task would land on control while the
`created|reused <task-ref> for <period>` ledger line would not — and the ledger
is what stops the next sweep re-firing the period once Dream reaps the task.
Fixing that means adding an "authorized detached HEAD may publish to control"
mode to `sync_log` and `_sync_recurring_create_paths`, plus a separate
concurrency lock and a recursion marker. Checking the control branch out in the
temp worktree gets all of that for free, because git itself refuses to check one
branch out twice.

The accepted cost: the local control ref advances (a fast-forward in the normal
case; a rebase if it carries diverged local commits) — the same thing every
on-control sweep does today.

<!-- coga:blackboard -->

## Design notes (design step, 2026-08-17)

Evidence gathered while writing the spec, so `implement` does not re-derive it:

- `coga/coga.local.toml` is **gitignored** (`coga/.gitignore`, and the test
  fixture mirrors it at `tests/conftest.py:328`). Any fresh worktree therefore
  has no `user` and `load_config` raises before the scan starts. Seeding the
  copy is not a nicety — the feature does not run without it. `.coga/` and
  `.agent-skills/` are also absent but are not needed: the child is spawned as
  `sys.executable -m coga.cli` (not the vendored shim) and no registered recipe
  reads the merged skill view.
- `git.sync_log:554` refuses on detached HEAD; `_sync_recurring_create_paths`
  skips the local commit on detached HEAD (see the rejection section above).
  This is what forced the control-branch shape over `--detach`.
- `git._try_update_local_ref:3973` already handles "a worktree holds the
  branch" by fast-forwarding *through* that worktree, so nothing downstream is
  surprised by the temp worktree owning the control ref for the run's duration.
- `discover_coga_repos` (`src/coga/workspace_discovery.py:18`) walks any
  directory under the scan root, pruning only `_REPO_SCAN_SKIP_DIRS` and
  `_`-prefixed segments. A temp worktree inside a scan root would be picked up
  as another Coga repo by a concurrent `--all`; the system temp dir avoids that
  without a new prune rule.
- `tests/test_recurring.py::test_recurring_all_scan_refuses_detached_checkout`
  (~:2645) asserts the *old* outcome for a detached checkout. Under this design
  a detached checkout leaves the control branch free, so the temp worktree
  succeeds and that test must be rewritten to assert the new behavior. Same for
  any sibling asserting `STALE_CONTROL_EXIT_CODE` purely from being off-branch.

## Open Questions

For `review-design`:

1. **Parent summary derivation.** The `--all` summary infers "serviced from a
   temp control worktree" from its own pre-dispatch `on_control_branch`
   observation plus a zero exit, rather than a distinct success signal from the
   child. It cannot currently be wrong (an unavailable worktree still exits
   non-zero), but it is an inference. Accept, or add an explicit child→parent
   signal?
2. **`--control-worktree` visibility.** Internal dispatch flag only, or also
   documented in `coga/cli` as a debugging spelling an operator can run by
   hand? Documenting it means supporting it.
3. **Stranded-worktree reaping.** This run prunes before it adds. Should
   `branch-sweep` (which already runs `git worktree prune`) also remove
   leftover `coga-recurring-*` registrations, or is prune-on-start enough?
4. **Should the copied `coga.local.toml` be a copy or a symlink?** Spec says
   copy at 0600 (predictable, no dangling link if the sweep outlives an
   unmount). Worth a second opinion since it duplicates secret *references*
   (not values) into a temp path.
