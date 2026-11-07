---
title: Retire the coga/install topic
status: done
owner: zach
contexts:
- coga-dev/principles
- coga/knowledge
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
agent: claude
---

## Description

Delete the `coga/install` topic so the README "Get started" section is the
only install path, as the owner decided on 2026-10-17. The README link to the
topic is already gone (the owner's README rewrite, 2026-11-03/04). What remains
is the topic itself, the links that still point at it, and the facts only it
holds.

1. Triage the orphan facts listed under Context. For each one, either move it
   to the topic that owns the surrounding behavior, or record that it already
   lives there or is deliberately dropped. Follow `coga/knowledge` for where a
   fact goes. Do not create a new catch-all install page under another name.
2. Delete `docs/contexts/coga/install/SKILL.md` and its packaged twin, and
   update the packaging bookkeeping that names them.
3. Repoint or remove every inbound link and mention, so nothing links to the
   deleted topic.
4. Close the README's one remaining gap. Add one plain line saying what to do
   when `coga --version` fails after `uv tool install coga` because the uv tool
   bin directory isn't on PATH (for example `uv tool update-shell`, then open a
   new terminal). Check that wording against current uv before writing it.

Done when: `coga/install` and its twin are gone; `grep -rn "coga/install"`
finds no live link or mention outside `docs/archive/`, `coga/tasks/` and
`coga/log.md`, which are history and are left alone; each
orphan fact is either in a named owning topic or recorded on the blackboard as
dropped, with a reason; the README covers the coga PATH case; and
`python -m pytest` plus `coga validate --json` pass.

## Context

### Why

- Owner decision, 2026-10-17: delete `coga/install` in favour of install
  instructions in the README.
- Zach, 2026-10-21: there should be no separate install page at all. Having to
  click into other pages to work out how to install coga is where it gets
  confusing.
- Walk, 2026-10-15: the page explains prerequisites instead of supplying them,
  and it reads as written for agents while the README reads as written for
  humans.
- `v1/29-test-and-fix-install-on-macos-and-windows` is closing and states on
  its blackboard that this ticket owns the topic's removal.
- `v1/33-review-all-doc`, the documentation acceptance pass, is in progress.
  It removed the README link but left retirement and re-homing to this ticket,
  and its final acceptance rechecks the result. Reconcile with its branch or
  merged state before you edit the same pages.

### Orphan facts to triage

From the 2026-10-17 owner-decision section on v1/29's ticket. These are
candidates, not commitments. Read the current
`docs/contexts/coga/install/SKILL.md` for the exact wording, because it may
hold more than this list:

- The macOS Command Line Tools trap, including the headless `softwareupdate`
  route, and that the CLT ships Python 3.9. The README now covers the basic
  `xcode-select --install` path.
- Why the floor is Python 3.11: config loading uses `tomllib`, and what an
  older interpreter fails with.
- Why native Windows does not run. The topic's explanation (`coga.git`
  importing `fcntl` at module top) is stale: `fcntl` now appears only in
  `coga.oscompat` and `coga.repl_supervisor`. `coga/launch` ("Phases and
  routing") already owns the Windows boundary, so this is likely "already
  owned". Do not carry the stale explanation forward.
- The Python <3.11 failure detail: the yanked `coga==0.0.1` that an old
  interpreter resolves to, `uv tool install --python 3.11`, and that an older
  venv does not help.
- The `--require-hashes` install failure and its two workarounds.
- The pipx, venv and pip install alternatives. Rehome them or drop them on
  purpose; the README now offers only uv.
- Which external CLIs are checked when, and that `coga init` enforces only
  `git`. `coga.dependencies` is the code source of truth.
- Upgrade and removal commands for each installer, including the upgrade
  note that bundled batteries need no per-repo refresh. `coga/uninstall` owns
  removal.
- "Verify": `coga --version` prints `unknown` without package metadata, and
  there is one CLI with no per-repo version.
- "CLI older than the templates it sweeps" (a lagging editable install in
  clone scope). This probably belongs to `coga/recurring/scheduling`.
- "Audit retention adoption" (`coga_edge.trim_log --install`). This is likely
  already owned by `coga/edge-code` and `coga/configuration`.

### Where it is referenced (as of 2026-11-04)

- Topics: `docs/README.md` and the `coga/init`, `coga/first-task`, `coga/cli`,
  `coga/uninstall`, `coga/recurring/scheduling` and
  `coga-dev/current-direction` topics. Edit the package copy under
  `src/coga/resources/templates/coga/bootstrap/contexts/` for user topics and
  mirror any legacy live copy (see AGENTS.md). In `coga/uninstall`, the link
  explains what counts as a uv-tool install, so the replacement has to carry
  that meaning rather than just dropping the link.
- Packaged skills: `coga/testing/clean-install`,
  `coga/testing/clean-install/macos-aws` (two links, one to the
  `#macos-check-git-before-init` anchor) and
  `coga/testing/clean-install/windows-aws` under
  `src/coga/resources/templates/coga/bootstrap/skills/`, each with a live
  copy in `coga/skills/` to mirror. Whatever replaces the anchor must still
  give the same check.
- `tests/test_packaging.py`: `"coga/install"` appears in the required
  bootstrap context refs list (`REQUIRED_BOOTSTRAP_CONTEXT_REFS`).
- `tests/legacy_removal_inventory.txt`: the
  `docs/contexts/coga/install/SKILL.md` ↔ package-twin row.
- `coga.dependencies` module docstring names the `coga/install` topic as the
  human-facing description of the dependency set.
- Open tickets under `coga/tasks/` (including
  `coga/tasks/context-audiences/README.md`) also mention it. They are not code, so
  leave them, but note on the blackboard any whose premise this changes.

`coga/knowledge` is attached because triaging the orphan facts is the core job.
`coga-dev/packaging` (`docs/contexts/coga-dev/packaging/SKILL.md`) is cited,
not attached. Read its sections on twins and the legacy inventory before
editing the bookkeeping.

### README PATH gap

The README's only PATH line covers `uv` itself, so a reader whose
`coga --version` fails after `uv tool install coga` is told nothing. In the
Kiro trial on 2026-10-30, Kiro's installer printed "Installation complete!"
above the PATH step that made the tool runnable. Keep the fix to a line or two
in the README, in keeping with `coga-dev/principles`. Do not add a page.

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

Previous ref: `marketing/fix-installer/make-the-readme-install-section-the-only-install-p` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/1174
branch: coga/v1-26-retire-install-topic

## Implement handoff (2026-11-04, claude)

Done on branch `coga/v1-26-retire-install-topic` (commit 05d15be), pushed, no PR yet.
v1/33's PR #1139 had already merged into main, so there was no branch to reconcile.

Changes:
- Deleted `coga/install` (package copy + `docs/contexts` legacy twin); dropped its
  `REQUIRED_BOOTSTRAP_CONTEXT_REFS` entry and its `legacy_removal_inventory.txt` row.
- Repointed links: coga/init, first-task, cli, uninstall, architecture,
  recurring/scheduling (package + live twins), the 3 clean-install skills (package +
  `coga/skills` live copies), `docs/README.md`, coga-dev/current-direction, and the
  `coga.dependencies` docstring. Install links now go to README `#get-started`.
- README: added "If `coga` isn't found, uv's tool directory isn't on your `PATH`: run
  `uv tool update-shell`, then open a new terminal." Checked against uv 0.13.6
  (`uv tool update-shell`: "Ensure that the tool executable directory is on the `PATH`").
- On main (published): draft `_v2/microkernel/support-commands-boundary` attached
  `coga/install` in `contexts:`, which would become a `coga validate` error. Swapped it
  for `coga/init`.

### Orphan-fact triage
- External CLI checks/offers (only git enforced; package managers, sudo, no-TTY
  fallback, `op` never offered + note, agent CLI via brew cask/npm, never curl|sh,
  `coga build` offer) -> **moved to coga/init**. That also fixes init's stale claim
  that init offers `op` (code: `op` has `offer_install=None`, `init._note_missing_op`).
- Headless macOS CLT `softwareupdate` route -> **moved to the macos-aws harness skill**
  (its only consumer), with the same `git --version` check, "full Xcode not
  required" and "other Git sources are fine". The README covers the basic
  `xcode-select --install` path.
- CLT ships an old system python3 -> kept as one line in macos-aws. **Dropped** from
  user docs: uv supplies its own Python (the README says so).
- "CLI older than the templates it sweeps" -> **moved to coga/recurring/scheduling**.
- `--version` (`unknown` without metadata; one CLI, no per-repo version) -> **coga/cli**
  index row.
- Upgrade note (bundled batteries need no per-repo refresh) -> **already owned** by
  coga/context-layout ("an upgrade changes the fallback without touching the repo").
  The `uv tool upgrade coga` command is in the README and first-task.
- Audit retention adoption (`coga_edge.trim_log --install`) -> **already owned** by
  coga/init and coga/edge-code.
- Native Windows -> **already owned** by coga/launch "Phases and routing" (README
  links it). The stale `fcntl` explanation was not carried forward (the topic did not
  contain it anyway).
- Python <3.11 failure (yanked 0.0.1, `--python 3.11`, older venv), `--require-hashes`
  workarounds, pipx/venv/pip alternatives, pip/pipx/editable upgrade commands ->
  **dropped on purpose**. The README offers only uv, which downloads a compatible
  Python and ignores pip config, so those failures cannot occur on the documented
  path. coga/uninstall still documents pipx/pip *removal* detection (behavior).
  The editable dev install stays in AGENTS.md.
- Why the floor is 3.11 (tomllib): it was not in the retired topic and is
  **already owned** by coga-dev/testing. `requires-python` in pyproject declares
  the supported floor.
- Removal -> already owned by coga/uninstall.

### Follow-ups / notes
- Peer review completed the required coga/init size review and recorded the
  exception in the owning topic and its legacy twin. See the peer-review receipt
  below; the size-review follow-up is resolved.
- Open tickets whose premise changes because `coga/install` is gone (prose mentions
  only; left unedited as instructed): v1/14 (interactive Windows launch: its contract
  update should target coga/launch/README), v1/18, v1/20, v1/23, v1/24, v1/43,
  v1/package-definitions/01, `_v2/install-smoke-ci-matrix`,
  `_v2/rewrite-the-coga-dev-current-direction-native-wind`,
  `document-the-non-executable-script-validate-check`,
  `marketing/fix-installer/add-gemini-...`, `context-audiences/README.md`, and blocked
  v1/30 (clean-install audit).
- v1/33's final acceptance should recheck this result.

## Peer review

2026-11-04, resumed Codex: direct review **completed** against final head
`c1ced683e14e9699153ac8f5973ee3548bdef545` and base
`42e3ca6e0fa7ebe016943580541c698c690e89df`. All 26 diff paths were reviewed after the
rebase. No unresolved must-fix findings remain. Claude authored the retirement
implementation; the earlier Codex session authored the two-file init size
exception. The combined receipt uses `self` to disclose that overlap. This
session added only the two authorized ticket-state repairs on main. No child
review CLI or subagent ran.

Resolved findings:
- The init size exception remains in the package owner and matching legacy copy.
- The human authorized changing completed v1/29's context attachment from
  `coga/install` to `coga/init`, resolving the retirement's broken-context error.
- The same authorization covered placing v1/31's existing coordination note
  under `## Production notes`, preserving its prose and resolving the existing
  draft-blackboard error. Both repairs were published on main in `42e3ca6e0`
  before rebasing; the CLI-maintained blocker resolution below records consent.
- The refreshed `## PR` contains only its fenced YAML mapping. The old separator
  inside that section caused the preparation parser to refuse it; the refreshed
  record parses and renders with the intended `skim` recommendation.

Verification: **4453 passed, 10 skipped** in 623.04 seconds; repository validation
passes with **96 OK, 11 warnings, no errors**. The exact commands and revision
receipts are below. Checked all ten package/live pairs (nine identical, one
deleted on both sides), four unique replacement link targets including their
anchors, and both literal and relative references to the retired topic. The
init, agent-install, version, uninstall and recurring compatibility statements
match their owning code. The additional identity/authentication facts from the
retired topic already live in README Get started and coga/architecture.

The PATH remedy was rechecked with uv 0.13.6 help and the current
[Astral tools guide](https://docs.astral.sh/uv/guides/tools/#installing-tools).
No runtime terminal surface changed, and no cloud or fresh-machine install walk
was run. Tests used Python 3.12.12 on Linux; they do not establish a new Python
3.11 or Windows result. Use a basetemp outside this checkout: the prior session
found that an in-checkout basetemp lets missing-repo tests discover real config.

The branch was rebased onto fetched main; range-diff confirms both implementation
commits were preserved unchanged. Main was fetched again after verification and
had not moved. The verified head is pushed with an explicit force-with-lease,
and this manual session returned to clean main before writing the handoff.
The superseded failing validation receipt is replaced below. The next step can
open the PR; no PR was opened in this review session.

## PR

```yaml
title: Retire the coga/install topic
author: claude/codex
author_evidence: Claude Code (Claude Opus 5.5) authored the retirement implementation, as recorded in
  the implement handoff and commit trailer. The earlier Codex peer review added the init size exception
  and its legacy twin. This resumed Codex session applied the two human-authorized ticket repairs on main;
  it added no further implementation changes.
head: c1ced683e14e9699153ac8f5973ee3548bdef545
base: 42e3ca6e0fa7ebe016943580541c698c690e89df
depth: skim
rationale: Bounded documentation retirement with the full suite and repository validation passing. The
  final rebased diff was directly reviewed with no unresolved findings. Skim the orphan-fact choices and
  disclosed verification limits; the combined review is conservatively classified as self-review because
  Codex authored the small size-exception correction.
implementation: Deletes the install topic and its legacy twin, removes its packaging entries, moves surviving
  facts into init, recurring scheduling, the CLI index and the macOS harness, repoints installation links
  to README Get started, and adds the uv tool PATH remedy. The init topic now records its reviewed size
  exception.
deviations: 'Also corrects the stale init claim that op is offered for installation and records the required
  init size exception. The human explicitly authorized two exceptions to the task-history exclusion: the
  completed v1/29 context attachment now names coga/init, and the existing v1/31 coordination note is
  classified as Production notes without changing its prose. Those repairs were published as Coga state
  on main in 42e3ca6e0, before rebasing this branch, and are not part of its implementation diff.'
limitations: No new macOS/AWS or clean-machine installation was run. The PATH remedy was checked against
  uv 0.13.6 help and the current Astral tools guide. The suite ran on Linux with Python 3.12.12, not Python
  3.11 or Windows. Repository validation passes with 11 warnings about other ticket state. No interactive
  runtime surface changed.
files:
  README.md: Add the uv tool PATH line (uv tool update-shell).
  docs/README.md: Drop the installation reference link; README is the only install path.
  docs/contexts/coga-dev/current-direction/SKILL.md: Repoint init-offer and Windows contracts to coga/init
    and coga/launch.
  docs/contexts/coga/architecture/SKILL.md: Legacy twin mirror of the package edit.
  docs/contexts/coga/cli/SKILL.md: Legacy twin mirror of the package edit.
  docs/contexts/coga/first-task/SKILL.md: Legacy twin mirror of the package edit.
  docs/contexts/coga/init/SKILL.md: Legacy twin of the init contract changes and reviewed size exception.
  docs/contexts/coga/install/SKILL.md: Deleted legacy twin of the retired topic.
  docs/contexts/coga/recurring/scheduling/SKILL.md: Legacy twin mirror of the package edit.
  docs/contexts/coga/uninstall/SKILL.md: Legacy twin mirror of the package edit.
  src/coga/dependencies.py: Docstring names coga/init instead of the retired topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: Topic map install entry
    points to README Get started.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Init install-first link to README;
    describe --version in the index row.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: Repoint install, upgrade
    and agent-install links.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Absorb external-CLI checks
    and install offers, correct the stale op claim, and record the reviewed size exception.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: Deleted the retired topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Absorb the
    CLI-older-than-templates note.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/uninstall/SKILL.md: Explain uv-tool install
    via README instead of the retired topic.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/SKILL.md: Install link
    to README Get started.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md: Inline
    the headless CLT softwareupdate steps and git check; install link to README.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md: Install
    link to README Get started.
  coga/skills/coga/testing/clean-install/SKILL.md: Legacy live copy mirror.
  coga/skills/coga/testing/clean-install/macos-aws/SKILL.md: Legacy live copy mirror.
  coga/skills/coga/testing/clean-install/windows-aws/SKILL.md: Legacy live copy mirror.
  tests/legacy_removal_inventory.txt: Remove the coga/install twin row.
  tests/test_packaging.py: Remove coga/install from REQUIRED_BOOTSTRAP_CONTEXT_REFS.
review:
  reviewer: codex
  kind: self
  status: passed
  head: c1ced683e14e9699153ac8f5973ee3548bdef545
  base: 42e3ca6e0fa7ebe016943580541c698c690e89df
  detail: Direct review completed for all 26 diff paths after the rebase. Claude authored the retirement
    change; Codex independently reviewed that implementation and authored/self-reviewed only the earlier
    two-file size-exception correction. This resumed Codex session re-reviewed the final combined diff
    and the two authorized state repairs. No unresolved findings. All ten package/live pairs and the replacement
    links were checked. No child review CLI or subagent ran.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q --basetemp=/home/n/Code/.coga-pytest-v1-26-resume-20261104T2115
  status: passed
  head: c1ced683e14e9699153ac8f5973ee3548bdef545
  base: 42e3ca6e0fa7ebe016943580541c698c690e89df
  detail: 4453 passed, 10 skipped in 623.04 seconds on Linux with Python 3.12.12. The basetemp is outside
    the checkout so missing-repo tests cannot discover its real parent configuration.
- command: coga validate --json
  status: passed
  head: c1ced683e14e9699153ac8f5973ee3548bdef545
  base: 42e3ca6e0fa7ebe016943580541c698c690e89df
  detail: 'Exit 0: 96 OK, 11 warnings, no errors. Both previously blocking errors are resolved. Output
    saved at /tmp/coga-v1-26-resume-validation.json; the CLI imports this checkout.'
- command: rg -n -F 'coga/install' . --glob '!docs/archive/**' --glob '!coga/tasks/**' --glob '!coga/log.md'
  status: passed
  head: c1ced683e14e9699153ac8f5973ee3548bdef545
  base: 42e3ca6e0fa7ebe016943580541c698c690e89df
  detail: No live matches outside the explicitly excluded history; rg exit 1 is the expected no-match
    result. A separate scan for relative ../install/SKILL.md links also found none.
- command: git diff --check origin/main...HEAD
  status: passed
  head: c1ced683e14e9699153ac8f5973ee3548bdef545
  base: 42e3ca6e0fa7ebe016943580541c698c690e89df
  detail: No whitespace errors on the feature branch.
- command: uv tool update-shell --help
  status: passed
  head: c1ced683e14e9699153ac8f5973ee3548bdef545
  base: 42e3ca6e0fa7ebe016943580541c698c690e89df
  detail: uv 0.13.6 describes adding the tool executable directory to PATH. Confirmed against https://docs.astral.sh/uv/guides/tools/#installing-tools.
    No shell configuration was changed.
```

## Blockers

- [x] [2026-11-04 18:39] [agent:codex] id=20261104T183935 Authorize two limited ticket-history repairs so required coga validate --json can pass: replace coga/install with coga/init in the completed v1/29-test-and-fix-install-on-macos-and-windows context attachment, and classify the existing coordination note in v1/31-test-install-on-windows as Production notes. This task explicitly leaves coga/tasks history alone. The first error is introduced by retirement; the second already exists on main. The exact unapplied patch is recorded on the blackboard.
  resolved: [2026-11-04 21:12] [human:nicktoper] The human authorized both limited ticket-history repairs: replace the completed v1/29 context attachment coga/install with coga/init, and classify the existing v1/31 coordination note under Production notes without changing its prose. These two edits are an explicit exception to this task history exclusion.
