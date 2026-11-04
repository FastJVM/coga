---
title: Guard foreign linked worktree branch cleanup
status: active
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
    skills:
    - code/peer-review
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
---

## Description

Foreign worktrees, meaning a recorded `worktree:` that is not a linked
worktree of this repository, are not a supported layout outside recurring. A
stray one must never cause branch deletion in the clone that is running the
cleanup. Today it can. For a recorded worktree that exists and belongs to
another repository, `checkout_disposal.dispose_checkout` refuses the worktree
removal. It still calls `branchcleanup.delete_branch(cfg, root, branch, ...)`
against the invoking clone. `delete_branch` has no ownership guard, so a
same-named local branch there can be deleted, with `-d`/`-D` plus the leased
remote delete. Found on PR #939. Both autoclose paths reach it, because
`autoclose._owner_held_branch` returns `None` while the directory exists. So
does `coga retire`, through `_cleanup_checkout` in the bundled
`bootstrap/retire/ticket.py`. Retire also has the same hole for a *foreign
primary* checkout, such as a sandbox clone.

Fix, as defense in depth with no new reporting machinery:

- In `dispose_checkout`, after the claim scan, check the recorded worktree. If
  its directory exists and it is not this repository's linked worktree, skip
  all branch cleanup in this clone and add one note saying why. "Not this
  repository's linked worktree" means `"foreign-linked"`, `"foreign-primary"`,
  or `None` from `git.classify_checkout`.
- Leave the worktree in place, as today.

Done means:

- Under autoclose and `coga retire`, a recorded foreign linked worktree, and a
  foreign primary under retire, leave a same-named local branch in the
  invoking clone untouched.
- A regression test fails on current `main` and passes with the fix.
- Tickets whose worktree is already gone keep their normal branch cleanup.
- `coga/checkout-cleanup` is updated in both copies.
- `python -m pytest` passes.

## Context

### Guard rules

- Classify only when the recorded worktree is set *and* its directory exists.
  `git.classify_checkout` also returns `None` for a missing path. Treating
  that as foreign would break the ordinary `already_gone` path, which is the
  common case. `retire_worklist._recorded_relation` already resolves the path
  and checks that it is a directory, so reuse it or mirror it.
- `"primary"` is this repository's own primary checkout. Its branch is judged
  here as today, so the guard must not catch it.
- `_sweep_owned_branches` runs only when `disposal.worktree_gone`, so a
  surviving foreign worktree never reaches it. No test is needed for that
  path.

### Don't change the autoclose remedy

- Do **not** set `CheckoutOutcome.branch_owner` for these entries. Its arm in
  `manual_command` comes before the foreign-linked arm and would emit
  `git -C <owner> branch -d`.
- That would break `test_cross_repo_worktree_names_its_owning_checkout` in
  `tests/test_autoclose_dispose.py`, which asserts there is no such text.
- The existing foreign-linked remedy stays as it is.

### Tests

- Autoclose: in `tests/test_autoclose_dispose.py`, use the
  `_other_repo_worktree` fixture and add a same-named branch in
  `git_repo.root`. Follow the shape of
  `test_another_clones_primary_is_preserved_and_discharged_without_reposting`,
  which asserts that a same-named branch "must never be touched".
- Retire: add a test in `tests/test_retire.py`, since retire calls
  `dispose_checkout` directly. A fix inside `_owner_held_branch` alone would
  pass the autoclose test and leave retire broken.

### Docs (cited, not attached, because this ticket edits them)

- In `docs/contexts/coga/checkout-cleanup/SKILL.md`, section "Primary checkouts
  and other clones", the doc currently states the bug as intended: "an
  existing foreign *linked* worktree is the exception, whose recorded branch
  is judged in the sweeping clone."
- Rewrite that passage so it says foreign checkouts never have their branch
  judged in the invoking clone, for autoclose *and* `coga retire`, and that
  foreign worktrees are expected only for recurring.
- Keep the packaged twin
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/SKILL.md`
  byte-identical; `tests/test_packaging.py` enforces it.
- Fix the module docstrings in `autoclose.py` and `retire_worklist.py` if they
  restate the old rule.
- The recurring exception needs no special handling in this guard.

### Out of scope

- Removing foreign worktree directories.
- Deleting anything in the owning repository.
- New remedies or owner-reporting for these stray records.
- Changing `classify_checkout`.

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

Previous ref: `guard-foreign-linked-worktree-branch-cleanup` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
