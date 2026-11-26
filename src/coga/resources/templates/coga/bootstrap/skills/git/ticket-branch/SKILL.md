---
name: git/ticket-branch
description: Launch hook for `git: ticket-branch` workflows; switch to the ticket branch at launch start, commit, push and return at launch exit.
---

`coga launch` runs this skill's `run.py` around every launch of a ticket
whose frozen workflow declares `git: ticket-branch`. Do not invoke it as a
workflow step. Launch passes `enter` before it reads the ticket and `exit`
after the step chain ends, on every path. `coga/git` ("Ticket-branch mode")
owns the contract: branch discovery, the refusals, the exit commit and push,
and how to recover when a phase stops.
