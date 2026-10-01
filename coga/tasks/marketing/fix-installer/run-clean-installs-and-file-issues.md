---
title: Run clean installs and file issues
status: in_progress
owner: nicktoper
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
step: 1 (execute)
agent: claude
---

## Description

In an attended session with the owner present, use the Linux and macOS
clean-install harnesses to walk the documented new-user path end to end, and
file one draft ticket per root cause found. Do not fix anything here.

For each OS (Linux, macOS) × artifact (current PyPI release, wheel from
`main`), on Python 3.11, walk these steps: prerequisites, `uv tool install
coga` (and note where the documented alternatives differ), `coga --version`,
`git init` of a scratch repo, `coga init --user <name>`, `coga ticket "<first
task>"`, the owner's agent login, then `coga launch` of that first task
through to its workflow's `done`. What "done" requires depends on the first
task's workflow. A PR workflow needs a throwaway GitHub repo and an
authenticated `gh` on the machine. Record which workflow was used.

File each issue with `coga create "marketing/fix-installer/<title>" --workflow
code/with-review --description "<repro + expected>"`. Each repro states the
OS, Python version, artifact and version, exact command, observed vs expected
output, and a suggested fix location. Before filing, grep `coga/tasks/` for an
existing owner and link it instead of duplicating. Record whether the issue
reproduces on PyPI, on main, or both, so bugs already fixed on main are not
filed as live. Known findings to file: the Xcode CLT prompt on fresh macOS,
and `README.md`'s two conflicting "Getting Started" blocks (link to
`marketing/readme-top`, which owns the README).

Done means every OS × artifact run is complete (or its blocking step is
recorded), each distinct issue has a filed draft, a findings matrix (run →
step reached → child slugs) is on this blackboard, no AWS resource is left
running, and the owner has reviewed the list. Finish with `coga mark done`.

## Context

Part of the `marketing/fix-installer/` set (V1), which replaced the single
`marketing/fix-installer` ticket that `marketing/build-the-launch-plan`
tracks. It depends on the harness tickets `linux-clean-install-harness` and
`macos-clean-install-harness-on-aws` having merged, so launch it after both.
Windows is `v2/windows-native-clean-install`.

**AWS.** Uses the macOS harness and the owner's AWS SSO profile
(currently `multiply-telemetry`). The owner runs `aws sso login --profile
<profile>` before launch; pass `--profile` (or export `AWS_PROFILE`) in
every `aws` call yourself, since the ticket declares no secret. Ask the
owner before provisioning (the 24-hour `mac2` host minimum) and tear down per
that harness's runbook, recording resource IDs here.

The expected behavior is cited, not attached: `README.md` and the
`coga/install`, `coga/init`, `coga/first-task` and `coga/releasing` topics
(`docs/contexts/coga/<ref>/SKILL.md`). A mismatch with them is a finding. If
something blocks the walk entirely, work around it on the test machine,
record the workaround, and file it. Coordinate commands with
`marketing/readme-top`. `marketing/verify-posthog-telemetry-with-the-live-clean-wheel`
also runs a clean wheel, so reuse its setup if it helps. The parked
`v2/onboarding-v2-first-run-experience-after-removing` assumes `coga build`
was removed, which is obsolete. No product release or personal-account action
beyond the approved AWS test resources is authorized.

<!-- coga:blackboard -->

## Precondition check (2026-09-28)

Ticket says launch after both harness tickets merge. Neither has:
- `linux-clean-install-harness`: `in_progress` at implement; no local or
  remote branch, no PR. `scripts/clean-install/` does not exist on `main`.
- `macos-clean-install-harness-on-aws`: `draft`, never started.
Only the pinned-release gate `scripts/verify-clean-install-container.sh` exists.
Asked the owner how to proceed.
Owner chose to stop and park: relaunch after both harness tickets have merged.
No runs were started, no issues filed, and no AWS resources were created.

---

## Blockers

- [x] [2026-09-29 08:42] [agent:claude] id=20260929T084212 Waiting on marketing/fix-installer/linux-clean-install-harness and macos-clean-install-harness-on-aws to merge (neither has a branch/PR yet); unblock and relaunch after both land.
  resolved: [2026-10-01 11:56] [human:nicktoper] Owner confirms both clean-install harness tickets have merged; clear the dependency blocker and proceed with runbook verification and clean-install testing.

---

## Blocker reminders

- 741767debc86 last_reminded: 2026-09-29 08:50

## Resumed precondition verification — 2026-10-01

Owner confirmed both harnesses merged and authorized clearing the old ask;
`coga unblock` recorded that resolution. Subsequent live GitHub verification
found Linux PR #930 merged at 2026-09-29T21:39:08Z, but macOS PR #943 still
OPEN with no merge commit. Fetched `origin/main`; the local main checkout
has the Linux harness but no `aws-mac.sh` or `macos-walk.sh`. Asked the owner
whether to wait for #943, proceed with Linux only, or park. No new install
runs, issues, or AWS resources created during this session yet.

The macOS harness blackboard records host `h-0833c01ac15e645ac` in
`us-east-1a` still allocated, earliest release 2026-10-01T23:28:57Z
(16:28:57 Pacific). That is prior-session evidence, not a current AWS
verification; keep cleanup visible when resuming the macOS work.
