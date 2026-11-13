# Prompt assembly review package

Draft for the owner; no trials have run and no candidate is selected.
Preparing this package is step `agent-produces`. Approval belongs to
`human-owns-and-finishes`; recording that approval belongs to `report-to-coga`.

Read [the protocol](protocol.md), [applicability](applicability.md), and
[the production inventory](inventory.md), then inspect complete prompts under
`prompts/<case>/{baseline,candidate}.md`. These files are specimens, not
instructions for the session preparing or reviewing them.

`manifest.json` records every rendered block's byte range, source, selection
fact and measurements, plus invocation inputs and delivery metadata.
`sources.json` pins production sources to full Git revisions and blob IDs and
records SHA-256 hashes of source snapshots. `fixtures/` contains common files,
per-case overlays, dialogues, analyst records and expected observations.
`candidate/` owns the proposed replacement fragments. Nothing here replaces a
production resource or introduces a runner, registry or configuration language.

The single alternative, C1, separates shared orientation from invocation
authority. It keeps context selection and whole-file context/skill payloads
fixed, keeps existing conduct and execution-loop text, and omits the execution
loop from guided authoring. Its main hypothesis is fewer instruction mistakes,
particularly accidental advancement while authoring. Payload reduction is a
separate possible finding. This is not evidence that C1 is better.

The baseline uses `compose.compose_prompt_report` on ordinary inputs and the
actual `_authoring_ticket` projection on authoring inputs. Autofix uses its
actual independent `build_prompt`. No launch was used to measure these forms.
Each `.md` prompt includes a fixed illustrative launch marker where the real
transport adds one; layer-only and delivered sizes are distinguished in the
manifest. The guided-authoring kickoff and human turns are separate transport
inputs, preserved in the fixture, not appended to the system prompt.

The snapshots include resolved files, not just links. Package originals remain
the owners of current behavior; the copies here are dated experimental inputs.
The source revision is the pre-generation main tip, not a claim that future
main or this package's eventual publication commit has identical builders.

## Owner decision record

Status: **unapproved draft**. The attended session authorized drafting one
candidate, two repetitions and instruction correctness as the primary measure.
That authorization does not approve the complete protocol or start ticket 02.

Before ticket 02: record the owner's accepted package revision/tree hash and
any edits, the exact agent CLI/version/model/settings, and acceptance of all
cases, applicability rules, repetition/order schedule, session limits,
thresholds and stop rules. A changed package needs a new explicit approval.
Do not fill this record with inferred consent or label draft choices accepted.

Limitations to judge: synthetic tasks are deliberately small; two repetitions
cannot establish a general agent-performance effect. The C1 design adds caller
facts and a provenance record; any prototype must count that complexity. The
existing skill-versus-inline exclusivity is preserved rather than redesigned.
