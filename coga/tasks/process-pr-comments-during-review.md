---
slug: process-pr-comments-during-review
title: process pr comments during review
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
---

## Description

When a `code/*` workflow reaches its human-owned `review` step, the ticket is
parked and there is no way to hand work back to an agent: `coga bump` has
rewritten `assignee:` to the human owner, and `coga launch <slug>` is hard-
refused as a human handoff. The owner reviews by leaving comments on the GitHub
PR, so those comments currently have to be re-typed into a new ticket or applied
by hand.

Make it possible, on demand, to relaunch an agent on an already-open PR so it
reads the unresolved review comments, applies the fixes, pushes to the PR
branch, and replies on each thread — leaving the merge decision with the human.

Two parts:

1. **Relax the human-handoff launch gate** so an explicit `--agent <type>`
   override launches an agent on a human-owned step. The override is ephemeral:
   `assignee:` on disk is unchanged.
2. **Add a `code/address-pr-comments` skill** and wire it as `skills:` on the
   `review` step of all three `code/*` workflows.

Tickets **already** parked at `review` when this lands will not pick it up (their
workflow snapshot is frozen — see Part 2). That is an accepted limitation, not a
gap to solve here: the owner's call is that the in-flight population is small and
short-lived.

### Acceptance

- `coga launch <slug> --agent claude` starts an agent on a `review`-step ticket;
  without `--agent` it is still refused exactly as today.
- After that session, `assignee:` on disk still reads the human owner.
- A ticket created after this change reaches `review` with the skill composing
  into the assist launch's prompt.
- `python -m pytest` green, including the inverted gate test named below.

## Context

### Shape of the feature (decided with the owner during authoring)

- **Trigger is on demand.** The owner runs `coga launch <slug> --agent claude`
  once they have finished commenting. No new workflow step (comments usually
  arrive *after* a step would have run) and no recurring sweep that polls PRs
  and launches by itself.
- **Authority of the assisting agent:** apply the must-fix comments on the
  recorded branch, run `python -m pytest`, commit and push to the PR branch, and
  reply to each thread saying what it did. It must **not** merge, **not** resolve
  GitHub threads, and **not** advance the ticket.
- **The skill must not bump.** `review` is the final step of all three `code/*`
  workflows, so the ticket stays in `review` and the existing `autoclose-merged`
  sweep marks it `done` after the human merges (`autoclose.py:223-234` requires
  `status in {active, in_progress}` *and* the final step, so this is sound). This
  is an explicit exception to the base prompt's "always end a step with
  `coga bump`" rule — say so in the skill, or an agent will bump or
  `coga mark done` out of habit.
- **Session termination.** The assist launch is attended by definition — the
  human just typed the command. The session ends when they end it; do **not**
  reach for `coga slack` as a terminator, because it emits the done marker only
  for bootstrap refs (`src/coga/commands/slack.py:74-75`) and is explicitly
  non-terminal for ordinary tasks. A useful free property to keep as an
  acceptance check: because the assist changes neither step nor status,
  `_harness_stop_reason` returns "still on …; stopping" (`launch.py:1173-1174`),
  so the supervisor will not loop.

### Part 1 — the launch gate

`_refuse_human_handoff_launch` (`src/coga/commands/launch.py:1232`) bails
whenever `assignee:` is not in `cfg.agents`. It is called twice — `launch.py:257`
(before activation) and `launch.py:276` (after). `agent_override` is passed in but
only interpolated into the *error message*; it does not open the gate. Separately,
`_read` (`launch.py:174-179`) applies the override to `frontmatter["assignee"]`
only when the target `is_bootstrap`, so a real task never picks it up. Once the
gate lets the launch through, `launch_assignee = agent_override or assignee`
(`launch.py:286`, mirrored in the chain loop at `launch.py:401-403` for the first
step only) already resolves the agent type correctly.

Required properties of the change:

- The override must be **explicit** — never inferred, never defaulted. Without
  `--agent`, a human-owned step is still refused exactly as today.
- The override must be **ephemeral**. `_read` mutates an in-memory `Ticket`;
  make sure that mutation cannot reach disk. After the session, `assignee:` must
  still read the human owner.
- The launch banner must say it is assisting on a human-owned step, so the
  unusual launch is visible in the transcript.

**An existing test asserts the current behaviour and must be inverted, not
worked around.** `test_launch_agent_override_does_not_bypass_human_handoff`
(`tests/test_launch.py:2826-2850`) asserts exit code 2 and
`Cannot launch fix-retry-logic with --agent 'codex'`. Its *name* encodes today's
refusal as a deliberate invariant — this ticket is the decision to change that
invariant, so rewrite the test rather than treating the red as a signal to stop.
Add coverage for: permitted with an explicit `--agent`, still refused without
one, and `assignee:` unchanged on disk afterwards.

**Known wrinkle, decide during implement:** in-session commands re-read
`assignee:` from disk, so `coga slack` derives its audit actor as
`f"agent:{ticket.assignee}"` (`src/coga/commands/slack.py:56`) and an assisting
agent's FYI lands in `coga/log.md` as `agent:<human>`. That is a direct
consequence of the ephemerality requirement. Either thread the effective launch
agent through, or accept it knowingly — don't discover it in production.

**`megalaunch` is deliberately untouched.** It enforces its own independent human
gate (`megalaunch.py:836-841`, `skipped-human-gate`), which this change does not
relax — a sweep grabbing human-owned steps would be bad. But its docstring
(`megalaunch.py:162-168`) claims `--agent` has "the same semantics as
`coga launch --agent`", which becomes false. Fix that docstring in this PR.

**Tradeoff, accepted deliberately by the owner:** this relaxation is *global* —
any human-owned step on any workflow becomes agent-launchable with an explicit
`--agent`. The narrower alternative (a per-step `agent_assist: true` opt-in in the
workflow) was considered and rejected in favour of the smaller diff. The three
properties above are the mitigations; keep them.

### Part 2 — the skill and the workflow wiring

- Write the skill at `coga/skills/code/address-pr-comments/SKILL.md`, plus the
  packaged copy at
  `src/coga/resources/templates/coga/bootstrap/skills/code/address-pr-comments/SKILL.md`.
  The `code/*` skills are byte-identical pairs today
  (`coga/skills/code/{design,implement,open-pr,self-qa}` vs the packaged tree).
  Shipping only one copy breaks a bootstrapped repo: the ref is wired into the
  **packaged** workflow templates, so a repo without the packaged skill raises
  `ComposeError` from `_missing_skill_message` (`compose.py:348-349`), and
  `coga validate` flags it (`validate.py:1048`).
- Wire `skills: [code/address-pr-comments]` onto the `review` step of
  `code/with-review.md`, `code/with-self-review.md`, and
  `code/design-then-implement.md` under
  `src/coga/resources/templates/coga/bootstrap/workflows/code/`. These are
  bundled-only — there is no repo-local `coga/workflows/code/` — so that is a
  single-copy edit, unlike the skill above.
- `compose.py:344` reads a step's `skills:` regardless of its `assignee:`, so
  attaching a skill to an owner-assigned step composes correctly. It only ever
  reaches an assisting agent, since a human step composes no prompt otherwise —
  which is exactly the intended audience.

**The skill must restate the limits, because wiring it deletes the prose that
carries them today.** `_step_layers` returns early once `skill_refs` is non-empty
(`compose.py:346-359`) and never reaches the inline fallback, so the moment the
`review` step gains a `skills:` entry, the must-not-merge paragraph at
`code/with-review.md:111-116` (identical in the other two workflows) stops
composing. Carry that language — may inspect, may run verification, may push
explicitly requested fixes, **must not merge / resolve / advance** — into the
skill itself. Leave the workflow paragraph in the file for human readers.

**Accepted limitation: already-parked tickets get nothing.** A ticket's `steps:`
come from the snapshot frozen into its own frontmatter (`ticket.py:213-221`) at
create (`create.py:189`) or activation (`mark.py:365-382`), and nothing refreshes
it — `_freeze_workflow_ref` is a documented no-op once `workflow:` is already a
dict. So any ticket sitting at `review` today keeps `skills: []` forever. (This
ticket's own frozen snapshot above is an example.) The owner has accepted this;
do not build a re-freeze mechanism here.

**Reading comments:** `gh` is already a hard dependency (`src/coga/open_pr.py`,
`src/coga/autoclose.py`). Unresolved review threads need `gh api graphql` —
`gh pr view --comments` returns issue comments and misses per-line thread
resolution state. The PR URL is on the ticket as `pr:` under `## Dev` (see the
attached `dev/code` context); the branch is `branch:` in the same block.

**Microkernel rule (CLAUDE.md).** Part 1 edits shared launch machinery, which is
fine. Part 2 is markdown only. The `gh api graphql` invocation belongs **in the
skill text**, not in a new `src/coga/` helper module — a single-consumer GraphQL
helper in core is exactly what the rule forbids.

### Out of scope

- Automatic/recurring triggering (a sweep that polls open PRs and launches on its
  own) — considered and rejected for now.
- A general re-freeze / snapshot-refresh mechanism for edited workflows, and any
  attempt to reach tickets already parked at `review`. Explicitly declined by the
  owner as a small, short-lived population. (A re-freeze would fix the whole class
  — every workflow `steps:` edit is invisible to in-flight tickets, including
  `assignee:` fixes and added `requires:` gates — but it needs a re-anchor rule
  for `step: N (name)` when steps are inserted, renamed, or removed. Its own
  ticket if it ever earns one.)
- Resolving GitHub threads, and merging, both of which stay with the human.
- Any change to the `open-pr` step, `coga open-pr`, or the `requires: pr` gate.
- Relaxing `megalaunch`'s independent human gate.

<!-- coga:blackboard -->

## Dev
pr: https://github.com/FastJVM/coga/pull/677
branch: codex/address-pr-comments
worktree: /tmp/coga-address-pr-comments.WN9lV7/repo

## Implementation

- Started from `main` at `e8f6678a`.
- Keep the explicit `--agent` override ephemeral and expose the assist in the
  launch banner; leave megalaunch's independent human gate unchanged.
- Accept the documented `coga slack` audit-actor wrinkle: the assist skill
  explicitly forbids using Slack as a terminator, and threading transient
  launch identity through unrelated commands would widen this change.
- Implemented the explicit human-step assist gate and visible banner without
  mutating `assignee:`, kept megalaunch's independent gate, added the live and
  packaged `code/address-pr-comments` skill, and wired all three bundled code
  workflows.
- Added regression coverage for explicit assist, no-override refusal,
  on-disk assignee preservation, all three frozen review-step skill refs and
  prompt composition, packaged resources, and the skill's owner-gate limits.
  The focused regression set passes (8 tests).
- Committed as `4da030e2` (`Enable agent assists during PR review`). A final
  `git fetch origin main && git rebase FETCH_HEAD` reported the branch
  up-to-date; `FETCH_HEAD` (`e8f6678a`) is an ancestor and the feature checkout
  is clean.
- Final verification: `python -m pytest` → 1573 passed, 1 skipped;
  source-backed CLI smoke passed; `coga validate --json` against `example/coga`
  reported 2 ok and no issues. The example's local `approve → merge` workflow
  is an intentional override, so the bundled `review` wiring does not apply to
  it.
- Peer review has since hardened the single-checkout assist publication path
  around exact PR/control lifecycle leases, push-destination identity,
  transactional draft/paused activation, block/reblock rollback, and
  notification preflight. A fresh `codex review --base main` on commit
  `0ab8373e` found three remaining P1 races: generated commits need a local-ref
  CAS, assists must reject non-atomic multi-`pushurl` remotes, and retryable
  log-publication refusals must suppress the CLI catch-all sweep. All three are
  now fixed with regression coverage; the captured generated tree also owns
  the control overlay so late worktree edits cannot split PR/control state.
  Current verification: `python -m pytest` → 1618 passed, 1 skipped. Do not
  advance until the branch is committed/rebased and a new review is clean.
- A fresh independent review of `b4279b4a` found seven further must-fix gaps:
  fork assists can fetch control state from the base fetch URL instead of the
  verified push destination; lifecycle state is published before the final
  spawn gates; raw credential-bearing push URLs can leak through Git errors;
  compensation fails if a concurrent descendant advances the feature ref;
  a no-sweep refusal still runs the aligned refresh; a trailing-log refusal
  skips the blocked-resume reblock; and teardown can push generated commits
  after the PR closes or merges. All seven are now addressed: assist refresh
  reads the verified push destination; lifecycle publication is the final
  pre-spawn action; Git diagnostics redact URL credentials; compensation
  reverses only generated paths atop live descendants; no-sweep paths skip
  refresh; trailing refusals re-block first; and every generated teardown push
  re-proves the PR is open at the exact OID. The matching live/packaged
  architecture context now records those guarantees. Focused verification is
  green (`tests/test_git.py`: 136 passed; `tests/test_mark.py` +
  `tests/test_launch.py`: 176 passed). Full-suite/rebase/final-review checks
  remain before advancement.
- Committed the seven-finding review fix as `3a5387da` (`Peer review: harden
  assist publication`). Pre-rebase full verification is green:
  `python -m pytest` → 1625 passed, 1 skipped. A fresh
  `git fetch origin main && git rebase FETCH_HEAD` found the branch already
  current at `eb5a198a`; that fetched tip is an ancestor, both live/packaged
  pairs are byte-identical, and the feature checkout is clean.
- The mandatory post-rebase `codex review --base main` found seven additional
  actionable gaps: same-path peer edits can be lost during remote
  compensation; unconditional local byte restoration can overwrite concurrent
  ticket/log work; exact-tip alignment accepts unexpected dirt; generic
  `GitError` can be swallowed in strict mode; in-session block/unblock pushes
  do not re-prove that the PR remains open; override validation runs before an
  aligning fast-forward can refresh config; and lower-level lease probe errors
  escape the assist refusal path. All seven are fixed with focused regressions:
  compensation now reverse-merges ordinary paths and refuses overlap; shared
  rollback is conditional and union-preserves concurrent audit lines; strict
  leases reject exact-tip dirt and normalize/re-raise every Git failure;
  in-session block/unblock inherit the exact recorded PR and re-prove it open
  at the push boundary; and override validation runs only after alignment.
  Broad focused verification passed (269 Git/launch tests and 159
  command/mark/env/supervisor/skill tests), followed by
  `python -m pytest` → 1632 passed, 1 skipped. Commit, unconditional rebase,
  post-rebase verification, and a clean repeat review remain before advancement.
- Committed that seven-finding pass as `9ef12b3f` (`Peer review: fail closed on
  assist races`), rebased unconditionally onto fetched `origin/main`
  (`eb5a198a`, already current), and re-ran the full suite: 1632 passed,
  1 skipped. The required repeat `codex review --base main` found three more
  actionable transaction/authorization gaps: failed leased `block`/`unblock`
  commands can fall through to the ordinary state sweep (including
  `unblock --all` swallowing the failure); launch publication can switch to a
  newly edited `pr:` URL instead of staying bound to the URL verified during
  alignment; and an aligned-assist setup failure can sweep a deliberately
  retained retry log into an unpublished feature commit. Fix all three, add
  regressions, and obtain another clean review before advancement.
- The three repeat-review gaps are now fixed: strict `block`/`unblock`
  failures use the no-sweep retry code and `unblock --all` aborts; launch pins
  every guard to the exact `pr:` URL authorized during alignment; and
  aligned-assist setup refusals cannot hand retained state to CLI teardown.
  The matching live/packaged architecture and sync contexts are updated and
  byte-identical. Targeted race tests and the full command/launch suites pass
  (213 tests), followed by `python -m pytest` → 1635 passed, 1 skipped.
  Committed as `3f4b9a98` (`Peer review: pin assist authorization`), fetched
  `origin/main`, and rebased unconditionally onto `FETCH_HEAD` (already
  current). Post-rebase `python -m pytest` is also green: 1635 passed,
  1 skipped. A clean repeat review remains before advancement.
- The next mandatory `codex review --base main` found five more actionable
  strict-assist edges: early alignment/config refusals and failed in-session
  lease acquisition can still enter the broad CLI sweep; a Slack delivery
  failure can append an unleased audit line after strict state publication;
  a deleted PR branch can fall back to a local-only generated commit during
  teardown; and a fork PR whose head is named like the control branch is only
  rejected after an ordinary log push. Address all five (including the
  analogous `unblock --all` acquisition path), add regressions, and obtain a
  clean repeat review before advancement.
- Those five edges are fixed: launch marks the recorded checkout as retry-only
  before PR alignment and rejects control-named PR heads before any write;
  `block`, direct `unblock`, and `unblock --all` propagate no-sweep lease
  acquisition failures; strict lifecycle notifications keep delivery failures
  on stderr without appending unleased audit bytes; and pinned log/refresh
  publishers require an exact live remote tip instead of creating local-only
  commits after branch deletion. Live/packaged architecture and sync contexts
  remain byte-identical. Focused affected suites pass (560 tests), followed by
  `python -m pytest` → 1644 passed, 1 skipped. Commit, unconditional rebase,
  post-rebase verification, and a clean repeat review remain.
- Committed that pass as `a5ccafd7` (`Peer review: close assist teardown
  gaps`), fetched `origin/main`, and rebased unconditionally onto `FETCH_HEAD`
  (already current). Post-rebase `python -m pytest` is green: 1644 passed,
  1 skipped. The required repeat review remains before advancement.
- The post-rebase repeat review found eight further P1/P2 correctness gaps:
  automatic unresolved re-block cannot reacquire a lease while the trailing
  usage append is dirty; the permitted log dirt is not proven append-only;
  compensation can merge onto a concurrently switched branch; strict alignment
  also runs for agent-owned overrides; unexpected setup exceptions can re-enable
  the broad CLI sweep; a TTY-less assist reports an alignment error instead of
  the documented TTY refusal; explicit `coga block` attributes the human owner
  instead of the effective assist agent; and an unarmed rollback can snapshot
  peer bytes as generated state and erase them. Fix all eight with regressions,
  then repeat the full verification/rebase/review loop. The review's P3 request
  to move the one-caller notification preflight is a placement nit and is
  intentionally skipped under this step's “skip nits” rule.
- All eight correctness gaps are now covered in the feature checkout. The
  unresolved re-block lease admits only an explicit append-only audit delta;
  strict publication rejects audit rewrites; compensation verifies the active
  branch and HEAD before its local merge; only human-owned overrides enter
  assist alignment; setup interrupts retain the no-sweep exit; TTY refusal
  precedes assist validation; the child carries its effective agent for
  blocker/audit attribution; and unarmed rollback refuses to guess at current
  bytes. The live and packaged architecture contexts record these boundaries
  and remain byte-identical. Focused verification is green:
  `tests/test_git.py` (146 passed) and `tests/test_launch.py` (139 passed).
  Full-suite verification, commit, unconditional fetch/rebase, post-rebase
  verification, and a clean repeat review remain before advancement.
- Committed the eight-finding pass as `967ff987` (`Peer review: close remaining
  assist races`), fetched `origin/main`, and rebased unconditionally onto
  `FETCH_HEAD` (`eb5a198a`, already current). Post-rebase
  `python -m pytest` is green: 1649 passed, 1 skipped. Live/packaged
  architecture and skill pairs are byte-identical and the feature checkout is
  clean. The required repeat review found one P2: a non-TTY retry refuses
  before strict assist setup is marked, so a deliberately retained append-only
  assist log can fall through to the generic CLI sweep. Preserve the ordinary
  exit-2 TTY refusal for clean launches, but use the no-sweep retry exit when
  the checkout locally proves that sole append-only log shape; add a regression
  and repeat the full verification/rebase/review loop. The fix now performs
  that local proof before the TTY refusal without touching recorded-checkout or
  remote validation; clean and rewritten-log cases retain exit 2. The launch
  suite passes 141 tests and `python -m pytest` passes 1651 tests with 1
  skipped; live/packaged architecture context copies are byte-identical and
  `git diff --check` is clean. Committed as `f2ac1748` (`Peer review: preserve
  TTY retry state`), fetched `origin/main`, and rebased unconditionally onto
  `FETCH_HEAD` (already current). Post-rebase `python -m pytest` is green:
  1651 passed, 1 skipped. One clean repeat review remains before advancement.
- The repeat review found four more must-fix races/invariants. A concurrent
  checkout switch can redirect the assist alignment fast-forward onto another
  branch; failed refresh cleanup can reset that branch's index and blindly
  overwrite its worktree bytes; an exception after strict lifecycle
  publication restores only local bytes and leaves feature/control state
  published as `in_progress`; and re-resolving the user's prefix after
  alignment can silently select a different task if the original ticket moved.
  Fix all four with focused regressions, then repeat the full
  verification/rebase/review loop before advancement.
- All four findings are fixed with five focused regressions. Alignment pins
  the exact initially resolved task slug and rechecks the sampled branch/HEAD
  before either fast-forward path. Failed refresh cleanup verifies checkout
  ownership, resets no unrelated index, restores only bytes still matching
  its generated snapshot, and union-removes generated audit lines around peer
  appends. The strict lifecycle publisher records its durable boundary before
  output/notification work, so a later interrupt retains one clean,
  feature/control-consistent `in_progress` state for retry instead of locally
  rewinding it. Live/packaged architecture contexts remain byte-identical.
  The focused regressions, complete Git suite (149 passed), complete launch
  suite (143 passed), and `python -m pytest` (1656 passed, 1 skipped) are
  green. Commit, unconditional fetch/rebase, post-rebase full verification,
  and a clean repeat review remain before advancement.
- Committed the four-finding pass as `029105a7` (`Peer review: guard final
  assist races`), fetched `origin/main`, and rebased unconditionally onto
  `FETCH_HEAD` (already current). Post-rebase `python -m pytest` is green:
  1656 passed, 1 skipped. The mandatory repeat review remains before
  advancement.
- The repeat review found three more must-fix transaction gaps. The control
  guard leases only `(status, step, assignee)`, so a concurrent owner
  body/blackboard/attachment edit can be overwritten by the whole-task
  overlay; an interrupt after the feature push but before the control landing
  bypasses compensation and splits the two refs; and strict mark rollback is
  armed only after post-write validation, so a validation rejection can retain
  an unpublished generated mutation. Fix all three fail-closed with
  regressions, then repeat the full verification/rebase/review loop.
- All three transaction gaps are now fixed. The lease pins the exact
  control-side task object (including directory-form attachments); strict
  publication catches interrupts across both pushes, compensating a
  feature-only publication and retaining a proven feature/control publication;
  and state writers arm rollback immediately after each generated write,
  before validation, then re-arm after the audit append. Live and packaged
  architecture contexts document the guarantees and remain byte-identical.
  The focused regressions pass, the complete Git/launch suites pass
  (297 tests), and `python -m pytest` is green (1661 passed, 1 skipped).
  Committed as `68ce1768` (`Peer review: close assist transaction gaps`),
  fetched `origin/main`, and rebased unconditionally onto `FETCH_HEAD`
  (already current). Post-rebase `python -m pytest` is also green:
  1661 passed, 1 skipped. A clean repeat review remains before advancement.
- The mandatory repeat review reproduced eleven further transaction and
  teardown gaps. An inconclusive post-control probe can compensate the feature
  half after control accepted it; the final launch lease can overwrite a ticket
  edit made after its stale read; strict commits read selected paths from the
  live worktree instead of the armed snapshot; log fast-forward can erase an
  append made after its sample; refresh writes paths before re-verifying the
  checkout; some post-alignment setup work sits outside the no-sweep guard;
  explicit strict `block` can publish before discovering invalid notification
  config; compensation rewrites stale requested bytes over a preserved peer
  edit; and interrupts can strand local strict commits or leave strict
  log/refresh push outcomes unreconciled. Fix all eleven with regressions, then
  repeat the full verification/rebase/review loop before advancement.
- All eleven findings are fixed, with an additional fail-closed check for a
  checkout switch between alignment and session setup. Strict lifecycle
  commits now use the state writer's armed byte snapshot; final launch bytes
  are rechecked after lease acquisition; ambiguous durable outcomes retain
  generated state; log/refresh pushes reconcile interrupts against the exact
  destination; refresh and alignment writes recheck checkout ownership;
  compensation keeps its peer-preserving descendant bytes; and strict block
  notification config is preflighted before mutation. All post-alignment
  failures use the no-sweep exit. Live and packaged architecture/sync contexts
  remain byte-identical. Focused Git/launch verification passes 309 tests and
  `python -m pytest` is green (1673 passed, 1 skipped). Commit, unconditional
  fetch/rebase, post-rebase full verification, and a clean repeat review
  remain.
- Committed that pass as `da3d30a0` (`Peer review: harden assist
  publication`), fetched `origin/main`, and rebased unconditionally onto
  `FETCH_HEAD` (already current). Post-rebase `python -m pytest` is green:
  1673 passed, 1 skipped; parity and diff checks are clean.
- The mandatory repeat review reproduced eight further must-fix gaps:
  strict ticket writers can overwrite a peer edit made after their stale
  `Ticket` read; strict refresh writes do not compare the live worktree with
  their sampled bytes; explicit block, unblock, and automatic reblock do not
  roll back and use the no-sweep exit for every interrupt after their first
  mutation; an ambiguous compensating push is treated as definitively failed;
  alignment can lose its temporarily hidden audit append on an interrupt;
  a post-fast-forward alignment reread still sits outside the no-sweep
  boundary; refresh rollback starts only after its first worktree writes; and
  strict commit finalization accepts a switch to another branch at the same
  OID. Fix all eight with regressions, then repeat the full
  verification/rebase/review loop before advancement.
- Those eight gaps are fixed in `afa46d77` (`Peer review: harden assist
  transactions`), rebased unconditionally onto fetched `origin/main`
  (`46c6f0b5`). Post-rebase `python -m pytest` is green (1696 passed,
  1 skipped), resource parity and validation checks pass, and the checkout is
  clean. The required repeat `codex review --base origin/main` found eight
  additional actionable edges: post-alignment setup can still escape the
  no-sweep boundary; exceptional blocked-assist exits can bypass automatic
  re-blocking; lifecycle snapshot capture can adopt or overwrite a peer ticket
  revision; the first strict block/unblock blackboard write is unguarded;
  lifecycle publication is not revalidated immediately before spawn; refresh
  can overwrite dirt arriving after its initial scan; strict pushes can
  re-resolve a changed remote instead of using the verified URL; and the
  append-only log exception does not reject mode/type-only changes. Fix all
  eight with regressions, then repeat the full verification/rebase/review loop
  before advancement.
- Those eight findings are fixed in `27a008dd` (`Peer review: close strict
  assist races`). The post-alignment setup operations share the no-sweep
  boundary; exceptional exits re-block unresolved resumes; lifecycle parse,
  rollback, and final spawn validation use one exact ticket revision and a
  fresh branch/control/PR proof; first blocker mutations are conditional;
  refresh rechecks each sampled path; every strict feature/control/
  compensation operation uses the lease's captured push URL; and the audit
  exception rejects mode/type changes and requires a real byte suffix. Live
  and packaged architecture/sync contexts remain byte-identical. The affected
  Git/launch suites pass 333 tests, `python -m pytest` passes 1705 with 1
  skipped both before and after an unconditional fetch/rebase onto
  `origin/main` (`46c6f0b5`, already current), and the feature checkout is
  clean. A clean repeat review remains before advancement.
- The required repeat `codex review --base origin/main` passed all 1705 tests
  but found four further must-fix correctness gaps: strict control publication
  uses an ordinary push that can recreate a deleted or force-rewound control
  ref; rollback `arm()` resamples live files and can adopt a peer edit made
  after Coga's write; strict unblock can return early when a peer already
  resolved the final blocker without checking its captured ticket revision;
  and an interrupt during aligned teardown refresh can escape as 130/143 and
  re-enable the broad CLI state sweep. Fix all four with regressions, update
  the durable contract where needed, and repeat the full
  verification/rebase/review loop before advancement.
- All four findings are now fixed with focused regressions. Strict control
  candidates use an exact lease on each freshly guarded base; rollback arming
  accepts only caller-constructed ticket bytes and exact encoded log appends;
  a would-be no-op blocker resolution validates the captured full-ticket
  revision before returning; and exceptional assist teardown refresh exits are
  normalized to the no-sweep temporary failure. The live and packaged
  architecture contexts document those boundaries and remain paired. The nine
  focused race cases pass, followed by the complete affected Git/launch/mark/
  ticket/primitives/commands suites (504 passed). Committed as `a046c2b4`
  (`Peer review: lease strict assist state`), fetched `origin/main`, and
  rebased unconditionally onto `FETCH_HEAD` (`46c6f0b5`, already current).
  `python -m pytest` is green both before and after rebase (1710 passed,
  1 skipped), the context pair and diff check are clean, and the checkout is
  clean. A clean repeat review remains before advancement.
- The required repeat review reran the full suite (1710 passed, 1 skipped) and
  reproduced two remaining P1 races. Strict `block`, `unblock`, and automatic
  unresolved reblock capture their rollback baseline only after network lease
  acquisition, so a peer ticket edit in that window can be adopted or replaced
  by stale state. Separately, feature alignment reads the process-shared
  `FETCH_HEAD` after fetching; another fetch in the same checkout can replace
  it and make the assist fast-forward its feature branch to an unrelated
  control commit. Capture the exact ticket revision before lease/preflight and
  recheck it at the first write across all three paths; bind strict fetches to
  command-scoped refs instead of `FETCH_HEAD`, with regressions and durable
  context updates before repeating the full verification/rebase/review loop.
- Both P1 races now have fixes and regressions in the feature checkout. Strict
  block/unblock/reblock pin and parse the pre-lease ticket bytes before their
  first conditional write; strict Git fetch consumers resolve UUID-scoped refs
  and never rely on shared `FETCH_HEAD`. Live and packaged architecture/sync
  contexts remain byte-identical, and the complete Git/launch suites pass (342
  tests). Full-suite verification, commit, rebase, and another clean review are
  still required before advancement.
- Committed the two-race fix as `855e0fe2` (`Peer review: isolate assist
  state`). An unconditional `git fetch origin main && git rebase FETCH_HEAD`
  found the branch already current at `46c6f0b5`; `python -m pytest` passes
  after the rebase (1714 passed, 1 skipped), and the feature checkout is clean.
  The mandatory repeat Codex review is the remaining judgment gate.
- The repeat reviewer reran the full suite successfully (1714 passed, 1
  skipped) but did not terminate after an extended exhaustive scan of the
  12.5k-line branch diff, so it was interrupted rather than allowed to run
  indefinitely. Its concrete must-fix observation is valid: although core Git
  consumers now use command-scoped fetch refs, both shipped copies of the
  address-comments skill still tell the assisting agent to read shared
  `FETCH_HEAD`. Replace those instructions with unique private refs, cover the
  contract in the skill test, then run a fresh required review.
- The skill correction is committed as `6abdfe16` (`Peer review: isolate skill
  fetch state`), rebased onto the unchanged `origin/main`, and the full suite
  remains green (1714 passed, 1 skipped). The next review pass again compacted
  its own context before returning a verdict, but first reproduced one further
  must-fix regression: `read_blackboard` / `replace_blackboard` now decode raw
  bytes without universal-newline translation, while `_FENCE_RE` rejects the
  carriage return on a CRLF fence line. Preserve the exact byte CAS while
  recognizing CRLF fences, add a compatibility regression, and rerun review at
  a bounded reasoning setting so the tool can finish.
- The CRLF compatibility fix is committed as `bb360382` (`Peer review:
  preserve CRLF ticket fences`) with an exact byte-preservation regression.
  The branch is current with `origin/main` at `46c6f0b5`, clean, and 25 commits
  ahead. Final verification is green: `python -m pytest` reports 1715 passed
  and 1 skipped; resource pairs are byte-identical; `git diff --check` and the
  source-backed CLI smoke pass; and `coga validate --json` against
  `example/coga` reports 2 ok with no issues. The bounded mandatory
  `codex review --base origin/main` completed with: “No actionable correctness
  issues were identified.”

## PR

Summary:
- Permit an explicit, ephemeral agent assist on a human-owned launch step and
  make the assist visible without relaxing the default or megalaunch gates.
- Ship `code/address-pr-comments` in live and packaged form and attach it to
  the final review step of all three bundled code workflows, using private
  command-scoped fetch refs rather than shared `FETCH_HEAD` state.
- Preserve the owner merge/thread-resolution gate while making assist state
  publication fail closed under concurrent ticket, checkout, branch, and
  remote changes; document the changed CLI and synchronization contracts.

Test plan:
- `python -m pytest` (1715 passed, 1 skipped)
- source-backed CLI smoke
- `coga validate --json` against `example/coga` (2 ok, no issues)
