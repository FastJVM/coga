---
title: Move Slack FYIs to a command ticket
status: draft
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
step: 1 (design)
---

## Description

Move the `slack` FYI procedure (operands, formatting, route selection) into an editable bootstrap command ticket and complete edge implementation, only with a verified matching-session completion path. Split from v1/microkernel/09-work-orchestration-commands-to-tickets at its owner gate on 2026-11-16; the carried-over design is below.

### Carried-over scope and objectives

Hackability: users can change FYI operands, formatting and route selection
through ticket-owned files. The current head is `src/coga/commands/slack.py`,
`slack` (94 physical lines). It calls `notification.post`, then
`logfile.append_log`, then `repl_supervisor.emit_done_marker` for a bootstrap
ref, through `deferred_done_marker`, which defers the request to command exit
but does not check whether `git.sync_log` succeeded (`True`/`False` confirmed,
`None` miss; truthiness would wrongly reject an already-landed log).

Ticket 09 retained this head under a co-versioning proof: the script phase
clears `COGA_SUPERVISED`, the sentinel and the expected identity, so an edge
script cannot preserve delivery + audit + matching-session completion without
a new parent-owned mechanism. This ticket decides whether that mechanism is
worth its cost, or records the retained head as the settled placement.

Invocation uses 09's plain-launch rules (`slack = "launch bootstrap/slack --"`,
no agent fallback, Typer help recognition, interrupt rule). Verify they merged
before designing on them. Under 09's fail-closed help rule, `--message --help`
is detected as help, and the script must exit 2 when its parse reaches the
command body under `COGA_SCRIPT_HELP=1`; today's head would post the literal
message. Design must decide whether that change is acceptable or require
`-- --help` quoting.

### Carried-over acceptance criteria (from 09, to be refined at design)

- [ ] `slack` operands, FYI formatting and route selection live in
  `bootstrap/slack` and its complete edge implementation, only after the
  completion mechanism below is implemented and reviewed. Otherwise retain the
  entire head and record the owner-reviewed proof; moving ordinary FYIs alone
  does not complete the migration.
- [ ] Ordinary FYIs never complete a task or enclosing session. A bootstrap FYI
  completes only the matching live bootstrap session, after successful channel
  handling, durable audit and command finalization. Mismatched root, identity,
  stale invocation, nonzero child, delivery failure, audit failure, or
  uncertain publication never signals completion. No outer sentinel, assist or
  expected-step authority reaches `ticket.py`; stdout is never a completion
  channel.
- [ ] Preserve disabled-channel handling (diagnostic, audit and `posted`),
  important-route refusal rather than flow fallback, actor resolution, message
  validation, sanitized errors and one send attempt. A delivery followed by an
  audit failure reports the delivered-but-unrecorded state without automatic
  resend. Git-disabled completion requires successful local audit, not a claim
  of remote durability. Explicitly document the stricter audit gate below.
- [ ] Complete local fork through sibling 05; contract owners
  (`coga/notifications`, `producers`, `coga/cli`, `coga/edge-code`,
  `coga/script-tickets`, `coga/state-publication`, `coga-dev/microkernel`)
  updated in the same PR; line counts and Linux receipts as in 09.

### Completion mechanism — options for design

#### Option A — parent-owned audited-notification protocol (carried from 09)

Do not give the script the caller's sentinel or expected-task/assist variables.
Do not treat successful exit from `bootstrap/slack` as proof that a different
bootstrap session finished. Proposed minimal handoff to siblings 03 and 10:

- The invoking parent captures and validates the existing live outer-session
  identity before script isolation: repository identity, bootstrap slug and
  session generation/channel. Repository identity must permit a verified
  same-repository command from a separate checkout/clone, as existing slug
  completion does; an absolute checkout-path equality test is insufficient. With no verified outer session, ordinary FYIs
  still work but cannot end one. A matching string supplied by the child is
  insufficient. Existing supervisor identity checks must gain generation-bound
  verification where needed; no ambient-only new completion credential.
- Provide one fixed, invocation-scoped **audited notification operation**, not
  arbitrary RPC/plugin callbacks. The parent services a structured request
  carrying resolved target, formatted text, requested destination and audit
  message. It resolves target/root and actor itself, uses `notification.post`
  once, appends the audit and confirms required log publication with existing
  `git.sync_log`/strict publication semantics. Return a typed success/failure
  receipt bound to this invocation and target. The edge owns operands and
  formatting, and prints `posted` only after successful acknowledgement.
- Only the parent holds completion authority. For a successful request naming
  the exact captured bootstrap target in the same repository/generation, it
  records a deferred completion intent. Finish only after child exit zero,
  successful audit confirmation and final publication/retained-log checks.
  Use `repl_supervisor.deferred_done_marker`/`emit_done_marker` after those
  checks; do not request a marker merely because a notification was attempted.
- Ordinary task targets and different bootstrap targets may receive valid FYIs
  but never release the outer session. No replay across child invocations,
  nested unrelated scripts, roots or supervisor generations. A child crash,
  stale/duplicate receipt, broken request channel or parent interruption cannot
  authorize completion. Consume/close the one-invocation channel at teardown.
- Disabled notifications keep existing successful no-channel handling; delivery
  failures remain exit 1, invalid operands/config/target/agent remain exit 2.
  A new audit-publication refusal retains the delivered FYI and log, exits 75,
  suppresses sweep/refresh and gives strict-publication recovery. Recovery must
  not resend or replay a completion/transition. Log recovery alone never
  terminates a later session; any new explicit FYI is a new send.

The transport must work on POSIX and native Windows without terminal parsing,
inherit no completion capability into grandchildren, and contain no knowledge
of the Slack alias or command-ticket name. Lifecycle sibling 10 must consume
or explicitly accept the generic verified finalizer; do not count hypothetical
callers as two real consumers. Notification/audit operations retain their
co-versioning proof independently of whether that finalizer gains a second
caller. Add no queue, retry service, durable message spool or general RPC host.

**Tradeoff for owner decision:** this parent operation adds transport and
verification code to move a 94-line head. It is a proposed dependency, not an
existing safe API or an approved implementation. If siblings 03/10 cannot
supply this small bounded operation economically, retain `commands.slack.slack`
under an explicit reviewed proof: it joins delivery, audit and matching-session
completion inside the CLI's deferred finalization, and the script boundary
currently destroys the authority needed to preserve that transaction. Keep
its placement open until the owner accepts that proof; do not claim full Slack
forkability or a completed move. The preferred migration waits for the shared
operation rather than introducing a command-specific completion exception.

There is also a deliberate correctness tightening to approve: today the head
requests completion after local `append_log`, while `deferred_done_marker`
waits for the best-effort sweep but does not inspect whether publication
succeeded. The new durable-audit criterion must reject failed confirmation.
Do not describe this as existing exact remote-durability parity; update
`coga/state-publication`, `coga/script-tickets` and notification owners with
this behavior if approved.


#### Option B — post-exit audit-line check (evaluator recommendation, 09)

The parent captures the session identity before isolation, runs the child,
and after exit 0 confirms on control (or locally when Git is disabled) a new
`slack:` audit line for the captured bootstrap slug written during this
invocation; only then does it request the marker. This trusts cooperative
child output, which Option A rejects. Make the threat model explicit
(accidental versus adversarial completion) so the owner can choose. Option C
is to keep the 94-line head under the proof.

### Test map carried from 09

Extend `tests/test_commands.py`,
`test_slack_accepts_and_completes_stateless_bootstrap_target` and
`test_slack_on_durable_task_does_not_complete_session`, plus
`tests/test_notification_messages.py`, `test_slack_fyi_includes_title`, and
`tests/test_done_marker_emission.py`. Current ambient-sentinel fixtures are
insufficient proof of the proposed verified parent boundary: add real nested
script subprocess tests using fake agent seams, with matching/mismatching
slug, repository and generation, absent/stale identity, ordinary targets,
disabled channel, send/audit/publish failures, already-published audit,
child crash, duplicate request and channel loss. Assert no outer completion
variables or assist authority in the child's environment and no completion
on failure. Pair successful completion with an assertion that finalization
finished before the sentinel write. No real Slack or agent process is needed.


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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
