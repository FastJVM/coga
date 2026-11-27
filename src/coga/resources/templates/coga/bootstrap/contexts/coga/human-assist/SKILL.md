---
name: coga/human-assist
description: The `coga launch <slug> --agent <type>` assist on an owner-held step — when it is entered, which branch it runs on, what it leaves to the owner, and whom its lifecycle lines credit.
---

# Assist on an owner step

An owner may explicitly run `coga launch <slug> --agent <type>` on an
owner-held step. The override applies to that assist and leaves the workflow
role and ticket agent intact. Lifecycle audit lines name the assisting agent
when an in-session command acts on that ticket.

Launch a PR assist from the base. The workflow's `enter` script takes the
assist to the ticket branch. The agent follows the review skill, pushes any
requested changes to the PR and records ticket notes locally. The owner runs
the final bump to publish the ticket and decides when to merge. See
[Git](../git/SKILL.md).
