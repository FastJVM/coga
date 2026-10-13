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
step: 2 (peer-review)
agent: claude
---

## Description

The Linux clean-install harness (`scripts/clean-install/`, contract in `coga/testing/clean-install`) stops after `coga init` and `coga validate`; its only attended continuation is `coga-clean-install ticket`. The advertised first-run command, `coga build` (alias for `launch coga-build`), is never exercised, so a release can pass the harness while onboarding is broken (see the done ticket `coga-build-fails-after-init-on-a-github-scaffolded`). The 2026-10-12 run on 0.4.0 (containers `clean-pypi-1011`, `clean-main-1011`) confirmed init leaves `coga-build` active at step 1 (gather-and-spec), but nobody launched it. Add a `coga-clean-install build [--agent NAME]` continuation to `container.sh`, mirroring `ticket`: require init-passed evidence, keep the real TTY, and record the command, exit code, and the resulting ticket status/step in evidence (not the agent conversation or login output). Update the `coga/testing/clean-install` topic and its packaged twin with the attended steps (install and log in an agent inside the container, then run it). Then run it attended on both artifacts and record whether `coga build` reaches and bumps its first step. Each failure found gets its own ticket. Also note in the topic that a retained container may be stopped (for example after a host restart) and needs `docker start` before `docker exec`. Done means the harness and docs change is merged and one attended run's evidence is in the PR.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

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

## PR

```yaml
title: Add an attended coga build continuation to the clean-install harness
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5), attended by the human.
head: 165c9b7a185ddce114fc1e8ad323805874bccc7d
base: 42112951e57fb812d5c89f11bbad3cf7299027b2
depth: skim
rationale: Repository test tooling and docs only; no package code changes. Read the build.txt contract and the attended-run evidence.
implementation: Adds `coga-clean-install build [--agent NAME]` sharing an attended helper with `ticket`; records command, coga-build status/step before and after, non-[system] coga-build log lines, and exit code in evidence/build.txt. Documents the attended build steps and `docker start` for stopped containers.
deviations: Attended runs used COGA_CLEAN_INSTALL_NETWORK=host because the bridge network could not fetch curl inside the container; the main container ran the branch's container.sh via docker cp after the [system]-filter fix.
limitations: macOS walk does not yet pass `build` through. The PyPI container's own build.txt predates the [system] filter; its host copy was filtered.
files:
  scripts/clean-install/container.sh: Add the attended build continuation and shared attended helper.
  tests/test_clean_install_harness.py: Cover build evidence, failure/absent ticket, init requirement, and conversation exclusion.
  docs/contexts/coga/testing/clean-install/SKILL.md: Document attended coga build, its evidence, and docker start for stopped containers.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/testing/clean-install/SKILL.md: Packaged twin of the clean-install topic.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Code review has not run yet; the workflow's later review step owns it.
checks:
  - command: .venv/bin/python -m pytest -q
    status: passed
    head: 165c9b7a185ddce114fc1e8ad323805874bccc7d
    base: 42112951e57fb812d5c89f11bbad3cf7299027b2
    detail: 3603 passed in 316s on a clean tree at head.
  - command: ./scripts/clean-install/run.sh pypi clean-pypi-1013h alice (COGA_CLEAN_INSTALL_NETWORK=host), then attended coga-clean-install build --agent claude
    status: passed
    head: 165c9b7a185ddce114fc1e8ad323805874bccc7d
    base: 42112951e57fb812d5c89f11bbad3cf7299027b2
    detail: Install/init/validate passed with coga 0.4.0; coga-build active step 1 -> step 2 -> done, exit 0. Harness at the first branch commit; build.txt host copy filtered per the second.
  - command: ./scripts/clean-install/run.sh main clean-main-1013h alice (COGA_CLEAN_INSTALL_NETWORK=host), then attended coga-clean-install build --agent claude
    status: passed
    head: 165c9b7a185ddce114fc1e8ad323805874bccc7d
    base: 42112951e57fb812d5c89f11bbad3cf7299027b2
    detail: Wheel from origin/main 42112951e, reports 0.4.0; init/validate passed; first attempt exited by human at step 1; second attempt step 1 -> step 2 -> done, exit 0.
```
