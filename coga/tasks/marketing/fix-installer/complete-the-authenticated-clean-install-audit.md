---
title: Complete the authenticated clean-install audit
status: active
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

Complete the authenticated first-task verification left unfinished by marketing/fix-installer/run-clean-installs-and-file-issues. That dated audit closed with authentication blockers on all four runs; it does not prove a completed first task. This ticket owns the readiness rerun, not product fixes or release publication.

1. In an attended session, review README.md, docs/contexts/coga/install/SKILL.md, coga/init, coga/first-task, and the Linux/macOS clean-install runbooks. Coordinate with marketing/readme-top and the existing fix-installer tickets: offer-agent-cli-install-and-setup-at-init, document-the-macos-command-line-tools-prerequisite, and pin-python-3-11-in-the-macos-clean-install-harness. Verify relevant fixes have landed before testing them. Ask the owner if readiness or access is missing; do not silently substitute older evidence.
2. Run fresh Linux and macOS environments on Python 3.11 against both the current unpinned PyPI release and a wheel built from fetched main. Record date, OS, exact Python and Coga versions, commands, source commit where applicable, wheel hashes, and evidence paths. Reuse the existing harnesses; old 0.2.0/0.3.2 receipts and the separate 0.4.0 install/init smoke are historical, not passes for this matrix.
3. For every run, follow prerequisites, uv tool install, coga --version, scratch git init, coga init --user, owner agent login, coga ticket, and coga launch through the first task's actual done state. Use an owner-approved harmless direct/body task unless the owner chooses another workflow. Record which workflow ran and inspect its result and terminal status; a zero exit or successful init alone is insufficient. The owner authenticates in each environment; do not copy personal credentials between machines. Run launch only from an owner terminal or an appropriate separate test session, never recursively inside a supervised agent launch.
4. Record each failure, its exact reproduction and any test-only workaround. Search coga/tasks for an existing owner before filing a distinct draft on code/with-review. Distinguish PyPI-only, main-only and shared failures; patched-package runs do not count as unmodified artifact passes. No product repairs belong in this ticket.
5. Keep the run-to-step-to-finding matrix on the blackboard, preserve receipts, remove disposable environments and verify any approved AWS resources are terminated/released. Obtain owner review, then hand the evidence to marketing/build-the-launch-plan and marketing/readme-top.

Done requires all four runs to complete an authenticated first task, evidence and issue ownership recorded, cleanup verified, and owner review. A recorded login blocker alone does not satisfy this follow-up; ask the attending owner and retain the unfinished work. Finish with coga mark done only after these criteria are met.

Use the owned-Mac route from marketing/fix-installer/affordable-macos-testing-on-owned-macs-and-per-min when available. Any new AWS host allocation needs explicit owner spend approval; prior approval and released resources do not carry over. No release, paid service signup, GitHub repository creation, or other personal-account mutation is authorized by this draft. marketing/publish-coga-1-0-as-the-final-v1-step separately owns verification of the final published 1.0 artifact; this ticket provides pre-release readiness evidence and does not replace that check.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
