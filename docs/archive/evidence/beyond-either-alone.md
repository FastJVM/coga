# Beyond either alone: claim check and research evaluation

Dated 2026-11-02. Evidence page, not current instructions.

## The claim

Coga lets people and agents reach results neither reaches alone. Two senses
of *gestalt* carry the argument:

1. **The whole exceeds the parts, given the right process.** Human plus agent
   is not better by default; process makes it so.
2. **Insight comes from restructuring the whole problem.** Coga keeps the whole
   plan in text, so a person can see it at once and rearrange it, and later
   sessions start from the rearranged plan.

Thinkpick is the motivating case. The agent produced a reasonable plan fast. A
human saw that its premise was untested, rearranged the plan to establish
ground truth first, and later paused the project. The rearranged plan
persisted in tickets and contexts, not in either party's memory.

## Part 1: does Coga implement the mechanism?

Checked against the code on 2026-11-02.

| Mechanism the claim needs | Status | Where |
| --- | --- | --- |
| The plan is durable, inspectable text | Yes | Tickets under `coga/tasks/`; no database or hidden memory |
| Each session's prompt is built from those files, not from memory | Yes | `compose_prompt_report` in `src/coga/compose.py` composes fixed layers from files; `--prompt-report` measures them |
| Missing knowledge is surfaced rather than dropped | Yes | Compose refuses when an attached context does not resolve |
| The plan can be rearranged cheaply | Yes | Direct edits, `coga ticket`, `mark` (paused/canceled), `block`, `bump --to`, `delete` |
| The rearrangement carries into later sessions, by any agent | Yes | Every launch recomposes from current files; agent type is per ticket |
| Context selection is explicit, whoever does it | Yes | `contexts:` frontmatter, written by a human or by an agent (`coga ticket`, `coga build`) |
| Gates ask for judgment about premises, not only approval | Partly | `code/design-then-implement` rewinds to design when the premise is wrong; `code/review-design` asks which assumptions remain unstated; the ticket skill asks which assumptions to question before launch. Other shipped review steps focus on the work product |
| "See the whole at once" | Partly | `coga status` lists tickets, and the files are readable; there is no dedicated whole-plan view, so seeing the whole relies on reading tickets |

Verdict: the mechanism exists. Its weakest parts are the two the research
below flags as decisive, premise-level review and visibility of the whole.

## Part 2: what the state of the art says

### Supports the claim

- **Synergy exists when the human holds an edge the AI lacks.** Vaccaro,
  Almaatouq and Malone's meta-analysis (Nature Human Behaviour, 2024; 106
  experiments, 370 effect sizes) found synergy when the human alone
  outperformed the AI alone (g = 0.46), and losses when the AI was stronger
  (g = −0.54). Judging premises and purpose is a place where the human is
  plausibly stronger, which is where Coga directs human attention.
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC11659167/>
- **Process beats strength.** Kasparov's account of freestyle chess: "weak
  human + machine + better process" beat a strong human with an inferior
  process (Deep Thinking, 2017; restated in CACM).
  <https://cacm.acm.org/?p=225260>
- **Accurately selected prior context helps; unfiltered context does not.**
  SWE-ContextBench (2026) found that accurately summarized and retrieved prior
  experience significantly improves resolution, most on harder tasks, while
  unfiltered or wrongly selected context gives limited or negative benefit.
  Coga makes that selection explicit and correctable.
  <https://arxiv.org/abs/2602.08316>
- **Insight is restructuring.** Gestalt insight research (Köhler, Duncker) and
  Ohlsson's representational change theory treat insight as a change in how
  the problem is represented. Work on situated insight (Vallée-Tourangeau)
  argues that interacting with external artifacts drives that change, which
  supports putting the plan in an editable external form.
  <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10219327/>,
  <https://eprints.kingston.ac.uk/33548/7/Vallee-Tourangeau-F-33548a.pdf>

### Cuts against the claim, or bounds it

- **The default is negative.** In the same meta-analysis, human–AI
  combinations did worse on average than the better of either alone
  (g = −0.23), and decision tasks showed losses (g = −0.27). Review gates are
  decision tasks. Division of labour was not a significant moderator, so
  "assign by strength" alone does not explain synergy.
- **Generic context files do not help.** Gloaguen et al. (ETH, 2026): repo-level
  AGENTS.md files did not generally improve success and raised cost by over 20%.
  Repository overviews did not help; non-standard practices did. Coga's claim
  holds only for precisely selected facts the code does not state.
  <https://arxiv.org/abs/2602.11988>
- **Summaries cannot replace source.** Natural-language summaries answered 4 of
  45 behavioral questions against 27 of 45 for the source. Contexts should hold
  decisions and constraints, with the agent free to read the code.
  <https://arxiv.org/abs/2607.09691>
- **Oversight erodes.** Lee et al. (CHI 2025): higher trust in generative AI
  goes with less critical thinking. Reports on agent PR review and permission
  prompts describe rising approval and falling scrutiny over time. A gate can
  turn into a rubber stamp, which is the losing case.
  <https://www.microsoft.com/en-us/research/?p=1135061>,
  <https://arxiv.org/abs/2608.23642>

### Not found

No study found tests whether an external, editable plan helps people catch a
wrong premise in an agent's plan, which is the specific mechanism claimed.
Spec-driven tools (GitHub Spec Kit, Kiro) put specs at the center of agent
work, but evaluations found are vendor or blog comparisons of workflow, not
outcome studies.

### Verdict

**Plausible and consistent with the evidence, not demonstrated.** The
literature supports the conditions the claim relies on: synergy where the
human holds the edge, process over strength, precise context over volume,
insight through restructuring external representations. It also says the
default outcome is worse than either alone, so the claim stands or falls on
whether Coga's process actually produces premise-level judgment. The only
direct evidence is one case (Thinkpick).

## Part 3: evaluation as a research contribution

### Originality: moderate

- The components are not new. Persistent spec and task files (Spec Kit, Kiro,
  AGENTS.md), human-in-the-loop gates, and the theory (Engelbart's
  augmentation framework, distributed cognition, Kasparov's law, Gestalt
  insight) all predate Coga.
- What is less common is the framing: an agent's plan as an external
  representation for human restructuring, with explicit context selection by
  human or agent, cross-session carry-over, and "decide not to build" as a
  first-class outcome. Spec-driven tools treat the spec as an input to
  execution; Coga treats the plan as something to be reconsidered.
- Linking the meta-analytic synergy conditions to agent tooling design, rather
  than to single-shot decision aids, is an open gap in the literature found.

### Potential impact: high if it holds, unproven

- It addresses a known, measured problem: human–AI pairs underperform the
  better partner on average. A process that reliably flips that for planning
  work would matter well beyond Coga.
- It is a design principle other tools could adopt, not a Coga-only feature.
- Limits: evidence is n = 1; the process costs attention; adoption depends on
  the first-use experience; and gates degrade if reviewers start trusting the
  agent.

### Interestingness: high

- It is counterintuitive: the honest headline is "pairs do worse by default;
  here is a process meant to make them better."
- It is falsifiable with a clean design. Plant a flawed premise in a planning
  task; give one group raw agent sessions and another a Coga workflow with the
  plan as tickets and a premise-review gate; measure how often and how early
  the premise is caught, total time, and outcome quality, and check whether
  catches persist across sessions. A null result would also be informative.
- It ties a classic cognitive-science mechanism (restructuring) to a current
  engineering question (how to direct agents).

### What would strengthen it

- Run the planted-premise study above, even at small scale, with transcripts.
- Make premise review explicit in shipped review gates, since the evidence
  says that is where synergy is won or lost.
- Consider a whole-plan view, since restructuring depends on seeing the whole.
