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
step: 3 (open-pr)
launch_generation: pending:14ff41df-9c79-4c6f-ac33-0404cf7b6586
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

Clean feature worktree with three commits ahead of `origin/main`:
`2d245178` restores the four modes; `8d607263` adds validation;
`7c8cf6bd` applies peer-review fixes. Fetched and rebased successfully onto
`57e5681c` during peer review. Branch remains local; the next step opens the PR.

## What changed

- `src/coga/validate.py`: `_check_shebang_executables` checks the installed
  skills root and packaged bootstrap skills during a whole-repo sweep. Any
  regular file beginning with `#!` needs an executable bit, regardless of
  extension. Failures are `non-executable-script` errors with an actionable
  mode-change hint. Import-only modules without a shebang remain valid.
- A top-down walk prunes `.git`, `__pycache__`, `node_modules`, and `.venv`
  before descending. Symlinked files and directory contents are skipped.
- Four committed modes are now `100755`: the ticket's three files plus
  `coga/skills/clarity/scripts/validate_package.py`, added since the survey.
- Dream classifies the new issue as a PR proposal. The packaged `coga/cli`
  context documents the behavior and remediation; it has no live twin.

## Mode-source decision

POSIX normally checks `Path.stat().st_mode & 0o111`, including non-Git
repositories and machines without Git. Local `git config` queries detect
`core.fileMode=false`; that setting and non-POSIX platforms use
`git ls-files --stage` instead. A root is skipped when neither mode source is
trustworthy. Git filenames are decoded explicitly as UTF-8, preserving
non-ASCII paths on Windows. The queries are local and read-only; network/auth
probes remain opt-in. Stage mode changes with `git add --chmod=+x` where Git
ignores filesystem modes.

This supersedes the implement step's decision to always trust POSIX stat.
The existing GitHub-probe mocks now explicitly allow only the new local mode
query while still rejecting unexpected network/auth commands.

## Peer review

`codex review --base origin/main` **returned successfully** from the recorded
feature worktree before any handoff. Its one P2 finding was that
`sorted(root.rglob("*"))` traversed excluded dependency trees before filtering:
100,000 excluded files took 3.6 seconds and about 106 MiB extra peak memory.
Fixed by pruning before descent with `os.walk`.

Additional findings from this peer-review pass: POSIX `core.fileMode=false`
could both falsely flag index `100755` / stat `0644` and miss index `100644` /
stat `0755`; Windows locale decoding could silently skip non-ASCII index paths.
Both are fixed. Regression tests demonstrated all four failures before the
fixes (two mode-source cases, Unicode paths, and dependency traversal).
Bundled-root coverage also confirms that packaged scripts are checked.

## Verification

- Focused validation and Dream tests: **163 passed**.
- Full suite before the final rebase: **2443 passed, 1 pre-existing failure**.
- Post-rebase full suite: **2443 passed, the same 1 pre-existing failure**
  (217.53 seconds). A final fetch confirmed zero commits behind `origin/main`.
- `coga validate --json` in the feature checkout's `coga/`: **zero
  non-executable-script issues**, 32 unrelated task/config findings (including
  missing local user and webhook configuration). Full JSON is at
  `/tmp/coga-shebang-peer-review-validate-final.json`.
- `coga validate --json` in `example/coga/`: **zero issues**, exit 0.
- `coga validate --task validate-that-committed-skill-scripts-with-a-sheba --json`
  from the primary checkout after the blackboard update: **zero issues**, exit 0.
- `git diff --check origin/main...HEAD`: passed. Git's index confirms `100755`
  for all four repaired scripts.

The full-suite failure is
`tests/test_packaging.py::test_live_and_packaged_copies_stay_identical`:
`coga/contexts/coga/codebase/SKILL.md` differs from its packaged twin in the
`text.py` and skill-update paragraphs. Reproduced on the primary `main`
checkout with the isolated packaging test; this change touches neither file.
The pending packaged-side repair is recorded under
`autofix/report-per-skill-outcomes-from-gh-skill-update-in`, PR #796.

Exact feature-suite commands (Python 3.12 from the primary checkout's venv):

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/n/Code/claude/coga-shebang-exec-check/src /home/n/Code/claude/coga/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_validate.py tests/test_dream_validate_drift.py --tb=short
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" ../coga/.venv/bin/python -m pytest -q -p no:cacheprovider --tb=short
```

From each of the two Coga roots above:

```bash
env -u SLACK_WEBHOOK_URL -u COGA_IMPORTANT_WEBHOOK_URL PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/n/Code/claude/coga-shebang-exec-check/src coga validate --json
```

The inherited webhook variables were unset only for these read-only checks;
no configuration files were edited.

## PR

Skill instructions can fail with permission denied when a shebanged script is
committed without its executable bit. Add `non-executable-script` errors to
`coga validate` for the installed and packaged bootstrap skill trees, and
restore `100755` on the four affected scripts. Document the check in the CLI
context and classify its findings as Dream PR proposals.

Use working-tree modes on POSIX and the Git index on Windows or when
`core.fileMode=false`; skip roots with no trustworthy mode source. Local Git
queries keep validation offline. Prune dependency directories before traversal
and preserve non-ASCII Git paths when reading the index.

Test plan: `python -m pytest -q -p no:cacheprovider --tb=short` with the feature `src` on `PYTHONPATH` (2443 passed, 1 pre-existing failure); `coga validate --json` in `coga/` and `example/coga/` (zero shebang errors; example has zero issues). The full-suite failure is unrelated `coga/codebase` live/packaged drift, also reproduced on `main` and tracked in PR #796.
