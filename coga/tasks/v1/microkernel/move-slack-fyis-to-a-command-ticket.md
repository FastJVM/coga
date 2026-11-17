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
step: 6 (open-pr)
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

## Dev

branch: coga/v1-microkernel-move-slack-fyis-to-a-command-tick-d8c446


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

## Owner decisions (implement step, 2026-11-17, attended)

The owner answered in session:

- **Dependencies:** stack this branch on PR #1244's branch
  (`coga/v1-microkernel-09-work-orchestration-commands-to-b46008`) rather than
  block; 05 (PR #1239) is still open too. Rebase when they merge.
- **Accepted every design recommendation:** Option D; the agent runs
  `coga mark done bootstrap/<name>` even after a failed roll-up FYI (reporting
  the failure in its final answer); reuse `mark done` (no new verb); exit 75
  with no completion when the audit line cannot be confirmed (Git enabled),
  local append suffices with Git disabled; `coga slack --message --help`
  exits 2; `mark done` rejects `--message`/`--force` on a bootstrap ref
  (exit 2 before any effect); FYI-style attribution
  (`bump.resolve_main_agent`), documented as a lifecycle exception.
- Evaluator must-resolve items 1-3 are adopted as written (both alias
  inventories, direct edge-unit plus real `cli.main` alias integration tests,
  option refusal).

## Open Questions

(Answered: see Owner decisions above.)


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


## Evaluator review

Cold review at `36b0c8ecfaf3679c4d65a021e0f0914424b327d5` (2026-11-16).
**Not ready for implementation until the findings below and the existing owner
questions are resolved.** Option D is a coherent boundary: retain session
completion in lifecycle machinery and make FYIs editable edge behavior. No new
completion protocol is needed. Description/Context heading placement and the
frozen design-review workflow are correct. No implementation or spec edits
were made during evaluation.

### Must resolve before implementation

1. **Complete the alias migration for existing installations.** Proposed
   shape only adds the alias to shipped `coga.toml` and removes the CLI table
   entry. `src/coga/aliases.py::BUILTIN_COMMANDS` independently reserves
   `slack`; leaving it there rejects the new alias. Add the expansion to
   `DEFAULT_ALIASES` as well, so upgrading an existing repo without a local
   slack alias preserves the command. `coga/cli`, “Aliases and recipes”,
   specifies this default behavior; `tests/test_aliases.py` verifies the
   builtin inventory and dispatch without an aliases section. Require tests
   for both inventories and an existing config with no slack alias.

2. **Correct the alias/subprocess verification plan.**
   `runner.invoke(app, ["slack", ...])` does not exercise argv rewriting:
   `src/coga/cli.py::_register_alias_placeholder` explicitly raises if called;
   rewriting happens in `cli.main`. Also, `launch_script.run_script_phase`
   executes a fresh interpreter, so patching `coga_edge.slack.post` in pytest
   cannot intercept delivery through the alias. Specify direct edge-unit
   tests with notification mocks, plus actual `cli.main`/CLI alias integration
   tests with a safe subprocess-visible fixture (e.g. notifications disabled
   for real script execution). Cover fatal delivery/configuration exits at
   the direct seam and verify status propagation through launch. This avoids
   failing placeholders or accidentally attempting real webhook delivery.

3. **Define existing `mark done` options for bootstrap targets.**
   `src/coga/commands/mark.py::done` accepts `--message` and `--force`.
   The new branch requires a fixed audit message and no notification, but
   says neither whether these flags are rejected nor how they are consumed.
   Decide explicitly (rejecting unsupported options is sufficient), including
   empty `--message`, and test refusal before append/publication/signalling.
   Otherwise implementers must invent public behavior or silently drop input.

### Recommendations and owner decisions

- Resolve the five existing Open Questions in durable intent before handing
  implementation over, especially completing after a failed FYI and the audit
  publication gate. They are decisions for the next owner step, not blockers
  for this evaluation.
- Reconcile completion attribution with the lifecycle contract:
  `commands/common.py::completion_identity` and `coga/script-tickets`,
  “Completion attribution”, distinguish evidence that an agent ran from task
  metadata. The proposed bootstrap case deliberately copies FYI attribution
  instead. Either document this lifecycle exception or choose completion
  attribution consistent with the shared rule, with supervised/manual/script
  tests. The current spec is explicit enough to implement its chosen rule,
  but its audit meaning should be an owner decision.
- PR #1239 and PR #1244 were both confirmed OPEN with no merge commit.
  Their absence does not block design review; implementation must recheck
  both dependencies and use exact task slugs if blocked. The current plan
  only spells out the terminal dependency action for 09.

### Verification

Source inspection checked `commands/slack.py::slack`, `commands/mark.py::done`
and `_load`, `commands/common.py`, `tasks.resolve_target`, `git.sync_log`,
`notification.post`, `repl_supervisor.emit_done_marker` and
`deferred_done_marker`, alias dispatch, existing command/sentinel tests,
packaged workflow, edge-code and CLI contracts, and 09's help subprocess path.
Fresh fetch found no relevant drift from the reviewed main revision.
Linux baseline receipt: `36b0c8ecfaf3679c4d65a021e0f0914424b327d5`,
Pop!_OS 24.04 LTS, Python 3.12.12,
`PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest --basetemp=/home/n/Code/coga-test-slack-design`
→ **4900 passed, 33 skipped in 840.25s**. Only this ticket's blackboard was
edited; production code and tests match the named revision. Scoped validation:
`PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task v1/microkernel/move-slack-fyis-to-a-command-ticket --json`
→ 1 OK, no issues. `git diff --check` passed. Final fetch found no relevant
main drift. Native Windows/macOS checks are deferred to release; Python 3.11
floor was not exercised here.

## Implement handoff (2026-11-17)

Branch is **stacked on PR #1244 (09)**: its two commits (`08256389f`,
`79255ea81`, 09's rebased onto main `ca88ec1ae`) sit under this ticket's two
commits (`4edddccbc` implementation, `75fcaa98d` test pins). Merge #1244 first,
then rebase onto main (git drops 09's patch-equivalent commits) and refresh
`## PR` head/base and receipts. Until then a PR against main would also show
09's diff. #1239 (05) is not a dependency of this code.

What changed:

- `coga slack` → default alias `launch bootstrap/slack --` (added to
  `aliases.DEFAULT_ALIASES`, removed from `BUILTIN_COMMANDS` and the CLI
  command table). An alias still targeting `slack` gets the replacement
  expansion message (`aliases._RETIRED_BUILTINS`, generalized from 09's
  megalaunch special case). The shipped `coga.toml` was not changed: 09's
  `megalaunch`/`retire` precedent keeps defaults only in `DEFAULT_ALIASES`.
- `src/coga_edge/slack.py` (`slack`, `main`): the former head minus
  `emit_done_marker`, plus the `COGA_SCRIPT_HELP` refusal. Packaged
  `bootstrap/slack/{ticket.md,ticket.py}`, with the shim at mode 100644 and no
  shebang (megalaunch precedent).
- `commands/mark.py::_finish_stateless_command`: `mark done bootstrap/<name>`
  rejects `--message`/`--force` (exit 2) → resolves actor via
  `resolve_main_agent` → appends `done (stateless command)` → with Git enabled
  requires `git.sync_log` not `None` (otherwise it withholds the sweep and
  exits 75 with the `publish-state` recovery) → `emit_done_marker(ref.id_slug)`.
  The other verbs on a bootstrap ref still exit 2 (`resolve_task` refuses).
- Callers: the two bootstrap tickets and `prompt-queue.md` now say to post the
  roll-up FYI, then `coga mark done bootstrap/<name>` even after a failed FYI.
- Docs: `coga/cli` (new "Stateless command completion" section, the owner of
  the contract), `coga/notifications`, `producers`, `edge-code` (fork route),
  `launch`, `script-tickets`, `state-publication`, and dev topics
  `microkernel` (row removed, settled paragraph), `codebase`, and the
  `internals/{agent-spawn,notifications,state-publication/log-writers}`.
- `reminders.py` still shells `python -m coga.cli slack`; that now runs a
  nested stateless launch. It is covered by
  `test_slack_alias_works_from_inside_a_running_script_phase`.

Line counts (`wc -l`, production `src/` only, base `79255ea81` → `75fcaa98d`):
core removed `commands/slack.py` 94 and `cli.py` −2, and added `aliases.py`
+6 net and `mark.py` +72 net (the new completion branch and gate), so core
is −18 net. Edge added `coga_edge/slack.py` 109 and the shim 8 (+117).
Whole system +99. The FYI body is a **relocation** (94 → 109, mostly the help
check and `main`), not a deletion. The +72 is new behavior (the audit-confirmed
completion gate), not parity. The deletion is of a special case: no
notification head holds supervisor authority any more.

Adjacent note (not fixed): `docs/contexts/coga-dev/internals/agent-spawn`
still records the known gap that `coga slack` attributes the routed/default
agent, not `COGA_EXPECTED_AGENT`. That is unchanged, and script isolation
clears that variable anyway, so a fix would need ticket-metadata-free
evidence.

## Peer review

Codex completed direct review of Claude's Slack implementation and reread the
fixes through `40b285cede717bc4b818834f007b8daa6646be3d`, using PR #1244's
`d68562ea8174d9825c550e1d28025a2ccd334381` as the Slack diff base.

- Updated both recurring wrappers to describe scoped sentinel completion and
  the delegation contract to name `mark done` as the completion command.
  Initial review edits named the verb in the wrapper itself, which tripped
  two packaging checks. The command syntax now lives with the delegated
  command and its contract.
- Restricted the prompt-report sweep exemption to launch options. A literal
  `--prompt-report` Slack message now posts and publishes its audit line.
- Used the shared shell quoting helper for the completion recovery command.
  With an unavailable Git remote, the command retained the audit line,
  exited 75 and left the sentinel unset.
- Clarified that after an unconfirmed publish a session can exit normally
  or reach a configured timeout.

An 80×24 PTY and loopback HTTP catcher verified the FYI payload, flow and
important routing, a fatal HTTP 503, and help refusal. An actual PTY supervisor
with a test agent stayed alive after the Slack FYI and exited upon the
matching `mark done` sentinel. A disposable Git remote confirmed the audit
line for a literal `--prompt-report` message and success/failure cases for
completion publication.

The branch is pushed. PR #1244 remains open, so this branch still contains
its two commits. The configured PR-opening step targets main and would
include the dependency diff. The owner approved advancing with the stacked diff while PR #1244 is open.

The Linux full-suite receipt and Python 3.11 focused receipt are below. Using physical line counts from `git diff --numstat --no-renames`, the Slack diff against `d68562ea8` removes 16 net core Python lines and adds 117 edge Python lines including the shim, for 101 net production Python lines. The old 94-line Slack head is relocated and the audit gate adds lifecycle behavior. Markdown and resource inventory account for 146 additions and 52 deletions outside tests. Test changes account for 391 additions and 61 deletions.

## PR

```yaml
"title": "Move Slack FYIs to an editable command ticket; end stateless commands with mark done"
"author": "claude"
"author_evidence": "Implement session ran in Claude Code (claude-opus-5-5), launch 557cf03b-23dd-459f-8e3f-ca9b4f0e9b2d.\
  \ Codex authored the fixes during peer review in launch 41cc2e4c-6fd9-4bff-bfd1-fa92987f2033."
"head": "40b285cede717bc4b818834f007b8daa6646be3d"
"base": "657d6f5d65dd66e06800d86943a45660258552a4"
"depth": "deep"
"rationale": "Changes stateless completion and its publication gate, reroutes an externally visible command,\
  \ and is stacked on the megalaunch extraction."
"implementation": "A default alias runs the editable Slack command ticket and edge implementation. Stateless\
  \ mark done requires a confirmed audit line before signalling completion. Peer review fixed the literal\
  \ --prompt-report sweep case, quoted the recovery command and updated delegated recurring instructions."
"deviations": "Default alias lives in DEFAULT_ALIASES following PR #1244. The branch sits on the current\
  \ head of PR #1244, per the owner's stacking instruction."
"limitations": "The main-based diff includes the open dependency PR #1244. This review covers the Slack\
  \ changes with the dependency as base. Native Windows and macOS suites are deferred to release. Python\
  \ 3.11 evidence is focused."
"files":
  "coga/coga.toml": "Stacked PR #1244. Apply the owner-approved one-line pick alias migration in this\
    \ repository."
  "docs/contexts/coga-dev/codebase/SKILL.md": "Source map entry. Stacked PR #1244. Update the source map\
    \ for edge policy and shared claim, session-limit and foreground-wait modules."
  "docs/contexts/coga-dev/internals/agent-spawn/SKILL.md": "Stateless completion is mark done."
  "docs/contexts/coga-dev/internals/notifications/SKILL.md": "Producer path rename."
  "docs/contexts/coga-dev/internals/state-publication/log-writers/SKILL.md": "Log writer rows for the\
    \ edge FYI and completion."
  "docs/contexts/coga-dev/microkernel/SKILL.md": "Remove slack placement row; settled boundary. Stacked\
    \ PR #1244. Settle queue placement and document the bounded claim/authoring/Slack co-versioning proofs\
    \ and sibling ownership. Records the two authoring-adapter seams."
  "src/coga/aliases.py": "Default slack alias, builtin removal, retired-builtin hint. Stacked PR #1244.\
    \ Replace the megalaunch built-in and pick target with direct launch aliases; explain migration of\
    \ user aliases."
  "src/coga/argv.py": "Stacked PR #1244. Share exact separator-aware help recognition between dispatch\
    \ and publication."
  "src/coga/authoring.py": "Stacked PR #1244. Invoke the public ticket CLI with selected agent, isolated\
    \ identity, retained-finalization exit mapping and existing-target-only seams."
  "src/coga/claimed_session.py": "Stacked PR #1244. Own exact activation and claim transactions, readiness,\
    \ held-child release/admission and guarded rollback. Return refused activation errors for caller classification."
  "src/coga/cli.py": "Remove the builtin Slack dispatch and keep launch script operands from suppressing\
    \ the audit sweep. Stacked PR #1244. Remove the queue head; preserve help exclusions and expose Python-only\
    \ retained-finalization mapping and existing-target-only seams before context reset."
  "src/coga/commands/mark.py": "Add scoped, audit-gated stateless completion with a shell-quoted recovery\
    \ command."
  "src/coga/commands/megalaunch.py": "Stacked PR #1244. Delete the old built-in queue/picker command head."
  "src/coga/commands/slack.py": "Removed core head (renamed into the edge module)."
  "src/coga/commands/ticket.py": "Stacked PR #1244. Consume the renamed public TTY predicate; mark retained\
    \ finalization and refuse creation under the queue adapter's existing-target-only seam."
  "src/coga/config.py": "Stacked PR #1244. Point shared limit resolution commentary at its new owner."
  "src/coga/launch.py": "Stacked PR #1244. Expose the bounded claimed-session operation, public TTY predicate,\
    \ early script help and shared re-block result adapter."
  "src/coga/launch_script.py": "Stacked PR #1244. Add stateless no-fallback, help isolation, foreground\
    \ relay and exact exit propagation. Unknown or broken bootstrap help falls through to ordinary reporting."
  "src/coga/mark.py": "Stacked PR #1244. Own the shared unresolved-resume operation, typed outcomes and\
    \ activation refusal tuple. Documents the prepare-half refusal tuple."
  "src/coga/megalaunch.py": "Stacked PR #1244. Old side of the rename into src/coga_edge/megalaunch.py;\
    \ removes the former core queue-policy import path."
  "src/coga/process_relay.py": "Stacked PR #1244. Share interrupt-safe foreground waiting and one-shot\
    \ SIGTERM forwarding with recurring."
  "src/coga/recurring_runner.py": "Stacked PR #1244. Migrate existing relay and limit-parser consumers\
    \ while preserving recurring-specific contracts."
  "src/coga/resources/prompt-queue.md": "Queue conduct names mark done as stateless completion."
  "src/coga/resources/templates/coga/bootstrap/address-pr-comments/ticket.md": "Roll-up FYI then mark\
    \ done."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md": "Owns the stateless completion\
    \ contract and help change. Stacked PR #1244. Update this contract owner for editable queue dispatch,\
    \ script help/interrupts, full forks or publication/authoring boundaries."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md": "Slack fork route. Stacked\
    \ PR #1244. Update this contract owner for editable queue dispatch, script help/interrupts, full forks\
    \ or publication/authoring boundaries."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md": "Bootstrap session end\
    \ pointer. Stacked PR #1244. Update this contract owner for editable queue dispatch, script help/interrupts,\
    \ full forks or publication/authoring boundaries."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md": "Stacked PR #1244.\
    \ Update this contract owner for editable queue dispatch, script help/interrupts, full forks or publication/authoring\
    \ boundaries."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/SKILL.md": "FYI is an editable\
    \ script, never terminal."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/producers/SKILL.md": "Producer\
    \ rows updated."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/delegation/SKILL.md": "Point delegated\
    \ period completion at the stateless mark-done contract."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md": "Script children\
    \ cannot complete outer sessions. Stacked PR #1244. Update this contract owner for editable queue\
    \ dispatch, script help/interrupts, full forks or publication/authoring boundaries."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md": "Completion\
    \ audit gate and exit 75. Stacked PR #1244. Update this contract owner for editable queue dispatch,\
    \ script help/interrupts, full forks or publication/authoring boundaries."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/launch-boundaries/SKILL.md": "Stacked\
    \ PR #1244. Update this contract owner for editable queue dispatch, script help/interrupts, full forks\
    \ or publication/authoring boundaries."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/authoring/SKILL.md": "Stacked PR\
    \ #1244. Specify the queue authoring adapter: retained finalization maps to 75, pre-write refusals\
    \ continue, vanished picks are refused."
  "src/coga/resources/templates/coga/bootstrap/megalaunch/ticket.md": "Stacked PR #1244. Ship the editable\
    \ stateless command definition and links to its contract owners."
  "src/coga/resources/templates/coga/bootstrap/megalaunch/ticket.py": "Stacked PR #1244. Select the complete\
    \ installed edge policy through the reserved script entry."
  "src/coga/resources/templates/coga/bootstrap/resolve-conflicts/ticket.md": "Roll-up FYI then mark done."
  "src/coga/resources/templates/coga/bootstrap/retire/ticket.md": "Stacked PR #1244. Update help behavior\
    \ to the generic setup-free stateless-script contract."
  "src/coga/resources/templates/coga/bootstrap/retire/ticket.py": "Stacked PR #1244. Fail closed when\
    \ a help token was consumed as a value."
  "src/coga/resources/templates/coga/bootstrap/slack/ticket.md": "Stateless command ticket describing\
    \ the FYI and how to fork it."
  "src/coga/resources/templates/coga/bootstrap/slack/ticket.py": "Thin shim importing coga_edge.slack."
  "src/coga/resources/templates/coga/coga.toml": "Stacked PR #1244. Seed the new direct pick alias in\
    \ fresh repositories."
  "src/coga/resources/templates/coga/recurring/address-pr-comments/ticket.md": "Name the mark-done completion\
    \ signal for the delegated period."
  "src/coga/resources/templates/coga/recurring/resolve-conflicts/ticket.md": "Name the mark-done completion\
    \ signal for the delegated period."
  "src/coga/session_limits.py": "Stacked PR #1244. Relocate existing env/config liveness parsing with\
    \ caller-owned idle defaults."
  "src/coga/task_env.py": "Stacked PR #1244. Clear inherited script-help identity with all other launch-owned\
    \ task metadata."
  "src/coga_edge/megalaunch.py": "Stacked PR #1244. Provide the complete independently copyable queue\
    \ policy, parser and picker; consume shared core operations. Classify claimed activation refusals\
    \ as before; queue-owned idle default."
  "src/coga_edge/slack.py": "Edge FYI implementation with the help-marker refusal and no completion."
  "tests/fixtures/authoring_cancellation.py": "Stacked PR #1244. Migrate existing fixtures and mocks to\
    \ the public TTY predicate; preserve the existing behavior assertions."
  "tests/required_package_resources.txt": "Require the new packaged ticket files. Stacked PR #1244. Pin\
    \ both new bootstrap command resource owners."
  "tests/test_aliases.py": "Default alias, dispatch without aliases section, old-target hint. Stacked\
    \ PR #1244. Test direct aliases, old-target migration errors and separator-consistent sweep recognition."
  "tests/test_authoring.py": "Stacked PR #1244. Exercise the public invocation adapter, identity isolation,\
    \ real CLI dispatch with pre-write and finalization refusals, and refusal of a vanished pick without\
    \ creating a draft."
  "tests/test_checkouts.py": "Stacked PR #1244. Migrate existing fixtures and mocks to the public TTY\
    \ predicate; preserve the existing behavior assertions."
  "tests/test_cli.py": "Verify a literal Slack --prompt-report message does not bypass the state sweep.\
    \ Stacked PR #1244. Update pick expansion and test that only retained authoring finalization maps\
    \ to 75."
  "tests/test_commands.py": "Direct edge-unit FYI tests including no completion and help refusal."
  "tests/test_compose.py": "Queue conduct clause pins."
  "tests/test_create.py": "Stacked PR #1244. Migrate existing fixtures and mocks to the public TTY predicate;\
    \ preserve the existing behavior assertions."
  "tests/test_done_marker_emission.py": "Stateless mark done boundary, miss, git-disabled, refusals, scoping."
  "tests/test_git.py": "Stacked PR #1244. Migrate existing fixtures and mocks to the public TTY predicate;\
    \ preserve the existing behavior assertions."
  "tests/test_launch.py": "Queue conduct clause pins. Stacked PR #1244. Migrate existing fixtures and\
    \ mocks to the public TTY predicate; preserve the existing behavior assertions."
  "tests/test_launch_restart.py": "Stacked PR #1244. Migrate existing fixtures and mocks to the public\
    \ TTY predicate; preserve the existing behavior assertions."
  "tests/test_launch_script.py": "Real alias subprocess, nested script FYI, help paths. Stacked PR #1244.\
    \ Cover generic help, argv/cwd/streams/status, no-fallback and real alias interrupt/claim retention,\
    \ plus public TTY seams. Unknown bootstrap help reports without a traceback."
  "tests/test_megalaunch.py": "Stacked PR #1244. Migrate policy/transaction seams and preserve queue coverage;\
    \ add guarded rollback, routing, identity and authoring-exit regressions. Claimed activation refusal\
    \ keeps skipped-unlaunchable."
  "tests/test_notification_messages.py": "FYI format via the edge module."
  "tests/test_packaging.py": "Stacked PR #1244. Test isolated installed command execution, a complete\
    \ local fork, wheel reinstall and stock-shim restoration."
  "tests/test_period_state.py": "Stacked PR #1244. Migrate existing fixtures and mocks to the public TTY\
    \ predicate; preserve the existing behavior assertions."
  "tests/test_recurring.py": "Stacked PR #1244. Migrate TTY seams and parser tests to their shared owners\
    \ with explicit caller defaults."
  "tests/test_smoke.py": "Smoke FYI via the edge module."
  "tests/test_ticket.py": "Stacked PR #1244. Migrate existing fixtures and mocks to the public TTY predicate;\
    \ preserve the existing behavior assertions."
"review":
  "reviewer": "codex"
  "kind": "independent"
  "status": "passed"
  "head": "40b285cede717bc4b818834f007b8daa6646be3d"
  "base": "d68562ea8174d9825c550e1d28025a2ccd334381"
  "detail": "Codex completed direct review of the Claude-authored Slack diff and reread its own review\
    \ fixes on this head. Dependency PR #1244 has a separate Claude review on its own recorded pre-fix\
    \ revision."
"checks":
- "command": "PYTHONPATH=/home/n/Code/coga/src:/tmp/coga-slack-peer-xdist TERM=dumb .venv/bin/python -m\
    \ pytest -q -p no:cacheprovider -n 6 --dist loadfile --basetemp=/home/n/Code/coga-test-slack-peer-40b285ced"
  "status": "passed"
  "head": "40b285cede717bc4b818834f007b8daa6646be3d"
  "base": "657d6f5d65dd66e06800d86943a45660258552a4"
  "detail": "Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.12.12, pytest 9.1.1 and pytest-xdist\
    \ 3.8.0. 4980 passed, 33 skipped, 26 fork deprecation warnings in 234.35s. Exit 0."
- "command": "PYTHONPATH=/home/n/Code/coga/src TERM=dumb /tmp/coga-slack-peer-py311.4AiqY2/env/bin/python\
    \ -m pytest -q -p no:cacheprovider tests/test_aliases.py tests/test_cli.py tests/test_commands.py\
    \ tests/test_done_marker_emission.py tests/test_launch_script.py tests/test_notification_messages.py\
    \ tests/test_packaging.py -k 'slack or bootstrap or prompt_report or recurring_wrapper' --basetemp=/home/n/Code/coga-test-slack-peer-py311-final"
  "status": "passed"
  "head": "40b285cede717bc4b818834f007b8daa6646be3d"
  "base": "657d6f5d65dd66e06800d86943a45660258552a4"
  "detail": "Pop!_OS 24.04 LTS, Python 3.11.15. 66 passed, 363 deselected in 10.98s."
- "command": "PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python /tmp/coga-slack-peer-smoke.py"
  "status": "passed"
  "head": "40b285cede717bc4b818834f007b8daa6646be3d"
  "base": "657d6f5d65dd66e06800d86943a45660258552a4"
  "detail": "Pop!_OS 24.04 LTS, Python 3.12.12. 80×24 PTY and local HTTP catcher verified two successful\
    \ routes, one fatal HTTP 503, help refusal and separate completion."
- "command": "PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python /tmp/coga-slack-peer-git.py"
  "status": "passed"
  "head": "40b285cede717bc4b818834f007b8daa6646be3d"
  "base": "657d6f5d65dd66e06800d86943a45660258552a4"
  "detail": "Pop!_OS 24.04 LTS, Python 3.12.12. Local Git remote verified audit publication, marker scoping,\
    \ exit 75, retained line and recovery quoting."
- "command": "PYTHONPATH=/home/n/Code/coga/src TERM=dumb script -qefc 'stty rows 24 cols 80 && /home/n/Code/coga/.venv/bin/python\
    \ /tmp/coga-slack-peer-supervisor.py' /dev/null"
  "status": "passed"
  "head": "40b285cede717bc4b818834f007b8daa6646be3d"
  "base": "657d6f5d65dd66e06800d86943a45660258552a4"
  "detail": "Pop!_OS 24.04 LTS, Python 3.12.12. Real PTY supervisor observed the matching completion sentinel\
    \ after the test agent stayed alive through the FYI."
- "command": "PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task v1/microkernel/move-slack-fyis-to-a-command-ticket\
    \ --json"
  "status": "passed"
  "head": "40b285cede717bc4b818834f007b8daa6646be3d"
  "base": "657d6f5d65dd66e06800d86943a45660258552a4"
  "detail": "1 OK, zero issues."
- "command": "git diff --check origin/main...HEAD"
  "status": "passed"
  "head": "40b285cede717bc4b818834f007b8daa6646be3d"
  "base": "657d6f5d65dd66e06800d86943a45660258552a4"
  "detail": "No whitespace errors."
```
