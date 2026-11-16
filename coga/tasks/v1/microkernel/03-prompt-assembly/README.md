# Prompt assembly

An experiment-first group within the microkernel work. The owner asked for a
general ticket-based mechanism and for evidence that a new assembler improves
on the current form before replacing it. This directory is a plain group:
its tickets own the deliverables and their own workflows.

| Order | Ticket | Deliverable |
| --- | --- | --- |
| 01 | [Candidates and protocol](01-define-prompt-candidates-and-trial-protocol/ticket.md) | Complete prompt specimens and an owner-approved comparison protocol |
| 02 | [Paired comparison](02-compare-current-and-candidate-prompt-assembly/ticket.md) | Observed results and an owner decision, including a possible negative or inconclusive result |
| 03 | [Assembly defect fixes](03-implement-the-proven-prompt-assembly.md) | Rescoped 2026-11-15: fix defects in the current assembly, with unit tests (no migration) |
| 04 | [Output-quality comparison](04-compare-prompt-assembly-output-quality/ticket.md) | Owner's blinded judgment of current vs C1′: inconclusive (2026-11-15); current assembly kept |

Tickets 01, 02 and 04 use `draft-for-human` so the owner reviews the protocol
and judges the evidence. Neither comparison produced a positive selection (02:
C1 disqualified; 04: inconclusive), so ticket 03 was rescoped to fixing
defects in the current assembly. It uses `code/design-then-implement`,
retaining design review and code review. Numbering expresses the intended
order, not an automatic scheduler gate.

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
