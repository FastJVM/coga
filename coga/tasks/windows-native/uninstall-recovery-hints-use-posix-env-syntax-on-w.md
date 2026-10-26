---
title: Uninstall recovery hints use POSIX env syntax on Windows
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (evaluate-design)
agent: claude
launch_generation: pending:b60dcc56-ab7c-4634-90b5-270747ad6f11
---

## Description

Found during `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window`.
In `src/coga/commands/uninstall.py`, `_handle_package()` pins uv to the tools
directory containing the running Coga installation, but `_uninstall_via_tool()`
renders that override as POSIX `VAR=value` syntax on every platform. When uv is
missing or fails, a native Windows user cannot paste the recovery command into
PowerShell. The actual child process already receives the correct environment;
this change fixes the displayed command without changing package removal.

Use PowerShell syntax on native Windows and identify PowerShell in the recovery
instruction. For example, an override containing an apostrophe and a space
renders as:

```powershell
$env:UV_TOOL_DIR='C:\Users\O''Brien\uv tools'; uv tool uninstall coga
```

### Acceptance criteria

- [ ] On native Windows with environment overrides, both the missing-installer
  and nonzero-exit recovery paths in `src/coga/commands/uninstall.py`,
  `_uninstall_via_tool()`, print a
  pasteable PowerShell command with the same environment overrides and tool
  arguments as the attempted uninstall. Each assignment uses `$env:NAME=...;`
  before the command, and the recovery instruction explicitly names PowerShell.
  The progress message uses the same command rendering.
- [ ] Environment values are PowerShell literal strings: spaces, backslashes,
  apostrophes, Unicode, dollar signs, backticks, ampersands, and semicolons reach
  the tool unchanged. Escape embedded single-quote delimiters according to
  PowerShell's quoting rules; do not reuse POSIX `shlex.quote()` on Windows.
  Preserve override order. An absent or empty override mapping adds no
  assignments, so the existing `pipx uninstall coga` command stays unchanged.
- [ ] POSIX output remains byte-identical for the progress message and both
  recovery paths, including `shlex.quote()` behavior, whitespace, and commands
  without overrides. Pin representative plain, space-containing, and
  apostrophe-containing values with exact expected-output assertions.
- [ ] Actual execution remains unchanged: installer discovery, argv, inherited
  environment plus supplied overrides, `env=None` without overrides, output
  capture, result handling, and the refusal to fall back to pip for uv/pipx.
  Formatting does not mutate Coga's process environment or the caller's mapping.
- [ ] Regression coverage in `tests/test_uninstall.py` exercises both recovery
  paths and the progress rendering, including Windows selection and unchanged
  child-process arguments/environment. The tests run on native Windows. Include
  a native PowerShell test that executes the emitted hint with a harmless `uv`
  stub and verifies the literal `UV_TOOL_DIR` value and `tool uninstall coga`
  arguments; it must never invoke a real package uninstaller. Portable rendering
  cases also exercise both platform branches on POSIX.
- [ ] Update the global-package recovery contract in
  `docs/contexts/coga/uninstall/SKILL.md` and its packaged twin at
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/uninstall/SKILL.md`
  in the implementation PR, keeping the two files byte-identical. Document the
  platform-specific hint and that a pasted PowerShell assignment changes the
  current shell session's environment.

### Proposed shape

1. Keep the display change local to `src/coga/commands/uninstall.py`,
   `_uninstall_via_tool()`. A small private formatter (for example,
   `_format_tool_command(tool, subcommand, env, *, windows)`) can make both
   branches directly testable. Select Windows from the native platform at the
   call site. Preserve the current POSIX join/quoting operation; on Windows,
   join literal environment assignments with `; ` and append the existing
   fixed tool/subcommand/package tokens. Keep the command separate from any
   PowerShell label so it remains directly pasteable.
2. Use that one display value at all three existing output sites. Add the
   PowerShell guidance to Windows recovery prose when assignments are present;
   leave POSIX prose intact. Update `_uninstall_via_tool()`'s docstring, which
   currently describes only `VAR=value` prefixes. Leave the `subprocess.run()`
   call and `_handle_package()`'s installer dispatch unchanged.
3. Extend the two existing uv recovery tests to expect their native shell's
   syntax, and preserve the existing uv environment-routing test. Add table
   cases for formatting with no overrides and with quoted values, without
   globally monkeypatching `os.name` (which also affects `pathlib` and pytest).
   For the Windows-only execution test, capture the missing-tool hint, define
   a local PowerShell `uv` function that reports its environment and arguments,
   and run the captured command in a child `powershell.exe -NoProfile` process.
   Use encoded script transport as in the existing Windows shell tests. Include
   a value with a literal apostrophe and shell metacharacters, plus Unicode
   including a smart apostrophe; this checks quoting rather than reproducing
   the formatter in the expected result. Skip this execution test only on
   non-Windows hosts, with the other regression cases running on both platforms.
4. Update the owning uninstall topic and twin together. Verify with
   `python -m pytest tests/test_uninstall.py`,
   `python -m pytest tests/test_packaging.py::test_live_and_packaged_copies_stay_identical`,
   and the workflow-required full suite. Record the native Windows result using
   the existing Python 3.11 CI job or an available native checkout; a Linux run
   with simulated platform selection is not evidence that PowerShell ran.

### Out of scope

- cmd.exe syntax, detecting the caller's preferred shell, or a new CLI option.
- Changing installer ownership detection, subprocess execution, uninstall exit
  behavior, repository removal, or the generic non-purge package suggestions.
- Reformatting the separate pip fallback in `src/coga/commands/uninstall.py`,
  `_handle_package()`, or creating a shared shell-command framework for arbitrary
  executables, arguments, or environment variable names. Current callers use
  fixed uv/pipx command tokens and the `UV_TOOL_DIR` override.
- Provisioning Windows infrastructure or changing the CI matrix.

## Context

`coga/uninstall` (`docs/contexts/coga/uninstall/SKILL.md`) is cited rather than
attached: read **The global package** before implementation; it owns the
recovery behavior this PR changes. `coga-dev/testing`
(`docs/contexts/coga-dev/testing/SKILL.md`) is cited rather than attached: read
**Test-writing rules** and **CI posture and receipts** for native Windows
fixtures, exclusions, and verification evidence. `coga-dev/packaging`
(`docs/contexts/coga-dev/packaging/SKILL.md`) is cited rather than attached: read
**Canonical copies and twins** when updating the uninstall topic.

- `src/coga/commands/uninstall.py`, `_handle_package()`, passes
  `env={"UV_TOOL_DIR": str(venv.parent)}` to `_uninstall_via_tool()` for uv,
  and calls that helper without overrides for pipx. The helper constructs
  `display` once for the missing-tool hint, progress message, and failure hint.
  Its separate `subprocess.run()` call uses the resolved executable and merges
  the overrides into a copy of `os.environ`; shell syntax is not involved.
- `tests/test_uninstall.py`,
  `test_uninstall_purge_uv_failure_prints_command_with_tool_dir()` and
  `test_uninstall_purge_uv_install_without_uv_prints_uv_hint()`, currently assert
  POSIX `UV_TOOL_DIR=...` output on every host. They must change with the display.
  `test_uninstall_purge_runs_uv_tool_for_uv_install()` verifies that the owning
  venv's tools directory overrides a different inherited `UV_TOOL_DIR` and that
  uv does not fall back to pip; retain this execution contract.
- `tests/test_windows_clean_install.py`,
  `test_windows_walk_records_first_failure()`, already runs native PowerShell
  with UTF-16LE/base64 `-EncodedCommand` transport and skips on non-Windows
  hosts. Follow that transport pattern without using its install/walk code.
- `.github/workflows/test.yml`, job `pytest`, runs the full suite on
  `ubuntu-latest` and `windows-latest` with Python 3.11, so the native hint test
  needs no new job. `tests/test_packaging.py`,
  `test_live_and_packaged_copies_stay_identical()`, derives and compares the
  uninstall context's canonical/packaged pair.
- Microsoft documents [PowerShell literal-string quoting and embedded quote
  escaping](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_quoting_rules?view=powershell-5.1)
  and [environment variable assignment and session scope](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_environment_variables?view=powershell-5.1).
  Single-quoted values prevent expansion, embedded quote delimiters need
  escaping, and `$env:` assignments are inherited by child processes. Read the
  smart-quote note as well when implementing literal quoting.

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

## Design handoff

- Investigated on 2026-10-26 at `3f73f5ed285b8c78ad923b1e65d86a0ae8f20efe`.
  Started from clean `main`, fetched and fast-forwarded current control. This
  ticket has no recorded branch or PR; no branch, code, or PR was created.
- The defect is the shared display string, not subprocess environment routing.
  PowerShell is the chosen Windows recovery shell, as permitted by the seed
  ticket; naming it avoids implying that the snippet is cmd.exe syntax.
- Both current uv fallback assertions encode the bug. The spec includes their
  update, preserved POSIX output, a harmless native PowerShell regression, and
  the owning uninstall topic/twin update in the later implementation PR.
- Reconciled with `origin/main` at
  `b7941bda363e6b6ade126d495a04425dc08bd59b`; intervening commits changed
  unrelated instructions. Preserved and verified the ticket before refreshing
  the checkout, then reapplied the spec unchanged. Recovery copy:
  `/tmp/coga-uninstall-design-i3e5vlg9/ticket.md`.
- Verification:
  `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task windows-native/uninstall-recovery-hints-use-posix-env-syntax-on-w --json`
  returned exit 0, one task checked, no fixes or issues. A read-only call to
  `src/coga/compose.py`, `compose_prompt()`, confirmed all three spec subsections,
  six acceptance items, code context, and open questions reach the prompt.
  Frontmatter remains byte-identical to HEAD and there is exactly one blackboard
  fence. `git diff --check` passed. No implementation tests or native Windows
  execution were run during this design step.
- Next handoff is the frozen `evaluate-design` step; no open design decision
  requires blocking this queue entry.

## Open Questions

None identified during design.
