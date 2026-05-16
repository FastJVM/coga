---
name: eval/ambiguity-checklist
description: Independent LLM-as-judge subagent that evaluates a freshly-drafted ticket against the 6-axis Trail of Bits ambiguity checklist. Returns a typed verdict; never writes to disk. Invoked from bootstrap/ticket so it fires on every new ticket.
---

# Eval Pass: Ambiguity Checklist

This skill is an isolated judge. The drafting agent cannot evaluate
its own work without implementation-self bias — the LLM-as-judge
pattern only works when the judge has no stake in starting work,
which in practice means a fresh subagent context with no prior
conversation.

Always invoke via a fresh subagent (e.g. the Agent tool with
`subagent_type: general-purpose`). Never run inline in the drafting
agent's loop.

## When this skill is called

Every new ticket passes through this skill before activation.
`bootstrap/ticket` invokes it after the ticket body has been written
and before handing back to the human. It is also valid to call this
skill at later phases — for example, after a workflow's
implementation-plan step, to catch divergences between ticket intent
and the plan's concrete interpretation. Same skill, same verdict
contract, same caller responsibilities.

## Inputs (passed by the invoker)

- Path to `ticket.md`
- Paths to every file in the ticket's `contexts:` frontmatter
- Path to `blackboard.md` (may be empty for a new ticket)
- Repo root (for cheap discovery reads)

## Process

1. Read all inputs cold. You have no prior context.

2. Do cheap discovery to answer what the ticket leaves implicit:
   - `relay.toml` for project conventions and assignees.
   - Language and build configs (`pyproject.toml`, `package.json`,
     etc.) if the ticket touches those areas.
   - `relay-os/tasks/*/` for similar past tickets on the same
     workflow or namespace.
   - `.gitignore` and setup docs if environment is ambiguous.

   A question that discovery can answer is not a question. Spend
   more time reading than asking.

3. Apply the 6-axis Trail of Bits ambiguity checklist. Score each
   axis PASS (sufficient for an agent to act without guessing) or
   GAP (an agent would have to fabricate to proceed):

   | Axis | What it checks |
   | --- | --- |
   | Objective | What should change vs stay the same? |
   | Done criteria | What does success look like concretely? |
   | Scope | Which files / components / systems are in or out? |
   | Constraints | Compatibility, performance, style, dependencies? |
   | Environment | Language versions, OS, build tools, runtime? |
   | Safety | Destructive class, data migration, rollout, rollback? |

4. For each GAP axis, draft a multi-choice question with 2 or 3
   options:

   - **(a)** real choice — recommended default. Always present.
   - **(b)** real, distinct alternative. Always present.
   - **(c)** optional — a third real alternative, only when three
     genuinely distinct paths exist (e.g. JWT / OAuth / API keys).
     Do not include (c) just to offer a "not sure" — that's covered
     by the fast-path reply `defaults`.

   All listed options must be paths the implementer could
   meaningfully take. Don't invent a fake alternative to fill a
   slot.

5. Ask 1–5 questions total. The exact count is your judgment based
   on how many axes are GAP and how independent they are. Fewer is
   better when fewer gaps exist. If more than 5 gaps exist, pick the
   5 that eliminate the most branches of work and note the residual
   in `rationale`.

6. If the ticket attaches a context indicating destructive action
   class (e.g. `browser/destructive-actions`), always include a
   safety question even when the safety axis would otherwise pass.

## Verdict contract

Return a single JSON object. No prose outside the JSON.

```json
{
  "status": "PASS" | "GAP",
  "axes": {
    "objective":   "PASS|GAP",
    "done":        "PASS|GAP",
    "scope":       "PASS|GAP",
    "constraints": "PASS|GAP",
    "environment": "PASS|GAP",
    "safety":      "PASS|GAP"
  },
  "discovery": ["<file or grep target> → <what was learned>", "..."],
  "questions": [
    {
      "axis": "scope",
      "prompt": "<one-sentence question>",
      "options": [
        {"label": "a", "text": "<real choice — recommended>", "default": true},
        {"label": "b", "text": "<real, distinct alternative>"}
      ]
    }
  ],
  "rationale": "<one paragraph for the human: what gapped and why>"
}
```

## Rules

- **Never write to disk.** Verdict returns to the invoker; persistence
  is the invoker's responsibility.
- **Never assume silently.** If a default is chosen because the
  ticket is unclear, surface that as a question even when the default
  is the recommended path.
- **Discovery reads are unbounded but cheap.** Always read before
  asking.
- **1–5 questions, judge-calibrated.** Count is determined by how
  many axes are GAP and how independent they are, not a fixed quota.
  Skip questions that discovery already answered.
- **2 or 3 options per question.** (a) recommended default + (b)
  genuine alternative are mandatory. (c) is optional and only used
  when a third truly distinct path exists. Never (c) as "not sure" —
  `defaults` covers that.
- **Multiple choice > open-ended.** If a question is genuinely
  open-ended, flag it in `rationale` and explain why options don't
  fit.
- **Pause-before-acting applies upstream.** The invoker must not run
  state-changing commands until the verdict is consumed and any
  questions answered.

## Verdict handling (invoker contract)

The invoker is responsible for the following after receiving the
verdict:

- **`status: PASS`** — write a one-line entry to `blackboard.md` under
  `## Eval pass`: `PASS on <date>. Discovery: <bullet>.` Then proceed.
- **`status: GAP`** — render the `questions` array to the human as a
  clean numbered prompt. Never show raw JSON. The human replies in
  `<question-number><option-label>` form (e.g. `1a 2b 3c`) or
  `defaults` to accept all (a) options. Write the resolved Q&A to
  `blackboard.md` under `## Clarifications`, restate the resolved
  interpretation in 1–3 sentences, then proceed.

## Subagent invocation block

When invoking this skill via the Agent tool (or equivalent), paste
the following as the `prompt` parameter, substituting the bracketed
paths:

> You are an isolated judge running the eval/ambiguity-checklist
> skill. You did not draft the ticket and you will not implement it.
>
> **Inputs to read:**
> - Ticket: [path/to/ticket.md]
> - Blackboard: [path/to/blackboard.md]
> - Contexts: [list paths from ticket's contexts: frontmatter]
> - Repo root: [path]
>
> Follow the process in
> `relay-os/bootstrap/skills/eval/ambiguity-checklist/SKILL.md`:
> cheap discovery reads, then 6-axis ambiguity checklist, then 1–5
> 2-or-3-option questions for any GAP axes, then verdict.
>
> Return JSON only. No prose outside the JSON. Schema is in the
> SKILL.md verdict-contract section.

## See also

- Trail of Bits "ask-questions-if-underspecified" plugin —
  https://trailofbits-skills.mintlify.app/plugins/ask-questions-if-underspecified
  (the source of the 6-axis methodology and question patterns).
- LLM-as-a-judge — the architectural pattern this skill implements.
  Effectiveness depends on the judge running in a fresh context with
  no stake in the implementing agent's plan.
