---
slug: triage-the-v2-parking-area-empty-descriptions-prem
title: 'Triage the v2 parking area: empty descriptions, premise-dead drafts, permanently
  red validate'
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
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
secrets: null
step: 1 (implement)
---

## Description

The `coga/tasks/v2/` parking area needs a human triage pass. Dream 2026-08-24 found, mechanically:

- **18 of ~75 drafts have an empty `## Description`** — nothing between the heading and the next
  one. The v2 README's own premise check cannot be run on them.
- **A premise-dead cohort.** Confirmed dead: `audit-rules-md-usage-across-relay-and-decide-wheth`
  (`rules.md` no longer exists anywhere), `document-workflow-less-concept-capture-drafts-as-s`
  (architecture already documents it), `skill-update-aborts-on-uncommitted-log-file` (primary fix
  landed), `autotrigger-ticket-type` (every cross-reference dead), `split-context-to-doc-user-
  accessible-and-editable` (question answered by shipped precedent), plus `dev-loop-git-hygiene`,
  `relay-design-repositories`, and `add-relay-skill-search-with-candidate-eval` each settled the
  other way.
- **The known-stale-surfaces table is incomplete**: it omits `script:`, which 15 drafts in this very
  directory still carry, and its `relay-os/… -> coga/…` rename mapping sends readers to
  `workflows/code/*` paths that exist only inside the package.
- **`coga validate` is permanently red**, and every error in the repo comes from this directory. A
  green validate is not achievable, which quietly weakens the gate everywhere else.

Cancelling a premise-dead draft is a lifecycle change and human-only, which is why this is a ticket
and not a PR.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shards 06, 09, 11, 12), classified `gap`.

**Conflict to resolve first.** Phase 1 `validate-drift` proposes `unsynthesized-draft-blackboard`
synthesis PRs for four drafts, two of which — `autotrigger-ticket-type` and `split-context-to-doc`
— this scan independently found premise-dead. Do not synthesize a dead draft's authoring notes into
its body; decide cancel-vs-synthesize per draft here. The other two
(`measure-relay-prompt-scope-and-agent-precision`, `use-worktree-when-starting-a-dev-task`) keep the
synthesis route.

Standing pattern worth naming: the v2 README records that two drafts it cancelled as premise-dead
"were themselves Dream `gap` findings originally". Dream findings parked here decay. Whatever this
triage decides should also say where future `gap` findings go instead.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
