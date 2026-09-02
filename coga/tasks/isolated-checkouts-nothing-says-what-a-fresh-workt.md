---
slug: isolated-checkouts-nothing-says-what-a-fresh-workt
title: 'Isolated checkouts: nothing says what a fresh worktree lacks'
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
secrets: null
step: 1 (implement)
---

## Description

Record, in the contexts agents actually read, what a fresh linked worktree or
`/tmp` clone does **not** have — so that creating one stops being a trial-and-error
step that fails on the first mutating command.

Two related gaps, found by Dream 2026-W36 Phase 2 (shards `ks-01` and `ks-04`) from
five independent tickets.

**a. The `coga.local.toml` step is missing from both documents that tell an agent to
create a checkout.** `coga/contexts/dev/code/SKILL.md` ("Checkout boundary") and
`coga/skills/code/implement/SKILL.md` (step 3 and the `/tmp` fallback) each instruct
the agent to create a linked worktree or an independent `git clone --no-hardlinks`.
Neither mentions that `coga/coga.local.toml` is gitignored and therefore absent in
the new checkout, so the next mutating Coga command fails with exit 2 before doing
anything.

**b. Nothing states what else a fresh worktree lacks**, so every design in the
"run recurring from somewhere other than the operator's checkout" family re-derives
the same facts.

Deliverable: a short subsection under `dev/code`'s "Checkout boundary" (mirrored to
the packaged copy and to `code/implement`) giving the config-copy rule the three
existing precedents already follow — ordinary-copy the primary checkout's
`coga.local.toml` to the same repo-relative path, mode 0600, never symlink, stage or
commit it, and remove it with a disposable checkout — plus a "what a linked worktree
does not have" block in `coga/contexts/coga/codebase/SKILL.md`'s existing
`### Which checkout you invoke coga from` section.

Deciding *where* each half lands, and whether the codebase block belongs there or in
`dev/code`, is the design judgment this ticket exists for.

## Context

Citations name symbols and files, not line numbers.

**Evidence for (a).** Two tickets hit it as a live dead end:

- `coga/tasks/v2/auto-persist-dirty-launch-worktrees-to-pushed-bran.md` records in
  its blackboard that "task-scoped validation, `coga bump ...`, and `coga block ...`
  all failed before running because this launch checkout has no
  `coga/coga.local.toml` user configured".
- `coga/tasks/v2/propagate-local-coga-config-into-worktrees.md` names the same defect
  and lists three places that already work around it ad hoc: the live and packaged
  `recurring/dream/ticket.md`, the packaged `skills/retro/done-ticket/SKILL.md`, and
  `src/coga/resources/retire.md` — each of which requires an ordinary copy.

Grep confirms no context under `coga/contexts/` outside `secrets`, `codebase`, `sync`,
`architecture` and `recurring` mentions `coga.local.toml` at all, and neither of the
two checkout-creating documents does.

`v2/propagate-local-coga-config-into-worktrees` covers the **command-side**
enforcement (making Coga propagate the config itself). This ticket is the missing
**written convention** agents read today; the two are complements, and whoever picks
this up should check whether the other has landed first.

**Evidence for (b).** Three tickets re-derive the same worktree facts:

- `coga/tasks/service-recurring-from-a-temp-control-worktree-ins.md` records under its
  design notes that `coga.local.toml` is gitignored so any fresh worktree has no
  `user` and `load_config` raises before the scan starts — "seeding the copy is not a
  nicety, the feature does not run without it".
- `coga/tasks/reuse-the-existing-control-worktree-for-recurring.md` filed the identical
  fact later as `### Blocker found: the relayed child cannot load machine-local
  config`, verified against this repo's own linked worktrees (none carries the file),
  and had to escalate to the human for a resolution (a `COGA_LOCAL_CONFIG` env
  handoff).
- `coga/tasks/run-recurring-agent-templates-off-the-control-bran.md` restates it a
  third time under `### Worktree hygiene facts`, extends it to `.coga/` and
  `.agent-skills/`, and explicitly voids the second ticket's reasoning about
  `.agent-skills/` not being needed.

Two further facts are re-derived across the same tickets with no home:

- git refuses to check one branch out twice — simultaneously the concurrency lock in
  the temp-worktree design and the reason a create-only design cannot serve the layout
  Coga recommends;
- `git.sync_log` plus `_sync_recurring_create_paths` refuse to publish from a detached
  HEAD, which is what forces a worktree to have control checked *out* rather than
  `--detach`.

Which gitignored paths self-heal matters: `.agent-skills/` is rebuilt by launch, while
`coga.local.toml`'s absence hard-errors `load_config(require_user=True)`.

`coga/contexts/coga/codebase/SKILL.md`'s `### Which checkout you invoke coga from`
section already covers the inverse hazards (a feature worktree sweeping `coga/` edits
onto control; launch composing from the invoking checkout) but says nothing about what
a fresh or linked worktree is *missing*.

Candidate contexts to attach at design time: `coga/codebase`, `dev/code`. Both are
large; copy the needed facts rather than attaching wholesale if prompt size matters.

Filed by Dream 2026-W36, Phase 2 knowledge scan (shards `ks-01`, `ks-04`), classified
`gap`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
