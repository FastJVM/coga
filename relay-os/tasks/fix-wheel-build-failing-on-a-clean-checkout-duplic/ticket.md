---
title: Fix wheel build failing on a clean checkout (duplicate skills/_template force-include)
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

`pip wheel .` (the hatchling build) fails on a **clean checkout** of this repo
with:

    ValueError: A second file is being added to the wheel archive at the same
    path: `relay/resources/templates/relay-os/skills/_template/SKILL.md`.

`skills/_template/SKILL.md` is pulled in by **two** rules in
`[tool.hatch.build.targets.wheel]`: the `packages = ["src/relay"]` filesystem
walk *and* the explicit `force-include` of
`src/relay/resources/templates/relay-os/skills/_template`. Hatchling treats
them as two distinct files and aborts.

### Why it has gone unnoticed

- `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries` is the
  only test that actually builds a wheel, and it opens with
  `pytest.importorskip("hatchling")`. No CI runs, and dev venvs typically lack
  the `hatchling` *build backend*, so the test silently **skips** — the suite
  shows green while the wheel is unbuildable.
- When a developer *does* have hatchling installed, they are usually building
  from a tree where `relay init` / agent setup has created ~17 **gitignored**
  symlinks under the templates tree
  (`.claude/skills/relay`, `.codex/skills/relay`, `.agent-skills/*`). With those
  symlinks present, hatchling's walk dedups the `_template/SKILL.md` collision
  away and the build succeeds. A pristine checkout (a fresh `git clone` or
  `git worktree`, i.e. what a release or `pip install git+…` actually uses) has
  none of them, so the collision is fatal.

Net: the wheel builds on dev machines by accident and fails for anyone
installing from a clean source tree.

### Acceptance criteria

- `pip wheel --no-build-isolation --no-deps .` succeeds from a **fresh
  checkout with no init-generated symlinks** (reproduce by building from a new
  `git worktree`).
- The built wheel still contains every bootstrap battery the existing
  `EXPECTED_BOOTSTRAP_RESOURCES` list asserts, including
  `skills/_template/SKILL.md` — the force-include exists because the `packages`
  walk silently drops pure-data (no-`.py`) skill dirs (see the #259 comments in
  `pyproject.toml`), so the fix must keep `_template` shipping, not just stop
  duplicating it.
- The build is verified against **both** tree shapes: clean (no symlinks) and a
  dev tree that has the `.agent-skills`/`.claude`/`.codex` symlinks.
- `hatchling` is added as a tracked **dev/test** dependency (a dev-requirements
  file or a `[project.optional-dependencies]` test extra — NOT runtime
  `requirements.txt`, since relay never imports hatchling at runtime) so
  `test_wheel_includes_bootstrap_batteries` actually runs instead of skipping.

### Fix sketch (refine in implement)

- Likely either exclude `skills/_template` from the `packages` grab (mirroring
  the existing `bootstrap/` exclude+force-include pairing) so only the
  force-include ships it, or drop the `_template` force-include if the walk
  already covers it on a clean tree. The dedup behavior is symlink-sensitive,
  so test both tree shapes before settling.

## Context

Discovered while implementing
`detect-recurring-runs-that-mark-done-without-advan` (the skipping packaging
test was investigated and found to mask this). Unrelated to that ticket's
behavior; filed separately to keep scope clean. Relevant code:
`pyproject.toml` (`[tool.hatch.build.targets.wheel]` + `.force-include`) and
`tests/test_packaging.py`.

