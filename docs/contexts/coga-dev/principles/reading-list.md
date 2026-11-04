# Reading behind Coga's design principles

A companion to the [principles](SKILL.md), kept separate so they
stay short enough to include in a task's context. These are influences and
related readings, not evidence that Coga has achieved its ambitions.

- **Steve Jobs — [Make Something Wonderful](https://book.stevejobsarchive.com/).**
  The Steve Jobs Archive's collection of speeches, interviews, and writing
  provides a starting point for the bicycle-for-the-mind metaphor and the
  ambition to amplify what people can do with computers.
- **Tim O’Reilly — [Jensen Huang Gets It Wrong, Claude Gets It Right (2025)](https://www.oreilly.com/radar/jensen-huang-gets-it-wrong/).**
  An argument for designing AI tools that expand human capability and agency.
  Useful for asking whether a feature helps people pursue new possibilities,
  beyond automating existing work.
- **Robert M. Pirsig — [Zen and the Art of Motorcycle Maintenance](https://www.penguin.co.uk/books/431040/zen-and-the-art-of-motorcycle-maintenance-by-pirsig-robert/9780099598169).**
  Read for the relationship between quality, care, and understanding the
  tools you use. Coga's commitment to hackability is our interpretation of
  that influence.
- **Alan Kay — [Interview for The Machine That Changed the World (1990)](https://americanarchive.org/catalog/cpb-aacip-15-pv6b27q16d).**
  Read for computing as an interactive medium that changes how people
  represent problems, explore possibilities, and think. The small-kernel
  architecture is Coga's choice, not a rule attributed to this interview.

For a related argument about improving both tools and ways of working, read
**Douglas Engelbart's [Augmenting Human Intellect: A Conceptual Framework
(1962)](https://dougengelbart.org/pubs/augment-3906-Framework.html)**. It treats
human capability as a system of people, tools, language, methods, and
training, with improvements that can enable further improvements.

## Related contemporary work

These projects share parts of that tradition; they are related work, not
claims about where Coga's implementation came from.

- **Ink & Switch — [Malleable software (2025)](https://www.inkandswitch.com/essay/malleable-software/).**
  A research agenda for tools people reshape during ordinary use, with
  a gradual path from using software to changing it. It explicitly connects
  this ambition to Alan Kay and earlier work on user-tailorable systems.
- **[Glamorous Toolkit](https://gtoolkit.com/).** A Smalltalk-derived
  environment for understanding systems through contextual tools, including
  a moldable agent harness. Its
  [Smalltalk history](https://book.gtoolkit.com/smalltalk-history-2oiurgue84cv8xerpds2kphqh)
  makes that lineage explicit. It is a concrete neighbour for thinking about
  humans and agents inspecting and shaping their working environment.

## Context, skills, and plan review

These sources inform the choice to make working knowledge explicit,
selective, and reviewable. The studies evaluate their own tasks and agent
setups; they do not measure Coga. Our practical takeaway is to inspect which
guidance a task needs and revise it as the project changes.

- **Chroma — [Context Rot: How Increasing Input Tokens Impacts LLM Performance
  (2025)](https://www.trychroma.com/research/context-rot).** Controlled
  experiments show that longer inputs can make performance less reliable,
  including within the supported context window. This motivates focused
  starting context; restarting alone does not establish that a handoff
  retained every important fact.
- **Li et al. — [SkillsBench (2026, v4)](https://arxiv.org/abs/2602.12670v4).**
  Across 87 tasks and 18 model-harness configurations, curated skills raised
  the average pass rate from 33.9% to 50.5%. Focused skill bundles performed
  better than larger or exhaustive ones. This is evidence that selected
  procedural guidance can help on the evaluated tasks, rather than a general
  result about every skill or coding workflow.
- **Han et al. — [SWE-Skills-Bench (2026, v2)](https://arxiv.org/abs/2603.15401v2).**
  In a software-engineering evaluation, 92 of 98 skills had no statistically
  significant effect, and average pass ratio changed from 76.6% to 76.9%.
  Helpful skills supplied otherwise omitted procedures; harmful ones pushed
  their own templates over task instructions. Relevance and compatibility
  with the task matter.
- **Gloaguen et al. — [Evaluating AGENTS.md (2026, v3)](https://arxiv.org/abs/2602.11988v3).**
  Repository context files did not generally improve task success, and
  increased inference cost by over 20% on average. The authors distinguish
  useful non-standard practices from unhelpful repository overviews. A
  context file's existence is not evidence of its value to a particular task.
- **Anthropic — [Effective context engineering for AI agents](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents).**
  Describes structured notes outside the context window and reading them
  after resets to continue extended work. Coga's human-facing rationale is
  that people can also inspect, correct, and share those written handoffs.
- **Anthropic — [Claude Code plan mode as the default starting point](https://academy.claude.com/courses/ai-native-sdlc-playbook/plan-mode).**
  Describes an engineer questioning and correcting a written implementation
  plan before coding, then checking the result against it. This is practice
  guidance for making intended work reviewable, not a controlled experiment
  proving that reading any plan improves the result.

The [origins essay](../../../archive/origins.md) preserves Coga's earlier
founding narrative; it is historical context, not the current design principles.
