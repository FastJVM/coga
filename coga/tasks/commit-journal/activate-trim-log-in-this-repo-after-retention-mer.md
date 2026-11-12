---
title: Activate trim-log in this repo after retention merges
status: done
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
agent: claude
---

## Description

Enable audit retention in this repository using the current package-owned
trim-log definition. The owner approved the revised procedure on 2026-11-08
and controls both users; the owner coordinates their upgrade and resumption.
The current installer changes only `coga/recurring/jobs.toml` and
`coga/.gitattributes`. Definitions and the workflow resolve from the package.
The earlier five-live-file and manual-only plan is retained under
`## Superseded designs` on the blackboard.

### Acceptance criteria

- [x] Fresh control contains PR #1129's merged retention implementation
  (`42d1b30a47e30bb642f9e610d950681acdacd595`) and the package-definition
  cutover, verified by ancestry and source/resource inspection.
- [x] A non-editable wheel from a recorded source revision and SHA-256 is used
  to capture the installer output on the implementation branch. Only the job
  selection and log attribute change; a second invocation is a no-op.
  Configuration bytes and effective retention (currently the implicit 30-day
  default), unrelated selections/attributes, phone-home state and periods are
  preserved. Explicit retention `0` and disabled or parked jobs remain
  protected by the existing installer refusal tests.
- [ ] One reviewed PR merges selection and attribute adoption with removal of
  the attribute exception and obsolete rollout instructions. The package
  remains the sole definition owner. Packaging checks explicitly cover the
  selected job and permit its validated state carrier after first use.
- [ ] Control reports `coga/log.md: merge: unset`; the retire-worklist attribute
  remains `union`. Read-only discovery resolves packaged trim-log with
  `0 4 * * 1`, repo scope, `run_when_inactive: true`, and `trim-log/run`.
  Its package script and workflow exist, and its script is executable on
  POSIX. No operative staging instructions remain outside archived history.
- [ ] Focused packaging/retention/installed-wheel tests, the full local suite,
  pristine wheel packaging, scoped ticket validation, seeded-fixture validation
  and `git diff --check` pass on the final tested tree. Record exact commands,
  interpreter/platform, counts, head/base revisions, and unavailable evidence.
  Native Windows evidence required by `coga-dev/testing` remains a pre-merge
  obligation; there is no hosted test CI.
- [ ] After this launch exits and before merge or scheduler resumption, the
  owner replaces the deployment installation behind `~/.local/bin/coga` with
  the compatible non-editable wheel and records revision/hash and restart
  disposition. Fresh merged control is verified before releasing schedulers.
  Autoclose stays off through the resumption record and owner completion.
  No production trim, forced period, telemetry delivery, or manual log/cursor
  rewrite is used as proof.

### Approved implementation and publication

1. Use launch's prepared branch and return protocol. Keep the separate editable
   deployment source `/home/n/Code/coga` unchanged during implementation.
   Build an isolated wheel from fresh control, verify imports/resources and
   hash, then use its launcher's resolved interpreter to run
   `python -m coga_edge.trim_log --install` on this branch. Snapshot target
   preimages and config/state hashes outside the Coga roots and verify the
   exact two-file change and second-run idempotence.
2. Remove the `coga/.gitattributes` packaging divergence exception; add explicit
   selection/definition coverage and allow the first-use trim-log state carrier
   without allowing local definitions. Update the packaging topic and packaged
   runbook, and align the seeded runbook with that owner. Staging files and
   their special tests/fallbacks were already removed by the package cutover.
3. Test, commit the complete bundle, reconcile with main and push. Keep every
   adoption, test and documentation edit committed before a Coga publication
   or session handoff; dirty files inside the state roots can still publish
   ahead of review. Write this ticket's handoff without committing it, then
   bump once. Launch returns the checkout. Review and owner-assist sessions
   may use the same managed procedure. Open the PR only at `open-pr`.
4. The owner coordinates the two users, replaces the deployment wheel after
   the current launch exits, and keeps excluded writers and schedulers from
   running until compatible. Before merging, record that installation receipt
   and obtain the required review/platform evidence. Merge the entire bundle,
   verify fresh control and installed resources, then record which writers
   resume or remain stopped. PST/PDT is the approved scheduler timezone; the
   first ordinary sweep may service the latest past Monday immediately.

The owner-approved post-merge exception remains: verification and resumption
stay on this ticket; `open-pr` files no separate drafts for them. Autoclose
remains stopped until the disposition is recorded and the owner completes the
final gate. Existing exclusions remain in force; the abandoned Retro checkout
is untouched. The implementation session does not replace its running CLI.

### Verification and recovery

Run focused `python -m pytest tests/test_packaging.py tests/test_trim_log.py
 tests/test_edge_distribution.py`, followed by `python -m pytest`, with the
checkout's test interpreter and absolute checkout `PYTHONPATH`. Build the wheel
from a pristine scratch clone, which is not a production writer. Run
`git diff --check`, `coga validate --task
commit-journal/activate-trim-log-in-this-repo-after-retention-mer --json`, and
fixture validation from `tests/fixtures/seeded-repo/coga` with
`SLACK_WEBHOOK_URL` unset. Use read-only recurring discovery, configuration
loading and Git attribute inspection; no period needs to be materialized.

Retain source revision, wheel hash, installer preimages and idempotence proof,
configuration/state preservation, and final review/check receipts. After any
runbook edit, use the wheel built from the matching reviewed tree when
repeating installer checks. Recheck selection, packaged definitions,
attributes and effective retention on merged control before resumption.

Before merge, preserve the branch and operation-owned edits if interrupted;
resolve refusals without overwriting customizations. After merge, stop affected
writers and use a reviewed forward repair with a compatible wheel/repo pair.
Never restore the old union attribute, downgrade to a pre-retention writer,
roll back log/cursor state, delete mutation receipts, or replay transitions.
The persistent trim-log runbook owns detailed recovery.

### Out of scope

Retention algorithm/policy changes, configuration edits, other repositories,
unreviewed forks, unrelated checkout/task cleanup, hosted CI changes, manual
log/cursor edits and production maintenance or delivery tests.

## Context

### Current installer and package ownership

Read the packaged trim-log runbook at
`src/coga/resources/templates/coga/recurring/trim-log/operations.md`,
"Adoption after the compatible wheel upgrade" and recovery sections.
`src/coga_edge/trim_log.py`, `install`, validates legacy overrides and the
complete plan before writing only the selection and attribute;
`_attribute_plan` verifies effective attributes using a temporary index.
`main` routes exact `--install` without maintenance, reporting, or bumping.
`_phone_compatible` checks phone-home cursor/shim compatibility during
maintenance; installer success alone does not certify a custom fork.

`coga/edge-code/edge-code-upgrades.md` under packaged
`bootstrap/contexts/` owns the `migration:interpreter` command. Preserve the
launcher shebang's interpreter environment, not the resolved base Python.
`docs/contexts/coga-dev/packaging/SKILL.md`, "Package ownership and repo state"
and "Wheel packaging", owns the one-definition inventory and pristine build.
`tests/test_packaging.py`, `_ownership_problems` and
`test_live_counterpart_exceptions_stay_real_and_explained`, reject local
copies and stale exceptions. First-use state is separately validated by
`src/coga/recurring_state.py`, `inspect_parent_dir`.

### Publication and read-only verification

Read `coga/state-publication`, "Control versus feature checkouts", from
`src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md`.
`src/coga/git.py`, `_publish_locked` and `_routine_state_areas`, retain clean
committed recurring/configuration/knowledge edits on feature branches until
merge; dirty state-root files still publish. This current guard replaces the
old manual-only publication workaround. `coga/checkouts` and its reconciliation
leaf own branch handoffs and preserving the projected ticket during rebases.

`src/coga/recurring.py`, `list_templates` and `Template.load`, provide read-only
discovery and template fields. `ensure_template_state` creates the package-backed
parent carrier only on an admitted execution, so adoption does not need a live
parent. `src/coga/config.py`, `load_config` and `_parse_log`, preserve explicit
retention `0` and supply 30 when the setting is absent. The packaged
`coga/recurring/scheduling` topic, "Periods and the serviced-period ledger",
owns first-sweep catch-up.

`docs/contexts/coga-dev/testing/SKILL.md`, "Which code you are actually testing"
and "Verification tiers and receipts", owns interpreter and platform evidence.
`tests/test_trim_log.py`, `test_install_idempotence_and_exact_allowlist`, and
`tests/test_edge_distribution.py`,
`test_installed_trim_log_adoption_and_headless_period` and
`test_documented_trim_adoption_uses_resolved_interpreter`, cover the installed
adoption path and opt-out without production execution.

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

pr: https://github.com/FastJVM/coga/pull/1191
branch: coga/commit-journal-activate-trim-log-in-this-repo-af-fb9f3f

## Open PR — 2026-11-08

`coga open-pr commit-journal/activate-trim-log-in-this-repo-after-retention-mer`
completed successfully from clean, current `main` and recorded
[PR #1191](https://github.com/FastJVM/coga/pull/1191) under Dev. Verified that
the PR record published to control, the PR is open and targets `main`, and
its head is the reviewed `68bba9ef085a62965b2fd0f4c8648a812699ec6f`.
GitHub reports it mergeable. The generated presentation retains the deep
recommendation, explicit self-review identity, actual receipts and outstanding
merge gates.

Fresh control before publication was `b576d62138d1f0e8c2a9f8ff21c32dd93e95c72d`.
Only this ticket and the audit log had advanced since the reviewed base
`8e536f3d389b9626c2638a57f15f8d7034f00fc8`; the command accepted that
non-overlapping generated state. The six-file implementation diff and reviewed
head are unchanged. `git diff --check origin/main...coga/commit-journal-activate-trim-log-in-this-repo-af-fb9f3f`
passed; no implementation tests were rerun in this mechanical publication step.

Direct review is recorded as completed with no must-fix findings. Native
Windows full-suite evidence and the deployment replacement with the compatible
non-editable wheel, including revision/hash and restart disposition, remain
required before merge. Fresh merged-control verification, writer/scheduler
resumption and owner completion remain here under the explicit exception;
no follow-up drafts were created. Keep autoclose stopped through that record
and owner completion. Deployment and schedulers were not changed by this step.

## Implementation — 2026-11-08

Implemented and pushed `3ac517d7abf78ca9ecb263090e1df096495d62ba` on the recorded branch. The final fetch found
`origin/main` at `dbcd84b8572a6213f3cbc3fc9d626d680aa1512f` with both adoption targets still at their
pre-adoption bytes. The bundle remains on the feature branch pending review;
no PR was opened. Launch owns checkout return after the handoff.

The owner approved the current two-file, managed-launch procedure and controls
both current users and their coordination. `coga unblock` resolved the old ask
before implementation. Existing exclusions, PST/PDT timezone, the autoclose
hold, and the post-merge ownership exception remain in force. The rewritten
body is the current contract; prior planning is retained under Superseded designs.

### Change and verification

- The isolated wheel installer selected trim-log and changed only the log
  attribute. Its repeat was a no-op. Retention stays 30; the log uses `-merge`
  and the retire worklist still uses `union`.
- Removed the attribute packaging exception and updated the owning packaging
  topic plus package/fixture runbooks. No live definition copies or period
  were created. The staging tree and staging-only checks were already gone.
- A regression check found that the first ordinary run's state carrier would
  fail the package inventory. The narrowly named lazy carrier is now allowed
  when absent and validated when present; local definition copies remain
  forbidden. Both new tests failed before the fix and passed afterwards.
- Focused suite: 119 passed in 79.47s. Full suite: 4655 passed, 11 skipped in
  888.95s. Linux x86_64, Pop!_OS 24.04 LTS, Python 3.12.12. The committed bytes
  were verified against the focused run; the full run tested this exact head.
- Installed-wheel checks verified five package resources against source,
  executable script, package workflow and read-only discovery, config/retention
  and 341 preserved Coga files. No production maintenance or delivery ran.
  Scoped validation passed (1 task); seeded validation passed (5 tasks).

### Wheel and installation receipts

Retained artifacts and logs: `/home/n/Code/codex/coga/.coga/rollouts/trim-log/3ac517d7abf78ca9ecb263090e1df096495d62ba`.

- Initial capture wheel: source `dbcd84b8572a6213f3cbc3fc9d626d680aa1512f`,
  SHA-256 `70e4f0e5cdcb153d76ced3478ed8af10fc39c7f391341fb0833d5ff7b4a69861` (`base-wheel/`).
- Candidate final wheel: source `3ac517d7abf78ca9ecb263090e1df096495d62ba`,
  SHA-256 `86e4c95bbef0225374621565d79efcfca8a239b795abb097195d9dd223c44105` (`final-wheel/coga-0.4.1-py3-none-any.whl`).
- Isolated non-editable interpreter: `/tmp/coga-trim-log-rollout-20261108-0274abfd/wheel-env/bin/python` (Python 3.12.12).
  `coga_edge.trim_log` imports from its site-packages, with source SHA-256
  `aa5961dfc5319be344aac727b0862e8e4ad8cbbc768ce961123191a70ba78b14`. The final-wheel installer is a no-op too.
- Existing deployment launcher `/home/n/.local/bin/coga` still resolves to
  `/home/n/.local/share/uv/tools/coga/bin/python` (Python 3.14.4), editable from
  `/home/n/Code/coga`. That checkout remained clean at
  `76fb34a33858e9ce31334ef185e4efbc3624eb57`; its source fingerprints were rechecked unchanged.
  No deployment replacement or scheduler restart is claimed.
- Shared config SHA-256: `1d64d233bb7ba4fb8a810cf20bd1c1e3f448884b282fd0805311539cff8234e2`.
  Local config SHA-256: `67b7f3c98f071a956ad4a2ff5d4b96debdf34f5d001213dce981430a9ad1de23`.
  Per-file pre/post hashes, resource hashes, preimages and command output are
  in `adoption.json`, `verification.json` and the retained logs. Original
  capture preimages remain at `/tmp/coga-trim-log-rollout-20261108-0274abfd/preimages`.

### Remaining gates

Current review receipts are recorded below under Peer review. The native
Windows full-suite receipt is still required before merge; saved harness records contain no provisioned host, and
this session allocated none. No Linux receipt is presented as Windows evidence.
The owner replaces the deployment install after this launch exits and before
merge or scheduler resumption. Rebuild the candidate wheel if review changes
its source/resources, and record the installed revision/hash and restart.

After merge, verify fresh control's selection, package resources, attributes
and preserved retention before the owner releases the two users/schedulers.
Record who resumed or remains stopped, then complete the owner gate before
releasing autoclose. The explicit exception keeps these obligations on this
ticket; `open-pr` must not create follow-up drafts for them. Recovery uses a
compatible reviewed wheel/repo pair and forward repair; do not restore the old
union attribute, log history or cursor state.

No other implementation finding remains open.

## Peer review

Direct Codex review **completed** on 2026-11-08, with **no must-fix findings**.
Reviewed head `68bba9ef085a62965b2fd0f4c8648a812699ec6f` against base
`8e536f3d389b9626c2638a57f15f8d7034f00fc8`. Implementation was also Codex, so this fresh
session is recorded as **self-review** under the PR identity rubric; the
configured peer role is not independent-review evidence. No implementation
changes were needed. No nested review CLI or subagent was used.

Preserved the projected ticket outside the repository and verified its bytes
before clearing it for the required fetch/rebase. Rebased the implementation
commit onto current main without conflicts, then restored and byte-compared
the ticket. `git range-diff` confirms the implementation patch is unchanged.
Main's intervening changes were this ticket's handoff and audit entries; the
final fetch still found the same base. Pushed the rebased branch with
`git push --force-with-lease origin coga/commit-journal-activate-trim-log-in-this-repo-af-fb9f3f`;
the remote moved from `3ac517d7abf78ca9ecb263090e1df096495d62ba` to the reviewed
head. The six implementation paths remain committed; this ticket stays
unstaged for launch's return/publication protocol.

Reviewed the two-file installer output and preservation/refusal coverage,
package-only definition/workflow discovery, exact log and retire attributes,
first-use carrier validation and local-definition rejection, the committed
state publication boundary, and adoption/recovery documentation. Package and
seeded runbooks are identical. Remaining staging references are historical
cutover task records or this ticket's Superseded designs, not operative
instructions. The diff changes no terminal/pager/notification rendering, so
no interactive-surface check applies.

Verification on the reviewed head: focused suite **119 passed in 64.59s**;
full local suite **4655 passed, 11 skipped in 734.34s**. Both used Python
3.12.12 on Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic x86_64, with
absolute checkout `PYTHONPATH`. Scoped ticket and seeded-fixture validation
passed (1 and 5 tasks); `git diff --check origin/main...HEAD` passed. Exact
commands and head/base receipts are in `## PR` below.

The pristine wheel built from `68bba9ef085a62965b2fd0f4c8648a812699ec6f` has SHA-256
`86e4c95bbef0225374621565d79efcfca8a239b795abb097195d9dd223c44105`, identical
to the implementation candidate. A new isolated non-editable environment
verified its import, implementation and five resource hashes, executable
script and package workflow, Monday 04:00 repo scope with inactive runs,
retention 30, log merge unset and retire merge union. Its installer invocation
reported already installed/no changes. All 368 files under the Coga root
were byte-preserved during installed verification. No parent/period was
created and no maintenance, forced period or delivery was run. The separate
deployment source remains clean at
`76fb34a33858e9ce31334ef185e4efbc3624eb57`.

Retained review logs, hashes, preimages, scripts, wheel and preparation:
`/home/n/Code/codex/coga/.coga/rollouts/trim-log/68bba9ef085a62965b2fd0f4c8648a812699ec6f/peer-review`.
Original execution scratch: `/tmp/coga-trim-log-peer-20261108-0lxewa0h`.

Recommendation: **deep**. Completed code review is not merge approval. Native
Windows full-suite evidence at this head is still required before merge;
saved completed harness instances are terminated and no new instance was
allocated. This Linux/Python 3.12 run is not Windows or Python 3.11 evidence.
The owner must replace the deployment installation with the compatible
non-editable wheel after this launch exits, recording source/hash and restart
disposition before merge or scheduler resumption. Post-merge verification,
resumption and owner completion remain on this ticket, with autoclose held;
the mechanical `open-pr` step must not create follow-up drafts for them.

## PR

```yaml
title: Activate packaged trim-log in this repository
author: codex
author_evidence: The recorded implementation session was executed by Codex. This fresh Codex review session
  made no implementation changes; its rebase preserved the patch exactly.
head: 68bba9ef085a62965b2fd0f4c8648a812699ec6f
base: 8e536f3d389b9626c2638a57f15f8d7034f00fc8
depth: deep
rationale: Audit-retention activation needs owner inspection. Direct Codex self-review completed with
  no must-fix findings; native Windows full-suite evidence and the deployment wheel replacement remain
  required before merge. This is not merge approval.
implementation: Select the packaged weekly job and log merge attribute in one commit, remove the transitional
  packaging exception, accept validated first-use state, and update adoption documentation and the seeded
  runbook.
deviations: Owner approved the current two-file package-based, launch-managed procedure on 2026-11-08.
  The package cutover had already removed staging and its special test/link fallbacks. The deployment
  wheel replacement is deferred until this launch exits, before merge or scheduler resumption. Owner controls
  both users and handles their coordination.
limitations: Native Windows full-suite evidence at the reviewed head is unavailable; saved harness instances
  are terminated and no new instance was allocated. Deployment CLI remains editable and must be replaced
  after this launch exits, before merge or scheduler resumption. Review is self-review under the identity
  rubric, not independent. No production trim, forced period or telemetry delivery was performed. No terminal/Slack
  rendering change requires interactive verification. Post-merge verification and resumption remain on
  this ticket under the owner exception; open-pr files no follow-up drafts and autoclose stays stopped
  until the disposition and owner completion.
files:
  coga/.gitattributes: Adopt the package log -merge rule while preserving the retire-worklist union rule.
  coga/recurring/jobs.toml: Select the packaged trim-log job without changing other job selections.
  docs/contexts/coga-dev/packaging/SKILL.md: Describe this repository's adoption and its optional first-use
    state carrier.
  src/coga/resources/templates/coga/recurring/trim-log/operations.md: Document reviewed publication of
    the two-file adoption without the obsolete source-repo attribute exception.
  tests/fixtures/seeded-repo/coga/recurring/trim-log/operations.md: Align the seeded runbook with the
    package owner and remove five-file staging instructions.
  tests/test_packaging.py: Remove the adopted attribute exception; verify selection/package fields and
    allow validated first-use trim-log state while rejecting definition copies.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 68bba9ef085a62965b2fd0f4c8648a812699ec6f
  base: 8e536f3d389b9626c2638a57f15f8d7034f00fc8
  detail: 'Direct Codex review completed on the rebased six-path diff with no must-fix findings. Reviewed
    two-file adoption, package ownership and first-use state validation, installer refusal/idempotence
    and installed-wheel regression coverage, clean committed state publication, and adoption/recovery
    instructions. The implementer was also Codex; no independent review is claimed. This records completed
    code review, not merge approval: native Windows evidence and deployment upgrade remain outstanding.'
checks:
- command: env PYTHONPATH=/home/n/Code/codex/coga/src TERM=dumb /home/n/Code/codex/coga/.venv/bin/python
    -m pytest tests/test_packaging.py tests/test_trim_log.py tests/test_edge_distribution.py --basetemp=/tmp/coga-trim-log-peer-20261108-0lxewa0h/focused-tmp
  status: passed
  head: 68bba9ef085a62965b2fd0f4c8648a812699ec6f
  base: 8e536f3d389b9626c2638a57f15f8d7034f00fc8
  detail: 119 passed in 64.59s. Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic x86_64, Python 3.12.12.
    Ran on the rebased committed head.
- command: env PYTHONPATH=/home/n/Code/codex/coga/src TERM=dumb /home/n/Code/codex/coga/.venv/bin/python
    -m pytest --basetemp=/tmp/coga-trim-log-peer-20261108-0lxewa0h/full-tmp
  status: passed
  head: 68bba9ef085a62965b2fd0f4c8648a812699ec6f
  base: 8e536f3d389b9626c2638a57f15f8d7034f00fc8
  detail: 4655 passed, 11 skipped in 734.34s (12m14s). Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic
    x86_64, Python 3.12.12. Ran on the rebased committed head; no implementation files changed during
    or after the run. Native Windows and the Python 3.11 floor were not exercised by this Linux run.
- command: env PIP_CACHE_DIR=/tmp/coga-trim-log-peer-20261108-0lxewa0h/pip-cache /home/n/Code/codex/coga/.venv/bin/python
    -m pip wheel --no-build-isolation --no-deps --wheel-dir /tmp/coga-trim-log-peer-20261108-0lxewa0h/wheel
    /tmp/coga-trim-log-peer-20261108-0lxewa0h/source
  status: passed
  head: 68bba9ef085a62965b2fd0f4c8648a812699ec6f
  base: 8e536f3d389b9626c2638a57f15f8d7034f00fc8
  detail: Pristine scratch clone at the reviewed head; clean checkout verified before building. coga-0.4.1-py3-none-any.whl
    SHA-256 86e4c95bbef0225374621565d79efcfca8a239b795abb097195d9dd223c44105, byte-identical to the implementation
    candidate. Installed non-editably into isolated wheel-env; deployment unchanged.
- command: env -u PYTHONPATH /tmp/coga-trim-log-peer-20261108-0lxewa0h/wheel-env/bin/python -B /tmp/coga-trim-log-peer-20261108-0lxewa0h/verify-installed.py
  status: passed
  head: 68bba9ef085a62965b2fd0f4c8648a812699ec6f
  base: 8e536f3d389b9626c2638a57f15f8d7034f00fc8
  detail: Python 3.12.12. Verified launcher shebang interpreter and non-editable site-packages import,
    implementation bytes and five package resources, executable script and packaged workflow, Monday 04:00
    repo schedule with run_when_inactive=true, retention 30, log merge unset, retire-worklist merge union,
    PST/PDT and no TZ override. Script also invoked the installed module with exact --install; reported
    already installed/no changes. All 368 files under the Coga root preserved, including shared/local
    config, audit log, phone-home state and periods; no trim-log parent or period created. Hashes and
    command output retained in installed-verification.json.
- command: env PYTHONPATH=/home/n/Code/codex/coga/src TERM=dumb /home/n/Code/codex/coga/.venv/bin/python
    -m coga.cli validate --task commit-journal/activate-trim-log-in-this-repo-after-retention-mer --json
  status: passed
  head: 68bba9ef085a62965b2fd0f4c8648a812699ec6f
  base: 8e536f3d389b9626c2638a57f15f8d7034f00fc8
  detail: 1 valid task; no issues or fixes. Python 3.12.12 on Pop!_OS 24.04 LTS.
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/codex/coga/src TERM=dumb /home/n/Code/codex/coga/.venv/bin/python
    -m coga.cli validate --json
  status: passed
  head: 68bba9ef085a62965b2fd0f4c8648a812699ec6f
  base: 8e536f3d389b9626c2638a57f15f8d7034f00fc8
  detail: '5 valid tasks; no issues or fixes. Python 3.12.12 on Pop!_OS 24.04 LTS. Working directory:
    /home/n/Code/codex/coga/tests/fixtures/seeded-repo/coga.'
- command: env PYTHONPATH=/home/n/Code/codex/coga/src TERM=dumb /home/n/Code/codex/coga/.venv/bin/python
    -m coga.cli recurring list
  status: passed
  head: 68bba9ef085a62965b2fd0f4c8648a812699ec6f
  base: 8e536f3d389b9626c2638a57f15f8d7034f00fc8
  detail: Read-only discovery resolves bundled trim-log, 0 4 * * 1, due and not created. No recurring
    sweep executed.
- command: git diff --check origin/main...HEAD
  status: passed
  head: 68bba9ef085a62965b2fd0f4c8648a812699ec6f
  base: 8e536f3d389b9626c2638a57f15f8d7034f00fc8
  detail: Six-path committed diff has no whitespace errors.
- command: Native Windows full suite at the reviewed head via scripts/clean-install/aws-windows.sh
  status: not-run
  detail: Not run. Saved harness lifecycle records show completed instances terminated; the other records
    have no instance. No live cloud query or new allocation performed. Required before merge under coga-dev/testing;
    Linux evidence and older unrelated Windows receipts do not replace it.
```

## Superseded designs

### 2026-11-08 — Five live artifacts and manual-only adoption

Superseded by: the owner-approved package selection and managed-branch procedure.
Reason: the package cutover removed live definitions and staging, and current
publication guards keep committed feature-branch recurring files from control.
The owner permits deployment-wheel replacement after this launch but before
merge or scheduler resumption and controls both current users.

#### Description

Activate audit retention in this repository after the compatible implementation
from PR #1129 reaches current main; that PR closes
`v1/39-trim-the-audit-log`, while this ticket owns the operational
rollout and its cleanup. After owner review of the rollout plan, quiesce and
upgrade every participating writer, run the documented interpreter-resolved
`python -m coga_edge.trim_log --install`, review and publish its five repo
artifacts, and remove the staging copy and temporary packaging exception
through a reviewed cleanup PR. Done means the compatible writers can resume,
the intended weekly job is discoverable on control with existing retention
settings preserved, the effective log merge attribute is unset, all five live
artifacts match their packaged copies, and the cleanup has merged with the
required checks passing. Do not trim the live log manually or force a
production maintenance run to demonstrate activation.

##### Acceptance criteria

- [ ] Fresh `origin/main` contains PR #1129's merged implementation, verified
  by ancestry and the installed sources/resources, not the old branch name or
  package version alone. The owner has approved the writer inventory,
  maintenance window, manual checkout procedure, reviewed wheel provenance,
  publication order, recovery and resumption at `review-design`.
- [ ] Every participating writer is stopped before replacement and upgraded
  before any enabling files are installed. Evidence names each checkout,
  launcher/interpreter, old/new source revision and wheel SHA-256, stopped
  session/worker or scheduler, and restart disposition. Unknown writers remain
  an owner prerequisite; excluded installations stay disabled. Long-running
  processes restart under the verified installation before resumption.
- [ ] On fresh control, the documented resolved-interpreter installer changes
  only the five listed artifacts. A second invocation with the same wheel,
  before editorial changes, is a no-op. Shared/local configuration, including
  an explicit retention `0`, unrelated attributes, parked jobs, local forks,
  phone-home state and existing period state are preserved. Refusals are
  resolved with the owner rather than overwritten.
- [ ] Activation and cleanup reach control together in one reviewed PR merge:
  all five live/package pairs exist and match, `ticket.py` is executable,
  `rollout/trim-log/` is gone, and the `coga/.gitattributes` divergence exception
  and staging-only test/link fallbacks are gone. No earlier Coga sweep publishes
  the branch's recurring files. The runbook and seeded fixture describe the
  adopted layout, with no remaining operative staging instructions.
- [ ] Fresh control reports `coga/log.md: merge: unset` from
  `git check-attr merge -- coga/log.md`; the retire-worklist attribute remains
  unchanged. Read-only discovery finds `trim-log`, schedule `0 4 * * 1`,
  `scope: repo`, `run_when_inactive: true`, and workflow `trim-log/run`.
  Effective retention equals the recorded pre-adoption value (currently the
  implicit 30-day default); configuration bytes are unchanged.
- [ ] Packaging, installed-wheel adoption, scoped validation and the full
  workflow-required suite pass on the final reviewed tree, with exact commands,
  interpreter/platform, counts and head/base revisions recorded. Required PR
  checks pass; unavailable platform evidence is disclosed, not inferred from
  another interpreter. The merged revision is rechecked before resumption.
- [ ] The owner has the merged PR/revision, wheel receipts, verification and
  compatible recovery instructions, and records which writers/schedulers
  resumed or remain stopped. No live log/cursor rewrite, forced period,
  production trim or phone-home delivery is used as activation proof.

##### Proposed shape

**Publication decision: one adoption-and-cleanup PR, using manual code steps.**
Do not publish installer output separately. A normal launched handoff on the
feature branch would sweep committed recurring files before the cleanup PR;
committing those files alone does not solve the problem. At `review-design`,
approve running `implement` and `peer-review` as manual/API sessions under
`coga/checkouts/manual`, outside a launch/megalaunch supervisor. Each session
starts and ends on current clean control and bumps only from control. Do not
change the frozen workflow or disable publication in config. If a future
runtime notice says launch prepared the branch, resolve that mismatch before
creating adoption files; do not override launch's return protocol mid-session.

1. **Approve and establish the maintenance window.** Recheck PR #1129 and
   control, refresh the blackboard inventory, and obtain the owner's answers
   below. Stop recurring launchers, ordinary launches, megalaunch/chat sessions,
   script workers and other publishers in every participating checkout. Keep
   schedulers, including autoclose, stopped through final verification; task
   status and this sandbox's process list do not establish quiescence. Upgrade
   each participating installation using its environment manager and the
   interpreter-resolution procedure. Retain old artifact/source evidence and
   record the reviewed compatible wheel hash and revision. The deployment
   controller must use a non-editable wheel, with no source-path override, so
   switching the repository branch cannot change its loaded implementation.
   Only freshly started, verified deployment/review controllers may perform
   the necessary workflow publications during this window, from clean control.
2. **Capture installer output on control without publishing it.** Following
   the manual checkout procedure, create/record the implementation branch and
   strictly publish that ticket linkage while still on clean `main`, before
   installing anything. Snapshot the five targets' prior existence, bytes and
   modes plus configuration and phone-home/period state. Run
   `"$COGA_PY" -m coga_edge.trim_log --install`, inspect the exact allowlist diff,
   effective attribute and preservation evidence, then repeat for idempotence.
   Save and byte/mode-verify the generated files and preimages outside both
   Coga roots. Restore only this operation's exact unpublished target changes
   to their preimages, removing only verified newly created targets; do not
   restore a whole tree or touch the log. Require clean current control again.
   Run no sweeping Coga command while these files are installed on control.
   This capture is preparation for the PR, not a published adoption.
3. **Build the combined branch.** Switch to the recorded feature branch,
   reapply the captured five artifacts, and perform the cleanup below. Stage
   exact paths and commit the entire bundle together; never include this task
   or `coga/log.md`. Run the required tests, freshen against main, verify all
   twins again and push. While this branch is checked out, use Git, tests and
   read-only inspection only: no Coga lifecycle/publication commands, launch,
   recurring sweep, or supervisor teardown. Preserve work and return to clean
   current `main` by the manual procedure before writing the blackboard and
   bumping. Keep controller notes outside swept roots until that return.
4. **Review and publish together.** The independent `peer-review` session
   follows the same manual isolation and return order, including any fixes,
   final rebase and tests. `open-pr` runs from control as usual, with the
   reviewed branch recorded on the ticket. Before every state handoff, verify
   that control still has its pre-adoption files and no activation dirt.
   Obtain owner review and merge the complete PR as one control update. This
   lands the new attribute with removal of its exception, and the live runbook
   with its packaged edit. Do not split these across a state publication and
   a later code merge. If control changes materially, preserve the bundle,
   reconcile and renew review/check evidence rather than overwrite it.
5. **Verify, then resume.** Refresh all participating checkouts to the reviewed
   compatible revision without discarding unique work. If repeating the
   installer after the runbook edit, first install the wheel built from that
   matching reviewed tree; an older installed resource will correctly refuse
   the new runbook. Record any replacement wheel's hash/revision per writer.
   Verify the published five pairs, attributes, discovery, retention and
   checks below. Restart only verified upgraded writers, then release the
   approved schedulers and record resumption. The first ordinary sweep may
   service the latest past Monday immediately: approval includes that normal
   behavior, not a promise to wait until the next Monday. Do not fabricate
   ledger state or force a run. Complete the owner-held final step only after
   merged-tree verification and the resumption record are available.

The cleanup edits are bounded:

- Delete the five staged files under `rollout/trim-log/` after their live
  replacements are in the same branch diff.
- In `tests/test_packaging.py`, remove only the `coga/.gitattributes` entry
  from `INTENTIONALLY_DIVERGENT_TWINS`, remove the trim-log staging fallback
  from `_context_link_problems`, and replace
  `test_staged_trim_log_rollout_matches_packaged_files` with an explicit
  five-artifact live/package existence and identity check. Keep generic twin,
  navigation and installed-wheel coverage. Explicit existence matters because
  generic twin discovery skips a missing non-context live counterpart.
- Replace the obsolete staging paragraph in the new live
  `coga/recurring/trim-log/operations.md` and its packaged twin. Keep the
  generic adoption/refusal/recovery instructions; describe the completed repo
  handoff without directing future operators to staging files. Apply the same
  editorial update to
  `tests/fixtures/seeded-repo/coga/recurring/trim-log/operations.md`.
- Search current code, runbooks, contexts and fixtures for remaining operative
  staging references, excluding `docs/archive/**`. Update affected canonical
  and packaged twins together. Historical notes in other task blackboards
  are evidence, not instructions to rewrite for this rollout.

##### Verification and recovery

During implementation, run focused
`python -m pytest tests/test_packaging.py tests/test_trim_log.py tests/test_edge_distribution.py`,
then the workflow-required `python -m pytest` with the checkout's test
interpreter and absolute checkout `PYTHONPATH` where needed. Existing fixture
tests already exercise installed adoption, opt-out `0`, refusal and recovery;
production execution adds no required evidence. Check wheel packaging from a
pristine scratch clone as required by `coga-dev/packaging`; do not use that
test checkout as another production writer. Record final source and artifact
hashes, not just the distribution version.

Run `git diff --check`, scoped
`coga validate --task commit-journal/activate-trim-log-in-this-repo-after-retention-mer --json`,
and fixture validation from `tests/fixtures/seeded-repo/coga` with
`SLACK_WEBHOOK_URL` unset. Use read-only `coga recurring list` and
`src/coga/recurring.py`, `Template.load`/`list_templates`, for template fields
and discoverability; there need not be a materialized period yet. Record the
actual scheduler timezone. Load configuration read-only through
`src/coga/config.py`, `load_config`, to compare effective retention and preserve
the original config bytes. Capture individual byte comparisons for all five
pairs, script mode, effective Git attribute, PR merge OID and check results.
Repeat the artifact/attribute/discovery checks on fresh merged control before
resuming; do not re-run the full suite solely because the PR merged unless
the tested tree changed.

Before publication, a refusal or interrupted installer capture leaves writers
stopped. Preserve generated files and preimages, inspect any partial writes,
and restore only verified operation-owned edits or seek owner resolution;
the install loop is not a crash-atomic five-file transaction. Abort/defer the
unmerged branch while retaining its work. After publication, stop affected
writers again and use a reviewed forward repair or compatible wheel/repo pair.
Do not restore the old union attribute or downgrade to a pre-retention writer
as a shortcut, and never roll back audit history, cursor identity/counters or
lifecycle state. Retained trim receipts and native Git conflicts use the
runbook's recovery sections; do not delete receipts or replay transitions.

##### Out of scope

Retention-policy/algorithm changes, core installer/publication redesign,
configuration edits, other repositories, migration of unreviewed forks,
cleanup of unrelated clones/tasks, changing the CI cadence, manual log/cursor
rewrites and production maintenance/delivery tests. This design step writes
only the ticket; it does not install a wheel, stop a writer, enable files,
create a branch, or open a PR.

#### Context

##### Rollout plan and prerequisite

[PR #1129](https://github.com/FastJVM/coga/pull/1129) merged at
2026-10-28T22:57:03Z as `42d1b30a47e30bb642f9e610d950681acdacd595`.
That commit is an ancestor of design-time `origin/main`
`1f67e8ad65e300b95313f5be1561b1b3641dd950`; the remote feature branch has been
deleted. Inspect current control for the references below and recheck ancestry
and content before adoption. The source ticket's lifecycle status is separate
from merge evidence; this ticket does not close it.

The blackboard records a partial local inventory, not authorization or proof
of quiescence. The owner resolves external visibility and maintenance choices
at `review-design`; unavailable answers do not prevent this planning step.
Implementation cannot start the rollout with those answers outstanding.
Read `coga/checkouts/manual` (`docs/contexts/coga/checkouts/manual/SKILL.md`),
"Procedure" and "Publish pre-branch ticket edits", for the manual code-step
handoffs selected above. This topic is cited rather than attached.

##### Runbook and installer

Required read: `coga/recurring/trim-log/operations.md`, "Adoption after the
compatible wheel upgrade" and recovery sections; before adoption it lives at
`rollout/trim-log/coga/recurring/trim-log/operations.md`. Resolve `COGA_PY` using
`docs/contexts/coga/edge-code/edge-code-upgrades.md`, `migration:interpreter`,
preserving the launcher's interpreter environment. On fresh control, run
`"$COGA_PY" -m coga_edge.trim_log --install`; review these five possible edits:

- `coga/recurring/trim-log/ticket.md`
- `coga/recurring/trim-log/ticket.py`
- `coga/recurring/trim-log/operations.md`
- `coga/workflows/trim-log/run.md`
- `coga/.gitattributes`

`src/coga_edge/trim_log.py`, `install` and `_attribute_plan`, own the bounded
installer. `main` routes exact `--install` directly to `install`, bypassing
`run_reported` and the maintenance/bump path. `install` reads the four resource
files with `src/coga/paths.py`, `packaged_template_path`, checks all planned
targets and calls `_attribute_plan` before writing; `_attribute_plan` checks
the effective proposed rule with a temporary Git index. Thus the running
wheel's resources, not an arbitrary source checkout, define idempotence.
`src/coga_edge/trim_log.py`, `_phone_compatible`, checks installed/frozen
phone-home shims during maintenance, not installation: a successful installer
does not prove that a custom phone-home fork is ready.

##### Publication, cleanup and proof

Coordinate adoption with removal of `rollout/trim-log/` and the
`coga/.gitattributes` exception in `tests/test_packaging.py`,
`INTENTIONALLY_DIVERGENT_TWINS`: installation makes that exception invalid
immediately, so publishing adoption first would break packaging checks.
Design must resolve this ordering before owner approval. Remove obsolete
staging assertions/fallbacks while retaining live/package coverage, and update
the runbook's staging paragraph and remaining staging references with their
packaged twins under `src/coga/resources/templates/coga/`.

Verify installer idempotence before editorial runbook cleanup, or upgrade to
the matching reviewed wheel before repeating it: `trim_log.install` compares
against its installed package, not this source tree. Verify the five published
twins, `git check-attr merge -- coga/log.md` reports `unset`, and the Monday
04:00 local-time schedule and preserved retention setting are discoverable.
Record writer/resumption evidence, published revisions, packaging checks,
scoped Coga validation and workflow-required tests; production trimming is
not required.

`coga-dev/packaging` (`docs/contexts/coga-dev/packaging/SKILL.md`) is cited
rather than attached: read "Canonical copies and twins". Its mapping and
exception rules are enforced by `tests/test_packaging.py`,
`_discover_live_packaged_twins` and
`test_intentional_divergences_stay_real_and_explained`.
The former only adds existing live counterparts; the latter rejects an
exception as soon as its live bytes equal the package. This is why the bundle
needs both explicit live-file coverage and one publication boundary.
`coga/state-publication` (`docs/contexts/coga/state-publication/SKILL.md`) is
cited rather than attached: read "When Coga publishes", "Control versus
feature checkouts" and "Strict publication on demand". Dirty Coga files and
eligible committed recurring state can publish ahead of a PR; a feature
branch alone does not prevent activation.

`coga/recurring/scheduling`
(`docs/contexts/coga/recurring/scheduling/SKILL.md`) is cited rather than
attached: read "Periods and the serviced-period ledger" for retroactive first
firing. `src/coga/commands/recurring.py`, `list_recurring`, calls
`src/coga/recurring.py`, `list_templates`, for a read-only view; it does not
call the creating/launching sweep. `src/coga/config.py`, `load_config`, uses
`_parse_log` to supply 30 when shared `[log]` is absent and preserves `0`.

`coga-dev/testing` (`docs/contexts/coga-dev/testing/SKILL.md`) is cited rather
than attached: read "Which code you are actually testing" and "CI posture and
receipts". The documented Test workflow is paused; local workflow checks
remain required, and this rollout does not authorize re-enabling CI. Recheck
actual PR requirements at publication. `tests/test_trim_log.py`,
`test_install_idempotence_and_exact_allowlist` and
`test_install_validates_all_files_before_writing`, cover the installer plan.
`tests/test_edge_distribution.py`,
`test_installed_trim_log_adoption_and_headless_period`, tests installed
resources and opt-out preservation in isolated fixtures, and
`test_documented_trim_adoption_uses_resolved_interpreter` exercises the
documented command. Keep these relationships intact during cleanup.

#### Implementation entry check — 2026-11-03

Owner resolved both open asks this session (see `## Blockers`): sole
participating writer is `~/.local/bin/coga`; every other clone/scheduler is
excluded until upgraded; the dirty Retro checkout is abandoned and untouched.

Implement still cannot start in this session:

- This megalaunch pick runs in `/home/n/Code/coga` on chat branch
  `coga/chat-0b453101cbae` (0 ahead / 5 behind `origin/main`), not clean
  `main`. Dirty files (`coga/log.md`, this ticket,
  `v1/refresh-main-before-megalaunch-builds-its-queue`) are already on
  `origin/main`, but the chat owns this checkout. `coga/checkouts/manual`'s
  start check forbids switching an occupied checkout.
- `~/.local/bin/coga` is still 0.4.1, an editable install of this checkout,
  and the live megalaunch supervisor runs from it. The rollout needs that
  writer stopped before it is replaced with the reviewed non-editable wheel.
  This session can't do that from inside the queue.

Next: after this megalaunch and chat end, start from a clean `main` with no
supervisor running. Build the wheel from current `origin/main` and record its
revision and SHA-256. `uv tool install` it in place of the editable install,
then verify `coga_edge.trim_log` imports from site-packages. Then resume
implement manually per the ticket's Proposed shape, steps 2–5. Nothing was
installed, branched or changed in this session.


#### Implementation prerequisite check

2026-10-29 PDT / 2026-10-30 UTC — Codex stopped at rollout prerequisites.
The owner advanced `review-design` to `implement` in
`67a692249d216ca43b1a04806f00703a6eeb4b8d`; that commit changes only `step:`.
The advancement is recorded, but supplies no answers to the writer inventory,
maintenance window, wheel provenance or resumption questions, and no resolution
of the evaluator's post-merge ownership finding. Do not infer stopped processes
or an approved deployment artifact from the workflow transition.

Entry was clean `main`; `git fetch origin main` and
`git merge --ff-only origin/main` confirmed current control at
`edd2b1798b580a6f6954a228a6f2178c03c6262f`. No feature branch or PR is recorded
for this ticket. The prompt identifies this session as a megalaunch queue step;
no checkout preparation or return witness was supplied. The selected rollout
requires manual/API code sessions outside launch/megalaunch, so this session
cannot perform the adoption branch work under that procedure.

Read-only recheck on that revision:

- GitHub still reports PR #1129 merged as
  `42d1b30a47e30bb642f9e610d950681acdacd595`; `git merge-base --is-ancestor
  42d1b30a47e30bb642f9e610d950681acdacd595 origin/main` exited 0.
- Resolving `/home/n/.local/bin/coga` by its direct shebang yields
  `/home/n/.local/share/uv/tools/coga/bin/python` (Python 3.12.12, Linux
  x86_64). It still imports editable
  `/home/n/Code/coga/src/coga_edge/trim_log.py`, SHA-256
  `d487c64de17f78519a412031bcd31cd538f2d33e4007772c7dc1be97626c13e9`.
  This is source evidence, not the required non-editable wheel receipt or
  proof of what an already-running supervisor loaded.
- All five staged artifacts byte-match that interpreter's packaged resources.
  The four live trim-log files are absent; `list_templates` does not discover
  `trim-log`. `git check-attr merge -- coga/log.md coga/retires.md` still
  reports `union` for both; `load_config` reports retention 30.
- The local writer inventory above remains partial. No host-wide quiescence,
  installation replacement, scheduler timezone, or restart disposition is
  established by this check. The deployment controller is still editable.

Required owner handoff: record each participating/excluded writer and its
stop/restart authority, the maintenance window and scheduler timezone, and
the reviewed wheel revision/SHA-256 for each environment. Resolve the evaluator
finding with either a linked follow-up owning merged-tree verification and
resumption or an explicit exception retaining them here, including how
`open-pr` handles it and holding autoclose until the disposition is recorded
and the owner completes the gate. Resume implementation manually outside
launch/megalaunch with a freshly verified non-editable controller. Preserve
the single adoption-and-cleanup PR boundary, including any review fixes.

Checks: scoped `coga validate --task
commit-journal/activate-trim-log-in-this-repo-after-retention-mer --json`
passed (one valid task, no issues or fixes); `git diff --check` passed.
Byte comparisons confirmed unchanged frontmatter/body and prior blackboard,
one fence, and unchanged shared/local configuration hashes. Only this ticket
has unstaged edits; there are no staged or untracked files. A final
`git fetch origin main` found HEAD and `origin/main` still at the revision
above, with no intervening changes to reconcile.

Only this prerequisite note was authored. No branch, installer run, wheel
replacement, writer stop/restart, activation files, code changes, production
trim or delivery was performed. Configuration, the five adoption targets and
staging files remain unchanged. Implementation tests and PR preparation are
not claimed: rollout has not started. The queue handoff is `coga block`,
keeping step 4 until the concrete missing inputs are recorded.

#### Design handoff

2026-10-28 local / 2026-10-29 UTC — Codex design investigation. No branch,
code, installation, live activation or PR created. The spec selects one merged
adoption/cleanup bundle and manual code-step returns to control so no feature
handoff sweeps recurring files early. Owner approval is still pending.

Evidence at `1f67e8ad65e300b95313f5be1561b1b3641dd950`:

- Started clean on `main`; fetched and fast-forward checked `origin/main`.
  GitHub and ancestry confirm PR #1129 merged as
  `42d1b30a47e30bb642f9e610d950681acdacd595`. Its former branch is absent
  remotely. `v1/39-trim-the-audit-log` still records `in_progress`, step 7
  (`review`); no lifecycle correction performed for that other task.
- All five staged files byte-match the package. Live trim-log template,
  workflow, parked template and period are absent. The effective live log
  merge attribute is `union`. Shared `[log]` is absent; `load_config` returns
  retention 30. No config edit is needed.
- Live phone-home `ticket.py` is the stock packaged shim; no `_phone-home`
  parent or frozen phone-home period script was found in this checkout.
  State was not changed. Re-inventory at the maintenance window.

#### Writer inventory — partial, requires owner confirmation

| Checkout / installation | Observed revision and state | Rollout disposition |
| --- | --- | --- |
| `/home/n/Code/coga` | Clean `main`, `1f67e8ad65e300b95313f5be1561b1b3641dd950`; sole registered worktree | Proposed deployment control; recheck before use. |
| `/home/n/.local/bin/coga` | Direct shebang `/home/n/.local/share/uv/tools/coga/bin/python`; metadata 0.4.1, editable import from `/home/n/Code/coga/src` | Actual current CLI. A fresh import sees retention; this does not prove the existing supervisor has reloaded it. Replace with verified compatible non-editable wheel for deployment. |
| `/home/n/Code/coga/.venv/bin/python` | Metadata 0.4.1, editable primary source | Test environment; owner must confirm whether it also launches writers. |
| `/home/n/Code/codex/coga` and `.venv/bin/python` | Clean `main`, `638478541ff4bc0d7264f7a7d71897463875148d`; metadata 0.3.2, editable local source | Potential writer; no upgrade/resumption proof. |
| `/home/n/Code/claude/coga` and `.venv/bin/python` | Clean `main`, `9c4e73e6c1de8733aa176fdfbeae7aca0b72a58e`; metadata 0.4.1, editable local source | Potential writer; version is not compatibility proof. |
| `/home/n/Code/claude/.dream-retro-20261026T172253Z/dream-ops` | Linked to the Claude clone; branch `dream/ops-20261026T172253Z`, `2796d89b0e208ce10c35584489510fd846608d37`; dirty `coga/log.md` and `coga/tasks/recurring/dream/ticket.md` | Occupied/retained state: owner must identify the session and preserve/reconcile its writes before upgrade. Left untouched. |
| `/home/n/Code/coga/.coga/worktrees/build-week-readme.IcnXYp` | Independent same-origin clone; clean `agent/build-week-readme`, `8a0d6ece3a091dbda35b42997b8005eab5a27f10`; no checkout venv found | Potential old writer; confirm exclusion or upgrade, do not delete. |

The prompt identifies a live megalaunch session. `/proc` inspection exposed
only this sandbox's process namespace, not a trustworthy host-wide session or
worker inventory. No Coga references were found in readable user systemd units
or `/etc/cron.{d,hourly,daily}`; user crontab access was denied. Broader local
discovery also had unreadable unrelated paths. No absence claim covers cron,
other users, remote hosts, CI, agent-app schedulers or additional clones.
This environment reports PST/PDT with no `TZ` override; confirm the actual
sweeper's timezone independently. No reviewed wheel artifact/hash has been
selected or installed by this step.

#### Open Questions

For the owner at `review-design`, before any rollout work:

1. Which of the listed clones/interpreters still publish, who owns the dirty
   Retro checkout, and what other hosts, users, launchers, timers or CI can
   write this repository? Confirm each writer as upgraded-and-participating
   or explicitly stopped/excluded, including the current megalaunch.
2. Approve the single-PR publication order and manual/API `implement` and
   `peer-review` sessions, with no supervisor or sweeping command on the
   adoption branch. Name the deployment controller and a maintenance window
   that keeps schedulers stopped through review, merge and final checks.
3. Which reviewed wheel artifact(s)/source revisions and SHA-256 receipts
   will be used for every participating environment, and who can replace
   those installations and restart their sessions? Preserve a compatible
   recovery pair; the observed editable versions are not upgrade receipts.
4. Approve the resumption order and normal first-sweep catch-up, confirm the
   sweeper timezone, and identify who verifies the merged tree before
   releasing schedulers and final task completion. Existing retention,
   including any opt-out found during recheck, remains unchanged.

#### Verification

- `coga validate --task commit-journal/activate-trim-log-in-this-repo-after-retention-mer --json`
  passed: one valid task, no fixes or issues.
- `git diff --check` passed. A direct `compose_prompt_report` check under
  `/home/n/.local/share/uv/tools/coga/bin/python` confirmed all spec subsections
  and owner questions compose, the body has only Description/Context level-two
  sections, the sole blackboard fence is intact, and frontmatter and the ticket
  guide are byte-unchanged. Source citations use symbols rather than line numbers.
- Final `git fetch origin main` found no intervening commits: HEAD and
  `origin/main` are both `1f67e8ad65e300b95313f5be1561b1b3641dd950`; only this
  ticket has local edits. No code tests or production maintenance were run for
  this design-only change. Implementation checks above are requirements, not
  claimed results. Next workflow step: independent `evaluate-design`, then
  the owner resolves Open Questions at `review-design`.

#### Evaluator review

2026-10-28 local / 2026-10-29 UTC — Codex cold review completed against
`f586061627a159b037c3aa5b3cfb6ecb7e39cb0b` (clean `main` and freshly fetched
`origin/main`). Reviewed the Description and Context as the implementation
contract, then checked the blackboard evidence. **One workflow clarification
must be resolved before implementation.** The bounded installer and combined
adoption/cleanup PR are otherwise implementable. This is not owner approval.

##### Must fix before implementation

1. **P2 — Resolve ownership of the work that remains after merge.**
   Acceptance criteria and Proposed shape, step 5, leave merged-tree checks,
   writer resumption and its receipt on this ticket, with final completion
   after those actions. But the frozen `code/open-pr` step's skill,
   `coga/skills/code/open-pr/SKILL.md`, "Order of operations", item 2, and
   "Acceptance for this step", requires post-merge obligations to be filed
   as separate drafts before opening the PR. The owning contract is
   `docs/contexts/coga/workflows/SKILL.md`, "Obligations the merge does not
   discharge". The plan currently says `open-pr` runs "as usual" without
   reconciling this requirement.

   Holding autoclose through final verification protects the maintenance
   window, but does not by itself resolve that pre-PR handoff. It also needs
   a precise release boundary: `src/coga/autoclose.py`, `_candidate` and
   `_try_bump_one`, close a final-step active/in-progress ticket when its PR
   is merged without checking acceptance criteria or resumption evidence.
   Step 5 currently releases schedulers and then records resumption.

   At `review-design`, choose and record either a linked follow-up that owns
   the post-merge checks/resumption, or an explicit owner-approved exception
   retaining those obligations here. For the latter, specify how `open-pr`
   handles the exception and keep autoclose stopped until the resumption
   disposition is recorded and the owner completes the gate (writers still
   stopped may be recorded as such). This does not require splitting the
   adoption/cleanup PR or changing workflow code or configuration. Do not
   leave the mechanical PR-opening agent to infer the exception.

##### Optional recommendation

- Explicitly extend the manual-only rule to any pre-merge owner-review fixes
  or `code/address-pr-comments` assistance. The general prohibition on
  branch-side launch/teardown already covers them, but only `implement` and
  `peer-review` are named in the publication decision. The entry table in
  `docs/contexts/coga/checkouts/SKILL.md`, "Which checkout a step starts in",
  also puts a normal owner-held `review` assist on the feature branch;
  `coga/skills/code/address-pr-comments/SKILL.md` assumes that launched path.
  Naming this case prevents the ordinary assist workflow from defeating the
  single-publication boundary during later requested fixes.

##### Verified basis

- GitHub reports PR #1129 merged as
  `42d1b30a47e30bb642f9e610d950681acdacd595`; `git merge-base --is-ancestor`
  succeeds against fresh `origin/main`. Since the design's recorded base,
  only this ticket and the audit log changed. No rollout branch or PR exists
  in this ticket's Dev record.
- `src/coga_edge/trim_log.py`, `main`, `install` and `_attribute_plan`, match
  the stated allowlist, installed-resource comparison, preflight/refusal and
  temporary-index attribute check. Exact `--install` bypasses maintenance,
  reporting and bump. `_phone_compatible` runs during maintenance, so the
  inventory's phone-home review remains necessary. The plan correctly puts
  idempotence before the runbook edit and distinguishes refusal from a crash
  during the non-atomic five-file write loop.
- `src/coga/git.py`, `_candidates`, and `coga/state-publication` confirm the
  committed-recurring publication hazard. `src/coga/open_pr.py`, `open_pr`,
  inspects/pushes a recorded branch by name from control. The proposed manual
  returns therefore support the combined PR without publishing its files
  during ordinary implement/peer-review handoffs.
- All five staged files currently match both source-package and active
  interpreter resources. The four live trim-log files are absent; read-only
  `list_templates` does not discover the job. `Template.load` on staging
  reports `0 4 * * 1`, repo scope, `run_when_inactive: true`, and
  `trim-log/run`. `load_config` reports retention 30. Effective log and retire
  attributes are both still `union`. These are pre-adoption observations,
  not upgrade, quiescence or activation receipts; the active CLI still imports
  this checkout's editable sources.
- `tests/test_packaging.py`, `_discover_live_packaged_twins`,
  `test_intentional_divergences_stay_real_and_explained`,
  `_context_link_problems` and the staging test support the exact cleanup
  list. Searches outside archives found operative trim-log staging references
  in that test module and the staged, packaged and seeded-fixture runbooks,
  all covered by the plan. Installed-wheel adoption/refusal and documented
  interpreter tests exist in `tests/test_edge_distribution.py`; they were
  inspected, not executed in this design review.

##### Review checks and handoff

- `env PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python -m pytest tests/test_trim_log.py::test_install_idempotence_and_exact_allowlist tests/test_trim_log.py::test_install_validates_all_files_before_writing tests/test_autoclose.py::test_sweep_merged_bumps_final_step_with_merged_pr`
  — **7 passed**; Python 3.12.12, Linux x86_64. These use isolated fixtures;
  they are not the implementation's full-suite or platform receipts.
- Scoped `coga validate --task commit-journal/activate-trim-log-in-this-repo-after-retention-mer --json`
  passed: one valid task, no issues or fixes. `git diff --check` passed; a
  byte comparison with HEAD confirmed that frontmatter, body and all prior
  blackboard content are unchanged. Final fetch found HEAD and `origin/main`
  still at the reviewed revision; only this ticket has local edits.
- The existing Open Questions remain owner prerequisites, including the
  complete writer inventory, maintenance authority, wheel provenance and
  resumption order. This review does not resolve them or block the ticket:
  the next owner gate resolves the finding and those questions.
- Only this Evaluator review was authored. No ticket-body edit, branch, code,
  wheel installation, live installer/maintenance run or PR was produced.

---

## Blockers

- [x] [2026-10-29 21:58] [agent:claude] id=20261029T215814 Record the participating/excluded writer inventory, stop/restart authority and maintenance window (including current megalaunch, dirty Retro checkout and schedulers), scheduler timezone, and reviewed compatible wheel revision/SHA-256 per installation. Resolve the evaluator finding with a linked post-merge verification/resumption follow-up or an explicit exception explaining open-pr handling and keeping autoclose stopped through the recorded disposition and owner completion. Resume implement in a manual/API session outside launch/megalaunch with a freshly verified non-editable controller; the current CLI is editable and no stop/upgrade receipts are recorded.
  resolved: [2026-11-03 10:18] [human:nicktoper] Owner 2026-11-03: the only participating writer is the deployment install behind ~/.local/bin/coga, which must be replaced with the reviewed non-editable wheel (record revision + SHA-256) before activation. Excluded and kept from running coga until upgraded: ~/Code/codex/coga (0.3.2), ~/Code/claude/coga, ~/Code/coga/.venv (tests only), any cron/scheduled jobs, other machines or people. The dirty Retro checkout ~/Code/claude/.dream-retro-20261026T172253Z/dream-ops is abandoned and excluded: leave it untouched, not part of this rollout. Earlier settlements stand: PST/PDT scheduler timezone; post-merge exception (b), so merged-tree verification and resumption stay on this ticket, open-pr files no drafts for them, and autoclose stays off until the resumption record is written and the owner completes the final gate; implement may run under megalaunch if it uses only git/tests on the feature branch and returns to clean main before any coga command or bump; no maintenance window beyond holding autoclose.

- [x] [2026-11-02 22:08] [agent:claude] id=20261102T220849 Owner deferred rollout (2026-11-02). Settled: scheduler timezone PST/PDT; one reviewed non-editable wheel (record revision + SHA-256) for the single deployment installation; post-merge exception (b) — merged-tree verification and resumption stay on this ticket, open-pr files no drafts for them, autoclose stays off until the resumption record is written and the owner completes the final gate; megalaunch is acceptable for implement if the session uses only git/tests on the feature branch and returns to clean main before any coga command or bump; no separate maintenance window beyond holding autoclose. Still needed: the owner's list of live Coga writers for this repo (candidates: ~/Code/coga editable source behind ~/.local/bin/coga, ~/Code/codex/coga on 0.3.2, ~/Code/claude/coga, cron/scheduled jobs, other machines/people), each upgraded to the reviewed wheel or kept from running coga until upgraded; disposition of the dirty Retro checkout .dream-retro-20261026T172253Z/dream-ops.
  resolved: [2026-11-03 10:18] [human:nicktoper] Owner 2026-11-03: the only participating writer is the deployment install behind ~/.local/bin/coga, which must be replaced with the reviewed non-editable wheel (record revision + SHA-256) before activation. Excluded and kept from running coga until upgraded: ~/Code/codex/coga (0.3.2), ~/Code/claude/coga, ~/Code/coga/.venv (tests only), any cron/scheduled jobs, other machines or people. The dirty Retro checkout ~/Code/claude/.dream-retro-20261026T172253Z/dream-ops is abandoned and excluded: leave it untouched, not part of this rollout. Earlier settlements stand: PST/PDT scheduler timezone; post-merge exception (b), so merged-tree verification and resumption stay on this ticket, open-pr files no drafts for them, and autoclose stays off until the resumption record is written and the owner completes the final gate; implement may run under megalaunch if it uses only git/tests on the feature branch and returns to clean main before any coga command or bump; no maintenance window beyond holding autoclose.

- [x] [2026-11-03 10:20] [agent:claude] id=20261103T102001 Writer inventory resolved 2026-11-03. Implement now needs a session outside this megalaunch/chat: the checkout is occupied by chat branch coga/chat-0b453101cbae (not clean main), and the sole writer ~/.local/bin/coga is still an editable 0.4.1 install that this live supervisor runs from. After the queue ends, the owner (or a manual session) replaces it with a non-editable wheel built from current origin/main, records revision + SHA-256, and resumes implement from clean main.
  resolved: [2026-11-08 14:15] [human:nicktoper] Owner approved revised procedure on 2026-11-08: implement on the launch-prepared branch and let launch return the checkout. Use the current package-owned definitions and two-file installer (recurring/jobs.toml and .gitattributes), not the obsolete five-file live-copy rollout. Build and verify an isolated non-editable wheel for installer capture and tests. Keep /home/n/Code/coga, the separate editable deployment source, unchanged during this implementation; replace ~/.local/bin/coga after this launch exits and before PR merge or any scheduler resumption, recording source revision and wheel SHA-256. Commit the complete adoption and cleanup bundle before any Coga handoff; current publication guards keep clean committed recurring files on the branch. Existing writer exclusions, PST/PDT timezone, post-merge ownership exception, and autoclose hold through recorded resumption disposition and owner completion remain in force.


---

## Blocker reminders

- 20c3261f9049 last_reminded: 2026-10-30 11:14

- 7af0bbf2dd81 last_reminded: 2026-11-03 10:44
