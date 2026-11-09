---
title: 02 Repo cutover to package-owned definitions
status: done
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
agent: claude
contexts:
- coga-dev/principles
---

## Description

Stage B of the package-owned definitions split (see the group README for
the goal and full design). Migrate this repo onto the package-owned
definitions that stage A
(`v1/package-definitions/01-runtime-compatibility-for-package-owned-definit`)
made resolvable, remove the live copies, and enforce strict single-source
ownership.

### Dependency

Do not start until
`v1/package-definitions/01-runtime-compatibility-for-package-owned-definit`
is merged to control and every participating checkout's CLI is A or newer. If it is not, `coga block` naming that exact
ref. Use A's recorded legacy removal inventory and transitional-check
allowances as the starting point; recompute the inventory on current main.

### Stage B scope

**B — repo migration, removal, and strict ownership.** Reconcile with merged A
and verify the CLI in every participating checkout uses A or newer. During a
short coordinated migration window, quiesce state writers/recurring sessions,
back up local definitions plus complete blackboards/attachments, and inventory
active, parked, deleted and customized jobs. Compare definitions and sibling
files separately from mutable blackboards, using a known prior seed/version
when needed. A changed file is not presumed disposable merely because its
name matches a bundled resource. Ambiguity retains an intentional local
override until the owner decides; record the reason, never silently delete it.

Publish selection before removing its dependent definitions (it changes
nothing while equivalent locals still exist). For each approved bundled
parent, replace the definition with a carrier preserving the entire saved
blackboard byte-for-byte and remove only its reviewed definition siblings.
Keep nontrivial state even for jobs with no declared `state_keys`; retain
worklists, the shared log, clone ledgers, frozen periods and custom jobs.
Read state from freshly reconciled control, never from the package's zero
seed. A parent with no useful state can have no local ticket until first use.
Do not leave a carrier plus orphaned definition siblings at an intermediate
publication: prepare that parent's conversion as one guarded state change.

Live-copy deletions/conversions are normal Coga state and may reach control
before B's source/test commit. Use the ordinary publication path and inspect
its receipt; do not exclude paths, suppress guards, or commit the packaged
side through a state command. `coga run publish-state` without path operands
can sweep deletions; named operands must be existing files, so verify removed
paths separately in the resulting control tree. Reconcile any publication
conflict without discarding newer state. Check control with A's runtime and
packaging tests after selection, after the first conversion/deletion, and
after the full removal, before enabling B's strict test policy.

B replaces temporary twin equality with an inverse check: fail on every
unapproved live counterpart, even byte-identical ones. Keep explicit reasons
for scaffolds/state carriers and any reviewed override, require those reasons
to describe real current files, and reject new accidental package/live copies.
Do not preserve phone-home's full definition merely for its counters. Land
B's final ownership tests/docs after the removals are safe; no intermediate
control commit may depend on unmerged B runtime support.

The operator migration lives with the shipped init/recurring contracts, with
a linked release-note entry. It must work on customized existing repos and
rehearse a rollback: keep writers quiesced, retain current state/ledgers,
restore definitions from verified backups if needed, and restore selection
without replaying periods. Require A-or-newer clients after migration; old
clients cannot interpret carriers. Drain or defer migration of a job whose
frozen custom instructions still require removed definition attachments;
never rewrite frozen workflows or discard an unfinished period just to finish
the migration. Retained custom attachments are documented overrides, not
silent exceptions. Automatic seed-recognition/migration tooling is not
required.

### Acceptance criteria

- [x] This repo has no undeclared live counterparts of package resources;
  the inverse check fails on any unapproved live copy, even a byte-identical
  one, and on a deleted required fallback. All `coga-dev/` files remain
  local-only.
- [x] The compatibility stage is merged and in use on control before any
  dependent removal is published. A regression exercises the first live-copy
  deletion/state conversion from a feature checkout against that control
  version; control's package, navigation and representative runtime checks
  stay green before the cutover PR merges.
- [x] A separate final-state regression edits packaged content on a feature
  branch, both dirty and committed, then runs a mutating CLI exit sweep.
  Control's packaged bytes stay unchanged while ordinary local task,
  recurring-state and repo-context edits publish; control's packaging checks
  pass. No publication guard, root membership or provenance rule is weakened.
- [x] The documented operator migration is rehearsed on this repo, including
  rollback. Old seeds, customized overrides, parked jobs, saved state
  (including phone-home's complete `period_state`), worklists, clone ledgers,
  frozen periods, and repo-only jobs (`usage-report`, `upstream-coga`) and
  attachments are preserved. The temporary `rollout/trim-log/coga/`
  definition copies and their staged-twin assertions are removed.
- [x] Build the verification wheel from a pristine disposable clone and run
  installed-artifact smoke tests outside the editable source path. Cover all
  resource types and all nine parents with outward effects stubbed; compare
  package-resource bytes before/after and exercise read-only resources.
- [ ] The owning topics, `AGENTS.md`, indexes, shipped instructions and local
  development links describe the new ownership and navigation. Context-link
  validation reads the actual package tree. The relevant tests, seeded-repo
  validation and full suite pass after reconciliation with current main.

## Context

### Read first

The shared design contract and verified source context live in
[the group README](README.md) (`coga/tasks/v1/package-definitions/README.md`):
"Shared design" sections 1–4 and 6, "Out of scope", and "Context". Read it
in full before planning; it is not composed into this prompt. Update the
README's design in the same PR when this stage changes the contract.

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

pr: https://github.com/FastJVM/coga/pull/1190
branch: coga/v1-package-definitions-02-repo-cutover-to-packag-b5fd8f


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Peer review

- Direct Codex review **completed** in launch
  `45345faa-8745-4846-b00d-18ba936293ac`; re-reviewed all 38 paths at
  `d6550dae24eb043a99e8b7ccfe9a5c59e654483a` against base
  `4b7c3cda4bbd2b595fb12f0d69e790e5a53887d4` after the fixes and rebase.
  Actual implementation and review both used Codex, so this is self-review.
  No child review CLI ran; configured peer selection is not authorship evidence.
- **Resolved P2 — generated chat notice retained the removed twin rule.**
  `CheckoutNotice.render` now says to commit intended PR files before a sweep,
  matching the owning checkout topic. Rendered the resulting notice directly.
- **Resolved P2 — migration could publish a failed partial conversion.**
  The actual documented conversion block now runs in a subshell with `set -e`.
  Injected failure while removing the second sibling stops before publication;
  an injected publication failure stops before later commands. All three
  executable cases pass, including success, and preserve complete saved
  blackboard/worklist bytes. The unfixed block failed both negative cases.
  Recovery guidance restores verified definition preimages around current
  state before another mutating command; runtime publication guards are intact.
- The owner approved both corrections and prioritized the 11 Linux-skipped
  Windows integration cases. All 11 passed natively with zero skips before
  these fixes; exact head/base and cleanup receipts are in the follow-up below.
  This closes the missing targeted platform evidence, not the separate full
  Windows merge gate. Linux platform guards remain correct and unchanged.
- Rechecked all 102 backup file hashes, all eight complete carrier blackboards
  against control (including phone-home's 98,845 bytes), and all 89 removed
  paths. Migration receipts match; selection, conversion, rollback and full
  removal all followed Stage A. The final diff has no further review findings.
- The initial review's full Linux suite passed 4650 tests with 11 native-only
  skips at `a9691ad9c04d754518e5cbfcf46d7a66f0b6a8cf` / base
  `fb51b563f92b564b75c049419601e22db8c71765`. Its exact original receipt
  remains in `.coga/migrations/package-definitions-20261107/verification/peer-review/`.
  After the two fixes: 211 focused tests passed before commit. At the
  committed corrected head, the fresh pristine-clone wheel passed its content
  and installed-artifact assertions, and the full Linux suite passed
  **4653 tests, 11 skipped, exit 0 in 951.31s**. Those exact 11 skipped cases
  passed natively in the separate Windows run. Final fetch found main unchanged;
  the reviewed branch is pushed with all three commits ahead of main.
- Recommendation remains **deep**. The owner-approved Windows handoff deferral
  remains, with the before-merge obligations under `## Native merge gate`.
  The v1/14 fixes are still unmerged; no passing full native receipt is claimed.

## Review follow-up (2026-11-08)

- The owner approved both must-fix corrections and prioritized the 11 Linux
  skips. All are actual Windows-only integration cases (five Job Object,
  six PowerShell), so their platform guards remain. Ran all 11 on the
  standard native host at `cb30e8e19bae4336ec77664f5f5188f1a71c25b9`,
  base `4b7c3cda4bbd2b595fb12f0d69e790e5a53887d4`: **11 passed,
  0 skipped, exit 0 in 24.84s**, Windows Server 2025 build 26100 /
  Python 3.11.18, PowerShell 5.1, without externally enabling UTF-8 mode.
  The exact command, platform, UTC times, stdout and JUnit are retained in
  `.coga/clean-install/pkg-definitions-review-20261108/native-skips-final/`.
- The first native run also passed 11 tests, but its temporary PowerShell
  wrapper lost the process exit code. Preserved that evidence separately,
  corrected the wrapper to capture `$LASTEXITCODE`, and reran the same tests
  for the passing receipt above. No product change was needed for these skips.
- AWS SSO was renewed by the owner. Initial sandbox cache-write failures
  created no resources. Temporary run `pkg-definitions-skips-20261108b`
  used the standard Windows harness; no Defender exclusions were applied.
  Collected evidence, removed the scheduled task and verified zero Python,
  Git or uv processes. Real-time protection stayed enabled. The instance,
  security group and key pair have been removed. Harness status at
  2026-11-08T19:39:47Z confirmed termination and no tagged volumes. Helpers,
  private ledgers and receipts remain ignored.
- Applied both approved review fixes: the rendered chat notice now omits
  the obsolete twin rule, and the documented conversion block stops on
  conversion/publication failure. Recovery instructions preserve the current
  blackboard while restoring verified definition preimages before any later
  mutating command. No runtime publication guard changed.
- Exercised the actual documented shell block with publication stubbed:
  before the fix, two failure cases incorrectly continued and exited zero;
  after the fix, all three cases pass (success, sibling unlink failure,
  publication failure), preserving complete blackboard/worklist bytes.
  Broader checks passed 211 tests. Final-head full Linux verification passed
  4653 tests with 11 Windows-only skips in 951.31s; all 11 cases match the
  native passing inventory. Exact current receipts, stdout and JUnit are
  retained in `.coga/clean-install/pkg-definitions-review-20261108/`. A clean
  disposable clone built the retained wheel (SHA-256
  `70e4f0e5cdcb153d76ced3478ed8af10fc39c7f391341fb0833d5ff7b4a69861`),
  whose two artifact assertions passed. Repo/seeded validation passed.

## Migration attempt (2026-11-07)

- Human confirmed all participating clients include Stage A, approved the
  backed-up staged migration, and confirmed other recurring sessions/state
  writers are paused. Process inspection here exposes only the sandbox's
  namespace; the host-wide pause is the human's confirmation.
- Stage A PR #1159 merged as `bbca5cb0ed7c2bfb3187465c0a1d3fe49f85a019`.
  Both this checkout and the installed editable CLI at `/home/n/Code/coga`
  contain that merge. Both dependency asks were resolved with `coga unblock`.
- Recomputed inventory: 102 entries (including staged rollout files), all
  matching current package definitions or the reviewed Stage A hashes before
  migration. No ambiguous/custom bundled definitions found. Eight active bundled
  parents now retain their entire blackboards as carriers. `trim-log` remains
  unselected; `usage-report` and `upstream-coga` remain repo-only. All four
  saved recurring periods are done; no unfinished frozen attachment dependency.
- Verified local backup: `.coga/migrations/package-definitions-20261107/`
  contains the inventory/hash manifest, every legacy file, complete recurring
  directories and frozen periods, audit log, attribute scaffold, and both
  participating local checkouts' clone ledgers. Preserve it through rollout.
- Baseline control `cbe04a90713023aa81ea3d58b1b9cf0f0c3ba5cc`, tested from
  `/tmp/coga-stage-b-w2qqi_h7/control-check` with its own imports:
  `PYTHONPATH=/tmp/coga-stage-b-w2qqi_h7/control-check/src /home/n/Code/codex/coga/.venv/bin/python -m pytest -q tests/test_packaging.py tests/test_paths.py tests/test_recurring_state.py tests/test_recurring_shims.py tests/test_init.py -p no:cacheprovider --basetemp=/tmp/coga-stage-b-w2qqi_h7/baseline-tests`
  passed 252 tests in 13.00s (Python 3.12.12).
- Current publication contract has advanced since the group design snapshot:
  committed recurring files wait for merge; dirty recurring changes still
  publish. Migration uses ordinary dirty-state publication; regression coverage
  preserves the newer committed-file boundary without changing runtime code.
- Published selection before conversion, then converted phone-home alone;
  rehearsed rollback on this repo by restoring its verified definition and
  siblings around the current blackboard and restoring prior selection. Kept
  writers paused, current ledgers and frozen periods throughout; replayed no
  periods. Re-selected the eight jobs and completed all eight conversions and
  89 live-copy removals through ordinary `coga run publish-state` receipts.
  Each parent's conversion and sibling deletion was one guarded state change.
- Control checkpoints passed its own packaging, navigation, recurring-state,
  shim and init tests (same command as baseline, with the indicated basetemp):
  selection `d8b44caf0360a3779f4336d8b8e37a117cb4645d` (252 passed, 10.91s, `selection-tests`), first conversion
  `af924f84e06be968cc5774a15583b9ccd11c54b4` (252 passed, 11.04s,
  `first-conversion-tests`), rollback `48eb605cf6ef482c59ab06de353d8a5facf8d296`
  (252 passed, 10.96s, `rollback-tests`), and full removal
  `46d6cf2147eeadd3fb14215ca3de3fbdb7c75a58` (252 passed, 11.95s,
  `full-removal-tests`). Each run used a freshly reconciled disposable control
  clone and its own source imports, before enabling the strict feature policy.
- Verified all removed paths absent on control; all eight blackboards match
  saved bytes. Phone-home's complete 98,845-byte blackboard has SHA-256
  `db20a71b78fcb4533c916ca794369972b4bee8393af2ecb4b5a92a1550c9de01`.
  Worklists, both custom jobs and attachments, four frozen periods, the shared
  audit history and both local clone ledgers were retained. The five temporary
  rollout files are removed with the source change; live audit attributes and
  trim-log selection remain unchanged until their separate adoption task.
- The primary `/home/n/Code/coga` checkout was cleanly fast-forwarded to the
  completed cutover. Other upgraded checkouts may resume after pulling main.
  Keep the verified migration backup available through review and rollout.
- Implementing agent: Codex in this session, without a model override. The
  ownership/navigation checks pass (63 tests); the three real publication
  regressions pass, including dirty and committed package edits with ordinary
  task, carrier and repo-context positive controls. Full Linux verification
  passed (4650 passed, 11 skipped in 812.93s). The human subsequently approved a separate standard native Windows host;
  its results and teardown are tracked below.

## Implementation verification (2026-11-07)

- Implementation commit: `2a62293443b97288be69f21c0ad68c749fde1029`;
  merge base `46d6cf2147eeadd3fb14215ca3de3fbdb7c75a58`. Fetch/rebase found
  no new control commits and did not rewrite this head. All 36 implementation
  paths match the SHA-256 inputs recorded during the completed full Linux suite;
  only the projected ticket and group design notes remain unstaged.
- Pristine disposable clone `/tmp/coga-stage-b-w2qqi_h7/verification-clone`
  at that head passed the two wheel tests in 3.98s. The installed smoke runs
  outside editable source with all resource types, all nine parents, outward
  work stubbed, read-only resources and byte-for-byte package preservation.
- Also built a retained wheel directly from a second clean Git clone,
  `/tmp/coga-stage-b-w2qqi_h7/artifact-build-clone`, and ran the same content
  and installed-artifact assertions against that exact wheel. Wheel SHA-256:
  `cd7d782f49d1bfaa4bfaafa4f77100d6ae3f695f740ff1f6e93aa38250629be6`.
  Artifact, smoke driver, JSON receipt and pytest XML are retained under
  `.coga/migrations/package-definitions-20261107/verification/`. The first
  standalone driver inherited the host's deprecated bare Slack variable;
  clearing launch/notification variables as pytest does fixed the driver.
  This required no source change. Both clones remained Git-clean.

## Reconciled native verification (2026-11-07)

- Main advanced only in another ticket and the shared log. Rebased and pushed
  `46d007eb4b2d42043ae7f6e3668272aed9576a08` on base
  `7d8c2eeb70ddc8983942a38040bea01e48f6ad7c`; verified the source tree is
  unchanged from the earlier tested commit. Preserved both dirty task files
  through verified backups. Fresh Linux full-suite verification passed: 4650 passed, 11 skipped,
  0 failed in 724.24s on Pop!_OS 24.04 LTS / Python 3.12.12.
- A new pristine clone at the reconciled head passed both wheel tests in 3.93s.
  A wheel built directly there and its installed-artifact smoke also passed;
  its SHA-256 remains `cd7d782f49d1bfaa4bfaafa4f77100d6ae3f695f740ff1f6e93aa38250629be6`.
- Approved Windows run `pkg-definitions-b-20261107` attempted the full
  suite at that exact reconciled head: Windows Server 2025 Datacenter,
  build 26100, Python 3.11.18, started 2026-11-08T03:40:09Z.
  The Administrator S4U task is `CogaPackageDefinitionsB20261107`; remote
  results are under `C:\coga-clean-install\pkg-definitions-b`.
- Local resource ledger, keys and evidence stay in ignored
  `.coga/clean-install/pkg-definitions-b-20261107/`. The temporary
  `windows-run.py` helper there supports poll, collect and cleanup. Always
  collect the receipt, remove the scheduled task, run the standard harness
  teardown and verify status before finishing. Never publish credentials.
- The first encoded remote launch exceeded Windows command-line limits before
  any tests started; transferring the temporary script as a file fixed the
  harness invocation without a source change.

## Native baseline finding and existing owner

- The full Windows attempt at `46d007eb4b2d42043ae7f6e3668272aed9576a08`
  reproduced three failures in
  `tests/test_checkouts.py::test_policy_checks_peer_review_skill_for_current_and_legacy_steps`
  (both code/with-review shapes and code/design-then-implement). Focused
  feature reproduction: 3 failed in 5.76s. Separate native control checkout
  `7d8c2eeb70ddc8983942a38040bea01e48f6ad7c`: 3 failed in 7.83s.
  The fixture, `checkout_policy._changed_skill`, and packaged skill are
  unchanged by B. The Windows checkout has CRLF; text fixture IO writes LF
  and the byte-comparison policy chooses manual preparation.
- Existing owner `v1/14-interactive-coga-launch-on-native-windows` already
  owns these exact failures plus CRLF-sensitive packaging/carrier fixtures,
  native timeouts and detached Git maintenance. Its head
  `8ab6297fc1e2076fc0ffeebb6ecf09e1fd7c71c7` has a recorded green full native
  receipt (4649 passed, 103 skipped, 3 h 18 m), but those changes are not on
  current control. No duplicate baseline fix was made here.
- Stopped the known-failing full attempt at 2026-11-08T05:13:41Z after 93.5
  minutes: 649 pass, 3 skip and 3 failure symbols, 655 completed cases;
  exit 1, no completed full-suite JUnit report. This is incomplete evidence,
  not a passing native receipt. Its process tree and scheduled task were
  removed. Evidence stays in ignored `native-suite/` harness storage.
- Attended owner responses (2026-11-07): the updated decision explicitly
  chooses **handoff with the Windows merge gate pending**. It supersedes
  the earlier fixture-only repair option. The owner separately approved
  temporary test-path Defender exclusions, with restoration before teardown.

## Native cutover fixture follow-up

- Targeted Windows packaging/publication verification at the same head found
  `test_inventory_rejects_a_deleted_package_owner` writing native backslashes
  into a forward-slash resource manifest. The focused native reproduction
  failed in 1.13s before reaching the missing-resource assertion. The fix uses
  `PACKAGED_ROOT.as_posix()` in the fixture; it does not relax ownership or
  missing-resource checks. Focused Linux verification passes (1 test, 0.20s).
  This B fixture was fixed here; the unrelated `v1/14` baseline failures
  remain with their existing owner. Both new saved-state assertions compare
  raw Git bytes, avoiding
  text-mode CRLF conversion. All 41 focused Linux checks passed in 78.76s.
  The correction is committed and pushed as `8a68a5d1a127d0e14de04b4e9b4931da0be8d89f`;
  fresh full Linux verification passed (4650 passed, 11 skipped in 693.71s),
  and the 38 Windows packaging checks passed. Native publication results and
  the explicit merge gate are recorded below.

## Native merge gate — owner-approved deferral

- Final native focused run at `8a68a5d1a127d0e14de04b4e9b4931da0be8d89f`:
  **38 passed, 3 failed, 0 skipped in 866.47s**, Windows Server 2025
  Datacenter build 26100, Python 3.11.18. All packaging/installed-wheel
  checks passed. Each publication regression failed inside
  `tests/test_git.py`'s `_check_package_control`, while running that control
  tree's own tests; no runtime, publication guard, root membership or
  provenance rule was weakened.
- Historical A case: selection publishes, then the pre-conversion control
  check fails on three existing CRLF-sensitive packaging/carrier fixtures
  and two nested wheel-copy MAX_PATH failures (5 failed, 245 passed in
  171.40s). It did **not** reach its first deletion on Windows. The Linux
  regression and the five actual control migration checkpoints did pass.
- Both final-state cases pass their publication assertions: ordinary task,
  carrier and repo-context edits publish while packaged Git bytes remain
  unchanged. Their control checks then fail on two nested wheel-copy path
  limits plus the existing carrier LF/CRLF comparison (dirty case: 3 failed,
  250 passed in 174.23s; committed case: 3 failed, 250 passed in 224.99s).
- **Required before merge, still owned by this ticket:** reconcile the
  `v1/14` fixes; shorten the nested control-test temporary paths on Windows;
  and recheck the historical Stage A fixture's line-ending assumptions.
  Merging current Windows fixes does not rewrite the deliberately pinned
  historical A checkout. Preserve the original compatibility proof and all
  publication guards. Run a full native suite at the resulting B head.
- Exact stdout, JUnit, platform/command metadata and summaries are saved in
  `.coga/clean-install/pkg-definitions-b-20261107/native-final/` and
  `final-native-receipt.json`. Initial failing B-manifest evidence remains in
  `native-targeted/`; the portable fixture correction passes all 38 packaging
  checks on Windows and all 41 focused checks on Linux.
- The owner-approved exclusions covered only the checkout, this run's pytest
  temp directory and Git installation. All three were removed; verified empty
  path exclusions and enabled real-time protection at 2026-11-08T05:42:03Z.
  No process exclusions were used. All Python/Git/uv processes are gone and
  all three scheduled tasks were removed. AWS teardown completed: instance
  terminated at 2026-11-08T05:46:16Z, security group deleted at 05:46:17Z,
  key pair deleted at 05:46:19Z. Harness `status` at 05:46:39Z confirmed
  termination and no remaining tagged volumes or other run resources. The
  first sandboxed teardown needed an AWS SSO cache refresh; the approved
  escalated retry completed normally. Receipts stay in ignored harness evidence.

## Open-PR step (2026-11-08)

- `coga open-pr` opened PR #1190 at head `d6550dae` (3 commits ahead of
  main; non-overlapping task/log drift only). The owner chose to keep the
  native Windows full-suite gate on this ticket, with no separate draft. The
  PR body's limitations name it. **Do not merge #1190 until that receipt
  exists.**

## Current handoff

- Peer review is complete; both approved P2 findings are fixed, re-reviewed,
  committed and pushed. Final head `d6550dae24eb043a99e8b7ccfe9a5c59e654483a` is based on current control
  `4b7c3cda4bbd2b595fb12f0d69e790e5a53887d4`. Final fetch found main unchanged; the unconditional rebase was
  already completed on this base. No PR exists yet. Ready to bump once to
  the mechanical PR-opening step; no bump has run in this session.
- Full Linux suite at that head: **4653 passed, 11 skipped, 0 failed in
  951.31s**, exit 0. The exact 11 Windows-only skipped cases all passed
  natively at `cb30e8e19bae4336ec77664f5f5188f1a71c25b9`, zero skipped,
  exit 0 in 24.84s. Their Linux guards remain. The fresh pristine-clone wheel
  and both installed-artifact assertions passed; seeded/repo validation passed.
- Actual review identity is Codex, matching the implementation identity;
  `## PR` accurately records self-review and recommends **deep**. Every one
  of the 38 diff paths has an explanation, with exact check/review revisions.
- The owner-approved Windows full-suite deferral remains: reconcile v1/14,
  repair nested Windows control-test paths and historical Stage A line-ending
  assumptions, then obtain a full native receipt before merge. The targeted
  native passes do not satisfy that gate. The final acceptance checkbox stays
  open. Do not present this PR as merge-ready until that work is complete.
- The Windows scheduled task and test processes were removed, real-time
  protection remained enabled, and no Defender exclusions were used. AWS
  termination and deletion of the security group/key are verified, with no
  tagged volumes remaining. Evidence and the complete migration backup are
  retained. Only this projected ticket remains unstaged for launch publication.

## PR

```yaml
title: Enforce package-owned definitions after the repository cutover
author: codex
author_evidence: Actual implementation session used Codex, without a model override; launch 2999da1b-bf0b-4242-b752-37938dc5a81a.
  The configured ticket agent was not used as authorship evidence. Peer-review fixes were also implemented
  by Codex in launch 45345faa-8745-4846-b00d-18ba936293ac.
head: d6550dae24eb043a99e8b7ccfe9a5c59e654483a
base: 4b7c3cda4bbd2b595fb12f0d69e790e5a53887d4
depth: deep
rationale: Repository-wide definition removal and saved-state conversion warrant deep review. Direct Codex
  self-review completed and both new P2 findings are fixed. The owner-deferred full Windows verification
  remains a before-merge gate.
implementation: 'Completed the approved control cutover after Stage A: selected eight existing bundled
  jobs, retained all eight complete blackboards as carriers, removed 89 reviewed live definition files,
  and rehearsed rollback on this repo. The source change enforces strict single ownership, pins required
  resources, removes five staged trim-log copies, exercises real publication boundaries, and updates owning
  topics and navigation. Peer review removed the obsolete twin instruction from generated chat notices
  and made the migration shell stop before publication after a partial conversion, with recovery guidance
  and executable failure-path coverage.'
deviations: Current main now holds committed recurring edits until merge; the regression and group design
  preserve that newer contract while dirty carrier changes still publish. No state-root, provenance or
  runtime publication guard was changed. Trim-log remains unselected and its real audit attribute remains
  unchanged. The owner explicitly approved handoff with Windows verification deferred; native completion
  remains required before merge.
limitations: 'The full Linux suite and pristine installed-wheel verification pass at this head. The exact
  11 Linux-skipped native Windows cases passed on cb30e8e19bae4336ec77664f5f5188f1a71c25b9 before the
  review fixes; their platform guards remain. This is targeted evidence, not the required full native
  receipt. The prior owner-approved Windows handoff deferral remains: reconcile v1/14, shorten nested
  control-test paths and preserve the pinned historical Stage A compatibility proof while fixing its line-ending
  assumptions, then run the full native suite before merge. The three new POSIX shell runbook cases skip
  native Windows because they exercise a Unix operator script; native installed-wheel behavior has separate
  coverage. The temporary Windows host was fully torn down.'
files:
  AGENTS.md: Replace transitional mirroring instructions with package ownership, carrier exceptions and
    direct package navigation.
  coga/recurring/usage-report/ticket.md: Point this preserved repo-only job at the owning notification
    topic; leave its blackboard intact.
  coga/skills/coga/testing/clean-install/human-walk/SKILL.md: Repair development links to shipped clean-install
    skills after live-copy removal.
  coga/skills/coga/usage-report/post/SKILL.md: Repair the repo-only reporting skill link to the packaged
    notification owner.
  docs/README.md: Index user topics at their actual package owners and keep Coga-dev local.
  docs/contexts/coga-dev/codebase/SKILL.md: Update the source map from legacy inventory to required package
    resources.
  docs/contexts/coga-dev/packaging/SKILL.md: Own the strict inverse policy, physical scaffolds, saved
    carriers, reviewed overrides and artifact verification contract.
  docs/contexts/coga-dev/testing/SKILL.md: Document Stage A transition history, final publication regressions
    and clean installed-artifact checks.
  docs/release-notes/context-audiences.md: Repair the removed live-topic link to the owning package topic.
  docs/release-notes/package-definitions.md: Record the cutover and link the operator migration and rollback
    procedure.
  rollout/trim-log/coga/.gitattributes: Remove the temporary staged trim-log counterpart; actual log attributes
    and selection await their separate adoption task.
  rollout/trim-log/coga/recurring/trim-log/operations.md: Remove the temporary staged trim-log counterpart;
    actual log attributes and selection await their separate adoption task.
  rollout/trim-log/coga/recurring/trim-log/ticket.md: Remove the temporary staged trim-log counterpart;
    actual log attributes and selection await their separate adoption task.
  rollout/trim-log/coga/recurring/trim-log/ticket.py: Remove the temporary staged trim-log counterpart;
    actual log attributes and selection await their separate adoption task.
  rollout/trim-log/coga/workflows/trim-log/run.md: Remove the temporary staged trim-log counterpart; actual
    log attributes and selection await their separate adoption task.
  src/coga/compose.py: Remove the obsolete packaged-twin instruction from the generated chat checkout
    notice, matching the owning checkout guidance.
  src/coga/resources/templates/coga/bootstrap/address-pr-comments/ticket.md: Remove obsolete instructions
    to synchronize live and package definitions.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: Remove twin-mirroring
    requirements from the checkout procedure.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/chat/SKILL.md: Make ad-hoc checkout
    guidance preserve and edit the owning definition.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/reconciliation/SKILL.md: Reconcile
    owning definitions and dependent references after removing twins.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md: Show selection and
    saved state carriers in the package-owned layout.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md: Distinguish package upgrades
    for future runs from deliberate local definition forks.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Link the existing-repo migration
    procedure from the shipped init contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md: Describe one fact owner
    that may live in the package.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/package-definitions-migration.md: Specify
    quiescence, provenance review, verified complete backups, atomic conversions, milestone checks and
    state-preserving rollback. Stop the conversion block on failure and require restoration of verified
    definitions around current state before any later mutating command.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md: Replace obsolete
    twin guidance with reviewed override and ownership inventory rules.
  src/coga/resources/templates/coga/bootstrap/orient/ticket.md: Direct maintenance to the single package
    owner.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/contract-audit/SKILL.md: Audit
    strict ownership and required resources using the actual package tree.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/scan-protocol/SKILL.md: Describe
    counterpart ownership instead of twin equality.
  src/coga/resources/templates/coga/recurring/dream/ticket.md: Make recurring maintenance edit the package
    owner once.
  src/coga/resources/templates/coga/recurring/trim-log/operations.md: Remove obsolete staged-copy instructions
    while preserving separate explicit adoption.
  tests/legacy_removal_inventory.txt: Retire the temporary live-copy removal allowance after migration.
  tests/required_package_resources.txt: Independently pin all 144 required resource files so deleting
    an owner cannot evade the inverse check.
  tests/test_autoclose_sweep.py: Remove transitional twin assertions after the live autoclose definition
    is gone.
  tests/test_dream_worker_templates.py: Assert that Dream audits current ownership and the required-resource
    manifest.
  tests/test_edge_distribution.py: Execute the actual migration shell example on success and injected
    conversion/publication failures; require immediate stopping and byte-for-byte blackboard/worklist
    preservation. These three POSIX shell cases skip native Windows; installed-wheel runtime behavior
    is covered separately.
  tests/test_git.py: Exercise first conversion against actual Stage A control and both dirty/committed
    package isolation during a mutating CLI exit sweep. Compare saved-state Git blobs as raw bytes, without
    text-mode CRLF normalization.
  tests/test_packaging.py: Reject accidental counterparts, stale exceptions and missing fallbacks; validate
    carriers, actual package navigation and wheel resources. Serialize the synthetic required-resource
    manifest with forward slashes on every platform.
review:
  reviewer: codex
  kind: self
  status: passed
  head: d6550dae24eb043a99e8b7ccfe9a5c59e654483a
  base: 4b7c3cda4bbd2b595fb12f0d69e790e5a53887d4
  detail: Direct review completed in launch 45345faa-8745-4846-b00d-18ba936293ac; re-reviewed the final
    38-path diff after both fixes and reconciliation. The stale twin instruction and unsafe migration
    continuation are corrected. Executed the real shell example with injected unlink/publication failures
    and rendered the generated notice. Both actual implementation and review used Codex, so this is self-review.
    No additional findings; the previously owner-deferred Windows failures remain an explicit merge gate.
    Full Linux verification subsequently passed at this exact head/base, and the final fetch found main
    unchanged.
checks:
- command: env TERM=dumb PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest -q -p no:cacheprovider
    --basetemp=/tmp/coga-b-peer-fixes-full --junitxml=.coga/clean-install/pkg-definitions-review-20261108/full.xml
    > .coga/clean-install/pkg-definitions-review-20261108/full.out 2>&1
  status: passed
  head: d6550dae24eb043a99e8b7ccfe9a5c59e654483a
  base: 4b7c3cda4bbd2b595fb12f0d69e790e5a53887d4
  detail: 'Pop!_OS 24.04 LTS / Python 3.12.12: 4653 passed, 11 skipped, 0 failed in 951.31s, exit 0. Run
    after the fixes and unconditional reconciliation, with only the projected ticket unstaged. Includes
    all three real publication regressions and the three new documented-shell success/failure cases. All
    11 skipped case IDs match the separately passing native Windows run. Exact stdout, JUnit and metadata
    are retained in ignored review evidence.'
- command: C:\Users\Administrator\coga-work\.venv\Scripts\python.exe -m pytest -vv -rA tests/test_recurring_clone.py::test_windows_timeout_kills_descendant_after_parent_exit
    tests/test_uninstall.py::test_windows_uv_hint_runs_in_powershell tests/test_windows_clean_install.py::test_windows_walk_records_first_failure
    tests/test_windows_process_recovery.py -p no:cacheprovider --basetemp=C:\ct\s2\p --junitxml=C:\ct\s2\full.xml
  status: passed
  head: cb30e8e19bae4336ec77664f5f5188f1a71c25b9
  base: 4b7c3cda4bbd2b595fb12f0d69e790e5a53887d4
  detail: 'Windows Server 2025 build 26100 / Python 3.11.18 / PowerShell 5.1: all 11 cases previously
    skipped on Linux passed, zero skipped, exit 0 in 24.84s. Exact JUnit case set matches the Linux skip
    inventory. No externally enabled UTF-8 mode or Defender exclusions. The first wrapper lost the exit
    code despite passing tests; it was corrected and this rerun passed. Collected evidence, removed the
    task, verified no test processes, and verified AWS teardown at 2026-11-08T19:39:47Z.'
- command: env PYTHONDONTWRITEBYTECODE=1 /home/n/Code/codex/coga/.venv/bin/python -m pip wheel --no-build-isolation
    --no-deps . -w /home/n/Code/codex/coga/.coga/clean-install/pkg-definitions-review-20261108/dist
  status: passed
  head: d6550dae24eb043a99e8b7ccfe9a5c59e654483a
  base: 4b7c3cda4bbd2b595fb12f0d69e790e5a53887d4
  detail: Built from pristine disposable clone /tmp/coga-b-peer-fixed-artifact-tw3285sc/repo; coga-0.4.1-py3-none-any.whl
    SHA-256 70e4f0e5cdcb153d76ced3478ed8af10fc39c7f391341fb0833d5ff7b4a69861. Clone remained clean.
- command: env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/coga-b-peer-fixed-artifact-tw3285sc/repo/src
    /home/n/Code/codex/coga/.venv/bin/python /home/n/Code/codex/coga/.coga/clean-install/pkg-definitions-review-20261108/smoke-artifact.py
    /tmp/coga-b-peer-fixed-artifact-tw3285sc/repo /home/n/Code/codex/coga/.coga/clean-install/pkg-definitions-review-20261108/dist/coga-0.4.1-py3-none-any.whl
    /tmp/coga-b-peer-fixed-artifact-tw3285sc/smoke
  status: passed
  head: d6550dae24eb043a99e8b7ccfe9a5c59e654483a
  base: 4b7c3cda4bbd2b595fb12f0d69e790e5a53887d4
  detail: 'Both wheel assertions passed against that exact retained artifact: all resource types and nine
    parents, outward effects stubbed, read-only resources and unchanged package bytes. Installed outside
    editable source. Pristine clone clean before and after; Pop!_OS 24.04 LTS / Python 3.12.12.'
- command: env -u SLACK_WEBHOOK_URL -u COGA_IMPORTANT_WEBHOOK_URL TERM=dumb PYTHONPATH=/home/n/Code/codex/coga/src
    /home/n/Code/codex/coga/.venv/bin/python -m coga.cli validate --json
  status: passed
  head: d6550dae24eb043a99e8b7ccfe9a5c59e654483a
  base: 4b7c3cda4bbd2b595fb12f0d69e790e5a53887d4
  detail: 'From tests/fixtures/seeded-repo/coga: exit 0, 5 OK, no issues.'
- command: env -u SLACK_WEBHOOK_URL -u COGA_IMPORTANT_WEBHOOK_URL TERM=dumb PYTHONPATH=/home/n/Code/codex/coga/src
    /home/n/Code/codex/coga/.venv/bin/python -m coga.cli validate --json
  status: passed
  head: d6550dae24eb043a99e8b7ccfe9a5c59e654483a
  base: 4b7c3cda4bbd2b595fb12f0d69e790e5a53887d4
  detail: 'From repo root: exit 0, 98 OK, no errors. Twelve warnings at the checked ticket snapshot: the
    prior eleven plus this ticket blackboard exceeding 32 KiB.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: d6550dae24eb043a99e8b7ccfe9a5c59e654483a
  base: 4b7c3cda4bbd2b595fb12f0d69e790e5a53887d4
  detail: No whitespace errors.
- command: C:\Users\Administrator\coga-work\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
    --basetemp=C:\coga-clean-install\pkg-definitions-b\pytest --junitxml=C:\coga-clean-install\pkg-definitions-b\full.xml
  status: failed
  head: 46d007eb4b2d42043ae7f6e3668272aed9576a08
  base: 7d8c2eeb70ddc8983942a38040bea01e48f6ad7c
  detail: 'Windows Server 2025 Datacenter build 26100 / Python 3.11.18. Stopped the known-failing full
    attempt after 93.5 minutes: 649 pass, 3 skip and 3 failure symbols (655 completed cases); exit 1,
    no completed full-suite report. All three failures reproduce on unchanged control and are already
    owned by v1/14. This is incomplete, not a passing native receipt. No Defender exclusions were applied.'
- command: C:\Users\Administrator\coga-work\.venv\Scripts\python.exe -m pytest -q tests/test_checkouts.py::test_policy_checks_peer_review_skill_for_current_and_legacy_steps
    -p no:cacheprovider --basetemp=C:\coga-clean-install\pkg-definitions-b\baseline-pytest --junitxml=C:\coga-clean-install\pkg-definitions-b\baseline.xml
  status: failed
  head: 7d8c2eeb70ddc8983942a38040bea01e48f6ad7c
  base: 7d8c2eeb70ddc8983942a38040bea01e48f6ad7c
  detail: 'Native baseline reproduction in C:\coga-clean-install\pkg-definitions-b\control-baseline with
    PYTHONPATH pointing to that control checkout: 3 failed in 7.83s. Confirms the three checkout-policy
    failures predate B. The same focused feature check failed 3 in 5.76s.'
- command: C:\Users\Administrator\coga-work\.venv\Scripts\python.exe -m pytest -q tests/test_packaging.py
    tests/test_git.py::test_stage_b_first_deletion_and_carrier_publish_against_stage_a_control tests/test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep
    -p no:cacheprovider --basetemp=C:\coga-clean-install\pkg-definitions-b-final\pytest --junitxml=C:\coga-clean-install\pkg-definitions-b-final\full.xml
  status: failed
  head: 8a68a5d1a127d0e14de04b4e9b4931da0be8d89f
  base: 7d8c2eeb70ddc8983942a38040bea01e48f6ad7c
  detail: 'Windows Server 2025 Datacenter build 26100 / Python 3.11.18: 38 passed, 3 failed, 0 skipped
    in 866.47s. All packaging/wheel checks pass. The historical A case fails its pre-conversion control
    check (existing CRLF assumptions plus nested wheel-copy MAX_PATH); both final-state cases pass package/state
    publication assertions then fail nested control checks on MAX_PATH and the existing carrier LF/CRLF
    comparison. Temporary test-path Defender exclusions were owner-approved, then removed and verified;
    no process exclusions. These findings remain before-merge obligations under the explicit owner deferral.'
- command: C:\Users\Administrator\coga-work\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
  status: not-run
  detail: Full native verification at the final head is deferred by the owner. Reconcile v1/14, shorten
    nested control-test paths, and account for historical Stage A line endings, then run the full suite
    before merge. The prior full attempt and current focused failures are recorded separately; neither
    is a passing full native receipt.
```

## Dependency check (2026-11-03)

- Stage A (`v1/package-definitions/01-runtime-compatibility-for-package-owned-definit`)
  is `status: blocked` at `step: 2 (peer-review)` on `origin/main` (993005521),
  not merged. Per the ticket's Dependency section, no B work started; no branch
  created. Resume once A merges and every participating CLI is A or newer.
- Re-checked 2026-11-03 (origin/main 44f26537e): A advanced to `step: 4 (review)`
  (owner gate), PR https://github.com/FastJVM/coga/pull/1159 still OPEN, unmerged.
  Dependency unchanged; re-blocked naming A's exact slug so megalaunch can retry.

---

## Blockers

- [x] [2026-11-03 13:33] [agent:claude] id=20261103T133331 Waiting on v1/package-definitions/01-runtime-compatibility-for-package-owned-definit: stage A is blocked at peer-review and not merged to control. Per this ticket's Dependency section, stage B cannot start until A is merged and every participating checkout's CLI is A or newer.
  resolved: [2026-11-07 17:10] [human:nicktoper] Human confirmed all participating checkouts use Stage A or newer, recurring sessions and state writers can be paused, and both dependency asks may be cleared. PR #1159 merged as bbca5cb0ed7c2bfb3187465c0a1d3fe49f85a019 and its ticket is done on control. Both this feature checkout and the installed editable CLI from /home/n/Code/coga include Stage A. Proceed with the backed-up staged migration and rollback rehearsal, preserving complete state and ambiguous customizations.

- [x] [2026-11-03 15:14] [agent:claude] id=20261103T151432 Still waiting on v1/package-definitions/01-runtime-compatibility-for-package-owned-definit: it is at the owner review step and its PR https://github.com/FastJVM/coga/pull/1159 is open and unmerged. Stage B cannot start until A is merged to control and every participating checkout's CLI is A or newer. Merge #1159 to unblock.
  resolved: [2026-11-07 17:10] [human:nicktoper] Human confirmed all participating checkouts use Stage A or newer, recurring sessions and state writers can be paused, and both dependency asks may be cleared. PR #1159 merged as bbca5cb0ed7c2bfb3187465c0a1d3fe49f85a019 and its ticket is done on control. Both this feature checkout and the installed editable CLI from /home/n/Code/coga include Stage A. Proceed with the backed-up staged migration and rollback rehearsal, preserving complete state and ambiguous customizations.

---

## Blocker reminders

- bf4230493e77 last_reminded: 2026-11-05 08:55

- 41c01efb27f0 last_reminded: 2026-11-05 08:55
