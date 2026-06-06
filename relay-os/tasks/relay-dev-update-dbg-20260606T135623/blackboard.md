The blackboard is a notepad to be written to often as the human and agent works through a task.

### Run notes — relay-dev-update-dbg-20260606T135623

- Parent blackboard last_commit: a3f250f (range a3f250f..a3f250f recorded "yes" last run).
- This run: `git log a3f250f..origin/main` = **52 commits**, origin/main HEAD = 2866e19.
- This is a [debug] run. Posting to Slack + overwriting parent high-water mark would
  affect the REAL recurring task (next real run reads last_commit from the same parent
  blackboard). Asking human whether to post for real or dry-run before Step 4/5.

### Draft digest

Relay dev pulse — 52 commits since last update.

Workflow engine hardening: script-mode steps now advance the workflow on success
(#306); fixed the session-done sentinel leaking so an agent stops responding to a
present human (#290); same-branch git sync is now resilient to a moved
origin/<control> (#291).

Competition research landed: 8 competitor reports added — Backlog (#293), Conductor
(#294), Cursor (#295), Dust (#296), Linear Agent (#297), OpenClaw (#298), Paperclip
(#299), Superset (#300).

Docs & positioning: Relay Additions doc export + spec (#301, #304), Relay Paperclip
positioning docs (#289), bucket-comparison doc (#305), doc-create-workflow shipped
(#303), and the create-google-doc workflow now has the human convert HTML with
sign-off folded into revise (#292).

Plus recurring scaffolds (digest / dev-update) and new tickets queued
(product-launch-comms, add-subproject, relay-additions-spec).
