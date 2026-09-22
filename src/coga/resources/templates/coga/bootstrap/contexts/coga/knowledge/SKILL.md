---
name: coga/knowledge
description: The permanent authoring rule for Coga knowledge — which surface owns a fact (topics, skills, blackboard, log), one owner per fact, links never load content, when to attach versus cite a topic on a ticket, and the topic size review policy.
---

# Where knowledge lives

Every fact has exactly one owning file; when two copies disagree, the owner
is right. Choose the owner by what the knowledge is:

| Knowledge | Owner |
| --- | --- |
| Facts and contracts: behavior, invariants, edge cases, product intent | a topic under the configured contexts root (`<ref>/SKILL.md`) |
| Reusable process: how to do a thing | a skill (`coga/skills/<ref>/SKILL.md` or bundled) |
| One task's temporary working state | that ticket's blackboard ([coga/blackboard](../blackboard/SKILL.md)) |
| Execution history | `coga/log.md`, written only by CLI commands |
| Dated evidence, proposals, retired history | `docs/evidence/`, `docs/design/`, `docs/archive/` pages |

Humans and agents read the same topic file. Do not keep a short agent
rendition beside a longer human one: that is two owners of one fact, and the
copies drift independently. Pick the topic whose subject already covers the
neighbouring facts; when two fit, the more narrowly attached one wins, because
the fact then costs tokens only where it is needed.

## Narrative links, never restates

An index, README, overview, or neighbouring topic may summarize and link to
the owner, but carries no specification-grade detail: no ordered lists, exact
names, counts or field lists that can drift on their own. "Launch stacks
conduct before task material, ticket last; the order is in
`coga/prompt-composition`" is a summary; copying the layer list is a second
specification. Command semantics live in the topic that owns the behavior;
`coga/cli` is an index, and installed `coga <cmd> --help` is the syntax
authority.

**Sync rule.** A PR that changes an owner greps other surfaces for the fact
and fixes or deletes any restatement in the same PR. No test enforces this
across surfaces (only live/packaged twins are byte-checked); the authoring
rule is the enforcement and Dream's knowledge scan is the backstop. A live
topic and its packaged twin are one fact, not two surfaces. `CLAUDE.md` /
`AGENTS.md` load in every agent session, so they carry pointers plus only the
rules needed outside `coga launch`, never an owning statement.

## Links do not load content

Composition includes attached refs only
([coga/prompt-composition](../prompt-composition/SKILL.md)). A markdown link
in a topic, skill, or ticket is navigation: the agent reads the target only if
it chooses to open the file. So an overview does not bring in its children,
and knowledge a step requires must be attached explicitly by ref.

## Attach or cite

`contexts:` is one ticket-wide list, composed whole into every launch of
every step. Decide per ticket across all planned steps:

- **Attach** when a step must have the facts without being told to look:
  its correctness depends on rules spread across the topic, or the author
  cannot predict which facts it will hit. Test: would a launched step go
  wrong if this were absent from the prompt?
- **Cite** when steps need a few identifiable facts from a topic that is
  large relative to the rest of the prompt, or when the ticket will *edit*
  that topic (it gets read first anyway).

Measure relative size at authoring time with `approx_tokens` from
`coga launch --prompt-report` or a read-only `compose_prompt_report` on an
in-memory ticket copy with the candidate added; do not edit lifecycle
frontmatter to measure, and do not quote sizes (they go stale). No topic is
always-attach or always-cite.

A cite is one sentence in `## Context` naming the ref and path, saying it is
cited rather than attached, and naming the sections to read, followed by the
facts the step needs, cited as module plus symbol. Do not justify it by size.
The copied facts are a snapshot for that ticket, never a second owner. Citing
does not relax the sync rule: a ticket that changes behavior a cited topic
owns updates that topic, and its packaged twin, in the same PR.

## Topic size review policy

Each topic is a directory holding `SKILL.md` with only `name` and a
one-sentence `description` stating its scope. Targets: 60 to 160 lines and
500 to 1,500 tokens (ceil(chars/4), frontmatter included); overview topics at
most 1,000 tokens. A topic over 200 lines, 10,000 bytes, or 2,500 tokens is
reviewed for a split into narrower leaves in its namespace, so tickets can
attach only the contract they need. An exception needs a recorded reason.
