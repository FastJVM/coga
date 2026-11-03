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
step: 3 (open-pr)
agent: claude
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

## Dev

branch: coga/add-a-skill-for-the-attended-human-fresh-machine-i-84cdf7

## Implementation record

Claude Opus 5.5 authored the initial implementation (implement handoff),
pushed as `d0d07b353`; Codex rebased it as `13f662555` and committed the review
corrections as `35c0a7801`. The old implementation check receipts are
historical; `## PR` records this step's final verification.

Current decisions:

- `coga/testing/fresh-vm` owns shared VM preparation for both participants;
  `human-walk` owns the helper's method, with participant conduct in its guide.
- The v1/29 guide is now a compatibility pointer. Its separate dated findings
  remain untouched. Both new skills stay local; no packaged twin changed.
- PR #1145 is still separate and open. Its integration should cite
  `coga/testing/fresh-vm` instead of becoming another VM procedure owner.

## Peer review

Direct Codex review **completed**. The independent initial review covered
`13f662555eda4fb9cf12efcbc843c847536ed7b9` against
`04ec6bf9f967d7ebe2f0ad90dd9712b4172818d6`. After applying findings, Codex
reviewed the complete final diff at `35c0a7801fa18983c6ee032147f1a8016abfc3b5` against `04ec6bf9f967d7ebe2f0ad90dd9712b4172818d6`.
The final receipt is marked self-review because the reviewer authored the
corrections; the initial Claude implementation was independently reviewed.
No unresolved findings. No nested agent CLI or review tool was used.

Corrected findings:

1. Removed competing VM instructions and the false claim that a new macOS account has no Homebrew. The shared fresh-vm skill is now the single setup/baseline/reuse/cleanup owner, written for both participants.
2. Replaced guide-for-zach.md with a compatibility pointer; preserved the separate dated evidence attachment. The old guide no longer supplies stale platform-failure and timing instructions.
3. Scoped snapshot/clipboard limitations to the observed bare UTM setup and linked current UTM support. Removed the assumed Claude artifact-service dependency; added guest-readable command transfer and host screenshots when paste is unavailable.
4. Removed reliance on the old Windows OOBE local-account bypass and made account setup follow the selected Windows build. The Windows baseline records caption/build/architecture through CIM and looks up both agent CLIs without invoking Python aliases.
5. Kept the ticket's artifact source and done criteria authoritative, including v1/31's candidate wheel and completed-task requirement. Re-walk evidence records the resolved commit rather than only an ambiguous main package version.

Verification: the exact final-head commands and counts are under `## PR`.
Both new skills also passed skill-creator's `quick_validate.py`. An inline
Python link/anchor scan checked 15 repository links in the four procedure
files; the three shell snippets passed `bash -n` without execution.

No executable terminal surface changed. The Mac/Windows GUI procedures were
reviewed against the source walk evidence and vendor docs, not driven in a
VM in this Linux session; no attended install outcome is claimed. UTM's
[current guest support](https://docs.getutm.app/guest-support/macos/),
Microsoft's [OOBE update](https://blogs.windows.com/windows-insider/2025/10/06/announcing-windows-11-insider-preview-build-26220-6772-dev-channel/),
the [VirtualBox manual](https://download.virtualbox.org/virtualbox/7.0.22/UserManual.pdf),
and Microsoft's [OS inventory example](https://learn.microsoft.com/en-us/powershell/scripting/samples/collecting-information-about-computers)
support the platform corrections.

The feature branch is committed and pushed, and the checkout is back on
`main`. Next is the mechanical PR-opening step.

## PR

```yaml
title: Add attended install-walk guidance with shared VM preparation
author: claude/codex
author_evidence: The implement handoff identifies Claude Opus 5.5 as author of d0d07b353
  (rebased as 13f662555). Codex applied the peer-review corrections in 35c0a7801 in this
  session.
head: 35c0a7801fa18983c6ee032147f1a8016abfc3b5
base: 04ec6bf9f967d7ebe2f0ad90dd9712b4172818d6
depth: skim
rationale: 'Bounded documentation change with no executable runtime or packaged resource
  changes. Direct review, the full Linux suite, and task validation passed. Read the VM
  version assumptions and the scope limits: Codex reviewed its own corrections, and no attended
  Mac or Windows walk was performed.'
implementation: Extracts the attended install method and participant guide from v1/29 into
  maintained local skills. VM setup, baseline capture, reuse, and cleanup now have one shared
  owner usable by competitor trials. The original guide becomes a compatibility pointer,
  while dated observations remain in their attachment.
deviations: Shared VM preparation lives at coga/testing/fresh-vm rather than under human-walk.
  Review replaced historical blanket UTM limitations and the Windows local-account bypass
  with version-aware guidance, and made ticket-defined artifacts and completion criteria
  authoritative.
limitations: 'No actual macOS/Windows VM walk ran in this Linux session; the Python suite
  does not validate those GUI instructions. New skills remain local. The separate open PR
  #1145 still needs to cite fresh-vm when its competitor-trial skill is integrated.'
files:
  coga/skills/coga/testing/clean-install/human-walk/SKILL.md: Helper procedure for recording
    attended observations and verifying fixes against the ticket-specified artifact and
    completion criteria.
  coga/skills/coga/testing/clean-install/human-walk/operator-guide.md: Generalized participant
    instructions, note template, and wrap-up, linking the shared setup procedure.
  coga/skills/coga/testing/fresh-vm/SKILL.md: Single shared VM preparation and reuse procedure,
    including inherited-tool exclusions, stub-safe baselines, and version-aware transfer/account
    setup.
  coga/tasks/v1/29-test-and-fix-install-on-macos-and-windows/guide-for-zach.md: Replace
    the duplicated legacy guide with a pointer so its existing entry point reaches the maintained
    procedure without losing dated evidence.
  docs/README.md: Index the two local skills.
  docs/contexts/coga-dev/testing/SKILL.md: Link the attended walk as the human counterpart
    to the automated harnesses.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 35c0a7801fa18983c6ee032147f1a8016abfc3b5
  base: 04ec6bf9f967d7ebe2f0ad90dd9712b4172818d6
  detail: Direct review completed with no unresolved findings. Codex independently reviewed
    Claude's rebased 13f662555, then applied the recorded findings and reviewed the complete
    final diff at 35c0a7801. Classified as self-review for the final receipt because Codex
    authored those corrections; no nested review CLI or second agent was used.
checks:
- command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest -q
  status: passed
  detail: 4306 passed, 10 skipped in 550.84 seconds on Linux with Python 3.12.12. No macOS,
    Windows, or Python 3.11 execution is claimed.
  head: 35c0a7801fa18983c6ee032147f1a8016abfc3b5
  base: 04ec6bf9f967d7ebe2f0ad90dd9712b4172818d6
- command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m coga.cli validate
    --task add-a-skill-for-the-attended-human-fresh-machine-i --json
  status: passed
  detail: 1 task checked; no issues.
  head: 35c0a7801fa18983c6ee032147f1a8016abfc3b5
  base: 04ec6bf9f967d7ebe2f0ad90dd9712b4172818d6
- command: git diff --check origin/main...HEAD
  status: passed
  detail: No whitespace errors.
  head: 35c0a7801fa18983c6ee032147f1a8016abfc3b5
  base: 04ec6bf9f967d7ebe2f0ad90dd9712b4172818d6
```
