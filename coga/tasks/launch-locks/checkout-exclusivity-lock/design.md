<!-- Moved from the blackboard of launch-locks/checkout-exclusivity-lock on 2026-10-06 (large-blackboard remedy, coga/blackboard). Verbatim. -->

## Design (step 1, 2026-10-06)

Owning contract topic: **new `coga/internals/checkout-lock`**
(`docs/contexts/coga/internals/checkout-lock/SKILL.md`, its packaged twin under
`src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/checkout-lock/SKILL.md`,
and an entry in `tests/test_packaging.py` `REQUIRED_BOOTSTRAP_CONTEXT_REFS`
beside the other `coga/internals/*` refs). Code home: new
`src/coga/checkout_lock.py`. It is shared infra with several consumers:
`cli.main` acquires, releases, and gates `init`/`uninstall`;
`repl_supervisor` and `launch_script` record children; and the recovery
command uses it.

### Problem

Today nothing stops two `coga launch` processes, or a launch and a
`coga chat`, from working in the same checkout. The launch boundary in
`git.prepare_control_checkout` moves HEAD and restores or removes files.
`_refresh_agent_skills_for_launch` rebuilds `coga/.agent-skills/`. A code
agent switches branches. A second launch in the same working tree can yank
HEAD, the tree, or the skill view out from under a live agent. `coga/launch`
§ Targets even says bootstrap targets are "concurrent launches safe".
`git.state_lock` serializes only short ticket read-modify-write windows.
We want at most one working launch per physical checkout, shown by a
plain file, with a manual and conservative recovery after a crash.

### Core idea

The lock is one file, `<cfg.repo_root>/.coga/launch.lock`. A process becomes
the holder by atomically creating it with complete metadata. The holder is
the outermost `cli.main` process of a *launch-class* command. It acquires the
lock before `app()` runs, so no command side effect has happened yet. It
releases the lock in `cli.main`'s `finally` after the end-of-command sweep.
That makes ownership span the whole invocation: entry sweep, checkout
preparation, every script and agent phase, chained steps, the final
publication, the checkout return, and the outer sweep. Child processes
inherit an environment witness, so nested `coga` commands recognize their
own session instead of refusing it. The file existing is the lock. Its
metadata only supports inspection and recovery, and age never proves
anything.

### Acceptance criteria

- [ ] **Path and identity.** `checkout_lock.lock_path(cfg)` returns
      `cfg.repo_root.resolve() / ".coga" / "launch.lock"`. It is the only
      constructor. Because the file lives *in* the checkout, every symlink,
      bind-mount, or relative-path alias of the checkout reaches the same
      inode, so physical identity needs no path canonicalization. The resolved
      path is recorded for display and for the witness check. Root and nested
      layouts both put it beside `coga.toml`. Different clones and linked
      worktrees each have their own file and stay independent.
- [ ] **Launch-class commands acquire.** `checkout_lock.takes_lock(argv)`
      reads the alias-expanded argv. It is true for `launch` (including
      `bootstrap/*`, `coga chat`, delegated recurring targets, and
      `--prompt-report`, which still rebuilds the skill view and sweeps),
      `megalaunch`, `ticket` (guided authoring spawns an agent in this
      checkout), and `recurring` when its own work runs here (bare or
      `launch`; not `--all`, not `list`). It is also true for `run
      recurring-scan` (the per-repo child of `recurring --all`). It is
      false for `--help`/`-h` and for every other command. A config-less
      invocation (`cfg is None`) never takes the lock.
- [ ] **Acquire** (`checkout_lock.acquire(cfg, argv)`), called in `cli.main`
      after config load and alias expansion, before the `try: app()` block:
      1. Witness check (below). If the witness matches, the command is
         nested: it neither acquires nor releases.
      2. `mkdir(.coga, exist_ok=True)`. If `.coga` exists and is not a
         directory, refuse.
      3. Ignore check (below).
      4. Write the full metadata to `.coga/launch.lock.<session>.tmp` with
         `O_CREAT|O_EXCL`, mode `0600`, and fsync. Then, with SIGINT and
         SIGTERM blocked (`signal.pthread_sigmask`, the pattern
         `repl_supervisor` already uses) and under the guard (below), call
         `os.link(tmp, lock)` and register the held handle in a module-level
         slot. Finally unlink the tmp file. `link` is atomic and fails with
         `EEXIST`, so the lock appears exclusively *and complete*: no
         partially written lock is possible. A filesystem without hard links
         (`EPERM`/`ENOTSUP`/`EXDEV`) falls back to `O_CREAT|O_EXCL` on the
         lock path plus write and fsync. That fallback is documented as able
         to leave partial metadata after a crash.
      5. On `EEXIST`, read the holder and refuse (below).
      6. On success, set `os.environ["COGA_CHECKOUT_LOCK_SESSION"] =
         <session>` so every child inherits it. Install SIGTERM and SIGHUP
         handlers that raise `SystemExit(128 + signum)`, but only where the
         current disposition is `SIG_DFL`, so `finally` runs on a polite kill
         before launch installs its own handlers. Launch's existing
         `_on_signal` handlers keep working unchanged.
- [ ] **Metadata.** The file is UTF-8 JSON with `indent=2`, sorted keys, and
      a trailing newline:
      - `format` (`"coga-checkout-lock/1"`) and `session` (uuid4);
      - `host`: `/etc/machine-id` or null, plus `hostname`;
      - `boot_id`: Linux `/proc/sys/kernel/random/boot_id`, macOS `sysctl
        kern.boottime`, else null;
      - `pid`, `pgid`, and `pid_start`, the start marker. On Linux that is
        field 22 of `/proc/<pid>/stat`; elsewhere `ps -o lstart= -p <pid>`;
        null if unreadable;
      - `user`, `checkout` (resolved `cfg.repo_root`), `git_toplevel` (or
        null), `command` (the alias-expanded argv), `started_at` (UTC
        ISO-8601), and `coga_version`;
      - `children`: a list of `{pid, pgid, pid_start, kind:
        "agent"|"script", started_at}`.
- [ ] **Children are recorded, so a surviving agent is visible.**
      `checkout_lock.note_child_started(pid, kind)` and
      `note_child_exited(pid)` do nothing unless this process holds the
      lock. Otherwise they rewrite the lock atomically under the guard:
      temp file, `os.replace`, then a check that the bytes still name our
      session. `repl_supervisor.run_with_done_marker` calls them right after
      `pty.fork()` returns in the parent. The child leads its own session,
      so pgid = pid. It calls them after reaping, and does the same on the
      non-PTY path (switch `subprocess.run` to `Popen` + `wait`).
      `launch_script.run_script_phase` does the same for the `ticket.py`
      child. A nested (witness) process does not record its children. That
      is an accepted limitation: its processes belong to the holder's
      recorded process group or run in the foreground inside it.
- [ ] **Witness.** `COGA_CHECKOUT_LOCK_SESSION` is a separate variable from
      `COGA_SUPERVISED`. `launch_script` pops `COGA_SUPERVISED` and the
      sentinel and expected-task/step variables for `ticket.py` children,
      but it must *not* pop this one. `build_launch_env` and the authoring
      env (`config.scrub_op_auth_env`) both start from `os.environ` and
      already carry it. A launch-class command whose env witness equals the
      `session` in *this* checkout's lock file runs nested: it skips
      acquisition and release. If the witness is set but the file is
      missing, unparsable, or holds another session, the witness is ignored
      and normal acquisition applies. This covers the
      recurring control relay into another worktree and `recurring --all`
      children in other repos.
- [ ] **Refusal.** A losing launch-class command prints to stderr and exits
      **75** (`git.RETRY_WITHOUT_SWEEP_EXIT_CODE`). The message names the
      path, `session`, `command`, `pid`, `hostname`, `started_at`, recorded
      children, and an advisory liveness verdict (same procedure as
      recovery, informational only). It ends with the recovery command. The
      refusal happens before `app()` and outside its `try`, so no sweep,
      checkout preparation, skill rebuild, or log write runs. Recurring's
      `_sweep_stopping_exit` already stops a sweep on 75, which is the right
      outcome for an occupied checkout. An unparsable lock file refuses the
      same way and names the raw path.
- [ ] **Release.** In `cli.main`'s `finally`, after `_sweep_coga_state`
      (every branch: success, `SystemExit` including 75, other exceptions,
      Ctrl-C), and before the contextvar resets: under the guard, read the
      lock. If its `session` is ours, unlink it. If the file is missing or
      names another session, print a loud warning ("checkout lock was
      removed or replaced while this launch held it") and touch nothing.
      Then unregister and remove the env witness. A release `OSError` prints
      a warning naming the file and the recovery command, and it never
      changes the exit status. A nested process never releases.
- [ ] **Guard.** A short `fcntl.flock(LOCK_EX)` on an `O_RDONLY` fd of the
      `.coga/` *directory* covers the link-create, child rewrites, release,
      and recovery's compare-and-unlink. It is held for microseconds, the
      kernel releases it, and it leaves no file behind. It closes the
      ABA race in which a recoverer or a stale releaser unlinks a newer
      holder's file. It is *not* `git.state_lock`, which stays unchanged.
      The long-lived exclusion is the file itself, never a held flock.
- [ ] **Ignore check and repair.** In a git checkout, before writing:
      - If `git ls-files --error-unmatch` reports the lock path as tracked,
        refuse with "remove it from the index".
      - If `git check-ignore -q <lock path>` says it is not ignored, repair
        locally by creating `.coga/.gitignore` with `*\n` via `O_EXCL`. This
        is a self-ignoring directory with no tracked change, so it never
        dirties the checkout that the launch boundary must prove clean.
        Never overwrite or append to an existing `.coga/.gitignore`.
      - Re-check. If it is still not ignored, refuse with the remedy `coga
        init --update` (which refreshes both managed blocks) and commit.
      - Non-git and Git-disabled workspaces skip this check.
      - Existing state: both managed blocks already carry an unanchored
        `.coga/`. `update._HOST_GITIGNORE_BODY` covers the git-root
        `.gitignore`, and the packaged `coga/.gitignore` covers the nested
        layout. The unanchored pattern matches `<coga root>/.coga/` in root
        and nested layouts. This repo was verified: `git check-ignore -v
        coga/.coga/launch.lock` → `coga/.gitignore:9:.coga/`.
      - The launch boundary's "ignored file the move would overwrite"
        refusal fires only if the target commit *tracks* that path. The
        tracked-path refusal above, plus no Coga code ever committing
        `.coga/`, keeps it from firing. If control ever did track it, the
        boundary refusing is the correct conservative outcome.
- [ ] **Never disposable.** Coga only ever deletes a lock whose bytes parse as
      `coga-checkout-lock/1` and whose `session` it was told about: its own
      at release, or the `--session` the human typed at recovery. It also
      deletes only its own `launch.lock.<session>.tmp`. It never removes
      `.coga/` or other files there, and never rewrites a user's
      `.coga/.gitignore`. A stray tmp file left by a crash between link and
      unlink is harmless. Recovery lists it and deletes it only when its
      session equals the released one.
- [ ] **Other mutating commands.** Commands that are not launch-class do not
      acquire and are not refused: `create`, `bump`, `block`, `unblock`,
      `mark`, `owner`, `slack`, `run <recipe>`, `delete`, `retire`, `skill
      install/update/remove`, and the end sweep. None of them moves this
      checkout's HEAD. They serialize through `git.state_lock` and the
      publish compare-and-set, as today. When a lock exists and the
      witness does not match, `cli.main` prints one stderr notice
      ("checkout occupied by launch <session> (<command>, pid <pid>);
      proceeding: this command does not move the checkout"). Nested calls
      from the holding session match the witness, so they print nothing
      and can never deadlock, because they never acquire. **Exception:**
      `init` (all forms) and `uninstall` refuse with 2 while a foreign
      lock exists, because they rewrite or remove the Coga tree, `.coga/`,
      and the agent-skill view under a live agent. Read-only commands
      (`status`, `show`, `validate`, `usage`, `recurring list`, `secret
      get`, `checkout-lock` show) never read the lock for gating.
- [ ] **Recovery command** `coga checkout-lock` is read-only (show) and
      `coga checkout-lock release --session <uuid>` is the explicit
      recovery. Add `checkout-lock` to `cli._NON_SWEEPING_COMMANDS`.
      Release does the following:
      1. Read bytes B. If there is no file, report that and exit 0. If the
         file is unparsable, refuse and print the path. The manual procedure
         below applies.
      2. `--session` must equal B's `session`. This pins the exact holder the
         human inspected.
      3. If the env witness equals the session, refuse ("you are inside the
         holding session").
      4. `host`/`hostname` must equal this machine's. Otherwise refuse: "lock
         created on <hostname>; release it there or remove it manually".
      5. Liveness. If `boot_id` differs from the current one, every recorded
         process is dead. Otherwise judge the holder `pid` and each child
         `pid` like this:
         - no such process → dead;
         - start marker differs → dead (PID reused);
         - marker equal → **alive**;
         - marker unreadable → **unknown**.

         Then for each recorded `pgid` whose leader is dead, `os.killpg(pgid,
         0)` succeeding means a group member survives → **alive**. Any alive
         or unknown verdict refuses, naming each pid/pgid and the remedy
         (`kill -TERM -<pgid>`, then retry). There is no `--force`.
      6. Under the guard, re-read the file. It must equal B byte for byte. Then
         unlink it and its stray tmp file. If it changed, refuse ("lock
         changed during recovery").
      7. Print a reminder that the dead session may have left uncommitted
         work. The next launch's checkout boundary refuses unpublished
         changes, so inspect `git status` before relaunching.
- [ ] **Manual procedure** (documented in the topic). It works without the
      command, and it is the path for an unparsable file, another host, or
      an unknown verdict:
      1. `cat` the file.
      2. Confirm with `ps -p <pid> -o lstart=` and `ps -g <pgid>` (or a
         reboot) that the recorded processes and their groups are gone.
      3. Check that no agent is running in that directory.
      4. `rm <coga root>/.coga/launch.lock`.

      Stated limitations:
      - a child recorded in the fork-to-record window, or a `setsid`
        descendant that left the group, is invisible;
      - a lock on a network filesystem shared by two machines cannot be
        judged from the other machine.
- [ ] **No automatic stale clearing.** Acquisition never replaces an existing
      lock, even after a reboot (see Open Questions).
- [ ] **Accepted limitation, documented:** two Coga roots nested in one git
      checkout (`config.find_checkout_root`) hold separate locks, though
      both move the same HEAD. Manual Git, editors, and IDE tooling are not
      excluded: the lock only coordinates Coga launch-class commands.
- [ ] **Composition with `launch-locks/ticket-ownership-lock`** (independent;
      neither depends on the other):
      - The checkout lock is acquired first, in `cli.main`. The ticket lock
        is acquired later, inside `_launch`.
      - Release runs in reverse: the ticket lock inside `_launch`, then the
        `cli.main` sweep, then the checkout lock.
      - A checkout-lock refusal means the ticket lock is never attempted.
      - A ticket-lock refusal unwinds through `cli.main`'s `finally`, which
        releases the checkout lock.
- [ ] Contracts updated in the implementation PR, each with its packaged
      bootstrap twin:
      - `coga/launch`: § Targets drops "concurrent launches safe" for
        bootstrap targets and states the checkout lock; add a "Checkout
        lock" paragraph and the 75 refusal under Options and exits.
      - `dev/checkouts`: § Launch boundary gets acquisition-before-entry;
        the in-session and manual sections note that `coga` launch-class
        commands from inside a session are nested; § What a fresh checkout
        lacks lists `.coga/launch.lock`.
      - `coga/internals/state-publication`: the sweep is followed by
        release; `checkout-lock` is non-sweeping.
      - `coga/internals/agent-spawn`: child recording and the witness.
      - `coga/megalaunch`: the queue holds one checkout lock throughout.
      - `coga/recurring/delegation`: delegated sessions run in-process
        under the period's lock.
      - `coga/cli`: the new command.
      - `coga/extension-model`: the command-placement note.
      - `coga/packaging`: the `.coga/` runtime-file list.
      - The new `coga/internals/checkout-lock`.

### Proposed shape (order of work)

1. `src/coga/checkout_lock.py` with pure helpers first: `lock_path`,
   metadata render/parse, `process_identity(pid)` (start marker, boot id,
   machine id), and `liveness(meta)` → per-process verdicts. Then
   `guard(cfg)`, `takes_lock(argv)`, `acquire` → `HeldCheckoutLock | Nested
   | None`, `release`, `note_child_started/exited`, and `recover(cfg,
   session)`. Unit tests use fake `/proc` readers.
2. `cli.main`: acquire after alias expansion (refuse → `sys.exit(75)` before
   `try`), the `init`/`uninstall` foreign-lock refusal, the non-launch notice,
   and release in `finally` after the sweep.
3. `repl_supervisor.run_with_done_marker` (PTY and non-PTY paths) and
   `launch_script.run_script_phase`: the child notes. Assert in
   `launch_script` that the witness survives the env scrub.
4. `commands/checkout_lock.py` (show/release) and its registration.
5. Docs and packaged twins, `REQUIRED_BOOTSTRAP_CONTEXT_REFS`, `example/`
   untouched (no fixture state changes).
6. Tests in `tests/test_checkout_lock.py` plus additions to `tests/test_cli.py`
   and `tests/test_launch.py` covering the acceptance cases below. Use
   subprocess-level tests for SIGKILL survival where practical; otherwise
   use fakes.

### Out of scope

- Cross-checkout or cross-machine ticket exclusion (sibling ticket).
- Any liveness daemon, heartbeat, lease renewal, TTL, or recurring stale-lock
  collector.
- Automatic clearing of stale locks (including post-reboot), unless the
  owner opts in (Open Questions).
- Excluding manual Git, editors, or non-launch Coga commands from the
  checkout.
- Unifying two Coga roots nested in one checkout.
- Changing `git.state_lock`.
- Windows support beyond "no hard links → `O_EXCL` fallback; liveness
  unknown → manual".

### Acceptance cases (tests and the design-review checklist)

1. **Same ticket, same checkout.** Terminal A runs `coga launch T` and holds
   the lock. Terminal B's `coga launch T` exits 75 before any sweep or log
   line, naming A's session, pid, command, and start. A is unaffected.
2. **Different tickets, same checkout.** The same as case 1 with `coga launch
   U`. The refusal does not depend on the ticket.
3. **Chat plus task.** `coga chat` holds the lock, and `coga launch T`
   refuses with 75. The reverse also refuses. Bootstrap is no longer
   "concurrent safe".
4. **Symlinked path.** `cd` through a symlink alias (and through a relative
   `..` path) to the same checkout and launch. The command reaches the same
   file and refuses. The recorded `checkout` is the resolved path.
5. **Different clones and linked worktrees.** Simultaneous launches in clone
   X and clone Y both start. Each holds its own file.
6. **Ctrl-C.**
   - During preflight, during an agent session, and during the checkout
     return: `KeyboardInterrupt` or launch's `_on_signal` raises
     `SystemExit(130)`. The `cli.main` `finally` runs the sweep rule and
     then releases. No file remains.
   - Ctrl-C during the acquisition link is masked, so the lock either exists
     and is registered (and released) or does not exist.
7. **Polite SIGTERM to the coga process** before launch installs its handlers.
   The acquisition-time handler raises `SystemExit(143)` and the lock is
   released.
8. **Supervisor SIGKILL with a surviving agent child.**
   - The file remains with `children` recording the agent's pid, pgid, and
     start marker.
   - A new launch refuses with 75 and the advisory verdict "child <pid>
     alive".
   - `checkout-lock release --session S` refuses while the child or any
     member of its group lives.
   - After `kill -TERM -<pgid>`, release succeeds.
   - If a later process reuses the child's pid, the start marker differs, so
     the pid counts as dead (PID reuse).
9. **Holder SIGKILL with no children** (for example during preflight).
   Release succeeds once the holder pid is gone or reused. Recovery never
   relies on the lock's age.
10. **Reboot.** `boot_id` differs, so every recorded process is dead, and
    release succeeds without killing anything. Acquisition still refuses
    until a human releases (no auto-clear).
11. **Scripts.**
    - `ticket.py` runs under the lock and is recorded as a `script` child.
    - A `ticket.py` that calls a launch-class command (for example a script
      recipe that runs `coga launch --prompt-report`) runs nested via the
      witness and neither refuses nor releases.
    - `COGA_SUPERVISED` is still scrubbed and the witness is not.
12. **Nested commands inside a session.** The agent runs `coga bump`,
    `block`, `mark done`, `slack`, `run open-pr`, and `status`. None of
    them acquires, refuses, or prints the occupied notice. The done
    sentinel still tears the REPL down, and the outer process releases
    after its sweep.
13. **Nested delegation and recurring.**
    - `coga recurring` holds the lock across the whole sweep. A `delegate:`
      bootstrap session runs in-process without re-acquiring.
    - `coga recurring --all` does not acquire. Each `run recurring-scan`
      child acquires in its own repo. If one child finds that repo occupied,
      it exits 75 and stops that repo.
    - The control relay from a feature checkout to the control worktree:
      the parent holds checkout A, the child acquires worktree B, and
      there is no deadlock.
14. **Megalaunch.** One lock covers the whole queue across every pick. A
    second megalaunch or launch in the same checkout refuses with 75. A
    megalaunch in another clone runs.
15. **Authoring.** `coga ticket` holds the lock. A concurrent `coga launch` in
    the same checkout refuses, and the reverse also refuses.
16. **Preflight failure.** Missing CLI, refused activation, push-auth failure,
    or a checkout-boundary entry refusal (75): the lock is released in
    `finally`. A boundary-75 still skips the sweep.
17. **Teardown failure.**
    - A refused checkout return sets `state_sweep_withheld`. The sweep is
      withheld, the lock is still released, and the exit is unchanged.
    - A release `OSError` warns, names the file and the recovery command, and
      leaves the exit status unchanged.
18. **Lock replaced while held.** A human `rm`s the file mid-session and
    another launch acquires. The first launch's release finds a foreign
    session, warns, and leaves the newer lock in place.
19. **Recovery races.**
    - Two `checkout-lock release` runs on the same bytes: the guard plus
      byte equality means the second sees "no file" or "changed".
    - Recovery against a live holder that releases while recovery checks,
      followed immediately by a new acquire: recovery's byte re-check under
      the guard refuses and never unlinks the new lock.
20. **Partial metadata.** A crash after tmp write but before link leaves only
    `launch.lock.<session>.tmp`. The next acquire succeeds and ignores it. A
    malformed `launch.lock` (hand-made, or written by the no-link fallback)
    refuses with 75. The command refuses to remove it, and the manual
    procedure applies.
21. **Ignore rule.**
    - New repo (`coga init`), root and nested layouts: `check-ignore` passes
      with no repair.
    - A pre-rule repo: `.coga/.gitignore` (`*`) is created, `git status`
      stays clean, and the launch boundary still proves clean.
    - An existing user `.coga/.gitignore` that does not cover the lock: it is
      not modified, and the launch refuses with the `coga init --update`
      remedy.
    - A tracked `.coga/launch.lock` refuses.
22. **Other mutating commands.**
    - Terminal B's `coga bump U` while A holds the lock prints the occupied
      notice and proceeds.
    - Terminal B's `coga init --update` or `coga uninstall` refuses with 2.
    - `coga status`/`show` are silent and unaffected.
23. **`--prompt-report` and `--help`.**
    - `coga launch T --prompt-report` acquires and releases (and refuses
      while occupied).
    - `coga launch --help` never touches the lock.
    - A config-less directory never touches it.
24. **Combined with the ticket lock** (if shipped):
    - Acquisition order is checkout then ticket. A checkout refusal means no
      ticket-lock attempt.
    - A ticket-lock refusal releases the checkout lock through `finally`.
