---
title: Install link for Claude Code yields the desktop app not the CLI
status: draft
owner: zach
workflow: null
---

## Description

`README.md:103` links `https://claude.com/claude-code`, which gives the user
the Claude desktop `.dmg`. Dragging that into Applications does not give coga
the `claude` CLI it drives, so `coga build` still reports no agent. On a fresh
Mac `installer_argv` in `src/coga/agent_cli_setup.py` finds neither brew nor
npm, returns None, and falls back to printing that same URL. Decide what a
fresh Mac is told to run so the user ends up with the CLI.

Done when: a user on a fresh Mac who follows the install path ends up with a
working, authenticated `claude` CLI.

## Context

### Why

- Finding 15 on `test-and-fix-install-on-macos-and-windows`, recorded there as
  the highest-severity finding of the walk and still open.
- Zach's Mac VM walk log records the dead end in full: Claude.dmg downloaded,
  dragged to Applications, and simply downloading Claude did not set it up the
  way coga needs.
- His workaround was to install Node from nodejs.org and then run
  `npm install -g @anthropic-ai/claude-code`, which no documentation mentions.
- `src/coga/agent_cli_setup.py:9-12` states the policy that the installer is
  the vendor's package and never a `curl | sh` script, so the obvious fix runs
  against current policy.
- That tension is finding 16 on the same ticket, open and awaiting an owner
  ruling; this ticket cannot land without it.
- `https://claude.ai/install.sh` is Anthropic's own script and installs under
  `$HOME` with neither Node nor Homebrew, which is why the five-line block on
  PR #1043 used it.
- The same gap applies to Codex: its manifest entry offers only brew and npm.

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

Previous ref: `marketing/fix-installer/install-link-for-claude-code-yields-the-desktop-ap` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Documentation coordination — 2026-10-29

The documentation acceptance pass, `v1/33-review-all-doc`, pushed candidate
`bd72b19d2a13972005285252b53df7504350bbc7` on `codex/v1-33-doc-acceptance`.
README and coga/install now link the vendor's CLI quickstart and name the login
command. This is not merged yet. `src/coga/dependencies.py` still points to
`https://claude.com/claude-code`, and the install helper still needs brew/npm.
Those product fixes and the fresh authenticated-Mac success criterion remain
owned here; the documentation change is not a completion receipt.
