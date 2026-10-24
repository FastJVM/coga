---
title: Test BMAD Method
status: in_progress
owner: zach
contexts:
- coga-dev/principles
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
agent: claude
step: 1 (agent-produces)
---

## Description

Zach installs BMAD Method (https://github.com/bmad-code-org/bmad-method) and
runs a real task through it end to end in a VM; the agent drafts the write-up of
how it compares to Coga. As of October 2026 BMAD sits at roughly 54k stars. The
trial installs the stable v6 line with `npx bmad-method install`, which needs
Node 20.12+, Python 3.10+ and uv; the v7 preview alpha, which installs as skills
or via the plugin marketplace for Claude Code and Codex, is out of scope. Its delivery loop is four phases —
clarify, plan, build and verify, learn and adjust — and it layers product,
architecture, UX, development and testing perspectives over multi-agent
workflows, scaling process weight to the size of the change.

The write-up covers four things:

- The installation experience end to end.
- Whether the role-and-phase structure earns its keep on a small change, or is
  mostly ceremony.
- How its learn-and-adjust phase compares with what Coga does through contexts,
  skills, and the retro and dream passes.
- What it does that Coga does not.

The trial runs on a fresh VM with nothing installed. Install coverage therefore
starts at the prerequisites — Node, Python, uv, and Claude Code itself — not at
`npx bmad-method install`. Record what the bare machine demanded, in order.

Done when the BMAD section of the "Coga Competitor Tests" Google Doc reflects a
trial Zach considers finished. The doc as a whole stays unfinished until
Compound Engineering is tested, and sharing it is not this ticket's job.

Why now: BMAD is the closest competitor on positioning. Its tagline — agile AI driven development, turn an idea or change request into working software without giving up the thinking — is nearly the sentence we would write for Coga, so we need first-hand evidence of where the two actually diverge rather than guessing from feature lists.

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

### How this runs

Zach runs BMAD hands-on in a VM, pastes screenshots into the session, and notes
what he sees. The agent discusses findings with him and drafts write-up text for
the doc. The agent does not run BMAD. This is information gathering, not a
staged project — follow Zach's lead on what to look at next.

The VM is one of the spare `cogatest` UTM machines, retitled for this trial;
Zach confirms which at launch. It starts bare. The SpecKit VM was deleted, so
nothing carries over from that trial except what is already in the doc and in
this ticket.

Do not draft findings for a step Zach has not run yet. Write-up text comes from
his screenshots and notes, not from BMAD's docs — a plausible paragraph he did
not observe is a failure, not a head start.

`coga-dev/principles` is attached because the write-up's Coga-side claims feed
README positioning and have to stay aligned with it.

### Where findings go

The doc is "Coga Competitor Tests" —
https://docs.google.com/document/d/19qnSHqN2eH5e66peQ7X-R6NPIg6IPHc0wsS3cBxUEuM/edit
(its Drive filename is still "Untitled document"). It is a numbered running log
per tool, with Zach's screenshots inline. Its BMAD section is the deliverable.
`FastJVM/coga` is public, so findings stay in the doc and the blackboard stays a
pointer. The doc itself is owner-only, so its URL here is safe.

The Drive tools can read that doc but cannot write to it: `update_file` changes
metadata only, and there is no content-edit tool for an existing Doc. So the
agent drafts markdown and Zach pastes it in — Docs converts pasted markdown to
real headings and lists. Do not create a replacement Doc; the screenshots live
in this one.

`competition-testing/test-compound-engineering` carries the share with Nico,
because it is the last of the three trials. Nothing about the share belongs to
this ticket.

### The trial task

Build `tiny-ticket`: a command-line tool that stores tasks as markdown files
with YAML frontmatter, with three commands — create a task, list tasks, and
validate the files. Validation enforces that `status` is one of a fixed set and
that any non-draft task has a workflow.

Zach picked it because he knows the correct design cold, so a bad spec or plan
is obvious on sight. Keep the product name `tiny-ticket`, matching the SpecKit
and Compound Engineering trials, and use the project directory
`bmad-tiny-ticket`.

### Install starting point

The trial runs the stable v6 line via `npx bmad-method install`, because the
comparison target is what a user installs today and the install findings feed
the installer ticket. Record the exact version that ran — v6 takes patch
releases weekly, so the line moves.

The v7 preview alpha is a separate pass if Zach wants one, never a mid-install
switch. It restructures the role personas into skills, so it changes the answer
to the role-and-phase question rather than confirming it, and its install story
is not what a user meets today. As of 2026-10-23 it has also slipped past its
estimated release date without shipping.

Prerequisites on a bare machine are Node 20.12+, Python 3.10+, and uv, which
BMAD's README names for its own setup and Python scripts. BMAD itself has no uv,
uvx, pip, or pipx install path — no `bmad-method` package exists on PyPI, and
both lines install through npx. What else a bare machine needs is part of what
this trial establishes.

Read the SpecKit section of the doc before the install starts. Its numbered log
is the baseline for what a bare `cogatest` VM needs, including how Claude Code
got onto it — Claude Code is not present on a fresh machine and has to be
installed before any agent-driven step.

Installer findings are also input to
`marketing/fix-installer/make-the-readme-install-section-the-only-install-p`,
which owns the copy-pasteable install commands.

### Out of scope

Only BMAD's main delivery loop gets trialled.

What is worth comparing across the three tools gets decided once the docs exist,
not up front. Do not start a three-way matrix mid-trial.

Do not commit trial output, competitor notes, or the `tiny-ticket` source into
this repo. The scratch project stays in the VM. At `report-to-coga`, record the
doc link and that the section is done — not what the trial found.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
