---
title: Design external script/service mechanism
status: draft
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

**Sibling design ticket to `cli-extension-model/propose-declarative-shim-mechanism`.**
Both are the two undesigned mechanisms named by the `relay/extension-model`
context. That ticket designs the **tier-2 shim** (the `→ ticket` enabler); this
one designs the **external script/service** home (the `→ external` enabler).
Keep the two narrow and distinct — do not absorb the shim here.

The model says command-shaped logic has three homes: kernel, tickets/workflows,
and external scripts/tools. The external home splits in two:

- **External tool** — an existing third-party CLI Relay shells out to (`gh`, `op`,
  `git`). Already works; nothing to design.
- **External script / service** — a *Relay-authored* stateless capability that
  lives outside **both** the kernel and the ticket model. This home has **no
  mechanism today**: a stateless Relay operation can currently only be a built-in
  Typer command or a `mode: script` ticket step. There is no first-class surface
  for a Relay-authored stateless script/service that is neither.

Write a design proposal for that surface. It should cover:

1. **Boundary** — what belongs in this home vs. a command, a ticket, an external
   tool, or the kernel. Use the model's tests: stateless + parameterized (not a
   ticket), Relay-authored (not just an external tool), not regress/bootstrap and
   not a mid-flight trust hook (not kernel).
2. **Mechanism candidates** — sketch and compare at least: a `gh`-style extension
   (installable, owns its own argv), a separate package/service Relay depends on,
   and a `relay-os/scripts/` target that `launch` (or a thin dispatcher) can call.
   Say which, and why.
3. **Dispatch** — how invocation reaches it (params stay at the command/Typer
   layer — no transient launch params, no `relay.toml` DSL).
4. **Trust** — acquirers stay external, **verify/inject stays kernel**. Confirm
   the skill installer (`skill install/update/remove`, already a thin `gh skill`
   wrapper) is the worked example, and that secret *values* never route through
   the ticket/prompt/git machinery.
5. **The `→ external` move plan** — which current commands migrate here and in
   what order (skill installer → `gh` extension is the lead candidate;
   `init --update`?), with the carve-outs respected.
6. **Risks** — another dependency to install, provenance/extraction home, betting
   against `gh skill` leaving preview (the README already lists `gh` as an
   external CLI dependency).

Done = a committed markdown design proposal (home it sensibly — `docs/` or a
relay context; say which and why). **The proposal is the deliverable.** Building
the surface/runner is a separate follow-up ticket, gated on greenlight.

## Context

- The ratified rule this implements: `relay/extension-model` (three homes, the
  external tool vs external-script/service split, the trust-straddle, the
  guardrails). Read it first — this ticket fills its one named-but-undesigned
  `→ external` gap.
- The verb-by-verb evidence and the worked `skill` example: `docs/cli-extension-audit.md`.
- The exemplar to subsume: `src/relay/commands/skill.py` (~193 lines) — already a
  thin wrapper on `gh skill` adding provenance (`.relay-source.json`), digest
  local-adaptation detection, conflict status, `--force` semantics. The PR thread
  flagged the natural extraction is a `gh` extension, deferred until a second
  consumer or `gh skill` GA — this proposal decides that.
- Sibling/ordering: `propose-declarative-shim-mechanism` (tier-2 shim) is move 2,
  this is move 3, in the model's "sequenced externalization" section. Move 1
  (reads/`recurring` → script shims) needs no new mechanism.

**Out of scope:** implementing the surface, migrating any command, the tier-2
shim (its own ticket), and the move-1 ticket work. Design only.
