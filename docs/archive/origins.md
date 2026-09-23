# Coga origins

> **History.** Selected founding narrative from the original vision essay
> (`docs/vision.md`, first written 2026-04-24 and revised through 2026-09-11),
> archived 2026-09-22 during the documentation-library migration. Statements
> such as "six months ago" or "at month six" are relative to that essay, not to
> today. The current purpose, audience, bet and limits are in
> [`product/vision`](../contexts/product/vision/SKILL.md); the enduring
> constraints are in [`coga/principles`](../contexts/coga/principles/SKILL.md).
> Nothing here is a behavioral contract.

## The reset

FastJVM is a two-person deeptech startup making the JVM faster. When its
research took longer than expected and funding was running short, the founders
chose to rebuild rather than shut down: they let engineers go and reconstituted
the company around the two founders, one senior engineer and whatever leverage
frontier agents could provide. Coga was built as the operating substrate for
that reconstitution. Every recurring task, workflow and piece of institutional
knowledge either moved into it or was cut.

The essay argued that this reset was a precondition: a company with
established SaaS tools, processes and tribal knowledge cannot layer Coga on top
and get the same leverage, because the substrate has to be the operating
substrate rather than a parallel one.

## The classical mode

The essay's philosophical center came from Pirsig's *Zen and the Art of
Motorcycle Maintenance*: the romantic mode uses a machine without understanding
its inside; the classical mode understands and maintains it. The essay called
most software romantic — rented black boxes, hidden agent prompts and rules —
and positioned Coga as classical: every file the agent reads is readable, every
rule editable, and a mistake is fixed by editing the context. Markdown over
databases, CLIs over UIs, direct edits over PR cycles, and discipline over
enforcement were presented as consequences of that choice.

## Homoiconicity and the substrate

Everything Coga operates on is markdown in a Git repository: tasks, contexts,
skills, workflows, the base prompt and blackboards. The essay compared this to
Lisp's homoiconicity — code and data in one structure, so inspection and
modification are the same action — and accepted the Lisp tradeoff: flexibility
without structure means discipline substitutes for enforcement, and at some
team size the missing structure is needed.

## The correction loop and compounding

The essay measured the loop from observed mistake to live fix at "about two
minutes" (edit the context, commit, the next run uses it), contrasted with the
days-to-weeks loop of configuring a SaaS platform. Cheap corrections get made
constantly, including marginal ones, so the context library improves with use
and each new automation inherits the corrected material. At month six the
founders judged their context library more valuable than the CLI, scripts,
workflows and base prompt combined. The two-minute figure is an owner-reported
illustration, not a controlled measurement.

## Self-bootstrapping

The essay described Dream (generic cleanup that proposes changes for human
review), REM (repo-specific recurring maintenance) and guided ticket authoring
as the system's "strange loop", after Hofstadter: the rules are files that the
same agents can read and propose changes to. Current contracts for these are
`coga/dream`, `coga/recurring` and `coga/tickets`.

## Why it was thought hard to duplicate

Three barriers were named, none of them in the code: the reset (most companies
cannot rebuild around a new substrate), the encoded expertise (forking Coga
gets the CLI, not the context library), and the sustained discipline (the essay
noted six months of practice, "ask us again in four years"). Publishing was
therefore judged to cost nothing, and to serve alignment, future hiring and the
small set of founder-operated technical teams near a similar reset.

The essay's "What this is not" list said Coga was not a product that was sold
or supported, not an agent, not a platform, not a replacement for judgment and
not defensible by conventional moats. The current market reasoning is in
[`marketing/strategy`](../contexts/marketing/strategy/SKILL.md).

## Lineage

Pirsig's classical mode (1974), McCarthy's Lisp (1958), Hofstadter's strange
loops (1979), the Hearsay-II blackboard architecture from CMU in the 1970s, and
Unix's small tools composed through files. The essay's claim was that the new
element is economic: frontier agents lower the cost of automation enough that
understanding your own machine becomes viable for a small team again.
