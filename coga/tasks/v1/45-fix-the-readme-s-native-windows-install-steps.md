---
title: Fix the README's native-Windows install steps
status: draft
owner: zach
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
---

## Description

The README's native-Windows section was written against Windows Server 2025. Walk 1 of v1/31 (Windows 11 Home 26300, 2026-11-10) found where it fails a new user on a consumer install. Walks record findings only and leave the doc edits to the docs owner. v1/33 was the routed owner and is now done, so this ticket collects the open items.

Must fix:

- The uv install line fails silently (v1/31 finding 5). Windows 11 client defaults to the `Restricted` execution policy. Under it, `irm https://astral.sh/uv/install.ps1 | iex` refuses to run and calls `exit`, which closes the PowerShell window before the user can read the error. `uv` is then "not recognized". Server 2025 defaults to `RemoteSigned`, so the tested route never saw this. Use uv's own documented form, `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`, which leaves the machine's policy unchanged.

Should fix:

- No `python` command after `uv python install 3.11` (finding 10). `python` resolves to the Microsoft Store stub, so agents report that Python isn't installed. Consider `uv python install 3.11 --default`, or a note.
- No step creates a repo (findings 4 and 7). PowerShell opens in `C:\WINDOWS\system32`, and "change into your project's Git repository" gives a new user nothing to change into. Spell out `mkdir`, `cd` and `git init`.
- The `git var GIT_AUTHOR_IDENT` pre-check is easy to miss and repeats `coga init`'s own clear refusal (finding 6). The README sets identity per repo, while init's message uses `--global`; drop the check or make them agree.
- Say "tested on Windows 11" once a walk on the final candidate passes.

Coordinate with v1/43:

- The README still says `uv tool install coga`, while PyPI 0.4.1 predates the Windows port (finding 2). This resolves when 1.0 publishes; until then, say how to install.
- Coordinate with `v1/47-cap-requires-python-and-stop-init-leading-with-a-c`: without `--python`, uv now picks CPython 3.15 and the PyYAML build fails, needing MSVC. Seen in v1/20's walk on 2026-11-11. Whichever lands first, the README must not leave a no-Python machine on that path.

Out of scope: init's symlink failure (finding 8) is a code bug and needs its own ticket. Evidence: `coga/tasks/v1/31-test-install-on-windows.md`, "Walk 1 summary" and findings 2–10.

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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
