---
title: Add an attended coga build step to the clean-install harness
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
step: 4 (review)
agent: claude
---

## Description

The Linux clean-install harness (`scripts/clean-install/`, contract in `coga/testing/clean-install`) stops after `coga init` and `coga validate`; its only attended continuation is `coga-clean-install ticket`. The advertised first-run command, `coga build` (alias for `launch coga-build`), is never exercised, so a release can pass the harness while onboarding is broken (see the done ticket `coga-build-fails-after-init-on-a-github-scaffolded`). The 2026-10-12 run on 0.4.0 (containers `clean-pypi-1011`, `clean-main-1011`) confirmed init leaves `coga-build` active at step 1 (gather-and-spec), but nobody launched it. Add a `coga-clean-install build [--agent NAME]` continuation to `container.sh`, mirroring `ticket`: require init-passed evidence, keep the real TTY, and record the command, exit code, and the resulting ticket status/step in evidence (not the agent conversation or login output). Update the `coga/testing/clean-install` topic and its packaged twin with the attended steps (install and log in an agent inside the container, then run it). Then run it attended on both artifacts and record whether `coga build` reaches and bumps its first step. Each failure found gets its own ticket. Also note in the topic that a retained container may be stopped (for example after a host restart) and needs `docker start` before `docker exec`. Done means the harness and docs change is merged and one attended run's evidence is in the PR.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/1012
branch: clean-install-build

Plan (agreed with the human): `coga-clean-install build [--agent NAME]` mirroring
`ticket` via a shared attended helper; `evidence/build.txt` records command,
coga-build `status:`/`step:` before and after (or absent), exit code, and the
scratch repo's `coga/log.md` lines for coga-build. Tests in
`tests/test_clean_install_harness.py`; topic + packaged twin updated, including
the `docker start` note. Prior 1011 containers no longer exist; the attended
run uses fresh containers.

## Implement handoff

Commits on `clean-install-build` (see `git log origin/main..clean-install-build`):
(harness + tests + topic/twin; then a fix dropping `[system]` usage lines from
`build.txt`, because they quote the conversation's request/outcome — found in
the PyPI run's first evidence).

Decisions:
- `ticket` and `build` share one `attended` helper in `container.sh`; `build`
  additionally records `before_*`/`after_*` frontmatter `status`/`step`
  (`*_ticket=absent` if gone; a `done` ticket has no `step:`) and the scratch
  repo's `[coga-build]` log lines minus `[system]`. `build.txt` appends, so a
  re-run keeps earlier attempts.
- frontmatter read uses portable `sed -n -e` (no GNU `\|`), since the macOS
  walk shares `container.sh`.
- Topic documents `docker start` for a stopped retained container and running
  `build` before `ticket`.

Attended run (2026-10-13), both on `COGA_CLEAN_INSTALL_NETWORK=host`, image
`sha256:149d59953fc7f50680cf914373e142951e99cbaeae3471e7a582de8e8cf694bf`:
- First pair `clean-pypi-1013`/`clean-main-1013` (bridge) passed init but
  in-container `apt-get` for curl timed out (known, documented bridge issue);
  removed. Host receipts kept in `.coga/clean-install/`.
- `clean-pypi-1013h` (PyPI coga 0.4.0): human ran `build`; active step 1 →
  bumped to step 2 → done (8 starter drafts), exit 0. Host copy of build.txt
  filtered of `[system]` lines after the fix (container copy predates it).
- `clean-main-1013h` (wheel from origin/main 42112951e57fb812d5c89f11bbad3cf7299027b2,
  reports 0.4.0; harness script docker-cp'd from the branch fix): attempt 1
  the human exited at the first question (in_progress, step 1, exit 0 — not a
  bug); attempt 2 driven by the agent via tmux: step 1 bumped → step 2 → done
  (7 drafts), exit 0. Claude login was supplied by the human.
- Failures found in Coga: none, so no new tickets. Note: init's scratch repo
  has no `origin`, so `coga build` commits state on local main only (warning,
  expected for the harness).

Follow-up (not done here): `scripts/clean-install/macos-walk.sh` passes only
`ticket` through to `container.sh`; add `build` there and to
`coga/testing/clean-install/macos-aws` if the Mac walk should cover it.

Next step: PR description must include the per-artifact evidence above
(command, image ID, version, main SHA, init outcome, build outcome). Containers
`clean-pypi-1013h`, `clean-main-1013h` are retained; remove with
`docker rm -f` when done.

## Peer review

2026-10-14, Claude Code (claude-opus-5-5) session. Same agent family as the
implementer (Claude), so this is **not independent** review. Two earlier
Codex peer-review sessions (2026-10-13) never got a verdict: the nested
`codex review` failed on a masked `/tmp/codex-daemon-1000` runtime dir. Their
receipts are superseded by this session.

- Start check: clean `main`. Rebased the branch onto main `64aba962d` before review.
- `/code-review` (default effort) **returned**, run 1: it covered only commit
  08b32137b. Must-fix: the `grep -vF '] [system] '` filter dropped every system
  lifecycle line (blocked/started), which contradicted the topic's "usage records".
  The test fixture also lacked the real `v1` marker. Fixed in df5110fd3: anchor the
  match on the ref field, drop only `[system] {` JSON usage records, and update the
  fixtures and tests (a system lifecycle line is kept; a peer line mentioning
  `[coga-build]` is excluded).
- `/code-review` (default effort) **returned**, run 2: full branch vs main at
  head df5110fd3. Must-fix:
  - A bare `build` recorded `+ coga build ''`.
  - The `log:` section re-appended the whole history on every re-run.

  Both fixed in 0c80a081a (now 3c3a239): the log offset is taken before the launch
  and only lines appended since then are kept. The tests now link `tail` and `wc`,
  which the Debian image has. Documented in the topic and its twin rather than
  filtered: agent and human audit lines (a bump message, a block reason, an unblock
  answer) may name the operator's idea, so read `build.txt` before quoting it.

  Skipped as nits: directory-form ticket path, the malformed-frontmatter range in
  `sed`, `|| true` masking grep exit 2, reuse of `coga show`, and the `case`
  dispatch refactor.
- The fix commits were written by this session and were **not re-reviewed** by a tool.
- Terminal surface: `docker cp` the final script into the retained
  `clean-main-1013h` container, then
  `script -qec "docker exec -it clean-main-1013h bash -lc 'stty rows 24 cols 80; bash /tmp/container-review.sh build'"`.
  The TTY was preserved and the already-done refusal was readable. The record read
  `+ coga build`, `before_status=done`, `after_status=done`, an empty `log:`
  (nothing appended by this launch) and `build_exit_code=2`. One more record was
  appended to that container's `build.txt`.
- Freshened: main moved during review (PR #1004, which touched the macos-aws
  topic and test_packaging, not the changed lines). Final rebase onto
  `d9c9b7c66` was clean. Pushed with `--force-with-lease`; remote head is
  `3c3a23955e64d5cdb9be4544fc6c5d4b123b8f13`.
- `.venv/bin/python -m pytest -q` on the final head 3c3a239: 3599 passed in 335s.
  `git diff --check` and the twin comparison passed.
- End: checkout back on a clean `main`. Containers `clean-pypi-1013h` and
  `clean-main-1013h` are still retained; remove them with `docker rm -f` after merge.

## PR

```yaml
title: Add an attended coga build continuation to the clean-install harness
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5), attended by the human; peer-review fix commits by a Claude Code (claude-opus-5-5) session.
head: 3c3a23955e64d5cdb9be4544fc6c5d4b123b8f13
base: d9c9b7c66045726f60f9abd159b7a2f6cf929f95
depth: deep
rationale: Shell harness that records attended evidence; the review was same-family, not independent, and the final fix commit was not tool-reviewed. A human should read container.sh's evidence filtering and the attended-run receipts.
implementation: Adds `coga-clean-install build [--agent NAME]`, which shares an attended helper with `ticket`. Records the command, coga-build status/step before and after, the coga-build audit-log lines appended during the launch (minus [system] JSON usage records), and the exit code in evidence/build.txt. Documents the attended build steps, which audit lines are kept, and `docker start` for stopped containers.
deviations: Attended runs used COGA_CLEAN_INSTALL_NETWORK=host because the bridge network could not fetch curl inside the container. The main container ran the branch's container.sh via docker cp after the [system]-filter fix.
limitations: The macOS walk does not yet pass `build` through. The attended runs predate the peer-review filter and log-offset fixes; the PyPI container's own build.txt predates the [system] filter, and its host copy was filtered by hand. Agent/human audit lines may quote the operator's idea (documented).
files:
  scripts/clean-install/container.sh: Add the attended build continuation, shared attended helper, and per-launch log evidence.
  tests/test_clean_install_harness.py: Cover build evidence, the bare-build record, failure and absent ticket, the init requirement, and log filtering (usage records out, lifecycle lines kept, peer mentions out).
  docs/contexts/coga/testing/clean-install/SKILL.md: Document attended coga build, its evidence, and docker start for stopped containers.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/testing/clean-install/SKILL.md: Packaged twin of the clean-install topic.
review:
  reviewer: claude
  kind: self
  status: failed
  head: df5110fd343473f2ace5f9893886a2ba5f743f24
  base: 64aba962d531cb276b2f29a70f676d18649a5323
  detail: Claude Code /code-review (claude-opus-5-5), default effort. Same agent family as the implementer, so not independent. Run 1 covered 08b32137b only. Run 2 covered the full branch vs main at head df5110fd3. The review returned must-fix findings (status failed at that head). They were applied in df5110fd3 (run 1) and 0c80a081a (run 2); 0c80a081a was not re-reviewed. Final head 3c3a239 differs from 0c80a081a only by a clean rebase.
checks:
  - command: .venv/bin/python -m pytest -q
    status: passed
    head: 3c3a23955e64d5cdb9be4544fc6c5d4b123b8f13
    base: d9c9b7c66045726f60f9abd159b7a2f6cf929f95
    detail: 3599 passed in 335s.
  - command: script -qec "docker exec -it clean-main-1013h bash -lc 'stty rows 24 cols 80; bash /tmp/container-review.sh build'" (final container.sh via docker cp)
    status: passed
    head: 0c80a081a1b30cd89c6033fcda6a548e6f6a0abc
    base: 64aba962d531cb276b2f29a70f676d18649a5323
    detail: Real PTY on a completed ticket; the record showed `+ coga build`, before/after done, an empty per-launch log, and exit 2 propagated.
  - command: ./scripts/clean-install/run.sh pypi clean-pypi-1013h alice (COGA_CLEAN_INSTALL_NETWORK=host), then attended coga-clean-install build --agent claude
    status: passed
    head: 165c9b7a185ddce114fc1e8ad323805874bccc7d
    base: 42112951e57fb812d5c89f11bbad3cf7299027b2
    detail: Image sha256:149d59953fc7f50680cf914373e142951e99cbaeae3471e7a582de8e8cf694bf. Install/init/validate passed with coga 0.4.0; coga-build went active step 1 -> step 2 -> done (8 starter drafts), exit 0. Harness at the first branch commit.
  - command: ./scripts/clean-install/run.sh main clean-main-1013h alice (COGA_CLEAN_INSTALL_NETWORK=host), then attended coga-clean-install build --agent claude
    status: passed
    head: 165c9b7a185ddce114fc1e8ad323805874bccc7d
    base: 42112951e57fb812d5c89f11bbad3cf7299027b2
    detail: Same image. Wheel from origin/main 42112951e, reports 0.4.0; init/validate passed. Attempt 1 the human exited at step 1; attempt 2 went step 1 -> step 2 -> done (7 drafts), exit 0. No Coga failures found, so no new tickets.
```

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `marketing/fix-installer/add-an-attended-coga-build-step-to-the-clean-insta`
Recorded: 2026-10-14T19:12:43+00:00

    [open-pr] origin/main advanced only through non-overlapping Coga task/log state; branch is safe to publish
    PR presentation: review kind must be independent, self, or none.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `marketing/fix-installer/add-an-attended-coga-build-step-to-the-clean-insta`
Recorded: 2026-10-14T19:12:51+00:00

    [open-pr] origin/main advanced only through non-overlapping Coga task/log state; branch is safe to publish
    PR presentation: reviewer must be a compact identity.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `marketing/fix-installer/add-an-attended-coga-build-step-to-the-clean-insta`
Recorded: 2026-10-14T19:13:01+00:00

    [open-pr] origin/main advanced only through non-overlapping Coga task/log state; branch is safe to publish
    PR presentation: invalid status 'returned'.
