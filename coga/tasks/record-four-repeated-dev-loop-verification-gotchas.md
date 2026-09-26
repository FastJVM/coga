---
title: Record four repeated dev-loop verification gotchas in the coga codebase context
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
---

## Description

Filed by Dream 2026-W39, Phase 6. Route: `gap` findings with no open owner (whole-corpus search done: hits were incidental rediscoveries in verification notes, not owners). Four repeated dev-loop verification gotchas that tickets keep re-deriving and that no context carries. Design judgment needed on whether they belong as bullets under `coga/testing` (`docs/contexts/coga/testing/SKILL.md` — its commands, environment pitfalls and restricted-sandbox sections now own what the findings below cite as the `coga/contexts/coga/codebase/SKILL.md` "how to run tests and validation" / "two non-obvious traps" bullets), and in what form. Keep the live and packaged twin byte-identical. Note the old codebase context was touched by many open PRs at filing time — base on main after they land.

**F34 — Recurring cleanup test globs the shared system tempdir and fails on stale leftovers**  
(Dream 2026-W39 Phase 2, shard ks-16; class `gap`; target `coga/contexts/coga/codebase/SKILL.md`)

Two independent tickets hit the same full-suite failure and each re-derived the remedy from scratch. `activation-does-not-resolve-step-1-s-assignee-role` (`## Verification`) reports "a subsequent full run ... hit a transient unrelated worktree in the cleanup test's shared `/tmp` glob" and reran under a private `TMPDIR=/tmp/coga-step-one-final-tests`; `packaged-code-workflows-never-name-coga-retire-as` (`## Open PR`) reports `tests/test_recurring.py::test_control_worktree_is_removed_and_unregistered_after_the_run` failing identically on `origin/main` "caused by stale `/tmp/coga-recurring-repo-*` fixture directories left by earlier runs on this machine (the test globs the whole tempdir)" and calls it "a pre-existing test-isolation gap on `main`, not fixed here". The mechanism is verifiable: the test (`tests/test_recurring.py`, `leftovers = list(Path(tempfile.gettempdir()).glob(f"{_CONTROL_WORKTREE_PREFIX}{git_repo.root.name}-*"))`) asserts an empty match over the *machine-wide* tempdir, and every `git_repo` fixture names its root `repo` (`tests/conftest.py`, `root = tmp_path / "repo"`), so one aborted run of any control-worktree test leaves a `coga-recurring-repo-*` directory that breaks this assertion for every later run until someone deletes it by hand. `coga/contexts/coga/codebase/SKILL.md` carries a test-gotcha list (wheel build backend, `PYTHONPATH` absolute, portable fixture scripts, live-vs-packaged comparisons) but nothing about this: grep for `coga-recurring-repo`, `TMPDIR`, or the test name finds nothing in any context or skill. No open ticket owns it (grep of `coga/tasks/` for those terms hits only the two tickets above). Proposed carrier: a bullet in the codebase context's test-gotcha list naming the test, the cause (shared-tempdir glob keyed on the fixture's fixed `repo` name), and the remedy (run the suite with a private `TMPDIR`, or clear `$(python -c 'import tempfile;print(tempfile.gettempdir())')/coga-recurring-repo-*` first) — or a note that the proper fix is to point the test at `tmp_path` instead, if a code fix is preferred over documentation.

**F37 — `codex review`'s own test probe always fails on missing `tomlkit`; nothing says to expect it**  
(Dream 2026-W39 Phase 2, shard ks-15; class `gap`; target `coga/contexts/coga/codebase/SKILL.md`)

At least a dozen tickets' `## Peer review` / verification notes each rediscover the same thing and re-justify it in prose: `codex review --base main` runs its own test attempt under the ambient interpreter, which lacks `tomlkit`, so its probe fails collection (`31 errors` in one record), and the agent then has to explain that the review verdict still stands and rerun the suite through the declared venv. Independent instances: `coga/tasks/exclude-superseded-designs-from-launch-prompts.md:169` ("Its attempted tests could not collect because ambient Python lacks `tomlkit`; the full suite passed separately"), `coga/tasks/preserve-edits-during-released-claim-recovery.md:106` ("Its own test attempt failed collection because its interpreter lacked `tomlkit`"), `coga/tasks/document-how-packaged-contexts-reach-a-repo-and-se.md:185`, `coga/tasks/phase-0-audit-is-complete-per-the-plan-but-still-i.md:111`, `coga/tasks/state-which-branch-is-canonical-for-machine-genera.md:173`, `coga/tasks/narrative-candidates-md-publishes-log-text-the-own.md:153`, plus `title-only-tickets…:183`, `test-recurring-create…:94`, `cleanup/handle-a-bare-slack-webhook…:128`, `ticket-relationships…:229`. `coga/contexts/coga/codebase/SKILL.md` covers two adjacent facts — the `.venv` is the test environment with `tomlkit` (line ~473) and `codex review` fails in-sandbox (line 560) — but neither it, `coga/skills/code/self-qa/SKILL.md` (which names `codex review` at line 38), nor the `code/with-review` peer-review step (`skills: []`) says that the reviewer's embedded test probe is expected to fail on `tomlkit`, that this is not a finding against the branch, and that the agent must run the suite itself via `PYTHONPATH=<checkout>/src <venv>/bin/python -m pytest` and record that command as the evidence. One bullet next to the sandbox item under the "codex review" list in `coga/codebase` (and a pointer from `code/self-qa`) would stop the per-ticket rediscovery. No open ticket found owning this (grep of `coga/tasks/` for `codex review` + `tomlkit` among non-done/canceled tickets).

**F38 — The wheel-building test also needs `pip` in the venv, not only `hatchling` — a repeated pre-existing failure nobody recorded**  
(Dream 2026-W39 Phase 2, shard ks-20; class `gap`; target `coga/contexts/coga/codebase/SKILL.md`)

`coga/contexts/coga/codebase/SKILL.md` (the "two non-obvious traps" bullets around line 415, twin in `src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md`) says `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries` shells out to `python -m pip wheel --no-build-isolation --no-deps .` and fails loud when `hatchling` is missing from the venv. It never says the same about `pip` itself, and that is the failure agents actually keep hitting: a venv created with `uv venv` (or `python -m venv --without-pip`) ships no `pip` module, so the subprocess dies with `No module named pip` before hatchling is even consulted. At least five independent tickets re-diagnosed this from scratch and each spent a verification paragraph proving it "fails identically on main": `no-context-records-the-ci-posture-publish-only-rel` (blackboard `## Verification`: "the project `.venv` has no pip ... Pre-existing and unrelated"; peer review repaired it with `python -m ensurepip` then `pip install 'hatchling>=1.18'`), `automerge/fix-let-a-lot-of-open-craps` (`## Implement handoff`: tests ran from "`uv venv .venv` + `uv pip install -e ".[test]"` (plus `pip`, which the wheel test needs)"), `launch-activates-before-preflight` (line ~401: "`No module named pip` in the venv"), `megalaunch-activates-picks-before-preflight` (line ~268, same), and `retire-never-removes-a-worktree-that-ran-the-tests` (line ~371: "`ensurepip` is available but pip is not installed"). No open ticket owns this (grep of `coga/tasks/` for `No module named pip` / `ensurepip` / `uv venv` hits only tickets whose subject is something else). Proposed carrier: extend the existing "The only wheel-building test needs a build backend in the venv" bullet in `coga/codebase` to say the test also needs `pip` importable in the interpreter running pytest, that `uv venv` does not install one, and that the one-line repair is `python -m ensurepip` (or `uv pip install pip`) before `pip install -e ".[test]"`; `docs/development.md` line ~20 could add the same one-liner to its install block so a `uv`-created venv gets pip. Keep both context copies byte-identical.

**F39 — Validating `example/coga` needs `env -u SLACK_WEBHOOK_URL`; the daily-commands list does not say so**  
(Dream 2026-W39 Phase 2, shard ks-15, ks-28 (merged); class `gap`; target `coga/contexts/coga/codebase/SKILL.md`)

Ten tickets (grep `env -u SLACK_WEBHOOK_URL` across `coga/tasks/`) each rediscover that running `coga validate --json` against the seeded `example/coga` fixture fails when the operator's shell exports a bare `SLACK_WEBHOOK_URL`, and each writes the same workaround into its verification notes: `coga/tasks/megalaunch-only-shows-one-page.md` ("Needs `env -u SLACK_WEBHOOK_URL` — a bare value in this shell's env trips an unrelated config check"), `coga/tasks/exclude-superseded-designs-from-launch-prompts.md` ("The fixture disables notifications; unset the inherited legacy bare webhook variable rather than editing config"), `coga/tasks/reject-context-artifacts-that-escape-the-checkout.md` ("Unsetting the inherited bare webhook avoids the existing removed-environment-key guard"), plus `move-cogacontext-to-roodoc…`, `simplify-ticket-format`, `title-only-tickets…`, `the-v2-parking-area-premise-check…`, `activation-does-not-resolve-step-1…`, `validate-that-committed-skill-scripts…`, `cleanup/add-a-debug-mode-to-init…`. The guard itself is owned and explained by `coga/contexts/coga/sync/SKILL.md:414-416` (a bare exported `SLACK_WEBHOOK_URL` fails config load until `[notification.slack].webhook = "env:SLACK_WEBHOOK_URL"` is declared), so this is not a stale claim — but the operational consequence for the test fixture is absent from `coga/contexts/coga/codebase/SKILL.md`'s "Daily commands" (line ~436 lists `coga validate --json` with no mention of the env), which is where an implementing agent looks. One sentence there — "from `example/coga`, run `env -u SLACK_WEBHOOK_URL coga validate --json`; the fixture disables notifications and the config-load guard rejects a bare inherited webhook variable; do not edit the fixture's config to satisfy it" — would end the repeat. No open ticket owns it (all matching tickets are done or are the two in-progress fix tickets above, neither of which targets the docs).

_Merged duplicate from ks-28 ("`coga validate` on `example/` needs `env -u SLACK_WEBHOOK_URL` on dev shells — a repeated verification gotcha with no carrier"):_ At least ten tickets record the same verification struggle: running `coga validate --json` in `example/` fails on a dev shell that exports a bare `SLACK_WEBHOOK_URL`, because the seeded fixture's `webhook = "env:SLACK_WEBHOOK_URL"` trips the bare-env guard described in `coga/contexts/coga/sync/SKILL.md` (~line 414-416), and every ticket rediscovers the `env -u SLACK_WEBHOOK_URL coga validate --json` workaround by hand. Independent evidence: `coga/tasks/cleanup/add-a-debug-mode-to-init-for-vendoring-from-source.md` (Verification: "needs `env -u SLACK_WEBHOOK_URL` — a stray var in this shell trips the bare-webhook check"), `coga/tasks/megalaunch-only-shows-one-page.md:206` ("a bare value in this shell's env trips an ..."), `coga/tasks/simplify-ticket-format.md:765,942,1153`, plus `title-only-tickets-have-no-convention-and-no-valid`, `the-v2-parking-area-premise-check-has-four-holes`, `activation-does-not-resolve-step-1-s-assignee-role`, `reject-context-artifacts-that-escape-the-checkout`, `exclude-superseded-designs-from-launch-prompts`, `validate-that-committed-skill-scripts-with-a-sheba`, `move-cogacontext-to-roodoc-so-its-easier-for-human`. Neither `coga/contexts/coga/codebase/SKILL.md` nor `docs/development.md` mentions `SLACK_WEBHOOK_URL` at all (grep confirms), so the smoke-path instruction in CLAUDE.md ("`coga validate --json` validates repo/task structure") silently fails for anyone with the variable exported. Proposed carrier: one sentence in the codebase context's test/verification guidance (the section that owns "`coga validate --json` on `example/`") naming the guard and the `env -u` prefix, or a fixture change so `example/coga.toml` does not resolve the operator's real env var. No open ticket owns this: every ticket mentioning the variable is `done`, `in_progress` on unrelated work, or the unrelated draft `v2/let-notification-webhooks-resolve-1password-refere`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/900
branch: record-dev-loop-verification-gotchas

Plan (agreed with owner 2026-09-25): F34 fixed in the test itself (private
`tempfile.tempdir` under `tmp_path`) rather than documented; F37/F38/F39 as
bullets in `coga/testing` (live + packaged twin), plus a pointer from
`code/self-qa` for F37. The findings' `coga/codebase` targets moved to
`coga/testing` before implementation.

## Implement handoff

Commit `08c589590` on `record-dev-loop-verification-gotchas` (pushed, based on
`b8c297b4f`).

- **F34 (code fix):** `tests/test_recurring.py`
  `test_control_worktree_is_removed_and_unregistered_after_the_run` now
  monkeypatches `tempfile.tempdir` to a private dir under `tmp_path`.
  `recurring_runner` creates the control worktree with `tempfile.mkdtemp` and
  checks ownership with `tempfile.gettempdir()`, so both follow the patch.
  Regression evidence: with a planted `/tmp/coga-recurring-repo-stale.*` dir,
  the unchanged test failed; the patched test passed.
- **F37:** a new bullet under "Restricted sandboxes" in `coga/testing` says
  `codex review`'s own test probe is expected to fail collection. It is not a
  finding; run the suite yourself and record that command. `code/self-qa`
  (live + packaged) points to it.
- **F38:** the Commands section of `coga/testing` covers pip-less `uv venv`
  (`python -m ensurepip` / `uv pip install pip`); the `hatchling` bullet says
  the wheel tests shell out to `python -m pip`.
- **F39:** the Commands section of `coga/testing` says to validate
  `example/coga` with `env -u SLACK_WEBHOOK_URL coga validate --json` and not
  to edit the fixture's config. I reproduced the guard failure first.
- The live and packaged copies of both `coga/testing` and `code/self-qa` are
  byte-identical (`tests/test_packaging.py` green).
- I left `docs/development.md` untouched on purpose: `coga/testing` owns
  these facts.

Verification: `PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q` ->
`2945 passed`.

Housekeeping: at start, the launch's own `launched` line in `coga/log.md` was
unpublished. The owner approved it, and the pre-branch state sweep published it.


## Peer review

`codex review --base main` returned successfully with no actionable findings.
Its targeted verification used the checkout venv successfully:
`PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_recurring.py::test_control_worktree_is_removed_and_unregistered_after_the_run tests/test_packaging.py -q`
-> `24 passed`. No review fixes were needed. The change touches documentation
and test isolation only; no terminal or rendered interaction needs manual QA.

Fetched `origin/main` and rebased unconditionally onto `5af4b2576`; no conflicts.
Post-rebase verification:
- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q` -> `2945 passed`.
- From `example/coga`:
  `env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json`
  -> `ok_count: 4`, no issues.
- `git diff --check` -> clean.

Rebased commit `f5a52825b` was pushed with `--force-with-lease`; checkout
returned to clean `main` before writing this handoff.

## PR

Isolate the recurring cleanup test's temporary directory so stale worktrees
from earlier runs cannot cause false failures. Record the reviewer dependency,
pip-less venv, and inherited Slack webhook verification gotchas in
`coga/testing`, with a pointer from `code/self-qa`; keep both packaged twins
byte-identical.

Test plan: `PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q` -> 2945 passed;
seeded fixture validation with `env -u SLACK_WEBHOOK_URL` -> 4 OK, no issues;
`git diff --check` clean.
