---
title: no weird state in personal dir
status: in_progress
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
step: 8 (review)
agent: claude
---

## Description

Agents and the scripts they write keep run state outside the repo when they
need somewhere unversioned to put it: `~/.local/state/<tool>`, `$XDG_STATE_HOME`,
`/tmp/...`, `~/.codex/...`, or a sibling directory such as
`~/Code/<repo>-validation`. That state is invisible, unshared and unbacked, and
outlives the repo that made it. Nobody remembers where it went, so it is never
cleaned up: the owner has about 100 GB of temporaries that were never deleted,
on a machine whose disk (and `/tmp`) is deliberately small. Coga must own this.
A ticket or script that needs unversioned state gets a Coga-managed place inside
the repo.

**Reading is unrestricted.** Agents may read and inspect anything outside the
repo without permission. The writing rule keeps durable launch state in the
repo and requires cleanup of disposable scratch used elsewhere.

### Requirements

- **One managed place.** Coga provides a git-ignored, repo-local directory for
  unversioned state (keys, run records, traces, evidence, caches), created and
  ignored by `coga init`, beside today's `.coga/`. Design picks the exact path
  and its layout. It has at least a durable area and a `tmp/` area.
- **Handed to every executor.** Launch exposes the directory to agents and
  script phases through an environment variable in the existing `COGA_*`
  family. It also points `TMPDIR`, `TMP` and `TEMP` at the managed `tmp/` area,
  so `mktemp`, Python `tempfile` and most tools land there automatically. The
  base prompt explains how to use the managed directories.
- **The rule, stated once.** Use the managed tmp directory for ordinary
  scratch. When a tool needs a dedicated disposable directory outside the
  checkout, including under system temp, delete it when the work ends,
  including on failure. Other writes outside the repo require the owner's
  explicit grant in the session, recorded on the blackboard. The agent CLI
  manages its own session files (`~/.claude`, `~/.codex`).
- **Coga's own files keep the system temp.** Every nested `coga` process
  (`bump`, `launch`, reviewers, megalaunch) inherits the redirected `TMPDIR`.
  So launch keeps the original value (for example as `COGA_SYSTEM_TMPDIR`), and
  Coga's own temp users keep resolving to the system temp: `oscompat.lock_dir`
  per-user locks, `compose.write_prompt_file`, the `repl_supervisor` `coga-done-*`
  sentinels and the `skill_manager` temp dirs. Otherwise the locks would stop
  excluding each other across checkouts, and live files would be purged.
- **Temporaries are purged, everything else is kept.** A launch empties only
  the `tmp/` area it created, when it ends, including on failure. A nested
  launch never purges its parent's `tmp/`. A `tmp/` left behind by SIGKILL or a
  crash is swept by a later launch or by `coga validate`; the design picks
  which. The durable area (evidence, keys, run records) is never deleted
  automatically.
- **Visible.** `coga validate` reports the managed directory's size and
  contents, per ticket if the design adopts a per-ticket layout (the design
  states attribution either way). State is never silently lost or forgotten.
  `coga status` is out of scope.

Done means: after `coga init`, a launched agent and a `ticket.py` script phase
both see the variable and a repo-local `TMPDIR`. A temp file they create lands
in the managed `tmp/` area and is gone after the launch, while a file they put
in the durable area survives and shows up with its size in
`coga validate` (`coga status` is out of scope, see below). The base prompt
states the rule, and tests cover it.

### Design decisions

- **Location: inside the existing `.coga/`, not a new top-level directory.**
  The managed tree is `<coga root>/.coga/`, where `<coga root>` is
  `cfg.repo_root` (`coga/` in the nested layout, the checkout root in the root
  layout), which is where `.coga/` already lives (`recurring-runs/`,
  `dream-scans/`, `recurring-clone/`, `megalaunch-selection.json`). Reasons:
  every repo that has ever run `coga init` already ignores `.coga/`. Both
  managed ignore blocks list it unanchored, so pre-existing repos need no
  ignore change and no first-use hazard. The ticket's worry about durable
  evidence sitting beside disposable `[launch].worktree` checkouts no longer
  applies: no `[launch].worktree` key exists in `config.py` today, and only
  a stale comment in this repo's root `.gitignore` mentions it. The path stays
  short, which helps with `sun_path`. pytest's default `norecursedirs` skips
  dot-directories, so generated test files under it are never collected.
  What we give up: `.coga/` mixes Coga's own machine state with agent state.
  Separate subdirectories keep them apart.
- **Layout.**
  ```
  <coga root>/.coga/
    data/<id_slug>/      durable, per ticket  (COGA_TASK_DATA_DIR)
    data/_shared/        durable, cross-ticket (keys reused by several tickets)
    tmp/<token>/         one per launch       (TMPDIR, TMP, TEMP)
    tmp/<token>.lock     liveness lock held by that launch
    recurring-runs/ ...  existing Coga state, untouched
  ```
  `<id_slug>` is the target's `ref.id_slug` verbatim (`v1/foo` gives
  `data/v1/foo/`, a bootstrap target gives `data/bootstrap/<name>/`).
  `<token>` is 8 lowercase hex characters (`secrets.token_hex(4)`), short on
  purpose for socket paths.
- **Attribution: per ticket.** Durable state is attributed by directory, so
  `validate` can say which ticket owns how many bytes, and flag state whose
  ticket is `done`, `canceled` or gone. `data/_shared/` is reported as
  `(shared)`. Any other top-level entry under `data/` is `(unattributed)`.
- **Which checkout.** Each process uses its own `cfg.repo_root`, the same rule
  `.coga/` and `recurring_clone.clone_state_dir()` follow today. A nested
  launch in another checkout uses that checkout's `.coga/`. The variables
  live in `TASK_ENV_KEYS`, so `apply_task_env` re-derives them and nothing is
  inherited. (Durable data in a linked worktree dies with the worktree. See
  Open Questions.)
- **Sweep owner: launch sweeps, validate reports and `--fix` sweeps.** A
  launch, when it opens its tmp scope, removes every sibling `tmp/<token>/`
  whose lock is not held. `coga validate` stays read-only by default. It
  reports orphans as `orphan-tmp` warnings, and `coga validate --fix` removes
  them through `apply_safe_fixes`, which already owns deterministic repairs
  that leave task state alone.
- **Long paths warn, they don't fall back.** If the absolute `tmp/<token>`
  path is longer than 64 bytes, launch prints one stderr warning naming the
  path, its length, and the ~108-byte `sun_path` limit. It still uses the
  path. Silently falling back to `/tmp` would break the rule.

#### Evaluator resolutions (owner-adopted 2026-11-21, supersede the above where they differ)

1. **Every executor.** Megalaunch's `_launch_until_stop` opens one scope
   per child chain and passes it to `run_script_phase` and the agent spawn.
   `recurring_clone.run_clone_template` opens one scope per run; clone
   scripts get `COGA_DATA_DIR` and the tmp variables but no
   `COGA_TASK_DATA_DIR` (they still have no task identity). Parser-only
   bootstrap help is exempt (it clears `TASK_ENV_KEYS`).
2. **Read-only dispatch and `--prompt-report`.** Read-only gets a tmp scope
   (creating `.coga/tmp/` is its one permitted effect) but no data variables,
   never creates `data/`, and never sweeps. `--prompt-report` creates nothing.
3. **Exclusive deletion.** The owner and the sweeper delete while holding the
   lock, then retire the lock file (POSIX unlinks while held; Windows closes,
   then unlinks). A sweeper re-checks the lock path's inode after locking.
   Lock without directory is an orphan; a lockless directory is an orphan
   after 60 s. `find_orphans` (validate) uses the same predicate, opens only
   existing lock files, and creates nothing.
4. **Attribution.** Two roots: `data/tasks/<id_slug>/` and
   `data/bootstrap/<name>/`, so task `bootstrap/status` and the stateless
   `bootstrap/status` never collide. Each owned dir holds a `.coga-owner`
   record (`task <id>` / `bootstrap <id>`); the size walk stops at nested
   owners, so `foo` and `foo/bar` never double-count. A record whose ref no
   longer resolves, or is `done`/`canceled`, is `stale-state`; files under no
   record are `(unattributed)`.
5. **Worktrees (Open Question 1).** `data/` resolves to the primary
   checkout by reading the worktree's `.git` file and `commondir` (no `git`
   subprocess); `tmp/` stays per checkout. This also keeps Retro's worktree
   under a purged tmp from holding durable data.
6. **Scoped repair.** Only repo-wide `validate --fix` sweeps orphans;
   `--task` neither reports nor sweeps them. An empty orphan still warns.
   A failed removal stays an `orphan-tmp` warning carrying the error.
   Dream's `validate-drift` classifies both kinds as human-needed and never
   commits the machine-local `orphan-tmp` fix.

Open Questions 2–4 kept the recommended answers: warn only, on every launch
including command aliases (owner reconfirmed during implement); keep
`data/_shared/`; purge, warn and leave the rest for the sweep.

### Acceptance criteria

- [ ] New shared module `src/coga/run_state.py` owns the layout, the tmp
      scope, the sweep and the size walk. `launch.py`, `launch_script.py`,
      `validate.py` and `commands/init.py` import it, which gives it the ≥2
      consumers the microkernel rule requires.
- [ ] `coga init` creates `<coga root>/.coga/data/` and `<coga root>/.coga/tmp/`
      (idempotent). The comments in both managed ignore blocks
      (`commands/update.py` `_HOST_GITIGNORE_BODY` and the packaged
      `templates/coga/.gitignore`) describe `.coga/` as machine-local state
      including `data/` (durable agent state) and `tmp/` (purged per launch).
      The ignore *entries* do not change.
- [ ] Every `_launch` invocation (attended, recurring period, delegated)
      opens exactly one tmp scope after `cfg` is known, and closes it in a
      `finally`. While it is open, the env handed to agent sessions **and**
      `ticket.py` script phases has:
      - `TMPDIR`, `TMP`, `TEMP` = `<coga root>/.coga/tmp/<token>` (absolute)
      - `COGA_SYSTEM_TMPDIR` = the inherited value if already set, otherwise
        the launching process's `tempfile.gettempdir()` computed before
        any override
      - `COGA_DATA_DIR` = `<coga root>/.coga/data` and `COGA_TASK_DATA_DIR` =
        `<coga root>/.coga/data/<id_slug>`, both in `TASK_ENV_KEYS` and built
        by `build_task_env`. The task data dir exists before the first phase
        runs.
- [ ] Guided `coga ticket` interviews also get one tmp scope and a durable
      directory for the selected target, including `bootstrap/ticket` when no
      target is given.
- [ ] The `launch(..., read_only=True)` script path and `recurring_clone`'s
      `ticket.py` runs get the same scope and variables.
- [ ] When the scope closes, normally, on exception, on `LaunchBail` and on
      `KeyboardInterrupt`, the launch removes its own `tmp/<token>/` and
      `tmp/<token>.lock`, and nothing else. If the removal is incomplete (a
      daemon still holds a file, or a permission error), it prints one stderr
      warning with the path and the error and leaves the remainder for the
      sweep. It never fails the launch over this.
- [ ] A nested `coga launch` (megalaunch child, recurring sweep, a reviewer
      that a human launched from inside a session) creates its own sibling
      token. It never removes the parent's: the parent's lock is held.
- [ ] The sweep removes a `tmp/<token>/` only when it can take
      `tmp/<token>.lock` without blocking, or when the lock file is missing
      and the dir's mtime is older than 60 seconds. That grace covers the
      window between creating the lock and creating the directory. Locking
      reuses `oscompat.lock_fd`, so POSIX and Windows behave alike, and a
      lock dies with a SIGKILLed owner.
- [ ] Coga's own temp users resolve to the system temp through a new
      `oscompat.system_tmpdir()`, which returns `COGA_SYSTEM_TMPDIR` if set,
      else `tempfile.gettempdir()`. Callers: `oscompat.lock_dir`,
      `compose.write_prompt_file` (its default `dest_dir`),
      `repl_supervisor` and `repl_supervisor_nt` `coga-done-*` sentinels,
      the three `skill_manager` `TemporaryDirectory` calls, the Windows
      placeholder in `launch.agent_command_refusal` (whose width must match
      the real prompt path), and `coga_edge/skill_update_pr.py`'s
      `NamedTemporaryFile`. A test proves that with
      `TMPDIR=<managed tmp>` and `COGA_SYSTEM_TMPDIR=<sys>` set, each one
      lands under `<sys>`.
- [ ] `coga validate` (text and `--json`) reports managed state:
      - JSON gains a top-level `"state"` object:
        `{"root": str, "total_bytes": int, "entries": [{"owner": "<id_slug>|(shared)|(unattributed)|(tmp)", "path": str, "bytes": int, "files": int, "kind": "data"|"tmp-live"|"tmp-orphan"}]}`.
        Empty directories are omitted. Existing keys are unchanged.
      - Text prints one `State: <root> <human size>` line, then one line per
        entry, before the issues. "All good" still prints when there are no
        issues.
      - Warnings: `orphan-tmp` (an unlocked `tmp/<token>/`, fixable by
        `--fix`), and `stale-state`, which names the owner and the size for
        a `data/<id_slug>/` whose ticket is `done`, `canceled`, or no longer
        resolves. `stale-state` is never auto-fixed.
      - `validate --task <slug>` reports only that ticket's data entry.
- [ ] The base prompt `src/coga/resources/prompt.md` gains a short
      `## Unversioned state` section. It names `$COGA_TASK_DATA_DIR`, then
      `$COGA_DATA_DIR/_shared/` for cross-ticket state, then `$TMPDIR` for
      disposable files. It permits unrestricted reading and allows dedicated
      disposable work directories outside the checkout when needed, with
      cleanup on success or failure. It names the other restricted targets
      (`~/.local`, `$XDG_*`, `~/.<tool>`, `/tmp`, sibling directories,
      external storage), explains the owner grant recorded on the
      blackboard, and leaves agent session files to their CLI.
- [ ] Tests (see Proposed shape) cover: env present for an agent session and
      a script phase; a temp file created via `tempfile` in a script phase
      lands under `tmp/<token>/` and is gone after the launch; a file in
      `$COGA_TASK_DATA_DIR` survives and appears in `validate --json`
      `state`; purge on failure (a script exiting non-zero, and a raised
      exception); a nested scope leaves the parent's tmp intact; the sweep
      removes an unlocked orphan and spares a locked one; `validate --fix`
      removes an orphan; `system_tmpdir()` routing; `coga init` creates both
      dirs.
- [ ] Docs updated in the same PR: `coga/init` (the dirs and why `.coga/`),
      `coga/launch` (a new "Run state" section that owns the tmp scope,
      purge and sweep contract), `coga/script-tickets` (`COGA_TASK_*`
      contract list gains `COGA_TASK_DATA_DIR` and `COGA_DATA_DIR`, and
      mentions TMPDIR), `coga/sandboxes` (the repo-local TMPDIR is in the
      checkout, which `workspace-write` already allows), `AGENTS.md` and
      `coga-dev/packaging` (`.coga/` now also holds `data/` and `tmp/`).
      This repo's root `.gitignore` drops the stale `[launch].worktree`
      comment.
- [ ] Manual receipt on the blackboard: one real attended Claude Code launch
      and one Codex launch (`--no-daemon`, `workspace-write`) where the agent
      runs `echo $TMPDIR; mktemp; python -c 'import tempfile;print(tempfile.mkdtemp())'`
      and the CLI itself keeps working. Both paths must be under
      `.coga/tmp/<token>/`, and both must be gone after exit.

### Proposed shape

1. **`src/coga/run_state.py`** (new, about 150 lines):
   - Constants: `DATA_DIR_ENV = "COGA_DATA_DIR"`,
     `TASK_DATA_DIR_ENV = "COGA_TASK_DATA_DIR"`,
     `SYSTEM_TMPDIR_ENV = "COGA_SYSTEM_TMPDIR"`, `TMP_ENV_NAMES = ("TMPDIR", "TMP", "TEMP")`,
     `SHARED = "_shared"`, `SOCKET_WARN_BYTES = 64`, `ORPHAN_GRACE_SECONDS = 60`.
   - `state_root(cfg) -> Path` (`cfg.repo_root / ".coga"`), `data_root(cfg)`,
     `tmp_root(cfg)`, `task_data_dir(cfg, ref)`.
   - `ensure_layout(cfg) -> None`, used by init and the scope.
   - `@contextmanager launch_tmp_scope(cfg) -> Iterator[TmpScope]`: sweep
     orphans, create and lock `<token>.lock`, mkdir `<token>/`, warn if
     long, yield `TmpScope(path, env_overrides: dict[str, str])`, and in
     `finally` release the lock and `shutil.rmtree` with error collection.
     `env_overrides` holds the three TMP names and `COGA_SYSTEM_TMPDIR`.
   - `apply_tmp_env(env, scope) -> dict[str, str]` (a copy with the overrides).
   - `sweep_orphans(cfg) -> list[Path]` and `find_orphans(cfg) -> list[Path]`
     (read-only, for validate).
   - `usage(cfg, refs) -> StateReport`: a walk with `os.scandir` and
     `lstat`, which never follows symlinks.
2. **`task_env.py`**: add the two data vars to `TASK_ENV_KEYS` and
   `build_task_env`. Directory creation does not belong in the pure builder.
   `launch_tmp_scope`, or the caller, ensures `task_data_dir` before the
   spawn.
3. **`launch.py`**: in `_launch`, wrap the phase loop in a
   `contextlib.ExitStack` stored on `_LaunchInvocation`.
   `_prepare_target` enters `launch_tmp_scope(self.cfg)` once `cfg` is
   loaded. Every place that builds a session or script env
   (`build_launch_env` call sites in `_run_initial_script`,
   `_supervise_steps`, and `prepare_agent_launch`) applies
   `apply_tmp_env`. Where the code has no direct handle on the invocation,
   the scope is passed down explicitly rather than stashed in a global.
   The `read_only` branch of `launch()` wraps `run_script_phase` in its own
   scope. Keep `build_launch_env` secret-only: it has no lifecycle.
4. **`launch_script.py` `run_script_phase`**: take an optional
   `tmp_env: Mapping[str, str]` and apply it after `apply_task_env`. Each
   caller passes the scope's overrides. `recurring_clone` opens its own
   scope around its run.
5. **`oscompat.system_tmpdir()`**, and route the listed temp users through
   it (`dir=` arguments and `lock_dir`).
6. **`validate.py`**: `Report.state: StateReport | None`, filled in `run`
   and `validate_task`; `_check_run_state(cfg, refs)` emits `orphan-tmp`
   and `stale-state`; `apply_safe_fixes` calls `sweep_orphans`;
   `emit_report` adds the `state` key and text lines.
7. **`commands/init.py`**: call `run_state.ensure_layout(cfg)`. Update the
   managed ignore comments in `commands/update.py` and
   `templates/coga/.gitignore`.
8. **`resources/prompt.md`**: add the `## Unversioned state` section, kept
   under 15 lines.
9. **Tests**: new `tests/test_run_state.py` (scope, sweep, nesting, usage,
   `system_tmpdir`); extend `tests/test_launch.py` / script-phase tests with
   a `ticket.py` that writes `tempfile.mkstemp()` and
   `$COGA_TASK_DATA_DIR/keep.txt` and prints `$TMPDIR`; extend validate and
   init tests. The seeded fixture `tests/fixtures/seeded-repo/coga/` has no
   `.coga/` and needs none, since the layout is created on demand. Add a
   fixture script ticket only if the existing ones cannot carry the
   assertion.

Order: 1, then 5, 2, 4, 3, 6, 7, 8, 9, then docs.

### Out of scope

- Moving Coga's own small bookkeeping files out of the system `/tmp`. The
  owner considers `/tmp` self-cleaning and these files small, and the per-user
  locks are deliberately outside every checkout. This ticket targets bulk
  writes by agents and the scripts they write. The constraint above only keeps
  Coga's files where they are today.
- Reporting in `coga status`. That is an alias to the `bootstrap/status`
  ticket; a follow-up can add it.
- Agent CLIs' own session and config directories.
- The owner's personal cron job, which appends `uv tool upgrade coga` output to
  `~/.local/state/coga-upgrade.log`. That is not Coga code.
- Enforcement. Nothing blocks or detects writes outside the repo, such as a
  sandbox profile or an audit of `$HOME`. The rule is prose plus a default
  that makes compliance automatic.
- A socket-path fallback, such as a short `/tmp` symlink to the managed tmp.
  The design only warns. See Open Questions.
- Moving existing `.coga/` contents (`recurring-runs/`, `dream-scans/`, ...)
  under `data/`, and size limits or quotas on `data/`.
- Deleting a ticket's `data/` when the ticket is retired or deleted.
  `stale-state` makes it visible, and the owner deletes it.
- Commands other than `coga launch` (for example a bare `coga bump` run by a
  human) get no tmp scope.

## Context

### Background

Found in `manycore-com/magicator2` and `manycore-com/fastci` on 2026-11-21. An
agent-written `scripts/aws-bench.sh` (magicator2 `5850817c4`, 2026-11-06) kept
benchmark keys and evidence under `~/.local/state/magicator-bench`. Other runs
used `~/.codex/magicator-bench-state`, `/tmp/...` and
`~/Code/fastci-sota1-validation`, about 17 GB of research evidence in all. It
was all moved by hand into each repo's ignored `data/`, and the repos now state
the rule in `coga/context.md`. Coga should make that the default instead of a
per-repo rule.

### Pointers

Cited topics live under `src/coga/resources/templates/coga/bootstrap/contexts/coga/`.

- `coga/init` (cited): read what `coga init` writes and how it seeds
  `.gitignore`. Document the new directory and its ignore entry there. Today
  `.gitignore` ignores all of `.coga/` inside the Coga-managed block. If the
  directory goes under `.coga/`, no ignore change is needed, but durable
  evidence then sits beside disposable `[launch].worktree` checkouts. The
  design weighs that trade-off explicitly. Repos that predate `coga init` must
  already list the directory in `.gitignore` before first use, or git
  untracked scans will see it.
- `coga/launch` and `coga/prompt-composition` (cited): read the launch
  environment and the base-prompt layer. The rule goes into the base prompt
  resource under `src/coga/resources/`. `config.build_launch_env` is the shared
  environment builder for agents and script phases, and is the natural place
  for the new variables.
- `coga/script-tickets` (cited): `ticket.py` phases get the same environment.
- `coga/sandboxes` (cited). The fact the design depends on: Codex
  `workspace-write` allows writes to the checkout and to the temp dirs it
  knows, and `.git` stays read-only. Confirm a repo-local `TMPDIR` is writable
  in sandboxed and nested-reviewer sessions.
- Existing env vars (`COGA_TASK_DIR`, `COGA_TASK_BLACKBOARD`, `COGA_REPO_ROOT`,
  ...) come from `launch` and `task_env.apply_task_env`. Follow their naming.
  `apply_task_env` re-derives the environment for each nested launch and
  handles checkouts whose state lives elsewhere, so the design decides which
  checkout's managed directory a nested run uses.

### Pitfalls for the design

- Unix socket paths are limited to about 108 bytes (`sun_path`). A deep repo
  path plus `tmp/` can break ssh ControlMaster, gpg-agent, tmux, Docker/BuildKit
  and Python `multiprocessing`. Plan a short path, or a fallback for sockets.
- Claude Code and Codex use `TMPDIR` for their own scratch space and daemon
  sockets (for example `/tmp/codex-daemon-<uid>`). Check that redirecting it
  does not break the agent CLI, which this rule leaves alone.
- uv and pip build directories follow `TMPDIR`. That works, but renames from
  the cache to tmp can cross devices and be slower.
- `TMP` and `TEMP` matter only on Windows.
- `.coga/` today holds machine-local run records. `AGENTS.md` and
  `coga-dev/packaging` list it as a local artifact. Update both if the new
  directory sits beside it or inside it.
- Update `tests/fixtures/seeded-repo/` and the init/launch/status tests.

### Codebase facts the design rests on (verified 2026-11-21)

Cite symbols. Any ranges below are navigational only and expected to drift.

- **Where `.coga/` lives.** The machine-state directory is `cfg.repo_root / ".coga"`
  (`recurring_autofix.py` run records, `recurring_clone.clone_state_dir()`).
  In this repo that is `coga/.coga/`. Nothing exists at the checkout-root
  `.coga/`. `task_env.host_repo_root(cfg)` is the checkout, not this.
- **It is already ignored twice.** `commands/update.py`
  `_HOST_GITIGNORE_BODY` (written by `ensure_host_gitignore`, called from
  `commands/init.py` `init`) and the packaged
  `src/coga/resources/templates/coga/.gitignore` (refreshed by
  `_refresh_coga_gitignore`) both list unanchored `.coga/`. Only the
  comments need to change.
- **No `[launch].worktree`.** `config.py` has no such key, and the
  `configuration` topic's `[launch]` row lists only `idle_timeout` and
  `max_session`. The root `.gitignore` comment mentioning it is stale.
- **Env builders.** `config.build_launch_env(cfg, declared, base_env=)` only
  scopes secrets and scrubs 1Password auth. It is called per session, from
  `launch.py` `_LaunchInvocation._run_initial_script` /
  `_supervise_steps` / `prepare_agent_launch`, `launch_script.run_script_phase`,
  and `recurring_clone`. `task_env.apply_task_env` then clears
  `TASK_ENV_KEYS` and re-sets them from `build_task_env(cfg, ref, ticket)`.
  That is what guarantees that a nested launch re-derives rather than
  inherits. `run_script_phase` calls `build_launch_env`, then
  `apply_task_env`, then pops the supervisor/expected keys, which is where
  `tmp_env` slots in.
- **Launch lifecycle seam.** `launch._launch` builds one `_LaunchInvocation`
  and runs `_prepare_target` → `_classify_target` → `_run_initial_script` →
  `_prepare_agent`, then `_supervise_steps`. The supervisor chains steps
  inside this one call, so one `_launch` = one tmp scope covers the whole
  step chain. `launch()`'s `read_only` branch bypasses `_launch` and calls
  `run_script_phase` directly. `launch_recurring_period` and
  `launch_with_before_spawn` both go through `_launch`.
- **Coga's own temp users** (all resolve via `tempfile` → `TMPDIR` today):
  `oscompat.lock_dir` (only `tests/test_oscompat.py` calls it now, but keep
  it routed), `compose.write_prompt_file` (`NamedTemporaryFile(dir=dest_dir)`),
  `repl_supervisor` and `repl_supervisor_nt` (`mkdtemp(prefix="coga-done-")`),
  `skill_manager` (three `TemporaryDirectory(prefix="coga-skill-…")`),
  `launch.agent_command_refusal` (Windows placeholder sized like the real
  prompt path), `coga_edge/skill_update_pr.py` (`NamedTemporaryFile`).
  `atomicio` uses `dir=path.parent`, so it is unaffected.
  `templates/.../skills/git/push-and-open-pr/run.py` is a workflow script, so
  it *should* land in the managed tmp.
- **Locking primitive.** `oscompat.lock_fd(fd, blocking=)` is flock on POSIX
  and `msvcrt.locking` on byte 0 on Windows. Both are released by the kernel
  when the owner dies.
- **Validate shape.** `validate.Report` has `issues`, `fixes`, `ok_count`.
  `emit_report` serializes `generated_at`, `ok_count`, `fixes`, `issues`.
  `apply_safe_fixes` is the only mutating path and runs only under `--fix`.
  Text output prints "All good" only when `issues` is empty, so state
  reporting must not be an info-severity issue.
- **Sandbox.** Per `coga/sandboxes` ("Codex sandbox grant"), Codex
  `workspace-write` makes the checkout writable, so `<coga root>/.coga/tmp/`
  is writable without a grant. The topic also says Dream's Retro pass puts a
  linked worktree inside its `mktemp -d` run directory. With this change that
  directory sits under `.coga/tmp/<token>/` inside the checkout. Confirm that
  `git worktree add` into an ignored subdir of the primary checkout works,
  and that the purge runs `git worktree prune`, or leaves the stale worktree
  metadata harmless.

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

pr: https://github.com/FastJVM/coga/pull/1280
branch: coga/v1-no-weird-state-in-personal-dir-d9bd4b
base: main
remote: origin
reviewed: afcf188110a594f05b94dbadb57f0350f5f9e880


## Implement (step 5) — handoff

Implemented in `ee01e9211` on this branch. The six evaluator resolutions and
the answers to Open Questions 1–4 were adopted by the owner in the implement
session and now live in `## Description` → "Evaluator resolutions"; the
Evaluator review below is resolved by them.

Decisions made during implement, with reasons:
- Worktree data root reads `.git` → `gitdir` → `commondir` on disk instead
  of running `git rev-parse`: `build_task_env` runs on every spawn
  (including `coga ticket` authoring), and a subprocess there broke tests
  stubbing `subprocess.run` and cost a call per spawn.
- The >64-byte path warning fires on every launch, command aliases and
  read-only dispatch included (owner reconfirmed after seeing that it adds
  stderr noise for `coga usage`-style aliases in deep repos). Tests quiet it
  in-process via `tests/conftest.py` and filter it in subprocess helpers.
- Tmp env is applied at the spawn call sites (`_supervise_steps`,
  megalaunch) and inside `run_script_phase(tmp_scope=)`, not in
  `spawn_agent_session`, so `coga ticket` authoring (not a launch) gets no
  tmp scope, per Out of scope.
- Dream `validate-drift` classifies `orphan-tmp`/`stale-state` as
  human-needed and drops machine-local `orphan-tmp` fixes before
  `git add`, which would otherwise fail on an ignored, deleted path.

Remaining work (not done in this session):
- **Manual receipts.** The acceptance criterion's real attended Claude Code
  and Codex (`--no-daemon`, `workspace-write`) launches cannot run from
  inside this agent session (no nested `coga launch`). The owner should run
  one of each and have the agent run
  `echo $TMPDIR; mktemp; python -c 'import tempfile;print(tempfile.mkdtemp())'`,
  confirm both paths are under `coga/.coga/tmp/<token>/`, that the CLI keeps
  working, and that both are gone after exit; record the output here.
- Windows paths (lock retirement order, `msvcrt` on read) are covered only
  by code review; Windows/macOS checks are release-only per coga-dev/testing.

## Evaluator review

Resolved during implement: see `## Description` → "Evaluator resolutions".

The design needs revision before implementation. The frozen workflow has the
right owner gate, the Description is structured for the implementation prompt,
and the proposed shared module has several real consumers.

### Must resolve before implementation

1. **Cover every executor and define its data identity.**
   `src/coga_edge/megalaunch.py` → `_launch_until_stop` calls
   `run_script_phase` and `prepare_agent_launch` directly. Scope the
   megalaunch child chain explicitly and test both paths. In
   `src/coga/recurring_clone.py` → `run_clone_template`, clone scripts have
   a template name and period, no task ref, and explicitly lose
   `TASK_ENV_KEYS`. Define their data variables and reporting identity while
   preserving the absence of task completion authority. Explicitly exempt
   parser-only bootstrap help (`launch_script.run_bootstrap_script_help`),
   which can run without a repository and clears inherited task identity.
2. **Decide what read-only dispatch may write and delete.**
   `coga/launch` → “Read-only command dispatch” excludes initialization
   and sweeps. The proposed common scope creates the durable layout and
   sweeps previous runs, including when called by shipped read aliases.
   Define the permitted effects and test them with missing state and with
   pre-existing orphan and durable entries. Also specify whether
   `--prompt-report` may create state or sweep when no executor runs.
3. **Keep cleanup exclusive through deletion.** Proposed shape 1 releases
   its lock before removing the directory. `oscompat.lock_fd` protects
   only while held, so a launch sweep or `validate --fix` can delete the
   same tree concurrently. Specify exclusive deletion and lock-file
   retirement, including Windows close-before-unlink and a crash between
   lock creation and directory creation. Use the same grace predicate for
   reporting and removal, and keep default validation from creating lock
   files. Test overlapping cleanup attempts and interrupted creation.
4. **Make attribution and retention unambiguous.** `tasks.list_tasks`
   accepts both `tasks/foo.md` and `tasks/foo/bar.md`, so `data/foo` is
   both an owner and a namespace. It also accepts `tasks/bootstrap/status.md`,
   whose id collides with the stateless `BootstrapRef.id_slug`.
   The unattributed rule cannot distinguish a deleted `v1/foo` from an
   arbitrary subtree. Define a collision-free mapping or explicit ownership
   record and test these cases. Decide worktree lifetime in the body.
   The current mapping puts durable data inside the parent’s purgeable
   tree when the Retro skill creates a linked checkout beneath `mktemp -d`
   (`skills/retro/done-ticket`, linked checkout setup). That conflicts
   with durable retention.
5. **Define scoped validate repair.** In `src/coga/validate.py`,
   `validate_task(fix=True)` calls `apply_safe_fixes(cfg, only=[ref])`.
   An unconditional sweep there would let `validate --task <slug> --fix`
   delete unrelated tmp state it never reports. Decide whether orphan repair
   is repo-wide only and specify how empty orphans and failed removals
   appear in the report.

### Optional refinements

- Align “One managed place” with the location inside `.coga/` and update
  the Context pointer that still suggests extending `build_launch_env`.
  Clarify that the layout helper is idempotent while `commands/init.py`
  refuses to reinitialize an existing repo.
- In the attended receipts, capture the actual paths from both temp tools
  and their post-exit cleanup. Clarify that POSIX can unlink an open file
  successfully while its process continues to hold the disk space.

## Peer-review notes

- Codex reproduced an unlinked liveness lock, a failed-mkdir cleanup that
  could delete a pre-existing directory, and validation aborting on invalid
  UTF-8 ownership metadata. The correction makes launch retry a retired
  lock, holds a claim through orphan deletion, and keeps evidence visible
  when ownership metadata cannot be read.
- The owner authorized disposable scratch outside the checkout with
  cleanup on success or failure. Peer review used dedicated system-temp
  pytest directories under that rule. The prompt now carries the rule.
- The owner moved the two real attended agent smoke checks to the owner
  gate. Record the paths printed by both temp tools and their post-exit
  absence before closing the ticket.
- The earlier in-checkout suite discovered the live repo during an
  uninstall test. Deleted tracked files were restored from the index.
  The 18 pre-existing unstaged audit-log lines and the ignored local
  config were not recovered. With owner authorization, peer review recreated
  the local config with only `user = "nicktoper"`. The earlier fixture
  directories were removed.

## PR review follow-up

The guided `coga ticket` interviewer opens one managed temporary scope and
creates the durable directory for its target before spawning. The regression
test covers a named task and the no-target interview, with successful and
failed agent exits. It checks that scratch and the lock are removed and that
durable files survive. [Review thread](https://github.com/FastJVM/coga/pull/1280#discussion_r4657144642)

Verified `1076d8a944975183c34dd59467a62824605a9f69` on Pop!_OS 24.04 LTS
(Linux 7.2.15-76070215-generic, Python 3.12.12). The three temp variables
pointed to a dedicated `/tmp/coga-pr1280.owGTQD` directory, removed after
the run. `COGA_SYSTEM_TMPDIR` and `SLACK_WEBHOOK_URL` were unset.

- `PYTHONPATH="$PWD/src" TERM=dumb /home/n/Code/coga/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_ticket.py tests/test_run_state.py`
  passed 83 tests in 2.95s.
- `PYTHONPATH="$PWD/src" TERM=dumb /home/n/Code/coga/.venv/bin/python -m pytest -q -p no:cacheprovider`
  passed 3,194 tests with 29 skips in 196.83s.
- `env -u SLACK_WEBHOOK_URL PYTHONPATH="$PWD/src" /home/n/Code/coga/.venv/bin/python -m coga.cli validate --task v1/no-weird-state-in-personal-dir --json`
  passed with the worktree's missing local user warning.

The PR now targets `main` after its parent PR #1279 merged. The Dev record
reflects that base. GitHub currently reports a merge conflict.

## PR

```yaml
title: Keep launch run state inside the repo
author: claude
author_evidence: >-
  Attended implement session ran as Claude Code (claude-opus-5-5); see the
  implement handoff above.
head: afcf188110a594f05b94dbadb57f0350f5f9e880
base: d8b7250303f0ce5002de63522603439bf7cfd3aa
depth: deep
rationale: >-
  Changes the environment of every launched agent and script (TMPDIR, TMP,
  TEMP and new COGA_* variables), adds lock-guarded deletion of on-disk state,
  and extends the validate JSON contract. The independent review found
  cleanup and attribution defects that the review commit resolves.
implementation: >-
  New src/coga/run_state.py owns the .coga/data and .coga/tmp layout, the
  per-launch tmp scope (lock held from before mkdir until after deletion),
  the orphan sweep and the usage walk. _launch, megalaunch child chains,
  recurring clone runs and read-only dispatch open scopes; task_env exports
  COGA_DATA_DIR and COGA_TASK_DATA_DIR; Coga's own temp files use
  oscompat.system_tmpdir(); validate reports state, orphan-tmp and
  stale-state; init creates both areas; the base prompt states the rule.
  Codex closed the liveness-lock race and added regression tests, preserved
  evidence with unreadable metadata, and implemented the owner's clarified
  policy for disposable scratch outside the checkout.
deviations: >-
  Adopts the six owner-approved evaluator resolutions recorded in the ticket
  Description, so data lives under data/tasks and data/bootstrap with
  .coga-owner records rather than data/<id_slug>, and linked worktrees keep
  data in the primary checkout. The orphan sweep lives in validate.run
  rather than apply_safe_fixes, so a --task fix never sweeps.
limitations: >-
  The owner deferred the attended Claude Code and Codex smoke checks to
  the owner gate. Native Windows and macOS verification is deferred to
  release, and the Linux test environment used Python 3.12. The long-path
  warning fires on every launch whose tmp path exceeds 64 bytes.
files:
  .gitignore: Replace the stale [launch].worktree comment in the managed block with the run-state description.
  AGENTS.md: List .coga/data and .coga/tmp as machine-local state.
  coga/.gitignore: Match the packaged managed-block comment for .coga/.
  docs/contexts/coga-dev/codebase/SKILL.md: Add run_state.py and system_tmpdir to the source map.
  docs/contexts/coga-dev/packaging/SKILL.md: List .coga/data and .coga/tmp as machine-local artifacts.
  src/coga/commands/init.py: Create the run-state areas during init.
  src/coga/commands/update.py: Describe data/ and tmp/ in the host managed ignore comment.
  src/coga/compose.py: Write prompt files to the system temp.
  src/coga/launch.py: Open one tmp scope per _launch and read-only dispatch; apply it to agent spawns.
  src/coga/launch_script.py: Accept tmp_scope in script phases and chains; withhold data vars from read-only.
  src/coga/oscompat.py: Add COGA_SYSTEM_TMPDIR and system_tmpdir(); route lock_dir through it.
  src/coga/recurring_clone.py: Give clone scripts a tmp scope and COGA_DATA_DIR without task identity.
  src/coga/repl_supervisor.py: Create done sentinels in the system temp.
  src/coga/repl_supervisor_nt.py: Create done sentinels in the system temp.
  src/coga/resources/prompt.md: Add the Unversioned state rule to the base prompt.
  src/coga/resources/templates/coga/.gitignore: Describe data/ and tmp/ in the packaged ignore comment.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Document the run-state areas init creates.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: New Run state section owning the scope, purge and sweep contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md: Mention the base prompt's run-state rule.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sandboxes/SKILL.md: Note the repo-local TMPDIR is inside the workspace-write root.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: Add COGA_DATA_DIR, COGA_TASK_DATA_DIR and TMPDIR to the env contract.
  src/coga/run_state.py: New shared module for layout, tmp scope, sweep and usage.
  src/coga/skill_manager.py: Create skill scratch directories in the system temp.
  src/coga/task_env.py: Export and clear the two data variables with the task namespace.
  src/coga/validate.py: Report state, orphan-tmp and stale-state; sweep orphans on repo-wide --fix.
  src/coga_edge/megalaunch.py: Open one tmp scope per child chain for script and agent phases.
  src/coga_edge/skill_update_pr.py: Write the PR body temp file to the system temp.
  src/coga_edge/validate_drift.py: Classify the new kinds and never commit machine-local orphan-tmp fixes.
  tests/conftest.py: Quiet the socket-path warning for in-process tests.
  tests/report_helpers.py: Filter the run-state warning from subprocess stderr.
  tests/test_dream_validate_drift.py: Expect the state key and cover skipped machine-local fixes.
  tests/test_init.py: Cover init creating ignored run-state areas.
  tests/test_launch_script.py: Cover script and agent env, purge on failure and exception, prompt-report and read-only.
  tests/test_megalaunch.py: Cover megalaunch scopes for agent and script phases.
  tests/test_recurring_clone.py: Cover clone scope and data variables without task identity.
  tests/test_run_state.py: Unit tests for scope, sweep, attribution, worktrees, validate and temp routing.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: afcf188110a594f05b94dbadb57f0350f5f9e880
  base: d8b7250303f0ce5002de63522603439bf7cfd3aa
  detail: >-
    Codex reviewed the full recorded diff in a separate session from the
    Claude implementation and authored the localized review corrections.
    Codex re-reviewed those corrections at the resulting head and verified
    lock acquisition and cleanup, corrupt metadata handling and prompt
    guidance. See Peer-review notes for the original failing reproduction.
checks:
  - command: >-
      TMPDIR=/tmp/coga-peer-review-exact.ST5BjZ9l PYTHONPATH="$PWD/src"
      TERM=dumb .venv/bin/python -m pytest -q -p no:cacheprovider
    status: passed
    head: afcf188110a594f05b94dbadb57f0350f5f9e880
    base: d8b7250303f0ce5002de63522603439bf7cfd3aa
    detail: >-
      3190 passed, 29 skipped in 158.43s on the exact reviewed code and tests.
      Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.12.12.
      Fixture directory removed.
  - command: >-
      TMPDIR=/tmp/coga-peer-review-focused.YN9k3I0f PYTHONPATH="$PWD/src"
      TERM=dumb .venv/bin/python -m pytest -q -p no:cacheprovider
      tests/test_run_state.py
    status: passed
    head: afcf188110a594f05b94dbadb57f0350f5f9e880
    base: d8b7250303f0ce5002de63522603439bf7cfd3aa
    detail: >-
      28 passed in 0.33s on Pop!_OS 24.04 LTS,
      Linux 7.2.15-76070215-generic, Python 3.12.12. Fixture directory removed.
  - command: >-
      env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src
      /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json
    status: passed
    head: afcf188110a594f05b94dbadb57f0350f5f9e880
    base: d8b7250303f0ce5002de63522603439bf7cfd3aa
    detail: >-
      Exit 0 in this repo (80 tasks, warnings only, including missing local
      operator) and tests/fixtures/seeded-repo/coga (5 tasks, no issues).
  - command: attended Claude Code and Codex launches running mktemp and tempfile.mkdtemp
    status: not-run
    detail: >-
      Owner explicitly deferred live smoke checks to the owner gate.
```
