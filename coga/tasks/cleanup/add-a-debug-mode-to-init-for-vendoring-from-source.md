---
slug: cleanup/add-a-debug-mode-to-init-for-vendoring-from-source
title: Vendor the init venv from PyPI only, dropping source-install paths
status: done
owner: nicktoper
human: nick
agent: claude
assignee: nicktoper
contexts: []
skills: []
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
secrets: null
---

## Description

**Scope superseded 2026-09-08 (owner): delete the vendored venv outright.**
The original task below collapsed the three install-source tiers to one. PR
review made the better question visible: the vendored venv is not load-bearing
at all, so the tiers are not worth simplifying — they are worth deleting.

`coga init` scaffolds the markdown OS and nothing else. Remove the vendored
venv, the repo-local CLI it backed, and everything that existed only to feed
them: `resolve_install_source` / `InstallSource`, `install_venv`,
`vendored_cli_version`, `write_pin` / `read_pin` / `COGA_PIN`,
`write_bin_wrapper`, the `~/.local/bin/coga` shim, `COGA_PYTHON`, the
requires-python and pip-hint helpers, and `install_skill_requirements`. The
`coga` an operator runs is their own global install, in every repo.

**Why it isn't load-bearing.** The documented install path is `uv tool install
coga` then `coga init`, and `_try_install_shim` skips when `~/.local/bin/coga`
is already claimed — which it always is after a global install. So the vendored
CLI is never the one that runs. `install_skill_requirements` was called only
from `install_venv`, so a skill installed later never got deps at all, and
nothing put `.coga/.venv/bin` on a launched agent's `PATH`, so the deps it did
install were invisible to the documented `python .../gmail.py` invocation.
`COGA_PIN`'s only reader was `coga --version`. Skill dependencies become the
operator's to install, which is what the skills' own error messages now say.

**Retained from the original task:** `.coga/` itself stays — it still holds
machine-local run records and the megalaunch selection.

---

*Original task, kept for the record:*

`coga init` currently resolves the CLI it vendors through three tiers in
`resolve_install_source()` (`src/coga/commands/update.py:66`): a
`COGA_REPO_URL` override, the source checkout the running package is imported
from, then `coga==<running version>` from PyPI. Collapse that to the last one.
A user's repo should always vendor a release; the two source paths are
complexity serving a workflow nobody uses.

**The scrub. Build exactly this — the decision is made, do not reopen it:**

1. Delete the `COGA_REPO_URL` override and `_running_checkout_root()` from the
   resolution path, leaving `resolve_install_source()` as
   `coga==<running version>` from PyPI. `InstallSource.kind` collapses to a
   single case; `_checkout_install_source()`, `_pyproject_project_name()` and
   `pip_git_source()` go with it. Keep `redacted_git_source()` — it has 8
   other callers.
2. Fail clearly when the running version isn't on PyPI (the unreleased-main
   case), rather than surfacing a raw pip error. The message should say init
   vendors releases only and name the version it tried.
3. Rewrite the packaged
   `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md:27-38`
   paragraph, which documents the three-tier behaviour.
4. Drop the now-dead tests in `tests/test_init.py:320-412` (seven tests, of
   which the override and checkout ones go entirely) and cover the new failure
   message.
5. Document the resulting behaviour in `docs/development.md` and
   `docs/releasing.md`, which say nothing about it today. Consider documenting
   `COGA_PYTHON` (`update.py:420`) in the same pass — it is undocumented in
   exactly the same way.

**Out of scope.** Do not touch managed-skill installs (`coga skill install`
and the managed-skill manifest are unaffected). Do not publish to PyPI. Keep
`.coga/` as the machine-local state directory.

*(The original out-of-scope line reserved the vendored venv and the `COGA_PIN`
format; the superseding scope above removes both deliberately.)*

## Context

**This does not need to wait for the 1.0 publish.** Checked 2026-09-05:
users installed from PyPI are running a released version, so
`coga==<that version>` resolves and nothing changes for them. The test suite
never reaches the network — `resolve_install_source` and `vendored_cli_version`
are monkeypatched (`tests/test_init.py:270`) and `install_venv` tests use
`_fake_install_source()`. The only real `coga init` in tooling is
`scripts/verify-clean-install-container.sh:32`, the release gate, which
installs from PyPI by design and runs a released version.

The one consequence is that a coga developer on unreleased main (this repo is
`0.3.1`; PyPI serves `0.2.0`) running `coga init` gets the new failure from
item 2. That is the intended behaviour, not breakage: init vendors releases,
and the message says so. Land whenever.

**Why the source tiers aren't needed (verified 2026-09-05).** Neither coga
development checkout has a vendored venv at all — no `coga/.coga/.venv`, no
`COGA_PIN`, in either `/home/n/Code/codex/coga` or `/home/n/Code/claude/coga`.
Both run the global `uv tool` editable install (`~/.local/bin/coga` →
`~/.local/share/uv/tools/coga/bin/coga`, `direct_url.json` pointing at the
claude checkout). Coga developers install the CLI from source and run it
globally; the vendored venv is a user's-repo artifact. So the "developers need
a source lever to test init" justification does not hold.

**The bug that started this, and why removal beats a flag.** The middle tier
silently picks whatever checkout the running package is imported from. With
the owner's editable install linked to `/home/n/Code/claude/coga`, running
`coga init` from `/home/n/Code/codex/coga` vendors the *claude* checkout —
wrong bytes, no warning, no output naming the source. The original plan was to
add `--from-source PATH` to disambiguate; deleting the implicit tier removes
the ambiguity instead of adding surface to manage it.

**Blast radius.** One real caller of `resolve_install_source()`:
`init.py:827`, which resolves before any writes so a bad source fails loud
leaving nothing on disk. Plus `install_venv()`'s default argument
(`update.py:609`). Tests are `tests/test_init.py:320-412`.

**Docs surfaces.** `docs/development.md` and `docs/releasing.md` contain zero
mention of `COGA_REPO_URL` or source-vendoring — nothing to delete there, only
the new behaviour to describe. `docs/migrating-to-coga.md:14` lists
`COGA_REPO_URL` in the Relay→Coga rename table and must lose the row.
`docs/reference.md:14-19` enumerates `coga init`'s arguments; no flag is being
added, so it needs no new option, but check it says nothing stale.
`docs/releasing.md:87` states the install gate "deliberately installs Coga
only from PyPI" — after this change that becomes true of *all* init runs, so
the paragraph can be simplified rather than contradicted.

**Twin-rule exception.** CLAUDE.md requires live and packaged copies of
shipped contexts to be edited together, but the packaged
`bootstrap/contexts/coga/cli/SKILL.md` has no live twin —
`coga/contexts/coga/cli/` does not exist. `cli` is packaged-only. Do not hunt
for one.

**Unchanged by this ticket:** the vendored venv is built with stdlib
`python -m venv` (`update.py:672`) and `<venv>/bin/python -m pip install`
(`update.py:693`), with a second pip pass in `install_skill_requirements`
(`update.py:752`). uv is how a developer installs the CLI, not how init builds
`.coga/.venv`. Leave that alone.

Source: `marketing/phase-0-audit` step 1 (2026-09-02), triaged by the owner in
step 2 (2026-09-03); re-scoped 2026-09-05
from "add a debug mode" through "simplify the tiers" to "delete the source
tiers", after confirming no development checkout uses a vendored venv. This
directory holds the work the owner wants done before the marketing materials
ship.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/759
branch: vendor-pypi-only
worktree: /home/n/Code/codex/coga-vendor-pypi-only

## Plan (2026-09-05)

Implementing the scrub exactly as specified. Three calls the ticket left open,
decided this session:

1. **Item 2 detection is a pip-stderr hint, not a network pre-check.** Nothing
   can know a version is absent from PyPI without hitting the network, so a
   pre-flight PyPI query would put a network call in `resolve_install_source()`
   on every init. Instead `unpublished_release_hint()` sits beside the existing
   `hash_checking_hint()` and fires on pip's "no matching distribution" markers.
   Owner confirmed: keep pip's raw stderr *and* append the explanation, because
   an offline machine produces the same marker — replacing the message would
   misdiagnose no-network as unreleased. The hint's wording names both causes.
2. **`InstallSource.kind` deleted, not kept at one value.** With `checkout` and
   `url` gone the field has a single possible value and no reader in `src/`.
3. **`_requires_python_spec()` deleted too** — collateral dead code, its only
   caller was `_checkout_install_source()`. Its two direct unit tests go with
   it. `_running_requires_python()` (metadata-based) is what the release path
   uses and stays.

Keeping the `COGA_REPO_URL` *constant* (the upstream repo URL) — `uninstall.py`
imports it. Only `COGA_REPO_URL_ENV`, the override, goes.

## Implemented (2026-09-05)

Commit `07088bb9` on `vendor-pypi-only`, rebased onto latest `origin/main`,
working tree clean. All five checklist items landed.

**1. Resolution collapsed.** `resolve_install_source()` is now only
`coga==<running version>` from PyPI. Deleted: `COGA_REPO_URL_ENV`,
`_running_checkout_root()`, `_checkout_install_source()`,
`_pyproject_project_name()`, `pip_git_source()` (github_source.py), plus the
two collateral dead pieces from the Plan above. Kept: the `COGA_REPO_URL`
*constant* (uninstall.py:32 imports it — it is the upstream repo URL, not the
override) and `redacted_git_source()` (7 remaining callers in pr_assist.py and
git.py). Its import in update.py went, since the url branch was its only use
there.

**2. New failure path.** `unpublished_release_hint(stderr, pip_spec)` beside
`hash_checking_hint()`, fired from `install_venv`'s pip-failure branch. Also
dropped `stderr.replace(source.pip_spec, source.display)` — that redaction
existed only because a `url` source's spec could carry credentials; a
`coga==X` spec never can.

Verified live from this checkout's editable install:
`resolve_install_source()` → `InstallSource(pip_spec='coga==0.3.1',
display='coga==0.3.1 (PyPI)', requires_python='>=3.11')`. Before this change it
returned a checkout path — the bug in the ticket's Context.

**3–5.** Packaged `cli/SKILL.md` paragraph rewritten (no live twin, per the
ticket's twin-rule exception — confirmed `coga/contexts/coga/cli/` absent).
`docs/development.md` gains a "`coga init` vendors a published release"
section covering the dev consequence and `COGA_PYTHON`; `docs/releasing.md`
gains a Notes bullet and its gate paragraph is simplified rather than
contradicted; `docs/migrating-to-coga.md` loses the `RELAY_REPO_URL` row.
`docs/reference.md:14-19` checked — describes only init's arguments, nothing
stale, no new flag to add.

**Tests.** Ten dropped (the seven dead resolution tests, the
`_running_checkout_root` detection test, and the two `_requires_python_spec`
unit tests); five added: release pinning, `COGA_REPO_URL` proven inert, the
no-installed-distribution exit, and both hint branches.

## Verification

Ambient `python3` here is 3.9, which coga refuses. Built a throwaway 3.12
venv with `pip install -e ".[test]"` (in the scratchpad, not the repo) for an
authoritative run.

- Full suite in that venv: **1 failed, 2364 passed**. The one failure,
  `test_notification_messages.py::test_recurring_create_is_silent`, is
  **pre-existing**: stashing the whole diff and re-running it reproduces the
  identical `IsADirectoryError` on unmodified main.
- Cross-check with a bare `python3.12 -m pytest` (no editable test-extra
  install): unmodified main fails 27, this branch fails the same set. Neither
  side has a single `test_init` / update / github_source failure. Those 27 are
  an artifact of the missing editable install, not of this change.
- `coga validate --json` on `example/`: clean (needs `env -u
  SLACK_WEBHOOK_URL` — a stray var in this shell trips the bare-webhook
  check). On the repo itself: four pre-existing `unsynthesized-draft-blackboard`
  errors, all on unrelated `v2/*` tickets.
- No `example/` fixture change needed: nothing here touches task layout,
  prompt composition, or workflow semantics.

**Adjacent, not fixed here (follow-up candidates).** The repo's four
`unsynthesized-draft-blackboard` validate errors on `v2/*` tickets, and the
`test_recurring_create_is_silent` failure, both predate this ticket and are
out of its scope.

**Not done, by design:** no push and no PR — that is the `code/open-pr` step.

## Peer review (2026-09-05)

- Ran `git fetch origin main` and `git rebase FETCH_HEAD` in the recorded
  worktree. Rebase completed without conflicts onto `e023d244`; the feature
  commit is now `895f6c0d` and the branch is clean, one commit ahead.
- `codex review --base origin/main` completed with **no actionable
  regressions**. Its 211 targeted tests passed; no review-fix commit is needed.
- Full post-rebase `python -m pytest`: **2364 passed, 1 failed** in 150.99s.
  Used the implementation's Python 3.12 test venv, whose editable install was
  verified to point at this feature worktree, with its `bin` first on `PATH`
  and `PYTHONPATH=/home/n/Code/codex/coga-vendor-pypi-only/src`.
  Output: `/tmp/coga-vendor-peer-review-pytest.log`.
- The sole failure remains
  `tests/test_notification_messages.py::test_recurring_create_is_silent`.
  Re-ran `python -m pytest -q
  tests/test_notification_messages.py::test_recurring_create_is_silent` in
  the primary checkout with `PYTHONPATH=/home/n/Code/codex/coga/src`:
  identical `IsADirectoryError` on current `main` (`e023d244`). This confirms
  the implementation's baseline finding; no unrelated test repair is included.
- `git diff --check origin/main...HEAD` passes. Confirmed removed helpers
  have no remaining callers; the upstream URL constant and Git URL redaction
  remain available to their other consumers.
- `python -m coga.cli --help` passes. Validation passes with no issues:
  `python -m coga.cli validate --task
  cleanup/add-a-debug-mode-to-init-for-vendoring-from-source --json` in the
  primary checkout, and `env -u SLACK_WEBHOOK_URL python -m coga.cli validate
  --json` in the feature worktree's `example/` (using the respective absolute
  `PYTHONPATH` and the same test venv).
- Review is complete. Feature branch remains clean and committed; the
  `open-pr` step can publish `vendor-pypi-only` using the PR body below.

## PR

`coga init` now vendors `coga==<running version>` from PyPI for every install,
including editable CLI runs. Remove checkout and `COGA_REPO_URL` source
selection and the unused helpers. Pip resolution failures retain their error
details and add a release-only explanation naming the requested version and
the possibility that PyPI is unreachable.

Update the bundled CLI context, development and release docs (including
`COGA_PYTHON`), migration table, and source-resolution/error-message tests.

Test plan: Python 3.12 `python -m pytest` — 2364 passed, one pre-existing failure in `tests/test_notification_messages.py::test_recurring_create_is_silent`, independently reproduced on `main`; `python -m coga.cli validate --task cleanup/add-a-debug-mode-to-init-for-vendoring-from-source --json`, `env -u SLACK_WEBHOOK_URL python -m coga.cli validate --json` in `example/`, `python -m coga.cli --help`, and `git diff --check origin/main...HEAD` pass.
