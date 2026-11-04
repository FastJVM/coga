---
name: coga-dev/principles
description: Coga's design principles — the shared foundation for developing Coga and writing its README.
---

# Coga's design principles

Coga is an instrument for people directing agents, not another coding
agent. Agents work in sessions; people's goals, questions, and decisions
outlive those sessions. Coga keeps the working plan in text people can
inspect, challenge, and change — including when the right decision is not
to build.

## Principles

- **Expand human capacity.** Expand people's ability to think, explore, and
  create. People choose purpose and direction; agents help discover problems,
  challenge assumptions, and build. Automate mechanical work to leave more
  attention for judgment. People and agents together do not outperform the
  stronger of the two by default; process makes the difference. Route each
  step to whoever is stronger at it, and keep the whole problem in a form
  people can see and restructure, so together they reach what neither reaches
  alone.
- **Text above code.** Readable text carries intent, knowledge, and decisions.
  Code implements that understanding and can be rewritten as we learn.
- **Context is explicit.** People can find, question, correct, and choose the
  knowledge each task needs. Make what an agent works from understandable.
- **Small improvements compound.** Correct the instructions behind an error
  so later work starts from better understanding. Keep changes visible and
  correctable; retain what proves useful and revise what stops working.
- **Yours and hackable.** People own their knowledge and tools. They can
  inspect, change, and move them, reshape how they work, and replace agents.
  The mechanisms serving those freedoms can change too.
- **Keep everything at human scale.** Keep Coga a thin overlay on agent
  capabilities, small enough to inspect and change. The tool should fit the
  way people work, not make them fit its process.
- **Amplify agents, don't duplicate them.** Use existing coding agents to
  plan, research, implement, and review. Coga organizes and carries their
  work across tasks and sessions instead of rebuilding their capabilities.
- **Coga encoded in Coga.** Use the same tickets, contexts, and workflows to
  describe and evolve Coga itself.
- **Fail loud.** Surface missing knowledge and failed operations so people
  can correct them. Never present an unnoticed failure as success.
- **The task outlives the session.** Give substantive work a durable record
  that people can direct and agents can resume.

## Consequences

- **Homoiconicity for agents.** Tickets, contexts, and workflows use the
  same Markdown that agents read and can edit. There is no separate
  agent-only version of the plan.
- **Everything is disposable except the text.** Code and methods can be
  replaced. Intent, decisions, and what we learn survive in editable files.
- **Agents can manage Coga itself.** They can write tickets, revise contexts,
  and change workflows without learning a special language.
- **Build Coga on base concepts agents are good with.** Use familiar tickets,
  plans, and workflows rather than inventing a language agents must learn.

## In practice

Planning serves both people and agents. The agent's proposal gives the human
something concrete to read: the intended outcome, assumptions, approach,
and criteria for success. A human can question its assumptions, correct the
tickets or context, add a review step, or stop the project. The revised text
also directs later agent work. Coga uses the agent's planning capability and
keeps that shared understanding editable across sessions. The
[Coga history examples](../../../../README.md#when-coga-changed-its-own-mind)
show a discarded architectural assumption and a maintenance workflow changed
when it became clear that transient notes would not preserve key findings.

Fresh sessions make written handoffs important. The agent records useful
findings, decisions, and open questions in the
[blackboard](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md); the next
[launch](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md) starts from the current
files. People can inspect, correct, and share the working knowledge carried
forward. The record can be incomplete or wrong, so its reviewability matters
as much as its persistence. This gives people a practical way to manage
context rot and understand the work they delegate.

Choose knowledge and procedures for their relevance to the task. Explicit
attachment puts selected guidance into the starting prompt; deciding what is
needed, missing, or obsolete remains work for people and agents. The
[research on context and skills](reading-list.md#context-skills-and-plan-review)
supports examining that choice carefully: useful guidance can help, while
irrelevant or conflicting instructions can add cost or hurt results. Those
studies do not establish a performance gain for Coga itself.

These principles guide Coga's design. The
[README](https://github.com/FastJVM/coga/blob/main/README.md) derives from them;
edits to the README must stay aligned. Behavioral topics own current
implementation contracts, including Git. The
[reading list](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/principles/reading-list.md)
records our influences.
