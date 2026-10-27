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
step: 2 (evaluate-design)
agent: claude
launch_generation: 9156bb15-e92f-4658-9e6a-4764e26bcefa
---

## Description

The owner paused GitHub's Test workflow on 2026-10-26 after repeated failure
notifications. Its all-PR/all-main triggers turn frequent ticket/log
publication into repeated full Linux/Windows runs. Restore useful CI with a
deliberate release cadence and explicit checks for platform-sensitive work.

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
owned by `state-sync-published-unmerged-recurring-templates`.

### Recommended policy and tradeoff

Use one full Python 3.11 Linux/Windows matrix as a prerequisite of **every
package publication**, plus an independently dispatchable Test workflow.
Remove automatic PR and push triggers; retain no selective automatic PR
coverage. The incident's pytest runtimes were 6m42s on Linux and 54m06s on
Windows, before queueing and setup. A previous Windows run recorded in
PR #1097 took about 80 minutes. Frequent source PRs would still consume that
feedback time under a source-path filter, while changes to shipped prompts
and templates make a narrow path allowlist easy to get wrong.

The tradeoff is explicit: ordinary PRs lose automatic hosted feedback and
depend on step-level tests and review; release uploads always wait for both
platforms. Before merging platform-sensitive changes, the implementer or
reviewer must manually dispatch Test on the candidate branch and record the
actual tested commit. This includes OS-dependent imports, process/terminal
handling, locks, filesystem/path/encoding/Git behavior, dependency or Python
requirements, packaging/install behavior, executable templates, native test
fixtures and skip rules, and either CI workflow. Pure ticket/log updates and
prose-only edits need no hosted matrix; normal local verification, including
twin checks where relevant, still applies. A source-affecting change after
the receipt requires a new run. A state-only rebase may retain historical
evidence with a precise content comparison, never a claim that the new SHA
was tested.

This proposal gates PyPI/TestPyPI uploads. Retaining
`.github/workflows/release.yml`, `on.release.types: [published]`, means the
GitHub Release page is already published when its package gate runs. The
release procedure should run Test on the exact intended tag commit before
publishing that page; the upload workflow still runs its own gate. Gating
creation of the GitHub Release page itself would be a different release
orchestration decision, called out for owner review below.

### Acceptance criteria

- [ ] Reconcile with current main and the two related tickets. Preserve
  PR #1118's merged reminder behavior, including its human-pause guidance.
  The complete packaging suite passes without skipping, weakening, or adding
  an exception for `test_live_and_packaged_copies_stay_identical()`; any
  newly exposed CI failures receive real fixes.
- [ ] Test has only `workflow_dispatch` and `workflow_call` entry points.
  Pushes and PR events, including routine task/log-only changes, launch no
  matrix. Both entry points run the full suite on `ubuntu-latest` and
  `windows-latest` with Python 3.11 and the existing supported exclusions.
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
- [ ] Both matrix legs finish independently (`fail-fast: false`). Explicit
  test/release runs do not cancel one another, and newer state pushes cannot
  enqueue or cancel them. Document deliberate manual cancellation and the
  resulting refusal to publish.
- [ ] `coga-dev/testing` owns the chosen cadence, manual-check criteria,
  cancellation policy, and evidence requirements. Update the live releasing
  skill and its packaged twin to describe the gate and distinguish Test
  validation from index publication. Keep their bytes identical and retain
  the existing local packaging and attended clean-install checks.
- [ ] Verify workflow syntax, all event/target routes, dependency failure
  behavior, and current branch-protection/ruleset settings. Do not require a
  Test status on every PR when this policy intentionally omits automatic PR
  runs. Record the observed settings and any separately approved change.
- [ ] After the reviewed trigger change is on default `main`, verify that
  definition before enabling Test. Obtain green hosted Linux and Windows
  runs for the repaired commit; record run/job URLs, full checked-out SHA,
  Python versions, commands, pass/skip counts, and runtimes. Verify at least
  one subsequent routine state push created no Test run. Confirm GitHub's
  workflow state is `active` at completion. Missing or failed hosted evidence
  leaves rollout incomplete, even if local tests pass.

### Proposed shape

1. Recheck the incident against fetched main. Use
   `tests/test_packaging.py`, `test_live_and_packaged_copies_stay_identical()`,
   and a direct diff of the two blocker-reminders templates before editing
   either. The mismatch is already repaired at design time. Do not duplicate
   the state-publication ticket or revert the merged recurring feature.
2. In `.github/workflows/test.yml`, replace `on.pull_request` and `on.push`
   with `on.workflow_call` and `on.workflow_dispatch`. Keep `jobs.pytest`,
   its OS matrix, Python floor, Git identity, Linux ripgrep setup,
   `python -m pip install -e ".[test]"`, and `TERM=dumb` pytest environment.
   Pin its checkout to `${{ github.sha }}` and log the checked-out SHA and
   Python version. The workflow needs only `contents: read` and no secrets.
3. In `.github/workflows/release.yml`, add `jobs.tests` calling
   `./.github/workflows/test.yml`, with `permissions: {contents: read}`.
   Add `needs: tests` to **both** `jobs.testpypi` and `jobs.pypi`, keeping
   their existing event/target selection and normal success prerequisite.
   Pin both publishing checkouts to `${{ github.sha }}` too. Keep build,
   `twine check`, and upload together in each existing publishing job;
   preserve the `release.yml` identity, `testpypi`/`pypi` environments,
   Trusted Publishing, and job-scoped OIDC permissions. No artifact handoff
   or new publishing workflow is needed.
4. Remove Test's old PR/main `concurrency` expression. Use no shared
   concurrency group in either workflow: deliberate invocations are
   independent, and the two matrix jobs remain parallel. With no push/PR
   triggers there is no automatic backlog to coalesce. Operators may cancel
   a redundant manual Test run; cancellation never authorizes a dependent
   upload. Do not share a group between a reusable workflow and its caller.
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
   definitions are available on default main, exercise the gate on a
   disposable branch derived from the reviewed commit: keep the same
   workflow filenames and dependency/target conditions, replace all
   build/upload steps with inert sentinels, remove publishing
   environments/OIDC, and replace the matrix's expensive test steps with
   short controllable pass/fail steps. Inspect that branch before dispatching
   its Release workflow with `--ref`, separately for each index target.
   Neither sentinel may run after one matrix leg fails; success admits only
   the selected target; cancellation must not admit an upload sentinel.
   Record the exact substitutions and the probe's different SHA, then clean
   up the disposable branch. Never dispatch production Release as a test.
   No permanent Actions-expression framework is needed.
7. Keep Test disabled throughout pre-merge preparation. Leave the rollout
   checklist below on the blackboard for owner-held review; the frozen
   workflow has no separate post-merge agent step. Implementation/open-pr
   handoffs must distinguish finished code from pending operational checks.

### Rollout and verification

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
normal state push and confirm it produced no Test run. Do not create a fake
state edit solely for this observation. Record settings, URLs, counts, and
enabled state on the blackboard before treating resumption as complete.

If the new definition or hosted run fails, retain logs, disable Test again,
and repair through the same reviewed path. Do not restore all-push triggers
or bypass the Release dependency to make an upload proceed. Do not assume a
disabled reusable workflow's invocation behavior; keep releases on hold
during a failed rollout. A repaired, reviewed default-branch definition and
renewed local/static verification precede another controlled enable-and-test
attempt.

### Out of scope

- Changing Coga's state-publication selection, recurring scheduling, or
  reminder behavior; those have their own owners and tickets.
- Publishing a package, creating a release/tag, changing trusted publishers,
  or changing repository access/merge policy as a verification shortcut.
- Adding automatic path-filtered PR checks, schedules, macOS/Python matrices,
  caching/sharding, runner upgrades, or interactive agent/AWS tests.
- Changing `coga.toml` or `coga.local.toml`, weakening twin checks, or
  suppressing failure notifications instead of removing redundant triggers.

## Context

### Required reading and source map

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
- `coga/tasks/state-sync-published-unmerged-recurring-templates.md` is at
  owner `review-design`, with no implementation PR recorded. Its planned
  publication fix is coordination context, not a prerequisite for this
  already-merged twin repair or a reason to weaken checks.

### GitHub evidence and semantics

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
  for resumption. The workflow definition is retained for the future repair.
- Repository metadata confirmed public visibility. GitHub's billing policy
  makes standard hosted compute free here; the immediate concerns are feedback
  delay, duplicated work, and notifications. The release-focused cadence is a
  proposal, not a completed design decision.

<!-- coga:blackboard -->

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

The spec now recommends release-gated plus manual Linux/Windows testing,
with no automatic PR/main runs and required manual evidence for platform
changes. It includes both index dependencies, immutable checkout identity,
independent run/cancellation behavior, nonpublishing gate probes, and a
post-merge enablement checklist. Workflow configuration and GitHub enabled
state are unchanged. No implementation branch, code change, PR, hosted run,
package upload, or release was created in this design step.

## Design handoff

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

## Open Questions

- Owner decision at `review-design`: approve removal of all automatic PR
  coverage in favor of release gates plus the stated manual pre-merge
  checks. This deliberately trades automatic Windows regression detection
  on ordinary PRs for fewer long-running checks and notifications. The
  recommendation is concrete; it is not an already-approved policy.
- Confirm that the automatic gate protects package-index publication while
  the GitHub Release page retains its existing `published` trigger. The
  proposal adds an explicit pre-tag manual Test procedure and a mandatory
  upload gate. If the GitHub page itself must be technically gated, settle
  that release-orchestration requirement before implementation.
