The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev update run — 2026-06-06

- Parent recurring: `relay-os/recurring/relay-dev-update/`.
- last_commit from parent blackboard: `2866e19`.
- New HEAD: `a1808f8` (origin/main). Range `2866e19..a1808f8` = 14 commits.
- Composition: mostly automated ticket-lifecycle commits from debug runs
  (digest-dbg-*, dream-dbg-*) plus the bucket-comparison-document task.
- Real content changes:
  - `9abe0be` Deactivate `dream` recurring template (dream/ -> _dream/).
    Bundled a new `marketing/positioning/SKILL.md` (+129) and a
    product-launch-comms ticket / relay-additions-spec edits.
  - `bucket-comparison-document` task created and taken to step 2 (draft)
    (3f71620, 93e19ff, 4521c00).
- No `src/relay/` code changes in this range.

Plan: post one-line digest to Slack, overwrite parent's Dev Update State
with new high-water mark, then `relay mark done`.
