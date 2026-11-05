---
title: filter by user for megalaunch
status: draft
owner: nicktoper
workflow: code/with-review
---

## Description

`coga megalaunch --pick` lists every non-terminal ticket from every owner.
While we finish v1, the picker is cluttered with a teammate's tickets that I
will never launch. Add owner filtering to megalaunch:

- **`--pick` defaults to my tickets.** With no flag, the picker offers only
  tickets whose `owner:` equals `cfg.current_user`.
- **`--owner <name>`** filters to that owner's tickets instead, on both
  `--pick` and the bare sweep. For example, `coga megalaunch --owner zach`
  drains zach's launchable tickets while he is away.
- **`--all-owners`** restores today's every-owner picker list. On the sweep,
  it covers every owner. This flag cannot be combined with `--owner`.

The filter is on the ticket's `owner:` (the accountable human), not on who
holds the current step.

Done means the following, with tests and docs updated in the same PR:

- `coga megalaunch --pick` shows only my tickets.
- `--pick --owner zach` shows only zach's.
- `--pick --all-owners` shows everyone's.
- `coga megalaunch --owner zach` sweeps zach's tickets through the same
  launchability gates that the default sweep applies to mine.
- The default bare sweep behaves exactly as it does today.

## Context

### Current behaviour (as of this writing)

- **Bare sweep.** It already filters by owner. It silently ignores tickets
  whose `owner` is not `cfg.current_user` (owner-less tickets included). The
  check exists in two places: the queue scan, and the per-launch reread in
  `coga.megalaunch` (the `not explicit and ticket.owner != cfg.current_user`
  gate, which reports `skipped-human-gate`). The blocked-ticket and
  dependency-drain paths in the same module also compare against
  `cfg.current_user`.
- **Picker.** `megalaunch.launchable_candidates` builds the `--pick` list,
  and its docstring states "every non-terminal task of any owner". The
  command wiring is in `commands/megalaunch.py`
  (`megalaunch`, `_resolve_selection`).
- **Current user.** `cfg.current_user` comes from `user` in
  `coga.local.toml`.

### Design notes

- **Thread one target owner through the engine.** Do not keep
  `cfg.current_user` hard-coded at each gate. Every sweep gate (queue scan,
  launch-time reread, blocked/ask paths, dependency drain) must compare
  against the same chosen owner, so that `--owner zach` cannot queue a ticket
  that the reread then rejects. Notifications and the run summary should
  still name the operator correctly. The operator is the person running
  megalaunch (`current_user`), even when the tickets belong to someone else.
- **Explicit selections stay explicit.** A confirmed pick is a filter over
  what the human checked. The owner flags only shape the list offered. A
  saved `--relaunch` selection replays as-is, so reject `--owner` or
  `--all-owners` combined with `--relaunch` as ambiguous, the same way
  `_resolve_selection` already rejects `--relaunch` with `--pick` or a
  directory.
- **Why `--all-owners` and not `--owner all`:** it cannot collide with a
  real coga user named `all`.
- **Unknown owner.** An `--owner` value that matches no ticket should give an
  empty picker or sweep with a clear message, not an error. Owners are free
  strings on tickets, and there is no user registry to validate against.

### Docs to update in the same PR (edit these, not attached)

- `src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md`:
  the "Bare sweep" and "Explicit selection" sections, and the frontmatter
  description ("owner-scoped sweep"). Mirror any legacy live copy as
  required by `tests/test_packaging.py`.
- Check `coga/cli` (`.../contexts/coga/cli/SKILL.md`) for a flag listing
  that needs the new options.
- Update the `--pick` help text in `commands/megalaunch.py`, which currently
  says "any owner".

### Tests

Picker candidate filtering covers default, `--owner`, and `--all-owners`.
The sweep with `--owner <other>` launches that owner's ticket and still
skips other owners at the reread. Flag conflicts to test: `--owner` with
`--all-owners`, and either flag with `--relaunch`. Existing megalaunch tests
live in `tests/test_megalaunch.py`.

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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

**Clarity and "done."** The ticket is clear enough to start work. The five "Done means" bullets are behaviours a reviewer can check, and the Tests section names concrete cases. One gap: it doesn't say whether `--owner` or `--all-owners` on the bare sweep also changes the dependency drain. The design notes suggest yes, but a done bullet should say so.

**Workflow.** `code/with-review` fits. This is a CLI and engine change with a docs twin, and it ends in a PR.

**Contexts.** Leaving them unattached is defensible, since the implementer has to read `coga/megalaunch` closely anyway. Two additions would help:
- Name the legacy live copy explicitly. `docs/contexts/coga/megalaunch/SKILL.md` is pinned in `tests/legacy_removal_inventory.txt`, so it must be mirrored.
- Drop or soften the `coga/cli` pointer. That topic has only a table row pointing at `coga/megalaunch`; flags are documented by `--help`, not in a flag list.
- Optionally attach `coga-dev/testing`.

**Scope.** Reasonable as one PR. No split needed.

**Gate claims: accurate, with gaps.** I found four owner gates in `coga.megalaunch`:
- the queue scan (`:360`)
- the launch reread (`:1250`, the `not explicit and …` gate)
- the drain scan (`:457`)
- the drain's dependency-activation reread (`:525`)

The last two are both inside `_drain_satisfied_blockers`. The ticket's "blocked/ask paths" are those same two drain gates; there isn't a separate ask path. The ticket also misses these:
- **Stale docstrings.** "any owner" text at `megalaunch.py:13`, `:229` and `:1003`, plus the command module docstring at `commands/megalaunch.py:9`, all need updating, not just the `--pick` help at `:67`.
- **Report message.** The reread message says "is not current operator {current_user}". Under `--owner` it should name the target owner.
- **Re-block notifications.** The re-block path (`:1966-1984`) correctly uses `current_user` as the operator and the ticket owner as the one who must answer. Keep it that way; no change is needed there.

**Is sweeping another owner's tickets safe? Raise this before launch.**
- **Claims.** Megalaunch replaces an earlier plain `launch_generation` claim on `in_progress` tickets "without checking whether that session still runs" (`:2066`; SKILL.md "Bare sweep"). So `--owner zach` can take over a session zach left running on another machine. Pending and released claims are still refused. The ticket should state whether that is acceptable, or exclude `in_progress` work under `--owner`.
- **Dependency drain.** The drain auto-answers zach's open asks and relaunches them. That is the operator answering another person's blocker. It should be an explicit decision, not inherited silently.
- **Notifications.** Lifecycle posts (start, block, done) notify zach for work he didn't start. Log lines record actor `megalaunch`, not the operator.
- **Default change.** Making `--pick` mine-only also changes the `pick` alias. Check for tests that assume every owner appears.

**Prompt size.** Task_context is 43%, just over the ~40% line. Most of it is the required field-guide comment, so trim only the prose. The "Current behaviour" section can drop the line references and the `cfg.current_user` source note to save about 100 tokens. No other layer is near the limit.
