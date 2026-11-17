---
title: Move Slack FYIs to a command ticket
status: in_progress
owner: nicktoper
contexts:
- coga-dev/microkernel/objectives
- coga-dev/principles
- coga-dev/testing
- coga-dev/project-stage
- coga/script-tickets
- coga/state-publication
- coga/notifications
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 2 (evaluate-design)
agent: claude
---

## Description

Move the `slack` FYI procedure (operands, formatting, route selection) into an
editable bootstrap command ticket with a complete edge implementation. Split
from v1/microkernel/09-work-orchestration-commands-to-tickets at its owner gate
on 2026-11-16.

The blocker 09 found is that `coga slack` is two things at once: an FYI, and
the only completion signal a stateless agent-backed bootstrap session has
(`bootstrap/address-pr-comments` and `bootstrap/resolve-conflicts` end with a
`coga slack --task bootstrap/<name>` roll-up, and `prompt-queue.md` tells
megalaunch sessions the same). A script-phase child loses the sentinel and
expected identity, so an edge FYI script cannot also end the outer session.
09's carried options were a parent-owned audited-notification protocol
(Option A), a post-exit audit-line check (Option B), or keeping the 94-line
head (Option C).

This design recommends **Option D: separate completion from notification.**
Stateless bootstrap completion becomes an explicit lifecycle action in the
command that already owns session-ending (`coga mark done`), and `coga slack`
becomes a pure, non-terminal FYI that moves wholesale to the edge. No new
transport, protocol or parent callback is needed: the completion runs in the
agent's own supervised process, which already holds the sentinel, exactly as
`bump`/`mark`/`block` do today. It removes the only special case that ties a
notification head to supervisor authority, which is the microkernel
objective ("fewer special cases"). The cost is one extra instruction line in
two bootstrap tickets and the queue prompt, and the roll-up FYI and
completion are no longer one atomic command (see Open Questions on the
blackboard). If the owner rejects D, Option C (retain the head under 09's
recorded proof) is the fallback; A and B are summarized under *Alternatives*.

### Acceptance criteria

Completion (core, `coga mark done` on a bootstrap target):

- [ ] `coga mark done bootstrap/<name>` is accepted for a stateless bootstrap
  ref (`tasks.BootstrapRef`). It writes no ticket file, runs no workflow or
  completion gate, and keeps refusing every other `mark` verb on a bootstrap
  ref (`active`, `paused`, `canceled`, …) with exit 2.
- [ ] It resolves the actor as today's slack head does for a bootstrap ref
  (`bump.resolve_main_agent` with the same `allow_prospective_default` rule);
  an `OperatorResolutionError` exits 2 without logging or signalling.
- [ ] It appends exactly one audit line (`done (stateless command)` or similar,
  fixed text chosen by the implementer and documented in `coga/cli`) and then
  confirms it: with Git enabled, `git.sync_log` must return `True` or `False`
  (`None` is a miss). With Git explicitly disabled (`cfg` git-disabled), a
  successful local append suffices; the implementer must distinguish this
  from `_publishable_root` returning `None` for a failure, since `publish`
  returns `None` for both.
- [ ] On confirmed audit it calls `repl_supervisor.emit_done_marker(ref.id_slug)`
  (deferred by `cli.main`'s `deferred_done_marker` as today). On a publication
  miss it does **not** request the marker, retains the log line, exits 75,
  and prints the strict-publication recovery (`coga run publish-state <log>`).
  Recovery never signals completion; the idle/max-session backstops still
  release the session. This is the deliberate audit-gate tightening; document
  it as new behavior, not as parity.
- [ ] The marker names `ref.id_slug`, so a bootstrap completion never releases
  a session for a different target (existing supervisor check). No
  notification is posted by `mark done` on a bootstrap ref (the roll-up FYI
  is the notification; avoid a double post).

FYI (edge):

- [ ] `slack = "launch bootstrap/slack --"` alias (09's plain-launch rules)
  replaces the Typer command; `"slack"` is removed from `cli.py`'s command
  table and `src/coga/commands/slack.py` is deleted.
- [ ] `bootstrap/slack/ticket.md` + `ticket.py` ship in the package; the
  script is a thin import of `coga_edge.slack` (the 05 edge-code pattern),
  and the module holds operands (`--task`, `--message`, `--important`),
  message formatting and route selection. A local fork gets the full
  behavior, per `coga/edge-code`.
- [ ] Behavior parity for every target: empty message → exit 2; config error
  → exit 2; unknown target → exit 2; bootstrap actor via
  `resolve_main_agent`, ordinary actor via `commands.common.current_operator`
  (both derive from ticket metadata, not env, so script isolation does not
  change attribution); one `notification.post(..., important=...)` attempt
  with `fatal=True` (delivery miss → exit 1, no audit line beyond the
  channel's own failure record); important route never falls back to flow;
  disabled/no-channel keeps today's stderr diagnostic + audit + `posted`;
  `slack: <message>` audit line via `logfile.append_log`; `posted` on stdout
  only after the post and append.
- [ ] `coga slack` **never** completes any session, including for a
  `bootstrap/<name>` target. Nothing in the edge module imports
  `repl_supervisor`.
- [ ] Help: the script checks `COGA_SCRIPT_HELP == "1"` at its command body and
  exits 2 before any effect, so `coga slack --message --help` exits 2 instead
  of posting `--help` (accepted behavior change; document in `coga/cli`).
  `coga slack --help` shows the script's help.
- [ ] Every caller that relies on slack-as-completion switches to the explicit
  pair: `bootstrap/address-pr-comments/ticket.md`,
  `bootstrap/resolve-conflicts/ticket.md`, `resources/prompt-queue.md`
  (stateless bootstrap paragraph), and any skill or context that states the
  slack-completes-bootstrap rule (grep `coga slack --task bootstrap` and
  "releases that stateless session").

Docs and verification:

- [ ] Contract owners updated in the same PR: `coga/notifications`,
  `coga/notifications/producers`, `coga/cli`, `coga/edge-code`,
  `coga/script-tickets`, `coga/state-publication` (the new completion audit
  gate and exit 75), `coga/launch` if it describes bootstrap completion, and
  `coga-dev/microkernel` (remove the `slack` row from *Open command
  placements*; replace 09's "retained head" paragraph with the settled
  boundary: completion is a `mark done` lifecycle case, FYI is edge).
- [ ] Packaging: `tests/required_package_resources.txt` lists the new ticket
  files; `test_packaging` passes.
- [ ] Report before/after production line counts per
  `coga-dev/microkernel/objectives` (removed `commands/slack.py`, added
  `coga_edge/slack.py` + shim, added `mark` bootstrap branch), distinguishing
  relocation from deletion.
- [ ] Full Linux suite receipt per `coga-dev/testing`; native checks deferred
  to release.

### Proposed shape

Order of work (requires 09's PR #1244 merged; see blockers below):

1. **Core completion.** In `src/coga/commands/mark.py` (the `done` verb),
   branch on `isinstance(ref, BootstrapRef)` *before* the prepared-ticket
   transaction (bootstrap targets are packaged/stateless; there is no ticket
   to reconcile). Implement as a small private helper in `mark.py`, e.g.
   `_finish_stateless_command(cfg, ref)`: resolve actor → `append_log` →
   confirm with `git.sync_log` (or Git-disabled local success) →
   `emit_done_marker(ref.id_slug)` or exit 75 with recovery text. Reuse
   `git.sync_failure_report` wording where possible. If sibling 10 has already
   moved `mark` by implementation time, put the branch wherever `mark done`
   lives and record it on 10's ticket.
2. **Edge FYI.** Add `src/coga_edge/slack.py` (argparse, `main(argv) -> int`,
   help-marker check, the body of today's `commands.slack.slack` minus the
   `emit_done_marker` call). Add
   `src/coga/resources/templates/coga/bootstrap/slack/ticket.md` (stateless
   command ticket describing operands and how to fork) and `ticket.py`
   (shebang? follow the shim convention 09 used for `bootstrap/retire` and
   `bootstrap/megalaunch`, including mode). Add the alias to the shipped
   `coga.toml` `[aliases]` next to 09's `megalaunch` alias.
3. **Remove the head.** Delete `src/coga/commands/slack.py`, its `cli.py`
   registration and help-table entry.
4. **Callers.** Update the two bootstrap tickets and `prompt-queue.md`:
   "post the roll-up with `coga slack --task bootstrap/<name> --message …`,
   then, as the final action, run `coga mark done bootstrap/<name>`; run the
   completion even if the FYI failed, after stating the failure in your final
   report" (subject to the Open Question on failure semantics).
5. **Docs + tests** (below), then line counts and receipts.

Tests:

- `tests/test_commands.py`: rewrite
  `test_slack_accepts_and_completes_stateless_bootstrap_target` →
  slack on a bootstrap target posts and logs but writes **no** sentinel;
  keep `test_slack_on_durable_task_does_not_complete_session`,
  `test_slack_important_forwards_to_notification_post` (patch target moves to
  `coga_edge.slack.post`), `test_bootstrap_slack_completion_attributes_configured_agent`
  (attribution only), `test_bootstrap_slack_refuses_invalid_agent_without_completing`.
  Invoke through the alias (`runner.invoke(app, ["slack", …])`) so the
  plain-launch path is exercised, plus a direct `coga_edge.slack.main` unit.
- `tests/test_done_marker_emission.py`: `mark done bootstrap/<name>` signals
  with the slug after the boundary (`test_main_writes_the_sentinel_only_after_the_boundary`
  pattern); publication miss → exit 75, line retained, no sentinel;
  Git-disabled → signals after local append; invalid agent → exit 2, no line,
  no sentinel; other `mark` verbs on a bootstrap ref → exit 2; a marker from
  `bootstrap/a` does not satisfy a supervisor polling `bootstrap/b`.
- `tests/test_notification_messages.py::test_slack_fyi_includes_title`:
  retarget to the edge module.
- Help: `coga slack --message --help` exits 2 with no post and no log line;
  `coga slack --help` exits 0.
- Packaging/alias tests per 09's precedent (`tests/test_aliases.py`,
  `tests/test_packaging.py`).

### Alternatives (owner may choose instead of D)

- **C — retain the head.** Keep `commands/slack.py` under 09's recorded
  co-versioning proof; this ticket then only lands the doc settlement and
  (optionally) the audit-gate tightening inside the existing head. Cheapest,
  but leaves FYI formatting unforkable and keeps the notification/completion
  special case.
- **A — parent-owned audited-notification protocol** (09's carried design): an
  invocation-scoped channel through which the launching parent performs the
  post/audit and holds completion authority. Preserves single-command
  atomicity, but adds cross-platform transport and generation verification
  to move a 94-line head, and 03/10 have not offered it. Not recommended.
- **B — post-exit audit-line check**: parent completes after the child exits 0
  if a fresh `slack:` line for the captured slug landed. Cheap, but turns a
  cooperative child's log output into a completion credential (fine against
  accidents, not against a forked script), and still couples FYI to
  completion. Not recommended.

### Out of scope

- Any parent↔script RPC, completion callback, or new completion credential.
- Moving `mark`/`bump`/`block` themselves (sibling 10 owns that placement);
  this ticket only adds a bootstrap case to `mark done`.
- Changing notification channels, webhook config, `notification.post`, or
  `logfile.append_log`.
- Retrying or spooling FYIs; strict publication of an FYI's own log line
  (the launch settlement/sweep publishes it as for any script).
- `bump --message` FYIs and other producers.
- Native Windows/macOS receipts (release-only).

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

### Codebase facts

- Current head: `src/coga/commands/slack.py`, `slack()`; registered in
  `src/coga/cli.py` command table (`"slack": ("coga.commands.slack", "slack", {})`).
  Completion is the `emit_done_marker(session_id=ref.id_slug)` call for a
  `BootstrapRef`; `cli.main` wraps dispatch in
  `repl_supervisor.deferred_done_marker()`, which writes the marker after the
  end-of-command sweep but never checks publication success.
- `git.sync_log(cfg, message=...)` returns `True`/`False` (published / already
  held) or `None` (failure or skip). `git.publish` returns `None` from
  `_publishable_root` both for disabled Git and for unpublishable roots, so
  the Git-disabled branch must be decided from config, not the return value.
- `notification.post(..., fatal=True)` raises `typer.Exit(1)` on delivery
  miss; with no channels it writes `[notification] no channels configured`
  to stderr and returns (today's disabled-channel success path).
- Actor resolution reads ticket metadata only: `commands.common.current_operator`
  (ordinary) and `bump.resolve_main_agent` (bootstrap). Script isolation's
  cleared env does not affect it.
- `mark.py` has no `BootstrapRef` handling today; only `slack.py` and
  `ticket.py` among commands accept bootstrap refs.
- Slack-as-completion callers: `bootstrap/address-pr-comments/ticket.md`,
  `bootstrap/resolve-conflicts/ticket.md` (both agent-only, no `ticket.py`),
  `src/coga/resources/prompt-queue.md` (stateless bootstrap paragraph).
- 09's plain-launch rules (`COGA_SCRIPT_HELP`, stateless script interrupts,
  `megalaunch`/`retire` alias + shim precedent) exist only on PR #1244's
  branch `coga/v1-microkernel-09-work-orchestration-commands-to-b46008`, not
  on main as of 2026-11-16. Edge-code shim conventions come from 05 (PR #1239,
  also open).

<!-- coga:blackboard -->

## Design status (design step, 2026-11-16)

Spec written above recommending Option D (completion via
`coga mark done bootstrap/<name>`; slack becomes a pure edge FYI). Option C is
the fallback. Investigation notes are under `### Codebase facts` in Context.

## Dependencies

- Implementation requires 09 (PR #1244: plain-launch alias rules,
  `COGA_SCRIPT_HELP`) and 05 (PR #1239: edge-code shim pattern) merged; both
  were OPEN at design time. Implement must verify, and block naming
  `v1/microkernel/09-work-orchestration-commands-to-tickets` if 09 is not
  merged.
- Sibling 10 (`lifecycle-verbs-to-ticket-operations`, at design) should know
  `mark done` gains a bootstrap case; 03 is not needed under Option D.

## Open Questions

1. **Choose D vs C (vs A/B).** D drops single-command atomicity of
   "roll-up posted ⇒ session ends" in exchange for no new protocol and a
   fully forkable slack. Accept?
2. **Failure semantics of the roll-up under D.** Today a failed roll-up post
   leaves the bootstrap session running until the idle backstop. Proposed:
   the agent reports the failure in its final answer and still runs
   `coga mark done bootstrap/<name>`, so the session ends promptly. The
   alternative is "only mark done after a successful slack", which keeps
   today's stall. Which?
3. **Verb spelling.** `coga mark done bootstrap/<name>` (reuses the existing
   session-ending verb; recommended) vs a new verb. A new verb would add
   surface, against project-stage posture.
4. **Audit-gate tightening.** Approve exit 75 + no completion when the
   bootstrap completion's log line cannot be confirmed on control (Git
   enabled), with local-append success when Git is disabled?
5. **Help change.** Accept that `coga slack --message --help` now exits 2
   (fail-closed help) instead of posting the literal `--help`?
