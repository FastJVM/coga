---
slug: improve-readme
title: improve-readme
status: draft
mode: agent
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
  - coga/principles
skills: []
workflow: docs/with-review
secrets: null
script: null
---

## Description

Rewrite the top-level `README.md`. The current version (920 lines) reads as
AI slop — it front-loads a full CLI command reference and over-explains before
it has earned attention. Replace it with something minimal and human that a
first-time reader actually finishes.

Target shape, in this order:

1. **Hook + one short paragraph** — open minimal, then a single tight
   paragraph whose only job is to convince someone this is worth using. No
   throat-clearing, no restating the tagline three ways.
2. **Install** — the shortest path to `coga` on your PATH. Lead with `uv`
   (verify the correct incantation against how the package is published —
   `uv tool install coga` for an isolated CLI, or `uv pip install coga`); the
   editable-from-source path can stay but should be secondary.
3. **Demo** — one paragraph or a short transcript that makes what Coga *does*
   obvious at a glance. Only include this if it genuinely lands; **if the best
   you can write is weak, drop the section entirely** rather than shipping a
   flat demo.
4. **Key values** — a short section on what makes Coga different: it surfaces
   everything (you're in charge, nothing hidden, your corrections compound,
   markdown + git on your disk, no lock-in). This is the manifesto/vision
   distilled to a few lines — pull from the attached `coga/principles` context
   and `docs/vision.md`, don't reinvent it.

Done = a dramatically shorter README that follows this arc and reads like a
person wrote it. Ruthlessly cut; brevity is the point.

## Context

- **Current README:** `README.md` at repo root, 920 lines. Skim it for the
  real install steps and the genuine feature claims, but treat almost all of
  it as material to cut, not preserve. The exhaustive `## Commands` reference
  (every `coga <cmd>`) does **not** belong in the README — link out or drop it.
- **Voice source:** `docs/vision.md` is the public-facing manifesto (Pirsig
  classical-vs-romantic framing, "don't don't think — think better", compounding
  context, legibility, no lock-in). The attached `coga/principles` context is
  the canonical distilled form — when the two diverge, `principles` is canon.
  Match that voice; do not out-manifesto it.
- **Install reality:** Coga is a Python package published as `coga`
  (`pip install coga` / `pipx install coga` today). Confirm the exact `uv`
  command works before writing it — don't assume.
- **Scope:** README-only, docs change, no code. Keep the diff to `README.md`.
  If a demo requires a feature that doesn't exist yet, don't invent it — write
  from what's real or drop the demo.
- **The trap to avoid:** the reason this ticket exists is generated-prose bloat.
  The human owns the final voice at the review gate; the draft is a starting
  point to be cut down, not the finished product.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

**Clarity for a fresh agent: strong.** The Description gives a concrete 4-part target arc (Hook → Install → Demo → Key values), a clear Done definition, and a stated editorial intent ("reads like a person wrote it, ruthlessly cut"). An agent with no prior context could absolutely start. The `## Context` section is unusually good — it names the current README, the voice source, the install reality, the scope fence, and even "the trap to avoid." This is above the median ticket for pick-up-ability.

**Workflow fit: correct.** `docs/with-review` is the right pick. The change is markdown-only (`README.md`), and the workflow explicitly exists for README/prose edits — its peer-review step reviews prose/accuracy/cross-copy sync instead of running `/code-review` + pytest on a no-code diff. No mismatch. One small note: the workflow's cross-copy-sync step (`coga/` vs `src/coga/resources/templates/coga/`) is a no-op here since the top-level `README.md` isn't a shipped template copy — harmless, just won't apply.

**Contexts: thin but defensible.** Only `coga/principles` is attached. That is the canonical distilled voice source, so it's the right single attachment. But note a real gap: the ticket leans heavily on `docs/vision.md` too ("pull from the attached `coga/principles` context and `docs/vision.md`"), yet `vision.md` is *not* attached — it's only referenced by path in the prose. The agent will have to open it manually. That's fine (the ticket says where it is), but if you wanted it composed into the prompt you'd attach it. Given vision.md is 260 lines of manifesto, *not* attaching it whole is arguably the right call — but then the ticket is asking the agent to go read a long file it didn't get handed.

**Should the needed fact have been copied into `## Context` instead of attaching `coga/principles` whole?** Partly, yes. The actual deliverable for section 4 ("Key values") is a ~5-line distillation: you're in charge, nothing hidden, corrections compound, markdown+git on disk, no lock-in. The ticket already lists those five in the Description (line 40-41). So the load-bearing facts are *already inline*. Attaching the whole `principles` context is then belt-and-suspenders for voice-matching — reasonable, low cost, not a problem. No important context is missing.

**Scope: reasonable, one ticket's worth.** It's a single-file rewrite with a fixed target shape. Not bundled. The "ruthlessly cut 920→short" framing keeps it bounded. The only scope-creep risk is implicit: deciding *what* to cut from a 920-line README (the entire `## Commands` reference, Dream/REM, notifications, etc.) is judgment-heavy, but the ticket pre-answers it ("the exhaustive `## Commands` reference does not belong — link out or drop it"). Good.

**Assumptions to question before launch:**

1. **The `uv` install command is unverified and the ticket knows it.** The Description says "lead with `uv`" but the current README ships `pip`/`pipx` only, and `## Context` admits "Confirm the exact `uv` command works before writing it — don't assume." This is the biggest live risk: the ticket is *instructing* a voice/tone rewrite but also asking the agent to make a factual packaging claim it flags as unconfirmed. If the package isn't actually installable via `uv tool install coga` (e.g. not on PyPI, or name differs), the agent could ship a broken install line. The instruction to verify is present but easy for a prose-focused agent to skim past. **Recommend: confirm the package is on PyPI as `coga` and pick the exact `uv` incantation before launch, or downgrade the "lead with uv" instruction to "keep pip, add uv if it works."** Note the README's git URL is `github.com/FastJVM/coga` — worth confirming the PyPI name matches.

2. **"Drop the demo if weak" is a soft escape hatch that invites skipping the hardest part.** Section 3 tells the agent to drop the demo entirely "if the best you can write is weak." A prose-generating agent will be tempted to self-declare its demo weak and cut it, avoiding the one section that requires real product understanding. Combined with "don't invent a feature that doesn't exist," a lazy pass produces a README with no demo at all — technically compliant, but the demo is what makes "what Coga does obvious at a glance." **Recommend the human decide up front** whether a demo is required, or the review gate should specifically check for its presence/quality.

3. **Voice ceiling is stated but subjective.** "Match that voice; do not out-manifesto it" and "don't reinvent it" are good guardrails, but the current README opener (Pirsig, "Don't don't think. Think better.") is *already* fairly manifesto-heavy. The agent has no crisp signal for how much voice is too much — this will land on the human at the `review` gate, which is where the ticket correctly puts final voice ownership. Not a blocker, just know the review step is doing real work here, not rubber-stamping.

**Bottom line:** Ready to launch. Description and context are clear, workflow and contexts are appropriate, scope is contained. The one thing to nail down before launch is the `uv` install command (verify PyPI publication + exact incantation), and I'd give the agent a firmer steer on whether the demo is mandatory rather than leaving it a self-graded drop.
