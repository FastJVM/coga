---
title: Publish sibling ticket handoffs during targeted authoring
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
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
step: 2 (peer-review)
agent: claude
launch_generation: pending:72ba3195-8bbe-424a-8209-787c477f10dd
---

## Description

Targeted `coga ticket <slug>` authoring can detect edits to another ticket
but omit them from its guarded validation and publication, leaving their
durability to a later best-effort sweep. Include tickets authored during the
interview in the finalization boundary and investigate why the observed
cancellation handoff escaped the later sweep. Done means a targeted interview
that updates a sibling publishes the valid changes together, validates all
selected tickets before publishing any part of the finalizer's transaction,
and a cancellation/teardown regression proves the handoff is published or the
command exits nonzero and identifies retained state and its recovery path.
Preserve the existing lifecycle, checkout, and human-gate rules; this work
does not authorize executing the sibling ticket's workflow.

## Context

### Incident and recovery

On 2026-10-28, authoring of
`show-which-agents-are-available-on-the-machine-dur` added an approved 11-line
`## Open Questions` handoff to
`marketing/fix-installer/ask-which-agents-to-enable-during-coga-init`, then ran
`coga mark canceled` on the duplicate. The successor remained at owner design
review; the note concerned agents outside built-in discovery and neither
changed approved requirements nor resolved design findings.

Cancellation published in `3831c8502`; usage in `2b0e4e4d5` reported exit 0
and kind `done`, yet the next interview found the handoff dirty on `main`
and absent from `origin/main`. The transcript returned a running tool-session
ID for cancellation, without a completed exit before the agent ended: timing
evidence only. Both tickets validated after cancellation.

Recovery is complete: `coga run publish-state`, requiring the successor's
absolute path, published the note in `d294c0956`. The tree was verified clean
and the successor matched `origin/main`. Do not replay cancellation or modify
the successor's workflow to recover this incident.

### Confirmed gap and remaining uncertainty

- In `src/coga/authoring.py`, `changed_authoring_paths` detects the sibling
  change, but `finalize_authored`'s `TaskRef` branch selects only the named
  target for `authored_refs` and `task_sync_paths`. `support_paths` excludes
  the whole tasks tree, so it cannot carry the sibling. The `BootstrapRef`
  path instead uses `authored_task_refs` to discover authored tickets.
- Deterministic reproduction: in a disposable configured repo, create two
  valid tickets, snapshot with `snapshot_authoring_state`, change only the
  second ticket, and call `finalize_authored` with the first ticket's
  `TaskRef`. A spy on `git.publish` observes **zero calls**, although
  `changed_authoring_paths` includes the second ticket. This reproduces the
  finalizer omission independently of any concurrent process.
- A complete isolated `python -m coga.cli ticket duplicate --agent codex`
  run with a stub agent that edits a sibling, invokes `mark canceled`, and
  waits did publish the sibling and exit cleanly. The ordinary sweep can
  therefore mask the omission. The exact reason the live sweep missed the
  note remains unproven; retain this distinction and reproduce the relevant
  timing/refusal path before claiming the incident's full cause is fixed.
- Inspect `commands.ticket._run_authoring_session`,
  `commands.mark.canceled`, `launch.spawn_agent_session`,
  `repl_supervisor.run_with_done_marker`, and `cli._sweep_coga_state` for the
  cancellation-to-finalization boundary. The done marker is emitted before
  the child CLI's final sweep; supervisor teardown signals the process group.
  The outer `coga ticket` invocation also has an end-of-command sweep after
  finalization. Interrupting the child sweep alone therefore does not explain
  the retained handoff: trace the outer finalizer and sweep as well, including
  refusals and whether either process actually reaches them. Preserve
  intentional withholding after validation/publication refusal.

### Scope and verification

Cite `coga/state-publication`
(`docs/contexts/coga/state-publication/SKILL.md`) rather than attach it; read
"When Coga publishes" and "Strict publication on demand". Guided authoring
owns a guarded publish of authored state, and publication refusal retains
edits with a nonzero result. Update this owner and its packaged twin if the
contract changes. Cite `coga-dev/internals/state-publication`
(`docs/contexts/coga-dev/internals/state-publication/SKILL.md`), sections
"The end-of-command sweep" and "Guided-authoring finalization", for the
implementation explanation; this topic is also cited rather than attached
and must be updated with the fix. For teardown, cite
`coga-dev/internals/agent-spawn`
(`docs/contexts/coga-dev/internals/agent-spawn/SKILL.md`), section "The
supervisor", rather than attach it: a `done` outcome describes how the agent
was stopped, not proof that the child CLI finished its sweep. Update that
owner if supervisor behavior changes.

The no-partial-publication guarantee applies to the finalizer's own
transaction. Earlier lifecycle commands and their sweeps can already have
published state; an authorized cancellation must not be rolled back. Test an
invalid authored sibling followed by cancellation and record which writes
precede finalization, without claiming the finalizer prevented earlier
publication. A broader change to sweep isolation or supervisor design needs
a separate design decision if the investigation proves it necessary.

### Regression coverage

Extend `tests/test_authoring.py` and appropriate command/supervisor coverage:

- An unchanged, canceled, or deleted named target must not hide edits to
  surviving siblings. Continue validating an existing named target even when
  unchanged; validate every other selected ticket before the finalizer's
  first publication write. Keep authored ticket and support-file changes in
  the same guarded transaction.
- An invalid authored sibling prevents the finalizer from publishing any
  selected ticket or support file, retains the edits, and produces a nonzero
  command result with its sweep withheld. Separately cover cancellation
  before finalization and distinguish writes already published by that
  lifecycle command from writes attempted by the finalizer.
- Cover newly created and deleted sibling tickets, attachment-only edits and
  deletions, and file-to-directory promotion, including both sides of the
  move. Deleted tickets have no remaining body to validate; their removal
  must still be accounted for in publication.
- Exclude paths unchanged since the entry snapshot, even when they were
  already dirty, including an untouched dirty attachment beside a changed
  ticket. File fingerprints identify changed paths, not hunk authorship;
  decide how a pre-dirty path edited again is treated before coding, then
  document and test that choice.
- Exercise the PTY done-sentinel teardown path with controlled synchronization
  around cancellation and its sweep, not only a stub that waits for the
  cancellation subprocess to finish. Assert the outer command's completed
  exit, diagnostics, remote ticket bytes, and any retained local edits. A
  session usage record with outcome `done` alone is insufficient evidence.

Use isolated local Git remotes and stub agents; do not require Slack, real
agent credentials, or network services. Keep these tests deterministic;
timing sleeps alone must not establish that the cancellation race occurred.
Record exact commands and results and keep the fixture-interpreter fix in
`fix-release-env-fixture-interpreter-symlink-in-fre` separate.
Shared `code/open-pr` prompt cleanup is also out of scope; its historical
recovery narrative is a separate maintenance candidate.

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

## Dev

branch: coga/publish-sibling-ticket-handoffs

## Implementation plan

Codex is implementing this step (the ticket's configured agent remains unchanged).
Start verified clean on current main. Extend targeted finalization to include
changed sibling paths, validating all surviving selected tickets before the
single publication. Reproduce cancellation with synchronized PTY teardown and
trace both child and outer sweeps; do not infer the live incident's cause from
a done outcome. Preserve lifecycle and owner gates. Tests and documentation
will specify file-level treatment of paths dirty before the interview.

## Implementation findings

- Selection uses exact changed file paths, including deleted siblings and both
  sides of promotion; every surviving changed/new sibling and the existing
  named target validate before publication. Untouched entry dirt is excluded
  from this transaction, including attachments beside changed tickets. A
  pre-dirty path edited again is carried in full (no hunk attribution).
- No lifecycle or supervisor implementation changed. Cancellation still
  publishes its transition and signals done before its child CLI sweep.
  The new PTY fixture gates sentinel observation at that sweep boundary,
  reaps the cancellation subprocess, and checks the outer completed exit,
  remote bytes, and retained edits. The successor stays at owner design review.
- Five synchronized cases passed: interrupted/completed child sweep with a
  valid sibling, interrupted/completed child sweep with an invalid sibling,
  and interrupted child sweep plus remote publication rejection. A completed
  lifecycle sweep may already publish an invalid sibling; the finalizer
  refuses without rolling back those prior writes or cancellation.
- Baseline experiment used HEAD's original authoring.py in an isolated fixture:
  PTY outcome done/0, cancellation child exit 143, outer sweep reached and not
  withheld, outer command exit 0 despite rejecting remote. Finalizer selected
  only duplicate + context; sibling remained dirty locally and absent remotely.
  Evidence: /tmp/coga-sibling-baseline.log and
  /tmp/coga-sibling-baseline-run/test_ticket_cancellation_pty_f0/synchronization/.
  This proves the omission plus an outer-sweep refusal can reproduce the symptom;
  it does not prove which refusal/interruption occurred in the live incident.
- Initial new regressions failed 21/21 before the fix. Current authoring tests:
  `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_authoring.py -q --tb=short`
  -> 55 passed. The PTY subset -> 5 passed. Full-suite verification passed: 4338 passed, 10 skipped (see PR receipts below).
- Example fixture validation (from tests/fixtures/seeded-repo/coga):
  `env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json`
  -> exit 0, ok_count 5, no issues.

## PR

```yaml
title: Publish sibling ticket handoffs during targeted authoring
author: codex
author_evidence: This implement session ran Codex, not the ticket-configured Claude. No additional
  model override was requested; the exact model variant is not exposed in this session.
head: 1984164d6441202852d0631fe2a33c064b4e50ab
base: 192fd278c324a570a8231bcc4e25f5c55c772eb1
depth: deep
rationale: Changes publication durability and validation scope. Independent code review is the next
  workflow step; the historical incident cause remains unproven.
implementation: Targeted and bootstrap finalization discover changed/new siblings, validate every
  surviving selected ticket plus the existing named target, and publish exact changed paths with support
  files in one guarded transaction. Failures keep edits and report strict recovery with the outer
  sweep withheld.
deviations: None. Lifecycle commands, supervisor behavior, checkout rules, and owner gates are preserved.
  No PR has been opened.
limitations: The synchronized old-finalizer experiment reproduces exit 0 with a retained sibling when
  the child sweep is interrupted and the outer sweep is rejected; it does not establish the live incident
  cause. Earlier lifecycle sweeps can publish an invalid sibling before finalization rejects it. Verification
  used Linux/Python 3.12.12; native Windows and Python 3.11 were not run.
files:
  docs/contexts/coga-dev/internals/state-publication/SKILL.md: Explain exact file selection, validation
    ordering, and the child/outer cancellation publication boundaries.
  docs/contexts/coga/state-publication/SKILL.md: Own the sibling handoff, pre-dirty file, deletion,
    and retained-state recovery contracts.
  src/coga/authoring.py: Validate surviving authored siblings and select exact changed paths, including
    deletions, in one required-path publication.
  src/coga/commands/ticket.py: Identify retained authoring state and strict recovery after finalization
    refuses with its sweep withheld.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Keep the shipped
    user contract byte-identical to its canonical topic.
  tests/fixtures/authoring_cancellation.py: Synchronize real PTY teardown with the cancellation child
    sweep and observe the outer CLI boundary.
  tests/test_authoring.py: Cover sibling discovery and validation, exact paths, pre-dirty files, attachments,
    removals, and promotions.
  tests/test_git.py: Prove an invalid sibling prevents the outer command from publishing tickets or
    support files without cancellation.
  tests/test_ticket.py: Check complete outer exits, diagnostics, local/remote bytes, and owner-gate
    preservation through cancellation.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: This is the implement step; independent code review belongs to the next frozen peer-review
    step.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q --tb=short
  status: passed
  head: 1984164d6441202852d0631fe2a33c064b4e50ab
  base: 192fd278c324a570a8231bcc4e25f5c55c772eb1
  detail: '4338 passed, 10 skipped in 530.05s (exit 0), Python 3.12.12 on Linux. The suite reported
    its skips; none were added to suppress failures. Tested source/tests/docs equal the committed
    tree. Output: /tmp/coga-sibling-full.log.'
- command: cd tests/fixtures/seeded-repo/coga && env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src
    /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json
  status: passed
  head: 1984164d6441202852d0631fe2a33c064b4e50ab
  base: 192fd278c324a570a8231bcc4e25f5c55c772eb1
  detail: Exit 0; ok_count 5; fixes and issues empty.
- command: git diff --check origin/main...HEAD
  status: passed
  head: 1984164d6441202852d0631fe2a33c064b4e50ab
  base: 192fd278c324a570a8231bcc4e25f5c55c772eb1
  detail: Exit 0; no whitespace errors.
```

## Implement handoff

Implementation commit: `1984164d6441202852d0631fe2a33c064b4e50ab`.
Pushed branch: `coga/publish-sibling-ticket-handoffs`.
Fresh control at push: `192fd278c324a570a8231bcc4e25f5c55c772eb1`.
No PR opened. Next step is independent peer review of the publication selection
and the synchronized cancellation tests. The implementation changes no sibling
workflow or owner gate. The separate fixture-interpreter ticket remains
`v1/12-fix-release-env-fixture-interpreter-symlink-in-fre`; no edits were made
there or to shared open-pr prompts.

Full verification ran on the committed implementation; source, tests, and
contexts were checked unchanged afterward. The initial regression-only run
failed 21 tests on the old implementation. Two preliminary full runs were
interrupted before completion while finalizing fixture/doc changes; they are
not verification receipts. The complete committed-head run above is the final
result. Baseline refusal evidence is retained in the local paths above and its
conclusions are captured here for review.

Manual checkout return completed: the published ticket bytes were verified
against origin/main before restoring the feature copy; main was fast-forwarded
and verified clean. `coga validate --task publish-sibling-ticket-handoffs-during-targeted-au --json`
then returned exit 0, ok_count 1, no issues. Advancing implement to peer-review.
