---
title: Document Quick Start for empty and existing repositories
status: draft
owner: nicktoper
workflow: null
---

## Description

Give the README two complete Quick Start paths: a new empty repository eligible for coga build onboarding, and an existing repository where init says coga build is unavailable. Follow current init behavior instead of routing both users into an empty-repository-only command.

Done when each path states its prerequisites and gives valid commands through a first usable task or conversation, explains when build is available, and is checked against current help and representative empty/nonempty fixtures. Keep this change focused on onboarding instructions; a broader README rewrite is outside scope.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
