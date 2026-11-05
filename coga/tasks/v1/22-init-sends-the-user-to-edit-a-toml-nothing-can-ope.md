---
title: Init sends the user to edit a toml nothing can open
status: in_progress
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
step: 3 (open-pr)
agent: claude
---

## Description

`coga init` ends with a "Next steps" list whose first item (after the PATH
step, when needed) is "Edit `<repo>/coga/coga.toml` — set your agents,
notification channels, and aliases". It is built in the next-steps block at
the end of `commands/init.py` (the `steps.append(...)` that names
`coga.toml`). A fresh Mac has no application registered for `.toml`, so a new
user is sent to a file they cannot open as their first instruction.

Decision (settled during ticket authoring): **drop the step.** The audience is
developers comfortable with CLI tools, and nothing in a first run needs the
edit — init already asks for the default agent, and the closing notifications
note already shows the exact `coga.toml` lines for opting into Slack. Do not
replace it with "how to open a .toml" guidance.

Done when: `coga init`'s next steps no longer tell the user to edit
`coga.toml`, the remaining steps renumber cleanly in both the empty-repo and
existing-repo paths, and a test pins that the next-steps output does not send
the user to edit `coga.toml`.

## Context

### Why

- Findings 10 and 11 on `test-and-fix-install-on-macos-and-windows`, both
  open: next steps leads with an unnecessary `coga.toml` edit, and nothing
  opens `.toml` on a fresh Mac.
- Zach's Mac VM walk log: his run had no system application set to open the
  coga files, and his instinct was TextEdit over VS Code because TextEdit ships
  with macOS.
- He also doubted the step belongs in the instructions at all; authoring
  decided to drop it (see Description).
- `ask-which-agents-to-enable-during-coga-init` removes the agents half of that
  edit; notifications are covered by init's closing notifications note, and
  aliases are not first-run material. Nothing is left, so this ticket does not
  wait on that one.

### Scope

- Remove the step from the next-steps block in `commands/init.py`. Numbering
  comes from `enumerate(steps, 1)`, so it renumbers itself.
- Add a test in `tests/test_init.py` beside
  `test_init_next_steps_name_the_agent_cli_prerequisite`. Assert only on the
  "Next steps:" block: `_print_notification_state` prints after it and still
  (correctly) mentions `coga.toml` as a later Slack opt-in, so a whole-output
  assertion would fail. No current test asserts the removed line.
- Update the `coga/init` topic, which lists the next steps including "edit
  `coga.toml`" (its next-steps passage). Edit the package owner
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md`
  and mirror it byte-identically into the legacy live copy
  `docs/contexts/coga/init/SKILL.md` (pinned in
  `tests/legacy_removal_inventory.txt`), or `tests/test_packaging.py` fails.
  It is an editing target, so it is not attached. The README has no copy.
- Out of scope: the notifications note itself, which is optional later
  guidance, not a first instruction.

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

Previous ref: `marketing/fix-installer/init-sends-the-user-to-edit-a-toml-nothing-can-ope` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: coga/v1-22-init-drop-coga-toml-next-step

## Handoff (implement)

- Removed the `Edit <repo>/coga/coga.toml …` step from the next-steps block in
  `src/coga/commands/init.py` (`init` command, the `steps` list); numbering
  comes from `enumerate(steps, 1)`, so the rest renumbers itself.
- New test `tests/test_init.py::test_init_next_steps_do_not_send_the_user_to_edit_coga_toml`,
  parametrized empty/filled. It slices only the "Next steps:" block (up to the
  blank line `_print_notification_state` emits first), asserts no `coga.toml`,
  and asserts the step numbers are contiguous from 1. It fails on the old code
  (both cases) and passes with the fix.
- `coga/init` topic: dropped "edit `coga.toml`" from the next-steps sentence
  in the package owner; mirrored byte-identically to `docs/contexts/coga/init/SKILL.md`.
- Note: the shell's `python` here lacks `tomlkit`; use `.venv/bin/python -m pytest`.

## Peer review

- Direct Codex review **completed**, independently of the Claude implementer,
  with **no findings and no fixes needed**. Reviewed the complete four-file
  diff and surrounding init output, test fixtures, notification boundary,
  and owning topic. The implementation commit credits Claude Opus 5.5,
  consistent with the implement handoff.
- Reviewed and tested head: `8a8941a382b0721c453bded20c5a9be202e3e35f`.
  Diff base: `2b4bb7b45a5433e0c970fd27a3bfcfda2f4a30aa`.
- Rebased onto fetched `origin/main` before review. Main's intervening
  commits changed only ticket state. The final fetch/rebase left the reviewed
  head/base unchanged; pushed with an explicit `--force-with-lease` and
  returned this manual checkout to clean, current `main` before writing this
  handoff. The remote feature branch has the reviewed head and remains one
  commit ahead of main.
- `.venv/bin/python -m pytest`: **4455 passed, 10 skipped** in 577.65 seconds
  on Linux/Python 3.12.12, including both new regression cases and packaging.
  `git diff --check main...HEAD` passed on the feature branch; the package
  topic and its legacy copy compare byte-identically.
- Real PTY checks ran the branch's `python -m coga.cli init <scratch-repo>
  --user tester` against real temporary Git repositories. At **80x24**, both
  empty and filled repositories with `coga` on PATH printed steps **1–3**.
  At **120x40**, both paths without `coga` on PATH printed steps **1–4**,
  beginning with the PATH instruction. Every run exited 0; no Next steps
  block mentioned `coga.toml`, the empty/filled command remained `coga build`
  / `coga ticket`, and the separate Slack opt-in note still named the TOML.
  The exact helper invocations are in the PR checks below; the helper clears
  inherited Coga launch and Slack environment variables for each scratch run.
- Recommendation: **merge**. No design deviations or unresolved concerns.
  No native macOS, Windows, or Python 3.11 run was performed; this deletion
  changes printed guidance and uses the existing platform-neutral enumeration.
  Next step owns the mechanical PR opening.

## PR

```yaml
title: Drop the edit-coga.toml step from init's next steps
author: claude
author_evidence: The implement handoff records Claude Code (claude-opus-5-5); the implementation commit credits Claude Opus 5.5. This fresh peer-review session ran as Codex and made no implementation changes.
head: 8a8941a382b0721c453bded20c5a9be202e3e35f
base: 2b4bb7b45a5433e0c970fd27a3bfcfda2f4a30aa
depth: merge
rationale: Small removal of unnecessary first-run guidance with no runtime behavior change. Independent Codex review completed without findings; the full suite and real PTY checks cover both repo paths and the optional PATH step.
implementation: Removes the coga.toml edit step from init's Next steps list; enumerate renumbers the remaining steps in both the empty-repo and filled-repo paths.
deviations: None.
limitations: The separate notifications note intentionally retains coga.toml as a later Slack opt-in. Verification ran on Linux/Python 3.12.12; native macOS, Windows, and Python 3.11 were not run because the change only removes printed guidance and preserves the existing enumeration.
files:
  src/coga/commands/init.py: Drop the coga.toml edit step from the Next steps list.
  tests/test_init.py: Pin that the Next steps block names no coga.toml and numbers contiguously, in the empty and filled paths; import re.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Remove the edit-coga.toml step from the coga/init topic's next-steps list.
  docs/contexts/coga/init/SKILL.md: Byte-identical legacy mirror of the package coga/init topic.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 8a8941a382b0721c453bded20c5a9be202e3e35f
  base: 2b4bb7b45a5433e0c970fd27a3bfcfda2f4a30aa
  detail: Direct Codex review completed on the final rebased diff, independently of the Claude implementer. Inspected all four paths and their surrounding contracts; no findings, fixes, or unresolved concerns. Real PTY checks confirmed the displayed guidance.
checks:
  - command: .venv/bin/python -m pytest
    status: passed
    head: 8a8941a382b0721c453bded20c5a9be202e3e35f
    base: 2b4bb7b45a5433e0c970fd27a3bfcfda2f4a30aa
    detail: 4455 passed, 10 skipped in 577.65 seconds on Linux/Python 3.12.12; includes the new empty/filled regression cases and packaging checks.
  - command: |
      .venv/bin/python /tmp/coga-v1-22-init-terminal-check.py --cols 80 --rows 24
      .venv/bin/python /tmp/coga-v1-22-init-terminal-check.py --filled --cols 80 --rows 24
      .venv/bin/python /tmp/coga-v1-22-init-terminal-check.py --missing-coga --cols 120 --rows 40
      .venv/bin/python /tmp/coga-v1-22-init-terminal-check.py --filled --missing-coga --cols 120 --rows 40
    status: passed
    head: 8a8941a382b0721c453bded20c5a9be202e3e35f
    base: 2b4bb7b45a5433e0c970fd27a3bfcfda2f4a30aa
    detail: Four real PTY invocations of the branch CLI against temporary Git repos, all exit 0. Both repo paths numbered 1–3 with coga on PATH and 1–4 without it; no Next steps TOML edit, correct build/ticket command, and the separate Slack note retained. The temporary helper cleared inherited Coga launch and Slack environment variables.
  - command: git diff --check main...HEAD
    status: passed
    head: 8a8941a382b0721c453bded20c5a9be202e3e35f
    base: 2b4bb7b45a5433e0c970fd27a3bfcfda2f4a30aa
    detail: Passed on the final feature branch with no whitespace errors.
```
