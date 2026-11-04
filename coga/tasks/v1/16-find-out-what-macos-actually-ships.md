---
title: Find out what macOS actually ships
status: done
owner: zach
agent: claude
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
---

## Description

Reconcile what the existing macOS install evidence establishes about `pip`,
`python3`, and `git`: which are usable binaries, which are Command Line Tools
(CLT) stubs, and what installation paths the available tools can support.
Use Apple's documentation, the existing repo evidence, and primary upstream
sources for any proposed bootstrap. Read-only checks on the machine running
this ticket are in scope and count as one observation of the CLT-installed
state. Do not create or run another Mac or VM environment, and do not edit the
install instructions.

### Questions and acceptance

- Answer by machine state: a fresh machine without CLT, a machine with CLT,
  and a migrated machine whose installed dependencies must be identified.
  Record each observation's macOS version, architecture, CLT version when
  known, and source. Distinguish observed facts, documented guarantees,
  inferences, and unknowns; do not invent a per-release matrix when sources
  do not support one.
- Say whether a fresh VM guest is a fair stand-in for a new Mac, or name what
  differs. The walk evidence in this repo comes from a VM, and the
  disagreement turns on whether that generalizes.
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
  `coga/tasks/v1/29-test-and-fix-install-on-macos-and-windows/macos-walk-findings.md`.
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
can install only missing dependencies. This ticket exists because Nico and the
owner disagree about what a new Mac ships. Nico's position is that pip is
native on macOS. The owner's repeated experience is that a fresh VM has no
usable Python or git until the Command Line Tools are downloaded. Both
observations may be true of different machine states, and whether a VM
generalizes to a new Mac is itself unsettled. Adjudicating that is the job.

The owner decided on 2026-10-21 to answer from documentation and existing runs
rather than build another VM, and on 2026-11-03 allowed read-only checks on the
machine running this ticket. The repo already has relevant observations; the
work is to source and reconcile them, then answer the remaining pip and
bootstrap questions.

Installing Coga needs uv or pip, and the install flow will probably assume most
users already have one of them. That assumption is not a reason to skip this
answer: it decides what the install section tells a user who has neither, and
how confidently it can claim a dependency is already present. This ticket does
not choose the install flow.

### Required source reading

- Read `coga/tasks/v1/29-test-and-fix-install-on-macos-and-windows/macos-walk-findings.md`,
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
- The machine running this ticket is itself an observation. Record its macOS
  version, architecture, and CLT version, then check how `pip3` and
  `python3 -m pip` resolve on it. It is one configured machine, not the
  fresh-machine answer, and the record must say so.
- `coga/tasks/v1/28-affordable-macos-testing-on-owned-macs-and-per-min.md`
  describes a proposed owned-Mac test setup and is blocked pending a deployed
  target. Its Apple Silicon VM design and Intel attach-only route are not
  evidence of a completed fresh-machine run. A fresh user account also does
  not isolate machine-wide dependencies. Determine what the existing sources
  actually establish about migrated machines instead of assuming their tools.

### Consumers of the answer

- `coga/tasks/v1/26-make-the-readme-install-section-the-only-install-p.md`
  owns giving surviving install facts a home; pass it a link to the sourced
  result alongside the existing CLT findings.
- `coga/tasks/v1/17-separate-installing-coga-from-installing-its-depen.md`
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

Previous ref: `marketing/fix-installer/find-out-what-macos-actually-ships` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Production notes

The evaluator review below was never synthesized into the body. It is kept as
the record of the authoring pass, not as outstanding work.

### Evaluator review

##### Verified

Every path and section the current body cites was opened. Unless flagged below, the claims hold.

- `pyproject.toml` `[project]` (line 10) is exactly `requires-python = ">=3.11"`. Cited by key, no line number — correct convention.
- `coga/tasks/v1/29-test-and-fix-install-on-macos-and-windows/macos-walk-findings.md` exists and carries all four cited regions: `## Host facts (Zach's Mac, 2026-10-15)`, `## Pre-walk findings (from the docs, no walk needed)`, `### Baseline (guest, before any install)`, and both walk records (`## New-user walk: macOS` and `## New-user walk: macOS — run 2`). The baseline does show a no-CLT guest with `/usr/bin/git` and `/usr/bin/python3` as stubs on macOS 26.6.2 arm64.
- `scripts/clean-install/macos-walk.sh`: the `reset` case does the CLT removal (`rm -rf /Library/Developer/CommandLineTools`, `xcode-select --reset`, plus a fresh-login-shell check that `git` resolves to `/usr/bin/git`); the `walk` case does the interpreter provisioning (`uv python install 3.11`) behind the "macOS ships /usr/bin/python3 3.9, below Coga's floor" comment. Cited by case name, not line number — correct.
- `coga/tasks/v1/28-affordable-macos-testing-on-owned-macs-and-per-min.md`: `status: blocked`, "No local-Mac implementation has been made", "The owner has not yet deployed a macOS test environment", Tart vanilla arm64 image with no CLT, Intel `attach` "never reset", and "A fresh user account does not isolate machine-wide dependencies." The ticket's "proposed … blocked pending a deployed target" is accurate.
- Ownership boundaries: ticket 17's Description says verbatim "This ticket decides what the install section contains"; ticket 26's says "Before removing it, carry over the facts on that page that have no other home"; ticket 29's `## Owner decision, 2026-10-17` does list the CLT trap and "that the CLT ships Python 3.9" as orphan facts needing a home.
- `docs/contexts/coga/checkouts/SKILL.md` ends its `## Stranded ticket writes` section with, verbatim, "`ticket.py` and attachments under `coga/tasks/` can be implementation work and stay in the diff." Confirmed — but see the workflow section for why that does not make the branch/PR route work.
- Agent and workflow resolve. `coga/coga.toml` declares exactly `[agents.claude]` and `[agents.codex]`, so `docs/with-review`'s `peer-review` (`assignee: other-agent`) infers codex unambiguously. A string `workflow:` with no `step:` on a `draft` is the correct pre-activation shape.
- No citation in the current body carries a bare line number, a "near line N", or a size/token-count justification.
- The ~15 KiB `## Superseded designs` block costs nothing at launch: `_without_superseded_designs` in `src/coga/blackboard.py` strips it from the composed blackboard layer, which reports 311 B.
- All seven substantive findings from the 2026-10-21 review are addressed: the two richest sources are now cited; the uv-bootstrap inference is re-posed as a question to verify; "per macOS version" became "by machine state"; the two deleted ticket slugs are gone from the body; ticket 28 is described as proposed and blocked; stub-vs-CLT precision is held; and the `EXTERNALLY-MANAGED` / install-destination sub-question was added.

##### Findings that would change the work

**1. Two of the three cited `coga/install` section names no longer exist, and the section was rewritten on the exact disputed point.** `### macOS: install the Command Line Tools first` was renamed to `### macOS: check Git before init` in `eb075c44c` ("Document optional macOS CLT and uv setup", nicktoper, 2026-10-28). The body changed from "A fresh Mac has no real Git … Install the CLT before installing Coga" to "Coga requires **working Git**, not Xcode … If it prints a version, there is no need to install CLT solely for Coga. Git installed via Homebrew, MacPorts, or another working source is fine." The same commit added `curl -LsSf https://astral.sh/uv/install.sh | sh` to `## Install the CLI`. Three consequences:

- The agent will not find the cited headings.
- The other party to the disagreement already moved the documented position *after* the owner's 2026-10-21 decision, and the ticket's Context does not say so. "Compare its current assertions with the dated evidence" now means comparing against a softened claim, not the one the dispute was about.
- Part of the dated evidence is already obsolete: `macos-walk-findings.md` finding 2 says "`coga/install` links uv's homepage without an install command", which `eb075c44c` fixed. That collides with "Preserve the dated walk evidence" — the agent needs to be told to date-stamp rather than correct it.

Also: "Python is older than 3.11" is not a heading. It is the bold lead-in `**Python older than 3.11.**` under `### Install failures`.

**2. Four on-point sources are uncited, and three of them are the non-VM or second-VM evidence the ticket says the repo lacks.**

- `docs/archive/evidence/macos-clean-install-runs-2026-10.md` (17 lines) is the only committed EC2-Mac evidence: "the walk reproduced the SSH error on a **fresh macOS 27 host**; the dialog path was not exercised" and "an earlier walk that resolved the PyPI `0.0.1` placeholder on the **system Python 3.9** was set aside as not evidence for the 3.11 floor." The second line is a real Mac where pip on the CLT 3.9 resolved and installed a package from PyPI — direct evidence on the central pip question.
- `coga/skills/coga/testing/clean-install/macos-aws/SKILL.md` documents the CLT-installed → no-CLT transition on real hardware ("removes the CLT that the AMI ships", "It never preinstalls CLT") and what `baseline.txt` records (macOS version, CLT state, Homebrew, `/etc/paths`). The `baseline.txt` files themselves are not in the repo.
- `coga/tasks/competition-testing/test-compound-engineering.md`, `## Observed — lap 0, install (2026-10-24)`: a second bare-macOS VM (`cogatests-Virtual-Machine`) where "Zach ran `python3 -V`, which triggered the Xcode Command Line Tools install prompt". Entry 27 names the macOS "`~/Library/Python/3.x/bin` trap" explicitly — repo evidence on the install-destination question the Description treats as unevidenced.
- `coga/tasks/competition-testing/test-kiro.md`, `## Decisions`: a third bare VM (`cogatest-kiro`), "Bare at the start — `xcode-select -p` errored in the R1 baseline capture", plus "**Xcode Command Line Tools** were installed by operator habit before Kiro asked for anything" — a recorded no-CLT → CLT transition on one machine, which is the comparison the ticket is built around.

The Description's premise, "The walk evidence in this repo comes from a VM, and the disagreement turns on whether that generalizes", therefore understates the record: three independent fresh-macOS VM baselines plus one fresh non-VM EC2 Mac host, all with no CLT. Adding these changes the answer the agent can defend and removes most of the reason to reach for Apple's documentation.

One scope decision to make explicitly: the detailed logs for both competitor trials are *off-repo* — claude.ai artifacts and the "Coga Competitor Tests" Google Doc named in `test-kiro.md` under `### Install starting point`, described there as "the baseline for what a bare `cogatest` VM needs". An agent told to work from "the existing repo evidence" will miss them. Either cite them or rule them out.

**3. The branch/PR half of `docs/with-review` cannot complete for a deliverable whose only changed path is under `coga/tasks/`.** Detailed in the workflow section — this is the one finding that blocks the ticket as written.

##### Worth fixing before launch

- **Description and Context disagree about what the local machine proves.** Description: "count as one observation of the CLT-installed state." Context: "It is one configured machine, not the fresh-machine answer, and the record must say so." The Context's wording is the honest one; the Description's invites exactly the overclaim the Context forbids.
- **"Link that answer from the two consuming install-path tickets" names neither a region nor a checkout.** `docs/contexts/coga/state-publication/SKILL.md` (`## Control versus feature checkouts`) says "Write deliberate ticket prose and knowledge edits on `main`", while `implement` runs on a feature branch. Say: edit tickets 26 and 17 on control, under their `## Context`.
- **The target file's own scope line does not cover the new section.** `macos-walk-findings.md` opens "Dated evidence from the macOS walks (2026-10-15 to 2026-10-18)" and states "The live status of each finding is the `## Findings status` list on the ticket's blackboard." A document-sourced reconciliation plus a one-host spot check is neither dated walk evidence nor a numbered finding. Have the new section state its provenance, and say whether ticket 29's `## Findings status` gets a pointer.
- **Concurrency with ticket 29.** It is `status: in_progress` with `branch: install-walk-findings` and `pr: https://github.com/FastJVM/coga/pull/1043` under `## Dev`, and the findings file is its attachment. Two tickets may write the same file; say which wins.
- **If `docs/archive/evidence/macos-clean-install-runs-2026-10.md` is cited, note its broken link.** Line 4 points at `../../contexts/coga/testing/clean-install/macos-aws/SKILL.md`, which does not exist; the runbook is at `coga/skills/coga/testing/clean-install/macos-aws/SKILL.md`. `peer-review`'s link check will land on it.
- **The title still reads as discovery** ("Find out what macOS actually ships") while the Description is reconciliation. The 2026-10-21 version admitted the mismatch in Context; the current one dropped the admission without renaming. One clause either way.

##### Workflow fit

In *shape*, `docs/with-review` is right: the deliverable is prose, and the `peer-review` bar — "Accuracy … Spot-check anything load-bearing against the source it describes", "Links & references" — is precisely what sourced desk research needs, where `code/with-review`'s diff review plus `python -m pytest` would be value-light. Agent and peer resolve cleanly. `peer-review`'s cross-copy check is a no-op for this path, correctly, since the ticket forbids editing `coga/install` (whose packaged twin at `src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md` I confirmed is byte-identical today).

The `checkouts` sentence the ticket leans on is real but is being over-read. It sits inside `## Stranded ticket writes` and is a statement about what the *stranded-write detector* tolerates — not a guarantee the file reaches a PR. The mechanism runs the other way:

- `_routine_state_areas` in `src/coga/git.py` returns the whole `tasks_dir(cfg)` prefix (`coga/tasks/`) plus `recurring_dir` and `coga/log.md`. `_publish_locked` sets `adopt_only` to that set whenever HEAD is not control, and `_candidates` then adopts *committed* branch paths inside it (the gate is that control's blob at the path is one the branch derived from, which holds for an edit to an existing file).
- So a committed change to `coga/tasks/v1/29-…/macos-walk-findings.md` on a feature branch is published to control at the next sweeping command — which is the `coga bump` that ends `implement`. The ticket's instruction "commit it before running a sweeping Coga command, following `coga/checkouts`" does not protect this deliverable; it guarantees the opposite. The advice it borrows from `docs/contexts/coga/state-publication/SKILL.md` ("Pre-review publication hazard") explicitly exempts "routine task, log, or recurring state".
- `open-pr` then refuses. `check_branch_contains_control` in `src/coga/github_preflight.py` computes `control_paths = _changed_paths(merge_base, control_ref)` and `feature_paths = _changed_paths(merge_base, head)` and fails when `unsafe_overlaps = control_paths & feature_paths` is non-empty, reporting "Overlapping paths: …"; `open_pr.py` raises `OpenPrError("Branch … is not safe to publish")`. Rebasing onto the now-identical control — what the error text suggests — leaves the branch with no diff at all.
- Nothing warns earlier: `stranded_task_state_paths`' docstring says its callers "pass the ticket file of the task they are acting on, never all of `tasks/**`, because a branch may legitimately edit *other* tickets as implementation work."

Two workable fixes:

- **(a) Land the research note outside the Coga roots.** `docs/archive/evidence/` already holds `macos-clean-install-runs-2026-10.md`; a sibling there is reviewable in a real PR, has no packaged twin, and keeps `docs/with-review` intact. Link it from the findings file rather than embedding the section there.
- **(b) Keep the file where it is and drop the branch/PR.** `src/coga/resources/templates/coga/bootstrap/workflows/draft-for-human.md` states "This workflow has no push or PR step" in its sibling note's sense, its `human-owns-and-finishes` step is the adjudication gate this disagreement actually needs, and it is already what both competitor-trial tickets in `coga/tasks/competition-testing/` use for exactly this evidence-logging shape. `direct/body` also avoids the PR but has no review gate.

Pick (a) if Nico should see a PR; (b) if the owner adjudicates. As written, the ticket picks neither and will dead-end at `open-pr`.

##### Contexts

Empty `contexts:` is the right call. The ticket consumes four specific documents, not standing rules, and all are reachable with Read.

Cite-not-attach for `coga/install` is also right, and for the stated reason rather than a size one: the ticket reads three named spots once and is forbidden from editing the file. No planned step depends on rules spread across it — the one rule-shaped thing it owns (the `>=3.11` floor) the ticket already routes to `pyproject.toml` `[project].requires-python` as the owner. Attaching it would add ~8.8 KiB (~2.2k tokens) to a 5.2k prompt for a document read once. No cite justifies itself by size or token count.

One gap: the Description points at `coga/checkouts` for the commit discipline, but the rules that actually decide the deliverable's fate live in `coga/state-publication` (`## Control versus feature checkouts`). If the branch/PR route survives, cite that too — better, fix the route so neither citation is load-bearing.

##### Scope and assumptions

Scope is one question and fits one ticket; it excludes editing the install instructions and choosing the install flow, and both exclusions are honoured by the acceptance list. **No split warranted.** (If one were ever needed, siblings in a plain directory — `coga/tasks/competition-testing/` is the in-repo precedent — never a parent.)

The read-only allowance is genuinely productive, but two things need tightening before it is safe:

- **Provider resolution is unstated, and on the likely host it inverts the answer.** On the machine this evaluation ran from (macOS 26.4.1, arm64, CLT present at `/Library/Developer/CommandLineTools`), `command -v python3` → `/opt/anaconda3/bin/python3`, `pip3` → `/opt/anaconda3/bin/pip3`, `git` → `/opt/homebrew/bin/git`. **None of the three binaries the ticket asks about resolve to Apple's or the CLT's copy.** A bare `pip3 --version` here measures Anaconda and would be filed as "the CLT-installed state". Require the absolute resolved path and the provider for every binary, and absolute `/usr/bin/python3 -m pip` for the Apple one. Note too that `macos-walk-findings.md`'s "Host facts (Zach's Mac, 2026-10-15)" records python.org 3.13 in `/usr/local/bin` and no Anaconda — the repo's own host record is already stale, so re-derive rather than quote it.
- **"One observation of the CLT-installed state" is the wrong label** for a developer workstation carrying Homebrew and Anaconda. Use the Context's "one configured machine" wording in the Description.

For calibration on what the allowance *can* settle: on that host `/usr/bin/python3 -V` prints `Python 3.9.6`; `/usr/bin/pip3` exists as the same 118928-byte stub as `/usr/bin/python3`; and `EXTERNALLY-MANAGED` is absent from the CLT 3.9 stdlib. Three of the Description's sub-questions are answerable by observation on one machine — that is the case for keeping the allowance, scoped as above.

Three further assumptions to settle before launch:

- **The central question is not observable read-only.** "Whether it can bootstrap uv so uv can provision a supported interpreter" cannot be settled without running `pip install uv`, which read-only forbids. The ticket correctly routes it to uv's published metadata. State explicitly that no install — and no `--dry-run` resolution — is to be treated as proof, and that any such check on this host would exercise Anaconda's pip rather than Apple's.
- **The launch host is assumed to be a Mac.** Ticket 29's own `## Blockers` entry records "this queued Linux session cannot reach" Zach's Mac, so queued launches are not macOS. Add one line: if the launch host is not macOS, record the machine observation as unavailable and answer from sources only. Otherwise an agent on Linux has nothing to record and may quietly reuse the findings file's host facts as if it had measured them.
- **"A migrated machine whose installed dependencies must be identified"** is listed as a row to answer, but no source in the repo observes a Migration Assistant machine and Apple publishes nothing on it. Say up front that "unknown, no source" is an acceptable answer for that row, or the agent will infer one.

##### Prompt budget

Nothing warrants a trim. `task_context` at 2162 tokens is 41.5% of 5207 and nominally crosses the threshold, but 5135 B (~1326 tokens, 25% of the whole prompt) of it is the stock ticket-guide comment every ticket carries. Author prose in `## Context` is ~3.5 KiB / ~836 tokens (16%); `## Description` is 2507 B / 628 tokens (12%). Total author prose is ~28% of the composed prompt — lean for a ticket carrying five sub-questions and a sourcing list. `base_prompt` at 17.7% is the next largest layer and is fixed overhead.

The only real redundancy: the macOS-version / architecture / CLT-version recording instruction appears twice (Description bullet 1 and the Context machine-observation bullet), as does the `pip3` / `python3 -m pip` resolution check. Merging saves ~40 tokens — not worth doing for size, worth doing so the two copies cannot drift apart on what the local machine proves, which is exactly where they already disagree.

The correct move is to add: the four missing citations plus the host-not-macOS line is roughly +100 tokens, about 2% of the prompt.

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
