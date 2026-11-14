# Coga task — fail-validation-when-local-user-is-required-for-ex

Title: Fail validation when local user is required for execution
Task directory: coga/tasks/fail-validation-when-local-user-is-required-for-ex.md
Status: in_progress

---

## Coga base prompt

# Coga base prompt

You are an agent working inside Coga, this team's repo-level workbench for
directing coding agents. The ticket, its contexts, and the current workflow
step say what to do; everything below says how to operate. Work from the task
files: durable state, not session memory, is the source of truth.

## Check the starting checkout

The **Checkout (runtime)** notice at the end of this prompt states what
launch observed and did to this checkout: the branch, any ticket it projected,
and who returns the checkout. Where it says launch prepared the checkout, do
not repeat that setup or return yourself. Where it says no preparation was
supplied or no branch was set up, read `coga/checkouts` from the configured
contexts root or bundled package and follow it before editing.
If the checkout is unexpected or preparation failed, read
`coga/checkouts/launch-boundary` and follow its checkout recovery procedure.
Identify the branch's ticket, verify its current control-copy status and PR
merge status, and inspect uncommitted edits separately before proposing
changes. Explain what is finished and what remains unknown. Do not
automatically stash, discard edits, or switch an occupied checkout merely to
get onto `main`; resolve unclear ownership or intent through session conduct.

## Reconcile before publishing

Reconcile with current main before publishing or handing off edits. Main is
the shared source of truth and is expected to move during your work. Read and
follow `coga/checkouts/reconciliation` from the configured contexts root or
the bundled package; it applies to code, documentation, ticket edits, and
ad-hoc sessions alike. Resolve ordinary drift yourself; escalate unclear
intent or unavailable access per session conduct. Preserve unique work
throughout reconciliation.

## The ticket and blackboard

The composed header gives the exact task path. Use it; do not reconstruct it
from the slug. A task is either a `.md` ticket or a directory containing
`ticket.md`; directory-form tasks may also carry attachments.

After YAML frontmatter, a normal ticket has two regions separated by exactly
`<!-- coga:blackboard -->`:

- **Above the fence: ticket body.** This is durable task intent and state.
  You may edit `contexts` and the body sections — nothing else. Every other
  frontmatter field, including `status`, `step`, `workflow`, `owner`, `agent`,
  `skills`, `secrets`, and any repo extension field, is owned by
  CLI commands and humans; editing one silently reroutes later launches. A
  specialized authoring skill may grant an explicit exception; absent that,
  the allowlist holds. There is no assignment field to edit: who holds the
  ticket is derived from the current workflow step's `assignee:` role.
- **Below the fence: blackboard.** This is free-form working memory. Read it
  first, update it throughout the step, and leave a useful handoff.
  Superseded design history stays on disk under the `coga/blackboard`
  convention ("Superseded designs"); the composed blackboard includes a
  pointer for deliberate reading.

The retained audit trail lives separately in repo-global `coga/log.md`.
Do not edit it: Coga commands write it. Put your observations on the
blackboard.

When editing frontmatter, preserve existing fields, order, and formatting. Do
not invent fields. Write lists one item per line:

```yaml
contexts:
  - email/payment-flow
  - stripe/idempotency
```

## Boundaries

- Do not run `coga launch` from inside an agent launch. Use a subagent or edit
  files directly. Script-mode launches, which run a skill rather than another
  agent, are fine.
- Do not edit `coga.toml` or `coga.local.toml`.

---

## Ticket loop

# Ticket loop

This layer composes only for a task ticket. A stateless `bootstrap/<name>`
target has no blackboard, workflow, or lifecycle; its own ticket says how it
finishes.

## The loop

1. **Start from the blackboard.** It is composed into this prompt below, not
   a file to go open: the working memory carried across stateless sessions,
   holding prior plans, findings, decisions, and open blockers. Read it as
   current state before planning anything.
2. **Do the current step.** Follow the ticket, contexts, and step skill. Record
   useful findings and decisions, with reasons, on the blackboard as you go.
   Keep it concise enough to compose into the next launch.
3. **Reconcile before publishing or handing off edits**, as the base prompt
   directs.
4. **Run `bump` as the *last* thing in the current step, then stop.**
   `coga bump <id>` is the only command that advances a workflow. Run it after
   the work is complete and the blackboard is current.
   On the final step, `coga bump` marks the task `done`. At an owner-controlled
   gate, bump only when the human explicitly asks you to advance or close it.
5. **Never stop silently.** If you cannot reach the transition, escalate the
   way the `Session conduct` layer in this prompt directs. Do not leave
   completed or blocked work invisible.

## Finishing the step

- **One transition, one step.** `coga bump <id>` reads the current step and
  advances exactly once. Run it with no step selector: `--to` and `--backward`
  are human-only. After bumping, exit cleanly. One step, one session: do not
  read or work the newly selected step in this process. Under a `coga launch`
  supervisor, `coga bump`, `coga mark done`, `coga mark canceled`, and
  `coga block` each end your session and let the supervisor spawn what comes
  next. How the supervisor chains steps is in `coga/launch`; you do
  not drive it.
- **API/manual sessions don't chain.** After a bump outside `coga launch`, the
  human relaunches the next step. Do not call `coga launch` yourself.
- **Do not go backward.** Escalate incorrect earlier work instead of changing
  the frozen workflow or trying to rewind it yourself.
- **No workflow means no bump.** Finish a workflow-less ticket with
  `coga mark done <id>`. Never set `status: done` by hand.

## Blocking and FYIs

Use `coga block --task <id> --reason "<specific ask>"` only when a concrete
human answer or unavailable capability prevents progress. It records the ask,
sets `status: blocked`, notifies the owner, and ends a launched session. Stop
after blocking. The `Session conduct` layer in this prompt is what decides
whether input is available and how to escalate; read every other instruction
to block or to ask, workflow step skills included, through it.

Make the reason actionable. Prefer "Retry policy needs a maximum backoff for
429s" to "Unclear what to do."

State transitions notify on their own. Add a one-line FYI only when useful:

- `coga bump <id> --message "<FYI>"` attaches it to the step handoff.
- `coga slack --task <id> --message "<FYI>"` sends one without a transition.

Neither replaces `coga block`. Put longer detail on the blackboard.

---

## Session conduct — megalaunch queue

This session is one step in a sequential `coga megalaunch` queue. The REPL has
a TTY so work can stream live and a human can interrupt, but the TTY is
transport, not evidence that a human is waiting to answer. Input you do not
already have is unavailable.

- State a concise plan and its tradeoff, then continue. Do not ask for plan
  confirmation or end a turn waiting for permission; a present human can
  redirect you while you work.
- Do not ask-and-wait for missing input here. If a concrete decision,
  credential, permission, or unavailable capability truly prevents progress,
  run `coga block --task <slug> --reason "<specific ask>"` as the terminal
  action. Merely saying that you are blocked leaves the queue hanging and
  does not notify the owner.
- When another Coga task is the blocker, include that task's exact
  path-qualified slug in `--reason`. Megalaunch can then recognize when the
  dependency finishes later in this run and retry this task automatically.
- **Existing blocker-resolution exception.** If the composed prompt includes
  `Resolve the open blocker first`, the human explicitly selected this task
  to resolve those already-open asks. Discuss those asks with them, then run
  `coga unblock <slug> --answer "<resolution>"` and continue if resolved, or
  terminally `coga block` again if unresolved. This exception is only for the
  existing asks; new unavailable input still follows the queue rule above.
- If a code step cannot create the feature branch because the sandbox mounts
  `.git` read-only, follow the independent `/tmp` clone fallback in the
  `code/implement` skill before treating it as a blocker.
- Finish the workflow step with `coga bump`, `coga mark done`, or `coga block`.
  An authorized `coga mark canceled` transition also releases the queue; use it
  only when intentional abandonment is the task decision.
  A normal final response or an agent CLI `task_complete` event does not signal
  Coga and does not release the queue.

---

## Repo context

# Context

This is Coga's own repository: the Python package in `src/coga/`, its tests
in `tests/`, and the canonical topic library in `docs/contexts/`. `AGENTS.md`
holds the repository guidelines. Attach `coga-dev/principles` to tickets that
change the README or Coga's design.

---

## Current step: implement (skill: code/implement)

---
name: code/implement
description: Agent step for a code change. On the branch launch prepared (or one you set up per `coga/checkouts` when it did not), implement, test, commit, push, and hand off. Stops before the PR — that belongs to a later step.
---

# Implement the change

You are doing the actual code change, in the checkout this session was
launched from. The prompt's **Checkout (runtime)** notice says where you
are: under `coga launch` the feature branch is already created or reused,
its `branch:` linkage is on control, and launch returns the checkout after
you bump. If the notice says no branch was set up, or none was supplied,
follow `coga/checkouts` (its `manual` leaf) for the moves launch would have
made. **Do not open a PR yet** — the later `code/open-pr` step does that,
after review and fixes.

## Order of operations

1. **Read the ticket carefully.** Description, acceptance criteria,
   referenced files. If anything is ambiguous, don't guess: write the
   ambiguity to the blackboard and escalate per your launch mode — ask
   the attending human, or `coga block` in a queue run.

   When adding or revising code facts in the ticket's `## Context`,
   **Cite module plus symbol, never a bare line number.** For example,
   `src/coga/git.py` plus `git.sync_task_state`. If a line range helps
   navigation, name the symbol first and mark the range as an aid. Explain
   the relationship that makes the fact relevant, so the explanation survives
   a refactor. Apply this even to a raw `coga create` ticket that never passed
   through guided authoring or a design step.
2. **Close already-satisfied tickets directly.** If every requested
   checklist item has already landed in other work and there is genuinely
   no diff or PR to create, do not manufacture one and do not
   `coga block` — a blocker is for an unanswered human question, not for
   finished work. A branch launch prepared stays unused; leave it to the
   existing cleanup. Write per-item evidence under `## Already satisfied`
   on the blackboard. Before closing, file every open item the ticket or
   blackboard still records as its own draft (`coga create`) and link it,
   since a closed ticket owns nothing (`coga/workflows`, "Obligations the
   merge does not discharge"). Then run `coga mark done <slug>` and stop.
   Use this only when the evidence is concrete; if a human decision is
   genuinely needed, escalate that ask per your launch mode instead (ask the
   attending human; `coga block` in a queue run).
3. **Confirm the checkout.** Check HEAD against the notice. On a prepared
   branch the only entry dirt is this ticket, projected unstaged from
   control: write your notes and handoff there, and never stage, commit, or
   restore it. A notice that reports kept local commits (ahead or diverged)
   means reconcile them per `coga/checkouts/reconciliation` before pushing.
   Anything unexpected — another branch, other dirt — means stop and follow
   `coga/checkouts/launch-boundary`'s recovery: ask the attending human, or
   `coga block` in a queue run. Without a prepared branch, perform the
   `coga/checkouts` manual start check and branch setup, including publishing
   `branch:` before switching. Work parked for days drifts: start from
   current `main`, not from where the last session left off.

   **Read-only Git: the sandbox clone fallback.** A managed sandbox may
   allow source edits while mounting `.git` read-only, so your first commit
   on the prepared branch is refused. Stop implementation writes and follow
   `coga/checkouts/sandbox-clone` ("First refusal after launch switched"):
   preserve verified copies of all work, keep the prepared branch, and hand
   recovery to the host; do not continue in a new clone, allocate another
   branch, or bump. When the ticket already records a `worktree:` clone,
   the notice names it: change code only there and keep the ticket in this
   checkout. A manual session that cannot create its branch makes the clone
   that topic describes. In every clone, on creation and on each resumed
   session, seed its local config with the ordinary `seed_local_config.py`
   attachment beside this skill:

   ```bash
   python /resolved/code/implement/seed_local_config.py /primary/repo/coga /feature/repo
   ```

   The first argument is the primary directory containing `coga.toml`; the
   second is the clone's Git root. Resolve this skill local-first, falling
   back to the installed bundled skill (`coga/checkouts/sandbox-clone`, "What
   a fresh checkout lacks"). Stop on failure; never synthesize an actor.
4. **Implement on the feature branch.** Match existing code style. Keep changes scoped to the
   ticket — no opportunistic refactors. If you find a real adjacent bug,
   note its symptom, affected code, evidence or reproduction, and any
   existing follow-up ticket reference for the blackboard (write it with the
   handoff in step 11); don't fix it here.
   State what remains unresolved. `retro/done-ticket` owns carrying that
   finding into a durable context before deleting this ticket, so the
   blackboard is a handoff, not the bug's final home.
5. **Test.** Add a regression test before the fix when the ticket is a
   bug. Run `python -m pytest`. If validation behavior changed, run
   `coga validate --json` against the repo's seeded fixture. **Make new tests
   conform to the existing suite, not to your own taste** — agents
   reliably skip this because a clean-from-scratch test is easier to
   write than one that matches a quirky neighbor:
   - Read a sibling `tests/test_*.py` first and mirror its naming,
     structure, and fixture style. Match the suite; don't reinvent it.
   - Reuse the project's existing harness and helpers. Do not introduce
     a new test framework, assertion library, or mocking dependency the
     repo doesn't already use.
   - Keep coverage deterministic and low-creating: no real time,
     network, or filesystem nondeterminism; no sprawling mocks where a
     fixture or a plain call would do.
6. **Update the seeded fixture** when behavior affects task layout,
   prompt composition, or workflow semantics. The repo's agent
   instruction file (`AGENTS.md` or `CLAUDE.md`) names the fixture and
   when it must change.
7. **Commit.** Conventional, present-tense summary line. Reference the
   ticket slug in the body. One commit per logical change is fine.
8. **Freshen against the control branch.** With `<remote>` and `<control>`
   from `[git].remote` and `[git].control_branch` in `coga.toml` (defaults
   `origin` and `main`), run `git fetch <remote> <control> && git rebase
   FETCH_HEAD` on the feature branch, preserving the projected ticket as
   `coga/checkouts` describes; if commits came in, re-run the tests and fix
   what broke. Apply `coga/checkouts/reconciliation` when reconciling changes
   or deciding what needs human input. The later `coga open-pr` refuses a
   branch missing material commits from `<remote>/<control>`, and as a
   script it has no judgment to rebase with — freshness lands in the agent steps,
   while judgment is available.
9. **Push.** `git push -u <remote> <branch-name>` (add `--force-with-lease`
   when a rebase rewrote an already-pushed branch). Stay on the branch when
   launch returns the checkout; a manual session performs the
   `coga/checkouts` end-of-step return instead. In the sandbox clone layout,
   push from the clone.
10. **Prepare publication evidence.** Read [coga/pr-publication/preparation](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/bootstrap/contexts/coga/pr-publication/preparation/SKILL.md),
    “Presentation and review-depth rubric” and “Preparation record”. Before the
    handoff, retain the actual implementing agent identity from this session
    (including overrides), exact check commands/results/counts and omission
    reasons, and the full tested head and merge-base OIDs. Do not substitute the
    ticket's configured agent or a planned test command for execution evidence.
    If tests ran on uncommitted changes, establish that the committed tree is
    identical before associating that receipt with the commit. A rebase or later
    fix needs fresh verification; never just change an old receipt's OID.

    Write the structured `## PR` preparation on the live blackboard with the
    handoff below: actual-change title, advisory depth and rationale,
    implementation/deviations/limitations, reasons for every actual diff path,
    and check/review receipts using that topic's schema. This is required even
    when the workflow has no later code review. If review has not run, say so
    and why; design approval does not count as code review. Later judgment
    steps update this record after their fixes and completed reviews. Test
    obligations remain those of this workflow (including step 5 above).
11. **Hand off and bump — this is what ends the step.** Write the handoff
   into the live ticket (the projected copy under launch, `main` in a manual
   session): what changed, decisions, and anything the next step needs.
   Confirm `## Dev` records this attempt's `branch:`. Then run
   `coga bump <slug>`. It publishes the ticket and advances the workflow;
   it is the *only* thing that does so — there is no autobump. Where the
   workflow declares `requires: branch`, `coga bump` refuses to advance
   unless this checkout's ticket copy has a usable `branch:` line under
   `## Dev`; if it refuses, record the line rather than working around it.
   If you stop without bumping, the workflow stalls on `implement`, the
   later steps never start, and your work is invisible even though the
   branch is pushed. If something keeps you from reaching it, escalate per
   your launch mode — ask the attending human, or `coga block` with a reason
   in a queue run.

## Acceptance for this step

- The feature branch is recorded as `branch:` under `## Dev` (plus
  `worktree:` for a sandbox clone), contains the latest `origin/main`, and
  is pushed.
- Tests pass locally.
- No PR yet. The blackboard reflects what changed and any decisions made.
- `coga bump <slug>` ran last — the step is not done until it has. A manual
  session left the checkout on a clean, fast-forwarded `main`.
- Or, for the already-satisfied path only: the blackboard records concrete
  evidence under `## Already satisfied`, and `coga mark done <slug>` has
  closed the ticket. An unused prepared branch needs no commit or PR.

## What this skill does NOT do

- Open a PR — that's `code/open-pr`.
- Self-QA the diff — that's `code/self-qa`.
- Resolve unrelated test failures it didn't cause.

## Gotchas

- If the test suite fails for reasons unrelated to your change, write
  it to the blackboard and escalate per your launch mode rather than
  masking it.

---

## Task description

Add an explicit validation mode for checkouts that are expected to execute
mutating or recurring work. Today `coga validate` reports a missing
`coga.local.toml` user as a warning and exits 0 so a fresh clone can run
diagnostics. That is useful for inspection, but it is a false-green when
`validate` is used as a headless-runner preflight: the real `coga recurring`
then exits 2 before doing work.

Preserve the diagnostic-friendly default and add
`coga validate --execution-ready`. In that mode the existing `missing-user`
issue becomes an error and the command exits 1.

---

## Task-specific context

- `validate.py` intentionally emits `missing-user` with warning severity so
  read-only commands remain usable in a fresh clone. Do not remove that default
  behavior.
- Mutating commands load configuration with `require_user=True`; the recurring
  sweep does too, while `recurring list` and ordinary validation do not.
- Since Coga PR #613, `coga recurring --all` treats a missing-user checkout as
  an unconfigured non-target and does not fail the aggregate run. A real
  scheduler target can therefore be skipped while the parent exits
  successfully unless provisioning has its own strict preflight.
- The immediate downstream case is FastJVM/patents PR #130: its headless
  runbook can resolve every secret and pass `validate --check-slack`, yet the
  scheduled sweep still cannot run until `coga.local.toml` contains
  `user = "runner"`.
- Implementation anchors are `src/coga/commands/validate.py` and
  `src/coga/validate.py` (`_missing_user_issue`, `run`, `validate_task`, and
  `_main`), with coverage in `tests/test_cli.py` and
  `tests/test_validate.py`.

CLI contract:

- Default validation keeps `missing-user` at warning severity and exits 0 when
  there are no other errors.
- `--execution-ready` keeps issue kind `missing-user`, promotes severity to
  `error`, and exits 1. Text and `--json` output must agree.
- The flag works for whole-repo and `--task` validation. With `--fix`, it
  remains an error because Coga must not invent the actor.
- It composes normally with `--check-slack` and `--check-github`; their existing
  incompatibility with `--task` is unchanged.
- Both the Typer command and `src/coga/validate.py::_main` expose identical
  behavior.

Done means:

- `coga validate --execution-ready` returns 1 and a clear `missing-user` error
  when the local actor is absent;
- ordinary `coga validate`, `status`, `show`, and other intended read-only
  fresh-clone diagnostics retain their current behavior;
- text and JSON output, both CLI entrypoints, `--task`, `--fix`, and the network
  check combinations follow the contract above;
- The local-only `coga-dev/testing` and `coga/recurring/scheduling` (with its
  packaged twin) show strict validation as the preflight
  before invoking recurring work. No external repository documentation is
  required by this ticket.

Out of scope: automatically choosing or copying an actor identity. Worktree
local-config propagation belongs to sibling ticket
`op/propagate-local-coga-config-into-worktrees`. This ticket does not change
`recurring --all` discovery or its intentional skip-unconfigured behavior;
each real scheduler target must run strict validation in its own checkout
before the sweep.

---

## Blackboard (current state)

The blackboard is a notepad to be written to often as the human and agent works through a task.

---

## Checkout (runtime)

No checkout preparation was supplied for this prompt: nothing here claims that a branch was prepared or that this checkout will be returned. Before editing, follow `coga/checkouts` ("Start, work, end") yourself.
