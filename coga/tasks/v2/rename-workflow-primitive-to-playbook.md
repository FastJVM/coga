---
slug: v2/rename-workflow-primitive-to-playbook
title: Rename workflow primitive to playbook
status: draft
mode: agent
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- coga/architecture
- coga/codebase
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Rename the **workflow** primitive to **playbook** across the codebase, the
shipped contexts, and the docs.

**Why.** The current name is the weakest in the system on two counts:

1. *It mislabels the thing.* "Workflow" carries the romantic, absorption-camp
   connotation — the n8n/Zapier/CI sense of *the automation runs itself*. That
   is the opposite of what this primitive is: a sequence of **handoffs between
   operators** (`assignee: agent | human | owner`), with a human gate built
   into the step list. We are naming our most human-in-the-loop primitive with
   the vocabulary of the camp Relay defines itself against.
2. *The product is literally a relay.* A relay (race) is a baton passed between
   runners. The steps *are* the relay; the distinctive thing about them is the
   operator handoff, not the automation. "Playbook" names that correctly —
   ordered plays, process knowledge, no "runs-itself" baggage — and pairs
   cleanly with the existing `skills` / `contexts` vocabulary.

This mirrors the earlier `relay step → relay bump` rename (see
`relay/current-direction`): same motive — a name that overloaded/mislabeled
the concept and confused readers.

**Proposed name:** `playbook` (open to alternatives — `track`, `route` were
runners-up). The design step should confirm the name before the mechanical
rename begins.

**Scope / blast radius (for the design step to turn into a precise plan).**
This touches a *reserved frontmatter key*, so it is not a simple find/replace:

- **Reserved frontmatter key** `workflow:` (+ `step:` stays, it names a
  position *within* a playbook) — listed in `relay/architecture` canonical key
  set and enforced by `validate.py`.
- **Source** (~20 modules reference `workflow`): `workflow.py` (likely renamed),
  `compose.py`, `bump.py`, `mark.py`, `launch.py`, `launch_script.py`,
  `ticket.py`, `validate.py`, `config.py`, `create.py`, `paths.py`,
  `recurring.py`, `automerge.py`, `retrofit.py`, `retire.py`, and the
  `commands/` thin wrappers.
- **CLI surface**: the `--workflow` flag on `relay draft` / `relay create`;
  any help text and error messages ("a workflow-less draft can't be
  activated…").
- **On-disk layout**: the `relay-os/workflows/` directory and the packaged
  copy under `src/relay/resources/templates/relay-os/workflows/` — keep both
  in sync.
- **Shipped contexts/docs**: `relay/architecture`, `relay/principles`,
  `relay/current-direction`, `relay/codebase`, `docs/vision.md`,
  `docs/market-thesis.md`, `README.md`.
- **Migration of existing tickets**: every live ticket carries a frozen
  `workflow:` block in frontmatter. Decide on backward compatibility — accept
  the old key as a deprecated alias for one release, or write a one-shot
  migration (`relay retrofit`?) that rewrites in place. The fail-loud
  principle argues against silently accepting both forever.
- **Tests & fixtures**: `tests/test_*.py` and `example/relay-os/`.

**Out of scope (unless the design step decides otherwise):** renaming `step`
(it names a position within a playbook and reads fine), or changing any
behavior — this is a pure rename, no semantic change.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
