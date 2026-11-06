---
title: Repair CI and resume with release-focused triggers
status: in_progress
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
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 5 (open-pr)
agent: claude
---

## Description

The owner paused GitHub's Test workflow on 2026-10-26 after repeated failure
notifications: its all-PR/all-main triggers turned frequent ticket/log
publication into repeated full Linux/Windows runs. On 2026-11-05 the owner
decided not to resume hosted CI at all. Verification moves to the agent
side: coding agents run the suite during their steps, and the release
procedure requires receipts from every supported platform, with Windows on
the AWS harness and macOS on the EC2 Mac host once macOS works.

The incident was a real packaging inconsistency: the live blocker-reminders
template reached main through state publication before its packaged twin.
`tests/test_packaging.py`, `test_live_and_packaged_copies_stay_identical()`,
failed on both platforms in
[run 40403547211](https://github.com/FastJVM/coga/actions/runs/40403547211).
`recurring-unblock-launch`
[PR #1118](https://github.com/FastJVM/coga/pull/1118) has since merged both
the behavior and matching templates, and current packaging tests pass.
Preserve that repair and leave the consistency check intact. The broader
publication-rule change is owned by
`v1/03-state-sync-published-unmerged-recurring-templates`.

### Decision and tradeoff

Owner decision, 2026-11-05: **no hosted test CI.** Delete
`.github/workflows/test.yml`. Keep `.github/workflows/release.yml` as the
upload mechanism, unchanged in behavior. This again reverses a CI decision:
a 2026-09-24 no-CI policy was reversed on 2026-10-23 by PR #1097, which this
ticket now undoes. `coga-dev/testing` records that history so a later
reader does not re-add CI without seeing why it was removed.

Verification has three tiers, all agent-run:

1. **Every change.** Implement, self-QA and review steps run the full suite
   locally on Linux and record receipts, as `coga-dev/testing` already
   requires.
2. **Platform-sensitive changes** (OS-dependent imports, process/terminal
   handling, locks, filesystem/path/encoding/Git behavior, dependency or
   Python requirements, packaging/install behavior, executable templates,
   native test fixtures and skip rules): **required before merge** (owner
   decision, 2026-11-05). Run the full suite natively on Windows through the
   Windows AWS harness, and on macOS once it is supported, at the PR's head
   commit, and record the receipt in the PR and ticket. A source-affecting
   change after the receipt requires a new run. The implementer runs it; the
   reviewer refuses to approve a platform-sensitive PR without it.
3. **Every release, before tagging.** The full suite at the exact commit to
   be tagged, on Linux, on Windows (AWS harness), and on macOS (EC2 Mac
   host, macOS AWS harness) once macOS works, which is the owner's
   "supported" threshold, plus the existing build,
   `twine check`, and clean-install checks. At least one tier-3 suite run
   uses a real Python 3.11 interpreter (the `requires-python` floor), for
   example in the Linux clean-install harness's Python 3.11 container or a
   uv-managed 3.11 on the Windows harness; a 3.12 run is not evidence for
   the floor. Any failure or missing receipt
   means no tag. Tag that exact full SHA and verify the tag resolves to it
   before publishing the GitHub Release page.

The tradeoff is explicit. Nothing mechanical blocks an upload: the tier-3
gate is a procedure in the releasing skill, enforced by the agent or human
running the release. A full native Windows run takes about two hours on the
harness. In exchange there are no hosted runs, queues or notifications, and
every platform check runs on real machines Coga already uses.

### Acceptance criteria

- [ ] Reconcile with current main and the two related tickets. Preserve
  PR #1118's merged reminder behavior, including its human-pause guidance.
  The complete packaging suite passes without skipping, weakening, or adding
  an exception for `test_live_and_packaged_copies_stay_identical()`.
- [ ] `.github/workflows/test.yml` is deleted and no other workflow runs
  tests. `release.yml`'s triggers, jobs, environments, Trusted Publishing,
  and OIDC permissions are unchanged; only its stale setup comment pointing
  at a nonexistent releasing topic path is corrected.
- [ ] The required tier-2 check is visible to every agent working in this
  repo: the testing policy owns it, and `AGENTS.md` "Testing Guidelines"
  gains a one-line pointer to it. Do not add it to shipped `code/*` skills:
  `coga-dev/` topics are local-only and shipped skills must not depend on
  them (`coga/context-layout`, "Context audiences").
- [ ] `docs/contexts/coga-dev/testing/SKILL.md`, "CI posture and receipts",
  is rewritten (and may be renamed) to own the no-hosted-CI decision with
  its date and history, the three verification tiers, the platform-sensitive
  list, the Python 3.11 floor-evidence requirement (replacing "cite the CI
  run"), and the receipt fields: full commit SHA, platform and OS version,
  Python version, exact command, pass/skip/fail counts, and runtime. Remove
  the stale paused-CI text and the description of `test.yml`. Keep the facts
  still relevant to local runs, such as ripgrep on PATH for the POSIX
  migration-runbook test and `TERM=dumb` when output formatting matters.
- [ ] The releasing skill (`coga/skills/coga/releasing/SKILL.md`) and its
  packaged twin
  (`src/coga/resources/templates/coga/bootstrap/skills/coga/releasing/SKILL.md`)
  stay byte-identical. Their "Real release" pre-tag gate requires the tier-3
  receipts on every supported platform, recorded where the release is
  tracked, and tags the captured, tested full SHA instead of `target main`,
  verifying the tag before publishing the page. They link the testing policy
  rather than restating it, and describe TestPyPI as a real upload to a test
  index.
- [ ] The Windows and macOS AWS harness skills are linked from the testing
  policy as the way to run tier 2 and tier 3. The macOS harness
  (`src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md`)
  currently has no procedure for checking out a SHA and running the full
  suite; add a short one modeled on the Windows harness's "Fix loop" and
  "Long native runs". The owner confirmed the EC2 Mac host is the macOS
  machine. If the procedure cannot be verified on that host in this PR,
  write it as unverified and file the verification as its own ticket before
  `coga open-pr`. The releasing skill and both harness
  skills have legacy live copies under `coga/skills/coga/...`, listed in
  `tests/legacy_removal_inventory.txt`: edit the package copy, mirror it
  byte-for-byte into the live copy, and commit both together before any
  sweeping command.
- [ ] No stale claims of hosted CI remain: grep `docs/contexts`,
  `src/coga/resources`, `coga/skills`, `README.md`, and `AGENTS.md` for
  `test.yml`, the Test workflow, `CI`, `setup-python`, and
  `windows-latest`, and fix every hit in the same PR. This includes the
  testing topic's "Known suite failures" section, which still refers to the
  CI setup-python interpreter and the hosted `windows-latest` drive split.
- [ ] Verify locally: the packaging suite, the full suite, `actionlint` on
  `release.yml` (not installed here; use its release binary from
  github.com/rhysd/actionlint, or record the gap), and `coga validate
  --json`, each with command and counts.
  This ticket has no post-merge obligation: deleting the file needs no
  GitHub-side step, and the disabled workflow record can stay. If the
  implementer finds a step only possible after merge, file it as its own
  ticket before `coga open-pr`, per `docs/contexts/coga/workflows/SKILL.md`,
  "Obligations the merge does not discharge".

### Out of scope

- Any hosted CI, including a release-gating test job, schedules, or
  path-filtered PR checks.
- Scripting a one-command pre-release run across all three platforms.
  This is a natural follow-up ticket if tier 3 proves tedious; propose it,
  don't build it here.
- Making macOS a supported platform, changing Python versions, or changing
  `requires-python`.
- Publishing a package, creating a release or tag, changing trusted
  publishers, or changing repository access or merge policy.
- Changing state-publication selection, recurring scheduling, or reminder
  behavior; those have their own owners and tickets.
- Changing `coga.toml` or `coga.local.toml`, or weakening twin checks.

## Context

### Required reading and source map

- Cite rather than attach `coga-dev/testing` at
  `docs/contexts/coga-dev/testing/SKILL.md`: read "Which code you are actually
  testing", "Test-writing rules", and "CI posture and receipts", plus its
  links to the clean-install harnesses. This is the policy owner rewritten in
  this PR.
- Windows harness:
  `src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md`,
  "Fix loop: checkout and remote commands" and "Long native runs". The full
  native suite takes about two hours and must run as a scheduled task with
  polling, not over one SSH session. macOS harness: the sibling
  `macos-aws/SKILL.md` (EC2 Mac dedicated host).
- Cite rather than attach `coga-dev/packaging` at
  `docs/contexts/coga-dev/packaging/SKILL.md`: read "Canonical copies and
  twins". `tests/test_packaging.py`, `_discover_live_packaged_twins()`, maps
  packaged files through `_live_counterparts()` into
  `IDENTICAL_LIVE_PACKAGED_PAIRS`, which
  `test_live_and_packaged_copies_stay_identical()` compares byte-for-byte.
  The blocker-reminders template is not an intentional-divergence exception.
- Cite rather than attach `coga/state-publication` at
  `docs/contexts/coga/state-publication/SKILL.md`, "Control versus feature
  checkouts": dirty canonical topics and skills publish through sweeps.
  Commit PR-owned knowledge with its packaged twin before running sweeping
  commands on the feature branch.
- Read `coga/skills/coga/releasing/SKILL.md`, "The release workflow",
  "Real release", and "Clean first-install gate". Today step 2 says "The
  workflow runs no tests, so this is the only behavioral check" and requires
  only a local full suite. Step 3 tags with `target main`. There is no
  `docs/contexts/coga/releasing/SKILL.md` in current main.
- `coga/tasks/recurring-unblock-launch.md` is done; PR #1118 merged at
  `94d3dad35bce156081ed6c02f15935355075091d`, and follow-up `7dfaf56ad`
  preserves the human-pause guidance. Both blocker-reminders copies match on
  current main; recheck rather than copying an older template.
- `coga/tasks/v1/03-state-sync-published-unmerged-recurring-templates.md` is
  coordination context, not a prerequisite.

### GitHub state

- On 2026-10-27, `gh api repos/FastJVM/coga/actions/workflows/test.yml`
  returned workflow ID `394591152`, `state: disabled_manually`. Main had no
  branch protection (`404 Branch not protected`) and no rulesets (`[]`), so
  no required check depends on Test. Recheck before deleting the file.
- The incident run's logs: Linux Python 3.11.17, 4048 passed / 10 skipped /
  1 failed in 402.39s; Windows Python 3.11.9, 3956 passed / 102 skipped /
  1 failed in 3246.62s. Windows skips about 90 more tests than Linux; the
  tier-3 Windows run exists for behavior that differs natively (paths,
  processes, locks, encoding), not because of extra Windows-only tests.

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

### Immediate mitigation — 2026-10-26

- The owner asked to turn off CI, create a repair/resumption ticket, and
  consider release-only runs. At ticket creation, no repair or new trigger
  policy had been implemented; subsequent findings are recorded above.
- Disabled GitHub workflow `Test` (`test.yml`, ID `394591152`) with
  `gh workflow disable test.yml --repo FastJVM/coga`. The API confirmed
  `state: disabled_manually`.
- Canceled all six active test runs: `40414860631`, `40414505496`,
  `40414500365`, `40414494051`, `40414474870`, and `40414471060`.
  A subsequent run listing showed no unfinished test runs.
- Updated `coga-dev/testing` to own the paused CI posture and the conditions
  for resumption. (Superseded 2026-11-05: the workflow is now deleted, not
  repaired; see Decision and tradeoff.)
- Repository metadata confirmed public visibility. GitHub's billing policy
  makes standard hosted compute free here; the immediate concerns are feedback
  delay, duplicated work, and notifications.

Previous ref: `windows-native/repair-ci-and-resume-with-release-focused-triggers` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

## Dev

branch: coga/v1-13-repair-ci-and-resume-with-release-focused--a448a8

## Implement handoff — 2026-11-05

Attended session (agent: claude, model claude-opus-5-5). Branch pushed at
`cc2f64255177c9c92caf4b9b0444631e7f549b6c`, rebased on origin/main
`a8fe8af9cd79f7873325f6ca45211451d8d770a0`. No PR yet.

What changed:
- `0e5d03567` **Sync packaged twins with live copies (owner decision this
  session).** Main's packaging suite was red at start (2 failed / 35 passed):
  state sync `421ee15c0` published v1/14 (interactive launch on native
  Windows) live-copy edits without package twins: windows-aws harness,
  launch-boundary, first-task, install, launch, recurring/scheduling,
  script-tickets, tickets/authoring, plus a `coga/install#windows-baseline`
  link in coga-dev/current-direction. Owner chose "sync package to live":
  the eight package owners now carry the published live text verbatim. **v1/14's
  PR must reconcile with this** (its package twins already match its live
  text on main once this merges).
- `cc2f64255` the ticket's change: `test.yml` deleted; `release.yml` comment
  path fixed only (actionlint clean); `coga-dev/testing` "CI posture and
  receipts" replaced by "Verification tiers and receipts" (decision + history,
  three tiers, platform-sensitive list, 3.11 floor evidence, receipt fields,
  local-run facts); stale setup-python / hosted-Windows text in "Known suite
  failures" rewritten; `coga-dev/codebase` map line; AGENTS.md Testing
  Guidelines pointer; releasing skill (both copies, byte-identical) pre-tag
  gate requires tier-3 receipts, tags the captured full SHA and checks it via
  `git ls-remote ... ^{}` before publishing, TestPyPI described as a real
  upload; macOS harness (both copies) gains "Full suite at a commit", marked
  **unverified**, follow-up filed: `v1/44-verify-the-macos-full-suite-procedure-on-the-ec`.
- Windows harness needed no tier text: the policy links its fix loop / long
  native runs; its `checkout` already syncs with uv-managed Python 3.11, which
  the policy cites as floor evidence.

Decisions / notes:
- Remaining grep hits for `CI` are generic adopting-repo text (open-pr
  "resolve CI failures", bootstrap/import, coga.toml template comments,
  phone-home `CI` env suppression, notifications, edge-code) — not claims
  of Coga hosted CI; left unchanged.
- This change is not platform-sensitive (docs/workflow deletion only), so no
  tier-2 Windows receipt.
- Observed during the step (adjacent, owned by
  `v1/03-state-sync-published-unmerged-recurring-templates`): `coga create`
  triggered "Sync coga state" `a8fe8af9c`, which published this branch's
  committed **live** copies (releasing, macos-aws, coga-dev/testing,
  coga-dev/codebase) to main without their package twins. Main's packaging
  twin check is therefore red until this PR merges. Same incident class as
  the one this ticket started from.
- GitHub rechecked 2026-11-05: workflow 394591152 `disabled_manually`, main
  unprotected (404), rulesets `[]`. No post-merge obligation found.
- Follow-up proposed, not filed: one-command pre-release run across all
  platforms, if tier 3 proves tedious.

## PR

```yaml
title: Delete hosted test CI; move verification to agent-run tiers
author: claude
author_evidence: Implement step ran as an attended Claude session (claude-opus-5-5); see Implement handoff — 2026-11-05.
head: cc2f64255177c9c92caf4b9b0444631e7f549b6c
base: a8fe8af9cd79f7873325f6ca45211451d8d770a0
depth: standard
rationale: Docs/policy changes plus one workflow deletion; no Python changes. The twin-sync commit 0e5d03567 carries v1/14's published live text into package owners (owner decision) and needs reviewer attention.
implementation: Deletes .github/workflows/test.yml (owner decision 2026-11-05, no hosted CI); fixes only release.yml's stale setup comment; adds an AGENTS.md pointer to the tiered verification policy; makes the releasing skill's pre-tag gate require tier-3 receipts and tag the tested full SHA; adds an unverified macOS full-suite procedure; syncs eight package twins to live text published by 421ee15c0. The coga-dev/testing and coga-dev/codebase rewrites and the live releasing/macos-aws copies reached main early through state sync a8fe8af9c, so they are already in the base and absent from this diff.
deviations: Twin sync of v1/14's live text (commit 0e5d03567) is outside this ticket's scope; the owner chose it in the implement session because main's packaging suite was red.
limitations: No Python 3.11 suite run and no Windows/macOS run (change is not platform-sensitive). macOS procedure is unverified; tracked by v1/44-verify-the-macos-full-suite-procedure-on-the-ec.
files:
  .github/workflows/release.yml: Correct the stale setup-comment path only; behavior unchanged.
  .github/workflows/test.yml: Deleted; owner decision 2026-11-05, no hosted test CI.
  AGENTS.md: One-line Testing Guidelines pointer to the tier policy in coga-dev/testing.
  coga/skills/coga/testing/clean-install/macos-aws/SKILL.md: Live mirror of the package macOS harness (byte-identical).
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md: Add unverified "Full suite at a commit" procedure.
  src/coga/resources/templates/coga/bootstrap/skills/coga/releasing/SKILL.md: Tier-3 pre-tag gate, tag captured full SHA, verify tag, TestPyPI described as a real upload.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md: Package twin synced to live text published by 421ee15c0 (owner decision).
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/launch-boundary/SKILL.md: Package twin synced to live text published by 421ee15c0 (owner decision).
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: Package twin synced to live text published by 421ee15c0 (owner decision).
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: Package twin synced to live text published by 421ee15c0 (owner decision).
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: Package twin synced to live text published by 421ee15c0 (owner decision).
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Package twin synced to live text published by 421ee15c0 (owner decision).
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: Package twin synced to live text published by 421ee15c0 (owner decision).
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/authoring/SKILL.md: Package twin synced to live text published by 421ee15c0 (owner decision).
review:
  reviewer: none
  kind: none
  status: not-run
  detail: The frozen code/design-then-implement workflow has no code-review step before open-pr; design approval is not code review. The owner reviews at the next step.
checks:
  - command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider
    status: passed
    head: cc2f64255177c9c92caf4b9b0444631e7f549b6c
    base: a8fe8af9cd79f7873325f6ca45211451d8d770a0
    detail: "Linux (Pop!_OS 24.04 LTS), Python 3.12.12: 4453 passed, 10 skipped, 0 failed in 557.09s."
  - command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_packaging.py
    status: passed
    head: cc2f64255177c9c92caf4b9b0444631e7f549b6c
    base: a8fe8af9cd79f7873325f6ca45211451d8d770a0
    detail: 37 passed (was 2 failed / 35 passed on main 604add79c before the twin sync).
  - command: actionlint .github/workflows/release.yml
    status: passed
    head: cc2f64255177c9c92caf4b9b0444631e7f549b6c
    base: a8fe8af9cd79f7873325f6ca45211451d8d770a0
    detail: actionlint 1.7.7 release binary; exit 0, no findings.
  - command: env -u SLACK_WEBHOOK_URL coga validate --json
    status: passed
    head: cc2f64255177c9c92caf4b9b0444631e7f549b6c
    base: a8fe8af9cd79f7873325f6ca45211451d8d770a0
    detail: "97 ok, 0 errors, 9 warnings (all unrelated tickets: unfrozen-workflow, stuck-in-progress)."
  - command: Python 3.11 full suite
    status: not-run
    detail: Docs-only change; tier 1 permits reporting the interpreter used.
  - command: Windows/macOS native full suite
    status: not-run
    detail: Not platform-sensitive; macOS procedure unverified, see v1/44.
```

## Design investigation — 2026-10-27

Started on clean `main` at `7cd26919d`; fetched `origin/main` and confirmed
the checkout was current. This ticket has no implementation branch or PR.

- GitHub confirms `recurring-unblock-launch` PR #1118 merged as
  `94d3dad35bce156081ed6c02f15935355075091d` on 2026-10-26. The live and
  packaged blocker-reminders templates now match, including the later
  human-pause guidance. Preserve that merged behavior; do not replay the old
  template fix.
- `state-sync-published-unmerged-recurring-templates` is at owner-held
  `review-design`. Its broader committed-recurring publication fix remains
  separate work; `src/coga/git.py`, `_routine_state_areas()`, still includes
  `recurring_dir(cfg)` in the feature-checkout adoption allowlist.
- GitHub API: Test workflow `394591152` remains `disabled_manually`;
  the latest six runs are the canceled mitigation runs. Main's classic
  protection endpoint returns `404 Branch not protected`; the effective
  branch-rules endpoint returns `[]`. No required checks were found.
- Run `40403547211` logs confirm the single packaging failure on both
  platforms: Linux Python 3.11.17, 4048 passed / 10 skipped / 1 failed in
  402.39s; Windows Python 3.11.9, 3956 passed / 102 skipped / 1 failed in
  3246.62s. These are historical incident results, not current-head receipts.
- Current local diagnostic:
  `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_packaging.py`
  -> **30 passed in 4.39s**, Python 3.12.12, at `7cd26919d`.
  `git diff --no-index coga/recurring/blocker-reminders/ticket.md src/coga/resources/templates/coga/recurring/blocker-reminders/ticket.md`
  -> exit 0. No full-suite or new hosted verification is claimed.

The hosted release-gate design this investigation produced is superseded;
see Superseded designs. No implementation branch, code change, PR, hosted
run, package upload, or release was created in this design step.

## Spec revision — 2026-11-05

Attended `coga ticket` edit at owner `review-design`. The body was rewritten
for the owner's no-hosted-CI decision; the hosted release-gate design, its
evaluator review, and the open questions it raised are archived under
Superseded designs below. Frontmatter, step, and frozen workflow are
unchanged. The design-investigation evidence above (PR #1118, twin match,
GitHub settings, incident counts) still holds; its design conclusion does not. The earlier P1
(post-merge rollout orphaned by autoclose) no longer applies: this design has
no post-merge obligation.

Owner decisions, same session: tier 2 (platform-sensitive Windows run) is
required before merge; macOS receipts become required once macOS works,
on the EC2 Mac host; the title stays unchanged.

## Superseded designs

### 2026-11-05 — Hosted release gate plus Test workflow

Superseded by: no hosted CI; agent-run verification tiers with a
release-procedure gate on Linux, Windows (AWS) and macOS (dedicated machine).
Reason: in the attended `coga ticket` session the owner first rejected
removing all automatic PR coverage, then chose Linux-on-PR with Windows only
at release, then decided to drop hosted CI entirely and put verification on
the agent side, since agents already run Windows on AWS and macOS on a
dedicated machine. The owner confirmed that gating only the package upload,
not the GitHub Release page, was acceptable under the hosted design.

Intermediate revision (same day, never implemented): Test on `pull_request`
(Linux only, `paths-ignore` for `coga/tasks/**` and `coga/log.md`) plus
`workflow_dispatch`/`workflow_call` (Linux + Windows), an event-selected
matrix, a PR-only concurrency group, Release `needs: tests` on both upload
jobs, and a separate `maintenance/with-approval` rollout ticket for
post-merge enablement.

#### Description

The owner paused GitHub's Test workflow on 2026-10-26 after repeated failure
notifications. Its all-PR/all-main triggers turn frequent ticket/log
publication into repeated full Linux/Windows runs. Restore useful CI with
Linux checks on PRs and a full-platform gate before every release.

The incident was a real packaging inconsistency: the live blocker-reminders
template reached main through state publication before its packaged twin.
`tests/test_packaging.py`, `test_live_and_packaged_copies_stay_identical()`,
failed on both platforms in
[run 40403547211](https://github.com/FastJVM/coga/actions/runs/40403547211).
Since this ticket was drafted, `recurring-unblock-launch`
[PR #1118](https://github.com/FastJVM/coga/pull/1118) has merged both the
behavior and matching templates. Current packaging tests pass. Preserve that
repair, diagnose any remaining failures on the implementation revision, and
leave the consistency check intact. The broader publication-rule change is
owned by `v1/03-state-sync-published-unmerged-recurring-templates`.

##### Recommended policy and tradeoff

Owner decision, 2026-11-05: **Linux on every PR, the full platform matrix
only at release.** One Test workflow serves three entry points:

- `pull_request`: Python 3.11 on `ubuntu-latest` only (about 7 minutes in
  the incident run), skipped by `paths-ignore` for PRs touching only
  `coga/tasks/**` and `coga/log.md`. Do not ignore `docs/**`,
  `coga/recurring/**`, skills, or workflows: the incident itself was a
  recurring-template twin mismatch that the packaging tests caught. Use an
  ignore list, not an allowlist, so an unanticipated path runs rather than
  skips.
- `workflow_call` from Release, and `workflow_dispatch`: the full release
  matrix, currently `ubuntu-latest` and `windows-latest`.
- Pushes to `main` trigger nothing; routine state publication creates no run.

The incident's Windows pytest took 54m06s (about 80 minutes in PR #1097),
which is why Windows runs only as the release gate. A manual dispatch stays
available to anyone who wants early Windows feedback, but it is optional, not
a pre-merge requirement for any class of change.

The tradeoff is explicit: a Windows-only regression is caught at release
time, not at PR time. The gate then blocks the upload rather than shipping
the regression, and it is fixed through an ordinary PR before the release is
retried. macOS is planned: the release matrix is the single place it will be
added, and every leg in that matrix is automatically an upload prerequisite.
Adding the macOS leg is a later change, out of scope here.

**Cutover exception.** While Test is disabled, no Linux PR run exists. This
ticket's own workflow change, and any repair made during a failed rollout,
therefore merges on local/static verification alone and receives its hosted
evidence after merge through the rollout ticket below. The testing policy
must label this exception so later readers do not treat a PR merged without
its Linux run as precedent.

This proposal gates PyPI/TestPyPI uploads (owner-confirmed 2026-11-05). Retaining
`.github/workflows/release.yml`, `on.release.types: [published]`, means the
GitHub Release page is already published when its package gate runs. The
release procedure should run Test on the exact intended tag commit before
publishing that page; the upload workflow still runs its own gate. Gating
creation of the GitHub Release page itself would be a different release
orchestration decision; the owner chose not to make it here.

##### Acceptance criteria

- [ ] Reconcile with current main and the two related tickets. Preserve
  PR #1118's merged reminder behavior, including its human-pause guidance.
  The complete packaging suite passes without skipping, weakening, or adding
  an exception for `test_live_and_packaged_copies_stay_identical()`; any
  newly exposed CI failures receive real fixes.
- [ ] Test's entry points are exactly `pull_request` (with the `paths-ignore`
  above), `workflow_dispatch`, and `workflow_call`; it has no `push`
  trigger. PR runs use only `ubuntu-latest`. Dispatch and call runs use the
  full release matrix (`ubuntu-latest`, `windows-latest`). All use Python
  3.11 and the existing supported exclusions. A PR touching only
  `coga/tasks/**` or `coga/log.md` launches no run.
- [ ] Every Release route (GitHub release, manual `target: pypi`, and manual
  `target: testpypi`) requires successful completion of both matrix jobs
  before its build/upload job runs. Failure, cancellation, timeout, or a
  skipped prerequisite prevents publication. No bypass input,
  `continue-on-error`, or unconditional publish condition is introduced.
- [ ] Tests and publishing check out the same event commit, never a freshly
  resolved moving branch. Record `git rev-parse HEAD` and the interpreter in
  job logs. Release uses the reusable workflow from its own commit; a prior
  green result for another revision is not a substitute for this dependency.
- [ ] A manual Test run cannot publish: it has no index selector, publishing
  environment, OIDC permission, upload action, or downstream release trigger.
  Manual Release remains an intentional upload, including TestPyPI.
- [ ] Matrix legs finish independently (`fail-fast: false`). Release and
  dispatch runs do not cancel one another, and nothing a state push or PR
  does can enqueue or cancel them. A newer push to the same PR may cancel
  that PR's superseded Linux run. Document deliberate manual cancellation and the
  resulting refusal to publish.
- [ ] `coga-dev/testing` owns the chosen cadence (Linux per PR, full
  matrix at release, optional manual dispatch), the Windows-at-release
  tradeoff, cancellation policy, evidence requirements, and the labeled cutover
  exception. Update the live releasing skill and its packaged twin to
  describe the gate and distinguish Test validation from index publication.
  Their "Real release" procedure tags the captured, tested full SHA (not a
  moving `target main`) and verifies the tag resolves to that SHA before
  publishing the page. Keep their bytes identical and retain the existing
  local packaging and attended clean-install checks.
- [ ] Verify workflow syntax, all event/target routes, the dependency graph
  statically (every upload job needs `tests`, with no overriding `if`), and
  current branch-protection/ruleset settings. The executed failure and
  cancellation probe is post-merge work owned by the rollout ticket. Do not make the
  Linux check a required status: `paths-ignore` skips leave a required check
  pending forever on state-only PRs. Record the observed settings and any separately approved change.
- [ ] During the implement step (and in any case before `coga open-pr`),
  file the post-merge rollout as its own draft ticket with `coga create`
  and `workflow: maintenance/with-approval`, using the `### Rollout and
  verification` section below as its specification and done criteria. Its
  `approve` step is the owner gate before enablement, and it records no PR,
  so no merge can close it. Choose any valid slug in this ticket's `v1/`
  group. Any repair PR or `coga-dev/testing` receipt PR the rollout needs
  gets its own `code/*` ticket; the rollout ticket closes only through its
  own `cleanup-and-verify` step. Link it from this ticket's handoff and from
  the PR body. The PR and handoff state plainly that Test remains disabled and
  hosted evidence is pending in that ticket. This ticket's merge closes the
  code change only; it never claims rollout completion.

##### Proposed shape

1. Recheck the incident against fetched main. Use
   `tests/test_packaging.py`, `test_live_and_packaged_copies_stay_identical()`,
   and a direct diff of the two blocker-reminders templates before editing
   either. The mismatch is already repaired at design time. Do not duplicate
   the state-publication ticket or revert the merged recurring feature.
2. In `.github/workflows/test.yml`, replace `on.push` with
   `on.workflow_call` and `on.workflow_dispatch`, and keep `on.pull_request`
   with the `paths-ignore` above. Select the OS list by event, for example
   `os: ${{ fromJSON(github.event_name == 'pull_request' &&
   '["ubuntu-latest"]' || '["ubuntu-latest","windows-latest"]') }}`; inside
   a called workflow `github.event_name` is the caller's event, so Release
   gets the full list. Keep `jobs.pytest`, its Python floor, Git identity,
   Linux ripgrep setup, `python -m pip install -e ".[test]"`, and `TERM=dumb`
   pytest environment. Pin checkout to `${{ github.sha }}` and log the
   checked-out SHA and Python version. The workflow needs only
   `contents: read` and no secrets.
3. In `.github/workflows/release.yml`, add `jobs.tests` calling
   `./.github/workflows/test.yml`, with `permissions: {contents: read}`.
   Add `needs: tests` to **both** `jobs.testpypi` and `jobs.pypi`, keeping
   their existing event/target selection and normal success prerequisite.
   Pin both publishing checkouts to `${{ github.sha }}` too. Keep build,
   `twine check`, and upload together in each existing publishing job;
   preserve the `release.yml` identity, `testpypi`/`pypi` environments,
   Trusted Publishing, and job-scoped OIDC permissions. No artifact handoff
   or new publishing workflow is needed.
4. Replace Test's old PR/main `concurrency` expression with a group that
   applies only to PR runs, for example
   `group: ${{ github.event_name == 'pull_request' &&
   format('test-pr-{0}', github.event.pull_request.number) || github.run_id }}`
   with `cancel-in-progress` only for PRs. Dispatch and Release-called runs
   then get a unique group and are independent; do not share a group between
   the reusable workflow and its caller. Release itself has no concurrency
   group. Operators may cancel a redundant manual run; cancellation never
   authorizes a dependent upload.
5. Rewrite `docs/contexts/coga-dev/testing/SKILL.md`, "CI posture and
   receipts", to own the policy and explain its feedback/runtime tradeoff.
   Keep operational state truthful: the implementation PR describes the new
   policy and pending enablement; record the dated enabled-state receipt
   only after rollout. Fix the stale "only workflow" / "runs no tests"
   claims in `coga/skills/coga/releasing/SKILL.md` and
   `src/coga/resources/templates/coga/bootstrap/skills/coga/releasing/SKILL.md`.
   Those skills should link the testing policy and supply the release
   procedure, not duplicate its specification. Correct the stale releasing
   topic path in the release workflow's setup comment. Describe TestPyPI as
   a real upload to a test index, not a nonpublishing validation command.
6. Validate locally with the packaging suite, full suite, `actionlint` on
   both workflows, and `coga validate --json`. Check the trigger/dependency
   graph for all three Release routes and standalone Test. After the new
   definitions are available on default main, the rollout ticket exercises
   the gate on a disposable branch derived from the reviewed commit: keep the same
   workflow filenames and dependency/target conditions, replace all
   build/upload steps with inert sentinels, remove publishing
   environments/OIDC, and replace the matrix's expensive test steps with
   short controllable pass/fail steps. Inspect that branch before dispatching
   its Release workflow with `--ref`, separately for each index target.
   Neither sentinel may run after one matrix leg fails; success admits only
   the selected target; cancellation must not admit an upload sentinel.
   Record the exact substitutions and the probe's different SHA, then clean
   up the disposable branch. Never dispatch production Release as a test.
   No permanent Actions-expression framework is needed. This probe is
   post-merge work, owned by the rollout ticket, not by this ticket's PR.
7. Keep Test disabled throughout pre-merge preparation. This ticket's frozen
   workflow ends at owner `review`, and `autoclose-merged` marks it done when
   its PR merges without reading the blackboard
   (`docs/contexts/coga/workflows/SKILL.md`, "Obligations the merge does not
   discharge"). So every post-merge obligation lives in the separate rollout
   ticket required above: controlled enablement, both hosted receipts, the
   inert gate and cancellation probes, observation of a real state push, the
   enabled-state receipt in `coga-dev/testing`, and failed-rollout recovery.
   Implementation and open-pr handoffs distinguish finished code from that
   ticket's pending checks.

##### Rollout and verification

This section is the specification for the separate rollout ticket filed
before `coga open-pr`; it is not completed by this ticket's merge. That
ticket is done only when Linux and Windows hosted runs for the repaired
commit are green with run/job URLs, full checked-out SHA, Python versions,
commands, pass/skip counts, and runtimes recorded; the release-gate probe
and cancellation check pass; at least one subsequent routine state push
created no Test run; a source PR produced a Linux-only run and a
state-only PR produced none; and GitHub reports the workflow `active`. Missing or
failed hosted evidence leaves it open, even if local tests pass.

Manual dispatch requires a workflow definition on the default branch; the
current default has no dispatch trigger. Do not re-enable the old definition
to obtain a test run. First land the reviewed change with local/static
verification complete and confirm default `main` contains only the new Test
entry points and both Release dependencies. Recheck effective rules and
workflow state, then enable with
`gh workflow enable test.yml --repo FastJVM/coga` and confirm the API reports
`active`. This enables only the reviewed cadence.

Dispatch the nonpublishing Test workflow with
`gh workflow run test.yml --repo FastJVM/coga --ref <branch-or-tag>` against
the repaired revision. Capture the run's actual SHA and both checkout-log
SHAs; if a moving branch selected another commit, inspect that commit and
report or repeat the run instead of relabeling its result. Complete the
nonpublishing release-gate probe and cancellation check, then observe a
normal state push and confirm it produced no Test run. Also observe a real
source PR producing a Linux-only run and a state-only PR producing none. Do not create a fake
state edit solely for this observation. Record settings, URLs, counts, and
enabled state on the rollout ticket's blackboard before treating resumption as complete.

If the new definition or hosted run fails, retain logs, disable Test again,
and repair through the same reviewed path. Do not restore all-push triggers
or bypass the Release dependency to make an upload proceed. Do not assume a
disabled reusable workflow's invocation behavior; keep releases on hold
during a failed rollout. A repaired, reviewed default-branch definition and
renewed local/static verification precede another controlled enable-and-test
attempt.

##### Out of scope

- Changing Coga's state-publication selection, recurring scheduling, or
  reminder behavior; those have their own owners and tickets.
- Publishing a package, creating a release/tag, changing trusted publishers,
  or changing repository access/merge policy as a verification shortcut.
- Adding Windows to PR runs, schedules, the planned macOS leg, other Python
  versions,
  caching/sharding, runner upgrades, or interactive agent/AWS tests.
- Changing `coga.toml` or `coga.local.toml`, weakening twin checks, or
  suppressing failure notifications instead of removing redundant triggers.

#### Context

##### Required reading and source map

- Cite rather than attach `coga-dev/testing` at
  `docs/contexts/coga-dev/testing/SKILL.md`: read "Which code you are actually
  testing", "Test-writing rules", and "CI posture and receipts" before
  implementation. This is the policy owner to update in the same PR.
- Cite rather than attach `coga-dev/packaging` at
  `docs/contexts/coga-dev/packaging/SKILL.md`: read "Canonical copies and
  twins" and "Wheel packaging". `tests/test_packaging.py`,
  `_discover_live_packaged_twins()`, maps packaged files through
  `_live_counterparts()` into `IDENTICAL_LIVE_PACKAGED_PAIRS`, which
  `test_live_and_packaged_copies_stay_identical()` compares byte-for-byte.
  The blocker-reminders template is not an intentional-divergence exception.
- Cite rather than attach `coga/state-publication` at
  `docs/contexts/coga/state-publication/SKILL.md`: read "When Coga publishes"
  and "Control versus feature checkouts", especially the pre-review hazard.
  In `src/coga/git.py`, `_publish_locked()` passes `_routine_state_areas()`
  into `_candidates()` for non-control checkouts; that committed-state
  allowlist still includes recurring templates. Dirty canonical topics and
  skills also publish through sweeps. Commit PR-owned knowledge with its
  packaged twin before running sweeping commands on the feature branch.
- Read `coga/skills/coga/releasing/SKILL.md`, "The release workflow",
  "Real release", and "Clean first-install gate"; its fallback/twin is
  `src/coga/resources/templates/coga/bootstrap/skills/coga/releasing/SKILL.md`.
  There is no `docs/contexts/coga/releasing/SKILL.md` in current main.
- Current `.github/workflows/test.yml`, `on` and `concurrency`, create a run
  for each PR/main event and preserve every main push; `jobs.pytest` supplies
  the two-platform matrix. Current `.github/workflows/release.yml`,
  `jobs.testpypi.if` and `jobs.pypi.if`, select an index from the release event
  or dispatch target. Neither job has a test dependency; each independently
  checks out source, builds, checks metadata, and uploads.
- `coga/tasks/recurring-unblock-launch.md` is done; GitHub confirms PR #1118
  merged at `94d3dad35bce156081ed6c02f15935355075091d`. The follow-up commit
  `7dfaf56ad` preserves different guidance for human-paused periods. Both
  blocker-reminders copies match on current main. Recheck these facts before
  any repair rather than copying an older branch's template.
- `coga/tasks/v1/03-state-sync-published-unmerged-recurring-templates.md` is at
  owner `review-design`, with no implementation PR recorded. Its planned
  publication fix is coordination context, not a prerequisite for this
  already-merged twin repair or a reason to weaken checks.

##### GitHub evidence and semantics

- CI was introduced by [PR #1097](https://github.com/FastJVM/coga/pull/1097).
  [Incident run 40403547211](https://github.com/FastJVM/coga/actions/runs/40403547211)
  tested `c9fa73a0e24abb42e726931e043cf6a09a70f64c`. Its two job logs confirm
  one packaging failure each; exact versions/counts/timings are below.
- On 2026-10-27, `gh api repos/FastJVM/coga/actions/workflows/test.yml`
  returned workflow ID `394591152`, `state: disabled_manually`.
  `gh api repos/FastJVM/coga/branches/main/protection` returned
  `404 Branch not protected`; `gh api repos/FastJVM/coga/rules/branches/main`
  returned `[]`. These are dated observations, not settings to assume at
  rollout. No required-check setting needs removal on this evidence.
- Repository metadata still reports public visibility and the matrix uses
  standard hosted runners. Their compute is free under
  [GitHub's billing policy](https://docs.github.com/en/billing/concepts/product-billing/github-actions),
  rechecked 2026-10-27. Runtime, queueing, and notifications motivate this
  change; recheck pricing if visibility or runner class changes.
- [Reusable-workflow semantics](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)
  resolve `./.github/workflows/test.yml` from the caller's commit. Explicit
  caller permissions must allow checkout while the test job receives no
  OIDC publishing permission.
- [Job dependencies](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idneeds)
  require prerequisite success unless a condition overrides that behavior.
  [Event semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
  give a release the tagged commit and a manual dispatch its selected ref's
  commit; pin checkout to that event SHA.
- [Manual dispatch](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
  needs the workflow on the default branch and supports selecting another
  branch with `--ref`. Keep this requirement in the rollout ordering.
  [Concurrency semantics](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
  permit independent runs when no group is configured. Shared groups can
  cancel pending runs even without in-progress cancellation, which is why
  the proposed release/manual cadence does not use them.


#### Design handoff

The implementation spec is under `## Description` and `## Context`;
acceptance criteria are authored for the evaluator and owner to review.
No policy approval is claimed. The next step is the frozen
`evaluate-design` step, followed by the owner's `review-design` gate.

Verification:

- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task windows-native/repair-ci-and-resume-with-release-focused-triggers --json`
  -> exit 0, `ok_count: 1`, no issues or fixes.
- `git diff --check` -> exit 0.
- Direct read-only `compose.compose_prompt_report()` check confirmed that
  all spec sections and open questions compose. Frontmatter and the ticket
  guide remain byte-identical to HEAD; exactly one blackboard fence exists,
  and only Description/Context are level-two body sections. The first
  diagnostic used the checkout root as the config root and failed before
  composition; rerunning with the actual `coga/` config root passed.
- Final freshness fetch found `origin/main` still at
  `7cd26919d3555a0cc03f8e144611b1bc58e168e4`, with no intervening changes.
  This ticket is the only edited file. The packaging diagnostic above is
  the only suite run in this design step; CI remains paused.

#### Open Questions

Both resolved by the owner on 2026-11-05 (attended `coga ticket` session):

- PR coverage: not "no automatic PR runs" (too radical). Linux runs on
  every non-state PR; Windows runs only as the release gate; manual
  dispatch is optional. macOS will join the release matrix later.
- Release-page gating: the gate protects package uploads only; the GitHub
  Release page keeps its `published` trigger, preceded by the procedural
  pre-tag Test run.

#### Evaluator review

2026-10-27. Cold review of Description and Context against fetched `main`
`4cdc72995b5896733bfcd359abe0f9fde2b439ec`. The checkout started clean on
that revision. This ticket has no implementation branch or PR. The body
sections compose under the correct headings; the frozen workflow places
this evaluation before the owner's `review-design` gate.

**Verdict: revise before implementation for the rollout-ownership finding
below.** The proposed reusable matrix, upload dependencies, permissions, and
commit identity are otherwise implementable as one coherent PR. The owner's
two policy decisions under Open Questions remain decisions for that gate;
this review does not approve either policy.

##### Must fix before implementation

1. **P1 — Give the post-merge rollout an owner that survives merge.**
   Proposed shape item 7 leaves enablement and hosted verification on this
   ticket at owner review, while the final acceptance criterion requires
   those operations after merge. This ticket's frozen workflow ends at
   `review`. `src/coga/autoclose.py`, `OPEN_STATUSES`, `_on_final_step()`,
   `_candidate()`, and `_try_bump_one()`, mark an active/in-progress final-step
   ticket done once its recorded PR is merged, without reading acceptance
   criteria or the blackboard. An unchecked rollout list therefore cannot
   keep this ticket open. The existing
   `tests/test_autoclose.py::test_sweep_merged_bumps_final_step_with_merged_pr`
   confirms that behavior.

   Resolve this in the spec before implementation: require a separately
   tracked rollout task, filed with `coga create` and linked before
   `coga open-pr`, owning controlled enablement, both hosted receipts, the
   inert gate/cancellation probes, observation of a real state push, and
   failed-rollout recovery. Its completion must not depend solely on this
   implementation PR merging. Alternatively the owner must choose a
   lifecycle that does not close the outstanding obligation on merge.
   `docs/contexts/coga/workflows/SKILL.md`, "Obligations the merge does not
   discharge", and `coga/skills/code/open-pr/SKILL.md`, order-of-operations
   item 2, explicitly require this handoff. Leaving only a checklist on the
   current blackboard contradicts that contract and can report completion
   while Test remains disabled or unverified. No lifecycle or ticket-body
   change was made by the evaluator.

##### Optional recommendations

- Make the initial cutover exception explicit when writing the testing
  policy. The general pre-merge rule includes either CI workflow, while
  Rollout and verification deliberately requires local/static verification
  and merging before controlled enablement. Label that initial repair path
  (and repairs while Test is disabled) so later readers can distinguish it
  from the ordinary manual pre-merge requirement. The present rollout
  ordering already expresses the intended exception.
- When updating the releasing skill, replace "Real release" step 3's
  moving `target main` instruction with tagging the captured, tested full
  SHA and verifying the tag resolves to it before publishing the page.
  The spec already requires the intended tag commit to be tested; making
  the procedure concrete prevents a long hosted run plus intervening state
  pushes from silently selecting a different commit. Apply the same edit
  to the packaged twin.

##### Evidence and verification

- Rechecked both workflow files, the releasing skill and its packaged twin,
  the testing/packaging/state-publication topics, the packaging discovery
  and identity checks, and the resolved packaged workflow. The current
  Release jobs have no `needs`; Test retains its PR/main triggers and
  `fail-fast: false`. This frozen ticket omits the newer `peer-review` step;
  design evaluation is not a future implementation-review receipt.
- GitHub's [reusable-workflow contract](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows#calling-a-reusable-workflow)
  confirms same-commit local calls. Its [dependency contract](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idneeds)
  supports the proposed normal-success prerequisite. The [event reference](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
  confirms release/dispatch commit identity and the caller payload in the
  reusable workflow; [manual dispatch](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
  and [concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
  support the proposed rollout order and independent runs. This is contract
  verification, not an executed release-gate probe.
- GitHub reconfirmed [PR #1118](https://github.com/FastJVM/coga/pull/1118)
  merged as `94d3dad35bce156081ed6c02f15935355075091d`. Both reminder copies
  include the human-pause guidance and match byte-for-byte. The separate
  state-publication ticket remains at owner `review-design` with no PR
  recorded; `_routine_state_areas()` still includes recurring templates.
- Re-read both [incident run](https://github.com/FastJVM/coga/actions/runs/40403547211)
  job logs: checkout `c9fa73a0e24abb42e726931e043cf6a09a70f64c`, the single
  reminder-twin failure, and the reported Python versions, counts, and
  runtimes all match the design's historical receipts.
- Read-only GitHub checks on 2026-10-27:
  `gh api repos/FastJVM/coga/actions/workflows/test.yml` reports
  `394591152`, `disabled_manually`;
  `gh api repos/FastJVM/coga/branches/main/protection` returns HTTP 404
  "Branch not protected";
  `gh api repos/FastJVM/coga/rules/branches/main` returns `[]`.
  No workflow or repository setting was changed.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_packaging.py`
  -> **30 passed in 4.63s**, Python **3.12.12**, importing this checkout.
  Direct `git diff --no-index` comparisons of both blocker-reminders copies
  and both releasing-skill copies each exited 0.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_autoclose.py::test_sweep_merged_bumps_final_step_with_merged_pr tests/test_autoclose.py::test_sweep_merged_skips_non_final_step`
  -> **2 passed in 3.51s**, Python **3.12.12**.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task windows-native/repair-ci-and-resume-with-release-focused-triggers --json`
  -> exit 0, `ok_count: 1`, no fixes or issues. `git diff --check` passed.
  A byte comparison against HEAD confirmed the entire pre-existing ticket
  is preserved and exactly one evaluator section was appended below the
  single blackboard fence. The final freshness fetch still found
  `origin/main` at the reviewed revision, with no intervening changes.
- No implementation, branch, PR, hosted run, package upload, or release was
  created. Full-suite, Python 3.11/Windows, actionlint, and rollout evidence
  remain implementation/rollout work. Only this evaluator section was added;
  the authored spec, frontmatter, and prior blackboard were preserved.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `v1/13-repair-ci-and-resume-with-release-focused-triggers`
Recorded: 2026-11-06T06:40:32+00:00

    [open-pr] origin/main advanced only through non-overlapping Coga task/log state; branch is safe to publish
    PR presentation: invalid YAML under ## PR: mapping values are not allowed here
      in "<unicode string>", line 27, column 63:
         ...  warnings (all unrelated tickets: unfrozen-workflow, stuck-in-pr ... 
                                             ^

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `v1/13-repair-ci-and-resume-with-release-focused-triggers`
Recorded: 2026-11-06T06:40:42+00:00

    [open-pr] origin/main advanced only through non-overlapping Coga task/log state; branch is safe to publish
    PR presentation: review must be a mapping.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `v1/13-repair-ci-and-resume-with-release-focused-triggers`
Recorded: 2026-11-06T06:41:19+00:00

    [open-pr] origin/main advanced only through non-overlapping Coga task/log state; branch is safe to publish
    PR presentation: depth must be merge, skim, or deep.
