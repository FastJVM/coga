---
title: Update the testing topic's stale helper reference and Windows agent-fake fixture
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
launch_generation: pending:ca5c4fb5-1095-4b76-b681-f97033044102
---

## Description

Filed by Dream run recurring/dream, period 2026-W46 (run 20261112T051938Z), Phase 6 disposition. Two findings held as a draft because open PRs #1201 (Retro pytest-temp-roots) and #1195 already edit the target docs/contexts/coga-dev/testing/SKILL.md without carrying these fixes; handle after their review.

1. drift (Phase 3 ca-02): lines ~129-130 ('Do not pin to live dogfooded state') cite _strip_runtime_state in tests/test_autoclose_sweep.py; no such symbol exists in tests/ or src/ (removed in 5102c3be4). Replace the example or drop the parenthetical, keeping the rule.
2. extract (Phase 2 ks-13, source: done+checkout) from v1/14-interactive-coga-launch-on-native-windows, which stays on disk as retirement debt: native suite runs found ~126 orchestration tests that faked shutil.which, subprocess.run, or launch.run_with_done_marker but still resolved and ran the real installed claude.exe on Windows, because the Windows planner resolves against the child PATH/PATHEXT and spawns through ProcessTree. The fix is the autouse fixture tests/conftest.py::_windows_agent_spawn_follows_test_fakes (keeps the bare CLI name while one of those seams is faked, routes the no-console ungated spawn through a faked subprocess.run, exempts test_repl_supervisor_nt.py). Add a Windows test-writing bullet: a test that models an agent must fake one of those three seams. Verify against tests/conftest.py first.

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

branch: update-testing-topic-stale-helper

## Plan

- Item 1: `_strip_runtime_state` is absent from tests/ and src/ (grep). No current helper replaces it, so drop the parenthetical and keep the rule.
- Item 2: verified `tests/conftest.py::_windows_agent_spawn_follows_test_fakes` matches the description (seams: `shutil.which`, `subprocess.run`, `launch.run_with_done_marker`; exempts `test_repl_supervisor_nt`). Add a Windows test-writing bullet after the `windows_skip` bullet.

## Handoff (implement)

- Commit e4658cae7 on `update-testing-topic-stale-helper` (pushed, rebased on origin/main 8d463b93f). Only `docs/contexts/coga-dev/testing/SKILL.md` changed:
  - "Do not pin to live dogfooded state" now reads "Strip runtime fields or freeze the period; assert structure." The parenthetical is dropped because no successor helper exists.
  - Added the bullet "A test that models an agent must fake one of the agent seams" after the `windows_skip` bullet. It names the three seams, the PATH/PATHEXT + `ProcessTree` reason, the ~126-test finding, the conftest fixture, and the `test_repl_supervisor_nt.py` exemption.
- PR #1201 (still open) also edits this file in a different region. If it merges first, expect at most a trivial rebase.
- Adjacent pre-existing failure, not fixed here: `README.md:53` links to the deleted ticket `coga/tasks/document-the-remedy-for-a-bloated-blackboard-sibli.md` (deleted in 61388855a). This fails `tests/test_packaging.py::test_context_navigation_has_no_broken_links`, and both `tests/test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep` params fail because they re-run it. The draft `coga/tasks/make-retro-check-inbound-doc-links-before-deleting.md` references the same link; open-pr's freshness or the README owner needs to replace it.

## Peer review

- Completed independent direct review as Codex; implementation was by Claude (implement handoff and commit co-author trailer). No must-fix findings; no implementation changes made during review.
- Reviewed final head `00d5c8f611d30fdd160035eceed3db91aecf3143` against base `02daa839179d74ee42bf5c69f7186cb8388ea640`. Read the full testing topic, branch diff and commit, `tests/conftest.py::_windows_agent_spawn_follows_test_fakes`, and the Windows planner/spawn code and its dedicated tests. The missing helper has no matches in tests/ or src/; removing the cite preserves the rule. The Windows bullet matches all three fake seams, the no-console/ungated dispatch conditions, and the dedicated test-module exemption.
- Rebased unconditionally onto fetched main before review. Final fetch confirmed main still at the reviewed base; pushed the rebased branch with `--force-with-lease`, then returned this manual checkout to clean, current main before writing this handoff.
- Full Linux suite at the reviewed head: 3 failed, 4763 passed, 33 skipped in 743.13s. Failures are `tests/test_packaging.py::test_context_navigation_has_no_broken_links` and both parameters of `tests/test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep`; all trace to README.md:53's existing link to the ticket deleted in `61388855a`. README and that deletion are unchanged by this branch. `git diff --check` passed.
- No terminal/manual surface to drive: this is Markdown guidance only. Native Windows verification is inapplicable because no code, fixtures, or skip rules changed. The Linux receipt uses Python 3.12.12 and is not Python 3.11 floor evidence. PR recommendation is `deep` because the required suite has failures, despite no findings in this diff.

## PR

```yaml
title: Fix the testing topic's stale helper cite and add the Windows agent-seam rule
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5) in a megalaunch queue.
head: 00d5c8f611d30fdd160035eceed3db91aecf3143
base: 02daa839179d74ee42bf5c69f7186cb8388ea640
depth: deep
rationale: Bounded documentation change with completed independent review and no findings, but the required full suite fails on the pre-existing README link to a deleted ticket. Inspect that verification limitation before merging.
implementation: Drops the parenthetical citing the removed _strip_runtime_state helper while keeping the rule, and adds a Windows test-writing bullet requiring agent-modeling tests to fake shutil.which, subprocess.run, or launch.run_with_done_marker, citing conftest's _windows_agent_spawn_follows_test_fakes.
deviations: None.
limitations: No native Windows or terminal check is applicable to this documentation-only change; the described fixture and execution behavior are unchanged. Linux verification used Python 3.12.12, not the Python 3.11 floor. Three existing suite failures remain outside this diff.
files:
  docs/contexts/coga-dev/testing/SKILL.md: Remove stale helper cite; add Windows agent-seam test-writing bullet.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 00d5c8f611d30fdd160035eceed3db91aecf3143
  base: 02daa839179d74ee42bf5c69f7186cb8388ea640
  detail: Codex direct review completed on the final rebased diff with no must-fix findings; verified guidance against conftest and Windows planner/spawn code. Claude authored the implementation; no review fixes were needed.
checks:
  - command: PYTHONPATH=/home/n/Code/coga/src TERM=dumb .venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=/home/n/.codex/tmp/testing-topic-peer-20261112
    status: failed
    head: 00d5c8f611d30fdd160035eceed3db91aecf3143
    base: 02daa839179d74ee42bf5c69f7186cb8388ea640
    detail: Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.12.12; 3 failed, 4763 passed, 33 skipped in 743.13s. Navigation fails on README.md:53's pre-existing link to the deleted document-the-remedy-for-a-bloated-blackboard-sibli ticket; both final-package publication parameters fail on the same nested navigation check. Tested a clean committed tree.
  - command: git diff --check
    status: passed
    head: 00d5c8f611d30fdd160035eceed3db91aecf3143
    base: 02daa839179d74ee42bf5c69f7186cb8388ea640
    detail: No whitespace errors; checked on the feature branch before checkout return.
```
