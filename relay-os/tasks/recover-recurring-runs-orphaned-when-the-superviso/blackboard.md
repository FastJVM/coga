The blackboard is a notepad to be written to often as the human and agent works through a task.

## Final design (2026-06-05, with nick) — SIMPLE: no liveness detection

After iterating, nick steered to the minimal design. **No heartbeat, no
staleness heuristic, no `relay recover` command.** Just stop skipping
`in_progress` and relaunch/resume it.

Rationale: `relay recurring` is a foreground command run by hand in a shell —
no daemon, no concurrent sweep in normal use. So an `in_progress` recurring
period task at scan time can only be a *past* dead sweep's orphan. Relaunch and
resume its step. Worst case a false relaunch redoes some work → the human
catches it (cheap, recoverable). Not worth a detection mechanism.

The rule:
- `done`        → skip (finished work never re-runs; "done vs incomplete" is
                  just status — a crashed run never reached `mark done`).
- `in_progress` → relaunch and **resume the current step** (only behavior change).
- `active`      → launch as today.   `paused` → still skip (human parked it).

Accepted tradeoff: sequential re-run (human catches a dup). Out of scope:
concurrent stomp (only if two sweeps run at once — a future cron ticket).

Workflow = `code/with-review` (implement → peer-review → open-pr → human review).

### Key grounding facts (from reading source)
- `recurring.py:102` `DueTask.launchable` = `status == "active"` only → the trap;
  widen it (or `DueScan.due`) to include `in_progress`.
- `scan_due` get-or-creates the existing period task (`scaffold_template`
  returns the existing dir) → no duplicate task dir on relaunch.
- `commands/recurring.py` `_launch_scaffolded` today only launches `active` →
  the launch path must accept an `in_progress` ticket and re-compose from its
  current `step:`. Confirm/ wire this.
- Period slug + template-blackboard ledger already make per-period status
  authoritative → no new ledger needed.

### Scope guard
Resume the crashed *step*; cleaning up half-written artifacts (the motivating
incident leaked a digest spool + failed auto-push) is the resumed step/agent's
concern, not this ticket's.

### Superseded
The earlier "automatic reclaim + heartbeat marker file" design (and the two
AskUserQuestion picks behind it) was dropped in favor of the above. The
**Evaluator review** below was written against that heartbeat design, so its
points about markers / `.gitignore` / pid-vs-beat / thresholds are now moot —
keep it only for the few still-relevant notes (launch path only resumes via
`step:`; worktree partial-state is punted; key off the `tasks/<slug>/` dir not
the template).

## Contexts attached
- `relay/recurring` — the system being changed.
- `relay/architecture` — "status is the signal" / no-mutex constraint the
  reclaim bends. Implementer needs it to judge the tradeoff.

## Evaluator review

(Independent fresh-eyes review of the filled ticket, verbatim.)

This confirms a critical gap: `sync_task_state` does `git add` the whole task dir pathspec. A marker file inside the task dir would get staged and committed unless `.gitignore` excludes it. `git add -- <taskdir>` respects `.gitignore`, so the ignore entry is load-bearing. But the ticket only says "task dirs are committed, so the marker must be ignored" — it doesn't flag that `relay launch` itself flips the ticket to `in_progress` and commits the task dir at launch start, which is the exact moment the marker would be written. I have enough to write the evaluation.

### Evaluation: `recover-recurring-runs-orphaned-when-the-supervisor` ticket

#### Description clarity — strong, with two unstated decisions
- The problem statement is unusually clear and grounded in a real 2026-06-04 incident. A cold agent can understand the failure mode (supervisor process tree SIGKILLed mid-sweep, orphan frozen `in_progress`, sweep skips it forever) without prior context.
- The "what we want" / "chosen approach" split cleanly separates problem from design, and both design forks (automatic-reclaim vs explicit-command; heartbeat-marker vs mtime) are stated as *decided*, which is exactly what an implementer needs.
- Missing decision 1 — **threshold value is undecided.** The text says "older than a threshold," "anchored above… 900s," "~2× that window," "should be configurable (env override)." That is a range and an intent, not a number. The implementer must pick the default (1800s? a multiplier of `_RECURRING_IDLE_TIMEOUT_SECONDS`?) and the env var name. Worth nailing down before launch, since it directly governs false-reclaim risk.
- Missing decision 2 — **marker refresh cadence / `beat` semantics.** It says "refresh it while alive (it already wakes every `_SENTINEL_POLL_INTERVAL`)" — that is 0.25s, far too hot to rewrite a file on every wake. The implementer needs a separate, coarser beat interval. Unstated.

#### Workflow fit (code/with-review) — correct
- This is a real multi-file code change (`repl_supervisor.py`, `recurring.py`, `commands/launch.py`, `.gitignore`, context docs). Peer review plus PR is the right shape. No mismatch. The change has subtle concurrency/cross-machine reasoning that genuinely benefits from a second agent's review, so the workflow is well-chosen rather than over-heavy.

#### Attached contexts — both relevant, key facts correctly copied into `## Context`
- `relay/recurring` is directly on-point (period slug, ledger, the skip behavior the reclaim modifies).
- `relay/architecture` is the right attach because the design knowingly bends "Status is the signal." The ticket's `## Context` block correctly *names* the specific load-bearing facts ("no mutex; status is the only coordination signal") rather than leaving them buried in a broad context — this is the right call given how large `relay/architecture` is.
- One context-vs-copy nit: `relay/architecture` is ~290 lines covering far more than the reclaim touches. The single fact the implementer must hold ("there is no filesystem mutex; status is the only signal") is already paraphrased in `## Context`, so the attach is somewhat redundant for the reader — but it's the right safety net for the reviewer. Acceptable.

#### Scope — reasonable, well-bounded, single ticket
- Scope is explicitly bounded: reclaim resumes the *step*; cleanup of half-written artifacts (the leaked digest spool) is declared the resumed agent's concern, not this ticket's. That is the correct boundary and prevents this from swelling into a cleanup-orchestration ticket.
- The sibling ticket (`supervisor-liveness-watchdog…`) is correctly carved off as the inverse case (live supervisor, wedged agent). No bundling. This is one ticket's worth of work.

#### Technical soundness — design largely holds, but several real gaps

**Claims about the code that check out:**
- `run_with_done_marker` is indeed the right write/refresh/remove site, and it already has a select loop that wakes periodically. ✓
- The task dir is **already in scope** at the call site (`launch.py:420` passes `session_id=str(ref.path.resolve())`) — so "threading the task dir into `run_with_done_marker`" is nearly free; the function just needs a new `task_dir` param, or it can reuse the resolved session path. The ticket slightly overstates this as a plumbing concern; it's a one-arg addition. ✓ (minor over-claim)
- `DueTask.launchable` returns `status == "active"` and the `in_progress` skip is exactly there — the reclaim point is correctly identified. ✓
- `_RECURRING_IDLE_TIMEOUT_SECONDS = 900` and the `RELAY_REPL_IDLE_TIMEOUT` override pattern exist as described. ✓

**Gaps / risks the ticket under-weights:**
1. **The marker-write site only fires for `mode == "interactive"`.** `run_with_done_marker` is called *only* in the interactive branch of `launch.py` (line 409); `auto`/`script` go through `subprocess.run` with no marker. The recurring sweep launches interactive REPLs, so this happens to cover the motivating case — but the marker lifecycle is coupled to interactive mode, not to "is a recurring period task running." Also, `run_with_done_marker` early-returns to `subprocess.run` when `stdout` is not a TTY (line 148), writing no marker. So a recurring task that crashes in any non-TTY/non-interactive context leaves *no* marker, and the reclaim must fall back to "no marker at all = ?". The ticket's liveness logic only defines dead-vs-live for tasks that *have* a marker; it doesn't say what a stale `in_progress` with **no marker file** means. That's the most common-looking orphan and it's underspecified.

2. **`.gitignore` is necessary but the ticket understates *why it's load-bearing and timing-sensitive*.** `git.sync_task_state` does `git add -- <taskdir>` (confirmed `git.py:91,179-184`), and `relay launch` commits the task dir when it flips `active → in_progress` *at launch start* — the same instant the marker is written. If the ignore entry is missing or the marker path doesn't match it, the marker gets committed and **pushed to the control branch**, then synced to other machines, poisoning the cross-machine `pid`/`host` logic with a foreign live-looking marker. The ticket lists `.gitignore` as a bullet but frames it as tidiness ("machine-local runtime state"); it's actually correctness-critical for the cross-machine fork. Recommend the implementer verify the ignore pattern works under `git add -- <pathspec>` (a bare filename like `.relay-run.json` in `.gitignore` will match; a rooted `/.relay-run.json` will not).

3. **Marker removal on SIGKILL — the `finally` block does not run.** The design relies on "clean teardown removes the marker; SIGKILL leaves it stale." Correct — but note `run_with_done_marker`'s own `finally` (lines 285-307) runs on *normal* teardown (done-signal, self-exit, even SIGTERM-from-watcher). When the **outer** supervisor is SIGKILLed (laptop sleep kills the whole tree), neither the `finally` nor any atexit runs, so the marker correctly persists. Good — but the implementer must put marker removal in that `finally`, AND must *not* remove it on the SIGTERM/idle-timeout path in a way that erases a legitimately-orphaned marker. Edge: idle-timeout teardown (watcher SIGTERMs a *live-but-stalled* agent) will run the `finally` and delete the marker — that's fine because the task is being torn down cleanly, but it intersects with the sibling watchdog ticket; worth a comment.

4. **Concurrency claim is optimistic.** "A fresh launch rewrites the marker at start, so a reclaim won't relaunch something another sweep just picked up." There's still a TOCTOU window: scan A reads a stale marker and decides to reclaim; before A relaunches, scan B also reads the same stale marker and decides to reclaim; both relaunch. The marker is advisory (correctly stated), so the real backstop is `status` flipping to `in_progress` on launch — but two near-simultaneous reclaims both see `in_progress` (the *stale* one) and both proceed. Without a mutex this is the known accepted failure (two divergent workers, recoverable in git), but the ticket presents the marker-rewrite as if it closes the race. It narrows it; it doesn't close it. Fine given the no-mutex philosophy, but the claim should be softened so the implementer doesn't over-trust it.

5. **`pid` reuse on same host.** `os.kill(pid, 0)` succeeding only means *some* process holds that pid, not *our* supervisor. After a reboot/sleep cycle, pid 48213 may belong to something unrelated → the liveness check reports "alive" → orphan never reclaimed. The `beat` staleness check is the saving fallback, but then the `pid` check adds little on the same host and mostly creates false-live readings. The host gating handles cross-machine; the pid-reuse-after-reboot case argues for treating `beat` as primary and `pid` as a fast-path only. The ticket treats `pid`-dead and `beat`-stale as equal "EITHER" conditions; `pid`-*alive* should probably **not** override a stale `beat`.

#### Assumptions to question before launch
- That `in_progress` recurring period tasks are reliably distinguishable from the parent recurring template state — confirm the reclaim keys off `relay-os/tasks/<name>-<period_key>/` tickets, not the `relay-os/recurring/<name>/` template (the ledger lives in the template blackboard; the orphan lives in tasks/). The ticket says this but the implementer must not conflate them.
- That "resume its current workflow step" works for `code/with-review`: relaunching an `in_progress` ticket re-composes from `step:` — but the crashed `implement` step may have left a half-finished feature *worktree* on another branch. Resuming the step is fine for the conversation; the worktree/branch state recovery is exactly the "partial side effects" the ticket punts on. Confirm that punt is acceptable for the worktree case specifically (the ticket only names the digest-spool case).
- That the threshold anchored at "2× idle-timeout" is safe when an operator has *raised* `RELAY_REPL_IDLE_TIMEOUT`: the reclaim threshold must derive from the same effective timeout, not the hardcoded 900s, or a long-running attended session could be falsely reclaimed.

#### Bottom line
A well-written, correctly-scoped ticket that a cold agent can start from. The heartbeat-marker + automatic-reclaim design is sound in shape and the code references are accurate. Before launch, pin down: (a) the threshold default + env var name + beat cadence, (b) what a stale `in_progress` with **no** marker means (the common non-TTY/auto case the marker doesn't cover), (c) confirm the `.gitignore` pattern actually excludes the marker under `git add -- <pathspec>` since the launch-time auto-commit will otherwise push it cross-machine, and (d) soften the concurrency and `pid`-liveness claims so the implementer treats `beat` staleness as primary.
