---
slug: secrets-instructions-correction
title: Launch activates a draft before its preflight checks refuse it
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 2 (review-design)
---

## Description

**Why this ticket exists.** The trigger was a malformed `secrets:` block, but
the defect has nothing to do with secrets. `coga launch` writes the
draft → `active` transition to disk *before* it runs the preflights that can
refuse the launch, so a ticket whose session never started is left on disk
claiming work began — and the operator hand-repairs state the CLI is supposed
to own. Any refusal in that window does it; the bad `secrets:` is just the
one that got reported. Re-verified against `main` on 2026-08-14: the line
numbers below still hold.

`coga launch` performs a **durable** draft/paused → `active` transition *before*
it runs the preflight checks that can refuse the launch. A ticket with a
malformed `secrets:` block — the originally reported trigger — is therefore
written to disk as `active`, with its `workflow:` snapshot frozen, its `step:`
seeded, an `activated … — auto on launch` line appended to `coga/log.md`, and a
git state sync pushed, and *only then* refused. The operator is left with a
ticket that says work has started on a session that never ran, and has to
hand-repair state that CLI commands are supposed to own.

Concretely, in `src/coga/commands/launch.py`:

| line | what happens |
| --- | --- |
| 542 | `_auto_activate(...)` — **durable write**: `mark_active` → `prepare_active`, `ticket.write`, `append_log`, `git.sync_task_state` |
| 544 | `_refuse_human_handoff_launch` — can refuse |
| 546 | TTY check — can refuse |
| 557 | agent-type resolution — can refuse |
| 568 | agent CLI binary check — can refuse |
| 579 | `compose_prompt` preflight — can refuse |
| **591** | **`build_launch_env(cfg, ticket.secrets)` → `SecretError` — the reported refusal** |
| ~620 | `_preflight_push_auth` — can refuse |
| 674 | `mark_in_progress` — the flip the preflights actually guard |

The comment at 573–577 ("Fail loud BEFORE flipping status … don't flip the
ticket to in_progress") is accurate only about the `in_progress` half. The
`active` half already happened at 542, which is exactly the failure the report
describes.

Two paths in this same function already do the right thing, so the fix is to
make the third consistent rather than to invent a policy:

- **blocked-resume** defers `_auto_activate` to line 666 — after every preflight,
  immediately before the `in_progress` flip.
- **assist** never activates early at all: `_prospective_assist_ticket`
  (line 1045) builds an in-memory activated *view* via `prepare_active` and
  publishes lifecycle state only at the final gate. Note line 542 is already
  guarded by `assist_publication is None`.

`mark.py:445 prepare_active` is documented as precisely this "pure preparation
boundary … without writing durable state", with `mark_active` as "the durable
wrapper". The normal draft/paused path is the one caller that skips the
boundary and writes immediately.

## Context

Original report was a raw paste; the Description above was rewritten at design
time after the scope block was resolved.

**The "wrong instruction" half of the original premise does not reproduce here.**
Every instruction in this repo already documents the correct list form:

- `coga/tasks/_template/ticket.md:12` — "one `- NAME: <ref>` list entry per secret"
- `docs/operations.md:183` — "Each entry is a single-key map", list example
- `coga/contexts/coga/architecture/SKILL.md:156` — "a list of single-key maps `- NAME: <ref>`"
- `coga/contexts/coga/secrets/SKILL.md:28` — list example
- `src/coga/config.py:1094` — the validator error quoted in the original report

A repo-wide grep for a mapping-form `secrets:` example returns nothing outside
this ticket's own body. The blocker asking Zach to choose between (a) a wrong
instruction in another repo, (b) the launch ordering bug, and (c) both was
resolved to **(b)**: (a) has no target in this repo, so it cannot be actioned
here; it survives as an Open Question on the blackboard for `review-design`.

Note the ticket slug still says `secrets-instructions-correction`, which now
describes the trigger rather than the fix. Renaming is the owner's call at
`review-design`; the malformed `secrets:` block is the *reproducer*, not the
subject.

**[2026-08-14] Retiring this ticket was proposed and rejected.** The reasoning
was that the premise doesn't reproduce in this repo — true of half (a), the
documentation fix, and false of half (b). Half (b) was re-checked against
`main` that day and is live: `_auto_activate` at `launch.py:542` still sits
above the `SecretError` refusal at 591, the push-auth preflight at 614, and
the `in_progress` flip at 674. Deleting the ticket would not have deleted the
bug. The stale slug is what made it illegible enough to look disposable.

## Acceptance Criteria

- [ ] Launching a **draft** ticket whose `secrets:` is a mapping (or otherwise
      raises `SecretError`) leaves it on disk with `status: draft` — unchanged
      frontmatter, no `activated …` line in `coga/log.md`, no state sync.
- [ ] The same holds for every other refusal between the old line 542 and the
      `in_progress` flip: missing agent CLI, no TTY, `ComposeError`, and failed
      push auth all leave a draft ticket as `draft`.
- [ ] The same holds for a **paused** ticket: a refused launch leaves it
      `paused`.
- [ ] A launch that passes all preflights is behaviorally unchanged: the ticket
      ends `in_progress`, and the log still shows the `activated (draft →
      active) — auto on launch` line before the `started (active → in_progress)`
      line.
- [ ] The activation refusals `_auto_activate` maps today still fail loud with
      the same operator-facing messages and exit non-zero: `WorkflowMissing`,
      `WorkflowError`, `RequiredExtensionMissing`, `BlackboardNeedsSynthesis`.
      A workflow-less draft is still refused *before* any agent spawn.
- [ ] `compose_prompt` and `_refuse_human_handoff_launch` still see an activated
      view (frozen workflow, seeded `step:`) — i.e. deferring the durable write
      does not regress step-assignee refusal or prompt composition for drafts.
- [ ] The blocked-resume path (line 666) and the assist path are untouched in
      behavior.
- [ ] New test: a draft ticket + bad `secrets:` → non-zero exit, ticket still
      `draft`, no agent spawned, `coga/log.md` byte-identical to before.
- [ ] `python -m pytest` passes; `coga validate --json` is clean.

## Proposed Shape

One file carries the change: `src/coga/commands/launch.py`. No signature
changes in `mark.py`, `config.py`, or `compose.py` — `prepare_active` and
`mark_active` already expose the needed boundary.

1. **Split `_auto_activate` (line 1295) into prepare + commit.** Keep its
   existing `except` ladder — that error-message mapping is the valuable part
   and must not be duplicated.
   - `_prepare_auto_activate(cfg, ref, ticket) -> None` — calls
     `prepare_active(cfg, ref, ticket)` inside the current `try`, keeping every
     `_bail` message verbatim. Mutates `ticket` in memory only.
   - `_commit_auto_activate(cfg, ref, ticket, *, prior, sync_state=True) -> None`
     — calls `mark_active(...)` with the existing `log_message` /`echo`
     (`activated ({prior} → active) — auto on launch`). `prior` must be captured
     *before* the prepare call, since `prepare_active` overwrites
     `ticket.frontmatter["status"]`; today `_auto_activate` reads it at entry.
   - `_auto_activate` stays as `prepare` + `commit`, keeping line 666
     (blocked-resume) working unchanged. There are exactly two call sites, both
     in this file (542 and 666) — verified by `grep -rn "_auto_activate" src/`.
     `mark_active` re-runs `prepare_active` internally, which is harmless and
     idempotent on an already-`active` in-memory ticket.

   Two existing tests already pin this helper and should keep passing untouched
   — treat a change to either as a signal the refactor drifted:
   `test_launch_auto_activates_draft_and_paused` (tests/test_launch.py:2178,
   happy path → `in_progress`) and `test_launch_auto_activate_bails_without_workflow`
   (tests/test_launch.py:2289, workflow-less draft → exit 2, "no workflow").
2. **At line 536–542, swap the durable call for the prepare call.** Capture
   `prior_status = ticket.status` alongside it — a local, because the commit is
   now far away and `ticket.status` will read `active` by then.
3. **Commit the activation just before the `in_progress` flip.** Immediately
   above the `if (... ticket.status == "active" and assist_publication is None)`
   block at 668, add: if this launch prepared an activation (`prior_status in
   {"draft", "paused"}` and `assist_publication is None`), call
   `_commit_auto_activate(...)`. Ordering with the existing line 666
   blocked-resume `_auto_activate` must stay mutually exclusive — one launch
   activates via exactly one of the two paths.
4. **Fix the stale comments.** Lines 531–534 ("The flip to `in_progress` still
   happens later … so this only does the `mark active` half") and 573–577
   ("Fail loud BEFORE flipping status") both describe the old ordering; rewrite
   them to say no durable lifecycle write happens until every preflight passes.
5. **Tests** in `tests/test_launch.py`, beside the existing secret tests
   (~1455–1495):
   - `test_launch_draft_bad_secrets_leaves_ticket_draft` — the primary
     regression. Assert status, the absence of an `activated` log line, and no
     spawn. Model it on `test_launch_fails_loud_on_op_read_error`, but from a
     **draft** fixture — that existing test starts from `active_task`, which is
     why it passes today and masks the bug. Leave it as-is; it still covers the
     already-active case.
   - `test_launch_draft_missing_agent_cli_leaves_ticket_draft` — proves the fix
     is ordering, not secret-specific.
   - `test_launch_draft_no_workflow_still_refuses` — guards criterion 5, that
     splitting `_auto_activate` did not lose the activation error ladder.
   - One happy-path assertion that a successful draft launch still logs
     `activated` then `started`, in that order.

Suggested order of work: (1) + (2) + (3) together (the refactor is not
separable from the move), then (4), then (5) — or write the primary regression
test first and watch it fail, which is cheap here.

## Out of Scope

- **Accepting the mapping form.** The list shape is deliberate
  (`src/coga/config.py:1094`); `coga/contexts/coga/architecture/SKILL.md:156`
  explains why a bare-string entry and a raw literal are both rejected. Not
  touched.
- **The `weather-events` repo.** If the instruction that produced the mapping
  form lives there, the fix is over there and needs a filename — Open Question,
  not this PR.
- **Adding a "wrong form" counter-example to this repo's docs.** Plausible
  follow-up, but this repo's instructions are already correct, so it is a
  separate judgment call for the owner.
- **`coga megalaunch`'s early activation.** It activates picked tickets up front
  (`megalaunch.py:1046`, `activated … — explicit megalaunch pick`) and
  `_preflight_agent_launch` requires `active`/`in_progress` by design. That is a
  deliberate different contract — an explicit human pick *is* the activation
  decision. Untouched here; flagged as an Open Question.
- **Restructuring the preflight gauntlet** into a declarative list. Tempting
  while in this code; a much larger diff than the ordering fix warrants.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design notes

Scope resolved to the launch ordering bug (see Blockers below for the full
reasoning). Verified by reading, not assumed:

- `src/coga/commands/launch.py:542` `_auto_activate` is a durable write —
  `mark_active` → `prepare_active` + `ticket.write` + `assert_task_valid` +
  `append_log` + `git.sync_task_state` (`src/coga/mark.py:472`).
- It sits *above* every refusing preflight, including the `SecretError` one at
  591. Line numbers in the Description table were read off the file directly.
- Nothing between 542 and 674 re-reads the ticket from disk (checked), so
  deferring the durable write and carrying an in-memory activated `ticket` is
  safe for the non-assist path.
- `src/coga/mark.py:445` `prepare_active` already exists as the pure
  prepare/commit boundary this fix needs — no new abstraction required.
- The assist path (`_prospective_assist_ticket`, line 1045) and blocked-resume
  (line 666) already follow the target ordering. This makes the fix a
  consistency change with two in-repo precedents rather than a new policy.
- `tests/test_launch.py:1492` `test_launch_fails_loud_on_op_read_error` asserts
  `status == "active"` after a secret failure — but starts from an
  already-active fixture, so it never exercises draft→active. That is why the
  bug ships green.

## Open Questions

1. **Does a wrong instruction actually exist in `weather-events`?** (Zach's
   original ask, half (a).) It cannot be actioned from this repo — no
   mapping-form `secrets:` example exists here outside this ticket's own body.
   If it does exist there, name the file and it becomes a separate ticket in
   that repo. Answering "no / don't care" closes this cleanly; the code fix
   stands either way.
2. **Should the slug be renamed?** `secrets-instructions-correction` now
   describes the reproducer, not the change. Something like
   `launch-activates-before-preflight` matches the spec. Owner's call — I did
   not rename, since the slug is the task identity.
3. **Is `coga megalaunch`'s up-front activation intended to stay as-is?** It
   activates all picked tickets before launching any (`megalaunch.py:1046`),
   and `_preflight_agent_launch` requires `active`/`in_progress`, so the same
   "activated but never ran" residue is reachable there — a queue pick whose
   secrets are malformed fails at `build_launch_env` (`megalaunch.py:1190`)
   with the ticket already flipped. I read this as a deliberately different
   contract (an explicit human pick *is* the activation decision) and left it
   out of scope. Say so if you'd rather it match `launch`.
4. **Should a refused launch of a ticket that was already `active` be touched
   at all?** Current behavior leaves it `active`, which seems right — nothing
   was falsely claimed. The spec preserves it. Flagging only because it is the
   case the existing test covers.

---

## Blockers

- [x] [2026-08-13 22:21] [agent:claude] id=20260813T222158 Zach to confirm the ticket's scope before design starts. The premise does not reproduce in this repo: every instruction here already documents the correct '- NAME: <ref>' list form (coga/tasks/_template/ticket.md:12, docs/operations.md:183, coga/contexts/coga/architecture/SKILL.md:156, coga/contexts/coga/secrets/SKILL.md:28, src/coga/config.py:1094), and a repo-wide grep finds no mapping-form example outside this ticket's own body — so there is no instruction here to correct. Which did you actually hit: (a) the wrong instruction lives in another repo (weather-events?) — name the file; (b) the real defect is that coga launch marks the task active BEFORE validating secrets:, so a typo strands the ticket and needs hand-repair — a code fix in src/coga/; or (c) both, as one ticket or split. Contexts are still unset pending that answer.
  resolved: [2026-08-13 22:54] [human:nicktoper] Scoped to (b) on reproduced evidence, since (a) has no target in this repo. Re-verified: no mapping-form 'secrets:' example exists anywhere here outside this ticket's own Description, so there is no instruction in this repo to correct; if the bad instruction lives in weather-events, that fix belongs in that repo and needs a filename only Zach can supply — carried forward as an Open Question for the owner at review-design rather than blocking a second time. (b) does reproduce and is precise: src/coga/commands/launch.py:542 calls _auto_activate (a durable write — status draft/paused to active, freezes the workflow snapshot, seeds step, appends the log, git-syncs) BEFORE the fail-loud preflight gauntlet at 544-591 (human-handoff refusal, TTY check, agent-type resolution, CLI-binary check, compose preflight, and the secrets preflight at 591 that raises SecretError). So a malformed 'secrets:' on a draft ticket strands it in 'active' with a frozen workflow and a spurious activation log entry. Two internal precedents show the intended shape: the blocked-resume path already defers _auto_activate to line 666, after every preflight, and the assist path already composes an in-memory prospective activation via _prospective_assist_ticket/prepare_active without writing. mark.py:445 prepare_active is documented as exactly this 'pure preparation boundary'. Fix is to make the normal draft/paused path do what those two already do. Existing coverage masks the bug: test_launch_fails_loud_on_op_read_error starts from an already-active task and asserts only that it stays active.
