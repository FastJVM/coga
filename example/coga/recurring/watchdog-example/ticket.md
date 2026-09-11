---
schedule: "0 9 * * 1"
title: Watchdog recovery example
owner: marc
agent: claude
workflow: direct/body
---

## Description

Demonstrate recovery of an interrupted recurring run. Preserve its findings
and finish the recorded step when explicitly resumed.

<!-- coga:blackboard -->

This example has a watchdog-paused period. An ordinary scan reports it as an
unresolved failure; `coga launch recurring/watchdog-example` resumes it.
