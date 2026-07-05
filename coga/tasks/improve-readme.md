---
slug: improve-readme
title: improve-readme
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/principles
skills: []
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 4 (review)
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
3. **Key values** — a short section on what makes Coga different: it surfaces
   everything (you're in charge, nothing hidden, your corrections compound,
   markdown + git on your disk, no lock-in). This is the manifesto/vision
   distilled to a few lines — pull from the attached `coga/principles` context
   and `docs/vision.md`, don't reinvent it.

No demo/example section — deliberately out of scope for this rewrite.

Done = a dramatically shorter README that follows this arc and reads like a
person wrote it. Ruthlessly cut; brevity is the point.

## Context

- **Current README:** `README.md` at repo root, 920 lines. Skim it for the
  real install steps and the genuine feature claims, but treat almost all of
  it as material to cut, not preserve. The exhaustive `## Commands` reference
  (every `coga <cmd>`) does **not** belong in the README — drop it. The real
  command reference and guides are handled by the companion ticket
  `write-real-coga-documentation-command-reference-gu`; a bare "Full docs →"
  pointer is fine, but don't try to preserve the reference content here.
- **Voice source:** `docs/vision.md` is the public-facing manifesto (Pirsig
  classical-vs-romantic framing, "don't don't think — think better", compounding
  context, legibility, no lock-in). The attached `coga/principles` context is
  the canonical distilled form — when the two diverge, `principles` is canon.
  Match that voice; do not out-manifesto it.
- **Install reality (verified):** Coga is on PyPI as `coga` (v0.2.0, requires
  Python ≥3.11; repo `github.com/FastJVM/coga`). Lead the install section with
  `uv tool install coga` — that's the isolated-CLI path that puts `coga` on the
  PATH, the direct replacement for today's `pipx install coga`. `uv pip install
  coga` is the into-an-environment fallback, and plain `pip install coga` still
  works. Keep the editable-from-source path (`git clone` + `pip install -e .`)
  but make it secondary. These commands are confirmed against PyPI — don't
  re-derive or substitute a guessed incantation.
- **Scope:** README-only, docs change, no code. Keep the diff to `README.md`.
  No demo section. Full command reference / real docs are a separate ticket
  (`write-real-coga-documentation-command-reference-gu`) — link out, don't
  inline.
- **The trap to avoid:** the reason this ticket exists is generated-prose bloat.
  The human owns the final voice at the review gate; the draft is a starting
  point to be cut down, not the finished product.

## PR

https://github.com/FastJVM/coga/pull/520

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

_Evaluator review resolved and merged into `## Context` (2026-07-04): `uv`
install command verified against PyPI (`coga` v0.2.0) and baked into the Install
reality bullet; the demo section is already out of scope in the Description, so
the reviewer's demo/4-part-arc notes are moot. Blackboard cleared — ready to
launch._

## Dev

- branch: codex/improve-readme
- worktree: /tmp/coga-improve-readme
- pr: https://github.com/FastJVM/coga/pull/520
- Plan: replace `README.md` with a short README-only public entry point: hook,
  install, key values, and a pointer to the companion docs ticket for the full
  command guide.
- Commit: 207a97ed1c63dae44c9077bede260983373f56ea (`Rewrite README`)
- Result: `README.md` only, reduced from 918 lines to 73 lines. Shape is hook +
  one paragraph, install, key values; no demo and no command reference.
- Verification:
  - `git diff --check`
  - `test -f docs/vision.md`
  - `test -f coga/contexts/coga/principles/SKILL.md`
  - `coga --help`
  - `PYTHONPATH=src python -m coga --help`
  - Note: `python -m coga.cli --help` failed in the ambient interpreter because
    the source checkout is not installed there; verified the actual README
    surface with `coga --help` instead.

## Open PR

- PR opened: https://github.com/FastJVM/coga/pull/520 (base `main`).
- On open, the PR was `CONFLICTING`/`DIRTY`: `main` had advanced and also
  touched `README.md`. Merged `origin/main` into `codex/improve-readme`; the
  only content conflict was `README.md` (main re-introduced the long command
  reference this ticket removes). Resolved with `git checkout --ours README.md`
  (kept the 73-line rewrite); all other files auto-merged from main.
- Post-merge state: `git diff --name-only origin/main...HEAD` → `README.md`
  only; `git diff --check` clean; PR now `MERGEABLE`/`CLEAN`.
- Docs re-verification: referenced links resolve — `docs/vision.md`,
  `coga/contexts/coga/principles/SKILL.md`, `LICENSE` all present. No pytest run
  because the merge touched no code/fixtures on this branch's diff (README-only).

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":1054208,"cli":"codex","input_tokens":155486,"model":"gpt-5.5","output_tokens":10817,"provider":"openai","schema":1,"session_id":"019f303b-801a-77f2-a9eb-f227f34c13b4","slug":"improve-readme","step":"implement","title":"improve-readme","ts":"2026-07-05T03:07:50.662378Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":460672,"cli":"codex","input_tokens":142597,"model":"gpt-5.5","output_tokens":4548,"provider":"openai","schema":1,"session_id":"019f303f-26b2-7841-b8c7-0eea3c61c399","slug":"improve-readme","step":"peer-review","title":"improve-readme","ts":"2026-07-05T04:13:41.505344Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":96589,"cache_read_input_tokens":1954381,"cli":"claude","input_tokens":26275,"model":"claude-opus-4-8","output_tokens":19920,"provider":"anthropic","schema":1,"session_id":"b7bb5aca-0ef2-4e00-9162-9afa87247bf9","slug":"improve-readme","step":"open-pr","title":"improve-readme","ts":"2026-07-05T04:16:15.475301Z","usage_status":"ok"}
## Peer Review

- Native review: `codex review --base main` initially hit the known read-only
  app-server setup error in the sandbox; rerun outside the sandbox completed
  with no factual or functional findings.
- Manual content pass: reviewed `README.md` against `main`, `docs/vision.md`,
  `coga/contexts/coga/principles/SKILL.md`, and `pyproject.toml`. The
  implementation commit changes only `README.md`, keeps the requested arc, drops
  the command reference/demo, and uses the verified install commands.
- Link/reference pass: `docs/vision.md`,
  `coga/contexts/coga/principles/SKILL.md`, and `LICENSE` are present. No
  context/template cross-copy sync needed because this is README-only.
- Verification: `git diff --check main -- README.md`; no pytest run because no
  code or fixture changed.
