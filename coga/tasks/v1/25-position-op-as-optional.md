---
title: Position op as optional
status: active
owner: zach
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

`coga init` still offers to install `op` (the 1Password CLI) and lists it
alongside `gh` as a tool init handles, so a user who keeps secrets in a
different manager is steered toward 1Password. Stop init from offering to
install `op` at all. In its place, print one note naming what needs it, so a
user with another secrets manager skips it knowing nothing is broken. `op`
stays a supported, documented feature: the team uses `op://` secrets. Only
init's positioning changes.

Done when: interactive `coga init` on a machine without `op` never prompts to
install it, under any package manager; init's output says `op` is only needed
for tickets that declare `op://` secrets; `docs/contexts/coga/install/SKILL.md`
and its packaged twin describe that behaviour; and `tests/test_init.py`
covers it.

## Context

### Decision (owner, 2026-11-03)

- Drop the install offer for `op` and keep a one-line note in init's output.
  The rejected alternatives were removing `op` from init output entirely, and
  keeping the `[y/N]` offer with only the message split.
- This ticket stays separate from `v1/18-handle-gh-not-being-installed-by-default`,
  which reworks the `gh` half of the same message. Both edit
  `_offer_optional_tools`. Whichever lands second rebases onto the first and
  keeps the other's `gh` or `op` wording intact.

### Current behaviour

- `dependencies.DEPENDENCIES` declares `op` with `offer_install=False`. That
  only sets the confirm default to no. Because the value is not `None`,
  `init._offer_install` still prints "`op` is not installed … Will run: brew
  install --cask 1password-cli … Install it now? [y/N]" on brew and winget
  machines. That prompt is coga setting up 1Password, which the owner said
  must never happen.
- `init._offer_optional_tools` builds its warning list only from deps whose
  `offer_install is not None`. Setting `op` to `offer_install=None` alone
  therefore removes `op` from the output entirely. The implementer has to add
  the note line deliberately: it is not a single-field change.
- That list currently puts `op` and `gh` under one heading, "Optional tools not
  on PATH (init continues without them)", which reads as though init handles
  both.
- The `op` entry's `purpose` string already states the facts the note needs:
  only needed for `op://vault/item/field` secrets, resolved with `op read` at
  launch, and fails loudly if missing. Reuse it rather than restating it.
- `op` has `packages` only for brew and winget. Decide whether `packages` stays
  for future use or is removed. Nothing should be able to install it from init.

### Files to change

- `src/coga/dependencies.py` (the `op` entry) and `src/coga/commands/init.py`
  (`_offer_optional_tools` and its docstring, which names `op` as offered).
- `docs/contexts/coga/install/SKILL.md`, the prerequisites list and the
  "offers to install a missing `git`, `gh` … or `op` (default no)" paragraph.
  Its packaged twin
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md`
  must stay byte-identical; `tests/test_packaging.py` enforces it. These files
  are being edited, so they are not attached.
- `tests/test_init.py`, which already covers the optional-tool offers.
- The README currently does not mention `op`. Leave it that way unless the
  change makes a mention necessary.

### Why

- Zach on the walk, 2026-10-15: init lists `gh` and `op` together as optional
  tools without saying who needs either.
- Zach, 2026-10-21: people may have their own secret management system, so
  `op` should never read as something coga init sets up for them.

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

Previous ref: `marketing/fix-installer/position-op-as-optional` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: coga/v1-25-op-not-offered-at-init
pr: https://github.com/FastJVM/coga/pull/1162

## Production notes

Landed in PR #1162, authored directly in the ticket session at the owner's
direction rather than through the `code/with-review` workflow.

### What shipped

- `op` carries `offer_install=None` and no `packages`, which removes it from
  `init._offer_install` and from the `_offer_optional_tools` warning list.
- `init._note_missing_op` prints one note when `op` is not on PATH, in
  interactive mode and not. It runs after the "Optional tools not on PATH"
  block, so the note sits outside that heading, and it sources its text from
  the manifest `purpose` so the two cannot drift:

  ```
  `op` (1Password CLI) is not on PATH, and init does not install it:
    needed only when a ticket declares an `op://vault/item/field` secret, which coga resolves live with `op read` at launch (run `op signin`).
    Install it from https://developer.1password.com/docs/cli/get-started/ only if you need it.
  ```

- `docs/contexts/coga/install/SKILL.md` and its packaged twin describe the new
  behaviour; the twin stayed byte-identical.

### Decisions closed

- `packages` removed rather than kept: `_offer_install` returns on
  `offer_install is None` before reading them, so brew/winget entries would be
  unreachable install data inviting reuse.
- The note keeps the install URL and prints in both modes.
- The install topic's prerequisites list already read correctly, so only the
  install-offer paragraph changed.

### Verification

`tests/test_init.py` 149 passed and `tests/test_packaging.py` 31 passed
locally; those are the only test files that reference the changed symbols. The
full local suite was started and killed before it finished, so CI on PR #1162
is the full-suite gate.

New and changed tests: `test_dep_check_never_offers_to_install_op`
parametrized over darwin, win32 and linux; the warning-list test asserts
`"op: install from"` is absent and the note present;
`test_init_offers_optional_tools_once_preflight_passes` expects
`offers == ["gh"]`. Removed `test_dep_check_skips_op_offer_without_a_package`
and the dead `"1password-cli": "op"` mapping in the `_interactive` fake.

### Open follow-on

`v1/18-handle-gh-not-being-installed-by-default` (draft) still cites `op` as
`offer_install=False` at `dependencies.py:99` and says to "settle them
together". Both are stale. Its implementer rebases onto this and keeps the
`op` note and `_note_missing_op` intact. Not edited from this session.

### Draft-authoring evaluator review (2026-11-03)

Kept for the record. Its code citations describe `main` before PR #1162, so
the line numbers and the `offer_install=False` claims are historical.

**Code claims: all correct.** `op` has `offer_install=False` (dependencies.py ~:99); `_offer_install` (init.py:485) only skips on `offer_install is None` or a missing package, so brew/winget still get the "Will run: brew install --cask 1password-cli … [y/N]" prompt. `_offer_optional_tools` (init.py:433) filters `offer_install is not None`, so `None` silently drops `op` from output — exactly the trap the ticket warns about. Docstring does name `op` as offered. Install SKILL.md and its packaged twin are byte-identical and lines 31/35–41 match the ticket's description. README has no `op` mention.

**Clarity:** Good; a cold agent can start. Gaps: it doesn't name the tests that will break — `test_init_offers_optional_tools_once_preflight_passes` asserts `offers == ["gh", "op"]`, `test_dep_check_warns_but_does_not_crash_on_optional_tools` asserts `"op: install from"`, and `test_dep_check_skips_op_offer_without_a_package` becomes moot. Listing these saves a search. The `_interactive` fake_run mapping `"1password-cli": "op"` also becomes dead.

**Done:** Checkable, but "one note" is underspecified: under the existing warning heading or its own? Since v1/18 is reworking that heading, say "outside the 'Optional tools' heading" explicitly. Also say whether the note keeps the install URL (I'd say yes) and whether it prints in non-interactive init too (it should — "in both modes").

**Workflow:** code/with-review fits — small behaviour change with tests and a docs twin.

**Contexts:** None attached is right. Consider citing `coga/secrets` (docs/contexts/coga/secrets/SKILL.md) by path so the note's claim ("only `op://`") stays consistent, and `coga-dev/packaging` for the twin rule. Nothing needs attaching.

**Scope / v1/18 conflict:** Scope fine. The rebase rule is stated, but v1/18 (draft, `workflow: null`) still says "settle them together" while this ticket says separate. Update v1/18's Context to point back here so they don't contradict.

**Assumptions to question:** (1) The `packages` decision is left open — I'd resolve it to "remove", since `agent_cli_setup._lookup` reads `DEPENDENCIES` and dead install data invites reuse; decide before launch. (2) The `purpose` string is multi-sentence; reusing it whole won't be "one line" — say which slice (first sentence / up to "at launch"). (3) The `op` comment "offered, default no" needs rewriting.

**Prompt size:** task_context at 44% (2017 tokens) is a trim candidate — the "Why" quotes and decision rationale's second half could move to the blackboard or be compressed to one line each.
