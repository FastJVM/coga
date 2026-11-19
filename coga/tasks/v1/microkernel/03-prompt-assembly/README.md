# Prompt assembly

An experiment-first group within the microkernel work. The owner asked for a
general ticket-based mechanism and for evidence that a new assembler improves
on the current form before replacing it. All four tickets are done, retro'd
and deleted; the links below are historical permalinks to their last
revision, kept as optional provenance.

| Order | Ticket (historical) | Outcome |
| --- | --- | --- |
| 01 | [Candidates and protocol](https://github.com/FastJVM/coga/blob/96ff8dab0c00087c200f33a688c43149fb4be792/coga/tasks/v1/microkernel/03-prompt-assembly/01-define-prompt-candidates-and-trial-protocol/ticket.md) | Complete prompt specimens and an owner-approved comparison protocol |
| 02 | [Paired comparison](https://github.com/FastJVM/coga/blob/96ff8dab0c00087c200f33a688c43149fb4be792/coga/tasks/v1/microkernel/03-prompt-assembly/02-compare-current-and-candidate-prompt-assembly/ticket.md) | C1 disqualified; no positive selection |
| 03 | [Assembly defect fixes](https://github.com/FastJVM/coga/blob/96ff8dab0c00087c200f33a688c43149fb4be792/coga/tasks/v1/microkernel/03-prompt-assembly/03-implement-the-proven-prompt-assembly.md) | Rescoped 2026-11-15: fixed defects in the current assembly, with unit tests (no migration); evidence stays in `03-implement-the-proven-prompt-assembly-evidence/` |
| 04 | [Output-quality comparison](https://github.com/FastJVM/coga/blob/96ff8dab0c00087c200f33a688c43149fb4be792/coga/tasks/v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality/ticket.md) | Owner's blinded judgment of current vs C1′: inconclusive (2026-11-15); current assembly kept |

Current owners of what these tickets established:

- The assembler ruling (current assembly kept):
  [coga/prompt-composition](../../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md#assembler-ruling).
- The paired, blinded trial method (protocol, decision rule, harness pitfalls):
  [coga-dev/testing/agent-trials](../../../../../docs/contexts/coga-dev/testing/agent-trials/SKILL.md).
- Composition internals and known limits:
  [coga-dev/internals/compose](../../../../../docs/contexts/coga-dev/internals/compose/SKILL.md).

The experiment covered both interactive sessions and noninteractive recurring
autofix analysis. This index does not restate the protocol or ruling; read the
owners above.

[Launch decomposition](../03-launch-decomposition.md) remains a distinct
execution deliverable: stateless invocation/publication, session admission,
completion and duplicated setup. It is not a parent for this group. Prompt
experiments use the current executor; they do not wait for that refactor.
The implementation tickets coordinate only the actual shared seams they need.

The objectives are owned by
[coga-dev/microkernel/objectives](../../../../../docs/contexts/coga-dev/microkernel/objectives/SKILL.md).
The preceding broad prompt scope and evaluation are retained under
`## Superseded designs` in the launch-decomposition ticket; that history is
optional provenance. Current requirements live in the topics listed above.
