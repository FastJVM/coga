---
title: Ticket ownership lock
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
- coga/internals/launch-claims
- coga/internals/claim-recovery
- coga/internals/state-publication
- coga/internals/git-regressions
agent: claude
---

## Description

Design an independent per-ticket ownership lock that prevents concurrent launches of the same ticket across checkouts and machines. User direction: keep an inspectable lock file beside the ticket while a launch works on it, remove the claim when the launch finishes, and include metadata for garbage collection and safe crash/restart recovery. This deliberately revises the current no-task-ownership-lock contract.

Define placement for both directory-form and bare .md tickets without introducing duplicate task discovery. If the lock is shared through Git, acquisition must atomically claim absence on control and confirm publication before spawning; creating a local file alone cannot exclude another clone. Specify owner/session UUID, machine identity, process identity including a start marker, checkout path, and start time. Explain what proves a worker dead, what remains uncertain on another machine, and how restart adopts or replaces a stale claim without admitting two workers. A reused PID or matching owner is insufficient.

Hold ownership across script and agent phases, workflow bumps and chained steps, through final publication and release. Done means launch/session completion, including interrupted or refused teardown, not only terminal ticket status; preserve unpublished work during recovery. Define ambiguous acquire/release publication outcomes, compare-and-set removal of the exact claim, stale-session write rejection, and interaction with existing launch_generation and megalaunch claims. Do not promise protection against arbitrary external side effects or manual Git writes.

Evaluate a daily recurring collector for stale claims; never clear a potentially live worker solely because the claim is old. Immediate restart recovery must not depend on a daily job. Define local-only behavior when Git sync is unavailable.

Orthogonal sibling: launch-locks/checkout-exclusivity-lock protects a physical checkout, not ticket identity. This ticket must stand alone and permit different tickets in separate clones. When both ship, acquire the checkout lock first, then the ticket lock (the sibling already fixes this order); release in reverse order (ticket lock before the checkout lock, whose release follows the outer `cli.main` sweep); specify how a refusal of either unwinds the other. Include concurrency/crash acceptance scenarios and update owning contracts and packaged twins in the eventual implementation PR. The design requires owner approval before code. The design step is done when the design is on the blackboard (per `code/design`), ending with the concurrency/crash acceptance-scenario list, and names the `coga/internals/*` topic that will own the lock contract.

The design spec for this ticket lives on the blackboard below (`## Design`), as the step instruction above requires; `## Open Questions` there lists what the owner decides in `review-design`.

## Context

Owner priority: design and ship ticket ownership locking before checkout exclusivity; checkout collisions are considered uncommon. Keep the two deliverables independent.

The owner clarified "fast git sync" means immediate lock acquisition/release publication, not general state-sync performance work. Publish the claim immediately and confirm acquisition on control before work starts; publish removal immediately when the launch finishes. Do not depend on delayed sweeps. Failed or uncertain acquisition must not start work; failed release must remain visible for reconciliation. Fast publication alone is not mutual exclusion: simultaneous claims still require an atomic remote decision.

Contract being revised: `coga/launch` (`docs/contexts/coga/launch/SKILL.md`, "Status is the signal") currently says there is no task-ownership mutex and that megalaunch's claim and `git.state_lock` are not ownership locks. The implementation PR rewrites that paragraph and the related lines in `coga/internals/launch-claims` and `coga/internals/claim-recovery`.

Code anchors (cite by symbol; line numbers drift):

- `git.publish` with `expect={path: bytes | None}` (`None` = must not exist on control) and `guard=` is the existing atomic compare-and-set against control; the lock's acquire and exact-claim release should build on it rather than invent a new remote primitive.
- `git.ticket_regression_reason` holds the `pending:`/`released:` launch_generation seal rules; `launch._reconcile_released_launch_admission` is the existing released-witness recovery path. Define how the ownership lock composes with both.
- `git.state_lock` is the short-lived, per-checkout, reentrant `flock`; keep it separate and do not lengthen it.
- `git.fetch_control` and `git.sync_task_state` are the fetch and strict-publication helpers.
- `tasks.list_tasks` / `tasks.resolve_task` own discovery (see placement facts below).

Cited, not attached — `coga/tickets` (`docs/contexts/coga/tickets/SKILL.md`, "Where tasks live and how they are named"). Placement facts: `list_tasks` walks `coga/tasks/` at any depth; a directory holding `ticket.md` is a task and is never recursed into; a bare `<slug>.md` is a file-form task; `<slug>.md` and `<slug>/` must not both exist (`DuplicateTaskSlugError`); `README.md` is never a task and `_`-prefixed names are skipped at every level; attachments are never composed, and only the exact sibling `ticket.py` changes dispatch. Moving a task orphans its log history under the old ref.

Cited, not attached — `coga/recurring/scheduling` (`docs/contexts/coga/recurring/scheduling/SKILL.md`), for evaluating the daily collector. Facts: templates live under `coga/recurring/` and materialize one stable task per template under `tasks/recurring/`; a `ticket.py` period runs headless and is the shape for unattended schedulers, while agent periods need TTYs; a scheduled agent run must reach `done` in one launch or the sweep pauses it; repo-inactivity skips templates unless `run_when_inactive: true`; the shipped daily `autoclose-merged` template chains registered `coga run` recipes from its `ticket.py`.

Sweep interaction (main gap from the authoring review): `git.sync_coga_state`, the end-of-command sweep, publishes every dirty path under the tasks directory. A lock file beside the ticket would therefore be pushed by any unrelated `coga` command in any clone, including an unconfirmed, stale, or deleted claim. The design must state whether the sweep, `delete-task`/Retro, and moving a task skip, carry, or refuse lock paths.

Cited, not attached — `coga/internals/agent-spawn` (`docs/contexts/coga/internals/agent-spawn/SKILL.md`): read it for supervisor death with a surviving agent child, which crash recovery must handle (the sibling attaches it for the same case).

Open design questions:

- Is the cost of two extra control commits/pushes per launch, and refusing to start when control is unreachable, acceptable?
- Under megalaunch, does the admission step or the child acquire the ticket lock, and how does that compose with the `pending:` seal?
- Do `coga ticket` authoring and recurring `ticket.py` periods take the lock?
- Does "local-only when Git sync is unavailable" also cover `[git].enabled = false` and remote-less repos?
- Should the daily stale-claim collector be a recurring template with a `ticket.py` (microkernel rule) rather than core code, and is it a separate follow-up ticket?

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

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

## Decisions (owner, attended design session 2026-10-01)

- Write guard: refuse **all** non-holder publications of a held ticket (Q2).
- Recurring periods take the lock uniformly; the two extra commits per run
  are accepted (Q1, recurring half).
- Daily collector is a **separate follow-up ticket** (Q5), not in this PR.

## Open Questions

Q2 and Q5 are decided above, as is the recurring half of Q1; the rest remain
for `review-design`.

1. **Cost.** Two extra control commits/pushes per launch (acquire, release),
   plus one fetch, and refusing to start when control is unreachable. Proposal:
   accept. Recurring periods add two commits each per run — accept, or exempt
   recurring because the recurring gate already admits one runner?
2. **Non-holder writes while held.** Proposal refuses every non-holder
   publication of a held ticket (another clone's `mark`/`block`/`unblock`/
   sweep, or a human in a second terminal), not just stale sessions. Stricter
   and simpler; the cost is that a human must wait or `coga unlock` before
   editing a running ticket through Coga. Alternative: only reject writers
   carrying a *different* session.
3. **`coga unlock` placement.** New top-level command (shared lock infra,
   package-private CAS invariant) vs. a `coga run` recipe. Proposal: top-level.
4. **`coga ticket` on an existing ticket**: refuse up front when held
   (proposal) or acquire the lock for the authoring session?
5. **Daily collector.** Proposal: separate follow-up ticket; a recurring
   template whose `ticket.py` calls `coga unlock --collect`, which releases
   only claims from *this* host proven dead with no unpublished state, and
   reports (never clears) every other claim with its age. Immediate recovery
   never depends on it (launch adopts). Worth building at all?
6. **Local-only scope.** Proposal: `[git].enabled = false` and non-Git →
   local `O_EXCL` lock; remote-less → normal local-control CAS; missing
   control branch → refuse rather than degrade. Confirm.

## Evaluator review

Cold review, 2026-10-01. **Not ready for implementation.** The body clearly
identifies the required outcome and explicitly locates the spec on this
blackboard. The frozen workflow matches the packaged
`code/design-then-implement` workflow: this review hands findings to the owner,
not approval to implement. The shared lock module, Git CAS foundation,
separate checkout-lock deliverable, and separate collector follow-up fit the
repo boundaries. The following protocol gaps must be resolved first.

### Must resolve before implementation

1. **P1 — The fork-to-record death proof can admit two workers.** The
   Liveness proof claims Linux's environment scan closes this window, while
   Env witness explicitly leaves the supervisor environment unchanged.
   `src/coga/repl_supervisor.py::run_with_done_marker` forks first and installs
   the supplied environment only in `os.execvpe`. An ordinary, ungated child
   stopped before exec has neither that witness nor a roster entry if the
   supervisor dies before recording it. A recoverer can declare the claim
   dead, adopt, and start a second worker before the first child resumes.
   A local fork probe confirmed the live pre-exec child's `/proc/.../environ`
   lacks the proposed key even though the future exec environment contains it.
   Specify a durable spawning barrier and child-release protocol for **every**
   spawn path (PTY, non-TTY, script), or treat incomplete spawning as uncertain
   on Linux too. Define the state's transitions and test an actual paused
   pre-exec child, not just a fake process table. Scenario 12 currently asserts
   a guarantee the proposed mechanism cannot provide.

2. **P1 — Normal/exceptional release lacks proof that workers stopped.**
   Release only requires published task bytes; it never checks the child
   roster or surviving descendants. In
   `src/coga/repl_supervisor.py::run_with_done_marker`, the PTY-loop `finally`
   restores terminal state and removes the sentinel; `waitpid` is afterwards,
   and arbitrary exceptions do not run `_trigger_term`. Wrapping `_launch`
   in a release context manager therefore does not establish child death on
   `KeyboardInterrupt` or another exception. `launch_script.run_script_phase`
   uses `subprocess.run`, with no process-group/descendant shutdown contract.
   A surviving child can coexist with a newly acquired owner after removal.
   Specify terminate/reap and descendant evidence before release, and retain
   the claim if termination is uncertain. Add interrupt, natural parent exit
   with a surviving descendant, and teardown-failure tests. This is needed
   independently of crash-time adoption and does not promise fencing of
   arbitrary external side effects.

3. **P1 — Recovery is circular and contradicts the retained-state scenarios.**
   Existing claim rule 3 refuses adoption whenever the old checkout has
   unpublished task state, including when invoked from that same checkout;
   Release and scenarios 18/23 nevertheless promise that relaunch there
   adopts, publishes/reconciles, and releases. Moreover,
   `commands/launch.py::_CheckoutBoundary.enter` publishes and calls
   `git.prepare_control_checkout` **before** the proposed acquisition point.
   The new holder guard rejects that publication under the dead session's
   claim; `git._plan_preparation` then refuses unpublished paths. A local
   `released:` witness cannot pass an ordinary sync either
   (`git.ticket_regression_reason`,
   `launch._reconcile_released_launch_admission`). Recovery is unreachable.
   Specify a narrow recovery entry before preparation, its exact CAS and
   preservation rules, and when new work may start. Cover done/canceled and
   deleted tickets with withheld releases: ordinary launch cannot resume all
   of them. Also reconcile the statement that a pending generation retains
   its lock until manual reconciliation with generic Release, which would
   remove it when ticket bytes already equal control. Extend scenarios 18/23
   to real Git checkouts with dirty state and the entry boundary enabled.

4. **P1 — Recurring holds need their own complete outer boundary.** The
   acceptance criterion includes every recurring period, but Proposed shape
   only wraps `_launch` and `megalaunch._launch_until_stop`.
   `src/coga/recurring_runner.py::_launch_due_tasks` and `_launch_created`
   call `_run_delegated_task` directly; its child is a bootstrap target,
   expressly exempt from locking. These paths would take no period lock.
   Ordinary recurring launches also return before the runner calls
   `_stop_if_unfinished_after_launch`; releasing inside `_launch` leaves that
   final pause/publication outside ownership. `_prepare_forced_launch` can
   activate before dispatch. Specify which recurring caller owns the hold
   through activation, delegation, finalization and checkout settlement, and
   how direct `coga launch recurring/...` shares it without double acquisition.
   Add sweep, named, direct, forced, delegated, timeout and failed-finalization
   scenarios. `tests/test_recurring.py::test_delegated_task_launches_target_and_owns_lifecycle`
   confirms that lifecycle ownership is in the runner.

5. **P1 — Local-only replacement/removal has no atomic decision.** `O_EXCL`
   protects first creation; reading exact bytes and then unlinking does not
   protect release or unlock. A releaser can read claim A, a concurrent
   remover can delete A and a launcher create B, then the first releaser can
   unlink B. Two adopters can likewise both read a dead A unless replacement
   is serialized. Define the local compare-and-replace/delete transaction,
   including all acquire/adopt/unlock/release participants; the existing
   short-lived `git.state_lock` is a possible checkout-local primitive without
   turning it into the long ownership hold. Add local-mode concurrent adopter
   and replacement-between-check-and-unlink tests. Scenario 26 alone only
   proves initial creation exclusion.

6. **P2 — Excluding locks from publication does not make stale local files
   harmless to checkout preparation.** Lock paths / scenario 21 promise a
   stale dirty lock cannot block preparation. `git._plan_preparation` examines
   all staged, tracked and untracked paths and rejects bytes that differ from
   pinned control; it does not consult `_candidates`. Filtering the latter
   prevents publication but leaves precisely this obstruction. Specify a
   separate, evidence-preserving stale-lock reconciliation rule, or explicitly
   make this a diagnosed refusal with a recovery procedure and revise scenario
   21. Test dirty tracked and untracked lock files, not just a clean feature
   checkout whose HEAD contains an older lock.

### Optional recommendations and owner decisions

- Tighten the new `publish(content=...)` contract before coding it. Current
  `git._guard` requires `expect=None` to mean absence even if desired bytes
  already match control (`tests/test_git.py::test_expect_none_means_the_path_must_not_exist_on_control`).
  Forced candidates therefore do not give the stated idempotent `False` acquire
  when the claim already exists. Describe explicit reconciliation of that
  case rather than treating a generic `False` as remote confirmation. Also
  preserve the distinction between observed working bytes and desired landed
  bytes in `fast_forward_control`'s staging proof; its remote-less path uses
  `merge --ff-only` when a worktree holds control, not always `update-ref`.
- Reserve or diagnose the lock-path namespace. `tasks.list_tasks` currently
  allows a group/directory task named `foo.lock` alongside `foo.md`; the
  proposed claim for `foo` collides with that directory. Do not silently
  replace a subtree in the Git tree. Add malformed-claim, path-collision and
  orphan-unlock coverage, plus the new env keys to test isolation.
- State rollout assumptions: older launchers and publishers do not enforce
  these locks. Name the writer-upgrade/quiet-window requirement or explicitly
  limit guarantees to participating versions. Include
  `coga/internals/agent-spawn`, recurring ownership topics and `dev/checkouts`
  in the eventual contract changes if the fixes above change their behavior.
- Owner still decides general launch cost/availability, `unlock` command
  placement, existing-ticket authoring, and local-only scope. The all-writer
  guard, recurring participation and separate collector were already decided;
  remove their stale alternatives from Open Questions when accepting the
  revision. No decision was made on the owner's behalf in this review.

### Verification

Read the current source, relevant tests, supplied contracts, discovery and
recurring topics, and the packaged workflow. No implementation, fixture,
ticket-body or frontmatter edits were made. An isolated fork/pipe probe
verified the pre-exec environment gap and reaped its child.

The initial ambient `python -m pytest` attempt could not collect because
`tomlkit` is absent there. The repository venv completed **12 passed** with:

```sh
.venv/bin/python -m pytest -q tests/test_git.py::test_expect_pins_the_exact_control_copy tests/test_git.py::test_expect_none_means_the_path_must_not_exist_on_control tests/test_git.py::test_guard_sees_every_base_the_publish_pushes_on tests/test_git.py::test_pending_claim_on_control_accepts_only_its_own_admission tests/test_git.py::test_a_released_witness_is_never_published tests/test_repl_supervisor.py::test_pty_child_replaces_inherited_environment tests/test_recurring.py::test_delegated_task_launches_target_and_owns_lifecycle
```

These validate existing mechanisms; they are not implementation tests for the
proposed lock. Handoff: owner resolves or explicitly dispositions the six
must-fix findings before advancing to implementation.
