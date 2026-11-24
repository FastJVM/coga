---
title: Stop the test suite from deleting files in the real checkout when TMPDIR is
  inside the repo
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: open-branch
    skills: []
    assignee: agent
    requires: branch
    run: git/open-branch
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: push-and-open-pr
    skills: []
    assignee: agent
    requires: pr
    run: git/push-and-open-pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 4 (push-and-open-pr)
agent: claude
---

## Description

During a coga launch on 2026-11-23 (ticket move-the-assembler-trial-evidence-out-of-the-shipp, launch a0eebbce), `.venv/bin/python -m pytest -q` ran with the launch's in-repo `TMPDIR` (`coga/.coga/tmp/<id>/`), so pytest's tmp_path trees lived inside this Git work tree. The run deleted 35 tracked files from the real checkout: coga/coga.toml, coga/context.md, coga/log.md, coga/.gitattributes, coga/.gitignore, coga/workflows/*, docs/contexts/.gitignore and docs/contexts/coga-dev/**. It also removed the untracked, gitignored coga/coga.local.toml and coga/.coga/data/. The tracked files were restored from HEAD; the uncommitted coga/log.md delta and the local config were lost. Rerunning with TMPDIR set to a disposable /tmp directory deleted nothing.

Unconfirmed hypothesis: a test or fixture that creates a repo under tmp_path without its own `git init`, or that resolves the coga root by walking upward, reaches this repo's `.git` or `coga/` and runs a destructive operation (deinit, retire, purge, clean) against it. Find the culprit by bisecting with an in-repo TMPDIR on a throwaway clone, never in a live checkout.

Acceptance: the suite cannot modify files outside its own tmp trees even when TMPDIR is inside the repo. For example, tests could refuse an in-repo basetemp, or fixtures could pin GIT_CEILING_DIRECTORIES and the coga root. Add a regression test or guard. If launch's in-repo TMPDIR is the deeper hazard for tools that walk upward, coga-dev/testing should say how to run pytest under coga launch.

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: open-branch
          run: git/open-branch               # Local-first skill directory containing run.py.
          assignee: agent
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (open-branch)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
A workflow run: selects a script for its step. A sibling ticket.py supplies the default script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

The recurring runner writes delegate on materialized period tickets. It
names the parent template's frozen bootstrap/<name> target.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev records branch:, base:, remote:, reviewed: (the commit OID),
and pr: (the full /pull/ URL). Write one field per line and omit unknown
values. coga/git owns the fields and the workflow that writes them.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->
## Dev

branch: coga/stop-the-test-suite-from-deleting-files-in-the-r-2cc57b
base: fix-read-only-tmp-sweep
remote: origin
reviewed: 679fdbc39142300e8633523c198e5793cab384e5

## Findings

- Culprit, confirmed on a throwaway clone in /tmp: `tests/test_uninstall.py::test_uninstall_outside_repo_errors`
  chdirs to `tmp_path/nowhere` and ran `coga uninstall --yes`. With TMPDIR at
  `<repo>/coga/.coga/tmp/<id>/`, `coga.config.find_repo_root` walks up to the real
  `coga/coga.toml`, and `commands/uninstall.py::_execute_plan` rmtrees `docs/contexts/`
  and then `coga/`. Alone, that test deleted 346 paths on the clone, plus AGENTS.md
  and the `.gitignore` block.
- Owner chose **redirect** over refuse (2026-11-24, attended session).
- The implementation negative control restored the old uninstall test and
  disabled the temp-root guard in a disposable clone of 0cce044efd.
  Both original child-pytest regressions failed as expected.

## Implementation

- `tests/conftest.py::pytest_configure` (tryfirst): when pytest's temp root
  (`PYTEST_DEBUG_TEMPROOT` or `gettempdir()`) sits inside a checkout (see
  `enclosing_checkout`: a `.git` file, a `.git` dir with HEAD, `coga.toml`, or
  `coga/coga.toml`), it sets `PYTEST_DEBUG_TEMPROOT` to `$COGA_SYSTEM_TMPDIR`
  (else /tmp) and prints that in the report header. It raises UsageError
  when an explicit `--basetemp` is inside a checkout or contains the
  checkout under test. An empty `.git` directory is ignored, matching
  `find_checkout_root`.
- Culprit test hardened: it asserts `find_repo_root(empty)` raises, and it
  runs without `--yes`.
- New `tests/test_suite_temproot.py`: a marker unit test, an invariant probe
  (`tmp_path` outside every checkout), and child-pytest regressions (redirect
  plus the culprit test leaving a fake host untouched, and refusal of
  explicit basetemp inside or containing a checkout).
- Docs: `docs/contexts/coga-dev/testing/SKILL.md` temp-root paragraph.
- `_isolate_tmpdir` now also clears
  `COGA_SYSTEM_TMPDIR`. Before this change, three tests
  (`test_launch_gives_script_and_agent_one_purged_tmp_and_durable_data`,
  `test_lock_directory_is_per_user`,
  `test_scope_redirects_temp_keeps_system_tmp_and_purges`) failed whenever
  that variable was inherited, which every `coga launch` exports.
  Reproduced on the base commit c771516f2 (they pass with the variable unset).
- Diff base: the recorded stacked base `fix-read-only-tmp-sweep`
  (c771516f2, one commit above origin/main 7c78e1920). The PR targets that
  branch, so the receipts use it as `base`.

## Peer review

- Codex reproduced a second deletion path at 0cce044efd10b72a7822fae4772c07ec12f27f37.
  Starting pytest in a sibling directory and selecting a test by absolute
  path let `--basetemp` name a parent of the disposable clone.
  Pytest removed the clone and its local-config sentinel before fixture
  setup finished. The guard checks ancestors of the temp path, and
  pytest's own argument check protects the invocation directory and its
  ancestors. The owner approved the correction in the attended session.
  Commit 679fdbc39142300e8633523c198e5793cab384e5 checks the resolved
  basetemp against the checkout that contains the suite's conftest.
  The new child-pytest regression supplies a directory containing a
  disposable checkout as basetemp while invoking pytest from outside it.
- The focused run on the correction passed with 51 passed, 1 skipped
  in 1.25s on Pop!_OS 24.04 LTS, Python 3.12.12. Restoring the old
  conftest in the disposable clone made the new regression fail as
  expected. The child pytest exited 0 instead of refusing with exit 4.
- Independently ran the full suite at the same head on Pop!_OS 24.04 LTS,
  Python 3.12.12. From the disposable clone, with the primary checkout's
  venv interpreter, ran
  `env TERM=dumb TMPDIR="$PWD/coga/.coga/tmp/launch" COGA_SYSTEM_TMPDIR="<scratch>/system" PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 /home/n/Code/coga/.venv/bin/python -m pytest -p no:cacheprovider -q`.
  3202 passed, 29 skipped in 184.34s. Git status including ignored files
  matched before and after. Local config and durable data sentinel contents
  matched, and the in-checkout launch temp directory stayed empty.
- The owner approved setting aside the unrelated draft before publication.
  Only `coga/tasks/manage-better-git-sync.md` was stashed. Its Git blob
  matches the copy in stash 972211334116ecd4db4589dc2dfbd5f290a592f8.

## PR

```yaml
title: Keep the test suite's tmp trees outside every checkout
author: claude
author_evidence: >-
  Claude Opus 5.5 wrote the original implementation in attended Coga
  launch ad83d4aa. Codex wrote the basetemp ancestor correction during
  peer review in launch 908d4af7.
head: 679fdbc39142300e8633523c198e5793cab384e5
base: c771516f294bd47cb32ee26ca3a29d0d701af669
depth: deep
rationale: >-
  The guard runs at session start and changes where pytest creates test
  directories. It protects the checkout from repository discovery by
  tests and from pytest's own explicit basetemp cleanup.
implementation: >-
  The pytest_configure guard redirects an implicit temp root inside a Git
  or Coga checkout via PYTEST_DEBUG_TEMPROOT. It refuses explicit basetemp
  paths inside a checkout or containing the checkout under test. The
  uninstall regression checks that repository discovery fails and declines
  deletion if asked. Per-test isolation clears inherited COGA_SYSTEM_TMPDIR.
deviations: >-
  The owner chose to redirect implicit temp roots and approved the
  basetemp ancestor check found in review. Clearing inherited
  COGA_SYSTEM_TMPDIR also fixes three preexisting test failures under
  coga launch.
limitations: >-
  Verified on Linux. Native Windows and macOS runs are deferred to release.
  On Windows, a redirect requires an outside COGA_SYSTEM_TMPDIR.
  Redirected runs use pytest's normal retention under the system temp root.
files:
  tests/conftest.py: "Detect unsafe temp roots at pytest startup and isolate COGA_SYSTEM_TMPDIR per test."
  tests/test_uninstall.py: "Check that repository discovery fails before invoking uninstall and decline confirmation."
  tests/test_suite_temproot.py: "Exercise checkout markers, implicit redirection, and both explicit basetemp refusals."
  docs/contexts/coga-dev/testing/SKILL.md: "Document the guard and how to run pytest under coga launch."
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 679fdbc39142300e8633523c198e5793cab384e5
  base: c771516f294bd47cb32ee26ca3a29d0d701af669
  detail: >-
    Codex manually reviewed the full diff against the recorded stacked
    base, traced both startup paths and reproduced removal of a disposable
    checkout by pytest's basetemp cleanup. Codex did not participate in
    the original implementation and authored and verified the correction
    during peer review. The regression passed with the correction and
    failed when the original conftest was restored. The full Linux run
    passed with an in-checkout launch temp directory. Approved this head
    after checking both explicit path refusals, automatic redirection,
    and the uninstall test's confirmation path.
checks:
  - command: >-
      env TERM=dumb TMPDIR="$PWD/coga/.coga/tmp/launch"
      COGA_SYSTEM_TMPDIR="<scratch>/system" PYTHONPATH="$PWD/src"
      PYTHONDONTWRITEBYTECODE=1 /home/n/Code/coga/.venv/bin/python -m pytest -p no:cacheprovider -q
    status: passed
    head: 679fdbc39142300e8633523c198e5793cab384e5
    base: c771516f294bd47cb32ee26ca3a29d0d701af669
    detail: >-
      Disposable clone on Pop!_OS 24.04 LTS, Python 3.12.12. 3203 passed,
      29 skipped in 208.74s. Git status including ignored files matched.
      Local config and durable data sentinels matched byte for byte and
      the in-checkout launch TMPDIR stayed empty.
  - command: >-
      env TERM=dumb TMPDIR="$PWD/coga/.coga/tmp/launch"
      COGA_SYSTEM_TMPDIR="<scratch>/system" PYTHONPATH="$PWD/src"
      PYTHONDONTWRITEBYTECODE=1 "<scratch>/venv/bin/python" -m pytest
      -p no:cacheprovider -q tests/test_suite_temproot.py tests/test_uninstall.py
    status: passed
    head: 679fdbc39142300e8633523c198e5793cab384e5
    base: c771516f294bd47cb32ee26ca3a29d0d701af669
    detail: >-
      Pop!_OS 24.04 LTS, Python 3.11.15 in a scratch venv installed with
      uv sync --locked --extra test --python /home/n/.local/bin/python3.11.
      51 passed, 1 skipped in 2.49s. The launch TMPDIR stayed empty.
  - command: "git diff --check refs/remotes/origin/fix-read-only-tmp-sweep...HEAD"
    status: passed
    head: 679fdbc39142300e8633523c198e5793cab384e5
    base: c771516f294bd47cb32ee26ca3a29d0d701af669
    detail: "Exit 0 with no whitespace errors."
```
