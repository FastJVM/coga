---
slug: write-coga-secrets-management-service-account-cont
title: Write coga secrets-management + service-account context
status: draft
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

Write a coga context (`coga/contexts/coga/`) — and/or a README section —
documenting the secrets-management pattern for headless jobs: how the
`coga-recurring-sa` 1Password service account + `coga-recurring` vault work, and
the recipe for adding a new headless secret and reffing it from a ticket.

Should cover:
- The SA / vault model — `coga-recurring-sa` (identity) reads the
  `coga-recurring` vault (container); why the names are distinct
  (`op://<vault>/<item>/<field>` — the vault, not the SA, routes the lookup).
- Least-privilege scoping (SA read-only to one vault; leaked token = one-vault
  blast radius).
- Where the SA token lives (root/admin vault, human-delivered into the cron env;
  never an `op://` ref, never in the vault it reads).
- The add-a-headless-secret recipe: create the vault item, declare the inline
  `op://coga-recurring/<item>/<field>` ref on the *consuming* ticket, verify
  with a clean-env `coga secret get`.

Companion to [[op-service-account]], which sets up the SA/vault infra itself.
Note: op-service-account's blackboard originally folded these docs into *its*
PR — decide whether the docs live here or there and update whichever ticket
loses them.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
