---
title: Publish build vision before handing off starter tickets
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
launch_generation: pending:bfd85d8a-0195-4e7b-aa8d-b23c730a33ec
---

## Description

The build onboarding must not hand over `coga launch <slug>` for its starter tickets until the agreed `product/vision` is confirmed on the published branch. Today `build/onboarding.md` presents the batch and launch command in chat and only then runs `coga bump`, whose end-of-command sweep is what publishes the vision. A fresh clone taken in between, or after a failed push, gets tickets whose `product/vision` context is missing (reported: `broken-context` from validate, launch exit 2).

Fix: onboarding explicitly publishes the vision (and the generated tickets) before the launch handoff, using the shared publication path #977 shipped, and only presents the batch as launchable once that publication succeeded. If publication fails, the files stay on disk, the step does not bump, and the agent tells the human in chat that the handoff is unfinished (naming the failure and how to retry) and records the same on the onboarding ticket's blackboard — it never presents launch commands as ready.

Done when an automated test runs onboarding's publish-then-handoff path from an empty repository and shows: the vision and starter tickets are on the published branch; a fresh clone resolves every generated ticket's contexts and `coga validate` passes; the same holds with a relocated `[layout] contexts` root; and a forced publication failure leaves recoverable files, no bump, and the explicit unfinished-handoff record. Live and packaged `build/onboarding.md` stay byte-identical.

## Context

### Background

Reported 2026-10-07 by another AI on the downstream thinkpick repo: six generated tickets referenced `product/vision`, which was not tracked in Git. That report was never independently reproduced; reproducing it is optional — the revision may be unobtainable — and the ordering gap above is confirmed by reading the current template.

### Already shipped — reuse, do not redo

PR #977 (sibling ticket `publish-all-coga-and-context-files-automatically`, merged 2026-10-08) made `git.sync_coga_state` publish everything under `git.coga_root_paths` — the Coga root plus the contexts root, including a relocated or previous one — via `git.publish`. `tests/test_layout_contexts.py` already asserts a relocated `product/vision` is tracked after publication and composes in a fresh clone. That sibling owns the publication policy; this ticket owns only the onboarding ordering, the failure handoff, and the end-to-end onboarding test.

### Design notes and constraints

- The owner chose an explicit publish before the handoff over merely reordering bump-then-handoff, so onboarding can detect and report failure. There is no `coga sync`/publish CLI today, so this likely needs a callable entry point. Respect the microkernel rule (`coga/extension-model`): prefer reusing an existing command or a registered `coga run` recipe with a stable argv/stdout/exit contract over a new core command, and justify any core placement.
- `coga/workflows/build/onboarding.md` and `src/coga/resources/templates/coga/workflows/build/onboarding.md` are twins (enforced by `tests/test_packaging.py`); edit both.
- Cited, not attached, because they are editing or reference targets: `coga/internals/state-publication` (`docs/contexts/coga/internals/state-publication/SKILL.md` — end-of-command sweep and guided authoring sections), `coga/sync` (`docs/contexts/coga/sync/SKILL.md`), and `dev/checkouts` (`docs/contexts/dev/checkouts/SKILL.md`), all touched by #977. `coga/init` (`docs/contexts/coga/init/SKILL.md`) covers seeding the onboarding ticket only; update it if the handoff contract it describes changes.
- The old done ticket remove-coga-build-and-project is historical: current source includes build onboarding.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
