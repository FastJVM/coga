---
title: Coalesce Coga state commits to one per lifecycle event
status: active
owner: nicktoper
contexts:
- coga-dev/principles
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
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
agent: claude
---

## Description

Coga's own state publication buries real work in `git log`: of the last 300
commits on `main` examined on 2026-10-23, 233 were bookkeeping (`Ticket: …`,
`Log: …`, and `Sync coga state …`), with several commits per launched step.
Design and implement coalescing of writes that can share a publication
boundary, reducing bookkeeping without delaying state another operator needs.

The design step establishes and justifies an achievable commit bound for
explicit launch scenarios; the owner approves it before implementation. One
lifecycle commit plus at most one teardown log commit is a hypothesis for a
step with no separate startup publications, not a promised total for every
launch. The usage record is captured after the agent's final lifecycle sync;
activation, start, branch linkage, and queue admission can introduce other
publication deadlines that the design must account for.

### Design requirements

Define the counting interval from immediately before launch entry to after
usage capture, checkout return, and the command's final sweep. Use an isolated
seeded Git repository with a remote, deterministic agent and usage fixtures,
and an owner handoff after one bump. Count actual new commits on control and
inspect their contents, not merely calls to sync helpers. Compare a resumed
`in_progress` step with an initial `active` launch; account separately for
draft activation, branch creation versus reuse, and megalaunch admission.
Explain every retained startup commit rather than silently excluding it from
a claimed whole-launch bound. A clean sweep must remain a no-op.

Choose the smallest grouping consistent with publication deadlines. Lifecycle
state must be visible when the command hands off, before the next operator
can act. Do not delay a required publication, rewrite or force-push shared
`main`, weaken publication guards, or hide a failed publish. Verify deferred
lines when an agent exits without a transition, fails, or is interrupted, and
preserve retained-state/withheld-sweep diagnostics. Classify bootstrap,
authoring, script, recurring, and megalaunch paths explicitly; a bound for an
ordinary task is not automatically their bound. Preserve admission and
checkout guarantees, and take any necessary contract change to the owner
design gate.

Done when the owner has approved the bound and its tradeoffs, seeded real-Git
launch-and-bump tests assert that bound and publication timing, affected
failure and no-transition exits retain their publish-or-report guarantee,
`recurring_activity` preserves its current classification, the publication
topics and packaged twins are updated in the same PR, and `python -m pytest`
passes.

## Context

Split from `fix-the-commit-git-journal` (deleted); sibling
`commit-journal/trim-the-audit-log` owns log size and retention.

### Prerequisite already landed

`commit-journal/publish-log-lines-left-uncommitted` landed in
[PR #1117](https://github.com/FastJVM/coga/pull/1117) on 2026-10-26. Its durable
contract is in `coga/state-publication`, "Every log line has a publisher":
each log write publishes before its command exits, reports retained lines,
or has a documented later publisher. The inventory distinguishes lifecycle
syncs, explicit log syncs, and sweeps; initialization's human-owned first
push, usage teardown, writer-owned later publishes, and withheld-state exits
are deliberate exceptions. Failure records are covered by the failure
report, not retried in a publication loop.

That work deliberately made `coga ticket` publish its start line immediately,
matching chat and ordinary launch: a dirty log throughout an attended session
can block fast-forwards and clean-checkout checks. Any proposed deferral must
address that reason and identify its later publisher, including when the
agent never bumps. Re-inventory `logfile.append_log` callers across `src/`
and update the owning topic's deliberate-deferral list for every changed path.
`checkouts.enter_ticket_checkout` requires clean control before switching;
deferring the managed launch audit must preserve that precondition.

### Where commits come from

- `git.sync_log` publishes `log.md` alone. Managed ordinary launches use
  `launch._LaunchInvocation._prepare_step_checkout` before switching; unmanaged
  launches also pass `commit_log=True` from
  `launch._LaunchInvocation._supervise_steps` to
  `launch.spawn_agent_session`. `commands.ticket._run_authoring_session`
  passes it too. Script and recurring launch writers have their own paths.
- `git.sync_task_state` publishes a task and the log together. Besides
  `bump.advance_step`, inspect `mark.mark_active`, `mark.mark_in_progress`,
  and `checkouts._publish_linkage`: launch startup can publish before the
  final bump. Commit subjects must still name the ticket and event, such as
  `Ticket: <slug> — step 4 (review)`.
- `megalaunch._launch_until_stop` publishes a strict start claim;
  `megalaunch._admit_launch_claim_after_release` separately publishes the
  admitted generation and launch audit after releasing the held child. Their
  ordering protects concurrent launches and cannot be folded away casually.
- `git.sync_coga_state` covers entry/return settlement and the exit sweep
  selected by `cli._should_sweep_coga_state`. An agent's blackboard edit can
  be swept by a command before bumping; the historical extra sweep
  `a2388fbe0` carried such a `pr:` edit.
- `launch.spawn_agent_session` captures usage in `finally` and then calls
  `git.sync_log`, after the agent's final `bump`/`mark` publication.
  `cli._warn_unpublished_log_lines` checks changed logs at command exit,
  including after a sweep; coalescing must preserve this failure reporting.

### Inactivity classification

Preserve `recurring_activity.is_machine_commit` and `_MACHINE_SUBJECT`
semantics, including the exceptions. Ordinary ticket lifecycle commits
count as activity; `Ticket: recurring/…`, `Ticket: autofix/…`, and blocker
reminders remain machine activity. Ordinary `Log:` and `Sync coga state`
commits remain machine activity, while `Log: bootstrap/…` counts as activity.
A coalesced ordinary lifecycle event must keep its activity classification,
and coalescing must not turn recurring/autofix lifecycle events into human
activity. Pin the affected subjects in regression coverage, using
`tests/test_recurring_activity.py` as the existing reference. Do not broaden
the classifier to make the repository look idle.

### Topics (cited, not attached; read before design)

- `coga/state-publication` at
  `docs/contexts/coga/state-publication/SKILL.md`, "When Coga publishes" and
  "Every log line has a publisher", plus "Control versus feature checkouts",
  owns publication deadlines and the deliberate deferrals summarized above. This is an edit target; update it
  and its twin at
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md`
  together.
- `coga-dev/internals/state-publication` at
  `docs/contexts/coga-dev/internals/state-publication/SKILL.md`, "Invariants"
  and "The end-of-command sweep", owns control as canonical, retaining
  failed writes, candidate selection, and deliberate sweep skips. Its leaf
  `coga-dev/internals/state-publication/publish` at
  `docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md`,
  "`publish` and its wrappers" and "Best-effort versus strict", owns the
  guarded transaction and failure distinctions that coalescing must retain.
- `coga-dev/internals/spool-merge` at
  `docs/contexts/coga-dev/internals/spool-merge/SKILL.md`, "How `publish`
  lands a union path" and "Crash-safe replacement is not a lock", owns
  concurrent append preservation and duplicate suppression. Keep log
  publication on that union-safe path; atomic writes and the per-checkout
  lock do not provide a cross-checkout lock.
- `coga-dev/internals/launch-claims` at
  `docs/contexts/coga-dev/internals/launch-claims/SKILL.md`, "Strict claim
  publication", "The pending seal", and "Held child and admission", owns
  the claim ordering summarized above. Account for those boundaries without
  redesigning launch ownership in this ticket.

Update any cited topic whose behavior changes in the same PR, keeping shipped
twins identical. Out of scope: log retention/compaction and sandbox Git-access
failures; this ticket preserves their existing reporting and recovery.

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
