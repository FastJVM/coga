---
title: Test Kiro
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

Zach installs the Kiro IDE and runs a real task through it end to end in a VM;
the agent keeps the running entry log and discusses findings with him. Kiro is
AWS's agentic development environment — a desktop IDE plus CLI, web and mobile
clients that share one `.kiro/` project directory. It is built around three
things: **specs**, a three-phase plan (`requirements.md` → `design.md` →
`tasks.md`); **steering files**, persistent project context under
`.kiro/steering/` with a per-file inclusion policy; and **agent hooks**, actions
fired by file changes, tool use or task completion.

The whole tool is the subject, not one feature. What the trial watches for:

- The installation experience end to end.
- How the spec phases compare to Coga workflows, steps and tickets.
- How steering files store and reuse project context, against what Coga does
  through contexts, skills, and the retro and dream passes.
- What it does that Coga does not. Hooks are the clearest candidate: Coga's
  recurring jobs fire on a schedule or on repo state, and nothing in Coga fires
  on a file change or a tool use.

The trial runs on a fresh VM with nothing installed. Install coverage therefore
starts at the prerequisites, not at the Kiro download. Record what it demanded,
in order.

Done when Zach has run the trial to a point he considers finished and has
published his write-up in the `coga-competitors` Drive folder beside the
SpecKit, BMAD and Compound Engineering write-ups, with Nico's access verified.

Why now: this is the fourth trial, and the first against a product rather than a
prompt pack layered on someone else's agent host. Steering files are also the
closest thing any competitor ships to Coga's `contexts:` — a per-file inclusion
policy over durable project knowledge — so this is the sharpest read available
on whether that shape is a Coga idea or table stakes.

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

Zach runs Kiro hands-on in a VM, pastes screenshots into the session, and notes
what he sees. The agent keeps the running entry log, discusses findings with
him, and flags what looks weak. The agent does not run Kiro. This is information
gathering, not a staged project — follow Zach's lead on what to look at next.

The VM is one of the spare `cogatest` UTM machines. At launch Zach confirms both
which machine and that it has been reverted to a bare snapshot. This is not a
formality: the Compound Engineering trial left Claude Code, a Python venv and
`ce-tiny-ticket` on `cogatests-Virtual-Machine` on 2026-10-24, and running the
install on a dirty machine voids the prerequisite comparison across all four
tools. Nothing else carries over from the SpecKit, BMAD or Compound Engineering
trials except what is already in those write-ups and in this ticket.

Do not draft findings for a lap Zach has not run yet. Entries come from his
screenshots and notes, not from Kiro's docs — a plausible observation he did not
observe is a failure, not a head start.

The workflow's `agent-produces` step means the two artifacts described below,
not a draft of the write-up. Read its "draft the deliverable" wording that way.

`coga-dev/principles` is attached to keep the Coga-side claims in the log and in
discussion honest — it is what stops a comparison sentence from overshooting.
It does not describe the Coga mechanisms this trial compares against; those are
in **What Kiro is being compared against** below.

### Where findings go

Three artifacts, with different owners.

**The agent owns the running entry log.** A numbered log of what happened, one
entry per observation, kept as a claude.ai artifact and updated live during the
trial. Compound Engineering's ran to 36 entries. Record the artifact URL on the
blackboard.

**The agent owns the command relay.** Zach cannot copy from this session into
the VM. Any command or prompt the agent wants run goes into a separate command
relay artifact for pasting — never into chat. Keep it separate from the entry
log on purpose: the log is for reading back before recording, the relay is for
pasting. In the VM, `claude.ai/code/artifacts` lists both by title, so there is
no URL to type. This is a property of Zach's VM setup, carried from the BMAD and
Compound Engineering trials, and it binds harder here — Kiro is a GUI IDE with
long spec prompts to paste.

**Zach owns the write-up.** He records his thinking in Pocket and produces the
flow-of-thought write-up from that recording in a separate session. The agent
does not draft it. The finished doc lands in the `coga-competitors` Drive
folder beside the other three.

That ordering means this ticket cannot close from inside the trial session. At
`report-to-coga`, record the entry-log and relay URLs and that the trial is
finished; the write-up link and the share check get added when the doc exists.

`FastJVM/coga` is public, so findings stay in the log and the doc; the
blackboard stays a pointer.

On sharing: verify `nicolas@fastjvm.com` has access rather than assuming it. He
held `writer` on the Compound Engineering write-up and on the "Coga Competitor
Tests" running doc as of 2026-10-26, but a new doc is a new object with its own
permissions. Share by named account, not by switching on link-sharing.

### The trial task

Build `tiny-ticket`: a command-line tool that stores tasks as markdown files
with YAML frontmatter, with three commands — create a task, list tasks, and
validate the files. Validation enforces that `status` is one of a fixed set and
that any non-draft task has a workflow.

This is the same build all three siblings ran. Zach picked it because he knows
the correct design cold, so a bad plan is obvious on sight. Keep the product
name `tiny-ticket` and use the project directory `kiro-tiny-ticket`.

The starting prompt is fixed, not freshly written. Lap 1 feeds Kiro Zach's BMAD
description verbatim — including the gap in `tiny-ticket create )` where the
argument was never named, which is the exact hole BMAD caught — plus one
sentence scoping the pass to `create`. Compound Engineering got that same
starting line, so "did it find the real gaps" is a fair head-to-head; a fourth
tool handed a better-written prompt breaks it. The text is in the Compound
Engineering ticket's blackboard under **Lap 1 prompt decision**.

### Why the trial runs in laps

One lap per `tiny-ticket` command: lap 1 `create`, lap 2 `list`, lap 3
`validate`. How many laps actually run is Zach's call — the sibling stopped at
lap 2 once the question had an answer he considered sufficient.

What is not optional is that the laps share one VM and one `kiro-tiny-ticket`
directory. `.kiro/` has to survive between laps or there is nothing for a later
spec or steering file to read back, and the reuse half of the tool goes
untested — which is how SpecKit and BMAD both ended with no evidence on the
claim at all.

What to watch across laps: whether stored steering visibly changes later output,
and whether what got captured was worth capturing. A single build exercises only
the write half.

### What the docs claim

Carry these in so the trial can check them rather than restate them. Where the
trial contradicts a claim, the contradiction is the finding.

- **Steering** lives in `.kiro/steering/*.md` for a workspace and
  `~/.kiro/steering/` globally, with workspace winning on conflict. Kiro
  generates three defaults from a Generate Steering Docs button: `product.md`,
  `tech.md`, `structure.md`. Each file declares one of four `inclusion:` modes
  in YAML frontmatter: `always` (the default), `fileMatch`, `manual`, and
  `auto`. Verified against kiro.dev on 2026-10-29 — the four-mode shape
  resembles Cursor's rule types closely enough to be worth not taking on
  trust. Worth watching: what the generated defaults actually contain, and
  whether any mode other than `always` gets used in practice.
- **Specs** gate on a human between phases and produce `requirements.md`,
  `design.md` and `tasks.md`. Kiro claims it groups independent tasks into
  concurrent "waves".
- **Hooks** fire on agent file changes, tool use or task completion.

A feature that reads well in the docs and goes unused in three laps is a
finding, not a gap in the trial.

### What Kiro is being compared against

The Coga side of each comparison, since `coga-dev/principles` carries the
philosophy and not the mechanisms:

- **Contexts** are domain-knowledge files a ticket names in `contexts:`. Every
  one is inlined in full into every launch prompt for every step. There is no
  conditional or on-demand mode — the choice is attach or don't, and the
  discipline is to copy the one needed fact into the ticket instead of
  attaching the whole file. That is the direct comparison with steering's four
  inclusion modes, and Kiro may well have the better answer here.
- **Skills** are process knowledge attached to a workflow step rather than to a
  ticket, so they load only on the step that needs them.
- **Retro** runs after a task finishes and writes what was learned back into
  contexts and skills.
- **Dream** is a periodic pass that reads across finished work and proposes new
  tickets and contexts from it.

Retro and dream are the closest analogues to a steering file getting updated
mid-project. Specs compare against workflows, steps and the ticket body. Hooks
compare against nothing on trigger, as `## Description` says.

### Install starting point

The IDE only — download the desktop installer from kiro.dev and run it. Sign-in
offers Google, GitHub, AWS Builder ID, or an org identity; no AWS account is
strictly required. Zach picks which at launch.

Kiro's free tier is 50 credits; Pro is $20 per user per month for 1,000
credits. Both checked on kiro.dev 2026-10-29 and both perishable — reconfirm
rather than quoting this. Nobody has measured what one lap costs, in this trial
or the siblings, so whether 50 credits covers three laps is unknown rather than
known-insufficient. Decide before lap 1 whether to pay, and record the actual
burn per lap — that number is itself a finding, and it is the only credible
cost comparison the four write-ups will have.

Read the SpecKit, BMAD and Compound Engineering sections of the "Coga Competitor
Tests" running doc —
https://docs.google.com/document/d/19qnSHqN2eH5e66peQ7X-R6NPIg6IPHc0wsS3cBxUEuM/edit
— before the install starts — their numbered logs are the
baseline for what a bare `cogatest` VM needs. Kiro is a desktop app rather than
a terminal install, so expect that baseline to diverge early.

Install friction is directly useful to Coga's own install docs. Record it even
where it is not a Kiro-versus-Coga comparison, and route it to the `v1/` install
queue — `v1/26-make-the-readme-install-section-the-only-install-p` owns the
copy-pasteable install commands — rather than letting it die in the entry log.

### Out of scope

The CLI, web and mobile clients are not exercised. They share `.kiro/`, so they
are worth a sentence in the write-up, but only the IDE gets trialled. One docs
fact to note rather than test: CLI V3 supports all four steering inclusion
modes, V1 and V2 only some.

What is worth comparing across the four tools gets decided once all four
write-ups exist, not up front. Do not start a four-way matrix mid-trial.

Do not commit trial output, competitor notes, or the `tiny-ticket` source into
this repo. The scratch project stays in the VM. At `report-to-coga`, record
links and status — the entry-log and relay URLs, and that the trial is
finished — not what the trial found.

<!-- coga:blackboard -->

## State

`agent-produces` opened 2026-10-29. Both artifacts the step owns are built and
published. Nothing observed yet — no lap has run.

## Artifacts

- **Running entry log** — https://claude.ai/code/artifact/d3266b10-1cf1-45ed-98ba-6f709cb3d8cd
  Source: `scratchpad/kiro-trial-log.html`. Republish the same path to keep the
  URL; from another session pass the URL as `url`. Carries the scaffold, the
  tag legend, the prior-trial prerequisite baseline, and the five docs claims
  to check. Zero entries.
- **Command relay** — https://claude.ai/code/artifact/6bec366c-0131-4423-ba10-aa4db25c96aa
  Source: `scratchpad/kiro-command-relay.html`. Four pending items: R1 bare
  snapshot baseline, R2 the lap-1 prompt, R3 steering capture, R4 spec output
  size.

## Working rule

Zach cannot copy from this session into the VM. Any command or prompt the agent
wants run goes into the relay, never into chat. In the VM both artifacts are
listed by title at `claude.ai/code/artifacts`.

## Lap 1 prompt decision

R2 is Zach's BMAD description verbatim, including the gap in `tiny-ticket
create )`, plus the same scoping sentence Compound Engineering got. Source is
the CE section of the running doc, which records the exact text CE was handed.
Do not repair the typo and do not pre-answer Kiro's questions.

## Baseline read from the running doc (2026-10-29)

Read the SpecKit, BMAD and CE sections before install. Prerequisite chains:
SpecKit needed Claude Code, discovered only after `specify init` failed. BMAD
needed Xcode CLI tools, uv, Python 3.12 and node 24, and its CLI did not work
until an undocumented `uv tool install`. CE needed Claude Code alone.

Two install failures worth watching for a Kiro equivalent: CE's two-line paste
fed the second command to the first as an argument, and its installer printed
success below the PATH warning. Both are input to
`v1/26-make-the-readme-install-section-the-only-install-p`.

Standing result all three siblings share: `tiny-ticket` did not work the way
Zach wanted at the end, despite heavy planning and review.

R1 avoids running `python3 -V`, which is what triggered the Xcode CLI tools
prompt in the CE trial and would contaminate the prerequisite comparison.

## Lap plan

1. Lap 0 — install from the bare snapshot through sign-in. Record every demand
   in order, and the credit balance before lap 1.
2. Lap 1 — `create`: full spec cycle, Generate Steering Docs, record the burn.
3. Lap 2 — `list`: watch whether stored steering visibly changes the output.
4. Lap 3 — `validate`: same watch with two laps of steering behind it.

Laps share one VM and one `kiro-tiny-ticket` directory. How many run is Zach's
call.

## How the write-up gets produced

Zach records his thinking in Pocket and produces the write-up from that
recording in a separate session. The agent does not draft it. This session's
job is the trial and the entry log.

## Open — needed before lap 0

- Which `cogatest` VM, and confirmation it is reverted to a bare snapshot.
- Which sign-in: Google, GitHub, AWS Builder ID, or org identity.
- Free tier or Pro, decided before lap 1.
