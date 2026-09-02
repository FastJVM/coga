---
slug: launch-activates-before-preflight
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
one that got reported.

`coga launch` performs a **durable** draft/paused → `active` transition *before*
it runs the preflight checks that can refuse the launch. A ticket with a
malformed `secrets:` block — the originally reported trigger — is therefore
written to disk as `active`, with its `workflow:` snapshot frozen, its `step:`
seeded, an `activated … — auto on launch` line appended to `coga/log.md`, and a
git state sync pushed, and *only then* refused. The operator is left with a
ticket that says work has started on a session that never ran, and has to
hand-repair state that CLI commands are supposed to own.

Everything below is in `src/coga/commands/launch.py`, inside `_launch`, in
source order. Anchors are symbols and guard conditions, not line numbers —
`_launch` has grown ~790 lines since this spec was first written and every
line number in the original draft had rotted (re-verified against `main`
2026-09-02):

| where in `_launch` | what happens |
| --- | --- |
| the `ticket.status in {"draft", "paused"} and assist_publication is None` guard, under the comment "Typing `coga launch` *is* the readiness signal" | `_auto_activate(cfg, ref, ticket)` — **durable write**: `mark_active` → `prepare_active`, `ticket.write`, `assert_task_valid`, `append_log`, `git.sync_task_state` |
| next statement | `_refuse_human_handoff_launch` — can refuse |
| next | `_interactive_stdio_has_tty()` → `_refuse_tty_launch` — can refuse |
| next | `cfg.agent_type(launch_assignee)` → `ConfigError` — can refuse |
| next | `shutil.which(agent.cli)` → `agent_cli_missing_message` — can refuse |
| next | `compose_prompt(...)` → `ComposeError` / `FileNotFoundError` — can refuse |
| **next** | **`env = build_launch_env(cfg, ticket.secrets)` → `SecretError` — the reported refusal** |
| next | `_preflight_push_auth(cfg, ref, is_bootstrap=is_bootstrap)` — can refuse |
| final gate | the `ticket.status == "active" and assist_publication is None` guard → `mark_in_progress` — the flip the preflights actually guard |

The comment above `compose_prompt` ("Fail loud BEFORE flipping status … don't
flip the ticket to in_progress") is accurate only about the `in_progress` half.
The `active` half already happened at the top of that block, which is exactly
the failure the report describes.

Two paths in this same function already do the right thing, so the fix is to
make the third consistent rather than to invent a policy:

- **blocked-resume** defers its `_auto_activate` to the
  `if blocked_resume and … ticket.status == "blocked"` guard — after every
  preflight, immediately before the `in_progress` flip.
- **assist** never activates early at all: `_prospective_assist_ticket` builds
  an in-memory activated *view* via `prepare_active` and publishes lifecycle
  state only at the final gate (`_publish_assist_lifecycle_before_spawn`). Note
  the buggy call site is already guarded by `assist_publication is None`.

`mark.py`'s `prepare_active` is documented as precisely this "pure preparation
boundary … without writing durable state", with `mark_active` as "the durable
wrapper" that calls it and then writes. The normal draft/paused path is the one
caller that skips the boundary and writes immediately.

**A third call site now exists.** The script path — the
`elif not is_bootstrap and isinstance(ref, TaskRef) and ticket.status in
{"draft", "paused", "blocked"}` branch inside `if entry is not None:` — calls
`build_launch_env(cfg, ticket.secrets)` *then* `_auto_activate`, under the
comment "Secret resolution belongs before the activation write." That path
already fixed the reported symptom locally, for secrets only, and it is
deliberately upstream of the agent-only preflights because a `ticket.py` run
genuinely *is* work starting. It is out of scope to move, but it is a third
caller of `_auto_activate` and the refactor below must keep it working.

## Context

Original report was a raw paste; the Description above was rewritten at design
time after the scope block was resolved, and re-anchored to symbols on
2026-09-02.

**The "wrong instruction" half of the original premise does not reproduce here.**
Every instruction in this repo already documents the correct list form:

- `coga/tasks/_template/ticket.md` — "one `- NAME: <ref>` list entry per secret"
- `docs/operations.md` — "Each entry is a single-key map", list example
- `coga/contexts/coga/architecture/SKILL.md` — "a list of single-key maps `- NAME: <ref>`"
- `coga/contexts/coga/secrets/SKILL.md` — list example
- `src/coga/config.py` — the validator error quoted in the original report

A repo-wide grep for a mapping-form `secrets:` example returns nothing outside
this ticket's own body. The blocker asking Zach to choose between (a) a wrong
instruction in another repo, (b) the launch ordering bug, and (c) both was
resolved to **(b)**: (a) has no target in this repo, so it cannot be actioned
here; it survives as an Open Question on the blackboard.

**Slug history.** This ticket was `secrets-instructions-correction` until
2026-09-02, renamed to `launch-activates-before-preflight` by the owner
because the old slug named the reproducer rather than the fix. `coga/log.md`
is append-only, so all history before that date is recorded under the old
slug — `coga show launch-activates-before-preflight` reconstructs nothing from
the log, and the audit trail for this ticket must be read by grepping
`secrets-instructions-correction` in `coga/log.md`.

**[2026-08-14] Retiring this ticket was proposed and rejected. [2026-09-02] It
was proposed again and rejected again on the same grounds.** The reasoning both
times was that the premise doesn't reproduce — true of half (a), the
documentation fix, and false of half (b). Half (b) was re-verified against
`main` on 2026-09-02 and is live: the durable `_auto_activate` still sits above
the `SecretError` refusal, the push-auth preflight, and the `in_progress` flip;
`_auto_activate` still calls `mark_active`; and
`test_launch_fails_loud_on_op_read_error` (`tests/test_launch.py`) still starts
from the `active_task` fixture, so the suite still can't see the bug. Deleting
the ticket would not have deleted the bug. What made it *look* disposable both
times was illegibility — the stale slug in August, and by September a spec
whose every line-number citation pointed at the wrong code.

## Acceptance Criteria

- [ ] Launching a **draft** ticket whose `secrets:` is a mapping (or otherwise
      raises `SecretError`) leaves it on disk with `status: draft` — unchanged
      frontmatter, no `activated …` line in `coga/log.md`, and no
      `Ticket: <slug> — active` state commit. (Note the precise wording: `_bail`
      exits through the `except SystemExit` handler in `_launch`, which still
      runs `_refresh_launch_checkout` → `refresh_coga_state_from_control`. A
      refused launch may therefore still produce *some* git activity; what must
      not exist is the activation commit.)
- [ ] The same holds for every other refusal between the activation call and the
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
      `WorkflowError`, `RequiredExtensionMissing`, `BlackboardNeedsSynthesis`,
      and `TaskValidationError`. A workflow-less draft is still refused *before*
      any agent spawn.
- [ ] `compose_prompt` still sees an activated view (frozen workflow, seeded
      `step:`) — this is what makes keeping the *prepare* call at the current
      site load-bearing (`compose.py` reads `ticket.current_step()` and
      `ticket.workflow`). `_refuse_human_handoff_launch` reads only
      `ticket.assignee` and does **not** depend on the activated view, so it is
      unaffected either way.
- [ ] The blocked-resume path, the assist path, and the script path are
      untouched in behavior.
- [ ] New test: a draft ticket + bad `secrets:` → non-zero exit, ticket still
      `draft`, no agent spawned, `coga/log.md` byte-identical to before.
- [ ] `python -m pytest` passes; `coga validate --json` is clean.

## Proposed Shape

One file carries the change: `src/coga/commands/launch.py`. No signature
changes in `mark.py`, `config.py`, or `compose.py` — `prepare_active` and
`mark_active` already expose the needed boundary.

1. **Split `_auto_activate` into prepare + commit.** Keep its existing `except`
   ladder — that error-message mapping is the valuable part and must not be
   duplicated. **Split the ladder along the same seam as the exceptions:**
   `mark_active` calls `prepare_active` first and only then writes, so
   `WorkflowMissing`, `WorkflowError`, `RequiredExtensionMissing`, and
   `BlackboardNeedsSynthesis` all originate in the *prepare* half, while
   `TaskValidationError` comes from the post-write `assert_task_valid` in the
   *commit* half. (`prepare_active` also raises `CancellationError` for a
   canceled ticket; `_auto_activate` does not map it today because launch
   refuses terminal tickets earlier. Don't add a handler — just don't lose the
   existing behavior.)
   - `_prepare_auto_activate(cfg, ref, ticket) -> None` — calls
     `prepare_active(cfg, ref, ticket)` inside a `try` carrying the four
     preparation `_bail` messages verbatim. Mutates `ticket` in memory only.
   - `_commit_auto_activate(cfg, ref, ticket, *, prior, sync_state=True) -> None`
     — calls `mark_active(...)` with the existing `log_message` / `echo`
     (`activated ({prior} → active) — auto on launch`), carrying the
     `TaskValidationError` `_bail`. `prior` must be captured *before* the
     prepare call, since `prepare_active` overwrites
     `ticket.frontmatter["status"]`; today `_auto_activate` reads it at entry.
   - `_auto_activate` stays as `prepare` + `commit`, keeping the blocked-resume
     and script call sites working unchanged. There are exactly **three** call
     sites, all in `_launch` — verified by `grep -rn "_auto_activate" src/`:
     the script-path branch, the buggy draft/paused agent-path branch, and the
     blocked-resume branch. Only the middle one moves.
     `mark_active` re-runs `prepare_active` internally, which is harmless and
     idempotent on an already-`active` in-memory ticket.

   Two existing tests already pin this helper and should keep passing untouched
   — treat a change to either as a signal the refactor drifted:
   `test_launch_auto_activates_draft_and_paused` (happy path → `in_progress`)
   and `test_launch_auto_activate_bails_without_workflow` (workflow-less draft
   → exit 2, "no workflow"), both in `tests/test_launch.py`.
2. **At the draft/paused agent-path guard, swap the durable call for the
   prepare call.** Capture `prior_status = ticket.status` alongside it — a
   local, because the commit is now far away and `ticket.status` will read
   `active` by then. **Initialize `prior_status: str | None = None` *above* the
   enclosing `try:`, not inside the guard.** Step 3's condition reads it
   unconditionally, and the guard does not fire for bootstrap refs, assist
   launches, already-active tickets, or blocked resumes — an in-guard-only
   assignment raises `UnboundLocalError` on every one of those paths.
3. **Commit the activation just before the `in_progress` flip.** Immediately
   above the `if isinstance(ref, TaskRef) and ticket.status == "active" and
   assist_publication is None:` block, add: if this launch prepared an
   activation (`prior_status in {"draft", "paused"}` and `assist_publication is
   None`), call `_commit_auto_activate(...)`. Ordering with the adjacent
   blocked-resume `_auto_activate` must stay mutually exclusive — one launch
   activates via exactly one of the three paths.

   Two operator-visible ordering changes follow from the move, neither of which
   any current test asserts. Both are acceptable; state them rather than
   discover them. (a) `mark_active`'s echo — `<slug>: active — auto on launch` —
   now prints *after* the `Launch: agent …` / `Launch: found agent CLI at …`
   lines instead of before. (b) `assert_task_valid(action="mark active")` runs
   inside the commit, so an activation-time validation failure now surfaces
   *after* the agent-CLI, compose, secret, and push-auth refusals rather than
   before it. The messages are unchanged; only which error the operator meets
   first changes.

   **Decide the lost-update window explicitly.** Today the activation write is
   instantaneous. Deferred, the in-memory `ticket` is held across
   `compose_prompt`, `build_launch_env` (which may shell out to `op read`), and
   `_preflight_push_auth` (a real network round-trip) — seconds — and then
   `mark_active` renders and overwrites `ref.ticket_path` wholesale, silently
   clobbering any concurrent edit. The blocked-resume path already carries this
   exact unguarded window, so accepting it is not a regression relative to the
   precedent being followed; the assist path, by contrast, *does* guard it
   (`_publish_assist_lifecycle_before_spawn` compares
   `ref.ticket_path.read_bytes()` against the bytes captured before the gate and
   refuses on drift). Either capture the pre-prepare bytes and refuse on drift,
   or record in the code comment that the window is knowingly accepted. Do not
   leave it unstated.

   While in the helper: `_auto_activate`'s `sync_state: bool = True` keyword is
   dead — no call site passes it. Drop it or keep it deliberately.
4. **Fix the stale comments.** The "Typing `coga launch` *is* the readiness
   signal … so this only does the `mark active` half" comment and the "Fail
   loud BEFORE flipping status" comment above `compose_prompt` both describe
   the old ordering; rewrite them to say no durable lifecycle write happens
   until every preflight passes. Two invariants the deferral now depends on
   belong in code comments, not only on this blackboard: (a) nothing between the
   prepare and the commit re-reads the ticket from disk on the non-assist path;
   and (b) `mark_active` re-running `prepare_active` is idempotent *because* the
   second run sees `prior_status == "active"` and therefore skips the draft-only
   blackboard-synthesis gate. A future change to either would break the split
   silently.
5. **Tests** in `tests/test_launch.py`, beside the existing secret tests
   (near `test_launch_fails_loud_on_op_read_error`):
   - `test_launch_draft_bad_secrets_leaves_ticket_draft` — the primary
     regression. Assert status, the absence of an `activated` log line, and no
     spawn. **Model it on `test_launch_refuses_unsynthesized_draft_blackboard`,
     not on `test_launch_fails_loud_on_op_read_error`** — the former already
     asserts exactly the shape these criteria want (`ticket_md.read_text() ==
     before` and `"activated (draft" not in _read_log(...)`). The latter starts
     from `active_task`, which is why it passes today and masks the bug; leave
     it as-is, it still covers the already-active case.
     **Fixture trap:** `prepare_active` checks the blackboard *before* the
     workflow, and only when `prior_status == "draft"`. A draft fixture whose
     blackboard still carries authoring notes refuses with
     `BlackboardNeedsSynthesis` and never reaches `SecretError` — the test would
     pass while asserting the wrong refusal. Use a clean blackboard and assert
     the refusal message, not just the status.
   - `test_launch_draft_missing_agent_cli_leaves_ticket_draft` — proves the fix
     is ordering, not secret-specific.
   - `test_launch_draft_no_workflow_still_refuses` — guards the criterion that
     splitting `_auto_activate` did not lose the activation error ladder.
     `test_launch_refuses_unsynthesized_draft_blackboard` pins the
     `BlackboardNeedsSynthesis` arm of that same ladder and must keep passing
     untouched.
   - One happy-path assertion that a successful draft launch still logs
     `activated` then `started`, in that order.

Suggested order of work: (1) + (2) + (3) together (the refactor is not
separable from the move), then (4), then (5) — or write the primary regression
test first and watch it fail, which is cheap here.

## Out of Scope

- **Accepting the mapping form.** The list shape is deliberate
  (`src/coga/config.py`); `coga/contexts/coga/architecture/SKILL.md` explains
  why a bare-string entry and a raw literal are both rejected. Not touched.
- **The `weather-events` repo.** If the instruction that produced the mapping
  form lives there, the fix is over there and needs a filename — Open Question,
  not this PR.
- **Adding a "wrong form" counter-example to this repo's docs.** Plausible
  follow-up, but this repo's instructions are already correct, so it is a
  separate judgment call for the owner.
- **The script path's own pre-activation.** It calls `build_launch_env` before
  `_auto_activate` deliberately, and activating before a `ticket.py` run is
  correct — that run is work starting. Left alone; it just has to keep working
  across the refactor.
- **The recurring runner's forced-run activation.** `recurring_runner.py`
  durably `mark_active`s a period ticket before invoking launch's preflights,
  and its docstring defends that ("If the later launch preflight fails, the task
  is at least live for a future normal sweep"). Deliberate, and untouched — but
  it means the criteria above are true of `coga launch`, not repo-wide. Noted
  because an implementer grepping `mark_active` will hit it.
- **`coga megalaunch`'s early activation.** It activates picked tickets up front
  (`activated … — explicit megalaunch pick`) and `_preflight_agent_launch`
  requires `active`/`in_progress` by design. That is a deliberate different
  contract — an explicit human pick *is* the activation decision. Untouched
  here; flagged as an Open Question.
- **Restructuring the preflight gauntlet** into a declarative list. Tempting
  while in this code; a much larger diff than the ordering fix warrants.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design notes

Scope resolved to the launch ordering bug (see Blockers below for the full
reasoning). Verified by reading, not assumed — re-verified 2026-09-02 and
re-anchored to symbols after every original line number rotted:

- `_auto_activate` (`src/coga/commands/launch.py`) is a durable write —
  `mark_active` → `prepare_active` + `ticket.write` + `assert_task_valid` +
  `append_log` + `git.sync_task_state` (`src/coga/mark.py`).
- Its draft/paused agent-path call site sits *above* every refusing preflight,
  including the `SecretError` one.
- Nothing between that call and the `in_progress` flip re-reads the ticket from
  disk (re-checked 2026-09-02), so deferring the durable write and carrying an
  in-memory activated `ticket` is safe for the non-assist path.
- `prepare_active` already exists as the pure prepare/commit boundary this fix
  needs — no new abstraction required.
- The assist path (`_prospective_assist_ticket` →
  `_publish_assist_lifecycle_before_spawn`) and the blocked-resume branch
  already follow the target ordering. This makes the fix a consistency change
  with two in-repo precedents rather than a new policy.
- `test_launch_fails_loud_on_op_read_error` (`tests/test_launch.py`) asserts
  `status == "active"` after a secret failure — but starts from an
  already-active fixture, so it never exercises draft→active. That is why the
  bug ships green.
- **New since the original spec:** a third `_auto_activate` call site, in the
  script path, which calls `build_launch_env` before activating. The original
  spec's "exactly two call sites" claim is now wrong; corrected in Proposed
  Shape.
- **New since the original spec:** the `_auto_activate` error ladder splits
  across the prepare/commit seam — four exceptions come from `prepare_active`,
  `TaskValidationError` from the post-write `assert_task_valid`. The original
  spec kept the ladder in one piece, which would have put a post-write handler
  on a pre-write helper.

## Spec maintenance

Every code citation in this ticket is a symbol or a guard condition. Do not
reintroduce line numbers: `_launch` grew ~790 lines between 2026-08-14 and
2026-09-02, and the resulting mismatch is twice what made a live bug look
retired. See the sibling ticket
`ticket-specs-should-cite-symbols-not-line-numbers`.

## Open Questions

1. **Does a wrong instruction actually exist in `weather-events`?** (Zach's
   original ask, half (a).) It cannot be actioned from this repo — no
   mapping-form `secrets:` example exists here outside this ticket's own body.
   If it does exist there, name the file and it becomes a separate ticket in
   that repo. Answering "no / don't care" closes this cleanly; the code fix
   stands either way.
2. ~~**Should the slug be renamed?**~~ **Resolved 2026-09-02** by the owner:
   renamed `secrets-instructions-correction` → `launch-activates-before-preflight`.
   `coga/log.md` is append-only, so pre-rename history stays under the old
   slug; see "Slug history" in `## Context`.
3. **Is `coga megalaunch`'s up-front activation intended to stay as-is?** It
   activates all picked tickets before launching any, and
   `_preflight_agent_launch` requires `active`/`in_progress`, so the same
   "activated but never ran" residue is reachable there — a queue pick whose
   secrets are malformed fails at `build_launch_env` with the ticket already
   flipped. I read this as a deliberately different contract (an explicit human
   pick *is* the activation decision) and left it out of scope. Say so if you'd
   rather it match `launch`.
4. **Should a refused launch of a ticket that was already `active` be touched
   at all?** Current behavior leaves it `active`, which seems right — nothing
   was falsely claimed. The spec preserves it. Flagging only because it is the
   case the existing test covers.

## Evaluator review

Cold review, 2026-09-02, by an independent session that did not see the
authoring conversation. Verbatim.

### Verification against source

I read `src/coga/commands/launch.py` (3478 lines; `_launch` spans 494–1986), `src/coga/mark.py`, and `tests/test_launch.py`.

**1. `_auto_activate` performs a durable write via `mark_active` — CONFIRMED.**
`_auto_activate` is at `src/coga/commands/launch.py:2297`; its body calls `mark_active(...)` with `log_message=f"activated ({prior} → active) — auto on launch"`. `mark_active` (`src/coga/mark.py:748`) does exactly what the ticket claims, in this order: `prepare_active` → `ticket.write(ref.ticket_path)` → `assert_task_valid(action="mark active")` → `append_log` → `typer.echo` → `git.sync_task_state(message=f"Ticket: {slug} — active")`. Durable, logged, and pushed.

**2. The draft/paused agent-path call site precedes `build_launch_env`/`SecretError`, `_preflight_push_auth`, and `mark_in_progress` — CONFIRMED, exactly in the order the ticket's table gives.** Inside the `try:` at line 1316: the `not is_bootstrap and isinstance(ref, TaskRef) and ticket.status in {"draft","paused"} and assist_publication is None` guard calls `_auto_activate` at **1328**, under the "Typing `coga launch` *is* the readiness signal" comment. Then `_refuse_human_handoff_launch` (1330) → `_interactive_stdio_has_tty()`/`_refuse_tty_launch` (1332) → `cfg.agent_type` → `shutil.which` → `compose_prompt` (with the "Fail loud BEFORE flipping status" comment at 1359) → `build_launch_env` → `except SecretError: _bail` (1372–1376) → `_preflight_push_auth` (1398) → the `ticket.status == "active" and assist_publication is None` guard → `mark_in_progress` (1455). The bug is live on `main` as described.

Two harmless omissions from the ticket's table: `preflight_post` (assist-only), `warn_if_installed_predates_source` (warn-only), and the assist PR head re-verification block also sit in that window. Also worth knowing: a few refusals *already* precede activation (`cfg.agent_type(agent_override)` at ~1300, `_refresh_agent_skills_for_launch`, the "has no assignee" bail at 1314), so the ticket's "everything that can refuse is below" is true only of the listed preflights, not literally of all refusals. Doesn't change the fix.

**3. Exactly three `_auto_activate` call sites, each described correctly — CONFIRMED.** `grep -rn "_auto_activate" src/` returns 1153 (script path), 1328 (buggy agent path), 1452 (blocked-resume), plus the definition at 2297. The script branch is verbatim `elif not is_bootstrap and isinstance(ref, TaskRef) and ticket.status in {"draft","paused","blocked"}` inside `if entry is not None:`, preceded by `build_launch_env(cfg, ticket.secrets)` under the "Secret resolution belongs before the activation write" comment. Blocked-resume is `if blocked_resume and isinstance(ref, TaskRef) and ticket.status == "blocked": if assist_publication is None: _auto_activate(...)` immediately above the `in_progress` block. The assist precedent is real too: `_prospective_assist_ticket` (2047) calls `prepare_active` on a *copy* and maps the same errors to `ComposeError`; `_publish_assist_lifecycle_before_spawn` (~2158) calls `mark_active(..., sync_state=False, mutation_snapshot=snapshot)` at the final gate.

Note: `_auto_activate`'s `sync_state: bool = True` keyword is **dead** — no call site passes it. The split should decide whether to keep it.

**4. Prepare/commit exception split — CONFIRMED.** In `prepare_active` (`mark.py:721`): `CancellationError` (canceled), `BlackboardNeedsSynthesis` (via `_refuse_unsynthesized_draft_blackboard`, **only when prior status is `draft`**), `WorkflowMissing` (`_has_workflow`), `WorkflowError` (`_freeze_workflow_ref` → `Workflow.load`), `RequiredExtensionMissing`. `TaskValidationError` comes only from `assert_task_valid` *after* `ticket.write` in `mark_active`. The claimed seam is exact.

The idempotency claim also holds, for a reason the ticket doesn't state: at commit time `prior_status` is already `"active"`, so the re-run of `prepare_active` skips both `CancellationError` and the blackboard check (which is gated on `prior_status != "draft"`), `_freeze_workflow_ref` is a no-op on a frozen dict with a step, and the extension check re-passes. So the commit half genuinely cannot raise the four prepare-side errors.

**5. Test claims — CONFIRMED.** `test_launch_fails_loud_on_op_read_error` (`tests/test_launch.py:2207`) takes the `active_task` fixture, uses `list_tasks(cfg)[0]` (`fix-retry-logic`, already active), and ends `assert Ticket.read(ref.ticket_path).status == "active"` — it never exercises draft→active. `test_launch_auto_activates_draft_and_paused` (2990, parametrized draft/paused) and `test_launch_auto_activate_bails_without_workflow` (3101) both exist and assert what the ticket says.

**One test the ticket missed:** `test_launch_refuses_unsynthesized_draft_blackboard` (3017) also pins the activation ladder (the `BlackboardNeedsSynthesis` arm) and — crucially — is a *better model for the new regression test* than `test_launch_fails_loud_on_op_read_error`, because it already asserts the shape the criteria want: `ticket_md.read_text() == before` and `"activated (draft" not in _read_log(...)`. The spec should name it.

### Reviewer assessment

**Description clarity — good, genuinely cold-startable.** The symbol/guard-condition anchoring works; I located every cited site on the first try. The ticket is honest about what does and doesn't reproduce. Main cost is length and duplication (below).

**Workflow fit — yes.** `code/design-then-implement` at step 2 (`review-design`, owner) is right: the design exists, the owner needs to approve and answer the Open Questions, then bump to `implement`. One concrete hazard: **the frozen `workflow:` snapshot in this ticket's frontmatter is stale.** The live `code/design-then-implement` (`src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md`) now declares `requires: branch` on the `implement` step; the ticket's frozen copy does not. So the branch/worktree gate will *not* fire at implement→open-pr, and the ticket will instead fail later at `coga open-pr` with "No usable `branch:` recorded". The implementer must record `branch:`/`worktree:` under `## Dev` in the checkout they bump from anyway. (There is no `## Dev` section in the ticket today.)

**Contexts `[]` — this is wrong.** `coga/contexts/coga/launch-internals/SKILL.md` says in its own front matter and body: "Attach only to tickets that change launch.py, the recurring runner, open-pr, or the step gates… Add `coga/launch-internals` to a ticket's `contexts:` list when the work touches those paths." This ticket changes lifecycle publication ordering in `launch.py` and sits adjacent to the strict-assist publication machinery (leases, mutation snapshots, `_publish_assist_lifecycle_before_spawn`) that it explicitly promises not to disturb. That is precisely the guarantee set that context documents. It's ~19 KiB (~5k tokens), which would roughly double the prompt — a deliberate call, but the repo's own instruction points at attaching it, at minimum for the `implement` step.

**Scope — right-sized.** One file, one helper split, one moved call, two comment rewrites, four tests. Not bundled. The Out of Scope list is doing real work.

**Proposed Shape — implementable, with these gaps:**

1. **`prior_status` must be initialized before the guard, not inside it.** Step 2 says "capture `prior_status = ticket.status` alongside it"; step 3's condition reads `prior_status in {"draft","paused"}`. If the guard doesn't fire (bootstrap, `BootstrapRef`, assist, already-active, blocked), that name is unbound → `UnboundLocalError` at step 3. Initialize `prior_status: str | None = None` above the `try:` at 1316.
2. **A new lost-update window the spec doesn't acknowledge.** Today the activation write is instantaneous. Deferred, the in-memory `ticket` is held across `compose_prompt`, `build_launch_env` (which may shell out to `op read`) and `_preflight_push_auth` (a real network `git push --dry-run`) — seconds — and then `mark_active` renders and overwrites `ref.ticket_path` wholesale. A concurrent edit to the ticket in that window is silently clobbered. The assist precedent the ticket cites as "already does the right thing" guards exactly this: `_publish_assist_lifecycle_before_spawn` compares `ref.ticket_path.read_bytes() != initial_bytes` and refuses. Blocked-resume has the same unguarded window today, so this isn't a regression relative to that path — but the spec should either capture the pre-prepare bytes and refuse on drift, or state explicitly that it accepts the window.
3. **Output ordering changes and the spec doesn't say so.** `mark_active` echoes `{slug}: active — auto on launch` before syncing. After the move, that line appears *after* the `Launch: agent … (cli=…)` / `Launch: found agent CLI at …` lines instead of before. No current test asserts stdout order (only `_read_log`), so nothing breaks, but it's an operator-visible change worth a line in the ticket.
4. **`assert_task_valid(action="mark active")` also moves.** Deferring the commit means an activation-time validation failure now surfaces *after* the agent-CLI, compose, secret and push-auth refusals rather than before. Criterion 5 ("same operator-facing messages") still holds; the *ordering* of which error the operator sees first changes. Worth stating.
5. **Criterion 6 is half wrong.** `_refuse_human_handoff_launch` (line 3417) reads only `ticket.assignee` — it never touches the workflow or the step. So it does not depend on the activated view at all, and "does not regress step-assignee refusal" overstates it. `compose_prompt` genuinely does depend on it (`compose.py:403` `ticket.current_step()`, `:426` `ticket.workflow`), so keeping the *prepare* call at the current call site is load-bearing — the spec gets that part right.
6. **Criterion "no state sync" is imprecise.** `_bail` calls `sys.exit`, which lands in the `except SystemExit` handler at 1499 → `_refresh_launch_checkout(cfg)` → `git.refresh_coga_state_from_control(..., message="Refresh coga state after launch")`. So a refused launch may still produce git activity; what the criterion means is "no `Ticket: &lt;slug&gt; — active` commit". The `coga/log.md` byte-identity criterion *is* sound — I confirmed there is no `append_log` anywhere in `_launch` before the flip.
7. **Test trap for the new draft+bad-secrets test.** `prepare_active` checks the blackboard *before* the workflow, and only for `prior_status == "draft"`. A draft fixture whose blackboard carries authoring notes will refuse with `BlackboardNeedsSynthesis` and never reach `SecretError`. The `active_task`/`fix-retry-logic` fixture is clean (which is why `test_launch_auto_activate_bails_without_workflow` reaches the "no workflow" message), but a test built on `_create_chain_task` + `replace_blackboard` could easily assert the wrong refusal.
8. **Missed code path: `recurring_runner.py:3638`.** A forced recurring run durably `mark_active`s the period ticket *before* invoking launch's preflights, and its own docstring defends that ("If the later launch preflight fails, the task is at least live for a future normal sweep"). The ticket lists megalaunch as out of scope but never mentions this one. It doesn't change the fix, but it means criteria 1–3 are true of `coga launch` only, not repo-wide — and an implementer who greps `mark_active` will hit it and wonder.
9. **Megalaunch out-of-scope reasoning verified, and it is the weaker half.** `megalaunch._activate_for_launch` (1044) durably activates, and `_preflight_agent_launch` (1189) then runs `compose_prompt`, `build_launch_env`, and the push-auth check — so the identical "activated but never ran" residue is fully reachable there, exactly as Open Question 3 says. The "an explicit human pick *is* the activation decision" rationale is coherent but thin: the operator picking from a queue hasn't asserted the secrets parse either. This is the Open Question most worth the owner actually answering before implement, because the answer determines whether the invariant is "launch is atomic" or "launch is atomic, megalaunch isn't."

**Assumptions to question before implementing:**

- "Nothing between the call and the flip re-reads the ticket from disk" — I re-verified this for the non-assist path in the 1328–1452 window and it holds today. It is a *fragile* invariant that the deferral now depends on; the ticket should say so in a code comment, not only on the blackboard.
- The spec's "`mark_active` re-runs `prepare_active` internally, which is harmless and idempotent" is correct, but only because the second run sees `prior_status == "active"` and therefore skips the draft-only blackboard gate. That's worth a comment in the code, since a future change to `_refuse_unsynthesized_draft_blackboard`'s gating would silently change the commit half's behavior.
- Open Question 1 (weather-events) is unanswerable from this repo and doesn't gate the fix — the owner can close it "no/don't care" at review-design without touching scope.

**Prompt budget:** no single layer exceeds 40% (blackboard 1627/5259 = 31%, base_prompt 27%, task_description 21%, task_context 12%). But ticket-owned text is 63% of the prompt and is substantially self-duplicating — the blackboard's "Design notes" bullets restate the Description table and the Context section nearly verbatim (durable-write claim, call-site ordering, the two precedents, the masking test, the third call site, the ladder split). Collapsing the verified-facts list into the Description and leaving the blackboard as Open Questions + Blockers would cut ~800–1000 tokens with no information loss, and would buy back most of the cost of attaching `coga/launch-internals`.

### Disposition

Applied to the spec in this session: gaps 1, 3, 4, 5, 6, 7, 8, the dead
`sync_state` kwarg, the two code-comment invariants, and the better model test
(`test_launch_refuses_unsynthesized_draft_blackboard`). Gap 2 (lost-update
window) is written into Proposed Shape as an explicit decision the implementer
must make and record rather than silently inherit.

Left for the owner at `review-design` — see Owner decisions below.

## Owner decisions

1. **Attach `coga/launch-internals` to `contexts:`?** The context's own
   description says to attach it to tickets that change `launch.py`. It is
   24 KiB (~5k tokens) and would roughly double this ticket's composed prompt
   (currently ~5,259 tokens). Not attached — it is a real token cost against a
   real instruction, and the call is the owner's.
2. **The frozen `workflow:` snapshot is stale.** The live
   `code/design-then-implement` declares `requires: branch` on `implement`;
   this ticket's frozen copy predates that. Left untouched — a frozen snapshot
   is CLI/human-owned state and rewriting it during authoring is out of
   bounds. Consequence if left: the branch/worktree gate will not fire at
   implement→open-pr, and the failure surfaces later at `coga open-pr` as
   "No usable `branch:` recorded". There is also no `## Dev` section on the
   ticket yet.
3. **Open Question 3 (megalaunch)** is the one the evaluator says most deserves
   an answer before `implement`, because it decides whether the invariant is
   "launch is atomic" or "launch is atomic, megalaunch isn't".
4. **Blackboard trim.** The evaluator estimates ~800–1000 tokens of duplication
   between Design notes and the Description/Context. Not cut — the duplication
   is the evidence trail that twice stopped this ticket from being retired by
   mistake, so removing it has a cost that isn't only tokens.

---

## Blockers

- [x] [2026-08-13 22:21] [agent:claude] id=20260813T222158 Zach to confirm the ticket's scope before design starts. The premise does not reproduce in this repo: every instruction here already documents the correct '- NAME: <ref>' list form (coga/tasks/_template/ticket.md:12, docs/operations.md:183, coga/contexts/coga/architecture/SKILL.md:156, coga/contexts/coga/secrets/SKILL.md:28, src/coga/config.py:1094), and a repo-wide grep finds no mapping-form example outside this ticket's own body — so there is no instruction here to correct. Which did you actually hit: (a) the wrong instruction lives in another repo (weather-events?) — name the file; (b) the real defect is that coga launch marks the task active BEFORE validating secrets:, so a typo strands the ticket and needs hand-repair — a code fix in src/coga/; or (c) both, as one ticket or split. Contexts are still unset pending that answer.
  resolved: [2026-08-13 22:54] [human:nicktoper] Scoped to (b) on reproduced evidence, since (a) has no target in this repo. Re-verified: no mapping-form 'secrets:' example exists anywhere here outside this ticket's own Description, so there is no instruction in this repo to correct; if the bad instruction lives in weather-events, that fix belongs in that repo and needs a filename only Zach can supply — carried forward as an Open Question for the owner at review-design rather than blocking a second time. (b) does reproduce and is precise: src/coga/commands/launch.py:542 calls _auto_activate (a durable write — status draft/paused to active, freezes the workflow snapshot, seeds step, appends the log, git-syncs) BEFORE the fail-loud preflight gauntlet at 544-591 (human-handoff refusal, TTY check, agent-type resolution, CLI-binary check, compose preflight, and the secrets preflight at 591 that raises SecretError). So a malformed 'secrets:' on a draft ticket strands it in 'active' with a frozen workflow and a spurious activation log entry. Two internal precedents show the intended shape: the blocked-resume path already defers _auto_activate to line 666, after every preflight, and the assist path already composes an in-memory prospective activation via _prospective_assist_ticket/prepare_active without writing. mark.py:445 prepare_active is documented as exactly this 'pure preparation boundary'. Fix is to make the normal draft/paused path do what those two already do. Existing coverage masks the bug: test_launch_fails_loud_on_op_read_error starts from an already-active task and asserts only that it stays active.
