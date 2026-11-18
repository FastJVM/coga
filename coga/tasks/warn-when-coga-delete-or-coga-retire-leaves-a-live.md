---
title: Warn when coga delete or coga retire leaves a live link to the deleted ticket
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 1 (design)
agent: claude
launch_generation: e5df0aaa-62f9-428f-957d-16c7902f2ee8
---

## Description

Follow-up from `make-retro-check-inbound-doc-links-before-deleting`. That
ticket made Retro (`retro/done-ticket`) search tracked files for a source
task's path before deleting it, and repoint live-tree references
(`blob/<control-branch>/` URLs, relative Markdown links, bare paths) to a
commit permalink. Two delete paths still skip that check:

- **`coga retire` on a `done` ticket** deletes it deterministically, with no
  Retro run.
- **An ordinary human `coga delete <task>`** has the same gap.

Either one can break navigation on main. That already happened once: a README
link to the deleted `document-the-remedy-for-a-bloated-blackboard-sibli`
ticket broke and had to be fixed in PR #1214.

The design step must decide, with reasons:

1. **Where the check lives.** It can run inside the shared `run_delete_task`
   or only in the command-level callers (`commands/delete.delete` and the
   retire `ticket.py`'s `_delete_done_task`). Check the microkernel rule,
   because `run_delete_task` has more consumers than these two paths (see
   Context).
2. **Warn or refuse.** Choose between a warning or a refusal, and add an
   override flag if refusal is chosen.
3. **Whether `coga retire` repoints links itself.** It can rewrite the links
   to a permalink, or only warn and point the operator at the fix.

The design must also say how every other caller of `run_delete_task` is
treated: either unchanged or covered by the check (see the Code map in
Context). It must also say what the check does when Git is disabled or
unavailable.

Done means:

- `coga delete` and the done-ticket path of `coga retire` both detect tracked
  live-tree references to the task before deleting it, and warn or refuse as
  the approved design says.
- Tests cover a referenced and an unreferenced task on both paths. They also
  cover the false-positive cases the design decides on: an existing commit
  permalink, a longer slug that shares the prefix, a test-fixture path, and a
  short leaf collision.
- Unattended deletions do not become blocked. This covers recurring
  replacement, Dream/Retro deleting period tickets, and Retro's direct
  `coga delete`.
- The owning docs describe the new behavior in the same PR.

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

### Code map (cite by symbol; verify against current tree)

- `delete_task.run_delete_task(cfg, ref)` is the single implementation of
  task removal. It takes `git.state_lock`, removes the directory form or the
  file form, and returns a report line. It raises only `DeleteTaskError`. It
  does no Git publication: callers own that.
- Its consumers, all of which must keep working:
  - `commands/delete.delete`, the Typer head. It calls `run_delete_task` and
    then `git.publish` with `"Ticket: <id-slug> — deleted"`. The
    `--keep-control-checkout` flag is Retro's isolated direct delete.
  - `delete_task.run_delete_task_recipe`, the `coga run delete-task`
    registered recipe. It does a bare working-tree removal with no publish.
  - `coga retire`, which is an edge `ticket.py`. The done path is
    `_delete_done_task` in
    `src/coga/resources/templates/coga/bootstrap/retire/ticket.py`. It calls
    `run_delete_task` and then publishes `"Ticket: <id-slug> — deleted
    (retire)"`. `src/coga/resources/retire.md` is only the body of the
    canceled-ticket Retro task. Canceled retire goes through Retro, which
    already handles inbound references, so it is out of scope.
  - Recurring replacement in `recurring.py`. It deletes and recreates a
    period task **at the same path** and runs unattended. A reference check
    inside `run_delete_task` would fire on every replacement, either as noise
    or as a blocked recurring job. That is the main argument against putting
    the check in the shared function without a caller opt-in.
  - `recurring.promote_task` (`coga recurring promote`). It copies a task into
    a recurring template and then removes it **permanently**, so it is a third
    path that can break links. The design must decide whether it gets the
    check.
  - Dream's Retro deletes recurring period tickets with
    `coga delete recurring/<name>`, unattended. See
    `src/coga/resources/templates/coga/recurring/dream/ticket.md`, which
    describes the period-ticket deletion. `tasks/recurring/` paths already get
    many tracked hits, but those paths are recreated every period, so they are
    not broken links. A naive check in `coga delete` would fire on nearly every
    period delete, and a refusal there would block Dream.
  - `coga run delete-task` is also used by Dream's cleanup-orphan-markers
    task.
  - Retro calls `coga delete` for a no-durable-knowledge source only after
    its agent has judged that no inbound references exist. Otherwise it routes
    the source through a reference-pin PR. That judgment drops cases that a
    plain `git grep` will still match:
    - longer slugs that share the prefix
    - fixture paths
    - existing commit permalinks, which contain the path
    - excluded trees
    - links from other live tickets

    So a deterministic refusal **would** block Retro's direct delete. The
    design must pick one of:
    - apply the same filters Retro applies
    - add a caller opt-out flag that Retro's documented `coga delete` calls
      pass
    - warn only

### Search rule to reuse (copied from `retro/done-ticket`, section "Inbound references")

Package skill:
`src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md`.
Search tracked files for both the task path relative to the Git root and its
final slug component. The leaf search catches relative links such as
`../tasks/<leaf>.md`. Exclude the task root and the log:

```bash
git grep -n -F -e '<tasks-root>/<slug>' -e '<task-leaf>' -- . ':!<tasks-root>' ':!<coga-os>/log.md'
```

When reading the hits:

- Honor search restrictions (for example `':!docs/archive'`).
- A longer slug that shares the prefix is not a reference, and neither is the
  same relative path inside a test fixture.
- Existing commit permalinks are already safe.
- Links from other live tickets are out of scope.

A deterministic check cannot "inspect each hit" the way Retro's agent does.
The design has to choose the false-positive policy. One option is to report
the hits and leave the judgment to the operator.

If links are repointed, the target is a commit permalink of the control-branch
tip that still contains the task (full OID). Retro sends repoints through a
reviewable PR, because `coga delete` publishes only the task and the log. If
`coga retire` repoints, the design must say how those doc edits get reviewed or
published.

### Microkernel rule (cited, not attached: `coga-dev/microkernel`, `docs/contexts/coga-dev/microkernel/SKILL.md`)

Read "The kernel tier and its edges" and "Open command placements".

- Core code needs at least 2 real consumers, or a reviewed co-versioned
  contract.
- `delete` is a kernel head because it is a thin head over the fixed
  `delete-task` recipe.
- Logic with one consumer belongs at the edge, for example in the retire
  `ticket.py`.
- A shared helper (such as a "find live references to a path" function called
  by both `coga delete` and retire) passes the two-consumer bar. Placing that
  logic inside `run_delete_task` changes every consumer listed above.

### Git disabled or unavailable

`git grep` needs Git. The design must say what happens when Git is disabled in
config, when there is no repo root, or when `git` is missing. Retire's
`_cleanup_checkout` already soft-skips in these cases. For publication and
soft-skip semantics, see `coga/state-publication` (cited, not attached).

### Docs to update in the same PR

- `coga/cli`, for `delete` and `retire` behavior.
- `bootstrap/delete-task` skill contract, if recipe behavior changes.
- `coga/tickets/discovery`, which covers retired-task recovery.
- The `retro/done-ticket` "Inbound references" section, if the shared helper
  becomes the canonical search.

Follow `coga/knowledge`: one owner per fact.

### Out of scope

- Changing Retro's own repoint flow.
- Links from other live tickets.
- The canceled-ticket path of `coga retire`, which Retro already covers.
- If the design picks warn-only, `coga retire` repointing links itself can go
  to a follow-up ticket instead of this one.
- Rewriting history: existing broken links are already fixed (PR #1214).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
