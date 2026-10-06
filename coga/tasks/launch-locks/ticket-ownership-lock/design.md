<!-- Moved from the blackboard of launch-locks/ticket-ownership-lock on 2026-10-06 (large-blackboard remedy, coga/blackboard). Verbatim. -->

## Design (step 1, 2026-10-01)

Owning contract topic: **new `coga/internals/ticket-locks`**
(`docs/contexts/coga/internals/ticket-locks/SKILL.md`, plus its packaged twin
`src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/ticket-locks/SKILL.md`
and an entry in `tests/test_packaging.py` `REQUIRED_BOOTSTRAP_CONTEXT_REFS`, the
way every other `coga/internals/*` topic is listed). Code home: new
`src/coga/ticket_lock.py` (shared infra: launch, megalaunch, the publish guard,
delete, validate/status, and `coga unlock` all consume it).

### Problem

Today "status is the signal" (`coga/launch`): nothing stops two clones, or two
machines, from launching the same ticket. Megalaunch's `launch_generation`
claim is a per-spawn CAS on ticket bytes, not a hold across a launch;
`git.state_lock` serializes one checkout only. The first concurrent worker
learns of the second only when its publish is refused by provenance, after
work is done. We want one launch per ticket at a time, visibly, across clones
and machines, with crash recovery that never admits two workers.

### Core idea

A claim is a small file **on the control branch**, beside the ticket. It is
acquired by a compare-and-set publish that requires its absence on control and
released by a compare-and-set publish that requires its exact bytes. Control's
ref update (the server's push decision) is the only arbiter; local files never
decide. Liveness evidence that only the holding machine can read stays in the
ignored `.coga/` runtime dir and is never published.

### Acceptance criteria

- [ ] Lock path is `<tasks>/<parent>/<slug>.lock` for both forms: beside
      `<slug>.md` (file form) and beside the `<slug>/` directory (directory
      form), never inside the task directory. `tasks.list_tasks`,
      `git._ticket_rels`, and `DuplicateTaskSlugError` are unaffected (non-`.md`
      file, not a directory). A file↔directory conversion keeps the same lock
      path. Helper `ticket_lock.lock_path(cfg, ref)` is the only constructor.
- [ ] Claim content is UTF-8 JSON, `indent=2`, sorted keys, trailing newline,
      exactly: `format` (`"coga-ticket-lock/1"`), `ticket` (id_slug),
      `session` (uuid4), `previous_session` (uuid or null), `host` (machine id
      or null), `hostname`, `boot_id` (or null), `pid_ns` (or null), `pid`,
      `pid_start` (platform start marker or null), `checkout` (resolved
      `cfg.repo_root`), `user` (OS user), `started_at` (UTC ISO-8601),
      `launch` (`"launch"` | `"megalaunch"` | `"recurring"`), `argv` (the
      `coga` argv). Exact bytes are the identity: release and replace pin them.
- [ ] **Acquire** (Git sync available): before any lifecycle write, script run,
      agent-skill rebuild, or prompt composition, launch writes the local
      session record (below), then publishes the claim with
      `expect={lock: None}` and the new `content=` override (below),
      `strict`. Outcomes:
      - pushed (`True`) → held; fast-forward makes the file visible in a control
        checkout.
      - `False` (control already holds those exact bytes) → held (idempotent).
      - `StateRegressionError` (control has a claim) → go to *Existing claim*.
      - `GitError` (definitely not on control) → refuse, delete local record,
        exit 75, nothing started.
      - `UncertainPublishError` → refuse, keep the record marked
        `acquire-uncertain`, exit 75, nothing started. The next launch of that
        ticket from this checkout resolves it (control holds our bytes → our
        dead claim → *Existing claim*; absent → drop record).
      - soft-skip `None` because the control branch is missing → refuse exit 2
        with `control_branch_mismatch_message` (never silently degrade).
- [ ] **Existing claim** on control, decided in this order:
      1. Same `session` as this process's env witness → refuse "already held by
         the enclosing session" (nested `coga launch`).
      2. Holder proven dead (proof below) and its recorded checkout has no
         unpublished state for this task → **adopt**: CAS-replace with
         `expect={lock: old_bytes}`, `content={lock: new_claim}` carrying
         `previous_session`. Two recoverers race on the same `old_bytes`; only
         one push lands, the loser sees `StateRegressionError` and re-enters this
         decision against the new claim (which is live).
      3. Holder proven dead but its recorded checkout (same host) has dirty or
         unpublished paths under the task → refuse, naming that checkout:
         "launch from there to publish and release".
      4. Otherwise (live, or uncertain, including any other host) → refuse
         exit 2 naming hostname, checkout, pid, `started_at`, session, why
         liveness is uncertain, and the explicit break command.
- [ ] **Liveness proof** (`ticket_lock.holder_state(claim) -> live | dead |
      uncertain`). Dead is proven only on the same host
      (`host` and `pid_ns` both equal and non-null):
      - `boot_id` differs → dead (every process from that boot is gone).
      - Same boot: the supervisor (`pid`, `pid_start`) is gone or its start
        marker differs; **and** every child in the local session record is gone
        (pid absent or start differs) **and** no live process has that child pid
        as its process group/session id (`pty.fork` makes the agent a session
        leader; grandchildren keep that pgid); **and** (Linux) no live process of
        this user carries `COGA_TICKET_LOCK_SESSION=<session>` in
        `/proc/<pid>/environ`. The env scan closes the fork-to-record window
        and catches a surviving agent after an external SIGKILL of the
        supervisor.
      - Anything unreadable (no record, no start marker, non-Linux with a
        record still in `spawning`, different host or pid namespace, null host)
        → **uncertain**. A matching pid alone, a matching owner/user, or the
        claim's age never prove anything.
      - Start marker: Linux `/proc/<pid>/stat` field 22 (ticks since boot),
        host `/etc/machine-id`, `boot_id` from
        `/proc/sys/kernel/random/boot_id`, `pid_ns` from `readlink
        /proc/self/ns/pid` (containers sharing a machine-id cannot prove each
        other dead). macOS: `kern.proc.pid` start time, `IOPlatformUUID`,
        `kern.bootsessionuuid`, `pid_ns` = `"darwin"`. Any other platform: null
        → uncertain.
- [ ] **Local session record** `<cfg.repo_root>/.coga/ticket-locks/<session>.json`
      (ignored via the existing `.coga/` rule from
      `commands/update.ensure_host_gitignore`): the claim bytes, `state`
      (`acquiring` | `acquire-uncertain` | `held` | `spawning` | `releasing` |
      `release-uncertain` | `release-withheld`), and `children` (pid,
      start marker) appended immediately after each `pty.fork`/`os.fork` in
      `repl_supervisor` and each `ticket.py` `Popen` in `launch_script`.
      Written with write-temp-then-`os.replace`. Deleted after a confirmed
      release. Never swept, never published.
- [ ] **Hold span.** One claim per `coga launch <task>` invocation: acquired
      once after the checkout boundary re-resolves the canonical ref, held across
      `ticket.py` phases, every chained agent step, between-phase settles, and
      released after the final `return_checkout()` and before `_launch`
      returns to `cli.main` (so before the end-of-command sweep).
      Implementation: a context manager wrapping the body of `_launch` from the
      acquisition point, so every `_bail`, `SystemExit`, `KeyboardInterrupt`,
      and normal return passes through release.
- [ ] **Release.** Precondition: every path of the task (file-form `.md`, or
      every file under the directory) is byte-equal on control (no
      unpublished task state). If not, one `git.sync_task_state(strict=True)`
      as holder; if still not equal → **withhold**: keep the claim on control,
      mark the record `release-withheld`, print the paths and "rerun `coga
      launch <ref>` here to publish and release", keep the command's exit
      status. Otherwise CAS-delete: `content={lock: None}`,
      `expect={lock: claim_bytes}`. Outcomes: pushed → released, delete record; `StateRegressionError` (claim was
      replaced or broken) → report "this session's claim was replaced by
      <session>", delete record, never touch the new claim; `GitError` /
      `UncertainPublishError` → record `release-uncertain`, warn, keep exit
      status. The next launch of that ticket from this checkout finds our dead
      claim and adopts it (so recovery does not wait for a collector).
- [ ] **Holder-only ticket writes (stale-session rejection).** `git._guard`
      gains a check for every candidate under a task path: read control's lock
      blob for that task at `base`. If a claim exists and the publishing
      process does not hold that exact session → refuse
      (`StateRegressionError`, "ticket <ref> is held by session S on <host>
      since T"). A process that believes it holds session S but control shows a
      different claim, or none, is refused too ("this session's claim was
      replaced/removed"). The publishing process's identity is the in-process
      holder registry (`ticket_lock.held_session(ref)`) or, for child
      processes, env `COGA_TICKET_LOCK_SESSION` + `COGA_TICKET_LOCK_TICKET`.
      Effects: a broken-then-revived old worker's writes stay local; another
      clone's sweep, `mark`, `block`, `unblock`, `delete`, or authoring of a
      held ticket is refused until release. The refusal leaves files as
      written, per the existing best-effort/strict rules.
- [ ] **Env witness.** The launch passes `COGA_TICKET_LOCK_SESSION` and
      `COGA_TICKET_LOCK_TICKET` to every agent child (through the env built for
      `spawn_agent_session`) and every `ticket.py` child (`launch_script` keeps
      them; it pops only `COGA_SUPERVISED`, the sentinel, and the expected-step
      vars). `os.environ` of the supervisor is never mutated.
- [ ] **Lock paths are never ordinary state.** In `git._candidates`, a lock
      path is a candidate only when it is in `content` (exact-bytes publish);
      otherwise it is dropped. So `sync_coga_state`, `sync_task_state`, and
      authoring finalization never carry a lock file, stale or not. With
      `content`, the working tree is never written first: `git.publish` gains
      `content: Mapping[Path, bytes | None]` — "land these exact bytes;
      each such path must also be in `expect`" — overlaid in `_build_tree` and
      forced into the candidate set; `fast_forward_control` then materializes
      (or removes) the file in a control checkout. Consequence: no dirty lock
      file ever blocks `git.prepare_control_checkout` or the sweep.
- [ ] **delete / Retro / moves.** `delete_task.run_delete_task` and `coga
      delete` refuse when control or the worktree holds a claim for the task,
      unless this process holds it (the holder's later release still CAS-removes
      it). Deletion never removes a lock file. There is no move command;
      a manual `git mv` of a held task orphans the claim (documented
      limitation). `coga validate` reports an orphan lock (no task at its ref)
      and malformed claims; it never deletes them.
- [ ] **Explicit break and cleanup: `coga unlock <ref> --session <uuid>`.**
      CAS-removes exactly that claim (`expect` = control's current bytes, which
      must carry that session). Refuses when the holder is proven live locally.
      For `uncertain` it requires the exact `--session` (the human asserts the
      other worker is gone; copy it from the refusal). Never touches a newer
      claim. Works on done/canceled/deleted (orphan) tickets. `coga launch` has
      no takeover flag: break, then launch.
- [ ] **Inspection.** `coga status` (no network: local HEAD/working tree only)
      marks a held task with holder hostname, session prefix, and
      `started_at`; `coga show <ref>` prints the claim. The file itself is
      readable on any control checkout.
- [ ] **Local-only mode.** `[git].enabled = false` or not a Git repo: the
      claim is created in the working tree with `O_CREAT|O_EXCL` (one notice
      line: "ticket lock is local to this checkout; other clones are not
      excluded"), removed at release by verifying exact bytes then unlinking.
      Same liveness/adoption rules against the local file. Remote-less repo:
      ordinary path — `publish` commits on local control through
      `fast_forward_control`'s `update-ref <ref> <new> <old>`, which is the CAS
      between worktrees of that repo.
- [ ] **Megalaunch.** `megalaunch._launch_until_stop` acquires the ticket lock
      (`launch: "megalaunch"`) once, before the first `_preflight_agent_launch`
      / activation claim, and releases in a `finally` at its return, after its
      last settle. The per-step `pending:`/admitted/`released:` generation
      protocol is unchanged and nested inside the hold: claim, admission, and
      `_restore_ticket_bytes` are holder writes. A held lock is a new skip
      reason in `_candidate_result` ("held by <host>/<session>"), never a
      failure of the sweep. `git.ticket_regression_reason` is unchanged and runs
      before the holder check; both must pass.
- [ ] **Released-witness and pending recovery.** A megalaunch killed after
      release leaves its dead claim on control plus the local `released:`
      witness. `coga launch` acquires first (adopting the dead same-host
      claim), then runs `_reconcile_released_launch_admission` as holder. A
      retained `pending:` claim keeps refusing launch as today; its ticket lock
      stays until the human reconciles and runs `coga unlock`.
- [ ] **Recurring periods** take the lock exactly like ordinary launches
      (`launch: "recurring"`), including `ticket.py`-only periods and the
      period whose `delegate:` dispatches a bootstrap target; the bootstrap
      target itself takes none. **Bootstrap targets**, `--prompt-report`, and
      `coga ticket` creating a new ticket take no lock. `coga ticket` on an
      existing ticket refuses up front when it is held (see Open Questions).
- [ ] **Exit codes.** Held by another session (live/uncertain) or nested → 2.
      Unreachable or uncertain acquisition → 75 (retry, no sweep). Either
      refusal after checkout entry still runs `return_checkout()` first.
- [ ] Contracts and twins updated in the same PR: new
      `coga/internals/ticket-locks`; `coga/launch` "Status is the signal"
      rewritten (one lock per ticket; status still says *what* step),
      plus Agent preflight order and Options/exits; `coga/internals/launch-claims`
      (megalaunch holds the ticket lock around its claims; state_lock still not
      ownership); `coga/internals/claim-recovery` (acquire before
      reconciliation; dead-claim adoption); `coga/internals/state-publication`
      and `coga/internals/git-regressions` (`content=`, lock candidates,
      holder refusal); `coga/tickets` (lock path is not a task);
      `coga/megalaunch` (skip reason); packaged twins of each.

### Proposed shape (order of work)

1. `src/coga/ticket_lock.py`: `lock_path`, `Claim` (render/parse exact bytes),
   process identity (`host_identity()`, `process_start(pid)`), `holder_state`,
   session record IO, the holder registry, `acquire(cfg, ref, *, launch)` →
   `HeldLock` context manager, `release`, `replace`, `unlock`. Pure functions
   first; unit tests with fake `/proc` roots.
2. `src/coga/git.py`: `publish(..., content=)`; `_candidates` lock filtering;
   `_guard` holder check (needs `ticket_lock` only for parsing/registry, keep
   the import one-way: `ticket_lock` → `git` for publish, `git` → a small
   `ticket_lock` parse/registry API without cycles — put parse + registry in
   `ticket_lock` and import lazily in `_guard` if needed).
3. `commands/launch.py` `_launch`: acquire right after the boundary's
   canonical re-resolution (exempt launches: right after resolution), before
   `_reconcile_released_launch_admission`, delegation routing, assist
   alignment, script discovery, activation; wrap to release after
   `return_checkout()`. Env witness into `spawn_agent_session`'s child env and
   `launch_script.run_script_chain` children; child roster hooks in
   `repl_supervisor` (`after_fork` callback) and `launch_script`.
4. `megalaunch._launch_until_stop` hold + skip reason.
5. `delete_task`, `commands/delete.py` refusal; `validate` orphan/malformed;
   `status`/`show` display; `commands/unlock.py` + registration.
6. Contexts + twins; `example/` fixture untouched unless a seeded lock is
   needed for the status display test.

### Out of scope

- The checkout-exclusivity sibling (`launch-locks/checkout-exclusivity-lock`).
  Composition when both ship: checkout lock acquired first (in `cli.main`,
  before entry sweep), ticket lock second (after preparation). Release ticket
  lock inside `_launch`, then the `cli.main` sweep, then the checkout lock. A
  checkout-lock refusal means the ticket lock is never attempted. A ticket-lock
  refusal returns the checkout and exits; the outer checkout lock releases in
  its own `finally`. A withheld/uncertain ticket release never prevents the
  checkout-lock release (the ticket claim is independent evidence on control).
- The daily stale-claim collector (follow-up ticket; see Open Questions).
- Combining the acquire commit with megalaunch's first claim commit, or the
  release with the final state publication (later optimization).
- Protection against manual Git writes, editors, `git mv`, external side
  effects of a broken-but-alive worker (pushed branches, PRs, Slack posts),
  or any non-Coga writer. The holder check only gates Coga's publish path.
- Any lease/heartbeat/expiry. Age never clears a claim.

### Concurrency / crash acceptance scenarios

Each becomes a test (two clones sharing a bare remote; fake process tables for
liveness) unless marked *manual*.

1. Two clones launch the same ticket simultaneously → exactly one push lands;
   the other gets `StateRegressionError`, sees a live claim, exits 2, starts
   nothing, writes no lifecycle state.
2. Two clones launch different tickets → both acquire; neither blocks.
3. Same checkout, second terminal launches the held ticket → refused exit 2
   (holder pid live).
4. Nested `coga launch` of the same ticket from inside the session → refused
   "already held by the enclosing session".
5. Normal chained run across a `ticket.py` phase and two agent steps → one
   acquire commit, one release commit; claim present on control throughout.
6. Agent runs `coga bump`/`block`/`mark done` → holder writes publish; session
   ends; release lands after final state.
7. Ctrl-C in the REPL and in a `ticket.py` phase → release runs.
8. Preflight refusal after acquisition (missing CLI, secret, push auth) →
   claim released; ticket bytes unchanged.
9. Acquisition push fails definitely (remote down) → exit 75, no claim, record
   removed.
10. Acquisition uncertain → exit 75; next launch: claim on control with our
    bytes → dead (pid gone) → adopted; claim absent → fresh acquire.
11. Supervisor SIGKILLed, agent child survives → relaunch on same host: env
    scan / pgid finds the child → uncertain/live → refused; after the child
    exits → adopted with `previous_session`.
12. Supervisor SIGKILLed between fork and roster append → Linux env scan sees
    the child → refused. (Non-Linux: record `spawning` → uncertain → manual.)
13. PID reuse: dead supervisor's pid now belongs to an unrelated process with a
    different start marker → not live; proof continues to the children.
14. Reboot (same host, new boot_id) → dead → adopted.
15. Claim from another machine, worker actually dead → refused with holder
    details; `coga unlock --session` removes exactly that claim; relaunch
    acquires.
16. Claim broken from machine B while worker on A still runs → A's next
    `bump`/sweep/final publish is refused ("claim replaced"); A's work stays
    local; A's release does not delete B's claim.
17. Two recoverers on the same host adopt the same dead claim simultaneously
    → one CAS wins; the other refuses against the now-live claim.
18. Release refused because ticket state could not be published → claim kept,
    `release-withheld`; relaunch in the same checkout adopts, publishes, and
    releases.
19. Release push uncertain → record `release-uncertain`; relaunch adopts or
    finds it absent.
20. Unrelated `coga` command in another clone with a stale dirty copy of the
    held ticket → sweep refused by holder check; lock file never swept.
21. Local stale lock file (e.g. leftover in a feature checkout) → never
    published by the sweep; `prepare_control_checkout` not blocked.
22. Megalaunch picks a held ticket → skipped "held", sweep continues.
23. Megalaunch killed after child release (released witness) → `coga launch`
    adopts the dead claim, reconciles, resumes.
24. `coga delete` / Retro on a held task → refused; on an unheld one,
    unchanged.
25. Different container sharing machine-id → pid namespace differs →
    uncertain, never "dead".
26. `[git].enabled = false` → `O_EXCL` local lock; second launch in the same
    checkout refused; notice printed.
27. Remote-less repo with two worktrees → `update-ref` CAS on local control
    admits one.
28. Missing control branch → exit 2 with the config message, no local-only
    fallback.
29. With the checkout lock (when it ships): checkout-lock refusal → no ticket
    acquire; ticket-lock refusal → checkout returned, checkout lock released.
