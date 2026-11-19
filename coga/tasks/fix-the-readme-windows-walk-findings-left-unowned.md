---
title: Fix the README Windows walk findings left unowned by v1-33
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
step: 2 (peer-review)
agent: claude
---

## Description

Filed by Dream recurring/dream, period 2026-W47 (run 20261118T170921Z), Phase 6 disposition of Phase 4 Retro follow-ups. Target README.md (native-Windows install section). v1/31-test-install-on-windows (active) records README doc findings whose recorded owner, v1/33-review-all-doc, is done and deleted, so no live ticket owns them; Retro of v1/45-fix-the-readme-s-native-windows-install-steps flagged them as deferred should-fix items. Still true on main 2026-11-18: Finding 6 (minor) — README's manual `git var GIT_AUTHOR_IDENT` pre-check (README.md ~line 159) duplicates coga init's fail-loud guard and says set identity 'in this repo' while init's message says --global; make them agree or drop the pre-check. Finding 7 (moderate) — 'Change into your project's Git repository' gives no way to create one for the new-empty-repo path, and PowerShell opens in C:\WINDOWS\system32; spell out mkdir <name>; cd <name>; git init. Finding 10 (moderate) — README's `uv python install 3.11` (README.md ~line 142) gives no `python` command (uv exposes only a versioned shim, so python resolves to the WindowsApps Store stub); consider `uv python install 3.11 --default` or a README note. Read v1/31's blackboard 'Findings' for full evidence before editing; human Windows 11 walk is the check.

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

branch: coga/fix-the-readme-windows-walk-findings-left-unowned

## Implement handoff

Done on `coga/fix-the-readme-windows-walk-findings-left-unowned` (pushed, commit 1ceeb41f5, README.md only):
- Finding 6: removed the `git var GIT_AUTHOR_IDENT` pre-check and the per-repo `git config` advice. The README now says init stops before writing anything and prints the `git config --global` commands, which matches `commands/init._check_git_identity` and init's fail-before-writes ordering (v1/31 S7a/S8 evidence).
- Finding 7: "Initialize a repository" now explains how to create a new repo (`cd ~`, `mkdir my-project`, `cd my-project`, `git init`) and says PowerShell opens in system32. These lines run in both PowerShell and sh.
- Finding 10: changed to `uv python install 3.11 --default`, plus a one-line note that without it `python` opens the Store stub. `scripts/clean-install/windows-walk.ps1` already uses `--default` for the same reason.

Limitations / for review:
- Not verified on Windows. The ticket names the human Windows 11 walk as the check. Not verified: whether uv's bin dir precedes `%LOCALAPPDATA%\Microsoft\WindowsApps` on a fresh user PATH, so `--default` actually shadows the stub.
- Not changed (out of scope): the windows-aws walk skill (`skills/coga/testing/clean-install/windows-aws`, walk step 2) and `windows-walk.ps1` walk phase still run plain `uv python install 3.11` for the walk user, so a walk does not exercise the README's new `--default`. Consider aligning it in a follow-up if the walk should mirror the README exactly.
- v1/31 Findings 6/7/10 still say "owner v1/33; open". After merge, whoever closes this should mark them resolved there.

## PR

```yaml
title: Fix README init and Windows Python steps from the Windows walk
author: claude
author_evidence: >-
  Implement session ran as Claude Code (Opus 5.5) in a megalaunch queue step.
head: 1ceeb41f5ae37d3e89f8d8112f28ee73736a5c8b
base: 586aa99608ab6910c199f576a45be46b86c8867f
depth: skim
rationale: >-
  README-only wording change in the install and init sections; check the
  shell portability of the new-repo commands and the identity wording against init.
implementation: >-
  Drops the README's manual git identity pre-check in favor of init's own
  guard, spells out creating a new repo from the home folder, and installs
  uv's Python with --default so python is not the Microsoft Store stub.
deviations: "None."
limitations: >-
  No Windows run; the human Windows 11 walk is the acceptance check. The
  windows-aws walk harness still runs plain uv python install 3.11 for the
  walk user.
files:
  README.md: >-
    Fix v1/31 Windows walk findings 6, 7 and 10 in the install and
    Initialize a repository sections.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: >-
    Peer review is the next workflow step; no review has run yet.
checks:
  - command: .venv/bin/python -m pytest -q
    status: passed
    head: 1ceeb41f5ae37d3e89f8d8112f28ee73736a5c8b
    base: 586aa99608ab6910c199f576a45be46b86c8867f
    detail: >-
      5004 passed, 33 skipped in 777.90s. The shell python lacked tomlkit, so
      the first plain python -m pytest run failed at collection; reran with
      the repo venv.
```
