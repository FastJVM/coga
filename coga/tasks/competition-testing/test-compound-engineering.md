---
title: Test Compound Engineering
status: done
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

## State

**Closed 2026-10-26 at Zach's direction.** Laps 0, 1 and 2 run; laps 3 and 4
stopped by owner decision once the knowledge-capture question had an answer
he considered sufficient.

### Closing record

- Deliverable: **"Compound Engineering — Testing Breakdown (Oct 26, 2026)"**
  — https://docs.google.com/document/d/10QVxLKiIPCe-mhtLl9PtVIh3up7cDpPT4cp7zDbnS9M/edit
  In the `coga-competitors` Drive folder beside the SpecKit and BMAD
  write-ups. Written by Zach from his Pocket recording in a separate
  session.
- Section is done. Zach submitted it to Nico for review.
- **Share verified, not assumed:** `nicolas@fastjvm.com` holds `writer` on
  both that doc and the "Coga Competitor Tests" running log
  (checked 2026-10-26). The ticket's share obligation, carried as the last
  of the three trials, is discharged.
- Running entry log, 36 entries:
  https://claude.ai/code/artifact/7ce77c38-b019-46e6-8cf9-38805552f8b3

### Not run, and what it costs

- **Lap 3 (`validate`).** The one case where the stored learning and the
  existing code point in opposite directions — lap 2's learning says don't
  use `Path.glob`, and `available_workflows` in `create.py` still does.
  It would have settled attribution decisively. The write-up's conclusion
  rests on lap 2's negative evidence instead.
- **Lap 4 (`/lfg`).** So the ticket's question about whether unattended
  mode is worth anything in practice has no answer.
- Two relay checks: whether "(Recommended)" is instructed by the skill
  file, and the bare-Claude control for entry 17.

Zach will open new tickets for anything that surfaces from this work.

## Observed — lap 0, install (2026-10-24)

VM: `cogatest@cogatests-Virtual-Machine`, bare macOS.

1. Zach ran `python3 -V`, which triggered the Xcode Command Line Tools
   install prompt. **Carried over from the BMAD routine, not demanded by
   Compound Engineering** — he confirmed this. Nothing in CE has asked for
   Python or the CLI tools so far. Do not list them as CE prerequisites.
2. `curl -fsSL https://claude.ai/install.sh | bash` installed Claude Code
   2.1.310 to `~/.local/bin/claude`. Single command, no interview.
3. The installer printed a setup note that `~/.local/bin` is not on PATH,
   with the `echo 'export PATH=...' >> ~/.zshrc` fix — and then printed
   `✅ Installation complete!` *below* that note. The success line lands last
   while `claude` is still not runnable. Zach knew to paste the fix. Someone
   who skims to the checkmark gets command-not-found.

4. Claude Code opened on Opus 5.5 / Claude Max with an auto-mode permission
   notice. Zach pasted the README's two install lines together.
   `/plugin marketplace add` consumed the whole paste as its source argument,
   so the Add Marketplace field held
   `EveryInc/compound-engineering-plugin /plugin install compound-engineering`
   and failed with "not a valid GitHub owner/repo shorthand". The error text
   is good about valid forms but does not notice the argument contains a
   second slash command. Fix is to enter the shorthand alone, then run the
   install command separately.

   This is the sharpest install finding so far and it generalizes: a
   multi-line install block breaks when the first command opens an
   interactive prompt. Direct input to the installer ticket.

5. Entering the shorthand alone worked. **`EveryInc` capitalization does not
   matter** — the marketplace added fine. Question closed.
6. `/plugin install compound-engineering` works exactly as the README writes
   it; Claude Code expanded it to
   `compound-engineering@compound-engineering-plugin` itself. Not a
   documentation error. So the install-doc tally is one real problem, the
   two-line paste, not two.
7. The install dialog's entire disclosure is "Components will be discovered
   at installation" — directly under a notice saying Anthropic cannot verify
   what a plugin contains and you should trust it before installing. 36
   skills and six commands land without being named at the decision point.
   Plugin author shown as Kieran Klaassen and Trevin Chow. Scope options
   offered: user, project, local. Zach took user scope on the dedicated VM.

   Contrast for the write-up: Coga's position is that what an agent works
   from is inspectable before it runs. Here the trust decision comes first
   and the contents after.

8. Typing `/ce` lists the skills unorganized. Of the six loop commands only
   `ce-plan` and `ce-work` are in the visible 17, at positions 2 and 3,
   interleaved with `ce-pov`, `ce-debug`, `ce-proof`, `ce-sweep`,
   `ce-commit`. Nothing marks the loop or its order. `/ce-setup` is listed
   but describes itself as "Check Compound Engineering health and repo-local
   config" — a diagnostic, not a starting point. Only the README says to run
   it first. Descriptions assume undefined vocabulary: Compound Pack, oracle
   panel, `lfg`-ready plan.

   Zach's framing, which leads the artifact entry: the tool is confusing in
   the terminal, the only place to find the first step and the core loop is
   the README, and BMAD was by far the most helpful at showing you what you
   needed right there in the terminal.

   Unverified: whether that completion list scrolled. `ce-brainstorm`,
   `ce-compound`, `ce-simplify-code`, `ce-code-review` were not in the
   visible 17. If a `/ce` filter truly omits `ce-brainstorm`, sharpen this.

## Observed — lap 0, setup (2026-10-25)

Plugin v3.32.1. Skills cached at
`~/.claude/plugins/cache/compound-engineering-plugin/compound-engineering/3.32.1/skills`.

9. `/ce-setup` in a non-git directory reported the directory isn't a repo,
   named what git unlocks, said it was skipping repo-local fixes and why,
   and offered to run `git init`. Vindicates not pre-running it.
10. Five of six optional tools missing (`agent-browser`, `gh`, `ast-grep`,
    `ffmpeg`, `node`; only `jq` present). Setup completed anyway: "Install
    optional tools only for the workflows you use." Node is optional here,
    where BMAD required node 24 outright.
11. Two consent prompts, each naming exactly what it would write. Decline
    paths are the good part: config "defaults still apply", scratch ignore
    "a skill will offer this at its first write" — deferred, not buried.
12. `docs_root` default is `docs/`, volunteered unprompted. Three locations
    with different durability: `.compound-engineering/config.yaml`
    (committed), `.context/compound-engineering/` (gitignored scratch),
    `docs/` (artifacts and learnings).
13. Skipped line: "agent-instructions offers (no AGENTS.md or CLAUDE.md in
    the repo; setup doesn't create one)." It saw the gap and refused to
    invent project instructions. **Exact inverse of SpecKit's constitution**,
    which the SpecKit write-up called the sharpest contrast with Coga.

Standing read at end of lap 0: CE's install and setup *conduct* is better
than both siblings — thinner prerequisites, graceful degradation, consent
before each write, no unbidden generation. The orientation problem in entry
8 is real but separate from conduct. Keep both in the write-up.

## Observed — lap 1, brainstorm (2026-10-25)

15. Skills cache holds 37 entries, one being `CODING_STANDARDS.md`: **36
    skills exactly**. All six loop commands present, plus `lfg` and `wtf`.
    So the four missing from the `/ce` completion list were below the fold
    of a list ordered neither alphabetically nor by the loop. Contents are
    inspectable after install, which softens entry 7. A
    `ce-compound-refresh` exists alongside `ce-compound`.
16. `/ce-brainstorm` asks one question at a time. The first arrived with a
    **pre-filled answer in the input box**, one tab from submitted, and the
    suggestion was broader than the truth. Later questions came as explicit
    options, some tagged "(Recommended)", which is milder — visible, and
    declining costs a keypress.
17. **Zach's framing, and the most important thing said in this trial.**
    All three tools are prompt files over the same model, so when CE asks a
    sharp question that is Claude generating it. What a skill controls is
    whether it asks, when, in what format, what posture. Consequence: the
    description deliberately kept the hole BMAD caught, and CE caught it
    too — which means the simplest explanation is the model finds it and
    neither plugin earns the credit. "It found a real gap" is currently
    unsupported for all three tools. Control added to the relay: the same
    paragraph to bare Claude, no plugin.
18. **Headline finding.** Zach: CE gave the best-guided brainstorm of the
    three and got him closest to his original intent — seven questions,
    mostly enter-presses. But because he was selecting rather than typing,
    he never enumerated his fields and **forgot `--owner` and a created
    date**, both of which he had specified in the BMAD run when question 6
    was open prose ("title, status, workflow, created date, owner").
    Recognition versus recall: multiple choice is bounded by the tool's
    imagination. Decision: **let the omission ship as evidence.**
    Live test: whether a later loop step catches the missing fields.

19. **Half-catch, and the split is informative.** The brainstorm synthesis
    flagged the missing created date by name, traced its consequence
    (slug-only filenames mean `list` cannot sort by creation order), and
    invited a fix. Owner appeared nowhere. Created date was derivable from
    the design; owner existed only in Zach's head and was never in the
    input. Handling: added the created date, said nothing about owner, so
    the build ships half-right with a record of which half was
    recoverable. Also credit: "I'll skip an approach menu" when choices
    already pointed one way, and an explicit out-of-scope list.
20. **Nothing sequences the loop.** The brainstorm ended "Confirm and I'll
    write the requirements-only plan next" — CE was about to produce the
    plan without `/ce-plan` running. No state, no gate, no check that an
    earlier step ran; the loop lives in the README. Spec Kit was the
    opposite extreme and refused out-of-order commands. This matters
    because the compounding thesis depends on `/ce-compound`, which is
    optional, unprompted and last — where people stop. Raises the stakes
    on lap 4: `/lfg` is the only mechanism that guarantees the loop
    completes, not merely an unattended-mode curiosity.

21. **CE's internal reasoning docs leaked.** A `cat` in a command that
    exited 1 printed `ce-plan/references/synthesis-summary.md` verbatim —
    CE's own prompt engineering, including "Stage 1 is an internal
    three-bucket draft... The user only sees stage 2" and "it just doesn't
    reach the user verbatim". Settles entry 17: the prompts are readable.
    Clean contrast — CE deliberately withholds part of its reasoning;
    Coga's position is that what the agent works from is findable and
    correctable.
22. `/ce-plan` replays decisions **with provenance**: "You picked each from
    a set of options I showed you, and for the last two you moved on
    without objecting." Self-monitoring the entry-18 failure mode.
    **Confirmed with Zach: he did not prompt the created-date catch — CE
    found it unaided.** But the flag never converted: he didn't answer,
    and `/ce-plan` carried forward "title, status, workflow" without
    re-raising it. Asymmetry worth keeping — passive acceptance is tracked
    for menus, not for concerns raised in prose. Silence became a no.
23. **Six steps, one accumulating session, no context guidance.** Zach's
    question. Three-way: BMAD told him to exit and start fresh between
    phases; Coga does it per ticket by construction; CE says nothing. Its
    implicit answer is `docs/solutions/` plus a `ce-handoff` skill, neither
    in the loop nor prompted. Won't bite on tiny-ticket; open question at
    scale.
24. **Zach's framing.** It hides reasoning and is largely agent-led. The
    process is efficient but is trying to automate everything — plausibly
    good for small projects, a genuine open question for larger ones. The
    pieces: multiple choice over prose, pre-marked recommendations, a
    pre-written answer, a withheld reasoning stage, and a loop that
    continues itself unasked. Individually conveniences, together a
    posture.

25. **The loop chains itself, by instruction not by state.** `/ce-work` ran
    on into simplification and then review with nothing typed — "starting
    the **required** code review". So entry 20 is amended: no gate, but
    real propagation. Five parallel review agents (quality, reuse,
    comments, test value, efficiency) in 15-19s. It applied three findings
    and declined three with reasons — judgment, though still deciding
    without asking, which is structurally BMAD's flaw with more
    transparency.
26. **The chain stopped one step short of `/ce-compound`.** Ended at "Still
    on your side" with install notes and a PR offer; compound never
    mentioned. The same output held three cross-lap notes for laps 2 and 3.
    Entry 20's worry confirmed: propagation covers four steps and stops at
    the one the product's claim rests on.
27. **Three for three on the broken command, and the first to admit it.**
    "I only installed it into a throwaway [virtualenv] for testing" —
    `tiny-ticket` does not run for Zach; it's the macOS
    `~/Library/Python/3.x/bin` trap. But CE named the remaining step and
    the directory, where SpecKit and BMAD shipped broken CLIs silently.
    Honest headline: all three failed, one disclosed. Does make the earlier
    "works correctly end to end" read as overclaiming.
28. **The review did real work.** Four defects, each reproduced by an
    independent validator before fixing. Best moment of the trial: it
    refused the reviewer's slug-shortening suggestion because it would have
    changed Zach's slug-only naming rule, explained why, and offered the
    choice back. Also self-reported stray files its own tests wrote.
29. **`/ce-compound` wrote exactly one learning**, chose it unilaterally,
    and declined a second ("mostly the same cleanup, so I'd skip it").
    Of the review's three cross-lap notes, one survived (open task files as
    UTF-8); the walk-up collision and JSON-style quoted frontmatter did
    not. Roughly one in four, with no flag that anything was dropped.
    Strong parts: a separate agent verified every claim, line reference and
    test name against the code and corrected one; the file records what
    *didn't* work. No pointer added to the folder from anywhere.
    **Zach's framing:** you aren't in control of what gets saved. Coga is
    reactive — you notice a need and write a context — rather than guided.
    Both failure modes belong in the write-up: CE captures even when you'd
    skip it but may capture the wrong subset silently; Coga captures what
    you judged worth keeping but only when you notice.

`/ce-plan` also committed to the three-for-three test explicitly: "a
working `tiny-ticket` command on your PATH", installed as an editable
Python package "rather than a loose script dropped into `~/.local/bin`".
Python chosen because Python 3 is present and Node isn't. It said the right
thing; shipping it is the test.

Behaviors worth crediting from the same stretch: CE traced consequences
rather than transcribing — choosing slug-only names immediately produced a
collision question, and "found like git" produced a first-run question.
It also labels the scope cost of options ("Adds an init command to this
pass"). Recommendations are not uniformly heavier: three leaned toward more
machinery, two toward less. Zach declined one (numeric IDs plus a counter),
which is the premise of picking `tiny-ticket` working as intended.

Serial-vs-batched is a real tradeoff for the write-up. CE asks one at a
time, which is why it could adapt question 6 to answer 5; BMAD batched
seven, which showed the whole shape at once. Watch whether serial becomes
an endurance test at scale.

## Observed — lap 2, list (2026-10-25)

Entries 30-36 in the artifact. The ones that matter:

- **30.** Zach's interim read: CE is the best of the three because it works
  in laps, which is what he values in Coga. Supported by CE's own
  behavior — it deferred cleanups "to the `list`/`validate` pass" and
  wrote forward-looking sections. Caveat attached: at that point nothing
  had been read back.
- **31.** He nearly ran lap 2 in lap 1's window. **CE's default usage
  pattern makes its own central claim untestable** — nothing says to
  restart, and a same-session lap 2 recalls everything from conversation.
  Would look identical with an empty `docs/solutions/`.
- **32.** Every loop handoff is offered — plan→work came as a menu with
  "Start ce-work (Recommended)" — **except review→compound, which offers
  nothing.** Sharper and fairer than "nothing sequences the loop". Also:
  `/ce-brainstorm` has its own plan-write phase, so two of the six steps
  overlap and which runs depends on whether you type "confirmed" or a
  slash command.
- **33.** Central question, qualified answer. Lap 2 shipped a *fresh*
  encoding bug (UTF-8 BOM) caught by review. Final code is right —
  `listing.py:53` is `read_bytes().decode("utf-8-sig", errors="replace")`
  — and the lap-2 plan handled locales in detail, citing
  `PYTHONUTF8=0`. But the plan credits *"the existing test ... already
  exercises that locale"*, so `tests/` fully explains it. Learning
  sufficient, not necessary. It demonstrably did not prevent the repeat.
- **34.** CE found an open design question (broken symlinks skipped
  silently) and said it **"isn't recorded anywhere else, since there's no
  PR"** — naming its own missing durable record. `docs/` was flagged
  uncommitted after both laps and committed only on request; it scanned
  config for secrets first, unasked.
- **35.** Plan files annotate decisions with provenance —
  "(session-settled: user-approved — chosen over ...)". Verification is
  consistent everywhere: doc-vs-code checks, a 14s repo-claims verifier,
  five parallel review lenses, and disclosure that no outside-model
  reviewer was available.
- **36.** Lap 2's compound step **read the existing learning**, found it
  stale, judged its guidance still correct, declined to edit it, named
  `/ce-compound-refresh`, and reused its taxonomy values. Its reason for
  writing a new one answers the attribution critique directly: a code
  comment "wouldn't stop the next command from making the same mistake",
  and `available_workflows` still uses `glob`. Verified with real
  experiments on Python 3.9.6.

Standing read after two laps: the **verification discipline** is CE's
strongest feature and neither sibling has anything like it. The
**compounding claim** is still unproven — every apparent memory has been
recoverable from the repo — but lap 2's compound step set up the one case
where it won't be.

## Working rule

Zach cannot copy from this session into the VM. **Any command the agent wants
run goes into the command relay artifact**, not into chat.

Relay: https://claude.ai/code/artifact/e525ce43-3a35-4922-8f88-65dfdd96611f
Source: `scratchpad/ce-command-relay.html`. Separate from the entry log on
purpose, mirroring the BMAD trial's two-artifact pattern — the log is for
reading back before recording, the relay is for pasting.

In the VM, `claude.ai/code/artifacts` lists both by title; no URL typing.

Pending checks in the relay, not yet run: `cat
.compound-engineering/config.yaml` (is `docs_root` a commented line, not just
a one-time summary mention) and an `ls` of the skills cache (real skill
count; whether `ce-brainstorm` and `ce-compound` exist, per entry 8).

## Lap 1 prompt decision

The relay's lap-1 `/ce-brainstorm` argument is Zach's BMAD description
**verbatim**, including the gap in `tiny-ticket create )` where the argument
was never named — the exact hole BMAD caught. His seven BMAD answers are
deliberately withheld. Only addition is one sentence scoping the pass to
`create`. Same starting line for both tools, so "did it find real gaps" is a
fair head-to-head.

Parked for "what it does that Coga does not", from the skill list only:
`ce-sweep` pulls Slack and GitHub Issues into a plan; `ce-handoff` writes a
session handoff for the next agent. Non-loop skills are out of scope to
trial, but these are candidates the write-up owes an answer on.

Read-across: so far the thinnest prerequisite chain of the three trials.
SpecKit needed Claude Code installed mid-flow after `specify init` failed;
BMAD needed Xcode CLI tools, uv, Python 3.12 and node 24. CE has needed
Claude Code alone.

The PATH-ordering point is input to
`marketing/fix-installer/make-the-readme-install-section-the-only-install-p` —
same failure surface exists in Coga's install.

## Baseline read from the doc (2026-10-24)

Read the SpecKit and BMAD sections before install. What a bare `cogatest` VM
needed in the earlier trials:

- SpecKit: Claude Code was missing, so `specify init --integration claude`
  failed and had to be rerun after installing it.
- BMAD: Xcode Command Line Tools, uv, Python 3.12, node 24. Zach noted uv was
  hard to find because the README put it slightly outside the install section.
- BMAD's CLI did not work until `uv tool install` was run, which was not
  documented anywhere.

Both prior trials ended with a `tiny-ticket` that did not behave the way Zach
wanted, despite heavy planning and review. That is the standing result the
compound-engineering laps get measured against.

## How the write-up gets produced (Zach, 2026-10-24)

Changed from the ticket's "draft per lap" assumption. We run install and the
laps together in session; Zach records his learnings into Pocket once
`tiny-ticket` is finished; then he asks the agent to read that recording and
summarize it into a 1-2 page document with a "comparison to Coga" section.

So the Pocket recording is the primary source for the write-up, not
per-lap drafts. The session discussion is a second source, which is why the
agent keeps live notes here — the recording has Zach's conclusions, the
session has how we got there.

The deliverable is a **separate Drive doc**, not a section of the running-log
doc. It sits beside the two siblings in the `coga-competitors` folder
(Drive parent `1IcrA_s6z49h8SvsOuJeCQ5WjZYAVty89`):

- `Spec Kit Test Findings` — `1GIPYmBTvE-dJGiEeX-BqN9Y2Cwu0yVRPRc5FCNo4k1U`
- `BMAD Method — Testing Breakdown (Oct 24, 2026)` —
  `1SfnjQWseHbwX9xSoHi78zRyoATOFUAzo7bynMcwWYa4`

Both read. The BMAD doc is the closer model, since it was itself produced from
a Pocket recording: bolded source/scope header, "What was tested", a few
thematic sections, a differs-from-Coga section split into where each tool is
ahead, a bottom line, and a footer saying it came from the recording with
tool names normalized. Roughly a page and a half each. Match that register.

**The doc does not get written in this session.** Zach has Claude analyze the
Pocket recording separately, and a later agent session produces the artifact.
This session's job is the trial itself and the notes below. Drive `create_file`
with markdown `textContent` makes a real Doc when that session gets there. The
ticket's no-replacement-Doc rule is about the screenshot running log, which is
a different artifact and stays as is.

## Running entry log artifact

https://claude.ai/code/artifact/7ce77c38-b019-46e6-8cf9-38805552f8b3

Source file: `scratchpad/ce-trial-log.html` in the session scratchpad.
Republish the same path to keep the URL; from another session pass the URL as
`url`.

As in the BMAD trial, the agent keeps this published entry log during the
laps. Zach reads down it to put the findings in his own words before
recording; it is not the deliverable and not a draft of one. Entries are
numbered in the order things happened and tagged worked / friction / question
closed / reads-against-Coga. Carries lap-0 entries 1-7 as of 2026-10-24.

## Lap plan

1. Lap 0 — install: Claude Code, then the two `/plugin` commands. Record every
   prerequisite in order.
2. Lap 1 — `create`: full six-step loop. First `/ce-compound` write.
3. Lap 2 — `list`: watch whether `/ce-brainstorm` and `/ce-plan` visibly read
   back lap 1's learnings.
4. Lap 3 — `validate`: same watch, with two laps of stored learnings behind it.
5. Lap 4 — `/lfg` on a new feature, no git remote.

## Open

- Which `cogatest` VM.
- Nico's account for the final share.
