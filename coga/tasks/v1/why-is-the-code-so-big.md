---
title: 'Simplify branchsweep (pilot: cut Coga''s code size)'
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
launch_generation: pending:2749fd20-a1a4-46b4-951b-4423d98023c9
---

## Description

The owner's hypothesis is that most of Coga's ~60k lines in `src/coga/` serve
no real purpose. Modules look far more complex than the job they do; `git.py`
and `launch.py` are typical examples. This ticket is the **pilot** of a
module-by-module simplification. It codesigns `src/coga/branchsweep.py` with
the owner, then implements the simplification.

`branchsweep`'s essential job is small. For each branch, it checks whether the
PR merged or is still active and deletes the branch once it has landed. The
module is ~1,730 lines, carries a 75-line docstring, and imports 16 other
Coga modules. Most of that is incident-driven edge-case handling.

The design must:

1. State the module's essential job in one sentence.
2. List every mechanism and edge case it carries. Give each one a verdict with
   a reason:
   - **cut**: not worth keeping.
   - **fix at the source**: the incident came from elsewhere, often a state
     Coga itself produced. Fix it there and the sweep no longer needs to
     handle it.
   - **lift a level**: stop handling it in code. Fail loud and leave the
     judgment to the agent or human, guided by text.
   - **keep**: only if it is truly mechanical and earns its lines.
3. Give a target size, then implement it.

The design step is an attended codesign. The agent proposes verdicts, and the
owner settles them live in that session before the bump. Open questions do not
wait for `review-design`.

Done means a merged PR that brings `branchsweep.py` to the agreed target size,
or records on the blackboard why it could not. Every cut, moved, or kept
mechanism must trace to a verdict in the design. Mechanisms that guard
against data loss need an explicit verdict and reason. These include the
`retired/` archive tag before delete and the closed-unmerged authorization. The topics that describe the removed behavior must be updated in the
same PR. A short "method notes" section on the blackboard records what the
pilot taught for the next modules.



## Context

### Why simplify, and how to judge each case

- **The current code is too complex.** Edge cases that once caused incidents
  should be re-examined, not preserved by default. A defensive branch that
  encodes judgment works against `coga-dev/principles`
  (`docs/contexts/coga-dev/principles/SKILL.md`, cited, not attached).
  Three principles apply: "Text above code", "Amplify agents, don't
  duplicate them", and "Keep everything at human scale". "Fail loud" replaces
  silent defensive handling.
- **The design step is a codesign.** Run it attended, with the owner. Propose
  verdicts and let the owner decide; do not settle the cut list alone.
- **Tests are out of scope as a target** (~100k lines). Tests shrink with the
  code they cover. Delete tests for removed behavior rather than porting them.

### What `branchsweep.py` carries today (as of 2026-11-17)

The module docstring lists the mechanisms the design must give verdicts on:

- merged-PR lookup by head branch name, with a "no open PR" condition;
- the `merged_pr_verdict` patch-id and "only Coga state paths" analysis for
  refs that walked past, lag, or were rebased from the merged head;
- broad "any mention pins" matching against live ticket text, plus a recurring
  period-task exception;
- closed-unmerged PRs authorized through terminal-ticket ownership
  (`_terminal_owners`, `_closed_pr_claim`, `retire_worklist`);
- `retired/<branch>` archive tags with an `@<sha12>` fallback;
- worktree pinning and removal under `[git].worktrees_ticket_owned`;
- protection of the skill-update branch;
- the release-local-draft path (`--publish-and-release-local`);
- report rendering onto the period task's blackboard.

Coupling, which the design must take into account:

- The deletion plumbing is shared with `branchcleanup.py` (~1,175 lines), which
  retire also uses.
- `autoclose.py` (~1,842 lines) is imported by the sweep and also references
  it.
- `checkout_disposal.py` and `retire_worklist.py` are coupled to the sweep.
- `config.py` and `skill_manager.py` reference it.
- `runner.RECIPES["branch-sweep"]` calls `run_branch_sweep_recipe`.

The design decides how far the pilot reaches into these modules. Record that
boundary explicitly.

The sweep runs unattended as a recurring job. A "fail loud" verdict must say
where the failure surfaces: the period task's blackboard report or a
notification. One problem branch must not stop the sweep of the others.

### Topics to update in the same PR

These describe current sweep behavior. Edit them (do not attach them) when
behavior changes:

- `src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md`
- `.../coga/checkout-cleanup/terminal-owners/SKILL.md`
- `.../coga/checkout-cleanup/SKILL.md`
- the `branch-sweep/sweep` workflow and the `coga/branch-sweep/sweep` skill
  under the package `bootstrap/`
- the recurring job `src/coga/resources/templates/coga/recurring/branch-sweep/`
  (`ticket.md`, `ticket.py`)
- `tests/test_branchsweep.py` (~3k lines) and the sweep cases in
  `tests/test_recurring.py`: delete the tests for removed behavior

### Coordination with `v1/microkernel`

`v1/microkernel/04e-second-pass-move-branch-sweep-and-autofix-repl` (parked)
plans to move the branch-sweep recipe to the edge. Simplify first, so 04e
moves the smaller module. Moving ~1,700 lines only to cut most of them later
is wasted work. Leave a note on 04e's blackboard pointing here.

### After the pilot

Creating the sibling tickets is a follow-up, not part of this ticket's done.
Once the pilot lands, the owner creates them, carrying the method notes. Candidates, by size: `recurring_runner.py` (~5.7k lines),
`launch.py` (~4.6k), `git.py` (~3.8k), `recurring.py` (~2.8k),
`megalaunch.py` (~2.4k), `skill_manager.py` (~2.1k), `validate.py` (~2.1k),
`config.py` (~2.0k), `commands/init.py` (~2.0k), `autoclose.py` (~1.8k).

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
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
