---
title: Harden packaging and first-install before launch
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

Greg's overall takeaway from onboarding: getting a Python project to install the
same way on someone else's machine is hard, and Relay should invest in packaging
and a reliable first-install path before announcing — ideally a scripted /
one-command install. Decide and implement the supported install story (scripted
installer? pinned deps? pipx? published wheel?) so a clean machine reaches a
working `relay` reliably. This is the umbrella for the `install/` group.

## Context

Reported by Greg as a general comment after hitting the specific issues filed
alongside this ticket in `install/`. Pointers: the editable-install path
(CLAUDE.md "Build, Test, and Development Commands"), README Getting Started
(`marketing/readme-and-docs`), and the `pip install relay-os` packaging story
referenced in the `relay/cli` and `relay/architecture` contexts. This is a
scoping/decision ticket; the concrete fixes are its sibling tickets.
