---
title: Checkout exclusivity lock
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
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 3 (review-design)
contexts:
- coga/launch
- dev/checkouts
- coga/internals/launch-claims
- coga/internals/agent-spawn
- coga/internals/state-publication
agent: claude
---

## Description

Design an independent local lock that admits only one working Coga launch to a physical checkout at a time, regardless of ticket. User direction: an inspectable gitignored lock file while an agent works there. Decided path: `<coga root>/.coga/launch.lock` (beside `coga.toml`, inside the already-ignored `.coga/` runtime directory; supersedes the original root-level `.coga.lock` proposal). This is transient local runtime state and must never be published to Git or swept as task state.

Owner direction: checkout collisions are uncommon; prefer a simple lock file rather than a long-held OS advisory lock. Create it atomically (exclusive creation, not a separate existence check followed by a write) before any launch side effect, including log publication, state sweep, checkout preparation, script execution, and agent-skill regeneration. Hold through script/agent phases, chained steps, final publication, checkout return, and outer command cleanup. A losing launch names the holder and exits without a generic sweep mutating the occupied checkout. Include bootstrap/chat, ordinary tickets, recurring and megalaunch routes; specify delegation and nested child-command ownership without self-deadlock. Read-only commands remain available. Explicitly define interaction with other mutating Coga commands and limitations for manual Git/editor access.

Metadata should identify session, process and process start identity, machine, checkout, target and start time. File existence blocks a competing launch; metadata supports inspection and recovery, not proof of liveness by age alone. Remove only the owning session's file at normal teardown. After a crash the file remains: design a small explicit recovery procedure that establishes the old worker has stopped before removing/replacing it. Account for PID reuse, a surviving agent after supervisor death, partially written metadata, and races between recovery, release and acquisition. Prefer conservative refusal/manual recovery over a complex automatic liveness system. Resolve canonical checkout identity and symlink aliases. Confirm `.coga/` is ignored in existing and new repos (repair the ignore rule if missing) without treating an existing user file as disposable.

Lower priority than the ticket ownership lock: the owner identifies cross-checkout ticket collisions as the main problem. Orthogonal sibling: launch-locks/ticket-ownership-lock handles the same ticket across clones. This ticket only serializes one checkout; different checkouts remain independent and neither design depends on the other shipping. Use checkout-then-ticket acquisition order when combined. Keep the existing short-lived state_lock separate from the long-lived launch lock.

Design acceptance cases must cover two launches on the same/different tickets, chat plus task, symlinked paths, Ctrl-C, supervisor kill with a surviving child, scripts, nested delegation, preflight and teardown failures, and different clones. Update launch/checkouts/runtime contracts, the old bootstrap concurrency claims, and packaged twins in the eventual PR. Obtain owner approval of the design before implementation.

The design spec for this ticket lives in the sibling attachment `design.md` (moved from the blackboard's `## Design` for size on 2026-10-06), as the ticket's Context directs; `## Open Questions` on the blackboard lists what the owner decides in `review-design`.

## Context

Owner priority: `launch-locks/ticket-ownership-lock` ships first, and checkout collisions are considered uncommon. Keep this design small: one exclusive-create lock file plus a manual recovery procedure. It should not become a liveness daemon or a long-held `flock`. Neither ticket may depend on the other. If both ship, acquire the checkout lock first, then the ticket lock.

Code anchors (cite by symbol; line numbers drift):

- `git.state_lock` is the existing short-lived, reentrant, kernel-released `flock` in the system temp dir. It serializes one checkout's state writers and must stay separate from the new lock. Do not repurpose or lengthen it.
- Acquisition must precede every launch side effect. The side effects are listed in `coga/launch` (attached): the entry `sync_coga_state` sweep, `git.prepare_control_checkout`, activation, the `coga/.agent-skills/` rebuild, the `ticket.py` run, and the launch audit publish in `spawn_agent_session`. They live in `commands/launch.py` (`_launch`, `spawn_agent_session`) and `launch_script.run_script_chain`.
- The losing launch must not trigger the end-of-command sweep. `cli._sweep_coga_state` / `cli._should_sweep_coga_state` and `git.RETRY_WITHOUT_SWEEP_EXIT_CODE` (75) are the existing mechanism for exiting without a sweep. Decide whether a lock refusal reuses 75 or needs its own code.
- The release must happen after the checkout return and the outer `cli.main` sweep. That means ownership spans the whole `cli.main` invocation, not just `_launch`.
- Routes to cover: `coga chat` / `bootstrap/*` (currently documented as "concurrent launches safe" in `coga/launch` § Targets; that claim must change), recurring periods and their `delegate:` bootstrap sessions (`coga/recurring/delegation`, cited not attached), megalaunch picks (`coga/megalaunch`, cited), and `coga ticket` authoring, which also uses `spawn_agent_session`. Nested `coga` commands inside a session (`bump`, `block`, `mark`, `slack`, `run`) must recognize the owning session, and must not deadlock. `launch_script` pops `COGA_SUPERVISED` from a `ticket.py` child's env, so a `ticket.py` that calls `coga` would lose that witness. The lock likely needs its own env witness, not `COGA_SUPERVISED`.
- Lock location and scope (owner decision): one lock per Coga root, at `cfg.repo_root / ".coga" / "launch.lock"`, beside existing runtime state such as megalaunch's `.coga/megalaunch-selection.json`. `commands/update.ensure_host_gitignore` already writes `.coga/` into Coga's ignore block, so no new ignore entry is expected. Verify it holds for root and nested layouts and for repos initialized before that rule existed. Known accepted limitation: two Coga roots nested in one git checkout (`config.find_checkout_root`) hold separate locks, though both launches move the same checkout's HEAD. Document this rather than solve it. `sync_coga_state` never sweeps `.coga/`. The launch-boundary "proves every change" check in `dev/checkouts` ignores ignored files, but the design must confirm the lock never trips its "ignored file the move would overwrite" refusal.
- Teardown signals: `repl_supervisor.run_with_done_marker` handles SIGTERM/SIGKILL teardown and the `crash` classification (`coga/internals/agent-spawn`). The supervisor's own teardown already kills the whole process group (`os.killpg`); the dangerous case is an external SIGKILL of the supervisor, which runs no Python cleanup, so the agent child can survive with the lock file left behind. Recovery must detect that child (for example by process group or recorded child PID plus start time) and not just the supervisor PID.

The design deliverable goes on the blackboard via `code/design`, ending with the acceptance-case list from `## Description`. Owner review comes before any code. The eventual PR updates `coga/launch`, `dev/checkouts`, the relevant `coga/internals/*` topic, and the bootstrap "concurrent launches safe" wording, plus their packaged twins under `src/coga/resources/templates/coga/bootstrap/contexts/`.

Open design questions from the cold review (decide in `code/design`):
- Refusal exit code: reuse 75 (`RETRY_WITHOUT_SWEEP_EXIT_CODE`) or a distinct "occupied" code that still skips the sweep.
- Whether `coga ticket` authoring sessions take the lock.
- Name the `coga/internals/*` topic (existing or new) that owns the lock contract.
- Recovery tooling may split into a follow-up ticket if the PR grows.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design (step 1, 2026-10-06)

Moved verbatim to the sibling attachment `design.md` on 2026-10-06 (validate `large-blackboard`, coga/blackboard size remedy; ticket `validate-drift-blackboard-hygiene-two-oversized-bl`). It is the spec this ticket's review-design and implement steps work from: read `coga/tasks/launch-locks/checkout-exclusivity-lock/design.md` in full before reviewing or implementing. Evaluator-review references to `## Design` mean that file.

## Open Questions

1. **Refusal exit code.** I chose to reuse 75. It already means "occupied,
   retry later, don't sweep", and recurring already stops on it. Do you
   want a distinct code instead (for example 73) so scripts can tell
   "occupied" from "stale control"? That would also need
   `_sweep_stopping_exit` and the `cli.main` sweep exemption extended.
2. **`coga ticket` authoring takes the lock.** I decided yes: it spawns an
   agent that writes tickets in this checkout. Confirm, or exempt it
   because authoring never moves HEAD.
3. **`--prompt-report` takes the lock.** I decided yes, because it rebuilds
   `.agent-skills/` and sweeps. Exempting it would require it to stop
   rebuilding and sweeping, which is the known-defect fix in `coga/launch`.
4. **Recovery command name and placement.** I propose a new built-in
   `coga checkout-lock [release --session]`, justified as owning the
   guard-flock compare-and-unlink invariant. Alternatives:
   - share the sibling's `coga unlock` as `coga unlock --checkout --session`
     (this couples the two tickets);
   - ship only the documented manual `rm` procedure now and split the
     command into a follow-up ticket.
5. **Auto-clear after reboot.** A differing `boot_id` proves every recorded
   process dead. Should acquisition clear such a lock automatically and
   print what it cleared? The design default is no, staying conservative
   and manual.
6. **`init`/`uninstall` refusal** while a foreign lock exists. Is that the
   right set, or should `skill install/update/remove` also refuse? They
   change the skill tree a live agent reads, but they don't move HEAD.

## Evaluator review

Cold review, 2026-10-06. **Not ready for implementation.** The body clearly
delegates the specification to `## Design`; the location, separate state lock,
independence from the ticket lock, and owner-before-implementation workflow are
clear. The issues below are defects in the proposed guarantees and integration,
not reasons to block this evaluation. Owner review should resolve them before
advancing to implementation.

### Must resolve before implementation

1. **P1 — `retire` bypasses exclusivity entirely.** The design explicitly
   exempts `retire`, but `src/coga/commands/retire.py::retire` creates and
   publishes a task and then calls `commands.launch.launch` in-process unless
   `--no-launch` was passed. It does not reenter `cli.main`, so the proposed
   argv gate never acquires a lock. `tests/test_retire.py::test_retire_launches_after_create`
   confirms this route. A second terminal's `coga retire T` can therefore run
   checkout preparation and an agent while another launch holds the lock.
   Include the launching form in admission before its first side effect, and
   explicitly classify `--no-launch`. Add an occupied-checkout test through
   the real CLI entry point, asserting no creation/publication/spawn.

2. **P1 — Releasing on an exception does not establish that the worker has
   stopped.** `src/coga/commands/launch.py::_launch` installs `_on_signal`
   handlers that raise `SystemExit`. In
   `src/coga/repl_supervisor.py::run_with_done_marker`, the ordinary PTY loop's
   `finally` restores the terminal and removes the sentinel; it does not kill
   and reap the child on that exception. The subsequent `waitpid` is skipped.
   Group termination is performed for sentinel/timeouts and admission failure,
   not every unwinding path. `launch_script.run_script_phase` also has no
   owned-group teardown contract, and changing `subprocess.run` to `Popen` +
   `wait` does not supply one. A signal sent just to the launcher can thus
   return the checkout and remove the lock while the child still works.
   Specify termination/reaping (including surviving group members) before
   checkout return and release, or conservatively retain the lock and withhold
   checkout mutation when shutdown cannot be proved. Test PID-targeted SIGTERM
   and SIGHUP, exceptions while waiting, scripts, and a leader that exits while
   a descendant remains. Terminal Ctrl-C alone is insufficient evidence.

3. **P1 — Recovery can incorrectly pronounce an unrecorded worker dead.**
   Recording only *after* fork leaves a supervisor-SIGKILL window with valid
   metadata and an empty `children` list. Recovery then approves release when
   the supervisor/group are gone even though the new PTY session survives.
   The design acknowledges invisibility but does not make the recovery command
   refuse that uncertainty. Also, its claim that nested workers stay in the
   recorded group is false: `repl_supervisor.run_with_done_marker` calls
   `pty.fork`, creating a separate session even in a witness-bearing nested
   CLI, whose child notes would deliberately be ignored. Removing a child
   record immediately after reaping its leader loses surviving-group evidence
   as well. Define a pre-spawn uncertain state or held-child handshake and a
   policy for nested spawns and remaining groups; incomplete evidence must
   require manual confirmation rather than a successful automatic dead verdict.
   An existing conservative pattern is
   `src/coga/recurring_runner.py::_run_repo_recurring`'s `starting` marker
   before spawn and `_terminate_repo_recurring_process`'s group checks.
   Add deterministic kill-at-spawn-window and nested-child-survival cases.

4. **P1 — Child metadata updates can overwrite a newer owner's lock.**
   `Children are recorded` specifies `os.replace` followed by a session check.
   After manual removal and acquisition by B (acceptance case 18), A's next
   child-start/exit update replaces B's file with A's metadata; its post-write
   check then succeeds. The guard serializes this overwrite but cannot make it
   correct. Require format/session verification of the current file *before*
   replacement, inside the same guard, and refuse to recreate a missing lock.
   Add replacement tests for both child updates, not just final release.

5. **P1 — The acquisition cleanup boundary contradicts the interruption
   acceptance cases.** Acquire is explicitly outside `cli.main`'s `try`, yet
   its signal mask is restored inside acquire. A pending SIGINT can raise
   after successful link/registration and before the caller enters `try`;
   that caller's `finally` never runs. SIGTERM handlers installed only at the
   end of acquire leave a similar window. Compare the existing
   `repl_supervisor._defer_spawn_release_interrupts` contract: mask restoration
   occurs inside the surrounding cleanup handler. Put acquisition within an
   ownership-aware cleanup scope while separately preventing a losing or
   incomplete acquisition from sweeping. Cover interruption on unmask, after
   registration, and temporary-file cleanup failure, not just during `app()`.

6. **P1 — Manual recovery lacks the required race exclusion, and liveness
   fallbacks need conservative rules.** The unguarded `cat`/inspect/`rm`
   procedure can inspect A, then delete B after A releases and B acquires. It
   bypasses the exact-byte check and directory guard used by command recovery.
   For malformed files where the command refuses, require a stated quiescent
   maintenance procedure that stops all launchers and prevents new admission,
   or provide guarded recovery with explicit human confirmation. The liveness
   algorithm must also distinguish an unavailable boot ID from a proven
   different boot: `null != current_boot_id` is not reboot proof. Scripts and
   non-PTY children currently inherit a process group rather than create one
   (`launch_script.run_script_phase`, the non-PTY paths in
   `repl_supervisor.run_with_done_marker`), and the holder can share a group
   with its invoking tools. Do not prescribe `kill -TERM -<pgid>` as a generic
   remedy without proving that group is dedicated to this launch. Test unknown
   identities, shared groups, and recovery racing release/reacquisition.

7. **P2 — The stated safety rationale for other mutators is incorrect.**
   The notice says these commands do not move the checkout, but
   `src/coga/git.py::publish` calls `fast_forward_control`, which executes
   `git merge --ff-only` in the worktree holding control (including a different
   linked worktree). `_realign_control` can also run `read-tree -m -u` and
   `update-ref`. Lifecycle writers and the generic CLI sweep reach this path.
   The short `state_lock` does not protect an agent's branch switches or editor
   activity. Allowing outside mutators is an explicit proposed limitation,
   so broader exclusion is an owner choice; either accept and accurately
   document these checkout mutations or change their integration behavior.
   Remove the false notice and add a case for a foreign mutator while the
   holder is on control, including publication from another linked worktree.

8. **P2 — `init`/`uninstall` gating and the ignore-repair remedy do not match
   today's CLI.** `src/coga/cli.py::main` dispatches `uninstall` before alias
   expansion/the ordinary `try`; both commands intentionally tolerate broken
   config with `cfg=None`. `commands.init.init` also accepts a target path,
   so the ambient config is not necessarily the tree it will modify. A gate
   solely at the proposed acquisition point misses these paths. Define target
   root discovery independent of successful config parsing, including malformed
   locks, and how the check remains valid until destructive work completes.
   Separately, `coga init --update` does not exist: `commands.init.init` and
   the observed `coga init --help` expose only the path and `--user`. Replace
   the advertised recovery command with a verified repair procedure. Cover
   broken config, an explicit target in another directory, and the uninstall
   early-dispatch branch.

### Optional recommendations and owner choices

- Reusing exit 75 fits `cli.main` and
  `recurring_runner._sweep_stopping_exit`. Locking authoring and the current
  mutating `--prompt-report` path is consistent with the stated scope. Keep
  no automatic stale clearing. These are reasonable defaults for the owner
  to accept, not approvals issued by this review.
- Keep this one PR focused on admission and conservative recovery. The new
  shared module has real launch/CLI consumers, and a guarded recovery command
  has a plausible co-versioned transaction under `coga/extension-model`.
  Cross-platform liveness automation is optional; an unknown verdict and a
  safe manual procedure fit the requested small design better than extending
  it into a process monitor.
- Use real subprocess tests for the race/signal guarantees above; fake-only
  coverage cannot establish process-group or signal-mask behavior. Add the
  checkout witness to test environment isolation (`tests/conftest.py::LAUNCH_OWNED_ENV`,
  `tests/test_env_isolation.py`) without adding it blindly to
  `task_env.TASK_ENV_KEYS`, which `apply_task_env` intentionally scrubs.
  Exercise `cli.main`, since direct `CliRunner.invoke(app, ...)` bypasses the
  proposed admission boundary. Preserve the existing held-child admission tests.
- The contract/twin plan and required-bootstrap registration are appropriate.
  Existing ignore coverage is confirmed by `git check-ignore -v
  coga/.coga/launch.lock` (`coga/.gitignore:9`),
  `commands.update._HOST_GITIGNORE_BODY`, and the packaged `.gitignore`.
  Keep the already accepted two-Coga-roots limitation explicit.

Verification: source/test/contract inspection, frozen workflow checked against
`src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md`,
`coga init --help`, and the ignore probe above. `git diff --check` passed;
`coga validate --task launch-locks/checkout-exclusivity-lock` exited 0 with
installed-version-skew and large-blackboard warnings. A byte-prefix check
confirmed the review was appended without changing prior ticket content.
No implementation or test-suite run was performed; no code, branch, or PR was produced. Ticket body and prior
blackboard sections remain unchanged. Next step is the owner `review-design`
gate, which resolves findings and records dispositions.
