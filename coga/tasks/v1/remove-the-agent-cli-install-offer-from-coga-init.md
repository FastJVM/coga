---
title: Remove the agent CLI install offer from coga init
status: draft
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
---

## Description

`coga init` offers to install an agent CLI the user does not have. Remove that
offer.

`init._offer_agent_cli` scans `PATH` for `claude` and `codex` and branches
three ways. Only the found-nothing branch goes away: the one that prints "No
agent CLI is installed" and prompts "Install which agent CLI?", then calls
`agent_cli_setup.offer_agent_cli` to run the vendor installer.

Keep the scan and the other two branches. With exactly one agent CLI on
`PATH`, init still asks to make it the `default_agent` in `coga.toml`. With
both, it still says nothing.

Done when: no `coga init` path offers to install an agent CLI or says where to
get one, init still offers an already-installed CLI as the default agent, and
`python -m pytest` passes.

### The two call sites are not the same

- `_setup_initialized_clone` (the clone path, near line 1174) passes `None`
  and discards the return, so the install offer is the call's only effect.
  Delete the call.
- `_do_init` (fresh init, near line 1359) feeds the return into the
  `default_agent` written to `coga.toml`. Keep it.

`launch.offer_agent_cli` stays. It fires only for the `coga build` onboarding
task, and this reversal is init-only, so the shared function keeps a caller.

### Stale text and tests this breaks

- `agent_cli_setup`'s module docstring says it is shared by interactive `coga
  init` and `coga build`; only `coga build` is left.
- `init._offer_optional_tools`'s docstring says agent CLIs are not warned
  about there because `_offer_agent_cli` offers them.
- `conftest._stub_init_dep_check` stubs `_offer_agent_cli` by string with
  `raising=False`, so renaming the function creates a dead attribute instead
  of failing, and the real one then runs in every init test.
- Eight tests in `tests/test_init.py` exercise the picker. The four
  install-path ones go; the four covering the scan and the default stay,
  including `test_agent_offer_proposes_the_only_installed_cli_as_default`.

### Init says nothing about where to install

Init names no install location at all. `_do_init`'s next-steps item 2
currently carries both manifest URLs and prints unconditionally; drop the URLs
and use the scan result, so a user with no agent CLI reads one statement of
fact — coga drives Claude Code (`claude`) or Codex (`codex`), neither is on
`PATH`, and launching agents needs one.

Say it once, in next steps. The scan's found-nothing branch prints nothing
where the prompt used to be.

Out of scope: `agent_cli_missing_message` still prints the manifest install
URL for `coga launch`'s point-of-need error, and the `install` field stays in
the manifest for it. A later ticket builds the supported-agents list from this
same scan and may put an install path there.

## Context

### Why

- Nico's direction, 2026-11-04: coga's users already run agentic coding tools,
  so someone with no agent CLI installed is not the audience init should be
  built around.
- The offer dead-ends on a fresh Mac. With neither brew nor npm available,
  picking `claude` prints "Install it from <url>, then re-run" and init then
  runs to completion anyway, so the advice is wrong as given.
- `v1/19-install-link-for-claude-code-yields-the-desktop-ap` closed
  2026-11-04 without fixing the related dead end where the linked installer
  yields the desktop app instead of the `claude` CLI.
- `agent_cli_setup`'s stated policy is that the installer is the vendor's
  package, never `curl | sh`, so there is no third fallback to reach for.

### This lands before ticket 20

`v1/20-ask-which-agents-to-enable-during-coga-init` rewrites the same function
into a picker that asks which agents to enable. It is parked at owner
`review-design` and unstarted; this ticket lands first and ticket 20 builds on
what remains. Its blackboard carries the 2026-11-04 reversal and has already
dropped the install offer from two acceptance criteria and a 2026-10-27 design
decision.

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
