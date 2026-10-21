---
title: Add a failed terminal status
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
agent: claude
---

## Description

Owner decision (2026-10-14), revising #1014. A terminal ticket can end three ways, and they need different retirement: done (positive learning landed in the merged PR); canceled (superseded, duplicate or no longer wanted, so nothing to learn, and the --message reason persists in coga/log.md); and the new failed (an approach was tried and did not work, so there is negative learning to extract: what was tried, why it failed, what would reopen it). Add `failed` as a third terminal status, set with `coga mark failed --message <reason>` (reason required, as for canceled). Retirement: `coga retire` deletes done and canceled tickets deterministically with no agent (checkout disposal, worklist discharge, `coga delete` and sync), and runs the Retro task (retro/done-ticket through retire.md) only on failed tickets, extracting the lesson into the topic that owns the subject, per the coga/knowledge rule that a decision not to act is owned by the topic, not the ticket. Rejected alternatives: one canceled status with no Retro, since failure lessons would depend on remembering to write them; and a --retro flag on cancel, since an explicit status is clearer. Design step: inventory every consumer of the status set and of the literal 'canceled' (src/coga/lifecycle.py VALID_STATUSES, TERMINAL_STATUSES and CANCELABLE_STATUSES; mark, megalaunch, views/coga status, notifications and GIF kinds, git/state publication, recurring and recurring_runner, retire, autoclose and branch-sweep terminal-owner rules, validate, create), and decide for each whether failed behaves like canceled. Decide the notification emoji and GIF key, whether autoclose or recurring can ever produce failed, and how Dream Phase 4 and Phase 6 and bootstrap/dream/scan/knowledge-scan route failed versus canceled findings (#1014 routed canceled to Retro). Update coga/lifecycle (status table and terminal rules), coga/tickets/discovery, dev/checkout-cleanup and its terminal-owners leaf, coga/recurring/dream/ticket.md, coga/notifications and the cli index, with live and packaged twins byte-identical. Done means: three terminal statuses with distinct retirement as above, no prompt or topic still promising Retro for canceled tickets, tests covering mark failed and retire for each terminal status, and the full suite and coga validate passing.

### Acceptance criteria

- [ ] `failed` is a valid, terminal status: `src/coga/lifecycle.py` has it in
  `VALID_STATUSES` and `TERMINAL_STATUSES` (so it drops out of
  `CANCELABLE_STATUSES` and `MAIN_AGENT_REQUIRED_STATUSES` automatically) and
  in `STATUS_DISPLAY_ORDER` between `done` and `canceled`.
- [ ] `coga mark failed <ref> --message <reason>` exists, is allowed from every
  non-terminal status (same set as `canceled`), refuses an empty or missing
  `--message`, clears `step:` and `launch_generation`, leaves body and
  blackboard untouched, appends `failed (<prior> → failed): <reason>` to
  `coga/log.md`, notifies with kind `failed`, syncs with commit subject
  `Ticket: <slug> — failed`, and emits the supervisor done marker.
- [ ] Nothing reactivates a failed ticket: `mark active`, `coga launch`,
  megalaunch activation and `coga recurring --force` all refuse it, exactly
  as they refuse `canceled`.
- [ ] `coga retire` on a `done` **or `canceled`** ticket runs no agent:
  checkout disposal, worklist discharge, `run_delete_task`, publish
  (`Ticket: <slug> — deleted (retire)`). A kept checkout refuses with exit 2
  and deletes/creates nothing, for both statuses.
- [ ] `coga retire` on a `failed` ticket creates and launches the
  `retire-<slug>` Retro task (today's canceled path, unchanged mechanics:
  `--agent`, `--no-launch`, kept-checkout → blocked retire task).
- [ ] `coga retire` on any non-terminal status still refuses, and its message
  names all three terminal statuses.
- [ ] No prompt, resource, skill, template or topic (live or packaged) still
  says canceled tickets get Retro; `rg -n -i "retro" | rg -i cancel` over
  `docs/contexts src/coga coga` returns only text that says canceled tickets
  do **not** get Retro (or none).
- [ ] Topics updated, live and packaged twins byte-identical (see Proposed
  shape, step 6); `tests/test_packaging.py` passes.
- [ ] Tests: `mark failed` (happy path from several statuses, required
  message, refusal from each terminal status, reactivation refused, done
  marker emitted, notification kind/emoji/GIF); `retire` for each terminal
  status (done → deleted, canceled → deleted with no task created, failed →
  retire task created with retire.md body, kept checkout for each); plus the
  touched-surface tests listed in step 7.
- [ ] `python -m pytest` and `coga validate --json` pass.

### Proposed shape

Decision rule applied to every consumer: **`failed` behaves exactly like
`canceled` everywhere except retirement** (where it takes the Retro path
canceled used to take) **and its own name in user-facing output** (log line,
notification, counts). Both are "terminal, did not land, never reactivated".

1. **Vocabulary** — `src/coga/lifecycle.py`: add `"failed"` to
   `VALID_STATUSES`, `TERMINAL_STATUSES`, and `STATUS_DISPLAY_ORDER`
   (`..., "done", "failed", "canceled"`). Add a small shared constant
   `NON_REACTIVATABLE_STATUSES = frozenset({"canceled", "failed"})` (terminal
   statuses nothing — not even `recurring --force` — reactivates) and use it
   at every literal `== "canceled"` reactivation check below, rather than
   sprinkling `{"canceled", "failed"}`.
2. **Finalizer + CLI** — `src/coga/mark.py`: generalize `mark_canceled()`
   into a shared private `_mark_abandoned(cfg, ref, ticket, *, status,
   actor, reason, slack_text, image_url, echo)` used by `mark_canceled()` and
   a new `mark_failed()` (export it in `__all__`). Keep `CancellationError`
   as the single error type (message names the target status).
   `prepare_active()`: refuse when `prior_status in
   NON_REACTIVATABLE_STATUSES` ("a failed ticket cannot be reactivated").
   `src/coga/commands/mark.py`: add `@app.command("failed")` mirroring
   `canceled()` — required `--message`, `_FAILED_FROM =
   set(CANCELABLE_STATUSES)`, `preflight_post`, assist-session actor, Slack
   text `❌ {actor} marked *{slug}* "{title}" failed: {reason}`,
   `image_url=cfg.gif_for("failed")`, echo `{slug}: failed — {reason}`,
   `emit_done_marker`. Update module docstring and `help=`. `src/coga/cli.py`:
   add `"failed"` to `_SWEEPING_MARK_SUBCOMMANDS`.
3. **Notifications** — `src/coga/notification/__init__.py`: add `"failed"`
   to `OUTCOME_EVENT_KINDS`. GIF key is `failed` under
   `[notification.slack.gifs]`, no fallback (like `canceled`). Emoji `❌`.
4. **Other code consumers** (most need nothing because they read
   `TERMINAL_STATUSES`; the explicit ones):
   - `src/coga/git.py` `_STATUS_RANK`: `"failed": 3`.
   - `src/coga/views.py` `_terminal_hint()`: iterate terminal statuses in
     `STATUS_DISPLAY_ORDER` instead of the literal `("done", "canceled")`.
     `src/coga/commands/status.py` `--all` help: "terminal `done`, `failed`
     and `canceled` tasks".
   - `src/coga/megalaunch.py` `_chain_stop_result()`: `MegalaunchOutcome`
     already uses `"failed"` for *launch* failure, so a ticket the agent marked
     failed must not reuse it. Add outcome `"marked-failed"` (detail `task
     failed`) next to `"canceled"` in the `Literal`, `MegalaunchRun.counts`,
     and the summary key list; see Open Questions.
   - `src/coga/recurring.py`: `retain_canceled` check uses
     `NON_REACTIVATABLE_STATUSES` (rename param `retain_terminal_refusal` or
     keep the name and update the docstring — implementer's call); update the
     `launchable` comment. `src/coga/recurring_runner.py`: the force-run
     refusal (`if ticket.status == "canceled"`) covers failed with the actual
     status in the message; the terminal-status classification (`elif status
     in TERMINAL_STATUSES: result = "completed"`) gets `detail = "task
     marked failed"` when `status == "failed"`. `src/coga/commands/recurring.py`
     help text: "A canceled or failed period task is refused".
   - `src/coga/commands/init.py` seeded command list: add a
     `coga mark failed <slug> --message "<reason>"` line beside canceled.
   - No change needed (read `TERMINAL_STATUSES`/`VALID_STATUSES`):
     `validate.py`, `create.py`, `bump.py`, `open_pr.py`, `owner.py`,
     `launch_script.py`, `checkout_disposal.py`, `recurring_autofix.py`,
     `branchsweep._terminal_owners` (failed owns its branches like canceled),
     `commands/launch.py` terminal refusal, `coga_edge/phone_home.py`
     (adds `tickets_failed` automatically — update the telemetry topic's
     property table). Comments/docstrings in `branchsweep.py`,
     `commands/launch.py` and `autoclose.py` that enumerate "done or
     canceled" get "failed" added.
   - **autoclose and recurring never produce `failed`.** Autoclose writes
     `done` only on a merged PR (work landed). The recurring sweep parks runs
     as `paused`/`blocked`. Only `coga mark failed` (human, or an agent the
     human authorized, same rule as `mark canceled`) writes it.
5. **Retire** — `src/coga/commands/retire.py`: accept `{"done", "canceled",
   "failed"}` (use `TERMINAL_STATUSES`); `if source.status in {"done",
   "canceled"}: _delete_terminal_task(...)` (rename of `_delete_done_task`,
   docstring generalized); the Retro path runs only for `failed`. Update
   module docstring, `retire()` docstring, `task` arg help and `--no-launch`
   help ("Failed tickets only"). `src/coga/resources/retire.md`: "canceled"
   → "failed" throughout; the reason lives in the `failed` log line; stop
   condition "Source task is not `status: failed`".
6. **Docs and skills** (live `docs/contexts/...` + packaged
   `src/coga/resources/templates/coga/bootstrap/contexts/...` twins, and the
   live/packaged Dream template and bundled skills):
   - `coga/lifecycle`: status values and table row for `failed`; terminal
     bullet ("done/canceled/failed are terminal; nothing reactivates a
     canceled or failed ticket"); retirement sentence (done and canceled
     deleted with no agent; failed goes through Retro); rewrite the
     convention bullet into three outcomes — **done** = scoped change landed;
     **failed** = an approach was tried and did not work (negative learning:
     what was tried, why it failed, what would reopen it), including work
     stranded off control after a real attempt; **canceled** = superseded,
     duplicate or no longer wanted, nothing to learn, reason in the log.
     Retire relies on it: mark `failed`, not `canceled`, to keep a lesson.
     Keep the "decision not to act lands in the topic before or with the
     cancel" bullet, noting retire will not Retro a canceled ticket so the
     topic edit is the only route. Description frontmatter mentions
     cancellation rules → "terminal rules".
   - `coga/tickets/discovery`: "`coga retire` accepts only a terminal
     (`done`, `failed` or `canceled`) ticket".
   - `dev/checkout-cleanup`: retire section — done and canceled deterministic,
     failed gets the Retro task; kept-checkout paragraph split "done or
     canceled" vs "failed"; record the 2026-10-14 owner decision revising
     2026-10-13 and the two rejected alternatives (single canceled with no
     Retro; `--retro` flag). `dev/checkout-cleanup/terminal-owners`: "owner
     must be `done`, `failed` or `canceled`"; "When it runs" adds
     `coga mark failed`; "A canceled or failed ticket deleted before any
     pass ran...".
   - `coga/recurring/dream/ticket.md` (+ packaged twin):
     Phase 4 never takes a canceled or failed ticket; both are retirement
     debt. Phase 4 / Phase 6 routing below. "an open ticket — any status but
     `done`, `failed` or `canceled`".
     - `source: failed` → retirement debt (exactly what #1014 gave
       `canceled`): list under the run summary's retirement-debt section,
       open no PR, since `coga retire` runs Retro on it.
     - `source: canceled` → proposal PR, like `done+checkout` (restores the
       pre-#1014 rule), since retire now deletes it without Retro and the
       scan is the backstop for an unlanded decision not to act. Also list it
       as retirement debt.
   - `bootstrap/dream/scan/knowledge-scan` (packaged skill; live copy if one
     exists under `coga/skills`): add `source: failed`; re-point
     `source: canceled` to "Phase 6 opens the proposal PR"; keep the
     "abandoned design is not durable, but a reusable fact or a decision not
     to act is" rule on both.
   - `retro/done-ticket` (packaged): description and the `### Canceled
     tickets` section → `### Failed tickets` (read the `failed` log line;
     extract what was tried, why it failed, what would reopen it); the
     stop-and-ask exceptions name a single `failed` slug from `coga retire`.
   - `coga/extension-model`: retire creates a retire task "for a failed
     ticket" and deletes done/canceled in place.
   - `coga/blackboard`: done-ticket remedy text unchanged unless it mentions
     canceled retirement (check).
   - `coga/notifications` (OUTCOME_EVENT_KINDS list, GIF kinds),
     `notifications/producers` (row for `mark failed` → `mark.py`
     `mark_failed`, flow), `notifications/failures` (`mark_failed`,
     `commands/mark.py` `failed`), packaged `coga.toml` comment ("done,
     failed, canceled").
   - `coga/cli`: the `mark` row stays; add to "Picking a command": "abandon
     work: `coga mark canceled` (nothing to learn) or `coga mark failed`
     (tried and did not work; retire runs Retro)". `coga/first-task`: same
     distinction beside its canceled line.
   - `coga/launch`, `coga/session-conduct`, `coga-dev/internals/agent-spawn`,
     `coga-dev/internals/git-refresh` (rank), `coga-dev/internals/recurring-admission`,
     `coga/megalaunch` (summary counts), `coga/recurring/scheduling` (failed
     period: terminal, refused by `--force`, delete to rerun),
     `coga/recurring/templates`, `coga/recurring/phone-home/ticket.md` (`tickets_failed`),
     `coga/workflows` (unfrozen-workflow accepted on canceled and failed),
     `dev/dev-record`, branch-sweep sweep skill (live `coga/skills/...` +
     packaged), `code/with-review` and `docs/with-review` workflows,
     `bootstrap/ticket` skill status lists: add `failed` wherever they
     enumerate terminal statuses.
   - Prompts: `src/coga/resources/prompt.md` (supervisor list adds
     `coga mark failed`), `prompt-megalaunch.md` and `prompt-queue.md` ("an
     authorized `coga mark canceled` or `coga mark failed`"),
     `prompt-attended.md` ("`done`, `failed` or `canceled`").
7. **Tests** — `tests/test_mark.py` (mark failed cases above),
   `tests/test_retire.py` (parametrize retire over done/canceled/failed;
   convert the existing canceled-Retro tests to failed and add
   canceled-deletes-deterministically + canceled-kept-checkout), 
   `tests/test_done_marker_emission.py`, `tests/test_notification.py` /
   `test_notification_messages.py` (kind accepted, GIF lookup),
   `tests/test_megalaunch.py` (`marked-failed` outcome and count),
   `tests/test_recurring.py` (force-run refuses failed), `tests/test_git.py`
   (rank), `tests/test_validate.py` (status accepted; terminal with `step:`
   rejected), `tests/test_dream_worker_templates.py` (routing text assertions
   for failed/canceled), and any status-count/view snapshot test. Update
   `tests/fixtures/seeded-repo/` only if a fixture enumerates statuses.

Order: 1 → 2 → 3 → 4 → 5 with tests alongside, then 6, then full suite +
`coga validate --json` + the `rg` check.

### Out of scope

- Converting existing `canceled` tickets on disk to `failed` (owner can
  re-mark by hand; there is no canceled → failed transition and none is
  added).
- Letting Dream Phase 4 Retro failed tickets or run `coga retire` itself.
- Any automatic producer of `failed` (autoclose, recurring watchdog, bump).
- Renaming `retro/done-ticket` or `CancellationError`.
- Telemetry server-side schema work beyond documenting `tickets_failed`.

## Context

Consumer inventory (status set and the literal `'canceled'`), with the
relationship that makes each one load-bearing:

- `src/coga/lifecycle.py` — `VALID_STATUSES`, `TERMINAL_STATUSES`,
  `CANCELABLE_STATUSES` (= valid − terminal, so failed leaves it
  automatically), `MAIN_AGENT_REQUIRED_STATUSES`, `STATUS_DISPLAY_ORDER`.
- `src/coga/mark.py` — `mark_canceled()` is the shared finalizer called by
  `commands/mark.py` `canceled()`; `prepare_active()` refuses
  `prior_status == "canceled"` and is called by `mark_active()`, launch,
  megalaunch (`_prepare_auto_activate` path) and `recurring_runner`.
- `src/coga/commands/mark.py` — `_CANCELED_FROM`, `canceled()` command (Slack
  text `🚫 ... canceled`, `cfg.gif_for("canceled")`, `emit_done_marker`).
- `src/coga/cli.py` — `_SWEEPING_MARK_SUBCOMMANDS` decides which `mark`
  subcommands trigger the post-command state sweep.
- `src/coga/notification/__init__.py` — `notify()` rejects kinds outside
  `OUTCOME_EVENT_KINDS`; `Config.gif_for(kind)` (`src/coga/config.py`)
  reads `[notification.slack.gifs]` per kind with no validation of keys.
- `src/coga/git.py` — `_STATUS_RANK` drives state-regression refusal when
  publishing; a missing key would break ranking for failed tickets.
- `src/coga/views.py` — `_terminal_hint()` hard-codes `("done", "canceled")`;
  status totals use `STATUS_DISPLAY_ORDER`.
- `src/coga/megalaunch.py` — `MegalaunchOutcome` already contains
  `"failed"` (launch error); `_chain_stop_result()` special-cases canceled,
  otherwise maps terminal → `"completed"`.
- `src/coga/recurring.py` — `create_template(retain_canceled=...)` and the
  `launchable` property comment; `src/coga/recurring_runner.py` —
  force-run refusal on canceled, `TaskOutcome` classification of terminal
  statuses as `"completed"`.
- `src/coga/commands/retire.py` — `retire()` gate `{"done", "canceled"}`,
  `_delete_done_task()` (deterministic path), Retro task creation via
  `create_task(workflow_name="direct/body", description=_retire_body(...))`
  which renders `src/coga/resources/retire.md`.
- `src/coga/branchsweep.py` `_terminal_owners()`, `src/coga/autoclose.py`,
  `src/coga/checkout_disposal.py`, `validate.py`, `create.py`, `bump.py`,
  `open_pr.py`, `owner.py`, `launch_script.py`, `recurring_autofix.py`,
  `commands/launch.py`: read `TERMINAL_STATUSES` only — inherit failed.
- `src/coga_edge/phone_home.py` — `_COUNT_KEYS` derived from
  `VALID_STATUSES`; adds `tickets_failed` to the closed telemetry schema.
- #1014 (merge `92dc76032`) is the change being revised; its diff lists
  every doc surface that encoded "canceled → Retro":
  `git diff 92dc76032^1 92dc76032 --stat`.
- Superseded sibling: `retire-canceled-tickets-without-retro` (canceled
  2026-10-14, reason points here).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design (2026-10-14, design step)

Spec written under `## Description` / `## Context`. Rule of thumb: failed ==
canceled everywhere except retirement (Retro) and its own name in output.
Inventory done by grepping `canceled`/`TERMINAL_STATUSES`/`VALID_STATUSES`
across `src/coga`, `src/coga_edge`, docs, resources, and the #1014 diff.

## Open Questions

1. **Megalaunch outcome name.** `MegalaunchOutcome` already uses `failed`
   for a launch error. Spec proposes a new `marked-failed` outcome; the
   alternative is folding it into `completed` with detail `task failed`
   (fewer moving parts, but the summary would count a failed ticket as
   completed). Owner to pick.
2. **Dream routing for `source: canceled`.** Spec restores the pre-#1014
   rule (Phase 6 opens a proposal PR) because retire no longer extracts
   anything from a canceled ticket. Alternative: drop canceled from the
   knowledge scan entirely, trusting "nothing to learn". Spec keeps the
   backstop since lifecycle already names the scan as the backstop for an
   unlanded decision not to act.
3. **Emoji.** `❌` for failed (canceled stays `🚫`). Confirm.
4. **Recurring run summary** for a period an agent marked failed: spec keeps
   result `completed` with detail `task marked failed`; alternative is
   `unfinished` so the sweep flags it. Owner to pick.
5. **Telemetry.** `tickets_failed` appears automatically in the closed
   PostHog property set. The telemetry topic says to query stored keys at
   acceptance; confirm a new count key needs no separate approval.

## Evaluator review

Cold review, 2026-10-14. **Needs owner resolution before implementation.**
The status split and reuse of the existing finalizer/retirement paths are
coherent and fit the kernel boundary. The spec uses the correct composed body
regions. The frozen workflow matches the shipped design-then-implement
workflow and sends this review to the owner next. No code or spec edits made.

### Must resolve before implementation

1. **Resolve “nothing reactivates” versus blocked-launch recovery.** Proposed
   shape 4 says `commands/launch.py` needs no behavior change, but
   `_reblock_unresolved_resume()` restores a cleared step and calls
   `mark_blocked()` even after a terminal transition when `resume_step` is
   supplied and an unanswered blocker remains. `reblock_after_script()`
   supplies that argument. An interactively resumed blocked ticket whose
   `ticket.py` invokes `mark failed` would therefore become blocked again.
   This is existing policy, owned by `coga/lifecycle` “Blocking and resume”
   and covered for terminal completion by
   `tests/test_launch_script.py::test_blocked_script_termination_reblocks_unresolved_ask`
   and `test_reblock_restores_the_original_position_not_an_assignment`.
   Choose whether this rollback also applies to failed/canceled (qualify the
   absolute acceptance criterion), or those verdicts override unresolved-ask
   recovery (name the code and contract change). Add regression cases for
   failed and canceled; refusal to launch an already-terminal ticket does
   not cover this path.

2. **Scope the no-stale-Retro check to maintained instructions.** Grepping all
   of `coga/` includes this ticket's old-path references, the historical spec
   and receipts in
   `coga/tasks/retire-deletes-done-tickets-without-a-retro-cancel.md`, and
   `coga/log.md` records. These cannot all become “canceled does not get Retro”
   through the planned edits; the log is append-only and historical claims
   are evidence, not current policy. Explicitly exclude task history/logs
   while retaining live skills, workflows, recurring templates, resources
   and topics. Treat grep hits as a reviewed candidate list: same-line
   matching also misses multiline promises.

3. **Include the shipped design-then-implement retirement instructions.**
   `src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md`,
   `## review`, still says that after a ticket is done, `coga retire`
   scaffolds and launches `retro/done-ticket`. This contradicts the
   deterministic done path in `commands/retire.py::retire` retained by this
   design. Step 6 names `code/with-review` and `docs/with-review` but omits
   this active workflow; a canceled-only grep cannot catch it. Include it
   in the retirement-semantics audit, preferably replacing the duplicated
   procedure with a short link to `dev/checkout-cleanup` per `coga/knowledge`.

### Optional recommendations and owner choices

- Include `src/coga/commands/megalaunch.py` in the wording inventory: its
  picker help and empty-picker message explicitly say “done/canceled”.
- Extend `tests/test_mark.py::test_transition_refuses_to_bury_terminal_control_copy`
  with failed as both the landed verdict and proposed local verdict. This
  checks the publication invariant behind its Git rank, beyond the constant.
- Resolve the five existing Open Questions at the owner gate. Telemetry's
  count derives automatically from `VALID_STATUSES`, and
  `tests/test_telemetry.py::test_inventory_scope_and_exact_zero_statuses`
  iterates that set. Decide whether the `coga/telemetry` “Closed wire contract”
  stored-key acceptance is required here or explicitly deferred; documenting
  a key and verifying ingestion are different checks. No external telemetry
  was sent during this review.

### Verification

Inspected lifecycle, mark, retire, launch recovery, megalaunch, recurring,
notifications, Git ranking, telemetry, Dream routing, packaging and workflow
surfaces, plus the #1014 change inventory. Current-behavior checks:

```sh
PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest -q tests/test_launch_script.py::test_blocked_script_termination_reblocks_unresolved_ask tests/test_launch_script.py::test_reblock_restores_the_original_position_not_an_assignment tests/test_retire.py::test_retire_deletes_a_done_ticket_without_a_retro_task tests/test_retire.py::test_retire_no_launch_creates_task_with_target_slug tests/test_telemetry.py::test_inventory_scope_and_exact_zero_statuses
```

**8 passed in 7.76s.** These verify existing behavior used as review evidence,
not an implementation of failed. Full-suite and repo-validation acceptance
remain implementation work.
