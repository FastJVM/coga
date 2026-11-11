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
step: 3 (open-pr)
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

pr: https://github.com/FastJVM/coga/pull/1195
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

- Direct Codex code review **completed** over final integrated head `72d6062e7ec5281f2815b09d5c8c2c4ebfe97a37` / base `d26934ef4c30b800e0b61c7ab0351d9690883265`, with no must-fix product findings. Actual implementer and reviewer were Codex: this is **self-review**, not independence inferred from the configured claude agent or a fresh session.
- Reviewed all ten diff paths, exact task refs/cancellation, multiple refs in an ask, full captured blocker records and colliding IDs, fenced/legacy/archived text, partial publication and refusal/uncertainty recovery, atomic activation, all-open manual unblock, owner scope, budgets, and fixed-point retries. Re-reviewed integration with main's Git optional-lock environment and deferred done-marker/supervisor changes.
- Human-approved baseline Windows repairs: fresh-child fake CLI resolver in `test_checkouts`; LF control clones and only one explicit-LF fixture write in the pinned Stage A tests; missing-CLI remedy assertions scoped to that diagnostic; terminal-size stdlib mock restored before pytest reporting. Historical product imports and assertions remain pinned. The testing topic owns the fixture guidance. No added product behavior for these repairs.
- Baseline evidence: abrupt-death failure reproduced on unchanged main `2107e39bdd0dbe419813944889d41968d4b690a7`; historical cutover and missing-CLI failures reproduced on unchanged main `0ba56e5100d0302f0de4fdf74ebda9d30b391519`. Verbose reporter failure also reproduced on Linux and unchanged main Windows. Detailed logs/receipts remain in Git history and `.coga/clean-install/dependency-review-20261110/`.
- Fresh fetch/rebase integrated main's merged PRs #1193/#1194. All ten remaining feature patches are byte-identical after stripping diff blob-ID metadata. The separately approved navigation repair independently landed as `4ee4d7e73` and was dropped as a proven duplicate. Current branch has three implementation commits; no ticket is staged or committed as feature work.
- Final integrated-head Linux receipts: **4,777 passed / 33 skipped in 880.99s (14:40)**; focused/packaging **239 passed in 115.16s**. Python 3.12.12 on Pop!_OS 24.04 LTS, Linux x86_64 / 7.2.15-76070215-generic. Logs `/tmp/coga-dependency-peer-integrated-full.log` and `/tmp/coga-dependency-peer-integrated-focused.log`. Repo validation passed: **108 OK / 13 warnings / no errors**; seeded validation **5 OK / no issues**. No current native/Python 3.11 full-suite receipt is claimed.
- Native focused receipt at old head `8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5` / base `46f3e7383a20e6d068577720c1684ebd40cd7a0d`: six approved repair cases passed in 1138.01s (18:58), JUnit confirms zero errors/failures/skips. Artifacts `final-focused-suite/`. The earlier repaired native crash case passed in 92.80s at `9310fb1781aa32adf48b5e6b71b15d91b653cbdb`.
- **Owner explicitly requested “Stop Windows testing; defer verification” to owner review after material main drift.** The last native full attempt ran at old head `8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5` from 2026-11-11T16:42:18Z to owner-requested stop at 20:37:22Z, reaching 58% without reported failures or internal errors. Partial artifacts `final-suite/`; earlier interrupted evidence is in `first-suite/`, `suite/`, and `remainder-suite/`. **No completed native full-suite receipt exists. Native verification of the integrated head remains required before merge; deferral is not a waiver.**
- Native environment: Windows Server 2025 Datacenter build 26100.33674, Python 3.11.18, runtime UTF-8 mode 0, absolute checkout `src` PYTHONPATH, TERM=dumb, short pytest root `C:\ct`. Run `dependency-review-20261110`, default t3.large / 50 GB, us-east-1a; instance `i-009374adc23a09e72`, AMI `ami-0b5f645abc199e666` (`Windows_Server-2025-English-Full-Base-2026.10.28`).
- **Windows cleanup completed.** Both scheduled tasks removed and zero Python/Git/uv processes verified. All three final Defender exclusions (checkout, `C:\ct`, Git) removed and absence verified at 20:39:25Z. Instance terminated 20:40:22Z, security group deleted 20:40:23Z, key pair deleted 20:40:25Z; status 20:40:41Z confirms terminated and no retained volume/security group/key pair. Original three exclusions had also been removed/verified before the final run. No cloud resources remain.
- Checkout recovery: another Coga activity returned the shared primary to main at 18:59:52Z. A failed guard was mistakenly followed by a rebase of clean main, retaining upstream history; no source/ticket work was lost and the pushed feature stayed at `8fdf885cb`. Published that finding and paused for the human. After the human follow-up, verified main clean/unchanged since our handoff, backed up the current control ticket, switched to the feature, rebased, and restored the ticket byte-for-byte. Branch/status guards now stop the operation sequence on failure.
- Real-terminal verification completed at this integrated head in an 80x24 PTY: A done, C active, B blocked on A/C plus a human ask. Bare megalaunch reported zero launches/drains and one unresolved skip; independent inspection proved B stayed blocked and only A resolved. Runner `/tmp/coga-dependency-terminal-integrated.py`. The verbose terminal-size reporter regression also passed (1 in 0.60s).
- Branch is committed and pushed at the final head above. Final fetch saw only unrelated ticket/log updates since the reviewed base; no further material drift. Current ticket is the only dirt and stays out of implementation commits. Review/preparation are complete for handoff to mechanical PR opening; native merge approval remains pending the explicitly deferred full-suite receipt.
- Adjacent Retro finding: the native runbook’s roughly two-hour estimate was too optimistic for this suite/host (the last attempt reached 58% in about 3h55m). Preserve that evidence for future harness expectations; no further harness scope was added here.

## PR

```yaml
title: Keep unfinished dependency blockers open in megalaunch
author: codex
author_evidence: The implement handoff and retained usage identify Codex as the actual implementer, despite
  the configured claude agent. Codex also made the approved Windows fixture repair during this review session.
head: 72d6062e7ec5281f2815b09d5c8c2c4ebfe97a37
base: d26934ef4c30b800e0b61c7ab0351d9690883265
depth: deep
rationale: Changes dependency activation and exact Git publication/recovery decisions. Direct Codex self-review
  completed without product-code findings. Owner explicitly deferred the required full native verification
  to owner review; inspect the diff and obtain that receipt before merge.
implementation: Resolve each satisfied dependency blocker with its own automatic answer using the captured
  blocker record. Publish partial answers under an exact ticket lease while retaining blocked; publish the
  remaining targeted resolutions and activation together before launch. Preserve all-open manual unblock behavior.
deviations: Human approved baseline Windows test-only repairs discovered during verification. The separately
  approved stale-link repair independently landed on main and dropped out during rebase. Main Git/Windows-supervisor
  changes were integrated; native verification of that integrated head was explicitly deferred by the owner.
limitations: Owner explicitly deferred native Windows verification to owner review; the integrated head still
  requires a full native receipt before merge. Local full verification uses Python 3.12.12. Historical Windows
  focused checks used Python 3.11.18 and precede material main integration. This was Codex self-review; no
  independent reviewer was used.
files:
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
  head: 72d6062e7ec5281f2815b09d5c8c2c4ebfe97a37
  base: d26934ef4c30b800e0b61c7ab0351d9690883265
  detail: Direct Codex self-review completed over all ten final diff paths at the recorded head/base, with
    no must-fix product-code findings. The main integration was re-reviewed. Merge approval remains pending
    the required native Windows full-suite receipt explicitly deferred by the owner; the completed code review
    is ready for PR publication.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest -q
  status: passed
  head: 72d6062e7ec5281f2815b09d5c8c2c4ebfe97a37
  base: d26934ef4c30b800e0b61c7ab0351d9690883265
  detail: 4777 passed, 33 skipped in 880.99s (0:14:40). Pop!_OS 24.04 LTS, Linux x86_64 / 7.2.15-76070215-generic,
    Python 3.12.12. Code/tests/docs matched the committed tree throughout; final head stayed unchanged. Log
    /tmp/coga-dependency-peer-integrated-full.log.
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest tests/test_packaging.py tests/test_megalaunch.py
    tests/test_blackboard.py tests/test_checkouts.py::test_abrupt_launch_death_is_recovered_at_the_next_entry
    tests/test_git.py::test_stage_b_first_deletion_and_carrier_publish_against_stage_a_control tests/test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep
    tests/test_launch.py::test_launch_agent_not_in_path -q
  status: passed
  detail: 239 passed in 115.16s (0:01:55). Pop!_OS 24.04 LTS, Linux x86_64 / 7.2.15-76070215-generic, Python
    3.12.12. Code/tests/docs match the committed tree. Log /tmp/coga-dependency-peer-integrated-focused.log.
  head: 72d6062e7ec5281f2815b09d5c8c2c4ebfe97a37
  base: d26934ef4c30b800e0b61c7ab0351d9690883265
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --json
  status: passed
  head: 72d6062e7ec5281f2815b09d5c8c2c4ebfe97a37
  base: d26934ef4c30b800e0b61c7ab0351d9690883265
  detail: 108 OK; 13 warnings; no errors. Same Linux/Python environment. Output /tmp/coga-dependency-peer-integrated-validate.json.
- command: cd tests/fixtures/seeded-repo/coga && env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src
    /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json
  status: passed
  head: 72d6062e7ec5281f2815b09d5c8c2c4ebfe97a37
  base: d26934ef4c30b800e0b61c7ab0351d9690883265
  detail: 5 OK; no warnings or errors. Same Linux/Python environment. Output /tmp/coga-dependency-peer-integrated-seed-validate.json.
- command: 'stty cols 80 rows 24

    PYTHONPATH=/home/n/Code/coga/src TERM=xterm-256color .venv/bin/python /tmp/coga-dependency-terminal-integrated.py
    run

    PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-dependency-terminal-integrated.py inspect'
  status: passed
  head: 72d6062e7ec5281f2815b09d5c8c2c4ebfe97a37
  base: d26934ef4c30b800e0b61c7ab0351d9690883265
  detail: 'Real 80x24 PTY on Linux/Python 3.12.12: zero launched/drained and one unresolved skip. Verified
    B remained blocked, only A resolved, and C plus the human ask stayed open.'
- command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest tests/test_megalaunch.py::test_windows_keys_resize_and_extended_keys
    -vv --tb=short
  status: passed
  head: 72d6062e7ec5281f2815b09d5c8c2c4ebfe97a37
  base: d26934ef4c30b800e0b61c7ab0351d9690883265
  detail: 1 passed in 0.60s; verbose reporting exits cleanly. Same Linux/Python environment. Log /tmp/coga-dependency-peer-integrated-verbose-key.log.
- command: git diff --check && git diff --check origin/main...HEAD
  status: passed
  head: 72d6062e7ec5281f2815b09d5c8c2c4ebfe97a37
  base: d26934ef4c30b800e0b61c7ab0351d9690883265
  detail: No whitespace errors in the implementation diff or projected handoff.
- command: C:\Users\Administrator\coga-work\.venv\Scripts\python.exe -m pytest tests/test_git.py::test_stage_b_first_deletion_and_carrier_publish_against_stage_a_control
    tests/test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep tests/test_launch.py::test_launch_agent_not_in_path
    tests/test_megalaunch.py::test_windows_keys_resize_and_extended_keys -vv --tb=short --basetemp=C:\ct --junitxml=C:\coga-clean-install\dependency-final-focused\junit.xml
  status: passed
  detail: 6 passed in 1138.01s (0:18:58), JUnit confirms no errors/failures/skips. Native Windows Server 2025
    build 26100.33674, Python 3.11.18; absolute checkout src PYTHONPATH, TERM=dumb. Artifacts .coga/clean-install/dependency-review-20261110/final-focused-suite/.
    Historical before material main integration; does not verify the integrated head.
  head: 8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5
  base: 46f3e7383a20e6d068577720c1684ebd40cd7a0d
- command: Native Windows full suite at the integrated PR head
  status: not-run
  detail: Owner explicitly stopped Windows testing and deferred verification to owner review. No completed
    native full-suite receipt exists. The historical attempt at 8fdf885cbb1bd90b4ed808e1d4b3afbad8c175c5 reached
    58% without reported failures before stopping; its partial results do not verify this integrated head.
    The full native receipt remains required before merge. Host teardown and exclusion removal are complete.
```
