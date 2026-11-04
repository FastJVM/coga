---
title: Test and fix install on macOS and Windows
status: done
owner: zach
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
contexts:
- coga/install
agent: claude
---

## Description

A human test, not an automated one. Zach (marketing) installs coga himself,
on a fresh macOS and a fresh Windows environment on his own hardware
(following `guide-for-zach.md`, attached), the way a first-time user would: follow the README / `coga/install` docs only, then
`uv tool install coga`, `coga init`, `coga build`, and a first `coga ticket`.
The agent session (run from Zach's usual coga checkout, not inside the fresh
environment) records every point where he gets stuck, confused, or has to
guess, and fixes what it can in the same session.

Known going in: on macOS, the Xcode Command Line Tools git stub and the
system Python 3.9 (below the 3.11 floor). Native Windows does not start at
all: `coga.git` imports `fcntl` at module top, so even `coga --help` fails,
and `repl_supervisor` / `megalaunch` need pty/termios/tty. The deep Windows
port is `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window` (owner decision 2026-10-13); this
ticket feeds it findings and does not duplicate it.

Windows moved out on 2026-10-18 (owner). This ticket is macOS only; the
title predates the split. The Windows walk is
`v1/31-test-install-on-windows`, deferred until the port
lands because a walk today tests a path that cannot work at all.

Done when: the macOS walk is done and its findings are listed on the
blackboard (each tagged fixed-in-PR, tracked-elsewhere, or open); fixes that
fit this ticket are merged as PRs; and the README carries clear install
instructions in no more than five lines. `docs/contexts/coga/install` is
being deleted (owner, 2026-10-17), so the blackboard also lists the facts
from it that are candidates for a surviving context — proposals for review,
not commitments.

## Context

### Zach's guide (attachment)

Zach is not an engineer. He follows `guide-for-zach.md` beside this ticket:
plain-language steps to make a fresh VM (UTM macOS VM on Apple Silicon,
VirtualBox Windows 11 VM) or, as fallback B, a new `cogatest` user account;
a baseline command; the install walk from the public README; a per-step note
template (command, time, what he saw vs expected, weird/slow, needed help);
and three wrap-up questions. The goal is human signal: lag (waits with no
feedback), idiosyncrasies (confusing text, surprise popups/warnings, guessed
steps), and whether each step works. Keep the guide in sync if the walk
changes, and fold what proves useful into `coga/install`.

Agent-side facts the guide simplifies:

- Option B (new user account) leaks machine-wide installs: on macOS the CLT
  (git stub won't appear), Homebrew under `/opt/homebrew`, python.org Python
  in `/usr/local/bin`; on Windows, Git for Windows, "all users" Python,
  machine-wide winget packages. Flag findings that depend on these.
- On a fresh Mac both `/usr/bin/git` and `/usr/bin/python3` are CLT stubs;
  Python 3.9 appears only after CLT installs. The baseline avoids invoking
  them.
- UTM cannot snapshot macOS guests (the guide uses Clone); VirtualBox needs
  "Skip Unattended Installation" or it bypasses OOBE and creates `vboxuser`.
- Zach pastes baselines and errors into this session; record them on the
  blackboard under the matching walk section.

### Walk rules

- Zach acts as a new user: docs only, no help from the agent unless he is
  stuck, and a needed hint is itself a finding.
- Per step, note: the exact command, what happened, what he expected, and
  how long he was stuck.
- Fix loop: finding -> PR -> merge -> re-walk the affected step in a fresh
  environment (VM clone/snapshot taken right after the baseline, or a new
  user account). `uv tool install coga` installs from PyPI, so a merged fix
  is not there until a release. For a re-walk, install from main instead:
  `uv tool install git+https://github.com/FastJVM/coga@main`, and note in
  the finding that it was checked against main, not a release. Doc-only fixes
  need no reinstall.
- `coga/testing/clean-install/macos-aws` already covers the automated
  fresh-Mac harness on EC2; this ticket is the human counterpart and does not
  rent machines.
- Repo is public: no account IDs, emails or keys on the blackboard.

Previous ref: `marketing/fix-installer/test-and-fix-install-on-macos-and-windows` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->
# Test and fix install on macOS and Windows

## Dev

pr: https://github.com/FastJVM/coga/pull/1043
branch: install-walk-findings

## Closing verification — review, 2026-11-04

Owner asked whether the ticket can be marked done, having read the current
README and judged this work superseded. Verified, and it can.

What the review step found:

- PR #1043 carries no review threads, reviews or comments, so the `review`
  step's own skill had no input to address. It was closed by the owner on
  2026-10-19; local HEAD `cdf2676b0` still matches its head exactly.
- Six findings are fixed on main, three were closed by owner decision on
  `v1/19`, and seven are tracked on live drafts. Per-finding evidence is under
  `## Findings status`.
- The walk's findings seeded a v1 install workstream rather than one PR:
  `v1/16` and `v1/19` are done, `v1/17`, `v1/18`, `v1/23`, `v1/24`, `v1/26`,
  `v1/27` and `v1/31` are drafts, and `v1/30` is blocked.
- Two findings had nothing tracking them, so
  `v1/cap-requires-python-and-stop-init-leading-with-a-c` was filed as a draft
  with the owner's agreement: finding 7's uncapped `requires-python`, and
  findings 9 through 11 on init's next steps. Closure would otherwise have
  retired them with this blackboard.
- The branch and its remote ref are deliberately left in place at
  `cdf2676b0`, so the closed PR keeps the walk's reasoning discoverable.

Done-when, as met:

- The macOS walk is complete and every finding is listed and tagged. Done.
- Fixes that fit the ticket are merged as PRs. Met in substance but not by
  this ticket: the owner landed the equivalent README himself after closing
  #1043.
- The README carries install instructions in no more than five lines. **Not
  met as written.** Main's "Get started" is seven command lines across four
  blocks plus roughly twenty lines of prose. The owner wrote that himself on
  2026-11-04, after closing the PR, so the five-line cap is superseded by his
  own editorial decision rather than outstanding work. Raised with him before
  closing and left as it stands.
- The blackboard lists the facts from `docs/contexts/coga/install` that are
  candidates for a surviving context. Done, under the 2026-10-17 decision
  above. That topic is still present on main, and `v1/26` owns its removal.

## Blackboard maintenance, 2026-10-19

Slimmed for `coga validate`'s large-blackboard warning by task
`slim-the-40-9-kib-blackboard-of-the-macos-and-wind`. Blackboard layer
before: 40.9 KiB; after: 18.2 KiB. Dated walk evidence moved verbatim to
[`macos-walk-findings.md`](macos-walk-findings.md), replaced here by
`## Findings status`; the 2026-10-15 plan moved to `## Superseded designs`.
Nothing was deleted.

## Owner decision, 2026-10-17: delete `coga/install`

The install topic is being removed and the install instructions become no
more than five lines in the README. This changes what most findings fix.
Findings 2, 3, 11 and 12 become requirements on the new README lines rather
than repairs to the topic, and finding 5 largely dissolves because the page
it describes will not exist. Finding 13 survives in reduced form: whatever
those lines say must describe what PyPI serves, not `main`.

Facts the topic currently owns that would otherwise have no home. Listed as
candidates for a surviving context, for review rather than as commitments:

- The macOS Command Line Tools trap, including the headless
  `softwareupdate` route, and that the CLT ships Python 3.9.
- Why the floor is Python 3.11: config loading uses `tomllib`, and what an
  older interpreter fails with.
- Why native Windows does not run: `coga.git` imports `fcntl` at module
  top and `cli.py` imports `coga.git` eagerly, so even `coga --help` fails,
  and WSL is the untested route. Overlaps
  `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window`.
- The `--require-hashes` install failure and its two workarounds.
- Which external CLIs are checked when, and that `coga init` enforces only
  `git`.
- The upgrade and removal commands per installer.

## Findings status

Final disposition of the sixteen walk findings, re-verified against
`origin/main` at `717792674` on 2026-11-04. Full text, terminal output and
reasoning are in [`macos-walk-findings.md`](macos-walk-findings.md).

None were fixed by this ticket's PR. #1043 was closed unmerged by the owner on
2026-10-19 with no review comments and no recorded reason, and the owner then
rewrote the README install path himself across 2026-11-03 and 2026-11-04. The
branch `install-walk-findings` stays unmerged and is not worth merging: main's
version is better in three places, since it tells macOS users to check
`git --version` before running `xcode-select --install`, links the vendor's
CLI quickstart where the branch kept the desktop-app link, and names the
release that fails on Windows instead of calling the platform unsupported.
README line numbers below are `origin/main` at `717792674`.

1. fixed on main — `README.md:84` scopes agent sessions to Linux and macOS;
   `:91` names release 0.4.1 as not ready for a first task.
2. fixed on main — `README.md:105` installs `uv` first and `:108` tells the
   user to open a new terminal if it is not on `PATH`.
3. fixed on main — `README.md:97` checks `git --version` first, then offers
   `xcode-select --install`.
4. fixed on main — `README.md:119` creates the repository, and the surrounding
   prose covers an existing one and the Git identity check.
5. tracked elsewhere — `v1/26-make-the-readme-install-section-the-only-install-p`,
   draft. `docs/contexts/coga/install` is still present on main, so the facts
   listed above are not orphaned yet.
6. fixed on main by ordering — installing the Command Line Tools first removes
   the dialog. The source build that caused it is finding 7.
7. tracked elsewhere — `v1/cap-requires-python-and-stop-init-leading-with-a-c`,
   draft, filed 2026-11-04. `pyproject.toml:10` is still uncapped, and
   `nothing-exercises-python-3-11-the-declared-floor` is canceled.
8. tracked elsewhere — `v1/17-separate-installing-coga-from-installing-its-depen`
   and `v1/18-handle-gh-not-being-installed-by-default`, both drafts.
9. tracked elsewhere — the draft filed for finding 7 covers it.
10. tracked elsewhere — same draft; `src/coga/commands/init.py` still makes the
    `coga.toml` edit init's second instruction.
11. tracked elsewhere — same draft.
12. fixed on main — `README.md:169` links the uninstall guide.
    `v1/27-link-uninstall-from-the-readme` is still a draft and its substance
    has landed.
13. fixed on main — the README now separates PyPI release 0.4.1 from the
    development version instead of describing `main` as what ships.
14. closed by decision — `v1/19`, 2026-11-04. The brew/npm-only manifest is
    accepted, for Codex as well as Claude.
15. closed by decision — `v1/19`, 2026-11-04, by decision rather than by a
    change. The README link is corrected, and
    `src/coga/dependencies.py:117` deliberately still points at
    `https://claude.com/claude-code`.
16. closed by decision — `v1/19` records it as not ruled on and no longer
    blocking anything.

## Host facts (Zach's Mac, 2026-10-15)

Moved verbatim to [`macos-walk-findings.md`](macos-walk-findings.md) on 2026-10-19.

## Pre-walk findings (from the docs, no walk needed)

Moved verbatim to [`macos-walk-findings.md`](macos-walk-findings.md) on 2026-10-19.

## Carried-over finding — answered, close it

Moved verbatim to [`macos-walk-findings.md`](macos-walk-findings.md) on 2026-10-19.

## New-user walk: macOS

Moved verbatim to [`macos-walk-findings.md`](macos-walk-findings.md) on 2026-10-19.

## New-user walk: macOS — run 2

Moved verbatim to [`macos-walk-findings.md`](macos-walk-findings.md) on 2026-10-19.

## Verification run: the proposed five lines

Moved verbatim to [`macos-walk-findings.md`](macos-walk-findings.md) on 2026-10-19.

## New-user walk: Windows — moved out

Deferred 2026-10-18 by owner decision and recreated as
`marketing/fix-installer/test-install-on-windows` (draft). A walk today
would test a path that cannot work, because Coga cannot start on native
Windows at all; it is worth running once the port lands and there is
something to install into. Zach runs it on his own Windows PC, which is
also why it wants its own ticket rather than a section here.

Nothing from the macOS walk is owed to it. The Windows-specific fact this
work produced — that `coga.git` imports `fcntl` at module top, so even
`coga --help` fails — already belongs to
`windows-native/01-core-port-cli-and-test-suite-pass-on-native-window` and is
listed above among the facts to rehome when `coga/install` is deleted.

## Handoff — implement, 2026-10-18

Note 2026-10-19: PR #1043 was closed unmerged on 2026-10-19 with no
comment, so this handoff may be stale; the reason is not recorded here.

The macOS walk is complete and the fix is on the branch. Three clean VMs:
one cold walk, one reproduction, one verification of the proposed block.
Sixteen findings, all recorded above with evidence.

What landed in code: one commit, `README.md` only, replacing the install
block with the five-line sequence verified on a clean machine and removing
two false claims — that Coga runs on native Windows, and that `coga init`
offers to install an agent CLI, which the released package does not do.

Three deviations from the owner's dictated text, each raised at the time
and left in deliberately:

- Kept "Linux or macOS" rather than macOS alone, because Coga does run on
  Linux and the owner's wording would have been false in the other
  direction. Line 1 carries a `macOS:` marker so Linux readers skip it.
- Added "Native Windows is unsupported." That fact lives only on the page
  being deleted, and Windows users will try regardless.
- Kept Nico's sentence about uv fetching a compatible Python
  (`ff906aac4`), because the platform line still requires Python 3.11+ and
  nothing in the block installs Python.

Deliberately out of scope, each with a reason recorded above: deleting
`coga/install` (owner is doing it, and the orphan facts need homes first),
capping `requires-python` for finding 7, and teaching the dependency
manifest the agent CLI's native installer for finding 16. The last two need
owner rulings listed under "Decisions needed" in the owner's report.

For the next step: `main` is red independently of this work. Two causes,
both reproduced on the merge-base with this change stashed — a drifted
`coga/recurring/autoclose-merged/ticket.md` twin, and the `CLAUDE.md`
core-boundary text. CI will fail on this PR until someone fixes them, and
that is not this ticket's job.

Also produced, outside the repo: an organised findings report in the
owner's Google Docs, with labelled screenshot slots he fills himself.

## Self-QA — 2026-10-18

Review form: **direct review, completed.** `/code-review` is not an invocable
skill in this harness, so the pass was read by hand over the branch diff vs
`main` — one file, `README.md`. `/simplify` ran, with its four-agent fan-out
replaced by an inline pass over the same four angles, because the diff
contains no code and this session is configured not to spawn subagents
unasked. Recorded as a limitation rather than a clean tool pass. Reviewer is
Claude, the same agent lineage as the implement step: this is self-review,
not independent review.

Findings applied — three, all resolved by one edit (commit `cdf2676b0`):

- **Six command lines against a five-line Done-when.** The implement step's
  block had six commands; the ticket caps the README install at five, and the
  sequence verified on the clean VM was five. `coga build` was that run's
  *pass condition* ("the five lines complete and `coga build` runs"), which
  the implement step folded into the block itself. Removed, owner confirmed.
- **Reuse — that line duplicated `README.md:127`**, which already covers
  `coga build` and correctly conditions it on the repo being empty. The
  install block restated it unconditionally, contradicting "First steps".
- **Existing-project entry point restored.** The old block's
  `cd <your git repository>` served existing repos; the new one hardcodes
  `mkdir myproject && cd myproject && git init`, so a user with a project
  following it literally creates a throwaway directory. Carried in one prose
  sentence after the block rather than a sixth command line.

The five commands are now byte-identical to what passed on the clean VM. The
implement step reworded only the comments, and comments do not execute, so
the verified behavior is preserved exactly.

Claims checked against the code rather than accepted from the diff:

- `pyproject.toml:10` has `requires-python = ">=3.11"`, uncapped — finding 7
  is real and unfixed.
- `src/coga/git.py:49` imports `fcntl` at module top — the new "Native
  Windows is unsupported" sentence is accurate.
- `src/coga/dependencies.py:119-122` gives `claude` only brew and npm —
  findings 14 and 16 are real.
- PyPI's latest is 0.4.0 and `src/coga/agent_cli_setup.py` is absent from
  `v0.4.0`, so dropping the "`coga init` offers to install the agent CLI"
  sentence was right for anyone running `uv tool install coga`.
- Both new installer URLs return HTTP 200, and `https://claude.ai/install.sh`
  is Anthropic's own script, installing under `$HOME` with neither Node nor
  Homebrew — which is what makes line 4 work on a fresh Mac.

No test asserts on the repo README's content, established by reading the
tests rather than assuming: every `test_init.py` reference writes its own
README into a temp target, and `test_edge_distribution.py:47` copies the real
one only because the wheel build needs `pyproject`'s readme, asserting
nothing about its text. A prose edit cannot introduce a failure, and the
suite result below matches the implement step's exactly.

Hand-swept surfaces: none apply. The diff touches no terminal, pager or
Slack surface. The fenced block and line widths were checked as rendered
text.

Not fixed, left for the human reviewer:

- `README.md:110` is 82 characters where the file otherwise wraps at ~78. No
  linter enforces it.
- Line 4 installs Claude Code while the prose above offers Claude *or* Codex;
  five lines has no room for both.
- `README.md:118` still links `docs/contexts/coga/install/SKILL.md`, the page
  the owner is deleting. Not a defect in this diff, but the two changes are
  coupled and that link breaks when the deletion lands.
- The removed agent-CLI sentence is *true on `main`*, so the README now
  understates `main` and will need it back at 0.4.1. This is finding 13's
  unresolved "docs track the release or `main`" question.
- Line 4's `claude` resolves only because line 2's uv installer puts
  `~/.local/bin` on PATH. Fine on the walk, but someone who already had uv
  and skipped line 2's new-terminal step could find `claude` missing.

## PR

```yaml
title: Replace README install block with a verified clean-machine sequence
author: claude
author_evidence: >-
  Both sessions ran as Claude Opus 5 under `coga launch`, attended by the owner
  throughout; no agent override was used. Implement wrote the block
  (`ed321e20e`); self-qa trimmed it to five lines (`cdf2676b0`).
head: cdf2676b0e20f1616ee458c3e496182e8143b91b
base: f6a7145f2cfa8ec3f5602f749d669775ea1be7da
depth: deep
rationale: >-
  Self-qa has completed and its findings are applied, but the depth stays deep
  on three rubric triggers, not on residual doubt about the change itself.
  Review was self-review — the same agent lineage as the implement step, with
  no independent reviewer — the suite is red from five pre-existing main
  failures, and findings 7, 13 and 16 remain open pending owner rulings. The
  change itself is one prose file whose sequence was walked end to end on a
  clean macOS VM, but it is the public front page's install path, the first
  thing every new user executes. An independent review returning green on
  this head is what should downgrade it.
implementation: >-
  Replaces the four-line README install block, which cannot complete on a
  fresh Mac, with the five-line sequence verified on a clean VM; corrects the
  platform sentence; and carries the existing-repository entry point in prose
  after the block.
deviations: >-
  Three departures from the owner's dictated wording, each raised with him
  before committing: kept "Linux or macOS" rather than macOS alone because
  Coga does run on Linux; added "Native Windows is unsupported" because that
  fact's only home is the page being deleted; kept Nico's uv/Python sentence
  from ff906aac4 because the platform line still names Python 3.11+. Self-qa
  then removed the implement step's sixth command, `coga build`, which
  exceeded the ticket's five-line cap and duplicated "First steps"; owner
  confirmed in session.
limitations: >-
  Verified on macOS 26.6.2 arm64 only. The Linux path is reasoned, not walked:
  line 1 is marked macOS-only and Linux users take git from their package
  manager. Line 4 installs the agent CLI with the vendor's own script, which
  sits against the policy in `src/coga/agent_cli_setup.py` that Coga itself
  never runs `curl | sh`; that policy governs what Coga executes, not what the
  README tells a user to run, but the tension is unresolved and is finding 16.
  Two coupled issues are out of scope and recorded under `## Self-QA`: the
  README still links `coga/install`, the page the owner is deleting, so that
  link breaks when the deletion lands; and the removed agent-CLI sentence is
  true on `main`, so the README now understates `main` until 0.4.1.
files:
  README.md: >-
    Install section — the five verified lines, the platform sentence corrected
    to drop the false native-Windows claim and the agent-CLI install offer the
    released package does not have, and a prose sentence for readers who
    already have a repository.
review:
  reviewer: claude
  kind: self
  status: passed
  head: cdf2676b0e20f1616ee458c3e496182e8143b91b
  base: f6a7145f2cfa8ec3f5602f749d669775ea1be7da
  detail: >-
    Direct review, completed in the self-qa session — not independent.
    `/code-review` is not an invocable skill in this harness, so the diff was
    read by hand as the step directs for that case; `/simplify` ran as an
    inline pass over its four angles because the diff contains no code. Three
    findings were raised and all three applied in `cdf2676b0`. The diff's
    factual claims were checked against the source rather than accepted:
    `pyproject.toml:10`, `src/coga/git.py:49`, `src/coga/dependencies.py:119`,
    the absence of `agent_cli_setup.py` from `v0.4.0`, and both installer URLs
    returning 200. Full detail under `## Self-QA`.
checks:
  - command: python -m pytest
    status: failed
    head: 69776a5ae (pre-rebase; README byte-identical to cdf2676b0)
    base: 8508d839856fee4623ce03ab2eefbf932d5033e2
    detail: >-
      3776 passed, 5 failed, 8 skipped in 35m44s, run on the working tree after
      the self-qa fix. Recorded at the pre-rebase base deliberately: the rebase
      onto f6a7145f2 moved only coga-state commits and did not touch README.md,
      so the tested README is byte-identical to the committed one, but this
      receipt does not by itself describe the final head — the targeted re-run
      below does.
  - command: python -m pytest (5 known failures + test_compose + test_edge_distribution)
    status: failed
    head: cdf2676b0e20f1616ee458c3e496182e8143b91b
    base: f6a7145f2cfa8ec3f5602f749d669775ea1be7da
    detail: >-
      5 failed, 97 passed in 59s at the final head. The failing set is
      identical to the full run's and to the implement step's: test_packaging
      and test_autoclose_sweep twin drift on
      coga/recurring/autoclose-merged/ticket.md, test_compose's CLAUDE.md
      core-boundary case, test_edge_distribution's legacy-adoption inventory,
      and a test_recurring git update-ref failure. None can be caused by this
      diff: no test asserts on the repo README's content — test_init writes its
      own into a temp target, and test_edge_distribution copies the real one
      only because the wheel build needs pyproject's readme. CI will stay red
      on this PR until main is fixed, which is not this ticket's job.
  - command: coga validate --json
    status: passed
    head: cdf2676b0e20f1616ee458c3e496182e8143b91b
    base: f6a7145f2cfa8ec3f5602f749d669775ea1be7da
    detail: >-
      269 ok, 2 errors, 47 warnings. Both errors are broken-context on
      marketing/demo-hackability-ask-claude-to-add-a-command-live, which this
      work does not touch. This ticket reports only a stuck-in-progress warn.
```

## Blockers

- [x] [2026-10-14 13:19] [agent:claude] id=20261014T131919 Needs an attended session on Zach's own Mac and Windows machines: the ticket is a hands-on clean-install walk (uv tool install coga, coga init, coga build, first ticket) on those machines, which this queued Linux session cannot reach. Relaunch it attended on the Mac, then on Windows. The Windows fcntl port is tracked separately in make-coga-run-on-native-windows.
  resolved: [2026-10-14 16:45] [human:zach] Owner chose rented disposable AWS macOS and Windows hosts; the read-only Mac preflight is green, so the old own-machine attendance premise no longer blocks the ticket.

## Superseded designs

- 2026-10-14: walk on rented AWS hosts (EC2 Mac and EC2 Windows Server).
  Dropped on 2026-10-15 because this ticket is the human counterpart to the
  automated harnesses. No AWS host was allocated and nothing was spent. The
  setup log, cost notes and removal steps now live in Zach's private admin
  repo (ticket `ops/aws-rented-machine-coga-install-testing`), not here.

### 2026-10-15 — VM walk order ending in a Windows walk and a `coga/install` update

Superseded by: the 2026-10-17 owner decision to delete `coga/install` in
favor of five README lines, and the 2026-10-18 move of the Windows walk to
`marketing/fix-installer/test-install-on-windows`.
Reason: the plan's last two stages no longer exist on this ticket.

#### Plan (2026-10-15, attended)


Owner chose the UTM VM as the primary macOS environment because it is the
most faithful, with a new `cogatest` user account as the cheap re-walk
environment after fixes. The VM walk goes first and cold. Order: VM walk ->
findings -> fixes -> re-walk fixed steps in a new user account -> Windows
walk -> update `coga/install`.

Decision: the doc fixes below are held until after the macOS walk, so Zach
hits the same docs a real new user hits today. If he gets stuck where
finding 1-3 predicts, the walk confirms them; if he sails past, the reading
was wrong.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `marketing/fix-installer/test-and-fix-install-on-macos-and-windows`
Recorded: 2026-10-19T03:22:54+00:00

    [open-pr] origin/main advanced only through non-overlapping Coga task/log state; branch is safe to publish
    PR presentation: review kind must be independent, self, or none.
