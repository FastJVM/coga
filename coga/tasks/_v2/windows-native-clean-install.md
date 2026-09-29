---
title: Windows native clean install
status: draft
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
step: 1 (implement)
---

## Description

Extend the clean-install work to **native Windows** (not WSL), deferred from
V1. The docs say nothing about Windows today, so first write a documented
Windows baseline in `coga/install` (Python, uv, PATH after `uv tool install`,
git and line endings, PowerShell as the shell, agent CLI support). Then add an
AWS EC2 Windows harness alongside the V1 Linux and macOS ones, walk the same
path on both artifacts (PyPI release and main wheel), and file one ticket per
issue. Done means the baseline and harness are merged and the run's findings
are filed.

## Context

Deferred from the V1 `marketing/fix-installer/` set. Reuse its harness scripts
and the owner's AWS SSO profile (currently `multiply-telemetry`; owner runs
`aws sso login --profile <profile>` before launch, agent passes `--profile`),
and ask the owner before any spend. Cited
topics: `coga/install`, `coga/init`, `coga/first-task`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
