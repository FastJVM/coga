---
title: Publish all Coga and context files automatically
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
    skills: []
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

Replace the narrow tasks/log/recurring automatic publication scope with one directory rule: publish eligible changes anywhere under the configured Coga workspace and the configured contexts directory. The owner explicitly approved this on 2026-10-07 while discussing PR #973: contexts, skills, workflows, shared config and other files in those directories should be committed through normal Coga state publication, without requiring a separate knowledge PR. In this repository the roots are coga/ and docs/contexts/; resolve configured paths rather than hard-coding these spellings. Retain Git ignore behavior and existing publication safeguards. Packaged copies under src/ remain ordinary reviewed source changes. Apply the same roots consistently to the sweep, authoring finalization, checkout preparation/return, state-only commit recovery and any unpublished-edit warning. Update the owning contracts, instructions, fixtures and packaged twins together, removing the obsolete knowledge-only PR requirement for files inside these roots.

### Acceptance criteria

- New, modified, deleted and renamed eligible files inside either configured
  root publish through the existing guarded state mechanism, including skills,
  workflows, shared coga.toml, and contexts relocated outside the Coga directory.
  Overlapping roots do not cause duplicate work. Unrelated repository files
  remain outside automatic publication.
- Ignored local files remain local: coga.local.toml, generated agent-tooling
  views, caches and other ignored artifacts are not force-added. Do not change
  the owner's configuration as part of implementing this behavior.
- Existing provenance, compare-and-swap, concurrent-update, ticket-generation,
  rollback and uncertain-push safeguards remain. Broadening which files are
  eligible does not permit stale overwrites or discarding unpublished changes.
- A bootstrap authoring session can write a context and leave it published;
  the next ordinary ticket launch succeeds without an extra knowledge branch.
  Build's generated product/vision is available to its tickets in a fresh clone.
  Publication failures retain the edits and do not claim a completed handoff.
- Checkout entry/return and recovery use the same directory membership as
  publication. A successfully published context or skill must not still be
  classified as a foreign dirty path. Source outside these roots remains
  protected by the normal code checkout and review rules.
- Add focused tests for both root layouts, additions/deletions/renames, ignored
  files, authoring/build handoffs, feature-checkout publication, and failed or
  concurrent publication. Run the workflow's checks and packaging twin checks.

## Context

### Owner decision — 2026-10-07

The owner approved automatic publication of everything in the Coga directory
and configured contexts directory, replacing the old distinction between task
state and knowledge requiring a separate PR. The accepted tradeoff is that
changes to instructions in those roots publish directly too. Git remains the
visible history and correction mechanism. This is an explicit policy change,
not a request to work around the dirty-checkout guard.

The triggering incident is PR #973
(https://github.com/FastJVM/coga/pull/973): bootstrap/ticket wrote an owner
decision into docs/contexts/dev/dev-record and left it dirty on main. Those
particular edits landed in #972. #973 proposes a warning and a knowledge branch
procedure; under the new policy, revise that approach for files inside the
managed roots. A warning can remain useful for genuine edits outside them.
Do not merge or close either PR as part of ticket intake.

Start with `src/coga/git.py::sync_coga_state`, `_state_areas`,
`src/coga/authoring.py::finalize_authored`, and the checkout boundary in
`src/coga/commands/launch.py`. Keep one shared directory-membership definition
rather than expanding independent allowlists. Inspect callers of these helpers
and publication/recovery tests before changing them.

Read coga/internals/state-publication
(`docs/contexts/coga/internals/state-publication/SKILL.md`, Invariants,
end-of-command sweep, Guided authoring and review work), coga/sync
(`docs/contexts/coga/sync/SKILL.md`), and dev/checkouts
(`docs/contexts/dev/checkouts/SKILL.md`), cited rather than attached because
they are editing targets. Update these owners and their packaged twins in the
same implementation PR. Find and remove conflicting statements in authoring
skills, prompts, and related topics. Keep canonical/package byte-identity
requirements for shipped material; the packaged tree under src/ is outside
this policy and still needs a code PR when its content changes.

Related ticket publish-build-vision-before-handing-off-starter-ti retains the
onboarding/fresh-clone acceptance case. Its earlier prohibition on widening
the sweep is superseded by this owner decision; implement the shared policy
here and reuse it there rather than adding an onboarding-specific publisher.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/977
branch: publish-coga-roots

## Implementation

- Shared lexical root membership publishes eligible files under the configured
  Coga and contexts directories; nested roots are deduplicated. Ignored files
  stay local. In the root layout the workspace is the checkout itself.
- Dirty managed-root files publish from any checkout. Committed feature-branch
  knowledge stays with its reviewed PR; routine ticket/log/recurring commits
  retain their existing adoption behavior. Packaged source remains reviewed.
- Authoring publishes changed tasks and knowledge together, reloads config,
  requires authored knowledge to participate or already match control, and
  withholds its exit sweep on failure. Newly ignored regular files stay local.
- Checkout return reloads config and retains both context roots for a move.
  It captures the pre-phase root at admission/return, so ticket.py's early
  config reload cannot lose old-path deletions. Invalid config or a changed
  Git destination stops publication/return without discarding edits.
- Symlinks and linked ancestors cannot expand membership, redirect explicit
  pathspecs, supply working bytes, or pass checkout cleanup proof. Submodules
  refuse in HEAD, control, or the index. Owning contracts and twins match.
- Initial implementation: Claude (implement commit coauthor evidence).
  Review fixes: Codex. PRs #972 and #973 were not modified.

## Peer review

All native `codex review` runs **returned**. No review remains in flight, and
all reproduced findings have been fixed. The owner explicitly approved the
symlink fix in this continuation, following the earlier authoring/relocation
approvals. This resolves the prior pending-approval handoff.

Findings addressed across the returned reviews: symlinked authoring targets
and ancestors, dirty/staged/removed submodules, stale authoring/return config,
false publication claims for committed feature knowledge, an exit sweep
bypassing authoring refusal, external-root relocation, newly ignored files
misclassified as deletions, and config reloaded before script checkout return.

The latest `codex review --base origin/main` began at
`381d13ddfa23c8c71d05b76c24f974cfe31f4229`, base
`ab1b225e15891237ad1ade6dad58b2cbd562abaa`, and returned one P2 finding:
script-phase config reload lost the old contexts root. A test-fixture correction
and documentation cleanup landed while that review ran; its receipt is kept
historical, not restamped as a clean final-head review. The final fix at
`8412b5950b4a2bb37bb213e2f186a54cc42521e3` captures the root in the boundary,
is manually inspected, and passes real run_script_chain cases for ordinary and
recurring admission. Codex authored fixes and reviewed them; independence is
not claimed. Recommendation remains **deep** for the owner.

No raw-terminal, pager, TTY-prompt, or rendered-notification surface changed.
No Python 3.11 run was made. One newly added test initially assumed its fixture
already had a .gitignore; that setup error was corrected, its obsolete run was
stopped, and the full final run below is clean.

## Verification and handoff

Final head: `8412b5950b4a2bb37bb213e2f186a54cc42521e3`.
Diff base: `ab1b225e15891237ad1ade6dad58b2cbd562abaa`.
The branch was fetched/rebased unconditionally, committed and pushed; checkout
returned to clean main. No source changes arrived on control after final testing.

- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest`:
  **3457 passed in 273.82s**, including packaging twins.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_launch_script.py tests/test_git.py tests/test_launch.py tests/test_packaging.py -q`:
  **427 passed in 65.71s** on the final working tree subsequently committed.
- From `example/coga`,
  `env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json`:
  **0 issues**.
- `git diff --check origin/main...publish-coga-roots`: clean.

Peer-review work is complete. The structured PR preparation covers every final
diff path and preserves actual author/reviewer identities and receipt revisions.
The next step is the mechanical open-pr step after one bump from main.

## PR

```yaml
title: Publish all eligible files under configured Coga and context roots
author: claude/codex
author_evidence: Initial implementation commit credits Claude Opus 5.5; Codex peer-review sessions implemented
  the subsequent fixes, as recorded above.
head: 8412b5950b4a2bb37bb213e2f186a54cc42521e3
base: ab1b225e15891237ad1ade6dad58b2cbd562abaa
depth: deep
rationale: Deep owner review is warranted because this expands automatic publication to instructions and
  shared config. All reproduced findings are fixed; the latest native review predates the final script-boundary
  fix and is retained as a historical receipt.
implementation: Publish eligible files throughout configured Coga and context roots using shared membership
  across sweeps, authoring, checkout return, recovery, and unpublished-work detection. Authoring publishes
  tasks with knowledge, refuses incomplete handoffs, and withholds failed exit sweeps. Retain pre-phase
  context roots across script config reloads so relocation carries both sides. Refuse symlinked paths
  and submodules; keep ignored files local.
deviations: Committed feature-branch knowledge stays review-bound; dirty managed-root files publish directly.
  In the root layout, the workspace is the entire checkout. Retro deliberately retains its reviewed-PR
  policy.
limitations: No Python 3.11 run or independent final-head review. The latest native review returned before
  the final script-boundary fix; its finding was addressed and manually inspected by Codex. No raw-terminal,
  pager, or rendered-notification surface changed.
files:
  coga/skills/coga/ticket/finalize/SKILL.md: Describe joint guarded publication of authored tickets and
    knowledge, including failure retention.
  docs/contexts/coga/context-layout/SKILL.md: Align relocated-context publication and move instructions
    with the approved automatic publication boundary.
  docs/contexts/coga/internals/assist-publication/SKILL.md: Apply the configured roots consistently to
    assist checkout publication.
  docs/contexts/coga/internals/git-refresh/SKILL.md: Use root membership for recovery of already published
    state commits.
  docs/contexts/coga/internals/human-assist/SKILL.md: Align recorded assist dirt classification with publication
    roots.
  docs/contexts/coga/internals/state-publication/SKILL.md: Own the broader publication policy, committed-feature
    exception, guarded authoring requirements, symlink and submodule safeguards.
  docs/contexts/coga/launch/SKILL.md: Describe root-wide publication at the launch boundary.
  docs/contexts/coga/principles/SKILL.md: Record the approved visible Git correction policy without requiring
    every knowledge edit to use a PR.
  docs/contexts/coga/sync/SKILL.md: Document root-wide sweeps and the review boundary for committed feature
    changes.
  docs/contexts/dev/checkouts/SKILL.md: Align checkout entry, return, and recovery instructions; require
    config reload before return publication.
  src/coga/authoring.py: Discover eligible root files, reload authored config, publish tasks and knowledge
    together, and reject incomplete handoffs.
  src/coga/cli.py: Update sweep documentation to match root-wide eligibility.
  src/coga/commands/launch.py: Reload config and preserve the pre-phase contexts root across script reloads
    and successful returns; share root membership for assist alignment.
  src/coga/commands/ticket.py: Withhold the CLI exit sweep after finalization failure so refused knowledge
    cannot leave separately published task references.
  src/coga/git.py: Share lexical root membership across publication and recovery, reject symlinked ancestors
    and submodules, preserve committed-feature review work, and require authored paths to participate
    or already match control.
  src/coga/mark.py: Reuse shared root membership for unpublished product-work detection.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md: Keep the packaged
    twin byte-identical to docs/contexts/coga/context-layout/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/assist-publication/SKILL.md: Keep
    the packaged twin byte-identical to docs/contexts/coga/internals/assist-publication/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/git-refresh/SKILL.md: Keep the packaged
    twin byte-identical to docs/contexts/coga/internals/git-refresh/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/human-assist/SKILL.md: Keep the
    packaged twin byte-identical to docs/contexts/coga/internals/human-assist/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/state-publication/SKILL.md: Keep
    the packaged twin byte-identical to docs/contexts/coga/internals/state-publication/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: Keep the packaged twin byte-identical
    to docs/contexts/coga/launch/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/principles/SKILL.md: Keep the packaged twin
    byte-identical to docs/contexts/coga/principles/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md: Keep the packaged twin byte-identical
    to docs/contexts/coga/sync/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/contexts/dev/checkouts/SKILL.md: Keep the packaged twin
    byte-identical to docs/contexts/dev/checkouts/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/skills/coga/ticket/finalize/SKILL.md: Keep the packaged
    twin byte-identical to coga/skills/coga/ticket/finalize/SKILL.md.
  src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md: Scope reviewed knowledge
    PRs to Retro and require committing review-bound edits before sweeping commands.
  tests/test_authoring.py: Assert joint publication, changed-knowledge selection, and failure propagation.
  tests/test_git.py: Exercise both layouts, publication and return safeguards, concurrent failures, symlinks,
    submodules, and committed-feature authoring refusals.
  tests/test_launch_script.py: Exercise real script-chain relocation after the script runner reloads config,
    through ordinary and recurring checkout admission.
  tests/test_layout_contexts.py: Verify relocated authored contexts and product vision survive publication
    and fresh-clone composition.
review:
  reviewer: codex
  kind: self
  status: failed
  head: 381d13ddfa23c8c71d05b76c24f974cfe31f4229
  base: ab1b225e15891237ad1ade6dad58b2cbd562abaa
  detail: 'codex review --base origin/main returned one P2 finding: script-runner config reload lost the
    prior contexts root. Fixed at 8412b5950b4a2bb37bb213e2f186a54cc42521e3 and manually inspected by Codex;
    two real script-chain regression cases and the required suite verify the fix. The native run began
    at the recorded head; a test-fixture correction and documentation cleanup landed while it ran. This
    historical receipt is not restamped as a clean final-head review. Codex authored review fixes, so
    independence is not claimed.'
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest
  status: passed
  head: 8412b5950b4a2bb37bb213e2f186a54cc42521e3
  base: ab1b225e15891237ad1ade6dad58b2cbd562abaa
  detail: 3457 passed in 273.82s on Python 3.12.12, including packaging twin checks.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_launch_script.py tests/test_git.py
    tests/test_launch.py tests/test_packaging.py -q
  status: passed
  head: 8412b5950b4a2bb37bb213e2f186a54cc42521e3
  base: ab1b225e15891237ad1ade6dad58b2cbd562abaa
  detail: 427 passed in 65.71s on the exact working tree committed as this head; includes both script-chain
    relocation cases and packaging twins.
- command: 'cd example/coga

    env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python -m coga.cli
    validate --json'
  status: passed
  head: 8412b5950b4a2bb37bb213e2f186a54cc42521e3
  base: ab1b225e15891237ad1ade6dad58b2cbd562abaa
  detail: 0 issues; four valid fixtures.
- command: git diff --check origin/main...publish-coga-roots
  status: passed
  head: 8412b5950b4a2bb37bb213e2f186a54cc42521e3
  base: ab1b225e15891237ad1ade6dad58b2cbd562abaa
  detail: No whitespace errors.
```

## Blockers

- [x] [2026-10-07 17:22] [agent:codex] id=20261007T172201 Publish the newer local edits to move-coga-development-rules-out-of-the-shipped-bas, then return the shared checkout to clean main. Its untracked ticket differs from origin/main, so dev/checkouts forbids discarding it or switching over it. Peer review returned, all findings are fixed, 3374 tests pass, branch publish-coga-roots is pushed at 204d20400, and the PR body is recorded; only checkout return and bump to open-pr remain.
  resolved: [2026-10-07 17:24] [human:nicktoper] Owner confirmed the concurrent edits are fixed. Verified the remaining local ticket/log changes are already published, returned to clean main, and confirmed the remote feature branch is still 204d20400. Control has advanced only in task/log state; reviewed source and test changes are unchanged.
