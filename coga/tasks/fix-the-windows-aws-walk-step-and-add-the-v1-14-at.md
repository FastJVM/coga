---
title: Fix the windows-aws walk step and add the v1-14 attended-launch harness gotchas
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 3 (open-pr)
agent: claude
launch_generation: 432cf7d5-27d8-4f5f-991a-14255e5d4a24
---

## Description

Filed by Dream recurring/dream, period 2026-W47 (run 20261118T170921Z), Phase 6 disposition. Target src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md is also edited by open Retro PRs #1256 and #1257, which add the Restricted-policy explanation and native-suite duration but leave step 2 showing the bare uv installer and do not carry the v1/14 gotchas. Phase 2 shards ks-23 (stale) and ks-11 (extract, source done+checkout: v1/14-interactive-coga-launch-on-native-windows is retirement debt; its branch still exists, so `coga retire` would delete it without Retro — this draft is the route for its remaining knowledge). Read the v1/14 ticket before it is retired for the full list.

Route: open a PR against the target once the overlapping PR(s) have landed or been rebased; the fix is pr-required (human review).

Finding: Windows attended-launch harness gotchas missing from windows-aws skill

- shard: ks-11
- class: extract
- target: v1/14-interactive-coga-launch-on-native-windows
- area: coga/testing/clean-install/windows-aws
- source: done+checkout

The ticket is `status: done`, but its `## Dev` branch `coga/v1-14-interactive-coga-launch-on-native-windows-e8b518` still exists locally and on `origin`, so this is `done+checkout` retirement debt. Nearly all of its durable knowledge already landed: the LF `.gitattributes` and Git `autoDetach` points are in `coga-dev/codebase/gotchas`, the DWORD/SystemExit and batch-shim transport in `coga-dev/internals/agent-spawn`, the Windows conftest fakes in `coga-dev/testing`, and the S4U long-run, Defender, `pty.fork`+`ssh -tt`+pyte driver and API-key guidance in `src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md`. A few verified box-run gotchas from "Implement — phase 2, session 2" have no home in that skill's "Attended agent session over SSH" / "Long native runs" sections, and they would trip the next attended run. (1) Auth alternative: the final acceptance used the owner logging in to their Claude subscription with `claude` over the harness `ssh`, with no API key. The skill names only the `ANTHROPIC_API_KEY`-over-stdin route. (2) Claude Code's first-run folder-trust dialog defaults to "No, exit". A driver that sends Enter ends the session with natural exit 1 (`bump1`). Pre-accept trust for the throwaway repo in the box's `~/.claude.json`. (3) Run the box-side launcher from a Python runner that ignores SIGINT/SIGBREAK and prints console modes before and after, not from a `.cmd` runner. A `.cmd` runner catches Ctrl+C itself ("Terminate batch job"), which is a harness artifact and not a Coga failure. (4) Defender exclusions may also need *process* exclusions (`python.exe`, `git.exe`, `uv.exe`), not just paths. Process exclusions are owner-added, since the agent's attempt was blocked, and both lists must be removed and verified empty before teardown. (5) The skill already covers a pending `usage` "claude transcript not found" before authentication? No, it does not: an unauthenticated onboarding session has no transcript, so that notice is expected there and not a usage bug. Add these as short bullets to the skill's attended-session section.

Finding: windows-aws skill shows the bare uv installer the walk no longer runs

- shard: ks-23
- class: stale
- target: src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md
- area: coga/testing/clean-install

The Walk section's step 2 says the walk runs "uv's official installer (`irm https://astral.sh/uv/install.ps1 | iex`)". `scripts/clean-install/windows-walk.ps1` `Install-Uv` (line 35) actually runs it in a child process as `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command 'irm https://astral.sh/uv/install.ps1 | iex'`, matching README.md line 135 (`powershell -ExecutionPolicy ByPass -c "irm … | iex"`). The distinction is load-bearing: v1/31's attended Windows 11 walk (finding 5, 2026-11-10) showed the bare form exits and closes the window under the client default `Restricted` policy, while Server 2025 defaults to `RemoteSigned`, so the harness never exercises that failure. Update step 2 to show the ByPass child-process form and note that harness evidence does not cover the client `Restricted` default.

Finding: walk-user phase skips the README's `uv python install 3.11 --default`

- source: fix-the-readme-windows-walk-findings-left-unowned (open-pr handoff, 2026-11-18)
- target: scripts/clean-install/windows-walk.ps1 (walk phase, line ~197) and the windows-aws skill Walk step 2 (line ~116)
- area: coga/testing/clean-install

That ticket's README change (v1/31 Finding 10) now tells Windows users to run `uv python install 3.11 --default`, then check that `python --version` resolves to uv's Python rather than the WindowsApps Store alias. The walk script's Administrator setup already uses `--default` (line ~86), but the walk-user phase and the skill's Walk step 2 still run plain `uv python install 3.11`, so a harness walk does not exercise the README's step or its PATH-precedence check. Align both with the README as merged.

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
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
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

## Dev

branch: coga/fix-the-windows-aws-walk-step-and-add-the-v1-14-at

## Plan (implement, 2026-11-18)

- Skill Walk step 2: show the walk's real ByPass child-process uv installer,
  `uv python install 3.11 --default` + `python --version`; note Server 2025
  covers neither the client `Restricted` default nor the Store alias.
- `windows-walk.ps1` walk phase: `--default`, then a `python --version` step
  resolved against the registry PATH a new terminal would get.
- Attended-session section: five short v1/14 gotcha bullets.
- Dependencies for open-pr: #1256/#1257 (same skill, other hunks) and #1267
  (README `--default`/`python --version`, which this aligns with) still open.

## Implement handoff (2026-11-18)

Done as planned; pushed `fff9598b3` on the branch (one commit over main
`5971b24e7`).

- `scripts/clean-install/windows-walk.ps1` walk phase: step
  `uv python install 3.11 --default`, then step `python --version`, which
  temporarily rebuilds `$env:Path` from the registry (`Refresh-MachinePath`,
  as a new terminal would), records `Get-Command python` source and version,
  and fails (exit 2) on a `\WindowsApps\` source or a non-3.11 version; PATH
  is restored afterward so later steps are unchanged. ASCII only.
- windows-aws skill: Walk step 2 rewritten (ByPass child-process installer,
  `--default`, `python --version`, Server 2025 evidence gaps); five gotcha
  bullets appended to "Attended agent session over SSH".
- Not verified natively: no Windows box this session; the new PowerShell step
  first runs on the next harness walk. If uv's installer leaves `.local\bin`
  off the user registry PATH or behind WindowsApps, that walk fails here,
  which is the README finding this check exists to catch.
- **For open-pr (ordering):** #1267 (README `--default` + `python --version`)
  is still open; this aligns the walk with it, so land #1267 first or at
  least together. #1256 (Restricted paragraph near the skill's top) and #1257
  (Long native runs) touch other hunks of the same skill; rebase after they
  land. #1256's paragraph partly overlaps this step-2 note; trim one if the
  reviewer prefers a single statement.
- v1/14 knowledge carried: points (1)–(5) of the ks-11 finding; the rest was
  already homed per the Description. v1/14 can be retired once this merges.

## Peer review

Independent direct Codex review completed on head `ab243ceb52b574d2890652abb8176229909a2d94`
against main `b3129bbb27acbc096ce2a867ee77d72c16814c97`. Claude implemented
the original patch. Codex rebased it, fixed one finding, then reviewed
the resulting two-file diff and checked the five attended-launch notes
against v1/14's phase 2 handoff.

The first version accepted any non-Store Python 3.11 on PATH. The revised
step compares the resolved executable with `python.exe` in
`uv python dir --bin` before invoking it. It still validates the version and
uses the registry-derived PATH for resolution. No unresolved code findings.

Linux PowerShell 7.7 parsed the full script and ran the committed step with
simulated command resolution. Expected cases passed: uv's 3.11 returned 0,
shadowed Python and wrong version each returned 2, and missing Python returned
1. The successful case restored the caller's PATH. Windows PowerShell 5.1,
native registry PATH and actual Store alias behavior remain unverified.
The interactive launch instructions describe existing behavior from v1/14.

At handoff, PRs #1256 and #1257 were open. They change the same runbook's
environment and long-run notes, respectively. Follow the ticket's publication
order and reconcile their changes before opening this PR. In particular,
#1256 overlaps the Restricted-policy explanation. The Windows README
alignment comes from open PR #1267, which should land first or together.

## PR

```yaml
title: Align the Windows walk with the README and add attended-run gotchas
author: claude
author_evidence: >-
  Claude Code (claude-opus-5-5) implemented the original patch, as recorded
  in the implement handoff. Codex authored the peer-review follow-up
  ab243ceb5 that tightens executable validation.
head: ab243ceb52b574d2890652abb8176229909a2d94
base: b3129bbb27acbc096ce2a867ee77d72c16814c97
depth: deep
rationale: >-
  Inspect the new fail-fast Windows PATH check. Linux tested its decision
  logic with a simulated resolver. Windows PowerShell 5.1, native PATH
  resolution and publication ordering still need attention.
implementation: >-
  The walk-user phase installs Python 3.11 with --default and checks that
  python resolves to uv's unversioned executable and reports 3.11. The
  runbook records the installer child process, Server 2025 coverage limits
  and five attended-launch findings from v1/14.
deviations: >-
  The harness builds the registry-derived PATH for command discovery,
  checks the resolved location against uv python dir --bin, then runs
  the selected executable with --version.
limitations: >-
  Native verification is deferred to release. The Server 2025 harness
  cannot cover the Windows 11 Restricted policy or Store alias.
  Publication must account for open runbook PRs #1256 and #1257 and
  Windows README PR #1267.
files:
  scripts/clean-install/windows-walk.ps1: >-
    Exercise the README's --default and python --version steps as the
    fresh walk user, including PATH precedence.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md: >-
    Document the actual walk commands and Server 2025 evidence gaps and
    retain the five attended-run notes from v1/14.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: ab243ceb52b574d2890652abb8176229909a2d94
  base: b3129bbb27acbc096ce2a867ee77d72c16814c97
  detail: >-
    Direct independent review of Claude's implementation completed.
    Codex fixed a false pass for a shadowing Python 3.11 and reviewed
    the resulting head, including its own follow-up. No unresolved code
    findings.
checks:
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider
    status: passed
    head: ab243ceb52b574d2890652abb8176229909a2d94
    base: b3129bbb27acbc096ce2a867ee77d72c16814c97
    detail: >-
      5004 passed, 33 skipped in 844.69 seconds. Linux Pop!_OS 24.04 LTS, Python 3.12.12, clean committed tree.
  - command: bash /tmp/coga-windows-walk-peer-pwsh/run-probe.sh
    status: passed
    head: ab243ceb52b574d2890652abb8176229909a2d94
    base: b3129bbb27acbc096ce2a867ee77d72c16814c97
    detail: >-
      Temporary PowerShell 7.7 probe on Linux parsed the script and executed
      its Step function and the Python check against mocked resolution.
      All four exit-code cases and the successful PATH restoration passed.
  - command: .venv/bin/coga validate --json
    status: passed
    head: ab243ceb52b574d2890652abb8176229909a2d94
    base: b3129bbb27acbc096ce2a867ee77d72c16814c97
    detail: >-
      Exited zero with 17 warnings and no errors.
  - command: git diff --check main...HEAD
    status: passed
    head: ab243ceb52b574d2890652abb8176229909a2d94
    base: b3129bbb27acbc096ce2a867ee77d72c16814c97
    detail: >-
      No whitespace errors.
  - command: Windows clean-install walk on Server 2025
    status: not-run
    detail: >-
      Native Windows verification is deferred to release under coga-dev/testing.
```
