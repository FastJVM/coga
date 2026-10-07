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
step: 1 (implement)
agent: claude
launch_generation: 727c5e15-28d5-4f06-9fe4-ccdfc2309f90
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
