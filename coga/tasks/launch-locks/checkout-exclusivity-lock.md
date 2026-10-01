---
title: Checkout exclusivity lock
status: draft
owner: nicktoper
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
step: 1 (design)
contexts:
  - coga/launch
  - dev/checkouts
  - coga/internals/launch-claims
  - coga/internals/agent-spawn
  - coga/internals/state-publication
---

## Description

Design an independent local lock that admits only one working Coga launch to a physical checkout at a time, regardless of ticket. User direction: an inspectable root-level gitignored lock file while an agent works there. Proposed path: .coga.lock; this is transient local runtime state and must never be published to Git or swept as task state.

Owner direction: checkout collisions are uncommon; prefer a simple lock file rather than a long-held OS advisory lock. Create it atomically (exclusive creation, not a separate existence check followed by a write) before any launch side effect, including log publication, state sweep, checkout preparation, script execution, and agent-skill regeneration. Hold through script/agent phases, chained steps, final publication, checkout return, and outer command cleanup. A losing launch names the holder and exits without a generic sweep mutating the occupied checkout. Include bootstrap/chat, ordinary tickets, recurring and megalaunch routes; specify delegation and nested child-command ownership without self-deadlock. Read-only commands remain available. Explicitly define interaction with other mutating Coga commands and limitations for manual Git/editor access.

Metadata should identify session, process and process start identity, machine, checkout, target and start time. File existence blocks a competing launch; metadata supports inspection and recovery, not proof of liveness by age alone. Remove only the owning session's file at normal teardown. After a crash the file remains: design a small explicit recovery procedure that establishes the old worker has stopped before removing/replacing it. Account for PID reuse, a surviving agent after supervisor death, partially written metadata, and races between recovery, release and acquisition. Prefer conservative refusal/manual recovery over a complex automatic liveness system. Resolve canonical checkout identity and symlink aliases. Define how the ignored path is installed in existing and new repos without treating an existing user file as disposable.

Lower priority than the ticket ownership lock: the owner identifies cross-checkout ticket collisions as the main problem. Orthogonal sibling: launch-locks/ticket-ownership-lock handles the same ticket across clones. This ticket only serializes one checkout; different checkouts remain independent and neither design depends on the other shipping. Use checkout-then-ticket acquisition order when combined. Keep the existing short-lived state_lock separate from the long-lived launch lock.

Design acceptance cases must cover two launches on the same/different tickets, chat plus task, symlinked paths, Ctrl-C, supervisor kill with a surviving child, scripts, nested delegation, preflight and teardown failures, and different clones. Update launch/checkouts/runtime contracts, the old bootstrap concurrency claims, and packaged twins in the eventual PR. Obtain owner approval of the design before implementation.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
