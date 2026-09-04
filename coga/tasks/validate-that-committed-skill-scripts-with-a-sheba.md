---
slug: validate-that-committed-skill-scripts-with-a-sheba
title: Validate that committed skill scripts with a shebang are executable
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
secrets: null
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
