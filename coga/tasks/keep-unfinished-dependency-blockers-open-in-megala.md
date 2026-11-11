---
title: Keep unfinished dependency blockers open in megalaunch
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
---

## Description

### Problem

Coga 0.4.1 can release a dependent ticket too early when it has more than one open dependency blocker. `_finished_blocker_dependency` selects the first named task that is done, but the dependency-drain publication calls `resolve_open_blockers`, which marks every open blocker resolved. If B depends on A and C, A is done, and C is still active, the bare megalaunch drain can clear both asks and activate B.

This behavior also clears unrelated human asks that happen to coexist with a satisfied dependency blocker.

### Reproduction

1. Create active tickets A, C, and dependent ticket B.
2. Run `coga block --task B --reason "Depends on A: need its result"`.
3. Run `coga block --task B --reason "Depends on C: need its result"`.
4. Mark A done while C remains active.
5. Run a bare `coga megalaunch` sweep.

Observed in a minimal reproduction: the drain selects A, then both blocker entries become resolved. The existing single-dependency drain test still passes, so the missing coverage is the multi-blocker case.

### Required behavior

- Resolve only open dependency blocker entries whose exact named task is done or was seen and then retired.
- Preserve every unsatisfied dependency blocker and every unrelated human blocker.
- Keep the dependent ticket blocked and do not launch it while any open blocker remains.
- When all remaining blockers are satisfied, publish their targeted resolutions and activation atomically before the launch claim, preserving current race and recovery guarantees.
- Preserve the manual `coga unblock` contract: an explicit human answer may continue to resolve all open asks in one transition.
- Preserve exact path-qualified task-reference matching and the rule that cancellation is not dependency completion.

### Implementation and documentation

Introduce targeted blocker-resolution behavior rather than reusing the all-open resolver in the dependency drain. Update the shipped `coga/lifecycle` and `coga/megalaunch` topics in the same change so multiple dependencies and mixed dependency/human blockers have one explicit contract.

### Acceptance criteria

- A regression test proves that with A done and C active, only the A blocker is resolved and B stays blocked.
- A regression test proves that two satisfied dependencies can be resolved and B can drain normally.
- A regression test proves that a satisfied dependency does not resolve an unrelated human ask.
- Existing single-dependency, activation-refusal, exact-reference, publication, and race tests remain green.
- Focused megalaunch tests, the full test suite, packaging checks, and `coga validate --json` pass.

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

branch: coga/keep-unfinished-dependency-blockers-open-in-mega-3a6dfd


## Implement progress

- Human approved targeted resolutions with partial progress kept blocked and the existing atomic activation/publication safeguards retained.
- `src/coga/megalaunch.py` + `_finished_blocker_dependencies` selects satisfied entries; `_publish_partial_dependency_resolution` publishes partial answers against exact ticket bytes; `_activate_for_launch` answers only selected records before its existing guarded publication.
- `src/coga/blackboard.py` + `resolve_blockers_text` targets full captured blocker records, preserving inert examples, superseded designs, legacy asks, and existing answers. Records rather than IDs are necessary because `_blocker_id` uses whole seconds and different asks can share an ID. ID generation is unchanged; broader ID-consumer implications remain an adjacent finding, with no existing follow-up found.
- Regression-first run: all four new multi-blocker cases failed on the original implementation (active/canceled/human asks cleared; two done dependencies answered with the wrong task name). First focused fixed run: 191 passed in 20.43s. Final verification and publication receipts are recorded below.
- Shipped lifecycle topic owns the multi-dependency/mixed-ask contract; megalaunch links it and owns exact publication and retry behavior. No fixture shape or workflow snapshot changed; runtime regressions use the existing megalaunch fixtures.
- Independent code review belongs to the next workflow step; none has run in implement.
- Final head pushed: `975a5b81d1191fa1da74bb1309118e0a40ee9f34`; base `d53c5566e3454ae6ecdb1809ce131279146cf0f0`. Includes the human-approved one-link navigation repair as a separate commit.
- Post-rebase focused/packaging run: 232 passed, 1 failed in 20.88s. Failure: `tests/test_packaging.py::test_context_navigation_has_no_broken_links`, because the unchanged local development branch-sweep topic links to removed anchor `#review-and-release-a-retained-local-draft` in the shipped branch-sweep topic. Both paths have zero diff from origin/main. Human approved removing the stale fragment so the link opens its owning topic; implemented in `975a5b81d`. The first full-suite run was interrupted before completion to restart verification on the final commit; it is not a full-suite receipt.
- Repo validation passed (107 OK, 10 warnings, no errors); seeded fixture validation passed (5 OK, no issues).
- Native Windows suite is required before merge for the new Git publication path under `coga-dev/testing`. Existing harness host no longer exists. Human explicitly deferred Windows verification to review; it remains required before merge. No host was provisioned. The harness requires approval outside windows-native tickets. AWS profile `coga-test` is configured; a read-only status attempt needed escalation to refresh SSO cache.

## Implement handoff

- Implemented and pushed both commits on the recorded branch. Fresh final fetch confirms the branch contains current `origin/main`; no implementation changes are uncommitted. The projected ticket remains outside the implementation commits.
- Final Linux receipts: full suite **4,719 passed, 33 skipped in 960.48s**; focused megalaunch/blackboard plus packaging **233 passed in 33.07s**. Repo validation: **107 OK, 10 warnings, no errors**. Seeded fixture validation: **5 OK, no issues**. Exact commands, tested head/base, platform, interpreter, and omission reasons are in PR preparation below.
- No PR opened. Independent review is the next workflow step. Actual implementer is **Codex**, despite the ticket's configured `agent: claude`; assess review independence using the actual identity, as the preparation contract requires.
- Human explicitly deferred the required native Windows full-suite receipt to review; obtain it before merge. No Windows resources were provisioned. Local tests used Python 3.12.12, so this step supplies no Python 3.11 floor receipt.
- Residual adjacent finding: timestamp-only blocker IDs can collide for asks appended within one second (`blackboard._blocker_id`). This implementation safely targets complete captured records. Other ID consumers and ID generation remain outside scope; no existing follow-up ticket was found. Preserve this finding for the later durable-knowledge/Retro handoff.

## Peer review

- Codex direct review completed on initial rebased head `bef10e1034e84530007d232dd1f380ec3b962276` / base `2107e39bdd0dbe419813944889d41968d4b690a7`, with no findings in the seven implementation paths. Actual implementer was Codex; this is self-review, not independent review inferred from configured roles.
- Inspected exact named refs, cancellation, asks naming multiple refs, captured records and duplicate IDs, inert/legacy/archived text, partial publication and refusal/uncertainty recovery, atomic activation, manual all-open unblock, owner scope, budgets, and fixed-point retries.
- Initial Linux review receipts on that head: full suite 4,719 passed / 33 skipped in 808.24s; focused/package checks 233 passed in 20.73s; repo validation 107 OK / 10 warnings / no errors; seeded validation 5 OK / no issues. Logs `/tmp/coga-dependency-peer-full-pytest.log`, `/tmp/coga-dependency-peer-focused-pytest.log`. These receipts are historical after the fixture repair below.
- Real PTY smoke: bare CLI in an isolated repo, A done / C active / B blocked on both plus a human region ask. Observed 0 launched, 0 drained, 1 skipped-unresolved-blocker. B stayed blocked; only A resolved; the summary retained C and the human ask. No picker/raw-terminal interaction code changed. Runner `/tmp/coga-dependency-terminal-smoke.py`. Supplemental 10,000 generated Markdown projections preserved blocker identity/order without exceptions.

### Native Windows finding and approved repair

- Full native run on the initial review head found `tests/test_checkouts.py::test_abrupt_launch_death_is_recovered_at_the_next_entry` failing. Isolated reproduction: 1 failed in 49.44s on the branch; 1 failed in 50.91s on unchanged main `2107e39bdd0dbe419813944889d41968d4b690a7`, using a separate clone and absolute baseline PYTHONPATH. The test file was identical on both. Evidence `/tmp/coga-dependency-windows-repro.log`, `/tmp/coga-dependency-windows-baseline.log`.
- The fresh child interpreter faked CLI discovery and its supervisor callback but lacked conftest's Windows resolver shim. Native command planning reported Claude missing and exited 2 before the simulated crash `os._exit(91)`. This is a baseline fixture defect, not a dependency-drain regression.
- Human approved including the child-resolver repair and rerunning suites. The fixture now supplies the fake resolver in that child, preserving Windows planning and crash-recovery coverage without skipping the test. The testing topic documents why child fixtures must install their own fakes. Local targeted regression passed (1 in 2.64s) before final rebase.
- Stopped the failing native run at 2026-11-11T05:11:29Z, verified zero Python/Git/uv processes, and retained interrupted-run evidence under `.coga/clean-install/dependency-review-20261110/first-suite/`. It is not a completed full-suite receipt.
- Main received routine state updates during the run. Preserved and verified the current ticket, audit log, and the newly created other task outside the repo; proved the latter two byte-identical to published main before clearing only those duplicates for rebase. Rebase completed without conflicts and restored the current handoff byte-for-byte. Only this ticket is dirty.
- Final candidate head `9310fb1781aa32adf48b5e6b71b15d91b653cbdb`, base `0ba56e5100d0302f0de4fdf74ebda9d30b391519`, pushed with `--force-with-lease`. Re-reviewed all nine diff paths; the original seven are byte-identical to the initial reviewed head. No further findings. Final focused/package/blackboard/megalaunch plus repaired-case run passed: 234 in 21.94s. Repaired native Windows case passed: 1 in 92.80s at this head; `/tmp/coga-dependency-windows-fixed.log`. Final Linux full suite passed: 4,719 passed / 33 skipped in 792.54s at this head (`/tmp/coga-dependency-peer-final-full-pytest.log`), same Pop!_OS 24.04 / Linux x86_64 / Python 3.12.12. Final repo validation: 108 OK / 11 warnings / no errors; one added warning is the empty-description draft that arrived on main. Seeded validation: 5 OK / no issues. Repeated the PTY smoke at 80x24 on this head, with the same correct partial-resolution result. Final native full suite restarted at 2026-11-11T05:17:12Z with verbose test names; its incomplete failed result is recorded below; original remote evidence moved to `C:\coga-clean-install\dependency-review-first\`.

### Additional native findings and pending repair approval

- Final native run at `9310fb1781aa32adf48b5e6b71b15d91b653cbdb` passed the repaired crash-recovery case but subsequently reported `tests/test_git.py::test_stage_b_first_deletion_and_carrier_publish_against_stage_a_control` failing at 36%. The full run later aborted as recorded below; it is not a green receipt. This test file has no branch diff. Isolated reproduction confirmed failure on the branch (1 failed in 469.86s) and on unchanged main `0ba56e5100d0302f0de4fdf74ebda9d30b391519` (1 failed in 402.76s). Logs `/tmp/coga-dependency-windows-cutover.log` and `/tmp/coga-dependency-windows-cutover-baseline.log`; helpers have matching `.ps1` names. The read-only control clone inherits system Git `core.autocrlf=true`: normalizing its legacy definition prefix from CRLF to LF reproduces the exact pinned expected SHA256 `4a6560da0ccd7a44cda17a0c6b63126352d24ca7a19e7f019e98db7c1a9d3f1d` (raw CRLF prefix is `d8c72ec8e7c546293462d89d9890a5f40e59c31e2e0a3b14aa6620f75838d8cf`). A fresh LF-only clone fixed two of the three common nested failures; a targeted run reported 1 failed / 2 passed in 3.58s, isolating one historical fixture write that omits `newline="\n"`. The baseline diagnostic also hit long fixture paths; this Windows host has LongPathsEnabled=0. Proposed repair keeps historical product imports and assertions pinned, sets LF in control clones, backports only that fixture write, and uses a short native temp root. Asked the attending human to approve this additional test-only scope. The later full-run outcome is recorded below. No further code edit or workflow transition has occurred.

- The continuing native run also reported both `test_final_package_edits_never_escape_a_mutating_cli_sweep` variants failing. Isolating the dirty-package variant with short `--basetemp=C:\pfg` passed (1 in 280.83s) without source/assertion changes; log `/tmp/coga-dependency-windows-package-probe.log`. The short-path execution plan addresses that nested fixture layout.
- Two `tests/test_launch.py::test_launch_agent_not_in_path` variants failed because the test globally forbids the substring `install`, while a legitimate Windows startup warning names `coga/testing/clean-install/macos-aws`. The actual missing-CLI remedy is correct. Isolated branch case: 1 failed in 1.95s; unchanged-main case: 1 failed in 3.13s, both at the same overbroad negative assertion. Logs `/tmp/coga-dependency-windows-launch-missing.log` and `/tmp/coga-dependency-windows-launch-missing-baseline.log`. A minimal test-only repair scopes the remedy assertions to the missing-CLI diagnostic, preserving the warning and product behavior. No source edit for this finding has been made.

- The native full run terminated early during pytest reporting: exit 3; 5 failed, 2,481 passed, 54 skipped in 13,463.43s (3:44:23). JUnit also records one internal error. The test body `test_windows_keys_resize_and_extended_keys` passed, but its global `shutil.get_terminal_size` lambda did not accept pytest's `fallback=` argument while reporting before fixture teardown. Reproduced exit 3 on Linux with `-vv` (`/tmp/coga-terminal-size-reporting-repro.log`) and unchanged-main Windows (body passed in 1.32s, then the same internal error; `/tmp/coga-dependency-windows-terminal-size-baseline.log`). Correct repair scopes that stdlib monkeypatch so it is restored before reporting; no picker behavior changes. Disk was healthy (about 27 GB free). Full incomplete artifacts are under `.coga/clean-install/dependency-review-20261110/suite/`.
- The completed package-cutover ticket `coga/tasks/v1/package-definitions/02-repo-cutover-to-package-owned-definitions.md` already records the historical CRLF and nested MAX_PATH failures with a before-merge verification obligation. The Windows interactive ticket `coga/tasks/v1/14-interactive-coga-launch-on-native-windows.md` is at owner review; its key-source equivalent is the reporting-mock case above. No work or workflow transition was performed on either ticket.
- Superseded the narrower pending permission question with one explicit batch approval: historical LF fixtures / short paths, precise missing-CLI diagnostic assertions, and the terminal-size mock lifetime. Approval was later received; the implemented batch is recorded below.
- Diagnostic continuation selects only nodes after the passed Windows-keys test using `/tmp/coga-dependency-windows-remainder.py`; it is explicitly not a full-suite receipt. Task `CogaDependencyRemainder`, remote evidence `C:\coga-clean-install\dependency-remainder\`, poll/download helper `/tmp/coga-dependency-windows-remainder-poll.py`. The first wrapper attempt omitted the repository root on sys.path and produced two collection errors, preserved under `remainder-collection-error/`; the wrapper now adds cwd before calling pytest. Restarted that diagnostic. Cleanup must wait for or stop both scheduled tasks, then remove both names.

### Approved portability batch and final rerun

- Human approved both the historical portability repair and the consolidated test-only batch. Commit `8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5`, base `46f3e7383a20e6d068577720c1684ebd40cd7a0d`, is pushed. Main drift since the previous receipt only changed unrelated ticket/audit state. Original product behavior and historical product imports/assertions remain unchanged.
- Control clones now explicitly disable autocrlf; only the pinned Stage A test's one fixture write is backported to LF. Missing-CLI remedy assertions inspect that diagnostic line, and the stdlib terminal-size mock is restored before pytest reporting. The testing topic owns the short native temp-root and shared-mock guidance.
- Direct review of the final eleven-path diff completed without product-code findings; Codex remains the actual implementer/reviewer, conservatively recorded as self-review. Required final verification is still running.
- Focused Linux/package/historical-control checks passed: 239 in 103.39s. The exact verbose terminal-size reproduction now passes (1 in 0.21s). Final Linux full suite passed: 4,719 passed / 33 skipped in 771.03s (12:51), same Linux/Python 3.12.12 environment; `/tmp/coga-dependency-peer-batch-full.log`. Repo validation passed with 108 OK / 12 warnings / no errors; seeded validation 5 OK / no issues. The final 80x24 PTY smoke also passed.
- The optional remainder diagnostic at the previous head was stopped at 2026-11-11T10:00:30Z while permission was pending. Its stdout contains 721 passes, 1 skip, no failures; it selected 2,212 nodes after deselecting the first 2,540. It is not a full-suite receipt. Artifacts, including the baseline terminal-size JUnit, are retained under `.coga/clean-install/dependency-review-20261110/remainder-suite/`.
- Both old scheduled tasks were removed and zero Python/Git/uv processes verified. All original three Defender exclusions were removed and absence verified at 2026-11-11T10:01:45Z. Initial cleanup used a nested PowerShell JSON array and removed nothing; corrected the manifest parsing and verified all three actual removals before proceeding. Teardown then failed because SSO expired; no cloud resources were destroyed. After approval and refreshed AWS access the same running host is being reused for final verification, with `C:\ct` as the short pytest temp root.

### Windows resources and cleanup obligation

- Human approved default provisioning and teardown, then separately approved temporary Defender exclusions. Run `dependency-review-20261110`, region/zone `us-east-1a`, default `t3.large` / 50 GB; instance `i-009374adc23a09e72`; AMI `ami-0b5f645abc199e666` (`Windows_Server-2025-English-Full-Base-2026.10.28`). Windows Server 2025 build 26100.33674, Python 3.11.18. Instance CPU credit mode is unlimited.
- Historical first-run exclusions were newly added and verified at 2026-11-11T04:12:30Z: `C:\Users\Administrator\coga-work`, `C:\Users\Administrator\AppData\Local\Temp\pytest-of-Administrator`, `C:\Program Files\Git`. The original manifest was `C:\coga-clean-install\dependency-review-owned-exclusions.json`; all three were removed and verified absent as recorded above.
- Final-run exclusions were applied and verified at 2026-11-11T16:21:52Z: checkout `C:\Users\Administrator\coga-work`, short pytest temp `C:\ct`, and `C:\Program Files\Git`. The final ownership manifest is `C:\coga-clean-install\dependency-final-owned-exclusions.json`; cleanup helper now reads that manifest and validates a flat three-string array. Remove and verify absence before final teardown. Old pytest fixtures were removed; about 28 GB free before rerun.
- Final native focused run started at 2026-11-11T16:22:48Z on the pushed final head, six cases with `--basetemp=C:\ct`; task `CogaDependencyReview`, evidence `C:\coga-clean-install\dependency-final-focused\`. Helpers `/tmp/coga-dependency-windows-final-focused-{schedule,poll}.py`; full-run helpers use `final-{schedule,poll}.py` and evidence `dependency-final`. All six focused cases passed (1138.01s / 18:58), with JUnit confirming 6 tests and zero errors/failures/skips; artifacts `final-focused-suite/`. Final full suite started at 2026-11-11T16:42:18Z on the same commit, `--basetemp=C:\ct`, source unchanged. Poll `/tmp/coga-dependency-windows-final-poll.py`; metadata records Python runtime UTF-8 mode 0. Current full receipt is pending.
- Remote suite evidence `C:\coga-clean-install\dependency-review\`; ignored local evidence `.coga/clean-install/dependency-review-20261110/`. Helpers `/tmp/coga-dependency-windows-schedule.py`, `/tmp/coga-dependency-windows-poll.py` (`artifacts` downloads), `/tmp/coga-dependency-remote-ps.py`, `/tmp/coga-dependency-windows-cleanup.ps1`. Before ending this session: collect artifacts, verify no test processes, remove exclusions, remove scheduled task, run harness teardown, then status must confirm terminated with no retained volume/security group/key pair.

## PR

```yaml
title: Keep unfinished dependency blockers open in megalaunch
author: codex
author_evidence: The implement handoff and retained usage identify Codex as the actual implementer, despite
  the configured claude agent. Codex also made the approved Windows fixture repair during this review session.
head: 8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5
base: 46f3e7383a20e6d068577720c1684ebd40cd7a0d
depth: deep
rationale: Changes dependency activation and Git publication/recovery decisions. Direct Codex self-review completed
  over the final diff; final Linux and native verification follow the human-approved baseline test-only repairs.
implementation: Resolve each satisfied dependency blocker with its own automatic answer using the captured
  blocker record. Publish partial answers under an exact ticket lease while retaining blocked; publish the
  remaining targeted resolutions and activation together before launch. Preserve all-open manual unblock behavior.
deviations: 'Human approved the stale-link repair, fresh-child Windows resolver fixture, and the subsequent
  portability batch: LF control clones and one explicit-LF historical fixture write, short native temp root,
  precise missing-CLI assertion, and restored terminal-size mock before reporting. Product behavior and historical
  assertions are preserved.'
limitations: Final native full-suite receipt remains required. Linux full/focused, packaging, validation, and
  terminal checks passed. Earlier native failures and interrupted diagnostic runs are historical evidence,
  not passing receipts.
files:
  docs/contexts/coga-dev/internals/branch-sweep/SKILL.md: Human-approved removal of a stale anchor found by
    the required packaging navigation check.
  src/coga/blackboard.py: Add targeted resolution of captured blocker records while preserving other asks,
    historical answers, and inert text.
  src/coga/megalaunch.py: Select satisfied dependency entries; publish partial resolutions while blocked and
    retain atomic activation when every remaining ask is satisfied.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md: Own the explicit multiple-dependency
    and mixed human/dependency blocker contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md: Document partial publication,
    exact snapshots, activation, recovery, and reconsideration in the drain.
  tests/test_blackboard.py: Cover exact-record targeting despite duplicate IDs and preservation of archived,
    fenced, legacy, and previously answered entries.
  tests/test_megalaunch.py: Cover unfinished/canceled/human blockers, two satisfied dependencies, same-run
    fixed points, multiple refs per ask, and partial publication success/refusal/uncertainty. Restore the shared
    terminal-size mock before pytest reporting.
  docs/contexts/coga-dev/testing/SKILL.md: Document fresh-child CLI fakes, explicit LF control fixtures, short
    native temp roots, and the lifetime of shared standard-library mocks.
  tests/test_checkouts.py: Repair the baseline native Windows abrupt-launch recovery test by installing the
    fake resolver in its generated child; retain actual Windows command planning and crash-recovery coverage.
  tests/test_git.py: Preserve pinned definition bytes in control clones and backport only the Stage A fixture
    newline; retain historical product imports and all assertions.
  tests/test_launch.py: Scope missing-CLI remedy assertions to its diagnostic, preserving unrelated legitimate
    startup warnings.
review:
  reviewer: codex
  kind: self
  status: pending
  head: 8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5
  base: 46f3e7383a20e6d068577720c1684ebd40cd7a0d
  detail: Direct Codex self-review completed over all eleven final paths; no product-code findings. The approved
    portability repairs preserve historical product code and assertions. Overall review waits for final full-suite
    receipts.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest -q
  status: passed
  detail: 4719 passed, 33 skipped in 792.54s (0:13:12). Pop!_OS 24.04 LTS, Linux x86_64 / 7.2.15-76070215-generic,
    Python 3.12.12. Log /tmp/coga-dependency-peer-final-full-pytest.log.
  head: 9310fb1781aa32adf48b5e6b71b15d91b653cbdb
  base: 0ba56e5100d0302f0de4fdf74ebda9d30b391519
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest tests/test_packaging.py tests/test_megalaunch.py
    tests/test_blackboard.py tests/test_checkouts.py::test_abrupt_launch_death_is_recovered_at_the_next_entry
    -q
  status: passed
  detail: 234 passed in 21.94s. Same Linux/Python environment. Log /tmp/coga-dependency-peer-final-focused-pytest.log.
  head: 9310fb1781aa32adf48b5e6b71b15d91b653cbdb
  base: 0ba56e5100d0302f0de4fdf74ebda9d30b391519
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --json
  status: passed
  detail: 108 OK, 11 warnings, no errors. The added warning is an empty-description draft introduced by main.
    Python 3.12.12 on Pop!_OS 24.04 LTS. Output /tmp/coga-dependency-peer-final-validate.json.
  head: 9310fb1781aa32adf48b5e6b71b15d91b653cbdb
  base: 0ba56e5100d0302f0de4fdf74ebda9d30b391519
- command: cd tests/fixtures/seeded-repo/coga && env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src
    /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json
  status: passed
  detail: 5 OK, no warnings or errors. Same Linux/Python environment. Output /tmp/coga-dependency-peer-final-seed-validate.json.
  head: 9310fb1781aa32adf48b5e6b71b15d91b653cbdb
  base: 0ba56e5100d0302f0de4fdf74ebda9d30b391519
- command: C:\Users\Administrator\coga-work\.venv\Scripts\python.exe -m pytest tests/test_checkouts.py::test_abrupt_launch_death_is_recovered_at_the_next_entry
    -q -x --tb=short --basetemp=C:\coga-clean-install\dependency-fixed-temp --junitxml=C:\coga-clean-install\dependency-review-fixed.xml
  status: passed
  detail: 1 passed in 92.80s. Windows Server 2025 Datacenter build 26100.33674, Python 3.11.18; cwd C:\Users\Administrator\coga-work,
    absolute PYTHONPATH to its src, TERM=dumb, no externally enabled Python UTF-8 mode. Log /tmp/coga-dependency-windows-fixed.log;
    JUnit retained under .coga/clean-install/dependency-review-20261110/reproductions/.
  head: 9310fb1781aa32adf48b5e6b71b15d91b653cbdb
  base: 0ba56e5100d0302f0de4fdf74ebda9d30b391519
- command: 'stty cols 80 rows 24

    PYTHONPATH=/home/n/Code/coga/src TERM=xterm-256color .venv/bin/python /tmp/coga-dependency-terminal-final.py
    run

    PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-dependency-terminal-final.py inspect'
  status: passed
  detail: 'Real 80x24 PTY: A done, C active, B blocked on A/C plus a human region ask. Observed zero launched/drained
    and one skipped-unresolved-blocker; inspected B remained blocked, only A resolved, C and human asks intact.
    Python 3.12.12 / Linux. No picker or raw-terminal interaction code changed.'
  head: 9310fb1781aa32adf48b5e6b71b15d91b653cbdb
  base: 0ba56e5100d0302f0de4fdf74ebda9d30b391519
- command: git diff --check
  status: passed
  detail: No whitespace errors in the implementation or current projected handoff.
  head: 9310fb1781aa32adf48b5e6b71b15d91b653cbdb
  base: 0ba56e5100d0302f0de4fdf74ebda9d30b391519
- command: C:\Users\Administrator\coga-work\.venv\Scripts\python.exe -m pytest -vv --tb=short --junitxml=C:\coga-clean-install\dependency-review\junit.xml
  status: failed
  detail: 'Incomplete full native run: exit 3; 5 failed, 2481 passed, 54 skipped in 13463.43s (3:44:23), plus
    one JUnit internal error. Windows Server 2025 Datacenter build 26100.33674, Python 3.11.18, absolute PYTHONPATH
    to the checkout src, TERM=dumb, no externally enabled Python UTF-8 mode. Historical LF/fixture failures,
    two long-path package variants, two overbroad missing-CLI assertions, then an invalid global terminal-size
    mock crashed pytest reporting after its test body passed. All nine new dependency-drain regression cases
    passed before the abort. Artifacts .coga/clean-install/dependency-review-20261110/suite/. This is not a
    completed Windows full-suite receipt; repair approval remains pending.'
  head: 9310fb1781aa32adf48b5e6b71b15d91b653cbdb
  base: 0ba56e5100d0302f0de4fdf74ebda9d30b391519
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest tests/test_packaging.py tests/test_megalaunch.py
    tests/test_blackboard.py tests/test_checkouts.py::test_abrupt_launch_death_is_recovered_at_the_next_entry
    tests/test_git.py::test_stage_b_first_deletion_and_carrier_publish_against_stage_a_control tests/test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep
    tests/test_launch.py::test_launch_agent_not_in_path -q
  status: passed
  detail: 239 passed in 103.39s. Linux x86_64, Pop!_OS 24.04, Python 3.12.12. Exact code/test/docs bytes match
    the committed tree; log /tmp/coga-dependency-peer-batch-focused.log.
  head: 8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5
  base: 46f3e7383a20e6d068577720c1684ebd40cd7a0d
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest tests/test_megalaunch.py::test_windows_keys_resize_and_extended_keys
    -vv --tb=short
  status: passed
  detail: 1 passed in 0.21s; the prior reporter-internal-error reproduction now exits 0. Same Linux environment.
  head: 8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5
  base: 46f3e7383a20e6d068577720c1684ebd40cd7a0d
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --json
  status: passed
  detail: 108 OK, 12 warnings, no errors. Python 3.12.12 on Pop!_OS 24.04; log /tmp/coga-dependency-peer-batch-validate.json.
    Warnings reflect live task state.
  head: 8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5
  base: 46f3e7383a20e6d068577720c1684ebd40cd7a0d
- command: cd tests/fixtures/seeded-repo/coga && env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src
    /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json
  status: passed
  detail: 5 OK, no warnings or errors. Same Linux environment; log /tmp/coga-dependency-peer-batch-seed-validate.json.
  head: 8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5
  base: 46f3e7383a20e6d068577720c1684ebd40cd7a0d
- command: 'stty cols 80 rows 24

    PYTHONPATH=/home/n/Code/coga/src TERM=xterm-256color .venv/bin/python /tmp/coga-dependency-terminal-batch.py
    run

    PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-dependency-terminal-batch.py inspect'
  status: passed
  detail: 'Real 80x24 PTY at final head: 0 launched, 0 drained, 1 skipped-unresolved-blocker. Verified B blocked;
    only A resolved; C and human ask remain open. Linux/Python 3.12.12.'
  head: 8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5
  base: 46f3e7383a20e6d068577720c1684ebd40cd7a0d
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest -q
  status: passed
  detail: 4719 passed, 33 skipped in 771.03s (0:12:51). Pop!_OS 24.04 LTS, Linux x86_64 / 7.2.15-76070215-generic,
    Python 3.12.12. Code/tests/docs match the committed tree throughout; log /tmp/coga-dependency-peer-batch-full.log.
  head: 8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5
  base: 46f3e7383a20e6d068577720c1684ebd40cd7a0d
- command: C:\Users\Administrator\coga-work\.venv\Scripts\python.exe -m pytest tests/test_git.py::test_stage_b_first_deletion_and_carrier_publish_against_stage_a_control
    tests/test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep tests/test_launch.py::test_launch_agent_not_in_path
    tests/test_megalaunch.py::test_windows_keys_resize_and_extended_keys -vv --tb=short --basetemp=C:\ct --junitxml=C:\coga-clean-install\dependency-final-focused\junit.xml
  status: passed
  detail: 6 passed in 1138.01s (0:18:58), JUnit confirms no errors/failures/skips. Native Windows Server 2025
    build 26100.33674, Python 3.11.18; absolute checkout src PYTHONPATH, TERM=dumb. Artifacts .coga/clean-install/dependency-review-20261110/final-focused-suite/.
  head: 8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5
  base: 46f3e7383a20e6d068577720c1684ebd40cd7a0d
- command: C:\Users\Administrator\coga-work\.venv\Scripts\python.exe -m pytest -vv --tb=short --basetemp=C:\ct
    --junitxml=C:\coga-clean-install\dependency-final\junit.xml
  status: pending
  detail: Started 2026-11-11T16:42:18Z on the same unchanged final commit; native Windows Server 2025 / Python
    3.11.18, runtime UTF-8 mode 0, absolute checkout src PYTHONPATH, TERM=dumb. Scheduled task CogaDependencyReview;
    final artifacts pending.
  head: 8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5
  base: 46f3e7383a20e6d068577720c1684ebd40cd7a0d
```
