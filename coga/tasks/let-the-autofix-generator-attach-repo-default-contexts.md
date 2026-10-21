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
step: 1 (implement)
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
- `coga/testing` at `docs/contexts/coga/testing/SKILL.md` is cited rather
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
