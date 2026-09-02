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

**The contract for this directory is `coga/tasks/v2/README.md`.** Read it first. It defines the
two-question premise check, carries the known-stale-surfaces table this ticket amends, and records
the `decide-the-fate-of-two-premise-dead-v2-drafts-whos` precedent for cancelling a parked draft
with a recorded reason. Cancel spelling is `coga mark canceled v2/<slug> --message "<reason>"`.

**Conflict to resolve first.** Phase 1 `validate-drift` proposes `unsynthesized-draft-blackboard`
synthesis PRs for four drafts, two of which — `autotrigger-ticket-type` and `split-context-to-doc`
— this scan independently found premise-dead. Do not synthesize a dead draft's authoring notes into
its body; decide cancel-vs-synthesize per draft here. The other two
(`measure-relay-prompt-scope-and-agent-precision`, `use-worktree-when-starting-a-dev-task`) keep the
synthesis route.

Standing pattern worth naming: the v2 README records that two drafts it cancelled as premise-dead
"were themselves Dream `gap` findings originally". Dream findings parked here decay. Whatever this
triage decides should also say where future `gap` findings go instead.

### Verified against `main` on 2026-09-02

All four Description claims re-checked and still exact:

- 18 of 76 v2 drafts have an empty `## Description`.
- 15 drafts carry `script:`, all of them `script: null`. This is a *different* dead surface from the
  `mode: script` row the table already has — `script:` is ticket frontmatter, and core has no reader
  for it anywhere. It needs its own row.
- The table's `relay-os/… -> coga/…` row misleads for workflow refs: `coga/workflows/code/` does not
  exist in the repo. The `code/*` workflows resolve only from
  `src/coga/resources/templates/coga/bootstrap/workflows/code/`.
- `coga validate` reports exactly 4 errors, all `unsynthesized-draft-blackboard`, all under `v2/`.

**Green validate is achievable.** That rule fires only on `status == "draft"`
(`src/coga/validate.py:447`), so cancelling the two premise-dead drafts and synthesizing the other
two clears all four errors. Everything else in `coga validate` output is a WARN, not an ERROR.

### Human gate placement — known and accepted

This ticket runs `code/with-review`, whose only human gate is the final `review` step, after the PR
is open. That was a deliberate choice by the owner, not an oversight. The consequence: the file
edits (empty descriptions, README table, the two blackboard syntheses) land in a branch and are
reviewable as a diff, but the eight `coga mark canceled` calls are lifecycle writes to
`coga/log.md` with Slack notifications — they are not part of any diff and are awkward to reverse.

So, in the `implement` step: do the file edits in the branch, but **do not fire the cancels
unreviewed**. Present the per-draft verdict (slug, dead-or-alive, the evidence) and get explicit
human confirmation first — the session is attended, so ask. If for any reason no human is reachable,
leave the cancels undone, land the mechanical half, and hand the verdict table to the `review` step
rather than guessing.

### Out of scope

Re-validating the premise of all 76 drafts. This ticket triages the cohort the Dream scan already
named plus the 18 empty descriptions; the rest of the parking area stays as-is.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
