---
slug: relay-forces-https
title: relay-forces-https
status: done
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

SSH-auth users are forced through HTTPS — Relay hardcodes the HTTPS upstream URL and HTTPS-leaning skill imports, so they need a token despite working SSH keys.
Make the git transport respect the user's setup: allow SSH URLs or auto-detect.
Touchpoints: RELAY_REPO_URL/clone_upstream in commands/update.py, source normalization in skill_manager.py

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: respect-git-transport
worktree: /tmp/relay-respect-git-transport
commit: 821b06e
pr: https://github.com/FastJVM/relay/pull/404

## Implementation Notes
- Plan: keep source edits isolated in the feature worktree; make Relay's updater prefer a configured or matching local SSH remote before falling back to HTTPS, and make skill source parsing recognize SSH GitHub forms without rewriting user input.
- Implemented in the feature worktree:
  - `src/relay/commands/update.py` now resolves the upstream URL from `RELAY_REPO_URL`, a matching local `upstream`/`origin` remote, an existing pin, then the HTTPS default.
  - `src/relay/commands/init.py` threads the resolved URL through clone/pin/update-all and uses it in the pip upgrade hint.
  - `src/relay/github_source.py` centralizes GitHub owner/repo parsing for HTTPS and SSH source forms; `src/relay/skill_manager.py` uses it for multi-skill guidance.
- Committed as `e81faf8 Respect SSH git transport`.
- Verification:
  - PASS: `PYTHONPATH=/tmp/relay-respect-git-transport/src python -m pytest tests/test_init.py tests/test_skill_manager.py` (`125 passed`).
  - PASS: `git diff --check`.
  - PASS with existing warning: `PYTHONPATH=/home/n/Code/codex/relay/src python -m relay.cli validate --task relay-forces-https --json` (`ok_count: 1`; warning: `assignee 'nick'` is not configured in this checkout).
  - FULL SUITE BASELINE NOISE: `PYTHONPATH=/tmp/relay-respect-git-transport/src python -m pytest` reported `818 passed, 1 skipped, 2 failed`; the only failures are in `tests/test_autoclose_sweep.py` because `main` already has `relay-os/recurring/autoclose-merged/blackboard.md` with `last_serviced_period: 2026-06-17` while the packaged copy does not; this diff does not touch those files.

## Peer Review
- Native review: `codex review --base main` initially failed in the sandbox with `failed to initialize in-process app-server client: Read-only file system`; reran outside the sandbox successfully.
- Must-fix findings:
  - P1: credential-bearing repo URLs could be printed during clone and persisted in `.relay/RELAY_PIN`.
  - P2: auto-detection could choose HTTPS `upstream` before an available SSH `origin`.
- Applied in feature worktree commit `821b06e peer-review: apply review findings`:
  - Added credential-safe git source rendering and SSH source detection in `src/relay/github_source.py`.
  - `clone_upstream`, `write_pin`, and the pip upgrade hint now redact credential userinfo before display or durable persistence while preserving the original URL for the actual `git clone`.
  - Matching remotes are collected first, then SSH remotes are preferred over HTTPS matches.
  - Added regression tests for redacted clone output, redacted pin writes, redacted pip hints, and SSH-over-HTTPS remote preference.
- Verification after commit:
  - PASS: `PYTHONPATH=/tmp/relay-respect-git-transport/src python -m pytest tests/test_init.py tests/test_skill_manager.py` (`129 passed`).
  - PASS: `git diff --check HEAD~1..HEAD`.
  - FULL SUITE BASELINE NOISE: `PYTHONPATH=/tmp/relay-respect-git-transport/src python -m pytest` reported `822 passed, 1 skipped, 2 failed`; failures remain the known `tests/test_autoclose_sweep.py` live-vs-packaged autoclose blackboard mismatch (`last_serviced_period: 2026-06-17`) and are outside this diff.
