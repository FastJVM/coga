---
name: coga/launch-internals
description: The strict publication invariants behind coga launch, the recurring runner, and the requires-pr gate — recorded-checkout and PR-head proofs, leases, compare-and-set publication, compensation, and recurring admission generations. Attach only to tickets that change launch.py, the recurring runner, open-pr, or the step gates.
---

# Coga launch internals

These are the concurrency and publication guarantees behind `coga launch`, the
recurring runner, and the `requires: pr` step gate. They are what a change to
`commands/launch.py`, the recurring scan, `step_gate.py`, or `open_pr.py` must
not break.

**Not attached by default, on purpose.** `coga/architecture` carries the model
an agent needs to *operate* — what runs when, what advances a step, what a
handoff means, and where each of these sections picks up. Everything here is
what the implementation must *guarantee* under concurrent writers, and it is
~19 KiB of prompt every ordinary ticket is better off not paying for. Add
`coga/launch-internals` to a ticket's `contexts:` list when the work touches
those paths.

## Strict human-assist publication

`coga launch <slug> --agent <type>` on a locally human-owned ticket is the
strict assist path. `coga/architecture` describes when it is entered; this is
what it must prove before and around every generated write.

### Around a `ticket.py` phase

A recorded single-checkout human assist first verifies and aligns its
authoritative PR tip, publishes the
started lifecycle and pre-script audit under the strict PR/control lease, then
executes `ticket.py` with the same task-scoped assist capability. Valid direct
ticket/blackboard output and the exit audit are republished from their exact
post-child byte snapshot under a lease acquired before user code; ignored
untracked leaves, including ignored non-regular local-environment entries, are
never part of that snapshot; tracked symlinks remain a refusal. Task validation
runs before publication, and an invalid result is restored and audited instead
of reaching either ref. If a nested lifecycle command already published while
the child ran, recovery restores the latest re-verified feature/control
lifecycle rather than the stale pre-child state. Live notification
configuration is preflighted before the child or any strict lifecycle/audit
publication.
Lifecycle commands invoked by that child (`bump`, `mark paused/done/canceled`,
`block`, and `unblock`) capture their own exact task-tree mutation snapshot
before acquiring a fresh inherited assist lease, publish earlier deterministic
attachments plus the transition to feature and control together, and include
the recurring parent high-water state when a period task completes. They leave
only the trailing script-exit audit for the parent to renew under an append-only
lease. While that scoped assist environment is present, the CLI's
generic end-of-command Coga subtree sweep is disabled on success and failure;
only an exact assist publisher may commit child state. Before every agent
spawn, launch rebuilds the environment from the fresh ticket's secret
declarations; after each child boundary it reloads config, target, and ticket
again before classifying the handoff. An explicit override assisting a human
step expires when the script advances to a configured agent-owned step, so the
durable assignee selects and is credited for that next deterministic or agent
phase; the aligned checkout's strict publication capability continues through
that configured-agent chain.

### Recorded checkout, PR head, and the publication lease

The assist publishes to an already-open PR branch, so it proves its right to
that branch before every generated push.

Publication requires launch to run from the exact recorded `worktree:` on the
recorded `branch:`; primary checkouts, linked worktrees, and independent
fallback clones are all supported, while a separate, missing, or mismatched
checkout keeps ordinary local-only log
handling. Before touching that branch, launch requires the recorded `pr:` to be
open and proves its actual head repository, branch, and OID match the
configured remote's **single** effective push URL — a same-named
base-repository branch cannot stand in for a fork PR head, a separate fetch URL
cannot authorize pushes to another repository, and a multi-`pushurl` remote is
refused because Git cannot update all of its destinations atomically. The
recorded PR branch must also have a different local name from the configured
control branch: Git exposes only one checked-out ref for that name, so Coga
cannot give a same-named fork head a feature-only publication transaction.
A merely-behind recorded checkout is then fast-forwarded before the final
config, ticket, skill-view, secrets, expected-step, and prompt reads for every
resumable status, including paused and blocked tickets; launch reloads that
state from the aligned tree before classifying its assignee, while preserving
the exact task slug originally resolved from any user-supplied prefix. Every
behind-checkout fast-forward rechecks the active branch and sampled HEAD
immediately before merging, so a concurrent checkout switch cannot redirect
the PR tip onto another branch. Strict alignment
also rejects unexpected staged, tracked, or untracked checkout dirt even when
the local tip already equals the remote; a genuinely append-only pending
union-safe audit log is the sole explicit exception. That exception requires a
non-empty byte suffix on the same regular file with the same Git mode; a
chmod-only delta or a symlink/type replacement is ordinary unexpected dirt.
Draft, paused, and blocked activation and
`in_progress` publication stay deferred through prompt
composition, prompt-file and argv construction, and the pre-session audit
commit. At the final pre-spawn boundary launch captures one exact ticket byte
revision, parses the lifecycle from those bytes, and binds rollback to that
same revision. It rechecks the bytes after the network-backed publication
lease is acquired,
re-proves that the exact recorded PR URL authorized during alignment is
unchanged and open at the exact leased remote OID, and requires the committed
feature ticket's `(status, step, assignee)` lifecycle tuple to match a freshly
fetched control copy. The lease also records the exact control-side task object
(ticket blob, or the directory tree including attachments), and every
publication attempt requires that object to remain unchanged; even a
same-lifecycle owner prose or attachment edit forces a fresh launch instead of
being overlaid. After lifecycle publication, launch obtains a fresh lease and
repeats the recorded-checkout, PR-head, and generated control-task proof before
returning to the actual spawn call. The publication guard repeats that same-URL
open-PR/OID proof immediately before every generated feature push. The lease
also captures the sole verified push URL itself; feature, control,
compensation, and outcome-probe operations use that URL directly, so a
concurrent `.git/config` rewrite cannot redirect or add a second destination.
Every fetched tip used by strict alignment, publication, compensation, and
refresh is stored in a UUID-scoped command-owned ref and resolved from that
ref. Strict paths never treat the checkout-wide `FETCH_HEAD` as authority:
another local process may overwrite it between Coga's fetch and read
subprocesses, even when both commands are otherwise correctly leased.
Every strict control candidate is also pushed under an exact lease on the
control base that just passed the task-object guard. A concurrent deletion or
force-rewind therefore loses that attempt; any retry fetches and guards the
new base before rebuilding instead of recreating a deleted ref or restoring
rewound history from a stale parent.
The
combined lifecycle commit is built directly on the verified tip and moves the
local branch with an expected-old-OID ref CAS. Its ticket and audit leaves come
from the rollback snapshot armed by the state writer, while unchanged task
attachments come from the leased feature tree; a concurrent worktree edit is
left visible and dirty instead of being adopted into either durable ref. An
interrupt around the local ref CAS rolls that exact generated commit back
before any remote publication. The captured tree is then pushed
under an exact remote-tip lease *before* the same captured state lands on
control or a start notification is sent. A lost lease removes that commit only
when the local ref still names it. An interrupt after the feature push probes
the exact destination: when control has not accepted the state it compensates
the feature branch before propagating, and when control has accepted it the
publisher records that durable boundary before propagating so local rollback
cannot split the two refs. If the control acceptance probe itself is
inconclusive, the generated feature state is retained for explicit
reconciliation; compensation is forbidden because control may already contain
it. If the later control landing fails,
compensation fetches the live feature descendant, applies only the inverse of
Coga's generated paths on top, reverse-three-way-merging ordinary files so
non-overlapping peer edits to the same path survive and refusing compensation
when those edits overlap. The checkout rechecks its active branch and HEAD
immediately before fast-forwarding to that compensation, and skips the local
merge if another command switched it. A completed local fast-forward keeps the
compensated descendant's worktree bytes, including same-path peer edits,
instead of rewriting the stale failed transition over them. A lost
acknowledgement for the compensating push is probed against that exact push
destination; if that probe is inconclusive or shows the ambiguous push did not
land, generated local bytes are retained for explicit reconciliation. The
error still escapes and the caller
restores an ordinary file only while it still equals an armed generated
snapshot, while removing generated audit lines union-safely from a concurrently
appended log; an unarmed rollback refuses rather than guessing that current
bytes belong to Coga. Strict state writers therefore arm rollback from the
exact bytes they constructed for each generated file write, never by rereading
a live path that a peer may already have changed, before post-write validation
can reject it; they then add the exact encoded audit append to that owned
snapshot. Before replacing a ticket from an in-memory state object, they also
require its live bytes to equal the latest captured revision. Their first
blocker append or resolution is likewise conditional on the captured
full-ticket bytes before the blackboard splice, including a would-be no-op
resolution whose last blocker was just resolved by a peer, so it cannot adopt
a peer revision and label it generated. Strict `block`, `unblock`, and the
automatic unresolved re-block capture that full-ticket revision before any
network-backed publication lease or notification preflight, parse their state
from the same captured bytes, and condition their first write on it. A peer
edit during that pre-write window is retained instead of becoming the
command's rollback baseline. A failure
before lifecycle publication restores those generated bytes. If an interrupt
lands only after both feature and control publication succeeded, launch retains
the identical published `in_progress` state instead of locally rewinding into a
dirty split; the same explicit launch can then retry the still-unstarted
session. A resumed blocked assist also runs its automatic unresolved re-block
on exceptional post-start exits such as signals, not only on a normal REPL
return. No unrelated concurrent work is swept. Reproducible
notification configuration errors are likewise checked before publication,
including an explicit in-session `coga block`.
If live delivery still fails after strict state publication, the failure stays
loud on stderr but does not append a new unleased audit line to the protected
checkout.
The assist also commits its own launch-log append so
Coga's audit line cannot trip the PR worktree's clean-tree gate. If the remote
or control ticket moves after composition, launch refuses to spawn and
requires a retry rather than working under stale instructions; a failed
generated-log push undoes only that commit and leaves the append dirty for the
retry. Behind-checkout audit alignment uses guarded replacement before the
fast-forward and append-only union restoration on every exit around it,
including interrupts before or after the ref moves, so an audit line appended
during alignment is never overwritten. That retryable refusal exits with the
no-sweep temporary-failure code,
so neither launch refresh nor CLI teardown can immediately commit the retained
append. TTY refusal still precedes recorded-checkout and remote validation, but
it locally recognizes a sole unstaged append-only audit-log delta and uses that
same no-sweep exit; a clean checkout or any other dirt keeps the ordinary exit
2. Every failure after strict assist alignment has begun, including later
ticket reads and other pre-session setup, uses the same no-sweep exit. A
checkout switch after alignment is a retry-only refusal, never a silent
downgrade to an ordinary launch. The child inherits a task-scoped recorded-branch,
recorded-PR, and effective-agent capability,
allowing required in-session state commands such as the blocked-resume
`coga unblock`, an explicit `coga block`, and deterministic completion via
`coga bump` or `coga mark paused/done/canceled` to acquire a fresh
feature/control lease
and re-prove the same PR is open immediately before their generated push,
while attributing a blocker to the assisting agent rather than the human ticket
assignee, without granting it to nested ordinary launches. If that resumed session exits
with its ask still open, launch obtains a fresh lease and republishes the
automatic `blocked` transition before notifying the owner; a lost reblock lease
restores the prior ticket and log bytes. That fresh lease admits a retained
trailing usage record only when the dirty audit bytes are append-only. The pre-session log, trailing usage
log, automatic unresolved re-block, and final generated control-state refresh
remain pinned to the recorded branch, re-prove the recorded PR is still open,
and publish captured generated OIDs only from a safely aligned, exact remote
tip. Assist refresh also reads control state from that verified push
destination, not a fork remote's potentially different fetch/base repository.
A strict refresh verifies the expected branch and HEAD again before its first
worktree write, retains its initial per-path byte sample, and rechecks each
candidate's live dirt immediately before replacing it. A peer edit after the
initial scan is skipped or defeats the expected-byte write rather than being
adopted as refresh input. A lost refresh lease restores its pre-refresh tip only while the
expected branch and HEAD still own the checkout, then restores ordinary bytes only when
they still match the generated snapshot and removes generated audit lines
union-safely around concurrent appends. Strict audit and refresh pushes catch
interrupts as well as ordinary Git failures and probe the exact destination
before deciding whether to retain or unwind their local generated commit. If the agent
switches branches or the PR closes, teardown skips those commits instead of
redirecting or advancing a merged branch and uses the same no-sweep exit. This
normalization also wraps the teardown refresh call itself: SIGINT, SIGTERM, or
another exceptional refresh exit after alignment becomes the no-sweep
temporary failure rather than falling through CLI teardown with 130/143. This
preserves the PR branch's local/remote alignment without the catch-all sweep
committing retained state on an unrelated or closed branch. Megalaunch keeps a
separate human gate and does not inherit this relaxation.

## Recurring admission generations

`coga/architecture` describes the recurring primitive and its lifecycle; this
is the admission machinery that keeps a stale or replaced period task from
starting, completing, or parking work at a stable path.

A sweep or named recurring run performs full recurring admission at its
outer boundary, freezes each period's exact ticket plus its creator-owned
`period_generation` token, then launches through an internal typed seam. Immediately
before each ordinary child, that seam refreshes control state, resolves only
the exact ref (never a prefix sibling), and rechecks branch/owner plus the
frozen generation. A task removed, paused, finished, or replaced while an
earlier child ran is skipped; an unverified remote-backed refresh refuses
rather than starting stale work. A Git checkout with no configured remote
freezes that local-only class at outer admission and uses exact local control
state; a remote that disappears afterward still refuses. A deterministic
child retains that refreshed admission generation; immediately before every
ordinary agent spawn, launch requires the same bounded token and the complete
current ticket to match the launchable state just composed. On either child's
unfinished exit, that token distinguishes a replacement from the same child's
ticket and audit writes; only the latter acquires a fresh exact lease, and the
guarded pause is derived from those newly leased bytes so concurrent
same-generation edits survive. A replacement refuses teardown instead of
parking the stable path's new owner.
It does not re-enter the whole public launch path. A
direct `coga launch recurring/<name>` has no such outer admission, so it gates
and requires verified catch-up before resolving even a locally missing period
ref when a remote is configured; without one, local `HEAD` is the sole control
state. For a frozen
delegation, the runner separately preflights the period task's push access
and leases its exact ticket bytes plus creator-owned generation at start,
final spawn, and post-child completion/timeout. The lifecycle publications
are compare-and-sets against control and every attempted Git verification
or publication failure propagates: an old or unverified child cannot start,
nor mark a later generation at the stable path done or paused. A sweep
continues after a delegated timeout only when its guarded pause publishes;
a stale or failed pause refuses the run. Final spawn admission also leases
the exact parent recurring ticket named by the period state snapshot against
control. Delegated completion consumes that same parent input in its strict
transaction, so a concurrent parent edit refuses instead of being
overwritten and `done` cannot land without the child's cross-run cursor
update. When a digest spool is installed, its completion event joins
that transaction; a live notification waits for durable publication. An
unaccepted generated local commit is unwound before
caller-owned file rollback. An ambiguous control push is probed by exact
candidate OID across every effective push destination; disagreement or
otherwise unknown acceptance retains local evidence and refuses for
reconciliation instead of rolling back into split state. Direct
launch may activate a paused/draft delegated period inline; scheduled and
named recurring scans keep paused periods parked.

## The `requires: pr` gate's publication path

`coga/architecture` describes the gate itself — a data check on the blackboard,
run before `coga bump` advances off the step. This is what `coga open-pr` must
guarantee when it writes the artifact the gate reads.

`coga open-pr` proves live-ticket ownership with `COGA_EXPECTED_TASK`, which
the outer step supervisor (`coga launch` or `coga megalaunch`) pins alongside
`COGA_EXPECTED_STEP` to the exact task and frozen step used for prompt
composition. Unlike the `COGA_TASK_*`
metadata, nested task re-derivation does not reassign either witness, so they
keep naming the outer session rather than whatever the environment last
described. The task witness separates a real session from an independent
fallback clone; the pair also makes `coga bump` refuse a stale supervised
session after another worker advances the ticket. The recipe
pushes the recorded feature branch by name, opens or readies the PR, and writes
`pr:` under `## Dev`; in the single-checkout layout it syncs that generated
ticket write to the feature branch *and* the control branch, so the branch stays
clean and both tips keep identical ticket bytes — otherwise the next run's
freshness gate would reject the command's own record as a divergent overlap.
That sync is reported but not fatal: the PR is already open once it runs, so a
failed push must not fail the command. Before its clean-tree gate it commits the
pending generated launch-log append, without exempting any other dirt. Its
freshness gate accepts byte-identical generated task/log overlaps created when
preceding lifecycle syncs committed the same state on the feature and control
branches, but still rejects any divergent blob; lifecycle-only task/log commits
do not satisfy the single-checkout branch's non-empty implementation guard.
After the command, the successful `requires: pr` transition lands the updated
ticket on control and republishes that transition commit to the PR branch, so
its `step:` / `assignee:` state cannot conflict at merge. Launch teardown then
publishes the trailing usage-log commit to the already-open branch, keeping its
remote and local tips aligned.

## What this context does NOT cover

- The model these invariants protect — what launch does, what advances a step,
  what a handoff means — see `coga/architecture`.
- The operator-facing behavior of the commands involved — see `coga/cli`.
- Where the code lives and how to test it — see `coga/codebase`.
- The recurring surface as a whole (schedules, templates, the autofix loop) —
  see `coga/recurring`.
