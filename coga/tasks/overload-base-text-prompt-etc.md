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
step: 2 (peer-review)
agent: claude
launch_generation: pending:3e2da5a1-cef6-4a5d-87f6-a77af667d840
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

## PR

```yaml
title: Let repos override Coga's fixed text resources
author: claude
author_evidence: Implement step session ran as Claude Code (claude-opus-5-5); this handoff.
head: a6afb07af437e90d8c0e17df1a8b339d0909404e
base: e7d7f720664bac5019279a20de31ccd9d0e0d92b
depth: deep
rationale: Touches every launch prompt's fixed layers, draft-activation readiness, and several activation error paths; no code review has run yet.
implementation: One repo-first resolver (paths.load_resource) for the seven top-level resources, threaded through compose, blackboard, create, validate, mark, and retire; prompt report shows overrides via PromptLayer.path; validate warns on unknown names.
deviations: Ticket context mentioned a repo/packaged source marker next to the conduct ref; followed the Done criterion instead (PromptLayer.path, no new field). cfg is keyword-optional on blackboard text helpers (None = packaged only).
limitations: Replace-only by design; overridden files stop receiving upstream edits. Unreadable-override handling for activation was added at each existing BlackboardNeedsSynthesis handler rather than a shared mechanism.
files:
  docs/contexts/coga/blackboard/SKILL.md: Document the overridable stock placeholder and three-way stock detection.
  docs/contexts/coga/prompt-composition/SKILL.md: Own the resource override rule and the prompt-report override listing.
  docs/contexts/coga/session-conduct/SKILL.md: Point conduct overrides at the owning rule.
  src/coga/blackboard.py: Read blackboard.md via the resolver; stock detection accepts packaged, raw, and title-rendered override.
  src/coga/commands/launch.py: Report repo overrides; refuse launch cleanly on an unreadable override during activation.
  src/coga/commands/mark.py: Refuse activation cleanly on an unreadable override.
  src/coga/commands/retire.py: Render retire.md via the resolver; name the override file on a bad template.
  src/coga/compose.py: Fixed layers read via the resolver and carry the override path.
  src/coga/create.py: Render the repo blackboard override for new tickets.
  src/coga/dream_validate_drift.py: Classify the two new validator kinds as human-needed.
  src/coga/mark.py: Pass cfg into draft-blackboard readiness.
  src/coga/megalaunch.py: Treat an unreadable override as a per-task activation failure.
  src/coga/paths.py: Add RESOURCE_NAMES, the repo-first resolver, and RepoResourceUnreadable.
  src/coga/recurring_runner.py: Map an unreadable override to RecurringError for delegated activation.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: Packaged twin of coga/blackboard.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md: Packaged twin of coga/prompt-composition.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/session-conduct/SKILL.md: Packaged twin of coga/session-conduct.
  src/coga/validate.py: Check resources/ for unknown and unreadable overrides; pass cfg to blackboard helpers.
  tests/test_blackboard.py: Cover override render, fallback, and stock detection forms.
  tests/test_compose.py: Cover base prompt, conduct variant, bootstrap override, fallback, and unreadable override.
  tests/test_launch.py: Cover the prompt-report override listing.
  tests/test_retire.py: Cover retire.md override and stray-brace error.
  tests/test_validate.py: Cover unknown-name warning and unreadable-override error.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Implement step does not review; code review belongs to a later workflow step.
checks:
  - command: .venv/bin/python -m pytest -q
    status: passed
    head: a6afb07af437e90d8c0e17df1a8b339d0909404e
    base: e7d7f720664bac5019279a20de31ccd9d0e0d92b
    detail: 3415 passed in 257s; run on the working tree that was then committed unchanged as a6afb07 (rebase was a no-op).
  - command: (cd example && env -u SLACK_WEBHOOK_URL ../.venv/bin/coga validate --json)
    status: passed
    head: a6afb07af437e90d8c0e17df1a8b339d0909404e
    base: e7d7f720664bac5019279a20de31ccd9d0e0d92b
    detail: 0 issues, ok_count 4; with a temporary resources/promt.md it reported one unknown-resource-override warn.
```
