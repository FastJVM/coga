---
title: Publish all Coga and context files automatically
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
step: 2 (peer-review)
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

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: publish-coga-roots

## Plan (implement, 2026-10-07)

- One shared membership helper in `src/coga/git.py` (`coga_root_paths`):
  the Coga root plus the contexts root, nested roots deduplicated. Same set
  `mark.stranded_product_paths` already excludes; reuse it there.
- Sweep publishes those roots; checkout preparation/return and
  `_local_control_subsumed` classify by them; assist-checkout alignment too.
- Committed-path adoption from a non-control branch stays limited to
  routine ticket/log/recurring state, so a reviewed code PR's committed
  knowledge edits are not pushed to control ahead of review and their
  packaged twins. Dirty files anywhere in the roots publish.
- Authoring finalization publishes authored tasks plus changed root files in
  one publish; a failure keeps the edits and exits non-zero.

## Handoff (implement → peer-review)

Branch `publish-coga-roots` pushed (commit cb068c8a4, rebased on origin/main).

What changed:
- `src/coga/git.py`: new `coga_root_paths(cfg)`, the shared membership
  definition (Coga root + `Config.contexts_root`, nested roots listed once).
  `sync_coga_state` publishes it; `_state_areas` (prepare/return,
  `_local_control_subsumed`) is built from it. `mark.stranded_product_paths`
  and `launch._align_recorded_assist_checkout` now use it too.
- Decision: `_candidates` adopts *committed* paths from a non-control
  (feature/detached) HEAD only inside routine state (`_routine_state_areas`:
  tasks, recurring, log). Otherwise a witness-launch `coga bump` on a
  feature branch would push a code PR's committed `docs/contexts` edits to
  main ahead of review and ahead of their `src/` twins (breaking
  test_packaging on main). Dirty files anywhere in the roots publish from
  any checkout (the accepted tradeoff).
- Decision: an untracked symlink found under a directory pathspec is
  skipped, not refused. Without this, an `.agent-skills/` symlink view in a
  repo missing its ignore rule would make the guard refuse every sweep,
  stalling ticket state too. Explicitly named or tracked symlinks are still
  refused.
- Root layout (coga.toml at the checkout root): the Coga root is the whole
  checkout, as the existing mark-done guard already treated it. Reviewers
  may want to confirm this literal reading of the owner decision.
- `src/coga/authoring.py`: the snapshot covers the roots (Git `ls-files`,
  so ignored files are never hashed; filesystem fallback outside a
  checkout). Finalize publishes authored tasks + changed non-task files
  (log excluded) in one publish. A failure raises `AuthoringError`, so
  `coga ticket` exits 2 with edits kept. The "carry them through a PR"
  notice is gone; a success lists the published knowledge files.
  `exclude_support_paths` was removed.
- Docs + twins: state-publication (new "The Coga roots" section, rewritten
  authoring section), sync, dev/checkouts, context-layout, git-refresh,
  assist-publication, human-assist, launch, principles #4 (Forbids/Receipt
  reworded to the owner decision; please review), coga/ticket/finalize skill.

Tests: new or rewritten in tests/test_git.py (nested/root/relocated ×
feature × finalize covering add/modify/delete/rename, ignored
coga.local.toml and .agent-skills, unrelated src.py; overlap dedupe;
untracked symlink; committed knowledge on a feature branch stays for its
PR; hand-committed skill on control; stale context CAS refusal; authoring
refused over a concurrent context edit; prepare cleans a published
context/skill; prepare still refuses dirty source; realign over a
hand-committed context). tests/test_authoring.py was updated to the new
contract. tests/test_layout_contexts.py: a relocated context edit and a new
product/vision publish, and a fresh clone composes and validates them.
Full `python -m pytest`: 3338 passed. The only failures were the 26
test_ticket.py cases, from a subprocess stub hit by the new git call. Fixed
by skipping Git outside a checkout (`find_checkout_root`), then re-ran
test_git/layout/packaging/ticket/authoring/mark/cli: 353 passed.
`coga validate --json` on example/coga: 0 issues.

Not done / follow-ups:
- Retro/Dream still describe knowledge PRs (retro/done-ticket,
  coga/dream, current-direction). Left unchanged: retro deliberately
  proposes reviewable PRs. Risk: a sweeping `coga delete` inside a retro
  worktree with *uncommitted* knowledge edits would now publish them
  directly. Worth checking in review or a follow-up.
- `github_preflight.is_coga_state_path` (open-pr/branch-sweep drift
  carve-out, tasks+log only) is unchanged. That one is PR scope, not
  publication.
- Build onboarding's explicit failed-publication handoff stays with
  publish-build-vision-before-handing-off-starter-ti. With this change,
  bump's sweep and the launch boundary publish the vision.
- PRs #973/#972 untouched.


## Peer review

`codex review --base main` **returned** on 2026-10-07. Its sandboxed first
attempt could not initialize the app server; the approved unsandboxed retry
completed. It reproduced a symlink escaping authoring's roots and a dirty
submodule being mistaken for deletion, then confirmed those fixes during the
review. Its final P2 finding was stale configuration during context relocation.
All three findings are fixed in pushed commit `204d20400` on
`publish-coga-roots`:

- Authoring never follows symlinks into publication targets outside its roots.
- Publication refuses submodules identified in HEAD, control, or the index,
  including dirty, updated, removed, and newly staged gitlinks.
- Finalization reloads and validates configuration before file discovery and
  ticket validation, retaining the original snapshot so a context move's
  deletion, destination, and config land in one guarded publication. Invalid
  config preserves every edit and fails before publication.
- Principles now consistently describe visible Git publication. Retro's
  deliberate reviewed-PR policy is scoped to Retro, with an explicit warning
  to commit review-bound knowledge before running sweeping commands. Owning
  contracts and packaged twins were updated.

The configured root-layout interpretation is intentional: when the Coga root
is the checkout root, all eligible checkout files fall inside it. The narrow
committed-feature adoption exception protects reviewed code/topic/twin changes;
dirty managed-root files still publish from feature checkouts. No raw-terminal,
pager, TTY prompt, or rendered-notification surface changed in this diff.

Verification (Python 3.12.12):
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest` after all fixes:
  **3374 passed in 294.09s**, including packaging twin checks.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_git.py tests/test_authoring.py tests/test_ticket.py -q`:
  **217 passed**, including the relocation and invalid-config cases.
- Earlier focused Git/authoring/layout/packaging check: **218 passed** after
  symlink/submodule fixes.
- From `example/coga`:
  `env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json`:
  **0 issues**.
- `git diff --check`: clean. Ambient `python -m pytest` initially failed
  collection because that interpreter lacks `tomlkit`; all receipts above use
  the repository's dependency-complete venv. No Python 3.11 run was made.

The branch was fetched/rebased unconditionally and force-pushed with lease.
Later remote changes are routine ticket/log publications only. PRs #973/#972
were not modified.

## Checkout return resolved

The owner confirmed the concurrent edits were fixed. Verified the remaining
local ticket bytes match origin/main and all local audit lines are published;
restored only those proven copies and returned to clean main. The feature
branch and its remote both remain `204d20400`. Control advanced only in
`coga/tasks/` and `coga/log.md`; the reviewed source and tests are unchanged,
so the 3374-test receipt above remains applicable.

`coga unblock` recorded the answer and restored status to active. Lifecycle
requires a fresh `coga launch` to move active to in_progress before a bare
bump can advance; this continuation must not launch itself or edit lifecycle
frontmatter. Resume this ticket normally, confirm entry on clean main, and
bump once to open-pr. Peer review has returned, all findings are fixed, the
branch is pushed, and the PR body below is ready; no review remains in flight.

## Peer review continuation — 2026-10-07, not ready to advance

This section supersedes the earlier ready-to-bump handoff. The fresh launch
found material PR-publication changes on main, rebased, and reran native review.
Both new `codex review` runs **returned**; none is in flight.

- `codex review --base main` at head `65bdab663b932ab464f16a43dae37ae0c48a7f99`,
  base `356a9220965a0eb68615a10c4084d97067353b3c`, returned P1 stale return config
  and P2 falsely reported publication of committed feature knowledge.
- Owner approved both fixes in the attended session. `git.publish(require_paths=...)`
  now requires each authored support file to be selected or already match control;
  checkout return reloads config and refuses an invalid config/changed destination.
- `codex review --base origin/main` at head `263bd2c663036058aaa86601c7a7b629dd06bb43`,
  base `1533d528c374c1ac292f57d1a9ef9d4685a41066`, returned three findings:
  P1 symlinked ancestors escape authoring roots; P2 CLI exit sweep bypasses an
  authoring refusal; P2 relocation between external roots loses old deletions.
- The two P2 follow-through fixes are committed and pushed at
  `46da7290f0e3c6c7f4f4f80864273defac9360db`: ticket finalization failure withholds
  its invocation's exit sweep; checkout return carries the prior contexts root
  through the shared root helper for publication, preparation, and recovery.
  The owner already approved these handoff/relocation fixes.
- **Still open: P1 symlinked ancestors.** Reproducer: seed tracked
  `coga/skills/team/helper.py`, snapshot authoring, replace the `team` directory
  with a symlink to `src`, and edit `src/helper.py`. The old snapshot child
  appears deleted; `git.relative_to_root` resolves its parent link and publishes
  the dirty source outside the roots. Proposed fix: reject linked ancestors
  before explicit authoring publication and in the publication guard; add
  regression coverage for source inside/outside the checkout. The attending
  owner was asked for approval and has not answered yet. Do not infer approval
  from elapsed time. The session's substantive-change confirmation rule is the
  reason for waiting; do not block the ticket or bump while this remains open.

Validation: latest committed tree passed
`PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_git.py tests/test_authoring.py tests/test_ticket.py tests/test_launch.py tests/test_launch_script.py tests/test_packaging.py -q`
(**484 passed in 67.70s**), including 14 focused return/failure cases. Earlier
full run at the preceding revision reported **3435 passed**, but is historical
and does not cover the last follow-through changes. Run the full suite again
after all remaining fixes. No new terminal or rendering surface is involved.

Branch is committed/pushed; checkout returned to main. No workflow transition
was made. Finish the symlink fix after approval, verify/review the final diff,
refresh the structured PR record below, return clean main, then bump once.
Initial implementation was Claude (commit coauthor evidence); Codex implemented
review fixes. Codex reviews are conservatively labeled self-review of the mixed
Claude/Codex implementation, not independent review of Codex's own fixes.

## PR

```yaml
title: Publish all eligible files under configured Coga and context roots
author: claude/codex
author_evidence: Initial implementation commit credits Claude Opus 5.5; Codex peer-review sessions implemented
  the subsequent fixes, as recorded above.
head: 46da7290f0e3c6c7f4f4f80864273defac9360db
base: 1533d528c374c1ac292f57d1a9ef9d4685a41066
depth: deep
rationale: Significant expansion of automatic instruction/config publication; a reproduced symlink escape
  is still unresolved. Do not open or merge until it is fixed and final verification is recorded.
implementation: Use shared configured-root membership for state sweeps, authoring, checkout preparation/return,
  recovery, and unpublished-work warnings. Publish authored tickets and knowledge together, withhold failed-authoring
  exit sweeps, and retain both context roots during launch-return relocation.
deviations: Committed feature-branch knowledge stays review-bound; dirty managed-root files publish directly.
  In the root layout, the workspace is the entire checkout. Retro deliberately retains its reviewed-PR
  policy.
limitations: Unresolved symlinked-ancestor escape awaits owner approval to fix. Final full-suite and review
  receipts must be refreshed after remaining fixes. No Python 3.11 run; no interactive rendering surface
  changed.
files:
  coga/skills/coga/ticket/finalize/SKILL.md: Describe joint guarded publication of authored tickets and
    knowledge, including failure retention.
  docs/contexts/coga/context-layout/SKILL.md: Make relocated contexts part of the automatic publication
    boundary.
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
  src/coga/commands/launch.py: Reload and validate return configuration, retain the previous context root
    for relocation, and reuse root membership for assist alignment.
  src/coga/commands/ticket.py: Withhold the CLI exit sweep after finalization failure so refused knowledge
    cannot leave separately published task references.
  src/coga/git.py: Share root membership across publication and recovery, retain committed-feature review
    protection, refuse submodules, and require authored paths to participate or already match control.
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
  tests/test_layout_contexts.py: Verify relocated authored contexts and product vision survive publication
    and fresh-clone composition.
review:
  reviewer: codex
  kind: self
  status: failed
  head: 263bd2c663036058aaa86601c7a7b629dd06bb43
  base: 1533d528c374c1ac292f57d1a9ef9d4685a41066
  detail: codex review --base origin/main returned three findings. Two P2 findings are fixed in the current
    head; P1 symlinked ancestors still escape publication roots. Historical review, not verification of
    current head. Codex also authored fixes; independence is not claimed.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_git.py tests/test_authoring.py
    tests/test_ticket.py tests/test_launch.py tests/test_launch_script.py tests/test_packaging.py -q
  status: passed
  head: 46da7290f0e3c6c7f4f4f80864273defac9360db
  base: 1533d528c374c1ac292f57d1a9ef9d4685a41066
  detail: 484 passed in 67.70s on the exact working tree subsequently committed as this head.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest
  status: not-run
  detail: Final-head full run pending the remaining symlink fix; previous revision reported 3435 passed.
```

## Blockers

- [x] [2026-10-07 17:22] [agent:codex] id=20261007T172201 Publish the newer local edits to move-coga-development-rules-out-of-the-shipped-bas, then return the shared checkout to clean main. Its untracked ticket differs from origin/main, so dev/checkouts forbids discarding it or switching over it. Peer review returned, all findings are fixed, 3374 tests pass, branch publish-coga-roots is pushed at 204d20400, and the PR body is recorded; only checkout return and bump to open-pr remain.
  resolved: [2026-10-07 17:24] [human:nicktoper] Owner confirmed the concurrent edits are fixed. Verified the remaining local ticket/log changes are already published, returned to clean main, and confirmed the remote feature branch is still 204d20400. Control has advanced only in task/log state; reviewed source and test changes are unchanged.
