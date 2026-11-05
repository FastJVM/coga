---
title: filter by user for megalaunch
status: in_progress
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
step: 2 (peer-review)
agent: claude
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
  launchability gates that the default sweep applies to mine, including
  the dependency drain of zach's blocked tickets.
- `--owner` with `--all-owners`, and either flag with `--relaunch`, are
  rejected with a clear error.
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
- **Owner gates.** There are four, all in `coga.megalaunch`: the queue scan,
  the launch reread, and two inside `_drain_satisfied_blockers` (the
  blocked-ticket scan and the dependency-activation reread). There is no
  separate "ask" path. The drain resolves only blockers whose named
  dependency has finished, then relaunches.
- **Claim takeover.** In the start path (`_prepare_agent_launch`'s claim
  check), an `in_progress` ticket with a plain `launch_generation` from an
  earlier session gets its claim replaced without checking whether that
  session still runs. Pending and released claims are refused.
- **Re-block notifications** already name `current_user` as the operator
  and the ticket owner as the person who must answer. Keep that as is.

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
- **Dependency drain follows the chosen owner (decided).** It only resolves
  blockers whose dependency has finished, so draining zach's tickets is
  mechanical work and does not answer a question on his behalf.
- **Claim takeover is allowed across owners (decided by the owner).** A
  sweep of zach's tickets treats his `in_progress` claims exactly as the
  default sweep treats mine: it replaces a plain claim and refuses pending
  and released claims. Don't add any special case. Coordinating with the
  other owner is the operator's responsibility. Note this in the
  `coga/megalaunch` docs.
- **The filter is on `owner:` only.** It never looks at who holds the
  current step. Owner-less tickets match only `--all-owners`.
- **Notifications go to the ticket owner (accepted).** Lifecycle posts for
  zach's tickets still notify zach, as the accountable human. Log actor
  attribution (`megalaunch`) is out of scope.
- **Reread message.** The launch-reread skip message currently says the
  owner "is not current operator {current_user}". It should name the target
  owner, or say that the ticket is outside the owner filter.

### Docs to update in the same PR (edit these, not attached)

- `src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md`:
  the "Bare sweep" and "Explicit selection" sections, and the frontmatter
  description ("owner-scoped sweep"). Mirror the edit byte-for-byte into the
  legacy live copy `docs/contexts/coga/megalaunch/SKILL.md`, which is pinned
  in `tests/legacy_removal_inventory.txt`, and commit both together.
- Fix the stale "any owner" text in the `--pick` help and the module
  docstring in `commands/megalaunch.py`. In `coga.megalaunch`, fix the
  module docstring, the run-staging docstring, and the
  `launchable_candidates` docstring.
- `coga/cli` has no flag list for megalaunch (it links to
  `coga/megalaunch`), so it needs no edit.

### Tests

Picker candidate filtering covers default, `--owner`, and `--all-owners`.
The sweep with `--owner <other>` launches that owner's ticket and still
skips other owners at the reread. Flag conflicts to test: `--owner` with
`--all-owners`, and either flag with `--relaunch`. Also cover:
- the drain under `--owner <other>`;
- an unknown `--owner` giving an empty result.

Check for existing tests, including tests of the `pick` alias, that assume
the picker lists every owner. Existing megalaunch tests live in
`tests/test_megalaunch.py`.

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

## Dev

branch: coga/v1-filter-by-user-for-megalaunch-85c239

## Implement handoff (2026-11-05, claude / claude-opus-5-5)

Pushed `871f6e54a` (rebased on origin/main `68dcf2215`, which brought only
coga/ state commits). No PR yet.

What changed:
- `coga.megalaunch.resolve_owner_filter(cfg, owner=, all_owners=)` returns
  one target owner (`None` = every owner). `_owner_in_scope` applies it at all
  four sweep gates: queue scan (`_run_sweep`), both checks in
  `_drain_satisfied_blockers`, and the exact reread in `_launch_until_stop`.
  `owner_filter` is a required kw-only param on `_launch_until_stop`; the
  selection path passes `None` together with `explicit=True`.
- `run_megalaunch(..., owner=, all_owners=)` refuses either flag combined with
  `selection`. `MegalaunchRun.owner_scope` ("zach" / "every owner" / None)
  adds an `Owner:` line to the summary and an "owner X" label to the Slack drain line.
- `launchable_candidates(..., owner=, all_owners=)` filters the picker list.
- CLI: `--owner NAME` and `--all-owners`. `_resolve_selection` rejects
  `--owner`+`--all-owners` and either flag with `--relaunch` (exit 2). An
  empty picker names the owner. An empty `--owner` sweep prints
  "No launchable tasks owned by X." The confirmed pick runs without the owner flags.
- The reread skip message is now "owner X is outside the owner filter (T)".
- Re-block notifications are unchanged (operator = current_user, the owner answers).
- Docs: added an "Owner filter" section, plus edits to Bare sweep (claim
  takeover across owners), Explicit selection, Dependency drain, and the
  description. Mirrored byte-for-byte into `docs/contexts/coga/megalaunch/SKILL.md`.

Decisions:
- Owner-less tickets fail `validate` at launch (`owner` is a required key).
  They are listable under `--all-owners`, so the tests cover the owner-less case only in the
  picker list.
- `--owner` with an empty string is not specially rejected. It matches nothing,
  so the run is an empty sweep.

Adjacent findings: none.

## PR

```yaml
title: Filter megalaunch by ticket owner
author: claude
author_evidence: Implement session ran Claude Code on claude-opus-5-5 (this session).
head: 871f6e54a5a837e2ee166ad4b4090acdbd42d5c5
base: 68dcf2215f21f996c24b0e1e62105782e3a6b6c4
depth: skim
rationale: Bounded CLI flag addition; one filter value threaded through existing gates, default sweep unchanged, tests per gate.
implementation: Adds --owner/--all-owners to coga megalaunch; --pick defaults to the operator's tickets; one owner filter gates scan, reread, and drain.
deviations: None from the ticket design.
limitations: Owner-less tickets appear under --all-owners but cannot launch (owner is a required key), so they report failed if picked or swept.
files:
  src/coga/megalaunch.py: Owner filter resolution and threading through sweep, drain, reread, picker candidates, and run summary.
  src/coga/commands/megalaunch.py: New --owner/--all-owners flags, conflict errors, empty-result messages, docstring/help fixes.
  tests/test_megalaunch.py: Cover picker filtering, --owner sweep, reread gate, drain, unknown owner, and flag conflicts; update the reread message and the all-owners candidate test.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md: Document the owner filter, cross-owner claim takeover, and drain scope.
  docs/contexts/coga/megalaunch/SKILL.md: Byte-identical legacy live copy of the package topic.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: No code review has run yet; review belongs to later workflow steps.
checks:
  - command: .venv/bin/python -m pytest tests/test_megalaunch.py tests/test_cli.py tests/test_packaging.py -q
    status: passed
    head: 871f6e54a5a837e2ee166ad4b4090acdbd42d5c5
    base: 68dcf2215f21f996c24b0e1e62105782e3a6b6c4
    detail: 219 passed on the rebased head.
  - command: .venv/bin/python -m pytest -q
    status: passed
    head: b5bf9c23627fff4b2b358d23c655b4ff7ae7000b
    base: 0dbe4a1e615aea6abd67f0f25a66cdcc5d81528e
    detail: 4462 passed, 10 skipped on the pre-rebase commit; the rebase changed only coga/ state files (src/tests/docs trees identical).
  - command: .venv/bin/coga validate --json
    status: passed
    head: b5bf9c23627fff4b2b358d23c655b4ff7ae7000b
    base: 0dbe4a1e615aea6abd67f0f25a66cdcc5d81528e
    detail: Exit 0.
```
