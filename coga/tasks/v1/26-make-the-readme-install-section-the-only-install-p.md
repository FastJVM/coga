---
title: Retire the coga/install topic
status: blocked
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
step: 2 (peer-review)
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

2026-11-04, Codex: direct review **completed** against final head `3843c2f3eecd45f37f912d6b68f5fe6e15848ff2`
and base `b0a9929d36828dd2fc933ccebedf6ba2c0aa18a5`. All 26 diff paths were reviewed,
including the post-review correction. Claude authored the retirement change;
Codex independently reviewed that implementation, then authored and self-reviewed
only the two-file size-exception correction. No child review CLI or subagent ran.
The final combined receipt uses `self` to disclose that limited overlap.

Findings:
- **Fixed:** the enlarged coga/init topic needed the size review required by
  coga/knowledge. Its closing exception now records why the fresh-repo and clone
  contracts stay together; package and legacy copy match. Commit `3843c2f3e`.
- **Open, P2:** completed
  `coga/tasks/v1/29-test-and-fix-install-on-macos-and-windows/ticket.md`
  still attaches `coga/install` in frontmatter. Validation checks that attachment
  even though the ticket is done, so deletion introduces a `broken-context` error.
  The history exclusion in the reference search does not exempt context resolution.
- **Existing validation blocker:**
  `coga/tasks/v1/31-test-install-on-windows.md` has an
  `unsynthesized-draft-blackboard` error on unchanged main as well. Its existing
  documentation-coordination note needs synthesis or an explicit Production notes
  classification. The earlier PR receipt calling full validation passed is
  superseded by the failing receipt below.

Verification: the full suite passed with 4453 passed and 10 skipped; this ticket's
scoped validation passes, but repository validation exits 1 with the two errors
above. Exact commands and revisions are in `## PR`. Checked all ten affected
package/live pairs (nine identical, one deleted on both sides), the three unique
replacement link targets and their anchors, and the dependency/agent-offer,
version, uninstall and recurring compatibility statements against their code.
The Python-floor rationale already lives in coga-dev/testing. No runtime terminal
surface changed and no cloud clean-install walk was run.

The PATH wording was independently checked with `uv tool update-shell --help`
on uv 0.13.6 and the current
[Astral tools guide](https://docs.astral.sh/uv/guides/tools/#installing-tools).

Test setup note: the first full attempt used a basetemp inside this checkout and
was interrupted after missing-repo tests found the real parent Coga config.
A fail-fast reproduction had 1 failed and 34 passed and confirmed that cause.
The complete passing run used a directory outside the checkout. The repository
and ticket state were unchanged by those attempts.

The branch was rebased onto fetched main, the final diff reviewed, and pushed
with an explicit force-with-lease. This manual session returned to clean main
before writing this handoff. No PR has been opened and no workflow bump is due
until the required validation passes.

The ticket explicitly says `coga/tasks/` history is left alone, so neither
historical ticket was edited. A concrete, **unapplied** repair is available at
`/tmp/coga-v1-26-proposed-ticket-repairs.patch` and passes `git apply --check`:
change only v1/29's context attachment to `coga/init`, and put v1/31's existing
coordination note under `## Production notes` without changing its prose.
Owner permission for these two limited repairs, or resolution by those ticket
owners, is needed before this peer-review step can advance. After resolution,
reconcile with main, recheck the final diff and validation, refresh the receipts,
and bump once. The queue stop is `coga block`, preserving step 2.

## PR

```yaml
title: Retire the coga/install topic
author: claude/codex
author_evidence: The implement handoff records Claude Code (claude-opus-5-5) as the implementation
  author. This Codex peer-review session added only the init size-exception sentence and its legacy
  twin in commit 3843c2f3e.
head: 3843c2f3eecd45f37f912d6b68f5fe6e15848ff2
base: b0a9929d36828dd2fc933ccebedf6ba2c0aa18a5
depth: deep
rationale: 'The documentation retirement is bounded and the full suite passes, but full validation
  fails: retiring the context breaks a completed ticket attachment, and main already has an unrelated
  Windows draft-blackboard error. Approval to repair those excluded historical tickets is required
  before the workflow advances. Codex independently reviewed the Claude change and self-reviewed
  its own small correction.'
implementation: Deletes the install topic and its legacy twin, removes its packaging entries, moves
  surviving facts into init, recurring scheduling, the CLI index and the macOS harness, repoints
  installation links to README Get started, and adds the uv tool PATH remedy. The init topic now
  records its reviewed size exception.
deviations: Also corrects the stale init claim that op is offered for installation. Peer review records
  the required init topic size exception. Historical task files are left unchanged as the ticket
  directs, so the broken attachment remains an unresolved finding.
limitations: No new macOS/AWS or clean-machine installation was run. The PATH remedy was checked
  against uv 0.13.6 help and current Astral documentation. Tests ran on Linux with Python 3.12.12,
  not a new Python 3.11 or Windows run. Full repository validation is failing; the earlier passed
  receipt is superseded.
files:
  README.md: Add the uv tool PATH line (uv tool update-shell).
  docs/README.md: Drop the installation reference link; README is the only install path.
  docs/contexts/coga-dev/current-direction/SKILL.md: Repoint init-offer and Windows contracts to
    coga/init and coga/launch.
  docs/contexts/coga/architecture/SKILL.md: Legacy twin mirror of the package edit.
  docs/contexts/coga/cli/SKILL.md: Legacy twin mirror of the package edit.
  docs/contexts/coga/first-task/SKILL.md: Legacy twin mirror of the package edit.
  docs/contexts/coga/init/SKILL.md: Legacy twin of the init contract changes and reviewed size exception.
  docs/contexts/coga/install/SKILL.md: Deleted legacy twin of the retired topic.
  docs/contexts/coga/recurring/scheduling/SKILL.md: Legacy twin mirror of the package edit.
  docs/contexts/coga/uninstall/SKILL.md: Legacy twin mirror of the package edit.
  src/coga/dependencies.py: Docstring names coga/init instead of the retired topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: Topic map install
    entry points to README Get started.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Init install-first link
    to README; describe --version in the index row.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: Repoint install,
    upgrade and agent-install links.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Absorb external-CLI checks
    and install offers, correct the stale op claim, and record the reviewed size exception.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: Deleted the retired
    topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Absorb
    the CLI-older-than-templates note.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/uninstall/SKILL.md: Explain uv-tool install
    via README instead of the retired topic.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/SKILL.md: Install
    link to README Get started.
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
  status: failed
  head: 3843c2f3eecd45f37f912d6b68f5fe6e15848ff2
  base: b0a9929d36828dd2fc933ccebedf6ba2c0aa18a5
  detail: 'Direct review completed for all 26 diff paths and the final size-exception fix. Codex
    independently reviewed the Claude implementation; the combined revision is conservatively classified
    as self-review because Codex authored and reviewed the small follow-up. One unresolved P2 finding:
    completed v1/29-test-and-fix-install-on-macos-and-windows still attaches coga/install, introducing
    a broken-context validation error. The v1/31 draft-blackboard error is independently present
    on main.'
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q --basetemp=/home/n/Code/.coga-pytest-v1-26-peer-review-20261105
  status: passed
  head: 3843c2f3eecd45f37f912d6b68f5fe6e15848ff2
  base: b0a9929d36828dd2fc933ccebedf6ba2c0aa18a5
  detail: 4453 passed, 10 skipped in 594.68 seconds on Python 3.12.12. Executed on the final working
    tree, subsequently committed unchanged at the recorded head.
- command: coga validate --json
  status: failed
  head: 3843c2f3eecd45f37f912d6b68f5fe6e15848ff2
  base: b0a9929d36828dd2fc933ccebedf6ba2c0aa18a5
  detail: 'Exit 1: 93 OK, 12 warnings, 2 errors. New broken-context on completed v1/29-test-and-fix-install-on-macos-and-windows;
    pre-existing unsynthesized-draft-blackboard on v1/31-test-install-on-windows. Baseline main at
    the recorded base had 94 OK, the same 12 warning kinds/tasks, and only the latter error.'
- command: coga validate --task v1/26-make-the-readme-install-section-the-only-install-p --json
  status: passed
  head: 3843c2f3eecd45f37f912d6b68f5fe6e15848ff2
  base: b0a9929d36828dd2fc933ccebedf6ba2c0aa18a5
  detail: 'Exit 0: 1 OK, no issues.'
- command: rg -n -F 'coga/install' . --glob '!docs/archive/**' --glob '!coga/tasks/**' --glob '!coga/log.md'
  status: passed
  head: 3843c2f3eecd45f37f912d6b68f5fe6e15848ff2
  base: b0a9929d36828dd2fc933ccebedf6ba2c0aa18a5
  detail: No matches outside the explicitly excluded history; rg exit 1 is the expected no-match
    result. The completed ticket attachment inside the excluded history still affects validation.
- command: git diff --check origin/main...HEAD
  status: passed
  head: 3843c2f3eecd45f37f912d6b68f5fe6e15848ff2
  base: b0a9929d36828dd2fc933ccebedf6ba2c0aa18a5
  detail: No whitespace errors.
```

---

## Blockers

- [ ] [2026-11-04 18:39] [agent:codex] id=20261104T183935 Authorize two limited ticket-history repairs so required coga validate --json can pass: replace coga/install with coga/init in the completed v1/29-test-and-fix-install-on-macos-and-windows context attachment, and classify the existing coordination note in v1/31-test-install-on-windows as Production notes. This task explicitly leaves coga/tasks history alone. The first error is introduced by retirement; the second already exists on main. The exact unapplied patch is recorded on the blackboard.
