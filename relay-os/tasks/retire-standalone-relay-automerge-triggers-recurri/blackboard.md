The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: retire-standalone-automerge-triggers
pr: https://github.com/FastJVM/relay/pull/414

Implemented directly on the primary checkout (no worktree). Peer review
(independent agent) came back clean — zero must-fix findings. Full suite
829 passed / 1 skipped; `relay validate --json` clean (5 pre-existing
unrelated `missing-step` errors).

Open question for owner review: `_remove_post_merge_hook` migration was
**kept** (only messaging updated), not dropped — it still prunes stale
hooks off old installs. See PR description.
