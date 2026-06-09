---
title: improve README and doc
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
  - relay/principles
skills: []
workflow: code/with-review
---

## Description

A full editorial pass over `README.md` and `docs/vision.md` — the two
public-facing docs. Two goals: (1) fix the concrete stale/wrong items listed
below, and (2) tighten readability and structure without changing what Relay
*is*. The README's claims and the vision essay's framing must stay consistent
with the canonical `relay/principles`; this pass corrects drift, it does not
re-pitch the product. Scope is exactly these two files — `docs/design.md`,
`docs/market-thesis.md`, and `docs/competition/*` are out of scope.

## Context

Findings from the investigation (verified against `src/relay/cli.py` and the
`FastJVM/relay` git remote on 2026-06-08):

**README.md — objective fixes**

1. Missing command reference entries. The Commands section claims "a one-screen
   entry per CLI command," but two registered built-ins have none:
   - `relay digest` (registered `src/relay/cli.py:84`) — no entry at all.
   - `relay validate` (`src/relay/cli.py:85`; flags `--json`, `--fix`,
     `--check-slack`, `--check`) — mentioned inline in Install / Slack /
     Development but has no `### relay validate` reference entry.
   Add reference entries matching the existing one-screen-per-command style.
2. No License section — repo ships AGPL-3.0 (`LICENSE`); README never states it.

**docs/vision.md — objective fixes**

3. Wrong repo URL on line 14: `github.com/relay-dev/relay`. Canonical is
   `github.com/FastJVM/relay` (git remote, README, and CLAUDE.md all agree).
4. Stale "six-command CLI" claim (line 22). Actual built-in command count is ~18
   (init, create, draft, ticket, launch, status, show, bump, automerge, delete,
   retire, panic, slack, digest, validate, skill, mark, recurring). Prefer a
   non-numeric reframe (e.g. "a small CLI") over a new exact count, which will
   drift again. **Edit line 22 surgically** — the word "six" recurs innocently
   throughout vision.md (e.g. "six months" of operation), so do NOT find-replace
   "six"; only the line-22 *command* claim is wrong.
5. Unfilled placeholder on line 246: a literal `[FILL IN WITH REAL NUMBERS: …]`
   TODO bracket sits in the credibility-anchor section the doc itself flags as
   load-bearing. **Owner-supplied figure (2026-06-08):** roughly **3x more
   productive** since running FastJVM on Relay — measured across PR count, "task
   units," and cost — but the underlying data is confidential and hard to
   extract precisely. So write this as an *honest directional* claim, not a
   fabricated metrics table: state the ~3x improvement across PR throughput /
   task units / cost, and be upfront that exact figures aren't published
   (confidential, hard to quantify). Team composition (two founders + one senior
   engineer, post-reset, ~month six) is already established earlier in the doc —
   reuse it, don't restate numbers you don't have. Do not invent precise metrics,
   automation counts, or domain tallies the owner didn't provide; keep the rest
   qualitative or pull domains from what the repo actually shows.

**Editorial pass (readability/structure — use judgment)**

- README intro is ~35 dense lines before `## Install`; consider a short "what
  you actually type" quickstart near the top.
- Tighten prose, fix any other stale command flags or cross-references found
  while editing. Keep Relay's voice and the principles-driven framing intact.
- Out of scope: splitting the CLI reference into a separate file (cuts against
  Relay's "one obvious file" ethos) — leave the README as the single reference.

Note: `relay/principles` is attached because this pass must preserve the
product's canonical claims/voice; `principles` is canon when README/vision
narrative diverges from it.
