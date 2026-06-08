The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

- branch: `fix-wheel-template`
- worktree: `/home/n/Code/codex/relay-fix-wheel-template`
- build env: `/tmp/wheelenv` (python3.12 venv with hatchling+pip; system python is 3.9, project needs >=3.11)

## Reproduction (confirmed)

Built `pip wheel --no-build-isolation --no-deps .` from the fresh worktree
(no init symlinks under templates tree). Fails with:

    ValueError: A second file is being added to the wheel archive at the same
    path: `relay/resources/templates/relay-os/skills/_template/SKILL.md`.

Confirms the `packages = ["src/relay"]` walk DOES pick up `_template/SKILL.md`
on a clean tree, colliding with the explicit `skills/_template` force-include.

## Fix (chosen)

Mirror the existing `bootstrap/` exclude+force-include pairing: add
`**/relay-os/skills/_template/**` to the wheel `exclude` list so the packages
walk no longer grabs it; the force-include remains the single, deterministic
shipper of `_template`. AC mandates keeping the force-include (the walk drops
pure-data dirs in some tree shapes), so excluding-from-walk is the right side
to cut, not dropping the force-include.

Also: add `hatchling` (+ pytest) as a tracked dev/test dependency via
`[project.optional-dependencies].test` so `test_wheel_includes_bootstrap_batteries`
actually runs instead of `importorskip`-skipping. NOT in runtime requirements.txt.

## Verification (done)

- clean tree (no symlinks): `pip wheel --no-build-isolation --no-deps .` → **succeeds**.
  Wheel contains `skills/_template/SKILL.md` exactly once + all
  EXPECTED_BOOTSTRAP_RESOURCES. (Before fix: ValueError collision — reproduced.)
- dev tree (recreated 21 symlinks via `refresh_agent_skill_view` + `.claude`/`.codex`
  compat links): build **also succeeds**, `_template` ships. Symlinks then removed;
  worktree diff is `pyproject.toml` only.
- `pytest tests/test_packaging.py` → 2 passed; `test_wheel_includes_bootstrap_batteries`
  now actually RUNS (hatchling installed via `.[test]`) instead of importorskip-skipping.
- Full suite: 561 passed, 1 failed, 2 collection errors — all unrelated/pre-existing:
  - `test_dream_worker_templates.py::test_cleanup_orphan_markers_declares_contract`
    fails on a line-wrap assertion (`as\n\`human-needed\``). Pre-existing on main
    (confirmed: fails on the primary checkout too). NOT caused by this change.
  - `test_gmail_skill.py` / `test_google_calendar_skill.py` collection errors:
    missing optional `googleapiclient` in the venv — environment-only.

## Adjacent finding (out of scope — follow-up ticket candidate)

A wheel built from a **dev tree** (with the gitignored `.agent-skills`/`.claude`/`.codex`
symlink views present) leaks ~51 `.agent-skills/...` view entries into the wheel.
Pre-existing; real releases build from clean trees (no symlinks) so it doesn't affect
shipped wheels. Could be fixed by excluding `**/.agent-skills/**`, `**/.claude/**`,
`**/.codex/**` from the wheel walk. Left for a separate ticket to keep this scoped.
