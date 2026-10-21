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
step: 2 (peer-review)
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

## PR

```yaml
title: Attach repo-default contexts to generated autofix tickets
author: codex
author_evidence: This attended implementation session ran in Codex; the launch environment records COGA_EXPECTED_AGENT=codex,
  overriding the ticket-configured claude identity. No model override was exposed in the session evidence.
head: ed1ff078763a795cb33a5b02e258d492edeb46dc
base: 04f4597dc682f1d10efbed4ab2bb5a78e1be453f
depth: deep
rationale: Bounded config/generator change with passing checks, but code review is pending the next peer-review
  step. Review the deliberate effect of invalid defaults on every config-loading command.
implementation: Adds optional shared [autofix].contexts, stores refs in declaration order, validates shape
  and local-first/bundled resolution during config load, and attaches the defaults to newly generated
  autofix tickets. Existing agent selection, workflow, run log, and analyst protocol are preserved.
deviations: None. Reconciliation with main required using the still-shipped coga/context-layout topic
  in the test fixture after coga/principles moved to the local-only development library.
limitations: Existing tickets are not backfilled. Configured missing or invalid contexts stop config-loading
  commands by design. Full-suite coverage is on Python 3.12; Python 3.11 coverage includes config, autofix,
  and packaging. Seven native Windows checks were skipped on Linux.
files:
  src/coga/config.py: Parse ordered shared autofix context defaults and validate them through the existing
    resolver at config load.
  src/coga/recurring_autofix.py: Pass configured context defaults to every newly generated autofix ticket.
  tests/test_config.py: Cover default/empty/contexts-only settings, order, relocated roots, bundled fallback,
    malformed values, missing refs, invalid local overrides, and shared-only policy.
  tests/test_recurring_autofix.py: Extend the related repo fixture and prove frontmatter, composed local/bundled
    bodies, agent/workflow/run-log preservation, and no backfill; dispatch the fake analyst by argv.
  docs/contexts/coga/configuration/SKILL.md: Add contexts to the shared autofix allowlist and link its
    owning operator guidance.
  docs/contexts/coga/recurring/autofix/SKILL.md: Document defaults, eager validation, lookup semantics,
    and the boundary between repo policy and the text-only analyst.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: Keep the packaged
    configuration topic byte-identical to its canonical owner.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md: Keep the packaged
    autofix topic byte-identical to its canonical owner.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: The implement step stops before code review; the next frozen workflow step is peer-review. Human
    approach confirmation was not code review.
checks:
- command: PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m pytest -ra
  status: passed
  head: ed1ff078763a795cb33a5b02e258d492edeb46dc
  base: 04f4597dc682f1d10efbed4ab2bb5a78e1be453f
  detail: 'Python 3.12.12: 3984 passed, 7 skipped in 373.59s. Skips: 2 Windows job-object integration
    tests and 5 native Windows PowerShell 5.1 tests. Run directly on this committed head.'
- command: PYTHONPATH=/home/n/Code/codex/coga/src /tmp/coga-autofix-py311/bin/python -m pytest tests/test_config.py
    tests/test_recurring_autofix.py tests/test_packaging.py -q
  status: passed
  head: ed1ff078763a795cb33a5b02e258d492edeb46dc
  base: 04f4597dc682f1d10efbed4ab2bb5a78e1be453f
  detail: 'Python 3.11.15: 331 passed in 4.82s. Ran before the final amend; staged tree b978d81a850a231a388d4feda30f45de3cd201e6
    matched the committed tree, and only this projected ticket remained dirty.'
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python
    -m coga.cli validate --json
  status: passed
  head: ed1ff078763a795cb33a5b02e258d492edeb46dc
  base: 04f4597dc682f1d10efbed4ab2bb5a78e1be453f
  detail: 'Working directory: /home/n/Code/codex/coga/tests/fixtures/seeded-repo/coga. 4 checks OK, 0
    issues, 0 fixes.'
- command: PYTHONPATH=/home/n/Code/codex/coga/src /home/n/Code/codex/coga/.venv/bin/python -m coga.cli
    validate --task let-the-autofix-generator-attach-repo-default-contexts --json
  status: passed
  head: ed1ff078763a795cb33a5b02e258d492edeb46dc
  base: 04f4597dc682f1d10efbed4ab2bb5a78e1be453f
  detail: 1 task OK, 0 issues, 0 fixes.
- command: git diff --check
  status: passed
  head: ed1ff078763a795cb33a5b02e258d492edeb46dc
  base: 04f4597dc682f1d10efbed4ab2bb5a78e1be453f
  detail: Passed with no whitespace errors.
- command: PYTHONPATH=/home/n/Code/codex/coga/src /tmp/coga-autofix-py311/bin/python -m pytest
  status: not-run
  detail: The full suite ran on Python 3.12. Real Python 3.11 verified all affected config/autofix tests
    plus packaging and resource loading; a second full-suite interpreter matrix was not required.
```
