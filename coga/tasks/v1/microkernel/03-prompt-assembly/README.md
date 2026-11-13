# Prompt assembly

An experiment-first group within the microkernel work. The owner asked for a
general ticket-based mechanism and for evidence that a new assembler improves
on the current form before replacing it. This directory is a plain group:
its tickets own the deliverables and their own workflows.

| Order | Ticket | Deliverable |
| --- | --- | --- |
| 01 | [Candidates and protocol](01-define-prompt-candidates-and-trial-protocol/ticket.md) | Complete prompt specimens and an owner-approved comparison protocol |
| 02 | [Paired comparison](02-compare-current-and-candidate-prompt-assembly/ticket.md) | Observed results and an owner decision, including a possible negative or inconclusive result |
| 03 | [Proven assembly implementation](03-implement-the-proven-prompt-assembly.md) | Production migration of the experimentally selected form, if replacement is justified |

The first two tickets use `draft-for-human` so the owner reviews the protocol
and judges the evidence. The implementation uses
`code/design-then-implement`, retaining design review and code review.
Numbering expresses the intended order, not an automatic scheduler gate.
Each dependent ticket names its prerequisite evidence. In particular, the
implementation ticket's positive-selection gate is stronger than completion
of the experiment. These drafts are not activated by this authoring pass.

The experiment covers both interactive sessions and noninteractive recurring
autofix analysis. Its implementation contract must keep deterministic ticket
execution deterministic. The tickets own the protocol, decision rule and
required behavior; this index does not prescribe another version of them.

[Launch decomposition](../03-launch-decomposition.md) remains a distinct
execution deliverable: stateless invocation/publication, session admission,
completion and duplicated setup. It is not a parent for this group. Prompt
experiments use the current executor; they do not wait for that refactor.
The implementation tickets coordinate only the actual shared seams they need.

The objectives are owned by
[coga-dev/microkernel/objectives](../../../../../docs/contexts/coga-dev/microkernel/objectives/SKILL.md).
The preceding broad prompt scope and evaluation are retained under
`## Superseded designs` in the launch-decomposition ticket. Current requirements
live in these new tickets; that history is optional provenance.
