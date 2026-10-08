---
title: overload base text; prompt, etc.
status: draft
owner: nicktoper
workflow: code/with-review
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
- `coga launch <slug> --prompt-report` shows whether each fixed layer came
  from `repo` or `packaged`;
- `coga validate` warns about a file in the repo `resources/` directory that
  matches no known resource name, so a typo can't silently do nothing;
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
- **Gotcha: stock-blackboard detection.** `_is_stock_blackboard` compares a
  ticket's blackboard to the stock template to decide that it is untouched.
  With an overridden `blackboard.md`, tickets created before the override
  still carry the packaged stub. Detection should accept both the effective
  (override) and the packaged stub, or authoring cleanup and prelaunch checks
  will treat old stubs as real content. Also note that `render_blackboard`
  substitutes `{task_title}`.
- **Precedent:** workflows and skills already resolve local-before-bundled
  with the same ref (`paths.resolve_workflow_path`, `resolve_skill_path`).
  Mirror that naming and error style. A missing packaged resource still raises
  `PackagedResourceMissing` → `ComposeError`; an unreadable repo override
  should fail the same loud, catchable way rather than silently falling back.
- **Prompt report:** layer metadata is carried on the composed result
  (`compose.py`, the dataclass documented as "Composed prompt plus layer
  metadata for prompt-scope reporting"). The `session_conduct` layer already
  records `ref=conduct_resource`, so add the source (`repo`/`packaged`) next to
  it.
- **Docs to edit (read, don't attach):**
  `docs/contexts/coga/prompt-composition/SKILL.md` (sections "Layer order" and
  "What each layer reads"), and `docs/contexts/coga/session-conduct/SKILL.md`
  if it states that conduct text is package-fixed. Check for a packaged twin
  under `src/coga/resources/templates/coga/bootstrap/contexts/`, since
  `tests/test_packaging.py` enforces byte identity.
- **Out of scope:** append/patch overrides, overriding files under
  `resources/templates/` (init scaffolds and bundled batteries already have
  their own local-override paths), and any config key to relocate the override
  directory.
- No `coga/resources/` directory exists in this repo today, so there's no
  collision.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
