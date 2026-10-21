---
title: Let the autofix generator attach repo-default contexts
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
    skills: []
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

Every ticket the `coga recurring` autofix loop files starts without contexts,
so repos must repeatedly attach their triage guidance by hand. Add optional
shared configuration `[autofix] contexts = ["<ref>", ...]`, validate its shape
and resolve each ref when config loads, and pass the configured list into
every newly generated `autofix/*` ticket; an absent key or an explicit empty
list keeps today's behavior. Early validation deliberately makes a missing
configured context fail every config-loading command, surfacing the mistake
before an unattended sweep. Done means tests demonstrate that valid defaults
survive ticket creation and compose their context bodies, invalid values and
unresolvable refs fail with actionable config errors, existing agent selection
and unset defaults still work, and the owning documentation and packaged
twins describe the setting.

## Context

Reported from a downstream repo, `FastJVM/admin`, where the evidence lives.

- That repo keeps a local context, `coga/upstream`, whose purpose is routing a
  failure diagnosed there to a fix in this repo; its own description says to
  attach it to every `autofix/*` ticket, because "is this upstream?" is the
  first question each one asks.
- It has been attached by hand twice (2026-09-01, and again 2026-09-16 for the
  four then-live autofix tickets). In between, every generated ticket —
  `build-the-missing-1099-nec-sweep-script-so-its-fir`,
  `put-dream-scan-directories-somewhere-they-survive`,
  `launch-due-recurring-tasks-the-sweep-drops-after-c`,
  `resync-four-coga-files-that-fell-behind-the-2026-0` — was born contextless,
  and 10 of that repo's 12 autofix tickets at the time carried no context. A
  session launched on one never composes the triage guidance it most needs.
- A hand re-attach after each sweep is a standing chore the generator could do
  once from config.
- Rechecked against current `origin/main` on 2026-10-21:
  `recurring_autofix.create_autofix_ticket` still passes `contexts=[]`, and
  `config._ALLOWED_AUTOFIX_KEYS` is still `{"agent"}`.

### Implementation boundaries

- In `src/coga/config.py`, widen `_ALLOWED_AUTOFIX_KEYS`, extend
  `_parse_autofix` and `load_config`, and carry `autofix_contexts` on `Config`
  beside `autofix_agent`. Accept a list of non-empty strings, rejecting
  whitespace-only strings and non-string elements. Retain declaration order.
  Both the absent table/key and `contexts = []` mean no defaults; a table
  containing only `contexts` must work without `agent`. Keep `[autofix]`
  shared-only and preserve the existing agent validation and fallback.
- Resolve refs using the contract of `paths.resolve_context_path` in
  `src/coga/paths.py`: the effective `Config.contexts_root` first, then the
  bundled fallback only when the local artifact is absent. This includes
  `[layout].contexts` relocation and the existing invalid-artifact checks in
  `config.require_context_artifact`; do not invent a second lookup policy.
  Config errors must identify `[autofix].contexts` and the offending value or
  unresolved ref. `paths` imports `config`, so account for that dependency
  when arranging validation rather than introducing a module import cycle.
- In `src/coga/recurring_autofix.py`, pass the configured defaults from
  `create_autofix_ticket` to `create_task` instead of the hardcoded empty list.
  This affects newly generated tickets only. Do not backfill existing
  tickets, change the analyst protocol, or introduce general ticket defaults.
  Shortening the shared `code/open-pr` and `code/address-pr-comments` skills
  is separate maintenance, outside this ticket.
- Cover parsing and resolution in `tests/test_config.py`, including unset
  and explicit-empty defaults, a contexts-only table, invalid types/blank
  entries, missing refs, default and relocated local roots, bundled fallback,
  and rejection in local config. Include an invalid local override of a ref
  that also exists in the bundle: config loading must reject it, name
  `[autofix].contexts` and the ref, and never silently accept the bundled
  copy. Cover generated ticket frontmatter and actual prompt composition in
  `tests/test_recurring_autofix.py`, retaining the existing workflow, run-log,
  and agent-selection behavior.

The alternative of having the analyst choose contexts was considered and is
not preferred. The analyst is text-in/text-out and Coga does every mutation;
which contexts a repo's triage needs is repo policy, not a per-finding
judgment. Keep that boundary in the autofix topic's operator guidance.

### Required reads and documentation

These topics are cited rather than attached. Read the named sections before
implementing or reviewing the affected behavior; the copied facts here are
task-specific guidance, and each topic remains the owner of its contract.

- `coga/recurring/autofix` at
  `docs/contexts/coga/recurring/autofix/SKILL.md` is cited rather than attached
  because it is an editing target: read **The loop** and **Operating it**.
  `recurring_autofix.create_autofix_ticket` owns generation; Coga supplies
  ticket metadata while the analyst supplies the finding. Update the
  operator knobs here and in
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md`.
- `coga/configuration` at `docs/contexts/coga/configuration/SKILL.md` is cited
  rather than attached because it is an editing target: read **Allowlists**
  and **Unknown keys fail loud**. `config.load_config` enforces shared-only
  policy and rejects unknown keys. Update the `[autofix]` allowlist row here
  and in
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md`.
- `coga/context-layout` at `docs/contexts/coga/context-layout/SKILL.md` is
  cited rather than attached: read **Local first, then bundled** and
  **Relocating: `[layout] contexts`** for `paths.resolve_context_path` and
  `Config.contexts_root`. Invalid local artifacts must fail rather than
  silently selecting a bundled context; unignored local files need not
  already be committed.
- `coga-dev/testing` at `docs/contexts/coga-dev/testing/SKILL.md` is cited rather
  than attached: read **Commands**, **Which code you are actually testing**,
  **Test-writing rules**, and **CI posture and receipts**. Use an absolute
  checkout `PYTHONPATH` and an available Python 3.11+ interpreter so subprocess
  tests exercise the branch. `config` and `launch` share the same
  `subprocess` module, so mocks must dispatch by argv rather than intercept
  unrelated Git calls. Record exact commands and result counts, run
  `coga validate --json` after this config change, and report a missing real
  Python 3.11 run as a verification gap. `tests/test_packaging.py` enforces
  byte-identical canonical and packaged topic twins.

<!-- coga:blackboard -->
## Dev

pr: https://github.com/FastJVM/coga/pull/1079
branch: coga/let-the-autofix-generator-attach-repo-default-co-140a79

## Implement handoff

- Implemented the approved plan: shared context defaults are validated at
  config load with the existing resolver and attached only to new autofix
  tickets. `Config.autofix_contexts` is an ordered tuple; the resolver import
  is deferred until config construction to avoid the `paths`/`config` cycle.
  The analyst protocol and existing agent selection are unchanged.
- Updated both owning topics and their packaged twins. The related autofix
  fixture covers local guidance, a local override, and bundled fallback.
- Actual implementing agent: Codex (launch override), despite the ticket's
  configured `agent: claude`. The attending human approved the plan before
  code edits. No independent code review has run; peer-review is next.
- Reconciled main's context-audience reorganization, read its updated governing
  instructions, and retained control's updated testing citation in this ticket.
  The test fixture now uses the still-shipped `coga/context-layout` ref.
- Pushed `ed1ff078763a795cb33a5b02e258d492edeb46dc` to the branch above. It
  contains current `origin/main` at `04f4597dc682f1d10efbed4ab2bb5a78e1be453f`;
  the final fetch after testing found no further drift. No PR opened.
- No unresolved implementation items or adjacent bugs found. Review the diff
  and refresh the preparation after any fixes; the advisory depth is `deep`
  because code review has not run yet.

## Verification history

- Baseline Python 3.11 config/autofix run: 273 passed. Adding the regressions
  before the implementation produced 28 failures and 273 passes on the
  uncommitted test tree based on `7a1d5642226f4b1079aab0659b73f77e54b62eb5`.
  Failures exposed the missing config field/allowlist and ticket defaults.
- Before main's context reorganization, commit
  `008c139de15459a6bdf2ee056081d158de731148` (base
  `7a1d5642226f4b1079aab0659b73f77e54b62eb5`) passed 301 Python 3.11
  config/autofix tests, 22 Python 3.11 packaging tests, and the Python 3.12
  full suite (3976 passed, 7 skipped). These are historical results, not
  receipts for the rebased head. Fresh results are recorded below.
- The final Python 3.11 test tree was verified identical to the committed tree
  `b978d81a850a231a388d4feda30f45de3cd201e6`; the full Python 3.12 rerun
  executed after the final commit. The projected ticket was never committed.

## Peer review

- Codex directly reviewed the eight-path diff after rebasing onto
  `3144c9f65aecf8977c72aa2f9d3507fb440e8a62`. The first review covered head
  `7be8d46945ab50318f4927ec029c41913e783b64` and found one contract gap:
  a relocated root's whole-tree artifact check could reject an invalid autofix
  default before the error gained its required `[autofix].contexts` prefix.
  The attending human approved fixing the diagnostic precedence.
- Added regressions for symlink, directory, and ignored overrides under both
  roots, plus valid defaults with an unrelated invalid local context. Before
  the fix, the focused Python 3.11 run failed all three relocated cases
  (3 failed, 5 passed, 221 deselected). Per-ref validation now runs before the
  full tree scan; the same resolver and all rejection rules remain in use.
  The autofix owner and packaged twin document the diagnostic contract.
  Red-run command (head `7be8d46945ab50318f4927ec029c41913e783b64` plus the
  uncommitted test expansion):

  ```sh
  PYTHONPATH=/home/n/Code/codex/coga/src /tmp/coga-autofix-py311/bin/python -m pytest tests/test_config.py -k 'autofix_contexts_reject_invalid_local_override or layout_contexts_ignored_context_rejected' -q
  ```

- Direct review **completed** on the final committed head
  `ba8527cfe63809d4eacdafe30505fcc7706970a0`, against base
  `3144c9f65aecf8977c72aa2f9d3507fb440e8a62`. Re-read the full eight-path diff,
  checked config/paths/create/compose interactions and the owning contracts,
  and verified both topic twins. The diagnostic finding is fixed; no
  unresolved findings or deviations remain.
- The pre-fix full-suite run was deliberately interrupted before source edits;
  it is not a passing receipt. The final committed head passed 335 Python 3.11
  config/autofix/packaging tests in 4.69s, seeded-repo validation (4 OK), and
  this task's validation (1 OK). The full Python 3.12 suite passed with
  3988 passed and 7 native-Windows skips in 362.88s. Exact final-head commands
  and receipts are under `## PR`; the red regression run and interrupted suite
  above are historical only.
- This is self-review: both implementation and this fresh review session ran
  in Codex. No independent reviewer or nested review CLI was used.
- No raw-terminal, pager, TTY prompt, or rendered Slack surface changed;
  interactive rendering verification is inapplicable. Tests exercise actual
  ticket frontmatter and composed context bodies through the shared APIs.
- Final freshness fetch found origin/main unchanged at the reviewed base.
  Pushed `ba8527cfe63809d4eacdafe30505fcc7706970a0` with an explicit lease on
  the previous remote head. The branch has two commits ahead of main.
  The projected ticket remains unstaged; launch owns publication and checkout
  return after the peer-review bump. No PR has been opened in this step.

## PR

```yaml
title: Attach repo-default contexts to generated autofix tickets
author: codex
author_evidence: The implement handoff records Codex via an explicit launch override of the ticket-configured
  Claude. This fresh peer-review session also ran in Codex (COGA_EXPECTED_AGENT=codex) and authored the
  diagnostic fix.
head: ba8527cfe63809d4eacdafe30505fcc7706970a0
base: 3144c9f65aecf8977c72aa2f9d3507fb440e8a62
depth: skim
rationale: 'Bounded config and generator change with completed Codex self-review, a passing full Python
  3.12 suite, and real Python 3.11 config/autofix/packaging coverage. Read the deliberate tradeoff: invalid
  defaults stop every config-loading command, and configured autofix refs now take diagnostic precedence
  over the rest of a relocated context tree. No independent review was performed.'
implementation: Adds optional shared [autofix].contexts, validates ordered refs through the existing local-first/bundled
  resolver at config load, and attaches them to newly generated autofix tickets. The review fix makes
  invalid relocated overrides identify the setting and ref before the full-tree scan, which still rejects
  unrelated invalid artifacts. Existing analyst protocol, agent selection, workflow, and run log are preserved.
deviations: None. The human approved the review fix for the requested relocated-root diagnostic contract.
  Reconciliation retained main's context-audience reorganization and the still-shipped coga/context-layout
  fixture ref.
limitations: Existing tickets are not backfilled. Missing or invalid configured refs deliberately stop
  config-loading commands. Review is self-review. The full suite ran on Python 3.12; real Python 3.11
  covered config, autofix, packaging, and resource loading. Seven native Windows checks were skipped on
  Linux.
files:
  src/coga/config.py: Parse ordered shared autofix defaults and validate them through the existing resolver;
    check configured refs before the full relocated-tree scan so invalid overrides retain setting/ref
    attribution.
  src/coga/recurring_autofix.py: Pass configured context defaults to every newly generated autofix ticket.
  tests/test_config.py: Cover defaults, shape, order, local/bundled resolution, relocated roots, shared-only
    policy, invalid overrides under both roots, and continued rejection of unrelated invalid artifacts.
  tests/test_recurring_autofix.py: Extend the related repo fixture and prove frontmatter, composed local/bundled
    bodies, agent/workflow/run-log preservation, and no backfill; dispatch the fake analyst by argv.
  docs/contexts/coga/configuration/SKILL.md: Add contexts to the shared autofix allowlist and link its
    owning operator guidance.
  docs/contexts/coga/recurring/autofix/SKILL.md: Own the operator setting, eager validation and diagnostics,
    lookup semantics, and repo-policy boundary with the text-only analyst.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: Keep the packaged
    configuration topic byte-identical to its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md: Keep the packaged
    autofix topic byte-identical to its canonical owner.
review:
  reviewer: codex
  kind: self
  status: passed
  head: ba8527cfe63809d4eacdafe30505fcc7706970a0
  base: 3144c9f65aecf8977c72aa2f9d3507fb440e8a62
  detail: 'Direct review completed after the rebase and diagnostic-fix commit. Read the complete final
    eight-path diff and affected config/paths/create/compose contracts. Fixed one finding: relocated invalid
    autofix overrides lost the required setting/ref attribution. No unresolved findings remain. Both implementer
    and reviewer were Codex; fresh session and peer selection do not establish independence. No nested
    review tool was invoked.'
checks:
- command: PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m pytest -ra
  status: passed
  head: ba8527cfe63809d4eacdafe30505fcc7706970a0
  base: 3144c9f65aecf8977c72aa2f9d3507fb440e8a62
  detail: 'Python 3.12.12: 3988 passed, 7 skipped in 362.88s. Skips: 2 Windows job-object integration
    tests and 5 native Windows PowerShell 5.1 tests. Ran on the final committed head.'
- command: PYTHONPATH=/home/n/Code/codex/coga/src /tmp/coga-autofix-py311/bin/python -m pytest tests/test_config.py
    tests/test_recurring_autofix.py tests/test_packaging.py -q
  status: passed
  head: ba8527cfe63809d4eacdafe30505fcc7706970a0
  base: 3144c9f65aecf8977c72aa2f9d3507fb440e8a62
  detail: 'Python 3.11.15: 335 passed in 4.69s. Ran on the final committed head, including the relocated-override
    regressions and preserved whole-tree validation.'
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python
    -m coga.cli validate --json
  status: passed
  head: ba8527cfe63809d4eacdafe30505fcc7706970a0
  base: 3144c9f65aecf8977c72aa2f9d3507fb440e8a62
  detail: 'Working directory: /home/n/Code/codex/coga/tests/fixtures/seeded-repo/coga. 4 checks OK, 0
    issues, 0 fixes.'
- command: PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m coga.cli
    validate --task let-the-autofix-generator-attach-repo-default-contexts --json
  status: passed
  head: ba8527cfe63809d4eacdafe30505fcc7706970a0
  base: 3144c9f65aecf8977c72aa2f9d3507fb440e8a62
  detail: 1 task OK, 0 issues, 0 fixes.
- command: git diff --check origin/main...HEAD
  status: passed
  head: ba8527cfe63809d4eacdafe30505fcc7706970a0
  base: 3144c9f65aecf8977c72aa2f9d3507fb440e8a62
  detail: Passed with no whitespace errors in the final committed diff.
- command: PYTHONPATH=/home/n/Code/codex/coga/src /tmp/coga-autofix-py311/bin/python -m pytest
  status: not-run
  detail: The full suite ran on Python 3.12. Real Python 3.11 verified affected config/autofix behavior
    plus packaging and resource loading; a second full-suite interpreter matrix was not required.
```

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `let-the-autofix-generator-attach-repo-default-contexts`
Recorded: 2026-10-21T19:01:06+00:00

    Branch 'coga/let-the-autofix-generator-attach-repo-default-co-140a79' is not safe to publish. refs/heads/coga/let-the-autofix-generator-attach-repo-default-co-140a79 does not contain latest origin/main. Rebase or merge before opening a PR, e.g. `git fetch origin main` then `git rebase origin/main`. Overlapping paths: src/coga/config.py. Reconcile it and relaunch, or `coga block --task let-the-autofix-generator-attach-repo-default-contexts`.
