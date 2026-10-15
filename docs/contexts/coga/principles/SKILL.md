---
name: coga/principles
description: Navigation from the retired principles document to Coga's manifesto and the topics that own its operational contracts.
---

# Where the principles live

Coga's philosophy and design principles now live together in its
[manifesto](https://github.com/FastJVM/coga/blob/main/docs/contexts/product/vision/SKILL.md)
(`product/vision` in Coga's own repository). This ref remains a navigation
page for existing tickets and links, not a second statement of principles.
A downstream project's `product/vision` describes that project, not Coga.

Operational contracts live in their focused topics:

- [Architecture](../architecture/SKILL.md): durable files and the correction loop.
- [Extension model](../extension-model/SKILL.md): small core, editable edges,
  and command surfaces.
- [Knowledge](../knowledge/SKILL.md): explicit context and one owner per fact.
- [State publication](../internals/state-publication/SKILL.md): publication and
  review boundaries; [Dream](../dream/SKILL.md): proposed knowledge corrections.
- [Agents](../agents/SKILL.md): choosing and replacing agents.
- [Telemetry](../telemetry/SKILL.md): the measurement policy and its limits.
- [Prompt composition](../prompt-composition/SKILL.md): missing inputs fail;
  [sync](../sync/SKILL.md): read-only commands and publication boundaries.
- [Lifecycle](../lifecycle/SKILL.md): durable tasks and human direction.

Links do not load these contracts into a prompt; attach the topics a task needs.
