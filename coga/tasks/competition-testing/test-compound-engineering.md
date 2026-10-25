---
title: Test Compound Engineering
status: draft
owner: zach
contexts:
- coga-dev/principles
workflow: draft-for-human
agent: claude
---

## Description

Zach installs the Compound Engineering plugin
(https://github.com/everyinc/compound-engineering-plugin) and runs a real task
through it end to end in a VM; the agent drafts the write-up of how it compares
to Coga. As of October 2026 it sits at roughly 26k stars. It installs natively on
Claude Code as a plugin and supports around 14 other agent hosts. It ships 36
skills in eight groups, arranged as a six-step loop — `/ce-brainstorm`,
`/ce-plan`, `/ce-work`, `/ce-simplify-code`, `/ce-code-review`, `/ce-compound` —
with a separate `/lfg` command that runs the whole loop hands-off. It
deliberately weights planning and review over execution, on the theory that
captured learnings make each next unit of work cheaper.

The write-up covers four things:

- The installation experience end to end.
- How the compound step stores and reuses learnings, against what Coga does
  through contexts, skills, and the retro and dream passes.
- Whether the unattended `/lfg` mode is worth anything in practice.
- What it does that Coga does not.

The trial runs on a fresh VM with nothing installed. Install coverage therefore
starts at the prerequisites — Claude Code itself, and whatever else the bare
machine demands — not at the plugin install command. Record what it demanded, in
order.

Done when the Compound Engineering section of the "Coga Competitor Tests" Google
Doc reflects a trial Zach considers finished, and he has shared the doc with
Nico. This is the last of the three trials, so it carries the share.

Why now: the compound step is the direct analogue of Coga retro and dream, which makes this the sharpest head-to-head on the knowledge-capture claim. Nico also flagged it as the competitor closest to dream, so confirming or killing that read matters for positioning.

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

Zach runs the plugin hands-on in a VM, pastes screenshots into the session, and
notes what he sees. The agent discusses findings with him and drafts write-up
text for the doc. The agent does not run the plugin. This is information
gathering, not a staged project — follow Zach's lead on what to look at next.

The VM is one of the spare `cogatest` UTM machines; Zach confirms which at
launch. It starts bare. Nothing carries over from the SpecKit or BMAD trials
except what is already in the doc and in this ticket.

Do not draft findings for a lap Zach has not run yet. Write-up text comes from
his screenshots and notes, not from the plugin's docs — a plausible paragraph he
did not observe is a failure, not a head start.

`coga-dev/principles` is attached because the write-up's Coga-side claims feed
README positioning and have to stay aligned with it.

### Where findings go

The doc is "Coga Competitor Tests" —
https://docs.google.com/document/d/19qnSHqN2eH5e66peQ7X-R6NPIg6IPHc0wsS3cBxUEuM/edit
(its Drive filename is still "Untitled document"). It is a numbered running log
per tool, with Zach's screenshots inline. Its Compound Engineering section is the
deliverable. `FastJVM/coga` is public, so findings stay in the doc and the
blackboard stays a pointer. The doc itself is owner-only, so its URL here is
safe.

The Drive tools can read that doc but cannot write to it: `update_file` changes
metadata only, and there is no content-edit tool for an existing Doc. So the
agent drafts markdown and Zach pastes it in — Docs converts pasted markdown to
real headings and lists. Do not create a replacement Doc; the screenshots live in
this one.

Zach shares the doc with Nico once all three sections exist. This ticket carries
that share: it is the last of the three trials, and neither
`competition-testing/test-speckit` nor `competition-testing/test-bmad-method`
holds the obligation any more. Share by named account rather than switching on
link-sharing. As of 2026-10-23 the doc's permissions listed zach only.

### The trial task

Build `tiny-ticket`: a command-line tool that stores tasks as markdown files
with YAML frontmatter, with three commands — create a task, list tasks, and
validate the files. Validation enforces that `status` is one of a fixed set and
that any non-draft task has a workflow.

Zach picked it because he knows the correct design cold, so a bad plan is
obvious on sight. Keep the product name `tiny-ticket`, matching the SpecKit and
BMAD trials, and use the project directory `ce-tiny-ticket`.

### Why the trial runs in laps

The compound step writes learnings to `docs/solutions/`, and later
`/ce-brainstorm` and `/ce-plan` runs read them back as grounding context. The
README's phrase for it is "Run one teaches it. Run two remembers." A single
build therefore exercises only the write half, and the reuse claim this ticket
exists to test would go untested.

So the trial runs one full six-step lap per `tiny-ticket` command: lap 1
`create`, lap 2 `list`, lap 3 `validate`. Laps 2 and 3 read what lap 1 captured.
What to watch is whether the stored learnings visibly change the brainstorm and
plan output, and whether what got captured was worth capturing. `docs_root` is
configurable, so record its default and whether the setting is discoverable.

All laps run in the same VM and the same `ce-tiny-ticket` directory. A lap is one
pass through the six commands on the same codebase, not a fresh setup. This is
required, not just convenient — `docs/solutions/` has to survive between laps or
there is nothing for `/ce-brainstorm` and `/ce-plan` to read back, and the reuse
half silently goes untested.

The laps are the load-bearing part of this trial, not a thoroughness bonus.
Neither sibling produced knowledge-capture evidence: `/speckit-converge` was
never run, and BMAD closed with its learn-and-adjust phase unprobed. This is the
only one of the three trials that will have data on the claim, so a lap cut short
leaves the head-to-head with nothing behind it on any tool.

A fourth lap runs `/lfg` on a new feature, so the hands-off mode gets judged
against the hand-driven laps on the same codebase. `/lfg` pushes, opens a PR and
watches CI with bounded repair loops when a git remote exists; with no remote it
stops at local commits. Keep `ce-tiny-ticket` remote-less so it stays local.

### Install starting point

Install is two slash commands inside Claude Code:
`/plugin marketplace add EveryInc/compound-engineering-plugin`, then
`/plugin install compound-engineering`. The org capitalization differs from the
repo URL's `everyinc`; record whether that matters. The README also warns to
refresh the marketplace before updating, or you stay on the old version.

Claude Code is not present on a fresh machine and has to be installed before any
plugin step. Read the SpecKit and BMAD sections of the doc before the install
starts — their numbered logs are the baseline for what a bare `cogatest` VM
needs, including how Claude Code got onto it.

Installer findings are also input to
`marketing/fix-installer/make-the-readme-install-section-the-only-install-p`,
which owns the copy-pasteable install commands.

### Out of scope

Only the six-step loop and `/lfg` get trialled. Of the 36 skills, the ones
outside the loop — `/ce-debug` and the rest — are not the comparison target.
The other 14 agent hosts are named in `## Description` for completeness; only
the Claude Code install gets exercised.

What is worth comparing across the three tools gets decided once the docs exist,
not up front. Do not start a three-way matrix mid-trial.

Do not commit trial output, competitor notes, or the `tiny-ticket` source into
this repo. The scratch project stays in the VM. At `report-to-coga`, record the
doc link, that the section is done, and that the share happened — not what the
trial found.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
