---
name: meta/create-suggest
description: Use immediately after relay create to fill in ticket frontmatter with suggested workflow, contexts, and skills based on the task title and description. Runs interactively — asks the human clarifying questions until the ticket is well-specified.
---

# Create-with-suggestions

You are helping a human flesh out a freshly-scaffolded ticket. The
ticket currently has a title and maybe a rough description. Your job
is to propose:

1. Which **workflow** (from `workflows/`) fits this task.
2. Which **contexts** (from `contexts/`) should attach.
3. Which **mode** (interactive / auto / script) suits the work.
4. Who should be the **assignee** (a human or an agent nickname).

## Process

1. Read the title and description in `ticket.md`.
2. Read the list of available workflows, contexts, and skills. Use
   the frontmatter `description` field of each to decide relevance.
3. Ask the human clarifying questions until the task is well-specified.
   Typical questions:
   - "Is this routine or novel? (routine → auto, novel → interactive)"
   - "Does this touch <domain X>? If so, I'd attach the <domain X>
     context block."
   - "Should this go through approval, or land directly?"
4. Write your suggestions to the ticket frontmatter **as a draft**.
   Do not overwrite fields the human already set. Preserve YAML
   formatting exactly.
5. Tell the human what you chose and why. The human edits or accepts.

## Rules

- This skill is the **only** sanctioned exception to the protocol's
  "do not edit `ticket.md` frontmatter" rule. The exception applies
  only while the human is present and approving each field as it
  lands. If the human steps away or the flow stops being interactive,
  stop writing to frontmatter and surface remaining suggestions on
  the blackboard's **Findings** section instead.
- Never invent a workflow, context, or skill that doesn't exist. If
  nothing fits, say so and suggest creating one (but do not create it
  yourself — that's a dream-skill proposal).
- Prefer fewer contexts over more. Three well-chosen context blocks
  beats seven loosely related ones.
- If the task looks like a one-shot automation (download something,
  click something, scrape something) and the existing skill already
  has a script, suggest `mode: script`.
- Default to `mode: interactive` when uncertain. The human can relax
  to auto later.

## When done

Call `relay step` to advance out of the creation step. The ticket is
now ready for normal work.
