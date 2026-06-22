---
title: Design the core boundary + external-script surface
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/extension-model
- relay/architecture
- relay/codebase
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
step: 1 (execute)
---

## Description

**Part of `cli-extension-model/` — Pass 1 (design: what stays *core*, what goes
*external*). Companion to `move-command-logic-to-tickets` (Pass 2: the `→ ticket`
execution). These are one decision split by direction — the trust-straddle means
"what stays kernel" and "what becomes an external script" are the same pen stroke,
so they live in one doc.**

Two halves, one design doc:

### A. The core boundary (explain — mostly settled)

`relay/extension-model` already fixes the kernel as `launch` + its dependency
closure (the `mark`/`bump` state-writes, secret injection, skill
verify-at-compose, notify) + fresh `init`. Restate that boundary as the doc's
premise, and **close the one open item**: `skill verify-at-compose` is classified
kernel but **not yet built** — specify it (compose fails loud when a loaded
skill's tree digest ≠ its recorded provenance digest) so the boundary is real, not
aspirational. The integrity checks live only in the `skill install` path today.

### B. The external-script/service surface (design — new)

The third home has no mechanism yet: a *Relay-authored* stateless capability that
lives outside **both** the kernel and the ticket model can today only be a built-in
command or a `mode: script` step. Design the first-class surface. Cover:

1. **Boundary** — what belongs here vs. command / ticket / external-tool / kernel
   (model tests: stateless + parameterized, Relay-authored, not regress/bootstrap
   and not a mid-flight trust hook).
2. **Mechanism candidates** — compare a `gh`-style extension (installable, owns its
   own argv), a separate package/service Relay depends on, and a `relay-os/scripts/`
   dispatch target. Pick one, say why.
3. **Dispatch** — params stay at the command/Typer layer (no transient launch
   params, no `relay.toml` DSL).
4. **Trust** — acquirers stay external, **verify/inject stays kernel**; the skill
   installer (`skill install/update/remove`, already a thin `gh skill` wrapper) is
   the worked example; secret *values* never route through the ticket/prompt/git
   machinery.
5. **The `→ external` move plan** — which commands migrate (skill installer → `gh`
   extension is the lead candidate; `init --update`?), in what order, carve-outs
   respected.
6. **Risks** — another dependency to install, provenance/extraction home, betting
   against `gh skill` leaving preview (the README already lists `gh` as an external
   CLI dependency).

Done = a committed markdown design doc covering **both halves** (home it sensibly —
`docs/` or a relay context; say which and why). **The doc is the deliverable.**
Building the verify-at-compose hook and the external-script surface are follow-ups,
gated on greenlight.

## Context

- The ratified rule this implements: `relay/extension-model` (three homes, the
  external tool vs external-script/service split, the trust-straddle, the
  guardrails). Read it first — Pass 1 fills its named-but-undesigned `→ external`
  gap and closes the verify-at-compose hook it flags as not-yet-built.
- The verb-by-verb evidence and the worked `skill` example: `docs/cli-extension-audit.md`.
- The exemplar to subsume: `src/relay/commands/skill.py` (~193 lines) — already a
  thin wrapper on `gh skill` adding provenance (`.relay-source.json`), digest
  local-adaptation detection, conflict status, `--force` semantics. The PR thread
  flagged the natural extraction is a `gh` extension, deferred until a second
  consumer or `gh skill` GA — this doc decides that.
- Companion: `move-command-logic-to-tickets` (Pass 2) owns the `→ ticket`
  execution (reads, `recurring`, and the tier-2 shim for the fused heads).
  `add-recurring-launch-aliases` is independent alias sugar.

**Out of scope:** implementing the surface or the verify hook, migrating any
command, and the `→ ticket` move work (Pass 2). Design only.
