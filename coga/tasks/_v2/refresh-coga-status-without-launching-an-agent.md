---
title: Refresh Coga status without launching an agent
status: draft
owner: nicktoper
workflow: null
---

## Description

Make it easy to see current task status without launching an agent or updating the whole code checkout.

Today coga status reads working-tree tickets and warns when the locally cached origin/main has tickets further along. It neither fetches nor refreshes files; coga launch refreshes the checkout, which makes launching feel necessary just to update the status view.

Explore a lightweight way to refresh only Coga state, or read status directly from the fetched control revision without modifying working-tree files. Decide how users explicitly request a network fetch versus viewing the last fetched state. Preserve the default read-only, no-network status contract unless deliberately revisited.

Assess latency rather than assuming refresh is slow: separate network fetch cost from local reads or file updates. If refreshing files, preserve unpublished edits, handle additions and deletions, account for contexts outside coga/, and explain how refreshed files relate to the current branch. Prefer existing Git primitives and avoid requiring an agent launch. The exact command or option and whether to copy files or only change the view remain design decisions.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
