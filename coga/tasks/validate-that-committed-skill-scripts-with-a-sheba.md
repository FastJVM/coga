---
title: Validate that committed skill scripts with a shebang are executable
status: in_progress
owner: nicktoper
agent: claude
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
launch_generation: 13d252c7-a18e-498f-953f-390a78a925dd
---

## Description

`coga/skills/browser/playwright/scripts/playwright_cli.sh` was committed `100644` while its own
`references/cli.md` documented invoking it as `"$PWCLI" …`. Every run failed permission-denied,
and it was only found when an agent hit it. PR #719 restored the bit; nothing stops it recurring.

Add a check: **a committed file whose first two bytes are `#!` must be executable.** That rule is
exactly right for this tree — it catches three real violations today and produces zero false
positives across every `.sh` / `.py` under the live and packaged skill trees.

Current violations:

| file | mode |
| --- | --- |
| `coga/skills/anthropic/skill-creator/eval-viewer/generate_review.py` | `100644` |
| `src/coga/resources/templates/coga/bootstrap/skills/coga/gmail/gmail.py` | `100644` |
| `src/coga/resources/templates/coga/bootstrap/skills/coga/google-calendar/gcal.py` | `100644` |

Fix those three in the same change so the check lands green.

## Context

### Why the shebang is the right predicate

The obvious rule — "scripts must be executable" — false-fires. `skill-creator/scripts/utils.py`
and `scripts/__init__.py` are import-only modules, correctly `100644`, and carry no shebang. The
seven sibling scripts that *are* meant to be run directly all carry one and are all `100755`. The
shebang is the author's own declaration of intent, so keying off it needs no allowlist.

Full survey as of 2026-09-01 — 14 files, shebang and mode agree on 11, disagree on the 3 above:

    100644 no-shebang  skill-creator/scripts/__init__.py          correct
    100644 no-shebang  skill-creator/scripts/utils.py             correct
    100644 shebang     skill-creator/eval-viewer/generate_review.py   VIOLATION
    100644 shebang     packaged coga/gmail/gmail.py                   VIOLATION
    100644 shebang     packaged coga/google-calendar/gcal.py          VIOLATION
    100755 shebang     (7 skill-creator scripts + both playwright_cli.sh copies)  correct

### Where the check belongs

`coga validate` is the better home than a pytest. The failure mode — an agent following a SKILL.md
that says to run a script, and getting permission-denied — happens in *any* Coga repo with
vendored skills, not just this one, and `coga validate --json` is the gate users already run. A
pytest in `tests/test_packaging.py` would only ever protect this repo.

`src/coga/validate.py` currently scopes to tasks, workflows, and recurring templates, so this adds
a new kind of check; keep it in its own `_check_*` function alongside the others and scope it to
the skills root (`skill_manager.skills_root`) plus the packaged bootstrap skills.

### Mode-reading subtlety

Prefer reading the working-tree mode (`Path.stat().st_mode & 0o111`) over shelling out to
`git ls-files -s`: it works in a Coga repo that is not a git checkout, which `coga validate` must
tolerate. Two caveats to handle:

- A local `chmod +x` that was never staged makes a still-broken commit look fine locally. That is
  acceptable for a validator — the fresh-clone case is what matters, and there the working-tree
  mode is set from the index.
- Repos with `core.fileMode=false` (and Windows checkouts) report unreliable working-tree modes.
  Decide whether to skip the check there or fall back to the git index when git is available, and
  say which in the PR body. Do not let it emit false errors on Windows.

Emit it as an `error`, not a `warn` — a non-executable documented script is a hard breakage, not a
style preference.

### Verification

`python -m pytest` plus `coga validate --json` clean after fixing the three files. Add a test that
the check fires: a temp skill dir with a shebanged `100644` script should produce the issue, and
the same script `100755` should not.

<!-- coga:blackboard -->

## Dev

branch: shebang-exec-check
worktree: /home/n/Code/claude/coga-shebang-exec-check

Separate feature checkout (linked worktree off `origin/main`). Two commits:
`d6acc70d` restores the modes, `c7ec58d8` adds the check. Rebased on
`origin/main` at handoff; no push, no PR.

## What changed

- `src/coga/validate.py`: new `_check_shebang_executables` wired into `run()`
  after the recurring-template check. Scope: `skill_manager.skills_root` plus
  `bundled_skills_root` (packaged bootstrap skills). Predicate: first two bytes
  `#!` → must be executable. Emits `non-executable-script`, severity `error`,
  task label `skills/<rel>` or `bootstrap/skills/<rel>`. Skips symlinks and
  `.git`/`__pycache__`/`node_modules`/`.venv` dirs.
- `src/coga/dream_validate_drift.py`: classifies the new kind as a PR
  proposal (`test_classifier_explicitly_covers_every_emitted_validator_kind`
  fails otherwise — every emitted kind must be classified).
- `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`:
  documents the check in the `coga validate` paragraph (no live twin exists
  for `coga/cli`, so no sync needed).
- Modes fixed: the ticket's three plus a **fourth** that landed after the
  survey — `coga/skills/clarity/scripts/validate_package.py` (shebang,
  100644). Full survey of both trees at branch time: 15 shebanged files, 4
  wrong, 0 false positives.
- Tests (`tests/test_validate.py`): fires on a shebanged `0o644` temp skill
  script and not on its `0o755` copy nor a shebang-less `0o644` module; skips
  silently with no trustworthy source; reads the git index (real `git_repo`
  harness, `update-index --chmod`) when the working tree carries no mode.
  `tests/test_dream_validate_drift.py` gains the kind in the PR-proposal
  parametrize.

## Decisions (for the PR body)

- **Mode source.** POSIX: `Path.stat()` only. It is what `exec` enforces on
  that machine, a fresh clone sets it from the index, and it keeps default
  `coga validate` subprocess-free — `test_run_no_github_check_by_default`
  and the `--check-github` fake-subprocess tests assert that no git runs
  unless opted in, so the ticket's "consult `git config core.fileMode`"
  variant was tried and rejected (it broke 10 tests). Non-POSIX (Windows):
  read `git ls-files --stage` under each root; if git is missing or the root
  is not in a checkout, skip the check for that root (no false errors).
  `core.fileMode=false` on POSIX is therefore handled by stat, i.e. by what
  the mount actually enforces — documented in the function docstring and
  the `coga/cli` context.
- Kept it a `_check_*` in `validate.py` per the ticket (not a pytest): the
  failure is any Coga repo's, not this one's.

## Verification

- `python -m pytest`: 2438 passed, 1 failed — the failure is
  `tests/test_packaging.py::test_live_and_packaged_copies_stay_identical`
  and is **pre-existing on `origin/main`** (reproduced with this branch's
  changes stashed): `coga/contexts/coga/codebase/SKILL.md` has drifted from
  its packaged twin (the `text.py` sentence and the `update_skills` /
  `gh skill update` paragraph). Not touched here; needs its own fix.
- `coga validate --json` from `coga/` in the worktree: zero
  `non-executable-script` issues (35 pre-existing unrelated drift items:
  stuck-in-progress, unfrozen-workflow, etc.). `chmod -x` on
  `playwright_cli.sh` makes it fire with the expected message; restored.
- `coga validate --json` against `example/coga`: `[]`.
- Interpreter note: the worktree has no venv; ran with
  `../coga/.venv/bin/python` (3.12) and pytest's `pythonpath = ["src"]`.
