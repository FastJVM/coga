---
title: overload base text; prompt, etc.
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
launch_generation: pending:b49e36aa-56e6-445f-b56d-8a79d3c8f405
---

## Description

Make Coga's fixed text layers hackable per repo. Right now every top-level
packaged resource under `src/coga/resources/` is read straight from the
installed wheel, and a repo cannot change any of them without forking the
package. Those resources are `prompt.md` (the base prompt),
`prompt-attended.md`, `prompt-megalaunch.md` and `prompt-queue.md` (session
conduct), `prompt-blocker-resolution.md`, `blackboard.md` (the stock
blackboard placeholder) and `retire.md`. This is a minor feature in the
"make everything hackable" direction. It follows the work that moved
Coga-development rules out of the shipped base prompt, which makes that
prompt a natural thing for repos to customize.

Semantics (decided with the owner): **replace only, all top-level
resources.** If a file named `<repo coga root>/resources/<name>` exists (the
directory `cfg.repo_root` points at, i.e. `coga/resources/<name>` in a
default layout), it wholly replaces the packaged resource of the same name.
Otherwise the packaged copy is used, exactly as today. There is no
append/patch mode, which is a deliberate tradeoff: a repo that overrides a
file stops receiving upstream edits to it until someone merges them by hand.

Done means:
- a repo-local `coga/resources/prompt.md` (and likewise each other resource)
  changes what `coga launch` composes and what the blackboard and retire paths
  render;
- `coga launch <slug> --prompt-report` shows when a fixed layer came from a
  repo override, by setting the existing `PromptLayer.path` to the override
  file (unset means packaged; no new field);
- `coga validate` emits a **warning, not an error**, for a file in the repo
  `resources/` directory that matches no known resource name, so a typo can't
  silently do nothing (`README.md` and dotfiles are ignored);
- tests cover override and fallback for at least the base prompt, one conduct
  variant and `blackboard.md`;
- the `coga/prompt-composition` topic (and any other owning topic the change
  touches, plus its packaged twin) documents the override rule in the same PR.

## Context

- **Loader today:** `paths.read_packaged_resource(name)` reads
  `files("coga.resources").joinpath(name)` and takes no config. This makes it
  the natural single choke point, but resolving a repo override needs the repo
  root, so callers will have to pass `cfg` or the root. It has these callers:
  `compose._resource` (base prompt, session conduct via
  `SESSION_CONDUCT_RESOURCES`, blocker-resolution preamble),
  `blackboard.render_blackboard` and `blackboard._is_stock_blackboard`, and
  `commands/retire.py` (`retire.md`). Prefer one resolver in `paths` (shared
  infra with several consumers, so it belongs in core) over per-caller
  lookups.
- **Callers that must newly receive `cfg`** (the real threading work): the
  cfg-free wrappers `blackboard.render_blackboard` (called from
  `commands/create.py` and `validate.py`) and `blackboard._is_stock_blackboard`
  (reached via `prelaunch_blackboard_synthesis_reason[_text]` from
  `validate.py` and `commands/mark.py`). Overrides apply to bootstrap
  (`BootstrapRef`) launches too.
- **Gotcha: stock-blackboard detection.** `_is_stock_blackboard` compares a
  ticket's blackboard to the stock template to decide that it is untouched.
  With an overridden `blackboard.md`, tickets created before the override
  still carry the packaged stub. Detection compares against the *raw*
  template, but `render_blackboard` substitutes `{task_title}`, so an override
  using it would never match. Treat a blackboard as stock if it matches the
  packaged stub, the raw override, or the title-rendered override.
- **Brace semantics:** `retire.md` is rendered with `str.format(slug=...)`
  while `blackboard.md` uses `.replace`. A `retire.md` override containing
  stray `{`/`}` must produce a clean error naming the override file, not a raw
  `KeyError`/`ValueError`.
- **Precedent:** workflows and skills already resolve local-before-bundled
  with the same ref (`paths.resolve_workflow_path`, `resolve_skill_path`).
  Mirror that naming and error style. A missing packaged resource still raises
  `PackagedResourceMissing` → `ComposeError`. An unreadable repo override fails
  loud and catchable (never a silent fallback) via a **sibling exception**
  whose message names the repo file. Don't reuse `PackagedResourceMissing`,
  whose message says to reinstall Coga.
- **Prompt report:** layer metadata is carried on the composed result
  (`compose.py`, the dataclass documented as "Composed prompt plus layer
  metadata for prompt-scope reporting"). The `session_conduct` layer already
  records `ref=conduct_resource`, so add the source (`repo`/`packaged`) next to
  it.
- **Docs to edit (read, don't attach):**
  `docs/contexts/coga/prompt-composition/SKILL.md` (sections "Layer order" and
  "What each layer reads"), `docs/contexts/coga/blackboard/SKILL.md` (stock
  placeholder / `_is_stock_blackboard` text), and
  `docs/contexts/coga/session-conduct/SKILL.md` if it states that conduct text
  is package-fixed. Check for a packaged twin
  under `src/coga/resources/templates/coga/bootstrap/contexts/`, since
  `tests/test_packaging.py` enforces byte identity.
- **Out of scope:** append/patch overrides, overriding files under
  `resources/templates/` (init scaffolds and bundled batteries already have
  their own local-override paths), and any config key to relocate the override
  directory.
- No `coga/resources/` directory exists in this repo today, so there's no
  collision. Check `example/coga/` too.
- The shipped base prompt is ~47% of a composed launch prompt. Trimming it is
  a separate ticket; this feature lets repos trim it locally.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: repo-resource-overrides

Plan: one resolver in `coga.paths` (`resolve_resource_path` / `read_resource`)
that prefers `<cfg.repo_root>/resources/<name>` over the packaged copy, with a
sibling `RepoResourceUnreadable` exception. Thread `cfg` through
`compose._resource`, `blackboard.render_blackboard`,
`blackboard._is_stock_blackboard` (+ prelaunch reason helpers),
`commands/retire._retire_body`, `validate`, `create`, `mark`. Prompt report
uses `PromptLayer.path` for overrides. Validate warns on unknown names.

## Implement handoff

Pushed `repo-resource-overrides` @ a6afb07 (one commit on top of origin/main
e7d7f72). What changed:

- `coga.paths`: `RESOURCE_NAMES`, `repo_resources_dir`,
  `resource_override_path`, `resolve_resource_path`, `load_resource` (text +
  override path), `read_resource`, and sibling exception
  `RepoResourceUnreadable` (names the repo file; never falls back).
- `compose._resource(cfg, name)` returns `(text, override_path)`; base prompt,
  session conduct, and blocker preamble set `PromptLayer.path` to the override
  (None = packaged). Bootstrap launches get overrides too.
- `launch._format_prompt_report` lists `Repo resource overrides:` lines for
  layers whose `ref` is in `RESOURCE_NAMES` and have a `path`.
- `blackboard.render_blackboard(title, *, cfg=None)`,
  `_is_stock_blackboard(text, *, cfg=None)`, and both
  `prelaunch_blackboard_synthesis_reason*` take keyword `cfg`; `cfg=None`
  means packaged-only (kept so the existing text-level tests and any
  config-less caller stay valid). Every production caller passes `cfg`:
  `create.create_task`, `validate` (fix + draft check), `mark.prepare_active`.
  Stock detection = packaged stub, raw override, or title-rendered override
  (regex around `{task_title}`; one consistent single-line title).
- `retire._retire_body(cfg, ...)`: a bad `str.format` override raises
  `RepoResourceUnreadable` naming the file; `retire` bails (exit 2).
- `RepoResourceUnreadable` is handled alongside `BlackboardNeedsSynthesis` in
  `commands/mark`, `commands/launch` (both activation paths),
  `megalaunch._PREPARE_ACTIVE_ERRORS` (→ per-task "failed"), and
  `recurring_runner` delegated activation, so one bad override fails a task,
  not a sweep.
- `validate._check_repo_resources`: `unknown-resource-override` (warn;
  README.md and dotfiles skipped; also non-file entries) and
  `unreadable-resource-override` (error). Classified human-needed in
  `dream_validate_drift.classify_issue` (required by the
  every-emitted-kind test).
- Docs: coga/prompt-composition ("What each layer reads" owns the rule;
  "Measuring" covers the report), coga/blackboard (stock detection),
  coga/session-conduct (pointer). Packaged twins copied byte-identical.

Decisions: ticket text said "add the source (repo/packaged)" in one place but
Done said use existing `PromptLayer.path` and no new field — followed Done.
No example fixture change: behavior is opt-in and the fixture has no
`resources/`; verified `coga validate --json` on example is clean and warns on
a temporary typo'd file (removed).

Not done / for review: no `coga/resources/README.md` scaffold shipped (out of
scope). The packaged stub is still always treated as stock even after an
override, by design (pre-override tickets).

## Peer review

Codex peer review completed on 2026-10-08. Started on clean main, fetched
origin/main, and rebased the feature branch unconditionally onto e11ea75e1147a6d7cc0a7cde83aa622030dc069d.
Original author: Claude Code (claude-opus-5-5); review fixes: this Codex session.

- `codex review --base main` returned on 6a58a21a00d032d330102a9c26a44a046dd5c82f
  with three P2 findings: directory allocation before override read, uncaught
  creation failures, and silent fallback for broken links. Fixed in f24e20ac0.
- The same command returned on f24e20ac04c9fa32a8ba95afcc7b5d0daa51931c
  with two P2 findings (asymmetric archive filtering and unreadable-directory
  validation) and one P3 formatting TypeError. All fixed in e7c93dc76.
- The final command returned on e7c93dc76a8823b65cb7d6e424ee432ee4c54e0d, base e11ea75e1147a6d7cc0a7cde83aa622030dc069d,
  with no actionable findings. The initial review was independent of Claude;
  the final review is self-review of Codex fixes. All three used Codex CLI
  v0.160.1 / gpt-6-astra. The first sandboxed invocation could not initialize
  its app server; successful reviews used the approved unsandboxed retry.

Historical checks: 3415 passed in 255.57s on 6a58a21a0; 3423 passed in
374.68s on f24e20ac0. These receipts are not evidence for the final head.
Final suite: 3426 passed in 355.48s (0:05:55); exact final commands and scope are in PR preparation.
No unresolved findings. The branch is committed and pushed. At return, main
advanced to d69bafec061181faa55a2069d8c0798cde3e433c through unrelated
ticket/log state only; all 13 drift paths are outside the feature diff and this
ticket. The reviewed code base remains e11ea75e1; no later rebase changed the head.

Human-facing check: drove `launch bootstrap/orient --prompt-report` in a real
PTY at 80x24 and 120x40 against an isolated copy of example. Both override
paths were visible and complete (long paths wrap normally); no cursor or pager
state is involved. A typo override produced an unknown-resource-override
warning with exit 0. Example validation otherwise returned no issues.

## PR

```yaml
title: Let repos override Coga's fixed text resources
author: claude/codex
author_evidence: Claude Code (claude-opus-5-5) implemented a6afb07; this Codex peer-review session authored
  fixes f24e20ac0 and e7c93dc76. Rebase carried the original implementation as 6a58a21a0.
head: e7c93dc76a8823b65cb7d6e424ee432ee4c54e0d
base: e11ea75e1147a6d7cc0a7cde83aa622030dc069d
depth: deep
rationale: Inspect the shared prompt-loading and failure paths. All checks pass and the final Codex review
  returned, but Codex also authored review fixes, so the final receipt is self-review rather than independent
  verification of every change.
implementation: A shared repo-first resolver wholly replaces any of seven fixed resources when coga/resources/<name>
  exists. Prompt reports expose override paths; validation warns on typos and reports unreadable overrides.
  Blackboard creation preflights text before allocating a task path; recurring failures stay per-template;
  stock detection compares both sides after archive projection; invalid retire formats name the override.
deviations: Ticket context mentioned a repo/packaged source marker next to the conduct ref; followed the
  Done criterion instead (PromptLayer.path, no new field). cfg is keyword-optional on blackboard text
  helpers (None = packaged only).
limitations: 'Replace-only: repo overrides stop receiving upstream edits until manually merged. No templates/
  overrides, relocation option, or README scaffold. Verified on Python 3.12.12; no Python 3.11 run. Final
  review is self-review of the Codex-authored fixes.'
files:
  docs/contexts/coga/blackboard/SKILL.md: Document the overridable stock placeholder and three-way stock
    detection.
  docs/contexts/coga/prompt-composition/SKILL.md: Own the resource override rule and the prompt-report
    override listing.
  docs/contexts/coga/session-conduct/SKILL.md: Point conduct overrides at the owning rule.
  src/coga/blackboard.py: Render overrides and recognize packaged, raw, and title-rendered stock forms
    with symmetric archive projection.
  src/coga/commands/launch.py: Report repo overrides; refuse launch cleanly on an unreadable override
    during activation.
  src/coga/commands/mark.py: Refuse activation cleanly on an unreadable override.
  src/coga/commands/retire.py: Render retire.md via the resolver; name the override file on a bad template.
  src/coga/compose.py: Fixed layers read via the resolver and carry the override path.
  src/coga/create.py: Render blackboard overrides before allocating a task directory so failed recurring
    creation is retryable.
  src/coga/dream_validate_drift.py: Classify the two new validator kinds as human-needed.
  src/coga/mark.py: Pass cfg into draft-blackboard readiness.
  src/coga/megalaunch.py: Treat an unreadable override as a per-task activation failure.
  src/coga/paths.py: Centralize repo-first reads and reject unreadable files, broken links, and non-file
    known paths without fallback.
  src/coga/recurring_runner.py: Map an unreadable override to RecurringError for delegated activation.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: Packaged twin of coga/blackboard.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md: Packaged twin
    of coga/prompt-composition.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/session-conduct/SKILL.md: Packaged twin of
    coga/session-conduct.
  src/coga/validate.py: Warn on unknown names; report unreadable files/directories and failed readiness;
    leave unsafe fence repairs untouched.
  tests/test_blackboard.py: Cover override/fallback and all stock forms, including archived template sections.
  tests/test_compose.py: Cover base prompt, conduct variant, bootstrap override, fallback, and unreadable
    override.
  tests/test_launch.py: Cover the prompt-report override listing.
  tests/test_retire.py: Cover override rendering and malformed brace, attribute, and index placeholders.
  tests/test_validate.py: Cover typo warnings, unreadable files/directories, broken links, scoped readiness,
    and safe-fix refusal.
  src/coga/commands/create.py: Report unreadable blackboard overrides as a clean CLI error, including
    guided ticket creation.
  src/coga/recurring.py: Translate creation override errors to per-template RecurringError so the sweep
    continues.
  tests/test_create.py: Verify the create CLI names a bad override and creates no ticket.
  tests/test_recurring.py: Prove a bad blackboard leaves existing periods runnable and permits creation
    after repair.
review:
  reviewer: codex
  kind: self
  status: passed
  head: e7c93dc76a8823b65cb7d6e424ee432ee4c54e0d
  base: e11ea75e1147a6d7cc0a7cde83aa622030dc069d
  detail: codex review --base main returned on the final head with no actionable findings; its affected-area
    tests passed 1,215 tests. Original Claude implementation was reviewed independently by Codex; subsequent
    fixes were authored by Codex and the final Codex review is conservatively recorded as self-review.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q
  status: passed
  head: e7c93dc76a8823b65cb7d6e424ee432ee4c54e0d
  base: e11ea75e1147a6d7cc0a7cde83aa622030dc069d
  detail: 3426 passed in 355.48s (0:05:55); Python 3.12.12, final committed tree.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_blackboard.py tests/test_validate.py
    tests/test_retire.py tests/test_packaging.py
  status: passed
  head: e7c93dc76a8823b65cb7d6e424ee432ee4c54e0d
  base: e11ea75e1147a6d7cc0a7cde83aa622030dc069d
  detail: 200 passed in 13.85s; working tree committed unchanged as e7c93dc76.
- command: cd example && env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python
    -m coga.cli validate --json
  status: passed
  head: e7c93dc76a8823b65cb7d6e424ee432ee4c54e0d
  base: e11ea75e1147a6d7cc0a7cde83aa622030dc069d
  detail: 0 issues, ok_count 4.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/overload-resource-smoke.py
  status: passed
  head: e7c93dc76a8823b65cb7d6e424ee432ee4c54e0d
  base: e11ea75e1147a6d7cc0a7cde83aa622030dc069d
  detail: 'Real PTY at 80x24 and 120x40; temporary copy of example with launch-owned env and SLACK_WEBHOOK_URL
    removed. Ran launch bootstrap/orient --prompt-report: both base and attended override paths visible;
    ordinary line wrapping preserves full paths. validate --json with resources/promt.md returned only
    a warning and exit 0. No raw-terminal loop or pager changed.'
- command: git diff --check main...repo-resource-overrides
  status: passed
  head: e7c93dc76a8823b65cb7d6e424ee432ee4c54e0d
  base: e11ea75e1147a6d7cc0a7cde83aa622030dc069d
  detail: No whitespace errors.
```
