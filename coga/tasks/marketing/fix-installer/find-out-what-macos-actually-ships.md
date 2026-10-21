---
title: Find out what macOS actually ships
status: draft
owner: zach
workflow: docs/with-review
---

## Description

Reconcile what the existing macOS install evidence establishes about `pip`,
`python3`, and `git`: which are usable binaries, which are Command Line Tools
(CLT) stubs, and what installation paths the available tools can support.
Use Apple's documentation, the existing repo evidence, and primary upstream
sources for any proposed bootstrap. Do not create or run another Mac or VM
environment, or edit the install instructions.

### Questions and acceptance

- Answer by machine state: a fresh machine without CLT, a machine with CLT,
  and a migrated machine whose installed dependencies must be identified.
  Record each observation's macOS version, architecture, CLT version when
  known, and source. Distinguish observed facts, documented guarantees,
  inferences, and unknowns; do not invent a per-release matrix when sources
  do not support one.
- Distinguish whether pip is present, whether it can install Coga directly
  under `[project].requires-python` in `pyproject.toml`, and whether it can
  bootstrap uv so uv can provision a supported interpreter. For the latter,
  verify the relevant uv version's Python requirement and macOS artifacts;
  an older Python's inability to run Coga does not settle this question.
- Check how `pip3` and `python3 -m pip` resolve, where a user installation
  writes executables, whether that destination is on PATH, and whether an
  `EXTERNALLY-MANAGED` restriction applies. Keep unverified possibilities
  as open questions rather than asserting that `pip install uv` succeeds.
- Add a sourced "Tool availability by machine state" section to
  `coga/tasks/marketing/fix-installer/test-and-fix-install-on-macos-and-windows/macos-walk-findings.md`.
  Preserve the dated walk evidence and identify any coverage gaps. This
  tracked findings attachment is the reviewable deliverable for the
  `docs/with-review` workflow; commit it before running a sweeping Coga
  command, following `coga/checkouts`.
- Link that answer from the two consuming install-path tickets named below.
  Keep evidence in the findings file and leave changes to the public install
  procedure with those tickets. Do not claim an unobserved machine state was
  tested.

## Context

### Purpose and scope

Nico asked on 2026-10-19 whether pip is native on macOS so the install flow
can install only missing dependencies. The owner decided on 2026-10-21 to
answer from documentation and existing runs, without another VM. The repo
already has relevant observations; the work is to source and reconcile them,
then answer the remaining pip and bootstrap questions.

### Required source reading

- Read `coga/tasks/marketing/fix-installer/test-and-fix-install-on-macos-and-windows/macos-walk-findings.md`,
  especially "Host facts", "Pre-walk findings", "Baseline (guest, before any
  install)", and both new-user walk records. Preserve the distinction between
  the no-CLT guest baseline and an already configured host.
- `coga/install` is cited rather than attached: read
  `docs/contexts/coga/install/SKILL.md`, "Prerequisites", "macOS: install the
  Command Line Tools first", and "Python is older than 3.11". Compare its
  current assertions with the dated evidence; `pyproject.toml`
  `[project].requires-python` owns Coga's supported Python floor.
- Read `scripts/clean-install/macos-walk.sh`, the `reset` and `walk` cases,
  for the harness's CLT removal and interpreter provisioning. Its comments
  are assertions to check against the run evidence, not proof that a fresh
  macOS installation has a working Python interpreter.
- `coga/tasks/marketing/fix-installer/affordable-macos-testing-on-owned-macs-and-per-min.md`
  describes a proposed owned-Mac test setup and is blocked pending a deployed
  target. Its Apple Silicon VM design and Intel attach-only route are not
  evidence of a completed fresh-machine run. A fresh user account also does
  not isolate machine-wide dependencies. Determine what the existing sources
  actually establish about migrated machines instead of assuming their tools.

### Consumers of the answer

- `coga/tasks/marketing/fix-installer/make-the-readme-install-section-the-only-install-p.md`
  owns giving surviving install facts a home; pass it a link to the sourced
  result alongside the existing CLT findings.
- `coga/tasks/marketing/fix-installer/separate-installing-coga-from-installing-its-depen.md`
  owns what the install section contains and consumes the direct-install and
  bootstrap answers. This research ticket does not choose that install flow.

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

## Superseded designs

### 2026-10-21 — Synthesize the evaluator review before launch

Superseded by: the machine-state questions, explicit sources, and findings-file
acceptance criteria in the current body.
Reason: the attended owner requested repair of the validation error. The
previous body assumed pip could help only when Python 3.11 was already present
and required a per-release answer without sufficient evidence. The evaluator's
substantive findings are incorporated above; its original assertions below
remain historical evidence to verify during the research step.

#### Description

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

#### Context

##### Why

- Nico asked for this first in the review on 2026-10-19, specifically whether
  `pip` is native on macOS.
- If `pip` is native the install can use it and leave uv as the opt-in path.
- Owner decision 2026-10-21: answer this from Apple's docs and the existing
  runs, which already cover both uv and pip. Do not run another VM.

##### What the repo already asserts

- `scripts/clean-install/macos-walk.sh` records both baseline facts: that
  `/usr/bin/git` is the shim a new user hits (`reset` case, near line 43 as of
  this writing), and that macOS ships `/usr/bin/python3` 3.9, below coga's
  floor, so the harness provisions 3.11 instead (`walk` case, near line 60).
- Those landed with `pin-python-3-11-in-the-macos-clean-install-harness` and
  `document-the-macos-command-line-tools-prerequisite`, both done.
- So the open question is narrower than the title: it is pip. Whether anything
  usable exists before the Command Line Tools, and whether they put `pip3` on
  PATH or leave only `python3 -m pip`.

##### Machine state is the variable

- The same `reset` case (near line 30) records that EC2 Mac AMIs ship Command
  Line Tools for their Homebrew, and deletes them so git behaves as it does on
  a new Mac.
- A machine that already has the tools has a real `python3` and a working
  `python3 -m pip`, so pip looks native on it; the VM walk found none. Confirm
  or kill that as the explanation of the disagreement.
- `affordable-macos-testing-on-owned-macs-and-per-min` designates disposable
  Apple Silicon VMs as the vessel for fresh-install tests and its Tart image
  has no Command Line Tools. It also records that a fresh user account does not
  isolate machine-wide dependencies, so a new account on a working Mac is the
  weaker test, not the VM.
- A VM cannot speak for a Mac set up by Migration Assistant, which carries the
  tools and Homebrew across. Most real new Macs look like that, so say which
  kind of Mac each answer describes.
- Intel has no fresh-install route today: the owned-Mac design can only attach
  to an Intel host and never resets it.

##### Where the answer lands

- The Command Line Tools trap and the tools-ship-3.9 fact are already listed on
  `test-and-fix-install-on-macos-and-windows` as orphan facts needing a
  surviving context, and
  `make-the-readme-install-section-the-only-install-p` owns giving them a home.
  Add the pip answer there rather than opening a second home for it.
- `separate-installing-coga-from-installing-its-depen` owns what the install
  section contains and is the consumer of this answer.

#### Evaluator review

I read the ticket cold, then verified every factual claim. Here's the assessment.

##### Verified as correct

- **`pyproject.toml:10`** is exactly `requires-python = ">=3.11"`. Precise.
- **All three `macos-walk.sh` citations hold** (`/Users/zach2179/dev/coga/scripts/clean-install/macos-walk.sh`, 90 lines): `reset` case line 43 is the git-shim echo; line 30 is the "EC2 Mac AMIs ship Command Line Tools for their Homebrew" comment with the deletion at line 35; `walk` case lines 59-61 carry the 3.9-below-floor/provision-3.11 comment. Module-plus-symbol shape with line numbers as drifting aids — correct convention.
- **Ownership boundaries are real and non-duplicative.** `separate-installing-coga-from-installing-its-depen.md` says verbatim "This ticket decides what the install section contains"; `make-the-readme-install-section-the-only-install-p.md` says "Before removing it, carry over the facts on that page that have no other home"; `test-and-fix-install-on-macos-and-windows/ticket.md` lines 135-138 do list "The macOS Command Line Tools trap … and that the CLT ships Python 3.9" as orphan-fact candidates. Every claim about the `affordable-macos-testing` design (no-CLT Tart image, arm64-only, Intel `attach` never resets, fresh account doesn't isolate) checks out too.
- **No citation justifies itself by size or token count.** Clean.

##### Findings that would change the work

**1. The two richest sources are uncited — this is the biggest problem.** The ticket says "the run evidence already in this repo" but cites only `macos-walk.sh`, whose comments are the harness author's *assertions*. The actual evidence is in two files the agent will not find:

- `/Users/zach2179/dev/coga/coga/tasks/marketing/fix-installer/test-and-fix-install-on-macos-and-windows/macos-walk-findings.md` (496 lines) holds the walked answer to exactly this question: a fresh macOS 26.6.2 arm64 baseline showing no CLT with `/usr/bin/git` and `/usr/bin/python3` as stubs, and a 2026-10-18 walk recording `python3 -m pip install coga` → `xcode-select: note: No developer tools were found, requesting install.` It also already corrected the stale `0.0.1` placeholder claim.
- `/Users/zach2179/dev/coga/docs/contexts/coga/install/SKILL.md` already documents the second answer: "On an older interpreter, `pip install coga` fails with `Could not find a version that satisfies the requirement coga` and `Requires-Python >=3.11` diagnostics", that CLT "provides Python 3.9 as `/usr/bin/python3`", and that a venv on an old interpreter doesn't help.

Cite both. Much of the "research" is sourcing and reconciling what's already written, not discovery — and the ticket's framing ("nobody has checked") will send an agent to Apple's docs to re-derive it.

**2. The Description's central inference is wrong as stated, and stated as settled.** It asserts "a native `pip` only helps if a 3.11 interpreter is already present." I checked PyPI: `uv` declares `requires-python = ">=3.8"` (uv 0.13.4). So on a Mac with CLT, `pip3 install uv` succeeds on Python 3.9, and uv then provisions 3.11 and installs coga. A native pip helps even with no 3.11 present — as a bootstrap for uv that avoids `curl … | sh`, which is precisely what `separate-installing-coga-from-installing-its-depen` would want to know. (`macos-walk-findings.md` dismissed uv-via-PyPI as "needs the absent Python" — true on the no-CLT machine, false on the CLT machine, which is the very split this ticket is about.) Re-pose it as a question and add `pip install uv` as a third sub-question.

**On your risk #8 specifically:** the reasoning holds narrowly — `pip install coga` on CLT 3.9 genuinely fails the `>=3.11` floor, and that's already verified and documented. But the leap from "can't install coga" to "a native pip doesn't help" does not hold. Prominence isn't the issue; correctness is.

**3. "Recorded per macOS version" is likely unachievable from the permitted sources,** so the done criterion can't be met as written. The repo's run evidence covers one macOS version (26.6.2) plus an unrecorded `amzn-ec2-macos-*` AMI, and Apple publishes no per-release table of CLT contents. The ticket's own best insight — "Machine state is the variable" — points at the right axis. Recommend restating as: answer per *machine state* (no-CLT / CLT-installed / Migration Assistant), recording the macOS version each observation came from, with "not documented by Apple; inferred from run X" an acceptable sourced answer. Otherwise "each claim carries the source it came from" pressures the agent to manufacture authority Apple never published.

##### Worth fixing before launch

**4. Two cited tickets no longer exist on disk.** `pin-python-3-11-in-the-macos-clean-install-harness` and `document-the-macos-command-line-tools-prerequisite` were done (`bdc189c14`, `2be274ee0`) then **deleted** (`8d62dcd6b`, `20f6dcfaa`). `find` and `grep` over the tree return nothing. "Both done" is historically true but unverifiable by an agent in the working tree. Drop the names — `macos-walk.sh` is the durable artifact and is already cited.

**5. `affordable-macos-testing-on-owned-macs-and-per-min` is `status: blocked`** and states "No local-Mac implementation has been made." The ticket cites it as established ("designates disposable Apple Silicon VMs as the vessel"). The content is accurate but it's a proposed design, not a capability. Say "proposes".

**6. Precision slip on the one fact at issue.** Context repeats `macos-walk.sh`'s loose "macOS ships `/usr/bin/python3` 3.9". The careful repo statement — in the orphan-facts list and confirmed by the baseline — is that `/usr/bin/python3` is a *stub* on a fresh Mac and the **CLT** ships 3.9. The whole ticket turns on that distinction; restating the loose version as settled is a hazard.

**7. Missing sub-question that decides the answer.** Even if `pip3` exists, Apple's framework Python installs `--user` into `~/Library/Python/3.9/bin`, which is not on the default PATH, and PEP 668 `EXTERNALLY-MANAGED` may block plain `pip install`. I grepped: the repo has **zero** evidence on either. The ticket asks "whether they put `pip3` on PATH" but not where pip *installs to*, which is what determines whether `pip3 install uv` actually works.

##### Workflow fit (#3)

`docs/with-review` is right in shape — peer-review's "spot-check anything load-bearing against the source it describes" is exactly what sourced desk research needs. One real tension: **the ticket never names a file for the answer to land in.** It says "add the pip answer there" (on `make-the-readme…`) and "the two install-path tickets have what they need" — i.e. the deliverable may be text in *sibling ticket bodies*. But `implement` requires a branch and `open-pr` requires a PR, and the workflow explicitly warns that the live ticket is "projected unstaged from control: … never stage or commit it." Editing sibling tickets is a control-plane edit, not a PR. Name a concrete committable path (a findings file beside `macos-walk-findings.md` is the obvious home). Also note: if the answer lands in `docs/contexts/coga/install/`, peer-review's cross-copy sync applies — there's a byte-identical packaged twin under `src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md`.

##### Contexts (#4)

No-attachment is defensible — the inputs are specific files, not standing rules. But `coga/install` is a genuine candidate, not as a rule set but because it already contains the answer-shaped prose the work must confirm or correct. Inline citation is enough; attachment is optional.

##### Scope (#6) and assumptions (#7)

Scope is fine — one question, one ticket, explicitly excludes editing install instructions. **No split warranted.** If anything it's under-scoped against its title; the Context admits this ("the open question is narrower than the title"), which is honest.

On the machine-state premise: it's sound and well-supported (baseline shows stubs, walk shows the CLT prompt), and the ticket correctly leaves room to be wrong — "Confirm or kill that as the explanation." That's the right framing. The inconsistency worth noting is that the ticket hedges this hypothesis properly while hard-asserting the pip-is-useless conclusion in the Description. Flip the second to match the first.

##### Prompt budget

Nothing warrants a trim. `task_context` at 1932 tokens is 39% of the 4954 total — just under your threshold, and 5132 B of its 7.5 KiB is the stock ticket guide. Author prose is ~2568 B, roughly 646 tokens, about 13% of the composed prompt. That's lean. `base_prompt` at 33% is the next largest and is fixed overhead. The correct move here is to **add** the two missing citations, not cut.
