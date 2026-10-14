# Core flexibility across administrative and patent work

Dated evidence, split out of the archived [ten-tool usage comparison](../archive/evidence/usage-comparison.md) on 2026-10-13 because [`marketing/positioning`](../contexts/marketing/positioning/SKILL.md) still cites it.

**September 12, 2026 — owner-requested local source inspection.** The owner
identified the admin and patents repositories as examples of flexibility in
Coga's core. Read their workflows, recurring definitions, selected Python
implementations and task metadata. This records generic operating structures;
private business records and narrative quotations are not publication sources.
No job, notification, financial action or filing was executed in this review.

| Inspected example | What the implementation expresses | Implication for Coga's scope |
|---|---|---|
| Admin reminders and monthly routines | Repository scripts read maintained task/template state, calculate the relevant period and prepare notifications. A recurring workflow invokes the named script and records the run; the underlying business action remains with the human. | A completed task can mean that an obligation was surfaced, without claiming that the obligation itself was fulfilled. Recurrence and business completion are separate concepts. |
| Admin preparation and human action | The local `human-gated` workflow specifies agent preparation, owner action, then agent verification and recording. Separate browser workflows describe unattended operation, human review/action, or human execution with agent support. | The repository defines procedures and responsibility boundaries appropriate to the operation. These are workflow definitions; their existence alone does not prove successful execution of every variant. |
| Patent lifecycle | The local workflow represents idea, optional provisional, candidate and granted-utility stages. Domain fields record the case's facts. Separate local scripts inspect those fields, detect changes and identify items needing attention; stage advancement is assigned to human confirmation by the written method. | A task can represent a case maintained over years. A workflow stage can describe the condition of that case, with several kinds of work occurring within it. |
| Proposed invention disclosures | A skill combines a deterministic source gatherer, agent screening and drafting, a human selection step and creation of approved candidate tasks. The gatherer's pending state is separate from its accepted scan state. | Domain judgment, ordinary scripts, human decisions and durable follow-up work can be composed into a repository-owned method. This inspection did not run the scanner or assess its output quality. |

Local evidence locations: `admin/coga/workflows/{human-gated,surface-due-and-notify}.md`,
`admin/coga/workflows/browser/`, the supplier-reminder and payroll-reconciliation
scripts beside their tasks; `patents/coga/workflows/patent/lifecycle-v2.md`,
the sweep/sync scripts under `patents/coga/tasks/repo/`, and
`patents/coga/skills/coga/auto-disclosure/{SKILL.md,gather.py}`. These paths
are relative to the owner's local directory of checkouts, not public links.
Task frontmatter includes completed admin reminder instances and active
patent lifecycle records; that is persisted usage evidence, not independent
verification of the underlying business outcomes.

The current Coga source supports the architectural explanation. Its
[configuration parser](../../src/coga/config.py) accepts declared extension
fields and repository-owned extension tables. The generic
[workflow parser](../../src/coga/workflow.py), [composer](../../src/coga/compose.py)
and [launcher](../../src/coga/commands/launch.py) operate on task state and
selected instructions. The inspected domain calculations live in repository
scripts using files and CLI calls; the core has no special dispatcher for
these administrative or patent procedures. Coga still ships coding workflows
and package commands such as PR handling. The supported claim is flexibility
of the shared task/workflow machinery, not that the package contains no
domain-oriented facilities.

**Version boundary:** some patent recurring templates still use older inline
script syntax. Current core instead recognizes the reserved sibling
`ticket.py` for a deterministic launch phase. The examples establish actual
authored methods and local implementations; this review does not certify that
every checkout is migrated or runnable unchanged against current Coga.

**Comparison with Compound Engineering:** its
[published default loop](https://github.com/EveryInc/compound-engineering-plugin)
centres on building and reviewing software. However, its explicit
[non-code execution route](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-work/references/non-code-execution.md)
produces knowledge-work deliverables while bypassing the coding/shipping
stages. Our earlier CE trial also executed a non-code plan. “Engineering
only” is therefore inaccurate. The defensible distinction is that CE supplies
an engineering-centred method with broader routes, while Coga's common task
runtime supports independently authored methods for recurring operations,
ongoing cases and deliverables. This is a concrete product-scope distinction;
it does not establish that CE cannot be extended to reproduce the examples.

Together with the moving-frontier thesis, these examples supply two forms of
adaptability: the method can vary with the domain of work and can be revised
as the available agents become more capable. The interface for human
direction remains useful across both changes. Neither future capability gains
nor a matched cross-domain superiority claim was tested here.
