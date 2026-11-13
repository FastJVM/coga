# Prompt assembly review package

Owner-approved package; no trials have run and no candidate is selected.
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

Status: **approved by the owner on 2026-11-12** during step
`human-owns-and-finishes`, which the owner explicitly advanced. Recorded in
step `report-to-coga`.

Accepted without edits: the complete baseline and C1 examples, the
applicability contract, all cases and predeclared expected outcomes, paired
controls and counterbalanced order, the session limits with the 60-session
ceiling and its reserve, primary and secondary thresholds, hard gates, stop
rules and separate-dimension reporting, all as written in `protocol.md`.
Accepted review-package tree SHA-256 (method in `sources.json`):
`f5ee59e2cd8ebf2d88f17f5ea9623b4699bee2cad3b1fa5a6cc34cec5e10dbbc`.
Writing this record changed only this README section and its intro line; the
resulting metadata-only hashes are recorded separately in `sources.json`
under `decision_record`. Every other attachment is byte-identical to the
accepted package.

Owner clarifications: keep two repetitions per arm and case; no expanded
reliability study at this stage. The owner judges the results at the end.
Report the observed outcomes and their limits without claiming broader
reliability. Correctness gates remain in force. Approval does not select C1
and does not authorize production migration.

Execution pins selected by the owner, applied identically to both arms:
Codex, model `gpt-6.1-sol` ("Sol"), reasoning effort `medium`. Observed on
2026-11-12 (no model session started):

| Pin | Value |
| --- | --- |
| CLI | `codex-cli 0.167.2` |
| Executable | `/home/n/.codex/packages/standalone/releases/0.167.2-x86_64-unknown-linux-musl/bin/codex` |
| Executable SHA-256 | `a9672d0fa0dd8fcf8cad136fa0d056b914bc046f5ac3d78f4a5cf390655af56b` |
| Model | `gpt-6.1-sol` from the local model cache; `medium` listed as supported. This identifier is not an immutable provider version: keep each pair adjacent; a detected change invalidates the pair |
| Reasoning | The local Codex config defaults to `high`, so every run passes `-m gpt-6.1-sol -c model_reasoning_effort="medium"` explicitly |
| Sampling/seed | `codex exec --help` exposes no temperature or seed flag; none is passed |
| OS / Python | Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.12.12 |
| Coga agent config | `coga/coga.toml` SHA-256 `1d64d233bb7ba4fb8a810cf20bd1c1e3f448884b282fd0805311539cff8234e2`: `launch_args = "--no-daemon"`, `discussion = "-c developer_instructions={prompt}"` |
| Transport templates | Ordinary/queued interactive: `codex --no-daemon <pins> <prompt>` (positional first message); guided authoring/discussion: `codex --no-daemon <pins> -c developer_instructions=<prompt>`, then the fixture kickoff as a separate turn; autofix one-shot: `codex <pins> exec <prompt>` (`DEFAULT_ANALYZE_TEMPLATES`) |
| Token/time limits | Per-case limits and totals in `protocol.md` "Budget and conduct script" |

Pins still open, to settle with the owner before the first ticket 02 session:
the trial/prototype revision (it does not exist yet), the sandbox and
approval policy passed to Codex for the trial fixture, the environment-key
policy, and a recheck of every pin above. Any change requires recording it,
and a changed package requires new explicit approval.

Limitations to judge: synthetic tasks are deliberately small; two repetitions
cannot establish a general agent-performance effect. The C1 design adds caller
facts and a provenance record; any prototype must count that complexity. The
existing skill-versus-inline exclusivity is preserved rather than redesigned.
