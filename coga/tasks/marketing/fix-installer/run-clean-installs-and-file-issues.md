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


## Current run — 2026-10-01

- Verified PR #943 merged at 19:19:19Z (merge `76ed1c43d6d2d73abcded0c48776b88e44f209b8`); both harnesses are now available on main.
- Live AWS check at ~22:20Z: host `h-0833c01ac15e645ac` is `available`, with no instances, allocated 2026-09-30T23:28:57Z. Owner explicitly approved reusing it in us-east-1a for a disposable test instance and cleanup. No new dedicated-host allocation is authorized or planned. Release only after 23:28:57Z and AWS host availability.
- Linux PyPI evidence: `.coga/clean-install/installer-pypi-20261001/`; Python 3.11.16, Coga 0.2.0. Install/version/git-init passed; `coga init --user nicktoper` exit 2 because gh is missing. Continuing with gh installed as a test-machine workaround.
- Linux main run started in `installer-main-20261001`; fetched source `581038663170badbcd2aa086149f35ca7d8ac7f7`, wheel 0.3.2, SHA256 `b23f9546d7e1c8f949999ae488ca051dadcdb96b3e819f9c1f64a73c2f59df60`.
- Mac harness does not pin Python 3.11; explicitly select 3.11 for the forthcoming walk. Earlier macOS 0.0.1 result is not evidence of PyPI state on supported Python; investigate interpreter selection before filing.


### Provisioned resources and Linux continuation

- Approved-host instance `i-0d3a252d7bf58d1ec`, public IP `98.92.230.104`, SG `sg-0e7c5aa2030eb3969`, key `coga-clean-install-installer-mac-20261001`, AMI `ami-0531fecfb292182a3`. Ledger: `.coga/clean-install/installer-mac-20261001/resources.env`. Original harness has no reuse switch; `/tmp/coga-reuse-approved-mac.sh` is a temporary operator copy that substitutes the existing host ID for allocate-hosts; all tracked harness files remain untouched. Standard `aws-mac.sh teardown installer-mac-20261001` can clean these resources.
- Owner selected Codex and a `direct/body` first task, avoiding any GitHub repo/account mutation. Codex 0.160.0 installed in Linux main container; owner asked to perform its device login in their terminal.
- Linux main install/init/validate passed with no validation issues. PyPI after installing gh now fails at `MultiplexedPath.joinpath() takes 2 positional arguments but 3 were given` on Python 3.11.16. Existing owner: `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` (done, PR #831), release follow-through: `cleanup/publish-coga-1-0-to-pypi`. No duplicate live code bug. Test-only package-marker workaround applied to continue; any later success is explicitly not an unmodified PyPI pass.


### Findings matrix (in progress, 2026-10-01T23:00Z)

All artifact walks below use Python 3.11.16. Linux is Debian bookworm x86_64, uv 0.12.20; Mac is macOS 27.0 build 26A428 arm64, uv 0.12.21.

| Run / artifact | Step reached / observed result | Existing owner or new draft |
| --- | --- | --- |
| Linux PyPI 0.2.0, `installer-pypi-20261001` | install/version/git init pass; init exit 2 without gh, then exit 1 with resource namespace TypeError. After test-only gh + package-marker workarounds, init/validate pass; old init vendors upstream `8890f9f1b2d73e23bfc467aa5f64185405fea341`. Codex login pending. | `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` (fixed on main), `cleanup/publish-coga-1-0-to-pypi` (release pending); gh requirement also fixed on main |
| Linux main 0.3.2, `installer-main-20261001`, source `581038663170badbcd2aa086149f35ca7d8ac7f7` | install/version/init/validate pass. Codex 0.160.0 installed; owner login pending. | No new main installer failure |
| Mac fresh prerequisite probe, `cltprobe` | git --version exit 1 before Python/artifact resolution; no active GUI for CLT prompt. Headless softwareupdate installs Command Line Tools for Xcode 27.0-27.0. | `marketing/fix-installer/document-the-macos-command-line-tools-prerequisite` (new draft) |
| Mac PyPI 0.2.0, `pypi311` | After CLT and explicit Python selection, install/version/git init pass; init exit 2 without gh. Continuation in progress. | Same PyPI release gap; no duplicate |
| Mac main 0.3.2, `main311`, source `8411a5e3689a0f3f24f5cd45257853eb218cea62` | After CLT and explicit Python selection, install/version/init/validate pass. gh was installed concurrently before init; op remains absent. Codex setup/login pending. | No new main installer failure |

Both main wheel checksums are identical: `b23f9546d7e1c8f949999ae488ca051dadcdb96b3e819f9c1f64a73c2f59df60`; source changes between builds were state only. The Mac default `/usr/bin/python3` is 3.9.6 after CLT. New draft `marketing/fix-installer/pin-python-3-11-in-the-macos-clean-install-harness` owns the missing interpreter pin in the harness; temporary Mac-side script explicitly installs/selects 3.11. Prior 0.0.1 placeholder observation must not be treated as a current supported-Python PyPI result.

README conflict stays with `marketing/readme-top`; its blackboard has the coordination note. Linux venv pip and pipx both resolve 0.2.0 on Python 3.11.16. pipx installed a separate environment but warned that the coga command was already owned by uv (expected when comparing installers in one test home). Plain pip changes the current environment; venv/pipx isolate it; none avoid the released package bug. No alternative is claimed as a separate clean end-to-end run.

Drafts created with `coga create --workflow code/with-review`; initial sandbox sync failed, later network-enabled create synced state successfully. No product files were edited. Workflow selected by owner: `direct/body`, intended read-only inspection task with findings on its blackboard; no PR/repo creation needed. No first task completed yet. AWS instance and host still running/allocated; cleanup remains mandatory.


### Continuation evidence — 2026-10-02T00:10Z

Mac PyPI 0.2.0 reproduced the same Python 3.11 resource namespace TypeError after installing gh. Test-only package marker then allowed init and validation to pass (ok_count 2, no issues); old init vendored upstream `b5e42a2993bf676e220583d3eb53037a7654b447`. It installed four optional managed skills and hit unauthenticated GitHub API rate limits on three; main init installs no skills, so this is additional obsolete-release behavior tracked with `cleanup/publish-coga-1-0-to-pypi`, not a new main bug. Receipt archive: `.coga/clean-install/installer-mac-20261001/walks/pypi311/continuation-evidence.tar`. Linux post-workaround receipts refreshed in `installer-pypi-20261001/container/`.

Codex 0.160.0 installed in both Linux containers and exposed to both Mac users. No owner credentials copied from the host or between machines. An attempted device login in the Linux main container expired after 15 minutes without authentication. No real `coga ticket` interview or first-task `coga launch` has completed. Intended workflow remains `direct/body`; no workflow was actually exercised. Owner was asked whether to retry sign-in or accept authentication as the recorded blocking step and clean up. Do not claim a full first-task pass.

At 00:10Z the host has exceeded its 24-hour minimum. AWS resource cleanup and owner review of the findings remain pending; do not mark done until cleanup is verified and the owner reviews the list.
