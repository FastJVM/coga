---
title: Find out what macOS actually ships
status: draft
owner: zach
workflow: docs/with-review
---

## Description

The install instructions should install only what a machine lacks, and nobody
has checked what macOS ships. Settle whether `pip`, `python3` and `git` are
present on a fresh macOS, which versions, and which of them are Command Line
Tools stubs rather than real binaries. Answer it from Apple's documentation and
the run evidence already in this repo; no new VM or Mac environment.

Record two answers, not one. Whether `pip` ships, and whether a coga install
can use it. The Command Line Tools Python is 3.9 and `pyproject.toml:10` pins
`requires-python = ">=3.11"`, so a native `pip` only helps if a 3.11
interpreter is already present.

Done when: the answer is recorded per macOS version, each claim carries the
source it came from, and the two install-path tickets have what they need. This
ticket does not edit the install instructions.

## Context

### Why

- Nico asked for this first in the review on 2026-10-19, specifically whether
  `pip` is native on macOS.
- If `pip` is native the install can use it and leave uv as the opt-in path.
- Owner decision 2026-10-21: answer this from Apple's docs and the existing
  runs, which already cover both uv and pip. Do not run another VM.

### What the repo already asserts

- `scripts/clean-install/macos-walk.sh`, in its `reset` case (near line 43 as
  of this writing), records that `/usr/bin/git` is the shim a new user hits.
- The same script's `walk` case (near line 60) records that macOS ships
  `/usr/bin/python3` 3.9, below coga's floor, and provisions 3.11 instead.
- Those landed with `pin-python-3-11-in-the-macos-clean-install-harness` and
  `document-the-macos-command-line-tools-prerequisite`, both done.
- So the open question is narrower than the title: it is pip. Whether anything
  usable exists before the Command Line Tools, and whether they put `pip3` on
  PATH or leave only `python3 -m pip`.

### Why the two readings disagree

- `macos-walk.sh`, in the same `reset` case (near line 30), records that EC2 Mac
  AMIs ship Command Line Tools for their Homebrew, and deletes them so git
  behaves as it does on a new Mac.
- A machine that already has the tools has a real `python3` and a working
  `python3 -m pip`, so pip looks native on it.
- The VM walk found no pip. The two observations are most likely about machines
  in different states rather than one of them being a mistake. Confirm or kill
  that explanation; it is the reason the ticket exists.

### Whether a VM is a fair test

- `affordable-macos-testing-on-owned-macs-and-per-min` designates disposable
  Apple Silicon VMs as the vessel for genuinely fresh-install tests, and the
  Tart image it chose has no Command Line Tools.
- The same ticket records that a fresh user account does not isolate
  machine-wide dependencies, so a new account on a working Mac is the weaker
  test, not the VM.
- A VM cannot speak for a Mac set up by Migration Assistant, which carries the
  tools and Homebrew across. Most real new Macs look like that, so say which
  kind of Mac each recorded answer describes.
- Intel has no fresh-install route today: the owned-Mac design can only attach
  to an Intel host and never resets it.

### Where the answer lands

- The Command Line Tools trap and the tools-ship-3.9 fact are already listed on
  `test-and-fix-install-on-macos-and-windows` as orphan facts needing a
  surviving context.
- `make-the-readme-install-section-the-only-install-p` owns giving those facts a
  home. Add the pip answer there rather than opening a second home for it.
- `separate-installing-coga-from-installing-its-depen` owns what the install
  section contains and is the consumer of this answer.

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
