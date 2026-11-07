---
title: Honor CODEX_HOME when locating Codex rollouts
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

`usage._codex_rollout_paths` globs `~/.codex/sessions/**/rollout-*.jsonl`
unconditionally. Codex keeps its sessions under `$CODEX_HOME/sessions` when
`CODEX_HOME` is set. For a user who sets it, every Codex launch would therefore
record `usage_status` unknown with reason `codex rollout not found for cwd`.
This has not been seen in this repo, where `CODEX_HOME` is unset. It was found
while closing `v1/35-recheck-codex-usage-completeness-after-the-session`.

Done means:

- The rollout root is `$CODEX_HOME/sessions` when `CODEX_HOME` is set and
  non-empty, and `~/.codex/sessions` otherwise. The value is used exactly as
  written, with no `~` expansion, to match Codex.
- A regression test in `tests/test_usage.py` sets `CODEX_HOME` to a directory
  outside `HOME`, writes a rollout there, and asserts that the session is
  snapshotted and parsed to `ok`.
- The existing Codex tests in `tests/test_usage.py` clear `CODEX_HOME`, for
  example with an autouse fixture, so they pass when a developer has it set.
- `coga/usage` and `coga-dev/internals/activity-capture` both state the
  lookup rule.
- `python -m pytest tests/test_usage.py tests/test_packaging.py` passes.

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

### Code pointers

- `usage._codex_rollout_paths` is the only place the root is built:
  `Path.home() / ".codex" / "sessions"`. Two functions call it.
  `usage.snapshot_session_files` takes the pre-spawn snapshot, and
  `usage._parse_codex_session` takes the post-run diff. Because both go through
  the same helper, they read the same root. Keep it that way by deciding the
  root in that one helper.
- `CODEX_HOME` is read from the environment of the coga process. The agent
  child inherits that environment, so coga and Codex see the same value.
  An empty string counts as unset. Do not expand `~`. The cold review
  recalled, without checking, that codex-rs `find_codex_home` treats empty as
  unset, uses the literal value, and errors if the path is missing. Confirm
  that against Codex's docs or source before you implement, and if Codex
  behaves differently, write down what you found on the blackboard.
- Out of scope, and to be documented as unsupported:
  - a relative `CODEX_HOME`, which Codex resolves against its own working
    directory (the checkout), while coga's cwd may differ;
  - a `CODEX_HOME` set only in the agent child's environment, through ticket
    `secrets:` or agent env config.
- The other `.codex` references in `init.py`, `uninstall.py`, `update.py`, and
  `skill_manager.py` are about the repo-local `.codex/skills` directory, not
  rollouts. Leave them alone.
- Existing Codex tests in `tests/test_usage.py` set `HOME` with
  `monkeypatch.setenv("HOME", tmp_path)` and write rollouts under
  `tmp_path/.codex/sessions`. Give the new test the same shape, and make the
  existing tests clear `CODEX_HOME` with `monkeypatch.delenv(...,
  raising=False)`, so that a developer with `CODEX_HOME` set does not see them
  fail.
- Out of scope: the Claude transcript root (`~/.claude/projects/...` in
  `usage`) has the same kind of hard-coded path but a different override
  (`CLAUDE_CONFIG_DIR`). Leave it alone and only mention it on the blackboard
  as a possible follow-up.

### Docs to edit (cited, not attached — this ticket edits them)

- `coga/usage`: the package owner is
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md`.
  It has a legacy live copy at `docs/contexts/coga/usage/SKILL.md`, listed in
  `tests/legacy_removal_inventory.txt`. Edit the package copy, mirror the
  change into the live copy byte for byte, and commit both together, or
  `tests/test_packaging.py` fails. The topic does not mention Codex rollouts
  yet. Add one sentence near the explanation of `unknown`: where Codex
  rollouts are looked up, and that a rollout missing from that root is
  recorded as unknown, not as zero.
- `coga-dev/internals/activity-capture`
  (`docs/contexts/coga-dev/internals/activity-capture/SKILL.md`, local only):
  the Codex paragraph currently says capture snapshots
  `~/.codex/sessions/**/rollout-*.jsonl`. Change it to give the
  `CODEX_HOME` rule.

<!-- coga:blackboard -->

## Dev

branch: coga/v1-honor-codex-home-when-locating-codex-rollouts-5b4cd1


The blackboard is a notepad to be written to often as the human and agent works through a task.
## Handoff (implement)

- Codex behavior verified against `codex-rs/utils/home-dir/src/lib.rs`
  (`find_codex_home`, openai/codex main, fetched 2026-11-06): empty
  `CODEX_HOME` is filtered to unset; value is `PathBuf::from(val)` (no `~`
  expansion); a missing path or a non-directory is a fatal error; a valid one
  is canonicalized. Matches the ticket's recollection.
- `usage._codex_sessions_root` decides the root once; `_codex_rollout_paths`
  (used by both `snapshot_session_files` and `_parse_codex_session`) globs it.
  The literal (non-canonicalized) path is globbed; that is equivalent for
  discovery.
- Tests: autouse `_clear_codex_home` fixture in `tests/test_usage.py`; new
  `test_parse_codex_rollout_honors_codex_home_outside_home` (CODEX_HOME outside
  HOME, decoy rollout under `~/.codex` ignored, snapshot + parse to `ok`).
  It fails without the fix. The usage suite also passes with
  `CODEX_HOME=/tmp/nonexistent-codex` exported.
- Docs: `coga/usage` package + live copy (byte-identical), and
  `coga-dev/internals/activity-capture` state the rule and the unsupported
  cases (relative CODEX_HOME; child-only CODEX_HOME via secrets/agent env).
- Pre-existing failures, not caused here (they fail identically with this
  change stashed; root cause: `Sync coga state` commits 421ee15c0/a8fe8af9c
  swept v1/14 and v1/13 live-copy edits onto main. Owner chose a separate
  fix: branch `fix/revert-swept-legacy-doc-copies`, packaging 37 passed
  there; PR https://github.com/FastJVM/coga/pull/1185. Once it merges, rebase this branch
  and rerun `tests/test_packaging.py`): `test_packaging.py::test_live_and_packaged_copies_stay_identical`
  (`coga/checkouts/launch-boundary` live vs package drift) and
  `test_context_navigation_has_no_broken_links` (missing anchors linked from
  `coga-dev/current-direction`, e.g. `coga/install#windows-baseline`).
- Possible follow-up (out of scope, not filed): Claude transcript root in
  `usage` hard-codes `~/.claude/projects` and ignores `CLAUDE_CONFIG_DIR`.

## Peer review

- Independent Codex direct review **completed**, including a final rereview
  after reconciliation, on head `d94674f7f0b7dbbcaff09600b69dde6e351a179a`,
  base `0a150faf1a0925530533812de8927b6dabb8d042`. Claude implemented the
  change (implement handoff and commit's Claude Opus 5.5 coauthor). This fresh
  Codex session reviewed all five diff paths, snapshot/parser callers, the
  launch environment boundary, test isolation, and documentation. **No
  must-fix code findings**; no implementation edits were needed.
- Rebased twice onto fetched main, without conflicts. Both times the projected
  ticket was backed up, verified, and restored byte for byte. The last main
  movement changed only phone-home build instructions and their explanatory
  packaging-exception string; runtime code, test assertions, and all five
  implementation paths were unchanged. The usage package/live pair is
  byte-identical. The final diff has one implementation commit ahead of main.
  Pushed final head `d94674f7f0b7dbbcaff09600b69dde6e351a179a` with an
  explicit `--force-with-lease` against the implement head; push succeeded.
- Rechecked `openai/codex`'s `codex-rs/utils/home-dir/src/lib.rs` via the
  GitHub connector (blob `caa43569c78bae9f5cc875092f378f4d935b8063`): empty is
  unset, `PathBuf::from` is literal, and valid custom directories are
  canonicalized. Official state-location docs:
  https://learn.chatgpt.com/docs/config-file/config-advanced#config-and-state-locations.
  Read-only scratch probes on the earlier, byte-identical implementation
  passed for unset/empty/custom roots, a literal tilde path component, a
  symlink root, and a missing root. No interactive terminal surface changed;
  terminal rendering checks are inapplicable.
- Final-head focused receipt: Pop!_OS 24.04 LTS, Python 3.12.12,
  `PYTHONPATH=/home/n/Code/claude/coga/src TERM=dumb .venv/bin/python -m pytest tests/test_usage.py tests/test_packaging.py`
  -> **75 passed, 2 failed in 4.39s**. All 40 usage tests pass. The two
  failures are `test_live_and_packaged_copies_stay_identical` (launch-boundary
  live/package drift) and `test_context_navigation_has_no_broken_links`
  (missing anchors). Both also reproduced on an isolated export of base
  `39610a034be9205b60476ef2684ac146efc10d0e`, excluding `docs/archive/`
  (2 failed in 0.69s). PR #1185 is still open and unmerged.
- Full Linux suite **returned**: same OS/interpreter,
  `PYTHONPATH=/home/n/Code/claude/coga/src TERM=dumb .venv/bin/python -m pytest`
  -> **4504 passed, 10 skipped, 2 failed in 638.56s**, with only those same
  two packaging failures. This receipt covers head
  `6b715e056770ab68f03076fa3400874d71b638c2`, base
  `39610a034be9205b60476ef2684ac146efc10d0e`, before the final documentation
  rebase. It remains historical: the affected focused suites were rerun on
  final head, and the full suite was not repeated for the prose-only drift.
  Python 3.11 was not exercised.
- Native Windows receipt is not recorded. `coga-dev/testing` requires it
  before approving path-sensitive changes. All four locally recorded Windows
  harness runs have teardown markers, and no `AWS_PROFILE` is selected.
  A new non-`windows-native/` run requires owner approval under the
  `coga/testing/clean-install/windows-aws` skill. No AWS resources were created.
- PR preparation recommends **deep**, explicitly carrying the failed checks,
  historical full-suite receipt, and missing Windows evidence. This completed
  code review is not merge approval; the existing owner review gate retains
  those verification decisions. No unrelated repairs were added to this branch.

## PR

```yaml
title: Honor CODEX_HOME when locating Codex rollouts
author: claude
author_evidence: Implement handoff records Claude Code (claude-opus-5-5); the implementation commit also credits Claude Opus 5.5. The fresh Codex peer session made no implementation edits.
head: d94674f7f0b7dbbcaff09600b69dde6e351a179a
base: 0a150faf1a0925530533812de8927b6dabb8d042
depth: deep
rationale: Independent direct review of the final diff found no must-fix code issues. The focused run still has two independently reproduced main failures, the full-suite receipt precedes the final prose-only rebase, and native Windows evidence is missing. These verification gaps warrant owner review before merge.
implementation: Adds usage._codex_sessions_root to select $CODEX_HOME/sessions when CODEX_HOME is non-empty, preserving the literal value, or ~/.codex/sessions otherwise. Both the pre-spawn snapshot and post-run parser use the same existing rollout glob. Tests isolate CODEX_HOME and cover snapshotting and parsing a custom root outside HOME while ignoring the default-root decoy. The two required topics document the lookup and unsupported cases.
deviations: No implementation deviations. Peer review rebased onto current main without code changes; unrelated packaging repairs remain in PR 1185.
limitations: Relative CODEX_HOME and values set only in the agent child environment are unsupported. The root is not canonicalized, but a symlink probe confirms equivalent discovery for an existing absolute root. No native Windows or Python 3.11 verification receipt; local checks use Linux and Python 3.12.12. Full-suite results are historical after the final documentation-only rebase; focused checks were rerun on final head. No interactive surface changed, so terminal rendering checks are inapplicable.
files:
  src/coga/usage.py: Select the Codex rollout root from the process environment for both snapshot and parse discovery.
  tests/test_usage.py: Clear ambient CODEX_HOME and cover a custom root outside HOME, including an ignored default-root decoy.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md: Document the lookup rule, unknown result for a missing rollout, and unsupported configurations in the package owner.
  docs/contexts/coga/usage/SKILL.md: Keep the transitional live copy byte-identical to its package owner.
  docs/contexts/coga-dev/internals/activity-capture/SKILL.md: Document the shared root and the parent-versus-child environment boundary in the local capture contract.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: d94674f7f0b7dbbcaff09600b69dde6e351a179a
  base: 0a150faf1a0925530533812de8927b6dabb8d042
  detail: Direct review completed, including rereview of all five diff paths after the final rebase. Covered caller flow, environment inheritance, regression-test isolation, package/live equality, and Codex source semantics. No must-fix code findings. Failing checks and missing Windows evidence remain explicit verification gaps; this receipt does not approve merging.
checks:
  - command: PYTHONPATH=/home/n/Code/claude/coga/src TERM=dumb .venv/bin/python -m pytest tests/test_usage.py tests/test_packaging.py
    status: failed
    head: d94674f7f0b7dbbcaff09600b69dde6e351a179a
    base: 0a150faf1a0925530533812de8927b6dabb8d042
    detail: Pop!_OS 24.04 LTS, Python 3.12.12; 75 passed, 2 failed in 4.39s. All 40 usage tests pass. The existing test_live_and_packaged_copies_stay_identical and test_context_navigation_has_no_broken_links failures reproduced independently on main before the last documentation-only advance. PR 1185 remains open and unmerged.
  - command: PYTHONPATH=/home/n/Code/claude/coga/src TERM=dumb .venv/bin/python -m pytest
    status: failed
    head: 6b715e056770ab68f03076fa3400874d71b638c2
    base: 39610a034be9205b60476ef2684ac146efc10d0e
    detail: Pop!_OS 24.04 LTS, Python 3.12.12; 4504 passed, 10 skipped, 2 failed in 638.56s. Only the two independently reproduced main packaging failures. Historical receipt before the final rebase, whose upstream delta changed phone-home build prose and a packaging-exception explanation only; runtime code and test assertions were unchanged. Focused usage/packaging checks were rerun on final head; the full suite was not repeated for that prose-only drift.
  - command: git diff --check
    status: passed
    head: d94674f7f0b7dbbcaff09600b69dde6e351a179a
    base: 0a150faf1a0925530533812de8927b6dabb8d042
    detail: No whitespace errors; the changed usage package/live topic pair also compares byte-identical.
  - command: Native Windows full suite (python -m pytest)
    status: not-run
    detail: Required before approving this path-sensitive change by coga-dev/testing. No implement receipt is recorded; all local Windows harness runs have teardown markers and AWS_PROFILE is unset. The Windows harness skill requires owner approval for a new run outside windows-native tickets. Remains a pre-merge verification gap.
```
