---
title: Diagnose clean-install failures on Linux, macOS and Windows
status: draft
owner: nicktoper
workflow: code/with-review
secrets:
  - AWS_PROFILE: env:AWS_PROFILE
---

## Description

Find every issue that stops a new user on a fresh machine from going from
nothing to one completed Coga task, on Linux, macOS and Windows. For each
issue, file its own draft ticket under `coga/tasks/v0/debug/installer/`.
This ticket only diagnoses and files. The fixes are implemented later through
those child tickets, not here.

To do that, build and commit a reusable clean-environment harness, so each
child ticket can later prove its fix with the same run:

- **Linux:** a Docker image with a fresh non-root user and nothing
  preinstalled beyond what the docs list as prerequisites.
- **macOS and Windows:** real AWS EC2 machines (EC2 Mac on a `mac2`
  dedicated host, and a Windows instance), provisioned and torn down by
  committed scripts.

On each OS, walk the documented path exactly as a new user would:
prerequisites, `uv tool install coga` (and the documented alternatives), `coga
--version`, `git init` of a scratch repo, `coga init --user <name>`,
`coga ticket "<first task>"`, and a launched first task through to `done`.
Run it against **Python 3.11** (the declared floor) and against **two
artifacts**: the current PyPI release and a wheel built from `main` with `uv
build`. Record which artifact each issue reproduces on, so bugs already fixed
on main are not refiled as live.

Done means:

- the harness (Docker script, AWS provision/run/teardown scripts, and a short
  runbook) is merged via PR;
- all three OSes have been run through the full path on both artifacts;
- every distinct issue found has a draft ticket in
  `coga/tasks/v0/debug/installer/` with a reproduction (OS, Python version,
  artifact and version, exact command, observed vs expected output) and a
  suggested fix location;
- a findings summary on this ticket's blackboard lists each OS × artifact run,
  the step it reached, and the child ticket slugs;
- no AWS resource is left running.

## Context

**AWS.** Credentials come from an SSO profile named by `AWS_PROFILE`
(declared in `secrets:`). The owner runs `aws sso login --profile <p>` before
launch. Confirm with the owner before creating any EC2 instance or dedicated
host, because it costs money: a `mac2.metal` dedicated host has a 24-hour
minimum allocation (roughly $25–30), and it can only be released after 24
hours. Pick the region with the owner, since Mac host availability varies by
region. Tear down every instance, release the host once it is allowed, and
record the resource IDs on the blackboard so nothing is orphaned. Do not use
the AWS root credentials in 1Password. The agent part of the first task needs
an authenticated Claude Code or Codex on each machine; the owner logs in
interactively (over SSH, or RDP/VNC for the GUI flows) when the run reaches
that step.

**Filing child tickets.** Use `coga create "v0/debug/installer/<title>"
--workflow code/with-review --description "<repro + expected>"` (a path prefix
in the title places the ticket in that directory). File one ticket per root
cause, not per symptom. Before filing, grep `coga/tasks/` for an existing
owner (for example, earlier Python-3.11 floor or init tickets) and link it
instead of duplicating.

**Out of scope.** A GitHub Actions install-smoke matrix is deferred to V2.
Do not create a new installer tier or onboarding framework. Do not fix issues
here; if something blocks the walk entirely, work around it on the test
machine, record the workaround, and file it. No product release or
personal-account action beyond the approved AWS test resources is authorized.

**Read first.** The documented path lives in `README.md` (Getting Started)
and in the `coga/install`, `coga/init`, `coga/first-task` and
`coga/releasing` topics (`docs/contexts/coga/<ref>/SKILL.md`). These are
cited, not attached: they are the expected behavior, and any mismatch with
them is an issue to file. `coga/install` states the prerequisites: Python
3.11+ (required for `tomllib`), git (the only tool `coga init` enforces), an
authenticated agent CLI for `launch`/`ticket`/`build`, `gh` recommended, and
`op` only for `op://` secrets. For where to commit the harness, cite
`coga/codebase`, `coga/testing` and `coga/packaging`. The harness is repo
dev tooling, not package code, so it stays out of `src/coga/`
(microkernel rule, `coga/extension-model`).

**Related.** This is the V1 prerequisite owned by
`marketing/build-the-launch-plan`. Coordinate the commands with
`marketing/readme-top`. `marketing/verify-posthog-telemetry-with-the-live-clean-wheel`
also runs a clean wheel, so reuse its setup if it helps. PostHog stays in
`marketing/add-telemetry`. The parked
`v2/onboarding-v2-first-run-experience-after-removing` ticket assumes `coga
build` was removed, which is obsolete, and does not govern this.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
