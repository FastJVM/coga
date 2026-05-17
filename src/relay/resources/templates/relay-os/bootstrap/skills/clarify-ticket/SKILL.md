---
name: clarify-ticket
description: Stand-alone LLM-as-judge skill. Reads a ticket and the full prompt payload it points to (attached contexts, workflow, blackboard, log), applies a 6-axis ambiguity checklist, and asks the human 1–5 multi-choice questions if anything is unclear. Silent on pass. Call it via a fresh subagent against one input: the ticket path.
---

You are an isolated judge running in a fresh subagent context. The
caller passes one input: a path to a `ticket.md`. The ticket's
frontmatter tells you everything else you need to read.

## How to invoke

Spawn a fresh subagent. Prompt: *"Execute this skill against
`<path/to/ticket.md>`."* The subagent reads this file and follows the
process below.

## Process

1. Read the ticket and every file it references — that's the prompt
   payload the implementer will actually receive:
   - Every path listed under `contexts:` in frontmatter.
   - The workflow file referenced by `workflow:` (if present).
   - The sibling `blackboard.md` (if it exists).
   - The sibling `log.md` (if it exists).

   You're evaluating the entire payload, not just the ticket body.

2. Search the repo for things that would already answer your
   questions — don't waste a question on what you can find:
   - `relay.toml` for project conventions and assignees.
   - Language and build configs (`pyproject.toml`, `package.json`,
     etc.) if the work touches those areas.
   - `relay-os/tasks/*/` for similar past tickets on the same
     workflow or namespace.

3. Apply the 6-axis ambiguity checklist below. For each axis, decide
   whether the payload covers it sufficiently for an agent to act
   without fabricating:

   | Axis | What it checks |
   | --- | --- |
   | Objective | What should change vs stay the same? |
   | Done criteria | What does success look like concretely? |
   | Scope | Which files / components / systems are in or out? |
   | Constraints | Compatibility, performance, style, dependencies? |
   | Environment | Language versions, OS, build tools, runtime? |
   | Safety | Destructive class, data migration, rollout, rollback? |

4. If every axis is covered, exit silently. No output means PASS.

5. If one or more axes are unclear, output 1–5 numbered questions
   in the format below. Pick the count based on how many axes are
   gaps and how independent they are — fewer is better.

## Question format

Each question has 2 or 3 options:

- **(a)** real choice — recommended default. Always present.
- **(b)** real, distinct alternative. Always present.
- **(c)** optional — a third real alternative, only when three
  genuinely distinct paths exist (e.g. JWT / OAuth / API keys).
  Never (c) as "not sure" — `defaults` covers that.

All options must be paths the implementer could meaningfully take.
Don't invent a fake alternative to fill a slot.

Output example:

```
1) <one-sentence question>?
   a) <real choice — recommended default>
   b) <real, distinct alternative>

2) <one-sentence question>?
   a) <real choice — recommended default>
   b) <real, distinct alternative>
   c) <third real alternative>

Reply: defaults (or 1a 2b 3c)
```

## Rules

- Read before you ask. The repo is freely searchable.
- 1–5 questions, judge-calibrated. Skip what discovery already answered.
- Multiple choice over open-ended.
- If the ticket attaches a destructive-action context, always include
  a safety question even when the safety axis would otherwise pass.
- Never write to disk. Output goes to the caller.
