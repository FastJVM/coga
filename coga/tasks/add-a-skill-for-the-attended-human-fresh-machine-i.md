---
title: Add a skill for the attended human fresh-machine install walk
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
launch_generation: 412d29e2-7307-49a6-9b98-7d7ade178852
---

## Description

Gap filed by Dream run 2026-11-02 (run 20261102T223931Z), Phase 2 knowledge scan, shard ks-install-1. Target: new skill coga/skills/coga/testing/clean-install/human-walk/SKILL.md (sibling of the automated macos-aws / windows-aws harness skills under coga/skills/coga/testing/clean-install/).

Three tickets run the same attended pattern: a non-engineer walks a tool install by hand on a spare cogatest UTM VM while an agent session on their normal account records findings. They are v1/29-test-and-fix-install-on-macos-and-windows (the whole procedure lives only in its attachment guide-for-zach.md and its agent-side facts), competition-testing/test-compound-engineering (done) and competition-testing/test-kiro; v1/31-test-install-on-windows is queued to repeat it. The reusable know-how exists only in ticket bodies:
- UTM cannot snapshot macOS guests, so Clone after deleting the cached .ipsw (~18 GB) or the clone fills the disk mid-walk; about 45 GB free is needed.
- VirtualBox needs Skip Unattended Installation, or it bypasses OOBE.
- A new user account leaks machine-wide CLT git, python.org Python in /usr/local/bin and Homebrew, so it cannot reproduce the git-stub or Python-floor steps.
- The baseline command must avoid invoking the /usr/bin/git or python3 stubs.
- UTM shares no clipboard with a macOS guest, so retyped out-of-band commands are VM artifacts, not findings.
- Revert a reused VM to a bare snapshot first.
- Conversational wall-clock times are not timing evidence.
- Re-walks of merged fixes install from PyPI or from uv tool install git+...@main.

coga/skills/coga/testing/clean-install/SKILL.md covers only the automated AWS harnesses. Related: Retro PR https://github.com/FastJVM/coga/pull/1145 adds coga/skills/competition-testing/hands-on-trial for competitor trials, which overlaps on VM hygiene. Decide whether the shared VM-hygiene part belongs in one skill both cite, and move the durable parts of guide-for-zach.md out before v1/29 retires.

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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: coga/add-a-skill-for-the-attended-human-fresh-machine-i-84cdf7

## Handoff — implement, 2026-11-02

Pushed `d0d07b353`; no PR yet (open-pr step).

Decisions:

- **Shared VM hygiene is its own skill**, `coga/skills/coga/testing/fresh-vm/SKILL.md`,
  cited by `clean-install/human-walk`. It is placed under `coga/testing/`
  rather than inside `human-walk` so a competitor trial can cite it without
  reaching into an install-walk skill. PR #1145 (`competition-testing/hands-on-trial`,
  open, not ours) is left untouched. Follow-up for whoever lands #1145 or
  for retro: replace its "Fresh VM" bullet's VM details with a citation of
  `coga/testing/fresh-vm`.
- **guide-for-zach.md's durable parts moved** to
  `clean-install/human-walk/operator-guide.md`, generalized: no names or
  dates, the perishable Windows `fcntl` paragraph replaced by "your helper
  tells you what is known to fail", and the stopwatch/"Time" field replaced
  by a "Waiting" field, matching the rule that conversational wall-clock
  times are not timing evidence. The original attachment stays on v1/29
  (in review, owner zach); it can be deleted when v1/29 retires.
- **Not packaged.** The Linux/AWS harness skills have bootstrap twins; the
  new two describe this team's spare `cogatest` VMs and stay local, like
  `coga/skills/marketing`. A link added to the packaged
  `clean-install/SKILL.md` was reverted because it would have needed a twin
  edit pointing at a non-shipped skill; the index (`docs/README.md`) and
  `coga-dev/testing` link the new skills instead.
- All eight ticket bullets are covered: .ipsw-before-clone and ~45 GB,
  VirtualBox Skip Unattended, leaked machine-wide tools, stub-safe baseline,
  UTM clipboard, revert-to-bare, wall-clock not evidence (human-walk),
  PyPI vs `git+...@main` re-walks (human-walk).

## PR

```yaml
title: Add attended human install-walk and fresh-VM skills
author: claude
author_evidence: >-
  Implemented in this session by Claude Opus 5.5 (claude-opus-5-5) under a
  megalaunch queue pick; no agent override.
head: d0d07b35357655bafef943da52bb063e94fe1cb2
base: 851af79289e779ddb885508764be8b2c4d97585c
depth: light
rationale: >-
  Documentation-only: two new local (unpackaged) skills, one attachment, and
  two index/link lines. No code, no packaged twin touched. Facts are moved
  from v1/29's guide and agent-side notes, the CE/Kiro tickets, and
  macos-walk-findings.md rather than newly asserted.
implementation: >-
  New coga/testing/clean-install/human-walk skill (agent method for an
  attended first-time install walk) with a generalized plain-language
  operator guide, and a new coga/testing/fresh-vm skill owning cogatest VM
  preparation, baseline, reuse and teardown, shared with competitor trials.
deviations: >-
  The shared VM-hygiene part lives at coga/skills/coga/testing/fresh-vm
  rather than inside human-walk, so competitor trials can cite it.
limitations: >-
  PR #1145's hands-on-trial skill does not yet cite fresh-vm (open PR, not
  this ticket's). guide-for-zach.md remains on v1/29 until it retires.
files:
  coga/skills/coga/testing/clean-install/human-walk/SKILL.md: >-
    New skill: roles, walk rules, record format, what a walk cannot measure,
    fix-and-re-walk loop with PyPI vs main installs, wrap-up.
  coga/skills/coga/testing/clean-install/human-walk/operator-guide.md: >-
    Plain-language tester guide moved from v1/29's guide-for-zach.md,
    generalized (no names, dates, or perishable platform failures).
  coga/skills/coga/testing/fresh-vm/SKILL.md: >-
    New shared skill: VM over new account (leaked tools), UTM clone/.ipsw
    order and clipboard, VirtualBox OOBE, stub-safe baselines, revert-to-bare,
    teardown.
  docs/README.md: Index links to the two new skills.
  docs/contexts/coga-dev/testing/SKILL.md: >-
    One sentence naming the attended walk as the harnesses' hand-run
    counterpart.
review:
  status: not-run
  detail: >-
    No code review yet; the workflow's peer-review step follows.
checks:
  - command: .venv/bin/python -m pytest -q
    status: passed
    head: 9e2f45c0e (pre-rebase; same diff as d0d07b353)
    base: 17f46d9e5
    detail: >-
      4306 passed, 10 skipped in 527s. The rebase onto 851af7928 added only a
      Coga-state commit; `git diff 9e2f45c0e d0d07b353 -- coga/skills docs`
      is empty.
  - command: .venv/bin/python -m pytest -q tests/test_packaging.py tests/test_validate.py tests/test_skill_manager.py
    status: passed
    head: d0d07b35357655bafef943da52bb063e94fe1cb2
    base: 851af79289e779ddb885508764be8b2c4d97585c
    detail: 279 passed at the final head.
  - command: coga validate --json
    status: passed
    head: 9e2f45c0e
    detail: >-
      No issues from this change; existing errors and warnings are on other
      tickets (v1/19, v1/26, v1/27, v1/31 draft blackboards, and others).
```
