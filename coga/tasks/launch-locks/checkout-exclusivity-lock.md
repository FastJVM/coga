---
title: Checkout exclusivity lock
status: active
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
step: 1 (design)
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
