---
name: coga/human-assist
description: The `coga launch <slug> --agent <type>` assist on an owner-held step — when it is entered, which branch it runs on, what it leaves to the owner, and whom its lifecycle lines credit.
---

# Assist on an owner step

An owner may explicitly run `coga launch <slug> --agent <type>` on an
owner-held step. The override applies to that assist and leaves the workflow
role and ticket agent intact. Lifecycle audit lines name the assisting agent
when an in-session command acts on that ticket.

Switch to the ticket branch before launching a PR assist. The agent follows
the review skill, commits and pushes any requested changes and ticket notes,
and leaves the final bump and merge to the owner. See [Git](../git/SKILL.md).
